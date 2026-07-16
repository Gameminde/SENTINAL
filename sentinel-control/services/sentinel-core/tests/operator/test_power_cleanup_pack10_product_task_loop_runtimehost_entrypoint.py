from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_runtimehost_exposes_product_task_loop_entrypoint(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    frame = host.product_task_loop_entrypoint_frame()

    assert frame["entrypoint_id"] == "product_action_kernel_task_loop"
    assert frame["enabled"] is True
    assert frame["runtime_bridge"] == "ModelLedProductActionKernelTaskLoop"
    assert frame["model_visible_available_actions"] == [
        "workspace_patch.apply_patch",
        "code_execution_sandbox.code_exec.run_profile",
        "bounded_channel.send_message",
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.open_result",
        "real_browser_control.real_browser.extract_evidence",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
        "worker_fleet.spawn_worker",
        "sentinel_loop.finish",
    ]
    assert "real_browser_control.real_browser.type_text" not in frame["model_visible_available_actions"]
    assert "real_browser_control.real_browser.click" not in frame["model_visible_available_actions"]
    assert "payment_authority.spend" not in frame["model_visible_available_actions"]
    assert "provider_native_tools" in frame["hard_boundaries"]
    assert frame["data_not_authority"] is True
    assert frame["can_execute"] is False


def test_product_task_loop_entrypoint_routes_code_then_channel_then_finish(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = _code_channel_finish_client()

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_entrypoint",
        mission_objective="Run bounded code, send a local bounded channel message, then finish.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_product_action_kernel_task_loop_finish"
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 2
    assert len(result.product_receipt_refs) == 2
    assert all(dispatch.adapter_id == "product_action_kernel_adapter" for dispatch in result.dispatch_results)


def test_entrypoint_uses_pack9_loop_not_local_actionkernel_shortcut(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_no_shortcut",
        mission_objective="Dispatch through the product runtime spine.",
        decision_client=_code_channel_finish_client(),
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    assert result.loop_id.startswith("product_action_kernel_task_loop_")
    assert result.dispatch_results
    assert all(dispatch.adapter_id == "product_action_kernel_adapter" for dispatch in result.dispatch_results)
    assert all(ref.startswith("product_action_kernel_receipt_") for ref in result.product_receipt_refs)
    assert all(ref.startswith("product_action_kernel_finalgate_") for ref in result.product_finalgate_refs)


def test_entrypoint_context_carries_prior_product_receipts(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = _code_channel_finish_client()

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_context",
        mission_objective="Expose product receipt truth to later model turns.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    assert decision_client.contexts[1]["recent_product_receipt_refs"] == [result.product_receipt_refs[0]]
    assert decision_client.contexts[2]["recent_product_receipt_refs"] == list(result.product_receipt_refs)
    assert decision_client.contexts[2]["model_visible_available_actions"] == ["sentinel_loop.finish"]


def test_finish_requires_product_receipt_or_explicit_noop_proof(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    finish_only = ProductActionKernelLoopDecisionClient(
        [ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "No-op."})]
    )

    blocked = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_finish_block",
        mission_objective="Finish without product proof should block.",
        decision_client=finish_only,
    )

    noop_client = ProductActionKernelLoopDecisionClient(
        [ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "No-op proof."})]
    )
    completed = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_finish_noop",
        mission_objective="Finish with explicit no-op proof may complete.",
        decision_client=noop_client,
        explicit_noop_proof_ref="noop:operator-approved-no-material-action",
    )

    assert blocked.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert blocked.blocked_reason == "MODEL_FINISH_BEFORE_PRODUCT_RECEIPT"
    assert completed.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert completed.material_action_count == 0


def test_replay_does_not_rerun_code_resend_channel_reapply_patch(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_replay",
        mission_objective="Prove product task-loop replay is no-react.",
        decision_client=_code_channel_finish_client(),
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.product_dispatch_delta == 0
    assert replay.command_executions_delta == 0
    assert replay.channel_transport_sends_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_real_channel_transport_blocked_without_explicit_grant(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_real_channel_block",
        mission_objective="Real channel transport is not enabled by Pack 10.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="bounded_channel",
                    operation="send_message",
                    params=_channel_params(adapter_id="telegram_live_adapter", channel="telegram"),
                )
            ]
        ),
        allowed_domains=("example.com",),
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "bounded_channel_real_transport_not_authorized"
    assert result.product_receipt_refs == ()


def test_browser_live_skill_routes_through_product_entrypoint_after_pack4(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    frame = host.product_task_loop_entrypoint_frame()

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_browser_product",
        mission_objective="Browser high-level power routes through the product entrypoint.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.search",
                    params={"query": "x", "engine_profile": "fake_product_search"},
                ),
                ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "Browser product route completed."}),
            ]
        ),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert "real_browser_control.real_browser.search" in frame["model_visible_available_actions"]
    assert "real_browser_control.real_browser.type_text" not in frame["model_visible_available_actions"]
    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "sentinel_loop:finish",
    )


def test_known_non_product_skill_returns_skill_not_product_dispatchable(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_non_product",
        mission_objective="Known non-product skill must block honestly.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [ActionEnvelope(capability_id="browser_control", operation="click", params={"ref": "button:test"})]
        ),
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "skill_not_product_dispatchable"


def test_unknown_skill_returns_unknown_skill_or_capability(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_unknown",
        mission_objective="Unknown skill must block honestly.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [ActionEnvelope(capability_id="unknown_power", operation="do", params={})]
        ),
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "unknown_skill_or_capability"


def test_high_risk_payment_login_credentials_contact_still_block(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    with pytest.raises(ValueError, match="credential|secret"):
        ActionEnvelope(capability_id="credential_vault", operation="read_secret", params={})

    for capability_id, operation in (
        ("payment_authority", "spend"),
        ("account_authority", "login"),
        ("external_channel", "contact_supplier"),
    ):
        result = host.run_product_action_kernel_task_loop(
            workspace_root=workspace,
            session_id=f"session_pack10_hard_stop_{capability_id}",
            mission_objective="High-risk actions stay closed.",
            decision_client=ProductActionKernelLoopDecisionClient(
                [ActionEnvelope(capability_id=capability_id, operation=operation, params={})]
            ),
        )

        assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
        assert result.product_receipt_refs == ()
        assert result.blocked_reason in {"skill_not_product_dispatchable", "unknown_skill_or_capability"}


def test_no_raw_provider_reasoning_dom_cookies_session_persisted(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack10_scan",
        mission_objective="Scan persisted task-loop artifacts.",
        decision_client=_code_channel_finish_client(),
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    persisted = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "runs").rglob("*.json"))
    persisted = persisted.replace(str(tmp_path), "[tmp_path]")
    persisted = persisted.replace(json.dumps(str(tmp_path))[1:-1], "[tmp_path]")
    forbidden = (
        "raw_provider",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning_content",
        "cookie:",
        "session_token",
        "authorization",
        "bearer ",
    )
    assert not any(marker in persisted.lower() for marker in forbidden)


def _code_channel_finish_client() -> ProductActionKernelLoopDecisionClient:
    return ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
                idempotency_key="pack10-code",
            ),
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params=_channel_params(),
                idempotency_key="pack10-channel",
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Product task-loop entrypoint completed."},
                idempotency_key="pack10-finish",
            ),
        ]
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 10\n", encoding="utf-8")
    return root


def _channel_params(
    *,
    adapter_id: str = "pack10_fake_channel",
    channel: str = "webhook",
) -> dict[str, object]:
    return {
        "adapter_id": adapter_id,
        "channel": channel,
        "body": "Safe bounded Pack 10 channel dispatch.",
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:pack10_product_loop"],
        "idempotency_key": "pack10-send-1",
    }


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))
