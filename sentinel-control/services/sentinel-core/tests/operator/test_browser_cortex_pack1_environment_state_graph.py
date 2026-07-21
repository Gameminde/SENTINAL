from __future__ import annotations

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.browser_environment_state import BrowserEnvironmentStateBuilder
from sentinel.operator.real_browser_control_runtime import RealBrowserEngineElement, RealBrowserEngineSnapshot
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_environment_state_graph_fuses_world_model_refs_and_product_cards() -> None:
    snapshot = _snapshot()

    state = BrowserEnvironmentStateBuilder().build(
        snapshot=snapshot,
        mission_objective="Find glasses under 5 EUR and summarize relevant products.",
        origin_hash=stable_hash("https://bounded.example/catalog"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        extracted_text=(
            "Blue light glasses visible price 4.80 EUR per unit MOQ 10 Supplier VisionCraft. "
            "TR90 sunglasses visible price 3.90 EUR per unit MOQ 20 Supplier SunWorks."
        ),
    )

    assert state.backend_truth.selected_backend_id == "cloak_browser"
    assert state.backend_truth.actual_backend_id == "cloak_browser"
    assert state.backend_truth.product_backend_proven is True
    assert state.page_state.page_kind_guess in {"search_results", "product_listing"}
    assert "input:search" in state.action_graph.search_like_refs
    assert "link:result_1" in state.action_graph.link_refs
    assert state.extraction_graph.product_or_result_candidate_count >= 1
    assert state.extraction_graph.relevant_product_candidate_count >= 1
    assert "browse_search" in state.recommended_model_skills
    assert "extract" in state.recommended_model_skills
    assert state.raw_material_persisted is False
    assert state.can_execute is False
    tabs = state.state_fields["tabs_and_frames"]["value"]
    assert tabs["known_active_page_count"] == 1
    assert tabs["tab_count"] == "unknown"
    assert tabs["frame_count"] == "unknown"
    structured = state.state_fields["structured_data"]["value"]
    assert structured["available"] is False
    assert structured["visible_candidate_cards_available"] is True
    assert structured["structured_data_source"] == "not_observed"


def test_environment_state_backend_truth_requires_full_cloak_match() -> None:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=_snapshot(),
        mission_objective="Research public docs.",
        origin_hash=stable_hash("https://bounded.example/docs"),
        selected_backend_id="playwright_real_browser_engine",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
    )

    assert state.backend_truth.backend_mismatch is True
    assert state.backend_truth.product_backend_proven is False


def test_environment_state_graph_summarizes_network_console_cookie_storage_without_values() -> None:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=_snapshot(),
        mission_objective="Research glasses.",
        origin_hash=stable_hash("https://bounded.example/catalog"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        network_events=[
            {"url_host": "www.alibaba.com", "method": "GET", "resource_type": "document", "status": 200},
            {"url": "https://leaky.example/path?token=secret", "method": "POST", "status": 403},
        ],
        console_messages=[{"type": "warning", "text": "blocked mixed-content token abc123"}],
        cookie_metadata=[
            {
                "name": "x-session",
                "value": "raw-cookie-value-must-not-leak",
                "domain": ".example.test",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
                "expires": 1919191919,
            }
        ],
        storage_metadata=[
            {
                "type": "localStorage",
                "origin": "https://bounded.example",
                "key": "cart_state",
                "value": "raw-storage-value-must-not-leak",
                "size": 128,
            }
        ],
    )

    dumped = state.safe_model_dump()
    serialized = str(dumped)

    assert state.protocol_graph.network_event_count == 2
    assert state.protocol_graph.console_event_count == 1
    assert state.session_graph.cookie_count == 1
    assert state.session_graph.storage_key_count == 1
    assert "raw-cookie-value-must-not-leak" not in serialized
    assert "raw-storage-value-must-not-leak" not in serialized
    assert "token=secret" not in serialized
    assert "blocked mixed-content token abc123" not in serialized
    assert "cookie_value" not in serialized
    assert "session_token" not in serialized


def test_environment_state_graph_detects_blockers_without_raw_dom_or_screenshots() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Human verification",
        state_hash=stable_hash("blocked"),
        elements=(
            RealBrowserEngineElement(
                ref="text:captcha",
                role="generic",
                name="Verify you are human captcha",
                text_preview="Please verify you are human",
            ),
            RealBrowserEngineElement(
                ref="button:login",
                role="button",
                name="Sign in",
                text_preview="Sign in",
            ),
        ),
    )

    state = BrowserEnvironmentStateBuilder().build(
        snapshot=snapshot,
        mission_objective="Search a product catalog.",
        origin_hash=stable_hash("https://bounded.example/captcha"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        extracted_text="<html><body>raw DOM should never appear</body></html>",
        screenshot_ref="C:/tmp/raw-screenshot.png",
    )

    dumped = state.safe_model_dump()
    serialized = str(dumped)

    assert state.blocker_graph.captcha_or_login_signals
    assert state.blocker_graph.hard_boundary_signals
    assert "raw DOM should never appear" not in serialized
    assert "raw-screenshot.png" not in serialized
    assert state.visual_graph.screenshot_persisted is False


def test_runtimehost_exposes_browser_environment_state_contract(tmp_path) -> None:
    frame = SentinelRuntimeHost(run_root=tmp_path / "runs").product_task_loop_entrypoint_frame()

    contract = frame["browser_environment_state_contract"]

    assert contract["contract_id"] == "browser_environment_state_graph_v1"
    assert contract["consumes_backend"] == "cloak_browser"
    assert contract["raw_cookie_values_exposed"] is False
    assert contract["raw_storage_values_exposed"] is False
    assert contract["raw_dom_exposed"] is False
    assert contract["raw_screenshots_exposed"] is False
    assert "accessibility_refs" in contract["state_sections"]
    assert "network_console_metadata" in contract["state_sections"]
    assert "cookie_storage_metadata" in contract["state_sections"]


def _snapshot() -> RealBrowserEngineSnapshot:
    return RealBrowserEngineSnapshot(
        page_title="Sentinel Browser Fixture",
        state_hash=stable_hash("browser-state"),
        elements=(
            RealBrowserEngineElement(
                ref="input:search",
                role="searchbox",
                name="Search products",
                text_preview="Search products",
            ),
            RealBrowserEngineElement(
                ref="button:search",
                role="button",
                name="Search",
                text_preview="Search",
            ),
            RealBrowserEngineElement(
                ref="link:result_1",
                role="link",
                name="Blue light glasses 4.80 EUR MOQ 10",
                text_preview="Blue light glasses visible price 4.80 EUR per unit MOQ 10 Supplier VisionCraft",
            ),
        ),
    )
