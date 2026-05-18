from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.agent.evidence_ranker import EvidenceCard
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import (
    EnvironmentCredentialResolver,
    LLMDecisionResultValidator,
    ModelExecutionBudgetPolicy,
    ModelExecutionCoordinator,
    ModelExecutionOutcomeClass,
    ModelProviderRegistry,
    ModelRetryPolicy,
    ModelTimeoutPolicy,
    ProviderCapabilityMetadata,
    ProviderCredentialHandle,
    ProviderCredentialSource,
    ProviderModelResponse,
    RealModelRequestBuilder,
    RealModelProvider,
    build_model_execution_receipt,
)
from sentinel.perf.caches.model_call_optimizer import ModelCallPlan


SECRET_VALUE = "unit-test-provider-token-not-real"
RAW_PROMPT = "mission card with raw prompt body and " + SECRET_VALUE


def _model_contract() -> UserModelContract:
    return UserModelContract(
        selected_model="deepseek-v4-pro",
        cost_profile=ModelCostProfile(
            model_name="deepseek-v4-pro",
            input_usd_per_1m=0.14,
            output_usd_per_1m=0.28,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="deepseek-v4-pro",
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
            expected_quality="pack-a-structural",
            minimum_evidence_refs=1,
            retry_budget=1,
        ),
    )


def _decision_frame() -> LLMDecisionFrame:
    return LLMDecisionFrame(
        mission_id="mission_pack_a",
        mission_card={"goal": "test model execution boundary"},
        authority_card={"allowed_tools": ["read_only"], "forbidden": ["execute_tool"]},
        progress_card={"phase": "llm_decision_cycle_locked"},
        top_k_evidence=[
            EvidenceCard(
                receipt_id="receipt_1",
                source_type="decision_frame",
                evidence_refs=["evidence_1"],
                summary="safe compact evidence",
                relevance_score=0.9,
                token_count=12,
            )
        ],
        selected_tool_surface=["read_only"],
        current_blockers=[],
        next_decision_options=["continue", "defer"],
        required_output_schema={"required": ["decision", "rationale", "evidence_refs"]},
        receipt_refs=["receipt_1"],
        token_count=120,
        user_selected_model="deepseek-v4-pro",
        frame_hash="f" * 64,
    )


def _model_call_plan() -> ModelCallPlan:
    return ModelCallPlan(
        model_id="deepseek-v4-pro",
        backend="deepseek",
        runtime="completion",
        use_prefix_reuse=False,
        stable_prefix_hash=None,
        evidence_delta_count=1,
        estimated_input_tokens=120,
        rationale="unit_test_plan",
    )


def _policies() -> tuple[ModelTimeoutPolicy, ModelRetryPolicy, ModelExecutionBudgetPolicy]:
    return (
        ModelTimeoutPolicy(connect_timeout_seconds=2.0, read_timeout_seconds=5.0, total_timeout_seconds=7.0),
        ModelRetryPolicy(max_attempts=1, retryable_outcomes=[]),
        ModelExecutionBudgetPolicy(max_input_tokens=2_000, max_output_tokens=500, max_total_estimated_usd=0.01),
    )


def _request():
    timeout, retry, budget = _policies()
    return RealModelRequestBuilder.build(
        frame=_decision_frame(),
        rendered_prompt=RAW_PROMPT,
        plan=_model_call_plan(),
        user_model=_model_contract(),
        timeout_policy=timeout,
        retry_policy=retry,
        budget_policy=budget,
    )


def test_provider_registry_rejects_unknown_disabled_and_fake_providers() -> None:
    registry = ModelProviderRegistry()
    with pytest.raises(LookupError):
        registry.get_enabled("missing", model_id="deepseek-v4-pro")

    disabled = RecordingProvider(enabled=False)
    registry.register(disabled)
    with pytest.raises(PermissionError):
        registry.get_enabled(disabled.provider_id, model_id="deepseek-v4-pro")

    with pytest.raises(ValueError):
        registry.register(RecordingProvider(provider_id="fake", is_fake_provider=True))


def test_provider_registry_rejects_silent_user_model_override() -> None:
    registry = ModelProviderRegistry()
    provider = RecordingProvider(supported_models=("other-model",))
    registry.register(provider)

    with pytest.raises(PermissionError):
        registry.get_enabled(provider.provider_id, model_id="deepseek-v4-pro")


def test_missing_credential_does_not_call_provider_and_does_not_fake_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_TEST_MODEL_KEY", raising=False)
    provider = RecordingProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    resolver = EnvironmentCredentialResolver(
        {"deepseek": {"env_var": "SENTINEL_TEST_MODEL_KEY", "scopes": ["model:read"]}}
    )
    coordinator = ModelExecutionCoordinator(registry=registry, credential_resolver=resolver)

    outcome = coordinator.execute(request=_request())

    assert outcome.outcome_class is ModelExecutionOutcomeClass.MISSING_CREDENTIAL
    assert outcome.success is False
    assert outcome.result is None
    assert provider.calls == 0


def test_request_metadata_excludes_raw_prompt_and_preserves_user_selected_model() -> None:
    request = _request()
    metadata = request.serializable_metadata()

    assert request.prompt_hash
    assert request.request_hash
    assert request.model_id == "deepseek-v4-pro"
    assert request.provider_id == "deepseek"
    assert RAW_PROMPT not in str(metadata)
    assert SECRET_VALUE not in str(metadata)


def test_credential_handle_excludes_raw_credential_and_logs_no_secret(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    handle = ProviderCredentialHandle.from_env(
        provider_id="deepseek",
        env_var_name="SENTINEL_TEST_MODEL_KEY",
        scopes=["model:read"],
    )

    assert handle.source_type is ProviderCredentialSource.ENV
    assert handle.source_ref_hash
    assert not hasattr(handle, "raw_value")
    assert "SENTINEL_TEST_MODEL_KEY" not in handle.model_dump_json()
    assert SECRET_VALUE not in caplog.text


def test_receipt_excludes_raw_prompt_and_credential_and_hash_is_deterministic() -> None:
    request = _request()
    result = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            response_id="resp_1",
            content={"decision": "defer", "rationale": "needs real provider", "evidence_refs": ["evidence_1"]},
            input_tokens=100,
            output_tokens=20,
            cost_usd=0.0001,
        )
    )

    receipt_a = build_model_execution_receipt(
        request=request,
        outcome_class=ModelExecutionOutcomeClass.SUCCESS_VALIDATED,
        result=result,
        credential=ProviderCredentialHandle.from_env(
            provider_id="deepseek",
            env_var_name="SENTINEL_TEST_MODEL_KEY",
            scopes=["model:read"],
        ),
        attempts=1,
    )
    receipt_b = build_model_execution_receipt(
        request=request,
        outcome_class=ModelExecutionOutcomeClass.SUCCESS_VALIDATED,
        result=result,
        credential=ProviderCredentialHandle.from_env(
            provider_id="deepseek",
            env_var_name="SENTINEL_TEST_MODEL_KEY",
            scopes=["model:read"],
        ),
        attempts=1,
    )

    dumped = receipt_a.model_dump_json()
    assert receipt_a.receipt_hash == receipt_b.receipt_hash
    assert RAW_PROMPT not in dumped
    assert SECRET_VALUE not in dumped
    assert result.sanitized_response_hash == receipt_a.response_hash


def test_validator_rejects_invalid_schema_refusal_and_authority_expansion() -> None:
    invalid = LLMDecisionResultValidator.validate(
        ProviderModelResponse(provider_id="deepseek", model_id="deepseek-v4-pro", content={"decision": "continue"})
    )
    assert invalid.outcome_class is ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA
    assert invalid.success is False

    refusal = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            refusal=True,
            content={"decision": "refuse", "rationale": "provider refused", "evidence_refs": []},
        )
    )
    assert refusal.outcome_class is ModelExecutionOutcomeClass.PROVIDER_REFUSAL
    assert refusal.success is False

    expansion = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={
                "decision": "execute",
                "rationale": "bad authority expansion",
                "evidence_refs": ["evidence_1"],
                "grant_tools": ["shell"],
            },
        )
    )
    assert expansion.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED
    assert expansion.authority_expansion is True


def test_coordinator_default_off_returns_deferred_outcome() -> None:
    coordinator = ModelExecutionCoordinator()
    outcome = coordinator.execute(request=_request())

    assert outcome.outcome_class is ModelExecutionOutcomeClass.DISABLED_BACKEND
    assert outcome.success is False
    assert outcome.result is None
    assert outcome.receipt is None


def test_coordinator_cannot_fake_success() -> None:
    registry = ModelProviderRegistry()
    registry.register(RecordingProvider(response=None))
    resolver = StaticCredentialResolver(
        ProviderCredentialHandle.from_env(
            provider_id="deepseek",
            env_var_name="SENTINEL_TEST_MODEL_KEY",
            scopes=["model:read"],
        )
    )
    coordinator = ModelExecutionCoordinator(registry=registry, credential_resolver=resolver)

    outcome = coordinator.execute(request=_request())

    assert outcome.success is False
    assert outcome.outcome_class is ModelExecutionOutcomeClass.MODEL_EXECUTION_DEFERRED
    assert outcome.result is None
    assert outcome.receipt is None


def test_coordinator_validates_provider_response_and_builds_safe_receipt() -> None:
    provider_response = ProviderModelResponse(
        provider_id="deepseek",
        model_id="deepseek-v4-pro",
        content={"decision": "continue", "rationale": "validated by provider", "evidence_refs": ["evidence_1"]},
        input_tokens=100,
        output_tokens=20,
    )
    provider = RecordingProvider(response=provider_response)
    registry = ModelProviderRegistry()
    registry.register(provider)
    resolver = StaticCredentialResolver(
        ProviderCredentialHandle.from_env(
            provider_id="deepseek",
            env_var_name="SENTINEL_TEST_MODEL_KEY",
            scopes=["model:read"],
        )
    )
    coordinator = ModelExecutionCoordinator(registry=registry, credential_resolver=resolver)
    request = _request()

    outcome = coordinator.execute(request=request)

    assert provider.calls == 1
    assert outcome.success is True
    assert outcome.outcome_class is ModelExecutionOutcomeClass.SUCCESS_VALIDATED
    assert outcome.result is not None
    assert outcome.result.decision == "continue"
    assert outcome.receipt is not None
    dumped = outcome.receipt.model_dump_json()
    assert RAW_PROMPT not in dumped
    assert SECRET_VALUE not in dumped


def test_model_output_never_executes_tools_or_organs() -> None:
    result = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={
                "decision": "continue",
                "rationale": "only a decision artifact",
                "evidence_refs": ["evidence_1"],
                "tool_calls": [{"tool": "shell"}],
                "organ_execution": {"organ": "desktop"},
            },
        )
    )

    assert result.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED
    assert result.tool_execution_requested is True
    assert result.organ_execution_requested is True


class RecordingProvider:
    provider_id = "deepseek"
    backend_id = "unit-test-structural"

    def __init__(
        self,
        *,
        provider_id: str = "deepseek",
        enabled: bool = True,
        is_fake_provider: bool = False,
        supported_models: tuple[str, ...] = ("deepseek-v4-pro",),
        response: ProviderModelResponse | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.enabled = enabled
        self.is_fake_provider = is_fake_provider
        self.supported_models = supported_models
        self.metadata = ProviderCapabilityMetadata(
            provider_id=provider_id,
            backend_id=self.backend_id,
            supported_models=list(supported_models),
            enabled=enabled,
        )
        self.response = response
        self.calls = 0

    def execute(self, request, *, timeout, credential):  # noqa: ANN001, ANN201
        self.calls += 1
        return self.response


class StaticCredentialResolver:
    def __init__(self, credential: ProviderCredentialHandle) -> None:
        self.credential = credential

    def resolve(self, *, provider_id: str, required_scopes: list[str]):
        return self.credential


def test_real_model_provider_protocol_accepts_structural_provider() -> None:
    assert isinstance(RecordingProvider(), RealModelProvider)


def test_timeout_policy_rejects_unbounded_or_zero_timeout() -> None:
    with pytest.raises(ValidationError):
        ModelTimeoutPolicy(connect_timeout_seconds=0.0, read_timeout_seconds=1.0, total_timeout_seconds=1.0)
    with pytest.raises(ValidationError):
        ModelTimeoutPolicy(connect_timeout_seconds=1.0, read_timeout_seconds=1.0, total_timeout_seconds=0.0)
