from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator import unified_execution_dispatcher as dispatch_mod
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.mission_execution_coordinator import MissionExecutionCoordinator, MissionExecutionRequest
from sentinel.operator.mission_lifecycle_service import MissionLifecycleService
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.power_skill_registry import PowerSkillBackendBinding, PowerSkillRegistry
from sentinel.operator.runtime_connections import (
    RuntimeConnectionMaturity,
    RuntimeConnectionProfile,
    RuntimeConnectionRegistry,
    RuntimeConnectionRoute,
)
from sentinel.operator.unified_execution_dispatcher import (
    DispatchStatus,
    UnifiedExecutionAdapterRegistry,
    UnifiedExecutionDispatcher,
    load_product_action_kernel_artifact,
)


def test_product_dispatchable_skill_routes_through_action_kernel_adapter(tmp_path: Path) -> None:
    adapter_cls = _product_adapter_cls()
    fixture = _ProductActionFixture(tmp_path, product_dispatchable=True)
    adapter = adapter_cls(
        capability_id="workspace_patch",
        operation="apply_patch",
        executor=fixture.executor,
        product_dispatchable_skill_ids=("workspace_patch",),
    )
    dispatcher = fixture.dispatcher(adapter)

    result = dispatcher.dispatch(request=fixture.request, authority=fixture.authority)

    assert result.status is DispatchStatus.COMPLETED
    assert result.adapter_id == "product_action_kernel_adapter"
    assert result.receipt_refs
    assert result.finalgate_refs
    assert fixture.executor_calls == ["workspace_patch:apply_patch"]
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED

    receipt_payload = _product_receipt_payload(fixture, result.receipt_refs[0])
    assert receipt_payload["skill_id"] == "workspace_patch"
    assert receipt_payload["capability_id"] == "workspace_patch"
    assert receipt_payload["operation"] == "apply_patch"
    assert receipt_payload["backend_id"] == "workspace_patch_skill"
    assert receipt_payload["authority_decision"] == "allowed"
    assert receipt_payload["execution_status"] == "completed"
    assert receipt_payload["replay_behavior"] == "no_reexecute_on_replay"
    assert receipt_payload["data_not_authority"] is True
    assert receipt_payload["can_execute"] is False


def test_known_skill_not_product_dispatchable_returns_precise_reason(tmp_path: Path) -> None:
    fixture = _ProductActionFixture(tmp_path, product_dispatchable=False)
    decision = fixture.coordinator.decide(fixture.request)

    assert decision.rejection_reason == "skill_not_product_dispatchable"
    assert decision.skill_id == "workspace_patch"
    assert decision.model_visible_backend_id == "workspace_patch_skill"
    assert decision.task_loop_reachable is True
    assert decision.product_reachable is False


def test_unknown_skill_returns_unknown_skill_not_unknown_capability_connection(tmp_path: Path) -> None:
    fixture = _ProductActionFixture(tmp_path, capability_id="unknown_skill", operation="run", product_dispatchable=False)

    decision = fixture.coordinator.decide(fixture.request)

    assert decision.rejection_reason == "unknown_skill_or_capability"


def test_authority_incompatible_dispatch_blocks_with_clear_reason(tmp_path: Path) -> None:
    adapter_cls = _product_adapter_cls()
    fixture = _ProductActionFixture(tmp_path, product_dispatchable=True, authority_allows_skill=False)
    adapter = adapter_cls(
        capability_id="workspace_patch",
        operation="apply_patch",
        executor=fixture.executor,
        product_dispatchable_skill_ids=("workspace_patch",),
    )
    dispatcher = fixture.dispatcher(adapter)

    result = dispatcher.dispatch(request=fixture.request, authority=fixture.authority)

    assert result.status is DispatchStatus.BLOCKED
    assert result.blocked_reason == "authority_incompatible_dispatch"
    assert fixture.executor_calls == []


def test_recoverable_executor_failure_blocks_without_fake_finalgate(tmp_path: Path) -> None:
    adapter_cls = _product_adapter_cls()
    fixture = _ProductActionFixture(tmp_path, product_dispatchable=True)
    executor_calls: list[str] = []

    def timeout_executor(envelope: ActionEnvelope, _context: dict[str, Any]) -> ActionResult:
        executor_calls.append(f"{envelope.capability_id}:{envelope.operation}")
        raise TimeoutError("locator timeout before material effect")

    adapter = adapter_cls(
        capability_id="workspace_patch",
        operation="apply_patch",
        executor=timeout_executor,
        product_dispatchable_skill_ids=("workspace_patch",),
    )
    dispatcher = fixture.dispatcher(adapter)

    result = dispatcher.dispatch(request=fixture.request, authority=fixture.authority)

    assert result.status is DispatchStatus.BLOCKED
    assert result.blocked_reason == "EXECUTOR_TIMEOUT"
    assert result.receipt_refs
    assert result.finalgate_refs == []
    assert result.terminal_certificate_refs
    assert executor_calls == ["workspace_patch:apply_patch"]
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.BLOCKED

    receipt_payload = _product_receipt_payload(fixture, result.receipt_refs[0])
    assert receipt_payload["execution_status"] == "recoverable_failed"
    assert receipt_payload["recovery_classification"] == "RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE"
    assert receipt_payload["authority_decision"] == "allowed"
    assert receipt_payload["replay_behavior"] == "no_reexecute_on_replay"


def _product_adapter_cls():
    assert hasattr(dispatch_mod, "ProductActionKernelDispatchAdapter"), "ProductActionKernelDispatchAdapter missing"
    return dispatch_mod.ProductActionKernelDispatchAdapter


class _ProductActionFixture:
    def __init__(
        self,
        tmp_path: Path,
        *,
        capability_id: str = "workspace_patch",
        operation: str = "apply_patch",
        product_dispatchable: bool,
        authority_allows_skill: bool = True,
    ) -> None:
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        self.kernel = MissionKernel(run_root=tmp_path / "runs")
        self.lifecycle = MissionLifecycleService(self.kernel)
        self.executor_calls: list[str] = []
        self.capability_id = capability_id
        self.operation = operation
        self.runtime_registry = _runtime_registry(capability_id, operation, product_dispatchable=product_dispatchable)
        self.skill_registry = _skill_registry(capability_id, product_reachable=product_dispatchable)
        self.coordinator = MissionExecutionCoordinator(
            self.runtime_registry,
            power_skill_registry=self.skill_registry,
        )
        mission = self.lifecycle.create_mission(
            session_id="session_pack6",
            draft=MissionDraft(
                title="Product ActionKernel dispatch",
                objective="Execute a bounded product skill through ActionKernel.",
                expected_artifacts=["product action receipt"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="pending",
                allowed_actions=_authority_allowed_actions(capability_id, operation, authority_allows_skill),
                forbidden_actions=["payment", "credential_access", "contact_supplier"],
                summary="Bounded product skill authority.",
            ),
            approval_scope=MissionAuthorityApprovalScope(
                user_id="operator_user",
                allowed_systems=["local_workspace"],
                allowed_tools=_authority_allowed_tools(capability_id, authority_allows_skill),
                allowed_actions=_authority_allowed_actions(capability_id, operation, authority_allows_skill),
                forbidden_actions=["payment", "credential_access", "contact_supplier"],
                allowed_paths=[str(self.workspace)],
                max_duration_minutes=5,
                max_actions=3,
                max_cost_usd=0.0,
            ),
            policy=MissionAuthorityPolicy(
                user_id="operator_user",
                allowed_systems=["local_workspace"],
                allowed_tools=_authority_allowed_tools(capability_id, authority_allows_skill),
                allowed_actions=_authority_allowed_actions(capability_id, operation, authority_allows_skill),
                forbidden_actions=["payment", "credential_access", "contact_supplier"],
                allowed_paths=[str(self.workspace)],
                max_duration_minutes=5,
                max_actions=3,
                max_cost_usd=0.0,
            ),
            capability_id=capability_id,
            operation=operation,
            parameters={"test": "safe"},
            workspace_ref=f"workspace:{self.workspace}",
            model_contract_ref="model_contract:fake",
        )
        self.mission_id = mission.record.mission_id
        self.request = mission.execution_request
        self.authority = mission.authority.envelope

    def dispatcher(self, adapter: Any) -> UnifiedExecutionDispatcher:
        return UnifiedExecutionDispatcher(
            kernel=self.kernel,
            lifecycle=self.lifecycle,
            coordinator=self.coordinator,
            adapter_registry=UnifiedExecutionAdapterRegistry({adapter.adapter_id: adapter}),
        )

    def executor(self, envelope: ActionEnvelope, _context: dict[str, Any]) -> ActionResult:
        self.executor_calls.append(f"{envelope.capability_id}:{envelope.operation}")
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            material_action=True,
            observation_summary="bounded product skill executed.",
        )


def _runtime_registry(capability_id: str, operation: str, *, product_dispatchable: bool) -> RuntimeConnectionRegistry:
    if not product_dispatchable:
        return RuntimeConnectionRegistry(connections=())
    return RuntimeConnectionRegistry(
        connections=(
            RuntimeConnectionProfile(
                connection_id=capability_id,
                display_name="Test product action skill",
                runtime_generation="product_action_kernel",
                authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                owner_module="sentinel.operator.unified_execution_dispatcher",
                owner_symbol="ProductActionKernelDispatchAdapter",
                adapter_id="product_action_kernel_adapter",
                supported_operations=(operation,),
                authority_requirement="MissionAuthorityEnvelope must grant the exact skill action.",
                authority_actions=(f"{capability_id}.{operation}",),
                receipt_contract="ProductActionKernelReceipt",
                finalgate_contract="ProductActionKernelFinalGateCertificate",
                replay_adapter="ProductActionKernelReplayView",
                production_reachable=True,
                limitations=("test-only bounded product action kernel route",),
            ),
        )
    )


def _authority_allowed_tools(capability_id: str, authority_allows_skill: bool) -> list[str]:
    return [capability_id] if authority_allows_skill else ["read_only_research"]


def _authority_allowed_actions(capability_id: str, operation: str, authority_allows_skill: bool) -> list[str]:
    return [f"{capability_id}.{operation}"] if authority_allows_skill else ["read_only_research.list_directory"]


def _skill_registry(capability_id: str, *, product_reachable: bool) -> PowerSkillRegistry:
    if capability_id == "unknown_skill":
        return PowerSkillRegistry(bindings=())
    return PowerSkillRegistry(
        bindings=(
            PowerSkillBackendBinding(
                skill_id=capability_id,
                capability_id=capability_id,
                model_visible_backend_id=f"{capability_id}_skill",
                owner_module="tests.operator.test_power_cleanup_product_action_kernel_dispatch_adapter",
                owner_symbol="_ProductActionFixture",
                backend_candidates=(f"{capability_id}_runtime",),
                product_reachable=product_reachable,
                task_loop_reachable=True,
                proof_contract="ProductActionKernelReceipt",
                replay_contract="ProductActionKernelReplayView no-react",
            ),
        )
    )


def _product_receipt_payload(fixture: _ProductActionFixture, receipt_ref: str) -> dict[str, Any]:
    payload = load_product_action_kernel_artifact(fixture.kernel, fixture.mission_id, "receipts", receipt_ref)
    assert payload is not None
    return payload
