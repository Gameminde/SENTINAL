from __future__ import annotations

import importlib.util
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class RuntimeConnectionRoute(StrEnum):
    AGENT_RUNTIME = "agent_runtime"
    POWER_RUNTIME = "power_runtime"
    LOCAL_GOVERNED_SURFACE = "local_governed_surface"
    PROPOSAL_ONLY = "proposal_only"
    EXPERIMENTAL_ONLY = "experimental_only"
    BLOCKED = "blocked"


class RuntimeConnectionMaturity(StrEnum):
    LIVE_PROVEN = "live_proven"
    LIVE_BOUNDED = "live_bounded"
    LOCAL_ONLY = "local_only"
    INJECTED = "injected"
    SANDBOX = "sandbox"
    PAPER = "paper"
    FOUNDATION = "foundation"
    CONTRACT_ONLY = "contract_only"
    EXPERIMENTAL = "experimental"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ConnectionHealthStatus(StrEnum):
    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed_with_limits"
    FAILED = "failed"


class RuntimeConnectionProfile(SentinelModel):
    connection_id: str
    display_name: str
    runtime_generation: str
    authoritative_route: RuntimeConnectionRoute
    maturity: RuntimeConnectionMaturity
    owner_module: str
    owner_symbol: str | None = None
    bridge_module: str | None = None
    bridge_symbol: str | None = None
    adapter_id: str | None = None
    supported_operations: tuple[str, ...] = Field(default_factory=tuple)
    tool_registry_refs: tuple[str, ...] = Field(default_factory=tuple)
    organ_registry_refs: tuple[str, ...] = Field(default_factory=tuple)
    authority_requirement: str
    authority_actions: tuple[str, ...] = Field(default_factory=tuple)
    telemetry_required: bool = True
    receipt_contract: str
    finalgate_contract: str
    replay_adapter: str
    memory_behavior: str = "data_only_no_authority"
    production_reachable: bool = False
    execution_enabled_by_registry: bool = False
    limitations: tuple[str, ...] = Field(default_factory=tuple)
    test_refs: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _connection_truth_is_data_only(self) -> "RuntimeConnectionProfile":
        if not self.connection_id.strip() or self.connection_id != self.connection_id.strip():
            raise ValueError("RuntimeConnectionProfile.connection_id must be stable and trimmed.")
        if self.execution_enabled_by_registry:
            raise ValueError("RuntimeConnectionRegistry cannot enable execution.")
        assert_data_not_authority(
            context="runtime_connection_profile",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    @property
    def profile_hash(self) -> str:
        return stable_hash(self.model_dump(mode="json"))


class RuntimeConnectionRegistry(SentinelModel):
    connections: tuple[RuntimeConnectionProfile, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "RuntimeConnectionRegistry":
        ids = [item.connection_id for item in self.connections]
        if len(ids) != len(set(ids)):
            raise ValueError("RuntimeConnectionRegistry cannot contain duplicate connection ids.")
        return self

    def get(self, connection_id: str) -> RuntimeConnectionProfile:
        for connection in self.connections:
            if connection.connection_id == connection_id:
                return connection
        raise KeyError(f"Unknown runtime connection `{connection_id}`.")

    def with_connection(self, connection: RuntimeConnectionProfile) -> "RuntimeConnectionRegistry":
        next_connections = [
            item
            for item in self.connections
            if item.connection_id != connection.connection_id
        ]
        next_connections.append(connection)
        return RuntimeConnectionRegistry(
            connections=tuple(sorted(next_connections, key=lambda item: item.connection_id))
        )

    def export_json(self) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in sorted(self.connections, key=lambda entry: entry.connection_id)
        ]


class ConnectionHealthFinding(SentinelModel):
    connection_id: str
    severity: str
    code: str
    safe_summary: str


class ConnectionHealthResult(SentinelModel):
    status: ConnectionHealthStatus
    checked_count: int
    failed_count: int
    warning_count: int
    findings: tuple[ConnectionHealthFinding, ...] = Field(default_factory=tuple)


def build_default_runtime_connection_registry() -> RuntimeConnectionRegistry:
    return RuntimeConnectionRegistry(
        connections=tuple(
            sorted(
                (
                    RuntimeConnectionProfile(
                        connection_id="mission_kernel",
                        display_name="MissionKernel",
                        runtime_generation="operator_spine",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LIVE_PROVEN,
                        owner_module="sentinel.operator.kernel",
                        owner_symbol="MissionKernel",
                        authority_requirement="MissionAuthorityEnvelope stored on mission record",
                        authority_actions=("mission_lifecycle",),
                        receipt_contract="MissionRunStoreEvent",
                        finalgate_contract="OperatorMissionStatusTerminalPolicy",
                        replay_adapter="sentinel.operator.replay",
                        production_reachable=True,
                        test_refs=("tests/test_mission_kernel.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="agent_runtime_bridge",
                        display_name="Operator AgentRuntime bridge",
                        runtime_generation="operator_to_agent_runtime",
                        authoritative_route=RuntimeConnectionRoute.AGENT_RUNTIME,
                        maturity=RuntimeConnectionMaturity.LIVE_BOUNDED,
                        owner_module="sentinel.operator.agent_bridge",
                        owner_symbol="OperatorAgentRuntimeBridge",
                        bridge_module="sentinel.operator.agent_bridge",
                        bridge_symbol="OperatorAgentRuntimeBridge",
                        authority_requirement="active MissionAuthorityEnvelope",
                        authority_actions=("run_agentruntime",),
                        receipt_contract="runtime_result.receipt_refs",
                        finalgate_contract="runtime_result.final_gate_certification",
                        replay_adapter="sentinel.agent.replay",
                        production_reachable=True,
                        test_refs=("tests/test_llm_live_operator_agentruntime_bridge_v0.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="power_runtime_bridge",
                        display_name="Operator PowerRuntime bridge",
                        runtime_generation="operator_to_power_runtime",
                        authoritative_route=RuntimeConnectionRoute.POWER_RUNTIME,
                        maturity=RuntimeConnectionMaturity.LIVE_BOUNDED,
                        owner_module="sentinel.operator.power_bridge",
                        owner_symbol="OperatorPowerRuntimeBridge",
                        bridge_module="sentinel.operator.power_bridge",
                        bridge_symbol="OperatorPowerRuntimeBridge",
                        authority_requirement="active MissionAuthorityEnvelope and PowerMissionPlan within envelope",
                        authority_actions=("run_power_runtime",),
                        receipt_contract="PowerRuntimeResult.receipt_refs",
                        finalgate_contract="PowerRuntimeResult.finalgate_certificate_refs",
                        replay_adapter="sentinel.power.runtime.PowerMissionTimeline",
                        production_reachable=True,
                        test_refs=("tests/test_llm_live_operator_power_runtime_bridge_v0.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="read_only_research",
                        display_name="Read-only research operator route",
                        runtime_generation="operator_read_only_production_spine",
                        authoritative_route=RuntimeConnectionRoute.AGENT_RUNTIME,
                        maturity=RuntimeConnectionMaturity.LIVE_BOUNDED,
                        owner_module="sentinel.operator.read_only_operator_spine",
                        owner_symbol="ReadOnlyProductionSpineSession",
                        bridge_module="sentinel.operator.agent_bridge",
                        bridge_symbol="OperatorAgentRuntimeBridge",
                        adapter_id="read_only_research_adapter",
                        supported_operations=("inspect_repository",),
                        tool_registry_refs=("read_only_observation",),
                        authority_requirement="MissionAuthorityEnvelope with read-only actions and snapshot scope",
                        authority_actions=("list_directory", "read_file_segment", "search_text", "finish_exploration"),
                        receipt_contract="ReadOnlyActionReceipt",
                        finalgate_contract="ReadOnlyFinalGateCertificate",
                        replay_adapter="ReadOnlyReplayView",
                        production_reachable=True,
                        limitations=("only read_only_research is wired to the Pack 3 dispatcher",),
                        test_refs=("tests/test_real_model_read_only_operator_production_spine_v1.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="workspace_patch",
                        display_name="Workspace patch product skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.operator.workspace_patch_runtime",
                        owner_symbol="WorkspacePatchRuntime",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=("apply_patch",),
                        tool_registry_refs=("workspace_patch",),
                        organ_registry_refs=("workspace_patch",),
                        authority_requirement="MissionAuthorityEnvelope must grant workspace_patch.apply_patch and the workspace path.",
                        authority_actions=("workspace_patch.apply_patch",),
                        receipt_contract="ProductActionKernelReceipt + WorkspacePatchReceipt",
                        finalgate_contract="ProductActionKernelFinalGateCertificate + WorkspacePatchFinalCertificate",
                        replay_adapter="WorkspacePatchReplayView",
                        production_reachable=True,
                        limitations=("hash-anchored single-file patch only; no shell, no path escape, no secret mutation",),
                        test_refs=("tests/operator/test_power_cleanup_runtimehost_safe_skill_product_registration.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="code_execution_sandbox",
                        display_name="Code execution sandbox product skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.SANDBOX,
                        owner_module="sentinel.operator.code_execution_sandbox_runtime",
                        owner_symbol="CodeExecutionSandboxRuntime",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=("code_exec.run_profile",),
                        tool_registry_refs=("code_execution_sandbox",),
                        organ_registry_refs=("code_execution_sandbox",),
                        authority_requirement="MissionAuthorityEnvelope must grant code_execution_sandbox.code_exec.run_profile and the workspace path.",
                        authority_actions=("code_execution_sandbox.code_exec.run_profile", "code_exec.run_profile"),
                        receipt_contract="ProductActionKernelReceipt + CodeExecutionReceipt",
                        finalgate_contract="ProductActionKernelFinalGateCertificate + CodeExecutionFinalCertificate",
                        replay_adapter="CodeExecutionReplayView",
                        production_reachable=True,
                        limitations=("profile-based sandbox execution only; no shell, no network, no credential access",),
                        test_refs=("tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="bounded_channel",
                        display_name="Bounded channel product skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.operator.connection_live_channel_action_runtime",
                        owner_symbol="ModelLedLiveChannelActionRuntime",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=("send_message",),
                        tool_registry_refs=("bounded_channel",),
                        organ_registry_refs=("channel_draft_send",),
                        authority_requirement="MissionAuthorityEnvelope must grant bounded_channel.send_message plus a mission-level bounded channel destination.",
                        authority_actions=("bounded_channel.send_message", "send_message"),
                        receipt_contract="ProductActionKernelReceipt + ChannelAdapterReceipt",
                        finalgate_contract="ProductActionKernelFinalGateCertificate + ChannelAdapterFinalGateCertificate",
                        replay_adapter="ChannelAdapterReplayView",
                        production_reachable=True,
                        limitations=("fake/local channel only by default; real transports require explicit future grant",),
                        test_refs=("tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="real_browser_control",
                        display_name="Real browser control product skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.operator.real_browser_control_runtime",
                        owner_symbol="RealBrowserControlRuntime",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=(
                            "real_browser.observe",
                            "real_browser.open",
                            "real_browser.search",
                            "real_browser.inspect_result",
                            "real_browser.open_result",
                            "real_browser.extract_evidence",
                            "real_browser.extract_entities",
                            "real_browser.extract_product_cards",
                            "real_browser.verify_extraction",
                        ),
                        tool_registry_refs=("real_browser_control",),
                        organ_registry_refs=("BrowserSessionManagerL5Live", "CloakBrowser", "BrowserWorldModelBuilder"),
                        authority_requirement="MissionAuthorityEnvelope must grant bounded browser skill actions plus the mission workspace browser_session handle.",
                        authority_actions=(
                            "real_browser_control.real_browser.observe",
                            "real_browser.observe",
                            "real_browser_control.real_browser.open",
                            "real_browser.open",
                            "real_browser_control.real_browser.search",
                            "real_browser_control.real_browser.inspect_result",
                            "real_browser_control.real_browser.open_result",
                            "real_browser_control.real_browser.extract_evidence",
                            "real_browser_control.real_browser.extract_entities",
                            "real_browser_control.real_browser.extract_product_cards",
                            "real_browser_control.real_browser.verify_extraction",
                        ),
                        receipt_contract="ProductActionKernelReceipt + RealBrowserActionReceipt",
                        finalgate_contract="ProductActionKernelFinalGateCertificate + RealBrowserFinalCertificate",
                        replay_adapter="RealBrowserControlReplayView no-reopen/no-reclick/no-retype/no-reextract",
                        production_reachable=True,
                        limitations=(
                            "Cloak/session is product-leading when available; Playwright is explicit compatibility only.",
                            "No login, payment, contact supplier, credential, cookie/session persistence, upload, download, or arbitrary JavaScript power.",
                        ),
                        test_refs=("tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="worker_fleet",
                        display_name="Worker fleet product skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.operator.worker_orchestration_runtime",
                        owner_symbol="WorkerOrchestrationRuntime",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=("spawn_worker",),
                        tool_registry_refs=("worker_fleet",),
                        organ_registry_refs=("worker_fleet_backend",),
                        authority_requirement="MissionAuthorityEnvelope must grant worker_fleet.spawn_worker; every child worker authority is a strict subset.",
                        authority_actions=("worker_fleet.spawn_worker", "spawn_worker"),
                        receipt_contract="ProductActionKernelReceipt + WorkerOrchestrationReceipt",
                        finalgate_contract="ProductActionKernelFinalGateCertificate",
                        replay_adapter="ProductActionKernelTaskLoopReplay no-respawn/no-reexecute",
                        production_reachable=True,
                        limitations=(
                            "local/fake bounded worker execution only; no worker provider calls, no scope expansion, no nested spawning",
                        ),
                        test_refs=("tests/operator/test_power_unification_pack5_multi_worker_long_task_orchestration.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="sentinel_loop",
                        display_name="Sentinel loop completion skill",
                        runtime_generation="product_action_kernel",
                        authoritative_route=RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.operator.action_kernel",
                        owner_symbol="ActionKernel",
                        adapter_id="product_action_kernel_adapter",
                        supported_operations=("summarize_evidence", "finish"),
                        tool_registry_refs=("sentinel_loop",),
                        organ_registry_refs=("sentinel_loop",),
                        authority_requirement="MissionAuthorityEnvelope for the active mission; completion cannot grant authority or execute external side effects.",
                        authority_actions=("sentinel_loop.summarize_evidence", "sentinel_loop.finish"),
                        receipt_contract="ProductActionKernelReceipt + ModelLedTaskLoopFinalCertificate",
                        finalgate_contract="ProductActionKernelFinalGateCertificate",
                        replay_adapter="ProductActionKernelTaskLoopReplay no-react completion lane",
                        production_reachable=True,
                        limitations=(
                            "internal completion lane only; no external send, browser, shell, credential, or provider-native power",
                        ),
                        test_refs=("tests/operator/test_real_monster_product_model_native_decision_client.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="browser_live_operator",
                        display_name="Browser live operator stack",
                        runtime_generation="browser_organs",
                        authoritative_route=RuntimeConnectionRoute.POWER_RUNTIME,
                        maturity=RuntimeConnectionMaturity.LOCAL_ONLY,
                        owner_module="sentinel.agent.organs.browser_operator_agent_l4_l5_live",
                        owner_symbol=None,
                        organ_registry_refs=("browser",),
                        authority_requirement="browser-scoped MissionAuthorityEnvelope",
                        authority_actions=("browser_observe", "browser_interact"),
                        receipt_contract="BrowserInteractionExecutionReceipt",
                        finalgate_contract="CoreFinalGate browser contracts",
                        replay_adapter="browser evidence and receipt adapters",
                        production_reachable=False,
                        limitations=("multiple browser runtime generations exist; official product route remains explicit opt-in",),
                        test_refs=("tests/test_browser_operator_agent_l4_l5_live.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="interactive_exploration",
                        display_name="Interactive self-exploration harness",
                        runtime_generation="real_model_experimental_harness",
                        authoritative_route=RuntimeConnectionRoute.EXPERIMENTAL_ONLY,
                        maturity=RuntimeConnectionMaturity.EXPERIMENTAL,
                        owner_module="sentinel.operator.interactive_exploration_read_only",
                        owner_symbol=None,
                        authority_requirement="experimental policy freeze and read-only snapshot scope",
                        authority_actions=("list_directory", "search_text", "read_file_segment", "finish_exploration"),
                        telemetry_required=False,
                        receipt_contract="experimental evidence catalog",
                        finalgate_contract="none_product_finalgate_not_claimed",
                        replay_adapter="exploration_trajectory.jsonl",
                        production_reachable=False,
                        limitations=("not a production MissionKernel/receipt/FinalGate route",),
                        test_refs=("tests/operator/test_interactive_exploration.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="tool_registry",
                        display_name="Capability ToolRegistry",
                        runtime_generation="capability_registry",
                        authoritative_route=RuntimeConnectionRoute.PROPOSAL_ONLY,
                        maturity=RuntimeConnectionMaturity.LIVE_BOUNDED,
                        owner_module="sentinel.capabilities.registry",
                        owner_symbol="ToolRegistry",
                        authority_requirement="policy decision only; caller must own execution path",
                        authority_actions=("capability_policy_decision",),
                        receipt_contract="CapabilityPolicyDecision.trace_event_id",
                        finalgate_contract="not_terminal_execution_surface",
                        replay_adapter="AgentEventBus policy trace",
                        production_reachable=True,
                        limitations=("registry decides policy but does not dispatch tools",),
                        test_refs=("tests/test_capability_registry.py",),
                    ),
                    RuntimeConnectionProfile(
                        connection_id="external_organ_registry",
                        display_name="ExternalOrganRegistry",
                        runtime_generation="organ_contract_registry",
                        authoritative_route=RuntimeConnectionRoute.PROPOSAL_ONLY,
                        maturity=RuntimeConnectionMaturity.LIVE_BOUNDED,
                        owner_module="sentinel.organs.registry",
                        owner_symbol="ExternalOrganRegistry",
                        authority_requirement="contract registration only; execution must use governed runtime",
                        authority_actions=("organ_contract_registered",),
                        receipt_contract="ORGAN_CONTRACT_REGISTERED event",
                        finalgate_contract="not_terminal_execution_surface",
                        replay_adapter="AgentEventBus organ contract trace",
                        production_reachable=True,
                        limitations=("organ contract registry does not enable execution",),
                        test_refs=("tests/test_p6_external_organ_foundry.py",),
                    ),
                ),
                key=lambda item: item.connection_id,
            )
        )
    )


def run_runtime_connection_health_gate(registry: RuntimeConnectionRegistry) -> ConnectionHealthResult:
    findings: list[ConnectionHealthFinding] = []
    for connection in registry.connections:
        findings.extend(_validate_connection(connection))
    failed_count = sum(1 for item in findings if item.severity in {"P0", "P1"})
    warning_count = len(findings) - failed_count
    status = (
        ConnectionHealthStatus.FAILED
        if failed_count
        else ConnectionHealthStatus.PASSED_WITH_LIMITS
        if warning_count
        else ConnectionHealthStatus.PASSED
    )
    return ConnectionHealthResult(
        status=status,
        checked_count=len(registry.connections),
        failed_count=failed_count,
        warning_count=warning_count,
        findings=tuple(findings),
    )


def _validate_connection(connection: RuntimeConnectionProfile) -> list[ConnectionHealthFinding]:
    findings: list[ConnectionHealthFinding] = []
    if _module_missing(connection.owner_module):
        findings.append(
            _finding(connection, "P1", "owner_module_missing", "Declared owner module is not importable.")
        )
    if connection.bridge_module and _module_missing(connection.bridge_module):
        findings.append(
            _finding(connection, "P1", "bridge_module_missing", "Declared bridge module is not importable.")
        )
    if not connection.authority_requirement.strip():
        findings.append(_finding(connection, "P1", "authority_requirement_missing", "Authority requirement is absent."))
    if not connection.authority_actions:
        findings.append(_finding(connection, "P1", "authority_actions_missing", "Authority actions are absent."))
    if connection.production_reachable and connection.connection_id == "read_only_research" and not connection.supported_operations:
        findings.append(_finding(connection, "P1", "supported_operations_missing", "Supported operations are absent."))
    if not connection.receipt_contract.strip():
        findings.append(_finding(connection, "P1", "receipt_contract_missing", "Receipt contract is absent."))
    if not connection.finalgate_contract.strip():
        findings.append(_finding(connection, "P1", "finalgate_contract_missing", "FinalGate contract is absent."))
    if not connection.replay_adapter.strip():
        findings.append(_finding(connection, "P1", "replay_adapter_missing", "Replay adapter is absent."))
    if connection.authoritative_route in {
        RuntimeConnectionRoute.AGENT_RUNTIME,
        RuntimeConnectionRoute.POWER_RUNTIME,
        RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE,
    } and not connection.telemetry_required:
        findings.append(_finding(connection, "P1", "telemetry_not_required", "Product route does not require telemetry."))
    if connection.authoritative_route is RuntimeConnectionRoute.EXPERIMENTAL_ONLY:
        findings.append(
            _finding(connection, "P3", "experimental_not_product_route", "Connection is explicitly experimental.")
        )
    if not connection.production_reachable and connection.authoritative_route not in {
        RuntimeConnectionRoute.EXPERIMENTAL_ONLY,
        RuntimeConnectionRoute.BLOCKED,
    }:
        findings.append(
            _finding(connection, "P3", "not_product_reachable", "Connection is declared but not product-reachable.")
        )
    return findings


def _module_missing(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is None


def _finding(
    connection: RuntimeConnectionProfile,
    severity: str,
    code: str,
    safe_summary: str,
) -> ConnectionHealthFinding:
    return ConnectionHealthFinding(
        connection_id=connection.connection_id,
        severity=severity,
        code=code,
        safe_summary=safe_summary,
    )


__all__ = [
    "ConnectionHealthFinding",
    "ConnectionHealthResult",
    "ConnectionHealthStatus",
    "RuntimeConnectionMaturity",
    "RuntimeConnectionProfile",
    "RuntimeConnectionRegistry",
    "RuntimeConnectionRoute",
    "build_default_runtime_connection_registry",
    "run_runtime_connection_health_gate",
]
