from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.agent.llm.memory_bridge import (
    LivingMissionMemoryEntry,
    MemoryBridgeResult,
    MemoryClaimStatus,
    MemorySourceClass,
)
from sentinel.memory.models import (
    MemoryIngestBatchResult,
    MemoryNamespace,
    MemoryNamespaceKind,
    MemoryTrustClass,
    PersistentMemoryQuery,
    PersistentMemoryRetrievalResult,
)
from sentinel.memory.service import PersistentSemanticMemoryService
from sentinel.shared.models import SentinelModel


class PersistentMemoryRecallBundle(SentinelModel):
    entries: list[LivingMissionMemoryEntry] = Field(default_factory=list)
    retrieval: PersistentMemoryRetrievalResult
    authority_effect: str = "none"
    execution_effect: str = "none"
    data_not_instruction: bool = True
    can_grant_authority: bool = False
    can_approve_execution: bool = False

    @model_validator(mode="after")
    def _bundle_is_data_only(self) -> PersistentMemoryRecallBundle:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("persistent memory recall cannot grant authority or execute")
        if self.data_not_instruction is not True:
            raise ValueError("persistent memory recall must remain data")
        if self.can_grant_authority or self.can_approve_execution:
            raise ValueError("persistent memory recall cannot authorize execution")
        return self


class PersistentMemoryRecallAdapter:
    """Projects durable records into the existing safe in-process memory contract."""

    def __init__(self, service: PersistentSemanticMemoryService) -> None:
        self.service = service

    def recall(
        self,
        *,
        owner_user_id: str,
        mission_id: str,
        query_text: str,
        current_time: datetime,
        entity_ids: list[str] | None = None,
        procedure_ids: list[str] | None = None,
        include_historical: bool = False,
        max_hits: int = 20,
    ) -> PersistentMemoryRecallBundle:
        retrieval = self.service.retrieve(
            PersistentMemoryQuery(
                requester_user_id=owner_user_id,
                mission_id=mission_id,
                query_text=query_text,
                entity_ids=list(entity_ids or []),
                procedure_ids=list(procedure_ids or []),
                include_historical=include_historical,
                max_hits=max_hits,
                current_time=current_time,
            )
        )
        entries = [
            LivingMissionMemoryEntry(
                memory_id=hit.record_id,
                mission_id=mission_id,
                source_class=hit.source_class,
                source_id=hit.source_id,
                source_lineage_id=hit.source_lineage_id,
                source_scope=hit.source_scope,
                validity_scope=mission_id,
                created_at=hit.created_at,
                observed_at=hit.observed_at,
                expires_at=hit.expires_at,
                claim_status=_projected_claim_status(hit.trust_class, hit.claim_status),
                confidence=_projected_confidence(hit.trust_class, hit.confidence),
                variance=_projected_variance(hit.trust_class, hit.variance),
                contradiction_refs=hit.contradiction_refs,
                evidence_refs=hit.evidence_refs,
                receipt_refs=hit.receipt_refs,
                uncertainty=[
                    "Persistent recall is scoped untrusted data; verify before use."
                ],
                safe_summary=hit.safe_summary,
                historical_only=hit.is_historical_only,
                entry_hash=None,
            )
            for hit in retrieval.hits
        ]
        return PersistentMemoryRecallBundle(entries=entries, retrieval=retrieval)


class PersistentMemoryIngestAdapter:
    """Writes existing memory bridge entries through the durable memory contract."""

    def __init__(self, service: PersistentSemanticMemoryService) -> None:
        self.service = service

    def persist_bridge_result(
        self,
        bridge_result: MemoryBridgeResult,
        *,
        requester_user_id: str,
    ) -> MemoryIngestBatchResult:
        accepted: list[str] = []
        rejected: list[str] = []
        reasons: dict[str, list[str]] = {}
        for entry in bridge_result.memory_entries:
            result = self.service.ingest_entry(
                entry,
                requester_user_id=requester_user_id,
                namespace=MemoryNamespace(
                    kind=MemoryNamespaceKind.MISSION,
                    owner_user_id=requester_user_id,
                    mission_id=entry.mission_id,
                ),
                trust_class=_requested_trust_class(entry.source_class),
            )
            if result.accepted and result.record is not None:
                accepted.append(result.record.record_id)
                continue
            rejected.append(entry.memory_id)
            reasons[entry.memory_id] = list(result.reasons)
        return MemoryIngestBatchResult(
            accepted_record_ids=accepted,
            rejected_source_memory_ids=rejected,
            rejection_reasons=reasons,
        )


def _requested_trust_class(source_class: MemorySourceClass) -> MemoryTrustClass:
    if source_class in {MemorySourceClass.user_instruction, MemorySourceClass.user_correction}:
        return MemoryTrustClass.USER_CONFIRMED
    if source_class is MemorySourceClass.evidence:
        return MemoryTrustClass.EVIDENCE_BOUND
    if source_class is MemorySourceClass.receipt:
        return MemoryTrustClass.RECEIPT_BOUND
    if source_class in {MemorySourceClass.verifier_result, MemorySourceClass.finalgate_result}:
        return MemoryTrustClass.VERIFIED_RESULT
    if source_class is MemorySourceClass.role_output:
        return MemoryTrustClass.INFERRED
    return MemoryTrustClass.UNTRUSTED


def _projected_claim_status(
    trust_class: MemoryTrustClass,
    claim_status: MemoryClaimStatus,
) -> MemoryClaimStatus:
    if trust_class in {MemoryTrustClass.INFERRED, MemoryTrustClass.UNTRUSTED}:
        return MemoryClaimStatus.UNKNOWN
    return claim_status


def _projected_confidence(trust_class: MemoryTrustClass, confidence: float) -> float:
    if trust_class in {MemoryTrustClass.INFERRED, MemoryTrustClass.UNTRUSTED}:
        return min(confidence, 0.25)
    return confidence


def _projected_variance(trust_class: MemoryTrustClass, variance: float) -> float:
    if trust_class in {MemoryTrustClass.INFERRED, MemoryTrustClass.UNTRUSTED}:
        return max(variance, 0.75)
    return variance
