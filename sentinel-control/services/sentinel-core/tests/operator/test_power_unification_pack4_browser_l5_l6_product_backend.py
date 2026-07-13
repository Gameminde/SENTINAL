from __future__ import annotations

import json
from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
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


def test_cloak_selected_as_product_backend_when_available(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_cloak_backend_truth",
        mission_objective="Search through the product-leading Cloak/session fake backend.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example",),
        max_model_calls=3,
        max_material_actions=1,
    )

    browser_receipt = _first_json(host.kernel.store.mission_dir(result.dispatch_results[0].mission_id) / "real_browser_control" / "receipts")
    assert browser_receipt["selected_backend_id"] == "cloak_browser"
    assert browser_receipt["actual_backend_id"] == "cloak_browser"
    assert browser_receipt["session_backend_kind"] == "cloakbrowser"
    assert browser_receipt["backend_mismatch"] is False


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
        allowed_domains=("bounded.example",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert calls == [True]


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
        allowed_domains=("bounded.example",),
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
    assert client.contexts[1]["recoverable_action_observations"][0]["failure_code"] == "real_browser_search_actuation_failed"
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
        allowed_domains=("bounded.example",),
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


def test_product_loop_recovers_browser_search_session_open_failure(tmp_path: Path, monkeypatch) -> None:
    class SearchReopenFailureEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
        def observe(self):  # type: ignore[no-untyped-def]
            raise RealBrowserControlRuntimeError("browser_session_missing_or_closed")

        def open(self):  # type: ignore[no-untyped-def]
            raise RealBrowserControlRuntimeError("cloakbrowser_open_failed:Error")

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://bounded.example/")
    monkeypatch.setattr(
        runtime_host_module,
        "build_cloak_first_real_browser_engine_from_env",
        SearchReopenFailureEngine,
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
                operation="real_browser.search",
                params={"query": "sunglasses under 5 euro"},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_search_reopen_recoverable",
        mission_objective="Search bounded product cards and recover if the browser session must be reopened.",
        decision_client=client,
        allowed_domains=("bounded.example",),
        max_model_calls=3,
        max_material_actions=2,
        max_recoverable_action_failures=1,
    )

    assert result.capability_sequence == (
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.search",
    )
    assert client.contexts[1]["recoverable_action_observations"][0]["failure_code"] == "real_browser_search_session_open_failed"


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
        allowed_domains=("bounded.example",),
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
        allowed_domains=("bounded.example",),
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


def test_first_turn_extract_without_browser_context_routes_to_search_before_extract(tmp_path: Path) -> None:
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
        allowed_domains=("bounded.example",),
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
        allowed_domains=("bounded.example",),
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
        allowed_domains=("bounded.example",),
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
        allowed_domains=("bounded.example",),
        max_model_calls=3,
        max_material_actions=1,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_browser_replay_hashes_large_artifacts_without_reparsing_json(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack4_browser_replay_large_artifact",
        mission_objective="Search browser product route and verify replay no-react.",
        decision_client=_browser_search_finish_client(),
        allowed_domains=("bounded.example",),
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
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))


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
