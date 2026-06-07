from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent import AgentEventType, AgentPhase, AgentRuntime
from sentinel.agent.brain.cognition_loop import BrainCognitionInput, BrainCognitionLoop
from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.llm.memory_bridge import MemoryBridgeResult, RoleLoopMemoryBridge
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.agent.organs.organ_dispatch import OrganDispatcher
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionConfig, OrganRuntimeExecutionMode
from sentinel.memory import PersistentMemoryIngestAdapter, PersistentSemanticMemoryService
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs.browser.models import BrowserFetchedPage
from sentinel.shared.enums import MissionMode, MissionType


NOW = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)
SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "export_json",
    "generate_research_questions",
    "write_trace",
]


class RecordingBrainLoop:
    def __init__(self, order: list[str] | None = None) -> None:
        self.calls: list[BrainCognitionInput | dict[str, Any]] = []
        self.order = order
        self.delegate = BrainCognitionLoop()

    def run(self, cognition_input: BrainCognitionInput | dict[str, Any]):
        self.calls.append(cognition_input)
        if self.order is not None:
            self.order.append("brain")
        return self.delegate.run(cognition_input)


class RecordingMemoryBridge:
    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.delegate = RoleLoopMemoryBridge()

    def build(self, bridge_input: Any) -> MemoryBridgeResult:
        self.calls.append(bridge_input)
        return self.delegate.build(bridge_input)


class RecordingDispatcher(OrganDispatcher):
    def __init__(self, order: list[str]) -> None:
        super().__init__()
        self.order = order

    def dispatch(self, **kwargs: Any):
        self.order.append("dispatch")
        return super().dispatch(**kwargs)


class FakeBrowserReadOnlyFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: Any, final_url: str) -> BrowserFetchedPage:
        self.calls.append(final_url)
        return BrowserFetchedPage(
            final_url="https://example.com/research",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body="<html><body>Public pricing is 49 dollars monthly.</body></html>",
        )


def _model_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model="openai/gpt-oss-20b",
        cost_profile=ModelCostProfile(
            model_name="openai/gpt-oss-20b",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="openai/gpt-oss-20b",
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=200,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="native_candidate_source",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _envelope(mission_id: str = "mission_native") -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_native",
        mission_type=MissionType.GTM,
        mission_title="Native Brain path test",
        mission_objective="Test native cognition to controlled organ feedback.",
        success_criteria=["all transitions are explicit"],
        mode=MissionMode.POWER,
        allowed_systems=["local_workspace", "public_web"],
        allowed_tools=["safe_file_writer"],
        allowed_actions=SAFE_ACTIONS,
        forbidden_actions=["send_email", "run_shell_command", "browser_submit", "credential_access", "api_mutation"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=30,
        max_actions=20,
        max_cost_usd=0.0,
    )


def _config(mode: OrganRuntimeExecutionMode, **updates: Any) -> OrganRuntimeExecutionConfig:
    browser = mode is OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY
    data: dict[str, Any] = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "brain_native_candidate_source_enabled": True,
        "memory_feedback_enabled": True,
        "temporary_candidate_bridge_enabled": False,
        "mode": mode,
        "allowed_action_levels": [DelegatedActionLevel.L4] if browser else [DelegatedActionLevel.L2, DelegatedActionLevel.L3],
        "allowed_organs": (
            ["browser_readonly", "browser_preparation", "browser_semantic_extraction"]
            if browser
            else ["local_artifact", "reversible_workspace"]
        ),
        "allow_l2": not browser,
        "allow_l3": not browser,
        "allow_browser_readonly": browser,
        "allow_browser_preparation": browser,
        "allow_browser_semantic_extraction": browser,
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _authority(levels: list[str], organs: list[str]) -> dict[str, Any]:
    browser = "browser" in organs
    return {
        "root_authority_present": True,
        "special_authority": browser,
        "user_review_granted": browser,
        "allowed_action_levels": levels,
        "allowed_organs": organs,
        "max_risk": "medium",
        "credential_scope": "none",
        "allowed_substeps": (
            ["browser_read_public_page", "browser_prepare_plan", "browser_semantic_extract"]
            if browser
            else ["create_generated_report", "replace_text_file"]
        ),
        "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
    }


def _contracts(tmp_path: Path, *, level: str) -> dict[str, dict[str, Any]]:
    if level == "L2":
        return {
            "file_operation": {
                "available": True,
                "allowed_action_levels": ["L2"],
                "required_receipt_fields": ["path_metadata", "artifact_hash", "lane_id", "gate_result_id"],
                "allowed_substeps": ["create_generated_report"],
                "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
                "allowed_workspace_root": str(tmp_path / "generated_root"),
                "allowed_artifact_subdir": "artifacts",
                "max_artifact_bytes": 4096,
            }
        }
    if level == "L3":
        return {
            "file_operation": {
                "available": True,
                "allowed_action_levels": ["L3"],
                "required_receipt_fields": ["path_metadata", "before_hash", "after_hash", "lane_id", "gate_result_id"],
                "allowed_substeps": ["replace_text_file"],
                "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
            },
            "reversible_workspace": {
                "available": True,
                "allowed_action_levels": ["L3"],
                "required_receipt_fields": ["path_metadata", "before_hash", "after_hash", "lane_id", "gate_result_id"],
                "allowed_workspace_root": str(tmp_path / "workspace_root"),
                "allowed_workspace_subdir": "work",
                "max_file_bytes": 4096,
                "max_patch_bytes": 2048,
                "allow_overwrite": True,
            },
        }
    receipt_fields = ["receipt_id", "lane_id", "gate_result_id", "forbidden_surface_absent"]
    return {
        "browser": {
            "available": True,
            "allowed_action_levels": ["L4"],
            "required_receipt_fields": receipt_fields,
            "allowed_substeps": ["browser_read_public_page", "browser_prepare_plan", "browser_semantic_extract"],
            "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "javascript"],
        },
        "browser_readonly": {
            "available": True,
            "allowed_domains": ["example.com"],
            "allowed_schemes": ["https"],
            "required_receipt_fields": receipt_fields,
        },
        "browser_preparation": {
            "available": True,
            "required_receipt_fields": receipt_fields,
            "max_candidate_targets": 4,
            "max_proposed_steps": 4,
        },
        "browser_semantic_extraction": {
            "available": True,
            "required_receipt_fields": receipt_fields,
            "max_evidence_cards": 6,
            "max_claims_per_source": 4,
        },
    }


def _l2_candidate(proposal_id: str = "brain_l2", path: str = "reports/native.md") -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "source_role_id": "planner",
        "artifact_kind": "file_operation_candidate",
        "action_level_candidate": "L2",
        "authority_class": "needs_gate",
        "risk_class": "low",
        "budget_estimate": {"action_count": 1, "artifact_bytes": 32},
        "evidence_refs": ["ev_l2"],
        "receipt_refs": ["receipt_l2"],
        "expected_outcome": "Create a local generated report.",
        "rollback_posture": "delete generated artifact with tombstone",
        "user_review_required": False,
        "safe_summary": "Create a local generated report.",
        "target_relative_path": path,
        "content": "# Native\n\nLocal artifact.",
        "action_kind": "create_generated_report",
    }


def _l3_candidate(before_hash: str) -> dict[str, Any]:
    return {
        "proposal_id": "brain_l3",
        "source_role_id": "planner",
        "artifact_kind": "file_operation_candidate",
        "action_level_candidate": "L3",
        "authority_class": "needs_gate",
        "risk_class": "medium",
        "budget_estimate": {"action_count": 1, "patch_bytes": 16},
        "evidence_refs": ["ev_l3"],
        "receipt_refs": ["receipt_l3"],
        "expected_outcome": "Replace one local text file reversibly.",
        "rollback_posture": "restore previous text from before snapshot",
        "user_review_required": False,
        "safe_summary": "Replace one local text file reversibly.",
        "target_relative_path": "docs/state.md",
        "content": "after\n",
        "before_hash": before_hash,
        "action_kind": "replace_text_file",
    }


def _browser_candidate(kind: str) -> dict[str, Any]:
    return {
        "proposal_id": f"brain_{kind}",
        "source_role_id": "researcher",
        "artifact_kind": "browser_step_candidate",
        "browser_organ_kind": kind,
        "action_level_candidate": "L4",
        "authority_class": "needs_user_review",
        "risk_class": "medium",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": [f"ev_{kind}"],
        "receipt_refs": [f"receipt_{kind}"],
        "expected_outcome": "Collect public web evidence as data.",
        "rollback_posture": "no external mutation; discard receipt",
        "user_review_required": False,
        "safe_summary": "Collect public web evidence without action.",
        "requested_url": "https://example.com/research",
        "objective_summary": "Collect public page evidence.",
        "validity_scope": "mission_native:web",
        "semantic_focus": ["pricing"],
        "candidate_goal": "Prepare non-executing evidence plan.",
    }


def _user_input(
    candidates: list[dict[str, Any]],
    *,
    authority: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
    temporary_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_refs = sorted({str(ref) for candidate in candidates for ref in candidate.get("evidence_refs", [])})
    return {
        "idea": "Native cognition dispatch fixture.",
        "organ_dispatch": {
            "brain_cognition_input": {
                "mission_id": "mission_native",
                "objective_summary": "Generate controlled proposal artifacts.",
                "user_model_contract": _model_contract().model_dump(mode="python"),
                "available_evidence_refs": evidence_refs,
                "existing_proposal_artifacts": candidates,
                "risk_flags": ["local_controlled_path"],
                "missing_evidence": ["follow_up_evidence"],
                "current_time": NOW,
            },
            "action_candidates": temporary_candidates or [],
            "authority": authority,
            "budget": {
                "remaining_action_count": 8,
                "remaining_retries": 1,
                "remaining_tokens": 100_000,
                "organ_budget_units": {"file_operation": 8, "browser": 8},
            },
            "available_evidence_refs": evidence_refs,
            "organ_contracts": contracts,
        },
    }


def _runtime(
    tmp_path: Path,
    config: OrganRuntimeExecutionConfig,
    *,
    fetcher: Any = None,
    order: list[str] | None = None,
    persistent_memory_ingest_adapter: PersistentMemoryIngestAdapter | None = None,
):
    brain = RecordingBrainLoop(order)
    memory = RecordingMemoryBridge()
    dispatcher = RecordingDispatcher(order) if order is not None else None
    runtime = AgentRuntime(
        project_root=tmp_path,
        organ_execution_config=config,
        brain_cognition_loop=brain,
        memory_bridge=memory,
        organ_dispatcher=dispatcher,
        browser_fetcher=fetcher,
        persistent_memory_ingest_adapter=persistent_memory_ingest_adapter,
    )
    return runtime, brain, memory


def test_default_off_exact_regression_skips_brain_memory_and_replan(tmp_path: Path) -> None:
    brain = RecordingBrainLoop()
    memory = RecordingMemoryBridge()
    result = AgentRuntime(project_root=tmp_path, brain_cognition_loop=brain, memory_bridge=memory).run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    assert result.organ_dispatch_result is None
    assert result.brain_cognition_result is None
    assert result.brain_candidate_source_status == "NOT_STARTED"
    assert result.memory_feedback_result is None
    assert result.memory_feedback_path == "NOT_STARTED"
    assert result.replan_packet is None
    assert brain.calls == []
    assert memory.calls == []
    assert not (tmp_path / "generated_root").exists()


def test_brain_native_enabled_uses_proposals_as_primary_source_without_fallback(tmp_path: Path) -> None:
    runtime, brain, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input(
            [_l2_candidate(path="reports/from-brain.md")],
            authority=_authority(["L2"], ["file_operation"]),
            contracts=_contracts(tmp_path, level="L2"),
            temporary_candidates=[_l2_candidate("temporary", "reports/from-temporary.md")],
        ),
        evidence_refs=["ev_l2"],
    )

    assert len(brain.calls) == 1
    assert result.brain_candidate_source_status == "CLOSED"
    assert result.organ_dispatch_result is not None
    execution = result.organ_dispatch_result.candidate_results[0].execution_result
    assert execution is not None
    assert "from-brain.md" in str(execution.executor_result_summary)
    assert "from-temporary.md" not in str(execution.executor_result_summary)


def test_temporary_user_input_bridge_is_disabled_by_default(tmp_path: Path) -> None:
    config = _config(
        OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY,
        brain_native_candidate_source_enabled=False,
        memory_feedback_enabled=False,
    )
    result = AgentRuntime(project_root=tmp_path, organ_execution_config=config).run(
        _envelope(),
        {
            "organ_dispatch": {
                "action_candidates": [_l2_candidate()],
                "authority": _authority(["L2"], ["file_operation"]),
                "organ_contracts": _contracts(tmp_path, level="L2"),
            }
        },
        evidence_refs=["ev_l2"],
    )

    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status.value == "no_candidates"
    assert not (tmp_path / "generated_root").exists()


def test_brain_native_l2_path_writes_real_memory_feedback_and_replan_packet(tmp_path: Path) -> None:
    runtime, _, memory = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    assert result.organ_dispatch_result is not None
    execution = result.organ_dispatch_result.candidate_results[0].execution_result
    assert execution is not None and execution.receipt is not None and execution.finalgate_certificate is not None
    assert len(memory.calls) == 1
    assert isinstance(result.memory_feedback_result, MemoryBridgeResult)
    assert result.memory_feedback_path == "CLOSED"
    assert result.memory_feedback_refs
    assert result.memory_feedback_result.memory_entries
    assert result.replan_ready is True
    assert result.replan_packet is not None
    assert result.replan_packet["status"] == "CLOSED"
    assert result.automatic_replan_executed is False


def test_brain_native_l3_path_produces_receipt_finalgate_feedback_and_replan(tmp_path: Path) -> None:
    target = tmp_path / "workspace_root" / "work" / "docs" / "state.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("before\n", encoding="utf-8")
    runtime, _, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input(
            [_l3_candidate(text_hash("before\n"))],
            authority=_authority(["L3"], ["file_operation"]),
            contracts=_contracts(tmp_path, level="L3"),
        ),
        evidence_refs=["ev_l3"],
    )

    execution = result.organ_dispatch_result.candidate_results[0].execution_result
    assert execution is not None
    assert execution.receipt.before_hash == text_hash("before\n")
    assert execution.receipt.after_hash is not None
    assert execution.finalgate_certificate is not None
    assert result.memory_feedback_path == "CLOSED"
    assert result.replan_packet["finalgate_certificate_refs"]
    assert target.read_text(encoding="utf-8") == "after\n"


def test_brain_native_browser_perception_trio_is_non_mutating_data_only(tmp_path: Path) -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    runtime, _, _ = _runtime(
        tmp_path,
        _config(OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY),
        fetcher=fetcher,
    )
    candidates = [_browser_candidate(kind) for kind in ("browser_readonly", "browser_preparation", "browser_semantic_extraction")]
    result = runtime.run(
        _envelope(),
        _user_input(candidates, authority=_authority(["L4"], ["browser"]), contracts=_contracts(tmp_path, level="L4")),
        evidence_refs=[f"ev_{kind}" for kind in ("browser_readonly", "browser_preparation", "browser_semantic_extraction")],
    )

    executed = [
        item.execution_result.organ_kind
        for item in result.organ_dispatch_result.candidate_results
        if item.execution_result is not None
    ]
    assert executed == ["browser_readonly", "browser_preparation", "browser_semantic_extraction"]
    assert fetcher.calls == ["https://example.com/research"]
    assert all(item.execution_result.execution_effect == "none" for item in result.organ_dispatch_result.candidate_results)
    assert result.memory_feedback_path == "CLOSED"


def test_memory_feedback_is_closed_only_after_real_bridge_result(tmp_path: Path) -> None:
    runtime, _, memory = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    assert memory.calls
    assert isinstance(result.memory_feedback_result, MemoryBridgeResult)
    assert result.memory_feedback_result.snapshot.memory_entry_ids
    assert result.memory_snapshot_ref
    assert result.memory_feedback_path == "CLOSED"
    assert result.durable_memory_persistence == "NOT_STARTED"


def test_durable_memory_persistence_is_not_claimed(tmp_path: Path) -> None:
    runtime, _, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    assert result.memory_feedback_result is not None
    assert result.memory_feedback_path == "CLOSED"
    assert result.durable_memory_persistence == "NOT_STARTED"
    assert "durable" not in result.memory_feedback_refs


def test_explicit_persistent_memory_adapter_writes_runtime_feedback_through(tmp_path: Path) -> None:
    service = PersistentSemanticMemoryService(tmp_path / "persistent-memory.sqlite3")
    runtime, _, _ = _runtime(
        tmp_path,
        _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY),
        persistent_memory_ingest_adapter=PersistentMemoryIngestAdapter(service),
    )

    result = runtime.run(
        _envelope(),
        _user_input(
            [_l2_candidate()],
            authority=_authority(["L2"], ["file_operation"]),
            contracts=_contracts(tmp_path, level="L2"),
        ),
        evidence_refs=["ev_l2"],
    )

    records, quarantined = service.store.records_for_user("user_native")
    assert result.durable_memory_persistence == "CLOSED"
    assert any(ref.startswith("persistent:pmem_") for ref in result.memory_feedback_refs)
    assert records
    assert quarantined == []


def test_persistent_memory_write_through_failure_is_safe_and_non_blocking(tmp_path: Path) -> None:
    class BrokenPersistentMemoryIngestAdapter:
        def persist_bridge_result(self, bridge_result, *, requester_user_id):
            raise RuntimeError("raw durable backend failure must not escape")

    runtime, _, _ = _runtime(
        tmp_path,
        _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY),
        persistent_memory_ingest_adapter=BrokenPersistentMemoryIngestAdapter(),
    )

    result = runtime.run(
        _envelope(),
        _user_input(
            [_l2_candidate()],
            authority=_authority(["L2"], ["file_operation"]),
            contracts=_contracts(tmp_path, level="L2"),
        ),
        evidence_refs=["ev_l2"],
    )

    assert result.organ_dispatch_result is not None
    assert result.memory_feedback_path == "CLOSED"
    assert result.durable_memory_persistence == "FAILED_SAFE"
    assert "raw durable backend failure" not in str(result.model_dump(mode="json"))


def test_replan_ready_packet_is_closed_without_automatic_replan(tmp_path: Path) -> None:
    runtime, _, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    packet = result.replan_packet
    assert result.replan_ready is True
    assert packet is not None and packet["status"] == "CLOSED"
    assert packet["brain_result_ref"]
    assert packet["proposal_artifact_refs"]
    assert packet["receipt_refs"]
    assert packet["finalgate_certificate_refs"]
    assert packet["memory_feedback_refs"]
    assert packet["recommended_next_loop_input"]
    assert result.automatic_replan_executed is False


def test_brain_memory_and_replan_preserve_selected_model_contract(tmp_path: Path) -> None:
    runtime, _, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )

    brain = result.brain_cognition_result
    assert brain.selected_provider_id == "groq"
    assert brain.selected_backend_id == "groq_openai_compatible_chat"
    assert brain.selected_model == "openai/gpt-oss-20b"
    assert "override" not in str(result.replan_packet).lower()


def test_brain_native_dangerous_surfaces_never_dispatch_execution(tmp_path: Path) -> None:
    dangerous = _browser_candidate("browser_readonly")
    dangerous.update({"browser_submit": True, "credential": True, "api_call": True, "desktop_action": True, "shell": True, "channel_send": True})
    runtime, _, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY))
    result = runtime.run(
        _envelope(),
        _user_input([dangerous], authority=_authority(["L4"], ["browser"]), contracts=_contracts(tmp_path, level="L4")),
        evidence_refs=["ev_browser_readonly"],
    )

    assert result.brain_cognition_result is not None
    assert result.brain_cognition_result.safety_validation.valid is False
    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status.value == "no_candidates"
    assert not any(item.execution_result for item in result.organ_dispatch_result.candidate_results)


def test_brain_native_source_runs_before_organ_dispatching_and_is_skipped_disabled(tmp_path: Path) -> None:
    order: list[str] = []
    runtime, brain, _ = _runtime(tmp_path, _config(OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY), order=order)
    result = runtime.run(
        _envelope(),
        _user_input([_l2_candidate()], authority=_authority(["L2"], ["file_operation"]), contracts=_contracts(tmp_path, level="L2")),
        evidence_refs=["ev_l2"],
    )
    disabled_brain = RecordingBrainLoop()
    disabled = AgentRuntime(project_root=tmp_path / "disabled", brain_cognition_loop=disabled_brain).run(_envelope("mission_disabled"), {})

    assert order[:2] == ["brain", "dispatch"]
    assert (AgentPhase.EXECUTING, AgentPhase.ORGAN_DISPATCHING) in [
        (event.phase_before, event.phase_after) for event in result.trace
    ]
    assert AgentEventType.ORGAN_DISPATCH_COMPLETED in [event.event_type for event in result.trace]
    assert brain.calls
    assert disabled_brain.calls == []
    assert disabled.brain_candidate_source_status == "NOT_STARTED"
