from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sentinel.agent.llm.memory_bridge import (
    LivingMissionMemoryEntry,
    MemoryClaimStatus,
    MemorySourceClass,
)
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.memory.indexes import (
    cosine_similarity,
    entity_score,
    lexical_score,
    provenance_score,
    semantic_vector,
)
from sentinel.memory.models import (
    MemoryDeletionReceipt,
    MemoryExpiryResult,
    MemoryIngestResult,
    MemoryNamespace,
    MemoryNamespaceKind,
    MemoryProvenance,
    MemoryRecord,
    MemoryTombstone,
    MemoryTrustClass,
    PersistentMemoryHit,
    PersistentMemoryQuery,
    PersistentMemoryRetrievalResult,
)
from sentinel.memory.sanitizer import (
    memory_text_rejection_reasons,
    sanitize_memory_payload,
    sanitize_memory_text,
)
from sentinel.memory.store import (
    DuplicateMemoryError,
    DurableMemoryStore,
    SupersessionTargetError,
    record_hash_payload,
)


class PersistentSemanticMemoryService:
    def __init__(
        self,
        database_path: Path | str,
        *,
        provenance_ref_validator: Callable[[LivingMissionMemoryEntry, MemoryTrustClass], bool]
        | None = None,
    ) -> None:
        self.store = DurableMemoryStore(database_path)
        self._provenance_ref_validator = provenance_ref_validator

    def close(self) -> None:
        self.store.close()

    def ingest_payload(
        self,
        payload: dict[str, Any],
        *,
        requester_user_id: str,
    ) -> MemoryIngestResult:
        sanitized, rejected_paths, payload_hash = sanitize_memory_payload(payload)
        if rejected_paths:
            return MemoryIngestResult(
                accepted=False,
                reasons=["forbidden_memory_payload"],
                rejected_payload_hash=payload_hash,
            )
        try:
            entry = LivingMissionMemoryEntry.model_validate(sanitized["entry"])
            namespace = MemoryNamespace.model_validate(sanitized["namespace"])
            trust_class = MemoryTrustClass(
                sanitized.get("trust_class", MemoryTrustClass.UNTRUSTED.value)
            )
        except (KeyError, ValueError, TypeError):
            return MemoryIngestResult(
                accepted=False,
                reasons=["invalid_memory_payload"],
                rejected_payload_hash=payload_hash,
            )
        return self.ingest_entry(
            entry,
            requester_user_id=requester_user_id,
            namespace=namespace,
            entity_refs=list(sanitized.get("entity_refs", [])),
            procedure_refs=list(sanitized.get("procedure_refs", [])),
            supersedes_refs=list(sanitized.get("supersedes_refs", [])),
            trust_class=trust_class,
        )

    def ingest_entry(
        self,
        entry: LivingMissionMemoryEntry,
        *,
        requester_user_id: str,
        namespace: MemoryNamespace,
        entity_refs: list[str] | None = None,
        procedure_refs: list[str] | None = None,
        supersedes_refs: list[str] | None = None,
        trust_class: MemoryTrustClass = MemoryTrustClass.UNTRUSTED,
    ) -> MemoryIngestResult:
        if not requester_user_id.strip() or namespace.owner_user_id != requester_user_id:
            return MemoryIngestResult(
                accepted=False,
                reasons=["memory_requester_owner_mismatch"],
                rejected_payload_hash=stable_hash(
                    {"requester_user_id": requester_user_id, "namespace": namespace.model_dump(mode="json")}
                ),
            )
        redacted_payload, rejected_paths, payload_hash = sanitize_memory_payload(
            {
                "entry": entry.model_dump(mode="json"),
                "namespace": namespace.model_dump(mode="json"),
                "entity_refs": list(entity_refs or []),
                "procedure_refs": list(procedure_refs or []),
                "supersedes_refs": list(supersedes_refs or []),
            }
        )
        if rejected_paths:
            return MemoryIngestResult(
                accepted=False,
                reasons=["forbidden_memory_payload"],
                rejected_payload_hash=payload_hash,
            )
        entry = LivingMissionMemoryEntry.model_validate(redacted_payload["entry"])
        namespace = MemoryNamespace.model_validate(redacted_payload["namespace"])
        entity_refs = list(redacted_payload["entity_refs"])
        procedure_refs = list(redacted_payload["procedure_refs"])
        supersedes_refs = list(redacted_payload["supersedes_refs"])
        safe_summary = entry.safe_summary
        safe_uncertainty = list(entry.uncertainty)
        reasons = memory_text_rejection_reasons(safe_summary)
        if reasons:
            return MemoryIngestResult(
                accepted=False,
                reasons=reasons,
                rejected_payload_hash=stable_hash({"summary": safe_summary}),
            )
        if namespace.kind is MemoryNamespaceKind.MISSION and namespace.mission_id != entry.mission_id:
            return MemoryIngestResult(
                accepted=False,
                reasons=["mission_namespace_mismatch"],
                rejected_payload_hash=stable_hash(entry.safe_payload()),
            )
        if namespace.kind is MemoryNamespaceKind.ENTITY and namespace.entity_id not in entity_refs:
            return MemoryIngestResult(
                accepted=False,
                reasons=["entity_namespace_reference_missing"],
                rejected_payload_hash=stable_hash(entry.safe_payload()),
            )
        if namespace.kind is MemoryNamespaceKind.PROCEDURE and namespace.procedure_id not in procedure_refs:
            return MemoryIngestResult(
                accepted=False,
                reasons=["procedure_namespace_reference_missing"],
                rejected_payload_hash=stable_hash(entry.safe_payload()),
            )

        effective_trust, trust_reasons = _validated_trust_class(
            entry,
            trust_class,
            provenance_ref_validator=self._provenance_ref_validator,
        )

        content_hash = stable_hash(
            {
                "namespace": namespace.model_dump(mode="json"),
                "safe_summary": safe_summary,
                "validity_scope": entry.validity_scope,
            }
        )
        duplicate = self.store.find_duplicate(
            owner_user_id=namespace.owner_user_id,
            source_lineage_id=entry.source_lineage_id,
            content_hash=content_hash,
        )
        if duplicate is not None:
            return MemoryIngestResult(
                accepted=False,
                reasons=["duplicate_lineage_or_content"],
                rejected_payload_hash=content_hash,
            )

        record_payload = {
            "record_id": f"pmem_{stable_hash({'owner': namespace.owner_user_id, 'namespace': namespace.model_dump(mode='json'), 'source_memory_id': entry.memory_id})[:24]}",
            "source_memory_id": entry.memory_id,
            "namespace": namespace.model_dump(mode="json"),
            "mission_id": entry.mission_id,
            "provenance": MemoryProvenance(
                source_class=entry.source_class,
                source_id=entry.source_id,
                source_lineage_id=entry.source_lineage_id,
                trust_class=effective_trust,
                source_scope=entry.source_scope,
                evidence_refs=list(entry.evidence_refs),
                receipt_refs=list(entry.receipt_refs),
            ).model_dump(mode="json"),
            "validity_scope": entry.validity_scope,
            "safe_summary": safe_summary,
            "uncertainty": safe_uncertainty,
            "entity_refs": _dedupe(entity_refs or []),
            "procedure_refs": _dedupe(procedure_refs or []),
            "contradiction_refs": _dedupe(entry.contradiction_refs),
            "supersedes_refs": _dedupe(supersedes_refs or []),
            "superseded_by_refs": [],
            "claim_status": entry.claim_status.value,
            "confidence": entry.confidence,
            "variance": entry.variance,
            "created_at": entry.created_at.isoformat(),
            "observed_at": entry.observed_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "historical_only": entry.historical_only,
            "content_hash": content_hash,
            "record_hash": "",
            "authority_effect": "none",
            "execution_effect": "none",
            "data_not_instruction": True,
            "can_grant_authority": False,
            "can_approve_execution": False,
            "can_create_delegated_lane": False,
            "can_unlock_credentials": False,
            "can_override_provider_model": False,
        }
        record_payload["record_hash"] = record_hash_payload(record_payload)
        record = MemoryRecord.model_validate(record_payload)
        try:
            self.store.save_with_supersession(record)
        except DuplicateMemoryError:
            return MemoryIngestResult(
                accepted=False,
                reasons=["duplicate_lineage_or_content"],
                rejected_payload_hash=content_hash,
            )
        except SupersessionTargetError as exc:
            return MemoryIngestResult(
                accepted=False,
                reasons=[str(exc)],
                rejected_payload_hash=stable_hash({"supersedes_refs": record.supersedes_refs}),
            )
        return MemoryIngestResult(accepted=True, record=record, reasons=trust_reasons)

    def retrieve(
        self,
        query: PersistentMemoryQuery | dict[str, Any],
    ) -> PersistentMemoryRetrievalResult:
        query = query if isinstance(query, PersistentMemoryQuery) else PersistentMemoryQuery.model_validate(query)
        query_payload = query.model_dump(mode="json")
        query_hash = stable_hash(query_payload)
        fts_scores = self.store.fts_scores(
            owner_user_id=query.requester_user_id,
            query_text=query.query_text,
            limit=query.candidate_limit,
        )
        records, quarantined = self.store.records_for_user(query.requester_user_id)
        query_vector = semantic_vector(query.query_text)
        hits: list[PersistentMemoryHit] = []
        for record in records:
            if not _namespace_visible(record, query):
                continue
            expired = record.expires_at is not None and record.expires_at <= query.current_time
            historical = record.historical_only or expired or record.claim_status is MemoryClaimStatus.SUPERSEDED
            if historical and not query.include_historical:
                continue
            lexical = lexical_score(query.query_text, " ".join([record.safe_summary, *record.uncertainty]))
            semantic = cosine_similarity(query_vector, semantic_vector(record.safe_summary))
            entity = entity_score(query.entity_ids, record.entity_refs)
            procedure = entity_score(query.procedure_ids, record.procedure_refs)
            if query.query_text.strip() and max(lexical, semantic, entity, procedure) <= 0.0:
                continue
            components = {
                "lexical": round(lexical, 6),
                "fts": fts_scores.get(record.record_id, 0.0),
                "semantic": round(semantic, 6),
                "entity": round(entity, 6),
                "procedure": round(procedure, 6),
                "provenance": round(provenance_score(record), 6),
                "freshness": 0.0 if expired else 1.0,
                "contradiction_penalty": -0.2 if record.contradiction_refs else 0.0,
                "historical_penalty": -0.25 if historical else 0.0,
            }
            score = max(
                0.0,
                round(
                    components["lexical"] * 0.35
                    + components["fts"] * 0.15
                    + components["semantic"] * 0.25
                    + components["entity"] * 0.1
                    + components["procedure"] * 0.1
                    + components["provenance"] * 0.1
                    + components["freshness"] * 0.05
                    + components["contradiction_penalty"]
                    + components["historical_penalty"],
                    6,
                ),
            )
            hits.append(
                PersistentMemoryHit(
                    record_id=record.record_id,
                    namespace=record.namespace,
                    mission_id=record.mission_id,
                    source_class=record.provenance.source_class,
                    source_id=record.provenance.source_id,
                    source_lineage_id=record.provenance.source_lineage_id,
                    source_scope=record.provenance.source_scope,
                    validity_scope=record.validity_scope,
                    trust_class=record.provenance.trust_class,
                    claim_status=record.claim_status,
                    safe_summary=record.safe_summary,
                    confidence=record.confidence,
                    variance=record.variance,
                    evidence_refs=record.provenance.evidence_refs,
                    receipt_refs=record.provenance.receipt_refs,
                    entity_refs=record.entity_refs,
                    procedure_refs=record.procedure_refs,
                    contradiction_refs=record.contradiction_refs,
                    supersedes_refs=record.supersedes_refs,
                    superseded_by_refs=record.superseded_by_refs,
                    created_at=record.created_at,
                    observed_at=record.observed_at,
                    expires_at=record.expires_at,
                    is_expired=expired,
                    is_historical_only=historical,
                    match_reasons=_match_reasons(components),
                    score_components=components,
                    retrieval_score=score,
                )
            )
        hits.sort(key=lambda hit: (-hit.retrieval_score, hit.record_id))
        candidates = hits[: query.candidate_limit]
        return PersistentMemoryRetrievalResult(
            query_hash=query_hash,
            hits=candidates[: query.max_hits],
            candidate_count=len(records),
            quarantined_record_ids=quarantined,
        )

    def expire(self, *, current_time: datetime) -> MemoryExpiryResult:
        records, _ = self.store.all_records()
        expired_ids: list[str] = []
        for record in records:
            if record.expires_at is None or record.expires_at > current_time:
                continue
            if record.claim_status is MemoryClaimStatus.EXPIRED and record.historical_only:
                continue
            updated = record.model_copy(
                update={
                    "claim_status": MemoryClaimStatus.EXPIRED,
                    "historical_only": True,
                    "record_hash": "",
                }
            )
            payload = updated.model_dump(mode="json")
            payload["record_hash"] = record_hash_payload(payload)
            self.store.update(MemoryRecord.model_validate(payload))
            expired_ids.append(record.record_id)
        return MemoryExpiryResult(expired_record_ids=expired_ids)

    def delete(
        self,
        record_id: str,
        *,
        requester_user_id: str,
        reason: str,
        current_time: datetime,
    ) -> MemoryDeletionReceipt:
        record = self.store.get(record_id)
        if record is None or record.namespace.owner_user_id != requester_user_id:
            raise ValueError("memory record not found for requester")
        tombstone = MemoryTombstone(
            record_id=record.record_id,
            owner_user_id=requester_user_id,
            namespace_kind=record.namespace.kind,
            content_hash=record.content_hash,
            record_hash=record.record_hash,
            deleted_at=current_time,
            reason_hash=stable_hash(sanitize_memory_text(reason)),
        )
        self.store.write_tombstone_and_delete(tombstone)
        return MemoryDeletionReceipt(
            record_id=record.record_id,
            tombstone_written=True,
            content_removed=True,
            deletion_hash=stable_hash(tombstone.model_dump(mode="json")),
        )

    def get_tombstone(self, record_id: str) -> MemoryTombstone | None:
        return self.store.get_tombstone(record_id)


def _namespace_visible(record: MemoryRecord, query: PersistentMemoryQuery) -> bool:
    namespace = record.namespace
    if namespace.owner_user_id != query.requester_user_id:
        return False
    if namespace.kind is MemoryNamespaceKind.MISSION:
        return namespace.mission_id == query.mission_id
    if namespace.kind is MemoryNamespaceKind.ENTITY:
        return namespace.entity_id in query.entity_ids
    if namespace.kind is MemoryNamespaceKind.PROCEDURE:
        return namespace.procedure_id in query.procedure_ids
    return namespace.kind in {MemoryNamespaceKind.USER, MemoryNamespaceKind.SHARED}


def _validated_trust_class(
    entry: LivingMissionMemoryEntry,
    requested: MemoryTrustClass,
    *,
    provenance_ref_validator: Callable[[LivingMissionMemoryEntry, MemoryTrustClass], bool] | None,
) -> tuple[MemoryTrustClass, list[str]]:
    refs_valid = (
        provenance_ref_validator is not None
        and provenance_ref_validator(entry, requested) is True
    )
    valid = {
        MemoryTrustClass.UNTRUSTED: True,
        MemoryTrustClass.INFERRED: entry.source_class is MemorySourceClass.role_output,
        MemoryTrustClass.USER_CONFIRMED: entry.source_class
        in {MemorySourceClass.user_instruction, MemorySourceClass.user_correction}
        and refs_valid,
        MemoryTrustClass.EVIDENCE_BOUND: bool(entry.evidence_refs) and refs_valid,
        MemoryTrustClass.RECEIPT_BOUND: bool(entry.receipt_refs) and refs_valid,
        MemoryTrustClass.VERIFIED_RESULT: entry.source_class
        in {MemorySourceClass.verifier_result, MemorySourceClass.finalgate_result}
        and bool(entry.evidence_refs or entry.receipt_refs)
        and refs_valid,
    }[requested]
    if valid:
        return requested, []
    return MemoryTrustClass.UNTRUSTED, ["trust_class_downgraded"]


def _match_reasons(components: dict[str, float]) -> list[str]:
    return [
        key
        for key in ("lexical", "fts", "semantic", "entity", "procedure", "provenance")
        if components.get(key, 0.0) > 0.0
    ]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value not in (None, "")))
