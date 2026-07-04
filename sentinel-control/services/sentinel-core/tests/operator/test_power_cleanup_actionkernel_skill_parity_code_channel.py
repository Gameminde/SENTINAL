from __future__ import annotations

import json
from pathlib import Path

from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.channel_adapter_replay import ChannelAdapterReplayBuilder
from sentinel.operator.code_execution_sandbox_replay import CodeExecutionReplayView
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import DispatchStatus


def test_runtimehost_registers_code_execution_sandbox_product_skill(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    connection = host.connection_registry.get("code_execution_sandbox")
    assert connection.adapter_id == "product_action_kernel_adapter"
    assert connection.production_reachable is True
    assert connection.supported_operations == ("code_exec.run_profile",)

    skill = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry).get(
        "code_execution_sandbox"
    )
    assert skill.product_reachable is True
    assert skill.adapter_id == "product_action_kernel_adapter"
    assert skill.can_execute is False


def test_code_execution_routes_through_product_action_kernel_adapter(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_code_mission(host, workspace, parameters={"profile_id": "fake_pass", "args": ["."]})

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.COMPLETED
    assert result.dispatch_result.adapter_id == "product_action_kernel_adapter"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    state = host.lifecycle.derive_request_state(mission.record.mission_id, mission.execution_request.request_id)
    assert state.state is MissionExecutionRequestState.COMPLETED

    product_receipt = _product_receipt(host, mission.record.mission_id, result.dispatch_result.receipt_refs[0])
    assert product_receipt["skill_id"] == "code_execution_sandbox"
    assert product_receipt["backend_id"] == "code_execution_skill"
    assert product_receipt["execution_status"] == "passed"
    assert product_receipt["material_action"] is True

    code_receipts = list(
        (host.kernel.store.mission_dir(mission.record.mission_id) / "code_execution_sandbox" / "receipts").glob("*.json")
    )
    assert code_receipts
    replay = CodeExecutionReplayView.from_store(
        host.kernel.store,
        mission_id=mission.record.mission_id,
        workspace_root=workspace,
    )
    assert replay.command_executions_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_code_execution_requires_explicit_sandbox_authority(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_code_mission(
        host,
        workspace,
        parameters={"profile_id": "fake_pass", "args": ["."]},
        allowed_tools=["read_only_research"],
        allowed_actions=["read_file_segment"],
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "authority_incompatible_dispatch"


def test_code_execution_timeout_becomes_recoverable_observation(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_code_mission(host, workspace, parameters={"profile_id": "fake_timeout", "args": ["."]})

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "EXECUTOR_TIMEOUT"
    product_receipt = _product_receipt(host, mission.record.mission_id, result.dispatch_result.receipt_refs[0])
    assert product_receipt["recovery_classification"] == "RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE"
    assert product_receipt["execution_status"] == "timeout"


def test_code_execution_blocks_network_filesystem_credentials_without_grant(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_code_mission(
        host,
        workspace,
        parameters={"profile_id": "fake_pass", "args": ["https://example.com"]},
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "code_exec_network_arg_blocked"


def test_runtimehost_registers_bounded_channel_product_skill_for_fake_channel(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    connection = host.connection_registry.get("bounded_channel")
    assert connection.adapter_id == "product_action_kernel_adapter"
    assert connection.production_reachable is True
    assert connection.supported_operations == ("send_message",)

    skill = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry).get("bounded_channel")
    assert skill.product_reachable is True
    assert skill.adapter_id == "product_action_kernel_adapter"
    assert skill.can_execute is False


def test_bounded_channel_routes_through_product_action_kernel_adapter(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_channel_mission(host, workspace, parameters=_channel_params())

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.COMPLETED
    assert result.dispatch_result.adapter_id == "product_action_kernel_adapter"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED

    product_receipt = _product_receipt(host, mission.record.mission_id, result.dispatch_result.receipt_refs[0])
    assert product_receipt["skill_id"] == "bounded_channel"
    assert product_receipt["backend_id"] == "bounded_channel_skill"
    assert product_receipt["execution_status"] == "completed"
    assert product_receipt["material_action"] is True

    replay = ChannelAdapterReplayBuilder(host.kernel.store).build(mission.record.mission_id)
    assert replay.reexecuted_actions is False
    assert len(replay.receipts) == 1
    assert replay.send_results[0].status == "sent"


def test_bounded_channel_requires_explicit_channel_authority(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_channel_mission(
        host,
        workspace,
        parameters=_channel_params(),
        allowed_tools=["bounded_channel"],
        allowed_actions=["bounded_channel.send_message"],
        allowed_domains=[],
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "authority_incompatible_dispatch"


def test_bounded_channel_real_send_not_available_without_explicit_grant(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_channel_mission(
        host,
        workspace,
        parameters=_channel_params(adapter_id="telegram_live_adapter", channel="telegram"),
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "bounded_channel_real_transport_not_authorized"


def test_bounded_channel_unavailable_becomes_recoverable_observation(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _create_channel_mission(
        host,
        workspace,
        parameters=_channel_params(adapter_id="missing_local_transport", channel="webhook"),
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "EXECUTOR_RECOVERABLE_RUNTIME_MISS"
    product_receipt = _product_receipt(host, mission.record.mission_id, result.dispatch_result.receipt_refs[0])
    assert product_receipt["recovery_classification"] == "RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE"


def test_known_non_product_skill_still_returns_skill_not_product_dispatchable(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = host.lifecycle.create_mission(
        session_id="session_pack8_non_product",
        draft=_draft(),
        authority_summary=_summary(["browser_control"], ["browser.click"]),
        approval_scope=_approval_scope(workspace, ["browser_control"], ["browser.click"]),
        policy=_policy(workspace, ["browser_control"], ["browser.click"]),
        capability_id="browser_control",
        operation="click",
        parameters={"ref": "button:test"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack8_fake",
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "skill_not_product_dispatchable"


def test_unknown_skill_returns_unknown_skill_or_capability(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = host.lifecycle.create_mission(
        session_id="session_pack8_unknown",
        draft=_draft(),
        authority_summary=_summary(["unknown_power"], ["unknown_power.do"]),
        approval_scope=_approval_scope(workspace, ["unknown_power"], ["unknown_power.do"]),
        policy=_policy(workspace, ["unknown_power"], ["unknown_power.do"]),
        capability_id="unknown_power",
        operation="do",
        parameters={},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack8_fake",
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "unknown_skill_or_capability"


def test_high_risk_payment_login_credentials_contact_still_block(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")
    registry = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry)

    for skill_id in ("payment_authority", "account_authority", "financial_authority", "external_api"):
        binding = registry.get(skill_id)
        assert binding.product_reachable is False
        assert binding.dispatch_enabled is False


def test_read_only_research_remains_supporting_evidence_not_primary_dispatch(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    read_only = host.connection_registry.get("read_only_research")
    assert read_only.adapter_id == "read_only_research_adapter"
    assert read_only.authoritative_route.value == "agent_runtime"
    assert host.connection_registry.get("workspace_patch").adapter_id == "product_action_kernel_adapter"
    assert host.connection_registry.get("code_execution_sandbox").adapter_id == "product_action_kernel_adapter"
    assert host.connection_registry.get("bounded_channel").adapter_id == "product_action_kernel_adapter"


def _create_code_mission(
    host: SentinelRuntimeHost,
    workspace: Path,
    *,
    parameters: dict[str, object],
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
):
    allowed_tools = allowed_tools or ["code_execution_sandbox"]
    allowed_actions = allowed_actions or ["code_execution_sandbox.code_exec.run_profile", "code_exec.run_profile"]
    return host.lifecycle.create_mission(
        session_id="session_pack8_code",
        draft=_draft(),
        authority_summary=_summary(allowed_tools, allowed_actions),
        approval_scope=_approval_scope(workspace, allowed_tools, allowed_actions),
        policy=_policy(workspace, allowed_tools, allowed_actions),
        capability_id="code_execution_sandbox",
        operation="code_exec.run_profile",
        parameters=parameters,
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack8_fake",
    )


def _create_channel_mission(
    host: SentinelRuntimeHost,
    workspace: Path,
    *,
    parameters: dict[str, object],
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
    allowed_domains: list[str] | None = None,
):
    allowed_tools = allowed_tools or ["bounded_channel", "channel_draft_send"]
    allowed_actions = allowed_actions or ["bounded_channel.send_message", "send_message"]
    allowed_domains = ["example.com"] if allowed_domains is None else allowed_domains
    return host.lifecycle.create_mission(
        session_id="session_pack8_channel",
        draft=_draft(),
        authority_summary=_summary(allowed_tools, allowed_actions),
        approval_scope=_approval_scope(workspace, allowed_tools, allowed_actions, allowed_domains=allowed_domains),
        policy=_policy(workspace, allowed_tools, allowed_actions, allowed_domains=allowed_domains),
        capability_id="bounded_channel",
        operation="send_message",
        parameters=parameters,
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack8_fake",
    )


def _channel_params(
    *,
    adapter_id: str = "pack8_fake_channel",
    channel: str = "webhook",
) -> dict[str, object]:
    return {
        "adapter_id": adapter_id,
        "channel": channel,
        "body": "Safe bounded channel dispatch.",
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:pack8_channel_context"],
        "idempotency_key": "pack8-send-1",
    }


def _draft() -> MissionDraft:
    return MissionDraft(
        title="RuntimeHost Pack 8 parity",
        objective="Dispatch bounded code and channel skills through ProductActionKernel.",
        expected_artifacts=["product action receipt", "skill receipt"],
    )


def _summary(allowed_tools: list[str], allowed_actions: list[str]) -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=allowed_actions,
        forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
        summary=f"Pack 8 authority for {', '.join(allowed_tools)}.",
    )


def _approval_scope(
    workspace: Path,
    allowed_tools: list[str],
    allowed_actions: list[str],
    *,
    allowed_domains: list[str] | None = None,
) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=allowed_tools,
        allowed_actions=allowed_actions,
        forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
        allowed_paths=[str(workspace)],
        allowed_domains=allowed_domains or [],
        max_duration_minutes=5,
        max_actions=3,
        max_recipients=1,
        max_cost_usd=0.0,
    )


def _policy(
    workspace: Path,
    allowed_tools: list[str],
    allowed_actions: list[str],
    *,
    allowed_domains: list[str] | None = None,
) -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=allowed_tools,
        allowed_actions=allowed_actions,
        forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
        allowed_paths=[str(workspace)],
        allowed_domains=allowed_domains or [],
        max_duration_minutes=5,
        max_actions=3,
        max_recipients=1,
        max_cost_usd=0.0,
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 8\n", encoding="utf-8")
    return root


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))
