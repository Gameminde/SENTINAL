"""Tests for Task 9 / F-A2.1 — Context-Sanitization Property Coverage.

These tests generate secret-shaped strings with Hypothesis and prove:

1. ``sanitize_context_text`` redacts every generated secret such that
   the original token is not substring-present in the sanitized
   output.
2. Building an ``LLMDecisionFrame`` from a ``ReceiptRecord`` whose
   ``text`` (raw body) carries arbitrary content never embeds that
   raw body into the frame — only ``receipt_id``, ``evidence_refs``,
   and the sanitized ``summary`` are carried through.
3. Normal prose context is not destroyed by the sanitizer.
4. Secrets embedded inside JSON-shaped nested structures are redacted
   by ``sanitize_context_payload`` (the structured-text entry point).

CP-9.1 (Secret Redaction Coverage):
    ∀ generated secret S: sanitize_context_text(S) != S
    ∧ S is not a substring of sanitize_context_text(S).

CP-9.2 (Raw Body Isolation):
    ∀ ReceiptRecord R, frame = LLMDecisionFrame.build(..., [card(R)], ...):
        R.text is not a substring of frame.render_prompt_text()
        ∧ R.text is not a substring of str(frame.model_dump()).
"""

from __future__ import annotations

import base64
import json
import string

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from sentinel.agent import (
    AuthorityCardBuilder,
    ContextBudgetPolicy,
    ContextNeedEstimator,
    LLMDecisionFrame,
    ModelCapabilityProfile,
    ModelCostProfile,
    PromptBudgetAllocator,
    QualityExpectationContract,
    StateCardBuilder,
    UserModelContract,
)
from sentinel.agent.evidence_ranker import (
    EvidenceCard,
    EvidenceRanker,
    sanitize_context_payload,
    sanitize_context_text,
)
from sentinel.agent.receipt_retriever import ReceiptRecord


# ---------------------------------------------------------------------------
# Hypothesis strategies for secret-shaped strings.
# ---------------------------------------------------------------------------

_ALNUM = string.ascii_letters + string.digits
_B64URL = string.ascii_letters + string.digits + "-_"


@st.composite
def _openai_key(draw) -> str:
    body = draw(
        st.text(alphabet=_ALNUM + "-_", min_size=10, max_size=48)
    )
    return f"sk-{body}"


@st.composite
def _stripe_key(draw) -> str:
    kind = draw(st.sampled_from(["live", "test"]))
    body = draw(st.text(alphabet=_ALNUM, min_size=10, max_size=32))
    return f"sk_{kind}_{body}"


@st.composite
def _aws_access_key(draw) -> str:
    prefix = draw(st.sampled_from(["AKIA", "ASIA", "AROA", "AIDA"]))
    body = draw(
        st.text(alphabet=string.ascii_uppercase + string.digits, min_size=16, max_size=16)
    )
    return f"{prefix}{body}"


@st.composite
def _github_token(draw) -> str:
    prefix = draw(st.sampled_from(["ghp", "gho", "ghu", "ghs", "ghr"]))
    body = draw(st.text(alphabet=_ALNUM, min_size=20, max_size=40))
    return f"{prefix}_{body}"


@st.composite
def _github_pat(draw) -> str:
    body = draw(st.text(alphabet=_ALNUM + "_", min_size=20, max_size=50))
    return f"github_pat_{body}"


@st.composite
def _google_api_key(draw) -> str:
    # Google keys are strictly 39 chars: "AIza" + 35 base64-ish.
    body = draw(st.text(alphabet=_ALNUM + "-_", min_size=35, max_size=35))
    return f"AIza{body}"


@st.composite
def _slack_token(draw) -> str:
    prefix = draw(st.sampled_from(["xoxb", "xoxp", "xoxa", "xoxr", "xoxs"]))
    body = draw(st.text(alphabet=_ALNUM + "-", min_size=10, max_size=40))
    return f"{prefix}-{body}"


@st.composite
def _jwt_token(draw) -> str:
    header = draw(st.text(alphabet=_B64URL, min_size=5, max_size=20))
    payload = draw(st.text(alphabet=_B64URL, min_size=5, max_size=30))
    sig = draw(st.text(alphabet=_B64URL, min_size=5, max_size=30))
    # Real JWTs start with `eyJ` (base64 of `{"`).
    return f"eyJ{header}.{payload}.{sig}"


@st.composite
def _pem_private_key(draw) -> str:
    kind = draw(st.sampled_from(["RSA", "EC", "DSA", ""]))
    label = f"{kind} PRIVATE KEY" if kind else "PRIVATE KEY"
    body_chunks = draw(
        st.lists(
            st.text(alphabet=_ALNUM + "+/=", min_size=8, max_size=64),
            min_size=2,
            max_size=8,
        )
    )
    body = "\n".join(body_chunks)
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----"


@st.composite
def _db_connection_string(draw) -> str:
    scheme = draw(
        st.sampled_from(
            ["postgres", "postgresql", "mysql", "mariadb", "mongodb", "redis"]
        )
    )
    user = draw(st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=10))
    # Password chars intentionally exclude `@`, `:`, `/`, whitespace to
    # keep the URL well-formed; the regex handles the generated shape.
    pw = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + "_-.",
            min_size=4,
            max_size=16,
        )
    )
    host = draw(st.text(alphabet=string.ascii_lowercase + ".", min_size=3, max_size=20))
    return f"{scheme}://{user}:{pw}@{host}:5432/app"


@st.composite
def _bearer_token(draw) -> str:
    body = draw(st.text(alphabet=_ALNUM + "._~+/=-", min_size=10, max_size=40))
    return f"Bearer {body}"


@st.composite
def _authorization_header(draw) -> str:
    body = draw(st.text(alphabet=_ALNUM + "._~+/=-", min_size=10, max_size=40))
    sep = draw(st.sampled_from([": ", "=", " = "]))
    return f"Authorization{sep}Bearer {body}"


@st.composite
def _name_equals_value(draw) -> str:
    name = draw(
        st.sampled_from(
            [
                "api_key",
                "api-key",
                "apikey",
                "access_token",
                "access-token",
                "auth_token",
                "refresh_token",
                "client_secret",
                "private_key",
                "token",
                "secret",
                "password",
                "passwd",
                "pwd",
            ]
        )
    )
    sep = draw(st.sampled_from(["=", ": ", ":", " = "]))
    value = draw(
        st.text(
            alphabet=_ALNUM + "-_.",
            min_size=6,
            max_size=40,
        )
    )
    return f"{name}{sep}{value}"


@st.composite
def _base64_long_token(draw) -> str:
    # A `name=value` wrapper ensures the generic regex fires even when
    # the token itself is indistinguishable from non-secret random text.
    raw = draw(st.binary(min_size=24, max_size=64))
    token = base64.b64encode(raw).decode("ascii").rstrip("=")
    name = draw(st.sampled_from(["token", "secret", "auth_token"]))
    return f"{name}={token}"


_SECRET_STRATEGIES = st.one_of(
    _openai_key(),
    _stripe_key(),
    _aws_access_key(),
    _github_token(),
    _github_pat(),
    _google_api_key(),
    _slack_token(),
    _jwt_token(),
    _pem_private_key(),
    _db_connection_string(),
    _bearer_token(),
    _authorization_header(),
    _name_equals_value(),
    _base64_long_token(),
)


# ---------------------------------------------------------------------------
# CP-9.1 — secret-shaped strings are always redacted.
# ---------------------------------------------------------------------------


@given(secret=_SECRET_STRATEGIES)
@settings(deadline=None, max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_secret_patterns_always_redacted_property(secret: str) -> None:
    """Any secret drawn from the strategies above is redacted. The
    sanitized output differs from the input, and the original secret
    token is not substring-present in the sanitized string.
    """
    sanitized = sanitize_context_text(secret)
    assert sanitized != secret, f"Sanitizer did not touch secret: {secret!r}"
    # Special case: URL-style connection strings preserve the host
    # tail after the `@` on purpose (the regex only eats the
    # ``scheme://user:pw@`` prefix). We just assert the password
    # segment between `:` and `@` is gone.
    if "://" in secret and "@" in secret:
        # Extract the credential segment and assert it is absent.
        scheme_tail = secret.split("://", 1)[1]
        cred, _host = scheme_tail.split("@", 1)
        assert cred not in sanitized, f"Credential not redacted: {cred!r} in {sanitized!r}"
    else:
        assert secret not in sanitized, (
            f"Secret survived redaction: {secret!r} still in {sanitized!r}"
        )


@given(
    prefix=st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=20),
    secret=_SECRET_STRATEGIES,
    suffix=st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=20),
)
@settings(deadline=None, max_examples=100)
def test_secret_redacted_when_embedded_in_prose(
    prefix: str, secret: str, suffix: str
) -> None:
    """Secrets embedded inside a larger string are redacted without
    requiring the secret to start or end the line."""
    combined = f"{prefix} {secret} {suffix}".strip()
    sanitized = sanitize_context_text(combined)
    if "://" in secret and "@" in secret:
        scheme_tail = secret.split("://", 1)[1]
        cred, _ = scheme_tail.split("@", 1)
        assert cred not in sanitized
    else:
        assert secret not in sanitized


# ---------------------------------------------------------------------------
# Preservation — the sanitizer does not destroy normal context.
# ---------------------------------------------------------------------------


_NORMAL_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + " .,;:!?'-",
    min_size=0,
    max_size=200,
).filter(
    # Exclude strings that happen to match a secret pattern by coincidence.
    lambda t: (
        "sk-" not in t.lower()
        and "sk_live_" not in t
        and "sk_test_" not in t
        and "AKIA" not in t
        and "ghp_" not in t
        and "gho_" not in t
        and "ghu_" not in t
        and "ghs_" not in t
        and "ghr_" not in t
        and "github_pat_" not in t
        and "AIza" not in t
        and "xoxb-" not in t
        and "xoxp-" not in t
        and "eyJ" not in t
        and "Bearer " not in t
        and "Authorization" not in t
        and "PRIVATE KEY" not in t
        # Exclude the generic name=value names.
        and not any(
            word in t.lower()
            for word in (
                "api_key",
                "api-key",
                "apikey",
                "access_token",
                "auth_token",
                "refresh_token",
                "client_secret",
                "private_key",
                "password",
                "passwd",
                "secret",
                " token",
                "pwd",
            )
        )
    )
)


@given(text=_NORMAL_TEXT)
@settings(deadline=None, max_examples=100)
def test_mixed_text_preserves_non_secret_context(text: str) -> None:
    """Non-secret prose passes through unchanged."""
    assert sanitize_context_text(text) == text


def test_prose_fixture_unchanged_by_sanitizer():
    """Explicit non-property example — a full sentence of normal
    evidence summary survives sanitization byte-for-byte."""
    text = (
        "The evaluator compared pricing evidence from the browser "
        "capture against the api receipt. Both receipts agreed that "
        "the listed price is within the expected band."
    )
    assert sanitize_context_text(text) == text


# ---------------------------------------------------------------------------
# CP-9.2 — raw body never leaks into the decision frame.
# ---------------------------------------------------------------------------


def _user_model() -> UserModelContract:
    model = "deepseek-v4-pro"
    return UserModelContract(
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.14,
            output_usd_per_1m=0.28,
            cached_input_usd_per_1m=0.07,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=128_000,
            supports_tool_calling=True,
            supports_prompt_caching=True,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=320,
            max_evidence_tokens=1_500,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="broad_exploration",
            minimum_evidence_refs=1,
            retry_budget=1,
        ),
    )


# Distinctive markers that HAVE to survive if carried — we use
# obviously-non-secret alphabets so the sanitizer itself does not mask
# the leak detection.
_RAW_BODY_ALPHABET = string.ascii_letters + string.digits + " .,;-"


@given(
    raw_body=st.text(alphabet=_RAW_BODY_ALPHABET, min_size=30, max_size=500),
    summary=st.text(alphabet=_RAW_BODY_ALPHABET, min_size=5, max_size=60),
)
@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_raw_body_never_in_decision_frame_property(raw_body: str, summary: str) -> None:
    """Build an LLMDecisionFrame from a receipt whose ``text`` (the
    raw-body field) carries arbitrary content; the frame MUST NOT
    embed that raw body in either ``render_prompt_text()`` or
    ``str(model_dump())``. Only the sanitized ``summary`` and
    ``receipt_id`` / ``evidence_refs`` should cross the boundary.

    We require ``raw_body`` to be distinct from ``summary`` (and to
    carry a unique marker) so the assertion is meaningful even when
    the strategies coincidentally generate overlapping text."""
    marker = "ZZ_RAW_BODY_UNIQUE_MARKER_ZZ"
    full_raw_body = f"{raw_body} {marker}"
    assume(marker not in summary)

    receipt = ReceiptRecord(
        receipt_id="r_rawbody",
        source_type="browser",
        summary=summary,
        text=full_raw_body,
        evidence_refs=["ev_rawbody"],
        relevance_tags=["relevance"],
        critical=True,
    )

    need = ContextNeedEstimator().estimate(
        mission_id="m_rawbody",
        objective="Inspect ranked evidence without leaking raw body.",
        blockers=[],
        required_evidence_refs=["ev_rawbody"],
        candidate_tools=["browser_read"],
    )

    cards = EvidenceRanker().rank([receipt], need)
    allocator = PromptBudgetAllocator(_user_model())

    frame = LLMDecisionFrame.build(
        mission_id="m_rawbody",
        mission_card=StateCardBuilder().mission_card(need),
        authority_card=AuthorityCardBuilder().authority_card(
            allowed_tools=["browser_read"], forbidden_tools=[], constraints=[]
        ),
        progress_card=StateCardBuilder().progress_card(completed=[], pending=[]),
        evidence=cards,
        selected_tool_surface=["browser_read"],
        current_blockers=[],
        next_decision_options=[],
        required_output_schema={"decision": "string"},
        budget_allocator=allocator,
    )

    rendered = frame.render_prompt_text()
    dumped = json.dumps(frame.model_dump(mode="json"), sort_keys=True, ensure_ascii=True)

    assert marker not in rendered, "Raw-body marker leaked into rendered prompt."
    assert marker not in dumped, "Raw-body marker leaked into frame dump."
    # Positive assertion: the receipt id IS present (proving the
    # frame built without erasing the pointer, so the assertion
    # above is not vacuously true).
    assert "r_rawbody" in dumped


def test_raw_body_with_secret_is_double_isolated():
    """Belt-and-braces: even if the raw body contains a secret,
    (a) the raw body must not appear in the frame, and (b) if any
    tail of the body somehow survives, the secret inside it must be
    redacted by the sanitizer."""
    receipt = ReceiptRecord(
        receipt_id="r_secret_body",
        source_type="browser",
        summary="Summary describes a page with credentials.",
        text="Authorization: Bearer leaky_token_abcdef123456789012 END_MARKER",
        evidence_refs=["ev_secret_body"],
        relevance_tags=["credentials"],
        critical=True,
    )

    need = ContextNeedEstimator().estimate(
        mission_id="m_secret_body",
        objective="Review credentials receipt without leaking token.",
        blockers=[],
        required_evidence_refs=["ev_secret_body"],
        candidate_tools=["browser_read"],
    )

    cards = EvidenceRanker().rank([receipt], need)
    allocator = PromptBudgetAllocator(_user_model())
    frame = LLMDecisionFrame.build(
        mission_id="m_secret_body",
        mission_card=StateCardBuilder().mission_card(need),
        authority_card=AuthorityCardBuilder().authority_card(
            allowed_tools=["browser_read"], forbidden_tools=[], constraints=[]
        ),
        progress_card=StateCardBuilder().progress_card(completed=[], pending=[]),
        evidence=cards,
        selected_tool_surface=["browser_read"],
        current_blockers=[],
        next_decision_options=[],
        required_output_schema={"decision": "string"},
        budget_allocator=allocator,
    )
    dumped = json.dumps(frame.model_dump(mode="json"), sort_keys=True, ensure_ascii=True)
    rendered = frame.render_prompt_text()
    assert "leaky_token_abcdef123456789012" not in dumped
    assert "leaky_token_abcdef123456789012" not in rendered
    assert "END_MARKER" not in dumped
    assert "END_MARKER" not in rendered


# ---------------------------------------------------------------------------
# Structured / nested redaction.
# ---------------------------------------------------------------------------


def test_nested_secret_redaction_in_dict():
    """``sanitize_context_payload`` walks dicts recursively."""
    payload = {
        "evidence": [
            {"summary": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhIn0.signature_here"},
            {"summary": "normal text"},
        ],
        "secrets": {
            "db": "postgres://admin:toor@db.local:5432/app",
            "api": "api_key=sk-verysecret123456789",
        },
        "tokens": ("Bearer abcdef1234567890abcdef",),
    }
    sanitized = sanitize_context_payload(payload)
    serialized = json.dumps(sanitized, default=str)
    assert "eyJhbGciOiJIUzI1NiJ9" not in serialized
    assert "toor" not in serialized
    assert "sk-verysecret123456789" not in serialized
    assert "abcdef1234567890abcdef" not in serialized
    # Structure preserved.
    assert "evidence" in sanitized
    assert "normal text" in serialized  # non-secret summary survives


def test_nested_secret_redaction_in_list():
    payload = [
        "safe prose",
        "password=hunter2",
        ["nested ghp_abcdefghijklmnopqrstuvwxyz1234567890"],
    ]
    sanitized = sanitize_context_payload(payload)
    serialized = json.dumps(sanitized, default=str)
    assert "hunter2" not in serialized
    assert "ghp_abcdefghijklmnopqrstuvwxyz1234567890" not in serialized
    assert "safe prose" in serialized


# ===========================================================================
# Task 9-A — Sanitizer Safety Sanity Pass.
#
# These tests lock in that the expanded ``SECRET_PATTERNS`` from Task 9
# remain:
#   * performant on large benign inputs (no catastrophic backtracking)
#   * conservative on normal technical prose (no over-redaction)
#   * consistent on the redaction marker (``[REDACTED_SECRET]`` only)
#   * scoped to the P6R context sanitizer — the two domain-specific
#     sibling modules (``screen_sanitizer``, ``credentials.redaction``)
#     are documented as intentionally separate.
# ===========================================================================


import time

from sentinel.agent.evidence_ranker import SECRET_PATTERNS


# ---------------------------------------------------------------------------
# Performance sanity.
# ---------------------------------------------------------------------------


def test_sanitizer_handles_large_benign_text_quickly():
    """1MB of benign prose must sanitize in well under 2 seconds on a
    typical developer workstation. The threshold is intentionally
    generous: our measured local baseline is ~0.5s, so a 2s budget
    still flags catastrophic-backtracking regressions without
    flapping on slower CI runners."""
    big_benign = "The quick brown fox jumps over the lazy dog. " * 20_000
    assert len(big_benign) >= 900_000
    start = time.perf_counter()
    out = sanitize_context_text(big_benign)
    elapsed = time.perf_counter() - start
    assert out == big_benign, "Benign prose was unexpectedly redacted."
    assert elapsed < 2.0, f"Sanitizer took {elapsed:.2f}s on 1MB benign text."


def test_sanitizer_handles_incomplete_pem_block_without_hang():
    """A malformed ``-----BEGIN PRIVATE KEY-----`` with no closing
    tag MUST NOT trigger catastrophic backtracking in the PEM
    pattern's ``[\\s\\S]+?`` body. We feed ~100KB of repeated content
    after an unmatched BEGIN marker and assert bounded runtime."""
    pem_incomplete = "-----BEGIN PRIVATE KEY-----\n" + ("A" * 100 + "\n") * 1000
    assert len(pem_incomplete) >= 100_000
    start = time.perf_counter()
    out = sanitize_context_text(pem_incomplete)
    elapsed = time.perf_counter() - start
    # No closing marker means the regex should NOT match; input passes
    # through unchanged.
    assert out == pem_incomplete
    assert elapsed < 2.0, f"Incomplete PEM took {elapsed:.2f}s."


def test_sanitizer_handles_long_base64_like_string():
    """A 300KB base64-shaped blob that does not match any specific
    secret pattern must pass through quickly. The generic
    ``name=value`` alternation is anchored at the name keyword, so
    random base64 content without a name prefix should not trigger
    redaction."""
    long_b64 = "abcdefghijABCDEFGHIJ0123456789" * 10_000
    assert len(long_b64) >= 300_000
    start = time.perf_counter()
    out = sanitize_context_text(long_b64)
    elapsed = time.perf_counter() - start
    assert out == long_b64
    assert elapsed < 2.0, f"Long base64 took {elapsed:.2f}s."


# ---------------------------------------------------------------------------
# False-positive sanity — technical prose should survive unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,text",
    [
        ("semver-v-prefix", "Running v1.2.3 of the library."),
        ("semver-plain", "Version 3.11.2 is available."),
        ("pg-localhost", "Connect to postgres://localhost:5432/db for smoke tests."),
        ("redis-localhost", "redis://127.0.0.1:6379/0 backs the worker queue."),
        ("mysql-socket", "mysql://localhost/app via unix socket."),
        ("dotted-id", "org.example.service.UserController handles requests."),
        ("short-id", "Use id=42 as the fixture key."),
        ("short-key-equals", "row={'k': 1, 'v': 2}"),
        ("markdown-code", "Use `sk-learn` in your ML pipeline for sklearn."),
        ("git-hash", "commit a1b2c3d4e5f60718293a4b5c6d7e8f90 on main."),
        ("uuid", "Request id b23c1f94-8d7e-4a6d-9f6a-1c2b3d4e5f60 returned 200."),
        ("long-word", "pseudopseudohypoparathyroidism is a real word."),
        ("scientific-notation", "Proton mass is 1.6726219e-27 kg."),
        ("code-snippet", "def compute(x):\n    return x * 2  # simple helper"),
        ("incomplete-pem-no-end", "Reading -----BEGIN PRIVATE KEY----- with no end marker here."),
        ("bearer-word", "The bearer of bad news arrived early."),
        ("authorization-word", "Authorization matters for governance review."),
        ("api-key-word", "API key management is a classic ops concern."),
        ("token-word", "A token of appreciation for your work."),
        ("password-word", "Password should be strong, distinct, and rotated."),
        ("jwt-too-short", "eyJa.bc.de is too short to be a real JWT."),
        ("https-no-cred", "See https://example.com/docs for the guide."),
    ],
)
def test_technical_prose_is_not_redacted(label: str, text: str) -> None:
    """Normal technical prose, code snippets, semver strings, UUIDs,
    git hashes, hostless URLs, and prose mentioning trigger words
    (``bearer``, ``token``, ``password``, ``authorization``, ``api
    key``) MUST pass through the sanitizer unchanged. These are the
    most common false-positive shapes for a regex-based sanitizer and
    guarding against them prevents Task 9 from over-redacting the
    decision frame into uselessness."""
    assert sanitize_context_text(text) == text, (
        f"False positive on {label}: input was unexpectedly redacted."
    )


# ---------------------------------------------------------------------------
# Redaction marker sanity.
# ---------------------------------------------------------------------------


REDACTION_MARKER = "[REDACTED_SECRET]"


def test_redaction_marker_is_stable_and_documented():
    """Every redaction substitutes a fixed marker. Downstream
    auditors rely on the marker being present in the output (so a
    diff of the context pre/post sanitization is greppable) and on
    it being the same token every time."""
    sanitized = sanitize_context_text("password=hunter2")
    assert REDACTION_MARKER in sanitized
    # And the marker does not carry the original secret suffix.
    assert "hunter2" not in sanitized


def test_redaction_does_not_produce_empty_or_broken_output():
    """Redacting a secret-only input must leave a non-empty result
    containing the marker — not an empty string (which would be
    indistinguishable from a genuine blank context)."""
    sanitized = sanitize_context_text("sk-abc123456789012345")
    assert sanitized, "Sanitizer collapsed input to empty string."
    assert REDACTION_MARKER in sanitized


def test_redaction_marker_keeps_json_decodable_when_surrounded_by_quotes():
    """If a caller has already JSON-encoded a secret inside a string
    field and then calls the sanitizer on the encoded text, the
    result must still parse as JSON. The marker contains no
    JSON-breaking characters."""
    raw_json = '{"token": "sk-verysecret123456789012345"}'
    sanitized = sanitize_context_text(raw_json)
    assert REDACTION_MARKER in sanitized
    # The result is still valid JSON (bracketed marker is inside the quoted string).
    decoded = json.loads(sanitized)
    assert decoded["token"] != "sk-verysecret123456789012345"
    # The decoded field holds the marker substring.
    assert "[REDACTED_SECRET]" in decoded["token"]


def test_redaction_marker_is_the_only_replacement_token():
    """Lock in that the expanded patterns all substitute the same
    ``[REDACTED_SECRET]`` token. A future refactor that introduced
    a second marker (``[REDACTED]``, ``***``, etc.) would break this
    test — by design, since multi-marker outputs are harder to audit."""
    samples = [
        "sk-verysecret123456789",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_abcdefghijklmnopqrstuvwxyz1234",
        "github_pat_AAAAAA11BBBBBBCCCCCCDDDDDD_EEEEEE",
        # Google keys are exactly 39 chars: "AIza" + 35 base64-ish.
        "AIza" + "1" * 35,
        "xoxb-1234567890-abcdef-ghijkl",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhIn0.signature_here",
        "postgres://user:p4ssw0rd@db.example.com/app",
        "Bearer abcdef1234567890abcdef",
        "password=hunter2",
    ]
    for sample in samples:
        sanitized = sanitize_context_text(sample)
        assert REDACTION_MARKER in sanitized, f"Missing marker on {sample!r}"
        # No other marker shapes leaked through.
        assert "[REDACTED]" not in sanitized.replace(REDACTION_MARKER, ""), (
            f"Stray [REDACTED] marker found in {sanitized!r}"
        )


# ---------------------------------------------------------------------------
# Pattern consistency — canonical sanitizer documentation.
# ---------------------------------------------------------------------------


def test_canonical_sanitizer_is_evidence_ranker_for_p6r_context():
    """The canonical P6R context sanitizer is
    ``sentinel.agent.evidence_ranker.sanitize_context_text``. Any
    call path that renders memory, evidence, or decision frames for
    LLM consumption routes through this function.

    ``sentinel.organs.desktop.screen_sanitizer.redact_secret_like_text``
    and ``sentinel.organs.credentials.redaction.CredentialTraceRedactor``
    are INTENTIONALLY separate:

    * ``screen_sanitizer`` targets desktop-organ screenshot OCR text
      and returns a ``SanitizedDesktopContext`` with redaction
      counters and pattern labels — a richer return type tailored to
      desktop operator review. Its pattern set is narrower (it only
      needs to handle what screenshot OCR actually surfaces).
    * ``credentials.redaction`` targets credential-trace payloads
      stored in organ receipts and operates structurally on nested
      dict/list/str shapes for the credentials subsystem.

    This test documents the three-sanitizer architecture and locks
    in that ``evidence_ranker.sanitize_context_text`` is the one
    Task 9 / F-A2.1 targets. The sibling modules were intentionally
    left unchanged.
    """
    # Canonical sanitizer is importable by its documented path.
    from sentinel.agent.evidence_ranker import sanitize_context_text as canonical
    assert callable(canonical)

    # Sibling modules continue to exist with their own SECRET_PATTERNS.
    from sentinel.organs.desktop.screen_sanitizer import (
        SECRET_PATTERNS as desktop_patterns,
    )
    from sentinel.organs.credentials.redaction import (
        SECRET_PATTERNS as credentials_patterns,
    )
    assert desktop_patterns is not SECRET_PATTERNS
    assert credentials_patterns is not SECRET_PATTERNS


def test_canonical_sanitizer_has_expected_pattern_count():
    """Freeze the expanded Task 9 pattern count so an accidental
    revert to the 2-pattern pre-Task-9 state fails loudly. If a
    future task legitimately adds more patterns, bump this number."""
    # 12 patterns after Task 9 expansion. This number is a floor —
    # future additions are fine; reversion below 12 is not.
    assert len(SECRET_PATTERNS) >= 12, (
        f"SECRET_PATTERNS has shrunk below the Task 9 baseline: "
        f"{len(SECRET_PATTERNS)} < 12. Inspect evidence_ranker.py."
    )
