from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.operator.browser_world_model import BrowserWorldModel
from sentinel.shared.models import SentinelModel, new_id


class BrowserDecisionFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("browser_decision_frame"))
    mission_objective: str
    current_progress_state: str
    allowed_actions: tuple[str, ...] = Field(default_factory=tuple)
    forbidden_actions: tuple[str, ...] = Field(default_factory=tuple)
    top_refs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    candidate_actions: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    candidate_extractions: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    recommended_next_actions: tuple[str, ...] = Field(default_factory=tuple)
    exact_action_envelope_examples: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    completion_requirements: dict[str, Any] = Field(default_factory=dict)

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BrowserDecisionFrameCompiler:
    def compile(
        self,
        *,
        mission_objective: str,
        world_model: BrowserWorldModel,
        available_actions: tuple[str, ...],
        progress_state: str,
        completion_requirements: dict[str, Any] | None = None,
    ) -> BrowserDecisionFrame:
        allowed_actions = tuple(_browser_actions(available_actions))
        return BrowserDecisionFrame(
            mission_objective=mission_objective[:500],
            current_progress_state=progress_state,
            allowed_actions=allowed_actions,
            forbidden_actions=(
                "login",
                "contact_supplier",
                "send_inquiry",
                "add_to_cart",
                "checkout",
                "payment",
                "account_creation",
                "submit_personal_data",
            ),
            top_refs=tuple(ref.model_dump() for ref in world_model.stable_refs[:12]),
            candidate_actions=_candidate_actions(world_model, allowed_actions),
            candidate_extractions=tuple(card.model_dump() for card in world_model.product_or_result_candidate_cards[:6]),
            blockers=tuple(
                list(world_model.modal_or_consent_signals)
                + list(world_model.captcha_or_login_signals)
                + list(world_model.dynamic_loading_signals)
            ),
            recommended_next_actions=_recommended_next_actions(world_model, allowed_actions),
            exact_action_envelope_examples=_examples(world_model, allowed_actions),
            completion_requirements=completion_requirements
            or {
                "requires_real_browser_observation_or_world_model": True,
                "requires_browser_state_change_or_meaningful_extraction": True,
                "requires_product_or_search_extraction": True,
                "requires_sentinel_loop_finish": True,
            },
        )


def _browser_actions(available_actions: tuple[str, ...]) -> list[str]:
    return [
        action
        for action in available_actions
        if action.startswith("real_browser_control.") or action == "sentinel_loop.finish"
    ]


def _candidate_actions(world_model: BrowserWorldModel, allowed_actions: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    candidates: list[dict[str, Any]] = []
    if "real_browser_control.real_browser.observe" in allowed_actions:
        candidates.append({"action": "real_browser.observe", "ref": None, "reason": "refresh stable refs/world model"})
    search_ref = world_model.search_like_refs[0] if world_model.search_like_refs else None
    if search_ref and "real_browser_control.real_browser.search" in allowed_actions:
        candidates.append(
            {
                "action": "real_browser.search",
                "ref": search_ref,
                "query_hint": "glasses under 5 euro",
                "reason": "run robust bounded search using the best search-like control",
            }
        )
    for ref in world_model.link_refs[:3]:
        if "real_browser_control.real_browser.inspect_result" in allowed_actions:
            candidates.append({"action": "real_browser.inspect_result", "ref": ref, "reason": "inspect visible result/product card"})
        if "real_browser_control.real_browser.open_result" in allowed_actions:
            candidates.append({"action": "real_browser.open_result", "ref": ref, "reason": "open a promising bounded result"})
    if "real_browser_control.real_browser.extract_product_cards" in allowed_actions:
        candidates.append(
            {
                "action": "real_browser.extract_product_cards",
                "ref": "page:product_cards",
                "reason": "extract title, price, MOQ, supplier and caveats as structured cards",
            }
        )
    if "real_browser_control.real_browser.verify_extraction" in allowed_actions:
        candidates.append({"action": "real_browser.verify_extraction", "ref": "page:product_cards", "reason": "verify extracted product cards before finish"})
    return tuple(candidates[:12])


def _recommended_next_actions(world_model: BrowserWorldModel, allowed_actions: tuple[str, ...]) -> tuple[str, ...]:
    preferred = [f"real_browser_control.{action}" for action in world_model.recommended_browser_actions]
    actions = [action for action in preferred if action in allowed_actions]
    if "real_browser_control.real_browser.extract_product_cards" in allowed_actions and world_model.product_or_result_candidate_cards:
        actions.append("real_browser_control.real_browser.extract_product_cards")
    if "real_browser_control.real_browser.verify_extraction" in allowed_actions and world_model.product_or_result_candidate_cards:
        actions.append("real_browser_control.real_browser.verify_extraction")
    if not actions and "real_browser_control.real_browser.observe" in allowed_actions:
        actions.append("real_browser_control.real_browser.observe")
    return tuple(dict.fromkeys(actions))


def _examples(world_model: BrowserWorldModel, allowed_actions: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    examples: list[dict[str, Any]] = []
    search_ref = world_model.search_like_refs[0] if world_model.search_like_refs else None
    link_ref = world_model.link_refs[0] if world_model.link_refs else None
    if "real_browser_control.real_browser.observe" in allowed_actions:
        examples.append({"capability_id": "real_browser_control", "operation": "real_browser.observe", "params": {}})
    if search_ref and "real_browser_control.real_browser.search" in allowed_actions:
        examples.append(
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.search",
                "params": {"ref": search_ref, "query": "glasses under 5 euro"},
            }
        )
    if link_ref and "real_browser_control.real_browser.inspect_result" in allowed_actions:
        examples.append(
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.inspect_result",
                "params": {"ref": link_ref},
            }
        )
    if link_ref and "real_browser_control.real_browser.open_result" in allowed_actions:
        examples.append(
            {"capability_id": "real_browser_control", "operation": "real_browser.open_result", "params": {"ref": link_ref}}
        )
    if "real_browser_control.real_browser.extract_product_cards" in allowed_actions:
        examples.append({"capability_id": "real_browser_control", "operation": "real_browser.extract_product_cards", "params": {}})
    if "real_browser_control.real_browser.verify_extraction" in allowed_actions:
        examples.append({"capability_id": "real_browser_control", "operation": "real_browser.verify_extraction", "params": {}})
    if "sentinel_loop.finish" in allowed_actions:
        examples.append(
            {
                "capability_id": "sentinel_loop",
                "operation": "finish",
                "params": {"safe_summary": "short evaluation based only on extracted cards and receipts"},
            }
        )
    return tuple(examples[:8])


__all__ = ["BrowserDecisionFrame", "BrowserDecisionFrameCompiler"]
