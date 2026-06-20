from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import text_hash
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
    ReadOnlyDecisionClient,
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
            self._persist_closeout(result)
            return result
        state = self.lifecycle.derive_request_state(request.mission_id, request.request_id)
        if state.state is not MissionExecutionRequestState.DISPATCH_DECIDED:
            result = self._block(request, decision, f"request_state_not_dispatchable:{state.state.value}")
            self._persist_closeout(result)
            return result
        if authority.id != request.mission_id or request.authority_envelope_ref != decision.authority_envelope_ref:
            result = self._block(request, decision, "authority_ref_mismatch")
            self._persist_closeout(result)
            return result
        try:
            adapter = self.adapter_registry.get(decision.adapter_id or "")
        except KeyError:
            result = self._block(request, decision, "unknown_adapter")
            self._persist_closeout(result)
            return result
        if adapter.adapter_id != decision.adapter_id:
            result = self._block(request, decision, "adapter_id_mismatch")
            self._persist_closeout(result)
            return result
        if adapter.capability_id != request.capability_id:
            result = self._block(request, decision, "capability_mismatch")
            self._persist_closeout(result)
            return result
        if adapter.operation != request.operation:
            result = self._block(request, decision, "operation_mismatch")
            self._persist_closeout(result)
            return result
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
        self._persist_closeout(result)
        return result

    def _block(self, request: MissionExecutionRequest, decision: MissionExecutionDecision | None, reason: str) -> UnifiedDispatchResult:
        return _blocked_result(request, decision, adapter_id=decision.adapter_id if decision else None, reason=reason)

    def _persist_closeout(self, result: UnifiedDispatchResult) -> None:
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
                "adapter_id": result.adapter_id,
                "status": result.status.value,
                "blocked_reason_hash": blocked_reason_hash,
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
            return
        if not self.kernel.is_terminal(result.mission_id):
            try:
                self.kernel.update_status(
                    result.mission_id,
                    OperatorMissionStatus.BLOCKED,
                    "Mission blocked after dispatch closeout.",
                )
            except MissionLifecycleError:
                pass


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


__all__ = [
    "DispatchStatus",
    "MissionExecutionDecisionStore",
    "ReadOnlyResearchAdapter",
    "UnifiedDispatchResult",
    "UnifiedExecutionAdapter",
    "UnifiedExecutionAdapterRegistry",
    "UnifiedExecutionDispatchContext",
    "UnifiedExecutionDispatcher",
]
