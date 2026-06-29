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
    for ref in world_model.search_like_refs[:4]:
        if "real_browser_control.real_browser.type_text" in allowed_actions:
            candidates.append({"action": "real_browser.type_text", "ref": ref, "reason": "enter product search query"})
        if "real_browser_control.real_browser.press_key" in allowed_actions:
            candidates.append({"action": "real_browser.press_key", "ref": ref, "key": "Enter", "reason": "submit search"})
    for ref in tuple(world_model.button_refs[:3]) + tuple(world_model.link_refs[:3]):
        if "real_browser_control.real_browser.click" in allowed_actions:
            candidates.append({"action": "real_browser.click", "ref": ref, "reason": "activate visible browser control or result"})
    if "real_browser_control.real_browser.extract_text" in allowed_actions:
        candidates.append({"action": "real_browser.extract_text", "ref": "page:text", "reason": "extract visible product/search information"})
    if "real_browser_control.real_browser.wait_for_text" in allowed_actions:
        candidates.append({"action": "real_browser.wait_for_text", "ref": None, "reason": "wait for result/product text after navigation"})
    if "real_browser_control.real_browser.scroll" in allowed_actions:
        candidates.append({"action": "real_browser.scroll", "ref": None, "reason": "reveal more result cards"})
    return tuple(candidates[:12])


def _recommended_next_actions(world_model: BrowserWorldModel, allowed_actions: tuple[str, ...]) -> tuple[str, ...]:
    preferred = [f"real_browser_control.{action}" for action in world_model.recommended_browser_actions]
    actions = [action for action in preferred if action in allowed_actions]
    if "real_browser_control.real_browser.extract_text" in allowed_actions and world_model.product_or_result_candidate_cards:
        actions.append("real_browser_control.real_browser.extract_text")
    if not actions and "real_browser_control.real_browser.observe" in allowed_actions:
        actions.append("real_browser_control.real_browser.observe")
    return tuple(dict.fromkeys(actions))


def _examples(world_model: BrowserWorldModel, allowed_actions: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    examples: list[dict[str, Any]] = []
    search_ref = world_model.search_like_refs[0] if world_model.search_like_refs else None
    link_ref = world_model.link_refs[0] if world_model.link_refs else None
    if "real_browser_control.real_browser.observe" in allowed_actions:
        examples.append({"capability_id": "real_browser_control", "operation": "real_browser.observe", "params": {}})
    if search_ref and "real_browser_control.real_browser.type_text" in allowed_actions:
        examples.append(
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.type_text",
                "params": {"ref": search_ref, "text": "glasses under 5 euro"},
            }
        )
    if search_ref and "real_browser_control.real_browser.press_key" in allowed_actions:
        examples.append(
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.press_key",
                "params": {"ref": search_ref, "key": "Enter"},
            }
        )
    if link_ref and "real_browser_control.real_browser.click" in allowed_actions:
        examples.append(
            {"capability_id": "real_browser_control", "operation": "real_browser.click", "params": {"ref": link_ref}}
        )
    if "real_browser_control.real_browser.extract_text" in allowed_actions:
        examples.append({"capability_id": "real_browser_control", "operation": "real_browser.extract_text", "params": {}})
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
