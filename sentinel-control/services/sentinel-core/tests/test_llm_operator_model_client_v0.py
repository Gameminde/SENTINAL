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
from sentinel.operator.llm_adapter import OperatorLLMConversationAdapter
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.model_client import OperatorCatalogModelClient
from sentinel.operator.models import OperatorMessage, OperatorMessageRole, OperatorMode


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
        self.request = httpx.Request("POST", "http://localhost:11434")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
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
