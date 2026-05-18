"""Tests for Task 8 / F-A2.7 — DecisionFrameVerifier mandatory params.

CP-8.1 (No Silent Skip):
    ∀ construction of DecisionFrameVerifier:
        required_evidence_refs ≠ None ∧ known_receipt_ids ≠ None

CP-8.2 (Ref Resolution):
    ∀ receipt_ref R in LLMDecisionFrame:
        R ∈ known_receipt_ids ∨ verify() fails

These tests lock in that construction without the two mandatory
parameters raises ``TypeError``, that the receipt-ref resolution
check can no longer be silently skipped, and that every call site
across the repository either passes real collections or explicit
empty collections with a documented comment.
"""

from __future__ import annotations

import ast
import pathlib
import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sentinel.agent.decision_frame import (
    DecisionFrameVerifier,
    LLMDecisionFrame,
)
from sentinel.agent.evidence_ranker import EvidenceCard
from sentinel.agent.prompt_budget import PromptBudgetAllocator
from sentinel.agent import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    ModelCostProfile,
    QualityExpectationContract,
    UserModelContract,
)


# ---------------------------------------------------------------------------
# Fixture helpers — build a minimal LLMDecisionFrame with N receipt refs.
# ---------------------------------------------------------------------------


def _user_model() -> UserModelContract:
    model = "deepseek-v4-pro"
    return UserModelContract(
        selected_provider_id="deepseek",
        selected_backend_id="deepseek_chat_completions",
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
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=320,
            max_evidence_tokens=1_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="broad_exploration",
            minimum_evidence_refs=1,
            retry_budget=1,
        ),
    )


def _build_frame_with_receipts(receipt_ids: list[str]) -> LLMDecisionFrame:
    """Build an LLMDecisionFrame carrying one evidence card per receipt id."""
    evidence_cards = [
        EvidenceCard(
            receipt_id=rid,
            source_type="browser",
            summary=f"Evidence summary for {rid}.",
            evidence_refs=[f"ev_{rid}"],
            relevance_score=1.0,
            token_count=10,
            critical=False,
        )
        for rid in receipt_ids
    ]
    allocator = PromptBudgetAllocator(_user_model())
    return LLMDecisionFrame.build(
        mission_id="m",
        mission_card={"objective": "verify ref resolution"},
        authority_card={"allowed_actions": ["browser_read"]},
        progress_card={"step": 1},
        evidence=evidence_cards,
        selected_tool_surface=["browser_read"],
        current_blockers=[],
        next_decision_options=[],
        required_output_schema={"decision": "string"},
        budget_allocator=allocator,
    )


# ---------------------------------------------------------------------------
# CP-8.1 — No silent skip at construction.
# ---------------------------------------------------------------------------


def test_construction_without_params_raises_type_error():
    """Pre-Task-8 doctrine allowed ``DecisionFrameVerifier()``. Post-
    Task-8 that construction MUST raise TypeError because both
    parameters are required keyword-only with no default."""
    with pytest.raises(TypeError):
        DecisionFrameVerifier()  # type: ignore[call-arg]


def test_construction_without_required_evidence_refs_raises_type_error():
    with pytest.raises(TypeError):
        DecisionFrameVerifier(known_receipt_ids=set())  # type: ignore[call-arg]


def test_construction_without_known_receipt_ids_raises_type_error():
    with pytest.raises(TypeError):
        DecisionFrameVerifier(required_evidence_refs=[])  # type: ignore[call-arg]


def test_construction_with_positional_args_raises_type_error():
    """The parameters are keyword-only, so positional passing is also
    rejected. This prevents callers from sneaking in
    ``DecisionFrameVerifier(None, None)`` through positional args."""
    with pytest.raises(TypeError):
        DecisionFrameVerifier([], set())  # type: ignore[misc]


def test_explicit_none_for_required_evidence_refs_raises_type_error():
    """``**kwargs`` expansion of a config dict that carries ``None``
    for the mandatory params must be rejected, not silently treated as
    empty."""
    with pytest.raises(TypeError):
        DecisionFrameVerifier(
            required_evidence_refs=None,  # type: ignore[arg-type]
            known_receipt_ids=set(),
        )


def test_explicit_none_for_known_receipt_ids_raises_type_error():
    with pytest.raises(TypeError):
        DecisionFrameVerifier(
            required_evidence_refs=[],
            known_receipt_ids=None,  # type: ignore[arg-type]
        )


def test_construction_with_explicit_empty_collections_succeeds():
    """Empty collections encode zero-trust; the Verifier is usable."""
    verifier = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=set(),
    )
    assert verifier.required_evidence_refs == []
    assert verifier.known_receipt_ids == set()


def test_known_receipt_ids_accepts_list_and_set():
    """Both list and set inputs are coerced to an internal set."""
    v_list = DecisionFrameVerifier(required_evidence_refs=[], known_receipt_ids=["r_a", "r_b"])
    v_set = DecisionFrameVerifier(required_evidence_refs=[], known_receipt_ids={"r_a", "r_b"})
    assert v_list.known_receipt_ids == v_set.known_receipt_ids == {"r_a", "r_b"}


# ---------------------------------------------------------------------------
# CP-8.2 — Ref resolution property.
# ---------------------------------------------------------------------------


_RECEIPT_ID = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_",
    min_size=3,
    max_size=16,
).filter(lambda s: s.startswith(tuple(string.ascii_lowercase)))


@given(receipt_ids=st.lists(_RECEIPT_ID, min_size=1, max_size=5, unique=True))
@settings(deadline=None, max_examples=25)
def test_receipt_ref_resolution_property_passes_with_correct_ids(receipt_ids: list[str]):
    """CP-8.2 (positive): passing the exact set of frame receipt ids
    causes every unresolvable-ref failure to be absent."""
    frame = _build_frame_with_receipts(receipt_ids)
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=set(frame.receipt_refs),
    ).verify(frame)
    unresolvable = [f for f in result.failures if f.startswith("unresolvable receipt ref:")]
    assert unresolvable == []


@given(receipt_ids=st.lists(_RECEIPT_ID, min_size=1, max_size=5, unique=True))
@settings(deadline=None, max_examples=25)
def test_receipt_ref_resolution_property_fails_on_missing_id(receipt_ids: list[str]):
    """CP-8.2 (negative): dropping any one ref from ``known_receipt_ids``
    causes that specific unresolvable-ref failure to be reported."""
    frame = _build_frame_with_receipts(receipt_ids)
    # Drop the first receipt id from the known graph; the frame still
    # references it, so verification must flag it.
    dropped = frame.receipt_refs[0]
    known_minus_one = set(frame.receipt_refs) - {dropped}
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=known_minus_one,
    ).verify(frame)
    assert f"unresolvable receipt ref: {dropped}" in result.failures


@given(receipt_ids=st.lists(_RECEIPT_ID, min_size=1, max_size=5, unique=True))
@settings(deadline=None, max_examples=25)
def test_receipt_ref_resolution_property_zero_trust_fails_all(receipt_ids: list[str]):
    """Zero-trust (``known_receipt_ids=set()``) must flag every receipt
    ref in the frame. This locks in that an empty collection is NOT a
    silent-skip — the pre-Task-8 signature had a None branch that
    skipped this loop entirely, which is what F-A2.7 banned."""
    frame = _build_frame_with_receipts(receipt_ids)
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=set(),
    ).verify(frame)
    unresolvable_refs = {
        f.removeprefix("unresolvable receipt ref: ")
        for f in result.failures
        if f.startswith("unresolvable receipt ref:")
    }
    assert unresolvable_refs == set(frame.receipt_refs)


def test_missing_known_receipt_id_fails_verification():
    """Explicit, non-property example to pair with the property tests."""
    frame = _build_frame_with_receipts(["r_alpha", "r_beta"])
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids={"r_alpha"},  # r_beta intentionally absent
    ).verify(frame)
    assert "unresolvable receipt ref: r_beta" in result.failures
    assert not any(f.endswith("r_alpha") for f in result.failures if "unresolvable" in f)


def test_correct_known_receipt_id_passes_receipt_resolution():
    frame = _build_frame_with_receipts(["r_alpha", "r_beta"])
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids={"r_alpha", "r_beta"},
    ).verify(frame)
    unresolvable = [f for f in result.failures if "unresolvable receipt ref" in f]
    assert unresolvable == []


# ---------------------------------------------------------------------------
# Acceptance — all call sites pass the required params.
# ---------------------------------------------------------------------------


def _iter_sentinel_python_files() -> list[pathlib.Path]:
    """All .py files under the sentinel package and its test suite."""
    core_root = pathlib.Path(__file__).resolve().parent.parent
    candidates: list[pathlib.Path] = []
    candidates.extend((core_root / "sentinel").rglob("*.py"))
    candidates.extend((core_root / "tests").rglob("*.py"))
    return candidates


def test_all_call_sites_pass_required_params():
    """AST-walk every DecisionFrameVerifier(...) construction in the
    repository and assert it passes both ``required_evidence_refs`` and
    ``known_receipt_ids`` as keywords. This prevents regressions where
    a future caller re-adds the silent-skip signature.

    This file is excluded from the walk because it contains
    intentionally-invalid constructions inside ``pytest.raises(TypeError)``
    blocks to lock in the CP-8.1 No-Silent-Skip contract.
    """
    this_file = pathlib.Path(__file__).resolve()
    offenders: list[tuple[str, int, str]] = []
    for path in _iter_sentinel_python_files():
        if path.resolve() == this_file:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — defensive
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Match both ``DecisionFrameVerifier(...)`` and
            # ``module.DecisionFrameVerifier(...)`` attribute access.
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name != "DecisionFrameVerifier":
                continue
            kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
            has_splat = any(kw.arg is None for kw in node.keywords)
            if has_splat:
                # ``**some_dict`` — we cannot statically prove both
                # keys are present. Flag for manual review.
                offenders.append((str(path), node.lineno, "uses ** splat — manual review required"))
                continue
            missing = {"required_evidence_refs", "known_receipt_ids"} - kwargs
            if missing:
                offenders.append((
                    str(path),
                    node.lineno,
                    f"missing keyword(s): {sorted(missing)}",
                ))

    assert offenders == [], (
        "DecisionFrameVerifier call sites missing mandatory kwargs: "
        + "\n".join(f"  {p}:{ln} — {msg}" for p, ln, msg in offenders)
    )
