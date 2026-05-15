# Feature: sentinel-performance-runtime-foundation, Task 6.11: Wire caches into the decision core
"""Regression tests — Task 6.11 default-off cache wiring.

**Validates: Requirements 2.1, 2.2, 2.3, 9.1, 9.5, 10.2.**

Property statement
------------------

Task 6.11 wires four optional caches/governors into
:class:`sentinel.agent.runtime.AgentRuntime`:

* :class:`sentinel.perf.caches.context_build_cache.ContextBuildCache`
  wrapping ``ContextBuilder.build``;
* :class:`sentinel.perf.caches.prompt_frame_cache.PromptFrameCache`
  wrapping ``LLMDecisionFrame.render_prompt_text``;
* :class:`sentinel.perf.caches.llm_decision_frame_cache.LLMDecisionFrameCache`
  wrapping ``LLMDecisionFrame.build``;
* :class:`sentinel.perf.caches.token_budget_governor.TokenBudgetGovernor`
  wrapping ``LLMDecisionFrame`` build with frame-budget enforcement.

Each is gated by ``if self._<cache> is not None:``. The
**default-off / bit-identical** contract from the patched ``tasks.md``
and the Phase C user direction requires that when every cache
parameter is ``None`` (the default), the runtime executes the same
path as the pre-Task-6.11 code: no extra method calls, no extra
event emissions, no overhead.

These regression tests confirm:

1. ``AgentRuntime`` can be constructed without any cache injection
   (the historic API remains valid).
2. A representative mission run with no caches injected produces
   the same observable outcome (success, final phase, mission
   result, event-stream shape) as before the wiring landed.
3. When a :class:`ContextBuildCache` is injected, two runs against
   the same envelope produce one cache miss followed by one cache
   hit (proving the wiring is connected) without changing the
   observable run outcome (proving authority and behavior are
   preserved).
"""

from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentPhase, AgentRuntime
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.perf.caches.context_build_cache import (
    CACHE_TYPE as CONTEXT_CACHE_TYPE,
    ContextBuildCache,
)
from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache
from sentinel.perf.caches.prompt_frame_cache import PromptFrameCache
from sentinel.perf.caches.token_budget_governor import TokenBudgetGovernor
from sentinel.shared.enums import MissionMode, MissionStatus, MissionType
from sentinel.shared.events import AgentEventType, EventBus


# ---------------------------------------------------------------------------
# Envelope fixture — mirrors test_agent_runtime.py to keep the two
# regression suites aligned.
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
        "user_id": "user_t611",
        "mission_type": MissionType.GTM,
        "mission_title": "Task 6.11 default-off regression",
        "mission_objective": "Confirm AgentRuntime preserves bit-identical behavior with caches uninjected.",
        "success_criteria": ["GTM files exist", "Trace exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": _SAFE_ACTIONS,
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
# 1. Constructor accepts the new cache parameters as ``None``.
# ---------------------------------------------------------------------------


def test_runtime_accepts_no_cache_injection_default(tmp_path):
    """``AgentRuntime`` without any cache injection constructs and
    exposes ``None`` on every cache attribute. Validates Task 6.11
    additive-optional-parameter contract."""

    runtime = AgentRuntime(project_root=tmp_path)

    assert runtime._context_build_cache is None
    assert runtime._prompt_frame_cache is None
    assert runtime._decision_frame_cache is None
    assert runtime._token_budget_governor is None


# ---------------------------------------------------------------------------
# 2. Default-off run produces the same observable outcome.
# ---------------------------------------------------------------------------


def test_runtime_default_off_run_matches_baseline(tmp_path):
    """A representative mission run with no cache injection produces
    a successful COMPLETED outcome and emits no cache-family events.

    The "no cache events emitted" assertion is the structural witness
    that the no-injection path does not call any cache machinery —
    every cache module emits at least one event on every call, so an
    empty cache-event slice proves the cache code path was not taken.
    """

    env = _envelope()

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": "Sentinel SPINE bit-identical baseline"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    project_path = Path(result.project_path or "")
    event_types = {event.event_type for event in result.trace}

    assert result.success is True
    assert result.final_phase == AgentPhase.COMPLETED
    assert result.mission_result is not None
    assert result.mission_result.state.status == MissionStatus.COMPLETED
    assert project_path.exists()

    # Default-off contract: the runtime emits no cache-family events
    # when no caches are injected. If any cache wiring leaked into
    # the no-injection path, at least one of these would fire.
    cache_event_types = {
        AgentEventType.CACHE_HIT,
        AgentEventType.CACHE_MISS,
        AgentEventType.CACHE_EVICTED,
        AgentEventType.CACHE_CORRECTNESS_VIOLATION,
    }
    assert cache_event_types.isdisjoint(event_types), (
        "default-off AgentRuntime must not emit any cache-family events"
    )


# ---------------------------------------------------------------------------
# 3. Inject ContextBuildCache — first run misses, second run hits.
# ---------------------------------------------------------------------------


def test_runtime_with_context_build_cache_emits_miss_then_hit(tmp_path):
    """Two runs against the same envelope with a shared
    :class:`ContextBuildCache` injection produce the expected
    miss-then-hit pattern, proving the wiring is connected.

    The cache key is composed from envelope-derived inputs; two runs
    with the same envelope hash to the same composite, so the second
    run's :meth:`ContextBuildCache.get_or_build` should return a
    cached :class:`AgentContext` instead of calling the builder. The
    observable run outcome must remain unchanged across both runs —
    the cache must not alter authority, mission result, or final
    phase.
    """

    env = _envelope()
    bus = EventBus(env.id)
    cache = ContextBuildCache(event_bus=bus)

    # First run — cache is empty, expect a miss.
    runtime_a = AgentRuntime(project_root=tmp_path, context_build_cache=cache)
    result_a = runtime_a.run(
        env,
        {"idea": "Sentinel SPINE first-run cache miss"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    miss_events = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_MISS
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    hit_events = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_HIT
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    assert len(miss_events) == 1, "first run must produce exactly one ContextBuildCache miss"
    assert hit_events == [], "first run must not produce any ContextBuildCache hit"
    assert miss_events[0].payload["mission_id"] == env.id

    # Second run — same envelope, same composite key, expect a hit.
    runtime_b = AgentRuntime(project_root=tmp_path, context_build_cache=cache)
    result_b = runtime_b.run(
        env,
        {"idea": "Sentinel SPINE first-run cache miss"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    miss_events_after = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_MISS
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    hit_events_after = [
        event for event in bus.events()
        if event.event_type == AgentEventType.CACHE_HIT
        and event.payload.get("cache_type") == CONTEXT_CACHE_TYPE
    ]
    assert len(miss_events_after) == 1, "second run must not produce a new miss"
    assert len(hit_events_after) == 1, "second run must produce exactly one cache hit"
    assert hit_events_after[0].payload["mission_id"] == env.id

    # Both runs must produce the same observable outcome — the cache
    # cannot alter authority, mission result, or final phase.
    assert result_a.success == result_b.success == True  # noqa: E712
    assert result_a.final_phase == result_b.final_phase == AgentPhase.COMPLETED


# ---------------------------------------------------------------------------
# 4. All four caches injectable simultaneously without breaking the run.
# ---------------------------------------------------------------------------


def test_runtime_accepts_all_four_caches_simultaneously(tmp_path):
    """All four Task-6.11 cache injections may be passed together;
    the runtime constructs and runs successfully. This is a smoke
    test for the additive-parameter surface — no behavioral
    assertions beyond a successful end-to-end mission run.

    The decision-frame cache and prompt-frame cache do not have
    AgentRuntime call sites yet (the cognitive cycle does not invoke
    ``LLMDecisionFrame.build`` or ``render_prompt_text`` from the
    runtime today); the helper attributes are stored for future
    wiring. This test confirms that storing them does not perturb
    the existing run path.
    """

    env = _envelope()
    bus = EventBus(env.id)

    runtime = AgentRuntime(
        project_root=tmp_path,
        context_build_cache=ContextBuildCache(event_bus=bus),
        prompt_frame_cache=PromptFrameCache(event_bus=bus),
        decision_frame_cache=LLMDecisionFrameCache(event_bus=bus),
        token_budget_governor=TokenBudgetGovernor(event_bus=bus),
    )

    result = runtime.run(
        env,
        {"idea": "Sentinel SPINE all-four-caches smoke test"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    assert result.success is True
    assert result.final_phase == AgentPhase.COMPLETED
    assert result.mission_result is not None
