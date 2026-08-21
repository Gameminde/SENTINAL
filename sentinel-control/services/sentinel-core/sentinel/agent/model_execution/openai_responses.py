from __future__ import annotations

import json
import os
from typing import Any

import httpx

from sentinel.agent.model_execution.catalog import ProviderBackendProfile
from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.openai_compatible import (
    _get_path,
    _http_error_diagnostic,
    _httpx_timeout,
    _local_provider_error_diagnostic,
    _parse_content,
    _safe_int,
    _safe_provider_label,
    _transport_error_diagnostic,
)
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.provider import RealModelProvider
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.shared.models import SentinelModel


class OpenAIResponsesProviderConfig(SentinelModel):
    provider_id: str
    backend_id: str
    endpoint_url: str
    credential_env: str | None
    default_model_id: str
    backend_profile: ProviderBackendProfile
    enabled: bool = True


class OpenAIResponsesProvider(RealModelProvider):
    is_fake_provider = False

    def __init__(self, *, config: OpenAIResponsesProviderConfig) -> None:
        self._config = config
        self.provider_id = config.provider_id
        self.backend_id = config.backend_id
        self.enabled = config.enabled
        self.endpoint_url = config.endpoint_url.rstrip("/")
        self.credential_env = config.credential_env
        self.default_model_id = config.default_model_id
        self.backend_profile = config.backend_profile
        self.supported_models = tuple(config.backend_profile.supported_models)
        self.metadata = {
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "endpoint_hash": text_hash(self.endpoint_url),
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
                    self.endpoint_url,
                    headers=headers,
                    json=self._request_body(request),
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return self._http_error_response(request, exc)
        except httpx.TimeoutException:
            return self._error_response(request, ModelExecutionOutcomeClass.TIMEOUT)
        except httpx.RequestError as exc:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.PROVIDER_ERROR,
                diagnostic=_transport_error_diagnostic(exc),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.PROVIDER_ERROR,
                diagnostic=_local_provider_error_diagnostic(exc),
            )

        return self.map_payload(request, payload)

    def _request_body(self, request: RealModelRequest) -> dict[str, Any]:
        return {
            "model": request.model_id,
            "input": request.prompt_text_in_memory_only or "",
            "stream": False,
            "max_output_tokens": max(1, request.estimated_output_tokens),
        }

    def map_payload(self, request: RealModelRequest, payload: dict[str, Any]) -> ProviderModelResponse:
        content = _extract_response_text(payload)
        if content is None:
            return self._error_response(
                request,
                ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
                diagnostic={
                    "content_extraction_source": "output_text|output[].content[].text",
                    "content_extraction_error": "missing_response_text",
                },
            )

        strict_json_only = request.request_metadata.get("strict_json_only") is True
        raw_text_transport = request.request_metadata.get("raw_text_transport")
        raw_text_in_memory_only: str | None = None
        finish_reason, finish_reason_hash = _safe_provider_label(_extract_finish_reason(payload))
        output_truncated = finish_reason == "length"
        if raw_text_transport in {"mutation_patch_v2", "read_only_audit_report_v1", "product_model_native_intent_v1"}:
            parsed_content = {
                "raw_text_hash": text_hash(content),
                "raw_text_transport": raw_text_transport,
                "visible_content_char_count": len(content),
                "visible_content_estimated_tokens": max(1, (len(content) + 3) // 4),
                "content_extraction_source": "responses.output_text",
                "normalization_strategy": "raw_text_transport",
            }
            raw_text_in_memory_only = content
        else:
            parsed_content = _parse_content(content, strict_json_only=strict_json_only, output_truncated=output_truncated)
        if not isinstance(parsed_content, dict):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
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
            finish_reason=finish_reason,
            output_truncated=output_truncated,
            input_tokens=_safe_int(_get_path({"usage": usage}, self.backend_profile.usage_mapping.input_tokens_path)),
            output_tokens=_safe_int(_get_path({"usage": usage}, self.backend_profile.usage_mapping.output_tokens_path)),
        )

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


def _extract_response_text(payload: dict[str, Any]) -> str | None:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts) if parts else None


def _extract_finish_reason(payload: dict[str, Any]) -> str | None:
    status = payload.get("status")
    if isinstance(status, str) and status:
        return status
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            finish_reason = item.get("finish_reason")
            if isinstance(finish_reason, str) and finish_reason:
                return finish_reason
    return None
