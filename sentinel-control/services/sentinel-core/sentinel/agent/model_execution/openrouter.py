from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any

from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.provider import RealModelProvider
from sentinel.agent.model_execution.redaction import text_hash


OPENROUTER_PROVIDER_ID = "openrouter"
OPENROUTER_BACKEND_ID = "openrouter_chat_completions"
OPENROUTER_DEFAULT_MODEL_ID = "deepseek/deepseek-v4-flash:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CREDENTIAL_ENV = "OPENROUTER_API_KEY"


class OpenRouterChatCompletionsProvider(RealModelProvider):
    provider_id = OPENROUTER_PROVIDER_ID
    backend_id = OPENROUTER_BACKEND_ID
    enabled = True
    is_fake_provider = False

    def __init__(
        self,
        *,
        base_url: str = OPENROUTER_BASE_URL,
        credential_env: str = OPENROUTER_CREDENTIAL_ENV,
        default_model_id: str = OPENROUTER_DEFAULT_MODEL_ID,
        reasoning_mode: str = "effort_high_exclude",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential_env = credential_env
        self.default_model_id = default_model_id
        self.reasoning_mode = reasoning_mode
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
        reasoning = self._reasoning_payload()
        if reasoning is not None:
            body["reasoning"] = reasoning
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=timeout.total_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._http_error_response(request, exc)
        except (TimeoutError, socket.timeout):
            return self._error_response(request, ModelExecutionOutcomeClass.TIMEOUT)
        except (urllib.error.URLError, OSError, json.JSONDecodeError, UnicodeDecodeError):
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
            parsed_content = {"raw_text_hash": text_hash(content)}

        if not isinstance(parsed_content, dict):
            return self._error_response(request, ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA)

        reasoning = self._extract_reasoning(message)
        if reasoning is not None:
            parsed_content["reasoning_present"] = True
            parsed_content["reasoning_hash"] = text_hash(reasoning)
        else:
            parsed_content["reasoning_present"] = False
        parsed_content["reasoning_enabled"] = True
        parsed_content["reasoning_excluded_requested"] = True

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

    @staticmethod
    def _extract_reasoning(message: dict[str, Any]) -> str | None:
        for field in ("reasoning_content", "reasoning", "reasoning_details"):
            value = message.get(field)
            if value:
                if isinstance(value, str):
                    return value
                if isinstance(value, list):
                    joined = " ".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in value)
                    return joined if joined else None
                return str(value)
        return None

    def _reasoning_payload(self) -> dict[str, Any] | None:
        if self.reasoning_mode == "none":
            return None
        if self.reasoning_mode == "exclude_only":
            return {"exclude": True}
        return {"exclude": True, "effort": "high"}

    def _http_error_response(self, request: RealModelRequest, exc: urllib.error.HTTPError) -> ProviderModelResponse:
        diagnostic = self._read_http_error_diagnostic(exc)
        if exc.code in (401, 403):
            return self._error_response(request, ModelExecutionOutcomeClass.PROVIDER_ERROR, diagnostic=diagnostic)
        if exc.code == 429:
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

    @staticmethod
    def _read_http_error_diagnostic(exc: urllib.error.HTTPError) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "http_status": exc.code,
            "provider_error_message": _truncate_safely(str(exc.reason or exc.msg or "")),
        }
        try:
            raw_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw_body = ""
        if raw_body:
            try:
                parsed = json.loads(raw_body)
            except json.JSONDecodeError:
                payload["provider_error_body_hash"] = text_hash(raw_body)
                return payload
            error = parsed.get("error") if isinstance(parsed, dict) else None
            if isinstance(error, dict):
                payload["provider_error_type"] = _truncate_safely(str(error.get("type", "")))
                payload["provider_error_code"] = _truncate_safely(str(error.get("code", "")))
                payload["provider_error_message"] = _truncate_safely(str(error.get("message", "")))
            else:
                payload["provider_error_body_hash"] = text_hash(raw_body)
        return payload


def _truncate_safely(value: str, limit: int = 240) -> str:
    return value[:limit]


def _safe_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)
