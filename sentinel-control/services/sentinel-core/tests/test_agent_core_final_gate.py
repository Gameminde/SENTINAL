from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentEventType, AgentPhase, AgentRuntime, CoreFinalGate, EventBus, ReviewFinding, certify_core_final_gate
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.mission.trace_timeline import MissionTraceTimeline
from sentinel.shared.enums import MissionActionRoute, MissionMode, MissionTraceEventType, MissionType
from sentinel.shared.models import new_id


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
        "mission_title": "P1N final gate test",
        "mission_objective": "Certify the complete Sentinel P1 core before P2.",
        "success_criteria": ["Final gate accepts the core trace"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["send_email", "run_shell_command", "browser_submit_form", "credential_access"],
        "allowed_paths": ["data/generated_projects"],
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def successful_result(tmp_path: Path):
    return AgentRuntime(project_root=tmp_path).run(envelope(), {"idea": "Final Gate"}, evidence_refs=["ev_wtp"])


def blocked_result(tmp_path: Path):
    env = envelope(allowed_actions=["create_project_folder"], allowed_tools=["safe_file_writer"])
    return AgentRuntime(project_root=tmp_path).run(env, {"idea": "Blocked Gate"}, evidence_refs=["ev_scope"])


def failed_check_names(gate_result):
    return {check.name for check in gate_result.checks if not check.passed}


def repair_recovered_result(tmp_path: Path):
    runtime = AgentRuntime(project_root=tmp_path)
    original_review = runtime.review_loop.review_worker_result
    review_calls = 0

    def review_once_then_clear(result):
        nonlocal review_calls
        review_calls += 1
        if review_calls == 1:
            return [ReviewFinding(code="forced_repair", severity="critical", message="Force a bounded repair pass.")]
        return original_review(result)

    runtime.review_loop.review_worker_result = review_once_then_clear
    return runtime.run(envelope(), {"idea": "Archived repair gate"}, evidence_refs=["ev_wtp"])


def rehash_mission_trace(events):
    previous_hash = None
    rehashed = []
    for index, event in enumerate(events):
        event_data = event.model_dump()
        event_data.update(
            {
                "sequence": index,
                "logical_time": index,
                "previous_hash": previous_hash,
                "event_hash": "",
            }
        )
        event_hash = MissionTraceTimeline._hash_payload(event_data)
        rehashed_event = event.model_copy(
            update={
                "sequence": index,
                "logical_time": index,
                "previous_hash": previous_hash,
                "event_hash": event_hash,
            }
        )
        rehashed.append(rehashed_event)
        previous_hash = event_hash
    return rehashed


def rehash_agent_trace(events):
    previous_hash = None
    rehashed = []
    for index, event in enumerate(events):
        event_data = event.model_dump()
        event_data.update(
            {
                "sequence": index,
                "logical_time": index,
                "previous_hash": previous_hash,
                "event_hash": "",
            }
        )
        event_hash = EventBus._hash_payload(event_data)
        rehashed_event = event.model_copy(
            update={
                "sequence": index,
                "logical_time": index,
                "previous_hash": previous_hash,
                "event_hash": event_hash,
            }
        )
        rehashed.append(rehashed_event)
        previous_hash = event_hash
    return rehashed


def test_core_final_gate_accepts_clean_successful_runtime_run(tmp_path):
    result = successful_result(tmp_path)

    gate = certify_core_final_gate(result, allowed_project_root=tmp_path)

    assert gate.accepted is True
    assert gate.errors == []


def test_core_final_gate_accepts_safe_early_blocked_runtime_run(tmp_path):
    result = blocked_result(tmp_path)

    gate = CoreFinalGate().evaluate(result, allowed_project_root=tmp_path)

    assert result.final_phase == AgentPhase.BLOCKED
    assert gate.accepted is True


def test_core_final_gate_rejects_tampered_trace_hash_chain(tmp_path):
    result = successful_result(tmp_path)
    tampered_trace = list(result.trace)
    tampered_trace[0] = tampered_trace[0].model_copy(update={"summary": "tampered"})
    tampered = result.model_copy(update={"trace": tampered_trace})

    gate = certify_core_final_gate(tampered, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert {"runtime_certification", "state_replay"} <= failed_check_names(gate)


def test_core_final_gate_rejects_result_runtime_certification_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.runtime_certification is not None
    unsafe = result.model_copy(
        update={
            "runtime_certification": result.runtime_certification.model_copy(
                update={"event_count": result.runtime_certification.event_count + 1}
            )
        }
    )

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "runtime_certification" in failed_check_names(gate)


def test_core_final_gate_rejects_result_state_snapshot_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.state_snapshot is not None
    unsafe = result.model_copy(
        update={
            "state_snapshot": result.state_snapshot.model_copy(
                update={"trace_hash": "forged_trace_hash"}
            )
        }
    )

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "state_replay" in failed_check_names(gate)


def test_core_final_gate_rejects_tampered_mission_trace_hash_chain(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    tampered_mission_trace = list(result.mission_result.trace_events)
    tampered_mission_trace[0] = tampered_mission_trace[0].model_copy(update={"summary": "tampered"})
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": tampered_mission_trace})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_trace_integrity" in failed_check_names(gate)


def test_core_final_gate_rejects_truncated_but_hash_valid_mission_trace(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    receipt_indexes = [
        index
        for index, event in enumerate(result.mission_result.trace_events)
        if event.event_type == MissionTraceEventType.ACTION_RECEIPT_RECORDED
    ]
    unsafe_trace = result.mission_result.trace_events[: max(receipt_indexes) + 1]
    assert unsafe_trace[-1].event_type == MissionTraceEventType.ACTION_RECEIPT_RECORDED
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_trace})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_trace_integrity" in failed_check_names(gate)


def test_core_final_gate_rejects_missing_mission_results_archive(tmp_path):
    result = successful_result(tmp_path)
    unsafe = result.model_copy(update={"mission_results": []})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_results_archive" in failed_check_names(gate)


def test_core_final_gate_rejects_tampered_archived_mission_result(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_results
    tampered_archive = list(result.mission_results)
    tampered_trace = list(tampered_archive[0].trace_events)
    tampered_trace[0] = tampered_trace[0].model_copy(update={"summary": "tampered archive"})
    tampered_archive[0] = tampered_archive[0].model_copy(update={"trace_events": tampered_trace})
    unsafe = result.model_copy(update={"mission_results": tampered_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_results_archive" in failed_check_names(gate)


def test_core_final_gate_rejects_archived_mission_result_missing_risk_decisions(tmp_path):
    result = repair_recovered_result(tmp_path)
    assert len(result.mission_results) == 2
    tampered_archive = list(result.mission_results)
    first = tampered_archive[0]
    unsafe_events = [
        event
        for event in first.trace_events
        if event.event_type != MissionTraceEventType.RISK_ROUTE_DECIDED
    ]
    tampered_archive[0] = first.model_copy(update={"trace_events": rehash_mission_trace(unsafe_events)})
    unsafe = result.model_copy(update={"mission_results": tampered_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_results_archive" in failed_check_names(gate)


def test_core_final_gate_rejects_archived_mission_result_missing_receipt_events(tmp_path):
    result = repair_recovered_result(tmp_path)
    assert len(result.mission_results) == 2
    tampered_archive = list(result.mission_results)
    first = tampered_archive[0]
    unsafe_events = [
        event
        for event in first.trace_events
        if event.event_type != MissionTraceEventType.ACTION_RECEIPT_RECORDED
    ]
    tampered_archive[0] = first.model_copy(update={"trace_events": rehash_mission_trace(unsafe_events)})
    unsafe = result.model_copy(update={"mission_results": tampered_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_results_archive" in failed_check_names(gate)


def test_core_final_gate_rejects_selected_tool_without_eligible_decision(tmp_path):
    result = successful_result(tmp_path)
    unsafe = result.model_copy(update={"selected_tools": [*result.selected_tools, "shell_critical_blocked"]})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "selected_tools_are_policy_eligible" in failed_check_names(gate)


def test_core_final_gate_rejects_tool_selection_decision_without_policy_trace(tmp_path):
    result = successful_result(tmp_path)
    unsafe_decisions = [
        decision.model_copy(update={"trace_id": "missing_policy_trace"})
        if decision.candidate_tool_id == "safe_file_writer"
        else decision
        for decision in result.tool_selection_decisions
    ]
    unsafe = result.model_copy(update={"tool_selection_decisions": unsafe_decisions})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "tool_policy_decisions_trace_bound" in failed_check_names(gate)


def test_core_final_gate_rejects_tool_selection_decision_trace_payload_mismatch(tmp_path):
    result = successful_result(tmp_path)
    selected_decision = next(
        decision
        for decision in result.tool_selection_decisions
        if decision.candidate_tool_id == "safe_file_writer"
    )
    unsafe_trace = []
    for event in result.trace:
        if event.id == selected_decision.trace_id:
            unsafe_trace.append(event.model_copy(update={"payload": {**event.payload, "tool_id": "forged_tool"}}))
        else:
            unsafe_trace.append(event)
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "tool_policy_decisions_trace_bound" in failed_check_names(gate)


def test_core_final_gate_rejects_tool_policy_side_effect_payload_mismatch(tmp_path):
    result = successful_result(tmp_path)
    selected_decision = next(
        decision
        for decision in result.tool_selection_decisions
        if decision.candidate_tool_id == "safe_file_writer"
    )
    unsafe_trace = []
    for event in result.trace:
        if event.id == selected_decision.trace_id:
            unsafe_trace.append(event.model_copy(update={"payload": {**event.payload, "requested_side_effects": []}}))
        else:
            unsafe_trace.append(event)
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "tool_policy_decisions_trace_bound" in failed_check_names(gate)


def test_core_final_gate_rejects_learning_without_human_approval(tmp_path):
    result = blocked_result(tmp_path)
    unsafe_proposals = [
        proposal.model_copy(update={"requires_human_approval": False})
        for proposal in result.learning_proposals
    ]
    unsafe = result.model_copy(update={"learning_proposals": unsafe_proposals})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "learning_requires_human_approval" in failed_check_names(gate)


def test_core_final_gate_rejects_learning_proposals_without_trace_event(tmp_path):
    result = blocked_result(tmp_path)
    unsafe_trace = [
        event
        for event in result.trace
        if event.event_type != AgentEventType.LEARNING_PROPOSED
    ]
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "learning_requires_human_approval" in failed_check_names(gate)


def test_core_final_gate_rejects_learning_proposal_count_mismatch(tmp_path):
    result = blocked_result(tmp_path)
    unsafe_trace = []
    tampered = False
    for event in result.trace:
        if not tampered and event.event_type == AgentEventType.LEARNING_PROPOSED:
            unsafe_trace.append(event.model_copy(update={"payload": {**event.payload, "proposal_count": 0}}))
            tampered = True
        else:
            unsafe_trace.append(event)
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "learning_requires_human_approval" in failed_check_names(gate)


def test_core_final_gate_rejects_project_path_outside_allowed_root(tmp_path):
    result = successful_result(tmp_path)
    unsafe = result.model_copy(update={"project_path": str(tmp_path.parent)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "project_scope" in failed_check_names(gate)


def test_core_final_gate_rejects_mission_result_project_path_divergence(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_mission_result = result.mission_result.model_copy(update={"project_path": str(tmp_path / "other")})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_result_consistency" in failed_check_names(gate)


def test_core_final_gate_rejects_mission_result_success_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_mission_result = result.mission_result.model_copy(update={"success": False})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_result_consistency" in failed_check_names(gate)


def test_core_final_gate_rejects_artifacts_without_mission_result(tmp_path):
    result = successful_result(tmp_path)
    unsafe = result.model_copy(update={"success": False, "final_phase": AgentPhase.FAILED, "mission_result": None})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_result_consistency" in failed_check_names(gate)


def test_core_final_gate_rejects_result_artifact_metadata_divergence(tmp_path):
    result = successful_result(tmp_path)
    unsafe_artifacts = [
        artifact.model_copy(update={"path": "forged-display-path.md"}) if index == 0 else artifact
        for index, artifact in enumerate(result.artifacts)
    ]
    unsafe = result.model_copy(update={"artifacts": unsafe_artifacts})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_result_consistency" in failed_check_names(gate)


def test_core_final_gate_rejects_active_plan_trace_divergence(tmp_path):
    result = successful_result(tmp_path)
    assert result.active_plan is not None
    unsafe_plan = result.active_plan.model_copy(
        update={
            "steps": [
                step.model_copy(update={"action": step.action.model_copy(update={"id": f"forged_{step.action.id}"})})
                if index == 0
                else step
                for index, step in enumerate(result.active_plan.steps)
            ]
        }
    )
    unsafe = result.model_copy(update={"active_plan": unsafe_plan})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "active_plan_matches_mission_trace" in failed_check_names(gate)


def test_core_final_gate_rejects_active_plan_action_mission_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.active_plan is not None
    unsafe_plan = result.active_plan.model_copy(
        update={
            "steps": [
                step.model_copy(update={"action": step.action.model_copy(update={"mission_id": "foreign_mission"})})
                if index == 0
                else step
                for index, step in enumerate(result.active_plan.steps)
            ]
        }
    )
    unsafe = result.model_copy(update={"active_plan": unsafe_plan})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "active_plan_matches_mission_trace" in failed_check_names(gate)


def test_core_final_gate_rejects_duplicate_active_plan_action_ids(tmp_path):
    result = successful_result(tmp_path)
    assert result.active_plan is not None
    duplicate_id = result.active_plan.steps[0].action.id
    unsafe_plan = result.active_plan.model_copy(
        update={
            "steps": [
                step.model_copy(update={"action": step.action.model_copy(update={"id": duplicate_id})})
                if index == 1
                else step
                for index, step in enumerate(result.active_plan.steps)
            ]
        }
    )
    unsafe = result.model_copy(update={"active_plan": unsafe_plan})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "active_plan_matches_mission_trace" in failed_check_names(gate)


def test_core_final_gate_rejects_result_evidence_chain_without_trace_event(tmp_path):
    result = successful_result(tmp_path)
    unsafe_chains = [
        chain.model_copy(update={"id": "forged_evidence_chain"}) if index == 0 else chain
        for index, chain in enumerate(result.evidence_chains)
    ]
    unsafe = result.model_copy(update={"evidence_chains": unsafe_chains})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "evidence_chains_trace_bound" in failed_check_names(gate)


def test_core_final_gate_rejects_duplicate_evidence_chain_trace_event(tmp_path):
    result = successful_result(tmp_path)
    unsafe_trace = []
    inserted = False
    for event in result.trace:
        unsafe_trace.append(event)
        if not inserted and event.event_type == AgentEventType.EVIDENCE_CHAIN_BUILT:
            unsafe_trace.append(event.model_copy(update={"id": new_id("aev")}))
            inserted = True
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "evidence_chains_trace_bound" in failed_check_names(gate)


def test_core_final_gate_rejects_successful_mission_result_without_artifact_receipts(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_mission_result = result.mission_result.model_copy(update={"artifact_receipts": []})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_artifact_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_mission_receipts_without_trace_events(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = [
        event
        for event in result.mission_result.trace_events
        if event.event_type != MissionTraceEventType.ACTION_RECEIPT_RECORDED
    ]
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_artifact_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_mission_receipt_event_hash_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = []
    tampered = False
    for event in result.mission_result.trace_events:
        if not tampered and event.event_type == MissionTraceEventType.ACTION_RECEIPT_RECORDED:
            unsafe_events.append(event.model_copy(update={"result": {**event.result, "artifact_sha256": "bad"}}))
            tampered = True
        else:
            unsafe_events.append(event)
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_artifact_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_duplicate_mission_artifact_receipts(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    assert result.mission_result.artifact_receipts
    duplicate_receipts = [*result.mission_result.artifact_receipts, result.mission_result.artifact_receipts[0]]
    unsafe_mission_result = result.mission_result.model_copy(update={"artifact_receipts": duplicate_receipts})
    unsafe_archive = list(result.mission_results)
    unsafe_archive[-1] = unsafe_mission_result
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result, "mission_results": unsafe_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_artifact_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_successful_mission_without_risk_route_decisions(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = [
        event
        for event in result.mission_result.trace_events
        if event.event_type != MissionTraceEventType.RISK_ROUTE_DECIDED
    ]
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_forged_mission_risk_route_posture(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = []
    tampered = False
    for event in result.mission_result.trace_events:
        if not tampered and event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED:
            unsafe_events.append(event.model_copy(update={"result": {**event.result, "posture": MissionMode.SAFE.value}}))
            tampered = True
        else:
            unsafe_events.append(event)
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_duplicate_risk_route_decision(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = []
    inserted = False
    for event in result.mission_result.trace_events:
        unsafe_events.append(event)
        if not inserted and event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED:
            unsafe_events.append(event.model_copy())
            inserted = True
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": rehash_mission_trace(unsafe_events)})
    unsafe_archive = list(result.mission_results)
    unsafe_archive[-1] = unsafe_mission_result
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result, "mission_results": unsafe_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_orphan_risk_route_decision(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    risk_event = next(
        event
        for event in result.mission_result.trace_events
        if event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED
    )
    unsafe_events = [
        *result.mission_result.trace_events[:-1],
        risk_event.model_copy(update={"action_id": "forged_action_without_route"}),
        result.mission_result.trace_events[-1],
    ]
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": rehash_mission_trace(unsafe_events)})
    unsafe_archive = list(result.mission_results)
    unsafe_archive[-1] = unsafe_mission_result
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result, "mission_results": unsafe_archive})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_executed_action_without_continuation_route(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = []
    tampered = False
    for event in result.mission_result.trace_events:
        if not tampered and event.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED:
            unsafe_events.append(
                event.model_copy(
                    update={
                        "result": {
                            **event.result,
                            "route": MissionActionRoute.ESCALATE.value,
                            "blocking_rule": "forged_escalation",
                        }
                    }
                )
            )
            tampered = True
        else:
            unsafe_events.append(event)
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_executed_action_without_action_routed_event(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_events = [
        event
        for event in result.mission_result.trace_events
        if event.event_type != MissionTraceEventType.ACTION_ROUTED
    ]
    unsafe_mission_result = result.mission_result.model_copy(update={"trace_events": unsafe_events})
    unsafe = result.model_copy(update={"mission_result": unsafe_mission_result})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "mission_risk_route_decisions" in failed_check_names(gate)


def test_core_final_gate_rejects_execution_posture_mode_mismatch(tmp_path):
    result = successful_result(tmp_path)
    assert result.execution_posture is not None
    unsafe = result.model_copy(update={"execution_posture": result.execution_posture.model_copy(update={"mode": MissionMode.SAFE})})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "execution_posture_matches_authority" in failed_check_names(gate)


def test_core_final_gate_rejects_global_action_budget_overflow(tmp_path):
    result = successful_result(tmp_path)
    assert result.mission_result is not None
    unsafe_trace = []
    tampered = False
    for event in result.trace:
        if not tampered and event.event_type == AgentEventType.WORKER_COMPLETED:
            unsafe_trace.append(event.model_copy(update={"payload": {**event.payload, "action_count": result.mission_result.mission.max_actions + 1}}))
            tampered = True
        else:
            unsafe_trace.append(event)
    unsafe = result.model_copy(update={"trace": unsafe_trace})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "global_action_budget" in failed_check_names(gate)


def test_core_final_gate_rejects_worker_action_count_payload_below_archive(tmp_path):
    result = successful_result(tmp_path)
    unsafe_trace = []
    tampered = False
    for event in result.trace:
        if not tampered and event.event_type == AgentEventType.WORKER_COMPLETED:
            unsafe_trace.append(event.model_copy(update={"payload": {**event.payload, "action_count": 0}}))
            tampered = True
        else:
            unsafe_trace.append(event)
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "global_action_budget" in failed_check_names(gate)


def test_core_final_gate_rejects_controlled_execution_omitted_from_results(tmp_path):
    env = envelope(
        allowed_tools=["safe_file_writer", "safe_local_markdown_tool"],
    )
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Controlled omission gate",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {"path": "runtime/omitted.md", "content": "must be accounted"},
                }
            ],
        },
        evidence_refs=["ev_wtp"],
    )
    unsafe = result.model_copy(update={"controlled_capability_results": []})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "controlled_capability_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_untraced_controlled_rejection_result(tmp_path):
    env = envelope(
        allowed_tools=["safe_file_writer", "safe_local_markdown_tool"],
    )
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Controlled rejection trace gate",
            "tool_calls": ["tool_id=safe_local_markdown_tool; no action here"],
        },
        evidence_refs=["ev_wtp"],
    )
    unsafe_results = [dict(item) for item in result.controlled_capability_results]
    unsafe_results[0].pop("trace_event_id", None)
    unsafe = result.model_copy(update={"controlled_capability_results": unsafe_results})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "controlled_capability_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_controlled_rejection_omitted_from_results(tmp_path):
    env = envelope(
        allowed_tools=["safe_file_writer", "safe_local_markdown_tool"],
    )
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Controlled rejection omission gate",
            "tool_calls": ["tool_id=safe_local_markdown_tool; no action here"],
        },
        evidence_refs=["ev_wtp"],
    )
    unsafe = result.model_copy(update={"controlled_capability_results": []})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "controlled_capability_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_duplicate_controlled_execution_receipt_event(tmp_path):
    env = envelope(allowed_tools=["safe_file_writer", "safe_local_markdown_tool"])
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Controlled duplicate gate",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {"path": "runtime/duplicate.md", "content": "must be unique"},
                }
            ],
        },
        evidence_refs=["ev_wtp"],
    )
    unsafe_trace = []
    inserted = False
    for event in result.trace:
        unsafe_trace.append(event)
        if not inserted and event.event_type == AgentEventType.CONTROLLED_CAPABILITY_EXECUTED:
            unsafe_trace.append(event.model_copy(update={"id": new_id("aev")}))
            inserted = True
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "controlled_capability_receipts" in failed_check_names(gate)


def test_core_final_gate_rejects_controlled_execution_missing_policy_or_capture_trace_refs(tmp_path):
    env = envelope(allowed_tools=["safe_file_writer", "safe_local_markdown_tool"])
    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {
            "idea": "Controlled missing trace refs gate",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {"path": "runtime/missing-trace-refs.md", "content": "must reference policy and capture"},
                }
            ],
        },
        evidence_refs=["ev_wtp"],
    )
    unsafe_trace = [
        event.model_copy(update={"trace_refs": ()})
        if event.event_type == AgentEventType.CONTROLLED_CAPABILITY_EXECUTED
        else event
        for event in result.trace
    ]
    unsafe = result.model_copy(update={"trace": rehash_agent_trace(unsafe_trace)})

    gate = certify_core_final_gate(unsafe, allowed_project_root=tmp_path)

    assert gate.accepted is False
    assert "controlled_capability_receipts" in failed_check_names(gate)
