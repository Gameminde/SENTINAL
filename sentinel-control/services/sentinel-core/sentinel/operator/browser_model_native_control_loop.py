from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
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
    "real_browser_control.real_browser.extract_evidence",
    "real_browser_control.real_browser.extract_entities",
    "real_browser_control.real_browser.extract_product_cards",
    "real_browser_control.real_browser.verify_extraction",
    "sentinel_loop.summarize_evidence",
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
        unsupported_reason = _unsupported_explicit_action_reason(action_name)
        if unsupported_reason is not None:
            return BrowserModelNativeIntentMapping(
                blocked=True,
                blocked_reason=unsupported_reason,
                intent_kind="explicit_action_blocked",
                safe_diagnostics={
                    **diagnostics,
                    "failure_code": unsupported_reason,
                    "requested_action_hash": text_hash(action_name),
                },
            )
        action_name = _completion_lane_override(action_name, params=params, normalized=normalized, context=context)
        return _mapped(
            action_name,
            params=params,
            target_ref=target_ref,
            intent_kind="canonical_action",
            diagnostics=diagnostics,
            context=context,
        )

    if _is_empty_provider_visible_content_before_material_action(model_output, visible_text=visible_text, source=source, context=context):
        return _recoverable_empty_provider_content_mapping(diagnostics)

    if not normalized:
        return _recommended_mapping(context, diagnostics=diagnostics, intent_kind="empty_or_ambiguous_intent")

    if _mentions_finish(normalized):
        if _finish_is_available(context):
            return _mapped(
                "sentinel_loop.finish",
                params=_terminal_finish_params(
                    context,
                    fallback_summary="Browser task evidence verified and relevance assessed; model requested finish.",
                ),
                intent_kind="finish",
                diagnostics=diagnostics,
            )
        if (
            _has_verified_browser_extraction(context)
            and _has_grounded_evidence_summary(context)
            and _has_objective_relevance_assessment(context)
        ):
            return _mapped(
                "sentinel_loop.finish",
                params=_terminal_finish_params(
                    context,
                    fallback_summary="Browser task evidence verified; finish with grounded caveats.",
                ),
                intent_kind="finish_after_grounded_relevance_assessment",
                diagnostics=diagnostics,
            )
        if _has_verified_browser_extraction(context):
            return _mapped("sentinel_loop.summarize_evidence", intent_kind="finish_requires_summary", diagnostics=diagnostics)
        if _has_browser_extraction(context):
            return _mapped("real_browser_control.real_browser.verify_extraction", intent_kind="finish_requires_verification", diagnostics=diagnostics)
        if _has_product_cards(context):
            return _mapped(_extract_action_for_context(context), intent_kind="finish_requires_extraction", diagnostics=diagnostics)
        return _recommended_mapping(context, diagnostics=diagnostics, intent_kind="finish_without_proof")

    if _has_verified_browser_extraction(context) and not _has_grounded_evidence_summary(context):
        if _mentions_new_search_query(normalized) and _mentions_evidence_insufficient(normalized):
            return _mapped(
                "real_browser_control.real_browser.search",
                params={"query": _extract_search_query(visible_text)},
                intent_kind="explicit_insufficient_evidence_new_search",
                diagnostics=diagnostics,
            )
        return _mapped("sentinel_loop.summarize_evidence", intent_kind="verified_extraction_needs_summary", diagnostics=diagnostics)

    if _has_verified_browser_extraction(context) and _mentions_completion_without_finish(normalized):
        return _mapped(
            "sentinel_loop.finish",
            params=_terminal_finish_params(
                context,
                fallback_summary="Browser task evidence verified; model requested completion.",
            ),
            intent_kind="completion_after_verified_extraction",
            diagnostics=diagnostics,
        )

    if _mentions_verify(normalized):
        return _mapped("real_browser_control.real_browser.verify_extraction", intent_kind="verify_extraction", diagnostics=diagnostics)

    if _has_product_cards(context) and not _has_browser_extraction(context):
        if _mentions_new_search_query(normalized):
            return _mapped(
                "real_browser_control.real_browser.search",
                params={"query": _extract_search_query(visible_text)},
                intent_kind="explicit_new_search_query",
                diagnostics=diagnostics,
            )
        return _mapped(_extract_action_for_context(context), intent_kind="extract_visible_cards", diagnostics=diagnostics)

    if _has_product_cards(context) and _has_browser_extraction(context) and not _has_verified_browser_extraction(context):
        return _mapped("real_browser_control.real_browser.verify_extraction", intent_kind="verify_visible_cards", diagnostics=diagnostics)

    if _mentions_open(normalized):
        return _mapped("real_browser_control.real_browser.open", intent_kind="open", diagnostics=diagnostics)

    if _mentions_extract_or_compare(normalized):
        return _mapped(_extract_action_for_context(context), intent_kind="extract_evidence", diagnostics=diagnostics)

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
    context: dict[str, Any] | None = None,
) -> BrowserModelNativeIntentMapping:
    mapped_params = dict(params or {})
    if canonical_action_name == "sentinel_loop.finish" and context is not None:
        mapped_params = _terminal_finish_params(context, fallback_summary=str(mapped_params.get("safe_summary") or ""))
    envelope = _envelope_from_action_name(canonical_action_name, params=mapped_params, target_ref=target_ref)
    return BrowserModelNativeIntentMapping(
        envelope=envelope,
        intent_kind=intent_kind,
        safe_diagnostics={
            **diagnostics,
            "mapped_action": canonical_action_name,
            "intent_kind": intent_kind,
        },
    )


def _recoverable_empty_provider_content_mapping(diagnostics: dict[str, Any]) -> BrowserModelNativeIntentMapping:
    failure_code = "PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION"
    return BrowserModelNativeIntentMapping(
        envelope=ActionEnvelope(
            capability_id="",
            operation="",
            params={"failure_code": failure_code},
        ),
        intent_kind="provider_empty_visible_content",
        safe_diagnostics={
            **diagnostics,
            "failure_code": failure_code,
            "intent_kind": "provider_empty_visible_content",
            "recommended_next_action": "ask_provider_for_native_browser_intent",
        },
    )


def _recommended_mapping(
    context: dict[str, Any],
    *,
    diagnostics: dict[str, Any],
    intent_kind: str,
) -> BrowserModelNativeIntentMapping:
    action = _strongest_contextual_browser_action(context) or _primary_recommended_action(context)
    if action is None:
        action = _safe_fallback_browser_action(context)
        if action is None:
            return BrowserModelNativeIntentMapping(
                blocked=True,
                blocked_reason="BROWSER_INTENT_NO_SAFE_RECOMMENDATION",
                intent_kind=intent_kind,
                safe_diagnostics={**diagnostics, "failure_code": "BROWSER_INTENT_NO_SAFE_RECOMMENDATION"},
            )
        diagnostics = {
            **diagnostics,
            "failure_code": "BROWSER_INTENT_NO_SAFE_RECOMMENDATION",
            "fallback_reason": "BROWSER_INTENT_NO_SAFE_RECOMMENDATION_RECOVERED",
        }
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


def _terminal_finish_params(context: dict[str, Any], *, fallback_summary: str) -> dict[str, Any]:
    summary = _grounded_summary_payload(context)
    summary_text = str(summary.get("summary_text") or fallback_summary or "Browser evidence was summarized with grounded caveats.").strip()
    evidence_refs = _public_evidence_refs(context)
    if not evidence_refs:
        evidence_refs = [f"evidence:{stable_hash({'summary': summary_text})}"]
    if summary.get("negative_result_confirmed") is True:
        return {
            "honest_blocker": {
                "reason": summary_text,
                "available_evidence_refs": evidence_refs,
                "missing_evidence": ["objective-satisfying result evidence"],
            },
            "answer_claims": [
                {
                    "claim_id": f"claim:{stable_hash({'negative': summary_text})}",
                    "claim_type": "declared_unknown",
                    "text": summary_text,
                    "evidence_refs": evidence_refs,
                    "confidence": 0.74,
                }
            ],
        }
    claim_type = "factual" if _has_public_evidence_summary(context) else "model_inference"
    return {
        "final_answer": {
            "answer_text": summary_text,
            "answer_kind": "grounded_browser_answer",
        },
        "answer_claims": [
            {
                "claim_id": f"claim:{stable_hash({'answer': summary_text})}",
                "claim_type": claim_type,
                "text": summary_text,
                "evidence_refs": evidence_refs if claim_type == "factual" else [],
                "confidence": 0.72 if claim_type == "factual" else 0.45,
            }
        ],
    }


def _grounded_summary_payload(context: dict[str, Any]) -> dict[str, Any]:
    summary = context.get("grounded_evidence_summary")
    if isinstance(summary, dict):
        if summary.get("present") is True:
            return {key: value for key, value in summary.items() if key != "present"}
        if summary.get("summary_text"):
            return summary
    return {}


def _public_evidence_refs(context: dict[str, Any]) -> list[str]:
    proof_summary = context.get("browser_proof_index_summary")
    refs = proof_summary.get("public_evidence_ids") if isinstance(proof_summary, dict) else ()
    if isinstance(refs, list | tuple):
        return [str(ref) for ref in refs[:8] if str(ref)]
    return []


def _has_public_evidence_summary(context: dict[str, Any]) -> bool:
    proof_summary = context.get("browser_proof_index_summary")
    return bool(isinstance(proof_summary, dict) and int(proof_summary.get("public_evidence_count") or 0) > 0)


def _coerce_to_model_visible_action(action_name: str) -> str:
    if action_name == "sentinel_loop.finish":
        return action_name
    if action_name == "sentinel_loop.summarize_evidence":
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
    if action_name.endswith(".extract_evidence"):
        return "real_browser_control.real_browser.extract_evidence"
    if action_name.endswith(".extract_entities"):
        return "real_browser_control.real_browser.extract_entities"
    if action_name.endswith(".extract_product_cards"):
        return "real_browser_control.real_browser.extract_product_cards"
    if action_name.endswith(".verify_extraction"):
        return "real_browser_control.real_browser.verify_extraction"
    return _primary_browser_action_fallback()


def _unsupported_explicit_action_reason(action_name: str) -> str | None:
    if action_name in _MODEL_VISIBLE_BROWSER_ACTIONS:
        return None
    normalized = _normalize_text(action_name.replace("_", " "))
    if any(_contains_affirmative_boundary_marker(normalized, marker) for marker in _HARD_BOUNDARY_MARKERS):
        return "BROWSER_INTENT_HARD_BOUNDARY"
    if action_name.startswith("real_browser_control.") or action_name.startswith("real_browser."):
        return "BROWSER_INTENT_ACTION_NOT_MODEL_VISIBLE"
    return None


def _primary_browser_action_fallback() -> str:
    return "real_browser_control.real_browser.extract_evidence"


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


def _is_empty_provider_visible_content_before_material_action(
    model_output: Any,
    *,
    visible_text: str,
    source: str,
    context: dict[str, Any],
) -> bool:
    if visible_text.strip() or not isinstance(model_output, dict):
        return False
    if _has_any_material_browser_action(context):
        return False
    content_source = str(
        model_output.get("content_source")
        or model_output.get("content_extraction_source")
        or source
        or ""
    ).lower()
    visible_count = model_output.get("visible_content_char_count")
    try:
        visible_count_int = int(visible_count)
    except (TypeError, ValueError):
        visible_count_int = 0
    provider_metadata_present = any(
        key in model_output
        for key in (
            "content_extraction_source",
            "finish_reason",
            "json_object_detected",
            "raw_text_hash",
            "reasoning_hash",
            "visible_content_char_count",
            "visible_content_estimated_tokens",
        )
    )
    return provider_metadata_present and visible_count_int == 0 and content_source in {"unsupported", "empty", ""}


def _has_any_material_browser_action(context: dict[str, Any]) -> bool:
    if context.get("has_real_browser_open_receipt") or context.get("has_real_browser_action_receipt"):
        return True
    requirements = context.get("completion_requirements")
    if isinstance(requirements, dict):
        return bool(
            requirements.get("has_real_browser_open_receipt")
            or requirements.get("has_real_browser_action_receipt")
            or requirements.get("has_real_browser_extraction_receipt")
            or requirements.get("has_real_browser_verified_extraction_receipt")
        )
    for observation in context.get("recent_receipts", ()) or ():
        if isinstance(observation, dict) and str(observation.get("operation", "")).startswith("real_browser."):
            return True
    return False


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _is_hard_boundary_intent(normalized: str) -> bool:
    if not normalized:
        return False
    if "submit search" in normalized or "search submit" in normalized:
        return False
    return any(_contains_affirmative_boundary_marker(normalized, marker) for marker in _HARD_BOUNDARY_MARKERS)


def _contains_affirmative_boundary_marker(normalized: str, marker: str) -> bool:
    for match in re.finditer(re.escape(marker), normalized):
        prefix = normalized[max(0, match.start() - 96) : match.start()]
        if _is_negated_boundary_context(prefix):
            continue
        return True
    return False


def _is_negated_boundary_context(prefix: str) -> bool:
    """Treat model statements that preserve boundaries as safe context.

    A model may say "finish without login/contact/payment" while explaining its
    next safe step. That is not an intent to log in, contact, or pay.
    """

    return bool(
        re.search(
            r"\b(do not|don't|dont|must not|should not|will not|won't|wont|cannot|can not|never|no|without|avoid|avoiding)\b.{0,80}$",
            prefix,
        )
    )


def _mentions_open(normalized: str) -> bool:
    return any(marker in normalized for marker in ("open the bounded", "open alibaba", "open page", "open the page"))


def _mentions_new_search_query(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in ("new search", "another search", "different search", "search again", "instead search")
    )


def _mentions_evidence_insufficient(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "evidence is insufficient",
            "not enough evidence",
            "insufficient evidence",
            "cards are not relevant",
            "results are not relevant",
            "need better evidence",
        )
    )


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


def _mentions_completion_without_finish(normalized: str) -> bool:
    return any(marker in normalized for marker in ("complete", "ready", "enough", "evaluative summary", "short evaluation"))


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
    frame = context.get("skill_decision_frame")
    if isinstance(frame, dict):
        actions = frame.get("recommended_next_actions")
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, str) and action.strip():
                    return _coerce_to_model_visible_action(action.strip())
    for key in ("primary_model_recommended_next_action", "model_visible_recommended_next_action", "recommended_next_action"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return _coerce_to_model_visible_action(value.strip())
    return None


def _strongest_contextual_browser_action(context: dict[str, Any]) -> str | None:
    if _has_verified_browser_extraction(context) and not _has_grounded_evidence_summary(context):
        return "sentinel_loop.summarize_evidence"
    if _has_verified_browser_extraction(context) and _has_grounded_evidence_summary(context) and _has_objective_relevance_assessment(context):
        return "sentinel_loop.finish"
    if _has_verified_browser_extraction(context) and _has_grounded_evidence_summary(context) and not _has_relevant_product_evidence(context):
        primary = _primary_recommended_action(context)
        if primary and primary != "real_browser_control.real_browser.search":
            return primary
        if _has_real_browser_search_receipt(context):
            return "real_browser_control.real_browser.extract_product_cards"
        return "real_browser_control.real_browser.search"
    if _has_browser_extraction(context) and not _has_verified_browser_extraction(context):
        return "real_browser_control.real_browser.verify_extraction"
    if _has_product_cards(context):
        return _extract_action_for_context(context)
    return None


def _extract_action_for_context(context: dict[str, Any]) -> str:
    if _context_has_commerce_evidence(context):
        return "real_browser_control.real_browser.extract_product_cards"
    return "real_browser_control.real_browser.extract_evidence"


def _context_has_commerce_evidence(context: dict[str, Any]) -> bool:
    summary = context.get("browser_world_model_summary")
    if isinstance(summary, dict):
        kind_counts = summary.get("candidate_entity_kind_counts")
        if isinstance(kind_counts, dict):
            for kind, count in kind_counts.items():
                if any(marker in str(kind).lower() for marker in ("commerce", "product", "catalog")):
                    try:
                        if int(count or 0) > 0:
                            return True
                    except (TypeError, ValueError):
                        return True
        if int(summary.get("product_candidate_count") or 0) > 0:
            return True
    model = context.get("browser_world_model")
    if isinstance(model, dict):
        cards = model.get("product_or_result_candidate_cards")
        if isinstance(cards, list):
            for card in cards:
                if not isinstance(card, dict):
                    continue
                kind = str(card.get("kind") or card.get("entity_kind") or "").lower()
                family = str(card.get("entity_family") or "").lower()
                if any(marker in f"{kind} {family}" for marker in ("commerce", "product", "catalog")):
                    return True
                commerce_fields = ("visible_price", "currency_or_unit", "minimum_order", "supplier_or_store")
                if any(str(card.get(field) or "").strip().lower() not in {"", "unknown"} for field in commerce_fields):
                    return True
    return False


def _safe_fallback_browser_action(context: dict[str, Any]) -> str | None:
    available = tuple(str(action) for action in context.get("available_actions", ()) if isinstance(action, str))
    preferred = (
        "real_browser_control.real_browser.observe",
        "real_browser_control.real_browser.extract_evidence",
        "real_browser_control.real_browser.extract_entities",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
    )
    for action in preferred:
        if action in available:
            return action
    return None


def _has_real_browser_search_receipt(context: dict[str, Any]) -> bool:
    requirements = context.get("completion_requirements")
    if isinstance(requirements, dict):
        return requirements.get("has_real_browser_search_receipt") is True
    return False


def _completion_lane_override(
    action_name: str,
    *,
    params: dict[str, Any],
    normalized: str,
    context: dict[str, Any],
) -> str:
    if not _has_verified_browser_extraction(context):
        return action_name
    if _has_grounded_evidence_summary(context):
        if action_name in {"sentinel_loop.finish", "sentinel_loop.summarize_evidence"}:
            return "sentinel_loop.finish"
        if _is_browser_navigation_or_search(action_name) and not (
            params.get("evidence_insufficient") is True or _mentions_evidence_insufficient(normalized)
        ):
            return "sentinel_loop.finish"
        return action_name
    if action_name == "sentinel_loop.finish":
        return "sentinel_loop.summarize_evidence"
    if action_name == "sentinel_loop.summarize_evidence":
        return action_name
    if _is_browser_navigation_or_search(action_name) and not (
        params.get("evidence_insufficient") is True or _mentions_evidence_insufficient(normalized)
    ):
        return "sentinel_loop.summarize_evidence"
    return action_name


def _is_browser_navigation_or_search(action_name: str) -> bool:
    return any(
        action_name.endswith(suffix)
        for suffix in (
            ".open",
            ".observe",
            ".search",
            ".inspect_result",
            ".open_result",
            ".extract_product_cards",
            ".verify_extraction",
        )
    )


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
    return bool(
        (context.get("finish_available") or context.get("objective_satisfied"))
        and _has_verified_browser_extraction(context)
        and _has_grounded_evidence_summary(context)
        and _has_objective_relevance_assessment(context)
    )


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


def _has_grounded_evidence_summary(context: dict[str, Any]) -> bool:
    summary = context.get("grounded_evidence_summary")
    if isinstance(summary, dict) and summary.get("present") is True:
        return True
    for item in context.get("bounded_observation_summaries", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("capability_id") == "sentinel_loop"
            and item.get("operation") == "summarize_evidence"
            and item.get("status") in {"completed", "passed", "success"}
        ):
            return True
    return False


def _has_objective_relevance_assessment(context: dict[str, Any]) -> bool:
    summary = context.get("grounded_evidence_summary")
    if isinstance(summary, dict) and summary.get("objective_relevance_assessed") is True:
        return True
    requirements = context.get("completion_requirements")
    if isinstance(requirements, dict):
        return bool(requirements.get("has_objective_relevance_assessment") is True)
    return False


def _has_relevant_product_evidence(context: dict[str, Any]) -> bool:
    summary = context.get("grounded_evidence_summary")
    if isinstance(summary, dict):
        return bool(summary.get("has_relevant_product_evidence") is True)
    requirements = context.get("completion_requirements")
    if isinstance(requirements, dict):
        return bool(requirements.get("has_relevant_product_evidence") is True)
    return False


__all__ = ["BrowserModelNativeIntentMapping", "map_browser_model_native_intent"]
