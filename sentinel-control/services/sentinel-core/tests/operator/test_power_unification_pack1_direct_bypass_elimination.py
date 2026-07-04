from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.channel_adapter import ChannelConnectorRuntime
from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterKind,
    ChannelProviderKind,
    ChannelRecipientPolicy,
    ChannelScopePolicy,
)
from sentinel.operator.connection_live_channel_action_models import LiveChannelSendDecision
from sentinel.operator.connection_live_channel_action_runtime import ModelLedLiveChannelActionRuntime
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.model_led_product_action_kernel_task_loop import ProductActionKernelLoopDecisionClient
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.mutation_artifact_channel import (
    GovernedMutationArtifactChannel,
    MutationArtifactChannelConfig,
)
from sentinel.operator.real_model_certification import _workspace_request
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_product_channel_receipt_records_internal_backend_and_product_dispatch_owner(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_unification_pack1_product_channel",
        mission_objective="Send one bounded local channel message through the product spine.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="bounded_channel",
                    operation="send_message",
                    params=_channel_params(),
                    idempotency_key="pack1-channel",
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Bounded channel dispatch completed."},
                ),
            ]
        ),
        allowed_domains=("example.com",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status.value == "completed"
    assert result.product_receipt_refs

    channel_mission_id = result.dispatch_results[0].mission_id
    adapter_receipt = _first_json(host.kernel.store.mission_dir(channel_mission_id) / "channel_adapters" / "receipts")
    assert adapter_receipt["backend_id"] == "channel_draft_send_organ_backend"
    assert adapter_receipt["backend_owner"] == "internal_channel_backend"
    assert adapter_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"
    assert adapter_receipt["future_permission"] is False


def test_direct_channel_runtime_receipt_is_not_product_dispatch_proof(tmp_path: Path) -> None:
    channel_runtime, mission_id = _channel_runtime(
        tmp_path,
        transport=lambda _request: {"delivery_ref": "direct-delivery"},
    )
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))

    ModelLedLiveChannelActionRuntime(channel_runtime).execute_send_decision(
        mission_id=mission_id,
        decision=_decision(adapter.adapter_id),
        envelope=_channel_envelope(mission_id),
    )

    adapter_receipt = _first_json(channel_runtime.store.mission_dir(mission_id) / "channel_adapters" / "receipts")
    assert adapter_receipt["backend_id"] == "channel_draft_send_organ_backend"
    assert adapter_receipt["backend_owner"] == "internal_channel_backend"
    assert adapter_receipt["product_dispatch_owner"] is None


def test_mutation_artifact_channel_declares_legacy_internal_apply_until_product_wired(tmp_path: Path) -> None:
    channel, _mission_id, _target = _mutation_channel(tmp_path)

    status = channel.product_wire_status()

    assert status["product_dispatchable"] is False
    assert status["apply_backend_id"] == "l3_reversible_workspace_executor_backend"
    assert status["current_path"] == "GovernedMutationArtifactChannel -> L3ReversibleWorkspaceExecutor"
    assert status["target_product_path"] == "RuntimeHost -> ProductActionKernelDispatchAdapter -> workspace_patch"
    assert status["classification"] == "BYPASS_PRODUCT_WIRE"


def test_high_risk_direct_bypass_rows_remain_locked_in_census() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    csv_path = (
        repo_root
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_POWER_UNIFICATION_PACK_0_DIRECT_BYPASS_AND_DUAL_PATH_CENSUS_V1.csv"
    )
    text = csv_path.read_text(encoding="utf-8")

    for bypass_id in ("BYPASS-SPEND-001", "BYPASS-EXTERNALAPI-001", "BYPASS-CLI-001"):
        assert bypass_id in text
    assert text.count("BYPASS_LOCK_HIGH_RISK") >= 5


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 1\n", encoding="utf-8")
    return root


def _channel_params() -> dict[str, object]:
    return {
        "adapter_id": "pack1_fake_channel",
        "channel": "webhook",
        "body": "Safe bounded Pack 1 channel dispatch.",
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:pack1_product_loop"],
        "idempotency_key": "pack1-send-1",
    }


def _channel_runtime(tmp_path: Path, transport=None) -> tuple[ChannelConnectorRuntime, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_unification_pack1_direct_channel",
        draft=MissionDraft(
            title="Direct channel compatibility path",
            objective="Exercise the legacy/internal channel runtime directly.",
            expected_artifacts=["channel receipt"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="pending",
            allowed_actions=["channel_send"],
            forbidden_actions=["payment", "credential_access"],
            summary="Direct channel compatibility authority.",
        ),
    )
    runtime = ChannelConnectorRuntime(kernel, transports={"webhook": transport} if transport else {})
    return runtime, record.mission_id


def _webhook_config(*, require_approval: bool) -> ChannelAdapterConfig:
    return ChannelAdapterConfig(
        adapter_id="adapter_unification_pack1_webhook",
        kind=ChannelAdapterKind.WEBHOOK,
        provider_kind=ChannelProviderKind.WEBHOOK,
        display_name="Pack 1 local webhook",
        capability_profile={"supports_inbound": True, "supports_outbound": True},
        recipient_policy=ChannelRecipientPolicy(allowed_domains=["example.com"], max_recipients=1),
        scope_policy=ChannelScopePolicy(allowed_channels=["webhook"]),
        approval_policy={"approval_required_for_send": require_approval},
    )


def _decision(adapter_id: str) -> LiveChannelSendDecision:
    return LiveChannelSendDecision(
        decision_id="decision_pack1_direct_channel",
        action="send_message",
        adapter_id=adapter_id,
        channel="webhook",
        body="Here is a bounded channel reply.",
        recipients=("founder@example.com",),
        recipient_provenance={"founder@example.com": "mission_level_destination_grant"},
        evidence_refs=("evidence:channel_context",),
        idempotency_key="pack1-direct-send",
    )


def _channel_envelope(mission_id: str) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Bounded channel mission",
        mission_objective="Send one scoped channel message.",
        allowed_tools=["channel:webhook", "channel_draft_send"],
        allowed_actions=["channel_send"],
        forbidden_actions=["payment", "credential_access"],
        allowed_domains=["example.com"],
        max_recipients=1,
        max_actions=10,
        created_at=now,
        expires_at=now + timedelta(minutes=30),
    )


def _mutation_channel(tmp_path: Path) -> tuple[GovernedMutationArtifactChannel, str, Path]:
    repo_root = tmp_path / "repo"
    target = repo_root / "src" / "pricing.py"
    target.parent.mkdir(parents=True)
    initial = "def double(amount: int) -> int:\n    return amount\n"
    target.write_text(initial, encoding="utf-8")
    kernel = MissionKernel(run_root=tmp_path / "runs")
    mission = kernel.create_mission(
        session_id="session_unification_pack1_mutation",
        draft=MissionDraft(title="Mutation compatibility lane", objective="Inspect mutation backend status."),
    )
    channel = GovernedMutationArtifactChannel(
        kernel=kernel,
        workspace_root=repo_root,
        mission_id=mission.mission_id,
        run_id="run:unification-pack1",
        workspace_ref="workspace:controlled-repo",
        config=MutationArtifactChannelConfig(max_chunk_bytes=128, max_artifact_bytes=2_048, max_chunks=8),
        workspace_request_factory=lambda path, content, before_hash: _workspace_request(
            repo_root,
            mission.mission_id,
            path,
            content,
            before_hash,
            remaining_action_count=16,
            remaining_patch_bytes=16_384,
        ),
    )
    assert text_hash(initial)
    return channel, mission.mission_id, target


def _first_json(directory: Path) -> dict[str, object]:
    files = sorted(directory.glob("*.json"))
    assert files
    return json.loads(files[0].read_text(encoding="utf-8"))
