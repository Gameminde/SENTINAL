from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from sentinel.agent.model_execution.catalog import ProviderBackendProfile
from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.provider import RealModelProvider
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.shared.models import SentinelModel
from sentinel.shared.safety_scanner import scan_forbidden_payload_flat


class OpenAICompatibleProviderConfig(SentinelModel):
    provider_id: str
    backend_id: str
    base_url: str
    credential_env: str | None
    default_model_id: str
    backend_profile: ProviderBackendProfile
    max_tokens_field: str = "max_completion_tokens"
    reasoning_request: dict[str, Any] | None = None
    enabled: bool = True


class OpenAICompatibleChatProvider(RealModelProvider):
    is_fake_provider = False

    def __init__(self, *, config: OpenAICompatibleProviderConfig) -> None:
        self._config = config
        self.provider_id = config.provider_id
        self.backend_id = config.backend_id
        self.enabled = config.enabled
        self.base_url = config.base_url.rstrip("/")
        self.credential_env = config.credential_env
        self.default_model_id = config.default_model_id
        self.backend_profile = config.backend_profile
        self.supported_models = tuple(config.backend_profile.supported_models)
        self.metadata = {
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "base_url_hash": text_hash(self.base_url),
            "credential_env_hash": text_hash(self.credential_env or ""),
            "profile_runtime": self.backend_profile.runtime,
        }

    def default_timeout_policy(self) -> ModelTimeoutPolicy:
        profile = self.backend_profile.timeout_profile
        return ModelTimeoutPolicy(
            connect_timeout_seconds=profile.connect_timeout_seconds,
            read_timeout_seconds=profile.read_timeout_seconds,
            total_timeout_seconds=profile.total_timeout_seconds,
        )

    def execute(
        self,
        request: RealModelRequest,
        *,
        timeout: ModelTimeoutPolicy,
        credential: ProviderCredentialHandle,
    ) -> ProviderModelResponse | None:
        if request.provider_id != self.provider_id or request.backend_id != self.backend_id:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.DISABLED_BACKEND,
                diagnostic={"rejected_reason": "provider_backend_mismatch"},
            )
        if credential.provider_id != self.provider_id:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.MISSING_CREDENTIAL,
                diagnostic={"rejected_reason": "credential_provider_mismatch"},
            )
        if self.credential_env and credential.source_ref_hash != text_hash(self.credential_env):
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.MISSING_CREDENTIAL,
                diagnostic={"rejected_reason": "credential_source_mismatch"},
            )
        if not self.backend_profile.supports_model(request.model_id):
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.DISABLED_BACKEND,
                diagnostic={"rejected_reason": "unsupported_model"},
            )
        headers = {"Content-Type": "application/json"}
        if self.credential_env:
            api_key = os.environ.get(self.credential_env)
            if not api_key:
                return self._error_response(request, ModelExecutionOutcomeClass.MISSING_CREDENTIAL)
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            with httpx.Client(timeout=_httpx_timeout(timeout)) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=self._request_body(request),
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return self._http_error_response(request, exc)
        except httpx.TimeoutException:
            return self._error_response(request, ModelExecutionOutcomeClass.TIMEOUT)
        except (httpx.RequestError, json.JSONDecodeError, ValueError):
            return self._error_response(request, ModelExecutionOutcomeClass.PROVIDER_ERROR)

        return self.map_payload(request, payload)

    def _request_body(self, request: RealModelRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": request.model_id,
            "messages": [{"role": "user", "content": request.prompt_text_in_memory_only or ""}],
            "stream": False,
            self._config.max_tokens_field: max(1, request.estimated_output_tokens),
            "temperature": 0,
        }
        if (
            request.request_metadata.get("response_format_json_object") is True
            and self.backend_profile.supports_json_mode
        ):
            body["response_format"] = {"type": "json_object"}
        body.update(self._reasoning_body_fields())
        return body

    def _reasoning_body_fields(self) -> dict[str, Any]:
        if self._config.reasoning_request is not None:
            return {"reasoning": self._config.reasoning_request}
        configured = self.backend_profile.reasoning_redaction_policy.request_reasoning_disable_fields
        if not isinstance(configured, dict):
            return {}
        return dict(configured)

    def map_payload(self, request: RealModelRequest, payload: dict[str, Any]) -> ProviderModelResponse:
        try:
            choice = payload["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
                diagnostic={
                    "content_extraction_source": "choices[0].message.content",
                    "content_extraction_error": "missing_choices_or_message",
                },
            )
        if not isinstance(message, dict):
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
                diagnostic={
                    "content_extraction_source": "choices[0].message.content",
                    "content_extraction_error": "message_not_object",
                },
            )

        content = message.get("content")
        if not isinstance(content, str):
            finish_reason, finish_reason_hash = _safe_provider_label(choice.get("finish_reason"))
            diagnostic = {
                "content_extraction_source": "choices[0].message.content",
                "content_extraction_error": "content_not_string",
            }
            if finish_reason:
                diagnostic["finish_reason"] = finish_reason
            if finish_reason_hash:
                diagnostic["finish_reason_hash"] = finish_reason_hash
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
                diagnostic=diagnostic,
            )

        strict_json_only = request.request_metadata.get("strict_json_only") is True
        raw_text_transport = request.request_metadata.get("raw_text_transport")
        raw_text_in_memory_only: str | None = None
        finish_reason, finish_reason_hash = _safe_provider_label(choice.get("finish_reason"))
        output_truncated = finish_reason == "length"
        if raw_text_transport in {"mutation_patch_v2", "read_only_audit_report_v1", "product_model_native_intent_v1"}:
            parsed_content = {
                "raw_text_hash": text_hash(content),
                "raw_text_transport": raw_text_transport,
                "visible_content_char_count": len(content),
                "visible_content_estimated_tokens": max(1, (len(content) + 3) // 4),
                "content_extraction_source": "choices[0].message.content",
                "normalization_strategy": "raw_text_transport",
            }
            raw_text_in_memory_only = content
        else:
            parsed_content = _parse_content(
                content,
                strict_json_only=strict_json_only,
                output_truncated=output_truncated,
            )
        if not isinstance(parsed_content, dict):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        reasoning_text = self._extract_reasoning(message)
        if reasoning_text:
            parsed_content["reasoning_present"] = True
            parsed_content["reasoning_hash"] = text_hash(reasoning_text)
            parsed_content["reasoning_char_count"] = len(reasoning_text)
        elif self.backend_profile.supports_reasoning_controls and "raw_text_hash" not in parsed_content:
            parsed_content["reasoning_present"] = False

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        reasoning_tokens = _safe_int(_get_path({"usage": usage}, self.backend_profile.usage_mapping.reasoning_tokens_path))
        if reasoning_tokens:
            parsed_content["reasoning_token_count"] = reasoning_tokens
        response_id = payload.get("id")
        response_model = payload.get("model")
        if finish_reason_hash:
            parsed_content["finish_reason_hash"] = finish_reason_hash
        if finish_reason:
            parsed_content["finish_reason"] = finish_reason
        parsed_content["output_truncated"] = output_truncated
        if response_model is not None and str(response_model) != request.model_id:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.DISABLED_BACKEND,
                diagnostic={"rejected_reason": "provider_model_mismatch"},
            )
        return ProviderModelResponse(
            provider_id=self.provider_id,
            model_id=request.model_id,
            response_id=text_hash(str(response_id)) if response_id else None,
            content=parsed_content,
            raw_text_in_memory_only=raw_text_in_memory_only,
            refusal=bool(message.get("refusal")),
            finish_reason=finish_reason,
            output_truncated=output_truncated,
            input_tokens=_safe_int(_get_path({"usage": usage}, self.backend_profile.usage_mapping.input_tokens_path)),
            output_tokens=_safe_int(_get_path({"usage": usage}, self.backend_profile.usage_mapping.output_tokens_path)),
        )

    def _extract_reasoning(self, message: dict[str, Any]) -> str | None:
        values: list[str] = []
        for field in self.backend_profile.reasoning_redaction_policy.raw_reasoning_fields:
            if field not in message:
                continue
            value = message.get(field)
            rendered = _render_reasoning_value(value)
            if rendered:
                values.append(rendered)
        return " ".join(values) if values else None

    def _http_error_response(self, request: RealModelRequest, exc: httpx.HTTPStatusError) -> ProviderModelResponse:
        status_code = exc.response.status_code
        diagnostic = _http_error_diagnostic(exc.response)
        if status_code == 429:
            return self._error_response(request, ModelExecutionOutcomeClass.RATE_LIMIT, diagnostic=diagnostic)
        return self._error_response(request, ModelExecutionOutcomeClass.PROVIDER_ERROR, diagnostic=diagnostic)

    def _error_response(
        self,
        request: RealModelRequest,
        outcome_class: ModelExecutionOutcomeClass,
        *,
        diagnostic: dict[str, Any] | None = None,
    ) -> ProviderModelResponse:
        return ProviderModelResponse(
            provider_id=self.provider_id,
            model_id=request.model_id,
            content=diagnostic or {},
            error_class=outcome_class.value,
        )


def _parse_content(
    content: str,
    *,
    strict_json_only: bool = False,
    output_truncated: bool = False,
) -> dict[str, Any]:
    base = {
        "content_extraction_source": "choices[0].message.content",
        "visible_content_char_count": len(content),
        "visible_content_estimated_tokens": max(1, (len(content) + 3) // 4),
    }
    if not content:
        return {
            **base,
            "raw_text_hash": text_hash(content),
            "json_object_detected": False,
            "normalization_strategy": "empty_visible_content",
        }
    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError:
        if strict_json_only:
            return {
                **base,
                "raw_text_hash": text_hash(content),
                "json_object_detected": False,
                "normalization_strategy": "strict_json_rejected",
            }
        parsed_content = _extract_single_allowed_json_object(content, output_truncated=output_truncated)
        if parsed_content is None:
            return {
                **base,
                "raw_text_hash": text_hash(content),
                "json_object_detected": False,
                "normalization_strategy": "truncated_or_invalid_json"
                if output_truncated
                else "no_json_object_detected",
                "multiple_json_objects_detected": _looks_like_multiple_json_objects(content),
                "markdown_fence_detected": _has_markdown_fence(content),
            }
        return {
            **parsed_content,
            **base,
        }
    if not isinstance(parsed_content, dict):
        return {
            **base,
            "raw_text_hash": text_hash(content),
            "json_object_detected": False,
            "normalization_strategy": "json_value_not_object",
        }
    return {
        **parsed_content,
        **base,
        "json_object_detected": True,
        "normalization_strategy": "plain_json_object",
    }


def _extract_single_allowed_json_object(content: str, *, output_truncated: bool) -> dict[str, Any] | None:
    stripped = content.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence_match is not None:
        inner = fence_match.group(1)
        try:
            parsed = json.loads(inner)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return {
                **parsed,
                "json_object_detected": True,
                "markdown_fence_detected": True,
                "normalization_strategy": "single_json_markdown_fence",
            }
        return None
    if output_truncated or _looks_like_multiple_json_objects(content):
        return None
    return None


def _looks_like_multiple_json_objects(content: str) -> bool:
    return re.search(r"\}\s*\{", content.strip()) is not None


def _has_markdown_fence(content: str) -> bool:
    return "```" in content


def _render_reasoning_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        rendered_items = [
            str(item.get("text", item)) if isinstance(item, dict) else str(item)
            for item in value
        ]
        joined = " ".join(item for item in rendered_items if item)
        return joined or None
    return str(value)


def _httpx_timeout(timeout: ModelTimeoutPolicy) -> httpx.Timeout:
    return httpx.Timeout(
        timeout.total_timeout_seconds,
        connect=timeout.connect_timeout_seconds,
        read=timeout.read_timeout_seconds,
        write=timeout.connect_timeout_seconds,
        pool=timeout.connect_timeout_seconds,
    )


def _http_error_diagnostic(response: httpx.Response) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {"http_status": response.status_code}
    try:
        parsed = response.json()
    except ValueError:
        diagnostic["provider_error_body_hash"] = text_hash(response.text)
        return diagnostic
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict):
        error_type, error_type_hash = _safe_provider_label(error.get("type"), max_len=240)
        error_code, error_code_hash = _safe_provider_label(error.get("code"), max_len=240)
        diagnostic["provider_error_type"] = error_type or ""
        diagnostic["provider_error_code"] = error_code or ""
        if error_type_hash:
            diagnostic["provider_error_type_hash"] = error_type_hash
        if error_code_hash:
            diagnostic["provider_error_code_hash"] = error_code_hash
        message = str(error.get("message", ""))
        if message:
            diagnostic["provider_error_message_hash"] = text_hash(message)
            diagnostic["provider_error_message_redacted"] = True
    else:
        diagnostic["provider_error_body_hash"] = text_hash(json.dumps(parsed, sort_keys=True))
    return diagnostic


def _get_path(payload: dict[str, Any], path: str | None) -> Any:
    if not path:
        return None
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _safe_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _safe_provider_label(value: Any, *, max_len: int = 120) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    rendered_full = str(value)
    rendered = rendered_full[:max_len]
    if scan_forbidden_payload_flat(rendered_full, path="$.provider_label"):
        return "unsafe_provider_label", text_hash(rendered_full)
    return rendered, None
