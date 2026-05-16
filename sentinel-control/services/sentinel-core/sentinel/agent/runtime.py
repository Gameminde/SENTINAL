from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any
from collections.abc import Callable

from pydantic import ConfigDict

from sentinel.shared.models import SentinelModel

from sentinel.agent.audit import RuntimeCertificationGate
from sentinel.agent.browser import (
    BrowserControlledCapabilityRunner,
    BrowserEvidenceInterpreter,
    BrowserFetcher,
    BrowserInteractionBackend,
    BrowserOperatorRouteProtocol,
    BrowserRenderer,
    DnsResolver,
)
from sentinel.agent.capability_selector import CapabilitySelector
from sentinel.agent.cognitive_cycle import CognitiveCycle
from sentinel.agent.controlled_capability import LocalControlledCapabilityRunner
from sentinel.agent.context_builder import ContextBuilder
from sentinel.agent.context_compressor import ContextCompressor
from sentinel.agent.event_bus import EventBus
from sentinel.agent.effort_router import EffortRouter
from sentinel.agent.events import AgentEventType
from sentinel.agent.evidence import EvidenceChainBuilder
from sentinel.agent.exceptions import AgentBlockedError, MissionRevokedError
from sentinel.agent.execution_posture import ExecutionPosturePolicy
from sentinel.agent.final_gate import CoreFinalGate
from sentinel.agent.hypothesis import HypothesisVerifier
from sentinel.agent.identity import AgentIdentity, default_agent_identity
from sentinel.agent.invariants import InvariantViolation
from sentinel.agent.learning_loop import LearningLoop
from sentinel.agent.method_selector import MethodSelector
from sentinel.agent.models import AgentContext, AgentRunResult
from sentinel.agent.phases import AgentPhase, can_transition
from sentinel.agent.planner_bridge import PlannerBridge
from sentinel.agent.repair_loop import CognitiveRepairLoop, RepairDecisionType
from sentinel.agent.replay import AgentTraceReplayer
from sentinel.agent.review_loop import ReviewLoop
from sentinel.agent.state import AgentState
from sentinel.agent.supervisor import Supervisor
from sentinel.agent.tool_call_protocol import ToolCallProtocol
from sentinel.agent.tool_selector import ToolSelector
from sentinel.agent.worker_coordinator import WorkerCoordinator
from sentinel.agent.world_model import ActionEvaluator
from sentinel.capabilities import ToolRegistry, default_tool_registry
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.mission.runner import MissionRunner
from sentinel.mission.safe_executors import mission_slug


if TYPE_CHECKING:
    from sentinel.perf.caches.context_build_cache import ContextBuildCache
    from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache
    from sentinel.perf.caches.prompt_frame_cache import PromptFrameCache
    from sentinel.perf.caches.token_budget_governor import TokenBudgetGovernor
    from sentinel.perf.measure.cost_profiler import CostProfiler
    from sentinel.perf.measure.latency_profiler import LatencyProfiler
    from sentinel.perf.sched.async_organ_scheduler import AsyncOrganScheduler, SubmissionAck
    from sentinel.perf.sched.backpressure_controller import BackpressureController
    from sentinel.organs.authority import OrganAuthorityEnvelope
    from sentinel.organs.dry_run import OrganDryRunReceipt
    from sentinel.organs.kill_switch import OrganKillSwitch


# Task 8.8 / sentinel-performance-runtime-foundation —
# Minimal frozen action stub satisfying the scheduler's structural
# ``_OrganActionLike`` protocol (``action_id``, ``mission_id``,
# ``organ_id``, ``action_type``). The scheduler reads only these short
# identifier strings from the action object — never any payload bytes,
# never any tool-call arguments, never any organ output. This stub is
# therefore sufficient for routing and matches the structural protocol.
#
# The model is frozen so the scheduler cannot be handed a mutable
# action object (defense against accidental post-submit mutation
# during the wrapper task's lifetime).
class _ToolCallSchedulerAction(SentinelModel):
    """Frozen scheduler action stub for routed AgentRuntime tool calls."""

    action_id: str
    mission_id: str
    organ_id: str
    action_type: str

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class AgentRuntime:
    def __init__(
        self,
        *,
        identity: AgentIdentity | None = None,
        project_root: str | Path | None = None,
        tool_registry: ToolRegistry | None = None,
        browser_renderer: BrowserRenderer | None = None,
        browser_fetcher: BrowserFetcher | None = None,
        browser_interaction_backend: BrowserInteractionBackend | None = None,
        browser_resolver: DnsResolver | None = None,
        browser_operator_route: BrowserOperatorRouteProtocol | None = None,
        latency_profiler: LatencyProfiler | None = None,
        cost_profiler: CostProfiler | None = None,
        # Task 6.11 / sentinel-performance-runtime-foundation —
        # additive optional cache injections. When every parameter
        # below is ``None`` (the default), :meth:`run` is byte-for-byte
        # identical to the pre-Task-6.11 path: no extra method calls,
        # no extra event emissions, no overhead. Each cache is gated
        # at its call site by an ``if self._<cache> is not None:``
        # guard. See :meth:`run` and the per-call-site comments below.
        #
        # Default-off / injection-gated contract (Phase C user
        # direction): existing public behavior is preserved.
        # Constructor changes are additive optional parameters with
        # ``None`` defaults. Cache hits never expand authority — the
        # composite key includes ``authority_hash``, so this is
        # structural. Cache events never include raw prompt bodies,
        # file bodies, browser bodies, credentials, secrets, or
        # artifact blobs (the cache modules already enforce this; the
        # integration here does not bypass).
        context_build_cache: ContextBuildCache | None = None,
        prompt_frame_cache: PromptFrameCache | None = None,
        decision_frame_cache: LLMDecisionFrameCache | None = None,
        token_budget_governor: TokenBudgetGovernor | None = None,
        # Task 8.8 / sentinel-performance-runtime-foundation —
        # additive optional async scheduler injections. When BOTH
        # parameters below are ``None`` (the default),
        # :meth:`_execute_controlled_tool_calls` runs each tool call
        # through the original synchronous runner path with
        # bit-identical observable behaviour: same receipt stream,
        # same event types in the same order, no extra emissions.
        # When BOTH are injected, organ-shaped tool calls route
        # through ``async_organ_scheduler.submit(...)`` (which
        # internally consults ``backpressure_controller`` for the
        # admission decision and emits its own
        # ``QUEUE_BACKPRESSURE_APPLIED`` / scheduler events). The
        # underlying ``OrganExecutionReceipt`` / controlled-capability
        # receipt sequence still matches the synchronous path
        # (Acceptance criterion 6 of Task 8.8). Backpressure
        # rejection surfaces as a documented rejection receipt /
        # event — never silently dropped (strict rule).
        #
        # Per Task 8.8 contract: existing safety checks
        # (``OrganAuthorityEnvelope`` validation,
        # ``OrganKillSwitch`` blocking gate, ``OrganDryRunReceipt``
        # pre-flight) are PRESERVED end-to-end. Authority,
        # kill-switch, and dry-run pre-flight happen BEFORE
        # ``scheduler.submit`` (Acceptance criterion 4); the
        # scheduler itself re-asserts kill-switch and authority
        # gates as a defense-in-depth chokepoint.
        async_organ_scheduler: AsyncOrganScheduler | None = None,
        backpressure_controller: BackpressureController | None = None,
    ) -> None:
        self.identity = identity or default_agent_identity()
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.tool_registry = tool_registry or default_tool_registry()
        self._latency_profiler = latency_profiler
        self._cost_profiler = cost_profiler
        # Task 6.11: store cache injections. ``None`` means "not
        # injected" — every consumer call site checks the attribute
        # against ``None`` before taking the cache path.
        self._context_build_cache = context_build_cache
        self._prompt_frame_cache = prompt_frame_cache
        self._decision_frame_cache = decision_frame_cache
        self._token_budget_governor = token_budget_governor
        # Task 8.8: store async scheduler + backpressure injections.
        # ``None`` means "not injected" — :meth:`_execute_controlled_tool_calls`
        # checks ``self._async_organ_scheduler is not None`` AND
        # ``self._backpressure_controller is not None`` before taking
        # the scheduler path. When either is None, the synchronous
        # path is used unchanged. The strict rule from Phase D is
        # explicit: do NOT use a flag that defaults on for tests but
        # off for prod — the "default off" behaviour is structural,
        # because absence of injection IS the default off.
        self._async_organ_scheduler = async_organ_scheduler
        self._backpressure_controller = backpressure_controller
        self.context_builder = ContextBuilder()
        self.context_compressor = ContextCompressor()
        self.cognitive_cycle = CognitiveCycle()
        self.method_selector = MethodSelector()
        self.capability_selector = CapabilitySelector(registry=self.tool_registry)
        self.tool_selector = ToolSelector(self.tool_registry)
        self.tool_call_protocol = ToolCallProtocol()
        self.hypothesis_verifier = HypothesisVerifier()
        self.action_evaluator = ActionEvaluator()
        self.effort_router = EffortRouter()
        self.execution_posture_policy = ExecutionPosturePolicy()
        self.evidence_chain_builder = EvidenceChainBuilder()
        self.browser_evidence_interpreter = BrowserEvidenceInterpreter()
        self.planner_bridge = PlannerBridge(project_root=str(self.project_root))
        self.browser_operator_route = browser_operator_route
        mission_runner = MissionRunner(project_root=self.project_root, browser_operator_route=browser_operator_route) if browser_operator_route is not None else None
        self.worker_coordinator = WorkerCoordinator(project_root=self.project_root, runner=mission_runner)
        self.review_loop = ReviewLoop()
        self.repair_loop = CognitiveRepairLoop()
        self.learning_loop = LearningLoop()
        self.supervisor = Supervisor()
        self.certification_gate = RuntimeCertificationGate()
        self.trace_replayer = AgentTraceReplayer()
        # Task 1.1 / Requirement 1 (FinalGate Runtime Integration):
        # CoreFinalGate is constructed here so that AgentRuntime.run can invoke
        # terminal safety certification on every exit path. CoreFinalGate has
        # no constructor dependencies — its `evaluate(result, allowed_project_root=...)`
        # call takes the run result and an optional project-root scope at call time.
        self._final_gate = CoreFinalGate()
        self.browser_renderer = browser_renderer
        self.browser_fetcher = browser_fetcher
        self.browser_interaction_backend = browser_interaction_backend
        self.browser_resolver = browser_resolver

    def _assert_memory_not_authority_boundary(
        self,
        boundary_name: str,
        context: AgentContext,
        envelope: MissionAuthorityEnvelope,
        original_allowed_actions: tuple[str, ...],
    ) -> None:
        """Re-invoke the Memory-not-Authority invariant at a phase boundary.

        Requirement 2 / Task 2 — the check is repeated at every phase
        transition (not just at CONTEXT_BUILDING) so that mid-run mutation of
        ``context.mission.allowed_actions`` or contamination of
        ``context.available_capabilities`` is detected before the next phase
        consumes the tainted state.

        Any :class:`InvariantViolation` raised here propagates to the
        ``except Exception`` handler in :meth:`run`, which wraps it into a
        BLOCKED :class:`AgentRunResult` and routes it through
        :meth:`_apply_final_gate` (F-A3.11).
        """
        self.supervisor.assert_context_did_not_expand_authority(
            context,
            envelope=envelope,
            original_allowed_actions=original_allowed_actions,
            boundary_name=boundary_name,
        )

    def run(
        self,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any] | None = None,
        *,
        evidence_refs: list[str] | None = None,
        memory_items: list[dict[str, Any]] | None = None,
    ) -> AgentRunResult:
        event_bus = EventBus(envelope.id)
        evidence_chains = []
        controlled_capability_results: list[dict[str, Any]] = []
        mission_results = []
        execution_posture = None
        context = None
        # Task 2.4-A Gap 2 fix: hoist local variables that may be bound in the
        # happy-path between different phases so the ``except Exception``
        # handler can unconditionally reference them when building the
        # BLOCKED fallback ``AgentRunResult``. Without this, an
        # ``InvariantViolation`` raised at the T21 (REPAIRING→EXECUTING)
        # boundary would drop ``mission_result`` and ``active_plan`` from
        # the BLOCKED result, causing ``CoreFinalGate`` to reject it with
        # ``archived_mission_results_without_final_mission_result`` and the
        # deep-invariant fail-safe in ``_apply_final_gate`` to raise
        # ``AgentBlockedError``.
        plan = None
        mission_result = None
        # Task 2 / Requirement 2 — Memory-not-Authority Multi-Phase Enforcement.
        # Capture the envelope's allowed_actions at run entry so subsequent
        # boundary re-checks can detect mid-run mutation / context contamination
        # that tries to grow authority beyond what was originally authorised.
        original_allowed_actions: tuple[str, ...] = tuple(envelope.allowed_actions)
        state = AgentState(mission_id=envelope.id).transition(AgentPhase.INITIALIZED)
        event_bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "Agent runtime initialized.",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
            payload={"agent_id": self.identity.id, "doctrine": self.identity.doctrine},
        )

        try:
            state = state.transition(AgentPhase.CONTEXT_BUILDING)
            # Task 6.11 / sentinel-performance-runtime-foundation —
            # ContextBuildCache integration. The cache is gated by
            # ``if self._context_build_cache is not None``. When the
            # cache is None (the default) we fall through to the
            # original inline build path below, which is bit-identical
            # to the pre-Task-6.11 code: no extra method calls, no
            # extra event emissions, no closures.
            #
            # When the cache is injected, we compute a composite key
            # from stable strings derived from the envelope. The
            # ``authority_hash`` slot is bound to ``envelope.id`` for
            # now (mission ID is unique per envelope and cannot
            # broaden authority); the four slot inputs will be plumbed
            # through to real hashes when Phase E ships (workspace
            # snapshot ID + organ-state hash + the actual
            # mission-hot-hash). The composite key still discriminates
            # by mission, which is sufficient to keep cache hits
            # within the original mission's authority envelope —
            # ``ContextBuildCache.composite_key`` includes
            # ``authority_hash``, so a frame built under different
            # authority hashes to a different cache entry by
            # construction. Cache hits never expand authority.
            if self._context_build_cache is not None:
                def _build_context_cached() -> AgentContext:
                    if self._latency_profiler is not None:
                        with self._latency_profiler.instrument(
                            mission_id=envelope.id,
                            action_id=f"{envelope.id}:context_build",
                            action_type="context_build",
                        ):
                            return self.context_builder.build(
                                envelope,
                                user_input=user_input or {},
                                evidence_refs=evidence_refs,
                                memory_items=memory_items,
                            )
                    return self.context_builder.build(
                        envelope,
                        user_input=user_input or {},
                        evidence_refs=evidence_refs,
                        memory_items=memory_items,
                    )

                composite_key = self._context_build_cache.composite_key(
                    mission_hot_hash=envelope.id,
                    workspace_snapshot_id="v1",
                    organ_state_hash="v1",
                    authority_hash=envelope.id,
                )
                context = self._context_build_cache.get_or_build(
                    composite_key,
                    _build_context_cached,
                    mission_id=envelope.id,
                )
            elif self._latency_profiler is not None:
                with self._latency_profiler.instrument(
                    mission_id=envelope.id,
                    action_id=f"{envelope.id}:context_build",
                    action_type="context_build",
                ):
                    context = self.context_builder.build(
                        envelope,
                        user_input=user_input or {},
                        evidence_refs=evidence_refs,
                        memory_items=memory_items,
                    )
            else:
                context = self.context_builder.build(
                    envelope,
                    user_input=user_input or {},
                    evidence_refs=evidence_refs,
                    memory_items=memory_items,
                )
            self.supervisor.assert_mission_can_run(context)
            self.supervisor.assert_context_did_not_expand_authority(context)
            event_bus.append(
                AgentEventType.CONTEXT_BUILT,
                "Agent context built from mission authority and input.",
                phase_before=AgentPhase.INITIALIZED,
                phase_after=AgentPhase.CONTEXT_BUILDING,
                payload={"summary": context.summary, "constraints": context.constraints},
            )

            if self._latency_profiler is not None:
                with self._latency_profiler.instrument(
                    mission_id=envelope.id,
                    action_id=f"{envelope.id}:context_compress",
                    action_type="context_compress",
                ):
                    context = self.context_compressor.compress(context)
            else:
                context = self.context_compressor.compress(context)
            event_bus.append(
                AgentEventType.CONTEXT_COMPRESSED,
                "Agent context compressed while preserving authority and references.",
                phase_before=AgentPhase.CONTEXT_BUILDING,
                phase_after=AgentPhase.CONTEXT_BUILDING,
                payload={"summary": context.summary, "evidence_refs": context.evidence_refs},
            )

            state = state.transition(AgentPhase.ORIENTING)
            self._assert_memory_not_authority_boundary(
                "context_building_to_orienting",
                context,
                envelope,
                original_allowed_actions,
            )
            if self._latency_profiler is not None:
                with self._latency_profiler.instrument(
                    mission_id=envelope.id,
                    action_id=f"{envelope.id}:orient",
                    action_type="orient",
                ):
                    state = self.cognitive_cycle.orient(state, context)
            else:
                state = self.cognitive_cycle.orient(state, context)
            event_bus.append(
                AgentEventType.ORIENTATION_COMPLETED,
                "Agent orientation completed.",
                phase_before=AgentPhase.CONTEXT_BUILDING,
                phase_after=AgentPhase.ORIENTING,
                payload={"known_facts": len(state.known_facts), "open_questions": len(state.open_questions)},
            )

            state = state.transition(AgentPhase.METHOD_SELECTING)
            self._assert_memory_not_authority_boundary(
                "orienting_to_method_selecting",
                context,
                envelope,
                original_allowed_actions,
            )
            methods = self.method_selector.select(context)
            state = state.model_copy(update={"selected_methods": methods})
            event_bus.append(
                AgentEventType.METHODS_SELECTED,
                "Agent selected deterministic work methods.",
                phase_before=AgentPhase.ORIENTING,
                phase_after=AgentPhase.METHOD_SELECTING,
                payload={"methods": [method.id for method in methods]},
            )

            state = state.transition(AgentPhase.CAPABILITY_SELECTING)
            self._assert_memory_not_authority_boundary(
                "method_selecting_to_capability_selecting",
                context,
                envelope,
                original_allowed_actions,
            )
            capabilities = self.capability_selector.select(context, methods)
            missing_capabilities = [need for need in capabilities if not need.available]
            self.supervisor.assert_capabilities_are_declared(capabilities)
            state = state.model_copy(update={"needed_capabilities": capabilities, "missing_capabilities": missing_capabilities})
            event_bus.append(
                AgentEventType.CAPABILITIES_SELECTED,
                "Agent declared capability needs.",
                phase_before=AgentPhase.METHOD_SELECTING,
                phase_after=AgentPhase.CAPABILITY_SELECTING,
                payload={"needed": [need.name for need in capabilities], "missing": [need.name for need in missing_capabilities]},
            )

            state = state.transition(AgentPhase.TOOL_SELECTING)
            self._assert_memory_not_authority_boundary(
                "capability_selecting_to_tool_selecting",
                context,
                envelope,
                original_allowed_actions,
            )
            tool_selection = self.tool_selector.select(context, capabilities, event_bus=event_bus)
            state = state.model_copy(
                update={
                    "tool_selection_decisions": tool_selection.decisions,
                    "selected_tools": tool_selection.selected_tools,
                    "candidate_tools": tool_selection.candidate_tools,
                    "blocked_tools": tool_selection.blocked_tools,
                    "unavailable_capabilities": tool_selection.unavailable_capabilities,
                }
            )
            tool_selection_findings = self.review_loop.review_tool_selection(capabilities, tool_selection)
            evidence_chains.append(
                self.evidence_chain_builder.build_tool_selection(
                    context,
                    tool_selection,
                    tool_selection_findings,
                    event_bus=event_bus,
                )
            )
            state = state.model_copy(update={"review_findings": tool_selection_findings})
            critical_tool_selection_findings = [
                finding for finding in tool_selection_findings if finding.severity == "critical"
            ]
            if critical_tool_selection_findings:
                state = state.transition(AgentPhase.LEARNING_PROPOSING)
                learning_proposals = self.learning_loop.propose(
                    review_findings=tool_selection_findings,
                    missing_capabilities=[need for need in capabilities if need.name in tool_selection.missing_capabilities],
                    mission_failed=True,
                )
                self.supervisor.assert_learning_is_safe(learning_proposals)
                event_bus.append(
                    AgentEventType.LEARNING_PROPOSED,
                    "Agent created learning proposals after tool selection review.",
                    phase_before=AgentPhase.TOOL_SELECTING,
                    phase_after=AgentPhase.LEARNING_PROPOSING,
                    payload={"proposal_count": len(learning_proposals)},
                )
                evidence_chains.append(
                    self.evidence_chain_builder.build_learning_proposal(
                        context,
                        learning_proposals,
                        tool_selection_findings,
                        [need for need in capabilities if need.name in tool_selection.missing_capabilities],
                        event_bus=event_bus,
                    )
                )
                state = state.transition(AgentPhase.BLOCKED)
                event_bus.append(
                    AgentEventType.AGENT_BLOCKED,
                    "Agent blocked execution because required tools were unavailable.",
                    phase_before=AgentPhase.LEARNING_PROPOSING,
                    phase_after=AgentPhase.BLOCKED,
                    payload={"findings": [finding.code for finding in critical_tool_selection_findings]},
                )
                self.supervisor.assert_trace_integrity(event_bus)
                return self._apply_final_gate(AgentRunResult(
                    mission_id=envelope.id,
                    final_phase=AgentPhase.BLOCKED,
                    success=False,
                    selected_methods=methods,
                    needed_capabilities=capabilities,
                    missing_capabilities=missing_capabilities,
                    tool_selection_decisions=tool_selection.decisions,
                    selected_tools=tool_selection.selected_tools,
                    candidate_tools=tool_selection.candidate_tools,
                    blocked_tools=tool_selection.blocked_tools,
                    unavailable_capabilities=tool_selection.unavailable_capabilities,
                    known_facts=state.known_facts,
                    assumptions=state.assumptions,
                    suspected=state.suspected,
                    open_questions=state.open_questions,
                    review_findings=tool_selection_findings,
                    learning_proposals=learning_proposals,
                    evidence_chains=evidence_chains,
                    trace=list(event_bus.events()),
                    runtime_certification=self._certify_trace(event_bus),
                    state_snapshot=self._snapshot_trace(event_bus),
                    escalation_reason="Tool selection produced critical findings.",
                ))

            state = state.transition(AgentPhase.HYPOTHESIS_VERIFYING)
            self._assert_memory_not_authority_boundary(
                "tool_selecting_to_hypothesis_verifying",
                context,
                envelope,
                original_allowed_actions,
            )
            hypothesis_result = self.hypothesis_verifier.run(context, event_bus=event_bus)
            state = state.model_copy(
                update={
                    "hypotheses": hypothesis_result.hypotheses,
                    "verified_hypotheses": hypothesis_result.verified_hypotheses,
                    "verification_tests": hypothesis_result.verification_tests,
                    "adversarial_findings": hypothesis_result.adversarial_findings,
                }
            )
            hypothesis_findings = self.review_loop.review_hypotheses(hypothesis_result)
            evidence_chains.append(
                self.evidence_chain_builder.build_hypothesis_verdict(
                    context,
                    hypothesis_result,
                    hypothesis_findings,
                    event_bus=event_bus,
                )
            )
            critical_hypothesis_findings = [finding for finding in hypothesis_findings if finding.severity == "critical"]
            if critical_hypothesis_findings:
                state = state.model_copy(update={"review_findings": hypothesis_findings})
                state = state.transition(AgentPhase.LEARNING_PROPOSING)
                learning_proposals = self.learning_loop.propose(
                    review_findings=hypothesis_findings,
                    missing_capabilities=[],
                    mission_failed=True,
                )
                self.supervisor.assert_learning_is_safe(learning_proposals)
                event_bus.append(
                    AgentEventType.LEARNING_PROPOSED,
                    "Agent created learning proposals after hypothesis verification review.",
                    phase_before=AgentPhase.HYPOTHESIS_VERIFYING,
                    phase_after=AgentPhase.LEARNING_PROPOSING,
                    payload={"proposal_count": len(learning_proposals)},
                )
                evidence_chains.append(
                    self.evidence_chain_builder.build_learning_proposal(
                        context,
                        learning_proposals,
                        hypothesis_findings,
                        [],
                        event_bus=event_bus,
                    )
                )
                state = state.transition(AgentPhase.BLOCKED)
                event_bus.append(
                    AgentEventType.AGENT_BLOCKED,
                    "Agent blocked execution because hypothesis verification violated invariants.",
                    phase_before=AgentPhase.LEARNING_PROPOSING,
                    phase_after=AgentPhase.BLOCKED,
                    payload={"findings": [finding.code for finding in critical_hypothesis_findings]},
                )
                self.supervisor.assert_trace_integrity(event_bus)
                return self._apply_final_gate(AgentRunResult(
                    mission_id=envelope.id,
                    final_phase=AgentPhase.BLOCKED,
                    success=False,
                    selected_methods=methods,
                    needed_capabilities=capabilities,
                    missing_capabilities=missing_capabilities,
                    tool_selection_decisions=tool_selection.decisions,
                    selected_tools=tool_selection.selected_tools,
                    candidate_tools=tool_selection.candidate_tools,
                    blocked_tools=tool_selection.blocked_tools,
                    unavailable_capabilities=tool_selection.unavailable_capabilities,
                    hypotheses=hypothesis_result.hypotheses,
                    verified_hypotheses=hypothesis_result.verified_hypotheses,
                    verification_tests=hypothesis_result.verification_tests,
                    adversarial_findings=hypothesis_result.adversarial_findings,
                    known_facts=state.known_facts,
                    assumptions=state.assumptions,
                    suspected=state.suspected,
                    open_questions=state.open_questions,
                    review_findings=hypothesis_findings,
                    learning_proposals=learning_proposals,
                    evidence_chains=evidence_chains,
                    trace=list(event_bus.events()),
                    runtime_certification=self._certify_trace(event_bus),
                    state_snapshot=self._snapshot_trace(event_bus),
                    escalation_reason="Hypothesis verification produced critical findings.",
                ))

            state = state.transition(AgentPhase.ACTION_SCORING)
            self._assert_memory_not_authority_boundary(
                "hypothesis_verifying_to_action_scoring",
                context,
                envelope,
                original_allowed_actions,
            )
            action_result = self.action_evaluator.evaluate(
                context,
                state,
                tool_selection,
                hypothesis_result,
                event_bus=event_bus,
            )
            state = state.model_copy(
                update={
                    "cognitive_actions": action_result.actions,
                    "world_model_predictions": action_result.predictions,
                    "objective_scores": action_result.scores,
                    "action_evaluations": action_result.evaluations,
                    "selected_action_id": action_result.selected_action_id,
                    "selected_action_name": action_result.selected_action_name,
                }
            )

            state = state.transition(AgentPhase.EFFORT_ROUTING)
            effort_route = self.effort_router.route(
                context,
                state,
                tool_selection,
                hypothesis_result,
                action_result,
                event_bus=event_bus,
            )
            state = state.model_copy(update={"effort_route": effort_route})

            state = state.transition(AgentPhase.PLANNING)
            self._assert_memory_not_authority_boundary(
                "effort_routing_to_planning",
                context,
                envelope,
                original_allowed_actions,
            )
            plan = self.planner_bridge.create_plan(
                context,
                methods,
                capabilities,
                tool_selection=tool_selection,
                verified_hypotheses=hypothesis_result.verified_hypotheses,
            )
            state = state.model_copy(update={"plan_id": plan.mission_id})
            event_bus.append(
                AgentEventType.PLAN_CREATED,
                "Mission plan created through MissionRegistry.",
                phase_before=AgentPhase.EFFORT_ROUTING,
                phase_after=AgentPhase.PLANNING,
                payload={
                    "steps": [step.id for step in plan.steps],
                    "selected_tools": tool_selection.selected_tools,
                    "verified_hypotheses": [hypothesis.id for hypothesis in hypothesis_result.verified_hypotheses],
                    "selected_action_id": action_result.selected_action_id,
                    "selected_action_name": action_result.selected_action_name,
                    "effort_level": effort_route.level,
                    "effort_score": effort_route.score,
                },
            )
            execution_posture = self.execution_posture_policy.select(
                envelope,
                reserved_plan_actions=len(plan.steps),
                phase=AgentPhase.PLANNING,
                event_bus=event_bus,
            )
            state = state.model_copy(
                update={
                    "execution_posture": execution_posture,
                    "max_repair_cycles": execution_posture.max_repair_cycles,
                }
            )

            state = state.transition(AgentPhase.PLAN_REVIEWING)
            review_findings = [
                *hypothesis_findings,
                *self.review_loop.review_plan(
                    context,
                    plan,
                    capabilities,
                    tool_selection=tool_selection,
                    verified_hypotheses=hypothesis_result.verified_hypotheses,
                ),
            ]
            state = state.model_copy(update={"review_findings": review_findings})
            event_bus.append(
                AgentEventType.PLAN_REVIEWED,
                "Agent reviewed plan before execution.",
                phase_before=AgentPhase.PLANNING,
                phase_after=AgentPhase.PLAN_REVIEWING,
                payload={"findings": [finding.code for finding in review_findings]},
            )
            evidence_chains.append(
                self.evidence_chain_builder.build_plan_creation(
                    context,
                    plan,
                    tool_selection,
                    hypothesis_result.verified_hypotheses,
                    review_findings,
                    event_bus=event_bus,
                )
            )
            critical_plan_findings = [finding for finding in review_findings if finding.severity == "critical"]
            if critical_plan_findings:
                state = state.transition(AgentPhase.LEARNING_PROPOSING)
                learning_proposals = self.learning_loop.propose(
                    review_findings=review_findings,
                    missing_capabilities=[need for need in missing_capabilities if need.required],
                    mission_failed=True,
                )
                self.supervisor.assert_learning_is_safe(learning_proposals)
                event_bus.append(
                    AgentEventType.LEARNING_PROPOSED,
                    "Agent created learning proposals after critical plan review.",
                    phase_before=AgentPhase.PLAN_REVIEWING,
                    phase_after=AgentPhase.LEARNING_PROPOSING,
                    payload={"proposal_count": len(learning_proposals)},
                )
                evidence_chains.append(
                    self.evidence_chain_builder.build_learning_proposal(
                        context,
                        learning_proposals,
                        review_findings,
                        [need for need in missing_capabilities if need.required],
                        event_bus=event_bus,
                    )
                )
                state = state.transition(AgentPhase.BLOCKED)
                event_bus.append(
                    AgentEventType.AGENT_BLOCKED,
                    "Agent blocked execution because plan review found critical issues.",
                    phase_before=AgentPhase.LEARNING_PROPOSING,
                    phase_after=AgentPhase.BLOCKED,
                    payload={"findings": [finding.code for finding in critical_plan_findings]},
                )
                self.supervisor.assert_trace_integrity(event_bus)
                return self._apply_final_gate(AgentRunResult(
                    mission_id=envelope.id,
                    final_phase=AgentPhase.BLOCKED,
                    success=False,
                    selected_methods=methods,
                    needed_capabilities=capabilities,
                    missing_capabilities=missing_capabilities,
                    tool_selection_decisions=tool_selection.decisions,
                    selected_tools=tool_selection.selected_tools,
                    candidate_tools=tool_selection.candidate_tools,
                    blocked_tools=tool_selection.blocked_tools,
                    unavailable_capabilities=tool_selection.unavailable_capabilities,
                    known_facts=state.known_facts,
                    assumptions=state.assumptions,
                    suspected=state.suspected,
                    open_questions=state.open_questions,
                    hypotheses=hypothesis_result.hypotheses,
                    verified_hypotheses=hypothesis_result.verified_hypotheses,
                    verification_tests=hypothesis_result.verification_tests,
                    adversarial_findings=hypothesis_result.adversarial_findings,
                    cognitive_actions=action_result.actions,
                    world_model_predictions=action_result.predictions,
                    objective_scores=action_result.scores,
                    action_evaluations=action_result.evaluations,
                    selected_action_id=action_result.selected_action_id,
                    selected_action_name=action_result.selected_action_name,
                    controlled_capability_results=controlled_capability_results,
                    effort_route=effort_route,
                    execution_posture=execution_posture,
                    review_findings=review_findings,
                    learning_proposals=learning_proposals,
                    evidence_chains=evidence_chains,
                    trace=list(event_bus.events()),
                    runtime_certification=self._certify_trace(event_bus),
                    state_snapshot=self._snapshot_trace(event_bus),
                    escalation_reason="Plan review produced critical findings.",
                    active_plan=plan,
                ))

            state = state.transition(AgentPhase.EXECUTING)
            self._assert_memory_not_authority_boundary(
                "plan_reviewing_to_executing",
                context,
                envelope,
                original_allowed_actions,
            )
            controlled_capability_results = self._execute_controlled_tool_calls(
                envelope,
                user_input or {},
                event_bus,
                max_calls=execution_posture.direct_tool_call_budget if execution_posture is not None else max(0, envelope.max_actions - len(plan.steps)),
            )
            state = state.model_copy(update={"controlled_capability_results": controlled_capability_results})
            browser_cortex = self.browser_evidence_interpreter.interpret(
                context,
                event_bus.events(),
                hypotheses=hypothesis_result.hypotheses,
                event_bus=event_bus,
            )
            browser_cortex_findings = browser_cortex.review_findings if browser_cortex.browser_signal_count else []
            if browser_cortex.evidence_chain is not None:
                evidence_chains.append(browser_cortex.evidence_chain)
            worker_result = self.worker_coordinator.run_mission_worker(context, event_bus, plan=plan)

            state = state.transition(AgentPhase.ARTIFACT_REVIEWING)
            artifact_findings = self.review_loop.review_worker_result(worker_result)
            control_findings = list(state.review_findings)
            all_findings = [*control_findings, *artifact_findings, *browser_cortex_findings]
            state = state.model_copy(update={"review_findings": all_findings})
            event_bus.append(
                AgentEventType.ARTIFACTS_REVIEWED,
                "Agent reviewed worker artifacts.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.ARTIFACT_REVIEWING,
                payload={"findings": [finding.code for finding in artifact_findings]},
            )

            mission_result = worker_result.mission_result
            if mission_result is not None:
                mission_results.append(mission_result)
            repair_decision = self.repair_loop.decide(
                context,
                state,
                review_findings=all_findings,
                adversarial_findings=hypothesis_result.adversarial_findings,
                objective_scores=action_result.scores,
                effort_route=effort_route,
                event_bus=event_bus,
            )
            repair_decision = self._block_repair_if_action_budget_would_overflow(
                envelope,
                state,
                repair_decision,
                controlled_capability_results,
                mission_result,
                plan_step_count=len(plan.steps),
                event_bus=event_bus,
            )
            state = state.model_copy(update={"repair_decision": repair_decision})
            evidence_chains.append(
                self.evidence_chain_builder.build_repair_decision(
                    context,
                    repair_decision,
                    all_findings,
                    hypothesis_result.adversarial_findings,
                    event_bus=event_bus,
                )
            )
            if repair_decision.decision == RepairDecisionType.ESCALATE:
                state = state.transition(AgentPhase.ESCALATED)
                event_bus.append(
                    AgentEventType.AGENT_ESCALATED,
                    "Agent escalated after bounded repair certification.",
                    phase_before=AgentPhase.ARTIFACT_REVIEWING,
                    phase_after=AgentPhase.ESCALATED,
                    payload={"repair_pressure": repair_decision.repair_pressure},
                    trace_refs=repair_decision.trace_refs,
                )
                self.supervisor.assert_trace_integrity(event_bus)
                return self._apply_final_gate(AgentRunResult(
                    mission_id=envelope.id,
                    final_phase=AgentPhase.ESCALATED,
                    success=False,
                    project_path=mission_result.project_path if mission_result else None,
                    artifacts=mission_result.artifacts if mission_result else [],
                    selected_methods=methods,
                    needed_capabilities=capabilities,
                    missing_capabilities=missing_capabilities,
                    tool_selection_decisions=tool_selection.decisions,
                    selected_tools=tool_selection.selected_tools,
                    candidate_tools=tool_selection.candidate_tools,
                    blocked_tools=tool_selection.blocked_tools,
                    unavailable_capabilities=tool_selection.unavailable_capabilities,
                    hypotheses=hypothesis_result.hypotheses,
                    verified_hypotheses=hypothesis_result.verified_hypotheses,
                    verification_tests=hypothesis_result.verification_tests,
                    adversarial_findings=hypothesis_result.adversarial_findings,
                    cognitive_actions=action_result.actions,
                    world_model_predictions=action_result.predictions,
                    objective_scores=action_result.scores,
                    action_evaluations=action_result.evaluations,
                    selected_action_id=action_result.selected_action_id,
                    selected_action_name=action_result.selected_action_name,
                    controlled_capability_results=controlled_capability_results,
                    effort_route=effort_route,
                    execution_posture=execution_posture,
                    repair_decision=repair_decision,
                    known_facts=state.known_facts,
                    assumptions=state.assumptions,
                    suspected=state.suspected,
                    open_questions=state.open_questions,
                    review_findings=all_findings,
                    evidence_chains=evidence_chains,
                    trace=list(event_bus.events()),
                    runtime_certification=self._certify_trace(event_bus),
                    state_snapshot=self._snapshot_trace(event_bus),
                    mission_result=mission_result,
                    mission_results=mission_results,
                    escalation_reason="Repair pressure exceeded escalation threshold.",
                    active_plan=plan,
                ))
            if repair_decision.decision == RepairDecisionType.REPAIR_ALLOWED:
                state = state.transition(AgentPhase.REPAIRING)
                state = state.model_copy(update={"repair_cycles": state.repair_cycles + 1})
                self.supervisor.assert_state_bounds(state)
                repair_execution_phase_before = state.phase
                state = state.transition(AgentPhase.EXECUTING)
                self._assert_memory_not_authority_boundary(
                    "repairing_to_executing",
                    context,
                    envelope,
                    original_allowed_actions,
                )
                event_bus.append(
                    AgentEventType.REPAIR_EXECUTED,
                    "Agent executed one bounded internal repair pass through the existing mission worker.",
                    phase_before=repair_execution_phase_before,
                    phase_after=AgentPhase.EXECUTING,
                    payload={
                        "repair_decision_id": repair_decision.id,
                        "repair_cycles": state.repair_cycles,
                        "max_repair_cycles": state.max_repair_cycles,
                        "instruction_count": len(repair_decision.instructions),
                    },
                    trace_refs=repair_decision.trace_refs,
                )
                repair_worker_result = self.worker_coordinator.run_mission_worker(context, event_bus, plan=plan)
                state = state.transition(AgentPhase.ARTIFACT_REVIEWING)
                repair_artifact_findings = self.review_loop.review_worker_result(repair_worker_result)
                all_findings = [*control_findings, *repair_artifact_findings]
                state = state.model_copy(update={"review_findings": all_findings})
                event_bus.append(
                    AgentEventType.ARTIFACTS_REVIEWED,
                    "Agent reviewed worker artifacts after bounded repair pass.",
                    phase_before=AgentPhase.EXECUTING,
                    phase_after=AgentPhase.ARTIFACT_REVIEWING,
                    payload={
                        "repair_decision_id": repair_decision.id,
                        "findings": [finding.code for finding in repair_artifact_findings],
                    },
                    trace_refs=repair_decision.trace_refs,
                )
                repair_mission_result = repair_worker_result.mission_result
                if repair_mission_result is not None:
                    mission_results.append(repair_mission_result)
                mission_result = repair_mission_result or mission_result

            success_phase_before = state.phase
            state = state.transition(AgentPhase.SUCCESS_EVALUATING)
            mission_success = bool(mission_result and mission_result.success and not [finding for finding in all_findings if finding.severity == "critical"])
            event_bus.append(
                AgentEventType.SUCCESS_EVALUATED,
                "Agent evaluated mission success.",
                phase_before=success_phase_before,
                phase_after=AgentPhase.SUCCESS_EVALUATING,
                payload={"success": mission_success},
            )
            evidence_chains.append(
                self.evidence_chain_builder.build_success_evaluation(
                    context,
                    mission_success=mission_success,
                    mission_result=mission_result,
                    review_findings=all_findings,
                    repair_decision=repair_decision,
                    event_bus=event_bus,
                )
            )

            state = state.transition(AgentPhase.LEARNING_PROPOSING)
            learning_proposals = self.learning_loop.propose(
                review_findings=all_findings,
                missing_capabilities=[need for need in missing_capabilities if need.required],
                mission_failed=not mission_success,
            )
            self.supervisor.assert_learning_is_safe(learning_proposals)
            event_bus.append(
                AgentEventType.LEARNING_PROPOSED,
                "Agent created safe learning proposals.",
                phase_before=AgentPhase.SUCCESS_EVALUATING,
                phase_after=AgentPhase.LEARNING_PROPOSING,
                payload={"proposal_count": len(learning_proposals)},
            )
            evidence_chains.append(
                self.evidence_chain_builder.build_learning_proposal(
                    context,
                    learning_proposals,
                    all_findings,
                    [need for need in missing_capabilities if need.required],
                    event_bus=event_bus,
                )
            )

            final_phase = AgentPhase.COMPLETED if mission_success else AgentPhase.FAILED
            state = state.transition(final_phase)
            if final_phase == AgentPhase.COMPLETED:
                self.supervisor.assert_completion(state, mission_result)
            event_bus.append(
                AgentEventType.AGENT_COMPLETED if mission_success else AgentEventType.AGENT_FAILED,
                "Agent run finalized.",
                phase_before=AgentPhase.LEARNING_PROPOSING,
                phase_after=final_phase,
                payload={"success": mission_success},
            )
            self.supervisor.assert_trace_integrity(event_bus)

            return self._apply_final_gate(AgentRunResult(
                mission_id=envelope.id,
                final_phase=final_phase,
                success=mission_success,
                project_path=mission_result.project_path if mission_result else None,
                artifacts=mission_result.artifacts if mission_result else [],
                selected_methods=methods,
                needed_capabilities=capabilities,
                missing_capabilities=missing_capabilities,
                tool_selection_decisions=tool_selection.decisions,
                selected_tools=tool_selection.selected_tools,
                candidate_tools=tool_selection.candidate_tools,
                blocked_tools=tool_selection.blocked_tools,
                unavailable_capabilities=tool_selection.unavailable_capabilities,
                hypotheses=hypothesis_result.hypotheses,
                verified_hypotheses=hypothesis_result.verified_hypotheses,
                verification_tests=hypothesis_result.verification_tests,
                adversarial_findings=hypothesis_result.adversarial_findings,
                cognitive_actions=action_result.actions,
                world_model_predictions=action_result.predictions,
                objective_scores=action_result.scores,
                action_evaluations=action_result.evaluations,
                selected_action_id=action_result.selected_action_id,
                selected_action_name=action_result.selected_action_name,
                controlled_capability_results=controlled_capability_results,
                effort_route=effort_route,
                execution_posture=execution_posture,
                repair_decision=repair_decision,
                known_facts=state.known_facts,
                assumptions=state.assumptions,
                suspected=state.suspected,
                open_questions=state.open_questions,
                review_findings=all_findings,
                learning_proposals=learning_proposals,
                evidence_chains=evidence_chains,
                trace=list(event_bus.events()),
                runtime_certification=self._certify_trace(event_bus),
                state_snapshot=self._snapshot_trace(event_bus),
                mission_result=mission_result,
                mission_results=mission_results,
                active_plan=plan,
            ))
        except Exception as exc:
            final_phase = AgentPhase.FAILED
            event_type = AgentEventType.AGENT_FAILED
            if isinstance(exc, MissionRevokedError):
                final_phase = AgentPhase.REVOKED
                event_type = AgentEventType.AGENT_REVOKED
            elif isinstance(exc, (AgentBlockedError, InvariantViolation)):
                final_phase = AgentPhase.BLOCKED
                event_type = AgentEventType.AGENT_BLOCKED
            learning_proposals = []
            if context is not None and can_transition(state.phase, AgentPhase.LEARNING_PROPOSING):
                learning_phase_before = state.phase
                state = state.transition(AgentPhase.LEARNING_PROPOSING)
                learning_proposals = self.learning_loop.propose(
                    review_findings=[],
                    missing_capabilities=[],
                    mission_failed=True,
                )
                self.supervisor.assert_learning_is_safe(learning_proposals)
                event_bus.append(
                    AgentEventType.LEARNING_PROPOSED,
                    "Agent created safe learning proposals after a runtime exception.",
                    phase_before=learning_phase_before,
                    phase_after=AgentPhase.LEARNING_PROPOSING,
                    payload={"proposal_count": len(learning_proposals)},
                )
                evidence_chains.append(
                    self.evidence_chain_builder.build_learning_proposal(
                        context,
                        learning_proposals,
                        [],
                        [],
                        event_bus=event_bus,
                    )
                )
            event_bus.append(
                event_type,
                "Agent run failed before completion.",
                phase_before=state.phase,
                phase_after=final_phase,
                payload={"error": str(exc)},
            )
            self.supervisor.assert_trace_integrity(event_bus)
            # Task 2.4-B: preserve mission_result / mission_results /
            # active_plan on the BLOCKED fallback. The relevant CoreFinalGate
            # checks are:
            #   * ``_mission_result_consistency`` now only rejects the
            #     dangerous inverse (``result.success=True`` while
            #     ``mission_result.success=False``). The legitimate downgrade
            #     where an overall run fails (e.g. a critical review finding
            #     fires post-execution) while the inner mission worker ran
            #     cleanly is explicitly permitted.
            #   * ``_mission_trace_errors_for_result`` still couples the
            #     mission timeline's terminal type to
            #     ``mission_result.success`` — but that is an inner-mission
            #     invariant and is always consistent with the archive we
            #     produced, regardless of the outer ``result.success``.
            #   * ``_mission_results_archive`` only requires that
            #     ``mission_result is None`` implies
            #     ``mission_results == []``.
            # Because the outer run's ``success=False`` no longer forces a
            # matching inner ``mission_result.success``, the fallback can
            # surface the full archive and the reviewed active plan whenever
            # we actually produced them, whether the inner mission succeeded
            # or failed locally.
            fallback_mission_result = mission_result
            fallback_mission_results = list(mission_results)
            fallback_active_plan = plan
            fallback_project_path = mission_result.project_path if mission_result else None
            fallback_artifacts = list(mission_result.artifacts) if mission_result else []
            return self._apply_final_gate(AgentRunResult(
                mission_id=envelope.id,
                final_phase=final_phase,
                success=False,
                review_findings=[],
                learning_proposals=learning_proposals,
                evidence_chains=evidence_chains,
                controlled_capability_results=controlled_capability_results,
                execution_posture=execution_posture,
                trace=list(event_bus.events()),
                runtime_certification=self._certify_trace(event_bus),
                state_snapshot=self._snapshot_trace(event_bus),
                mission_result=fallback_mission_result,
                mission_results=fallback_mission_results,
                project_path=fallback_project_path,
                artifacts=fallback_artifacts,
                active_plan=fallback_active_plan,
                escalation_reason=str(exc),
            ))

    def _execute_controlled_tool_calls(
        self,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        event_bus: EventBus,
        *,
        max_calls: int,
    ) -> list[dict[str, Any]]:
        raw_calls, requested_count = self._raw_tool_call_payloads(user_input, limit=max_calls)
        if requested_count == 0:
            return []
        if max_calls <= 0:
            event = event_bus.append(
                AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
                "Controlled local capability requests skipped because the direct-call budget is exhausted.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "reason": "direct_tool_call_budget_exhausted",
                    "requested_count": requested_count,
                    "max_calls": max_calls,
                },
            )
            return [
                {
                    "accepted": False,
                    "status": "rejected",
                    "reason": "direct_tool_call_budget_exhausted",
                    "requested_count": requested_count,
                    "trace_event_id": event.id,
                }
            ]

        runner = LocalControlledCapabilityRunner(
            registry=self.tool_registry,
            capture_root=self._controlled_capture_root(envelope),
        )
        browser_runner = BrowserControlledCapabilityRunner(
            registry=self.tool_registry,
            capture_root=self._controlled_capture_root(envelope),
            renderer=self.browser_renderer,
            fetcher=self.browser_fetcher,
            interaction_backend=self.browser_interaction_backend,
            resolver=self.browser_resolver,
        )
        results: list[dict[str, Any]] = []
        for raw_call in raw_calls:
            canonicalization = self.tool_call_protocol.canonicalize(
                raw_call,
                event_bus=event_bus,
                phase=AgentPhase.EXECUTING,
            )
            if not canonicalization.accepted or canonicalization.call is None:
                event = event_bus.append(
                    AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
                    "Controlled local capability request rejected because the tool call was not canonical.",
                    phase_before=AgentPhase.EXECUTING,
                    phase_after=AgentPhase.EXECUTING,
                    payload={
                        "reason": "tool_call_not_canonical",
                        "canonicalization_trace_id": canonicalization.trace_event_id,
                        "errors": canonicalization.errors,
                    },
                    trace_refs=[canonicalization.trace_event_id] if canonicalization.trace_event_id else [],
                )
                results.append(
                    {
                        "accepted": False,
                        "status": "rejected",
                        "reason": "tool_call_not_canonical",
                        "errors": canonicalization.errors,
                        "canonicalization_trace_id": canonicalization.trace_event_id,
                        "trace_event_id": event.id,
                    }
                )
                continue

            # Task 8.8 / sentinel-performance-runtime-foundation —
            # Default-off / injection-gated routing. The scheduler
            # path is taken ONLY when BOTH injections are present
            # AND the synchronous call site would have used the
            # local controlled-capability runner (the canonical
            # organ-call surface in this method). Browser routes
            # and browser-runner paths keep their existing
            # synchronous behaviour: those paths run a separate
            # organ chain (operator route or browser controlled
            # runner) whose receipt-stream contract is owned by the
            # browser organ tests; routing them through the
            # scheduler in this wave would change observable
            # behaviour beyond what Task 8.8 authorises. The
            # regression test in
            # ``tests/perf/sched/test_runtime_scheduler_wiring.py``
            # exercises the local-runner path because that is the
            # surface the task spec lists as the integration point.
            #
            # Pre-flight ordering (Acceptance criterion 4 of Task
            # 8.8): authority validation, kill-switch blocking
            # gate, and dry-run pre-flight ALL happen BEFORE
            # ``scheduler.submit``. A blocking kill-switch or denied
            # authority short-circuits the loop iteration with a
            # ``CONTROLLED_CAPABILITY_REJECTED`` event mapped from
            # the scheduler's documented rejection reason set
            # (``kill_switch_blocked``, ``authority_denied``,
            # ``backpressure_rejected``, ``queue_full``). The
            # synchronous runner is NEVER invoked on those paths,
            # so existing safety invariants remain end-to-end.
            scheduler_path_eligible = (
                self._async_organ_scheduler is not None
                and self._backpressure_controller is not None
                and canonicalization.call.action
                not in BrowserControlledCapabilityRunner.SUPPORTED_ACTIONS
            )
            if scheduler_path_eligible:
                routed_result = self._route_local_tool_call_through_scheduler(
                    call=canonicalization.call,
                    envelope=envelope,
                    event_bus=event_bus,
                    runner=runner,
                )
                results.append(routed_result)
                continue

            if canonicalization.call.action in BrowserControlledCapabilityRunner.SUPPORTED_ACTIONS:
                if self.browser_operator_route is not None:
                    if self._latency_profiler is not None:
                        with self._latency_profiler.instrument(
                            mission_id=envelope.id,
                            action_id=f"{envelope.id}:tool_call:{uuid.uuid4().hex[:8]}",
                            action_type="tool_call",
                        ):
                            route_result = self.browser_operator_route.run(
                                canonicalization.call,
                                envelope,
                                event_bus=event_bus,
                                capture_root=self._controlled_capture_root(envelope),
                            )
                    else:
                        route_result = self.browser_operator_route.run(
                            canonicalization.call,
                            envelope,
                            event_bus=event_bus,
                            capture_root=self._controlled_capture_root(envelope),
                        )
                    result = route_result.controlled_result
                    payload = result.model_dump(mode="json")
                    payload["operator_route"] = route_result.model_dump(mode="json", exclude={"controlled_result"})
                    results.append(payload)
                    continue
                if self._latency_profiler is not None:
                    with self._latency_profiler.instrument(
                        mission_id=envelope.id,
                        action_id=f"{envelope.id}:tool_call:{uuid.uuid4().hex[:8]}",
                        action_type="tool_call",
                    ):
                        result = browser_runner.run(canonicalization.call, envelope, event_bus=event_bus)
                else:
                    result = browser_runner.run(canonicalization.call, envelope, event_bus=event_bus)
            else:
                if self._latency_profiler is not None:
                    with self._latency_profiler.instrument(
                        mission_id=envelope.id,
                        action_id=f"{envelope.id}:tool_call:{uuid.uuid4().hex[:8]}",
                        action_type="tool_call",
                    ):
                        result = runner.run(canonicalization.call, envelope, event_bus=event_bus)
                else:
                    result = runner.run(canonicalization.call, envelope, event_bus=event_bus)
            results.append(result.model_dump(mode="json"))
        overflow_count = requested_count - len(raw_calls)
        if overflow_count > 0:
            event = event_bus.append(
                AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
                "Extra controlled local capability requests skipped after exhausting the direct-call budget.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "reason": "direct_tool_call_budget_exhausted",
                    "requested_count": requested_count,
                    "executed_or_evaluated_count": len(raw_calls),
                    "skipped_count": overflow_count,
                },
            )
            results.append(
                {
                    "accepted": False,
                    "status": "rejected",
                    "reason": "direct_tool_call_budget_exhausted",
                    "skipped_count": overflow_count,
                    "trace_event_id": event.id,
                }
            )
        return results

    def _block_repair_if_action_budget_would_overflow(
        self,
        envelope: MissionAuthorityEnvelope,
        state: AgentState,
        repair_decision,
        controlled_capability_results: list[dict[str, Any]],
        mission_result,
        *,
        plan_step_count: int,
        event_bus: EventBus,
    ):
        if repair_decision.decision != RepairDecisionType.REPAIR_ALLOWED:
            return repair_decision

        controlled_executed = self._accepted_controlled_capability_count(controlled_capability_results)
        mission_actions_used = mission_result.state.action_count if mission_result is not None else 0
        projected_total = controlled_executed + mission_actions_used + max(0, plan_step_count)
        if projected_total <= envelope.max_actions:
            return repair_decision

        reasons = [
            *repair_decision.reasons,
            "repair_blocked_by_global_action_budget",
        ]
        event = event_bus.append(
            AgentEventType.REPAIR_DECIDED,
            "Bounded repair was blocked because the projected run action budget would overflow.",
            phase_before=state.phase,
            phase_after=state.phase,
            payload={
                "decision": RepairDecisionType.REPAIR_BLOCKED,
                "repair_pressure": repair_decision.repair_pressure,
                "reasons": reasons,
                "findings_used": repair_decision.findings_used,
                "current_repair_cycles": state.repair_cycles,
                "max_repair_cycles": state.max_repair_cycles,
                "controlled_executed": controlled_executed,
                "mission_actions_used": mission_actions_used,
                "projected_repair_actions": max(0, plan_step_count),
                "projected_total_actions": projected_total,
                "max_actions": envelope.max_actions,
            },
            trace_refs=repair_decision.trace_refs,
        )
        return repair_decision.model_copy(
            update={
                "decision": RepairDecisionType.REPAIR_BLOCKED,
                "reasons": reasons,
                "can_continue": False,
                "instructions": [],
                "trace_refs": [*repair_decision.trace_refs, event.id],
            }
        )

    @staticmethod
    def _accepted_controlled_capability_count(results: list[dict[str, Any]]) -> int:
        return sum(1 for item in results if item.get("accepted") is True)

    @staticmethod
    def _raw_tool_call_payloads(user_input: dict[str, Any], *, limit: int) -> tuple[list[str], int]:
        raw_value = user_input.get("tool_calls", user_input.get("tool_call"))
        if raw_value is None:
            return [], 0
        items = raw_value if isinstance(raw_value, list) else [raw_value]
        requested_count = len(items)
        payloads: list[str] = []
        for item in items[: max(0, limit)]:
            if isinstance(item, str):
                payloads.append(item)
            elif isinstance(item, dict):
                payloads.append(json.dumps(item, sort_keys=True, default=str, separators=(",", ":")))
            else:
                payloads.append(str(item))
        return payloads, requested_count

    def _controlled_capture_root(self, envelope: MissionAuthorityEnvelope) -> Path:
        for allowed_root in envelope.allowed_paths or []:
            normalized = PurePosixPath(str(allowed_root).replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts or "*" in normalized.parts:
                continue
            if normalized.as_posix().rstrip("/") == "data/generated_projects":
                capture_root = (self.project_root / normalized / mission_slug(envelope.mission_title)).resolve()
                capture_root.relative_to(self.project_root)
                return capture_root
        raise ValueError("Controlled local capability capture requires data/generated_projects in mission allowed_paths.")

    def _certify_trace(self, event_bus: EventBus):
        return self.certification_gate.certify(event_bus.events())

    def _snapshot_trace(self, event_bus: EventBus):
        return self.trace_replayer.replay(event_bus.events()).snapshot

    # ------------------------------------------------------------------

    def _route_local_tool_call_through_scheduler(
        self,
        *,
        call: Any,
        envelope: MissionAuthorityEnvelope,
        event_bus: EventBus,
        runner: LocalControlledCapabilityRunner,
    ) -> dict[str, Any]:
        """Route a single local tool call through the async scheduler.

        Pre-flight: builds an ``OrganAuthorityEnvelope``,
        ``OrganKillSwitch``, and ``OrganDryRunReceipt`` from the
        mission envelope. The authority envelope's
        ``execution_authorized=True`` / ``dry_run_only=False`` mirrors
        the synchronous local-runner contract (the runner runs the
        action — it is not a dry-run-only path). The kill-switch is
        non-triggered by default; if the mission has a triggered
        kill-switch in a future wave, it should arrive here from
        ``self._mission_kill_switches[envelope.id]`` (out of scope
        for Task 8.8).

        Returns the same dict shape the synchronous path returns:

        * Success:  ``ControlledCapabilityResult.model_dump(mode="json")``
        * Rejected:
          ``{"accepted": False, "status": "rejected", "reason": ...,
             "trace_event_id": ...}``

        Backpressure or queue-full rejections from the scheduler are
        mapped to ``CONTROLLED_CAPABILITY_REJECTED`` events on the
        agent event bus, matching the existing rejection-receipt
        contract (Acceptance criterion 5: "ack.accepted is False →
        emit rejection-equivalent receipt mapping ack.reason to
        existing event types"). The scheduler's own
        ``KILL_SWITCH_BLOCKED`` / ``AUTHORITY_VIOLATION`` /
        ``PERFORMANCE_RECEIPT_RECORDED`` events are emitted in
        addition, providing the perf-trace audit surface.
        """
        # Late imports — these symbols are only needed on the
        # injection-gated path. Module-level imports would force a
        # cyclic dependency between ``sentinel.agent.runtime`` and
        # ``sentinel.perf.sched.async_organ_scheduler`` (the
        # scheduler imports nothing from the agent layer, but the
        # type-only forward refs above are sufficient for static
        # analysis without paying the import cost on the default
        # path).
        from sentinel.organs.authority import OrganAuthorityEnvelope
        from sentinel.organs.dry_run import OrganDryRunReceipt
        from sentinel.organs.kill_switch import OrganKillSwitch
        from sentinel.perf.sched.tool_call_queue import Priority

        action_id = f"{envelope.id}:tool_call:{uuid.uuid4().hex[:8]}"
        organ_id = f"controlled_local::{call.tool_id}"

        # Build the safety triple the scheduler requires. These are
        # the SAME safety surfaces the synchronous path consults —
        # local controlled-capability runner already runs through
        # ``ToolRegistry.decide`` (policy gate), capture sandbox
        # (path/scope gate), and registry side-effect gate. Adding
        # the scheduler's safety triple is additive: the runner's
        # internal gates remain the authoritative final barrier
        # before any artifact is written.
        authority = OrganAuthorityEnvelope(
            mission_id=envelope.id,
            root_authority_id=envelope.id,
            organ_id=organ_id,
            organ_name=f"controlled_local::{call.tool_id}",
            allowed_actions=list(envelope.allowed_actions),
            allowed_tools=list(envelope.allowed_tools),
            allowed_domains=[],
            allowed_accounts=[],
            allowed_paths=list(envelope.allowed_paths),
            max_actions=envelope.max_actions,
            max_cost_usd=envelope.max_cost_usd,
            execution_authorized=True,
            dry_run_only=False,
        )
        kill_switch = OrganKillSwitch(
            mission_id=envelope.id,
            organ_id=organ_id,
            enabled=True,
            triggered=False,
            execution_allowed=True,
        )
        dry_run = OrganDryRunReceipt(
            mission_id=envelope.id,
            organ_id=organ_id,
            action=call.action,
            reason="agent_runtime_scheduler_wiring",
            preview={"tool_id": call.tool_id, "action": call.action},
            risk_profile_id=f"orisk_{envelope.id}",
            authority_id=authority.id,
            evidence_refs=["ev_agent_runtime_scheduler_wiring"],
        )

        # Holder for the synchronous runner result; populated by the
        # ``organ_runner`` coroutine when the scheduler dequeues and
        # executes it. The scheduler does not propagate runner
        # return values back through ``submit`` (it only emits
        # outcome events + PerformanceReceipt), so we capture the
        # result via closure and read it after the wrapper task
        # completes. ``runner_exception`` carries any exception the
        # synchronous runner raised so the caller can surface it
        # consistently with the synchronous path.
        runner_result: dict[str, Any] = {}

        async def _organ_runner(action: Any) -> None:
            del action  # the scheduler reads no payload bytes
            inner = runner.run(call, envelope, event_bus=event_bus)
            runner_result["payload"] = inner.model_dump(mode="json")

        action_stub = _ToolCallSchedulerAction(
            action_id=action_id,
            mission_id=envelope.id,
            organ_id=organ_id,
            action_type=call.action,
        )

        # Drive scheduler.submit on a fresh event loop. Each tool
        # call is independent and the AgentRuntime call site is
        # synchronous (we MUST NOT change ``_execute_controlled_tool_calls``
        # to async without permission — strict rule). ``asyncio.run``
        # creates a fresh loop, runs ``submit`` + the wrapper task to
        # completion, then closes the loop, which is the documented
        # async-bridge pattern.
        async def _drive() -> SubmissionAck:
            ack = await self._async_organ_scheduler.submit(  # type: ignore[union-attr]
                action_stub,
                authority=authority,
                kill_switch=kill_switch,
                dry_run=dry_run,
                deadline_ms=int(max(1, envelope.max_duration_minutes) * 60 * 1000),
                priority=Priority.NORMAL,
                organ_runner=_organ_runner,
            )
            # Drain any in-flight wrapper task so the runner result
            # is populated and outcome events fire before we read
            # them. If the submission was rejected the scheduler
            # creates no wrapper task, so this gather is a no-op.
            pending = [
                task
                for task in asyncio.all_tasks()
                if task is not asyncio.current_task()
            ]
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            return ack

        ack: SubmissionAck = asyncio.run(_drive())  # type: ignore[assignment]

        if ack.accepted and "payload" in runner_result:
            return runner_result["payload"]

        # Map scheduler rejection reasons to a ``CONTROLLED_CAPABILITY_REJECTED``
        # event so the agent's existing rejection-receipt contract
        # (consumed by ``RuntimeCertificationGate``,
        # downstream verifiers and the trace replayer see the
        # rejection in the canonical shape. The scheduler has
        # already emitted its own typed event
        # (``KILL_SWITCH_BLOCKED`` / ``AUTHORITY_VIOLATION``) plus a
        # ``PerformanceReceipt`` with critical severity; this event
        # is the agent-layer mirror, not a duplicate.
        if not ack.accepted:
            event = event_bus.append(
                AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
                "Controlled local capability rejected by async organ scheduler.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "reason": ack.reason,
                    "scheduler_action_id": ack.action_id,
                    "scheduler_organ_id": ack.organ_id,
                    "tool_id": call.tool_id,
                    "action": call.action,
                },
            )
            return {
                "accepted": False,
                "status": "rejected",
                "reason": ack.reason,
                "tool_id": call.tool_id,
                "action": call.action,
                "scheduler_action_id": ack.action_id,
                "scheduler_organ_id": ack.organ_id,
                "trace_event_id": event.id,
            }

        # Accepted by submit but the wrapper task never ran the
        # synchronous runner to completion (e.g. the wrapper was
        # cancelled mid-flight, or the runner raised). Surface a
        # rejection-equivalent receipt so the trace contract is
        # never silently empty.
        event = event_bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
            "Controlled local capability did not produce a synchronous runner result.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "reason": "scheduler_runner_did_not_complete",
                "scheduler_action_id": ack.action_id,
                "scheduler_organ_id": ack.organ_id,
                "tool_id": call.tool_id,
                "action": call.action,
            },
        )
        return {
            "accepted": False,
            "status": "rejected",
            "reason": "scheduler_runner_did_not_complete",
            "tool_id": call.tool_id,
            "action": call.action,
            "scheduler_action_id": ack.action_id,
            "scheduler_organ_id": ack.organ_id,
            "trace_event_id": event.id,
        }

    def _block_repair_if_action_budget_would_overflow(
        self,
        envelope: MissionAuthorityEnvelope,
        state: AgentState,
        repair_decision,
        controlled_capability_results: list[dict[str, Any]],
        mission_result,
        *,
        plan_step_count: int,
        event_bus: EventBus,
    ):
        if repair_decision.decision != RepairDecisionType.REPAIR_ALLOWED:
            return repair_decision

        controlled_executed = self._accepted_controlled_capability_count(controlled_capability_results)
        mission_actions_used = mission_result.state.action_count if mission_result is not None else 0
        projected_total = controlled_executed + mission_actions_used + max(0, plan_step_count)
        if projected_total <= envelope.max_actions:
            return repair_decision

        reasons = [
            *repair_decision.reasons,
            "repair_blocked_by_global_action_budget",
        ]
        event = event_bus.append(
            AgentEventType.REPAIR_DECIDED,
            "Bounded repair was blocked because the projected run action budget would overflow.",
            phase_before=state.phase,
            phase_after=state.phase,
            payload={
                "decision": RepairDecisionType.REPAIR_BLOCKED,
                "repair_pressure": repair_decision.repair_pressure,
                "reasons": reasons,
                "findings_used": repair_decision.findings_used,
                "current_repair_cycles": state.repair_cycles,
                "max_repair_cycles": state.max_repair_cycles,
                "controlled_executed": controlled_executed,
                "mission_actions_used": mission_actions_used,
                "projected_repair_actions": max(0, plan_step_count),
                "projected_total_actions": projected_total,
                "max_actions": envelope.max_actions,
            },
            trace_refs=repair_decision.trace_refs,
        )
        return repair_decision.model_copy(
            update={
                "decision": RepairDecisionType.REPAIR_BLOCKED,
                "reasons": reasons,
                "can_continue": False,
                "instructions": [],
                "trace_refs": [*repair_decision.trace_refs, event.id],
            }
        )

    @staticmethod
    def _accepted_controlled_capability_count(results: list[dict[str, Any]]) -> int:
        return sum(1 for item in results if item.get("accepted") is True)

    @staticmethod
    def _raw_tool_call_payloads(user_input: dict[str, Any], *, limit: int) -> tuple[list[str], int]:
        raw_value = user_input.get("tool_calls", user_input.get("tool_call"))
        if raw_value is None:
            return [], 0
        items = raw_value if isinstance(raw_value, list) else [raw_value]
        requested_count = len(items)
        payloads: list[str] = []
        for item in items[: max(0, limit)]:
            if isinstance(item, str):
                payloads.append(item)
            elif isinstance(item, dict):
                payloads.append(json.dumps(item, sort_keys=True, default=str, separators=(",", ":")))
            else:
                payloads.append(str(item))
        return payloads, requested_count

    def _controlled_capture_root(self, envelope: MissionAuthorityEnvelope) -> Path:
        for allowed_root in envelope.allowed_paths or []:
            normalized = PurePosixPath(str(allowed_root).replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts or "*" in normalized.parts:
                continue
            if normalized.as_posix().rstrip("/") == "data/generated_projects":
                capture_root = (self.project_root / normalized / mission_slug(envelope.mission_title)).resolve()
                capture_root.relative_to(self.project_root)
                return capture_root
        raise ValueError("Controlled local capability capture requires data/generated_projects in mission allowed_paths.")

    def _certify_trace(self, event_bus: EventBus):
        return self.certification_gate.certify(event_bus.events())

    def _snapshot_trace(self, event_bus: EventBus):
        return self.trace_replayer.replay(event_bus.events()).snapshot

    # ------------------------------------------------------------------
    # Task 6.11 / sentinel-performance-runtime-foundation —
    # decision-core cache wrappers for future LLMDecisionFrame call
    # sites. The cognitive cycle in this codebase does not yet invoke
    # ``LLMDecisionFrame.build`` or ``LLMDecisionFrame.render_prompt_text``
    # directly from :class:`AgentRuntime`, but the spec requires
    # constructor-level injection of the caches and governor here so
    # downstream wiring (e.g. when the LLM-backed decision cycle lands)
    # can adopt the cache surface without changing public signatures
    # again. Each helper preserves the **default-off / bit-identical**
    # contract: when the relevant cache is ``None`` the helper calls
    # the underlying builder/renderer directly and emits no events.

    # ------------------------------------------------------------------

    def _build_decision_frame_cached(
        self,
        *,
        mission_id: str,
        composite_inputs: dict[str, str],
        builder: "Callable[[], LLMDecisionFrame]",
    ) -> "LLMDecisionFrame":
        """Wrap an :class:`LLMDecisionFrame` build with the decision-frame cache.

        Task 6.11 — when ``self._decision_frame_cache is not None``:
        compute the composite hash, attempt
        :meth:`LLMDecisionFrameCache.get`, and on miss fall through to
        ``builder()`` then ``put`` the result. The composite hash is
        derived from the four cache slots
        (``mission_hot_hash``, ``authority_hash``,
        ``evidence_set_hash``, ``tool_surface_hash``) which the caller
        passes in via ``composite_inputs``. Cache hits never expand
        authority — the composite includes ``authority_hash``, so a
        frame built under different authority hashes to a different
        cache entry by construction.

        When the cache is ``None`` the helper calls ``builder()``
        directly with no extra event emissions or method calls — the
        path is bit-identical to a non-injected runtime.
        """

        if self._decision_frame_cache is None:
            return builder()
        composite = self._decision_frame_cache.composite_hash(
            mission_hot_hash=composite_inputs["mission_hot_hash"],
            authority_hash=composite_inputs["authority_hash"],
            evidence_set_hash=composite_inputs["evidence_set_hash"],
            tool_surface_hash=composite_inputs["tool_surface_hash"],
        )
        cached = self._decision_frame_cache.get(composite, mission_id=mission_id)
        if cached is not None:
            return cached
        frame = builder()
        # ``put`` rejects ``frame.authority_expansion=True`` writes
        # with a ``ValueError`` (Requirement 12.2). We propagate that
        # rejection rather than swallowing it — an authority-expanding
        # frame must surface to the caller for the caller's safety
        # gates to handle.
        self._decision_frame_cache.put(composite, frame, mission_id=mission_id)
        return frame

    def _render_prompt_text_cached(
        self,
        frame: "LLMDecisionFrame",
        *,
        mission_id: str,
    ) -> str:
        """Wrap :meth:`LLMDecisionFrame.render_prompt_text` with the prompt cache.

        Task 6.11 — when ``self._prompt_frame_cache is not None``:
        :meth:`PromptFrameCache.get_or_render` is invoked with the
        frame and a ``renderer`` lambda that defers to
        :meth:`LLMDecisionFrame.render_prompt_text`. The cache is
        keyed by :attr:`LLMDecisionFrame.frame_hash`, which carries
        the authority-bearing slice of the frame; cache hits return
        the rendered text the *original* renderer produced for the
        *original* authority-bearing frame.

        When the cache is ``None`` the helper calls
        ``frame.render_prompt_text()`` directly with no extra event
        emissions — bit-identical to a non-injected runtime.
        """

        if self._prompt_frame_cache is None:
            return frame.render_prompt_text()
        return self._prompt_frame_cache.get_or_render(
            frame,
            lambda f: f.render_prompt_text(),
            mission_id=mission_id,
        )

    def _enforce_frame_budget(
        self,
        *,
        mission_id: str,
        builder: "Callable[[], LLMDecisionFrame]",
        frame_budget: int,
    ) -> tuple["LLMDecisionFrame", Any]:
        """Wrap an :class:`LLMDecisionFrame` build with the token-budget governor.

        Task 6.11 — when ``self._token_budget_governor is not None``:
        :meth:`TokenBudgetGovernor.enforce_frame` is invoked with the
        builder, ``self.context_compressor`` (the duck-typed
        compressor protocol the governor expects), and ``frame_budget``.
        The governor invokes ``builder()`` once, estimates the frame's
        token count, and runs up to three
        ``ContextCompressor.compress`` passes if the frame is over
        budget; on rejection it emits ``BUDGET_EXCEEDED`` with
        ``scope='frame'``. The returned tuple is
        ``(frame, BudgetDecision)``.

        When the governor is ``None`` the helper calls ``builder()``
        directly, returns ``(frame, None)``, and emits no events —
        bit-identical to a non-injected runtime.
        """

        if self._token_budget_governor is None:
            return builder(), None
        return self._token_budget_governor.enforce_frame(
            mission_id,
            builder,
            self.context_compressor,
            frame_budget,
        )

    def _apply_final_gate(self, result: AgentRunResult) -> AgentRunResult:
        """Evaluate CoreFinalGate on the terminal result before returning it.

        Task 1.2 / Task 1.3 / Requirement 1 (FinalGate Runtime Integration,
        finding F-A3.11).

        Guarantees no ``AgentRunResult`` can escape ``AgentRuntime.run``
        without passing terminal safety certification. The returned result
        ALWAYS carries a ``CoreFinalGateResult`` on
        ``final_gate_certification`` whose ``accepted`` flag is ``True``.

        Diagnostic vs certification distinction
        ---------------------------------------
        * ``final_gate_certification`` is the certification of the result
          that is **actually returned** to the caller. It therefore always
          represents an *accepted* gate evaluation — never the verdict of a
          rejected intended result.
        * When the intended result fails the gate, the rejection details
          are surfaced via ``escalation_reason`` (carrying the failed check
          names) on a downgraded ``AgentPhase.BLOCKED`` result, which is
          then re-certified so that the returned result's
          ``final_gate_certification.accepted`` is ``True``.

        If the downgraded ``BLOCKED`` result itself fails re-certification,
        that is a deep invariant failure: the runtime cannot manufacture a
        safe result, so ``AgentBlockedError`` is raised with both sets of
        failed check names rather than silently returning an uncertified
        result.

        Invariant preserved
        -------------------
            ∀ result returned by AgentRuntime.run:
                result.final_gate_certification is not None
                and result.final_gate_certification.accepted is True
        """
        gate_result = self._final_gate.evaluate(
            result,
            allowed_project_root=str(self.project_root),
        )
        if gate_result.accepted:
            return result.model_copy(
                update={"final_gate_certification": gate_result}
            )

        failed_check_names = [
            check.name for check in gate_result.checks if not check.passed
        ]
        blocked_reason = (
            "final_gate_rejected:" + ",".join(failed_check_names)
            if failed_check_names
            else "final_gate_rejected"
        )
        blocked_result = result.model_copy(
            update={
                "final_phase": AgentPhase.BLOCKED,
                "success": False,
                "escalation_reason": blocked_reason,
            }
        )
        blocked_gate_result = self._final_gate.evaluate(
            blocked_result,
            allowed_project_root=str(self.project_root),
        )
        if not blocked_gate_result.accepted:
            blocked_failed_check_names = [
                check.name
                for check in blocked_gate_result.checks
                if not check.passed
            ]
            raise AgentBlockedError(
                "CoreFinalGate rejected the intended result and the "
                "downgraded BLOCKED result also failed re-certification; "
                "refusing to return an uncertified AgentRunResult. "
                f"Intended-result failed checks: {failed_check_names}. "
                f"BLOCKED re-certification failed checks: "
                f"{blocked_failed_check_names}."
            )
        return blocked_result.model_copy(
            update={"final_gate_certification": blocked_gate_result}
        )
