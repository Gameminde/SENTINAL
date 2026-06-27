from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.kernel import MissionKernel, MissionLifecycleError
from sentinel.operator.mission_execution_coordinator import (
    MissionExecutionCoordinator,
    MissionExecutionDecision,
    MissionExecutionDecisionStatus,
)
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequest, MissionExecutionRequestState, MissionLifecycleService
from sentinel.operator.models import OperatorMissionStatus, OperatorMode
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyActionKind,
    ReadOnlyActionReceipt,
    ReadOnlyDecisionClient,
    ReadOnlyFinalGateCertificate,
    ReadOnlyProductionSpineResult,
    ReadOnlyProductionSpineSession,
    ReadOnlyReportClient,
)
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class DispatchStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class UnifiedDispatchResult(SentinelModel):
    dispatch_id: str = Field(default_factory=lambda: new_id("dispatch"))
    status: DispatchStatus
    mission_id: str
    execution_request_id: str
    decision_id: str | None = None
    adapter_id: str | None = None
    capability_id: str
    operation: str
    receipt_refs: list[str] = Field(default_factory=list)
    failed_attempt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    terminal_certificate_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    live_event_refs: list[str] = Field(default_factory=list)
    finalgate_status: str | None = None
    blocked_reason: str | None = None
    dispatch_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _dispatch_result_is_data_only(self) -> "UnifiedDispatchResult":
        assert_data_not_authority(
            context="unified_dispatch_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "status": self.status.value,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "decision_id": self.decision_id,
            "adapter_id": redact_operator_text(self.adapter_id or "") or None,
            "capability_id": redact_operator_text(self.capability_id),
            "operation": redact_operator_text(self.operation),
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "failed_attempt_refs": sanitize_operator_refs(self.failed_attempt_refs),
            "finalgate_refs": sanitize_operator_refs(self.finalgate_refs),
            "terminal_certificate_refs": sanitize_operator_refs(self.terminal_certificate_refs),
            "artifact_refs": sanitize_operator_refs(self.artifact_refs),
            "live_event_refs": sanitize_operator_refs(self.live_event_refs),
            "finalgate_status": redact_operator_text(self.finalgate_status or "") or None,
            "blocked_reason": redact_operator_text(self.blocked_reason or "") or None,
            "dispatch_hash": self.dispatch_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class DispatcherTerminalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("dispatch_terminal"))
    mission_id: str
    execution_request_id: str
    decision_id: str | None = None
    dispatch_id: str
    adapter_id: str | None = None
    status: str = "blocked"
    accepted: bool = False
    reason_code: str
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _terminal_certificate_is_data_only(self) -> "DispatcherTerminalCertificate":
        assert_data_not_authority(
            context="dispatcher_terminal_certificate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.accepted:
            raise ValueError("dispatcher terminal certificate cannot accept blocked routes")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "decision_id": self.decision_id,
            "dispatch_id": self.dispatch_id,
            "adapter_id": redact_operator_text(self.adapter_id or "") or None,
            "status": self.status,
            "accepted": self.accepted,
            "reason_code": redact_operator_text(self.reason_code),
            "certificate_hash": self.certificate_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "DispatcherTerminalCertificate":
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})


class DispatchProofVerificationResult(SentinelModel):
    ok: bool
    failure_code: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    report_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    material_observation_receipt_count: int = 0


class MissionExecutionDecisionStore:
    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel

    def persist(self, decision: MissionExecutionDecision) -> None:
        self.kernel.store.atomic_write_json(
            self.decision_path(decision.mission_id, decision.decision_id),
            decision.safe_model_dump(),
        )

    def decision_path(self, mission_id: str, decision_id: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "execution_decisions" / f"{decision_id}.json"


class UnifiedExecutionDispatchContext:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        lifecycle: MissionLifecycleService,
        decision_store: MissionExecutionDecisionStore,
    ) -> None:
        self.kernel = kernel
        self.lifecycle = lifecycle
        self.decision_store = decision_store

    def completed_result(
        self,
        *,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        adapter_id: str,
        receipt_refs: list[str] | None = None,
        finalgate_refs: list[str] | None = None,
        artifact_refs: list[str] | None = None,
        live_event_refs: list[str] | None = None,
    ) -> UnifiedDispatchResult:
        return UnifiedDispatchResult(
            status=DispatchStatus.COMPLETED,
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            decision_id=decision.decision_id,
            adapter_id=adapter_id,
            capability_id=request.capability_id,
            operation=request.operation,
            receipt_refs=list(receipt_refs or []),
            finalgate_refs=list(finalgate_refs or []),
            artifact_refs=list(artifact_refs or []),
            live_event_refs=list(live_event_refs or []),
            finalgate_status="accepted",
        )


class UnifiedExecutionAdapter(Protocol):
    adapter_id: str
    capability_id: str
    operation: str

    def execute(
        self,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        authority: MissionAuthorityEnvelope,
        context: UnifiedExecutionDispatchContext,
    ) -> UnifiedDispatchResult:
        ...


class UnifiedExecutionAdapterRegistry:
    def __init__(self, adapters: dict[str, UnifiedExecutionAdapter] | None = None) -> None:
        self._adapters = dict(adapters or {})

    def get(self, adapter_id: str) -> UnifiedExecutionAdapter:
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            raise KeyError("unknown_adapter") from exc


class ReadOnlyResearchAdapter:
    adapter_id = "read_only_research_adapter"
    capability_id = "read_only_research"
    operation = "inspect_repository"

    def __init__(
        self,
        *,
        decision_client_factory: Callable[[MissionExecutionRequest, MissionAuthorityEnvelope], ReadOnlyDecisionClient],
        report_client_factory: Callable[[MissionExecutionRequest, MissionAuthorityEnvelope], ReadOnlyReportClient],
    ) -> None:
        self._decision_client_factory = decision_client_factory
        self._report_client_factory = report_client_factory

    def execute(
        self,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        authority: MissionAuthorityEnvelope,
        context: UnifiedExecutionDispatchContext,
    ) -> UnifiedDispatchResult:
        if request.capability_id != self.capability_id or decision.capability_id != self.capability_id:
            return _blocked_result(request, decision, adapter_id=self.adapter_id, reason="capability_mismatch")
        if request.operation != self.operation or decision.operation != self.operation:
            return _blocked_result(request, decision, adapter_id=self.adapter_id, reason="operation_mismatch")
        snapshot_root = _workspace_from_ref(request.workspace_ref)
        cockpit = LLMLiveOperatorCockpit(
            run_root=context.kernel.store.run_root,
            mode=OperatorMode.DETERMINISTIC_TEST,
            lifecycle_service=context.lifecycle,
        )
        session = ReadOnlyProductionSpineSession(
            cockpit=cockpit,
            mission_id=request.mission_id,
            snapshot_root=snapshot_root,
            decision_client=self._decision_client_factory(request, authority),
            report_client=self._report_client_factory(request, authority),
            excluded_paths=["sentinel_internal"],
            owns_kernel_terminal=False,
            stop_after_first_material_receipt=_stop_after_first_material_receipt(request),
        )
        result = session.run_via_agent_runtime(envelope=authority)
        status = DispatchStatus.COMPLETED if result.status == "completed" and result.finalgate_status == "accepted" else DispatchStatus.BLOCKED
        return UnifiedDispatchResult(
            status=status,
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            decision_id=decision.decision_id,
            adapter_id=self.adapter_id,
            capability_id=request.capability_id,
            operation=request.operation,
            receipt_refs=list(result.receipt_refs),
            failed_attempt_refs=list(result.failed_attempt_refs),
            finalgate_refs=list(result.finalgate_refs),
            artifact_refs=list(result.artifact_refs),
            live_event_refs=list(result.live_event_refs),
            finalgate_status=result.finalgate_status,
            blocked_reason=result.blocked_reason,
        )


class UnifiedExecutionDispatcher:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        lifecycle: MissionLifecycleService,
        coordinator: MissionExecutionCoordinator,
        adapter_registry: UnifiedExecutionAdapterRegistry,
    ) -> None:
        self.kernel = kernel
        self.lifecycle = lifecycle
        self.coordinator = coordinator
        self.adapter_registry = adapter_registry
        self.decision_store = MissionExecutionDecisionStore(kernel)

    def dispatch(self, *, request: MissionExecutionRequest, authority: MissionAuthorityEnvelope) -> UnifiedDispatchResult:
        decision = self.coordinator.decide(request)
        self.decision_store.persist(decision)
        self.kernel.store.append_event(
            request.mission_id,
            event_type="mission_dispatch_decision_persisted",
            safe_summary="Mission execution routing decision persisted before adapter execution.",
            metadata={
                "execution_request_id": request.request_id,
                "decision_id": decision.decision_id,
                "decision_hash": decision.decision_hash,
                "adapter_id": decision.adapter_id,
                "status": decision.status.value,
            },
        )
        if decision.status is not MissionExecutionDecisionStatus.ROUTED:
            result = self._block(request, decision, decision.rejection_reason or "coordinator_rejected")
            return self._persist_closeout(result, request=request)
        state = self.lifecycle.derive_request_state(request.mission_id, request.request_id)
        if state.state is not MissionExecutionRequestState.DISPATCH_DECIDED:
            result = self._block(request, decision, f"request_state_not_dispatchable:{state.state.value}")
            return self._persist_closeout(result, request=request)
        authority_failure = self._dispatch_authority_failure(request=request, decision=decision, authority=authority)
        if authority_failure is not None:
            result = self._block(request, decision, authority_failure)
            return self._persist_closeout(result, request=request)
        try:
            adapter = self.adapter_registry.get(decision.adapter_id or "")
        except KeyError:
            result = self._block(request, decision, "unknown_adapter")
            return self._persist_closeout(result, request=request)
        if adapter.adapter_id != decision.adapter_id:
            result = self._block(request, decision, "adapter_id_mismatch")
            return self._persist_closeout(result, request=request)
        if adapter.capability_id != request.capability_id:
            result = self._block(request, decision, "capability_mismatch")
            return self._persist_closeout(result, request=request)
        if adapter.operation != request.operation:
            result = self._block(request, decision, "operation_mismatch")
            return self._persist_closeout(result, request=request)
        self.kernel.store.append_event(
            request.mission_id,
            event_type="mission_dispatch_started",
            safe_summary="Unified execution dispatcher started adapter execution.",
            metadata={
                "execution_request_id": request.request_id,
                "decision_id": decision.decision_id,
                "adapter_id": adapter.adapter_id,
            },
        )
        record = self.kernel.store.load_record(request.mission_id)
        if record.status is not OperatorMissionStatus.RUNNING:
            self.kernel.update_status(
                request.mission_id,
                OperatorMissionStatus.RUNNING,
                "Mission running under unified execution dispatcher.",
            )
        try:
            result = adapter.execute(
                request,
                decision,
                authority,
                UnifiedExecutionDispatchContext(kernel=self.kernel, lifecycle=self.lifecycle, decision_store=self.decision_store),
            )
        except Exception as exc:  # noqa: BLE001
            result = self._block(request, decision, f"adapter_exception:{exc.__class__.__name__}")
        if result.mission_id != request.mission_id or result.execution_request_id != request.request_id:
            result = self._block(request, decision, "adapter_result_correlation_failure")
        return self._persist_closeout(result, request=request)

    def _block(self, request: MissionExecutionRequest, decision: MissionExecutionDecision | None, reason: str) -> UnifiedDispatchResult:
        return _blocked_result(request, decision, adapter_id=decision.adapter_id if decision else None, reason=reason)

    def _dispatch_authority_failure(
        self,
        *,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        authority: MissionAuthorityEnvelope,
    ) -> str | None:
        if not request.verify_hash():
            return "request_hash_mismatch"
        if not decision.verify_hash():
            return "decision_hash_mismatch"
        if authority.id != request.mission_id:
            return "authority_mission_mismatch"
        if request.authority_envelope_ref != decision.authority_envelope_ref:
            return "authority_ref_mismatch"
        if authority.revoked_at is not None:
            return "authority_inactive"
        if datetime.now(UTC) > authority.resolved_expires_at():
            return "authority_inactive"
        return None

    def _persist_closeout(
        self,
        result: UnifiedDispatchResult,
        *,
        request: MissionExecutionRequest | None = None,
    ) -> UnifiedDispatchResult:
        result = self._verified_closeout_result(result, request=request)
        self.kernel.store.atomic_write_json(
            self.kernel.store.mission_dir(result.mission_id, create=True) / "dispatch_closeout" / f"{result.dispatch_id}.json",
            result.safe_model_dump(),
        )
        blocked_reason_hash = text_hash(result.blocked_reason) if result.blocked_reason else None
        self.kernel.store.append_event(
            result.mission_id,
            event_type="mission_dispatch_closeout_persisted",
            safe_summary="Mission dispatch closeout persisted.",
            metadata={
                "execution_request_id": result.execution_request_id,
                "decision_id": result.decision_id,
                "dispatch_id": result.dispatch_id,
                "adapter_id_hash": text_hash(result.adapter_id or ""),
                "status": result.status.value,
                "blocked_reason_hash": blocked_reason_hash,
                "terminal_certificate_ref_hashes": [text_hash(ref) for ref in sanitize_operator_refs(result.terminal_certificate_refs)],
            },
            receipt_refs=result.receipt_refs,
            finalgate_certificate_refs=result.finalgate_refs,
        )
        if result.status is DispatchStatus.COMPLETED and result.finalgate_status == "accepted" and result.receipt_refs and result.finalgate_refs:
            if not self.kernel.is_terminal(result.mission_id):
                self.kernel.update_status(
                    result.mission_id,
                    OperatorMissionStatus.COMPLETED,
                    "Mission completed after dispatch closeout and accepted FinalGate.",
                )
            return result
        if not self.kernel.is_terminal(result.mission_id):
            try:
                self.kernel.update_status(
                    result.mission_id,
                    OperatorMissionStatus.BLOCKED,
                    "Mission blocked after dispatch closeout.",
                )
            except MissionLifecycleError:
                pass
        return result

    def _verified_closeout_result(
        self,
        result: UnifiedDispatchResult,
        *,
        request: MissionExecutionRequest | None = None,
    ) -> UnifiedDispatchResult:
        if result.status is DispatchStatus.COMPLETED:
            proof = self._verify_completed_proof(result, request=request)
            if proof.ok:
                return result.model_copy(
                    update={
                        "receipt_refs": proof.receipt_refs,
                        "artifact_refs": proof.report_refs,
                        "finalgate_refs": proof.finalgate_refs,
                        "terminal_certificate_refs": proof.finalgate_refs,
                    }
                )
            blocked = result.model_copy(
                update={
                    "status": DispatchStatus.BLOCKED,
                    "finalgate_status": "rejected",
                    "blocked_reason": proof.failure_code,
                }
            )
            if not result.finalgate_refs:
                return self._with_dispatch_terminal_certificate(blocked, reason=proof.failure_code or "proof_verification_failed")
            return blocked
        if not result.finalgate_refs and not result.terminal_certificate_refs:
            return self._with_dispatch_terminal_certificate(result, reason=result.blocked_reason or "dispatch_blocked")
        return result

    def _verify_completed_proof(
        self,
        result: UnifiedDispatchResult,
        *,
        request: MissionExecutionRequest | None = None,
    ) -> DispatchProofVerificationResult:
        receipt_result = self._load_and_verify_receipts(result)
        if not receipt_result.ok:
            return receipt_result
        if request is not None and _stop_after_first_material_receipt(request):
            finalgate_result = self._load_and_verify_finalgate(result, validated_receipt_refs=receipt_result.receipt_refs)
            if not finalgate_result.ok:
                return finalgate_result
            return DispatchProofVerificationResult(
                ok=True,
                receipt_refs=receipt_result.receipt_refs,
                report_refs=[],
                finalgate_refs=finalgate_result.finalgate_refs,
                material_observation_receipt_count=receipt_result.material_observation_receipt_count,
            )
        report_result = self._load_and_verify_reports(result, known_evidence_refs=self._receipt_evidence_refs(result))
        if not report_result.ok:
            return report_result
        finalgate_result = self._load_and_verify_finalgate(result, validated_receipt_refs=receipt_result.receipt_refs)
        if not finalgate_result.ok:
            return finalgate_result
        return DispatchProofVerificationResult(
            ok=True,
            receipt_refs=receipt_result.receipt_refs,
            report_refs=report_result.report_refs,
            finalgate_refs=finalgate_result.finalgate_refs,
            material_observation_receipt_count=receipt_result.material_observation_receipt_count,
        )

    def _load_and_verify_receipts(self, result: UnifiedDispatchResult) -> DispatchProofVerificationResult:
        if not result.receipt_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_missing")
        material_count = 0
        for receipt_ref in result.receipt_refs:
            path = self._read_only_artifact_path(result.mission_id, "receipts", receipt_ref)
            if not path.exists():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_missing")
            receipt = ReadOnlyActionReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if receipt.mission_id != result.mission_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_mission_mismatch")
            if not receipt.verify_hash():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_hash_mismatch")
            if receipt.status == "success" and receipt.action in {
                ReadOnlyActionKind.LIST_DIRECTORY,
                ReadOnlyActionKind.READ_FILE_SEGMENT,
                ReadOnlyActionKind.SEARCH_TEXT,
            }:
                material_count += 1
        if material_count < 1:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_material_observation_missing")
        return DispatchProofVerificationResult(
            ok=True,
            receipt_refs=list(dict.fromkeys(result.receipt_refs)),
            material_observation_receipt_count=material_count,
        )

    def _load_and_verify_reports(
        self,
        result: UnifiedDispatchResult,
        *,
        known_evidence_refs: set[str],
    ) -> DispatchProofVerificationResult:
        if not result.artifact_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_report_missing")
        for report_ref in result.artifact_refs:
            path = self._read_only_artifact_path(result.mission_id, "reports", report_ref)
            if not path.exists():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_report_missing")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("mission_id") != result.mission_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_report_mission_mismatch")
            safe_report = str(payload.get("safe_report") or "")
            if not safe_report.strip():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_report_empty")
            if text_hash(safe_report) != payload.get("report_hash"):
                return DispatchProofVerificationResult(ok=False, failure_code="proof_report_hash_mismatch")
            evidence_refs = set(sanitize_operator_refs(payload.get("evidence_refs") or []))
            if not evidence_refs.issubset(known_evidence_refs):
                return DispatchProofVerificationResult(ok=False, failure_code="proof_report_unknown_evidence")
        return DispatchProofVerificationResult(ok=True, report_refs=list(dict.fromkeys(result.artifact_refs)))

    def _load_and_verify_finalgate(
        self,
        result: UnifiedDispatchResult,
        *,
        validated_receipt_refs: list[str],
    ) -> DispatchProofVerificationResult:
        if not result.finalgate_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_missing")
        for finalgate_ref in result.finalgate_refs:
            path = self._read_only_artifact_path(result.mission_id, "finalgate", finalgate_ref)
            if not path.exists():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_missing")
            certificate = ReadOnlyFinalGateCertificate.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if certificate.mission_id != result.mission_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_mission_mismatch")
            if not certificate.verify_hash():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_hash_mismatch")
            if not certificate.accepted:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_rejected")
            if set(certificate.receipt_refs) != set(validated_receipt_refs):
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_receipt_mismatch")
        return DispatchProofVerificationResult(ok=True, finalgate_refs=list(dict.fromkeys(result.finalgate_refs)))

    def _receipt_evidence_refs(self, result: UnifiedDispatchResult) -> set[str]:
        refs: set[str] = set()
        for receipt_ref in result.receipt_refs:
            path = self._read_only_artifact_path(result.mission_id, "receipts", receipt_ref)
            if not path.exists():
                continue
            receipt = ReadOnlyActionReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))
            refs.update(sanitize_operator_refs(receipt.evidence_refs))
        return refs

    def _with_dispatch_terminal_certificate(self, result: UnifiedDispatchResult, *, reason: str) -> UnifiedDispatchResult:
        certificate = DispatcherTerminalCertificate(
            mission_id=result.mission_id,
            execution_request_id=result.execution_request_id,
            decision_id=result.decision_id,
            dispatch_id=result.dispatch_id,
            adapter_id=result.adapter_id,
            reason_code=reason,
        ).with_hash()
        self.kernel.store.atomic_write_json(
            self.kernel.store.mission_dir(result.mission_id, create=True)
            / "dispatch_terminal_certificates"
            / f"{certificate.certificate_id}.json",
            certificate.safe_model_dump(),
        )
        self.kernel.store.append_event(
            result.mission_id,
            event_type="mission_dispatch_terminal_certified",
            safe_summary="Dispatcher terminal certificate recorded for blocked route.",
            metadata={
                "execution_request_id": result.execution_request_id,
                "dispatch_id": result.dispatch_id,
                "blocked": True,
                "proof_ref_hash": text_hash(certificate.certificate_id),
                "proof_reason_hash": text_hash(certificate.reason_code),
            },
        )
        return result.model_copy(update={"terminal_certificate_refs": [certificate.certificate_id]})

    def _read_only_artifact_path(self, mission_id: str, collection: str, ref: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "read_only_spine" / collection / f"{ref}.json"


def _blocked_result(
    request: MissionExecutionRequest,
    decision: MissionExecutionDecision | None,
    *,
    adapter_id: str | None,
    reason: str,
) -> UnifiedDispatchResult:
    return UnifiedDispatchResult(
        status=DispatchStatus.BLOCKED,
        mission_id=request.mission_id,
        execution_request_id=request.request_id,
        decision_id=decision.decision_id if decision else None,
        adapter_id=adapter_id,
        capability_id=request.capability_id,
        operation=request.operation,
        finalgate_status="rejected",
        blocked_reason=redact_operator_text(reason),
    )


def _workspace_from_ref(workspace_ref: str) -> Path:
    if not workspace_ref.startswith("workspace:"):
        raise ValueError("workspace_ref_not_dispatchable")
    path = Path(workspace_ref.removeprefix("workspace:")).resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError("workspace_ref_not_found")
    return path


def _stop_after_first_material_receipt(request: MissionExecutionRequest) -> bool:
    return request.execution_options.get("stop_after_first_material_receipt") is True


__all__ = [
    "DispatcherTerminalCertificate",
    "DispatchStatus",
    "DispatchProofVerificationResult",
    "MissionExecutionDecisionStore",
    "ReadOnlyResearchAdapter",
    "UnifiedDispatchResult",
    "UnifiedExecutionAdapter",
    "UnifiedExecutionAdapterRegistry",
    "UnifiedExecutionDispatchContext",
    "UnifiedExecutionDispatcher",
]
