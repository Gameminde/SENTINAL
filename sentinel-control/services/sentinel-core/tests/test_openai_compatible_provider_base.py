from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from sentinel.agent.model_execution import (
    ModelExecutionOutcomeClass,
    ModelTimeoutPolicy,
    ProviderCredentialHandle,
)
from sentinel.agent.model_execution.catalog import (
    ProviderBackendProfile,
    ProviderFamily,
    ProviderReasoningRedactionPolicy,
    ProviderTimeoutProfile,
    ProviderUsageMapping,
)
from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.redaction import text_hash

sys.path.append(str(Path(__file__).parent))
from test_real_model_execution_backend import _request  # noqa: E402


RAW_PROMPT = "catalog-base raw prompt should remain in memory only"
SECRET_VALUE = "unit-test-openai-compatible-token-not-real"


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
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=httpx.Response(self.status_code, json=self._payload),
            )


def test_openai_compatible_request_uses_selected_model_and_disables_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    provider = _provider()

    response = provider.execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    body = recorder.calls[0]["json"]
    assert body["model"] == "unit/model"
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert body["max_completion_tokens"] == 64
    assert "tools" not in body
    assert "tool_choice" not in body
    assert "functions" not in body
    assert response.error_class is None


def test_openai_compatible_unsupported_model_rejected_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    request = _compatible_request().model_copy(update={"model_id": "other/model"})

    response = _provider().execute(request, timeout=_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.DISABLED_BACKEND.value
    assert response.content["rejected_reason"] == "unsupported_model"
    assert recorder.calls == []


def test_openai_compatible_reasoning_fields_are_redacted_and_hash_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    payload = _payload(
        message_extra={
            "reasoning": "sensitive reasoning",
            "reasoning_content": "sensitive reasoning content",
            "reasoning_details": [{"text": "sensitive reasoning details"}],
        }
    )
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(payload))

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.content["reasoning_present"] is True
    assert response.content["reasoning_hash"] == text_hash(
        "sensitive reasoning sensitive reasoning content sensitive reasoning details"
    )
    dumped = response.model_dump_json()
    assert "sensitive reasoning" not in dumped
    assert "reasoning_details" not in dumped


def test_openai_compatible_usage_mapping_and_raw_payload_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    payload = _payload(usage={"input": 11, "output": 7, "total": 18})
    profile = _profile(
        usage_mapping=ProviderUsageMapping(
            input_tokens_path="usage.input",
            output_tokens_path="usage.output",
            total_tokens_path="usage.total",
        )
    )
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(payload))

    response = _provider(profile=profile).execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.input_tokens == 11
    assert response.output_tokens == 7
    dumped = response.model_dump_json()
    assert RAW_PROMPT not in dumped
    assert SECRET_VALUE not in dumped
    assert "unit_resp_1" not in dumped


def test_openai_compatible_rejects_provider_returned_model_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    payload = _payload()
    payload["model"] = "other/model"
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(payload))

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.DISABLED_BACKEND.value
    assert response.content["rejected_reason"] == "provider_model_mismatch"


def test_openai_compatible_timeout_profile_and_errors_are_profile_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    profile = _profile(
        timeout_profile=ProviderTimeoutProfile(
            connect_timeout_seconds=4.0,
            read_timeout_seconds=20.0,
            total_timeout_seconds=25.0,
        )
    )
    recorder = RecordingHttpxClient({"error": {"message": "rate limit"}}, status_code=429)
    monkeypatch.setattr("httpx.Client", recorder)
    provider = _provider(profile=profile)

    response = provider.execute(_compatible_request(), timeout=provider.default_timeout_policy(), credential=_credential())

    assert provider.default_timeout_policy().total_timeout_seconds == 25.0
    assert response.error_class == ModelExecutionOutcomeClass.RATE_LIMIT.value
    assert response.content["http_status"] == 429
    assert SECRET_VALUE not in response.model_dump_json()


def test_openai_compatible_missing_credential_and_fallback_do_not_call_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("UNIT_PROVIDER_KEY", raising=False)
    recorder = RecordingHttpxClient(_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content == {}
    assert recorder.calls == []


def test_openai_compatible_rejects_mismatched_credential_handle_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    mismatched_credential = ProviderCredentialHandle.from_env(
        provider_id="other_provider",
        env_var_name="UNIT_PROVIDER_KEY",
        scopes=["model:read"],
    )

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=mismatched_credential)

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content["rejected_reason"] == "credential_provider_mismatch"
    assert recorder.calls == []


def test_provider_error_message_is_hashed_or_classified_not_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    raw_error = "provider echoed sk-test-unit-secret-1234567890 and raw prompt fragment"
    recorder = RecordingHttpxClient({"error": {"type": "invalid_request", "message": raw_error}}, status_code=400)
    monkeypatch.setattr("httpx.Client", recorder)

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value
    assert "provider_error_message_hash" in response.content
    assert raw_error not in response.model_dump_json()
    assert "sk-test-unit-secret-1234567890" not in response.model_dump_json()


def _provider(*, profile: ProviderBackendProfile | None = None) -> OpenAICompatibleChatProvider:
    return OpenAICompatibleChatProvider(
        config=OpenAICompatibleProviderConfig(
            provider_id="unit_provider",
            backend_id="unit_openai_compatible_chat",
            base_url="https://unit.invalid/v1",
            credential_env="UNIT_PROVIDER_KEY",
            default_model_id="unit/model",
            backend_profile=profile or _profile(),
        )
    )


def _profile(
    *,
    usage_mapping: ProviderUsageMapping | None = None,
    timeout_profile: ProviderTimeoutProfile | None = None,
) -> ProviderBackendProfile:
    return ProviderBackendProfile(
        backend_id="unit_openai_compatible_chat",
        family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
        endpoint_template="https://unit.invalid/v1/chat/completions",
        runtime="chat_completions",
        supported_models=["unit/model"],
        supports_streaming=True,
        supports_json_mode=True,
        supports_tools=True,
        supports_reasoning_controls=True,
        usage_mapping=usage_mapping or ProviderUsageMapping(
            input_tokens_path="usage.prompt_tokens",
            output_tokens_path="usage.completion_tokens",
            total_tokens_path="usage.total_tokens",
        ),
        timeout_profile=timeout_profile or ProviderTimeoutProfile(),
        reasoning_redaction_policy=ProviderReasoningRedactionPolicy(
            raw_reasoning_fields=[
                "reasoning",
                "reasoning_content",
                "reasoning_details",
                "thinking",
                "thought",
                "thought_signature",
                "thinking_blocks",
            ],
            request_reasoning_disable_fields={"reasoning": {"exclude": True}},
        ),
    )


def _compatible_request():
    return _request().model_copy(
        update={
            "provider_id": "unit_provider",
            "backend_id": "unit_openai_compatible_chat",
            "backend": "unit_openai_compatible_chat",
            "runtime": "chat_completions",
            "model_id": "unit/model",
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 64,
        }
    )


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id="unit_provider",
        env_var_name="UNIT_PROVIDER_KEY",
        scopes=["model:read"],
    )


def _timeout() -> ModelTimeoutPolicy:
    return ModelTimeoutPolicy(connect_timeout_seconds=2.0, read_timeout_seconds=5.0, total_timeout_seconds=7.0)


def _payload(
    *,
    message_extra: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": json.dumps(
            {
                "decision": "continue",
                "rationale": "generic base validated",
                "evidence_refs": ["evidence_1"],
                "confidence": 0.9,
            }
        ),
    }
    if message_extra:
        message.update(message_extra)
    return {
        "id": "unit_resp_1",
        "model": "unit/model",
        "choices": [{"finish_reason": "stop", "message": message}],
        "usage": usage or {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }
