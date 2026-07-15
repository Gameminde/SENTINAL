from __future__ import annotations

import os
import threading
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.agent.organs.channel_draft_send_organ_v1 import ChannelSendTransportReceipt
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.authority_issuer import MissionAuthorityEnvelopeIssuer
from sentinel.operator.channel_adapter import (
    ChannelConnectorRuntime,
    ChannelConnectorRuntimeError,
    build_telegram_channel_transport_from_env,
)
from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterKind,
    ChannelProviderKind,
    ChannelRecipientPolicy,
    ChannelScopePolicy,
)
from sentinel.operator.code_execution_sandbox_runtime import CodeExecutionSandboxRuntime
from sentinel.operator.connection_live_channel_action_runtime import ModelLedLiveChannelActionRuntime
from sentinel.operator.daemon_models import DaemonQueueStatus, MissionDaemonConfig, daemon_utc_now
from sentinel.operator.daemon_runtime import MissionDaemonRuntime
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequest
from sentinel.operator.mission_execution_coordinator import MissionExecutionCoordinator
from sentinel.operator.mission_lifecycle_service import MissionLifecycleService
from sentinel.operator.mission_workspace_runtime import MissionWorkspaceRuntime, mission_workspace_product_body_frame
from sentinel.operator.browser_environment_state import browser_environment_state_contract
from sentinel.operator.browser_product_cutover_registry import build_default_browser_product_cutover_registry
from sentinel.operator.model_skill_surface import compile_model_skill_surface
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.read_only_operator_spine import ReadOnlyActionKind, ReadOnlyDecision, ReadOnlyDecisionClient, ReadOnlyReportClient
from sentinel.operator.real_browser_control_runtime import (
    BOUNDED_URL_AUTHORITY_REF,
    CLOAK_BROWSER_BACKEND_ID,
    RealBrowserControlRuntime,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
    build_cloak_first_real_browser_engine_from_env,
)
from sentinel.operator.runtime_connections import RuntimeConnectionRegistry, build_default_runtime_connection_registry
from sentinel.operator.unified_execution_dispatcher import (
    ProductActionKernelRoute,
    ProductActionKernelDispatchAdapter,
    ReadOnlyResearchAdapter,
    UnifiedExecutionAdapterRegistry,
    UnifiedExecutionDispatcher,
)
from sentinel.operator.workspace_patch_runtime import SENSITIVE_WORKSPACE_PATCH_NAMES, WorkspacePatchRuntime
from sentinel.operator.worker_orchestration_runtime import (
    WorkerOrchestrationRuntime,
    worker_orchestration_preflight,
)
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.shared.models import SentinelModel, new_id


LOCAL_FIXTURE_BROWSER_BACKEND_ID = "local_fixture_browser_engine"
LOCAL_FIXTURE_BROWSER_SESSION_KIND = "local_fixture"

_LIVE_CLOAK_ENGINE_LOCK = threading.RLock()

_TRUSTED_RUNTIME_CONTEXT_KEYS = frozenset(
    {
        "adapter_id",
        "authority",
        "backend_id",
        "execution_request_id",
        "kernel",
        "mission_id",
        "mission_workspace_manifest",
        "organ_id",
        "parameter_hash",
        "product_task_resource_scope",
        "root_browser_runtime_lease",
        "simple_skill_id",
        "workspace_ref",
    }
)

_MODEL_EVIDENCE_CONTEXT_ALLOWLIST = frozenset(
    {
        "actionability_frame",
        "bounded_observation_summaries",
        "browser_actionability_registry",
        "browser_backend_execution",
        "browser_cognitive_decision_frame",
        "browser_decision_frame",
        "browser_devtools_context",
        "browser_environment_state",
        "browser_environment_state_hash",
        "browser_observation_bundle",
        "browser_search_materiality",
        "browser_world_model",
        "browser_world_model_summary",
        "completion_requirements",
        "dispatch_summaries",
        "finish_available",
        "grounded_evidence_summary",
        "last_browser_action_summary",
        "mission_objective",
        "objective_satisfied",
        "progress_state",
        "real_browser_control_summary",
        "recoverable_action_observations",
    }
)


class RuntimeHostStatus(StrEnum):
    CREATED = "created"
    STARTED = "started"
    STOPPED = "stopped"


class RuntimeHostStatusView(SentinelModel):
    status: RuntimeHostStatus
    started: bool
    daemon_available: bool
    connection_count: int
    active_mission_count: int = 0
    host: object = Field(exclude=True)


class RuntimeHostDaemonPumpResult(SentinelModel):
    mission_id: str
    execution_request_ref: str
    claimed: bool
    tick_result: object | None = Field(default=None, exclude=True)
    dispatch_result: object | None = Field(default=None, exclude=True)


class ProductTaskBrowserRuntimeLease:
    """Root-task owner for one executable browser body.

    The lease owns the engine/session resources. Child missions receive only
    data-only refs and wrap the same engine in their per-mission runtime so
    receipts stay attached to the child MissionRecord while the browser body
    stays continuous.
    """

    backend_concurrency_capability = "one_active_cloak_context_global_measured"

    def __init__(
        self,
        *,
        root_scope_id: str,
        root_session_id: str,
        workspace_root: Path,
    ) -> None:
        self.root_scope_id = root_scope_id
        self.root_session_id = root_session_id
        self.workspace_root = workspace_root
        self.lease_id = f"browser_runtime_lease_{stable_hash({'root_scope_id': root_scope_id})[:16]}"
        self.safe_ref = f"root_browser_lease:{stable_hash({'lease_id': self.lease_id})[:16]}"
        self.lease_hash = stable_hash(
            {
                "lease_id": self.lease_id,
                "root_scope_id": self.root_scope_id,
                "root_session_id_hash": text_hash(self.root_session_id),
                "workspace_root_hash": stable_hash(str(self.workspace_root)),
            }
        )
        self.lifecycle_state = "created"
        self.engine: object | None = None
        self.open_count = 0
        self.close_count = 0
        self.recovery_attempt_count = 0
        self.last_failure_fingerprint: str | None = None
        self.live_context_lock_acquired = False
        self.live_context_lock_acquire_count = 0

    def engine_for(self, envelope: ActionEnvelope) -> object:
        if self.engine is None:
            self._acquire_live_context_lock_if_needed(envelope)
            try:
                self.engine = _product_browser_engine(envelope)
                self.open_count += 1
                self.lifecycle_state = "active"
            except Exception:
                self._release_live_context_lock_if_needed()
                raise
        return self.engine

    def recover_engine_once(self, envelope: ActionEnvelope) -> bool:
        if self.recovery_attempt_count >= 1:
            return False
        self.recovery_attempt_count += 1
        self.close_engine(mark_state="recovering")
        self._acquire_live_context_lock_if_needed(envelope)
        try:
            self.engine = _product_browser_engine(envelope)
            self.open_count += 1
            self.lifecycle_state = "active_after_recovery"
        except Exception:
            self._release_live_context_lock_if_needed()
            raise
        return True

    def close_engine(self, *, mark_state: str = "closed") -> None:
        engine = self.engine
        self.engine = None
        if engine is None:
            self._release_live_context_lock_if_needed()
            self.lifecycle_state = mark_state
            return
        close = getattr(engine, "close", None)
        close_all = getattr(engine, "close_all", None)
        try:
            if callable(close):
                close()
            elif callable(close_all):
                close_all()
        finally:
            self._release_live_context_lock_if_needed()
            self.close_count += 1
            self.lifecycle_state = mark_state

    def close(self) -> None:
        self.close_engine(mark_state="closed")

    def _acquire_live_context_lock_if_needed(self, envelope: ActionEnvelope) -> None:
        if not _product_browser_engine_requires_global_lock(envelope):
            return
        _LIVE_CLOAK_ENGINE_LOCK.acquire()
        self.live_context_lock_acquired = True
        self.live_context_lock_acquire_count += 1

    def _release_live_context_lock_if_needed(self) -> None:
        if not self.live_context_lock_acquired:
            return
        self.live_context_lock_acquired = False
        _LIVE_CLOAK_ENGINE_LOCK.release()

    def safe_model_dump(self) -> dict[str, object]:
        backend_id = _safe_engine_backend_id(self.engine)
        return {
            "lease_id": self.lease_id,
            "safe_ref": self.safe_ref,
            "lease_hash": self.lease_hash,
            "root_scope_id_hash": stable_hash(self.root_scope_id),
            "root_session_id_hash": text_hash(self.root_session_id),
            "lifecycle_state": self.lifecycle_state,
            "selected_backend_id": backend_id,
            "actual_backend_id": backend_id,
            "backend_concurrency_capability": self.backend_concurrency_capability,
            "global_context_lock_acquired": self.live_context_lock_acquired,
            "global_context_lock_acquire_count": self.live_context_lock_acquire_count,
            "open_count": self.open_count,
            "close_count": self.close_count,
            "recovery_attempt_count": self.recovery_attempt_count,
            "data_not_authority": True,
            "can_grant_authority": False,
            "can_execute": False,
        }

    def failure_fingerprint(
        self,
        *,
        envelope: ActionEnvelope,
        failure_code: str,
        context_cards: dict[str, Any],
    ) -> str:
        return stable_hash(
            {
                "capability": envelope.capability_id,
                "operation": envelope.operation,
                "body_lifecycle_state": self.lifecycle_state,
                "browser_environment_state_hash": str(context_cards.get("browser_environment_state_hash") or ""),
                "session_lease_hash": self.lease_hash,
                "failure_code": failure_code,
                "backend_identity": _safe_engine_backend_id(self.engine),
                "origin_hash": _safe_engine_origin_hash(self.engine),
            }
        )


class ProductTaskResourceScope:
    def __init__(
        self,
        *,
        scope_id: str,
        root_session_id: str,
        workspace_root: Path,
    ) -> None:
        self.scope_id = scope_id
        self.root_session_id = root_session_id
        self.workspace_root = workspace_root
        self.browser_lease: ProductTaskBrowserRuntimeLease | None = None
        self.closed = False

    def browser_engine_for(self, envelope: ActionEnvelope) -> object:
        if self.closed:
            raise RuntimeError("product_task_resource_scope_closed")
        if self.browser_lease is None:
            self.browser_lease = ProductTaskBrowserRuntimeLease(
                root_scope_id=self.scope_id,
                root_session_id=self.root_session_id,
                workspace_root=self.workspace_root,
            )
        return self.browser_lease.engine_for(envelope)

    def recover_browser_engine_once(self, envelope: ActionEnvelope) -> bool:
        if self.browser_lease is None or self.closed:
            return False
        return self.browser_lease.recover_engine_once(envelope)

    def browser_lease_card(self) -> dict[str, object]:
        if self.browser_lease is None:
            return {
                "root_scope_id_hash": stable_hash(self.scope_id),
                "root_session_id_hash": text_hash(self.root_session_id),
                "lifecycle_state": "not_acquired",
                "backend_concurrency_capability": ProductTaskBrowserRuntimeLease.backend_concurrency_capability,
                "data_not_authority": True,
                "can_grant_authority": False,
                "can_execute": False,
            }
        return self.browser_lease.safe_model_dump()

    def close(self) -> None:
        if self.closed:
            return
        try:
            if self.browser_lease is not None:
                self.browser_lease.close()
        finally:
            self.closed = True


class SentinelRuntimeHost:
    """Process-level owner for Pack 1 operator runtime infrastructure."""

    def __init__(
        self,
        *,
        run_root: Path | str,
        telemetry_sink: object | None = None,
        daemon_config: MissionDaemonConfig | None = None,
        connection_registry: RuntimeConnectionRegistry | None = None,
        adapter_registry: UnifiedExecutionAdapterRegistry | None = None,
        read_only_decision_client_factory: Callable[[MissionExecutionRequest, MissionAuthorityEnvelope], ReadOnlyDecisionClient] | None = None,
        read_only_report_client_factory: Callable[[MissionExecutionRequest, MissionAuthorityEnvelope], ReadOnlyReportClient] | None = None,
        require_read_only_model_clients: bool = False,
    ) -> None:
        if require_read_only_model_clients and (
            read_only_decision_client_factory is None or read_only_report_client_factory is None
        ):
            raise RuntimeError("read_only_provider_execution_factories_required")
        self.kernel = MissionKernel(run_root=run_root, telemetry_sink=telemetry_sink)
        self.connection_registry = connection_registry or build_default_runtime_connection_registry()
        self.coordinator = MissionExecutionCoordinator(self.connection_registry)
        self.authority_issuer = MissionAuthorityEnvelopeIssuer(self.kernel)
        self.workflow_runtime = DurableMissionWorkflowRuntime(self.kernel)
        self.daemon = MissionDaemonRuntime(
            self.kernel,
            config=daemon_config or MissionDaemonConfig(require_certified_telemetry=False),
            workflow_runtime=self.workflow_runtime,
        )
        self.lifecycle = MissionLifecycleService(
            self.kernel,
            authority_issuer=self.authority_issuer,
            daemon_runtime=self.daemon,
        )
        self.mission_workspace_runtime = MissionWorkspaceRuntime(self.kernel)
        self.adapter_registry = adapter_registry or UnifiedExecutionAdapterRegistry(
            {
                "read_only_research_adapter": ReadOnlyResearchAdapter(
                    decision_client_factory=read_only_decision_client_factory or _default_read_only_decision_client,
                    report_client_factory=read_only_report_client_factory or _default_read_only_report_client,
                ),
                "product_action_kernel_adapter": ProductActionKernelDispatchAdapter(
                    capability_id="workspace_patch",
                    operation="apply_patch",
                    executor=_default_workspace_patch_executor,
                    product_dispatchable_skill_ids=("workspace_patch",),
                    backend_id="workspace_patch_skill",
                    organ_id="workspace_patch",
                    preflight_validator=_workspace_patch_apply_preflight,
                    extra_routes=(
                        ProductActionKernelRoute(
                            capability_id="code_execution_sandbox",
                            operation="code_exec.run_profile",
                            executor=_default_code_execution_executor,
                            product_dispatchable_skill_ids=("code_execution_sandbox",),
                            backend_id="code_execution_skill",
                            organ_id="code_execution_sandbox",
                        ),
                        ProductActionKernelRoute(
                            capability_id="bounded_channel",
                            operation="send_message",
                            executor=_default_bounded_channel_executor,
                            product_dispatchable_skill_ids=("bounded_channel",),
                            backend_id="bounded_channel_skill",
                            organ_id="channel_draft_send",
                            preflight_validator=_bounded_channel_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="real_browser_control",
                            operation="real_browser.search",
                            executor=_default_real_browser_executor,
                            product_dispatchable_skill_ids=("real_browser_control",),
                            backend_id="browser_skill",
                            simple_skill_id="browse_search",
                            organ_id="browser_l5_l6_backend",
                            preflight_validator=_real_browser_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="real_browser_control",
                            operation="real_browser.extract_product_cards",
                            executor=_default_real_browser_executor,
                            product_dispatchable_skill_ids=("real_browser_control",),
                            backend_id="browser_skill",
                            simple_skill_id="extract",
                            organ_id="browser_l5_l6_backend",
                            preflight_validator=_real_browser_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="real_browser_control",
                            operation="real_browser.verify_extraction",
                            executor=_default_real_browser_executor,
                            product_dispatchable_skill_ids=("real_browser_control",),
                            backend_id="browser_skill",
                            simple_skill_id="extract",
                            organ_id="browser_l5_l6_backend",
                            preflight_validator=_real_browser_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="real_browser_control",
                            operation="real_browser.inspect_result",
                            executor=_default_real_browser_executor,
                            product_dispatchable_skill_ids=("real_browser_control",),
                            backend_id="browser_skill",
                            simple_skill_id="browse_search",
                            organ_id="browser_l5_l6_backend",
                            preflight_validator=_real_browser_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="real_browser_control",
                            operation="real_browser.open_result",
                            executor=_default_real_browser_executor,
                            product_dispatchable_skill_ids=("real_browser_control",),
                            backend_id="browser_skill",
                            simple_skill_id="browse_search",
                            organ_id="browser_l5_l6_backend",
                            preflight_validator=_real_browser_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="worker_fleet",
                            operation="spawn_worker",
                            executor=_default_worker_fleet_executor,
                            product_dispatchable_skill_ids=("worker_fleet",),
                            backend_id="worker_fleet_skill",
                            simple_skill_id="spawn_worker",
                            organ_id="worker_fleet_backend",
                            preflight_validator=_worker_fleet_preflight,
                        ),
                        ProductActionKernelRoute(
                            capability_id="sentinel_loop",
                            operation="summarize_evidence",
                            executor=_default_sentinel_loop_executor,
                            product_dispatchable_skill_ids=("sentinel_loop",),
                            backend_id="sentinel_loop_skill",
                            simple_skill_id="finish",
                            organ_id="sentinel_loop",
                        ),
                    ),
                ),
            }
        )
        self.dispatcher = UnifiedExecutionDispatcher(
            kernel=self.kernel,
            lifecycle=self.lifecycle,
            coordinator=self.coordinator,
            adapter_registry=self.adapter_registry,
        )
        self._product_task_resource_scopes: dict[str, ProductTaskResourceScope] = {}
        self._status = RuntimeHostStatus.CREATED

    def start(self) -> RuntimeHostStatusView:
        if self._status is RuntimeHostStatus.STARTED:
            return self.status()
        self.daemon.start()
        self._status = RuntimeHostStatus.STARTED
        return self.status()

    def shutdown(self) -> RuntimeHostStatusView:
        if self._status is RuntimeHostStatus.STOPPED:
            return self.status()
        self.close_all_product_task_resource_scopes()
        self.daemon.stop()
        self._status = RuntimeHostStatus.STOPPED
        return self.status()

    def status(self) -> RuntimeHostStatusView:
        return RuntimeHostStatusView(
            status=self._status,
            started=self._status is RuntimeHostStatus.STARTED,
            daemon_available=self.daemon is not None,
            connection_count=len(self.connection_registry.connections),
            active_mission_count=len(self.kernel.list_missions()),
            host=self,
        )

    def product_task_loop_entrypoint_frame(self) -> dict[str, Any]:
        model_visible_available_actions = [
            "workspace_patch.apply_patch",
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "worker_fleet.spawn_worker",
            "sentinel_loop.finish",
        ]
        model_skill_surface = compile_model_skill_surface(
            model_visible_actions=model_visible_available_actions,
            recommended_actions=model_visible_available_actions,
        )
        browser_product_cutover_frame = (
            build_default_browser_product_cutover_registry()
            .compile_frame()
            .safe_model_dump()
        )
        browser_environment_contract = browser_environment_state_contract()
        return {
            "entrypoint_id": "product_action_kernel_task_loop",
            "enabled": True,
            "runtime_bridge": "ModelLedProductActionKernelTaskLoop",
            "material_execution_owner": "RuntimeHost -> UnifiedExecutionDispatcher -> ProductActionKernelDispatchAdapter",
            "primary_model_surface": "model_visible_skills",
            "primary_model_language": "simple_mission_skills",
            "action_envelope_language": "internal_runtime_only",
            "model_skill_surface": model_skill_surface,
            "model_visible_skills": list(model_skill_surface["model_visible_skills"]),
            "primary_model_next_recommended_skills": list(model_skill_surface["recommended_next_skills"]),
            "primary_model_recommended_next_skill": model_skill_surface["primary_recommended_skill"],
            "runtime_internal_action_map": dict(model_skill_surface["runtime_internal_action_map"]),
            "model_visible_available_actions": model_visible_available_actions,
            "browser_product_cutover_frame": browser_product_cutover_frame,
            "browser_environment_state_contract": browser_environment_contract,
            "hidden_backend_bindings": [
                "browser_l5_l6_backend",
                "cloak_session_backend",
                "playwright_compatibility_backend",
                "worker_fleet_backend",
            ],
            "internal_or_out_of_scope_actions": [
                "real_browser_control.real_browser.type_text",
                "real_browser_control.real_browser.click",
                "real_browser_control.real_browser.select_option",
                "real_browser_control.real_browser.press_key",
                "browser_control.click",
                "payment_authority.spend",
                "credential_vault.read_secret",
                "external_channel.contact_supplier",
            ],
            "hard_boundaries": [
                "payment",
                "credential_access",
                "contact_supplier",
                "browser_login",
                "real_external_channel_without_explicit_grant",
                "provider_native_tools",
                "fallback_auto",
                "replay_side_effects",
            ],
            "data_not_authority": True,
            "authority_effect": "none",
            "can_grant_authority": False,
            "can_execute": False,
        }

    def mission_workspace_entrypoint_frame(self) -> dict[str, Any]:
        return mission_workspace_product_body_frame()

    def prepare_mission_workspace(
        self,
        *,
        mission_id: str,
        workspace_root: Path | str,
        allowed_domains: tuple[str, ...] = (),
        channel_destination_refs: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        manifest = self.mission_workspace_runtime.prepare(
            mission_id=mission_id,
            workspace_root=workspace_root,
            allowed_domains=allowed_domains,
            channel_destination_refs=channel_destination_refs,
        )
        return manifest.safe_model_dump(include_manifest_path=True)

    def run_product_action_kernel_task_loop(
        self,
        *,
        workspace_root: Path | str,
        session_id: str,
        mission_objective: str,
        decision_client: object,
        allowed_domains: tuple[str, ...] = (),
        max_model_calls: int = 6,
        max_material_actions: int = 3,
        max_recoverable_model_decision_failures: int = 0,
        max_recoverable_action_failures: int = 0,
        model_contract_ref: str = "model_contract:product_action_kernel_task_loop_entrypoint",
        explicit_noop_proof_ref: str | None = None,
    ) -> object:
        if self._status is not RuntimeHostStatus.STARTED:
            raise RuntimeError("runtime_host_not_started")
        from sentinel.operator.model_led_product_action_kernel_task_loop import ModelLedProductActionKernelTaskLoop

        resource_scope = self.create_product_task_resource_scope(
            root_session_id=session_id,
            workspace_root=workspace_root,
        )
        try:
            loop = ModelLedProductActionKernelTaskLoop(
                host=self,
                workspace_root=workspace_root,
                session_id=session_id,
                mission_objective=mission_objective,
                decision_client=decision_client,
                allowed_domains=allowed_domains,
                max_model_calls=max_model_calls,
                max_material_actions=max_material_actions,
                max_recoverable_model_decision_failures=max_recoverable_model_decision_failures,
                max_recoverable_action_failures=max_recoverable_action_failures,
                model_contract_ref=model_contract_ref,
                explicit_noop_proof_ref=explicit_noop_proof_ref,
                product_task_resource_scope=resource_scope,
            )
            return loop.run()
        finally:
            resource_scope.close()
            self._product_task_resource_scopes.pop(resource_scope.scope_id, None)

    def create_product_task_resource_scope(
        self,
        *,
        root_session_id: str,
        workspace_root: Path | str,
    ) -> ProductTaskResourceScope:
        scope = ProductTaskResourceScope(
            scope_id=f"product_task_resource_scope_{new_id('scope')}",
            root_session_id=root_session_id,
            workspace_root=Path(workspace_root).resolve(),
        )
        self._product_task_resource_scopes[scope.scope_id] = scope
        return scope

    def close_all_product_task_resource_scopes(self) -> None:
        for scope in tuple(self._product_task_resource_scopes.values()):
            scope.close()
        self._product_task_resource_scopes.clear()

    def pump_daemon_once(
        self,
        mission_id: str,
        *,
        product_task_resource_scope: object | None = None,
    ) -> RuntimeHostDaemonPumpResult:
        if self._status is not RuntimeHostStatus.STARTED:
            raise RuntimeError("runtime_host_not_started")
        request = self.lifecycle.latest_execution_request(mission_id)
        try:
            envelope = self.authority_issuer.resolve_active(mission_id)
        except ValueError as exc:
            reason = str(exc)
            if "revoked" in reason:
                if not self.kernel.is_terminal(mission_id):
                    self.kernel.update_status(mission_id, OperatorMissionStatus.REVOKED, "Mission authority revoked before dispatch.")
            elif "expired" in reason and not self.kernel.is_terminal(mission_id):
                self.kernel.update_status(mission_id, OperatorMissionStatus.BLOCKED, "Mission authority expired before dispatch.")
            return RuntimeHostDaemonPumpResult(
                mission_id=mission_id,
                execution_request_ref=request.request_id,
                claimed=False,
                tick_result=None,
                dispatch_result=None,
            )
        self.daemon.claim_lease(mission_id, now=daemon_utc_now())
        self.daemon.store.update_queue_status(
            mission_id,
            DaemonQueueStatus.RUNNING,
            safe_reason="Daemon lease claimed; unified dispatcher handoff starting.",
        )
        claimed_request = self.lifecycle.mark_request_claimed(mission_id, request.request_id)
        dispatch_result = self.dispatcher.dispatch(
            request=request,
            authority=envelope,
            product_task_resource_scope=product_task_resource_scope,
        )
        return RuntimeHostDaemonPumpResult(
            mission_id=mission_id,
            execution_request_ref=claimed_request.request_id,
            claimed=True,
            tick_result=None,
            dispatch_result=dispatch_result,
        )


__all__ = [
    "RuntimeHostDaemonPumpResult",
    "RuntimeHostStatus",
    "RuntimeHostStatusView",
    "SentinelRuntimeHost",
]


def _default_read_only_decision_client(_request: MissionExecutionRequest, _authority: MissionAuthorityEnvelope) -> ReadOnlyDecisionClient:
    return ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ]
    )


def _default_read_only_report_client(_request: MissionExecutionRequest, _authority: MissionAuthorityEnvelope) -> ReadOnlyReportClient:
    return ReadOnlyReportClient()


def _default_workspace_patch_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    kernel = context.get("kernel")
    if not isinstance(authority, MissionAuthorityEnvelope) or not isinstance(kernel, MissionKernel):
        raise RuntimeError("workspace_patch_runtime_context_missing")
    runtime = WorkspacePatchRuntime(
        kernel=kernel,
        mission_id=str(context.get("mission_id") or ""),
        workspace_root=_workspace_path_from_ref(str(context.get("workspace_ref") or "")),
    )
    return runtime.execute(envelope, authority=authority, context=context)


def _default_code_execution_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    kernel = context.get("kernel")
    if not isinstance(authority, MissionAuthorityEnvelope) or not isinstance(kernel, MissionKernel):
        raise RuntimeError("code_execution_runtime_context_missing")
    runtime = CodeExecutionSandboxRuntime(
        kernel=kernel,
        mission_id=str(context.get("mission_id") or ""),
        workspace_root=_workspace_path_from_ref(str(context.get("workspace_ref") or "")),
    )
    return runtime.execute(envelope, authority=authority, context=context)


def _default_bounded_channel_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    kernel = context.get("kernel")
    if not isinstance(authority, MissionAuthorityEnvelope) or not isinstance(kernel, MissionKernel):
        raise RuntimeError("bounded_channel_runtime_context_missing")
    params = dict(envelope.params)
    adapter_id = str(params.get("adapter_id") or "").strip()
    channel = str(params.get("channel") or "webhook").strip().lower()
    transports = {}
    if adapter_id != "missing_local_transport":
        transports[adapter_id] = _channel_transport_for(channel)
    channel_runtime = ChannelConnectorRuntime(
        kernel,
        transports=transports,
        product_dispatch_owner="product_action_kernel_adapter",
    )
    config = ChannelAdapterConfig(
        adapter_id=adapter_id,
        kind=ChannelAdapterKind.WEBHOOK,
        provider_kind=ChannelProviderKind.WEBHOOK,
        display_name=_channel_display_name(channel),
        recipient_policy=ChannelRecipientPolicy(
            allowed_domains=list(authority.allowed_domains or []),
            max_recipients=max(int(getattr(authority, "max_recipients", 1) or 1), 1),
        ),
        scope_policy=ChannelScopePolicy(allowed_channels=[channel]),
        approval_policy={"approval_required_for_send": False},
        metadata={"transport_kind": _channel_transport_kind(channel)},
    )
    channel_runtime.register_adapter(mission_id=str(context.get("mission_id") or ""), config=config)
    channel_authority = _channel_send_authority(authority)
    runtime = ModelLedLiveChannelActionRuntime(channel_runtime)
    return runtime.execute_action_envelope(
        mission_id=str(context.get("mission_id") or ""),
        envelope=envelope,
        authority=channel_authority,
    )


def _trusted_runtime_context_with_model_evidence(context: dict[str, Any], envelope: ActionEnvelope) -> dict[str, Any]:
    loop_context = context.get("loop_context")
    if not isinstance(loop_context, dict):
        candidate = envelope.params.get("loop_context")
        loop_context = candidate if isinstance(candidate, dict) else None
    runtime_context = dict(context)
    if not isinstance(loop_context, dict):
        return runtime_context
    model_evidence = {
        key: value
        for key, value in loop_context.items()
        if key in _MODEL_EVIDENCE_CONTEXT_ALLOWLIST and key not in _TRUSTED_RUNTIME_CONTEXT_KEYS
    }
    runtime_context.update(model_evidence)
    runtime_context["model_evidence"] = model_evidence
    return runtime_context


def _default_real_browser_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    kernel = context.get("kernel")
    if not isinstance(authority, MissionAuthorityEnvelope) or not isinstance(kernel, MissionKernel):
        raise RuntimeError("real_browser_runtime_context_missing")
    mission_id = str(context.get("mission_id") or "")
    workspace_root = _workspace_path_from_ref(str(context.get("workspace_ref") or ""))
    manifest = MissionWorkspaceRuntime(kernel).prepare(
        mission_id=mission_id,
        workspace_root=workspace_root,
        allowed_domains=tuple(authority.allowed_domains or ()),
    )
    browser_handle = _mission_workspace_browser_session_handle(manifest.safe_model_dump())
    runtime_context = _trusted_runtime_context_with_model_evidence(context, envelope)
    runtime_context["mission_workspace_manifest"] = manifest.safe_model_dump()
    scope = context.get("product_task_resource_scope")
    if isinstance(scope, ProductTaskResourceScope):
        engine = scope.browser_engine_for(envelope)
        runtime_context["root_browser_runtime_lease"] = scope.browser_lease_card()
        result = _execute_real_browser_action(
            kernel=kernel,
            mission_id=mission_id,
            engine=engine,
            session_ref=str(browser_handle.get("safe_ref") or "mission_workspace:browser_session"),
            envelope=envelope,
            authority=authority,
            runtime_context=runtime_context,
        )
        if not _is_browser_body_failure(result):
            return result
        first_fingerprint = _body_failure_fingerprint(scope, envelope=envelope, result=result)
        if not scope.recover_browser_engine_once(envelope):
            return _body_session_unavailable_result(envelope, scope=scope, prior_result=result, fingerprint=first_fingerprint)
        recovered_context = dict(runtime_context)
        recovered_context["root_browser_runtime_lease"] = scope.browser_lease_card()
        recovered = _execute_real_browser_action(
            kernel=kernel,
            mission_id=mission_id,
            engine=scope.browser_engine_for(envelope),
            session_ref=str(browser_handle.get("safe_ref") or "mission_workspace:browser_session"),
            envelope=envelope,
            authority=authority,
            runtime_context=recovered_context,
        )
        second_fingerprint = _body_failure_fingerprint(scope, envelope=envelope, result=recovered)
        if _is_browser_body_failure(recovered):
            return _body_session_unavailable_result(
                envelope,
                scope=scope,
                prior_result=recovered,
                fingerprint=second_fingerprint,
            )
        return recovered
    return _execute_real_browser_action(
        kernel=kernel,
        mission_id=mission_id,
        engine=_product_browser_engine(envelope),
        session_ref=str(browser_handle.get("safe_ref") or "mission_workspace:browser_session"),
        envelope=envelope,
        authority=authority,
        runtime_context=runtime_context,
    )


def _execute_real_browser_action(
    *,
    kernel: MissionKernel,
    mission_id: str,
    engine: object,
    session_ref: str,
    envelope: ActionEnvelope,
    authority: MissionAuthorityEnvelope,
    runtime_context: dict[str, Any],
) -> ActionResult:
    runtime = RealBrowserControlRuntime(
        kernel=kernel,
        mission_id=mission_id,
        engine=engine,
        session_ref=session_ref,
        selected_backend_id=_safe_engine_backend_id(engine),
        product_context=runtime_context,
    )
    return runtime.execute(envelope, authority=_real_browser_authority(authority), context=runtime_context)


def _is_browser_body_failure(result: ActionResult) -> bool:
    return result.failure_code in {
        "real_browser_search_session_open_failed",
        "real_browser_session_open_failed",
        "real_browser_body_session_open_failed",
    }


def _body_failure_fingerprint(
    scope: ProductTaskResourceScope,
    *,
    envelope: ActionEnvelope,
    result: ActionResult,
) -> str:
    if scope.browser_lease is None:
        return stable_hash({"failure_code": result.failure_code or "", "lease": "not_acquired"})
    return scope.browser_lease.failure_fingerprint(
        envelope=envelope,
        failure_code=result.failure_code or result.blocked_reason or "browser_body_failure",
        context_cards=result.context_cards,
    )


def _body_session_unavailable_result(
    envelope: ActionEnvelope,
    *,
    scope: ProductTaskResourceScope,
    prior_result: ActionResult,
    fingerprint: str,
) -> ActionResult:
    context_cards = dict(prior_result.context_cards)
    context_cards["body_circuit_breaker"] = {
        "failure_code": "BODY_SESSION_UNAVAILABLE",
        "prior_failure_code": prior_result.failure_code or prior_result.blocked_reason,
        "failure_fingerprint": fingerprint,
        "root_browser_runtime_lease": scope.browser_lease_card(),
        "provider_recall_allowed": False,
        "model_recall_allowed": False,
        "data_not_authority": True,
        "can_execute": False,
    }
    return ActionResult(
        action_id=envelope.action_id,
        capability_id=envelope.capability_id,
        operation=envelope.operation,
        status="blocked",
        material_action=False,
        observation_summary="Browser body remained unavailable after one bounded mechanical recovery.",
        blocked_reason="BODY_SESSION_UNAVAILABLE",
        failure_class=ActionFailureClass.SOURCE_BUG_OR_RUNTIME_INVARIANT,
        failure_code="BODY_SESSION_UNAVAILABLE",
        recoverable=False,
        context_cards=context_cards,
        recommended_next_actions=(),
    )


def _default_worker_fleet_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    kernel = context.get("kernel")
    if not isinstance(authority, MissionAuthorityEnvelope) or not isinstance(kernel, MissionKernel):
        raise RuntimeError("worker_fleet_runtime_context_missing")
    runtime = WorkerOrchestrationRuntime(
        kernel=kernel,
        mission_id=str(context.get("mission_id") or ""),
        workspace_root=_workspace_path_from_ref(str(context.get("workspace_ref") or "")),
        product_context=context,
    )
    return runtime.execute(envelope, authority=authority, context=context)


def _default_sentinel_loop_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
    authority = context.get("authority")
    if not isinstance(authority, MissionAuthorityEnvelope):
        raise RuntimeError("sentinel_loop_runtime_context_missing")
    effective_context = _trusted_runtime_context_with_model_evidence(context, envelope)
    return ActionKernel().execute(envelope, authority=authority, context=effective_context)


def _real_browser_preflight(
    params: dict[str, Any],
    request: MissionExecutionRequest,
    _authority: MissionAuthorityEnvelope,
) -> str | None:
    browser_cortex_case_id = str(params.get("browser_cortex_case_id") or "").strip()
    engine_profile = str(params.get("engine_profile") or "").strip().lower()
    if engine_profile == "playwright_compat":
        if params.get("explicit_compatibility_selection") is not True:
            return "real_browser_playwright_compatibility_requires_explicit_selection"
    if browser_cortex_case_id or engine_profile in {"fake_product_search", "local_fake", "inmemory", "playwright_compat"}:
        return None
    needs_live_browser_config = request.operation in {
        "real_browser.open",
        "real_browser.observe",
        "real_browser.search",
        "real_browser.inspect_result",
        "real_browser.open_result",
    }
    if needs_live_browser_config and not os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip():
        return "real_browser_live_backend_config_missing"
    return None


def _product_browser_engine(envelope: ActionEnvelope) -> object:
    browser_cortex_case_id = str(envelope.params.get("browser_cortex_case_id") or "").strip()
    if browser_cortex_case_id:
        from sentinel.operator.browser_cortex_deterministic_fixture import (
            browser_cortex_deterministic_fixture_engine_for_case,
        )
        from sentinel.operator.browser_cortex_quality_gate import build_browser_cortex_quality_corpus

        manifest = build_browser_cortex_quality_corpus(baseline_commit=str(envelope.params.get("baseline_commit") or "local"))
        for case in manifest.deterministic_cases:
            if case.task_id == browser_cortex_case_id:
                return browser_cortex_deterministic_fixture_engine_for_case(case)
        from sentinel.operator.browser_cortex_search_entity_development import (
            build_browser_cortex_search_entity_development_corpus,
            build_browser_cortex_search_entity_development_corpus_v2,
        )

        development_manifest = build_browser_cortex_search_entity_development_corpus(
            baseline_commit=str(envelope.params.get("baseline_commit") or "local")
        )
        for case in development_manifest.cases:
            if case.task_id == browser_cortex_case_id:
                return browser_cortex_deterministic_fixture_engine_for_case(case)
        development_manifest_v2 = build_browser_cortex_search_entity_development_corpus_v2(
            baseline_commit=str(envelope.params.get("baseline_commit") or "local")
        )
        for case in development_manifest_v2.cases:
            if case.task_id == browser_cortex_case_id:
                return browser_cortex_deterministic_fixture_engine_for_case(case)
        raise RuntimeError("browser_cortex_deterministic_case_not_found")
    engine_profile = str(envelope.params.get("engine_profile") or "").strip().lower()
    if engine_profile in {"fake_product_search", "local_fake", "inmemory"}:
        return _ProductLocalCloakBrowserEngine()
    if os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip():
        return build_cloak_first_real_browser_engine_from_env()
    raise RuntimeError("real_browser_live_backend_config_missing")


def _product_browser_engine_requires_global_lock(envelope: ActionEnvelope) -> bool:
    browser_cortex_case_id = str(envelope.params.get("browser_cortex_case_id") or "").strip()
    if browser_cortex_case_id:
        return False
    engine_profile = str(envelope.params.get("engine_profile") or "").strip().lower()
    if engine_profile in {"fake_product_search", "local_fake", "inmemory", "playwright_compat"}:
        return False
    return bool(os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip())


def _safe_engine_backend_id(engine: object | None) -> str:
    if engine is None:
        return ""
    return str(
        getattr(engine, "browser_backend_id", None)
        or getattr(engine, "backend_id", None)
        or engine.__class__.__name__
    )


def _safe_engine_origin_hash(engine: object | None) -> str:
    if engine is None:
        return ""
    return str(getattr(engine, "safe_url_origin_hash", "") or "")


def _worker_fleet_preflight(
    params: dict[str, Any],
    _request: MissionExecutionRequest,
    _authority: MissionAuthorityEnvelope,
) -> str | None:
    return worker_orchestration_preflight(params)


def _workspace_patch_apply_preflight(
    params: dict[str, Any],
    _request: MissionExecutionRequest,
    _authority: MissionAuthorityEnvelope,
) -> str | None:
    target = str(params.get("target_path") or params.get("target_ref") or "").strip()
    if not target:
        return "workspace_patch_target_required"
    raw = Path(target)
    if raw.is_absolute() or ".." in raw.parts:
        return "workspace_patch_target_not_authorized"
    if any(part in SENSITIVE_WORKSPACE_PATCH_NAMES for part in raw.parts):
        return "workspace_patch_target_not_authorized"
    return None


def _bounded_channel_preflight(
    params: dict[str, Any],
    _request: MissionExecutionRequest,
    authority: MissionAuthorityEnvelope,
) -> str | None:
    adapter_id = str(params.get("adapter_id") or "").strip()
    channel = str(params.get("channel") or "webhook").strip().lower()
    if not adapter_id:
        return "bounded_channel_adapter_required"
    if channel == "telegram":
        if "channel:telegram" not in set(authority.allowed_tools or []):
            return "bounded_channel_real_transport_not_authorized"
        if "telegram:configured-chat" not in set(authority.allowed_domains or []):
            return "bounded_channel_real_transport_not_authorized"
        if not _telegram_config_present():
            return "bounded_channel_real_transport_config_missing"
    elif channel != "webhook":
        return "bounded_channel_real_transport_not_authorized"
    if "channel_draft_send" not in set(authority.allowed_tools or []):
        return "authority_incompatible_dispatch"
    if not authority.allowed_domains:
        return "authority_incompatible_dispatch"
    return None


def _channel_send_authority(authority: MissionAuthorityEnvelope) -> MissionAuthorityEnvelope:
    allowed_actions = list(dict.fromkeys([*authority.allowed_actions, "channel_send"]))
    allowed_tools = list(dict.fromkeys([*authority.allowed_tools, "channel_draft_send"]))
    return authority.model_copy(update={"allowed_actions": allowed_actions, "allowed_tools": allowed_tools})


def _real_browser_authority(authority: MissionAuthorityEnvelope) -> MissionAuthorityEnvelope:
    return authority.model_copy(
        update={
            "allowed_actions": list(dict.fromkeys(authority.allowed_actions)),
            "allowed_tools": list(dict.fromkeys(authority.allowed_tools)),
            "allowed_domains": list(dict.fromkeys(authority.allowed_domains)),
        }
    )


def _mission_workspace_browser_session_handle(manifest: dict[str, Any]) -> dict[str, Any]:
    for handle in manifest.get("handles", []):
        if isinstance(handle, dict) and handle.get("kind") == "browser_session":
            return handle
    raise RuntimeError("mission_workspace_browser_session_handle_missing")


def _local_channel_transport(request: Any) -> ChannelSendTransportReceipt:
    mission_id = str(getattr(request, "mission_id", "mission"))
    channel = str(getattr(request, "channel", "webhook"))
    recipients = list(getattr(request, "recipients", []) or [])
    return ChannelSendTransportReceipt(
        delivery_ref=f"local-pack8:{mission_id}:{channel}:{len(recipients)}",
    )


def _channel_transport_for(channel: str) -> Callable[[Any], ChannelSendTransportReceipt]:
    if channel == "telegram":
        try:
            return build_telegram_channel_transport_from_env()
        except ChannelConnectorRuntimeError as exc:
            raise RuntimeError("bounded_channel_real_transport_config_missing") from exc
    return _local_channel_transport


def _channel_display_name(channel: str) -> str:
    return "Telegram bounded live channel" if channel == "telegram" else "Pack 8 local bounded channel"


def _channel_transport_kind(channel: str) -> str:
    return "telegram_real_product_dispatch" if channel == "telegram" else "local_fake_product_dispatch"


def _telegram_config_present() -> bool:
    return bool(os.environ.get("SENTINEL_TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("SENTINEL_TELEGRAM_CHAT_ID"))


class _ProductLocalCloakBrowserEngine:
    browser_backend_id = LOCAL_FIXTURE_BROWSER_BACKEND_ID
    session_backend_kind = LOCAL_FIXTURE_BROWSER_SESSION_KIND
    session_manager_backend_kind = LOCAL_FIXTURE_BROWSER_SESSION_KIND

    def __init__(self) -> None:
        self.opened = True
        self.query = ""
        self.results_visible = True
        self.open_count = 0
        self.observe_count = 0
        self.click_count = 0
        self.type_count = 0
        self.assert_count = 0
        self.select_count = 0
        self.extract_count = 0
        self.press_count = 0
        self.wait_count = 0
        self.scroll_count = 0
        self.close_count = 0

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash("local-cloak-browser://bounded-product-fixture")

    def open(self) -> RealBrowserEngineSnapshot:
        self.opened = True
        self.open_count += 1
        return self._snapshot()

    def observe(self) -> RealBrowserEngineSnapshot:
        self.opened = True
        self.observe_count += 1
        return self._snapshot()

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        self.opened = True
        if ref not in {element.ref for element in self._elements()}:
            raise RuntimeError("real_browser_element_ref_unknown")
        self.click_count += 1
        if ref == "button:search":
            self.results_visible = True
        return self._snapshot()

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self.opened = True
        if ref != "input:search":
            raise RuntimeError("real_browser_type_ref_not_textbox")
        self.query = text
        self.type_count += 1
        return self._snapshot()

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        del ref, option
        self.select_count += 1
        return self._snapshot()

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        self.assert_count += 1
        return text.lower() in self._page_text().lower(), self._snapshot()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self.opened = True
        self.extract_count += 1
        return self._page_text(), self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        if ref != "input:search":
            raise RuntimeError("real_browser_type_ref_not_textbox")
        self.press_count += 1
        if key == "Enter":
            self.results_visible = True
        return self._snapshot()

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        del timeout_ms
        self.wait_count += 1
        return text.lower() in self._page_text().lower(), self._snapshot()

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        self.wait_count += 1
        return self._snapshot()

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        del delta_y
        self.scroll_count += 1
        return self._snapshot()

    def close(self) -> None:
        self.close_count += 1
        self.opened = False

    def _snapshot(self) -> RealBrowserEngineSnapshot:
        text = self._page_text()
        return RealBrowserEngineSnapshot(
            page_title="Sentinel Product Browser Fixture",
            state_hash=stable_hash(
                {
                    "query_hash": text_hash(self.query),
                    "results_visible": self.results_visible,
                    "text_hash": text_hash(text),
                }
            ),
            elements=self._elements(),
        )

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        elements = [
            RealBrowserEngineElement(
                "input:search",
                "searchbox",
                "Search products",
                value_preview=self.query[:80],
            ),
            RealBrowserEngineElement(
                "button:search",
                "button",
                "Search",
                text_preview="Search",
            ),
        ]
        if self.results_visible:
            elements.append(
                RealBrowserEngineElement(
                    "link:result_1",
                    "link",
                    "Blue light glasses 4.80 EUR MOQ 10",
                    text_preview="Blue light glasses 4.80 EUR MOQ 10 Supplier VisionCraft",
                )
            )
        return tuple(elements)

    def _page_text(self) -> str:
        if not self.results_visible:
            return "Search products for bounded browser fixture."
        return "\n".join(
            [
                "Blue light glasses, visible price 4.80 EUR per unit, MOQ 10, Supplier VisionCraft.",
                "TR90 sunglasses, visible price 3.90 EUR per unit, MOQ 20, Supplier SunWorks.",
                "Caveat: shipping and customization costs are not visible.",
            ]
        )


def _workspace_path_from_ref(workspace_ref: str) -> Path:
    if not workspace_ref.startswith("workspace:"):
        raise RuntimeError("workspace_ref_not_dispatchable")
    path = Path(workspace_ref.removeprefix("workspace:")).resolve()
    if not path.exists() or not path.is_dir():
        raise RuntimeError("workspace_ref_not_found")
    return path
