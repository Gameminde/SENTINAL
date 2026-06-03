from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import Field

from sentinel.agent.events import AgentEventType
from sentinel.agent.phases import AgentPhase
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.agent.event_bus import EventBus
    from sentinel.agent.hypothesis import AdversarialFinding, HypothesisVerificationResult, MissionHypothesis
    from sentinel.agent.models import AgentContext, AgentEvent, CapabilityNeed, LearningProposal, ReviewFinding, ToolSelectionResult
    from sentinel.agent.repair_loop import RepairDecision
    from sentinel.mission.models import MissionPlan, MissionRunResult


class EvidenceDecisionType(StrEnum):
    TOOL_SELECTION = "tool_selection"
    HYPOTHESIS_VERDICT = "hypothesis_verdict"
    BROWSER_CORTEX_INTERPRETATION = "browser_cortex_interpretation"
    PLAN_CREATION = "plan_creation"
    REPAIR_DECISION = "repair_decision"
    SUCCESS_EVALUATION = "success_evaluation"
    LEARNING_PROPOSAL = "learning_proposal"


class EvidenceSourceType(StrEnum):
    MISSION_AUTHORITY = "mission_authority"
    USER_EVIDENCE_REF = "user_evidence_ref"
    TRACE_EVENT = "trace_event"
    BROWSER_OUTPUT = "browser_output"
    TOOL_POLICY = "tool_policy"
    HYPOTHESIS_TEST = "hypothesis_test"
    ADVERSARIAL_FINDING = "adversarial_finding"
    PLAN_REVIEW = "plan_review"
    WORKER_RESULT = "worker_result"
    REPAIR_DECISION = "repair_decision"
    SUCCESS_EVALUATION = "success_evaluation"
    LEARNING_PROPOSAL = "learning_proposal"


class EvidenceVerdict(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


class EvidenceClaim(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("eclaim"))
    mission_id: str
    decision_type: EvidenceDecisionType
    subject: str
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("eref"))
    source_type: EvidenceSourceType
    ref: str
    summary: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    trace_refs: list[str] = Field(default_factory=list)


class ContradictionRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("contra"))
    ref: str
    summary: str
    severity: str = "medium"
    trace_refs: list[str] = Field(default_factory=list)


class EvidenceChain(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("echain"))
    mission_id: str
    decision_type: EvidenceDecisionType
    claim: EvidenceClaim
    evidence: list[EvidenceRef] = Field(default_factory=list)
    contradictions: list[ContradictionRef] = Field(default_factory=list)
    verdict: EvidenceVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    trace_refs: list[str] = Field(default_factory=list)


class EvidenceChainReviewResult(SentinelModel):
    accepted: bool = False
    present_decision_types: list[EvidenceDecisionType] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class EvidenceChainBuilder:
    """Builds proof chains for mission-shaping decisions.

    P1J evidence is internal and replayable: it references mission authority,
    existing event ids, review findings, and local artifacts. It never retrieves
    live data and never changes authority.
    """

    def build_tool_selection(
        self,
        context: AgentContext,
        tool_selection: ToolSelectionResult,
        review_findings: list[ReviewFinding],
        *,
        event_bus: EventBus,
    ) -> EvidenceChain:
        critical = self._critical_findings(review_findings)
        contradictions = [
            *[
                ContradictionRef(
                    ref=finding.code,
                    summary=finding.message,
                    severity=finding.severity,
                    trace_refs=finding.trace_refs,
                )
                for finding in review_findings
            ],
            *[
                ContradictionRef(
                    ref=capability,
                    summary="Capability has no selected safe worker tool inside the current authority envelope.",
                    severity="critical",
                )
                for capability in tool_selection.missing_capabilities
            ],
        ]
        verdict = EvidenceVerdict.BLOCKED if critical else EvidenceVerdict.SUPPORTED
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.TOOL_SELECTION,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.TOOL_SELECTION,
                subject="tool_selection",
                statement="Selected tools are derived from declared capabilities, registry policy, and mission authority.",
                confidence=0.95 if not critical else 0.35,
            ),
            evidence=[
                EvidenceRef(
                    source_type=EvidenceSourceType.MISSION_AUTHORITY,
                    ref=context.mission.id,
                    summary="Mission authority envelope bounds allowed tools and actions.",
                ),
                EvidenceRef(
                    source_type=EvidenceSourceType.TOOL_POLICY,
                    ref="tool_selection_decisions",
                    summary=f"{len(tool_selection.decisions)} registry decisions were evaluated before planning.",
                    trace_refs=tool_selection.trace_refs,
                ),
            ],
            contradictions=contradictions,
            verdict=verdict,
            confidence=0.95 if not critical else 0.35,
            trace_refs=tool_selection.trace_refs,
        )
        return self._emit(event_bus, chain, phase=AgentPhase.TOOL_SELECTING)

    def build_hypothesis_verdict(
        self,
        context: AgentContext,
        hypothesis_result: HypothesisVerificationResult,
        review_findings: list[ReviewFinding],
        *,
        event_bus: EventBus,
    ) -> EvidenceChain:
        critical = self._critical_findings(review_findings)
        verified_ids = [hypothesis.id for hypothesis in hypothesis_result.verified_hypotheses]
        contradictions = [
            *[
                ContradictionRef(
                    ref=finding.id,
                    summary=finding.finding,
                    severity=finding.severity,
                    trace_refs=finding.trace_refs,
                )
                for finding in hypothesis_result.adversarial_findings
            ],
            *[
                ContradictionRef(
                    ref=hypothesis.id,
                    summary="Hypothesis was rejected before planning.",
                    severity="high",
                    trace_refs=hypothesis.trace_refs,
                )
                for hypothesis in hypothesis_result.rejected_hypotheses
            ],
            *[
                ContradictionRef(
                    ref=finding.code,
                    summary=finding.message,
                    severity=finding.severity,
                    trace_refs=finding.trace_refs,
                )
                for finding in review_findings
            ],
        ]
        verdict = EvidenceVerdict.BLOCKED if critical else EvidenceVerdict.SUPPORTED if verified_ids else EvidenceVerdict.INCONCLUSIVE
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.HYPOTHESIS_VERDICT,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.HYPOTHESIS_VERDICT,
                subject="hypothesis_verdict",
                statement="Only locally verified hypotheses may influence planning.",
                confidence=0.9 if verified_ids and not critical else 0.45,
            ),
            evidence=[
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.HYPOTHESIS_TEST,
                        ref=test.id,
                        summary=f"{test.method} returned {test.result}.",
                        confidence=0.85,
                        trace_refs=test.trace_refs,
                    )
                    for test in hypothesis_result.verification_tests
                ],
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.USER_EVIDENCE_REF,
                        ref=ref,
                        summary="User-provided evidence reference was preserved through hypothesis verification.",
                        confidence=0.7,
                    )
                    for ref in context.evidence_refs
                ],
            ],
            contradictions=contradictions,
            verdict=verdict,
            confidence=0.9 if verified_ids and not critical else 0.45,
            trace_refs=hypothesis_result.trace_refs,
        )
        return self._emit(event_bus, chain, phase=AgentPhase.HYPOTHESIS_VERIFYING)

    def build_plan_creation(
        self,
        context: AgentContext,
        plan: MissionPlan,
        tool_selection: ToolSelectionResult,
        verified_hypotheses: list[MissionHypothesis],
        review_findings: list[ReviewFinding],
        *,
        event_bus: EventBus,
    ) -> EvidenceChain:
        critical = self._critical_findings(review_findings)
        verdict = EvidenceVerdict.BLOCKED if critical else EvidenceVerdict.SUPPORTED if plan.steps else EvidenceVerdict.CONTRADICTED
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.PLAN_CREATION,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.PLAN_CREATION,
                subject=plan.mission_id,
                statement="The active plan uses only selected tools and verified hypotheses.",
                confidence=0.92 if verdict == EvidenceVerdict.SUPPORTED else 0.25,
            ),
            evidence=[
                EvidenceRef(
                    source_type=EvidenceSourceType.TOOL_POLICY,
                    ref="selected_tools",
                    summary=", ".join(tool_selection.selected_tools) if tool_selection.selected_tools else "No tools selected.",
                    trace_refs=tool_selection.trace_refs,
                ),
                EvidenceRef(
                    source_type=EvidenceSourceType.PLAN_REVIEW,
                    ref=plan.mission_id,
                    summary=f"Plan contains {len(plan.steps)} reviewed step(s).",
                ),
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.HYPOTHESIS_TEST,
                        ref=hypothesis.id,
                        summary="Verified hypothesis was available to PlannerBridge.",
                        confidence=hypothesis.confidence,
                        trace_refs=hypothesis.trace_refs,
                    )
                    for hypothesis in verified_hypotheses
                ],
            ],
            contradictions=[
                ContradictionRef(
                    ref=finding.code,
                    summary=finding.message,
                    severity=finding.severity,
                    trace_refs=finding.trace_refs,
                )
                for finding in review_findings
            ],
            verdict=verdict,
            confidence=0.92 if verdict == EvidenceVerdict.SUPPORTED else 0.25,
            trace_refs=[*tool_selection.trace_refs, *self._trace_refs_from_findings(review_findings)],
        )
        return self._emit(event_bus, chain, phase=AgentPhase.PLAN_REVIEWING)

    def build_repair_decision(
        self,
        context: AgentContext,
        repair_decision: RepairDecision,
        review_findings: list[ReviewFinding],
        adversarial_findings: list[AdversarialFinding],
        *,
        event_bus: EventBus,
    ) -> EvidenceChain:
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.REPAIR_DECISION,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.REPAIR_DECISION,
                subject=repair_decision.id,
                statement="Repair routing is computed from bounded pressure signals and cannot expand authority.",
                confidence=0.95,
            ),
            evidence=[
                EvidenceRef(
                    source_type=EvidenceSourceType.REPAIR_DECISION,
                    ref=repair_decision.id,
                    summary=f"{repair_decision.decision} at pressure {repair_decision.repair_pressure}.",
                    trace_refs=repair_decision.trace_refs,
                ),
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.PLAN_REVIEW,
                        ref=finding.code,
                        summary=finding.message,
                        confidence=0.8,
                        trace_refs=finding.trace_refs,
                    )
                    for finding in review_findings
                ],
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.ADVERSARIAL_FINDING,
                        ref=finding.id,
                        summary=finding.finding,
                        confidence=0.8,
                        trace_refs=finding.trace_refs,
                    )
                    for finding in adversarial_findings
                ],
            ],
            verdict=EvidenceVerdict.SUPPORTED,
            confidence=0.95,
            trace_refs=repair_decision.trace_refs,
        )
        return self._emit(event_bus, chain, phase=AgentPhase.ARTIFACT_REVIEWING)

    def build_success_evaluation(
        self,
        context: AgentContext,
        *,
        mission_success: bool,
        mission_result: MissionRunResult | None,
        review_findings: list[ReviewFinding],
        repair_decision: RepairDecision | None,
        event_bus: EventBus,
    ) -> EvidenceChain:
        critical = self._critical_findings(review_findings)
        verdict = EvidenceVerdict.SUPPORTED if mission_success and mission_result and not critical else EvidenceVerdict.INCONCLUSIVE
        if mission_success and (mission_result is None or critical):
            verdict = EvidenceVerdict.CONTRADICTED
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.SUCCESS_EVALUATION,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.SUCCESS_EVALUATION,
                subject="mission_success",
                statement="Mission success requires MissionRunner success and no critical review finding.",
                confidence=0.95 if verdict == EvidenceVerdict.SUPPORTED else 0.65,
            ),
            evidence=[
                EvidenceRef(
                    source_type=EvidenceSourceType.WORKER_RESULT,
                    ref=mission_result.project_path if mission_result else "missing_mission_result",
                    summary=f"MissionRunner success={mission_result.success if mission_result else False}.",
                    confidence=0.9 if mission_result else 0.2,
                    trace_refs=[event.id for event in mission_result.trace_events] if mission_result else [],
                ),
                *(
                    [
                        EvidenceRef(
                            source_type=EvidenceSourceType.REPAIR_DECISION,
                            ref=repair_decision.id,
                            summary=f"Repair decision before success evaluation: {repair_decision.decision}.",
                            confidence=0.9,
                            trace_refs=repair_decision.trace_refs,
                        )
                    ]
                    if repair_decision
                    else []
                ),
            ],
            contradictions=[
                ContradictionRef(
                    ref=finding.code,
                    summary=finding.message,
                    severity=finding.severity,
                    trace_refs=finding.trace_refs,
                )
                for finding in review_findings
                if finding.severity == "critical"
            ],
            verdict=verdict,
            confidence=0.95 if verdict == EvidenceVerdict.SUPPORTED else 0.65,
            trace_refs=repair_decision.trace_refs if repair_decision else [],
        )
        return self._emit(event_bus, chain, phase=AgentPhase.SUCCESS_EVALUATING)

    def build_learning_proposal(
        self,
        context: AgentContext,
        learning_proposals: list[LearningProposal],
        review_findings: list[ReviewFinding],
        missing_capabilities: list[CapabilityNeed],
        *,
        event_bus: EventBus,
    ) -> EvidenceChain:
        unsafe = [proposal.id for proposal in learning_proposals if not proposal.requires_human_approval]
        chain = EvidenceChain(
            mission_id=context.mission.id,
            decision_type=EvidenceDecisionType.LEARNING_PROPOSAL,
            claim=EvidenceClaim(
                mission_id=context.mission.id,
                decision_type=EvidenceDecisionType.LEARNING_PROPOSAL,
                subject="learning_proposals",
                statement="Learning output is proposal-only and requires human approval.",
                confidence=1.0 if not unsafe else 0.0,
            ),
            evidence=[
                EvidenceRef(
                    source_type=EvidenceSourceType.LEARNING_PROPOSAL,
                    ref="learning_proposal_count",
                    summary=f"{len(learning_proposals)} proposal(s) were produced; all must remain human-approved.",
                    confidence=1.0,
                ),
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.LEARNING_PROPOSAL,
                        ref=proposal.id,
                        summary=proposal.observed_failure,
                        confidence=0.8,
                        trace_refs=proposal.evidence_refs,
                    )
                    for proposal in learning_proposals
                ],
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.PLAN_REVIEW,
                        ref=finding.code,
                        summary=finding.message,
                        confidence=0.75,
                        trace_refs=finding.trace_refs,
                    )
                    for finding in review_findings
                ],
                *[
                    EvidenceRef(
                        source_type=EvidenceSourceType.TOOL_POLICY,
                        ref=capability.name,
                        summary=capability.missing_reason or "Capability remains unavailable.",
                        confidence=0.75,
                    )
                    for capability in missing_capabilities
                ],
            ],
            contradictions=[
                ContradictionRef(
                    ref=proposal_id,
                    summary="Learning proposal did not require human approval.",
                    severity="critical",
                )
                for proposal_id in unsafe
            ],
            verdict=EvidenceVerdict.SUPPORTED if not unsafe else EvidenceVerdict.CONTRADICTED,
            confidence=1.0 if not unsafe else 0.0,
        )
        return self._emit(event_bus, chain, phase=AgentPhase.LEARNING_PROPOSING)

    @staticmethod
    def _emit(event_bus: EventBus, chain: EvidenceChain, *, phase: AgentPhase) -> EvidenceChain:
        event = event_bus.append(
            AgentEventType.EVIDENCE_CHAIN_BUILT,
            f"Evidence chain built for {chain.decision_type}.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "chain_id": chain.id,
                "decision_type": chain.decision_type,
                "claim_id": chain.claim.id,
                "verdict": chain.verdict,
                "confidence": chain.confidence,
                "evidence_ref_ids": [ref.id for ref in chain.evidence],
                "contradiction_ids": [ref.id for ref in chain.contradictions],
            },
            trace_refs=chain.trace_refs,
        )
        return chain.model_copy(update={"trace_refs": [*chain.trace_refs, event.id]})

    @staticmethod
    def _critical_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
        return [finding for finding in findings if finding.severity == "critical"]

    @staticmethod
    def _trace_refs_from_findings(findings: list[ReviewFinding]) -> list[str]:
        refs: list[str] = []
        for finding in findings:
            refs.extend(finding.trace_refs)
        return list(dict.fromkeys(refs))


class EvidenceChainReviewer:
    """Verifies that traces include evidence chains before dependent decisions."""

    def review_events(self, events: list[AgentEvent] | tuple[AgentEvent, ...]) -> EvidenceChainReviewResult:
        trace = tuple(events)
        present, evidence_errors = self._evidence_positions(trace)
        errors: list[str] = []
        errors.extend(evidence_errors)

        self._require_chain_before(trace, present, EvidenceDecisionType.TOOL_SELECTION, AgentEventType.PLAN_CREATED, errors)
        self._require_chain_before(trace, present, EvidenceDecisionType.HYPOTHESIS_VERDICT, AgentEventType.PLAN_CREATED, errors)
        self._require_chain_before(trace, present, EvidenceDecisionType.PLAN_CREATION, AgentEventType.WORKER_STARTED, errors)
        self._require_chain_before(trace, present, EvidenceDecisionType.REPAIR_DECISION, AgentEventType.SUCCESS_EVALUATED, errors)

        learning_index = self._first_index(trace, AgentEventType.LEARNING_PROPOSED)
        if learning_index is not None and self._first_index(trace, AgentEventType.SUCCESS_EVALUATED, before=learning_index) is not None:
            self._require_decision_before(present, EvidenceDecisionType.SUCCESS_EVALUATION, learning_index, AgentEventType.LEARNING_PROPOSED, errors)

        completed_index = self._first_index(trace, AgentEventType.AGENT_COMPLETED)
        if completed_index is not None and self._first_index(trace, AgentEventType.LEARNING_PROPOSED, before=completed_index) is not None:
            self._require_decision_before(present, EvidenceDecisionType.LEARNING_PROPOSAL, completed_index, AgentEventType.AGENT_COMPLETED, errors)

        failed_index = self._first_index(trace, AgentEventType.AGENT_FAILED)
        if failed_index is not None and self._first_index(trace, AgentEventType.LEARNING_PROPOSED, before=failed_index) is not None:
            self._require_decision_before(present, EvidenceDecisionType.LEARNING_PROPOSAL, failed_index, AgentEventType.AGENT_FAILED, errors)

        block_index = self._first_index(trace, AgentEventType.AGENT_BLOCKED)
        if block_index is not None:
            if self._first_index(trace, AgentEventType.TOOLS_SELECTED, before=block_index) is not None:
                self._require_decision_before(present, EvidenceDecisionType.TOOL_SELECTION, block_index, AgentEventType.AGENT_BLOCKED, errors)
            if self._first_index(trace, AgentEventType.HYPOTHESES_REVIEWED, before=block_index) is not None:
                self._require_decision_before(present, EvidenceDecisionType.HYPOTHESIS_VERDICT, block_index, AgentEventType.AGENT_BLOCKED, errors)
            if self._first_index(trace, AgentEventType.PLAN_REVIEWED, before=block_index) is not None:
                self._require_decision_before(present, EvidenceDecisionType.PLAN_CREATION, block_index, AgentEventType.AGENT_BLOCKED, errors)

        escalate_index = self._first_index(trace, AgentEventType.AGENT_ESCALATED)
        if escalate_index is not None and self._first_index(trace, AgentEventType.REPAIR_DECIDED, before=escalate_index) is not None:
            self._require_decision_before(present, EvidenceDecisionType.REPAIR_DECISION, escalate_index, AgentEventType.AGENT_ESCALATED, errors)

        return EvidenceChainReviewResult(
            accepted=not errors,
            present_decision_types=sorted(present, key=lambda item: item.value),
            errors=errors,
        )

    @staticmethod
    def _evidence_positions(trace: tuple[AgentEvent, ...]) -> tuple[dict[EvidenceDecisionType, int], list[str]]:
        positions: dict[EvidenceDecisionType, int] = {}
        errors: list[str] = []
        for index, event in enumerate(trace):
            if event.event_type != AgentEventType.EVIDENCE_CHAIN_BUILT:
                continue
            raw_decision_type = event.payload.get("decision_type")
            try:
                decision_type = EvidenceDecisionType(raw_decision_type)
            except (TypeError, ValueError):
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            required_payload = ("chain_id", "claim_id", "verdict", "confidence", "evidence_ref_ids", "contradiction_ids")
            if any(key not in event.payload for key in required_payload):
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            if not event.payload.get("chain_id") or not event.payload.get("claim_id"):
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            try:
                EvidenceVerdict(event.payload.get("verdict"))
            except (TypeError, ValueError):
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            confidence = event.payload.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            if not isinstance(event.payload.get("evidence_ref_ids"), (list, tuple)) or not isinstance(event.payload.get("contradiction_ids"), (list, tuple)):
                errors.append(f"malformed_evidence_chain_event_{index}")
                continue
            positions.setdefault(decision_type, index)
        return positions, errors

    @staticmethod
    def _first_index(trace: tuple[AgentEvent, ...], event_type: AgentEventType, *, before: int | None = None) -> int | None:
        stop = before if before is not None else len(trace)
        for index, event in enumerate(trace[:stop]):
            if event.event_type == event_type:
                return index
        return None

    def _require_chain_before(
        self,
        trace: tuple[AgentEvent, ...],
        present: dict[EvidenceDecisionType, int],
        decision_type: EvidenceDecisionType,
        later: AgentEventType,
        errors: list[str],
    ) -> None:
        later_index = self._first_index(trace, later)
        if later_index is None:
            return
        self._require_decision_before(present, decision_type, later_index, later, errors)

    @staticmethod
    def _require_decision_before(
        present: dict[EvidenceDecisionType, int],
        decision_type: EvidenceDecisionType,
        later_index: int,
        later: AgentEventType,
        errors: list[str],
    ) -> None:
        position = present.get(decision_type)
        if position is None:
            errors.append(f"missing_evidence_chain_{decision_type.value}_before_{later.value}")
            return
        if position > later_index:
            errors.append(f"evidence_chain_{decision_type.value}_after_{later.value}")
