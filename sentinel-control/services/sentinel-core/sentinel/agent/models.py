from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, Field

from sentinel.agent.effort_router import EffortRoute
from sentinel.agent.events import AgentEventType
from sentinel.agent.evidence import EvidenceChain, EvidenceDecisionType
from sentinel.agent.execution_posture import ExecutionPosture
from sentinel.agent.hypothesis import AdversarialFinding, MissionHypothesis, VerificationTest
from sentinel.agent.phases import AgentPhase
from sentinel.agent.repair_loop import RepairDecision
from sentinel.agent.uncertainty import Assumption, Fact, Hypothesis, Question, UncertaintyState
from sentinel.agent.world_model import ActionEvaluation, CognitiveAction, ObjectiveScore, WorldModelPrediction
from sentinel.mission.models import MissionArtifact, MissionAuthorityEnvelope, MissionPlan, MissionRunResult
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    # Forward reference only — importing CoreFinalGateResult at runtime would
    # create a circular import because ``sentinel.agent.final_gate`` already
    # imports ``AgentRunResult`` from this module. The real type is wired in
    # by ``sentinel.agent.final_gate`` which calls ``AgentRunResult.model_rebuild``
    # with an explicit ``_types_namespace`` once the class is defined.
    from sentinel.agent.final_gate import CoreFinalGateResult
    from sentinel.perf.measure.performance_receipt import PerformanceReceipt


def utc_now() -> datetime:
    return datetime.now(UTC)


class MethodRef(SentinelModel):
    id: str
    name: str
    reason: str
    required_before: list[str] = Field(default_factory=list)


class CapabilityNeed(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capneed"))
    name: str
    reason: str
    required: bool = True
    available: bool = False
    missing_reason: str | None = None


class ToolSelectionStatus(StrEnum):
    ELIGIBLE_FOR_SAFE_WORKER = "eligible_for_safe_worker"
    ELIGIBLE_FOR_DRY_RUN = "eligible_for_dry_run"
    CANDIDATE = "candidate"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


class ToolSelectionDecision(SentinelModel):
    mission_id: str
    capability_name: str
    requested_action: str | None = None
    candidate_tool_id: str | None = None
    decision: ToolSelectionStatus
    reason: str
    manifest_status: str | None = None
    risk_class: str | None = None
    side_effects: list[str] = Field(default_factory=list)
    authority_allowed: bool = False
    registry_policy_result: str | None = None
    trace_id: str | None = None


class ToolSelectionResult(SentinelModel):
    decisions: list[ToolSelectionDecision] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    unavailable_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class ReviewFinding(SentinelModel):
    code: str
    severity: str
    message: str
    trace_refs: list[str] = Field(default_factory=list)


class WorkerTask(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("wtask"))
    worker_type: str
    mission_id: str
    input_refs: list[str] = Field(default_factory=list)
    expected_output: str
    allowed_actions: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


class WorkerResult(SentinelModel):
    task_id: str
    status: str
    output_refs: list[str] = Field(default_factory=list)
    facts_found: list[Fact] = Field(default_factory=list)
    assumptions_created: list[Assumption] = Field(default_factory=list)
    open_questions: list[Question] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
    mission_result: MissionRunResult | None = None


class LearningProposal(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("learn"))
    observed_failure: str
    evidence_refs: list[str] = Field(default_factory=list)
    proposed_change: str
    risk: str = "low"
    tests_needed: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True


class AgentContext(SentinelModel):
    mission: MissionAuthorityEnvelope
    user_input: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    memory_items: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    available_capabilities: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    world_model_refs: list[str] = Field(default_factory=list)
    summary: str = ""


# Task 13 / Requirement 13 — ``AgentEvent`` has been lifted into
# :mod:`sentinel.shared.events` as a platform primitive. It is re-exported
# here for backward compatibility. Callers that used to do
# ``from sentinel.agent.models import AgentEvent`` continue to work.
from sentinel.shared.events import AgentEvent  # noqa: F401, E402  (re-export)


class RuntimeCertificationResult(SentinelModel):
    mission_id: str | None = None
    event_count: int = 0
    certified: bool = False
    integrity_ok: bool = False
    terminal_ok: bool = False
    execution_seen: bool = False
    planning_seen: bool = False
    evidence_ok: bool = True
    evidence_chain_types: list[EvidenceDecisionType] = Field(default_factory=list)
    event_types: list[AgentEventType] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AgentStateSnapshot(SentinelModel):
    mission_id: str | None = None
    event_count: int = 0
    final_phase: AgentPhase | None = None
    last_event_id: str | None = None
    trace_hash: str | None = None
    selected_methods: list[str] = Field(default_factory=list)
    needed_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    unavailable_capabilities: list[str] = Field(default_factory=list)
    verified_hypotheses: list[str] = Field(default_factory=list)
    rejected_hypotheses: list[str] = Field(default_factory=list)
    selected_action_id: str | None = None
    selected_action_name: str | None = None
    effort_level: str | None = None
    effort_score: float | None = None
    execution_posture: str | None = None
    direct_tool_call_budget: int = 0
    repair_decision: str | None = None
    repair_pressure: float | None = None
    repair_cycles: int = 0
    max_repair_cycles: int = 0
    learning_proposal_count: int = 0
    worker_started: bool = False
    worker_completed: bool = False
    controlled_capability_executed_count: int = 0
    controlled_capability_rejected_count: int = 0
    project_path: str | None = None
    success: bool | None = None
    evidence_chain_ids: list[str] = Field(default_factory=list)
    evidence_chain_types: list[EvidenceDecisionType] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AgentReplayResult(SentinelModel):
    accepted: bool = False
    snapshot: AgentStateSnapshot
    certification: RuntimeCertificationResult
    errors: list[str] = Field(default_factory=list)


class AgentRunResult(SentinelModel):
    mission_id: str
    final_phase: AgentPhase
    success: bool
    project_path: str | None = None
    artifacts: list[MissionArtifact] = Field(default_factory=list)
    selected_methods: list[MethodRef] = Field(default_factory=list)
    needed_capabilities: list[CapabilityNeed] = Field(default_factory=list)
    missing_capabilities: list[CapabilityNeed] = Field(default_factory=list)
    tool_selection_decisions: list[ToolSelectionDecision] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    unavailable_capabilities: list[str] = Field(default_factory=list)
    hypotheses: list[MissionHypothesis] = Field(default_factory=list)
    verified_hypotheses: list[MissionHypothesis] = Field(default_factory=list)
    verification_tests: list[VerificationTest] = Field(default_factory=list)
    adversarial_findings: list[AdversarialFinding] = Field(default_factory=list)
    cognitive_actions: list[CognitiveAction] = Field(default_factory=list)
    world_model_predictions: list[WorldModelPrediction] = Field(default_factory=list)
    objective_scores: list[ObjectiveScore] = Field(default_factory=list)
    action_evaluations: list[ActionEvaluation] = Field(default_factory=list)
    selected_action_id: str | None = None
    selected_action_name: str | None = None
    controlled_capability_results: list[dict[str, Any]] = Field(default_factory=list)
    execution_posture: ExecutionPosture | None = None
    effort_route: EffortRoute | None = None
    repair_decision: RepairDecision | None = None
    known_facts: list[Fact] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    suspected: list[Hypothesis] = Field(default_factory=list)
    open_questions: list[Question] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    learning_proposals: list[LearningProposal] = Field(default_factory=list)
    evidence_chains: list[EvidenceChain] = Field(default_factory=list)
    trace: list[AgentEvent] = Field(default_factory=list)
    runtime_certification: RuntimeCertificationResult | None = None
    state_snapshot: AgentStateSnapshot | None = None
    mission_result: MissionRunResult | None = None
    mission_results: list[MissionRunResult] = Field(default_factory=list)
    performance_receipts: list["PerformanceReceipt"] = Field(default_factory=list)
    escalation_reason: str | None = None
    active_plan: MissionPlan | None = None
    # Task 1.3 / Requirement 1 (FinalGate Runtime Integration):
    # Full CoreFinalGateResult attached by AgentRuntime._apply_final_gate so
    # callers can inspect every gate check (accepted flag + per-check details).
    # Declared as an optional forward reference to avoid a circular import
    # with ``sentinel.agent.final_gate``; the real type is resolved at module
    # load time by ``CoreFinalGate``'s module via ``model_rebuild``.
    final_gate_certification: "CoreFinalGateResult | None" = None
