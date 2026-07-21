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
    schema_version: str = "browser_environment_state_v1"
    state_id: str = Field(default_factory=lambda: new_id("browser_env_state"))
    cognitive_graph_ready: bool = True
    backend_truth: BrowserBackendTruth
    page_state: BrowserPageStateGraph
    action_graph: BrowserActionGraph
    extraction_graph: BrowserExtractionGraph
    protocol_graph: BrowserProtocolGraph
    session_graph: BrowserSessionGraph
    blocker_graph: BrowserBlockerGraph
    visual_graph: BrowserVisualGraph
    state_fields: dict[str, dict[str, Any]] = Field(default_factory=dict)
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
            product_backend_proven=(
                selected_backend_id == "cloak_browser"
                and actual_backend_id == "cloak_browser"
                and session_backend_kind in {"cloakbrowser", "cloak_browser"}
            ),
        )
        page_state = BrowserPageStateGraph(
            page_state_hash=snapshot.state_hash,
            origin_hash=origin_hash,
            page_kind_guess=model.page_kind_guess,
            title_hash_or_safe_title=model.title_hash_or_safe_title,
            visible_text_summary_hash=model.visible_text_summary_hash,
            stable_ref_count=len(model.stable_refs),
        )
        action_graph = BrowserActionGraph(
            accessibility_refs=tuple(_safe_accessibility_ref(card) for card in model.stable_refs),
            search_like_refs=model.search_like_refs,
            form_controls=model.form_controls,
            button_refs=model.button_refs,
            link_refs=model.link_refs,
            recommended_browser_actions=model.recommended_browser_actions,
        )
        extraction_graph = BrowserExtractionGraph(
            product_or_result_candidate_count=len(model.product_or_result_candidate_cards),
            relevant_product_candidate_count=sum(
                1
                for card in model.product_or_result_candidate_cards
                if card.kind == "product_candidate" and card.relevance_to_objective in {"relevant", "partial"}
            ),
            cards=tuple(_safe_card(card) for card in model.product_or_result_candidate_cards),
        )
        protocol_graph = BrowserProtocolGraph(
            network_event_count=len(network_events),
            console_event_count=len(console_messages),
            network_events=tuple(_safe_network_event(event) for event in network_events[:20]),
            console_events=tuple(_safe_console_event(event) for event in console_messages[:20]),
        )
        session_graph = BrowserSessionGraph(
            cookie_count=len(cookie_metadata),
            storage_key_count=len(storage_metadata),
            cookies=tuple(_safe_cookie_meta(item) for item in cookie_metadata[:20]),
            storage_keys=tuple(_safe_storage_meta(item) for item in storage_metadata[:20]),
            login_state=_login_state(model),
            profile_material_persisted=False,
        )
        blocker_graph = BrowserBlockerGraph(
            modal_or_consent_signals=model.modal_or_consent_signals,
            captcha_or_login_signals=model.captcha_or_login_signals,
            dynamic_loading_signals=model.dynamic_loading_signals,
            hard_boundary_signals=_hard_boundary_signals(model),
        )
        visual_graph = BrowserVisualGraph(
            visual_refs_available=bool(screenshot_ref),
            screenshot_ref_hash=text_hash(screenshot_ref) if screenshot_ref else "",
            screenshot_persisted=False,
        )
        recommended_model_skills = _recommended_model_skills(model)
        return BrowserEnvironmentState(
            backend_truth=backend_truth,
            page_state=page_state,
            action_graph=action_graph,
            extraction_graph=extraction_graph,
            protocol_graph=protocol_graph,
            session_graph=session_graph,
            blocker_graph=blocker_graph,
            visual_graph=visual_graph,
            state_fields=_browser_cognitive_state_fields(
                backend_truth=backend_truth,
                page_state=page_state,
                action_graph=action_graph,
                extraction_graph=extraction_graph,
                protocol_graph=protocol_graph,
                session_graph=session_graph,
                blocker_graph=blocker_graph,
                visual_graph=visual_graph,
                recommended_model_skills=recommended_model_skills,
                model=model,
            ),
            world_model_summary=model.compact_summary(),
            recommended_model_skills=recommended_model_skills,
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


def _browser_cognitive_state_fields(
    *,
    backend_truth: BrowserBackendTruth,
    page_state: BrowserPageStateGraph,
    action_graph: BrowserActionGraph,
    extraction_graph: BrowserExtractionGraph,
    protocol_graph: BrowserProtocolGraph,
    session_graph: BrowserSessionGraph,
    blocker_graph: BrowserBlockerGraph,
    visual_graph: BrowserVisualGraph,
    recommended_model_skills: tuple[str, ...],
    model: BrowserWorldModel,
) -> dict[str, dict[str, Any]]:
    page_evidence = (
        f"state:{page_state.page_state_hash}",
        f"origin:{page_state.origin_hash}",
        f"visible_text:{page_state.visible_text_summary_hash}",
    )
    ref_evidence = tuple(f"ref:{stable_hash(ref)}" for ref in action_graph.search_like_refs[:8]) or page_evidence[:1]
    card_evidence = tuple(
        str(card.get("evidence_ref_hash") or f"card:{stable_hash(card)}")
        for card in extraction_graph.cards[:8]
    ) or page_evidence[:1]
    blocker_evidence = tuple(
        f"blocker:{text_hash(signal)}"
        for signal in (
            *blocker_graph.modal_or_consent_signals,
            *blocker_graph.captcha_or_login_signals,
            *blocker_graph.dynamic_loading_signals,
            *blocker_graph.hard_boundary_signals,
        )
    ) or page_evidence[:1]
    source = "cloak_session_cdp_a11y_safe_dom_world_model"
    return {
        "session_state": _state_field(
            {
                "backend": backend_truth.model_dump(mode="json"),
                "cookie_count": session_graph.cookie_count,
                "storage_key_count": session_graph.storage_key_count,
                "login_state": session_graph.login_state,
                "profile_material_persisted": session_graph.profile_material_persisted,
            },
            confidence=0.82,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="safe metadata only; raw session values are intentionally unavailable",
        ),
        "page_identity": _state_field(
            {
                "page_kind_guess": page_state.page_kind_guess,
                "title_hash_or_safe_title": page_state.title_hash_or_safe_title,
                "origin_hash": page_state.origin_hash,
            },
            confidence=0.78,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="classification is heuristic until corroborated by structured data and network state",
        ),
        "navigation_state": _state_field(
            {"origin_hash": page_state.origin_hash, "page_state_hash": page_state.page_state_hash},
            confidence=0.72,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="URL path is not exposed; state hash and origin are used instead",
        ),
        "tabs_and_frames": _state_field(
            {
                "active_page_known": True,
                "tab_count": "unknown",
                "frame_count": "unknown",
                "known_active_page_count": 1,
            },
            confidence=0.58,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="first runtime version exposes one active bounded page; full tab/frame census is not yet fused",
        ),
        "page_lifecycle": _state_field(
            {"lifecycle": _lifecycle_guess(blocker_graph), "dynamic_loading_signals": list(blocker_graph.dynamic_loading_signals)},
            confidence=0.62,
            evidence_refs=blocker_evidence,
            source=source,
            uncertainty_reason="lifecycle is inferred from visible dynamic-loading signals",
        ),
        "forms": _state_field(
            {"form_controls": list(action_graph.form_controls)},
            confidence=0.76 if action_graph.form_controls else 0.42,
            evidence_refs=ref_evidence,
            source=source,
            uncertainty_reason="form ownership/action URL is not exposed in safe model context",
        ),
        "search_controls": _state_field(
            {"search_like_refs": list(action_graph.search_like_refs), "ranked_count": len(action_graph.search_like_refs)},
            confidence=0.86 if action_graph.search_like_refs else 0.35,
            evidence_refs=ref_evidence,
            source=source,
            uncertainty_reason="ranking is based on role/name/value/ref semantics",
        ),
        "interactive_controls": _state_field(
            {
                "button_refs": list(action_graph.button_refs),
                "link_refs": list(action_graph.link_refs),
                "accessibility_ref_count": len(action_graph.accessibility_refs),
            },
            confidence=0.8 if action_graph.accessibility_refs else 0.34,
            evidence_refs=ref_evidence,
            source=source,
            uncertainty_reason="hidden, disabled, and secret controls are excluded from model-facing refs",
        ),
        "result_regions": _state_field(
            {
                "candidate_count": extraction_graph.product_or_result_candidate_count,
                "relevant_candidate_count": extraction_graph.relevant_product_candidate_count,
            },
            confidence=0.82 if extraction_graph.product_or_result_candidate_count else 0.3,
            evidence_refs=card_evidence,
            source=source,
            uncertainty_reason="candidate regions are inferred from repeated visible product/result signals",
        ),
        "candidate_entity_regions": _state_field(
            {"cards": list(extraction_graph.cards[:6])},
            confidence=0.78 if extraction_graph.cards else 0.3,
            evidence_refs=card_evidence,
            source=source,
            uncertainty_reason="fields may remain unknown unless visible evidence supports them",
        ),
        "network_summary": _state_field(
            {"network_event_count": protocol_graph.network_event_count, "events": list(protocol_graph.network_events)},
            confidence=0.68 if protocol_graph.network_event_count else 0.24,
            evidence_refs=tuple(f"network:{stable_hash(event)}" for event in protocol_graph.network_events[:8]) or page_evidence[:1],
            source=source,
            uncertainty_reason="network metadata is optional and never includes raw bodies or credentials",
        ),
        "console_summary": _state_field(
            {"console_event_count": protocol_graph.console_event_count, "events": list(protocol_graph.console_events)},
            confidence=0.65 if protocol_graph.console_event_count else 0.24,
            evidence_refs=tuple(f"console:{stable_hash(event)}" for event in protocol_graph.console_events[:8]) or page_evidence[:1],
            source=source,
            uncertainty_reason="console metadata is optional and text is hash-only",
        ),
        "structured_data": _state_field(
            {
                "available": False,
                "candidate_card_count": extraction_graph.product_or_result_candidate_count,
                "visible_candidate_cards_available": bool(extraction_graph.cards),
                "structured_data_source": "not_observed",
            },
            confidence=0.2,
            evidence_refs=card_evidence,
            source=source,
            uncertainty_reason="candidate cards are visible-evidence extractions; JSON-LD and microdata are not yet separately harvested",
        ),
        "storage_session_metadata": _state_field(
            {"cookies": list(session_graph.cookies), "storage_keys": list(session_graph.storage_keys)},
            confidence=0.78,
            evidence_refs=tuple(f"storage:{stable_hash(item)}" for item in (*session_graph.cookies, *session_graph.storage_keys)) or page_evidence[:1],
            source=source,
            uncertainty_reason="names/domains/keys are hash-only; values are never exposed",
        ),
        "overlays_modals_blockers": _state_field(
            {
                "modal_or_consent_signals": list(blocker_graph.modal_or_consent_signals),
                "captcha_or_login_signals": list(blocker_graph.captcha_or_login_signals),
                "hard_boundary_signals": list(blocker_graph.hard_boundary_signals),
            },
            confidence=0.76 if blocker_evidence else 0.35,
            evidence_refs=blocker_evidence,
            source=source,
            uncertainty_reason="blockers are inferred from safe visible text and signals",
        ),
        "visual_fallback_refs": _state_field(
            {
                "visual_refs_available": visual_graph.visual_refs_available,
                "screenshot_ref_hash": visual_graph.screenshot_ref_hash,
                "screenshot_persisted": visual_graph.screenshot_persisted,
            },
            confidence=0.5 if visual_graph.visual_refs_available else 0.2,
            evidence_refs=page_evidence[:1],
            source=source,
            uncertainty_reason="screenshots are not persisted by default",
        ),
        "available_safe_browser_skills": _state_field(
            {"skills": list(recommended_model_skills), "runtime_actions": list(action_graph.recommended_browser_actions)},
            confidence=0.84,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="skills are safe mission-level suggestions, not authority grants",
        ),
        "uncertainty": _state_field(
            {
                "page_kind_guess": model.page_kind_guess,
                "known_unknowns": _known_unknowns(extraction_graph, protocol_graph),
            },
            confidence=0.7,
            evidence_refs=page_evidence,
            source=source,
            uncertainty_reason="Sentinel exposes uncertainty explicitly instead of pretending browser understanding is complete",
        ),
        "recommended_recovery_paths": _state_field(
            {"paths": _recommended_recovery_paths(action_graph, extraction_graph, blocker_graph)},
            confidence=0.8,
            evidence_refs=(*page_evidence[:1], *ref_evidence[:3], *card_evidence[:3]),
            source=source,
            uncertainty_reason="recovery paths are recommendations for in-scope failures, not automatic authority expansion",
        ),
    }


def _state_field(
    value: Any,
    *,
    confidence: float,
    evidence_refs: tuple[str, ...],
    source: str,
    uncertainty_reason: str,
) -> dict[str, Any]:
    return {
        "value": value,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "evidence_refs": list(evidence_refs or ("unknown:evidence",)),
        "freshness": "current_snapshot",
        "source": source,
        "uncertainty_reason": uncertainty_reason,
    }


def _lifecycle_guess(blocker_graph: BrowserBlockerGraph) -> str:
    if blocker_graph.dynamic_loading_signals:
        return "dynamic_loading_or_partial"
    return "stable_current_snapshot"


def _known_unknowns(extraction_graph: BrowserExtractionGraph, protocol_graph: BrowserProtocolGraph) -> list[str]:
    unknowns: list[str] = []
    if not extraction_graph.cards:
        unknowns.append("no_product_or_result_cards_confirmed")
    if protocol_graph.network_event_count == 0:
        unknowns.append("network_metadata_absent")
    for card in extraction_graph.cards:
        for key in ("visible_price", "currency_or_unit", "minimum_order", "supplier_or_store"):
            if card.get(key) == "unknown":
                unknowns.append(f"{key}_unknown")
    return list(dict.fromkeys(unknowns or ["none_declared"]))


def _recommended_recovery_paths(
    action_graph: BrowserActionGraph,
    extraction_graph: BrowserExtractionGraph,
    blocker_graph: BrowserBlockerGraph,
) -> list[str]:
    if blocker_graph.captcha_or_login_signals:
        return ["stop_or_request_authority_for_human_verification_boundary"]
    if extraction_graph.product_or_result_candidate_count:
        return ["extract_product_cards", "verify_extraction", "summarize_grounded_evidence"]
    if action_graph.search_like_refs:
        return ["retry_best_ranked_search_control", "try_alternate_submit", "refresh_world_model"]
    return ["observe_again", "scroll_or_wait_for_results", "report_uncertain_page_shape"]


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
        "entity_family": _safe_text(str(getattr(card, "entity_family", "unknown"))),
        "entity_kind": _safe_text(str(getattr(card, "entity_kind", str(card.kind)))),
        "title": _safe_text(str(card.title)),
        "visible_price": _safe_text(str(card.visible_price)),
        "currency_or_unit": _safe_text(str(card.currency_or_unit)),
        "minimum_order": _safe_text(str(card.minimum_order)),
        "supplier_or_store": _safe_text(str(card.supplier_or_store)),
        "relevance_to_objective": str(card.relevance_to_objective),
        "relevance_reason": _safe_text(str(getattr(card, "relevance_reason", "unknown")), 180),
        "price_condition_supported": str(card.price_condition_supported),
        "evidence_ref_hash": str(card.evidence_ref_hash),
        "evidence_refs": [str(ref)[:160] for ref in tuple(getattr(card, "evidence_refs", ()) or ())[:8]],
        "extra_attributes": _safe_card_extensions(getattr(card, "extra_attributes", {}) or {}),
        "relationships": _safe_card_relationships(getattr(card, "relationships", ()) or ()),
        "confidence": float(card.confidence),
    }


def _safe_card_extensions(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, item in value.items():
        rendered_key = _safe_text(str(key), 64)
        if isinstance(item, bool | int | float):
            safe[rendered_key] = item
        else:
            safe[rendered_key] = _safe_text(str(item), 160)
    return safe


def _safe_card_relationships(value: Any) -> list[dict[str, Any]]:
    relationships = list(value) if isinstance(value, (list, tuple)) else []
    safe: list[dict[str, Any]] = []
    for item in relationships[:12]:
        if not isinstance(item, dict):
            continue
        safe.append(
            {
                "type": _safe_text(str(item.get("type") or "unknown"), 64),
                "target_hash": _safe_text(str(item.get("target_hash") or ""), 128),
                "confidence": float(item.get("confidence") or 0.0),
            }
        )
    return safe


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
