from __future__ import annotations

import json
import os
from pathlib import Path

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import (
    EnvironmentCredentialResolver,
    LLMDecisionResult,
    ModelExecutionCoordinator,
    ModelExecutionOutcome,
    ModelExecutionOutcomeClass,
    ModelProviderRegistry,
    ModelTimeoutPolicy,
    RealModelRequest,
    build_model_execution_receipt,
)
from sentinel.agent.model_execution.groq import GROQ_DEFAULT_MODEL_ID, GroqChatCompletionsProvider
from sentinel.agent.runtime import AgentRuntime
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.perf.caches.model_call_optimizer import ModelCallOptimizer
from sentinel.shared.enums import MissionMode, MissionType


SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "generate_research_questions",
    "write_trace",
]


def envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="user_runtime_model",
        mission_type=MissionType.GTM,
        mission_title="Runtime model execution wiring",
        mission_objective="Create a safe local GTM pack with model execution metadata.",
        success_criteria=["GTM files exist", "Trace exists"],
        mode=MissionMode.POWER,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_file_writer"],
        allowed_actions=SAFE_ACTIONS,
        forbidden_actions=["send_email", "run_shell_command", "credential_access"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=30,
        max_actions=20,
        max_cost_usd=1.0,
    )


def user_model_contract(model: str = "unit/model-alpha") -> UserModelContract:
    return UserModelContract(
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.10,
            output_usd_per_1m=0.20,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=32_000,
            supports_tool_calling=False,
            supports_prompt_caching=True,
            strengths=["runtime_test"],
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=200,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="runtime_model_execution_wiring",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


class RecordingModelExecutionCoordinator:
    def __init__(self, outcome_class: ModelExecutionOutcomeClass = ModelExecutionOutcomeClass.SUCCESS_VALIDATED) -> None:
        self.outcome_class = outcome_class
        self.calls: list[RealModelRequest] = []

    def execute(self, *, request: RealModelRequest) -> ModelExecutionOutcome:
        self.calls.append(request)
        success = self.outcome_class is ModelExecutionOutcomeClass.SUCCESS_VALIDATED
        result = LLMDecisionResult(
            provider_id=request.provider_id,
            model_id=request.model_id,
            decision="continue" if success else "reject",
            rationale_summary="validated runtime metadata",
            evidence_refs=["ev_direct"],
            confidence=0.9 if success else None,
            outcome_class=self.outcome_class,
            success=success,
            authority_expansion=self.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED,
            tool_execution_requested=self.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED,
            organ_execution_requested=self.outcome_class is ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED,
            sanitized_response_hash="a" * 64,
            input_tokens=11,
            output_tokens=7,
            cost_usd=0.00001,
        )
        receipt = build_model_execution_receipt(
            request=request,
            outcome_class=result.outcome_class,
            result=result,
            credential=None,
            attempts=1,
        )
        return ModelExecutionOutcome(
            outcome_class=result.outcome_class,
            success=result.success,
            result=result,
            receipt=receipt,
            provider_called=True,
        )


def _runtime(
    tmp_path: Path,
    *,
    contract: UserModelContract,
    optimizer: ModelCallOptimizer,
    coordinator: RecordingModelExecutionCoordinator | None = None,
) -> AgentRuntime:
    return AgentRuntime(
        project_root=tmp_path,
        user_model_contract=contract,
        model_call_optimizer=optimizer,
        model_execution_coordinator=coordinator,
    )


def test_runtime_model_execution_is_default_off_without_coordinator(tmp_path: Path) -> None:
    contract = user_model_contract()

    result = _runtime(
        tmp_path,
        contract=contract,
        optimizer=ModelCallOptimizer(default_model_id=contract.selected_model, default_backend="unit_provider"),
    ).run(envelope(), {"idea": "Sentinel"}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    assert cycle["model_call_plan"]["model_id"] == contract.selected_model
    assert cycle["model_execution"]["enabled"] is False
    assert cycle["model_execution_deferred"] is True
    assert cycle["model_execution_deferral_id"] == "LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER"
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True


def test_runtime_calls_provider_agnostic_coordinator_after_model_call_plan(tmp_path: Path) -> None:
    contract = user_model_contract("unit/model-alpha")
    coordinator = RecordingModelExecutionCoordinator()

    result = _runtime(
        tmp_path,
        contract=contract,
        optimizer=ModelCallOptimizer(default_model_id=contract.selected_model, default_backend="unit_provider"),
        coordinator=coordinator,
    ).run(envelope(), {"idea": "Sentinel"}, evidence_refs=["ev_direct"])

    assert len(coordinator.calls) == 1
    request = coordinator.calls[0]
    assert request.provider_id == "unit_provider"
    assert request.model_id == contract.selected_model
    assert request.prompt_hash
    assert request.prompt_text_in_memory_only is not None

    cycle = result.llm_decision_cycle
    assert cycle is not None
    assert cycle["model_execution"]["enabled"] is True
    assert cycle["model_execution"]["success"] is True
    assert cycle["model_execution"]["outcome_class"] == "SUCCESS_VALIDATED"
    assert cycle["model_execution"]["request"]["provider_id"] == "unit_provider"
    assert cycle["model_execution"]["request"]["model_id"] == contract.selected_model
    assert cycle["model_execution"]["result"]["decision"] == "continue"
    assert "prompt_text_in_memory_only" not in json.dumps(cycle, sort_keys=True)


def test_runtime_does_not_hardcode_groq_provider() -> None:
    runtime_source = Path("sentinel/agent/runtime.py").read_text(encoding="utf-8")

    assert "groq" not in runtime_source.lower()


def test_optimizer_recommendation_cannot_override_user_selected_model_or_execute(tmp_path: Path) -> None:
    contract = user_model_contract("unit/user-selected")
    coordinator = RecordingModelExecutionCoordinator()

    result = _runtime(
        tmp_path,
        contract=contract,
        optimizer=ModelCallOptimizer(default_model_id="unit/optimizer-recommendation", default_backend="unit_provider"),
        coordinator=coordinator,
    ).run(envelope(), {"idea": "Sentinel"}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    assert cycle["user_selected_model"] == contract.selected_model
    assert cycle["model_call_plan"] is None
    assert cycle["model_call_recommendation"]["model_id"] == "unit/optimizer-recommendation"
    assert cycle["model_execution"]["enabled"] is False
    assert coordinator.calls == []


def test_model_output_cannot_execute_tools_or_organs_and_final_gate_still_runs(tmp_path: Path) -> None:
    contract = user_model_contract()
    coordinator = RecordingModelExecutionCoordinator(ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED)

    result = _runtime(
        tmp_path,
        contract=contract,
        optimizer=ModelCallOptimizer(default_model_id=contract.selected_model, default_backend="unit_provider"),
        coordinator=coordinator,
    ).run(envelope(), {"idea": "Sentinel"}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    model_execution = cycle["model_execution"]
    assert model_execution["success"] is False
    assert model_execution["outcome_class"] == "AUTHORITY_EXPANSION_REJECTED"
    assert model_execution["result"]["tool_execution_requested"] is True
    assert model_execution["result"]["organ_execution_requested"] is True
    assert result.controlled_capability_results == []
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True


def test_runtime_real_groq_provider_success_validated_skip_safe(tmp_path: Path) -> None:
    if not _ensure_groq_key_loaded_from_process_or_dotenv():
        import pytest

        pytest.skip("GROQ_API_KEY absent from process env and ignored .env; skipping real runtime model call")

    contract = user_model_contract(GROQ_DEFAULT_MODEL_ID).model_copy(
        update={
            "context_budget_policy": ContextBudgetPolicy(
                max_decision_frame_tokens=2_000,
                max_tool_schema_tokens=250,
                max_evidence_tokens=1_000,
                reserve_output_tokens=800,
            )
        }
    )
    registry = ModelProviderRegistry()
    registry.register(GroqChatCompletionsProvider())
    coordinator = ModelExecutionCoordinator(
        registry=registry,
        credential_resolver=EnvironmentCredentialResolver({"groq": {"env_var": "GROQ_API_KEY", "scopes": ["model:read"]}}),
        timeout_policy=ModelTimeoutPolicy(
            connect_timeout_seconds=5.0,
            read_timeout_seconds=60.0,
            total_timeout_seconds=90.0,
        ),
    )

    result = _runtime(
        tmp_path,
        contract=contract,
        optimizer=ModelCallOptimizer(default_model_id=contract.selected_model, default_backend="groq"),
        coordinator=coordinator,
    ).run(envelope(), {"idea": "Return a safe compact GTM decision only."}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    model_execution = cycle["model_execution"]
    assert model_execution["enabled"] is True
    assert model_execution["provider_called"] is True
    assert model_execution["success"] is True
    assert model_execution["outcome_class"] == ModelExecutionOutcomeClass.SUCCESS_VALIDATED.value
    assert model_execution["request"]["provider_id"] == "groq"
    assert model_execution["request"]["model_id"] == GROQ_DEFAULT_MODEL_ID
    assert model_execution["result"]["model_id"] == GROQ_DEFAULT_MODEL_ID
    assert model_execution["result"]["outcome_class"] == ModelExecutionOutcomeClass.SUCCESS_VALIDATED.value
    assert model_execution["result"]["authority_expansion"] is False
    assert model_execution["result"]["tool_execution_requested"] is False
    assert model_execution["result"]["organ_execution_requested"] is False
    assert result.controlled_capability_results == []
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True

    dumped = json.dumps(cycle, sort_keys=True)
    assert os.environ["GROQ_API_KEY"] not in dumped
    assert "prompt_text_in_memory_only" not in dumped
    assert "reasoning_details" not in dumped
    assert "raw_text" not in dumped


def _ensure_groq_key_loaded_from_process_or_dotenv() -> bool:
    if os.environ.get("GROQ_API_KEY"):
        return True
    dotenv = Path(".env")
    if not dotenv.exists():
        return False
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == "GROQ_API_KEY" and value.strip():
            os.environ["GROQ_API_KEY"] = value.strip().strip('"').strip("'")
            return True
    return False
