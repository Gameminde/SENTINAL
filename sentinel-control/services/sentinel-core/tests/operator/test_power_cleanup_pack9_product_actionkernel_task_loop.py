from __future__ import annotations

import json
from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ModelLedProductActionKernelTaskLoop,
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import DispatchStatus


def test_model_led_product_loop_dispatches_code_then_channel_through_runtimehost(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
                idempotency_key="pack9-code",
            ),
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params=_channel_params(),
                idempotency_key="pack9-channel",
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Code and channel product dispatch completed."},
                idempotency_key="pack9-finish",
            ),
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_multi_skill",
        mission_objective="Run bounded code, send a bounded local channel message, then finish.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=2,
    )

    result = loop.run()
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_product_action_kernel_task_loop_finish"
    assert result.model_call_count == 3
    assert result.material_action_count == 2
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "sentinel_loop:finish",
    )
    assert tuple(dispatch.status for dispatch in result.dispatch_results) == (
        DispatchStatus.COMPLETED,
        DispatchStatus.COMPLETED,
    )
    assert all(dispatch.adapter_id == "product_action_kernel_adapter" for dispatch in result.dispatch_results)
    assert len(result.product_receipt_refs) == 2
    assert len(result.product_finalgate_refs) == 2

    code_receipt = _product_receipt(host, result.dispatch_results[0].mission_id, result.product_receipt_refs[0])
    channel_receipt = _product_receipt(host, result.dispatch_results[1].mission_id, result.product_receipt_refs[1])
    assert code_receipt["skill_id"] == "code_execution_sandbox"
    assert code_receipt["backend_id"] == "code_execution_skill"
    assert channel_receipt["skill_id"] == "bounded_channel"
    assert channel_receipt["backend_id"] == "bounded_channel_skill"

    assert decision_client.contexts[1]["recent_product_receipt_refs"] == [result.product_receipt_refs[0]]
    assert decision_client.contexts[2]["recent_product_receipt_refs"] == list(result.product_receipt_refs)
    assert decision_client.contexts[2]["product_action_kernel_dispatch_count"] == 2
    assert decision_client.contexts[2]["model_visible_available_actions"] == ["sentinel_loop.finish"]

    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.product_dispatch_delta == 0
    assert replay.command_executions_delta == 0
    assert replay.channel_transport_sends_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_model_led_product_loop_blocks_real_channel_transport_before_send(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params=_channel_params(adapter_id="telegram_live_adapter", channel="telegram"),
                idempotency_key="pack9-real-channel",
            )
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_real_channel_block",
        mission_objective="Attempt a real channel send without an explicit live transport grant.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=2,
        max_material_actions=1,
    )

    result = loop.run()

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "bounded_channel_real_transport_not_authorized"
    assert result.material_action_count == 0
    assert result.product_receipt_refs == ()
    assert result.dispatch_results[0].status is DispatchStatus.BLOCKED


def test_model_led_product_loop_rejects_non_product_skill_without_local_shortcut(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="browser_control",
                operation="click",
                params={"ref": "button:test"},
                idempotency_key="pack9-browser-shortcut",
            )
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_non_product_block",
        mission_objective="Non-product browser action must not bypass RuntimeHost.",
        decision_client=decision_client,
        max_model_calls=2,
        max_material_actions=1,
    )

    result = loop.run()

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "skill_not_product_dispatchable"
    assert result.capability_sequence == ("browser_control:click",)
    assert result.product_receipt_refs == ()
    assert result.dispatch_results[0].adapter_id is None


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 9\n", encoding="utf-8")
    return root


def _channel_params(
    *,
    adapter_id: str = "pack9_fake_channel",
    channel: str = "webhook",
) -> dict[str, object]:
    return {
        "adapter_id": adapter_id,
        "channel": channel,
        "body": "Safe bounded Pack 9 channel dispatch.",
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:pack9_product_loop"],
        "idempotency_key": "pack9-send-1",
    }


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))
