from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.event_bus import EventBus
from sentinel.agent.runtime import AgentRuntime
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.perf.caches.model_call_optimizer import ModelCallOptimizer
from sentinel.perf.caches.token_budget_governor import BudgetDecision, REASON_FRAME_REJECTED, REASON_WITHIN_BUDGET, TokenBudgetGovernor
from sentinel.shared.enums import MissionMode, MissionStatus, MissionType


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


def envelope(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "LLM decision cycle test",
        "mission_objective": "Create a safe local GTM pack with a compact LLM decision frame.",
        "success_criteria": ["GTM files exist", "Trace exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["send_email", "run_shell_command", "credential_access"],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def user_model_contract(model: str = "deepseek-v4-pro") -> UserModelContract:
    return UserModelContract(
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.14,
            output_usd_per_1m=0.28,
            cached_input_usd_per_1m=0.05,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=128_000,
            supports_tool_calling=True,
            supports_prompt_caching=True,
            strengths=["cheap_context", "agent_planning"],
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=8_000,
            max_tool_schema_tokens=1_000,
            max_evidence_tokens=2_000,
            reserve_output_tokens=1_000,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="runtime_planning",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def tight_user_model_contract(model: str = "deepseek-v4-pro") -> UserModelContract:
    contract = user_model_contract(model)
    return contract.model_copy(
        update={
            "context_budget_policy": ContextBudgetPolicy(
                max_decision_frame_tokens=50,
                max_tool_schema_tokens=10,
                max_evidence_tokens=10,
                reserve_output_tokens=10,
            )
        }
    )


class RecordingDecisionFrameCache:
    def __init__(self) -> None:
        self.inputs: dict[str, str] | None = None
        self.stored = False

    def composite_hash(
        self,
        *,
        mission_hot_hash: str,
        authority_hash: str,
        evidence_set_hash: str,
        tool_surface_hash: str,
    ) -> str:
        self.inputs = {
            "mission_hot_hash": mission_hot_hash,
            "authority_hash": authority_hash,
            "evidence_set_hash": evidence_set_hash,
            "tool_surface_hash": tool_surface_hash,
        }
        raw = json.dumps(self.inputs, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, composite: str, *, mission_id: str):  # noqa: ANN001
        return None

    def put(self, composite: str, frame, *, mission_id: str) -> None:  # noqa: ANN001
        self.stored = True


class RecordingPromptFrameCache:
    def __init__(self) -> None:
        self.called = False

    def get_or_render(self, frame, renderer, *, mission_id: str | None = None, verify: bool = False):  # noqa: ANN001
        self.called = True
        return renderer(frame)


class RecordingTokenBudgetGovernor:
    def __init__(self) -> None:
        self.called = False
        self.frame_budget: int | None = None

    def enforce_frame(self, mission_id: str, frame_builder, compressor, frame_budget: int):  # noqa: ANN001
        self.called = True
        self.frame_budget = frame_budget
        frame = frame_builder()
        return frame, BudgetDecision(
            accepted=True,
            tokens_used=frame.token_count,
            tokens_budget=frame_budget,
            reason=REASON_WITHIN_BUDGET,
        )


def test_agent_runtime_default_off_keeps_existing_result_shape(tmp_path: Path):
    env = envelope()

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": "Sentinel SPINE"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    assert result.success is True
    assert result.mission_result is not None
    assert result.mission_result.state.status == MissionStatus.COMPLETED
    assert result.llm_decision_cycle is None


def test_agent_runtime_builds_frame_prompt_and_model_plan_without_model_execution(tmp_path: Path):
    contract = user_model_contract()
    optimizer = ModelCallOptimizer(default_model_id=contract.selected_model, default_backend="deepseek")

    result = AgentRuntime(
        project_root=tmp_path,
        user_model_contract=contract,
        model_call_optimizer=optimizer,
    ).run(
        envelope(),
        {"idea": "Sentinel SPINE"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    cycle = result.llm_decision_cycle
    assert result.success is True
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True
    assert cycle is not None
    assert cycle["frame_hash"]
    assert cycle["prompt_sha256"] and len(cycle["prompt_sha256"]) == 64
    assert cycle["prompt_token_count"] > 0
    assert cycle["model_execution_deferred"] is True
    assert cycle["model_execution_deferral_id"] == "LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER"
    assert cycle["model_call_plan"]["model_id"] == contract.selected_model
    assert "prompt_text" not in cycle


def test_decision_cycle_cache_budget_and_prompt_wrappers_are_used(tmp_path: Path):
    contract = user_model_contract()
    decision_cache = RecordingDecisionFrameCache()
    prompt_cache = RecordingPromptFrameCache()
    budget_governor = RecordingTokenBudgetGovernor()

    env = envelope()
    result = AgentRuntime(
        project_root=tmp_path,
        decision_frame_cache=decision_cache,
        prompt_frame_cache=prompt_cache,
        token_budget_governor=budget_governor,
        user_model_contract=contract,
        model_call_optimizer=ModelCallOptimizer(default_model_id=contract.selected_model),
    ).run(env, {"idea": "Sentinel SPINE"}, evidence_refs=["ev_direct"])

    assert result.success is True
    assert decision_cache.stored is True
    assert decision_cache.inputs is not None
    assert env.id not in decision_cache.inputs.values()
    assert "v1" not in decision_cache.inputs.values()
    assert decision_cache.inputs["mission_hot_hash"] == result.llm_decision_cycle["cache_key"]["mission_hot_hash"]
    assert decision_cache.inputs["authority_hash"] == result.llm_decision_cycle["cache_key"]["authority_hash"]
    assert prompt_cache.called is True
    assert budget_governor.called is True
    assert budget_governor.frame_budget == contract.context_budget_policy.max_decision_frame_tokens


def test_decision_cycle_keeps_tool_surface_inside_authority_and_preserves_user_model(tmp_path: Path):
    contract = user_model_contract("qwen-3.5-max")
    env = envelope(allowed_tools=["safe_file_writer"])

    result = AgentRuntime(
        project_root=tmp_path,
        user_model_contract=contract,
        model_call_optimizer=ModelCallOptimizer(default_model_id=contract.selected_model),
    ).run(env, {"idea": "Sentinel SPINE"}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    assert set(cycle["selected_tool_surface"]).issubset(set(env.allowed_tools))
    assert cycle["user_selected_model"] == contract.selected_model
    assert cycle["model_call_plan"]["model_id"] == contract.selected_model


def test_decision_cycle_records_optimizer_alternative_without_overriding_user_model(tmp_path: Path):
    contract = user_model_contract("deepseek-v4-pro")

    result = AgentRuntime(
        project_root=tmp_path,
        user_model_contract=contract,
        model_call_optimizer=ModelCallOptimizer(default_model_id="gpt-5.5"),
    ).run(envelope(), {"idea": "Sentinel SPINE"}, evidence_refs=["ev_direct"])

    cycle = result.llm_decision_cycle
    assert cycle is not None
    assert cycle["user_selected_model"] == contract.selected_model
    assert cycle["model_call_plan"] is None
    assert cycle["model_call_recommendation"]["model_id"] == "gpt-5.5"


def test_decision_cycle_metadata_excludes_raw_prompt_and_secrets(tmp_path: Path):
    contract = user_model_contract()

    result = AgentRuntime(
        project_root=tmp_path,
        user_model_contract=contract,
        model_call_optimizer=ModelCallOptimizer(default_model_id=contract.selected_model),
    ).run(
        envelope(),
        {"idea": "Sentinel SPINE", "note": "password=redaction-test-value"},
        evidence_refs=["ev_direct"],
    )

    dumped = json.dumps(result.llm_decision_cycle, sort_keys=True)
    trace_dump = json.dumps([event.model_dump(mode="json") for event in result.trace], sort_keys=True)
    assert "redaction-test-value" not in dumped
    assert "redaction-test-value" not in trace_dump
    assert "prompt_text" not in dumped


def test_real_token_budget_governor_rejects_oversized_frame_without_context_compressor_crash(tmp_path: Path):
    contract = tight_user_model_contract()
    env = envelope()

    result = AgentRuntime(
        project_root=tmp_path,
        token_budget_governor=TokenBudgetGovernor(event_bus=EventBus(env.id), max_compression_passes=1),
        user_model_contract=contract,
        model_call_optimizer=ModelCallOptimizer(default_model_id=contract.selected_model),
    ).run(env, {"idea": "Sentinel SPINE"}, evidence_refs=["ev_direct", "ev_wtp"])

    cycle = result.llm_decision_cycle
    assert result.success is True
    assert cycle is not None
    assert cycle["budget_decision"]["accepted"] is False
    assert cycle["budget_decision"]["reason"] == REASON_FRAME_REJECTED
