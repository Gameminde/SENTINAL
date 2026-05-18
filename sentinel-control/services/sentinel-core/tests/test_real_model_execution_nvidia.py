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
from sentinel.agent.model_execution.nvidia import (
    NVIDIA_DEFAULT_MODEL_ID,
    NvidiaChatCompletionsProvider,
)
from tests.test_real_model_execution_backend import _request


RAW_PROMPT = (
    'Return exactly this JSON object: {"decision":"continue","rationale":"ok","evidence_refs":[],"confidence":0.9}'
)
SECRET_VALUE = "unit-test-nvidia-token-not-real"


class RecordingUrlOpen:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.calls: list[Any] = []

    def __call__(self, *_args: Any, **_kwargs: Any) -> RecordingUrlOpen:
        return self

    def __enter__(self) -> RecordingUrlOpen:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _Response(self.payload, status_code=self.status_code)


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
            raise httpx.HTTPStatusError("provider error", request=self.request, response=httpx.Response(self.status_code, json=self._payload))


def _nvidia_request():
    return _request().model_copy(
        update={
            "provider_id": "nvidia",
            "backend": "nvidia_openai_compatible_chat",
            "runtime": "chat_completions",
            "model_id": NVIDIA_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 80,
        }
    )


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id="nvidia",
        env_var_name="NVIDIA_API_KEY",
        scopes=["model:read"],
    )


def _request_timeout():
    from sentinel.agent.model_execution import ModelTimeoutPolicy

    return ModelTimeoutPolicy(connect_timeout_seconds=5.0, read_timeout_seconds=120.0, total_timeout_seconds=150.0)


def test_nvidia_missing_api_key_returns_missing_credential_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    calls: list[Any] = []
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = NvidiaChatCompletionsProvider().execute(
        _nvidia_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content == {}
    assert calls == []


def test_nvidia_request_uses_exact_model_and_excludes_secret_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", SECRET_VALUE)
    recorder = RecordingUrlOpen(_valid_nvidia_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = NvidiaChatCompletionsProvider().execute(
        _nvidia_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    call = recorder.calls[0]
    body = call["json"]
    metadata = _nvidia_request().serializable_metadata()

    assert body["model"] == NVIDIA_DEFAULT_MODEL_ID
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert SECRET_VALUE not in str(metadata)
    assert RAW_PROMPT not in str(metadata)
    assert response.error_class is None


def test_nvidia_response_validates_and_receipt_excludes_sensitive_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingUrlOpen(_valid_nvidia_payload()))

    request = _nvidia_request()
    response = NvidiaChatCompletionsProvider().execute(
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


def test_nvidia_http_errors_are_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingUrlOpen({"error": {"message": "unauthorized"}}, status_code=401))

    response = NvidiaChatCompletionsProvider().execute(
        _nvidia_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value
    assert response.content["http_status"] == 401
    assert SECRET_VALUE not in response.model_dump_json()


def test_nvidia_real_provider_skip_safe() -> None:
    if not os.environ.get("NVIDIA_API_KEY"):
        pytest.skip("NVIDIA_API_KEY absent; skipping real NVIDIA call")

    request = _nvidia_request()
    response = NvidiaChatCompletionsProvider().execute(
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

    if result.outcome_class in {
        ModelExecutionOutcomeClass.RATE_LIMIT,
        ModelExecutionOutcomeClass.TIMEOUT,
        ModelExecutionOutcomeClass.PROVIDER_ERROR,
        ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
    }:
        dumped = receipt.model_dump_json()
        assert os.environ["NVIDIA_API_KEY"] not in dumped
        assert request.prompt_text_in_memory_only not in dumped
        pytest.skip(f"real NVIDIA call returned provider outcome: {result.outcome_class.value}")

    assert response.error_class is None
    assert result.success is True
    dumped = receipt.model_dump_json()
    assert os.environ["NVIDIA_API_KEY"] not in dumped
    assert request.prompt_text_in_memory_only not in dumped


def _valid_nvidia_payload() -> dict[str, Any]:
    return {
        "id": "nvidia_resp_1",
        "model": NVIDIA_DEFAULT_MODEL_ID,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "decision": "continue",
                            "rationale": "NVIDIA test response validated",
                            "evidence_refs": ["evidence_1"],
                            "confidence": 0.9,
                        }
                    ),
                },
            }
        ],
        "usage": {"prompt_tokens": 14, "completion_tokens": 12, "total_tokens": 26},
    }
