from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.shared.models import SentinelModel


_HARD_BOUNDARY_MARKERS = (
    "login",
    "log in",
    "sign in",
    "account creation",
    "create account",
    "contact supplier",
    "contact the supplier",
    "send inquiry",
    "inquiry",
    "message supplier",
    "add to cart",
    "checkout",
    "payment",
    "pay ",
    "spend",
    "credential",
    "password",
    "secret",
    "cookie",
    "session",
    "upload",
    "download",
    "javascript",
    "external api",
    "desktop",
)

_MODEL_VISIBLE_BROWSER_ACTIONS = {
    "real_browser_control.real_browser.open",
    "real_browser_control.real_browser.observe",
    "real_browser_control.real_browser.search",
    "real_browser_control.real_browser.inspect_result",
    "real_browser_control.real_browser.open_result",
    "real_browser_control.real_browser.extract_product_cards",
    "real_browser_control.real_browser.verify_extraction",
    "sentinel_loop.finish",
}


class BrowserModelNativeIntentMapping(SentinelModel):
    envelope: ActionEnvelope | None = None
    blocked: bool = False
    blocked_reason: str | None = None
    intent_kind: str = "unknown"
    safe_diagnostics: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "intent_kind": self.intent_kind,
            "envelope": self.envelope.safe_identity_payload() if self.envelope is not None else None,
            "safe_diagnostics": self.safe_diagnostics,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


def map_browser_model_native_intent(model_output: Any, *, context: dict[str, Any]) -> BrowserModelNativeIntentMapping:
    """Map natural browser task intent to Sentinel's internal ActionEnvelope.

    This keeps the model-facing protocol skill/native while preserving the
    ActionEnvelope as the internal runtime representation.
    """

    visible_text, source, top_level_keys = _extract_visible_text(model_output)
    normalized = _normalize_text(visible_text)
    diagnostics = _safe_diagnostics(
        visible_text=visible_text,
        source=source,
        top_level_keys=top_level_keys,
        context=context,
    )

    if _is_hard_boundary_intent(normalized):
        return BrowserModelNativeIntentMapping(
            blocked=True,
            blocked_reason="BROWSER_INTENT_HARD_BOUNDARY",
            intent_kind="hard_boundary",
            safe_diagnostics={**diagnostics, "failure_code": "BROWSER_INTENT_HARD_BOUNDARY"},
        )

    explicit = _canonical_action_from_payload(model_output)
    if explicit is not None:
        action_name, params, target_ref = explicit
        return _mapped(action_name, params=params, target_ref=target_ref, intent_kind="canonical_action", diagnostics=diagnostics)

    if not normalized:
        return _recommended_mapping(context, diagnostics=diagnostics, intent_kind="empty_or_ambiguous_intent")

    if _mentions_open(normalized):
        return _mapped("real_browser_control.real_browser.open", intent_kind="open", diagnostics=diagnostics)

    if _mentions_finish(normalized):
        if _finish_is_available(context):
            return _mapped(
                "sentinel_loop.finish",
                params={"safe_summary": "Browser task evidence verified; model requested finish."},
                intent_kind="finish",
                diagnostics=diagnostics,
            )
        if _has_browser_extraction(context):
            return _mapped("real_browser_control.real_browser.verify_extraction", intent_kind="finish_requires_verification", diagnostics=diagnostics)
        if _has_product_cards(context):
            return _mapped("real_browser_control.real_browser.extract_product_cards", intent_kind="finish_requires_extraction", diagnostics=diagnostics)
        return _recommended_mapping(context, diagnostics=diagnostics, intent_kind="finish_without_proof")

    if _mentions_verify(normalized):
        return _mapped("real_browser_control.real_browser.verify_extraction", intent_kind="verify_extraction", diagnostics=diagnostics)

    if _has_product_cards(context) and _mentions_extract_or_compare(normalized):
        return _mapped("real_browser_control.real_browser.extract_product_cards", intent_kind="extract_visible_cards", diagnostics=diagnostics)

    if _mentions_extract_or_compare(normalized):
        return _mapped("real_browser_control.real_browser.extract_product_cards", intent_kind="extract_product_cards", diagnostics=diagnostics)

    if _mentions_open_result(normalized):
        return _mapped(
            "real_browser_control.real_browser.open_result",
            params=_result_ref_params(context),
            intent_kind="open_result",
            diagnostics=diagnostics,
        )

    if _mentions_inspect(normalized):
        return _mapped(
            "real_browser_control.real_browser.inspect_result",
            params=_result_ref_params(context),
            intent_kind="inspect_result",
            diagnostics=diagnostics,
        )

    if _mentions_search(normalized):
        return _mapped(
            "real_browser_control.real_browser.search",
            params={"query": _extract_search_query(visible_text)},
            intent_kind="search",
            diagnostics=diagnostics,
        )

    return _recommended_mapping(context, diagnostics=diagnostics, intent_kind="safe_ambiguous_intent")


def _extract_visible_text(model_output: Any) -> tuple[str, str, tuple[str, ...]]:
    if isinstance(model_output, str):
        return model_output, "text", ()
    if isinstance(model_output, dict):
        keys = tuple(str(key) for key in model_output)
        for key in ("reply", "message", "content", "text", "intent", "action_intent"):
            value = model_output.get(key)
            if isinstance(value, str) and value.strip():
                return value, key, keys
        action = model_output.get("action")
        if isinstance(action, str) and action.strip():
            return action, "action", keys
    return "", "unsupported", ()


def _canonical_action_from_payload(model_output: Any) -> tuple[str, dict[str, Any], str | None] | None:
    if not isinstance(model_output, dict):
        return None
    capability = model_output.get("capability_id")
    operation = model_output.get("operation")
    if isinstance(capability, str) and isinstance(operation, str) and capability.strip() and operation.strip():
        params = model_output.get("params") if isinstance(model_output.get("params"), dict) else {}
        target_ref = model_output.get("target_ref") if isinstance(model_output.get("target_ref"), str) else None
        return f"{capability.strip()}.{operation.strip()}", dict(params), target_ref
    action = model_output.get("action")
    if isinstance(action, str) and action.strip() and "." in action:
        params = model_output.get("params") if isinstance(model_output.get("params"), dict) else {}
        target_ref = model_output.get("target_ref") if isinstance(model_output.get("target_ref"), str) else None
        return action.strip(), dict(params), target_ref
    return None


def _mapped(
    canonical_action_name: str,
    *,
    params: dict[str, Any] | None = None,
    target_ref: str | None = None,
    intent_kind: str,
    diagnostics: dict[str, Any],
) -> BrowserModelNativeIntentMapping:
    envelope = _envelope_from_action_name(canonical_action_name, params=params or {}, target_ref=target_ref)
    return BrowserModelNativeIntentMapping(
        envelope=envelope,
        intent_kind=intent_kind,
        safe_diagnostics={
            **diagnostics,
            "mapped_action": canonical_action_name,
            "intent_kind": intent_kind,
        },
    )


def _recommended_mapping(
    context: dict[str, Any],
    *,
    diagnostics: dict[str, Any],
    intent_kind: str,
) -> BrowserModelNativeIntentMapping:
    action = _primary_recommended_action(context)
    if action is None:
        return BrowserModelNativeIntentMapping(
            blocked=True,
            blocked_reason="BROWSER_INTENT_NO_SAFE_RECOMMENDATION",
            intent_kind=intent_kind,
            safe_diagnostics={**diagnostics, "failure_code": "BROWSER_INTENT_NO_SAFE_RECOMMENDATION"},
        )
    params: dict[str, Any] = {}
    if action == "real_browser_control.real_browser.search":
        params["query"] = _query_from_mission(context)
    return _mapped(action, params=params, intent_kind=intent_kind, diagnostics=diagnostics)


def _envelope_from_action_name(
    canonical_action_name: str,
    *,
    params: dict[str, Any],
    target_ref: str | None,
) -> ActionEnvelope:
    if canonical_action_name == "finish":
        canonical_action_name = "sentinel_loop.finish"
    if canonical_action_name not in _MODEL_VISIBLE_BROWSER_ACTIONS:
        canonical_action_name = _coerce_to_model_visible_action(canonical_action_name)
    capability_id, operation = canonical_action_name.split(".", 1)
    return ActionEnvelope(
        capability_id=capability_id,
        operation=operation,
        target_ref=target_ref,
        params=params,
    )


def _coerce_to_model_visible_action(action_name: str) -> str:
    if action_name == "sentinel_loop.finish":
        return action_name
    if action_name.endswith(".open"):
        return "real_browser_control.real_browser.open"
    if action_name.endswith(".observe"):
        return "real_browser_control.real_browser.observe"
    if action_name.endswith(".search"):
        return "real_browser_control.real_browser.search"
    if action_name.endswith(".inspect_result"):
        return "real_browser_control.real_browser.inspect_result"
    if action_name.endswith(".open_result"):
        return "real_browser_control.real_browser.open_result"
    if action_name.endswith(".extract_product_cards"):
        return "real_browser_control.real_browser.extract_product_cards"
    if action_name.endswith(".verify_extraction"):
        return "real_browser_control.real_browser.verify_extraction"
    return _primary_browser_action_fallback()


def _primary_browser_action_fallback() -> str:
    return "real_browser_control.real_browser.extract_product_cards"


def _safe_diagnostics(
    *,
    visible_text: str,
    source: str,
    top_level_keys: tuple[str, ...],
    context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model_input_kind": "natural_intent" if visible_text.strip() else "empty",
        "content_source": source,
        "visible_content_present": bool(visible_text.strip()),
        "visible_content_hash": text_hash(visible_text),
        "visible_content_char_count": len(visible_text),
        "top_level_keys": list(top_level_keys),
        "internal_runtime_format": "ActionEnvelope",
        "context_primary_truth": context.get("decision_context_primary_truth"),
        "primary_recommended_action": context.get("primary_model_recommended_next_action"),
        "product_card_count": _product_card_count(context),
        "finish_available": bool(context.get("finish_available")),
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _is_hard_boundary_intent(normalized: str) -> bool:
    if not normalized:
        return False
    if "submit search" in normalized or "search submit" in normalized:
        return False
    return any(marker in normalized for marker in _HARD_BOUNDARY_MARKERS)


def _mentions_open(normalized: str) -> bool:
    return any(marker in normalized for marker in ("open the bounded", "open alibaba", "open page", "open the page"))


def _mentions_search(normalized: str) -> bool:
    return any(marker in normalized for marker in ("search", "find ", "look for", "under 5", "under five", "glasses", "sunglasses"))


def _mentions_extract_or_compare(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "extract",
            "visible product",
            "product card",
            "product cards",
            "compare",
            "use visible products",
            "title",
            "price",
            "moq",
            "supplier",
        )
    )


def _mentions_verify(normalized: str) -> bool:
    return any(marker in normalized for marker in ("verify", "check", "confirm", "validate"))


def _mentions_inspect(normalized: str) -> bool:
    return "inspect" in normalized or "look at this result" in normalized or "review result" in normalized


def _mentions_open_result(normalized: str) -> bool:
    return "open the best result" in normalized or "open result" in normalized or "open this result" in normalized


def _mentions_finish(normalized: str) -> bool:
    return any(marker in normalized for marker in ("finish", "done", "enough evidence", "summarize", "summary"))


def _extract_search_query(visible_text: str) -> str:
    normalized = _normalize_text(visible_text)
    if ("glasses" in normalized or "sunglasses" in normalized) and (
        "5" in normalized or "five" in normalized or "euro" in normalized or "eur" in normalized
    ):
        return "glasses under 5 euro"
    match = re.search(r"(?:search(?: for)?|find|look for)\s+(.+?)(?:[.?!]|$)", visible_text, flags=re.IGNORECASE)
    if match:
        query = " ".join(match.group(1).split())
        return query[:120] if query else _query_from_text_fallback(visible_text)
    return _query_from_text_fallback(visible_text)


def _query_from_text_fallback(visible_text: str) -> str:
    text = " ".join(visible_text.split())
    return text[:120] if text else "glasses under 5 euro"


def _query_from_mission(context: dict[str, Any]) -> str:
    objective = str(context.get("mission_objective") or "")
    return _extract_search_query(objective)


def _primary_recommended_action(context: dict[str, Any]) -> str | None:
    for key in ("primary_model_recommended_next_action", "model_visible_recommended_next_action", "recommended_next_action"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return _coerce_to_model_visible_action(value.strip())
    frame = context.get("skill_decision_frame")
    if isinstance(frame, dict):
        actions = frame.get("recommended_next_actions")
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, str) and action.strip():
                    return _coerce_to_model_visible_action(action.strip())
    return None


def _result_ref_params(context: dict[str, Any]) -> dict[str, Any]:
    refs = context.get("top_link_candidates")
    if isinstance(refs, list) and refs:
        return {"ref": str(refs[0])}
    top_refs = context.get("top_stable_refs")
    if isinstance(top_refs, list):
        for item in top_refs:
            if isinstance(item, dict) and item.get("ref"):
                return {"ref": str(item["ref"])}
    return {"ref": "page:result"}


def _has_product_cards(context: dict[str, Any]) -> bool:
    return _product_card_count(context) > 0


def _product_card_count(context: dict[str, Any]) -> int:
    summary = context.get("browser_world_model_summary")
    if isinstance(summary, dict):
        for key in ("product_or_result_candidate_count", "product_candidate_count", "result_candidate_count"):
            value = summary.get(key)
            if isinstance(value, int):
                return value
    model = context.get("browser_world_model")
    if isinstance(model, dict):
        cards = model.get("product_or_result_candidate_cards")
        if isinstance(cards, list):
            return len(cards)
    frame = context.get("browser_decision_frame")
    if isinstance(frame, dict):
        candidates = frame.get("candidate_extractions")
        if isinstance(candidates, list):
            return len(candidates)
    return 0


def _has_browser_extraction(context: dict[str, Any]) -> bool:
    requirements = context.get("completion_requirements")
    return bool(
        isinstance(requirements, dict)
        and requirements.get("has_real_browser_extraction_receipt") is True
    )


def _finish_is_available(context: dict[str, Any]) -> bool:
    return bool((context.get("finish_available") or context.get("objective_satisfied")) and _has_verified_browser_extraction(context))


def _has_verified_browser_extraction(context: dict[str, Any]) -> bool:
    summary = context.get("real_browser_control_summary")
    if isinstance(summary, dict):
        latest = summary.get("latest_action")
        if (
            isinstance(latest, dict)
            and latest.get("operation") == "real_browser.verify_extraction"
            and latest.get("status") in {"completed", "passed", "success"}
            and int(latest.get("receipt_count") or 0) > 0
        ):
            return True
    for item in context.get("bounded_observation_summaries", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("capability_id") == "real_browser_control"
            and item.get("operation") == "real_browser.verify_extraction"
            and item.get("status") in {"completed", "passed", "success"}
            and int(item.get("receipt_count") or 0) > 0
        ):
            return True
    return False


__all__ = ["BrowserModelNativeIntentMapping", "map_browser_model_native_intent"]
