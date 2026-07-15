from __future__ import annotations

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

_MODEL_SEARCH_ALLOWED_KEYS = frozenset({"query"})


def normalize_model_browser_search_parameters(
    params: Any,
    *,
    fallback_query: str,
) -> dict[str, Any]:
    """Return typed model-originated parameters for real_browser.search.

    The model may provide search text, but it may not smuggle trusted runtime
    fields, authority fields, backend selectors, or raw provider material
    through params. Unknown non-control fields are ignored rather than treated
    as executable instruction.
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
    return {"query": query}


def reject_execution_parameters_for_route(
    parameters: dict[str, Any],
    *,
    capability_id: str,
    operation: str,
    context: str,
) -> None:
    """Validate persisted execution parameters with route-aware data handling."""

    if capability_id == "real_browser_control" and operation == "real_browser.search":
        query = parameters.get("query")
        if isinstance(query, str):
            _reject_secret_like_query(query)
        elif query is not None:
            raise ValueError(f"{context}: browser search query must be text")
        scan_payload = dict(parameters)
        if "query" in scan_payload:
            scan_payload["query"] = "<typed_browser_search_query_data>"
        reject_operator_control_payload(scan_payload, context=context)
        return
    reject_operator_control_payload(parameters, context=context)


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
    if scan_secret_like_text(query, path="$.params.query"):
        raise BrowserSearchParameterBoundaryError("BROWSER_SEARCH_QUERY_SECRET_LIKE")


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")
