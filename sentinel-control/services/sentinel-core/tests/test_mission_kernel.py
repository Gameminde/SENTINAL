from __future__ import annotations

from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pytest

from sentinel.mission import (
    AutonomyEngine,
    EscalationGateway,
    MissionAction,
    MissionAuthorityEnvelope,
    MissionKillSwitch,
    MissionPlanner,
    MissionExecutionPosturePolicy,
    MissionRegistry,
    MissionRunner,
    MissionState,
    MissionTraceTimeline,
    SafeMissionExecutors,
)
from sentinel.mission.exceptions import MissionRevokedException
from sentinel.mission.models import utc_now
from sentinel.shared.enums import (
    ConfidenceLevel,
    ExternalityLevel,
    MissionActionRoute,
    MissionMode,
    MissionStatus,
    MissionType,
    MissionTraceEventType,
    ReversibilityLevel,
    SensitivityLevel,
)


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
        "mission_title": "GTM launch pack for Sentinel",
        "mission_objective": "Create a safe local GTM launch pack.",
        "success_criteria": [
            "GTM files exist",
            "Outreach remains draft-only",
            "Trace timeline exists",
        ],
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


def mission_action(env: MissionAuthorityEnvelope, action_type: str, **overrides) -> MissionAction:
    data = {
        "mission_id": env.id,
        "action_type": action_type,
        "tool": overrides.pop("tool", "safe_file_writer"),
        "intent": f"Run {action_type}",
        "target": "data/generated_projects/demo",
        "input": {"path": "data/generated_projects/demo"},
        "expected_output": "done",
        "reversibility": ReversibilityLevel.LOCAL_WRITE_REVERSIBLE,
        "externality": ExternalityLevel.INTERNAL_LOCAL,
        "sensitivity": SensitivityLevel.INTERNAL,
        "confidence": ConfidenceLevel.HIGH,
    }
    data.update(overrides)
    return MissionAction(**data)


def test_safe_gtm_mission_runs_without_micro_approval(tmp_path):
    env = envelope()
    result = MissionRunner(project_root=tmp_path).run_gtm_mission(
        env,
        idea="Sentinel GTM Operator",
        evidence_refs=["ev_direct", "ev_wtp"],
    )
    project_path = Path(result.project_path)

    assert result.success is True
    assert result.state.status == MissionStatus.COMPLETED
    assert (project_path / "00_VERDICT.md").exists()
    assert (project_path / "04_LANDING_PAGE_COPY.md").exists()
    assert (project_path / "05_OUTREACH_MESSAGES.md").exists()
    assert (project_path / "08_WATCHLIST.md").exists()
    assert (project_path / "mission_artifacts.json").exists()
    assert (project_path / "artifact_manifest.json").exists()
    assert (project_path / "mission_timeline.json").exists()

    outreach_payload = json.loads((project_path / "outreach_drafts.json").read_text(encoding="utf-8"))
    assert outreach_payload["sent"] is False

    event_types = [event.event_type for event in result.trace_events]
    assert MissionTraceEventType.REVIEW_EXECUTED in event_types
    assert MissionTraceEventType.RISK_ROUTE_DECIDED in event_types
    assert MissionTraceEventType.ACTION_RECEIPT_RECORDED in event_types
    assert MissionTraceEventType.ROLLBACK_AVAILABLE in event_types
    assert MissionTraceEventType.MISSION_COMPLETED in event_types
    assert result.artifact_receipts
    assert len(result.artifact_receipts) == len(result.artifacts)
    receipt_ids = {receipt.id for receipt in result.artifact_receipts}
    assert all(artifact.receipt_id in receipt_ids for artifact in result.artifacts)
    for artifact in result.artifacts:
        artifact_path = project_path / artifact.path
        assert artifact.sha256 == hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert artifact.size_bytes == artifact_path.stat().st_size
        assert artifact.rollback_strategy == "delete_created_artifact_after_user_confirmation_if_hash_matches"
        assert artifact.trace_refs
    rollback_payload = json.loads((project_path / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert len(rollback_payload["artifact_receipts"]) == len(result.artifacts)
    assert all(str(project_path).startswith(str(tmp_path / "data" / "generated_projects")) for _ in [project_path])


def test_generic_runner_runs_research_summary_mission_type(tmp_path):
    env = envelope(
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Research summary for mission OS",
        mission_objective="Create one bounded research summary.",
        allowed_actions=["create_project_folder", "create_markdown_file"],
        allowed_tools=["safe_file_writer"],
        success_criteria=["Research summary exists."],
    )

    result = MissionRunner(project_root=tmp_path).run_mission(
        env,
        idea="Mission OS extensibility",
        evidence_refs=["ev_research"],
    )
    project_path = Path(result.project_path)

    assert result.success is True
    assert result.state.status == MissionStatus.COMPLETED
    assert (project_path / "RESEARCH_SUMMARY.md").exists()
    assert (project_path / "mission_artifacts.json").exists()
    assert (project_path / "mission_timeline.json").exists()
    assert [artifact.type for artifact in result.artifacts] == ["research_summary"]
    assert len(result.artifact_receipts) == 1
    assert result.artifacts[0].receipt_id == result.artifact_receipts[0].id


def test_runner_converts_executor_exception_into_failed_mission_trace(tmp_path):
    runner = MissionRunner(project_root=tmp_path)
    definition = runner.registry.get(MissionType.GTM)

    def fail_execute(*args, **kwargs):
        raise RuntimeError("simulated executor failure")

    definition.executor.execute = fail_execute
    result = runner.run_gtm_mission(envelope(), idea="Executor failure", evidence_refs=["ev_1"])

    event_types = [event.event_type for event in result.trace_events]

    assert result.success is False
    assert result.state.status == MissionStatus.FAILED
    assert result.blocked_actions
    assert MissionTraceEventType.ACTION_BLOCKED in event_types
    assert MissionTraceEventType.MISSION_FAILED in event_types
    assert any(event.result.get("error") == "simulated executor failure" for event in result.trace_events)


def test_runner_preserves_executor_revocation_as_revoked_mission(tmp_path):
    runner = MissionRunner(project_root=tmp_path)
    definition = runner.registry.get(MissionType.GTM)

    def revoke_execute(*args, **kwargs):
        raise MissionRevokedException("mission_revoked: executor observed kill switch")

    definition.executor.execute = revoke_execute
    result = runner.run_gtm_mission(envelope(), idea="Executor revocation", evidence_refs=["ev_1"])
    event_types = [event.event_type for event in result.trace_events]

    assert result.success is False
    assert result.state.status == MissionStatus.REVOKED
    assert result.blocked_actions == []
    assert MissionTraceEventType.MISSION_REVOKED in event_types
    assert MissionTraceEventType.ACTION_BLOCKED not in event_types


def test_in_scope_reversible_action_auto_executes(tmp_path):
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "create_project_folder")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.AUTO_EXECUTE


def test_safe_posture_escalates_uncertain_local_action(tmp_path):
    env = envelope(mode=MissionMode.SAFE)
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "create_project_folder", confidence=ConfidenceLevel.UNKNOWN)

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.ESCALATE
    assert decision.posture == MissionMode.SAFE.value
    assert decision.blocking_rule == "safe_uncertainty_boundary"


def test_power_posture_auto_executes_uncertain_local_recoverable_action(tmp_path):
    env = envelope(mode=MissionMode.POWER)
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(
        env,
        "create_markdown_file",
        confidence=ConfidenceLevel.UNKNOWN,
        reversibility=ReversibilityLevel.STATE_MUTATING_RECOVERABLE,
    )

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.AUTO_EXECUTE
    assert decision.posture == MissionMode.POWER.value


def test_forged_power_posture_cannot_upgrade_safe_envelope(tmp_path):
    safe_env = envelope(mode=MissionMode.SAFE)
    power_env = envelope(mode=MissionMode.POWER)
    forged_power = MissionExecutionPosturePolicy().select(power_env).model_copy(update={"mission_id": safe_env.id})
    state = MissionState(mission_id=safe_env.id, status=MissionStatus.RUNNING)
    action = mission_action(safe_env, "create_markdown_file", confidence=ConfidenceLevel.UNKNOWN)

    decision = AutonomyEngine(project_root=tmp_path).decide(safe_env, state, action, posture=forged_power)

    assert decision.route == MissionActionRoute.ESCALATE
    assert decision.posture == MissionMode.SAFE.value
    assert decision.blocking_rule == "posture_authority_mismatch"


def test_out_of_scope_action_escalates(tmp_path):
    env = envelope(allowed_actions=["create_project_folder"])
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "create_watchlist")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.ESCALATE


def test_empty_allowed_actions_or_tools_grants_no_authority(tmp_path):
    state_env = envelope()
    state = MissionState(mission_id=state_env.id, status=MissionStatus.RUNNING)

    no_actions_env = envelope(allowed_actions=[])
    no_actions_action = mission_action(no_actions_env, "create_project_folder")
    no_tools_env = envelope(allowed_tools=[])
    no_tools_action = mission_action(no_tools_env, "create_project_folder")

    assert AutonomyEngine(project_root=tmp_path).decide(no_actions_env, state.model_copy(update={"mission_id": no_actions_env.id}), no_actions_action).route == MissionActionRoute.ESCALATE
    assert AutonomyEngine(project_root=tmp_path).decide(no_tools_env, state.model_copy(update={"mission_id": no_tools_env.id}), no_tools_action).route == MissionActionRoute.ESCALATE


def test_empty_allowed_paths_grants_no_write_scope(tmp_path):
    env = envelope(allowed_paths=[])
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "create_project_folder")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.ESCALATE
    assert decision.blocking_rule == "outside_authority"


@pytest.mark.parametrize(
    ("action_type", "tool"),
    [
        ("run_shell_command", "shell"),
        ("browser_submit_form", "browser"),
        ("credential_access", "secret_reader"),
        ("send_email", "email"),
        ("network_mutation", "http_client"),
        ("desktop_control", "desktop"),
        ("payment", "payment_gateway"),
    ],
)
def test_black_zone_actions_block_even_in_power_mode(tmp_path, action_type, tool):
    env = envelope(
        mode=MissionMode.POWER,
        forbidden_actions=[],
        allowed_actions=[*SAFE_ACTIONS, action_type],
        allowed_tools=["safe_file_writer", tool],
    )
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, action_type, tool=tool)

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.BLOCK


def test_black_zone_actions_block_case_insensitively(tmp_path):
    env = envelope(
        forbidden_actions=[],
        allowed_actions=[*SAFE_ACTIONS, "RUN_SHELL_COMMAND"],
        allowed_tools=["safe_file_writer", "SHELL"],
    )
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "RUN_SHELL_COMMAND", tool="SHELL")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.BLOCK


def test_real_email_send_blocks_or_escalates(tmp_path):
    env = envelope(forbidden_actions=[], allowed_actions=[*SAFE_ACTIONS, "send_email"], allowed_tools=["safe_file_writer", "email"])
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(
        env,
        "send_email",
        tool="email",
        externality=ExternalityLevel.EXTERNAL_PRIVATE,
        sensitivity=SensitivityLevel.PERSONAL,
    )

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route in {MissionActionRoute.ESCALATE, MissionActionRoute.BLOCK}


def test_path_traversal_outside_generated_projects_blocks(tmp_path):
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(
        env,
        "create_markdown_file",
        input={"path": "../outside.md", "content": "bad"},
        target="../outside.md",
    )

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.ESCALATE

    executors = SafeMissionExecutors(project_root=tmp_path)
    project_dir = executors.project_dir_for(env.mission_title)
    from sentinel.mission.artifacts import MissionArtifactIndex

    with pytest.raises(ValueError):
        executors.execute(action, project_dir, MissionArtifactIndex(project_dir))


def test_path_scoped_write_action_without_path_escalates(tmp_path):
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(
        env,
        "create_markdown_file",
        target=None,
        input={"content": "pathless write must not infer authority"},
    )

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.ESCALATE
    assert decision.blocking_rule == "outside_authority"


def test_artifact_index_refuses_to_record_external_files(tmp_path):
    from sentinel.mission.artifacts import MissionArtifactIndex

    project_dir = tmp_path / "data" / "generated_projects" / "demo"
    project_dir.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")

    index = MissionArtifactIndex(project_dir)

    with pytest.raises(ValueError):
        index.record_file("markdown", outside)


def test_artifact_index_records_hash_receipt_and_relative_scope(tmp_path):
    from sentinel.mission.artifacts import MissionArtifactIndex

    project_dir = tmp_path / "data" / "generated_projects" / "demo"
    project_dir.mkdir(parents=True)
    artifact_path = project_dir / "report.md"
    artifact_path.write_text("mission receipt body", encoding="utf-8")

    index = MissionArtifactIndex(project_dir, mission_id="mission_receipt_001")
    artifact = index.record_file("markdown", artifact_path, evidence_refs=["ev_1"], action_id="act_1")

    assert artifact.path == "report.md"
    assert artifact.sha256 == hashlib.sha256(b"mission receipt body").hexdigest()
    assert artifact.size_bytes == len(b"mission receipt body")
    assert artifact.receipt_id == index.artifact_receipts[0].id
    assert index.artifact_receipts[0].mission_id == "mission_receipt_001"
    assert index.artifact_receipts[0].artifact_path == "report.md"


def test_expired_and_revoked_missions_block(tmp_path):
    expired = envelope(expires_at=utc_now() - timedelta(minutes=1))
    revoked = envelope(revoked_at=utc_now())
    action = mission_action(expired, "create_project_folder")

    engine = AutonomyEngine(project_root=tmp_path)

    assert engine.decide(expired, MissionState(mission_id=expired.id, status=MissionStatus.RUNNING), action).route == MissionActionRoute.BLOCK
    assert engine.decide(revoked, MissionState(mission_id=revoked.id, status=MissionStatus.REVOKED), action.model_copy(update={"mission_id": revoked.id})).route == MissionActionRoute.BLOCK


def test_mission_identity_mismatch_blocks_before_execution(tmp_path):
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    action = mission_action(env, "create_project_folder").model_copy(update={"mission_id": "forged_mission"})
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "generated_projects" / "identity-trace")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action, timeline=timeline)

    assert decision.route == MissionActionRoute.BLOCK
    assert decision.blocking_rule == "mission_identity_mismatch"
    risk_event = next(event for event in timeline.events if event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED)
    assert risk_event.result["blocking_rule"] == "mission_identity_mismatch"


def test_runner_rejects_supplied_plan_with_foreign_action_mission_id(tmp_path):
    env = envelope()
    plan = MissionPlanner().create_gtm_plan(env, idea="Forged plan", evidence_refs=["ev_1"])
    forged_steps = [
        step.model_copy(update={"action": step.action.model_copy(update={"mission_id": "foreign_mission"})})
        if index == 0
        else step
        for index, step in enumerate(plan.steps)
    ]
    forged_plan = plan.model_copy(update={"steps": forged_steps})

    result = MissionRunner(project_root=tmp_path).run_mission(env, plan=forged_plan)

    assert result.success is False
    assert result.blocked_actions
    assert any(
        event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED
        and event.result.get("blocking_rule") == "mission_identity_mismatch"
        for event in result.trace_events
    )
    assert not any(event.event_type == MissionTraceEventType.ACTION_EXECUTED for event in result.trace_events)


def test_budget_and_max_actions_boundaries_escalate(tmp_path):
    env = envelope(max_cost_usd=1.0, max_actions=1)
    action = mission_action(env, "create_project_folder", estimated_cost=1.1)
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)

    assert AutonomyEngine(project_root=tmp_path).decide(env, state, action).route == MissionActionRoute.ESCALATE

    maxed_state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING, action_count=1)
    cheap_action = mission_action(env, "create_project_folder", estimated_cost=0)
    assert AutonomyEngine(project_root=tmp_path).decide(env, maxed_state, cheap_action).route == MissionActionRoute.ESCALATE


def test_escalated_mission_state_blocks_followup_actions(tmp_path):
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.ESCALATED)
    action = mission_action(env, "create_project_folder")

    decision = AutonomyEngine(project_root=tmp_path).decide(env, state, action)

    assert decision.route == MissionActionRoute.BLOCK
    assert "escalated" in " ".join(decision.reasons).lower()


def test_allow_for_this_mission_cannot_grant_black_zone_action(tmp_path):
    env = envelope()
    action = mission_action(env, "run_shell_command", tool="shell")

    with pytest.raises(ValueError):
        EscalationGateway().allow_for_this_mission(env, action)


def test_allow_for_this_mission_cannot_grant_black_zone_action_case_insensitively(tmp_path):
    env = envelope()
    action = mission_action(env, "RUN_SHELL_COMMAND", tool="SHELL")

    with pytest.raises(ValueError):
        EscalationGateway().allow_for_this_mission(env, action)


def test_every_boundary_route_writes_trace(tmp_path):
    env = envelope(allowed_actions=["create_project_folder"])
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "generated_projects" / "trace-test")

    auto_action = mission_action(env, "create_project_folder")
    AutonomyEngine(project_root=tmp_path).decide(env, state, auto_action, timeline=timeline)

    escalate_action = mission_action(env, "create_watchlist")
    AutonomyEngine(project_root=tmp_path).decide(env, state, escalate_action, timeline=timeline)

    block_action = mission_action(env, "run_shell_command", tool="shell")
    AutonomyEngine(project_root=tmp_path).decide(env, state, block_action, timeline=timeline)

    event_types = [event.event_type for event in timeline.events]
    assert MissionTraceEventType.ACTION_ROUTED in event_types
    assert MissionTraceEventType.RISK_ROUTE_DECIDED in event_types
    assert MissionTraceEventType.ACTION_ESCALATED in event_types
    assert MissionTraceEventType.ACTION_BLOCKED in event_types
    risk_events = [event for event in timeline.events if event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED]
    assert all("posture" in event.result for event in risk_events)
    assert any(event.result.get("blocking_rule") == "forbidden_or_black_zone" for event in risk_events)


def test_mission_timeline_is_append_only_hash_chained(tmp_path):
    env = envelope()
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "generated_projects" / "trace-hash")

    first = timeline.emit(MissionTraceEventType.MISSION_CREATED, "Mission created.")
    second = timeline.emit(MissionTraceEventType.MISSION_STARTED, "Mission started.")

    assert first.sequence == 0
    assert second.sequence == 1
    assert second.previous_hash == first.event_hash
    assert timeline.verify_chain() is True
    tampered = [first.model_copy(update={"summary": "tampered"}), second]
    assert MissionTraceTimeline.verify_events(tampered) is False


def test_mission_timeline_rejects_duplicate_event_ids_even_when_rehashed(tmp_path):
    env = envelope()
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "generated_projects" / "trace-duplicate")
    first = timeline.emit(MissionTraceEventType.MISSION_CREATED, "Mission created.")
    duplicate = first.model_copy(update={"summary": "Duplicate id event."})
    events = []
    previous_hash = None
    for index, event in enumerate([first, duplicate]):
        event_data = event.model_dump()
        event_data.update({"sequence": index, "logical_time": index, "previous_hash": previous_hash, "event_hash": ""})
        event_hash = MissionTraceTimeline._hash_payload(event_data)
        rehashed = event.model_copy(
            update={
                "sequence": index,
                "logical_time": index,
                "previous_hash": previous_hash,
                "event_hash": event_hash,
            }
        )
        events.append(rehashed)
        previous_hash = event_hash

    assert MissionTraceTimeline.verify_events(events) is False


def test_mission_timeline_emit_isolates_result_from_caller_mutation(tmp_path):
    env = envelope()
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "generated_projects" / "trace-copy")
    payload = {"nested": {"value": "original"}}

    event = timeline.emit(MissionTraceEventType.MISSION_CREATED, "Mission created.", result=payload)
    payload["nested"]["value"] = "mutated"

    assert event.result == {"nested": {"value": "original"}}
    assert timeline.verify_chain() is True


def test_mission_kill_switch_stops_and_revokes_future_actions():
    env = envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    kill_switch = MissionKillSwitch()

    stopped = kill_switch.stop(state)
    revoked_env, revoked_state = kill_switch.revoke(env, state)

    assert stopped.status == MissionStatus.STOPPED
    assert revoked_env.revoked_at is not None
    assert revoked_state.status == MissionStatus.REVOKED


def test_planner_outputs_dag_dependencies():
    env = envelope()
    plan = MissionPlanner().create_gtm_plan(env, idea="Mission authority", evidence_refs=["ev_1"])

    steps = {step.id: step for step in plan.steps}
    assert steps["generate_evidence_pack"].depends_on == ["prepare_workspace"]
    assert steps["generate_landing_copy"].depends_on == ["generate_evidence_pack"]
    assert steps["generate_outreach_drafts"].depends_on == ["generate_evidence_pack"]


def test_mission_registry_rejects_unknown_mission_type():
    registry = MissionRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown")


def test_generic_runner_has_no_gtm_specific_artifact_names():
    runner_source = Path(__file__).parents[1] / "sentinel" / "mission" / "runner.py"
    source = runner_source.read_text(encoding="utf-8")

    assert "00_VERDICT.md" not in source
    assert "05_OUTREACH_MESSAGES.md" not in source
    assert "create_gtm_plan" not in source
