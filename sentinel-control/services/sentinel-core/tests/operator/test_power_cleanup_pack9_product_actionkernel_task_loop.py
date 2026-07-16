from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ModelLedProductActionKernelTaskLoop,
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.real_browser_control_runtime import RealBrowserControlRuntimeError
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


def test_product_loop_replay_uses_store_filesystem_helpers_when_pathlib_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
                idempotency_key="pack9-code-long-path",
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Code product dispatch completed."},
                idempotency_key="pack9-finish-long-path",
            ),
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_replay_long_path_helpers",
        mission_objective="Run bounded code and finish.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=3,
        max_material_actions=1,
    )

    result = loop.run()
    mission_roots = tuple(str(host.kernel.store.mission_dir(mission_id)) for mission_id in result.mission_ids)
    original_exists = Path.exists
    original_glob = Path.glob
    original_rglob = Path.rglob
    original_read_bytes = Path.read_bytes

    def _is_mission_path(path: Path) -> bool:
        rendered = str(path)
        return any(rendered.startswith(root) for root in mission_roots)

    def _blocked_exists(path: Path) -> bool:
        if _is_mission_path(path):
            raise FileNotFoundError("raw pathlib mission path unavailable")
        return original_exists(path)

    def _blocked_glob(path: Path, pattern: str):
        if _is_mission_path(path):
            raise FileNotFoundError("raw pathlib mission path unavailable")
        return original_glob(path, pattern)

    def _blocked_rglob(path: Path, pattern: str):
        if _is_mission_path(path):
            raise FileNotFoundError("raw pathlib mission path unavailable")
        return original_rglob(path, pattern)

    def _blocked_read_bytes(path: Path) -> bytes:
        if _is_mission_path(path):
            raise FileNotFoundError("raw pathlib mission path unavailable")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "exists", _blocked_exists)
    monkeypatch.setattr(Path, "glob", _blocked_glob)
    monkeypatch.setattr(Path, "rglob", _blocked_rglob)
    monkeypatch.setattr(Path, "read_bytes", _blocked_read_bytes)

    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
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


def test_browser_runtime_exception_reaches_next_model_turn_as_recoverable_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://www.python.org/search/")
    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", lambda _envelope: _RuntimeDispatchFailingEngine())
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    scope = host.create_product_task_resource_scope(
        root_session_id="session_pack9_browser_runtime_exception",
        workspace_root=workspace,
    )
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "Path.glob official docs"},
                idempotency_key="pack9-browser-runtime-exception-1",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "Path.glob official docs"},
                idempotency_key="pack9-browser-runtime-exception-2",
            ),
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_browser_runtime_exception",
        mission_objective="Use Python.org browser search for official pathlib Path.glob documentation.",
        decision_client=decision_client,
        allowed_domains=("python.org",),
        max_model_calls=2,
        max_material_actions=2,
        max_recoverable_action_failures=1,
        product_task_resource_scope=scope,
    )

    result = loop.run()

    assert len(decision_client.contexts) == 2
    recovery = decision_client.contexts[1]["recoverable_action_observations"][0]
    assert recovery["failure_code"] == "real_browser_runtime_dispatch_exception"
    assert recovery["runtime_failure_fact"]["failure_stage"] == "browser_runtime_observe"
    assert recovery["model_visible_body_failure_packet"]["failure_stage"] == "browser_runtime_observe"
    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "real_browser_runtime_dispatch_exception"
    assert result.dispatch_results[0].blocked_reason == "real_browser_runtime_dispatch_exception"
    assert result.dispatch_results[0].safe_context_cards["runtime_failure_fact"]["material_effect_observed"] is False
    assert result.dispatch_results[0].safe_context_cards["runtime_failure_fact"]["session_continuity"]["root_lease_present"] is True
    assert result.dispatch_results[0].safe_context_cards["model_visible_body_failure_packet"]["can_execute"] is False


def test_off_scope_skill_selection_recovers_without_granting_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://www.python.org/search/")
    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", lambda _envelope: _RuntimeDispatchFailingEngine())
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    scope = host.create_product_task_resource_scope(
        root_session_id="session_pack9_scope",
        workspace_root=workspace,
    )
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass"},
                idempotency_key="pack9-off-scope-code-1",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "Path.glob official docs"},
                idempotency_key="pack9-off-scope-browser-2",
            ),
        ]
    )
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_scope",
        mission_objective="Use Python.org browser search for official pathlib Path.glob documentation.",
        decision_client=decision_client,
        allowed_domains=("python.org",),
        allowed_capabilities=("real_browser_control", "sentinel_loop"),
        max_model_calls=2,
        max_material_actions=2,
        max_recoverable_model_decision_failures=1,
        max_recoverable_action_failures=0,
        product_task_resource_scope=scope,
    )

    result = loop.run()

    assert "browse_search" in decision_client.contexts[0]["model_visible_skills"]
    assert "run_check" not in decision_client.contexts[0]["model_visible_skills"]
    assert len(decision_client.contexts) == 2
    recovery = decision_client.contexts[1]["recoverable_decision_observations"][0]
    assert recovery["failure_code"] == "MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE"
    assert result.capability_sequence == ("real_browser_control:real_browser.search",)
    assert result.dispatch_results[0].capability_id == "real_browser_control"
    assert result.dispatch_results[0].blocked_reason == "real_browser_runtime_dispatch_exception"
    assert result.blocked_reason == "MODEL_CALL_BUDGET_EXHAUSTED"


def test_real_browser_authority_adds_bounded_target_subdomain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://www.python.org/search/")
    authority = MissionAuthorityEnvelope(
        user_id="operator_user",
        mission_title="Python docs browser proof",
        mission_objective="Search the official Python docs.",
        allowed_tools=["real_browser_control"],
        allowed_actions=["real_browser.search"],
        allowed_domains=["python.org"],
    )

    expanded = runtime_host_module._real_browser_authority(authority)

    assert expanded.allowed_domains == [
        "python.org",
        "www.python.org",
        "real_browser:bounded_test_url",
    ]
    assert authority.allowed_domains == ["python.org"]


def test_real_browser_authority_does_not_add_ungranted_bounded_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://www.python.org/search/")
    authority = MissionAuthorityEnvelope(
        user_id="operator_user",
        mission_title="Wrong domain browser proof",
        mission_objective="Search a non-granted domain.",
        allowed_tools=["real_browser_control"],
        allowed_actions=["real_browser.search"],
        allowed_domains=["example.com"],
    )

    expanded = runtime_host_module._real_browser_authority(authority)

    assert "www.python.org" not in expanded.allowed_domains
    assert expanded.allowed_domains == ["example.com", "real_browser:bounded_test_url"]


def test_provider_empty_visible_content_after_product_receipt_recovers_to_finish(
    tmp_path: Path,
) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    decision_client = _ProviderEmptyAfterReceiptDecisionClient()
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_pack9_provider_empty_after_receipt",
        mission_objective="Search the bounded local browser fixture and finish with receipt proof.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        allowed_capabilities=("real_browser_control", "sentinel_loop"),
        max_model_calls=3,
        max_material_actions=1,
        max_recoverable_model_decision_failures=1,
    )

    result = loop.run()

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 1
    assert len(result.product_receipt_refs) == 1
    assert len(decision_client.contexts) == 3
    recovery = decision_client.contexts[2]["recoverable_decision_observations"][0]
    assert recovery["failure_code"] == "PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION"
    assert recovery["can_execute"] is False


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


class _RuntimeDispatchFailingEngine:
    browser_backend_id = "cloak_browser"
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"
    safe_url_origin_hash = "python-org-origin-hash"

    def bind_authority(self, authority: object) -> None:
        self.authority = authority

    def observe(self) -> object:
        raise RealBrowserControlRuntimeError("browser_session_post_action_snapshot_failed:RuntimeError")

    def close(self) -> None:
        self.closed = True


class _ProviderEmptyAfterReceiptDecisionClient:
    def __init__(self) -> None:
        self.contexts: list[dict[str, object]] = []
        self.call_count = 0

    def complete(self, context: dict[str, object]) -> ActionEnvelope:
        self.contexts.append(context)
        self.call_count += 1
        if self.call_count == 1:
            return ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"engine_profile": "local_fake", "query": "glasses under 5 euro"},
                idempotency_key="pack9-provider-empty-search",
            )
        if self.call_count == 2:
            raise ActionKernelError("PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION")
        return ActionEnvelope(
            capability_id="sentinel_loop",
            operation="finish",
            params={"safe_summary": "Bounded local browser receipt exists after provider-empty recovery."},
            idempotency_key="pack9-provider-empty-finish",
        )


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))
