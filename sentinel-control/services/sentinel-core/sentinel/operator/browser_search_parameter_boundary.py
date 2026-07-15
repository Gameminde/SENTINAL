from __future__ import annotations

import json
from typing import Any

from sentinel.operator.safety import reject_operator_control_payload
from sentinel.shared.safety_scanner import scan_secret_like_text


class BrowserSearchParameterBoundaryError(ValueError):
    pass


_CONTROL_PLANE_PARAM_KEYS = frozenset(
    {
        "action",
        "adapter_id",
        "allowed_actions",
        "allowed_domains",
        "allowed_paths",
        "authority",
        "authority_effect",
        "authority_envelope",
        "authority_envelope_ref",
        "authority_ref",
        "backend_id",
        "backend_override",
        "can_execute",
        "can_grant_authority",
        "capability_id",
        "chain_of_thought",
        "cookie",
        "credential",
        "credential_value",
        "data_not_authority",
        "engine_profile",
        "execution_effect",
        "fallback",
        "idempotency_key",
        "kernel",
        "mission_id",
        "model_override",
        "operation",
        "organ_id",
        "password",
        "profile_material",
        "provider_native",
        "provider_native_tools",
        "provider_override",
        "provider_response",
        "raw_dom",
        "raw_prompt",
        "raw_provider_output",
        "raw_provider_response",
        "raw_reasoning",
        "raw_response",
        "reasoning",
        "session",
        "session_cookie",
        "session_id",
        "session_token",
        "target_ref",
        "tool_calls",
        "workspace_ref",
    }
)

_MODEL_SEARCH_ALLOWED_KEYS = frozenset({"model_extensions", "query"})
_MAX_MODEL_EXTENSION_DEPTH = 4
_MAX_MODEL_EXTENSION_ITEMS = 32
_MAX_MODEL_EXTENSION_STRING_LENGTH = 1200
_MAX_MODEL_EXTENSIONS_BYTES = 4096
_MAX_TYPED_LOOP_CONTEXT_BYTES = 131_072
_MAX_TYPED_LOOP_CONTEXT_DEPTH = 9
_MAX_TYPED_LOOP_CONTEXT_ITEMS = 256
_MAX_TYPED_LOOP_CONTEXT_STRING_LENGTH = 4000

_TYPED_LOOP_CONTEXT_OPERATIONS = frozenset(
    {
        "real_browser.extract_product_cards",
        "real_browser.extract_evidence",
        "real_browser.extract_entities",
        "real_browser.verify_extraction",
        "summarize_evidence",
    }
)

_LOOP_CONTEXT_ROOT_KEYS = frozenset(
    {
        "BrowserEnvironmentState",
        "actionability_frame",
        "bounded_observation_summaries",
        "browser_actionability_registry",
        "browser_backend_execution",
        "browser_cognitive_decision_frame",
        "browser_decision_frame",
        "browser_devtools_context",
        "browser_environment_state",
        "browser_environment_state_hash",
        "browser_observation_bundle",
        "browser_recovery_evidence",
        "browser_search_materiality",
        "browser_world_model",
        "browser_world_model_summary",
        "can_execute",
        "can_grant_authority",
        "completion_requirements",
        "contradictions",
        "data_not_authority",
        "evidence_summaries",
        "grounded_evidence_summary",
        "model_blocker_assessment",
        "model_blocker_assessment_schema",
        "model_extensions",
        "model_visible_body_failure_packet",
        "mission_objective",
        "objective_satisfied",
        "progress_state",
        "real_browser_control_summary",
        "recoverable_action_observations",
        "runtime_failure_fact",
        "search_actuation_trace",
        "unknowns",
    }
)

_LOOP_CONTEXT_FORBIDDEN_KEYS = frozenset(
    {
        "allowed_actions",
        "allowed_domains",
        "allowed_paths",
        "authority",
        "authority_envelope",
        "authority_envelope_ref",
        "authority_ref",
        "backend_override",
        "cookie",
        "credential",
        "credential_value",
        "engine_profile",
        "fallback",
        "idempotency_key",
        "kernel",
        "mission_id",
        "model_override",
        "password",
        "profile_material",
        "provider_native",
        "provider_native_tools",
        "provider_override",
        "provider_response",
        "raw_dom",
        "raw_prompt",
        "raw_provider_output",
        "raw_provider_response",
        "raw_reasoning",
        "raw_response",
        "reasoning",
        "session_cookie",
        "session_id",
        "session_token",
        "tool_calls",
        "workspace_ref",
    }
)


def normalize_model_browser_search_parameters(
    params: Any,
    *,
    fallback_query: str,
) -> dict[str, Any]:
    """Return typed model-originated parameters for real_browser.search.

    The model may provide search text, but it may not smuggle trusted runtime
    fields, authority fields, backend selectors, or raw provider material
    through params. Unknown non-control fields remain available to the model as
    inert semantic extensions; they are never unpacked into executor arguments.
    """

    if params is None:
        raw_params: dict[str, Any] = {}
    elif isinstance(params, dict):
        raw_params = dict(params)
    else:
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_PARAMETERS_NOT_OBJECT")
    _reject_control_plane_keys(raw_params, path="$.params")
    query_value = raw_params.get("query")
    if query_value is None or str(query_value).strip() == "":
        query = str(fallback_query or "").strip() or "mission objective"
    elif isinstance(query_value, str):
        query = query_value.strip()
    else:
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_QUERY_NOT_TEXT")
    _reject_secret_like_query(query)
    normalized: dict[str, Any] = {"query": query}
    extensions = _normalize_model_extensions(raw_params)
    if extensions:
        normalized["model_extensions"] = extensions
    return normalized


def reject_execution_parameters_for_route(
    parameters: dict[str, Any],
    *,
    capability_id: str,
    operation: str,
    context: str,
) -> None:
    """Validate persisted execution parameters with route-aware data handling."""

    if capability_id == "real_browser_control" and operation == "real_browser.search":
        scan_payload = typed_browser_search_scan_payload(parameters, context=context)
        reject_operator_control_payload(scan_payload, context=context)
        return
    if (
        "loop_context" in parameters
        and (
            (capability_id == "real_browser_control" and operation in _TYPED_LOOP_CONTEXT_OPERATIONS)
            or (capability_id == "sentinel_loop" and operation == "summarize_evidence")
        )
    ):
        scan_payload = typed_loop_context_scan_payload(parameters, context=context)
        reject_operator_control_payload(scan_payload, context=context)
        return
    reject_operator_control_payload(parameters, context=context)


def typed_browser_search_scan_payload(parameters: dict[str, Any], *, context: str) -> dict[str, Any]:
    """Return a control-scan-safe view of typed browser search parameters.

    The typed operation is the authority-bearing fact. The query and model
    extensions are semantic data; they are scanned for actual secret values and
    control-plane keys, then masked before broader lexical payload scanners run.
    """

    scan_payload = dict(parameters)
    query = scan_payload.get("query")
    if isinstance(query, str):
        reject_typed_browser_search_semantic_text(query, path="$.params.query")
        scan_payload["query"] = "<typed_browser_search_query_data>"
    elif query is not None:
        raise ValueError(f"{context}: browser search query must be text")
    if "model_extensions" in scan_payload:
        _validate_model_extension_value(scan_payload["model_extensions"], path="$.params.model_extensions", depth=0)
        _validate_model_extensions_size(scan_payload["model_extensions"])
        scan_payload["model_extensions"] = "<typed_browser_search_model_extensions_data>"
    return scan_payload


def typed_loop_context_scan_payload(parameters: dict[str, Any], *, context: str) -> dict[str, Any]:
    """Return a control-scan-safe view for model-visible loop context.

    Loop context is evidence and semantic state carried to the next model turn.
    It is not executor arguments and it cannot grant authority. We therefore
    scan it for actual secrets and trusted-control override attempts, then mask
    it before the legacy lexical operator scanner sees topic words such as
    "login" or "download" inside ordinary mission text.
    """

    scan_payload = dict(parameters)
    loop_context = scan_payload.get("loop_context")
    if loop_context is None:
        return scan_payload
    if not isinstance(loop_context, dict):
        raise ValueError(f"{context}: typed loop_context must be an object")
    _validate_typed_loop_context(loop_context, path="$.params.loop_context", depth=0, root=True)
    _validate_typed_loop_context_size(loop_context, context=context)
    scan_payload["loop_context"] = "<typed_loop_context_semantic_data>"
    return scan_payload


def reject_typed_browser_search_semantic_text(value: str, *, path: str = "$.params.query") -> None:
    """Reject real secret values in search semantic data without topic policing."""

    if scan_secret_like_text(value, path=path):
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_QUERY_SECRET_LIKE")


def _validate_typed_loop_context(value: Any, *, path: str, depth: int, root: bool = False) -> None:
    if depth > _MAX_TYPED_LOOP_CONTEXT_DEPTH:
        raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_TOO_DEEP")
    if isinstance(value, dict):
        if len(value) > _MAX_TYPED_LOOP_CONTEXT_ITEMS:
            raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_TOO_MANY_ITEMS")
        for key, item in value.items():
            key_text = str(key)
            normalized_key = _normalize_key(key)
            child_path = f"{path}.{key_text}"
            if root and key_text not in _LOOP_CONTEXT_ROOT_KEYS:
                raise BrowserSearchParameterBoundaryError(f"TYPED_LOOP_CONTEXT_ROOT_KEY_UNSUPPORTED:{child_path}")
            _validate_typed_loop_context_key(normalized_key, item, path=child_path)
            _validate_typed_loop_context(item, path=child_path, depth=depth + 1)
        return
    if isinstance(value, list | tuple | set):
        if len(value) > _MAX_TYPED_LOOP_CONTEXT_ITEMS:
            raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_TOO_MANY_ITEMS")
        for index, item in enumerate(value):
            _validate_typed_loop_context(item, path=f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, str):
        if len(value) > _MAX_TYPED_LOOP_CONTEXT_STRING_LENGTH:
            raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_STRING_TOO_LONG")
        if scan_secret_like_text(value, path=path):
            raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_SECRET_LIKE")
        return
    if value is None or isinstance(value, bool | int | float):
        return
    raise BrowserSearchParameterBoundaryError("TYPED_LOOP_CONTEXT_NOT_DATA")


def _validate_typed_loop_context_key(normalized_key: str, value: Any, *, path: str) -> None:
    if _is_semantic_decision_frame_key(normalized_key, path=path):
        return
    if normalized_key in {"data_not_authority"}:
        if value is not True:
            raise BrowserSearchParameterBoundaryError(f"TYPED_LOOP_CONTEXT_DATA_AUTHORITY_VIOLATION:{path}")
        return
    if normalized_key in {"can_execute", "can_grant_authority", "can_approve_future_execution"}:
        if value is not False:
            raise BrowserSearchParameterBoundaryError(f"TYPED_LOOP_CONTEXT_TRUSTED_BOOL_OVERRIDE:{path}")
        return
    if normalized_key in {"authority_effect", "execution_effect"}:
        if str(value or "none") != "none":
            raise BrowserSearchParameterBoundaryError(f"TYPED_LOOP_CONTEXT_EFFECT_OVERRIDE:{path}")
        return
    if normalized_key in _LOOP_CONTEXT_FORBIDDEN_KEYS:
        raise BrowserSearchParameterBoundaryError(f"TYPED_LOOP_CONTEXT_CONTROL_PLANE_KEY:{path}")


def _is_semantic_decision_frame_key(normalized_key: str, *, path: str) -> bool:
    if normalized_key not in {"allowed_actions", "available_actions", "forbidden_actions"}:
        return False
    semantic_markers = (
        ".browser_decision_frame.",
        ".browser_cognitive_decision_frame.",
        ".browser_actionability_registry.",
        ".actionability_frame.",
        ".completion_requirements.",
    )
    return any(marker in path for marker in semantic_markers)


def _validate_typed_loop_context_size(value: dict[str, Any], *, context: str) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > _MAX_TYPED_LOOP_CONTEXT_BYTES:
        raise ValueError(f"{context}: typed loop_context too large")


def _reject_control_plane_keys(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            child_path = f"{path}.{key}"
            if normalized_key in _CONTROL_PLANE_PARAM_KEYS:
                raise BrowserSearchParameterBoundaryError(
                    f"BROWSER_SEARCH_CONTROL_PLANE_PARAM:{child_path}"
                )
            if normalized_key not in _MODEL_SEARCH_ALLOWED_KEYS:
                # Unknown model-originated fields are ignored at the boundary,
                # but their nested content still cannot hide control-plane keys.
                _reject_control_plane_keys(item, path=child_path)
                continue
            _reject_control_plane_keys(item, path=child_path)
        return
    if isinstance(value, list | tuple | set):
        for index, item in enumerate(value):
            _reject_control_plane_keys(item, path=f"{path}[{index}]")


def _reject_secret_like_query(query: str) -> None:
    reject_typed_browser_search_semantic_text(query)


def _normalize_model_extensions(raw_params: dict[str, Any]) -> dict[str, Any]:
    extensions: dict[str, Any] = {}
    explicit = raw_params.get("model_extensions")
    if explicit is not None:
        if not isinstance(explicit, dict):
            raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_NOT_OBJECT")
        for key, value in explicit.items():
            extensions[str(key)] = _normalize_model_extension_value(
                value,
                path=f"$.params.model_extensions.{key}",
                depth=1,
            )
    for key, value in raw_params.items():
        normalized_key = _normalize_key(key)
        if normalized_key in _MODEL_SEARCH_ALLOWED_KEYS:
            continue
        extensions[str(key)] = _normalize_model_extension_value(
            value,
            path=f"$.params.{key}",
            depth=1,
        )
    if extensions:
        _validate_model_extensions_size(extensions)
    return extensions


def _normalize_model_extension_value(value: Any, *, path: str, depth: int) -> Any:
    _validate_model_extension_value(value, path=path, depth=depth)
    if isinstance(value, dict):
        return {
            str(key): _normalize_model_extension_value(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
            for key, item in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [
            _normalize_model_extension_value(item, path=f"{path}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    return value


def _validate_model_extension_value(value: Any, *, path: str, depth: int) -> None:
    if depth > _MAX_MODEL_EXTENSION_DEPTH:
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_TOO_DEEP")
    if isinstance(value, dict):
        if len(value) > _MAX_MODEL_EXTENSION_ITEMS:
            raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_TOO_MANY_ITEMS")
        _reject_control_plane_keys(value, path=path)
        for key, item in value.items():
            _validate_model_extension_value(item, path=f"{path}.{key}", depth=depth + 1)
        return
    if isinstance(value, list | tuple | set):
        if len(value) > _MAX_MODEL_EXTENSION_ITEMS:
            raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_TOO_MANY_ITEMS")
        for index, item in enumerate(value):
            _validate_model_extension_value(item, path=f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, str):
        if len(value) > _MAX_MODEL_EXTENSION_STRING_LENGTH:
            raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_STRING_TOO_LONG")
        if scan_secret_like_text(value, path=path):
            raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_SECRET_LIKE")
        return
    if value is None or isinstance(value, bool | int | float):
        return
    raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_NOT_DATA")


def _validate_model_extensions_size(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > _MAX_MODEL_EXTENSIONS_BYTES:
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_MODEL_EXTENSIONS_TOO_LARGE")


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")
