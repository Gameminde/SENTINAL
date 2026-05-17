"""P1-P4 property-based tests for sentinel-context-cache-runtime-closure.

Spec: ``sentinel-context-cache-runtime-closure``.
Closure backlog item: P-C-KEY-01.

P1 — Cache Key Determinism Under Canonical Permutation (max_examples=100)
P2 — No Raw Secret Leakage in Sanitizer Rejection (max_examples=200, safety)
P3 — Permutation/Sort/Dedup Invariance for List Fields (max_examples=100)
P4 — Authority-Hash Changes When Authority-Relevant Fields Change (max_examples=200, safety)

Properties P2 and P4 are **mandatory for LOCKED status** (per spec
§Property-based tests / Wave 9 instruction). They run at max_examples=200
because they encode safety invariants.

Import-cycle caveat: see test_context_cache_key_builder.py — we seed
``sentinel.agent.runtime`` first to anchor the canonical production
import order before pulling ``ContextCacheKeyBuilder``.
"""
from __future__ import annotations

# Seed the canonical production import order before pulling
# ContextCacheKeyBuilder. Do not reorder these imports.
from sentinel.agent.runtime import AgentRuntime  # noqa: F401

import string

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.agent.models import AgentContext
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.caches import (
    CacheKeySanitizerRejection,
    ContextCacheKeyBuilder,
    OrganStateEntry,
    OrganStateView,
)


_EMPTY_SNAPSHOT_HASH = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)


# ---------------------------------------------------------------------------
# Strategies — restricted to ASCII-safe non-secret-pattern strings so we
# don't accidentally trip the canonical sanitizer in P1/P3.
# ---------------------------------------------------------------------------


# Deliberately exclude: 'sk-', 'sk_', AKIA prefixes, 'Bearer ', 'authorization',
# 'token', 'secret', 'password', 'passwd', 'pwd', '://user:pass@', '-----BEGIN'.
# Use a narrow alphabet of [a-z0-9_] with mandatory letter prefix to avoid
# patterns the sanitizer redacts.
_safe_word = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_",
    min_size=1,
    max_size=12,
).filter(
    lambda s: (
        s[0] in string.ascii_lowercase
        and not s.startswith("sk")
        and not s.startswith("sk_")
        and not s.startswith("akia")
        and not s.startswith("asia")
        and "token" not in s
        and "secret" not in s
        and "password" not in s
        and "passwd" not in s
        and "pwd" not in s
        and "bearer" not in s
        and "authorization" not in s
    )
)

_safe_word_list = st.lists(_safe_word, min_size=0, max_size=5, unique=True)


def _envelope(
    *,
    allowed_actions: list[str],
    allowed_tools: list[str],
    max_actions: int,
    max_cost_usd: float,
    success_criteria: list[str],
    mission_objective: str,
) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="user-prop",
        mission_title="title",
        mission_objective=mission_objective,
        success_criteria=list(success_criteria),
        allowed_actions=list(allowed_actions),
        allowed_tools=list(allowed_tools),
        max_actions=max_actions,
        max_cost_usd=max_cost_usd,
    )


def _context(
    envelope: MissionAuthorityEnvelope,
    *,
    constraints: list[str],
    evidence_refs: list[str],
) -> AgentContext:
    return AgentContext(
        mission=envelope,
        user_input={},
        evidence_refs=list(evidence_refs),
        memory_items=[],
        constraints=list(constraints),
    )


def _derive(
    *,
    envelope: MissionAuthorityEnvelope,
    context: AgentContext,
    organ_state: OrganStateView,
    snapshot: str = _EMPTY_SNAPSHOT_HASH,
    original_allowed_actions=None,
):
    snap = (
        tuple(original_allowed_actions)
        if original_allowed_actions is not None
        else tuple(envelope.allowed_actions)
    )
    return ContextCacheKeyBuilder.derive(
        envelope=envelope,
        context=context,
        organ_state=organ_state,
        workspace_snapshot_id=snapshot,
        original_allowed_actions=snap,
    )


# ---------------------------------------------------------------------------
# P1 — Determinism (max_examples=100)
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    allowed_actions=_safe_word_list,
    allowed_tools=_safe_word_list,
    max_actions=st.integers(min_value=1, max_value=200),
    max_cost_usd=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    success_criteria=_safe_word_list,
    mission_objective=_safe_word,
    constraints=_safe_word_list,
    evidence_refs=_safe_word_list,
)
def test_p1_determinism(
    allowed_actions, allowed_tools, max_actions, max_cost_usd,
    success_criteria, mission_objective, constraints, evidence_refs,
):
    """Same inputs produce the SAME ContextCacheKey twice."""
    env_a = _envelope(
        allowed_actions=allowed_actions,
        allowed_tools=allowed_tools,
        max_actions=max_actions,
        max_cost_usd=max_cost_usd,
        success_criteria=success_criteria,
        mission_objective=mission_objective,
    )
    env_b = _envelope(
        allowed_actions=allowed_actions,
        allowed_tools=allowed_tools,
        max_actions=max_actions,
        max_cost_usd=max_cost_usd,
        success_criteria=success_criteria,
        mission_objective=mission_objective,
    )
    ctx_a = _context(env_a, constraints=constraints, evidence_refs=evidence_refs)
    ctx_b = _context(env_b, constraints=constraints, evidence_refs=evidence_refs)
    organs = OrganStateView(organs=[])
    ck_a = _derive(envelope=env_a, context=ctx_a, organ_state=organs)
    ck_b = _derive(envelope=env_b, context=ctx_b, organ_state=organs)
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.organ_state_hash == ck_b.organ_state_hash
    assert ck_a.authority_hash == ck_b.authority_hash
    assert ck_a.workspace_snapshot_id == ck_b.workspace_snapshot_id
    assert ck_a.composite_hash == ck_b.composite_hash


# ---------------------------------------------------------------------------
# P2 — No Raw Secret Leakage (max_examples=200, mandatory for LOCKED)
# ---------------------------------------------------------------------------


# A canonical set of secret patterns the sanitizer redacts. Each must
# trip CacheKeySanitizerRejection AND must NOT appear in the exception
# message.
_SECRET_PATTERNS_FOR_TEST = st.sampled_from(
    [
        "sk-AAAAAAAAAAAAAAAAAAAA",
        "sk-1234567890abcdef1234",
        "sk_live_AAAAAAAAAAAAAAAAAA",
        "sk_test_BBBBBBBBBBBBBBBBBB",
        "AKIAABCDEFGHIJKLMNOP",
        "ASIAABCDEFGHIJKLMNOP",
        "Bearer abcdefghij1234567890XYZ",
        "Authorization: Bearer foo123456789",
        "password=hunter2hunter2",
        "secret=topsecretvalueX",
    ]
)


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(secret=_SECRET_PATTERNS_FOR_TEST, where=st.sampled_from(["constraints", "allowed_actions"]))
def test_p2_no_raw_secret_leakage(secret, where):
    """Embedding a canonical secret in any string input MUST raise
    CacheKeySanitizerRejection. The exception message MUST NOT contain
    the raw secret substring."""
    if where == "constraints":
        env = _envelope(
            allowed_actions=["read"],
            allowed_tools=["read_tool"],
            max_actions=5,
            max_cost_usd=1.0,
            success_criteria=["done"],
            mission_objective="objective",
        )
        ctx = _context(env, constraints=[secret], evidence_refs=[])
        organs = OrganStateView(organs=[])
        with pytest.raises(CacheKeySanitizerRejection) as excinfo:
            _derive(envelope=env, context=ctx, organ_state=organs)
    else:  # "allowed_actions"
        env = _envelope(
            allowed_actions=[secret],
            allowed_tools=["read_tool"],
            max_actions=5,
            max_cost_usd=1.0,
            success_criteria=["done"],
            mission_objective="objective",
        )
        ctx = _context(env, constraints=[], evidence_refs=[])
        organs = OrganStateView(organs=[])
        with pytest.raises(CacheKeySanitizerRejection) as excinfo:
            _derive(envelope=env, context=ctx, organ_state=organs)
    msg = str(excinfo.value)
    assert secret not in msg, (
        f"secret substring leaked into CacheKeySanitizerRejection message: "
        f"{msg[:80]!r}"
    )


# ---------------------------------------------------------------------------
# P3 — Permutation/Sort/Dedup Invariance (max_examples=100)
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    actions=st.lists(_safe_word, min_size=1, max_size=6, unique=True),
    tools=st.lists(_safe_word, min_size=1, max_size=6, unique=True),
    constraints=st.lists(_safe_word, min_size=0, max_size=6, unique=True),
    evidence=st.lists(_safe_word, min_size=0, max_size=6, unique=True),
    permutation_seed=st.integers(min_value=0, max_value=1_000_000),
)
def test_p3_permutation_invariance(actions, tools, constraints, evidence, permutation_seed):
    """authority_hash and mission_hot_hash MUST be invariant under
    permutation and benign duplication of list-typed inputs (canonical
    form sorts + dedupes)."""
    import random
    rng = random.Random(permutation_seed)

    actions_perm = list(actions)
    rng.shuffle(actions_perm)
    actions_dup = actions_perm + [actions_perm[0]] if actions_perm else actions_perm

    tools_perm = list(tools)
    rng.shuffle(tools_perm)
    tools_dup = tools_perm + [tools_perm[0]] if tools_perm else tools_perm

    constraints_perm = list(constraints)
    rng.shuffle(constraints_perm)
    constraints_dup = constraints_perm + [constraints_perm[0]] if constraints_perm else constraints_perm

    evidence_perm = list(evidence)
    rng.shuffle(evidence_perm)
    evidence_dup = evidence_perm + [evidence_perm[0]] if evidence_perm else evidence_perm

    env_canonical = _envelope(
        allowed_actions=actions,
        allowed_tools=tools,
        max_actions=5,
        max_cost_usd=1.0,
        success_criteria=["done"],
        mission_objective="objective",
    )
    env_permuted = _envelope(
        allowed_actions=actions_dup,
        allowed_tools=tools_dup,
        max_actions=5,
        max_cost_usd=1.0,
        success_criteria=["done"],
        mission_objective="objective",
    )

    ctx_canonical = _context(env_canonical, constraints=constraints, evidence_refs=evidence)
    ctx_permuted = _context(env_permuted, constraints=constraints_dup, evidence_refs=evidence_dup)

    organs = OrganStateView(organs=[])
    snap_canonical = tuple(actions)
    snap_permuted = tuple(actions_dup)

    ck_a = _derive(
        envelope=env_canonical, context=ctx_canonical, organ_state=organs,
        original_allowed_actions=snap_canonical,
    )
    ck_b = _derive(
        envelope=env_permuted, context=ctx_permuted, organ_state=organs,
        original_allowed_actions=snap_permuted,
    )
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.authority_hash == ck_b.authority_hash
    assert ck_a.composite_hash == ck_b.composite_hash


# ---------------------------------------------------------------------------
# P4 — Authority-hash changes when authority-relevant fields change
# (max_examples=200, mandatory for LOCKED)
# ---------------------------------------------------------------------------


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    base_actions=st.lists(_safe_word, min_size=1, max_size=4, unique=True),
    extra_action=_safe_word,
    base_tools=st.lists(_safe_word, min_size=1, max_size=4, unique=True),
    base_max_actions=st.integers(min_value=1, max_value=100),
    delta_max_actions=st.integers(min_value=1, max_value=50),
)
def test_p4_authority_hash_changes_when_authority_fields_change(
    base_actions, extra_action, base_tools, base_max_actions, delta_max_actions
):
    """Adding an action to allowed_actions or bumping max_actions MUST
    flip authority_hash. This is the core "memory cannot widen authority"
    invariant: any structural authority change must be observable in
    authority_hash, and therefore in composite_hash."""
    # The extra action must not already be in base_actions for the
    # widening case to be meaningful; assume it's not.
    if extra_action in base_actions:
        return  # vacuous case — Hypothesis will retry

    base = _envelope(
        allowed_actions=base_actions,
        allowed_tools=base_tools,
        max_actions=base_max_actions,
        max_cost_usd=1.0,
        success_criteria=["done"],
        mission_objective="objective",
    )
    widened_actions = _envelope(
        allowed_actions=base_actions + [extra_action],
        allowed_tools=base_tools,
        max_actions=base_max_actions,
        max_cost_usd=1.0,
        success_criteria=["done"],
        mission_objective="objective",
    )
    bumped_max_actions = _envelope(
        allowed_actions=base_actions,
        allowed_tools=base_tools,
        max_actions=base_max_actions + delta_max_actions,
        max_cost_usd=1.0,
        success_criteria=["done"],
        mission_objective="objective",
    )

    ctx_base = _context(base, constraints=[], evidence_refs=[])
    ctx_wider = _context(widened_actions, constraints=[], evidence_refs=[])
    ctx_bumped = _context(bumped_max_actions, constraints=[], evidence_refs=[])
    organs = OrganStateView(organs=[])

    # Use the BASE original_allowed_actions snapshot in all three
    # derivations so we measure ONLY the live envelope drift, not snapshot drift.
    snap = tuple(base.allowed_actions)

    ck_base = _derive(envelope=base, context=ctx_base, organ_state=organs, original_allowed_actions=snap)
    ck_wider = _derive(envelope=widened_actions, context=ctx_wider, organ_state=organs, original_allowed_actions=snap)
    ck_bumped = _derive(envelope=bumped_max_actions, context=ctx_bumped, organ_state=organs, original_allowed_actions=snap)

    assert ck_base.authority_hash != ck_wider.authority_hash
    assert ck_base.composite_hash != ck_wider.composite_hash
    assert ck_base.authority_hash != ck_bumped.authority_hash
    assert ck_base.composite_hash != ck_bumped.composite_hash
