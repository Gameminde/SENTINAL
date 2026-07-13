from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class BrowserProductPathClassification(StrEnum):
    PRODUCT_SPINE = "PRODUCT_SPINE"
    HIDDEN_BACKEND = "HIDDEN_BACKEND"
    COMPATIBILITY_ONLY = "COMPATIBILITY_ONLY"
    DEPRECATED = "DEPRECATED"
    SPECIAL_AUTHORITY_LOCKED = "SPECIAL_AUTHORITY_LOCKED"
    DELETE_AFTER_PARITY = "DELETE_AFTER_PARITY"


class BrowserProductCutoverPath(SentinelModel):
    path_id: str
    display_name: str
    owner_module: str
    owner_symbol: str | None = None
    classification: BrowserProductPathClassification
    migration_decision: str
    backend_id: str | None = None
    product_model_visible: bool = False
    product_proof_allowed: bool = False
    consumed_by_browser_cortex: bool = False
    executable_trace_proof: str = ""
    silent_fallback_allowed: bool = False
    delete_after_parity: bool = False
    lock_reason: str = ""
    hard_stop_categories: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _path_is_cutover_truth_not_power(self) -> "BrowserProductCutoverPath":
        assert_data_not_authority(
            context="browser_product_cutover_path",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.product_model_visible and self.classification is not BrowserProductPathClassification.PRODUCT_SPINE:
            raise ValueError("Only the product spine may be model visible.")
        if self.product_proof_allowed and self.classification in {
            BrowserProductPathClassification.COMPATIBILITY_ONLY,
            BrowserProductPathClassification.DEPRECATED,
            BrowserProductPathClassification.SPECIAL_AUTHORITY_LOCKED,
            BrowserProductPathClassification.DELETE_AFTER_PARITY,
        }:
            raise ValueError("Compatibility, deprecated, locked, and delete-after-parity paths cannot prove product power.")
        if self.classification in {
            BrowserProductPathClassification.COMPATIBILITY_ONLY,
            BrowserProductPathClassification.DEPRECATED,
            BrowserProductPathClassification.SPECIAL_AUTHORITY_LOCKED,
            BrowserProductPathClassification.DELETE_AFTER_PARITY,
        } and not self.lock_reason:
            raise ValueError("Non-product browser paths must explain the lock or migration reason.")
        if self.classification is BrowserProductPathClassification.SPECIAL_AUTHORITY_LOCKED and not self.hard_stop_categories:
            raise ValueError("Special authority browser paths must name hard stop categories.")
        if self.delete_after_parity and self.classification is not BrowserProductPathClassification.DELETE_AFTER_PARITY:
            raise ValueError("delete_after_parity is reserved for DELETE_AFTER_PARITY paths.")
        return self

    def safe_export(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BrowserProductCutoverFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("browser_product_cutover_frame"))
    paths: tuple[BrowserProductCutoverPath, ...] = Field(default_factory=tuple)
    registry_truth_mismatch_count: int = 0
    invariant: str = "browser_cutover_classification_is_map_not_authority"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _frame_is_cutover_truth_not_power(self) -> "BrowserProductCutoverFrame":
        mismatch_count = sum(
            1
            for path in self.paths
            if path.consumed_by_browser_cortex and not path.executable_trace_proof
        )
        object.__setattr__(self, "registry_truth_mismatch_count", mismatch_count)
        assert_data_not_authority(
            context="browser_product_cutover_frame",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        visible = [path for path in self.paths if path.product_model_visible]
        if [path.path_id for path in visible] != ["real_browser_control_product_spine"]:
            raise ValueError("The real browser product spine must be the only model-visible browser path.")
        if any(path.silent_fallback_allowed for path in self.paths):
            raise ValueError("Browser product cutover forbids silent fallback paths.")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BrowserProductCutoverRegistry(SentinelModel):
    paths: tuple[BrowserProductCutoverPath, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "BrowserProductCutoverRegistry":
        ids = [path.path_id for path in self.paths]
        if len(ids) != len(set(ids)):
            raise ValueError("BrowserProductCutoverRegistry cannot contain duplicate path ids.")
        return self

    def require(self, path_id: str) -> BrowserProductCutoverPath:
        for path in self.paths:
            if path.path_id == path_id:
                return path
        raise KeyError(f"Unknown browser product cutover path `{path_id}`.")

    def compile_frame(self) -> BrowserProductCutoverFrame:
        return BrowserProductCutoverFrame(paths=self.paths)

    def safe_export(self) -> list[dict[str, Any]]:
        return [path.safe_export() for path in self.paths]


def build_default_browser_product_cutover_registry() -> BrowserProductCutoverRegistry:
    return BrowserProductCutoverRegistry(
        paths=(
            _path(
                "real_browser_control_product_spine",
                display_name="Real browser skill product spine",
                owner_module="sentinel.operator.real_browser_control_runtime",
                owner_symbol="RealBrowserControlRuntime",
                classification=BrowserProductPathClassification.PRODUCT_SPINE,
                migration_decision="sole_product_browser_spine",
                backend_id="browser_skill",
                product_model_visible=True,
                product_proof_allowed=True,
                consumed_by_browser_cortex=True,
                executable_trace_proof="runtimehost_product_action_kernel_real_browser_control",
            ),
            _path(
                "browser_session_manager_l5_live",
                display_name="BrowserSessionManager L5 live session backend",
                owner_module="sentinel.agent.organs.browser_session_manager_l5_live",
                owner_symbol="BrowserSessionManagerL5Live",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="hidden_backend_consumed_by_browser_cortex",
                backend_id="cloak_browser",
                product_proof_allowed=True,
                consumed_by_browser_cortex=True,
                executable_trace_proof="browser_session_manager_real_browser_engine",
            ),
            _path(
                "cloak_session_backend",
                display_name="CloakBrowser live session backend",
                owner_module="sentinel.organs.browser.cloak_backend",
                owner_symbol="CloakBrowserSessionBackend",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="product_leading_backend_below_browser_cortex",
                backend_id="cloak_browser",
                product_proof_allowed=True,
                consumed_by_browser_cortex=True,
                executable_trace_proof="browser_session_manager_l5_cloak_backend",
            ),
            _path(
                "browser_world_model_builder",
                display_name="Browser world model builder",
                owner_module="sentinel.operator.browser_world_model",
                owner_symbol="BrowserWorldModelBuilder",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="cortex_state_graph_component",
                consumed_by_browser_cortex=True,
                executable_trace_proof="real_browser_control_world_context_cards",
            ),
            _path(
                "browser_model_native_control_loop",
                display_name="Browser model-native intent mapper",
                owner_module="sentinel.operator.browser_model_native_control_loop",
                owner_symbol="map_browser_model_native_intent",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="intent_to_internal_action_mapper",
                consumed_by_browser_cortex=True,
                executable_trace_proof="product_model_native_decision_client",
            ),
            _path(
                "browser_devtools_machine_intelligence",
                display_name="Browser DevTools machine intelligence organ",
                owner_module="sentinel.agent.organs.browser_devtools_machine_intelligence_v1",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="feed_safe_cdp_bidi_devtools_metadata_into_cortex",
                consumed_by_browser_cortex=True,
                executable_trace_proof="browser_observation_bundle",
            ),
            _path(
                "browser_failure_recovery_engine",
                display_name="Browser failure recovery organ",
                owner_module="sentinel.agent.organs.browser_failure_recovery_engine_v1",
                classification=BrowserProductPathClassification.HIDDEN_BACKEND,
                migration_decision="recover_in_scope_browser_failures_below_model",
                consumed_by_browser_cortex=True,
                executable_trace_proof="browser_recovery_evidence",
            ),
            _path(
                "playwright_real_browser_engine",
                display_name="Playwright real browser engine",
                owner_module="sentinel.operator.real_browser_control_runtime",
                owner_symbol="PlaywrightRealBrowserEngine",
                classification=BrowserProductPathClassification.COMPATIBILITY_ONLY,
                migration_decision="quarantine_as_explicit_compatibility_backend",
                backend_id="playwright_real_browser_engine",
                lock_reason="Playwright is compatibility/test only and cannot certify product browser power.",
            ),
            _path(
                "playwright_renderer",
                display_name="Playwright renderer",
                owner_module="sentinel.organs.browser.playwright_renderer",
                classification=BrowserProductPathClassification.DELETE_AFTER_PARITY,
                migration_decision="delete_after_cloak_cortex_rendering_parity",
                delete_after_parity=True,
                lock_reason="Historical Playwright renderer remains only until Cloak/Cortex parity is proven.",
            ),
            _path(
                "playwright_interaction_backend",
                display_name="Playwright interaction backend",
                owner_module="sentinel.organs.browser.playwright_interaction_backend",
                classification=BrowserProductPathClassification.DELETE_AFTER_PARITY,
                migration_decision="delete_after_cloak_cortex_actuation_parity",
                delete_after_parity=True,
                lock_reason="Historical Playwright interaction backend remains only until Cloak/Cortex parity is proven.",
            ),
            _special_authority(
                "browser_login_credential_session_broker",
                display_name="Browser login credential session broker",
                owner_module="sentinel.agent.organs.browser_login_credential_session_broker_l6",
                hard_stop_categories=("credential_access", "login_session", "account_mutation"),
            ),
            _special_authority(
                "browser_form_submit_special_authority",
                display_name="Browser form submit special authority",
                owner_module="sentinel.agent.organs.browser_form_submit_special_authority_l6",
                hard_stop_categories=("external_send", "form_submit", "personal_data"),
            ),
            _special_authority(
                "browser_js_sandbox_special_authority",
                display_name="Browser JavaScript sandbox special authority",
                owner_module="sentinel.agent.organs.browser_js_sandbox_special_authority_l6",
                hard_stop_categories=("javascript_execution", "page_mutation"),
            ),
            _special_authority(
                "browser_download_upload_quarantine",
                display_name="Browser download/upload quarantine authority",
                owner_module="sentinel.agent.organs.browser_download_upload_quarantine_l6",
                hard_stop_categories=("file_upload", "file_download", "external_file_transfer"),
            ),
            _special_authority(
                "browser_account_creation_special_authority",
                display_name="Browser account creation special authority",
                owner_module="sentinel.agent.organs.browser_account_creation_special_authority_l7",
                hard_stop_categories=("account_creation", "identity_mutation", "credential_access"),
            ),
            _special_authority(
                "browser_payment_spend_special_authority",
                display_name="Browser payment/spend special authority",
                owner_module="sentinel.agent.organs.browser_payment_spend_special_authority_l7",
                hard_stop_categories=("payment", "checkout", "spend"),
            ),
        )
    )


def _special_authority(
    path_id: str,
    *,
    display_name: str,
    owner_module: str,
    hard_stop_categories: tuple[str, ...],
) -> BrowserProductCutoverPath:
    return _path(
        path_id,
        display_name=display_name,
        owner_module=owner_module,
        classification=BrowserProductPathClassification.SPECIAL_AUTHORITY_LOCKED,
        migration_decision="keep_locked_until_explicit_special_authority_pack",
        lock_reason="Special authority browser power is not part of the default product browser cortex.",
        hard_stop_categories=hard_stop_categories,
    )


def _path(
    path_id: str,
    *,
    display_name: str,
    owner_module: str,
    classification: BrowserProductPathClassification,
    migration_decision: str,
    owner_symbol: str | None = None,
    backend_id: str | None = None,
    product_model_visible: bool = False,
    product_proof_allowed: bool = False,
    consumed_by_browser_cortex: bool = False,
    executable_trace_proof: str = "",
    silent_fallback_allowed: bool = False,
    delete_after_parity: bool = False,
    lock_reason: str = "",
    hard_stop_categories: tuple[str, ...] = (),
) -> BrowserProductCutoverPath:
    return BrowserProductCutoverPath(
        path_id=path_id,
        display_name=display_name,
        owner_module=owner_module,
        owner_symbol=owner_symbol,
        classification=classification,
        migration_decision=migration_decision,
        backend_id=backend_id,
        product_model_visible=product_model_visible,
        product_proof_allowed=product_proof_allowed,
        consumed_by_browser_cortex=consumed_by_browser_cortex,
        executable_trace_proof=executable_trace_proof,
        silent_fallback_allowed=silent_fallback_allowed,
        delete_after_parity=delete_after_parity,
        lock_reason=lock_reason,
        hard_stop_categories=hard_stop_categories,
    )


__all__ = [
    "BrowserProductCutoverFrame",
    "BrowserProductCutoverPath",
    "BrowserProductCutoverRegistry",
    "BrowserProductPathClassification",
    "build_default_browser_product_cutover_registry",
]
