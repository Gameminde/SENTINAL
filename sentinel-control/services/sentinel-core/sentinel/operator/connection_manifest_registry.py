from __future__ import annotations

import importlib.util
from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.connection_manifest_models import (
    ConnectionAdapterReadinessEntry,
    ConnectionAdapterReadinessReport,
    ConnectionDirection,
    ConnectionManifest,
    ConnectionManifestValidationReport,
    ConnectionRiskClass,
    ConnectionSurfaceStatus,
    RuntimeConnectionComparisonReport,
)
from sentinel.operator.runtime_connections import (
    RuntimeConnectionRegistry,
    build_default_runtime_connection_registry,
)
from sentinel.shared.models import SentinelModel


_RUNTIMEHOST_REGISTERED_ADAPTER_IDS = frozenset({"read_only_research_adapter"})
_UNIFIED_EXECUTION_ADAPTER_IDS = frozenset({"read_only_research_adapter"})


class ConnectionManifestRegistry(SentinelModel):
    manifests: tuple[ConnectionManifest, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "ConnectionManifestRegistry":
        ids = [manifest.connection_id for manifest in self.manifests]
        if len(ids) != len(set(ids)):
            raise ValueError("ConnectionManifestRegistry cannot contain duplicate connection ids.")
        return self

    def list_manifests(self) -> tuple[ConnectionManifest, ...]:
        return tuple(sorted(self.manifests, key=lambda item: item.connection_id))

    def get(self, connection_id: str) -> ConnectionManifest:
        for manifest in self.manifests:
            if manifest.connection_id == connection_id:
                return manifest
        raise KeyError(f"Unknown connection manifest `{connection_id}`.")

    def export_safe_summaries(self) -> list[dict[str, Any]]:
        return [manifest.safe_summary() for manifest in self.list_manifests()]

    def validate_all(self) -> ConnectionManifestValidationReport:
        findings: list[str] = []
        dispatchable_ids = [
            manifest.connection_id for manifest in self.manifests if manifest.product_dispatchable
        ]
        if dispatchable_ids != ["read_only_research"]:
            findings.append("only_read_only_research_may_be_product_dispatchable")
        for manifest in self.manifests:
            if manifest.risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5} and (
                manifest.production_reachable or manifest.product_dispatchable or manifest.adapter_id is not None
            ):
                findings.append(f"{manifest.connection_id}:high_risk_surface_not_locked")
        return ConnectionManifestValidationReport(
            ok=not findings,
            manifest_count=len(self.manifests),
            findings=tuple(findings),
        )

    def compare_runtime_connections(
        self,
        runtime_registry: RuntimeConnectionRegistry | None = None,
    ) -> RuntimeConnectionComparisonReport:
        runtime_registry = runtime_registry or build_default_runtime_connection_registry()
        manifest_ids = tuple(manifest.connection_id for manifest in self.list_manifests())
        runtime_ids = tuple(sorted(connection.connection_id for connection in runtime_registry.connections))
        return RuntimeConnectionComparisonReport(
            manifest_ids=manifest_ids,
            runtime_connection_ids=runtime_ids,
            missing_runtime_connection_profiles=tuple(
                connection_id for connection_id in manifest_ids if connection_id not in runtime_ids
            ),
            missing_manifests_for_runtime_connections=tuple(
                connection_id for connection_id in runtime_ids if connection_id not in manifest_ids
            ),
        )

    def adapter_readiness_report(
        self,
        *,
        runtime_registry: RuntimeConnectionRegistry | None = None,
        unified_execution_adapter_ids: set[str] | frozenset[str] | None = None,
        runtimehost_registered_adapter_ids: set[str] | frozenset[str] | None = None,
    ) -> ConnectionAdapterReadinessReport:
        runtime_registry = runtime_registry or build_default_runtime_connection_registry()
        runtime_ids = {connection.connection_id for connection in runtime_registry.connections}
        unified_ids = frozenset(unified_execution_adapter_ids or _UNIFIED_EXECUTION_ADAPTER_IDS)
        runtimehost_ids = frozenset(runtimehost_registered_adapter_ids or _RUNTIMEHOST_REGISTERED_ADAPTER_IDS)
        entries: list[ConnectionAdapterReadinessEntry] = []
        for manifest in self.list_manifests():
            runtime_profile_exists = manifest.connection_id in runtime_ids
            runtime_exists = _module_exists(manifest.owner_module)
            replay_exists = _replay_ref_exists(manifest.replay_schema_ref)
            adapter_exists = bool(manifest.adapter_id and manifest.adapter_id in unified_ids)
            runtimehost_registered = bool(manifest.adapter_id and manifest.adapter_id in runtimehost_ids)
            missing = list(manifest.missing_to_dispatchable)
            if not runtime_exists:
                missing.append("runtime_missing")
            if not replay_exists:
                missing.append("replay_missing")
            if not runtime_profile_exists:
                missing.append("runtime_connection_profile_missing")
            if not adapter_exists:
                missing.append("unified_execution_adapter_missing")
            if not runtimehost_registered:
                missing.append("runtimehost_registration_missing")
            if manifest.product_dispatchable:
                missing = []
            entries.append(
                ConnectionAdapterReadinessEntry(
                    connection_id=manifest.connection_id,
                    runtime_exists=runtime_exists,
                    replay_exists=replay_exists,
                    manifest_exists=True,
                    runtime_connection_profile_exists=runtime_profile_exists,
                    unified_execution_adapter_exists=adapter_exists,
                    runtime_host_registered=runtimehost_registered,
                    product_dispatchable=manifest.product_dispatchable,
                    missing_to_dispatchable=tuple(dict.fromkeys(missing)),
                )
            )
        return ConnectionAdapterReadinessReport(entries=tuple(entries))

    def high_risk_surfaces_locked(self) -> bool:
        return all(
            not manifest.production_reachable
            and not manifest.product_dispatchable
            and manifest.adapter_id is None
            for manifest in self.manifests
            if manifest.risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}
        )


def build_default_connection_manifest_registry() -> ConnectionManifestRegistry:
    return ConnectionManifestRegistry(
        manifests=tuple(sorted(_default_manifests(), key=lambda item: item.connection_id))
    )


def _default_manifests() -> tuple[ConnectionManifest, ...]:
    return (
        _manifest(
            connection_id="mission_kernel",
            surface_kind="operator_runtime",
            owner_module="sentinel.operator.kernel",
            runtime_class_name="MissionKernel",
            current_status=ConnectionSurfaceStatus.PRODUCT_PROVEN,
            production_reachable=True,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C0,
            data_types=("mission_events", "mission_status"),
            authority_required="MissionAuthorityEnvelope stored on mission record",
            can_read=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.operator.replay",
            status_reason="Product route owner for mission ledger and terminal state.",
            missing_to_dispatchable=("not_adapter_surface",),
        ),
        _manifest(
            connection_id="agent_runtime_bridge",
            surface_kind="operator_bridge",
            owner_module="sentinel.operator.agent_bridge",
            runtime_class_name="OperatorAgentRuntimeBridge",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED,
            production_reachable=True,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C1,
            data_types=("runtime_events", "agent_runtime_result"),
            authority_required="active MissionAuthorityEnvelope",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.agent.replay",
            status_reason="Bridge is reachable only through governed product routes.",
            missing_to_dispatchable=("not_adapter_surface",),
        ),
        _manifest(
            connection_id="power_runtime_bridge",
            surface_kind="operator_bridge",
            owner_module="sentinel.operator.power_bridge",
            runtime_class_name="OperatorPowerRuntimeBridge",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C4,
            data_types=("power_runtime_plan", "power_runtime_result"),
            authority_required="active MissionAuthorityEnvelope and PowerMissionPlan within envelope",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.power.runtime",
            status_reason="Power runtime bridge remains locked by Pack 2 manifest policy.",
            missing_to_dispatchable=("high_risk_locked", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="read_only_research",
            surface_kind="product_capability",
            owner_module="sentinel.operator.read_only_operator_spine",
            runtime_class_name="ReadOnlyProductionSpineSession",
            adapter_id="read_only_research_adapter",
            current_status=ConnectionSurfaceStatus.PRODUCT_PROVEN,
            production_reachable=True,
            product_dispatchable=True,
            direction=ConnectionDirection.LOCAL,
            risk_class=ConnectionRiskClass.C1,
            data_types=("workspace_directory_observation", "workspace_file_segment", "workspace_search_match"),
            authority_required="MissionAuthorityEnvelope with read-only workspace actions and snapshot scope",
            capability_id="read_only_research",
            operation="inspect_repository",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.operator.read_only_operator_spine",
            receipt_schema_ref="ReadOnlyActionReceipt",
            approval_policy_ref="MissionAuthorityApprovalScope:read_only_research",
            status_reason="Only product dispatchable Pack 2 surface.",
        ),
        _manifest(
            connection_id="model_provider_catalog",
            surface_kind="model_provider_transport",
            owner_module="sentinel.agent.model_execution.provider_profiles",
            runtime_class_name="ProviderBackendProfile",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C3,
            data_types=("prompt_frame", "visible_model_output", "safe_provider_diagnostics"),
            credential_env_names=(
                "GROQ_API_KEY",
                "OPENROUTER_API_KEY",
                "NVIDIA_API_KEY",
                "SENTINEL_CERT_MODEL_API_KEY",
                "DEEPSEEK_API_KEY",
                "MISTRAL_API_KEY",
                "XAI_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GEMINI_API_KEY",
                "COHERE_API_KEY",
                "LMSTUDIO_API_KEY",
                "SENTINEL_ALIYUN_DASHSCOPE_BASE_URL",
            ),
            credential_required=True,
            authority_required="explicit UserModelContract; no provider-native tools",
            can_read=True,
            external_side_effects_possible=True,
            requires_gate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="ProviderModelResponseSafeDiagnostics",
            allowed_destinations_policy_ref="policy:catalog_endpoint_hashes_only",
            status_reason="Provider catalog is metadata-visible but not a UnifiedExecutionAdapter.",
            missing_to_dispatchable=("unified_execution_adapter_missing", "runtime_connection_profile_missing"),
        ),
        _capability_manifest("model_router_runtime", "sentinel.operator.model_router", "ModelRouterRuntime", ConnectionRiskClass.C3),
        _capability_manifest("skill_fabric_runtime", "sentinel.operator.skill_fabric", "GovernedSkillFabricRuntime", ConnectionRiskClass.C4),
        _capability_manifest("channel_connector_runtime", "sentinel.operator.channel_adapter", "ChannelConnectorRuntime", ConnectionRiskClass.C4, can_send=True),
        _capability_manifest("desktop_sidecar_runtime", "sentinel.operator.desktop_sidecar", "DesktopSidecarRuntime", ConnectionRiskClass.C5),
        _capability_manifest("live_desktop_backend_runtime", "sentinel.operator.live_desktop_backend", "LiveDesktopBackendRuntime", ConnectionRiskClass.C5),
        _capability_manifest("voice_runtime", "sentinel.operator.voice_runtime", "VoiceRuntime", ConnectionRiskClass.C4),
        _capability_manifest("credential_vault_runtime", "sentinel.operator.credential_vault", "CredentialVaultRuntime", ConnectionRiskClass.C5),
        _capability_manifest("account_authority_runtime", "sentinel.operator.account_authority", "AccountAuthorityRuntime", ConnectionRiskClass.C5),
        _capability_manifest("financial_authority_runtime", "sentinel.operator.financial_authority", "FinancialAuthorityRuntime", ConnectionRiskClass.C5),
        _capability_manifest("worker_fleet_runtime", "sentinel.operator.worker_fleet", "WorkerFleetRuntime", ConnectionRiskClass.C1),
        _manifest(
            connection_id="browser_live_operator",
            surface_kind="browser_runtime_generation",
            owner_module="sentinel.agent.organs.browser_operator_agent_l4_l5_live",
            runtime_class_name=None,
            current_status=ConnectionSurfaceStatus.PARTIAL,
            direction=ConnectionDirection.BIDIRECTIONAL,
            risk_class=ConnectionRiskClass.C4,
            data_types=("browser_page_state", "browser_interaction_plan"),
            authority_required="browser-scoped explicit MissionAuthorityEnvelope",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="browser_evidence_and_receipt_adapters",
            status_reason="Runtime connection exists but remains local/non-dispatchable.",
            missing_to_dispatchable=("unified_execution_adapter_missing", "runtimehost_registration_missing"),
        ),
        _manifest(
            connection_id="interactive_exploration",
            surface_kind="experimental_harness",
            owner_module="sentinel.operator.interactive_exploration_read_only",
            runtime_class_name=None,
            current_status=ConnectionSurfaceStatus.EXPERIMENTAL,
            direction=ConnectionDirection.LOCAL,
            risk_class=ConnectionRiskClass.C1,
            data_types=("experimental_observation",),
            authority_required="experimental policy freeze and read-only snapshot scope",
            can_read=True,
            requires_gate=True,
            requires_receipts=True,
            replay_schema_ref="exploration_trajectory",
            status_reason="Experimental harness is not product dispatch.",
            missing_to_dispatchable=("experimental_only", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="browser_read_only_observation",
            surface_kind="browser_read_only_organ",
            owner_module="sentinel.agent.organs.browser_readonly_organ_v1",
            runtime_class_name="BrowserReadOnlyOrganV1",
            current_status=ConnectionSurfaceStatus.PARTIAL,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C2,
            data_types=("dom_snapshot", "page_text", "screenshot_ref"),
            authority_required="domain-scoped browser observation authority",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="browser_read_only_replay",
            status_reason="Browser observation exists as organ code, not Pack 2 product dispatch.",
            missing_to_dispatchable=("runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
        _browser_high_risk_manifest("browser_click_type_submit", "sentinel.agent.organs.browser_operator_agent_l4_l5_live", ConnectionRiskClass.C4),
        _browser_high_risk_manifest("browser_login_session", "sentinel.agent.organs.browser_login_credential_session_broker_l6", ConnectionRiskClass.C5),
        _browser_high_risk_manifest("browser_payment_account_special_authority", "sentinel.agent.organs.browser_payment_spend_special_authority_l7", ConnectionRiskClass.C5),
        _manifest(
            connection_id="external_api_dry_run",
            surface_kind="external_api_dry_run",
            owner_module="sentinel.organs.external_api.dry_run",
            runtime_class_name=None,
            current_status=ConnectionSurfaceStatus.IMPLEMENTED_NOT_DISPATCHABLE,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C3,
            data_types=("api_request_plan", "privacy_risk", "cost_estimate"),
            authority_required="dry-run authority only",
            can_read=True,
            requires_gate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="external_api_dry_run_receipts",
            status_reason="Dry-run planner is not a product dispatch adapter.",
            missing_to_dispatchable=("runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="external_api_read_write",
            surface_kind="external_api_live",
            owner_module="sentinel.agent.organs.external_api_read_write_organ_v1",
            runtime_class_name="ExternalAPIReadWriteOrganV1",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED_NOT_DISPATCHABLE,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C4,
            data_types=("api_method", "api_request_hash", "api_response_hash"),
            authority_required="explicit external API domain and method authority",
            can_read=True,
            can_write=True,
            external_side_effects_possible=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            requires_kill_or_revocation=True,
            replay_schema_ref="external_api_live_replay",
            status_reason="Live external API remains locked.",
            missing_to_dispatchable=("high_risk_locked", "runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="operator_memory_candidate",
            surface_kind="operator_memory_artifact",
            owner_module="sentinel.operator.read_only_operator_spine",
            runtime_class_name="ReadOnlyOperatorMemoryCandidateArtifact",
            current_status=ConnectionSurfaceStatus.PRODUCT_PROVEN,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C1,
            data_types=("safe_summary", "receipt_refs", "evidence_refs"),
            authority_required="data-only artifact; cannot grant recall authority",
            can_read=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.operator.read_only_operator_spine",
            status_reason="Memory candidate is data-only and non-dispatchable.",
            missing_to_dispatchable=("not_execution_surface",),
        ),
        _manifest(
            connection_id="tool_registry",
            surface_kind="capability_registry",
            owner_module="sentinel.capabilities.registry",
            runtime_class_name="ToolRegistry",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED,
            production_reachable=True,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C0,
            data_types=("capability_metadata", "policy_decision"),
            authority_required="policy-only caller-owned execution",
            can_read=True,
            requires_gate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="AgentEventBus policy trace",
            status_reason="Registry remains metadata-only.",
            missing_to_dispatchable=("not_execution_surface",),
        ),
        _manifest(
            connection_id="external_organ_registry",
            surface_kind="organ_contract_registry",
            owner_module="sentinel.organs.registry",
            runtime_class_name="ExternalOrganRegistry",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED,
            production_reachable=True,
            direction=ConnectionDirection.INTERNAL,
            risk_class=ConnectionRiskClass.C0,
            data_types=("organ_contract_metadata",),
            authority_required="contract registration only",
            can_read=True,
            requires_gate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="AgentEventBus organ contract trace",
            status_reason="Registry remains metadata-only.",
            missing_to_dispatchable=("not_execution_surface",),
        ),
        _manifest(
            connection_id="supabase_trace_repository",
            surface_kind="external_trace_storage",
            owner_module="sentinel.shared.db",
            runtime_class_name="SupabaseTraceRepository",
            current_status=ConnectionSurfaceStatus.PARTIAL,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C4,
            data_types=("trace_rows",),
            credential_env_names=("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"),
            credential_required=True,
            authority_required="tenant-bound external storage authority",
            can_read=True,
            can_write=True,
            external_side_effects_possible=True,
            requires_gate=True,
            requires_receipts=True,
            requires_replay=True,
            requires_kill_or_revocation=True,
            replay_schema_ref="supabase_trace_replay_missing",
            allowed_destinations_policy_ref="policy:supabase_env_names_only",
            status_reason="External storage remains locked before credential/tenant boundary.",
            missing_to_dispatchable=("high_risk_locked", "runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="cueidea_bridge_client",
            surface_kind="external_bridge_client",
            owner_module="sentinel.cueidea_bridge.client",
            runtime_class_name="CueideaBridgeClient",
            current_status=ConnectionSurfaceStatus.PARTIAL,
            direction=ConnectionDirection.OUTBOUND,
            risk_class=ConnectionRiskClass.C4,
            data_types=("bridge_request_metadata", "bridge_response_metadata"),
            credential_required=True,
            authority_required="explicit bridge destination and credential lease",
            can_read=True,
            can_write=True,
            external_side_effects_possible=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            requires_kill_or_revocation=True,
            replay_schema_ref="cueidea_bridge_replay_missing",
            status_reason="External bridge remains locked.",
            missing_to_dispatchable=("high_risk_locked", "runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
        _manifest(
            connection_id="file_system_workspace_bridge_read_only",
            surface_kind="filesystem_workspace_read_only",
            owner_module="sentinel.operator.read_only_operator_spine",
            runtime_class_name="ReadOnlyProductionSpineSession",
            current_status=ConnectionSurfaceStatus.PRODUCT_PROVEN,
            direction=ConnectionDirection.LOCAL,
            risk_class=ConnectionRiskClass.C1,
            data_types=("workspace_listing", "workspace_file_segment", "workspace_search_match"),
            authority_required="approved workspace read-only authority",
            can_read=True,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            replay_schema_ref="module:sentinel.operator.read_only_operator_spine",
            status_reason="Read-only filesystem bridge is reachable only through read_only_research adapter.",
            missing_to_dispatchable=("covered_by_read_only_research",),
        ),
        _manifest(
            connection_id="file_system_workspace_bridge_write_shell_future",
            surface_kind="filesystem_workspace_write_shell_future",
            owner_module="sentinel.agent.organs.reversible_workspace_executor",
            runtime_class_name="ReversibleWorkspaceExecutor",
            current_status=ConnectionSurfaceStatus.IMPLEMENTED_NOT_DISPATCHABLE,
            direction=ConnectionDirection.LOCAL,
            risk_class=ConnectionRiskClass.C5,
            data_types=("patch_plan", "shell_command_plan", "workspace_mutation_result"),
            authority_required="future explicit write/shell authority",
            can_read=True,
            can_write=True,
            external_side_effects_possible=False,
            requires_gate=True,
            requires_finalgate=True,
            requires_receipts=True,
            requires_replay=True,
            requires_kill_or_revocation=True,
            replay_schema_ref="workspace_mutation_replay_missing",
            status_reason="Write/shell remains future locked surface.",
            missing_to_dispatchable=("high_risk_locked", "runtime_connection_profile_missing", "unified_execution_adapter_missing"),
        ),
    )


def _capability_manifest(
    connection_id: str,
    owner_module: str,
    runtime_class_name: str,
    risk_class: ConnectionRiskClass,
    *,
    can_send: bool = False,
) -> ConnectionManifest:
    high_risk = risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}
    return _manifest(
        connection_id=connection_id,
        surface_kind="governed_capability_runtime",
        owner_module=owner_module,
        runtime_class_name=runtime_class_name,
        current_status=ConnectionSurfaceStatus.IMPLEMENTED_NOT_DISPATCHABLE,
        direction=ConnectionDirection.BIDIRECTIONAL if high_risk else ConnectionDirection.INTERNAL,
        risk_class=risk_class,
        data_types=("runtime_request", "runtime_result"),
        authority_required="explicit capability authority and adapter before product dispatch",
        can_read=True,
        can_write=high_risk,
        can_send=can_send,
        external_side_effects_possible=high_risk or can_send,
        requires_gate=True,
        requires_finalgate=True,
        requires_receipts=True,
        requires_replay=True,
        requires_kill_or_revocation=high_risk,
        replay_schema_ref=f"module:{owner_module.replace('_runtime', '_replay')}",
        status_reason="Governed runtime exists but has no UnifiedExecutionAdapter in Pack 2.",
        missing_to_dispatchable=("runtime_connection_profile_missing", "unified_execution_adapter_missing", "runtimehost_registration_missing"),
    )


def _browser_high_risk_manifest(
    connection_id: str,
    owner_module: str,
    risk_class: ConnectionRiskClass,
) -> ConnectionManifest:
    return _manifest(
        connection_id=connection_id,
        surface_kind="browser_high_risk_surface",
        owner_module=owner_module,
        runtime_class_name=None,
        current_status=ConnectionSurfaceStatus.PARTIAL,
        direction=ConnectionDirection.BIDIRECTIONAL,
        risk_class=risk_class,
        data_types=("browser_page_state", "browser_action_plan"),
        authority_required="explicit browser special authority",
        can_read=True,
        can_write=True,
        can_send=True,
        external_side_effects_possible=True,
        requires_gate=True,
        requires_finalgate=True,
        requires_receipts=True,
        requires_replay=True,
        requires_kill_or_revocation=True,
        replay_schema_ref="browser_special_authority_replay",
        status_reason="Browser external action surface remains locked.",
        missing_to_dispatchable=("high_risk_locked", "runtime_connection_profile_missing", "unified_execution_adapter_missing"),
    )


def _manifest(**kwargs: Any) -> ConnectionManifest:
    kwargs.setdefault("surface_id", f"surface:{kwargs['connection_id']}")
    kwargs.setdefault("adapter_id", None)
    kwargs.setdefault("runtime_class_name", None)
    kwargs.setdefault("production_reachable", False)
    kwargs.setdefault("product_dispatchable", False)
    kwargs.setdefault("credential_env_names", ())
    kwargs.setdefault("credential_required", False)
    kwargs.setdefault("capability_id", None)
    kwargs.setdefault("operation", None)
    kwargs.setdefault("can_read", False)
    kwargs.setdefault("can_write", False)
    kwargs.setdefault("can_send", False)
    kwargs.setdefault("can_execute", False)
    kwargs.setdefault("external_side_effects_possible", False)
    kwargs.setdefault("requires_gate", False)
    kwargs.setdefault("requires_finalgate", False)
    kwargs.setdefault("requires_receipts", False)
    kwargs.setdefault("requires_replay", False)
    kwargs.setdefault("requires_kill_or_revocation", False)
    kwargs.setdefault("prompt_injection_exposure", "bounded_untrusted_input")
    kwargs.setdefault("secret_exfiltration_exposure", "bounded_by_redaction_and_scope")
    kwargs.setdefault("receipt_schema_ref", None)
    kwargs.setdefault("replay_schema_ref", None)
    kwargs.setdefault("approval_policy_ref", "policy:manifest_visibility_only")
    kwargs.setdefault("allowed_destinations_policy_ref", None)
    kwargs.setdefault("missing_to_dispatchable", ())
    return ConnectionManifest(**kwargs)


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _replay_ref_exists(replay_schema_ref: str | None) -> bool:
    if not replay_schema_ref:
        return False
    if replay_schema_ref.startswith("module:"):
        return _module_exists(replay_schema_ref.removeprefix("module:").split(":", 1)[0])
    return "missing" not in replay_schema_ref


__all__ = [
    "ConnectionManifestRegistry",
    "build_default_connection_manifest_registry",
]
