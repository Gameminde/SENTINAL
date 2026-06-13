from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.agent.llm import LivingMissionMemoryEntry, MemoryClaimStatus, MemorySourceClass
from sentinel.memory import MemoryNamespace, MemoryNamespaceKind, MemoryTrustClass, PersistentSemanticMemoryService
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry import TelemetryDomain, TelemetryEventKind, TelemetryEventRecord, TelemetrySourceSurface, TelemetryStore


CANARY = "OPENAI" + "_API_KEY=" + "sk-" + "global-canary-1234567890abcdef"


def test_global_sensitive_canary_is_not_persisted_across_core_data_surfaces(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_global_invariant_canary",
        draft=MissionDraft(
            title="Global invariant canary",
            objective="Prove raw sensitive values do not persist across core data surfaces.",
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="mission_global_invariant_canary",
            allowed_actions=["audit_read"],
            forbidden_actions=["credential_unlock", "provider_override"],
            summary="Audit-only mission.",
        ),
    )
    with pytest.raises(ValueError, match="unsafe operator payload"):
        kernel.store.append_event(
            record.mission_id,
            event_type="global_sensitive_serialization_canary_rejected",
            safe_summary=f"Mission event saw {CANARY}",
            metadata={
                "credential_value": CANARY,
                "raw_prompt": CANARY,
                "provider_response": CANARY,
                "nested": {"reasoning": CANARY},
            },
            receipt_refs=[CANARY],
            finalgate_certificate_refs=[CANARY],
            memory_feedback_refs=[CANARY],
        )
    kernel.store.append_event(
        record.mission_id,
        event_type="global_sensitive_serialization_canary_redacted",
        safe_summary=f"Mission event saw {CANARY}",
        metadata={"notes": CANARY},
        receipt_refs=[CANARY],
        finalgate_certificate_refs=[CANARY],
        memory_feedback_refs=[CANARY],
    )

    telemetry = TelemetryStore(tmp_path / "telemetry")
    with pytest.raises(ValueError, match="unsafe operator payload"):
        TelemetryEventRecord(
            mission_id=record.mission_id,
            source_surface=TelemetrySourceSurface.MISSION_KERNEL,
            domain=TelemetryDomain.SAFETY,
            event_kind=TelemetryEventKind.SECRET_REDACTION_HIT,
            safe_summary=f"Telemetry saw {CANARY}",
            metadata={
                "credential_value": CANARY,
                "raw_prompt": CANARY,
                "provider_response": CANARY,
                "nested": {"reasoning": CANARY},
            },
            receipt_refs=[CANARY],
            finalgate_certificate_refs=[CANARY],
            memory_feedback_refs=[CANARY],
        )
    telemetry.record_event(
        TelemetryEventRecord(
            mission_id=record.mission_id,
            source_surface=TelemetrySourceSurface.MISSION_KERNEL,
            domain=TelemetryDomain.SAFETY,
            event_kind=TelemetryEventKind.SECRET_REDACTION_HIT,
            safe_summary=f"Telemetry saw {CANARY}",
            metadata={"notes": CANARY},
            receipt_refs=[CANARY],
            finalgate_certificate_refs=[CANARY],
            memory_feedback_refs=[CANARY],
        )
    )

    memory = PersistentSemanticMemoryService(tmp_path / "memory.sqlite3")
    memory_result = memory.ingest_entry(
        LivingMissionMemoryEntry(
            memory_id="memory_global_canary",
            mission_id=record.mission_id,
            source_class=MemorySourceClass.evidence,
            source_id="evidence_global_canary",
            source_lineage_id="lineage_global_canary",
            source_scope=record.mission_id,
            validity_scope=record.mission_id,
            created_at=datetime.now(UTC),
            observed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
            claim_status=MemoryClaimStatus.SUPPORTED,
            confidence=0.7,
            variance=0.1,
            contradiction_refs=[],
            evidence_refs=[CANARY],
            receipt_refs=[CANARY],
            uncertainty=[CANARY],
            safe_summary=f"Memory saw {CANARY}",
        ),
        requester_user_id="user_global_canary",
        namespace=MemoryNamespace(
            kind=MemoryNamespaceKind.MISSION,
            owner_user_id="user_global_canary",
            mission_id=record.mission_id,
        ),
        trust_class=MemoryTrustClass.EVIDENCE_BOUND,
    )
    memory.close()

    assert memory_result.accepted is True
    assert CANARY not in _all_text_under(tmp_path / "runs")
    assert CANARY not in _all_text_under(tmp_path / "telemetry")
    assert CANARY.encode("utf-8") not in (tmp_path / "memory.sqlite3").read_bytes()


def _all_text_under(root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in root.rglob("*")
        if path.is_file()
    )
