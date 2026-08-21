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
    _http_error_diagnostic,
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


class RequestErrorHttpxClient:
    def __call__(self, *_args: Any, **_kwargs: Any) -> RequestErrorHttpxClient:
        return self

    def __enter__(self) -> RequestErrorHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, *_args: Any, **_kwargs: Any) -> Any:
        raise httpx.RemoteProtocolError("server disconnected with sk-test-unit-secret-1234567890")


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


def test_openai_compatible_request_applies_safe_top_level_reasoning_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    profile = _profile().model_copy(
        update={
            "reasoning_redaction_policy": ProviderReasoningRedactionPolicy(
                raw_reasoning_fields=["reasoning_content"],
                request_reasoning_disable_fields={"enable_thinking": False, "reasoning_effort": "none"},
            )
        }
    )

    response = _provider(profile=profile).execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    body = recorder.calls[0]["json"]
    assert body["enable_thinking"] is False
    assert body["reasoning_effort"] == "none"
    assert "reasoning" not in body
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


def test_provider_request_error_preserves_safe_transport_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIT_PROVIDER_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RequestErrorHttpxClient())

    response = _provider().execute(_compatible_request(), timeout=_timeout(), credential=_credential())

    assert response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value
    assert response.content["provider_transport_error_class"] == "RemoteProtocolError"
    assert response.content["provider_transport_error_message_hash"] == text_hash(
        "server disconnected with sk-test-unit-secret-1234567890"
    )
    assert response.content["provider_transport_error_message_redacted"] is True
    dumped = response.model_dump_json()
    assert "server disconnected" not in dumped
    assert "sk-test-unit-secret-1234567890" not in dumped


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


def test_strict_json_request_does_not_extract_material_json_from_prose() -> None:
    request = _compatible_request().model_copy(
        update={"request_metadata": {"strict_json_only": True}}
    )
    payload = _payload()
    payload["choices"][0]["message"]["content"] = (
        'I will act now. {"decision":"continue","evidence_refs":[]} Done.'
    )

    response = _provider().map_payload(request, payload)

    assert set(response.content) == {"raw_text_hash"}
    assert response.finish_reason == "stop"
    assert response.output_truncated is False


def test_explicit_mutation_patch_transport_keeps_raw_text_memory_only() -> None:
    raw_patch = "\n".join(
        [
            "PATCH",
            "--- a/src/pricing.py",
            "+++ b/src/pricing.py",
            "@@ -1,2 +1,2 @@",
            " def double(amount: int) -> int:",
            "-    return amount",
            "+    return amount * 2",
        ]
    )
    request = _compatible_request().model_copy(
        update={
            "request_metadata": {
                "strict_json_only": False,
                "raw_text_transport": "mutation_patch_v2",
            }
        }
    )
    payload = _payload()
    payload["choices"][0]["message"]["content"] = raw_patch

    response = _provider().map_payload(request, payload)

    assert response.raw_text_in_memory_only == raw_patch
    assert response.content["raw_text_hash"] == text_hash(raw_patch)
    assert response.content["raw_text_transport"] == "mutation_patch_v2"
    assert response.content["visible_content_char_count"] == len(raw_patch)
    assert response.content["visible_content_estimated_tokens"] == max(1, (len(raw_patch) + 3) // 4)
    dumped = response.model_dump_json()
    assert raw_patch not in dumped
    assert "return amount * 2" not in dumped


def test_mutation_patch_transport_records_reasoning_metadata_without_raw_reasoning() -> None:
    request = _compatible_request().model_copy(
        update={
            "request_metadata": {
                "strict_json_only": False,
                "raw_text_transport": "mutation_patch_v2",
            }
        }
    )
    payload = _payload(
        message_extra={"content": "PATCH", "reasoning_content": "private patch reasoning with hidden diff"},
        usage={"prompt_tokens": 21, "completion_tokens": 320, "completion_tokens_details": {"reasoning_tokens": 315}},
    )
    profile = _profile(
        usage_mapping=ProviderUsageMapping(
            input_tokens_path="usage.prompt_tokens",
            output_tokens_path="usage.completion_tokens",
            total_tokens_path="usage.total_tokens",
            reasoning_tokens_path="usage.completion_tokens_details.reasoning_tokens",
        )
    )

    response = _provider(profile=profile).map_payload(request, payload)

    assert response.content["raw_text_hash"] == text_hash("PATCH")
    assert response.content["raw_text_transport"] == "mutation_patch_v2"
    assert response.content["visible_content_char_count"] == 5
    assert response.content["visible_content_estimated_tokens"] == 2
    assert response.content["reasoning_present"] is True
    assert response.content["reasoning_hash"] == text_hash("private patch reasoning with hidden diff")
    assert response.content["reasoning_char_count"] == len("private patch reasoning with hidden diff")
    assert response.content["reasoning_token_count"] == 315
    assert response.output_tokens == 320
    dumped = response.model_dump_json()
    assert "private patch reasoning" not in dumped
    assert "hidden diff" not in dumped
    assert "raw_text_in_memory_only" not in dumped


def test_read_only_audit_report_transport_keeps_visible_report_memory_only() -> None:
    report = "# Sentinel Audit\n\nEvidence-backed architecture map."
    request = _compatible_request().model_copy(
        update={
            "request_metadata": {
                "strict_json_only": False,
                "raw_text_transport": "read_only_audit_report_v1",
            }
        }
    )
    payload = _payload(
        message_extra={"content": report, "reasoning_content": "private audit reasoning"},
        usage={"prompt_tokens": 44, "completion_tokens": 92},
    )

    response = _provider().map_payload(request, payload)

    assert response.raw_text_in_memory_only == report
    assert response.content["raw_text_hash"] == text_hash(report)
    assert response.content["raw_text_transport"] == "read_only_audit_report_v1"
    assert response.content["visible_content_char_count"] == len(report)
    assert response.content["visible_content_estimated_tokens"] == max(1, (len(report) + 3) // 4)
    assert response.content["reasoning_present"] is True
    assert response.content["reasoning_hash"] == text_hash("private audit reasoning")
    dumped = response.model_dump_json()
    assert "Evidence-backed architecture map" not in dumped
    assert "private audit reasoning" not in dumped
    assert "raw_text_in_memory_only" not in dumped


def test_provider_records_safe_finish_reason_and_truncation_without_raw_content() -> None:
    request = _compatible_request().model_copy(
        update={"request_metadata": {"strict_json_only": True}}
    )
    payload = _payload()
    payload["choices"][0]["finish_reason"] = "length"
    payload["choices"][0]["message"]["content"] = '{"decision":"continue"'

    response = _provider().map_payload(request, payload)

    assert response.finish_reason == "length"
    assert response.output_truncated is True
    assert set(response.content) == {"raw_text_hash"}


def test_provider_redacts_unsafe_finish_reason() -> None:
    request = _compatible_request().model_copy(
        update={"request_metadata": {"strict_json_only": True}}
    )
    raw_finish = "stop sk-test-finish-secret-1234567890"
    payload = _payload()
    payload["choices"][0]["finish_reason"] = raw_finish
    payload["choices"][0]["message"]["content"] = '{"decision":"continue"}'

    response = _provider().map_payload(request, payload)
    dumped = response.model_dump_json()

    assert response.finish_reason == "unsafe_provider_label"
    assert response.content["finish_reason_hash"] == text_hash(raw_finish)
    assert raw_finish not in dumped


def test_provider_redacts_unsafe_error_type_and_code() -> None:
    raw_type = "invalid_request sk-test-type-secret-1234567890"
    raw_code = "bad_request sk-test-code-secret-1234567890"
    response = httpx.Response(
        400,
        json={"error": {"type": raw_type, "code": raw_code, "message": "safe"}},
    )

    diagnostic = _http_error_diagnostic(response)
    dumped = json.dumps(diagnostic)

    assert diagnostic["provider_error_type"] == "unsafe_provider_label"
    assert diagnostic["provider_error_type_hash"] == text_hash(raw_type)
    assert diagnostic["provider_error_code"] == "unsafe_provider_label"
    assert diagnostic["provider_error_code_hash"] == text_hash(raw_code)
    assert raw_type not in dumped
    assert raw_code not in dumped
