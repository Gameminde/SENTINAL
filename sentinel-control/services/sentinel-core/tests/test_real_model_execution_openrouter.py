from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pytest

from sentinel.agent.model_execution import (
    EnvironmentCredentialResolver,
    LLMDecisionResultValidator,
    ModelExecutionOutcomeClass,
    ModelProviderRegistry,
    ProviderCredentialHandle,
    build_model_execution_receipt,
)
from sentinel.agent.model_execution.openrouter import (
    OPENROUTER_DEFAULT_MODEL_ID,
    OpenRouterChatCompletionsProvider,
)
from sentinel.agent.model_execution.receipts import build_model_execution_receipt
from sentinel.agent.model_execution.redaction import text_hash
from tests.test_real_model_execution_backend import _request


RAW_PROMPT = "Return JSON for strawberry without leaking this raw prompt."
SECRET_VALUE = "unit-test-openrouter-token-not-real"


class RecordingHttpxClient:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *_args: Any, **_kwargs: Any) -> RecordingHttpxClient:
        return self

    def __enter__(self) -> RecordingHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _Response(self.payload, status_code=self.status_code)


class TimeoutHttpxClient:
    def __call__(self, *_args: Any, **_kwargs: Any) -> TimeoutHttpxClient:
        return self

    def __enter__(self) -> TimeoutHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, *_args: Any, **_kwargs: Any) -> Any:
        raise httpx.TimeoutException("timeout without key")


class _Response:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.request = httpx.Request("POST", "https://redacted.invalid")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=httpx.Response(self.status_code, json=self._payload),
            )


def _openrouter_request():
    request = _request().model_copy(
        update={
            "provider_id": "openrouter",
            "backend": "openrouter_chat_completions",
            "runtime": "chat_completions",
            "model_id": OPENROUTER_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
        }
    )
    return request


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id="openrouter",
        env_var_name="OPENROUTER_API_KEY",
        scopes=["model:read"],
    )


def test_openrouter_missing_api_key_returns_missing_credential_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    calls: list[Any] = []
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: calls.append((args, kwargs)))

    provider = OpenRouterChatCompletionsProvider()
    response = provider.execute(_openrouter_request(), timeout=_request_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content == {}
    assert calls == []


def test_openrouter_provider_metadata_and_request_exclude_raw_prompt_and_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_openrouter_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    call = recorder.calls[0]
    body = call["json"]
    headers = call["headers"]
    metadata = _openrouter_request().serializable_metadata()

    assert body["model"] == OPENROUTER_DEFAULT_MODEL_ID
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert body["stream"] is False
    assert body["reasoning"] == {"exclude": True, "effort": "high"}
    assert "Authorization" in headers
    assert SECRET_VALUE not in str(metadata)
    assert RAW_PROMPT not in str(metadata)
    assert response.error_class is None


def test_openrouter_reasoning_fields_are_hash_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    payload = _valid_openrouter_payload(
        message_extra={
            "reasoning_details": [{"text": "sensitive hidden reasoning"}],
            "reasoning_content": "sensitive hidden reasoning",
        }
    )
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(payload))

    response = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.content["reasoning_present"] is True
    assert response.content["reasoning_hash"] == text_hash("sensitive hidden reasoning sensitive hidden reasoning")
    assert "reasoning_details" not in response.content
    assert "reasoning_content" not in response.content
    assert "sensitive hidden reasoning" not in response.model_dump_json()


def test_openrouter_fake_response_marker_cannot_satisfy_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient({"fake_response": True}))

    response = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )
    result = LLMDecisionResultValidator.validate(response)

    assert result.success is False
    assert result.outcome_class is ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA


def test_openrouter_response_validates_and_receipt_excludes_sensitive_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(_valid_openrouter_payload()))

    request = _openrouter_request()
    response = OpenRouterChatCompletionsProvider().execute(
        request,
        timeout=_request_timeout(),
        credential=_credential(),
    )
    result = LLMDecisionResultValidator.validate(response)
    receipt = build_model_execution_receipt(
        request=request,
        outcome_class=result.outcome_class,
        result=result,
        credential=_credential(),
        attempts=1,
    )

    assert result.success is True
    dumped = receipt.model_dump_json()
    assert SECRET_VALUE not in dumped
    assert RAW_PROMPT not in dumped
    assert "reasoning_details" not in dumped


def test_openrouter_rate_limit_and_timeout_map_to_structured_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient({"error": {"message": "rate limited"}}, status_code=429))
    rate_limited = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )
    assert rate_limited.error_class == ModelExecutionOutcomeClass.RATE_LIMIT.value

    monkeypatch.setattr("httpx.Client", TimeoutHttpxClient())
    timeout = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )
    assert timeout.error_class == ModelExecutionOutcomeClass.TIMEOUT.value


def test_openrouter_http_error_diagnostic_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    monkeypatch.setattr(
        "httpx.Client",
        RecordingHttpxClient(
            {
                "error": {
                    "message": "Provider rejected reasoning parameter",
                    "type": "invalid_request_error",
                    "code": "bad_request",
                }
            },
            status_code=400,
        ),
    )

    response = OpenRouterChatCompletionsProvider().execute(
        _openrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value
    assert response.content["http_status"] == 400
    assert response.content["provider_error_type"] == "invalid_request_error"
    assert response.content["provider_error_code"] == "bad_request"
    assert response.content["provider_error_message"] == "Provider rejected reasoning parameter"
    assert SECRET_VALUE not in response.model_dump_json()


def test_openrouter_registry_and_missing_credential_path_stays_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = OpenRouterChatCompletionsProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    resolver = EnvironmentCredentialResolver(
        {"openrouter": {"env_var": "OPENROUTER_API_KEY", "scopes": ["model:read"]}}
    )

    assert registry.get_enabled("openrouter", model_id=OPENROUTER_DEFAULT_MODEL_ID) is provider
    resolved = resolver.resolve(provider_id="openrouter", required_scopes=["model:read"])
    assert resolved.outcome_class is ModelExecutionOutcomeClass.MISSING_CREDENTIAL


def test_openrouter_real_provider_skip_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY absent; skipping real OpenRouter call")

    request = _openrouter_request().model_copy(
        update={
            "prompt_text_in_memory_only": (
                "Return JSON only with decision, rationale, and evidence_refs for: "
                "count letters in strawberry."
            )
        }
    )
    response = _execute_real_openrouter_variant(request, reasoning_mode="effort_high_exclude")
    if response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value:
        response = _execute_real_openrouter_variant(request, reasoning_mode="exclude_only")
    if response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value:
        response = _execute_real_openrouter_variant(request, reasoning_mode="none")
    result = LLMDecisionResultValidator.validate(response)
    receipt = build_model_execution_receipt(
        request=request,
        outcome_class=result.outcome_class,
        result=result,
        credential=_credential(),
        attempts=1,
    )

    if result.outcome_class in {
        ModelExecutionOutcomeClass.RATE_LIMIT,
        ModelExecutionOutcomeClass.TIMEOUT,
        ModelExecutionOutcomeClass.PROVIDER_ERROR,
    }:
        dumped = receipt.model_dump_json()
        assert os.environ["OPENROUTER_API_KEY"] not in dumped
        assert request.prompt_text_in_memory_only not in dumped
        assert "reasoning_details" not in dumped
        pytest.skip(f"real OpenRouter call returned provider outcome: {result.outcome_class.value}")

    assert response.error_class is None
    assert result.success is True
    dumped = receipt.model_dump_json()
    assert os.environ["OPENROUTER_API_KEY"] not in dumped
    assert request.prompt_text_in_memory_only not in dumped
    assert "reasoning_details" not in dumped


def _execute_real_openrouter_variant(request, *, reasoning_mode: str):
    return OpenRouterChatCompletionsProvider(reasoning_mode=reasoning_mode).execute(
        request,
        timeout=_request_timeout(),
        credential=_credential(),
    )


def _request_timeout():
    from sentinel.agent.model_execution import ModelTimeoutPolicy

    return ModelTimeoutPolicy(connect_timeout_seconds=1.0, read_timeout_seconds=2.0, total_timeout_seconds=3.0)


def _valid_openrouter_payload(message_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": json.dumps(
            {
                "decision": "continue",
                "rationale": "letters counted from compact prompt",
                "evidence_refs": ["evidence_1"],
                "confidence": 0.8,
            }
        ),
    }
    if message_extra:
        message.update(message_extra)
    return {
        "id": "or_resp_1",
        "model": OPENROUTER_DEFAULT_MODEL_ID,
        "choices": [{"finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 10, "total_tokens": 22},
    }
