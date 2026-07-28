from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.live_run_evidence_sink import CrashSafeBoundedLiveRunEvidenceSink
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.real_browser_control_runtime import (
    InMemoryRealBrowserEngine,
    RealBrowserControlRuntime,
    RealBrowserControlRuntimeError,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import load_product_action_kernel_artifact


def test_browser_product_skill_consumes_mission_workspace_browser_session_handle(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = _browser_search_finish_client()

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_session_handle",
        mission_objective="Search a bounded fake browser catalog, then finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    action_mission_id = result.dispatch_results[0].mission_id
    manifest = _mission_workspace_manifest(host, action_mission_id)
    browser_handle = _handle(manifest, "browser_session")
    browser_receipt = _first_json(host.kernel.store.mission_dir(action_mission_id) / "real_browser_control" / "receipts")

    assert browser_receipt["browser_session_ref"] == browser_handle["safe_ref"]
    assert browser_receipt["mission_workspace_ref"] == manifest["manifest_id"]
    assert browser_receipt["mission_workspace_hash"] == manifest["manifest_hash"]
    assert browser_receipt["simple_skill"] == "browse_search"
    assert browser_receipt["internal_action_id"] == "real_browser_control.real_browser.search"
    assert browser_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"


def test_browse_search_routes_through_runtimehost_product_action_kernel(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_route",
        mission_objective="Run browser search through the product spine.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "sentinel_loop:finish",
    )
    assert result.dispatch_results[0].adapter_id == "product_action_kernel_adapter"
    product_receipt = _product_receipt(host, result.dispatch_results[0].mission_id, result.product_receipt_refs[0])
    assert product_receipt["skill_id"] == "browse_search"
    assert product_receipt["capability_id"] == "real_browser_control"
    assert product_receipt["operation"] == "real_browser.search"
    assert product_receipt["backend_id"] == "browser_skill"
    assert product_receipt["organ_id"] == "browser_l5_l6_backend"


def test_browse_search_domain_grant_translates_to_internal_bounded_url_authority(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_domain_only_grant",
        mission_objective="Run browser search through product spine with a public domain grant.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "sentinel_loop:finish",
    )
    browser_receipt = _first_json(
        host.kernel.store.mission_dir(result.dispatch_results[0].mission_id)
        / "real_browser_control"
        / "receipts"
    )
    assert browser_receipt["action_kind"] == "real_browser.search"


def test_browse_search_product_proof_survives_long_run_root(tmp_path: Path) -> None:
    long_root = tmp_path.parent / "lp" / "browser_product_spine_segment"
    host = SentinelRuntimeHost(run_root=long_root / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_long_path_receipt_proof",
        mission_objective="Run browser search through a long-path product proof root.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.product_receipt_refs
    assert result.product_finalgate_refs


def test_extract_routes_through_runtimehost_product_action_kernel(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_extract_route",
        mission_objective="Extract visible product cards through the product spine.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.extract_product_cards",
                    params={"engine_profile": "fake_product_search"},
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Browser extraction completed."},
                ),
            ]
        ),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    action_mission_id = result.dispatch_results[0].mission_id
    browser_receipt = _first_json(host.kernel.store.mission_dir(action_mission_id) / "real_browser_control" / "receipts")
    assert browser_receipt["action_kind"] == "real_browser.extract_product_cards"
    assert browser_receipt["simple_skill"] == "extract"
    assert browser_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"


def test_generic_extract_evidence_routes_through_runtimehost_product_action_kernel(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_extract_evidence_route",
        mission_objective="Extract visible open-world evidence through the product spine.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.extract_evidence",
                    params={"engine_profile": "fake_product_search"},
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Browser evidence extraction completed."},
                ),
            ]
        ),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    action_mission_id = result.dispatch_results[0].mission_id
    browser_receipt = _first_json(host.kernel.store.mission_dir(action_mission_id) / "real_browser_control" / "receipts")
    assert browser_receipt["action_kind"] == "real_browser.extract_evidence"
    assert browser_receipt["simple_skill"] == "extract"
    assert browser_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"


def test_browser_l5_l6_registered_as_hidden_backend_not_model_surface(tmp_path: Path) -> None:
    frame = SentinelRuntimeHost(run_root=tmp_path / "runs").product_task_loop_entrypoint_frame()

    assert "browse_search" in frame["model_visible_skills"]
    assert "extract" in frame["model_visible_skills"]
    assert "real_browser_control.real_browser.search" in frame["model_visible_available_actions"]
    assert "real_browser_control.real_browser.search" in frame["runtime_internal_action_map"].values()
    assert "browser_l5_l6_backend" in frame["hidden_backend_bindings"]
    assert "real_browser.type_text" not in frame["model_visible_skills"]
    assert "Playwright" not in json.dumps(frame["model_visible_skills"])
    assert "Cloak" not in json.dumps(frame["model_visible_skills"])


def test_local_fixture_backend_is_labeled_fixture_not_cloak(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_local_fixture_backend_truth",
        mission_objective="Search through the explicit local browser fixture backend.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    browser_receipt = _first_json(host.kernel.store.mission_dir(result.dispatch_results[0].mission_id) / "real_browser_control" / "receipts")
    assert browser_receipt["selected_backend_id"] == "local_fixture_browser_engine"
    assert browser_receipt["actual_backend_id"] == "local_fixture_browser_engine"
    assert browser_receipt["session_backend_kind"] == "local_fixture"
    assert browser_receipt["backend_mismatch"] is False


def test_missing_live_browser_config_blocks_without_fixture_impersonation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SENTINEL_BROWSER_TEST_URL", raising=False)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_missing_live_browser_config",
        mission_objective="Live browser product path must not silently impersonate Cloak with a fixture.",
        decision_client=_browser_search_finish_client_without_engine_profile(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=1,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "real_browser_live_backend_config_missing"
    assert len(result.dispatch_results) == 1
    assert result.dispatch_results[0].blocked_reason == "real_browser_live_backend_config_missing"
    mission_dir = host.kernel.store.mission_dir(result.dispatch_results[0].mission_id)
    assert not (mission_dir / "real_browser_control" / "receipts").exists()


def test_env_configured_browser_product_route_uses_cloak_first_engine_factory(tmp_path: Path, monkeypatch) -> None:
    calls: list[bool] = []

    def fake_factory() -> object:
        calls.append(True)
        return runtime_host_module._ProductLocalCloakBrowserEngine()

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_env_cloak_backend",
        mission_objective="Search through the env-configured Cloak product browser backend.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.search",
                    params={"query": "glasses under 5 euro"},
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Browser env route completed."},
                ),
            ]
        ),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert calls == [True]


def test_browser_action_start_exception_creates_body_failure_fact_and_packet(tmp_path: Path, monkeypatch) -> None:
    def fake_factory() -> object:
        raise FileNotFoundError("C:/private/local/private_cloak_binary.exe")

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    sink = CrashSafeBoundedLiveRunEvidenceSink(
        evidence_root=tmp_path / "evidence",
        run_id="action_start_exception",
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_action_start_exception_packet",
        mission_objective="Find official Python documentation for pathlib Path.glob.",
        decision_client=_browser_search_finish_client_without_engine_profile(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=1,
        max_material_actions=1,
        evidence_sink=sink,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert len(result.dispatch_results) == 1
    dispatch = result.dispatch_results[0]
    assert dispatch.blocked_reason == "real_browser_action_start_exception"
    cards = dispatch.safe_context_cards
    assert isinstance(cards, dict)
    fact = cards["runtime_failure_fact"]
    packet = cards["model_visible_body_failure_packet"]
    assert fact["failure_code"] == "real_browser_action_start_exception"
    assert fact["failure_stage"] == "binary_provenance_resolution"
    assert fact["resource_kind"] == "browser_binary"
    assert fact["exception_class"] == "FileNotFoundError"
    assert fact["exception_hash"]
    assert fact["typed_retryability"]["retryable"] is False
    assert fact["resource_lifecycle_facts"]["exists"] is False
    assert fact["resource_lifecycle_facts"]["mechanical_recovery_attempted"] is False
    assert packet["failure_stage"] == "binary_provenance_resolution"
    assert packet["typed_outcome"]["failure_code"] == "real_browser_action_start_exception"
    assert packet["runtime_failure_fact"]["authoritative"] is True
    assert packet["model_blocker_assessment"]["advisory_only"] is True

    snapshot = sink.load_snapshot()
    event_types = [event["event_type"] for event in snapshot["events"]]
    assert "browser_action_started" in event_types
    assert "runtime_failure_fact_created" in event_types
    assert "model_visible_failure_packet_created" in event_types
    assert "cleanup_result" in event_types
    persisted = json.dumps(snapshot, sort_keys=True) + json.dumps(cards, sort_keys=True)
    assert "private_cloak_binary.exe" not in persisted
    assert "C:/private/local" not in persisted


class _ClosableProductCloakEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
    def __init__(self) -> None:
        super().__init__()
        self.close_count = 0
        self.bound_root_session_ids: list[str] = []

    def bind_root_session_id(self, root_session_id: str) -> None:
        self.bound_root_session_ids.append(root_session_id)

    def close(self) -> None:
        self.close_count += 1
        self.opened = False


def test_root_browser_lease_reused_across_child_browser_actions(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
                params={"engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Verified browser extraction summarized and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_root_browser_lease_reuse",
        mission_objective="Find bounded product cards under 5 EUR, extract visible evidence, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert len(engines) == 1
    assert engines[0].type_count >= 1
    assert engines[0].press_count >= 1
    assert engines[0].extract_count >= 1
    assert engines[0].close_count == 1
    assert engines[0].bound_root_session_ids == ["session_pack4_root_browser_lease_reuse"]


def test_root_browser_lease_closes_on_material_budget_exhaustion(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "sunglasses under 5 euro"},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_root_browser_lease_budget_close",
        mission_objective="Search twice but budget only allows one material action.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MATERIAL_ACTION_BUDGET_EXHAUSTED"
    assert len(engines) == 1
    assert engines[0].close_count == 1


def test_live_cloak_root_leases_serialize_until_close(tmp_path: Path, monkeypatch) -> None:
    class SlowClosableProductCloakEngine(_ClosableProductCloakEngine):
        active_count = 0
        max_active_count = 0
        active_lock = threading.Lock()

        def __init__(self) -> None:
            super().__init__()
            with self.active_lock:
                type(self).active_count += 1
                type(self).max_active_count = max(type(self).max_active_count, type(self).active_count)

        def type_text(self, ref: str, text: str):  # type: ignore[no-untyped-def]
            time.sleep(0.15)
            return super().type_text(ref, text)

        def close(self) -> None:
            try:
                super().close()
            finally:
                with self.active_lock:
                    type(self).active_count -= 1

    SlowClosableProductCloakEngine.active_count = 0
    SlowClosableProductCloakEngine.max_active_count = 0

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", SlowClosableProductCloakEngine)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    start_barrier = threading.Barrier(2)
    results: list[ProductActionKernelTaskLoopStatus] = []

    def _run(index: int) -> None:
        workspace = tmp_path / f"workspace_{index}"
        workspace.mkdir()
        (workspace / "README.md").write_text("# concurrent browser root\n", encoding="utf-8")
        start_barrier.wait(timeout=5)
        result = host.run_product_action_kernel_task_loop(
            workspace_root=workspace,
            session_id=f"session_pack4_concurrent_root_{index}",
            mission_objective="Run live-env browser root through serialized product spine.",
            decision_client=_browser_search_finish_client_without_engine_profile(),
            allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
            max_model_calls=3,
            max_material_actions=1,
        )
        results.append(result.status)

    threads = [threading.Thread(target=_run, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert results == [ProductActionKernelTaskLoopStatus.COMPLETED, ProductActionKernelTaskLoopStatus.COMPLETED]
    assert SlowClosableProductCloakEngine.max_active_count == 1
    assert SlowClosableProductCloakEngine.active_count == 0


def test_runtimehost_shutdown_closes_leaked_root_browser_lease(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    scope = host.create_product_task_resource_scope(
        root_session_id="session_pack4_shutdown_leaked_browser_scope",
        workspace_root=_workspace(tmp_path),
    )

    scope.browser_engine_for(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        )
    )
    assert engines[0].close_count == 0

    host.shutdown()

    assert engines[0].close_count == 1
    assert scope.closed is True


def test_product_loop_continues_to_extract_after_recoverable_browser_search_with_cards(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class SearchActuationFailingCloakEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
        def type_text(self, ref: str, text: str):  # type: ignore[no-untyped-def]
            del ref, text
            raise RealBrowserControlRuntimeError("locator_timeout")

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        SearchActuationFailingCloakEngine,
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Verified browser extraction summarized and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_recover_search_cards_to_finish",
        mission_objective="Search bounded product cards, extract visible cards, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        max_recoverable_action_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.extract_product_cards",
        "real_browser_control:real_browser.verify_extraction",
        "sentinel_loop:summarize_evidence",
        "sentinel_loop:finish",
    )
    assert client.contexts[1]["recoverable_action_observations"][0]["failure_code"] == "real_browser_search_write_failed"
    assert (
        client.contexts[1]["browser_decision_frame"]["recommended_next_actions"][0]
        == "real_browser_control.real_browser.extract_product_cards"
    )


def test_summarize_evidence_uses_product_loop_browser_cards(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={
                    "query": "glasses under 5 euro",
                    "engine_profile": "fake_product_search",
                },
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Verified browser extraction summarized and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_summary_uses_loop_cards",
        mission_objective="Search bounded product cards, extract visible cards, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    summary_result = next(
        item
        for item in result.dispatch_results
        if item.capability_id == "sentinel_loop" and item.operation == "summarize_evidence"
    )
    summary = summary_result.safe_context_cards["grounded_evidence_summary"]
    assert summary["card_count"] > 0
    assert summary["cards"]


def test_body_session_unavailable_reaches_next_model_turn_before_terminal_block(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class SearchReopenFailureEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
        def __init__(self) -> None:
            super().__init__()
            self.close_count = 0

        def observe(self):  # type: ignore[no-untyped-def]
            raise RealBrowserControlRuntimeError("browser_session_missing_or_closed")

        def open(self):  # type: ignore[no-untyped-def]
            raise RealBrowserControlRuntimeError("cloakbrowser_open_failed:Error")

        def close(self) -> None:
            self.close_count += 1

    engines: list[SearchReopenFailureEngine] = []

    def fake_factory() -> SearchReopenFailureEngine:
        engine = SearchReopenFailureEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        fake_factory,
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Browser body unavailable after bounded recovery; no further browser action attempted."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_search_reopen_recoverable",
        mission_objective="Search bounded product cards and recover if the browser session must be reopened.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=2,
        max_recoverable_action_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.blocked_reason is None
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "sentinel_loop:finish",
    )
    assert client.call_count == 2
    assert result.model_call_count == 2
    recovery = client.contexts[1]["recoverable_action_observations"][0]
    assert recovery["failure_code"] == "BODY_SESSION_UNAVAILABLE"
    assert recovery["recommended_skill"] == "finish"
    assert recovery["model_visible_body_failure_packet"]["failure_stage"] == "session_lifecycle"
    assert recovery["model_visible_body_failure_packet"]["session_continuity"]["root_lease_present"] is True
    assert len(engines) == 2
    assert sum(engine.close_count for engine in engines) >= 2


def test_product_loop_does_not_block_browser_visible_trade_or_processor_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class SearchActuationFailingCatalogEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
        def type_text(self, ref: str, text: str):  # type: ignore[no-untyped-def]
            del ref, text
            raise RealBrowserControlRuntimeError("locator_timeout")

        def _page_text(self) -> str:
            return "\n".join(
                [
                    "Processeur audio Processeur audio",
                    "Trade Assurance Logo",
                    "Trade Assurance Icon",
                ]
            )

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        SearchActuationFailingCatalogEngine,
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses sunglasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Visible browser evidence handled without unsafe-payload false positive."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_visible_text_false_positive",
        mission_objective="Search bounded product cards, extract visible cards, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        max_recoverable_action_failures=1,
    )

    assert "real_browser_control:real_browser.search" in result.capability_sequence
    assert "real_browser_control:real_browser.extract_product_cards" in result.capability_sequence
    assert result.blocked_reason != "mission_execution_request_parameters: unsafe operator payload"


def test_completed_browser_search_context_propagates_to_extract_when_live_session_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class CompletedSearchThenClosedSessionEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
        def extract_text(self):  # type: ignore[no-untyped-def]
            raise RealBrowserControlRuntimeError("browser_session_missing_or_closed")

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        CompletedSearchThenClosedSessionEngine,
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Verified browser extraction summarized and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_completed_search_context_to_extract",
        mission_objective="Search bounded product cards, extract visible cards, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.extract_product_cards",
        "real_browser_control:real_browser.verify_extraction",
        "sentinel_loop:summarize_evidence",
        "sentinel_loop:finish",
    )
    assert client.contexts[1]["browser_world_model"]["product_or_result_candidate_cards"]
    assert result.dispatch_results[1].safe_context_cards["browser_world_model_summary"][
        "context_world_model_extraction_source"
    ] == "existing_safe_browser_world_model"


def test_first_turn_extract_without_browser_context_routes_to_search_before_extract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        runtime_host_module._ProductLocalCloakBrowserEngine,
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Verified browser extraction summarized and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_first_turn_extract_routes_to_search",
        mission_objective="Search bounded product cards for glasses under 5 euro, extract, verify, summarize, and finish.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.extract_product_cards",
        "real_browser_control:real_browser.verify_extraction",
        "sentinel_loop:summarize_evidence",
        "sentinel_loop:finish",
    )
    assert result.dispatch_results[0].operation == "real_browser.search"
    assert result.dispatch_results[1].operation == "real_browser.extract_product_cards"


def test_browser_loop_context_is_not_scanned_as_action_payload(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={
                    "query": "glasses under 5 euro",
                    "engine_profile": "fake_product_search",
                },
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Browser extraction completed."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_context_not_action_payload",
        mission_objective=(
            "Search bounded product cards for glasses under 5 euro, extract visible cards, "
            "then finish. Do not login, contact supplier, enter credentials, pay, or checkout."
        ),
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=4,
        max_material_actions=2,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.extract_product_cards",
        "sentinel_loop:finish",
    )
    assert result.dispatch_results[1].operation == "real_browser.extract_product_cards"
    assert result.dispatch_results[1].blocked_reason is None


def test_browser_loop_context_cannot_override_trusted_runtime_identity(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={
                    "query": "glasses under 5 euro",
                    "engine_profile": "fake_product_search",
                    "loop_context": {
                        "adapter_id": "malicious_adapter",
                        "backend_id": "malicious_backend",
                        "mission_id": "malicious_mission",
                        "workspace_ref": "workspace:malicious",
                        "browser_world_model": {"safe_summary": "allowed model evidence"},
                    },
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Browser search completed."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_loop_context_trusted_identity",
        mission_objective="Model evidence context may not override trusted runtime identity.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    action_mission_id = result.dispatch_results[0].mission_id
    browser_receipt = _first_json(host.kernel.store.mission_dir(action_mission_id) / "real_browser_control" / "receipts")
    product_receipt = _product_receipt(host, action_mission_id, result.product_receipt_refs[0])

    assert browser_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"
    assert product_receipt["backend_id"] == "browser_skill"
    assert result.dispatch_results[0].mission_id != "malicious_mission"


def test_playwright_requires_explicit_compatibility_selection(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_playwright_block",
        mission_objective="Playwright compatibility cannot silently certify product browser power.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.search",
                    params={
                        "query": "glasses under 5 euro",
                        "engine_profile": "playwright_compat",
                    },
                )
            ]
        ),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=1,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "real_browser_playwright_compatibility_requires_explicit_selection"


def test_browser_direct_legacy_path_not_counted_as_product_proof(tmp_path: Path) -> None:
    kernel = hostless_kernel(tmp_path)
    mission_id = kernel.create_mission(
        session_id="session_pack4_direct_browser",
        draft=_draft(),
    ).mission_id
    runtime = RealBrowserControlRuntime(
        kernel=kernel,
        mission_id=mission_id,
        engine=InMemoryRealBrowserEngine(),
        selected_backend_id="inmemoryrealbrowser_engine",
    )
    authority = _browser_authority()

    result = runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=authority,
        context={},
    )

    receipt = _first_json(kernel.store.mission_dir(mission_id) / "real_browser_control" / "receipts")
    assert result.status == "completed"
    assert receipt.get("product_dispatch_owner") in (None, "")
    assert receipt.get("mission_workspace_ref") in (None, "")


def test_browser_replay_does_not_reopen_research_reextract(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_replay",
        mission_objective="Search browser product route and verify replay no-react.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_browser_replay_does_not_create_session_process_context(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_replay_no_live_body",
        mission_objective="Search browser product route and verify replay creates no live body.",
        decision_client=_browser_search_finish_client_without_engine_profile(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )
    factory_calls_after_run = len(engines)
    close_count_after_run = engines[0].close_count

    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert len(engines) == factory_calls_after_run
    assert engines[0].close_count == close_count_after_run


def test_local_body_stress_reuses_and_reopens_root_browser_lease(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    outcomes = []

    for index in range(3):
        client = ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.search",
                    params={"query": f"glasses under {5 + index} euro"},
                ),
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.open_result",
                    params={"ref": "link:result_1"},
                ),
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.extract_product_cards",
                ),
                ActionEnvelope(
                    capability_id="real_browser_control",
                    operation="real_browser.verify_extraction",
                ),
                ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Verified browser extraction summarized and finished."},
                ),
            ]
        )
        outcomes.append(
            host.run_product_action_kernel_task_loop(
                workspace_root=workspace,
                session_id=f"session_pack4_local_body_stress_{index}",
                mission_objective="Find bounded product cards under 5 EUR, open one result, extract visible evidence, verify, summarize, and finish.",
                decision_client=client,
                allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
                max_model_calls=7,
                max_material_actions=5,
            )
        )

    assert all(outcome.status is ProductActionKernelTaskLoopStatus.COMPLETED for outcome in outcomes)
    assert len(engines) == 3
    assert all(engine.close_count == 1 for engine in engines)
    assert all(engine.type_count == 1 for engine in engines)
    assert all(engine.extract_count >= 2 for engine in engines)


def test_browser_replay_hashes_large_artifacts_without_reparsing_json(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_replay_large_artifact",
        mission_objective="Search browser product route and verify replay no-react.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )
    mission_dir = host.kernel.store.mission_dir(result.mission_ids[0])
    large_artifact = mission_dir / "execution_request_parameters" / "large_world_model.json"
    large_artifact.parent.mkdir(parents=True, exist_ok=True)
    large_artifact.write_text(json.dumps({"cards": [{"title": "x" * 2000}] * 300}), encoding="utf-8")

    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_replay_from_host_serializes_for_live_reporting(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_replay_from_host",
        mission_objective="Search browser product route and render replay proof.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )

    replay = ProductActionKernelTaskLoopReplay.from_host(host, mission_ids=result.mission_ids)
    payload = replay.safe_model_dump()

    assert replay.reexecuted_actions is False
    assert payload["reexecuted_actions"] is False
    assert payload["receipt_writes_delta"] == 0
    assert json.loads(json.dumps(payload)) == payload


def test_cleanup_result_records_post_close_browser_lease_card(tmp_path: Path, monkeypatch) -> None:
    engines: list[_ClosableProductCloakEngine] = []

    def fake_factory() -> _ClosableProductCloakEngine:
        engine = _ClosableProductCloakEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "evidence", run_id="post_close_cleanup")

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_post_close_cleanup",
        mission_objective="Search once and finish with post-close cleanup evidence.",
        decision_client=_browser_search_finish_client_without_engine_profile(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
        evidence_sink=sink,
    )

    snapshot = sink.load_snapshot()
    cleanup_events = [event for event in snapshot["events"] if event["event_type"] == "cleanup_result"]
    cleanup_payload = cleanup_events[-1]["payload"]
    lease_card = cleanup_payload["browser_lease_card"]

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert engines[0].close_count == 1
    assert cleanup_payload["cleanup_completed"] is True
    assert lease_card["lifecycle_state"] == "closed"
    assert lease_card["close_count"] == 1
    assert lease_card["global_context_lock_acquired"] is False


def _browser_search_finish_client() -> ProductActionKernelLoopDecisionClient:
    return ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={
                    "query": "glasses under 5 euro",
                    "engine_profile": "fake_product_search",
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Browser search completed."},
            ),
        ]
    )


def _browser_search_finish_client_without_engine_profile() -> ProductActionKernelLoopDecisionClient:
    return ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Browser search completed."},
            ),
        ]
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 4 browser product backend\n", encoding="utf-8")
    return root


def _mission_workspace_manifest(host: SentinelRuntimeHost, mission_id: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "mission_workspace" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _handle(manifest: dict[str, object], kind: str) -> dict[str, object]:
    for handle in manifest["handles"]:
        if handle["kind"] == kind:
            return handle
    raise AssertionError(f"missing handle {kind}")


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    payload = load_product_action_kernel_artifact(host.kernel, mission_id, "receipts", receipt_ref)
    assert payload is not None
    return payload


def _first_json(directory: Path) -> dict[str, object]:
    files = sorted(directory.glob("*.json"))
    assert files
    return json.loads(files[0].read_text(encoding="utf-8"))


def hostless_kernel(tmp_path: Path):
    from sentinel.operator.kernel import MissionKernel

    return MissionKernel(run_root=tmp_path / "runs")


def _draft():
    from sentinel.operator.models import MissionDraft

    return MissionDraft(title="Direct browser compatibility", objective="Direct runtime path is not product proof.")


def _browser_authority() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="operator_user",
        mission_title="Browser compatibility authority",
        mission_objective="Open bounded fake browser.",
        allowed_tools=("real_browser_control",),
        allowed_actions=("real_browser.open", "real_browser_control.real_browser.open"),
        forbidden_actions=("payment", "credential_access", "browser_login", "contact_supplier"),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        allowed_paths=("workspace:fake",),
        max_actions=2,
    )
