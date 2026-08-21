from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import (
    LLMDecisionResultValidator,
    ModelExecutionOutcomeClass,
    ProviderCredentialHandle,
    build_default_provider_catalog,
    build_model_execution_receipt,
)
from sentinel.agent.model_execution.opencode import (
    OPENCODE_BACKEND_ID,
    OPENCODE_CHAT_BACKEND_ID,
    OPENCODE_CHAT_PROVIDER_ID,
    OPENCODE_DEFAULT_MODEL_ID,
    OPENCODE_RESPONSES_URL,
    OPENCODE_CHAT_BASE_URL,
    OPENCODE_CHAT_DEFAULT_MODEL_ID,
    OpenCodeChatCompletionsProvider,
    OpenCodeResponsesProvider,
)
from sentinel.operator.model_client import OperatorCatalogModelClient

sys.path.append(str(Path(__file__).parent))
from test_real_model_execution_backend import _request  # noqa: E402


RAW_PROMPT = (
    'Return exactly this JSON object: {"decision":"continue","rationale":"ok","evidence_refs":[],"confidence":0.9}'
)
SECRET_VALUE = "unit-test-opencode-token-not-real"


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


class _Response:
    def __init__(self, payload: dict[str, Any] | str, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload)
        self.headers: dict[str, str] = {}
        self.request = httpx.Request("POST", "https://redacted.invalid")

    def json(self) -> dict[str, Any]:
        if isinstance(self._payload, str):
            raise json.JSONDecodeError("not json", self._payload, 0)
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=httpx.Response(self.status_code, json=self._payload),
            )


def _opencode_request():
    return _request().model_copy(
        update={
            "provider_id": "opencode",
            "backend_id": OPENCODE_BACKEND_ID,
            "backend": OPENCODE_BACKEND_ID,
            "runtime": "responses",
            "model_id": OPENCODE_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 80,
        }
    )


def _opencode_chat_request():
    return _request().model_copy(
        update={
            "provider_id": OPENCODE_CHAT_PROVIDER_ID,
            "backend_id": OPENCODE_CHAT_BACKEND_ID,
            "backend": OPENCODE_CHAT_BACKEND_ID,
            "runtime": "chat_completions",
            "model_id": OPENCODE_CHAT_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 80,
        }
    )


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id="opencode",
        env_var_name="OPENCODE_API_KEY",
        scopes=["model:read"],
    )


def _chat_credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id=OPENCODE_CHAT_PROVIDER_ID,
        env_var_name="OPENCODE_API_KEY",
        scopes=["model:read"],
    )


def _request_timeout():
    from sentinel.agent.model_execution import ModelTimeoutPolicy

    return ModelTimeoutPolicy(connect_timeout_seconds=5.0, read_timeout_seconds=60.0, total_timeout_seconds=70.0)


def test_opencode_catalog_lists_free_muse_spark_responses_model() -> None:
    entry = build_default_provider_catalog().get("opencode")
    backend = next(candidate for candidate in entry.backends if candidate.backend_id == OPENCODE_BACKEND_ID)

    assert entry.provider_id == "opencode"
    assert backend.backend_id == OPENCODE_BACKEND_ID
    assert backend.runtime == "responses"
    assert backend.endpoint_template == OPENCODE_RESPONSES_URL
    assert OPENCODE_DEFAULT_MODEL_ID == "muse-spark-1.2-contributor-free"
    assert backend.supports_model(OPENCODE_DEFAULT_MODEL_ID)
    assert not backend.supports_model("x-preview-f-free")
    assert entry.credential_policy.credential_env_var == "OPENCODE_API_KEY"


def test_opencode_catalog_routes_x_preview_free_to_chat_completions() -> None:
    entry = build_default_provider_catalog().get(OPENCODE_CHAT_PROVIDER_ID)
    backend = next(candidate for candidate in entry.backends if candidate.backend_id == OPENCODE_CHAT_BACKEND_ID)

    assert entry.provider_id == "opencode_chat"
    assert backend.runtime == "chat_completions"
    assert backend.endpoint_template == f"{OPENCODE_CHAT_BASE_URL}/chat/completions"
    assert backend.supports_model("x-preview-f-free")
    assert not backend.supports_model(OPENCODE_DEFAULT_MODEL_ID)


def test_opencode_missing_api_key_returns_missing_credential_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    calls: list[Any] = []
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = OpenCodeResponsesProvider().execute(
        _opencode_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content == {}
    assert calls == []


def test_opencode_responses_request_uses_exact_free_model_and_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_output_text_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = OpenCodeResponsesProvider().execute(
        _opencode_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    call = recorder.calls[0]
    body = call["json"]
    metadata = _opencode_request().serializable_metadata()

    assert call["url"] == OPENCODE_RESPONSES_URL
    assert body["model"] == OPENCODE_DEFAULT_MODEL_ID
    assert body["input"] == RAW_PROMPT
    assert body["stream"] is False
    assert SECRET_VALUE not in str(metadata)
    assert RAW_PROMPT not in str(metadata)
    assert response.error_class is None


def test_opencode_chat_request_uses_x_preview_free_and_chat_completions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_chat_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = OpenCodeChatCompletionsProvider().execute(
        _opencode_chat_request(),
        timeout=_request_timeout(),
        credential=_chat_credential(),
    )

    call = recorder.calls[0]
    body = call["json"]

    assert call["url"] == f"{OPENCODE_CHAT_BASE_URL}/chat/completions"
    assert body["model"] == OPENCODE_CHAT_DEFAULT_MODEL_ID
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert response.error_class is None


def test_opencode_output_text_response_validates_and_receipt_excludes_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(_valid_output_text_payload()))

    request = _opencode_request()
    response = OpenCodeResponsesProvider().execute(
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


def test_opencode_nested_output_response_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(_valid_nested_output_payload()))

    response = OpenCodeResponsesProvider().execute(
        _opencode_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )
    result = LLMDecisionResultValidator.validate(response)

    assert response.error_class is None
    assert result.success is True


def test_opencode_text_plain_response_is_treated_as_visible_model_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient(json.dumps(_decision_payload())))

    response = OpenCodeResponsesProvider().execute(
        _opencode_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )
    result = LLMDecisionResultValidator.validate(response)

    assert response.error_class is None
    assert response.content["content_extraction_source"] == "responses.output_text"
    assert result.success is True


def test_opencode_http_errors_are_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    monkeypatch.setattr("httpx.Client", RecordingHttpxClient({"error": {"message": "no payment method"}}, status_code=402))

    response = OpenCodeResponsesProvider().execute(
        _opencode_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.PROVIDER_ERROR.value
    assert response.content["http_status"] == 402
    assert "provider_error_message_hash" in response.content
    assert SECRET_VALUE not in response.model_dump_json()


def test_operator_catalog_model_client_routes_opencode_responses_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_output_text_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    request = _opencode_request().model_copy(
        update={
            "runtime": "product_model_native_decision",
            "request_metadata": {"raw_text_transport": "product_model_native_intent_v1"},
        }
    )
    client = OperatorCatalogModelClient(
        user_model_contract=_opencode_contract()
    )

    result = client.complete(request)

    assert recorder.calls[0]["url"] == OPENCODE_RESPONSES_URL
    assert result["content"] == json.dumps(_decision_payload())
    assert "raw_provider_response" in result
    assert SECRET_VALUE not in str(result)


def test_opencode_real_provider_skip_safe() -> None:
    if not os.environ.get("OPENCODE_API_KEY"):
        pytest.skip("OPENCODE_API_KEY absent; skipping real OpenCode call")

    request = _opencode_request()
    response = OpenCodeResponsesProvider().execute(
        request,
        timeout=_request_timeout(),
        credential=_credential(),
    )
    if response.error_class in {
        ModelExecutionOutcomeClass.RATE_LIMIT.value,
        ModelExecutionOutcomeClass.TIMEOUT.value,
        ModelExecutionOutcomeClass.PROVIDER_ERROR.value,
        ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA.value,
    }:
        assert os.environ["OPENCODE_API_KEY"] not in response.model_dump_json()
        assert request.prompt_text_in_memory_only not in response.model_dump_json()
        pytest.skip(f"real OpenCode call returned provider outcome: {response.error_class}")

    result = LLMDecisionResultValidator.validate(response)
    if result.outcome_class in {
        ModelExecutionOutcomeClass.RATE_LIMIT,
        ModelExecutionOutcomeClass.TIMEOUT,
        ModelExecutionOutcomeClass.PROVIDER_ERROR,
        ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
    }:
        assert os.environ["OPENCODE_API_KEY"] not in response.model_dump_json()
        assert request.prompt_text_in_memory_only not in response.model_dump_json()
        return

    assert response.error_class is None
    assert result.success is True
    receipt = build_model_execution_receipt(
        request=request,
        outcome_class=result.outcome_class,
        result=result,
        credential=_credential(),
        attempts=1,
    )
    dumped = receipt.model_dump_json()
    assert os.environ["OPENCODE_API_KEY"] not in dumped
    assert request.prompt_text_in_memory_only not in dumped


def _decision_payload() -> dict[str, Any]:
    return {
        "decision": "continue",
        "rationale": "OpenCode test response validated",
        "evidence_refs": ["evidence_1"],
        "confidence": 0.9,
    }


def _opencode_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="opencode",
        selected_backend_id=OPENCODE_BACKEND_ID,
        selected_model=OPENCODE_DEFAULT_MODEL_ID,
        cost_profile=ModelCostProfile(
            model_name=OPENCODE_DEFAULT_MODEL_ID,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=OPENCODE_DEFAULT_MODEL_ID,
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="opencode-provider-diagnostic",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _valid_output_text_payload() -> dict[str, Any]:
    return {
        "id": "resp_opencode_1",
        "model": OPENCODE_DEFAULT_MODEL_ID,
        "status": "completed",
        "output_text": json.dumps(_decision_payload()),
        "usage": {"input_tokens": 14, "output_tokens": 12, "total_tokens": 26},
    }


def _valid_nested_output_payload() -> dict[str, Any]:
    return {
        "id": "resp_opencode_2",
        "model": OPENCODE_DEFAULT_MODEL_ID,
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(_decision_payload())}],
            }
        ],
        "usage": {"input_tokens": 14, "output_tokens": 12, "total_tokens": 26},
    }


def _valid_chat_payload() -> dict[str, Any]:
    return {
        "id": "chat_opencode_1",
        "model": OPENCODE_CHAT_DEFAULT_MODEL_ID,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(_decision_payload()),
                },
            }
        ],
        "usage": {"prompt_tokens": 14, "completion_tokens": 12, "total_tokens": 26},
    }
