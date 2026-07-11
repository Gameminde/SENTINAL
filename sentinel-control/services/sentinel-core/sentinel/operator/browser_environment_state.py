from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.browser_world_model import BrowserWorldModel, BrowserWorldModelBuilder
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.operator.real_browser_control_runtime import RealBrowserEngineSnapshot


class BrowserBackendTruth(SentinelModel):
    selected_backend_id: str
    actual_backend_id: str
    session_backend_kind: str
    backend_mismatch: bool = False
    compatibility_only: bool = False
    product_backend_proven: bool = False


class BrowserPageStateGraph(SentinelModel):
    page_state_hash: str
    origin_hash: str
    page_kind_guess: str
    title_hash_or_safe_title: str
    visible_text_summary_hash: str
    stable_ref_count: int


class BrowserActionGraph(SentinelModel):
    accessibility_refs: tuple[dict[str, str], ...] = Field(default_factory=tuple)
    search_like_refs: tuple[str, ...] = Field(default_factory=tuple)
    form_controls: tuple[str, ...] = Field(default_factory=tuple)
    button_refs: tuple[str, ...] = Field(default_factory=tuple)
    link_refs: tuple[str, ...] = Field(default_factory=tuple)
    recommended_browser_actions: tuple[str, ...] = Field(default_factory=tuple)


class BrowserExtractionGraph(SentinelModel):
    product_or_result_candidate_count: int = 0
    relevant_product_candidate_count: int = 0
    cards: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class BrowserProtocolGraph(SentinelModel):
    network_event_count: int = 0
    console_event_count: int = 0
    network_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    console_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class BrowserSessionGraph(SentinelModel):
    cookie_count: int = 0
    storage_key_count: int = 0
    cookies: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    storage_keys: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    login_state: str = "unknown"
    profile_material_persisted: bool = False


class BrowserBlockerGraph(SentinelModel):
    modal_or_consent_signals: tuple[str, ...] = Field(default_factory=tuple)
    captcha_or_login_signals: tuple[str, ...] = Field(default_factory=tuple)
    dynamic_loading_signals: tuple[str, ...] = Field(default_factory=tuple)
    hard_boundary_signals: tuple[str, ...] = Field(default_factory=tuple)


class BrowserVisualGraph(SentinelModel):
    visual_refs_available: bool = False
    screenshot_ref_hash: str = ""
    screenshot_persisted: bool = False


class BrowserEnvironmentState(SentinelModel):
    state_id: str = Field(default_factory=lambda: new_id("browser_env_state"))
    backend_truth: BrowserBackendTruth
    page_state: BrowserPageStateGraph
    action_graph: BrowserActionGraph
    extraction_graph: BrowserExtractionGraph
    protocol_graph: BrowserProtocolGraph
    session_graph: BrowserSessionGraph
    blocker_graph: BrowserBlockerGraph
    visual_graph: BrowserVisualGraph
    world_model_summary: dict[str, Any]
    recommended_model_skills: tuple[str, ...] = Field(default_factory=tuple)
    raw_material_persisted: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _state_is_map_not_authority(self) -> "BrowserEnvironmentState":
        assert_data_not_authority(
            context="browser_environment_state",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.raw_material_persisted:
            raise ValueError("BrowserEnvironmentState cannot persist raw browser material.")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BrowserEnvironmentStateBuilder:
    def build(
        self,
        *,
        snapshot: "RealBrowserEngineSnapshot",
        mission_objective: str,
        origin_hash: str,
        selected_backend_id: str,
        actual_backend_id: str,
        session_backend_kind: str,
        extracted_text: str = "",
        network_events: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        console_messages: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        cookie_metadata: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        storage_metadata: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        screenshot_ref: str = "",
        world_model: BrowserWorldModel | None = None,
    ) -> BrowserEnvironmentState:
        model = world_model or BrowserWorldModelBuilder().build_from_snapshot(
            snapshot,
            mission_objective=mission_objective,
            origin_hash=origin_hash,
            extracted_text=extracted_text,
        )
        backend_truth = BrowserBackendTruth(
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            backend_mismatch=selected_backend_id != actual_backend_id,
            compatibility_only=actual_backend_id == "playwright_real_browser_engine",
            product_backend_proven=actual_backend_id == "cloak_browser",
        )
        return BrowserEnvironmentState(
            backend_truth=backend_truth,
            page_state=BrowserPageStateGraph(
                page_state_hash=snapshot.state_hash,
                origin_hash=origin_hash,
                page_kind_guess=model.page_kind_guess,
                title_hash_or_safe_title=model.title_hash_or_safe_title,
                visible_text_summary_hash=model.visible_text_summary_hash,
                stable_ref_count=len(model.stable_refs),
            ),
            action_graph=BrowserActionGraph(
                accessibility_refs=tuple(_safe_accessibility_ref(card) for card in model.stable_refs),
                search_like_refs=model.search_like_refs,
                form_controls=model.form_controls,
                button_refs=model.button_refs,
                link_refs=model.link_refs,
                recommended_browser_actions=model.recommended_browser_actions,
            ),
            extraction_graph=BrowserExtractionGraph(
                product_or_result_candidate_count=len(model.product_or_result_candidate_cards),
                relevant_product_candidate_count=sum(
                    1
                    for card in model.product_or_result_candidate_cards
                    if card.relevance_to_objective in {"relevant", "partial"}
                ),
                cards=tuple(_safe_card(card) for card in model.product_or_result_candidate_cards),
            ),
            protocol_graph=BrowserProtocolGraph(
                network_event_count=len(network_events),
                console_event_count=len(console_messages),
                network_events=tuple(_safe_network_event(event) for event in network_events[:20]),
                console_events=tuple(_safe_console_event(event) for event in console_messages[:20]),
            ),
            session_graph=BrowserSessionGraph(
                cookie_count=len(cookie_metadata),
                storage_key_count=len(storage_metadata),
                cookies=tuple(_safe_cookie_meta(item) for item in cookie_metadata[:20]),
                storage_keys=tuple(_safe_storage_meta(item) for item in storage_metadata[:20]),
                login_state=_login_state(model),
                profile_material_persisted=False,
            ),
            blocker_graph=BrowserBlockerGraph(
                modal_or_consent_signals=model.modal_or_consent_signals,
                captcha_or_login_signals=model.captcha_or_login_signals,
                dynamic_loading_signals=model.dynamic_loading_signals,
                hard_boundary_signals=_hard_boundary_signals(model),
            ),
            visual_graph=BrowserVisualGraph(
                visual_refs_available=bool(screenshot_ref),
                screenshot_ref_hash=text_hash(screenshot_ref) if screenshot_ref else "",
                screenshot_persisted=False,
            ),
            world_model_summary=model.compact_summary(),
            recommended_model_skills=_recommended_model_skills(model),
        )


def browser_environment_state_contract() -> dict[str, Any]:
    return {
        "contract_id": "browser_environment_state_graph_v1",
        "consumes_backend": "cloak_browser",
        "state_sections": [
            "backend_truth",
            "page_state",
            "accessibility_refs",
            "action_candidates",
            "extraction_cards",
            "network_console_metadata",
            "cookie_storage_metadata",
            "session_state",
            "blockers",
            "visual_fallback_refs",
        ],
        "raw_cookie_values_exposed": False,
        "raw_storage_values_exposed": False,
        "raw_dom_exposed": False,
        "raw_screenshots_exposed": False,
        "provider_reasoning_exposed": False,
        "action_envelope_language": "internal_runtime_only",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def _safe_accessibility_ref(card: Any) -> dict[str, str]:
    return {
        "ref": str(card.ref),
        "role": str(card.role),
        "name": _safe_text(str(card.name)),
        "text_preview": _safe_text(str(card.text_preview)),
        "value_preview": _safe_text(str(card.value_preview)),
    }


def _safe_card(card: Any) -> dict[str, Any]:
    return {
        "card_id": str(card.card_id),
        "kind": str(card.kind),
        "title": _safe_text(str(card.title)),
        "visible_price": _safe_text(str(card.visible_price)),
        "currency_or_unit": _safe_text(str(card.currency_or_unit)),
        "minimum_order": _safe_text(str(card.minimum_order)),
        "supplier_or_store": _safe_text(str(card.supplier_or_store)),
        "relevance_to_objective": str(card.relevance_to_objective),
        "price_condition_supported": str(card.price_condition_supported),
        "evidence_ref_hash": str(card.evidence_ref_hash),
        "confidence": float(card.confidence),
    }


def _safe_network_event(event: dict[str, Any]) -> dict[str, Any]:
    host = str(event.get("url_host") or event.get("host") or "")
    raw_url = str(event.get("url") or "")
    return {
        "host_hash": text_hash(host or _url_host_hint(raw_url)),
        "method": _safe_text(str(event.get("method") or "unknown"), 16),
        "resource_type": _safe_text(str(event.get("resource_type") or "unknown"), 32),
        "status": int(event.get("status") or 0),
    }


def _safe_console_event(event: dict[str, Any]) -> dict[str, Any]:
    text = str(event.get("text") or event.get("message") or "")
    return {
        "type": _safe_text(str(event.get("type") or "unknown"), 24),
        "text_hash": text_hash(text),
    }


def _safe_cookie_meta(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name_hash": text_hash(str(item.get("name") or "")),
        "domain_hash": text_hash(str(item.get("domain") or "")),
        "http_only": bool(item.get("httpOnly") or item.get("http_only")),
        "secure": bool(item.get("secure")),
        "same_site": _safe_text(str(item.get("sameSite") or item.get("same_site") or "unknown"), 24),
        "expiry_known": bool(item.get("expires") or item.get("expiry")),
    }


def _safe_storage_meta(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "storage_type": _safe_text(str(item.get("type") or "unknown"), 32),
        "origin_hash": text_hash(str(item.get("origin") or "")),
        "key_hash": text_hash(str(item.get("key") or "")),
        "size_hint": int(item.get("size") or item.get("size_hint") or 0),
    }


def _login_state(model: BrowserWorldModel) -> str:
    return "login_or_verification_visible" if model.captcha_or_login_signals else "unknown"


def _hard_boundary_signals(model: BrowserWorldModel) -> tuple[str, ...]:
    signals: list[str] = []
    text = " ".join([*model.captcha_or_login_signals, *model.modal_or_consent_signals]).lower()
    for marker, boundary in {
        "login": "login_or_account_boundary",
        "sign in": "login_or_account_boundary",
        "captcha": "human_verification_boundary",
        "cookie": "consent_or_cookie_boundary",
    }.items():
        if marker in text:
            signals.append(boundary)
    return tuple(dict.fromkeys(signals))


def _recommended_model_skills(model: BrowserWorldModel) -> tuple[str, ...]:
    skills: list[str] = []
    if model.search_like_refs or "real_browser.search" in model.recommended_browser_actions:
        skills.append("browse_search")
    if model.product_or_result_candidate_cards or "real_browser.extract_product_cards" in model.recommended_browser_actions:
        skills.append("extract")
    if model.captcha_or_login_signals:
        skills.append("recover")
    return tuple(dict.fromkeys(skills or ["browse_search"]))


def _url_host_hint(raw_url: str) -> str:
    if "://" not in raw_url:
        return raw_url[:80]
    return raw_url.split("://", 1)[1].split("/", 1)[0]


def _safe_text(value: str, limit: int = 120) -> str:
    value = " ".join(value.split())
    lowered = value.lower()
    if any(marker in lowered for marker in ("authorization", "bearer", "cookie", "password", "secret", "token", "session")):
        return f"redacted_hash:{text_hash(value)}"
    if "<html" in lowered or "<body" in lowered:
        return f"redacted_html_hash:{text_hash(value)}"
    return value[:limit]


__all__ = [
    "BrowserActionGraph",
    "BrowserBackendTruth",
    "BrowserBlockerGraph",
    "BrowserEnvironmentState",
    "BrowserEnvironmentStateBuilder",
    "BrowserExtractionGraph",
    "BrowserPageStateGraph",
    "BrowserProtocolGraph",
    "BrowserSessionGraph",
    "BrowserVisualGraph",
    "browser_environment_state_contract",
]
