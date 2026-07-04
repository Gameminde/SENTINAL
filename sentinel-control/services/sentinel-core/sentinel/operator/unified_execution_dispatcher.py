from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionExecutor, ActionKernel, ActionResult
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
    ReadOnlyMissionSummaryArtifact,
    ReadOnlyOperatorMemoryCandidateArtifact,
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


class ProductActionKernelReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("product_action_kernel_receipt"))
    mission_id: str
    execution_request_id: str
    decision_id: str
    dispatch_id: str
    action_id: str
    skill_id: str
    capability_id: str
    operation: str
    backend_id: str
    organ_id: str | None = None
    authority_decision: str
    execution_status: str
    material_action: bool
    action_result_hash: str
    result_summary_hash: str
    recovery_classification: str
    replay_behavior: str
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "ProductActionKernelReceipt":
        assert_data_not_authority(
            context="product_action_kernel_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "decision_id": self.decision_id,
            "dispatch_id": self.dispatch_id,
            "action_id": self.action_id,
            "skill_id": redact_operator_text(self.skill_id),
            "capability_id": redact_operator_text(self.capability_id),
            "operation": redact_operator_text(self.operation),
            "backend_id": redact_operator_text(self.backend_id),
            "organ_id": redact_operator_text(self.organ_id or "") or None,
            "authority_decision": redact_operator_text(self.authority_decision),
            "execution_status": redact_operator_text(self.execution_status),
            "material_action": self.material_action,
            "action_result_hash": self.action_result_hash,
            "result_summary_hash": self.result_summary_hash,
            "recovery_classification": redact_operator_text(self.recovery_classification),
            "replay_behavior": redact_operator_text(self.replay_behavior),
            "receipt_hash": self.receipt_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "ProductActionKernelReceipt":
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ProductActionKernelFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("product_action_kernel_finalgate"))
    mission_id: str
    execution_request_id: str
    decision_id: str
    dispatch_id: str
    adapter_id: str
    accepted: bool
    reason_code: str
    receipt_refs: list[str] = Field(default_factory=list)
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_data_only(self) -> "ProductActionKernelFinalGateCertificate":
        assert_data_not_authority(
            context="product_action_kernel_finalgate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "decision_id": self.decision_id,
            "dispatch_id": self.dispatch_id,
            "adapter_id": redact_operator_text(self.adapter_id),
            "accepted": self.accepted,
            "reason_code": redact_operator_text(self.reason_code),
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "certificate_hash": self.certificate_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "ProductActionKernelFinalGateCertificate":
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["certificate_hash"]
        payload["certificate_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


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

    def adapter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


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
            low_friction_read_only_power_mode=_low_friction_read_only_power_mode(request),
            model_led_read_only_autopilot=_model_led_read_only_autopilot(request),
            max_material_receipts=_max_material_receipts(request),
            max_provider_decision_calls=_max_provider_decision_calls(request),
            generate_read_only_mission_summary=_generate_read_only_mission_summary(request),
            write_operator_memory_candidate=_write_operator_memory_candidate(request),
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


class ProductActionKernelDispatchAdapter:
    adapter_id = "product_action_kernel_adapter"

    def __init__(
        self,
        *,
        capability_id: str,
        operation: str,
        executor: ActionExecutor,
        product_dispatchable_skill_ids: tuple[str, ...] | list[str] | set[str],
        backend_id: str | None = None,
        organ_id: str | None = None,
        parameter_resolver: Callable[
            [MissionExecutionRequest, MissionExecutionDecision, MissionAuthorityEnvelope, UnifiedExecutionDispatchContext],
            dict[str, Any],
        ]
        | None = None,
        preflight_validator: Callable[
            [dict[str, Any], MissionExecutionRequest, MissionAuthorityEnvelope],
            str | None,
        ]
        | None = None,
    ) -> None:
        self.capability_id = capability_id
        self.operation = operation
        self.backend_id = backend_id or f"{capability_id}_skill"
        self.organ_id = organ_id
        self._product_dispatchable_skill_ids = frozenset(product_dispatchable_skill_ids)
        self._action_kernel = ActionKernel(executors={capability_id: executor})
        self._parameter_resolver = parameter_resolver
        self._preflight_validator = preflight_validator

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
        if request.capability_id not in self._product_dispatchable_skill_ids:
            return _blocked_result(request, decision, adapter_id=self.adapter_id, reason="skill_not_product_dispatchable")
        if not _authority_allows_action(authority, capability_id=request.capability_id, operation=request.operation):
            return _blocked_result(request, decision, adapter_id=self.adapter_id, reason="authority_incompatible_dispatch")

        dispatch_id = new_id("dispatch")
        params = self._resolve_parameters(request, decision, authority, context)
        if self._preflight_validator is not None:
            preflight_failure = self._preflight_validator(params, request, authority)
            if preflight_failure:
                return UnifiedDispatchResult(
                    dispatch_id=dispatch_id,
                    status=DispatchStatus.BLOCKED,
                    mission_id=request.mission_id,
                    execution_request_id=request.request_id,
                    decision_id=decision.decision_id,
                    adapter_id=self.adapter_id,
                    capability_id=request.capability_id,
                    operation=request.operation,
                    finalgate_status="rejected",
                    blocked_reason=preflight_failure,
                )
        envelope = ActionEnvelope(
            capability_id=request.capability_id,
            operation=request.operation,
            target_ref=_target_ref_from_parameters(params),
            params=params,
            authority_ref=request.authority_envelope_ref,
            decision_ref=decision.decision_id,
            expected_receipt_type="ProductActionKernelReceipt",
        )
        action_result = self._action_kernel.execute(
            envelope,
            authority=authority,
            context={
                "mission_id": request.mission_id,
                "execution_request_id": request.request_id,
                "decision_id": decision.decision_id,
                "workspace_ref": request.workspace_ref,
                "model_contract_ref": request.model_contract_ref,
                "parameter_hash": request.parameter_hash,
                "adapter_id": self.adapter_id,
                "backend_id": self.backend_id,
                "organ_id": self.organ_id,
                "authority": authority,
                "kernel": context.kernel,
            },
        )
        receipt = self._write_receipt(
            request=request,
            decision=decision,
            context=context,
            dispatch_id=dispatch_id,
            action_result=action_result,
        )
        if action_result.recoverable or action_result.status not in {"completed", "success", "passed"}:
            return UnifiedDispatchResult(
                dispatch_id=dispatch_id,
                status=DispatchStatus.BLOCKED,
                mission_id=request.mission_id,
                execution_request_id=request.request_id,
                decision_id=decision.decision_id,
                adapter_id=self.adapter_id,
                capability_id=request.capability_id,
                operation=request.operation,
                receipt_refs=[receipt.receipt_id],
                finalgate_status="rejected",
                blocked_reason=(
                    action_result.failure_code
                    or action_result.blocked_reason
                    or "product_action_kernel_execution_failed"
                ),
            )
        certificate = self._write_finalgate(
            request=request,
            decision=decision,
            context=context,
            dispatch_id=dispatch_id,
            receipt_refs=[receipt.receipt_id],
        )
        return UnifiedDispatchResult(
            dispatch_id=dispatch_id,
            status=DispatchStatus.COMPLETED,
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            decision_id=decision.decision_id,
            adapter_id=self.adapter_id,
            capability_id=request.capability_id,
            operation=request.operation,
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
            finalgate_status="accepted",
        )

    def _resolve_parameters(
        self,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        authority: MissionAuthorityEnvelope,
        context: UnifiedExecutionDispatchContext,
    ) -> dict[str, Any]:
        if self._parameter_resolver is not None:
            return dict(self._parameter_resolver(request, decision, authority, context))
        return context.lifecycle.load_execution_parameters(request.mission_id, request.request_id)

    def _write_receipt(
        self,
        *,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        context: UnifiedExecutionDispatchContext,
        dispatch_id: str,
        action_result: ActionResult,
    ) -> ProductActionKernelReceipt:
        receipt = ProductActionKernelReceipt(
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            decision_id=decision.decision_id,
            dispatch_id=dispatch_id,
            action_id=action_result.action_id,
            skill_id=decision.skill_id or request.capability_id,
            capability_id=request.capability_id,
            operation=request.operation,
            backend_id=decision.model_visible_backend_id or self.backend_id,
            organ_id=self.organ_id,
            authority_decision="allowed",
            execution_status=action_result.status,
            material_action=action_result.material_action,
            action_result_hash=action_result.result_hash,
            result_summary_hash=stable_hash(action_result.safe_summary()),
            recovery_classification=action_result.failure_class.value if action_result.failure_class else "none",
            replay_behavior="no_reexecute_on_replay",
        ).with_hash()
        context.kernel.store.atomic_write_json(
            _product_action_kernel_artifact_path(context.kernel, request.mission_id, "receipts", receipt.receipt_id),
            receipt.safe_model_dump(),
        )
        return receipt

    def _write_finalgate(
        self,
        *,
        request: MissionExecutionRequest,
        decision: MissionExecutionDecision,
        context: UnifiedExecutionDispatchContext,
        dispatch_id: str,
        receipt_refs: list[str],
    ) -> ProductActionKernelFinalGateCertificate:
        certificate = ProductActionKernelFinalGateCertificate(
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            decision_id=decision.decision_id,
            dispatch_id=dispatch_id,
            adapter_id=self.adapter_id,
            accepted=True,
            reason_code="product_action_kernel_receipt_verified",
            receipt_refs=receipt_refs,
        ).with_hash()
        context.kernel.store.atomic_write_json(
            _product_action_kernel_artifact_path(context.kernel, request.mission_id, "finalgate", certificate.certificate_id),
            certificate.safe_model_dump(),
        )
        return certificate


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
        if result.adapter_id == ProductActionKernelDispatchAdapter.adapter_id:
            return self._verify_product_action_kernel_proof(result)
        receipt_result = self._load_and_verify_receipts(result)
        if not receipt_result.ok:
            return receipt_result
        if request is not None and (_stop_after_first_material_receipt(request) or _model_led_read_only_autopilot(request)):
            finalgate_result = self._load_and_verify_finalgate(result, validated_receipt_refs=receipt_result.receipt_refs)
            if not finalgate_result.ok:
                return finalgate_result
            artifact_result = self._load_and_verify_autopilot_artifacts(
                result,
                request=request,
                known_receipt_refs=set(receipt_result.receipt_refs),
                known_evidence_refs=self._receipt_evidence_refs(result),
            )
            if not artifact_result.ok:
                return artifact_result
            return DispatchProofVerificationResult(
                ok=True,
                receipt_refs=receipt_result.receipt_refs,
                report_refs=artifact_result.report_refs,
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

    def _verify_product_action_kernel_proof(self, result: UnifiedDispatchResult) -> DispatchProofVerificationResult:
        receipt_result = self._load_and_verify_product_action_kernel_receipts(result)
        if not receipt_result.ok:
            return receipt_result
        finalgate_result = self._load_and_verify_product_action_kernel_finalgate(
            result,
            validated_receipt_refs=receipt_result.receipt_refs,
        )
        if not finalgate_result.ok:
            return finalgate_result
        return DispatchProofVerificationResult(
            ok=True,
            receipt_refs=receipt_result.receipt_refs,
            finalgate_refs=finalgate_result.finalgate_refs,
            material_observation_receipt_count=receipt_result.material_observation_receipt_count,
        )

    def _load_and_verify_product_action_kernel_receipts(
        self,
        result: UnifiedDispatchResult,
    ) -> DispatchProofVerificationResult:
        if not result.receipt_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_missing")
        material_count = 0
        for receipt_ref in result.receipt_refs:
            path = _product_action_kernel_artifact_path(self.kernel, result.mission_id, "receipts", receipt_ref)
            if not path.exists():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_missing")
            receipt = ProductActionKernelReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if receipt.mission_id != result.mission_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_mission_mismatch")
            if receipt.execution_request_id != result.execution_request_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_request_mismatch")
            if not receipt.verify_hash():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_hash_mismatch")
            if receipt.authority_decision != "allowed":
                return DispatchProofVerificationResult(ok=False, failure_code="proof_receipt_authority_not_allowed")
            if receipt.execution_status in {"completed", "success", "passed"} and receipt.material_action:
                material_count += 1
        if material_count < 1:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_material_observation_missing")
        return DispatchProofVerificationResult(
            ok=True,
            receipt_refs=list(dict.fromkeys(result.receipt_refs)),
            material_observation_receipt_count=material_count,
        )

    def _load_and_verify_product_action_kernel_finalgate(
        self,
        result: UnifiedDispatchResult,
        *,
        validated_receipt_refs: list[str],
    ) -> DispatchProofVerificationResult:
        if not result.finalgate_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_missing")
        for finalgate_ref in result.finalgate_refs:
            path = _product_action_kernel_artifact_path(self.kernel, result.mission_id, "finalgate", finalgate_ref)
            if not path.exists():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_missing")
            certificate = ProductActionKernelFinalGateCertificate.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
            if certificate.mission_id != result.mission_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_mission_mismatch")
            if certificate.execution_request_id != result.execution_request_id:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_request_mismatch")
            if not certificate.verify_hash():
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_hash_mismatch")
            if not certificate.accepted:
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_rejected")
            if set(certificate.receipt_refs) != set(validated_receipt_refs):
                return DispatchProofVerificationResult(ok=False, failure_code="proof_finalgate_receipt_mismatch")
        return DispatchProofVerificationResult(ok=True, finalgate_refs=list(dict.fromkeys(result.finalgate_refs)))

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

    def _load_and_verify_autopilot_artifacts(
        self,
        result: UnifiedDispatchResult,
        *,
        request: MissionExecutionRequest,
        known_receipt_refs: set[str],
        known_evidence_refs: set[str],
    ) -> DispatchProofVerificationResult:
        summary_required = _generate_read_only_mission_summary(request)
        memory_required = _write_operator_memory_candidate(request)
        if not summary_required and not memory_required:
            return DispatchProofVerificationResult(ok=True, report_refs=[])
        if not result.artifact_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_missing")

        verified_artifact_refs: list[str] = []
        summary_refs: set[str] = set()
        memory_refs: set[str] = set()
        for artifact_ref in result.artifact_refs:
            summary_path = self._read_only_artifact_path(result.mission_id, "mission_summaries", artifact_ref)
            if summary_path.exists():
                summary = ReadOnlyMissionSummaryArtifact.model_validate(json.loads(summary_path.read_text(encoding="utf-8")))
                if summary.mission_id != result.mission_id:
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_mission_mismatch")
                if not summary.verify_hash():
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_hash_mismatch")
                if not set(summary.receipt_refs).issubset(known_receipt_refs):
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_receipt_mismatch")
                if not set(summary.evidence_refs).issubset(known_evidence_refs):
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_evidence_mismatch")
                summary_refs.add(summary.summary_id)
                verified_artifact_refs.append(summary.summary_id)
                continue

            memory_path = self._read_only_artifact_path(result.mission_id, "operator_memory_candidates", artifact_ref)
            if memory_path.exists():
                candidate = ReadOnlyOperatorMemoryCandidateArtifact.model_validate(json.loads(memory_path.read_text(encoding="utf-8")))
                if candidate.mission_id != result.mission_id:
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_mission_mismatch")
                if not candidate.verify_hash():
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_hash_mismatch")
                if candidate.authority_granting or candidate.can_execute or candidate.raw_secret_material:
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_authority_violation")
                if not set(candidate.receipt_refs).issubset(known_receipt_refs):
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_receipt_mismatch")
                if not set(candidate.evidence_refs).issubset(known_evidence_refs):
                    return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_evidence_mismatch")
                memory_refs.add(candidate.operator_memory_candidate_id)
                verified_artifact_refs.append(candidate.operator_memory_candidate_id)
                continue

            return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_autopilot_artifact_unknown")

        if summary_required and not summary_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_read_only_summary_missing")
        if memory_required and not memory_refs:
            return DispatchProofVerificationResult(ok=False, failure_code="proof_operator_memory_candidate_missing")
        return DispatchProofVerificationResult(ok=True, report_refs=list(dict.fromkeys(verified_artifact_refs)))

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
        return (
            self.kernel.store.mission_dir(mission_id, create=True)
            / "read_only_spine"
            / _read_only_artifact_collection_dir(collection)
            / f"{ref}.json"
        )


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


def _authority_allows_action(
    authority: MissionAuthorityEnvelope,
    *,
    capability_id: str,
    operation: str,
) -> bool:
    allowed_tools = set(authority.allowed_tools)
    allowed_actions = set(authority.allowed_actions)
    if capability_id not in allowed_tools:
        return False
    return (
        f"{capability_id}.{operation}" in allowed_actions
        or operation in allowed_actions
    )


def _target_ref_from_parameters(params: dict[str, Any]) -> str | None:
    for key in ("target_ref", "target_path", "path", "ref"):
        value = params.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _product_action_kernel_artifact_path(
    kernel: MissionKernel,
    mission_id: str,
    collection: str,
    ref: str,
) -> Path:
    return (
        kernel.store.mission_dir(mission_id, create=True)
        / "product_action_kernel"
        / collection
        / f"{ref}.json"
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


def _low_friction_read_only_power_mode(request: MissionExecutionRequest) -> bool:
    return request.execution_options.get("low_friction_read_only_power_mode") is True


def _model_led_read_only_autopilot(request: MissionExecutionRequest) -> bool:
    return request.execution_options.get("model_led_read_only_autopilot") is True


def _max_material_receipts(request: MissionExecutionRequest) -> int | None:
    value = request.execution_options.get("max_material_receipts")
    return int(value) if value is not None else None


def _max_provider_decision_calls(request: MissionExecutionRequest) -> int | None:
    value = request.execution_options.get("max_provider_decision_calls")
    return int(value) if value is not None else None


def _generate_read_only_mission_summary(request: MissionExecutionRequest) -> bool:
    return request.execution_options.get("generate_read_only_mission_summary") is True


def _write_operator_memory_candidate(request: MissionExecutionRequest) -> bool:
    return request.execution_options.get("write_operator_memory_candidate") is True


def _read_only_artifact_collection_dir(collection: str) -> str:
    if collection == "operator_memory_candidates":
        return "memory"
    return collection


__all__ = [
    "DispatcherTerminalCertificate",
    "DispatchStatus",
    "DispatchProofVerificationResult",
    "MissionExecutionDecisionStore",
    "ProductActionKernelDispatchAdapter",
    "ProductActionKernelFinalGateCertificate",
    "ProductActionKernelReceipt",
    "ReadOnlyResearchAdapter",
    "UnifiedDispatchResult",
    "UnifiedExecutionAdapter",
    "UnifiedExecutionAdapterRegistry",
    "UnifiedExecutionDispatchContext",
    "UnifiedExecutionDispatcher",
]
