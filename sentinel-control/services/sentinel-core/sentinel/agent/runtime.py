from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any
from collections.abc import Callable

from pydantic import ConfigDict

from sentinel.shared.models import SentinelModel

from sentinel.agent.audit import RuntimeCertificationGate
from sentinel.agent.brain.cognition_loop import BrainCognitionInput, BrainCognitionLoop, BrainCognitionResult
from sentinel.agent.browser import (
    BrowserControlledCapabilityRunner,
    BrowserEvidenceInterpreter,
    BrowserFetcher,
    BrowserInteractionBackend,
    BrowserOperatorRouteProtocol,
    BrowserRenderer,
    DnsResolver,
)
from sentinel.agent.browser.neural import motor_proposal_artifact_to_browser_step_candidate
from sentinel.agent.capability_selector import CapabilitySelector
from sentinel.agent.cognitive_cycle import CognitiveCycle
from sentinel.agent.controlled_capability import LocalControlledCapabilityRunner
from sentinel.agent.context_builder import ContextBuilder
from sentinel.agent.context_compressor import ContextCompressor
from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.agent.event_bus import EventBus
from sentinel.agent.effort_router import EffortRouter
from sentinel.agent.events import AgentEventType
from sentinel.agent.evidence import EvidenceChainBuilder
from sentinel.agent.evidence_ranker import EvidenceCard, sanitize_context_payload, sanitize_context_text
from sentinel.agent.exceptions import AgentBlockedError, MissionRevokedError
from sentinel.agent.execution_posture import ExecutionPosturePolicy
from sentinel.agent.final_gate import CoreFinalGate
from sentinel.agent.hypothesis import HypothesisVerifier
from sentinel.agent.identity import AgentIdentity, default_agent_identity
from sentinel.agent.invariants import InvariantViolation
from sentinel.agent.learning_loop import LearningLoop
from sentinel.agent.method_selector import MethodSelector
from sentinel.agent.model_execution import (
    ModelExecutionBudgetPolicy,
    ModelExecutionCoordinator,
    ModelExecutionOutcome,
    ModelExecutionOutcomeClass,
    ModelRetryPolicy,
    ModelTimeoutPolicy,
    RealModelRequestBuilder,
)
from sentinel.agent.models import AgentContext, AgentRunResult
from sentinel.agent.llm.memory_bridge import MemoryBridgeInput, MemoryBridgeResult, RoleLoopMemoryBridge
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.memory.integration import PersistentMemoryIngestAdapter
from sentinel.agent.organs.organ_dispatch import (
    OrganDispatcher,
    OrganDispatchResult,
    OrganDispatchStatus,
)
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionResult,
    execute_organ_runtime_request,
)
from sentinel.agent.phases import AgentPhase, can_transition
from sentinel.agent.planner_bridge import PlannerBridge
from sentinel.agent.prompt_budget import PromptBudgetAllocator
from sentinel.agent.repair_loop import CognitiveRepairLoop, RepairDecisionType
from sentinel.agent.replay import AgentTraceReplayer
from sentinel.agent.review_loop import ReviewLoop
from sentinel.agent.state import AgentState
from sentinel.agent.supervisor import Supervisor
from sentinel.agent.token_ledger import estimate_tokens
from sentinel.agent.tool_call_protocol import ToolCallProtocol
from sentinel.agent.tool_selector import ToolSelector
from sentinel.agent.worker_coordinator import WorkerCoordinator
from sentinel.agent.world_model import ActionEvaluator
from sentinel.capabilities import ToolRegistry, default_tool_registry
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.mission.runner import MissionRunner
from sentinel.mission.safe_executors import mission_slug
from sentinel.perf.caches import (
    CacheKeySanitizerRejection,
    ContextCacheKeyBuilder,
    MissingCacheKeyComponent,
    OrganStateEntry,
    OrganStateView,
)


if TYPE_CHECKING:
    from sentinel.agent.model_contract import UserModelContract
    from sentinel.perf.caches.context_build_cache import ContextBuildCache
    from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache
    from sentinel.perf.caches.model_call_optimizer import ModelCallOptimizer
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


class _DecisionFrameBudgetCompressor:
    """Adapter that lets TokenBudgetGovernor reject oversized frames safely."""

    def __init__(self, fallback: ContextCompressor) -> None:
        self._fallback = fallback

    def compress(self, frame: Any) -> Any:
        if isinstance(frame, LLMDecisionFrame):
            return frame
        return self._fallback.compress(frame)


def _temporary_dispatch_rejected_paths(payload: Any, path: str = "$") -> list[str]:
    rejected: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            child_path = f"{path}.{key}"
            if normalized in _TEMPORARY_DISPATCH_FORBIDDEN_KEYS and value not in (None, False, "", [], {}):
                rejected.append(child_path)
                continue
            rejected.extend(_temporary_dispatch_rejected_paths(value, child_path))
        return rejected
    if isinstance(payload, list | tuple | set):
        for index, value in enumerate(payload):
            rejected.extend(_temporary_dispatch_rejected_paths(value, f"{path}[{index}]"))
        return rejected
    if isinstance(payload, str):
        lowered = payload.lower()
        if any(marker in lowered for marker in _TEMPORARY_DISPATCH_FORBIDDEN_TEXT):
            rejected.append(path)
    return rejected


_TEMPORARY_DISPATCH_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "bearer",
    "chain_of_thought",
    "credential",
    "hidden_tool_payload",
    "password",
    "provider_response",
    "raw_organ_payload",
    "raw_prompt",
    "prompt",
    "raw_response",
    "reasoning",
    "secret",
    "thinking",
    "token",
    "tool_calls",
}

_TEMPORARY_DISPATCH_FORBIDDEN_TEXT = {
    "bearer ",
    "chain_of_thought",
    "hidden_tool_payload",
    "raw_prompt",
    "raw_response",
    "reasoning:",
    "secret",
}


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
        user_model_contract: UserModelContract | None = None,
        model_call_optimizer: ModelCallOptimizer | None = None,
        model_execution_coordinator: ModelExecutionCoordinator | None = None,
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
        organ_execution_config: OrganRuntimeExecutionConfig | None = None,
        organ_dispatcher: OrganDispatcher | None = None,
        brain_cognition_loop: BrainCognitionLoop | None = None,
        memory_bridge: RoleLoopMemoryBridge | None = None,
        persistent_memory_ingest_adapter: PersistentMemoryIngestAdapter | None = None,
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
        self._user_model_contract = user_model_contract
        self._model_call_optimizer = model_call_optimizer
        self._model_execution_coordinator = model_execution_coordinator
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
        self._organ_execution_config = organ_execution_config or OrganRuntimeExecutionConfig()
        self._organ_dispatcher = organ_dispatcher
        self._brain_cognition_loop = brain_cognition_loop
        self._memory_bridge = memory_bridge or RoleLoopMemoryBridge()
        self._persistent_memory_ingest_adapter = persistent_memory_ingest_adapter
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

    def execute_organ_runtime_request(
        self,
        request: OrganRuntimeExecutionRequest | dict[str, Any],
    ) -> OrganRuntimeExecutionResult:
        """Execute explicitly opted-in low-risk/perception organ requests only.

        This method is intentionally separate from :meth:`run`. Without an
        injected ``OrganRuntimeExecutionConfig`` that enables
        ``l2_l3_local_only`` or ``browser_readonly_preparation_only``, it
        returns a safe blocked result and never calls an organ.
        """

        return execute_organ_runtime_request(
            request,
            config=self._organ_execution_config,
            browser_readonly_fetcher=self.browser_fetcher,
        )

    def _organ_dispatch_should_run(self) -> bool:
        return bool(
            self._organ_execution_config.enabled
            and self._organ_execution_config.organ_dispatch_enabled
        )

    def _brain_native_should_run(self) -> bool:
        return bool(
            self._organ_dispatch_should_run()
            and self._organ_execution_config.brain_native_candidate_source_enabled
        )

    def _dispatch_organs_from_runtime(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        evidence_refs: list[str],
        brain_cognition_result: BrainCognitionResult | None = None,
    ) -> OrganDispatchResult:
        dispatch_inputs = self._organ_dispatch_inputs_from_user_input(
            user_input=user_input,
            evidence_refs=evidence_refs,
            brain_cognition_result=brain_cognition_result,
        )
        dispatcher = self._organ_dispatcher or OrganDispatcher()
        return dispatcher.dispatch(
            mission_id=envelope.id,
            action_candidates=dispatch_inputs["action_candidates"],
            proposal_artifacts=dispatch_inputs["proposal_artifacts"],
            config=self._organ_execution_config,
            authority=dispatch_inputs["authority"],
            authority_envelope=envelope,
            budget=dispatch_inputs["budget"],
            available_evidence_refs=dispatch_inputs["available_evidence_refs"],
            organ_contracts=dispatch_inputs["organ_contracts"],
            browser_readonly_fetcher=self.browser_fetcher,
        )

    def _organ_dispatch_inputs_from_user_input(
        self,
        *,
        user_input: dict[str, Any],
        evidence_refs: list[str],
        brain_cognition_result: BrainCognitionResult | None = None,
    ) -> dict[str, Any]:
        dispatch_block = user_input.get("organ_dispatch")
        if not isinstance(dispatch_block, dict):
            dispatch_block = {}
        brain_proposals = self._proposal_artifacts_from_brain_result(brain_cognition_result)
        if brain_proposals:
            action_candidates = brain_proposals
            proposal_artifacts = brain_proposals
        elif self._organ_execution_config.temporary_candidate_bridge_enabled:
            # TEMPORARY: this bridge exists only until BrainCognitionLoop is
            # fully owns candidate generation in all call sites. It accepts
            # explicit structured candidates only; it never parses free text.
            action_candidates = self._extract_temporary_organ_candidates_from_user_input(dispatch_block)
            proposal_artifacts = [
                item for item in dispatch_block.get("proposal_artifacts", [])
                if isinstance(item, dict)
            ]
        else:
            action_candidates = []
            proposal_artifacts = []
        authority = dispatch_block.get("authority") if isinstance(dispatch_block.get("authority"), dict) else {}
        budget = dispatch_block.get("budget") if isinstance(dispatch_block.get("budget"), dict) else {}
        available = dispatch_block.get("available_evidence_refs")
        organ_contracts = dispatch_block.get("organ_contracts")
        return {
            "action_candidates": action_candidates,
            "proposal_artifacts": proposal_artifacts,
            "authority": authority,
            "budget": budget,
            "available_evidence_refs": [str(ref) for ref in available] if isinstance(available, list) else list(evidence_refs),
            "organ_contracts": organ_contracts if isinstance(organ_contracts, dict) else {},
        }

    def _proposal_artifacts_from_brain_result(self, brain_result: Any) -> list[dict[str, Any]]:
        if brain_result is None:
            return []
        proposals = getattr(brain_result, "proposal_artifacts", None)
        if proposals is None and isinstance(brain_result, dict):
            proposals = brain_result.get("proposal_artifacts")
        if not isinstance(proposals, list):
            return []
        safety = getattr(brain_result, "safety_validation", None)
        if safety is not None and getattr(safety, "valid", True) is not True:
            return []
        extracted: list[dict[str, Any]] = []
        for item in proposals:
            if not isinstance(item, dict):
                continue
            if item.get("artifact_kind"):
                extracted.append(sanitize_context_payload(self._normalize_browser_neural_refs_in_proposal(item)))
                continue
            if item.get("proposal_artifact_id") and item.get("dispatch_required") is True:
                if not self._organ_execution_config.browser_neural_motor_proposal_source_enabled:
                    continue
                converted = motor_proposal_artifact_to_browser_step_candidate(item)
                if converted is not None:
                    extracted.append(sanitize_context_payload(self._normalize_browser_neural_refs_in_proposal(converted)))
        return extracted

    def _run_native_brain_cognition(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
    ) -> tuple[BrainCognitionResult | None, str]:
        dispatch_block = user_input.get("organ_dispatch")
        if not isinstance(dispatch_block, dict):
            dispatch_block = {}
        raw_input = dispatch_block.get("brain_cognition_input") or user_input.get("brain_cognition_input")
        if raw_input is None:
            return None, "PREPARED"
        mission_id = getattr(raw_input, "mission_id", None)
        if isinstance(raw_input, dict):
            mission_id = raw_input.get("mission_id")
        if mission_id != envelope.id:
            return None, "PARTIAL"
        requested_memory_owner = getattr(raw_input, "persistent_memory_owner_user_id", None)
        if isinstance(raw_input, dict):
            requested_memory_owner = raw_input.get("persistent_memory_owner_user_id")
        if requested_memory_owner not in (None, envelope.user_id):
            return None, "PARTIAL"
        if isinstance(raw_input, dict):
            raw_input = {**raw_input, "persistent_memory_owner_user_id": envelope.user_id}
        else:
            raw_input = raw_input.model_copy(
                update={"persistent_memory_owner_user_id": envelope.user_id}
            )

        brain_loop = self._brain_cognition_loop or BrainCognitionLoop()
        result = self._sanitize_brain_cognition_result_for_runtime(brain_loop.run(raw_input))
        if self._proposal_artifacts_from_brain_result(result):
            return result, "CLOSED"
        return result, "PARTIAL"

    @classmethod
    def _sanitize_brain_cognition_result_for_runtime(cls, result: BrainCognitionResult) -> BrainCognitionResult:
        proposals: list[dict[str, Any]] = []
        changed = False
        for proposal in result.proposal_artifacts:
            if not isinstance(proposal, dict):
                proposals.append(proposal)
                continue
            normalized = cls._normalize_browser_neural_refs_in_proposal(proposal)
            changed = changed or normalized != proposal
            proposals.append(normalized)
        return result.model_copy(update={"proposal_artifacts": proposals}) if changed else result

    def _write_memory_feedback_from_dispatch(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        brain_cognition_result: BrainCognitionResult | None,
        organ_dispatch_result: OrganDispatchResult,
    ) -> tuple[MemoryBridgeResult | None, str, list[str], str | None, str]:
        if not self._organ_execution_config.memory_feedback_enabled:
            return None, "PREPARED", [], None, "NOT_STARTED"

        loop_id = f"organ_dispatch_{organ_dispatch_result.trace.input_hash[:16]}"
        bridge_input = MemoryBridgeInput(
            mission_id=envelope.id,
            loop_id=loop_id,
            memory_items=self._memory_items_from_brain_and_dispatch(
                envelope=envelope,
                brain_cognition_result=brain_cognition_result,
                organ_dispatch_result=organ_dispatch_result,
            ),
            proposal_receipts=self._proposal_receipts_from_brain(brain_cognition_result),
            final_packet=self._memory_final_packet(organ_dispatch_result),
            budget_summaries=self._budget_summaries_from_dispatch(organ_dispatch_result),
            risk_flags=self._risk_flags_from_brain_and_dispatch(brain_cognition_result, organ_dispatch_result),
            unresolved_objections=list(getattr(brain_cognition_result, "unresolved_objections", []) or []),
            missing_evidence=list(getattr(brain_cognition_result, "missing_evidence", []) or []),
            blocked_intents=[
                f"candidate_blocked_{item.status.value}"
                for item in organ_dispatch_result.candidate_results
                if item.execution_result is None
            ],
        )
        result = self._memory_bridge.build(bridge_input)
        refs = [
            *[entry.memory_id for entry in result.memory_entries],
            *[signal.signal_id for signal in result.feedback_signals],
        ]
        memory_snapshot_ref = result.snapshot.loop_id if result.snapshot is not None else None
        if memory_snapshot_ref:
            refs.append(f"snapshot:{memory_snapshot_ref}")
        durable_status = "NOT_STARTED"
        if self._persistent_memory_ingest_adapter is not None:
            try:
                durable_result = self._persistent_memory_ingest_adapter.persist_bridge_result(
                    result,
                    requester_user_id=envelope.user_id,
                )
                refs.extend(
                    f"persistent:{record_id}" for record_id in durable_result.accepted_record_ids
                )
                durable_status = (
                    "CLOSED"
                    if durable_result.accepted_record_ids
                    and not durable_result.rejected_source_memory_ids
                    else "PARTIAL"
                )
            except Exception:
                durable_status = "FAILED_SAFE"
        return result, "CLOSED", refs, memory_snapshot_ref, durable_status

    def _memory_items_from_brain_and_dispatch(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        brain_cognition_result: BrainCognitionResult | None,
        organ_dispatch_result: OrganDispatchResult,
    ) -> list[dict[str, Any]]:
        validity_scope = f"{envelope.id}:organ_runtime"
        items: list[dict[str, Any]] = []
        for proposal in getattr(brain_cognition_result, "proposal_artifacts", []) or []:
            if not isinstance(proposal, dict):
                continue
            proposal_id = str(proposal.get("proposal_id") or proposal.get("proposal_artifact_id") or proposal.get("id") or stable_hash(proposal)[:16])
            neural_signal_refs = self._browser_neural_signal_refs_from_proposal(proposal)
            evidence_refs = [
                *[str(ref) for ref in proposal.get("evidence_refs", [])],
                *[str(ref) for ref in proposal.get("source_evidence_refs", [])],
            ]
            safe_summary = str(proposal.get("safe_summary") or "Brain proposal artifact observed as data.")
            if neural_signal_refs:
                safe_summary = f"{safe_summary} browser_neural_signal_refs={','.join(neural_signal_refs)}"
            items.append(
                {
                    "source_class": "proposal_artifact",
                    "source_id": proposal_id,
                    "source_lineage_id": stable_hash(sanitize_context_payload(proposal)),
                    "claim_status": "OBSERVED",
                    "confidence": 0.5,
                    "variance": 0.5,
                    "validity_scope": validity_scope,
                    "evidence_refs": sorted(set(evidence_refs)),
                    "receipt_refs": [str(ref) for ref in proposal.get("receipt_refs", [])],
                    "safe_summary": safe_summary,
                }
            )

        for candidate in organ_dispatch_result.candidate_results:
            evidence_refs = self._candidate_evidence_refs(candidate)
            receipt_refs = self._candidate_receipt_refs(candidate)
            if candidate.gate_decision is not None:
                items.append(
                    {
                        "source_class": "gate_result",
                        "source_id": f"gate_{candidate.candidate_id}",
                        "source_lineage_id": stable_hash(
                            {
                                "candidate_id": candidate.candidate_id,
                                "gate_decision": candidate.gate_decision.value,
                                "lane_id": candidate.lane_id,
                            }
                        ),
                        "claim_status": "OBSERVED",
                        "confidence": 0.7,
                        "variance": 0.3,
                        "validity_scope": validity_scope,
                        "evidence_refs": evidence_refs,
                        "receipt_refs": receipt_refs,
                        "safe_summary": f"DelegatedActionGate recorded decision {candidate.gate_decision.value} for candidate {candidate.candidate_id}.",
                    }
                )
            execution = candidate.execution_result
            if execution is None:
                continue
            receipt = execution.receipt
            if receipt is not None:
                receipt_id = self._object_ref(receipt, "receipt_id", "id") or f"receipt_{candidate.candidate_id}"
                items.append(
                    {
                        "source_class": "receipt",
                        "source_id": receipt_id,
                        "source_lineage_id": self._object_ref(receipt, "receipt_hash", "event_hash") or receipt_id,
                        "claim_status": "OBSERVED",
                        "confidence": 0.72,
                        "variance": 0.28,
                        "validity_scope": validity_scope,
                        "evidence_refs": evidence_refs,
                        "receipt_refs": [receipt_id],
                        "safe_summary": f"Organ receipt {receipt_id} recorded for {execution.organ_kind}.",
                    }
                )
            certificate = execution.finalgate_certificate
            if certificate is not None:
                certificate_id = self._object_ref(certificate, "certificate_id", "id") or f"certificate_{candidate.candidate_id}"
                items.append(
                    {
                        "source_class": "finalgate_result",
                        "source_id": certificate_id,
                        "source_lineage_id": self._object_ref(certificate, "certificate_hash", "input_hash") or certificate_id,
                        "claim_status": "OBSERVED",
                        "confidence": 0.74,
                        "variance": 0.26,
                        "validity_scope": validity_scope,
                        "evidence_refs": evidence_refs,
                        "receipt_refs": receipt_refs,
                        "safe_summary": f"FinalGate certificate {certificate_id} recorded for {execution.organ_kind}.",
                    }
                )
        return items

    @staticmethod
    def _proposal_receipts_from_brain(brain_cognition_result: BrainCognitionResult | None) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for proposal in getattr(brain_cognition_result, "proposal_artifacts", []) or []:
            if isinstance(proposal, dict):
                receipts.append(
                    {
                        "proposal_id": str(proposal.get("proposal_id") or proposal.get("proposal_artifact_id") or stable_hash(proposal)[:16]),
                        "proposal_hash": stable_hash(sanitize_context_payload(proposal)),
                        "receipt_refs": [str(ref) for ref in proposal.get("receipt_refs", [])],
                        "evidence_refs": [
                            *[str(ref) for ref in proposal.get("evidence_refs", [])],
                            *[str(ref) for ref in proposal.get("source_evidence_refs", [])],
                        ],
                        "browser_neural_signal_refs": AgentRuntime._browser_neural_signal_refs_from_proposal(proposal),
                        "safe_summary": str(proposal.get("safe_summary") or "Proposal artifact observed."),
                    }
                )
        return receipts

    @staticmethod
    def _memory_final_packet(organ_dispatch_result: OrganDispatchResult) -> dict[str, Any]:
        return {
            "source": "organ_dispatch_result",
            "organ_dispatch_status": organ_dispatch_result.status.value,
            "candidate_count": len(organ_dispatch_result.candidate_results),
            "executed_count": organ_dispatch_result.trace.executed_count,
            "gate_rejected_count": organ_dispatch_result.trace.gate_rejected_count,
            "input_hash": organ_dispatch_result.trace.input_hash,
            "safe_summary": organ_dispatch_result.safe_summary,
        }

    @staticmethod
    def _budget_summaries_from_dispatch(organ_dispatch_result: OrganDispatchResult) -> list[dict[str, Any]]:
        return [
            {
                "decision": "within_budget",
                "compliant": True,
                "candidate_count": len(organ_dispatch_result.candidate_results),
                "executed_count": organ_dispatch_result.trace.executed_count,
            }
        ]

    @staticmethod
    def _risk_flags_from_brain_and_dispatch(
        brain_cognition_result: BrainCognitionResult | None,
        organ_dispatch_result: OrganDispatchResult,
    ) -> list[str]:
        flags = [str(flag) for flag in getattr(brain_cognition_result, "risk_flags", []) or []]
        if organ_dispatch_result.trace.gate_rejected_count:
            flags.append("gate_rejection_recorded")
        if organ_dispatch_result.trace.execution_failed_count:
            flags.append("execution_failure_recorded")
        return flags

    @staticmethod
    def _candidate_receipt_refs(candidate: Any) -> list[str]:
        execution = getattr(candidate, "execution_result", None)
        refs: list[str] = []
        if execution is None:
            return refs
        receipt_id = AgentRuntime._object_ref(getattr(execution, "receipt", None), "receipt_id", "id")
        certificate_id = AgentRuntime._object_ref(getattr(execution, "finalgate_certificate", None), "certificate_id", "id")
        for ref in (receipt_id, certificate_id):
            if ref:
                refs.append(ref)
        return refs

    @staticmethod
    def _candidate_evidence_refs(candidate: Any) -> list[str]:
        execution = getattr(candidate, "execution_result", None)
        receipt = getattr(execution, "receipt", None) if execution is not None else None
        refs = getattr(receipt, "evidence_refs", None)
        if isinstance(refs, list):
            return [str(ref) for ref in refs]
        return []

    @staticmethod
    def _object_ref(obj: Any, *names: str) -> str | None:
        if obj is None:
            return None
        for name in names:
            value = getattr(obj, name, None)
            if value:
                return str(value)
            if isinstance(obj, dict) and obj.get(name):
                return str(obj[name])
        return None

    def _build_replan_packet(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        brain_cognition_result: BrainCognitionResult | None,
        organ_dispatch_result: OrganDispatchResult,
        memory_feedback_result: MemoryBridgeResult | None,
        memory_feedback_refs: list[str],
        memory_feedback_path: str,
    ) -> dict[str, Any]:
        receipt_refs = [
            ref
            for candidate in organ_dispatch_result.candidate_results
            for ref in self._candidate_receipt_refs(candidate)
            if ref
        ]
        finalgate_refs = [
            self._object_ref(
                getattr(getattr(candidate, "execution_result", None), "finalgate_certificate", None),
                "certificate_id",
            )
            for candidate in organ_dispatch_result.candidate_results
        ]
        finalgate_refs = [ref for ref in finalgate_refs if ref]
        proposals = getattr(brain_cognition_result, "proposal_artifacts", []) or []
        proposal_refs = [
            str(proposal.get("proposal_id") or proposal.get("proposal_artifact_id") or stable_hash(sanitize_context_payload(proposal))[:16])
            for proposal in proposals
            if isinstance(proposal, dict)
        ]
        browser_neural_signal_refs = sorted(
            {
                ref
                for proposal in proposals
                if isinstance(proposal, dict)
                for ref in self._browser_neural_signal_refs_from_proposal(proposal)
            }
        )
        browser_neural_motor_proposal_refs = sorted(
            {
                str(proposal.get("proposal_artifact_id") or proposal.get("source_motor_proposal_id"))
                for proposal in proposals
                if isinstance(proposal, dict) and (proposal.get("proposal_artifact_id") or proposal.get("source_motor_proposal_id"))
            }
        )
        brain_ref = None
        if brain_cognition_result is not None:
            brain_ref = stable_hash(
                {
                    "mission_id": brain_cognition_result.mission_id,
                    "status": brain_cognition_result.status.value,
                    "proposal_count": len(brain_cognition_result.proposal_artifacts),
                }
            )
        return {
            "status": "CLOSED" if memory_feedback_result is not None else "PREPARED",
            "mission_id": envelope.id,
            "source": "brain_native_organ_dispatch_memory_feedback",
            "brain_result_ref": brain_ref,
            "proposal_artifact_refs": proposal_refs,
            "browser_neural_signal_refs": browser_neural_signal_refs,
            "browser_neural_motor_proposal_refs": browser_neural_motor_proposal_refs,
            "organ_dispatch_status": organ_dispatch_result.status.value,
            "organ_dispatch_result_ref": organ_dispatch_result.trace.input_hash,
            "receipt_refs": receipt_refs,
            "finalgate_certificate_refs": finalgate_refs,
            "memory_feedback_path": memory_feedback_path,
            "memory_feedback_refs": list(memory_feedback_refs),
            "memory_snapshot_ref": memory_feedback_result.snapshot.loop_id if memory_feedback_result else None,
            "unresolved_objections": list(getattr(brain_cognition_result, "unresolved_objections", []) or []),
            "missing_evidence": list(getattr(brain_cognition_result, "missing_evidence", []) or []),
            "safe_next_step": getattr(brain_cognition_result, "safe_next_step_recommendation", None),
            "recommended_next_loop_input": {
                "mission_id": envelope.id,
                "source_replan_packet": "brain_native_candidate_source_and_memory_feedback_lock",
                "use_memory_feedback_refs": list(memory_feedback_refs),
                "use_browser_neural_signal_refs": browser_neural_signal_refs,
                "automatic_replan_executed": False,
            },
            "automatic_replan_executed": False,
        }

    @staticmethod
    def _browser_neural_signal_refs_from_proposal(proposal: dict[str, Any]) -> list[str]:
        refs: list[str] = []
        for key in ("source_signal_refs", "browser_neural_signal_refs", "neural_signal_refs"):
            value = proposal.get(key)
            if isinstance(value, list):
                refs.extend(AgentRuntime._safe_browser_neural_signal_ref(str(ref)) for ref in value)
        return sorted(set(refs))

    @classmethod
    def _normalize_browser_neural_refs_in_proposal(cls, proposal: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(proposal)
        for key in ("source_signal_refs", "browser_neural_signal_refs", "neural_signal_refs"):
            value = normalized.get(key)
            if isinstance(value, list):
                normalized[key] = [cls._safe_browser_neural_signal_ref(str(ref)) for ref in value]
        return normalized

    @staticmethod
    def _safe_browser_neural_signal_ref(ref: str) -> str:
        allowed = ref.startswith("nsig_") and 5 <= len(ref) <= 128 and all(
            char.isalnum() or char in {"_", "-"} for char in ref
        )
        if allowed:
            return ref
        return f"nsig_ref_hash_{stable_hash(ref)[:32]}"

    @staticmethod
    def _extract_temporary_organ_candidates_from_user_input(dispatch_block: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = dispatch_block.get("action_candidates")
        if candidates is None:
            candidates = dispatch_block.get("organ_action_candidates")
        if not isinstance(candidates, list):
            return []
        safe_candidates: list[dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if _temporary_dispatch_rejected_paths(candidate):
                continue
            safe_candidates.append(sanitize_context_payload(candidate))
        return safe_candidates

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
        context_cache_key = None
        llm_decision_cycle = None
        brain_cognition_result: BrainCognitionResult | None = None
        brain_candidate_source_status = "NOT_STARTED"
        organ_dispatch_result: OrganDispatchResult | None = None
        memory_feedback_result: MemoryBridgeResult | None = None
        memory_feedback_path = "NOT_STARTED"
        memory_feedback_refs: list[str] = []
        memory_snapshot_ref: str | None = None
        durable_memory_persistence = "NOT_STARTED"
        replan_ready = False
        replan_packet: dict[str, Any] | None = None
        automatic_replan_executed = False
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

                # sentinel-context-cache-runtime-closure / Task 3.2 —
                # replace the temporary envelope.id stand-in with the
                # canonical four-component ContextCacheKey. AgentRuntime
                # owns the derivation: ContextBuilder.build is wrapped
                # externally via ContextBuildCache.get_or_build. The
                # draft_context below is a pre-build AgentContext
                # snapshot constructed from the inputs already available
                # at CONTEXT_BUILDING (envelope, user_input,
                # evidence_refs, memory_items); it is NOT the post-build
                # context — that would require calling
                # ContextBuilder.build twice. mission_hot_hash reads
                # only envelope-side fields plus context.constraints /
                # evidence_refs / blockers, so the empty defaults on
                # draft_context produce a deterministic key for
                # identical inputs.
                #
                # original_allowed_actions is required as an explicit
                # kwarg per ContextCacheKeyBuilder.derive(...). There
                # is no fallback to envelope.id or to
                # envelope.original_allowed_actions (which does not
                # exist on MissionAuthorityEnvelope).
                #
                # On MissingCacheKeyComponent or
                # CacheKeySanitizerRejection: fall through to fresh
                # computation by invoking the existing
                # ``_build_context_cached`` closure directly. We never
                # serve a cached entry under uncertainty, never
                # construct a partial key, and never fall back to the
                # old envelope.id stand-in. The exception messages
                # raised by ContextCacheKeyBuilder do not echo any
                # rejected substring; this branch propagates no extra
                # detail beyond the deterministic exception type.
                try:
                    draft_context = AgentContext(
                        mission=envelope,
                        user_input=user_input or {},
                        evidence_refs=evidence_refs or [],
                        memory_items=memory_items or [],
                    )
                    ck = ContextCacheKeyBuilder.derive(
                        envelope=envelope,
                        context=draft_context,
                        organ_state=self._organ_state_view(),
                        workspace_snapshot_id=self._workspace_snapshot_id(),
                        original_allowed_actions=original_allowed_actions,
                    )
                    # sentinel-context-cache-runtime-closure / Task 3.3 —
                    # authority drift detector. Between ck derivation
                    # (above) and serving a cached context (below), the
                    # live envelope's authority surface could mutate.
                    # Recompute authority_hash ONLY (single cheap
                    # re-hash, not a full four-component re-derivation)
                    # from the active envelope using the same explicit
                    # original_allowed_actions snapshot already captured
                    # at run entry. If the recomputed value differs from
                    # ck.authority_hash, treat the in-flight key as
                    # invalid: do NOT serve cached, do NOT fall back to
                    # envelope.id, compute fresh via the existing
                    # _build_context_cached() closure. Per design
                    # §Invalidation Rules §Rule 1 — Authority drift
                    # mid-flight: never serve a cached entry under
                    # uncertainty. No raw envelope values are logged
                    # and no new AgentEventType is emitted; the drift
                    # path is silent and deterministic.
                    current_authority_hash = ContextCacheKeyBuilder.authority_hash(
                        envelope,
                        original_allowed_actions=original_allowed_actions,
                    )
                    if current_authority_hash != ck.authority_hash:
                        context = _build_context_cached()
                    else:
                        context_cache_key = ck
                        composite_key = self._context_build_cache.composite_key(
                            mission_hot_hash=ck.mission_hot_hash,
                            workspace_snapshot_id=ck.workspace_snapshot_id,
                            organ_state_hash=ck.organ_state_hash,
                            authority_hash=ck.authority_hash,
                        )
                        context = self._context_build_cache.get_or_build(
                            composite_key,
                            _build_context_cached,
                            mission_id=envelope.id,
                        )
                except (MissingCacheKeyComponent, CacheKeySanitizerRejection):
                    # Fall through to fresh computation. No partial key.
                    # No envelope.id fallback. No cached entry served.
                    context = _build_context_cached()
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

            llm_decision_cycle = self._run_llm_backed_decision_cycle(
                envelope=envelope,
                context=context,
                state=state,
                tool_selection=tool_selection,
                capabilities=capabilities,
                missing_capabilities=missing_capabilities,
                tool_selection_findings=tool_selection_findings,
                context_cache_key=context_cache_key,
                original_allowed_actions=original_allowed_actions,
            )

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
                    llm_decision_cycle=llm_decision_cycle,
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
                    llm_decision_cycle=llm_decision_cycle,
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
            if self._organ_dispatch_should_run():
                if self._brain_native_should_run():
                    brain_cognition_result, brain_candidate_source_status = self._run_native_brain_cognition(
                        envelope=envelope,
                        user_input=user_input or {},
                    )
                state = state.transition(AgentPhase.ORGAN_DISPATCHING)
                organ_dispatch_result = self._dispatch_organs_from_runtime(
                    envelope=envelope,
                    user_input=user_input or {},
                    evidence_refs=evidence_refs or [],
                    brain_cognition_result=brain_cognition_result,
                )
                if organ_dispatch_result.status is not OrganDispatchStatus.DISABLED:
                    (
                        memory_feedback_result,
                        memory_feedback_path,
                        memory_feedback_refs,
                        memory_snapshot_ref,
                        durable_memory_persistence,
                    ) = self._write_memory_feedback_from_dispatch(
                        envelope=envelope,
                        brain_cognition_result=brain_cognition_result,
                        organ_dispatch_result=organ_dispatch_result,
                    )
                    replan_ready = True
                    replan_packet = self._build_replan_packet(
                        envelope=envelope,
                        brain_cognition_result=brain_cognition_result,
                        organ_dispatch_result=organ_dispatch_result,
                        memory_feedback_result=memory_feedback_result,
                        memory_feedback_refs=memory_feedback_refs,
                        memory_feedback_path=memory_feedback_path,
                    )
                dispatch_event_type = (
                    AgentEventType.ORGAN_DISPATCH_SKIPPED
                    if organ_dispatch_result.status in {OrganDispatchStatus.DISABLED, OrganDispatchStatus.NO_CANDIDATES}
                    else AgentEventType.ORGAN_DISPATCH_COMPLETED
                )
                dispatch_event = event_bus.append(
                    dispatch_event_type,
                    "Agent runtime processed explicit organ dispatch opt-in.",
                    phase_before=AgentPhase.EXECUTING,
                    phase_after=AgentPhase.ORGAN_DISPATCHING,
                    payload={
                        "status": organ_dispatch_result.status.value,
                        "candidate_count": len(organ_dispatch_result.candidate_results),
                        "brain_candidate_source_status": brain_candidate_source_status,
                        "memory_feedback_path": memory_feedback_path,
                        "automatic_replan_executed": False,
                    },
                )
                if (
                    organ_dispatch_result.status is not OrganDispatchStatus.DISABLED
                    and not memory_feedback_refs
                    and memory_feedback_path == "PREPARED"
                ):
                    memory_feedback_path = "PREPARED"
                    memory_feedback_refs = [dispatch_event.id, organ_dispatch_result.trace.input_hash]
                    if replan_packet is not None:
                        replan_packet["memory_feedback_refs"] = list(memory_feedback_refs)
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

            artifact_review_phase_before = state.phase
            state = state.transition(AgentPhase.ARTIFACT_REVIEWING)
            artifact_findings = self.review_loop.review_worker_result(worker_result)
            control_findings = list(state.review_findings)
            all_findings = [*control_findings, *artifact_findings, *browser_cortex_findings]
            state = state.model_copy(update={"review_findings": all_findings})
            event_bus.append(
                AgentEventType.ARTIFACTS_REVIEWED,
                "Agent reviewed worker artifacts.",
                phase_before=artifact_review_phase_before,
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
                    llm_decision_cycle=llm_decision_cycle,
                    brain_cognition_result=brain_cognition_result,
                    brain_candidate_source_status=brain_candidate_source_status,
                    organ_dispatch_result=organ_dispatch_result,
                    memory_feedback_result=memory_feedback_result,
                    memory_feedback_path=memory_feedback_path,
                    memory_feedback_refs=memory_feedback_refs,
                    memory_snapshot_ref=memory_snapshot_ref,
                    durable_memory_persistence=durable_memory_persistence,
                    replan_ready=replan_ready,
                    replan_packet=replan_packet,
                    automatic_replan_executed=automatic_replan_executed,
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
                llm_decision_cycle=llm_decision_cycle,
                brain_cognition_result=brain_cognition_result,
                brain_candidate_source_status=brain_candidate_source_status,
                organ_dispatch_result=organ_dispatch_result,
                memory_feedback_result=memory_feedback_result,
                memory_feedback_path=memory_feedback_path,
                memory_feedback_refs=memory_feedback_refs,
                memory_snapshot_ref=memory_snapshot_ref,
                durable_memory_persistence=durable_memory_persistence,
                replan_ready=replan_ready,
                replan_packet=replan_packet,
                automatic_replan_executed=automatic_replan_executed,
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
                llm_decision_cycle=llm_decision_cycle,
                brain_cognition_result=brain_cognition_result,
                brain_candidate_source_status=brain_candidate_source_status,
                organ_dispatch_result=organ_dispatch_result,
                memory_feedback_result=memory_feedback_result,
                memory_feedback_path=memory_feedback_path,
                memory_feedback_refs=memory_feedback_refs,
                memory_snapshot_ref=memory_snapshot_ref,
                durable_memory_persistence=durable_memory_persistence,
                replan_ready=replan_ready,
                replan_packet=replan_packet,
                automatic_replan_executed=automatic_replan_executed,
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

    def _run_llm_backed_decision_cycle(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        context: AgentContext,
        state: AgentState,
        tool_selection: Any,
        capabilities: list[Any],
        missing_capabilities: list[Any],
        tool_selection_findings: list[Any],
        context_cache_key: Any,
        original_allowed_actions: tuple[str, ...],
    ) -> dict[str, Any] | None:
        """Build frame -> prompt -> model-call plan without executing a model.

        sentinel-llm-backed-decision-cycle: this seam is default-off unless a
        user-selected model contract is injected. It never calls a provider and
        never emits the prompt body; only frame/prompt hashes and compact plan
        metadata are returned on the terminal AgentRunResult.
        """

        if self._user_model_contract is None:
            return None

        self._assert_memory_not_authority_boundary(
            "tool_selecting_to_llm_decision_frame_before_build",
            context,
            envelope,
            original_allowed_actions,
        )

        budget_allocator = PromptBudgetAllocator(self._user_model_contract)
        selected_tool_surface = self._selected_llm_tool_surface(
            envelope=envelope,
            tool_selection=tool_selection,
        )
        evidence_cards = self._llm_decision_evidence_cards(context)
        mission_card = self._llm_decision_mission_card(envelope=envelope, context=context)
        authority_card = self._llm_decision_authority_card(
            envelope=envelope,
            original_allowed_actions=original_allowed_actions,
        )
        progress_card = self._llm_decision_progress_card(
            state=state,
            capabilities=capabilities,
            missing_capabilities=missing_capabilities,
            tool_selection=tool_selection,
            tool_selection_findings=tool_selection_findings,
        )
        current_blockers = self._llm_decision_blockers(
            missing_capabilities=missing_capabilities,
            tool_selection=tool_selection,
            tool_selection_findings=tool_selection_findings,
            state=state,
        )
        next_decision_options = [
            "continue_deterministic_runtime_path",
            "request_user_clarification_if_blocked",
            "escalate_before_execution_boundary",
        ]
        required_output_schema = {
            "type": "object",
            "required": ["decision", "rationale", "evidence_refs"],
            "properties": {
                "decision": {"type": "string"},
                "rationale": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "requested_tool": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        }

        def build_frame() -> LLMDecisionFrame:
            return LLMDecisionFrame.build(
                mission_id=envelope.id,
                mission_card=mission_card,
                authority_card=authority_card,
                progress_card=progress_card,
                evidence=evidence_cards,
                selected_tool_surface=selected_tool_surface,
                current_blockers=current_blockers,
                next_decision_options=next_decision_options,
                required_output_schema=required_output_schema,
                budget_allocator=budget_allocator,
            )

        key = context_cache_key or self._derive_llm_decision_context_cache_key(
            envelope=envelope,
            context=context,
            original_allowed_actions=original_allowed_actions,
        )
        evidence_set_hash = self._stable_decision_cycle_hash(
            [card.model_dump(mode="json", exclude={"id"}) for card in evidence_cards]
        )
        tool_surface_hash = self._stable_decision_cycle_hash(selected_tool_surface)
        cache_key_metadata: dict[str, str] | None = None
        if key is not None:
            cache_key_metadata = {
                "mission_hot_hash": key.mission_hot_hash,
                "authority_hash": key.authority_hash,
                "evidence_set_hash": evidence_set_hash,
                "tool_surface_hash": tool_surface_hash,
            }

            def cached_frame_builder() -> LLMDecisionFrame:
                return self._build_decision_frame_cached(
                    mission_id=envelope.id,
                    composite_inputs=cache_key_metadata,
                    builder=build_frame,
                )

            frame_builder = cached_frame_builder
        else:
            frame_builder = build_frame

        frame, budget_decision = self._enforce_frame_budget(
            mission_id=envelope.id,
            builder=frame_builder,
            frame_budget=budget_allocator.max_decision_frame_tokens,
        )

        if set(frame.selected_tool_surface) - set(envelope.allowed_tools):
            raise InvariantViolation("LLM decision frame selected tools outside mission authority.")
        if frame.authority_expansion:
            raise InvariantViolation("LLM decision frame attempted authority expansion.")
        if frame.raw_secret_leakage:
            raise InvariantViolation("LLM decision frame contains raw secret material.")

        self._assert_memory_not_authority_boundary(
            "tool_selecting_to_llm_decision_frame_after_build",
            context,
            envelope,
            original_allowed_actions,
        )

        rendered_prompt = self._render_prompt_text_cached(frame, mission_id=envelope.id)
        prompt_sha256 = hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()
        prompt_token_count = estimate_tokens(rendered_prompt)

        selected_model_call_plan = None
        model_call_plan = None
        model_call_recommendation = None
        if self._model_call_optimizer is not None:
            candidate_plan = self._model_call_optimizer.plan(frame, ledger=None)
            candidate_plan_payload = candidate_plan.model_dump(mode="json")
            if (
                candidate_plan.model_id == frame.user_selected_model
                and candidate_plan.provider_id == self._user_model_contract.selected_provider_id
                and candidate_plan.backend_id == self._user_model_contract.selected_backend_id
            ):
                selected_model_call_plan = candidate_plan
                model_call_plan = candidate_plan_payload
            else:
                model_call_recommendation = candidate_plan_payload

        model_execution_metadata = self._model_execution_metadata_default_off()
        if self._model_execution_coordinator is not None and selected_model_call_plan is not None:
            timeout_policy, retry_policy, budget_policy = self._default_model_execution_policies(
                selected_model_call_plan=selected_model_call_plan
            )
            request = RealModelRequestBuilder.build(
                frame=frame,
                rendered_prompt=rendered_prompt,
                plan=selected_model_call_plan,
                user_model=self._user_model_contract,
                timeout_policy=timeout_policy,
                retry_policy=retry_policy,
                budget_policy=budget_policy,
            )
            outcome = self._model_execution_coordinator.execute(request=request)
            model_execution_metadata = self._model_execution_outcome_metadata(outcome=outcome, request=request)

        metadata = {
            "enabled": True,
            "frame_id": frame.id,
            "frame_hash": frame.frame_hash,
            "frame_token_count": frame.token_count,
            "prompt_sha256": prompt_sha256,
            "prompt_token_count": prompt_token_count,
            "prompt_budget_respected": frame.prompt_budget_respected,
            "selected_tool_surface": list(frame.selected_tool_surface),
            "receipt_refs": list(frame.receipt_refs),
            "cache_key": cache_key_metadata,
            "budget_decision": budget_decision.model_dump(mode="json") if budget_decision is not None else None,
            "user_selected_model": frame.user_selected_model,
            "model_call_plan": model_call_plan,
            "model_call_recommendation": model_call_recommendation,
            "model_execution": model_execution_metadata,
            "model_execution_deferred": model_execution_metadata["outcome_class"] != ModelExecutionOutcomeClass.SUCCESS_VALIDATED.value,
            "model_execution_deferral_id": (
                None
                if model_execution_metadata["outcome_class"] == ModelExecutionOutcomeClass.SUCCESS_VALIDATED.value
                else model_execution_metadata.get("deferral_id", "RUNTIME_MODEL_EXECUTION_WIRING")
            ),
        }
        return sanitize_context_payload(metadata)

    @staticmethod
    def _model_execution_metadata_default_off() -> dict[str, Any]:
        return {
            "enabled": False,
            "outcome_class": ModelExecutionOutcomeClass.MODEL_EXECUTION_DEFERRED.value,
            "success": False,
            "provider_called": False,
            "message": "model execution coordinator is default-off",
            "deferral_id": "LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER",
            "request": None,
            "result": None,
            "receipt": None,
            "budget_summary": None,
        }

    def _default_model_execution_policies(self, *, selected_model_call_plan: Any) -> tuple[
        ModelTimeoutPolicy,
        ModelRetryPolicy,
        ModelExecutionBudgetPolicy,
    ]:
        assert self._user_model_contract is not None
        return (
            ModelTimeoutPolicy(connect_timeout_seconds=2.0, read_timeout_seconds=5.0, total_timeout_seconds=7.0),
            ModelRetryPolicy(max_attempts=1, retryable_outcomes=[]),
            ModelExecutionBudgetPolicy(
                max_input_tokens=max(
                    selected_model_call_plan.estimated_input_tokens,
                    self._user_model_contract.context_budget_policy.max_decision_frame_tokens,
                ),
                max_output_tokens=self._user_model_contract.context_budget_policy.reserve_output_tokens,
                max_total_estimated_usd=0.0,
            ),
        )

    @staticmethod
    def _model_execution_outcome_metadata(*, outcome: ModelExecutionOutcome, request: Any) -> dict[str, Any]:
        return {
            "enabled": True,
            "outcome_class": outcome.outcome_class.value,
            "success": outcome.success,
            "provider_called": outcome.provider_called,
            "message": outcome.message,
            "request": request.serializable_metadata(),
            "result": outcome.result.model_dump(mode="json") if outcome.result is not None else None,
            "receipt": outcome.receipt.model_dump(mode="json") if outcome.receipt is not None else None,
            "budget_summary": outcome.budget_summary,
        }

    @staticmethod
    def _stable_decision_cycle_hash(payload: Any) -> str:
        canonical = json.dumps(
            sanitize_context_payload(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _derive_llm_decision_context_cache_key(
        self,
        *,
        envelope: MissionAuthorityEnvelope,
        context: AgentContext,
        original_allowed_actions: tuple[str, ...],
    ) -> Any:
        try:
            return ContextCacheKeyBuilder.derive(
                envelope=envelope,
                context=context,
                organ_state=self._organ_state_view(),
                workspace_snapshot_id=self._workspace_snapshot_id(),
                original_allowed_actions=original_allowed_actions,
            )
        except (MissingCacheKeyComponent, CacheKeySanitizerRejection):
            return None

    @staticmethod
    def _llm_decision_evidence_cards(context: AgentContext) -> list[EvidenceCard]:
        cards: list[EvidenceCard] = []
        for index, ref in enumerate(context.evidence_refs[:8]):
            safe_ref = sanitize_context_text(str(ref))
            summary = (
                f"Evidence ref {safe_ref} is available outside the prompt; "
                "exact payload remains in the receipt graph."
            )
            cards.append(
                EvidenceCard(
                    receipt_id=safe_ref,
                    source_type="runtime_evidence_ref",
                    summary=summary,
                    evidence_refs=[safe_ref],
                    relevance_score=round(1.0 - (index * 0.01), 6),
                    token_count=estimate_tokens(summary),
                    critical=index == 0,
                )
            )
        return cards

    @staticmethod
    def _selected_llm_tool_surface(
        *,
        envelope: MissionAuthorityEnvelope,
        tool_selection: Any,
    ) -> list[str]:
        allowed = set(envelope.allowed_tools)
        selected = getattr(tool_selection, "selected_tools", []) or []
        return sorted({sanitize_context_text(str(tool)) for tool in selected if tool in allowed})

    @staticmethod
    def _llm_decision_mission_card(
        *,
        envelope: MissionAuthorityEnvelope,
        context: AgentContext,
    ) -> dict[str, Any]:
        return sanitize_context_payload(
            {
                "mission_id": envelope.id,
                "mission_type": envelope.mission_type.value
                if hasattr(envelope.mission_type, "value")
                else str(envelope.mission_type),
                "mission_title": envelope.mission_title,
                "mission_objective": envelope.mission_objective,
                "success_criteria": list(envelope.success_criteria),
                "context_summary": context.summary,
                "constraints": list(context.constraints),
            }
        )

    @staticmethod
    def _llm_decision_authority_card(
        *,
        envelope: MissionAuthorityEnvelope,
        original_allowed_actions: tuple[str, ...],
    ) -> dict[str, Any]:
        return sanitize_context_payload(
            {
                "mode": envelope.mode.value if hasattr(envelope.mode, "value") else str(envelope.mode),
                "allowed_actions": sorted(envelope.allowed_actions),
                "original_allowed_actions": sorted(original_allowed_actions),
                "forbidden_actions": sorted(envelope.forbidden_actions),
                "allowed_tools": sorted(envelope.allowed_tools),
                "allowed_domains": sorted(envelope.allowed_domains),
                "allowed_paths": sorted(envelope.allowed_paths),
                "max_actions": envelope.max_actions,
                "max_cost_usd": envelope.max_cost_usd,
                "risk_appetite_score": envelope.risk_appetite_score,
            }
        )

    @staticmethod
    def _llm_decision_progress_card(
        *,
        state: AgentState,
        capabilities: list[Any],
        missing_capabilities: list[Any],
        tool_selection: Any,
        tool_selection_findings: list[Any],
    ) -> dict[str, Any]:
        return sanitize_context_payload(
            {
                "phase": state.phase.value if hasattr(state.phase, "value") else str(state.phase),
                "selected_method_ids": [method.id for method in state.selected_methods],
                "needed_capabilities": [need.name for need in capabilities],
                "missing_capabilities": [need.name for need in missing_capabilities],
                "selected_tools": list(getattr(tool_selection, "selected_tools", []) or []),
                "candidate_tools": list(getattr(tool_selection, "candidate_tools", []) or []),
                "blocked_tools": list(getattr(tool_selection, "blocked_tools", []) or []),
                "unavailable_capabilities": list(getattr(tool_selection, "unavailable_capabilities", []) or []),
                "review_finding_codes": [finding.code for finding in tool_selection_findings],
            }
        )

    @staticmethod
    def _llm_decision_blockers(
        *,
        missing_capabilities: list[Any],
        tool_selection: Any,
        tool_selection_findings: list[Any],
        state: AgentState,
    ) -> list[str]:
        blockers: list[str] = []
        blockers.extend(f"missing_capability:{need.name}" for need in missing_capabilities if getattr(need, "required", False))
        blockers.extend(f"blocked_tool:{tool}" for tool in getattr(tool_selection, "blocked_tools", []) or [])
        blockers.extend(
            f"unavailable_capability:{capability}"
            for capability in getattr(tool_selection, "unavailable_capabilities", []) or []
        )
        blockers.extend(
            f"critical_finding:{finding.code}"
            for finding in tool_selection_findings
            if getattr(finding, "severity", "") == "critical"
        )
        blockers.extend(
            f"open_question:{question.question}"
            for question in state.open_questions
            if getattr(question, "blocks_completion", False)
        )
        return sanitize_context_payload(sorted(set(blockers)))

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
            _DecisionFrameBudgetCompressor(self.context_compressor),
            frame_budget,
        )

    def _organ_state_view(self) -> "OrganStateView":
        """Return the organ-state snapshot for ContextCacheKey derivation.

        sentinel-context-cache-runtime-closure / Task 3.1.

        At HEAD, ``AgentRuntime`` has no mission-wide organ-state map: there
        is no ``self._organ_registry``, no ``self._mission_kill_switches``,
        and ``self.tool_registry`` is a tool/capability registry — a tool is
        not equivalent to an organ. ``CapabilityManifest`` does not expose
        an ``organ_id`` field.

        At the CONTEXT_BUILDING phase no controlled-tool-call has been
        dispatched yet, so no ``OrganKillSwitch`` is engaged. Per the
        Task 3.1 brief's fallback rule (and the design's
        ``CacheInvalidationPolicy``-driven invalidation contract), return
        an empty ``OrganStateView``. Mid-run organ-state changes are
        reflected via the existing ``CacheInvalidationPolicy.invalidate(...)``
        path, not via re-deriving this view per call.

        Pure read-only over ``self``. Mutates no caller-owned object. No
        I/O. No external system access. No tool-registry expansion.
        """

        return OrganStateView(organs=[])

    def _workspace_snapshot_id(self) -> str:
        """Return the workspace snapshot id for ContextCacheKey derivation.

        sentinel-context-cache-runtime-closure / Task 3.1.

        Returns ``self._workspace_snapshot_cache.snapshot_id`` when a
        ``WorkspaceSnapshotCache`` is injected on the runtime (a future
        wave's optional kwarg) and exposes a non-empty ``snapshot_id``
        attribute. At HEAD no such cache is injected (``getattr`` returns
        ``None``); fall back to the canonical empty-snapshot SHA-256 hex
        constant ``e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855``
        (= ``sha256(b"").hexdigest()``), which is the value the Phase E
        ``WorkspaceSnapshotCache`` returns for an empty snapshot. Semantics
        identical.

        Pure read-only over ``self``. No I/O. Returns a 64-character
        lowercase hex string in all cases — the value is suitable as the
        ``workspace_snapshot_id`` slot on ``ContextCacheKey``.
        """

        cache = getattr(self, "_workspace_snapshot_cache", None)
        if cache is not None:
            snapshot_id = getattr(cache, "snapshot_id", None)
            if isinstance(snapshot_id, str) and snapshot_id:
                return snapshot_id
        return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

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
