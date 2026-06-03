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
    ModelExecutionBudgetLedger,
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
        selected_provider_id="deepseek",
        selected_backend_id="deepseek_chat_completions",
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
        provider_id="deepseek",
        backend_id="deepseek_chat_completions",
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


def test_provider_registry_rejects_string_false_enabled_provider() -> None:
    registry = ModelProviderRegistry()
    provider = RecordingProvider(enabled="false")  # type: ignore[arg-type]
    registry.register(provider)

    with pytest.raises(PermissionError):
        registry.get_enabled(provider.provider_id, model_id="deepseek-v4-pro")


def test_user_model_contract_requires_provider_backend_model_identity() -> None:
    with pytest.raises(ValidationError):
        UserModelContract(
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


def test_request_builder_keeps_provider_id_and_backend_id_distinct() -> None:
    timeout, retry, budget = _policies()
    plan = _model_call_plan().model_copy(
        update={
            "provider_id": "deepseek",
            "backend_id": "deepseek_chat_completions",
            "backend": "legacy_backend_alias",
        }
    )

    request = RealModelRequestBuilder.build(
        frame=_decision_frame(),
        rendered_prompt=RAW_PROMPT,
        plan=plan,
        user_model=_model_contract(),
        timeout_policy=timeout,
        retry_policy=retry,
        budget_policy=budget,
    )

    assert request.provider_id == "deepseek"
    assert request.backend_id == "deepseek_chat_completions"
    assert request.backend == "deepseek_chat_completions"


def test_request_builder_rejects_provider_backend_or_model_mismatch() -> None:
    timeout, retry, budget = _policies()

    with pytest.raises(ValueError, match="provider"):
        RealModelRequestBuilder.build(
            frame=_decision_frame(),
            rendered_prompt=RAW_PROMPT,
            plan=_model_call_plan().model_copy(update={"provider_id": "openrouter"}),
            user_model=_model_contract(),
            timeout_policy=timeout,
            retry_policy=retry,
            budget_policy=budget,
        )

    with pytest.raises(ValueError, match="backend"):
        RealModelRequestBuilder.build(
            frame=_decision_frame(),
            rendered_prompt=RAW_PROMPT,
            plan=_model_call_plan().model_copy(update={"backend_id": "other_backend"}),
            user_model=_model_contract(),
            timeout_policy=timeout,
            retry_policy=retry,
            budget_policy=budget,
        )


def test_registry_rejects_duplicate_provider_id() -> None:
    registry = ModelProviderRegistry()
    registry.register(RecordingProvider())

    with pytest.raises(ValueError, match="duplicate provider_id"):
        registry.register(RecordingProvider())


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


def test_environment_credential_resolver_requires_requested_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTINEL_TEST_MODEL_KEY", SECRET_VALUE)
    resolver = EnvironmentCredentialResolver(
        {"deepseek": {"env_var": "SENTINEL_TEST_MODEL_KEY", "scopes": ["model:write"]}}
    )

    resolved = resolver.resolve(provider_id="deepseek", required_scopes=["model:read"])

    assert resolved.outcome_class is ModelExecutionOutcomeClass.MISSING_CREDENTIAL
    assert resolved.credential is None


def test_coordinator_rejects_credential_handle_missing_required_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTINEL_TEST_MODEL_KEY", SECRET_VALUE)
    provider = RecordingProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    resolver = StaticCredentialResolver(
        ProviderCredentialHandle.from_env(
            provider_id="deepseek",
            env_var_name="SENTINEL_TEST_MODEL_KEY",
            scopes=["model:write"],
        )
    )
    coordinator = ModelExecutionCoordinator(registry=registry, credential_resolver=resolver)

    outcome = coordinator.execute(request=_request())

    assert outcome.outcome_class is ModelExecutionOutcomeClass.MISSING_CREDENTIAL
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


def test_coordinator_rejects_catalog_disabled_or_diagnostic_provider() -> None:
    from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog

    registry = ModelProviderRegistry()
    provider = RecordingProvider(provider_id="openrouter", supported_models=("deepseek/deepseek-v4-flash:free",))
    registry.register(provider)
    request = _request().model_copy(
        update={
            "provider_id": "openrouter",
            "backend_id": "openrouter_chat_completions",
            "backend": "openrouter_chat_completions",
            "model_id": "deepseek/deepseek-v4-flash:free",
        }
    )
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="openrouter",
                env_var_name="OPENROUTER_API_KEY",
                scopes=["model:read"],
            )
        ),
        provider_catalog=build_default_provider_catalog(),
        enabled_provider_ids={"openrouter"},
    )

    outcome = coordinator.execute(request=request)

    assert outcome.outcome_class is ModelExecutionOutcomeClass.DISABLED_BACKEND
    assert outcome.success is False
    assert provider.calls == 0


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


def test_coordinator_rejects_provider_response_identity_mismatch() -> None:
    provider_response = ProviderModelResponse(
        provider_id="deepseek",
        model_id="silently-overridden-model",
        content={"decision": "continue", "rationale": "identity mismatch", "evidence_refs": ["evidence_1"]},
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

    outcome = coordinator.execute(request=_request())

    assert provider.calls == 1
    assert outcome.success is False
    assert outcome.outcome_class is ModelExecutionOutcomeClass.DISABLED_BACKEND
    assert outcome.result is None
    assert outcome.receipt is None


def test_action_budget_blocks_oversized_model_request_before_provider_call() -> None:
    provider = RecordingProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ModelExecutionBudgetLedger(mission_id="mission_pack_a"),
    )
    request = _request().model_copy(update={"estimated_input_tokens": 2_001})

    outcome = coordinator.execute(request=request)

    assert outcome.outcome_class is ModelExecutionOutcomeClass.BUDGET_REJECTED
    assert outcome.success is False
    assert outcome.provider_called is False
    assert provider.calls == 0
    assert outcome.budget_summary["compliant"] is False
    assert outcome.budget_summary["decision"] == "action_input_tokens_exceeded"


def test_mission_budget_accumulates_across_multiple_model_calls() -> None:
    response = ProviderModelResponse(
        provider_id="deepseek",
        model_id="deepseek-v4-pro",
        content={"decision": "continue", "rationale": "within mission budget", "evidence_refs": ["evidence_1"]},
        input_tokens=60,
        output_tokens=40,
    )
    provider = RecordingProvider(response=response)
    registry = ModelProviderRegistry()
    registry.register(provider)
    ledger = ModelExecutionBudgetLedger(mission_id="mission_pack_a", max_mission_total_tokens=220)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ledger,
    )

    first = coordinator.execute(request=_request().model_copy(update={"estimated_input_tokens": 10, "estimated_output_tokens": 10}))
    second = coordinator.execute(
        request=_request().model_copy(
            update={"id": "model_request_second", "estimated_input_tokens": 10, "estimated_output_tokens": 10}
        )
    )

    assert first.success is True
    assert second.success is True
    assert ledger.safe_summary()["used_input_tokens"] == 120
    assert ledger.safe_summary()["used_output_tokens"] == 80
    assert ledger.safe_summary()["used_total_tokens"] == 200
    assert provider.calls == 2


def test_mission_budget_exhaustion_blocks_further_model_calls() -> None:
    response = ProviderModelResponse(
        provider_id="deepseek",
        model_id="deepseek-v4-pro",
        content={"decision": "continue", "rationale": "first call only", "evidence_refs": ["evidence_1"]},
        input_tokens=60,
        output_tokens=40,
    )
    provider = RecordingProvider(response=response)
    registry = ModelProviderRegistry()
    registry.register(provider)
    ledger = ModelExecutionBudgetLedger(mission_id="mission_pack_a", max_mission_total_tokens=110)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ledger,
    )

    first = coordinator.execute(request=_request().model_copy(update={"estimated_input_tokens": 10, "estimated_output_tokens": 10}))
    second = coordinator.execute(
        request=_request().model_copy(
            update={"id": "model_request_second", "estimated_input_tokens": 10, "estimated_output_tokens": 10}
        )
    )

    assert first.success is True
    assert second.outcome_class is ModelExecutionOutcomeClass.BUDGET_REJECTED
    assert second.provider_called is False
    assert second.budget_summary["decision"] == "mission_total_tokens_exhausted"
    assert provider.calls == 1


def test_actual_usage_budget_overrun_is_not_returned_as_success() -> None:
    response = ProviderModelResponse(
        provider_id="deepseek",
        model_id="deepseek-v4-pro",
        content={"decision": "continue", "rationale": "actual usage overran budget", "evidence_refs": ["evidence_1"]},
        input_tokens=2_500,
        output_tokens=40,
    )
    provider = RecordingProvider(response=response)
    registry = ModelProviderRegistry()
    registry.register(provider)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ModelExecutionBudgetLedger(mission_id="mission_pack_a"),
    )

    outcome = coordinator.execute(
        request=_request().model_copy(update={"estimated_input_tokens": 10, "estimated_output_tokens": 10})
    )

    assert outcome.outcome_class is ModelExecutionOutcomeClass.BUDGET_REJECTED
    assert outcome.success is False
    assert outcome.provider_called is True
    assert outcome.result is not None
    assert outcome.result.success is True
    assert outcome.budget_summary["compliant"] is False
    assert outcome.budget_summary["decision"] == "actual_action_input_tokens_exceeded"
    assert provider.calls == 1


def test_retry_attempts_consume_retry_budget() -> None:
    provider = RecordingProvider(
        response=ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={"decision": "continue", "rationale": "retry budget accounting", "evidence_refs": ["evidence_1"]},
            input_tokens=10,
            output_tokens=5,
        )
    )
    registry = ModelProviderRegistry()
    registry.register(provider)
    ledger = ModelExecutionBudgetLedger(mission_id="mission_pack_a", max_mission_retry_attempts=1)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ledger,
    )

    first = coordinator.execute(request=_request().model_copy(update={"estimated_input_tokens": 10, "estimated_output_tokens": 10}))
    second = coordinator.execute(
        request=_request().model_copy(
            update={"id": "model_request_second", "estimated_input_tokens": 10, "estimated_output_tokens": 10}
        )
    )

    assert first.success is True
    assert ledger.safe_summary()["used_retry_attempts"] == 1
    assert second.outcome_class is ModelExecutionOutcomeClass.BUDGET_REJECTED
    assert second.budget_summary["decision"] == "mission_retry_attempts_exhausted"
    assert provider.calls == 1


def test_timeout_budget_is_enforced_or_recorded_honestly() -> None:
    timeout, retry, _budget = _policies()
    constrained_budget = ModelExecutionBudgetPolicy(
        max_input_tokens=2_000,
        max_output_tokens=500,
        max_total_estimated_usd=0.01,
        max_provider_time_seconds_per_action=5.0,
    )
    request = RealModelRequestBuilder.build(
        frame=_decision_frame(),
        rendered_prompt=RAW_PROMPT,
        plan=_model_call_plan(),
        user_model=_model_contract(),
        timeout_policy=timeout,
        retry_policy=retry,
        budget_policy=constrained_budget,
    )
    provider = RecordingProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ModelExecutionBudgetLedger(mission_id="mission_pack_a"),
    )

    outcome = coordinator.execute(request=request)

    assert outcome.outcome_class is ModelExecutionOutcomeClass.BUDGET_REJECTED
    assert outcome.provider_called is False
    assert outcome.budget_summary["decision"] == "action_provider_time_budget_exceeded"
    assert outcome.budget_summary["provider_time_budget_seconds"] == 5.0


def test_budget_metadata_contains_no_raw_prompt_response_reasoning_or_key() -> None:
    provider = RecordingProvider()
    registry = ModelProviderRegistry()
    registry.register(provider)
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=StaticCredentialResolver(
            ProviderCredentialHandle.from_env(
                provider_id="deepseek",
                env_var_name="SENTINEL_TEST_MODEL_KEY",
                scopes=["model:read"],
            )
        ),
        budget_ledger=ModelExecutionBudgetLedger(mission_id="mission_pack_a"),
    )

    outcome = coordinator.execute(request=_request().model_copy(update={"estimated_input_tokens": 2_001}))
    dumped = str(outcome.budget_summary)

    assert RAW_PROMPT not in dumped
    assert SECRET_VALUE not in dumped
    assert "reasoning_details" not in dumped
    assert "raw_response" not in dumped


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


def test_validator_recursively_rejects_nested_tool_or_organ_intent() -> None:
    result = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={
                "decision": "continue",
                "rationale": "nested action attempt",
                "evidence_refs": ["evidence_1"],
                "nested": {
                    "Tool_Calls": [{"name": "shell"}],
                    "browser": {"submit": True},
                    "payment": {"amount": 10},
                },
            },
        )
    )

    assert result.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED
    assert result.tool_execution_requested is True
    assert result.authority_expansion is True


def test_validator_redacts_secret_like_rationale_before_durable_result() -> None:
    result = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={
                "decision": "continue",
                "rationale": "echoed prompt sk-test-unit-secret-1234567890 reasoning_details raw provider text",
                "evidence_refs": ["evidence_1"],
            },
        )
    )

    dumped = result.model_dump_json()
    assert "sk-test-unit-secret-1234567890" not in dumped
    assert "reasoning_details" not in dumped
    assert result.rationale_summary != "echoed prompt sk-test-unit-secret-1234567890 reasoning_details raw provider text"


def test_model_evidence_refs_must_bind_to_decision_frame_evidence() -> None:
    result = LLMDecisionResultValidator.validate(
        ProviderModelResponse(
            provider_id="deepseek",
            model_id="deepseek-v4-pro",
            content={
                "decision": "continue",
                "rationale": "invented evidence",
                "evidence_refs": ["invented_ref"],
            },
        ),
        allowed_evidence_refs={"evidence_1"},
    )

    assert result.outcome_class is ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA
    assert result.success is False


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
