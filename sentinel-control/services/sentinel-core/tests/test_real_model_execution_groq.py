from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pytest

from sentinel.agent.model_execution import (
    LLMDecisionResultValidator,
    ModelExecutionOutcomeClass,
    ProviderCredentialHandle,
    build_model_execution_receipt,
)
from sentinel.agent.model_execution.groq import GROQ_DEFAULT_MODEL_ID, GroqChatCompletionsProvider
from tests.test_real_model_execution_backend import _request


RAW_PROMPT = 'Return JSON only: {"decision":"continue","rationale":"ok","evidence_refs":[],"confidence":0.9}'
SECRET_VALUE = "unit-test-groq-token-not-real"


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
        return _Response(self.payload, self.status_code)


class _Response:
    def __init__(self, payload: dict[str, Any], status_code: int) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.request = httpx.Request("POST", "https://redacted.invalid")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("provider error", request=self.request, response=httpx.Response(self.status_code, json=self._payload))


def _groq_request():
    return _request().model_copy(
        update={
            "provider_id": "groq",
            "backend": "groq_openai_compatible_chat",
            "runtime": "chat_completions",
            "model_id": GROQ_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 128,
        }
    )


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(provider_id="groq", env_var_name="GROQ_API_KEY", scopes=["model:read"])


def _request_timeout():
    from sentinel.agent.model_execution import ModelTimeoutPolicy

    return ModelTimeoutPolicy(connect_timeout_seconds=3.0, read_timeout_seconds=20.0, total_timeout_seconds=30.0)


def test_groq_missing_key_returns_missing_credential_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    calls: list[Any] = []
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = GroqChatCompletionsProvider().execute(_groq_request(), timeout=_request_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert calls == []


def test_groq_request_uses_exact_model_and_excludes_secret_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_groq_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = GroqChatCompletionsProvider().execute(_groq_request(), timeout=_request_timeout(), credential=_credential())

    body = recorder.calls[0]["json"]
    metadata = _groq_request().serializable_metadata()

    assert body["model"] == GROQ_DEFAULT_MODEL_ID
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert SECRET_VALUE not in str(metadata)
    assert RAW_PROMPT not in str(metadata)
    assert response.error_class is None


def test_groq_response_validates_and_receipt_excludes_sensitive_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(_valid_groq_payload()))

    request = _groq_request()
    response = GroqChatCompletionsProvider().execute(request, timeout=_request_timeout(), credential=_credential())
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


def test_groq_http_errors_are_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient({"error": {"message": "rate limit"}}, status_code=429))

    response = GroqChatCompletionsProvider().execute(_groq_request(), timeout=_request_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.RATE_LIMIT.value
    assert response.content["http_status"] == 429
    assert SECRET_VALUE not in response.model_dump_json()


def test_groq_real_provider_skip_safe() -> None:
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY absent; skipping real Groq call")

    request = _groq_request()
    response = GroqChatCompletionsProvider().execute(request, timeout=_request_timeout(), credential=_credential())
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
        ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
    }:
        dumped = receipt.model_dump_json()
        assert os.environ["GROQ_API_KEY"] not in dumped
        assert request.prompt_text_in_memory_only not in dumped
        pytest.skip(f"real Groq call returned provider outcome: {result.outcome_class.value}")

    assert result.success is True
    dumped = receipt.model_dump_json()
    assert os.environ["GROQ_API_KEY"] not in dumped
    assert request.prompt_text_in_memory_only not in dumped


def _valid_groq_payload() -> dict[str, Any]:
    return {
        "id": "groq_resp_1",
        "model": GROQ_DEFAULT_MODEL_ID,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "decision": "continue",
                            "rationale": "Groq test response validated",
                            "evidence_refs": ["evidence_1"],
                            "confidence": 0.9,
                        }
                    ),
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }
