from __future__ import annotations

import json
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
from sentinel.agent.model_execution.catalog import (
    ProviderBackendProfile,
    ProviderCapabilityFlags,
    ProviderCatalog,
    ProviderCatalogEntry,
    ProviderCatalogStatus,
    ProviderCredentialPolicy,
    ProviderFamily,
    ProviderRealTestStatus,
)
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.policy import (
    ModelExecutionBudgetPolicy,
    ModelRetryPolicy,
    ModelTimeoutPolicy,
)
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.llm_adapter import OperatorLLMConversationAdapter
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.model_client import OperatorCatalogModelClient
from sentinel.operator.models import OperatorMessage, OperatorMessageRole, OperatorMode


class RecordingHttpxClient:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []
        self.client_kwargs: list[dict[str, Any]] = []

    def __call__(self, *_args: Any, **_kwargs: Any) -> RecordingHttpxClient:
        self.client_kwargs.append(dict(_kwargs))
        return self

    def __enter__(self) -> RecordingHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _Response(self.payload, status_code=self.status_code)


class _Response:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.request = httpx.Request("POST", "http://localhost:11434")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "unit http error",
                request=self.request,
                response=httpx.Response(self.status_code, json=self._payload, request=self.request),
            )
        return None


def test_catalog_model_client_calls_user_selected_local_openai_compatible_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload(_valid_output()))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is not None
    assert result.mission_draft.title == "AI training business launch"
    assert recorder.calls[0]["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in recorder.calls[0]["headers"]
    assert recorder.calls[0]["json"]["model"] == "llama3.2"


def test_catalog_model_client_calls_aliyun_dashscope_openai_compatible_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_CERT_MODEL_API_KEY", "unit-aliyun-key")
    monkeypatch.setenv(
        "SENTINEL_ALIYUN_DASHSCOPE_BASE_URL",
        "https://unit-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    )
    recorder = RecordingHttpxClient(_provider_payload(_valid_output(), model="deepseek-v4-pro"))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(
        provider_id="aliyun_dashscope",
        backend_id="aliyun_openai_compatible_chat",
        model="deepseek-v4-pro",
    )

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is not None
    assert recorder.calls[0]["url"] == (
        "https://unit-workspace.ap-southeast-1.maas.aliyuncs.com"
        "/compatible-mode/v1/chat/completions"
    )
    assert recorder.calls[0]["headers"]["Authorization"] == "Bearer unit-aliyun-key"
    assert recorder.calls[0]["json"]["model"] == "deepseek-v4-pro"


def test_catalog_model_client_accepts_single_fenced_mission_understanding_v2_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(
        _provider_payload(
            "```json\n"
            + json.dumps(
                {
                    "protocol_version": "cockpit_mission_understanding_v2",
                    "kind": "draft_mission",
                    "reply": "Mission draft ready.",
                    "title": "Repository architecture research",
                    "objective": "Map packages and command execution flow.",
                    "requested_capability": "read_only_research",
                    "expected_artifacts": ["evidence-linked report"],
                }
            )
            + "\n```"
        )
    )
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is not None
    assert result.mission_draft.title == "Repository architecture research"
    assert result.authority_summary is not None
    assert result.authority_summary.metadata["capability_id"] == "read_only_research"


def test_catalog_model_client_accepts_harmless_formatting_around_one_v2_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(
        _provider_payload(
            "\n\n"
            + json.dumps(
                {
                    "protocol_version": "cockpit_mission_understanding_v2",
                    "kind": "draft_mission",
                    "reply": "Mission draft ready.",
                    "title": "Repository architecture research",
                    "objective": "Map packages and command execution flow.",
                    "requested_capability": "read_only_research",
                }
            )
            + "\n\n"
        )
    )
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is not None
    assert result.metadata["understanding_protocol"] == "cockpit_mission_understanding_v2"


@pytest.mark.parametrize(
    "content",
    [
        (
            json.dumps(
                {
                    "protocol_version": "cockpit_mission_understanding_v2",
                    "kind": "draft_mission",
                    "reply": "one",
                    "title": "one",
                    "objective": "one",
                    "requested_capability": "read_only_research",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "protocol_version": "cockpit_mission_understanding_v2",
                    "kind": "draft_mission",
                    "reply": "two",
                    "title": "two",
                    "objective": "two",
                    "requested_capability": "read_only_research",
                }
            )
        ),
        '{"protocol_version":"cockpit_mission_understanding_v2","kind":"draft_mission"',
    ],
)
def test_catalog_model_client_rejects_ambiguous_or_truncated_v2_json(
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload(content))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is None
    assert result.metadata["blocked_reason"] == "invalid_structured_output"


def test_catalog_model_client_diagnoses_empty_visible_content_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload(""))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
        require_mission_understanding_v2=True,
    ).complete(_frame())

    diagnostics = result.metadata["structured_output_diagnostics"]
    assert result.mission_draft is None
    assert diagnostics["normalization_strategy"] == "empty_visible_content"
    assert diagnostics["content_extraction_source"] == "choices[0].message.content"
    assert diagnostics["visible_content_length"] == 0
    assert diagnostics["json_object_detected"] is False


def test_catalog_model_client_diagnoses_empty_json_object_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload("{}"))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
        require_mission_understanding_v2=True,
    ).complete(_frame())

    diagnostics = result.metadata["structured_output_diagnostics"]
    assert result.mission_draft is None
    assert diagnostics["normalization_strategy"] == "plain_json_object"
    assert diagnostics["content_extraction_source"] == "choices[0].message.content"
    assert diagnostics["visible_content_length"] == 2
    assert diagnostics["json_object_detected"] is True
    assert diagnostics["top_level_key_names"] == []


def test_openai_compatible_provider_extraction_failures_are_safe_diagnostics() -> None:
    provider = _openai_provider(supports_json_mode=False)
    request = _real_model_request()

    missing_choices = provider.map_payload(request, {"id": "missing", "model": "unit/model"})
    non_string = provider.map_payload(
        request,
        {
            "id": "bad-content",
            "model": "unit/model",
            "choices": [{"message": {"content": {"not": "a string"}}, "finish_reason": "stop"}],
        },
    )
    length_finish = provider.map_payload(
        request,
        {
            "id": "length",
            "model": "unit/model",
            "choices": [{"message": {"content": '{"protocol_version":'}, "finish_reason": "length"}],
        },
    )

    assert missing_choices.error_class == "INVALID_RESPONSE_SCHEMA"
    assert missing_choices.content["content_extraction_source"] == "choices[0].message.content"
    assert missing_choices.content["content_extraction_error"] == "missing_choices_or_message"
    assert non_string.error_class == "INVALID_RESPONSE_SCHEMA"
    assert non_string.content["content_extraction_error"] == "content_not_string"
    assert non_string.content["finish_reason"] == "stop"
    assert length_finish.content["finish_reason"] == "length"
    assert length_finish.content["output_truncated"] is True
    assert length_finish.content["normalization_strategy"] == "truncated_or_invalid_json"


def test_openai_compatible_provider_json_response_format_is_catalog_gated() -> None:
    request = _real_model_request(metadata={"response_format_json_object": True})

    body_without_support = _openai_provider(supports_json_mode=False)._request_body(request)
    body_with_support = _openai_provider(supports_json_mode=True)._request_body(request)

    assert "response_format" not in body_without_support
    assert body_with_support["response_format"] == {"type": "json_object"}


def test_catalog_model_client_missing_remote_credential_fails_closed_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    recorder = RecordingHttpxClient(_provider_payload(_valid_output()))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="openai_chat", backend_id="openai_chat_completions", model="gpt-5.4")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is None
    assert result.metadata["blocked_reason"] == "MISSING_CREDENTIAL"
    assert recorder.calls == []


def test_pack3_18_provider_http_error_is_not_wrapped_as_model_authored_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "unit-openai-key")
    recorder = RecordingHttpxClient(
        {
            "error": {
                "type": "invalid_request_error",
                "code": "unsupported_parameter",
                "message": "redacted by hash only",
            }
        },
        status_code=400,
    )
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="openai_chat", backend_id="openai_chat_completions", model="gpt-5.4")

    result = OperatorCatalogModelClient(user_model_contract=contract).complete(_real_model_request_for_contract(contract))

    assert result["provider_failure"] is True
    assert result["provider_failure_category"] == "PROVIDER_BAD_REQUEST"
    assert result["provider_error_class"] == "PROVIDER_ERROR"
    assert result["http_status"] == 400
    assert result["provider_error_code"] == "unsupported_parameter"
    assert result["provider_error_type"] == "invalid_request_error"
    assert result["diagnostic_retention_status"] == "retained"
    assert result["provider_id"] == "openai_chat"
    assert result["backend_id"] == "openai_chat_completions"
    assert result["model_id"] == "gpt-5.4"
    assert "endpoint_hash" in result
    assert "provider_response_hash" in result
    assert "reply" not in result
    assert "metadata" not in result
    assert "redacted by hash only" not in str(result)


def test_catalog_model_client_uses_read_only_decision_timeout_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "unit-openai-key")
    recorder = RecordingHttpxClient(_provider_payload(_valid_output(), model="gpt-5.4"))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="openai_chat", backend_id="openai_chat_completions", model="gpt-5.4")
    request = _real_model_request_for_contract(contract).model_copy(
        update={
            "runtime": "read_only_research_product",
            "request_metadata": {
                "read_only_lane": "exploration_decision",
                "timeout_policy": {
                    "connect_timeout_seconds": 2.0,
                    "read_timeout_seconds": 90.0,
                    "total_timeout_seconds": 92.0,
                },
            },
        }
    )

    OperatorCatalogModelClient(user_model_contract=contract).complete(request)

    timeout = recorder.client_kwargs[0]["timeout"]
    assert timeout.read == 90.0
    assert timeout.connect == 2.0


def test_catalog_model_client_rejects_invalid_read_only_decision_timeout_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "unit-openai-key")
    recorder = RecordingHttpxClient(_provider_payload(_valid_output(), model="gpt-5.4"))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="openai_chat", backend_id="openai_chat_completions", model="gpt-5.4")
    request = _real_model_request_for_contract(contract).model_copy(
        update={
            "runtime": "read_only_research_product",
            "request_metadata": {
                "read_only_lane": "exploration_decision",
                "timeout_policy": {
                    "connect_timeout_seconds": 2.0,
                    "read_timeout_seconds": 0.0,
                    "total_timeout_seconds": 0.0,
                },
            },
        }
    )

    result = OperatorCatalogModelClient(user_model_contract=contract).complete(request)

    assert result["metadata"]["blocked_reason"] == "READ_ONLY_TIMEOUT_POLICY_INVALID"
    assert recorder.calls == []


def test_catalog_model_client_rejects_unsupported_model_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload(_valid_output()))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="not-in-catalog")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(user_model_contract=contract),
    ).complete(_frame())

    assert result.mission_draft is None
    assert result.metadata["blocked_reason"] == "DISABLED_BACKEND"
    assert recorder.calls == []


def test_catalog_model_client_rejects_local_backend_non_loopback_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingHttpxClient(_provider_payload(_valid_output()))
    monkeypatch.setattr("httpx.Client", recorder)
    contract = _contract(provider_id="localbad", backend_id="localbad_chat", model="llama3.2")

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=OperatorCatalogModelClient(
            user_model_contract=contract,
            provider_catalog=_local_catalog(endpoint="https://example.com/v1/chat/completions"),
        ),
    ).complete(_frame())

    assert result.mission_draft is None
    assert result.metadata["blocked_reason"] == "LOCAL_ENDPOINT_NOT_LOOPBACK"
    assert recorder.calls == []


def _frame() -> OperatorConversationFrame:
    return OperatorConversationFrame.build(
        session_id="session_model_client",
        user_message=OperatorMessage(
            session_id="session_model_client",
            role=OperatorMessageRole.USER,
            content="Je veux lancer un business de formation IA.",
        ),
    )


def _contract(*, provider_id: str, backend_id: str, model: str) -> UserModelContract:
    return UserModelContract(
        selected_provider_id=provider_id,
        selected_backend_id=backend_id,
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=32_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="operator_v0",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _real_model_request_for_contract(contract: UserModelContract) -> RealModelRequest:
    timeout = ModelTimeoutPolicy(
        connect_timeout_seconds=2.0,
        read_timeout_seconds=10.0,
        total_timeout_seconds=12.0,
    )
    retry = ModelRetryPolicy(max_attempts=1, retryable_outcomes=[])
    budget = ModelExecutionBudgetPolicy(
        max_input_tokens=1000,
        max_output_tokens=1000,
        max_total_estimated_usd=0.0,
    )
    metadata = {"routing_policy": "explicit_user_model_contract_only"}
    return RealModelRequest(
        provider_id=contract.selected_provider_id,
        backend_id=contract.selected_backend_id,
        backend=contract.selected_backend_id,
        model_id=contract.selected_model,
        runtime="read_only_research_product",
        prompt_hash=stable_hash({"prompt": "unit"}),
        frame_hash=stable_hash({"frame": "unit"}),
        user_model_contract_id=contract.id,
        estimated_input_tokens=10,
        estimated_output_tokens=20,
        prompt_text_in_memory_only="Return one action.",
        request_metadata=metadata,
        timeout_policy_id=timeout.id,
        retry_policy_id=retry.id,
        budget_policy_id=budget.id,
        request_hash=stable_hash(metadata),
    )


def _provider_payload(content: dict[str, object] | str, *, model: str = "llama3.2") -> dict[str, object]:
    return {
        "id": "chatcmpl_unit",
        "model": model,
        "choices": [{"message": {"content": content if isinstance(content, str) else json.dumps(content)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }


def _valid_output() -> dict[str, object]:
    return {
        "reply": "Tres bien. Je vais clarifier la mission avant de commencer.",
        "intent": {"kind": "draft_mission", "text": "launch AI training business"},
        "mission_draft": {
            "title": "AI training business launch",
            "objective": "Research the target market and prepare launch artifacts.",
            "constraints": ["no payment", "no real outbound send"],
            "expected_artifacts": ["market summary", "launch plan"],
        },
        "authority_summary": {
            "mission_id": "mission_llm",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only; no external send or payment.",
        },
    }


def _local_catalog(*, endpoint: str) -> ProviderCatalog:
    return ProviderCatalog(
        entries=[
            ProviderCatalogEntry(
                provider_id="localbad",
                display_name="Local Bad",
                family=ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
                status=ProviderCatalogStatus.LOCAL_ONLY,
                backends=[
                    ProviderBackendProfile(
                        backend_id="localbad_chat",
                        family=ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
                        endpoint_template=endpoint,
                        runtime="local",
                        supported_models=["llama3.2"],
                    )
                ],
                credential_policy=ProviderCredentialPolicy(
                    credential_env_var=None,
                    credential_source_type="local_none",
                    required_for_real_call=False,
                ),
                capability_flags=ProviderCapabilityFlags(chat=True, local_runtime=True),
                real_test_status=ProviderRealTestStatus(),
            )
        ]
    )


def _openai_provider(*, supports_json_mode: bool) -> OpenAICompatibleChatProvider:
    backend = ProviderBackendProfile(
        backend_id="unit_backend",
        family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
        endpoint_template="https://example.invalid/v1/chat/completions",
        runtime="unit",
        supported_models=["unit/model"],
        supports_json_mode=supports_json_mode,
    )
    return OpenAICompatibleChatProvider(
        config=OpenAICompatibleProviderConfig(
            provider_id="unit_provider",
            backend_id="unit_backend",
            base_url="https://example.invalid/v1",
            credential_env=None,
            default_model_id="unit/model",
            backend_profile=backend,
        )
    )


def _real_model_request(metadata: dict[str, object] | None = None) -> RealModelRequest:
    timeout = ModelTimeoutPolicy(
        connect_timeout_seconds=2.0,
        read_timeout_seconds=10.0,
        total_timeout_seconds=12.0,
    )
    retry = ModelRetryPolicy(max_attempts=1, retryable_outcomes=[])
    budget = ModelExecutionBudgetPolicy(
        max_input_tokens=1000,
        max_output_tokens=1000,
        max_total_estimated_usd=0.0,
    )
    request_metadata = metadata or {}
    request_hash_payload = {
        "provider_id": "unit_provider",
        "backend_id": "unit_backend",
        "model_id": "unit/model",
        "metadata": request_metadata,
    }
    return RealModelRequest(
        provider_id="unit_provider",
        backend_id="unit_backend",
        backend="unit_backend",
        model_id="unit/model",
        runtime="unit_test",
        prompt_hash=stable_hash({"prompt": "unit"}),
        frame_hash=stable_hash({"frame": "unit"}),
        user_model_contract_id="umodel_unit",
        estimated_input_tokens=10,
        estimated_output_tokens=20,
        prompt_text_in_memory_only="Return JSON.",
        request_metadata=request_metadata,
        timeout_policy_id=timeout.id,
        retry_policy_id=retry.id,
        budget_policy_id=budget.id,
        request_hash=stable_hash(request_hash_payload),
    )
