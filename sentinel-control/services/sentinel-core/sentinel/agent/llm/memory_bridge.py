from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash
from sentinel.shared.models import SentinelModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class FeedbackSignalKind(StrEnum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INVENTED_EVIDENCE_REF = "INVENTED_EVIDENCE_REF"
    CONTRADICTION = "CONTRADICTION"
    RISK_FLAG = "RISK_FLAG"
    BUDGET_WASTE = "BUDGET_WASTE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    BLOCKED_INTENT = "BLOCKED_INTENT"
    SUCCESSFUL_STRATEGY = "SUCCESSFUL_STRATEGY"
    USER_REVIEW_REQUIRED = "USER_REVIEW_REQUIRED"
    SELF_IMPROVEMENT_CANDIDATE = "SELF_IMPROVEMENT_CANDIDATE"
    STALE_MEMORY = "STALE_MEMORY"
    USER_CORRECTION = "USER_CORRECTION"
    DUPLICATE_SOURCE_SUPPRESSED = "DUPLICATE_SOURCE_SUPPRESSED"
    SELF_GENERATED_EVIDENCE_QUARANTINED = "SELF_GENERATED_EVIDENCE_QUARANTINED"


class FeedbackSignalSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class FeedbackMemoryStatus(StrEnum):
    ACCEPTED = "accepted"
    PARTIAL = "partial"
    REJECTED = "rejected"
    HISTORICAL_ONLY = "historical_only"


class MemoryClaimStatus(StrEnum):
    OBSERVED = "OBSERVED"
    CLAIMED = "CLAIMED"
    INFERRED = "INFERRED"
    SUPPORTED = "SUPPORTED"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    CONTRADICTED = "CONTRADICTED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class MemorySourceClass(StrEnum):
    user_instruction = "user_instruction"
    user_correction = "user_correction"
    receipt = "receipt"
    evidence = "evidence"
    role_output = "role_output"
    proposal_artifact = "proposal_artifact"
    verifier_result = "verifier_result"
    gate_result = "gate_result"
    finalgate_result = "finalgate_result"
    system_policy = "system_policy"
    external_observation = "external_observation"


class MemorySafetyValidationResult(SentinelModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    payload_hash: str | None = None
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_create_delegated_lane: bool = False
    can_unlock_credentials: bool = False
    can_override_provider_model: bool = False

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> MemorySafetyValidationResult:
        _assert_no_authority_or_execution(self)
        return self


class SafeFeedbackSignal(SentinelModel):
    signal_id: str
    mission_id: str
    loop_id: str
    kind: FeedbackSignalKind
    severity: FeedbackSignalSeverity = FeedbackSignalSeverity.INFO
    status: FeedbackMemoryStatus = FeedbackMemoryStatus.ACCEPTED
    source_id: str | None = None
    source_lineage_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    safe_summary: str
    signal_hash: str
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_create_delegated_lane: bool = False
    can_unlock_credentials: bool = False
    can_override_provider_model: bool = False

    @classmethod
    def build(
        cls,
        *,
        mission_id: str,
        loop_id: str,
        kind: FeedbackSignalKind,
        safe_summary: str,
        severity: FeedbackSignalSeverity = FeedbackSignalSeverity.INFO,
        status: FeedbackMemoryStatus = FeedbackMemoryStatus.ACCEPTED,
        source_id: str | None = None,
        source_lineage_id: str | None = None,
        evidence_refs: list[str] | None = None,
        receipt_refs: list[str] | None = None,
    ) -> SafeFeedbackSignal:
        payload = sanitize_metadata(
            {
                "mission_id": mission_id,
                "loop_id": loop_id,
                "kind": kind.value,
                "severity": severity.value,
                "status": status.value,
                "source_id": source_id,
                "source_lineage_id": source_lineage_id,
                "evidence_refs": evidence_refs or [],
                "receipt_refs": receipt_refs or [],
                "safe_summary": safe_summary,
            }
        )
        signal_hash = stable_hash(payload)
        return cls(
            signal_id=f"feedback_{signal_hash[:16]}",
            signal_hash=signal_hash,
            **payload,
        )

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> SafeFeedbackSignal:
        _assert_no_authority_or_execution(self)
        return self


class LivingMissionMemoryEntry(SentinelModel):
    memory_id: str
    mission_id: str
    source_class: MemorySourceClass
    source_id: str
    source_lineage_id: str
    source_scope: str
    validity_scope: str
    created_at: datetime
    observed_at: datetime
    expires_at: datetime | None = None
    ttl_seconds: int | None = Field(default=None, ge=0)
    claim_status: MemoryClaimStatus
    confidence: float = Field(ge=0.0, le=1.0)
    variance: float = Field(ge=0.0, le=1.0)
    contradiction_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    safe_summary: str
    historical_only: bool = False
    entry_hash: str | None = None
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_create_delegated_lane: bool = False
    can_unlock_credentials: bool = False
    can_override_provider_model: bool = False

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> LivingMissionMemoryEntry:
        _assert_no_authority_or_execution(self)
        return self

    def safe_payload(self) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "memory_id": self.memory_id,
                "mission_id": self.mission_id,
                "source_class": self.source_class.value,
                "source_id": self.source_id,
                "source_lineage_id": self.source_lineage_id,
                "source_scope": self.source_scope,
                "validity_scope": self.validity_scope,
                "created_at": self.created_at.isoformat(),
                "observed_at": self.observed_at.isoformat(),
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "ttl_seconds": self.ttl_seconds,
                "claim_status": self.claim_status.value,
                "confidence": self.confidence,
                "variance": self.variance,
                "contradiction_refs": self.contradiction_refs,
                "evidence_refs": self.evidence_refs,
                "receipt_refs": self.receipt_refs,
                "uncertainty": self.uncertainty,
                "safe_summary": self.safe_summary,
                "historical_only": self.historical_only,
                "authority_effect": self.authority_effect,
                "execution_effect": self.execution_effect,
            }
        )


class LivingMissionMemorySnapshot(SentinelModel):
    mission_id: str
    loop_id: str
    memory_entry_ids: list[str] = Field(default_factory=list)
    feedback_signal_count: int = Field(default=0, ge=0)
    evidence_gap_count: int = Field(default=0, ge=0)
    contradiction_count: int = Field(default=0, ge=0)
    risk_flag_count: int = Field(default=0, ge=0)
    blocked_action_count: int = Field(default=0, ge=0)
    budget_issue_count: int = Field(default=0, ge=0)
    learned_pattern_count: int = Field(default=0, ge=0)
    expired_memory_count: int = Field(default=0, ge=0)
    duplicate_source_suppression_count: int = Field(default=0, ge=0)
    self_generated_evidence_quarantine_count: int = Field(default=0, ge=0)
    safe_summary: str
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> LivingMissionMemorySnapshot:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("Memory snapshots cannot grant authority or execution.")
        return self


class MemoryBridgeInput(SentinelModel):
    mission_id: str
    loop_id: str
    memory_items: list[dict[str, Any]] = Field(default_factory=list)
    existing_entries: list[LivingMissionMemoryEntry | dict[str, Any]] = Field(default_factory=list)
    role_loop_receipts: list[dict[str, Any]] = Field(default_factory=list)
    proposal_receipts: list[dict[str, Any]] = Field(default_factory=list)
    evidence_verification_results: list[Any] = Field(default_factory=list)
    proposal_validation_results: list[Any] = Field(default_factory=list)
    final_packet: dict[str, Any] = Field(default_factory=dict)
    budget_summaries: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    unresolved_objections: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    invented_evidence_refs: list[str] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    blocked_intents: list[str] = Field(default_factory=list)
    user_review_required: list[str] = Field(default_factory=list)
    self_improvement_candidates: list[dict[str, Any]] = Field(default_factory=list)
    current_time: datetime = Field(default_factory=utc_now)


class MemoryBridgeResult(SentinelModel):
    mission_id: str
    loop_id: str
    status: FeedbackMemoryStatus
    memory_entries: list[LivingMissionMemoryEntry] = Field(default_factory=list)
    feedback_signals: list[SafeFeedbackSignal] = Field(default_factory=list)
    snapshot: LivingMissionMemorySnapshot
    safety_validation: MemorySafetyValidationResult
    retrieval_contract: str = "data_not_instruction"
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_create_delegated_lane: bool = False
    can_unlock_credentials: bool = False
    can_override_provider_model: bool = False

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> MemoryBridgeResult:
        _assert_no_authority_or_execution(self)
        if self.retrieval_contract != "data_not_instruction":
            raise ValueError("Memory retrieval must remain data, not instruction.")
        return self


class RoleLoopMemoryBridge:
    def build(self, bridge_input: MemoryBridgeInput | dict[str, Any]) -> MemoryBridgeResult:
        if not isinstance(bridge_input, MemoryBridgeInput):
            bridge_input = MemoryBridgeInput.model_validate(bridge_input)

        safety = validate_memory_payload(bridge_input.model_dump(mode="json"))
        if not safety.valid:
            feedback = [
                _signal(
                    bridge_input,
                    FeedbackSignalKind.BLOCKED_INTENT,
                    "Blocked unsafe memory payload before persistence.",
                    severity=FeedbackSignalSeverity.BLOCKING,
                    status=FeedbackMemoryStatus.REJECTED,
                )
            ]
            snapshot = _snapshot(bridge_input, [], feedback)
            return MemoryBridgeResult(
                mission_id=bridge_input.mission_id,
                loop_id=bridge_input.loop_id,
                status=FeedbackMemoryStatus.REJECTED,
                memory_entries=[],
                feedback_signals=feedback,
                snapshot=snapshot,
                safety_validation=safety,
            )

        feedback: list[SafeFeedbackSignal] = []
        entries: list[LivingMissionMemoryEntry] = []
        seen_lineages: set[str] = set()

        for existing in bridge_input.existing_entries:
            entry = existing if isinstance(existing, LivingMissionMemoryEntry) else LivingMissionMemoryEntry.model_validate(existing)
            entries.append(entry)
            seen_lineages.add(entry.source_lineage_id)

        for item in bridge_input.memory_items:
            source_lineage_id = str(item.get("source_lineage_id") or item.get("source_id") or "")
            if source_lineage_id in seen_lineages:
                feedback.append(
                    _signal(
                        bridge_input,
                        FeedbackSignalKind.DUPLICATE_SOURCE_SUPPRESSED,
                        "Duplicate source lineage suppressed; repetition is not verification.",
                        source_id=str(item.get("source_id") or ""),
                        source_lineage_id=source_lineage_id,
                    )
                )
                continue
            entry, item_feedback = _entry_from_item(bridge_input, item)
            entries.append(entry)
            seen_lineages.add(entry.source_lineage_id)
            feedback.extend(item_feedback)

        entries, correction_feedback = _apply_user_correction_precedence(bridge_input, entries)
        feedback.extend(correction_feedback)
        feedback.extend(_signals_from_bridge_input(bridge_input))

        snapshot = _snapshot(bridge_input, entries, feedback)
        status = FeedbackMemoryStatus.PARTIAL if any(signal.severity is FeedbackSignalSeverity.ERROR for signal in feedback) else FeedbackMemoryStatus.ACCEPTED
        if entries and all(entry.historical_only for entry in entries):
            status = FeedbackMemoryStatus.HISTORICAL_ONLY
        return MemoryBridgeResult(
            mission_id=bridge_input.mission_id,
            loop_id=bridge_input.loop_id,
            status=status,
            memory_entries=entries,
            feedback_signals=feedback,
            snapshot=snapshot,
            safety_validation=safety,
        )


def validate_memory_payload(payload: Any) -> MemorySafetyValidationResult:
    rejected_paths = _scan_forbidden_payload(payload)
    sanitized = sanitize_metadata(payload)
    return MemorySafetyValidationResult(
        valid=not rejected_paths,
        reasons=["forbidden_memory_payload"] if rejected_paths else [],
        rejected_paths=rejected_paths,
        payload_hash=stable_hash(sanitized),
    )


def _entry_from_item(
    bridge_input: MemoryBridgeInput,
    item: dict[str, Any],
) -> tuple[LivingMissionMemoryEntry, list[SafeFeedbackSignal]]:
    now = bridge_input.current_time
    source_class = _source_class(item.get("source_class"))
    source_id = str(item.get("source_id") or f"{source_class.value}_source")
    source_lineage_id = str(item.get("source_lineage_id") or source_id)
    claim_status = _claim_status(item.get("claim_status"))
    evidence_refs = _string_list(item.get("evidence_refs"))
    receipt_refs = _string_list(item.get("receipt_refs"))
    contradiction_refs = _string_list(item.get("contradiction_refs"))
    expires_at = _expires_at(item, now)
    historical_only = expires_at is not None and expires_at <= now
    feedback: list[SafeFeedbackSignal] = []

    if historical_only:
        claim_status = MemoryClaimStatus.EXPIRED
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.STALE_MEMORY,
                "Expired memory returned as historical context only.",
                source_id=source_id,
                source_lineage_id=source_lineage_id,
            )
        )

    if contradiction_refs and claim_status not in {MemoryClaimStatus.EXPIRED, MemoryClaimStatus.SUPERSEDED}:
        claim_status = MemoryClaimStatus.CONTRADICTED

    if _is_self_generated(source_class) and claim_status is MemoryClaimStatus.SUPPORTED and not evidence_refs:
        claim_status = MemoryClaimStatus.CLAIMED
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.SELF_GENERATED_EVIDENCE_QUARANTINED,
                "Self-generated memory quarantined from independent evidence support.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=source_id,
                source_lineage_id=source_lineage_id,
                receipt_refs=receipt_refs,
            )
        )

    payload = sanitize_metadata(
        {
            "mission_id": bridge_input.mission_id,
            "source_class": source_class.value,
            "source_id": source_id,
            "source_lineage_id": source_lineage_id,
            "source_scope": str(item.get("source_scope") or bridge_input.mission_id),
            "validity_scope": str(item.get("validity_scope") or bridge_input.mission_id),
            "claim_status": claim_status.value,
            "safe_summary": str(item.get("safe_summary") or ""),
        }
    )
    memory_hash = stable_hash(payload)
    entry = LivingMissionMemoryEntry(
        memory_id=str(item.get("memory_id") or f"memory_{memory_hash[:16]}"),
        mission_id=bridge_input.mission_id,
        source_class=source_class,
        source_id=source_id,
        source_lineage_id=source_lineage_id,
        source_scope=str(item.get("source_scope") or bridge_input.mission_id),
        validity_scope=str(item.get("validity_scope") or bridge_input.mission_id),
        created_at=_datetime_or_now(item.get("created_at"), now),
        observed_at=_datetime_or_now(item.get("observed_at"), now),
        expires_at=expires_at,
        ttl_seconds=_optional_int(item.get("ttl_seconds") or item.get("ttl")),
        claim_status=claim_status,
        confidence=_bounded_float(item.get("confidence"), default=0.5),
        variance=_bounded_float(item.get("variance"), default=0.5),
        contradiction_refs=contradiction_refs,
        evidence_refs=evidence_refs,
        receipt_refs=receipt_refs,
        uncertainty=_string_list(item.get("uncertainty")),
        safe_summary=str(item.get("safe_summary") or ""),
        historical_only=historical_only,
        entry_hash=memory_hash,
    )
    return entry, feedback


def _apply_user_correction_precedence(
    bridge_input: MemoryBridgeInput,
    entries: list[LivingMissionMemoryEntry],
) -> tuple[list[LivingMissionMemoryEntry], list[SafeFeedbackSignal]]:
    correction_scopes = {
        entry.validity_scope
        for entry in entries
        if entry.source_class is MemorySourceClass.user_correction
    }
    if not correction_scopes:
        return entries, []

    feedback = [
        _signal(
            bridge_input,
            FeedbackSignalKind.USER_CORRECTION,
            "User correction preserved with precedence over inferred memory in scope.",
        )
    ]
    updated: list[LivingMissionMemoryEntry] = []
    for entry in entries:
        if (
            entry.validity_scope in correction_scopes
            and entry.source_class is not MemorySourceClass.user_correction
            and entry.claim_status in {MemoryClaimStatus.INFERRED, MemoryClaimStatus.CLAIMED}
        ):
            updated.append(
                entry.model_copy(
                    update={
                        "claim_status": MemoryClaimStatus.SUPERSEDED,
                        "contradiction_refs": _dedupe([*entry.contradiction_refs, "user_correction"]),
                    }
                )
            )
        else:
            updated.append(entry)
    return updated, feedback


def _signals_from_bridge_input(bridge_input: MemoryBridgeInput) -> list[SafeFeedbackSignal]:
    feedback: list[SafeFeedbackSignal] = []

    for claim_id in bridge_input.missing_evidence:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.MISSING_EVIDENCE,
                f"Missing evidence for {claim_id}.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=str(claim_id),
            )
        )
    for ref in bridge_input.invented_evidence_refs:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.INVENTED_EVIDENCE_REF,
                f"Invented evidence ref rejected: {ref}.",
                severity=FeedbackSignalSeverity.ERROR,
                source_id=str(ref),
            )
        )
    for contradiction in bridge_input.contradictions:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.CONTRADICTION,
                "Contradiction preserved for future verification.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=str(contradiction.get("claim_id") or "contradiction"),
                evidence_refs=_string_list(contradiction.get("evidence_refs")),
            )
        )
    for risk in bridge_input.risk_flags:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.RISK_FLAG,
                f"Risk flag preserved: {risk}.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=str(risk),
            )
        )
    for budget in bridge_input.budget_summaries:
        compliant = bool(budget.get("compliant", True))
        decision = str(budget.get("decision") or "")
        if not compliant or "exhausted" in decision.lower():
            kind = FeedbackSignalKind.BUDGET_EXHAUSTED if "exhausted" in decision.lower() else FeedbackSignalKind.BUDGET_WASTE
            feedback.append(
                _signal(
                    bridge_input,
                    kind,
                    f"Budget issue preserved: {decision or 'non_compliant_budget'}.",
                    severity=FeedbackSignalSeverity.WARNING,
                    source_id=decision or "budget",
                )
            )
    for blocked in bridge_input.blocked_intents:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.BLOCKED_INTENT,
                f"Blocked intent preserved: {blocked}.",
                severity=FeedbackSignalSeverity.ERROR,
                source_id=str(blocked),
            )
        )
    for review_ref in bridge_input.user_review_required:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.USER_REVIEW_REQUIRED,
                f"User review required before any future execution: {review_ref}.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=str(review_ref),
            )
        )
    for candidate in bridge_input.self_improvement_candidates:
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.SELF_IMPROVEMENT_CANDIDATE,
                str(candidate.get("safe_summary") or "Self-improvement candidate remains proposal-only."),
                source_id=str(candidate.get("id") or "self_improvement_candidate"),
            )
        )

    for result in bridge_input.evidence_verification_results:
        feedback.extend(_signals_from_evidence_result(bridge_input, result))
    for result in bridge_input.proposal_validation_results:
        feedback.extend(_signals_from_proposal_validation(bridge_input, result))
    return feedback


def _signals_from_evidence_result(bridge_input: MemoryBridgeInput, result: Any) -> list[SafeFeedbackSignal]:
    verdict = str(_read_attr(result, "verdict") or "")
    invented = _string_list(_read_attr(result, "invented_evidence_refs"))
    missing = _string_list(_read_attr(result, "missing_evidence_claim_ids"))
    contradictions = _read_attr(result, "contradictions") or []
    feedback: list[SafeFeedbackSignal] = []
    if "INVENTED_EVIDENCE_REF" in verdict:
        for ref in invented or ["invented_evidence_ref"]:
            feedback.append(
                _signal(
                    bridge_input,
                    FeedbackSignalKind.INVENTED_EVIDENCE_REF,
                    f"Invented evidence ref rejected: {ref}.",
                    severity=FeedbackSignalSeverity.ERROR,
                    source_id=ref,
                )
            )
    if "MISSING_EVIDENCE" in verdict:
        for claim in missing or ["missing_evidence"]:
            feedback.append(
                _signal(
                    bridge_input,
                    FeedbackSignalKind.MISSING_EVIDENCE,
                    f"Missing evidence for {claim}.",
                    severity=FeedbackSignalSeverity.WARNING,
                    source_id=claim,
                )
            )
    if "CONTRADICTED" in verdict:
        for contradiction in contradictions or [{"claim_id": "contradiction"}]:
            feedback.append(
                _signal(
                    bridge_input,
                    FeedbackSignalKind.CONTRADICTION,
                    "Contradiction preserved from verifier result.",
                    severity=FeedbackSignalSeverity.WARNING,
                    source_id=str(_read_attr(contradiction, "claim_id") or "contradiction"),
                    evidence_refs=_string_list(_read_attr(contradiction, "evidence_refs")),
                )
            )
    return feedback


def _signals_from_proposal_validation(bridge_input: MemoryBridgeInput, result: Any) -> list[SafeFeedbackSignal]:
    feedback: list[SafeFeedbackSignal] = []
    if bool(_read_attr(result, "missing_evidence")):
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.MISSING_EVIDENCE,
                "Proposal validation requires more evidence.",
                severity=FeedbackSignalSeverity.WARNING,
                source_id=str(_read_attr(result, "proposal_hash") or "proposal"),
            )
        )
    for ref in _string_list(_read_attr(result, "invented_evidence_refs")):
        feedback.append(
            _signal(
                bridge_input,
                FeedbackSignalKind.INVENTED_EVIDENCE_REF,
                f"Proposal validation rejected invented evidence ref: {ref}.",
                severity=FeedbackSignalSeverity.ERROR,
                source_id=ref,
            )
        )
    return feedback


def _snapshot(
    bridge_input: MemoryBridgeInput,
    entries: list[LivingMissionMemoryEntry],
    feedback: list[SafeFeedbackSignal],
) -> LivingMissionMemorySnapshot:
    signal_kinds = [signal.kind for signal in feedback]
    contradiction_refs = _dedupe(
        [
            ref
            for entry in entries
            for ref in entry.contradiction_refs
        ]
    )
    return LivingMissionMemorySnapshot(
        mission_id=bridge_input.mission_id,
        loop_id=bridge_input.loop_id,
        memory_entry_ids=[entry.memory_id for entry in entries],
        feedback_signal_count=len(feedback),
        evidence_gap_count=sum(
            1
            for kind in signal_kinds
            if kind in {FeedbackSignalKind.MISSING_EVIDENCE, FeedbackSignalKind.INVENTED_EVIDENCE_REF}
        ),
        contradiction_count=len(contradiction_refs)
        + sum(1 for kind in signal_kinds if kind is FeedbackSignalKind.CONTRADICTION),
        risk_flag_count=sum(1 for kind in signal_kinds if kind is FeedbackSignalKind.RISK_FLAG),
        blocked_action_count=sum(1 for kind in signal_kinds if kind is FeedbackSignalKind.BLOCKED_INTENT),
        budget_issue_count=sum(
            1
            for kind in signal_kinds
            if kind in {FeedbackSignalKind.BUDGET_WASTE, FeedbackSignalKind.BUDGET_EXHAUSTED}
        ),
        learned_pattern_count=sum(1 for kind in signal_kinds if kind is FeedbackSignalKind.SUCCESSFUL_STRATEGY),
        expired_memory_count=sum(1 for entry in entries if entry.claim_status is MemoryClaimStatus.EXPIRED),
        duplicate_source_suppression_count=sum(
            1 for kind in signal_kinds if kind is FeedbackSignalKind.DUPLICATE_SOURCE_SUPPRESSED
        ),
        self_generated_evidence_quarantine_count=sum(
            1 for kind in signal_kinds if kind is FeedbackSignalKind.SELF_GENERATED_EVIDENCE_QUARANTINED
        ),
        safe_summary=(
            f"Memory snapshot contains {len(entries)} entries and {len(feedback)} feedback signals. "
            "Authority effect none; execution effect none."
        ),
    )


def _signal(
    bridge_input: MemoryBridgeInput,
    kind: FeedbackSignalKind,
    safe_summary: str,
    *,
    severity: FeedbackSignalSeverity = FeedbackSignalSeverity.INFO,
    status: FeedbackMemoryStatus = FeedbackMemoryStatus.ACCEPTED,
    source_id: str | None = None,
    source_lineage_id: str | None = None,
    evidence_refs: list[str] | None = None,
    receipt_refs: list[str] | None = None,
) -> SafeFeedbackSignal:
    return SafeFeedbackSignal.build(
        mission_id=bridge_input.mission_id,
        loop_id=bridge_input.loop_id,
        kind=kind,
        safe_summary=safe_summary,
        severity=severity,
        status=status,
        source_id=source_id,
        source_lineage_id=source_lineage_id,
        evidence_refs=evidence_refs,
        receipt_refs=receipt_refs,
    )


def _scan_forbidden_payload(payload: Any, path: str = "$") -> list[str]:
    rejected: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{key}"
            if normalized in _FORBIDDEN_MEMORY_KEYS and _truthy_payload(value):
                rejected.append(child_path)
                continue
            rejected.extend(_scan_forbidden_payload(value, child_path))
        return rejected
    if isinstance(payload, list | tuple | set):
        for index, value in enumerate(payload):
            rejected.extend(_scan_forbidden_payload(value, f"{path}[{index}]"))
        return rejected
    if isinstance(payload, str) and _contains_forbidden_text(payload):
        rejected.append(path)
    return rejected


def _contains_forbidden_text(value: str) -> bool:
    lowered = value.lower()
    if _SECRET_LIKE_PATTERN.search(value):
        return True
    return any(marker in lowered for marker in _FORBIDDEN_MEMORY_TEXT)


def _truthy_payload(value: Any) -> bool:
    return value not in (None, False, "", [], {})


def _assert_no_authority_or_execution(model: Any) -> None:
    if getattr(model, "authority_effect", "none") != "none":
        raise ValueError("Memory cannot grant authority.")
    if getattr(model, "execution_effect", "none") != "none":
        raise ValueError("Memory cannot execute.")
    forbidden_flags = {
        "can_grant_authority": "grant authority",
        "can_approve_execution": "approve execution",
        "can_create_delegated_lane": "create delegated lanes",
        "can_unlock_credentials": "unlock credentials",
        "can_override_provider_model": "override provider/model",
    }
    for field, message in forbidden_flags.items():
        if bool(getattr(model, field, False)):
            raise ValueError(f"Memory cannot {message}.")


def _source_class(value: Any) -> MemorySourceClass:
    if isinstance(value, MemorySourceClass):
        return value
    return MemorySourceClass(str(value or MemorySourceClass.external_observation.value))


def _claim_status(value: Any) -> MemoryClaimStatus:
    if isinstance(value, MemoryClaimStatus):
        return value
    return MemoryClaimStatus(str(value or MemoryClaimStatus.UNKNOWN.value))


def _is_self_generated(source_class: MemorySourceClass) -> bool:
    return source_class in {
        MemorySourceClass.role_output,
        MemorySourceClass.proposal_artifact,
        MemorySourceClass.receipt,
    }


def _expires_at(item: dict[str, Any], now: datetime) -> datetime | None:
    explicit = _coerce_datetime(item.get("expires_at"))
    if explicit is not None:
        return explicit
    ttl = _optional_int(item.get("ttl_seconds") or item.get("ttl"))
    if ttl is None:
        return None
    return now + timedelta(seconds=ttl)


def _datetime_or_now(value: Any, now: datetime) -> datetime:
    return _coerce_datetime(value) or now


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _read_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


_FORBIDDEN_MEMORY_KEYS = {
    "api_key",
    "authorization",
    "authority_expansion",
    "backend_override",
    "bearer",
    "browser_submit",
    "chain_of_thought",
    "credential",
    "delegated_lane_creation",
    "direct_action",
    "execute_now",
    "mission_envelope_expansion",
    "model_override",
    "organ_execution",
    "password",
    "payment",
    "process",
    "prompt",
    "provider_override",
    "provider_response",
    "raw_prompt",
    "raw_response",
    "reasoning",
    "secret",
    "send_email",
    "shell",
    "spend",
    "terminal",
    "thinking",
    "token",
    "tool_calls",
    "trade",
}

_FORBIDDEN_MEMORY_TEXT = {
    "authority_expansion",
    "backend_override",
    "browser_submit",
    "chain_of_thought",
    "credential access",
    "delegated_lane_creation",
    "direct_action",
    "execute_now",
    "mission_envelope_expansion",
    "model_override",
    "organ_execution",
    "provider_override",
    "raw_prompt",
    "raw_response",
    "send_email",
    "shell/process",
    "tool_calls",
}

_SECRET_LIKE_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9_\-]{12,}|gsk_[A-Za-z0-9]+|nvapi-[A-Za-z0-9]+|sk-or-v1-[A-Za-z0-9]+)",
    re.IGNORECASE,
)
