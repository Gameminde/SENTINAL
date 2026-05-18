from __future__ import annotations

import json
import os
from typing import Any

import httpx

from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.provider import RealModelProvider
from sentinel.agent.model_execution.redaction import text_hash


GROQ_PROVIDER_ID = "groq"
GROQ_BACKEND_ID = "groq_openai_compatible_chat"
GROQ_DEFAULT_MODEL_ID = "openai/gpt-oss-20b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CREDENTIAL_ENV = "GROQ_API_KEY"


class GroqChatCompletionsProvider(RealModelProvider):
    provider_id = GROQ_PROVIDER_ID
    backend_id = GROQ_BACKEND_ID
    enabled = True
    is_fake_provider = False

    def __init__(
        self,
        *,
        base_url: str = GROQ_BASE_URL,
        credential_env: str = GROQ_CREDENTIAL_ENV,
        default_model_id: str = GROQ_DEFAULT_MODEL_ID,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential_env = credential_env
        self.default_model_id = default_model_id
        self.supported_models = (default_model_id,)
        self.metadata = {
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "base_url_hash": text_hash(self.base_url),
            "credential_env_hash": text_hash(self.credential_env),
        }

    def execute(
        self,
        request: RealModelRequest,
        *,
        timeout: ModelTimeoutPolicy,
        credential: ProviderCredentialHandle,
    ) -> ProviderModelResponse | None:
        api_key = os.environ.get(self.credential_env)
        if not api_key:
            return self._error_response(request, ModelExecutionOutcomeClass.MISSING_CREDENTIAL)

        body = {
            "model": request.model_id,
            "messages": [{"role": "user", "content": request.prompt_text_in_memory_only or ""}],
            "stream": False,
            "max_completion_tokens": max(1, request.estimated_output_tokens),
            "temperature": 0,
        }

        try:
            with httpx.Client(timeout=_httpx_timeout(timeout)) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            return self._http_error_response(request, exc)
        except httpx.TimeoutException:
            return self._error_response(request, ModelExecutionOutcomeClass.TIMEOUT)
        except (httpx.RequestError, json.JSONDecodeError, ValueError):
            return self._error_response(request, ModelExecutionOutcomeClass.PROVIDER_ERROR)

        return self._map_payload(request, payload)

    def _map_payload(self, request: RealModelRequest, payload: dict[str, Any]) -> ProviderModelResponse:
        try:
            choice = payload["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        content = message.get("content")
        if not isinstance(content, str):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            parsed_content = _extract_json_object(content)
            if parsed_content is None:
                parsed_content = {"raw_text_hash": text_hash(content)}

        if not isinstance(parsed_content, dict):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return ProviderModelResponse(
            provider_id=self.provider_id,
            model_id=str(payload.get("model") or request.model_id),
            response_id=text_hash(str(payload.get("id"))) if payload.get("id") else None,
            content=parsed_content,
            refusal=bool(message.get("refusal")),
            input_tokens=_safe_int(usage.get("prompt_tokens")),
            output_tokens=_safe_int(usage.get("completion_tokens")),
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


def _extract_json_object(content: str) -> dict[str, Any] | None:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


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
        diagnostic["provider_error_type"] = str(error.get("type", ""))[:240]
        diagnostic["provider_error_code"] = str(error.get("code", ""))[:240]
        diagnostic["provider_error_message"] = str(error.get("message", ""))[:240]
    else:
        diagnostic["provider_error_body_hash"] = text_hash(json.dumps(parsed, sort_keys=True))
    return diagnostic


def _safe_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)
