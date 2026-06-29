from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.shared.models import SentinelModel


SAFE_PROVIDER_METADATA_KEYS = {
    "provider_response_hash",
    "visible_content_length",
    "visible_content_char_count",
    "visible_content_estimated_tokens",
    "finish_reason",
    "output_truncated",
    "json_object_detected",
    "markdown_fence_detected",
    "multiple_json_objects_detected",
    "normalization_strategy",
    "content_extraction_source",
    "content_source",
    "content_extraction_error",
}

FORBIDDEN_MODEL_MATERIAL_KEYS = {
    "raw_provider",
    "raw_provider_response",
    "raw_prompt",
    "raw_response",
    "raw_visible_output",
    "raw_reasoning",
    "reasoning",
    "reasoning_content",
    "provider_wrapper_payload",
}


class BrowserActionExtractionError(ValueError):
    def __init__(self, message: str, *, diagnostics: dict[str, Any]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class BrowserActionExtractionResult(SentinelModel):
    envelope: ActionEnvelope
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.safe_identity_payload(),
            "diagnostics": dict(self.diagnostics),
        }


def extract_browser_action_envelope(
    payload: Any,
    *,
    allowed_actions: tuple[str, ...],
    last_successful_browser_action: str | None = None,
) -> BrowserActionExtractionResult:
    diagnostics = _base_diagnostics(payload, last_successful_browser_action=last_successful_browser_action)
    if not isinstance(payload, dict):
        diagnostics["failure_code"] = "MODEL_ACTION_JSON_NOT_OBJECT"
        diagnostics["recommended_next_action"] = _recommended_next_action(allowed_actions)
        raise BrowserActionExtractionError("browser_action_json_not_object", diagnostics=diagnostics)
    if any(key in payload for key in FORBIDDEN_MODEL_MATERIAL_KEYS):
        diagnostics["failure_code"] = "MODEL_ACTION_SCHEMA_INVALID"
        diagnostics["recommended_next_action"] = _recommended_next_action(allowed_actions)
        raise BrowserActionExtractionError("browser_action_forbidden_material", diagnostics=diagnostics)
    action_payload = _action_payload(payload)
    if action_payload is None:
        diagnostics["failure_code"] = "MODEL_ACTION_SCHEMA_INVALID"
        diagnostics["recommended_next_action"] = _recommended_next_action(allowed_actions)
        raise BrowserActionExtractionError("browser_action_missing", diagnostics=diagnostics)
    capability_id, operation = _capability_and_operation(action_payload)
    if not capability_id or not operation:
        diagnostics["failure_code"] = "MODEL_ACTION_SCHEMA_INVALID"
        diagnostics["recommended_next_action"] = _recommended_next_action(allowed_actions)
        raise BrowserActionExtractionError("browser_action_schema_invalid", diagnostics=diagnostics)
    normalized = _normalize_action(capability_id=capability_id, operation=operation)
    if normalized not in allowed_actions:
        diagnostics["action_object_detected"] = True
        diagnostics["failure_code"] = "MODEL_ACTION_NOT_ALLOWED"
        diagnostics["recommended_next_action"] = _recommended_next_action(allowed_actions)
        raise BrowserActionExtractionError("browser_action_not_allowed", diagnostics=diagnostics)
    envelope = ActionEnvelope(
        capability_id=capability_id,
        operation=operation,
        target_ref=_string_or_none(action_payload.get("target_ref")),
        params=dict(action_payload.get("params") or action_payload.get("arguments") or {}),
        decision_ref=_string_or_none(action_payload.get("decision_ref")),
    )
    diagnostics["action_object_detected"] = True
    diagnostics["failure_code"] = None
    diagnostics["recommended_next_action"] = None
    return BrowserActionExtractionResult(envelope=envelope, diagnostics=diagnostics)


def _base_diagnostics(payload: Any, *, last_successful_browser_action: str | None) -> dict[str, Any]:
    top_level_keys = list(payload.keys()) if isinstance(payload, dict) else []
    visible_length = payload.get("visible_content_char_count") if isinstance(payload, dict) else None
    visible_present = bool(visible_length) or bool(_non_metadata_keys(payload) if isinstance(payload, dict) else False)
    return {
        "visible_content_present": visible_present,
        "json_object_detected": isinstance(payload, dict),
        "action_object_detected": False,
        "content_source": payload.get("content_source") or payload.get("content_extraction_source")
        if isinstance(payload, dict)
        else None,
        "top_level_keys": top_level_keys,
        "failure_code": None,
        "recommended_next_action": None,
        "last_successful_browser_action": last_successful_browser_action,
    }


def _non_metadata_keys(payload: dict[str, Any]) -> list[str]:
    return [key for key in payload if key not in SAFE_PROVIDER_METADATA_KEYS]


def _action_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if "action" in payload and isinstance(payload["action"], dict):
        return dict(payload["action"])
    if "decision" in payload and isinstance(payload["decision"], dict):
        return dict(payload["decision"])
    if "tool" in payload or "operation" in payload or "capability_id" in payload:
        return {key: value for key, value in payload.items() if key not in SAFE_PROVIDER_METADATA_KEYS}
    action = payload.get("action")
    if isinstance(action, str):
        return {key: value for key, value in payload.items() if key not in SAFE_PROVIDER_METADATA_KEYS}
    return None


def _capability_and_operation(payload: dict[str, Any]) -> tuple[str, str]:
    capability_id = str(payload.get("capability_id") or "").strip()
    operation = str(payload.get("operation") or payload.get("tool") or payload.get("action") or "").strip()
    if operation in {"observe", "click", "type_text", "select_option", "assert_text", "extract_text", "press_key", "wait_for_text", "wait_for_load", "scroll"}:
        operation = f"real_browser.{operation}"
    if operation.startswith("real_browser.") and not capability_id:
        capability_id = "real_browser_control"
    if operation == "finish" and not capability_id:
        capability_id = "sentinel_loop"
    return capability_id, operation


def _normalize_action(*, capability_id: str, operation: str) -> str:
    return f"{capability_id}.{operation}"


def _recommended_next_action(allowed_actions: tuple[str, ...]) -> str | None:
    for action in allowed_actions:
        if action.startswith("real_browser_control.real_browser.observe"):
            return action
    return allowed_actions[0] if allowed_actions else None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


__all__ = ["BrowserActionExtractionError", "BrowserActionExtractionResult", "extract_browser_action_envelope"]
