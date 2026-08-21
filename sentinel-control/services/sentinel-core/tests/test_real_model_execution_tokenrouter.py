from __future__ import annotations

import json
from typing import Any

import pytest

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import (
    ModelExecutionOutcomeClass,
    ProviderCredentialHandle,
    build_default_provider_catalog,
)
from sentinel.agent.model_execution.tokenrouter import (
    TOKENROUTER_BACKEND_ID,
    TOKENROUTER_BASE_URL,
    TOKENROUTER_CREDENTIAL_ENV,
    TOKENROUTER_DEFAULT_MODEL_ID,
    TOKENROUTER_PROVIDER_ID,
    TokenRouterChatCompletionsProvider,
)
from sentinel.operator.model_client import OperatorCatalogModelClient
from sentinel.operator.product_model_native_decision_client import _default_canonical_transport_profiles

from test_real_model_execution_backend import _request


RAW_PROMPT = 'Return exactly {"decision":"continue","rationale":"ok","evidence_refs":[],"confidence":0.9}'
SECRET_VALUE = "unit-test-tokenrouter-token-not-real"


class RecordingHttpxClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *_args: Any, **_kwargs: Any) -> RecordingHttpxClient:
        return self

    def __enter__(self) -> RecordingHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _Response(self.payload)


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def _tokenrouter_request():
    return _request().model_copy(
        update={
            "provider_id": TOKENROUTER_PROVIDER_ID,
            "backend_id": TOKENROUTER_BACKEND_ID,
            "backend": TOKENROUTER_BACKEND_ID,
            "runtime": "chat_completions",
            "model_id": TOKENROUTER_DEFAULT_MODEL_ID,
            "prompt_text_in_memory_only": RAW_PROMPT,
            "estimated_output_tokens": 80,
        }
    )


def _credential() -> ProviderCredentialHandle:
    return ProviderCredentialHandle.from_env(
        provider_id=TOKENROUTER_PROVIDER_ID,
        env_var_name=TOKENROUTER_CREDENTIAL_ENV,
        scopes=["model:read"],
    )


def _request_timeout():
    from sentinel.agent.model_execution import ModelTimeoutPolicy

    return ModelTimeoutPolicy(connect_timeout_seconds=5.0, read_timeout_seconds=60.0, total_timeout_seconds=70.0)


def test_tokenrouter_catalog_lists_qwen_max_free_chat_model() -> None:
    entry = build_default_provider_catalog().get(TOKENROUTER_PROVIDER_ID)
    backend = next(candidate for candidate in entry.backends if candidate.backend_id == TOKENROUTER_BACKEND_ID)

    assert entry.provider_id == TOKENROUTER_PROVIDER_ID
    assert entry.credential_policy.credential_env_var == TOKENROUTER_CREDENTIAL_ENV
    assert backend.runtime == "chat_completions"
    assert backend.endpoint_template == f"{TOKENROUTER_BASE_URL}/chat/completions"
    assert backend.supports_model("qwen/qwen3.8-max-free")
    assert not backend.supports_model("qwen/qwen3.8-max")


def test_tokenrouter_missing_api_key_returns_missing_credential_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TOKENROUTER_CREDENTIAL_ENV, raising=False)
    calls: list[Any] = []
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = TokenRouterChatCompletionsProvider().execute(
        _tokenrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    assert response.error_class == ModelExecutionOutcomeClass.MISSING_CREDENTIAL.value
    assert response.content == {}
    assert calls == []


def test_tokenrouter_request_uses_root_v1_url_and_exact_free_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKENROUTER_CREDENTIAL_ENV, SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_chat_payload())
    monkeypatch.setattr("httpx.Client", recorder)

    response = TokenRouterChatCompletionsProvider().execute(
        _tokenrouter_request(),
        timeout=_request_timeout(),
        credential=_credential(),
    )

    call = recorder.calls[0]
    body = call["json"]

    assert call["url"] == f"{TOKENROUTER_BASE_URL}/chat/completions"
    assert body["model"] == TOKENROUTER_DEFAULT_MODEL_ID
    assert body["messages"][0]["content"] == RAW_PROMPT
    assert body["stream"] is False
    assert response.error_class is None
    assert SECRET_VALUE not in response.model_dump_json()


def test_operator_catalog_client_uses_tokenrouter_max_tokens_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKENROUTER_CREDENTIAL_ENV, SECRET_VALUE)
    recorder = RecordingHttpxClient(_valid_chat_payload())
    monkeypatch.setattr("httpx.Client", recorder)
    request = _tokenrouter_request().model_copy(
        update={
            "runtime": "product_model_native_decision",
            "request_metadata": {"raw_text_transport": "product_model_native_intent_v1"},
        }
    )
    client = OperatorCatalogModelClient(user_model_contract=_tokenrouter_contract())

    result = client.complete(request)

    body = recorder.calls[0]["json"]
    assert body["max_tokens"] == request.estimated_output_tokens
    assert "max_completion_tokens" not in body
    assert result["content"] == json.dumps(_decision_payload())
    assert SECRET_VALUE not in str(result)


def test_tokenrouter_canonical_decision_transport_profiles_are_supported() -> None:
    profiles = _default_canonical_transport_profiles(
        provider_id=TOKENROUTER_PROVIDER_ID,
        backend_id=TOKENROUTER_BACKEND_ID,
        model_id=TOKENROUTER_DEFAULT_MODEL_ID,
    )

    assert profiles == ("strict_json_content", "fenced_strict_json")


def _decision_payload() -> dict[str, Any]:
    return {
        "decision": "continue",
        "rationale": "TokenRouter test response validated",
        "evidence_refs": ["evidence_1"],
        "confidence": 0.9,
    }


def _tokenrouter_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id=TOKENROUTER_PROVIDER_ID,
        selected_backend_id=TOKENROUTER_BACKEND_ID,
        selected_model=TOKENROUTER_DEFAULT_MODEL_ID,
        cost_profile=ModelCostProfile(
            model_name=TOKENROUTER_DEFAULT_MODEL_ID,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=TOKENROUTER_DEFAULT_MODEL_ID,
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
            expected_quality="tokenrouter-provider-diagnostic",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _valid_chat_payload() -> dict[str, Any]:
    return {
        "id": "chat_tokenrouter_1",
        "model": TOKENROUTER_DEFAULT_MODEL_ID,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        _decision_payload()
                    ),
                },
            }
        ],
        "usage": {"prompt_tokens": 14, "completion_tokens": 12, "total_tokens": 26},
    }
