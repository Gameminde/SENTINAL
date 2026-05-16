from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.agent.effort_router import EffortRoute
from sentinel.agent.evidence import EvidenceChain
from sentinel.agent.exceptions import InvalidPhaseTransition
from sentinel.agent.execution_posture import ExecutionPosture
from sentinel.agent.hypothesis import AdversarialFinding, MissionHypothesis, VerificationTest
from sentinel.agent.models import CapabilityNeed, MethodRef, ReviewFinding, ToolSelectionDecision
from sentinel.agent.phases import AgentPhase, can_transition
from sentinel.agent.repair_loop import RepairDecision
from sentinel.agent.uncertainty import Assumption, Fact, Hypothesis, Question, UncertaintyState
from sentinel.agent.world_model import ActionEvaluation, CognitiveAction, ObjectiveScore, WorldModelPrediction
from sentinel.shared.models import SentinelModel


class AgentState(SentinelModel):
    mission_id: str
    phase: AgentPhase = AgentPhase.CREATED
    working_memory: dict = Field(default_factory=dict)
    known_facts: list[Fact] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    suspected: list[Hypothesis] = Field(default_factory=list)
    open_questions: list[Question] = Field(default_factory=list)
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
    execution_posture: ExecutionPosture | None = None
    controlled_capability_results: list[dict[str, Any]] = Field(default_factory=list)
    effort_route: EffortRoute | None = None
    repair_decision: RepairDecision | None = None
    evidence_chains: list[EvidenceChain] = Field(default_factory=list)
    plan_id: str | None = None
    active_step_id: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_used: float = Field(default=0.0, ge=0.0)
    repair_cycles: int = Field(default=0, ge=0)
    max_repair_cycles: int = Field(default=1, ge=0)

    @property
    def uncertainty(self) -> UncertaintyState:
        return UncertaintyState(
            known=self.known_facts,
            assumed=self.assumptions,
            suspected=self.suspected,
            unknown=self.open_questions,
        )

    def transition(self, next_phase: AgentPhase) -> "AgentState":
        if not can_transition(self.phase, next_phase):
            raise InvalidPhaseTransition(
                f"Invalid agent phase transition: `{self.phase}` -> `{next_phase}`."
            )
        return self.model_copy(update={"phase": next_phase})
