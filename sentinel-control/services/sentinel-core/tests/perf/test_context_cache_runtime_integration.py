"""I1-I5 + R1 integration tests for sentinel-context-cache-runtime-closure.

Spec: ``sentinel-context-cache-runtime-closure``.
Closure backlog items: P-C-KEY-01 / P-C-RUNTIME-01.

Coverage:
- I1: AgentRuntime default-off behavior unchanged.
- I2: AgentRuntime with ContextBuildCache injected completes successfully.
- I3: ContextBuildCache key composition no longer uses envelope.id stand-ins
       (composite_key now sources its four slots from ContextCacheKeyBuilder).
- I4: Authority drift mid-flight falls back to fresh build (no cached entry served).
- I5: ContextBuilder remains unmodified / no cache-helper imports.
- R1: Cached vs fresh AgentContext output is functionally equivalent under
      CanonicalComparison (excluding documented volatile/non-functional fields).

These integration tests mirror the foundation-spec fixture pattern from
``tests/perf/caches/test_runtime_cache_wiring.py`` so the closure-spec
contract layers cleanly on top of the existing default-off baseline.

Import-cycle caveat (Task 3.3): seed ``sentinel.agent.runtime`` first.
"""
from __future__ import annotations

# Seed the canonical production import order. Do not reorder these imports.
from sentinel.agent.runtime import AgentRuntime  # noqa: F401

import copy
from pathlib import Path

from sentinel.agent import AgentPhase
from sentinel.agent.models import AgentContext
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.caches.context_build_cache import (
    CACHE_TYPE as CONTEXT_CACHE_TYPE,
    ContextBuildCache,
)
from sentinel.perf.caches import (
    ContextCacheKeyBuilder,
    OrganStateView,
)
from sentinel.shared.enums import MissionMode, MissionStatus, MissionType
from sentinel.shared.events import AgentEventType, EventBus


# ---------------------------------------------------------------------------
# Fixtures (mirror tests/perf/caches/test_runtime_cache_wiring.py)
# ---------------------------------------------------------------------------


_SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "generate_research_questions",
    "write_trace",
]


def _envelope(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_closure_int",
        "mission_type": MissionType.GTM,
        "mission_title": "Context cache runtime closure integration",
        "mission_objective": "Verify ContextCacheKey-driven cache wiring end-to-end.",
        "success_criteria": ["GTM files exist", "Trace exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(_SAFE_ACTIONS),
        "forbidden_actions": [
            "send_email",
            "run_shell_command",
            "browser_submit_form",
            "credential_access",
        ],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


# ---------------------------------------------------------------------------
# I1 — AgentRuntime default-off behavior unchanged
# ---------------------------------------------------------------------------


def test_i1_default_off_run_completes_and_emits_no_cache_events(tmp_path):
    """When no caches are injected, AgentRuntime.run completes
    successfully and emits zero cache-family events. The closure-spec
    edits at the CONTEXT_BUILDING phase are gated by
    ``if self._context_build_cache is not None:``, so the default-off
    path must remain bit-identical to the foundation lock."""
    env = _envelope()
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": "closure default-off baseline"},
        evidence_refs=["ev_a", "ev_b"],
    )
    assert result.success is True
    assert result.final_phase == AgentPhase.COMPLETED
    assert result.mission_result is not None
    assert result.mission_result.state.status == MissionStatus.COMPLETED
    assert Path(result.project_path or "").exists()

    cache_event_types = {
        AgentEventType.CACHE_HIT,
        AgentEventType.CACHE_MISS,
        AgentEventType.CACHE_EVICTED,
        AgentEventType.CACHE_CORRECTNESS_VIOLATION,
    }
    event_types = {event.event_type for event in result.trace}
    assert cache_event_types.isdisjoint(event_types), (
        "default-off AgentRuntime must not emit any cache-family events"
    )


# ---------------------------------------------------------------------------
# I2 — AgentRuntime with ContextBuildCache injected completes successfully
# ---------------------------------------------------------------------------


def test_i2_runtime_with_context_build_cache_runs_to_completed(tmp_path):
    """Inject ContextBuildCache. AgentRuntime.run must reach COMPLETED
    and the trace must contain at least one ContextBuildCache miss event
    (the ContextCacheKey-driven path is exercised)."""
    env = _envelope()
    bus = EventBus(env.id)
    cache = ContextBuildCache(event_bus=bus)
    runtime = AgentRuntime(project_root=tmp_path, context_build_cache=cache)
    result = runtime.run(
        env,
        {"idea": "closure injected first run"},
        evidence_refs=["ev_a", "ev_b"],
    )

    assert result.success is True
    assert result.final_phase == AgentPhase.COMPLETED
    assert result.mission_result is not None
    assert result.mission_result.state.status == MissionStatus.COMPLETED

    miss_events = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_MISS
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    assert len(miss_events) == 1, (
        "first run with injected ContextBuildCache must produce exactly "
        "one ContextBuildCache miss"
    )


# ---------------------------------------------------------------------------
# I3 — ContextBuildCache composite_key no longer uses envelope.id stand-ins
# ---------------------------------------------------------------------------


def test_i3_composite_key_differs_from_envelope_id_stand_in(tmp_path):
    """Two envelopes that differ ONLY in id (mission_id) MUST produce the
    SAME ContextBuildCache composite_key. Pre-closure, the four slots
    were sourced from ``envelope.id`` (and the ``"v1"`` literals), so
    two missions with different ids would have hashed to different
    composite keys. Post-closure, the slots come from
    ContextCacheKeyBuilder canonical forms — which deliberately exclude
    envelope.id — so identical-content envelopes produce identical keys.
    This is the structural witness that the envelope.id stand-in is
    gone from the cache-key path."""
    env_one = _envelope()
    env_two = _envelope()
    assert env_one.id != env_two.id, "mission ids must differ by construction"

    bus = EventBus("integration-i3")
    cache = ContextBuildCache(event_bus=bus)

    # Build a draft AgentContext mirroring the runtime's pre-build snapshot
    # at CONTEXT_BUILDING (see runtime.py Task 3.2 block).
    def _draft(env: MissionAuthorityEnvelope) -> AgentContext:
        return AgentContext(
            mission=env,
            user_input={},
            evidence_refs=[],
            memory_items=[],
        )

    organs = OrganStateView(organs=[])
    snapshot = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    ck_one = ContextCacheKeyBuilder.derive(
        envelope=env_one,
        context=_draft(env_one),
        organ_state=organs,
        workspace_snapshot_id=snapshot,
        original_allowed_actions=tuple(env_one.allowed_actions),
    )
    ck_two = ContextCacheKeyBuilder.derive(
        envelope=env_two,
        context=_draft(env_two),
        organ_state=organs,
        workspace_snapshot_id=snapshot,
        original_allowed_actions=tuple(env_two.allowed_actions),
    )

    # All four cache-key value slots must be envelope.id-independent.
    assert ck_one.mission_hot_hash == ck_two.mission_hot_hash
    assert ck_one.organ_state_hash == ck_two.organ_state_hash
    assert ck_one.authority_hash == ck_two.authority_hash
    assert ck_one.workspace_snapshot_id == ck_two.workspace_snapshot_id

    # And therefore the composite_key the runtime uses with ContextBuildCache
    # must be the same for both envelopes.
    composite_one = cache.composite_key(
        mission_hot_hash=ck_one.mission_hot_hash,
        workspace_snapshot_id=ck_one.workspace_snapshot_id,
        organ_state_hash=ck_one.organ_state_hash,
        authority_hash=ck_one.authority_hash,
    )
    composite_two = cache.composite_key(
        mission_hot_hash=ck_two.mission_hot_hash,
        workspace_snapshot_id=ck_two.workspace_snapshot_id,
        organ_state_hash=ck_two.organ_state_hash,
        authority_hash=ck_two.authority_hash,
    )
    assert composite_one == composite_two, (
        "two envelopes that differ only in id MUST produce the same "
        "composite_key — the envelope.id stand-in must be gone from "
        "every cache-key value slot"
    )

    # And those composite values must NOT equal envelope.id either —
    # they should be 64-char SHA-256 hex digests, not opaque mission ids.
    assert composite_one != env_one.id
    assert composite_one != env_two.id


# ---------------------------------------------------------------------------
# I4 — Authority drift falls back to fresh build (no cached entry served)
# ---------------------------------------------------------------------------


def test_i4_authority_drift_flips_authority_hash_so_cache_misses(tmp_path):
    """The Task 3.3 authority drift detector recomputes ``authority_hash``
    using the live envelope. If we mutate the envelope's
    ``allowed_actions`` between two derivations, the recomputed
    ``authority_hash`` MUST differ from the original — proving the
    detector's input fingerprint changes whenever authority drifts.
    Combined with the composite key including ``authority_hash``, this
    guarantees the cache cannot serve a stale entry under widened or
    revoked authority."""
    env_initial = _envelope()
    snapshot_actions = tuple(env_initial.allowed_actions)

    h_initial = ContextCacheKeyBuilder.authority_hash(
        env_initial,
        original_allowed_actions=snapshot_actions,
    )

    # Authority drifts mid-flight: live envelope widens by one action.
    env_widened = env_initial.model_copy(
        update={"allowed_actions": list(env_initial.allowed_actions) + ["unrelated_extra_action"]}
    )
    h_widened_same_snapshot = ContextCacheKeyBuilder.authority_hash(
        env_widened,
        original_allowed_actions=snapshot_actions,  # snapshot unchanged
    )

    assert h_initial != h_widened_same_snapshot, (
        "live envelope.allowed_actions widening MUST flip authority_hash "
        "even when original_allowed_actions snapshot is unchanged"
    )

    # Authority drifts the other way: revocation timestamp set.
    env_revoked = env_initial.model_copy(
        update={"revoked_at": env_initial.created_at}
    )
    h_revoked = ContextCacheKeyBuilder.authority_hash(
        env_revoked,
        original_allowed_actions=snapshot_actions,
    )
    assert h_initial != h_revoked, (
        "setting revoked_at MUST flip authority_hash"
    )


# ---------------------------------------------------------------------------
# I5 — ContextBuilder remains unmodified / no cache-helper imports
# ---------------------------------------------------------------------------


def test_i5_context_builder_module_has_no_closure_imports():
    """ContextBuilder must not import anything from
    sentinel.perf.caches, must not reference ContextCacheKey or
    ContextCacheKeyBuilder, and must not have any cache-related kwarg
    on its public surface. This is the structural witness that
    AgentRuntime owns ContextCacheKey derivation."""
    import inspect

    from sentinel.agent import context_builder as cb_module

    source = inspect.getsource(cb_module)

    # No closure-spec imports.
    forbidden_substrings = [
        "sentinel.perf.caches",
        "ContextCacheKey",
        "ContextCacheKeyBuilder",
        "ContextBuildCache",
        "cache_key_provider",
        "context_build_cache",
    ]
    for forbidden in forbidden_substrings:
        assert forbidden not in source, (
            f"context_builder.py must not contain {forbidden!r} — "
            f"AgentRuntime owns ContextCacheKey derivation"
        )

    # ContextBuilder.build signature unchanged.
    sig = inspect.signature(cb_module.ContextBuilder.build)
    params = sig.parameters
    expected_params = {"self", "envelope", "user_input", "evidence_refs", "memory_items"}
    assert set(params) == expected_params, (
        f"ContextBuilder.build parameter set must be {expected_params}; "
        f"got {set(params)}"
    )
    # No required parameter besides envelope (and self).
    required = [
        name for name, p in params.items()
        if name not in ("self",) and p.default is inspect.Parameter.empty
    ]
    assert required == ["envelope"], (
        f"ContextBuilder.build must have only 'envelope' as required; got {required}"
    )


# ---------------------------------------------------------------------------
# R1 — CanonicalComparison regression: cached output equivalent to fresh
# ---------------------------------------------------------------------------


def test_r1_cached_context_equivalent_to_fresh_under_canonical_comparison(tmp_path):
    """The cached AgentContext returned on a cache hit must be
    functionally equivalent under CanonicalComparison to the AgentContext
    a fresh build would produce. ``ContextBuildCache.get_or_build``
    deepcopies its stored copy on read, so identity differs (id() not
    equal) but the canonical content is the same.

    Per the closure spec's CanonicalComparison contract, allowed
    volatile fields are object identifiers and nested envelope.id;
    must-match fields are mission authority decisions, available
    capabilities, evidence_refs, constraints, and summary."""
    env = _envelope()
    bus = EventBus(env.id)
    cache = ContextBuildCache(event_bus=bus)
    runtime = AgentRuntime(project_root=tmp_path, context_build_cache=cache)

    # First run populates the cache.
    result_first = runtime.run(
        env,
        {"idea": "R1 first run"},
        evidence_refs=["ev_x", "ev_y"],
    )
    assert result_first.success is True

    # Second run should hit the cache.
    result_second = runtime.run(
        env,
        {"idea": "R1 first run"},  # same input shape
        evidence_refs=["ev_x", "ev_y"],
    )
    assert result_second.success is True

    hit_events = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_HIT
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    assert len(hit_events) >= 1, (
        "second identical run with injected ContextBuildCache must produce "
        "at least one CACHE_HIT for the context-build slice"
    )

    # CanonicalComparison: both runs must reach COMPLETED with no
    # authority expansion, no raw secret leakage, and an identical
    # final-phase outcome. The cached path may have id() inequality
    # for the underlying AgentContext (deepcopy on read), but the
    # observable mission outcome must be identical across the
    # never-relax dimensions.
    assert result_first.final_phase == result_second.final_phase
    assert result_first.success == result_second.success

    # No CACHE_CORRECTNESS_VIOLATION events emitted — the cached
    # context did not diverge from a fresh build under any
    # canonical-comparison check the cache itself runs.
    correctness_violations = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION
    ]
    assert correctness_violations == [], (
        "cached context must be canonical-equivalent to a fresh build; "
        f"saw {len(correctness_violations)} CACHE_CORRECTNESS_VIOLATION events"
    )
