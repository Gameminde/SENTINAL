"""U1-U7 unit tests for sentinel-context-cache-runtime-closure / ContextCacheKeyBuilder.

Spec: ``sentinel-context-cache-runtime-closure``.
Closure backlog item: P-C-KEY-01.

These tests exercise the canonical-form contract recorded in design.md
§Hash Derivation for Each Component and the failure modes recorded in
design.md §Failure modes (1, 2, 7). They are deliberately deterministic
(no Hypothesis here — that's covered by P1-P4 in
test_context_cache_runtime_closure_property.py).

Import-cycle caveat (recorded in the Task 3.3 implementation log):
``sentinel.perf.caches.context_cache_key`` triggers a circular import
when it is the first entry point because it imports
``sentinel.agent.evidence_ranker``. We import ``sentinel.agent.runtime``
first to seed ``sys.modules``; this is the canonical production import
order (every production caller goes through ``AgentRuntime``).
"""
from __future__ import annotations

# Seed the canonical production import order before pulling
# ContextCacheKeyBuilder. Do not reorder these imports.
from sentinel.agent.runtime import AgentRuntime  # noqa: F401

import pytest
from datetime import UTC, datetime, timedelta

from sentinel.agent.models import AgentContext
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.caches import (
    CacheKeySanitizerRejection,
    ContextCacheKey,
    ContextCacheKeyBuilder,
    MissingCacheKeyComponent,
    OrganStateEntry,
    OrganStateView,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_envelope(
    *,
    allowed_actions: tuple[str, ...] = ("read",),
    allowed_tools: tuple[str, ...] = ("file_read",),
    max_actions: int = 5,
    max_cost_usd: float = 1.0,
    success_criteria: tuple[str, ...] = ("done",),
    user_id: str = "user-A",
    mission_title: str = "title",
    mission_objective: str = "objective",
) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id=user_id,
        mission_title=mission_title,
        mission_objective=mission_objective,
        success_criteria=list(success_criteria),
        allowed_actions=list(allowed_actions),
        allowed_tools=list(allowed_tools),
        max_actions=max_actions,
        max_cost_usd=max_cost_usd,
    )


def _make_context(
    envelope: MissionAuthorityEnvelope,
    *,
    constraints: tuple[str, ...] = ("c1", "c2"),
    evidence_refs: tuple[str, ...] = ("e1",),
) -> AgentContext:
    return AgentContext(
        mission=envelope,
        user_input={},
        evidence_refs=list(evidence_refs),
        memory_items=[],
        constraints=list(constraints),
    )


def _make_organ_state(
    organs: tuple[OrganStateEntry, ...] = ()
) -> OrganStateView:
    return OrganStateView(organs=list(organs))


_EMPTY_SNAPSHOT_HASH = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)


def _derive(
    *,
    envelope: MissionAuthorityEnvelope | None = None,
    context: AgentContext | None = None,
    organ_state: OrganStateView | None = None,
    workspace_snapshot_id: str = _EMPTY_SNAPSHOT_HASH,
    original_allowed_actions: tuple[str, ...] | list[str] | None = None,
) -> ContextCacheKey:
    env = envelope if envelope is not None else _make_envelope()
    ctx = context if context is not None else _make_context(env)
    orgs = organ_state if organ_state is not None else _make_organ_state()
    snap_actions = (
        tuple(original_allowed_actions)
        if original_allowed_actions is not None
        else tuple(env.allowed_actions)
    )
    return ContextCacheKeyBuilder.derive(
        envelope=env,
        context=ctx,
        organ_state=orgs,
        workspace_snapshot_id=workspace_snapshot_id,
        original_allowed_actions=snap_actions,
    )


# ---------------------------------------------------------------------------
# U1 — Same inputs produce identical ContextCacheKey
# ---------------------------------------------------------------------------


def test_u1_same_inputs_produce_identical_cache_key() -> None:
    """Determinism: two derivations from identical inputs MUST produce
    identical ContextCacheKey across all five fields."""
    env = _make_envelope()
    ck1 = _derive(envelope=env)
    ck2 = _derive(envelope=env)
    assert ck1.mission_hot_hash == ck2.mission_hot_hash
    assert ck1.workspace_snapshot_id == ck2.workspace_snapshot_id
    assert ck1.organ_state_hash == ck2.organ_state_hash
    assert ck1.authority_hash == ck2.authority_hash
    assert ck1.composite_hash == ck2.composite_hash


# ---------------------------------------------------------------------------
# U2 — Changing mission-hot fields changes mission_hot_hash AND composite_hash
# ---------------------------------------------------------------------------


def test_u2_mission_hot_change_propagates_only_to_mission_hot_and_composite() -> None:
    env_a = _make_envelope(mission_objective="obj-A")
    env_b = _make_envelope(mission_objective="obj-B")
    ck_a = _derive(envelope=env_a)
    ck_b = _derive(envelope=env_b)
    assert ck_a.mission_hot_hash != ck_b.mission_hot_hash
    assert ck_a.composite_hash != ck_b.composite_hash
    # workspace_snapshot_id, organ_state_hash, authority_hash MUST be
    # untouched — mission_objective is mission-hot, not authority.
    assert ck_a.workspace_snapshot_id == ck_b.workspace_snapshot_id
    assert ck_a.organ_state_hash == ck_b.organ_state_hash
    assert ck_a.authority_hash == ck_b.authority_hash


def test_u2b_constraints_change_propagates_only_to_mission_hot_and_composite() -> None:
    env = _make_envelope()
    ctx_a = _make_context(env, constraints=("only-A",))
    ctx_b = _make_context(env, constraints=("only-B",))
    ck_a = _derive(envelope=env, context=ctx_a)
    ck_b = _derive(envelope=env, context=ctx_b)
    assert ck_a.mission_hot_hash != ck_b.mission_hot_hash
    assert ck_a.composite_hash != ck_b.composite_hash
    assert ck_a.workspace_snapshot_id == ck_b.workspace_snapshot_id
    assert ck_a.organ_state_hash == ck_b.organ_state_hash
    assert ck_a.authority_hash == ck_b.authority_hash


# ---------------------------------------------------------------------------
# U3 — Changing workspace_snapshot_id changes ONLY workspace_snapshot_id and composite
# ---------------------------------------------------------------------------


def test_u3_workspace_snapshot_change_propagates_only_to_workspace_and_composite() -> None:
    other_snapshot = "f" * 64  # different 64-char lowercase hex
    ck_a = _derive(workspace_snapshot_id=_EMPTY_SNAPSHOT_HASH)
    ck_b = _derive(workspace_snapshot_id=other_snapshot)
    assert ck_a.workspace_snapshot_id != ck_b.workspace_snapshot_id
    assert ck_a.composite_hash != ck_b.composite_hash
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.organ_state_hash == ck_b.organ_state_hash
    assert ck_a.authority_hash == ck_b.authority_hash


# ---------------------------------------------------------------------------
# U4 — Changing organ_state changes organ_state_hash AND composite_hash
# ---------------------------------------------------------------------------


def test_u4_organ_state_change_propagates_only_to_organ_state_and_composite() -> None:
    organs_a = _make_organ_state()  # empty
    organs_b = _make_organ_state(
        organs=(
            OrganStateEntry(
                organ_id="organ_A",
                execution_allowed=True,
                advertised_capabilities=["cap_x"],
                kill_switch_triggered=False,
            ),
        )
    )
    ck_a = _derive(organ_state=organs_a)
    ck_b = _derive(organ_state=organs_b)
    assert ck_a.organ_state_hash != ck_b.organ_state_hash
    assert ck_a.composite_hash != ck_b.composite_hash
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.workspace_snapshot_id == ck_b.workspace_snapshot_id
    assert ck_a.authority_hash == ck_b.authority_hash


def test_u4b_organ_kill_switch_toggle_changes_organ_state_hash() -> None:
    organs_off = _make_organ_state(
        organs=(
            OrganStateEntry(
                organ_id="o1",
                execution_allowed=True,
                advertised_capabilities=["cap"],
                kill_switch_triggered=False,
            ),
        )
    )
    organs_on = _make_organ_state(
        organs=(
            OrganStateEntry(
                organ_id="o1",
                execution_allowed=True,
                advertised_capabilities=["cap"],
                kill_switch_triggered=True,
            ),
        )
    )
    ck_off = _derive(organ_state=organs_off)
    ck_on = _derive(organ_state=organs_on)
    assert ck_off.organ_state_hash != ck_on.organ_state_hash
    assert ck_off.composite_hash != ck_on.composite_hash


# ---------------------------------------------------------------------------
# U5 — Changing allowed/original authority actions changes authority_hash AND composite
# ---------------------------------------------------------------------------


def test_u5_envelope_allowed_actions_change_propagates_to_authority_and_composite() -> None:
    env_narrow = _make_envelope(allowed_actions=("read",))
    env_wide = _make_envelope(allowed_actions=("read", "write"))
    ck_narrow = _derive(envelope=env_narrow)
    ck_wide = _derive(envelope=env_wide)
    assert ck_narrow.authority_hash != ck_wide.authority_hash
    assert ck_narrow.composite_hash != ck_wide.composite_hash
    # Mission-hot/organ_state/workspace are unchanged.
    assert ck_narrow.mission_hot_hash == ck_wide.mission_hot_hash
    assert ck_narrow.organ_state_hash == ck_wide.organ_state_hash
    assert ck_narrow.workspace_snapshot_id == ck_wide.workspace_snapshot_id


def test_u5b_original_allowed_actions_snapshot_change_propagates_to_authority() -> None:
    env = _make_envelope(allowed_actions=("read",))
    snap_short = ("read",)
    snap_long = ("read", "exec")
    ck_short = _derive(envelope=env, original_allowed_actions=snap_short)
    ck_long = _derive(envelope=env, original_allowed_actions=snap_long)
    assert ck_short.authority_hash != ck_long.authority_hash
    assert ck_short.composite_hash != ck_long.composite_hash


def test_u5c_max_cost_usd_change_propagates_to_authority() -> None:
    env_a = _make_envelope(max_cost_usd=1.0)
    env_b = _make_envelope(max_cost_usd=2.5)
    ck_a = _derive(envelope=env_a)
    ck_b = _derive(envelope=env_b)
    assert ck_a.authority_hash != ck_b.authority_hash


# ---------------------------------------------------------------------------
# U6 — envelope.id / user_id / volatile timestamps do NOT affect authority_hash
# ---------------------------------------------------------------------------


def test_u6_envelope_id_does_not_affect_any_hash() -> None:
    """envelope.id is auto-generated and is not part of any canonical
    form. Two envelopes that differ ONLY in id MUST produce identical
    cache keys across all four component hashes."""
    env_a = _make_envelope()
    env_b = _make_envelope()
    # MissionAuthorityEnvelope auto-generates a fresh id per construction,
    # so env_a.id != env_b.id by default.
    assert env_a.id != env_b.id
    ck_a = _derive(envelope=env_a)
    ck_b = _derive(envelope=env_b)
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.authority_hash == ck_b.authority_hash
    assert ck_a.organ_state_hash == ck_b.organ_state_hash
    assert ck_a.composite_hash == ck_b.composite_hash


def test_u6b_user_id_does_not_affect_any_hash() -> None:
    env_a = _make_envelope(user_id="user-X")
    env_b = _make_envelope(user_id="user-Y")
    ck_a = _derive(envelope=env_a)
    ck_b = _derive(envelope=env_b)
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.authority_hash == ck_b.authority_hash
    assert ck_a.composite_hash == ck_b.composite_hash


def test_u6c_volatile_timestamps_do_not_affect_authority_or_mission_hot() -> None:
    """envelope.created_at is auto-generated; it is in _VOLATILE_FIELDS and
    must not influence any hash."""
    env_a = _make_envelope()
    env_b = _make_envelope()
    # Different created_at by construction (datetime.now(UTC) drift).
    # Set them explicitly to maximally different values to be sure.
    env_a = env_a.model_copy(
        update={"created_at": datetime(2020, 1, 1, tzinfo=UTC)}
    )
    env_b = env_b.model_copy(
        update={"created_at": datetime(2030, 1, 1, tzinfo=UTC)}
    )
    ck_a = _derive(envelope=env_a)
    ck_b = _derive(envelope=env_b)
    assert ck_a.authority_hash == ck_b.authority_hash
    assert ck_a.mission_hot_hash == ck_b.mission_hot_hash
    assert ck_a.composite_hash == ck_b.composite_hash


def test_u6d_expires_at_revoked_at_DO_affect_authority_hash() -> None:
    """expires_at and revoked_at are explicitly authority-relevant per
    design §Hash Derivation §authority — they MUST flip authority_hash
    even though they are timestamps."""
    env_clean = _make_envelope()
    expiry = env_clean.created_at + timedelta(hours=1)
    env_with_expiry = env_clean.model_copy(update={"expires_at": expiry})
    env_revoked = env_clean.model_copy(update={"revoked_at": expiry})
    ck_clean = _derive(envelope=env_clean)
    ck_expiry = _derive(envelope=env_with_expiry)
    ck_revoked = _derive(envelope=env_revoked)
    assert ck_clean.authority_hash != ck_expiry.authority_hash
    assert ck_clean.authority_hash != ck_revoked.authority_hash
    assert ck_expiry.authority_hash != ck_revoked.authority_hash


# ---------------------------------------------------------------------------
# U7 — Missing components & sanitizer rejection
# ---------------------------------------------------------------------------


def test_u7_missing_envelope_raises_missing_component() -> None:
    env = _make_envelope()
    ctx = _make_context(env)
    orgs = _make_organ_state()
    with pytest.raises(MissingCacheKeyComponent):
        ContextCacheKeyBuilder.derive(
            envelope=None,
            context=ctx,
            organ_state=orgs,
            workspace_snapshot_id=_EMPTY_SNAPSHOT_HASH,
            original_allowed_actions=tuple(env.allowed_actions),
        )


def test_u7_missing_context_raises_missing_component() -> None:
    env = _make_envelope()
    orgs = _make_organ_state()
    with pytest.raises(MissingCacheKeyComponent):
        ContextCacheKeyBuilder.derive(
            envelope=env,
            context=None,
            organ_state=orgs,
            workspace_snapshot_id=_EMPTY_SNAPSHOT_HASH,
            original_allowed_actions=tuple(env.allowed_actions),
        )


def test_u7_missing_organ_state_raises_missing_component() -> None:
    env = _make_envelope()
    ctx = _make_context(env)
    with pytest.raises(MissingCacheKeyComponent):
        ContextCacheKeyBuilder.derive(
            envelope=env,
            context=ctx,
            organ_state=None,
            workspace_snapshot_id=_EMPTY_SNAPSHOT_HASH,
            original_allowed_actions=tuple(env.allowed_actions),
        )


def test_u7_empty_workspace_snapshot_raises_missing_component() -> None:
    with pytest.raises(MissingCacheKeyComponent):
        _derive(workspace_snapshot_id="")


def test_u7_none_workspace_snapshot_raises_missing_component() -> None:
    with pytest.raises(MissingCacheKeyComponent):
        _derive(workspace_snapshot_id=None)  # type: ignore[arg-type]


def test_u7_missing_original_allowed_actions_raises_missing_component() -> None:
    env = _make_envelope()
    ctx = _make_context(env)
    orgs = _make_organ_state()
    with pytest.raises(MissingCacheKeyComponent):
        ContextCacheKeyBuilder.derive(
            envelope=env,
            context=ctx,
            organ_state=orgs,
            workspace_snapshot_id=_EMPTY_SNAPSHOT_HASH,
            original_allowed_actions=None,  # type: ignore[arg-type]
        )


def test_u7_missing_original_allowed_actions_in_authority_hash_raises() -> None:
    env = _make_envelope()
    with pytest.raises(MissingCacheKeyComponent):
        ContextCacheKeyBuilder.authority_hash(
            env,
            original_allowed_actions=None,  # type: ignore[arg-type]
        )


def test_u7_sanitizer_rejection_on_secret_pattern_in_constraints() -> None:
    """A canonical secret pattern (`sk-` token) embedded in a string
    field MUST cause CacheKeySanitizerRejection. The exception message
    MUST NOT echo the rejected substring."""
    env = _make_envelope()
    poisoned_ctx = _make_context(
        env,
        constraints=("sk-AAAAAAAAAAAAAAAAAAAAAAAA",),
    )
    with pytest.raises(CacheKeySanitizerRejection) as excinfo:
        _derive(envelope=env, context=poisoned_ctx)
    msg = str(excinfo.value)
    assert "sk-AAAAAAAAAAAAAAAAAAAAAAAA" not in msg
    # The field name is OK to surface; the raw value is not.


def test_u7_sanitizer_rejection_in_authority_allowed_actions() -> None:
    """A secret pattern in envelope.allowed_actions must trip the
    sanitizer when authority_hash runs."""
    env = _make_envelope(
        allowed_actions=("read", "Bearer abcdefghij1234567890")
    )
    with pytest.raises(CacheKeySanitizerRejection) as excinfo:
        _derive(envelope=env)
    msg = str(excinfo.value)
    assert "Bearer abcdefghij1234567890" not in msg


def test_u7_no_partial_key_on_failure() -> None:
    """When derive() raises, the caller never receives a partial
    ContextCacheKey; the exception path is the only outcome."""
    env = _make_envelope()
    poisoned_ctx = _make_context(
        env,
        constraints=("sk-BBBBBBBBBBBBBBBBBBBBBBBB",),
    )
    try:
        _derive(envelope=env, context=poisoned_ctx)
    except CacheKeySanitizerRejection:
        pass
    else:  # pragma: no cover
        pytest.fail("expected CacheKeySanitizerRejection")


def test_u7_context_cache_key_is_frozen() -> None:
    """ContextCacheKey is Pydantic frozen — mutation raises ValidationError."""
    ck = _derive()
    with pytest.raises(Exception):  # pydantic ValidationError
        ck.mission_hot_hash = "0" * 64  # type: ignore[misc]


def test_u7_context_cache_key_extra_forbid() -> None:
    """extra='forbid' rejects unknown fields at construction."""
    ck = _derive()
    with pytest.raises(Exception):  # pydantic ValidationError
        ContextCacheKey(
            mission_hot_hash=ck.mission_hot_hash,
            workspace_snapshot_id=ck.workspace_snapshot_id,
            organ_state_hash=ck.organ_state_hash,
            authority_hash=ck.authority_hash,
            composite_hash=ck.composite_hash,
            sneaky_extra="x",  # type: ignore[call-arg]
        )


def test_u7_context_cache_key_fields_are_64_hex_lowercase() -> None:
    ck = _derive()
    for field in (
        ck.mission_hot_hash,
        ck.workspace_snapshot_id,
        ck.organ_state_hash,
        ck.authority_hash,
        ck.composite_hash,
    ):
        assert len(field) == 64
        assert all(c in "0123456789abcdef" for c in field)
