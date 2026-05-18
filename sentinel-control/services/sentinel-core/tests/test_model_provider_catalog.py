from __future__ import annotations

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
    ProviderReasoningRedactionPolicy,
    ProviderRealTestStatusKind,
    ProviderRecommendation,
    ProviderRetryPolicy,
    ProviderTimeoutProfile,
    ProviderUsageMapping,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog
from sentinel.perf.caches.model_call_optimizer import ModelCallPlan


REQUIRED_PROVIDER_IDS = {
    "groq",
    "openrouter",
    "nvidia",
    "deepseek",
    "mistral",
    "xai",
    "openai",
    "openai_chat",
    "anthropic",
    "google_gemini",
    "cohere",
    "ollama",
    "lmstudio",
}


def test_default_provider_catalog_registers_required_entries() -> None:
    catalog = build_default_provider_catalog()

    assert set(catalog.provider_ids()) == REQUIRED_PROVIDER_IDS
    assert catalog.get("groq").family is ProviderFamily.OPENAI_COMPATIBLE_CHAT
    assert catalog.get("anthropic").family is ProviderFamily.ANTHROPIC_MESSAGES_NATIVE


def test_provider_catalog_rejects_unknown_disabled_and_fake_providers() -> None:
    catalog = build_default_provider_catalog()

    with pytest.raises(LookupError):
        catalog.require_enabled_provider("missing", model_id="whatever", enabled_provider_ids={"missing"})

    with pytest.raises(PermissionError):
        catalog.require_enabled_provider("groq", model_id="openai/gpt-oss-20b", enabled_provider_ids=set())

    with pytest.raises(ValueError, match="fake provider marker"):
        ProviderCatalog(entries=[_entry(provider_id="fake_provider", is_fake_provider=True)])


def test_provider_catalog_rejects_supported_model_mismatch() -> None:
    catalog = build_default_provider_catalog()

    with pytest.raises(PermissionError, match="user-selected model"):
        catalog.require_enabled_provider(
            "groq",
            model_id="silently/overridden-model",
            enabled_provider_ids={"groq"},
        )


def test_provider_catalog_metadata_is_secret_free() -> None:
    catalog = build_default_provider_catalog()
    dumped = catalog.safe_metadata()

    assert "GROQ_API_KEY" in str(dumped)
    assert "OPENROUTER_API_KEY" in str(dumped)
    for forbidden in ("gsk_", "nvapi-", "sk-or-v1", "Authorization: Bearer", "raw_prompt", "raw_response"):
        assert forbidden not in str(dumped)


def test_recommendation_cannot_mutate_contract_or_plan_or_execute() -> None:
    catalog = build_default_provider_catalog()
    recommendation = catalog.get("groq").recommendation
    contract = _user_model_contract("openai/gpt-oss-20b")
    plan = _model_call_plan("openai/gpt-oss-20b", "groq")

    before_contract = contract.model_dump()
    before_plan = plan.model_dump()
    metadata = recommendation.as_metadata() if recommendation else {}

    assert metadata["metadata_only"] is True
    assert metadata["can_execute"] is False
    assert not hasattr(recommendation, "execute")
    assert contract.model_dump() == before_contract
    assert plan.model_dump() == before_plan


def test_fallback_recommendation_is_not_executable() -> None:
    recommendation = ProviderRecommendation(
        recommended_for=["smoke"],
        avoid_for=[],
        latency_class="low",
        cost_class="low",
        reliability_class="proven",
        notes=["metadata only"],
        fallback_provider_ids=["openrouter"],
    )

    assert recommendation.as_metadata()["fallback_provider_ids"] == ["openrouter"]
    assert recommendation.can_execute is False
    assert recommendation.fallback_can_execute is False


def test_capability_flags_do_not_grant_tool_or_organ_execution() -> None:
    flags = ProviderCapabilityFlags(
        chat=True,
        streaming=True,
        tool_calling=True,
        server_side_tools=True,
        reasoning_controls=True,
    )

    assert flags.tool_calling is True
    assert flags.server_side_tools is True
    assert flags.grants_tool_execution is False
    assert flags.grants_organ_execution is False
    assert flags.server_side_tools_enabled_by_default is False


def test_reasoning_redaction_fields_are_metadata_only() -> None:
    policy = ProviderReasoningRedactionPolicy(
        raw_reasoning_fields=["reasoning", "reasoning_content", "reasoning_details"],
        request_reasoning_disable_fields={"reasoning": {"exclude": True}},
    )

    assert "reasoning_content" in policy.raw_reasoning_fields
    assert policy.stores_raw_reasoning is False
    assert policy.metadata_only is True


def test_real_test_statuses_match_provider_evidence() -> None:
    catalog = build_default_provider_catalog()

    assert catalog.get("groq").real_test_status.status is ProviderRealTestStatusKind.SUCCESS_VALIDATED
    assert catalog.get("groq").real_test_status.last_validated_model_id == "openai/gpt-oss-20b"
    assert catalog.get("groq").real_test_status.provider_adapter_commit == "187d251"
    assert catalog.get("groq").real_test_status.runtime_validation_commit == "9647993"
    assert catalog.get("groq").real_test_status.provider_catalog_commit == "7f0ddcb"
    assert catalog.get("groq").real_test_status.openai_compatible_base_commit == "4052be9"
    assert catalog.get("openrouter").real_test_status.status is ProviderRealTestStatusKind.DIAGNOSTIC_ONLY
    assert catalog.get("nvidia").real_test_status.status is ProviderRealTestStatusKind.DIAGNOSTIC_ONLY

    for provider_id in ("openai", "anthropic", "google_gemini", "cohere"):
        assert catalog.get(provider_id).real_test_status.status is ProviderRealTestStatusKind.NOT_STARTED


def test_catalog_entries_reject_secret_like_metadata() -> None:
    with pytest.raises(ValueError, match="secret-like"):
        _entry(provider_id="leaky", official_docs=["https://example.invalid?credential_value=unit-test-secret"])


def _entry(provider_id: str, *, is_fake_provider: bool = False, official_docs: list[str] | None = None):
    backend = ProviderBackendProfile(
        backend_id=f"{provider_id}_chat",
        family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
        endpoint_template="https://example.invalid/v1/chat/completions",
        runtime="chat_completions",
        supported_models=["unit/model"],
        usage_mapping=ProviderUsageMapping(),
        timeout_profile=ProviderTimeoutProfile(),
        retry_policy=ProviderRetryPolicy(),
        reasoning_redaction_policy=ProviderReasoningRedactionPolicy(),
    )
    return ProviderCatalogEntry(
        provider_id=provider_id,
        display_name=provider_id.title(),
        family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
        status=ProviderCatalogStatus.PLANNED,
        backends=[backend],
        credential_policy=ProviderCredentialPolicy(credential_env_var=f"{provider_id.upper()}_API_KEY"),
        capability_flags=ProviderCapabilityFlags(chat=True),
        real_test_status={"status": ProviderRealTestStatusKind.NOT_STARTED},
        official_docs=official_docs or ["https://example.invalid/docs"],
        is_fake_provider=is_fake_provider,
    )


def _user_model_contract(model: str) -> UserModelContract:
    return UserModelContract(
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.1,
            output_usd_per_1m=0.2,
            context_window_tokens=8_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=8_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=1_000,
            max_tool_schema_tokens=0,
            max_evidence_tokens=500,
            reserve_output_tokens=100,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="catalog-test",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _model_call_plan(model: str, backend: str) -> ModelCallPlan:
    return ModelCallPlan(
        model_id=model,
        provider_id=backend,
        backend_id=f"{backend}_openai_compatible_chat",
        backend=backend,
        runtime="chat_completions",
        use_prefix_reuse=False,
        stable_prefix_hash=None,
        evidence_delta_count=0,
        estimated_input_tokens=10,
        rationale="catalog-test",
    )
