from __future__ import annotations

from sentinel.operator.browser_product_cutover_registry import (
    BrowserProductPathClassification,
    build_default_browser_product_cutover_registry,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_pack0_classifies_product_browser_spine_and_cloak_backend() -> None:
    registry = build_default_browser_product_cutover_registry()

    product_spine = registry.require("real_browser_control_product_spine")
    cloak_backend = registry.require("cloak_session_backend")
    session_manager = registry.require("browser_session_manager_l5_live")

    assert product_spine.classification is BrowserProductPathClassification.PRODUCT_SPINE
    assert product_spine.product_model_visible is True
    assert product_spine.product_proof_allowed is True
    assert product_spine.consumed_by_browser_cortex is True
    assert product_spine.owner_module == "sentinel.operator.real_browser_control_runtime"

    assert cloak_backend.classification is BrowserProductPathClassification.HIDDEN_BACKEND
    assert cloak_backend.product_model_visible is False
    assert cloak_backend.product_proof_allowed is True
    assert cloak_backend.consumed_by_browser_cortex is True

    assert session_manager.classification is BrowserProductPathClassification.HIDDEN_BACKEND
    assert session_manager.backend_id == "cloak_browser"
    assert session_manager.consumed_by_browser_cortex is True


def test_pack0_playwright_is_quarantined_not_product_proof() -> None:
    registry = build_default_browser_product_cutover_registry()

    playwright_runtime = registry.require("playwright_real_browser_engine")
    playwright_renderer = registry.require("playwright_renderer")
    playwright_interaction = registry.require("playwright_interaction_backend")

    for path in (playwright_runtime, playwright_renderer, playwright_interaction):
        assert path.classification in {
            BrowserProductPathClassification.COMPATIBILITY_ONLY,
            BrowserProductPathClassification.DELETE_AFTER_PARITY,
        }
        assert path.product_model_visible is False
        assert path.product_proof_allowed is False
        assert path.silent_fallback_allowed is False
        assert "compatibility" in path.lock_reason.lower() or "parity" in path.lock_reason.lower()


def test_pack0_special_authority_browser_organs_locked_not_deleted() -> None:
    registry = build_default_browser_product_cutover_registry()

    locked_ids = {
        "browser_login_credential_session_broker",
        "browser_form_submit_special_authority",
        "browser_js_sandbox_special_authority",
        "browser_download_upload_quarantine",
        "browser_account_creation_special_authority",
        "browser_payment_spend_special_authority",
    }

    for path_id in locked_ids:
        path = registry.require(path_id)
        assert path.classification is BrowserProductPathClassification.SPECIAL_AUTHORITY_LOCKED
        assert path.product_model_visible is False
        assert path.product_proof_allowed is False
        assert path.hard_stop_categories
        assert path.delete_after_parity is False


def test_pack0_runtimehost_exposes_cutover_frame_without_granting_power(tmp_path) -> None:
    frame = SentinelRuntimeHost(run_root=tmp_path / "runs").product_task_loop_entrypoint_frame()

    cutover_frame = frame["browser_product_cutover_frame"]
    by_id = {item["path_id"]: item for item in cutover_frame["paths"]}

    assert cutover_frame["invariant"] == "browser_cutover_classification_is_map_not_authority"
    assert cutover_frame["can_execute"] is False
    assert cutover_frame["can_grant_authority"] is False

    assert by_id["real_browser_control_product_spine"]["classification"] == "PRODUCT_SPINE"
    assert by_id["real_browser_control_product_spine"]["product_model_visible"] is True
    assert by_id["cloak_session_backend"]["classification"] == "HIDDEN_BACKEND"
    assert by_id["playwright_real_browser_engine"]["classification"] == "COMPATIBILITY_ONLY"
    assert by_id["playwright_real_browser_engine"]["product_proof_allowed"] is False
    assert by_id["playwright_real_browser_engine"]["silent_fallback_allowed"] is False

    assert "playwright_real_browser_engine" not in frame["model_visible_skills"]
    assert "Playwright" not in " ".join(frame["model_visible_skills"])


def test_pack0_every_product_browser_path_has_migration_decision() -> None:
    registry = build_default_browser_product_cutover_registry()
    exported = registry.safe_export()

    assert exported
    assert all(item["classification"] for item in exported)
    assert all(item["migration_decision"] for item in exported)
    assert all(item["owner_module"] for item in exported)

    product_visible = [item for item in exported if item["product_model_visible"]]
    assert [item["path_id"] for item in product_visible] == ["real_browser_control_product_spine"]

    delete_later = [item for item in exported if item["delete_after_parity"]]
    assert {item["path_id"] for item in delete_later} >= {
        "playwright_renderer",
        "playwright_interaction_backend",
    }
