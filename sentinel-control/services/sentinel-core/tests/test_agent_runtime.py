from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentEventType, AgentPhase, AgentRuntime, ContextBuilder, ContextCompressor, MethodSelector, CapabilitySelector, audit_agent_trace
from sentinel.mission import MissionAuthorityEnvelope
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
        "mission_title": "SPINE GTM test",
        "mission_objective": "Create a safe local GTM pack through AgentRuntime.",
        "success_criteria": ["GTM files exist", "Trace exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["send_email", "run_shell_command", "browser_submit_form", "credential_access"],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def test_context_builder_cannot_expand_authority():
    env = envelope()
    context = ContextBuilder().build(env, user_input={"allowed_actions": ["send_email"]})

    assert "local_workspace_write" in context.available_capabilities
    assert "outreach_draft_generation" in context.available_capabilities
    assert "send_email" not in context.available_capabilities
    assert "generate_gtm_pack" not in context.available_capabilities


def test_context_compressor_preserves_identity_and_refs():
    env = envelope()
    context = ContextBuilder().build(
        env,
        user_input={"idea": "x" * 800},
        evidence_refs=["ev_001"],
    )
    compressed = ContextCompressor().compress(context)

    assert compressed.mission.id == env.id
    assert compressed.evidence_refs == ["ev_001"]
    assert len(compressed.summary) <= 500


def test_method_and_capability_selection_for_gtm():
    env = envelope()
    context = ContextBuilder().build(env, evidence_refs=["ev_001"])
    methods = MethodSelector().select(context)
    capabilities = CapabilitySelector().select(context, methods)

    assert "evidence_ladder" in [method.id for method in methods]
    assert "gtm_pack_generation" in [need.name for need in capabilities]
    assert "browser_research" in [need.name for need in capabilities if not need.available]


def test_agent_runtime_runs_safe_gtm_mission(tmp_path):
    env = envelope()

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": "Sentinel SPINE"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    project_path = Path(result.project_path or "")
    event_types = [event.event_type for event in result.trace]

    assert result.success is True
    assert result.final_phase == AgentPhase.COMPLETED
    assert result.mission_result is not None
    assert result.mission_result.state.status == MissionStatus.COMPLETED
    assert project_path.exists()
    assert (project_path / "mission_timeline.json").exists()
    assert "evidence_ladder" in [method.id for method in result.selected_methods]
    assert "safe_file_writer" in result.selected_tools
    assert "local_workspace_write" not in result.unavailable_capabilities
    assert result.tool_selection_decisions
    assert "browser_research" in [need.name for need in result.missing_capabilities]
    browser_need = next(need for need in result.missing_capabilities if need.name == "browser_research")
    assert browser_need.missing_reason == "Capability is not granted by mission authority, although an approved manifest exists."
    assert AgentEventType.AGENT_INITIALIZED in event_types
    assert AgentEventType.TOOLS_SELECTED in event_types
    assert AgentEventType.WORKER_COMPLETED in event_types
    assert AgentEventType.AGENT_COMPLETED in event_types
    assert all(event.sequence == index for index, event in enumerate(result.trace))
    trace_audit = audit_agent_trace(result.trace)
    assert trace_audit.accepted is True
    assert trace_audit.final_phase == AgentPhase.COMPLETED


def test_agent_runtime_executes_direct_controlled_local_tool_call(tmp_path):
    env = envelope(allowed_tools=["safe_file_writer", "safe_local_markdown_tool"])

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Sentinel SPINE",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {
                        "path": "runtime/decision.md",
                        "content": "# Decision\n\nMove aggressively on local controlled execution.",
                    },
                }
            ],
        },
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    project_path = Path(result.project_path or "")
    event_types = [event.event_type for event in result.trace]

    assert result.success is True
    assert result.runtime_certification is not None
    assert result.runtime_certification.certified is True
    assert result.state_snapshot is not None
    assert result.state_snapshot.controlled_capability_executed_count == 1
    assert result.controlled_capability_results
    assert result.controlled_capability_results[0]["accepted"] is True
    assert (project_path / "runtime" / "decision.md").read_text(encoding="utf-8").startswith("# Decision")
    assert event_types.index(AgentEventType.PLAN_REVIEWED) < event_types.index(AgentEventType.CONTROLLED_CAPABILITY_EXECUTED)
    assert event_types.index(AgentEventType.CONTROLLED_CAPABILITY_EXECUTED) < event_types.index(AgentEventType.WORKER_STARTED)
    assert "Move aggressively" not in str([event.payload for event in result.trace])


def test_agent_runtime_rejects_dangerous_direct_tool_call_and_keeps_solving(tmp_path):
    env = envelope(
        allowed_tools=["safe_file_writer", "shell_critical_blocked"],
        allowed_actions=[*SAFE_ACTIONS, "run_shell_command"],
    )

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Sentinel SPINE",
            "tool_calls": [
                {
                    "tool_id": "shell_critical_blocked",
                    "action": "run_shell_command",
                    "arguments": {"command": "whoami"},
                }
            ],
        },
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    event_types = [event.event_type for event in result.trace]

    assert result.success is True
    assert result.controlled_capability_results[0]["accepted"] is False
    assert result.controlled_capability_results[0]["reason"] == "black_zone_side_effect"
    assert AgentEventType.CONTROLLED_CAPABILITY_REJECTED in event_types
    assert AgentEventType.WORKER_COMPLETED in event_types
    assert result.mission_result is not None


def test_agent_runtime_traces_malformed_direct_tool_call_rejection(tmp_path):
    env = envelope(allowed_tools=["safe_file_writer", "safe_local_markdown_tool"])

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Sentinel SPINE",
            "tool_calls": ["tool_id=safe_local_markdown_tool; no action here"],
        },
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    event_types = [event.event_type for event in result.trace]

    assert result.success is True
    assert result.controlled_capability_results[0]["accepted"] is False
    assert result.controlled_capability_results[0]["reason"] == "tool_call_not_canonical"
    assert result.controlled_capability_results[0]["canonicalization_trace_id"]
    assert result.state_snapshot is not None
    assert result.state_snapshot.controlled_capability_rejected_count == 1
    assert event_types.index(AgentEventType.TOOL_CALL_CANONICALIZED) < event_types.index(AgentEventType.CONTROLLED_CAPABILITY_REJECTED)
    assert AgentEventType.WORKER_COMPLETED in event_types


def test_agent_runtime_bounds_direct_tool_calls_by_remaining_action_budget(tmp_path):
    env = envelope(
        allowed_tools=["safe_file_writer", "safe_local_markdown_tool"],
        max_actions=6,
    )

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Sentinel SPINE",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {
                        "path": "runtime/budget.md",
                        "content": "this direct write should not run",
                    },
                }
            ],
        },
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    project_path = Path(result.project_path or "")

    assert result.success is True
    assert result.controlled_capability_results[0]["accepted"] is False
    assert result.controlled_capability_results[0]["reason"] == "direct_tool_call_budget_exhausted"
    assert not (project_path / "runtime" / "budget.md").exists()


def test_agent_runtime_skips_overflow_direct_tool_calls_without_serializing_them(tmp_path):
    class ExplodingDict(dict):
        def items(self):
            raise AssertionError("overflow tool call should not be serialized")

    env = envelope(allowed_tools=["safe_file_writer", "safe_local_markdown_tool"], max_actions=7)

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Sentinel SPINE",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {"path": "runtime/one.md", "content": "one"},
                },
                ExplodingDict(
                    {
                        "tool_id": "safe_local_markdown_tool",
                        "action": "create_markdown_file",
                        "arguments": {"path": "runtime/two.md", "content": "two"},
                    }
                ),
            ],
        },
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    project_path = Path(result.project_path or "")

    assert result.success is True
    assert (project_path / "runtime" / "one.md").exists()
    assert not (project_path / "runtime" / "two.md").exists()
    assert result.controlled_capability_results[-1]["reason"] == "direct_tool_call_budget_exhausted"
    assert result.controlled_capability_results[-1]["skipped_count"] == 1


def test_agent_runtime_reports_revoked_mission_without_running(tmp_path):
    from sentinel.mission.models import utc_now

    env = envelope(revoked_at=utc_now())

    result = AgentRuntime(project_root=tmp_path).run(env, {"idea": "Should not run"}, evidence_refs=["ev_001"])

    assert result.success is False
    assert result.final_phase == AgentPhase.REVOKED
    assert result.project_path is None
    assert result.escalation_reason is not None
    assert "revoked" in result.escalation_reason.lower()


def test_agent_runtime_creates_learning_proposal_on_failure(tmp_path):
    env = envelope(allowed_actions=["create_project_folder"], allowed_tools=["safe_file_writer"])

    result = AgentRuntime(project_root=tmp_path).run(env, {"idea": "Incomplete mission"}, evidence_refs=["ev_001"])

    assert result.success is False
    assert result.final_phase == AgentPhase.BLOCKED
    assert result.mission_result is None
    assert result.learning_proposals
    assert all(proposal.requires_human_approval for proposal in result.learning_proposals)


def test_agent_runtime_does_not_disguise_internal_key_errors_as_policy_blocks(tmp_path):
    env = envelope()
    runtime = AgentRuntime(project_root=tmp_path)

    def raise_internal_key_error(*args, **kwargs):
        raise KeyError("internal planner cache miss")

    runtime.planner_bridge.create_plan = raise_internal_key_error

    result = runtime.run(env, {"idea": "Unknown mission"}, evidence_refs=["ev_001"])

    assert result.success is False
    assert result.final_phase == AgentPhase.FAILED
    assert result.escalation_reason is not None
    assert "internal planner cache miss" in result.escalation_reason
    assert AgentEventType.LEARNING_PROPOSED in [event.event_type for event in result.trace]
    assert result.learning_proposals
    assert result.runtime_certification is not None
    assert result.runtime_certification.certified is True


def test_agent_runtime_certifies_worker_crash_as_closed_failure(tmp_path):
    env = envelope()
    runtime = AgentRuntime(project_root=tmp_path)

    def raise_worker_error(*args, **kwargs):
        raise RuntimeError("worker engine crash")

    runtime.worker_coordinator.runner.run_mission = raise_worker_error

    result = runtime.run(env, {"idea": "Worker crash"}, evidence_refs=["ev_001"])
    event_types = [event.event_type for event in result.trace]

    assert result.success is False
    assert result.final_phase == AgentPhase.FAILED
    assert result.runtime_certification is not None
    assert result.runtime_certification.certified is True
    assert result.escalation_reason is not None
    assert "worker engine crash" in result.escalation_reason
    assert event_types.index(AgentEventType.WORKER_STARTED) < event_types.index(AgentEventType.WORKER_COMPLETED)
    assert AgentEventType.LEARNING_PROPOSED in event_types
    assert result.learning_proposals


def test_agent_runtime_redacts_secret_like_runtime_failure_text(tmp_path):
    env = envelope()
    runtime = AgentRuntime(project_root=tmp_path)
    leaked_secret = "OPENAI_API_KEY=sk-test-runtime-secret-1234567890"

    def raise_worker_error(*args, **kwargs):
        raise RuntimeError(leaked_secret)

    runtime.worker_coordinator.runner.run_mission = raise_worker_error

    result = runtime.run(env, {"idea": "Worker crash"}, evidence_refs=["ev_001"])
    rendered_trace = str([event.model_dump(mode="json") for event in result.trace])

    assert leaked_secret not in (result.escalation_reason or "")
    assert leaked_secret not in rendered_trace
    assert "[REDACTED_SECRET]" in (result.escalation_reason or "")


def test_critical_tool_selection_review_prevents_worker_execution(tmp_path):
    env = envelope(allowed_actions=["create_project_folder"], allowed_tools=["safe_file_writer"])

    result = AgentRuntime(project_root=tmp_path).run(env, {"idea": "Should block before worker"}, evidence_refs=["ev_001"])
    event_types = [event.event_type for event in result.trace]

    assert result.final_phase == AgentPhase.BLOCKED
    assert result.success is False
    assert result.mission_result is None
    assert AgentEventType.WORKER_STARTED not in event_types
    assert AgentEventType.AGENT_BLOCKED in event_types
    assert "required_tool_unavailable" in [finding.code for finding in result.review_findings]
