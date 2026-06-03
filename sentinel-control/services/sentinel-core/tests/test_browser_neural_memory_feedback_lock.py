from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentRuntime
from sentinel.agent.browser.neural import MotorProposalArtifact
from sentinel.agent.browser.neural.models import stable_neural_hash

from test_motor_neuron_to_organ_dispatch_lock import _config, _motor_proposal, _runtime_mission, _user_input


def test_memory_feedback_receives_neural_signal_refs(tmp_path: Path) -> None:
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=True)).run(
        _runtime_mission(),
        user_input=_user_input([
            _motor_proposal("mprop_browser_open", "open"),
            _motor_proposal("mprop_browser_close", "close"),
        ]),
    )

    assert result.memory_feedback_result is not None
    summaries = "\n".join(entry.safe_summary for entry in result.memory_feedback_result.memory_entries)
    assert "browser_neural_signal_refs=nsig_planner" in summaries
    assert result.memory_feedback_result.authority_effect == "none"
    assert result.memory_feedback_result.can_grant_authority is False


def test_replan_packet_includes_cortex_refs(tmp_path: Path) -> None:
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=True)).run(
        _runtime_mission(),
        user_input=_user_input([
            _motor_proposal("mprop_browser_open", "open"),
            _motor_proposal("mprop_browser_close", "close"),
        ]),
    )

    assert result.replan_ready is True
    assert result.automatic_replan_executed is False
    assert result.replan_packet is not None
    assert result.replan_packet["browser_neural_signal_refs"] == ["nsig_planner"]
    assert result.replan_packet["browser_neural_motor_proposal_refs"] == ["mprop_browser_close", "mprop_browser_open"]
    assert result.replan_packet["recommended_next_loop_input"]["use_browser_neural_signal_refs"] == ["nsig_planner"]


def test_failed_neural_proposal_generates_safe_memory_context_without_authority(tmp_path: Path) -> None:
    bad = _motor_proposal("mprop_bad_evidence", "open")
    bad["source_evidence_refs"] = ["ev_invented"]
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=True)).run(
        _runtime_mission(),
        user_input=_user_input([bad]),
    )

    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.trace.executed_count == 0
    assert result.memory_feedback_result is not None
    assert result.memory_feedback_result.authority_effect == "none"
    assert result.memory_feedback_result.can_grant_authority is False
    assert result.replan_packet is not None
    assert result.replan_packet["browser_neural_signal_refs"] == ["nsig_planner"]
    assert result.replan_packet["automatic_replan_executed"] is False


def test_unsafe_browser_neural_signal_refs_are_hashed_before_memory_or_replan(tmp_path: Path) -> None:
    payload = _motor_proposal("mprop_unsafe_signal_refs", "open")
    payload["source_signal_refs"] = [
        "nsig_session_cookie=sessionid_abc123",
        "nsig_url=https://example.com/?token=plainvalue",
        "nsig_planner",
    ]
    payload.pop("artifact_hash", None)
    hash_payload = {
        key: payload.get(key)
        for key in (
            "proposal_artifact_id",
            "mission_id",
            "organ_kind",
            "action_level",
            "target_ref",
            "source_signal_refs",
            "source_evidence_refs",
            "required_authority",
            "risk_flags",
            "expected_receipt_type",
            "verification_plan",
            "url",
            "action_kind",
            "allowed_domains",
            "target_role",
            "target_name",
            "text",
        )
    }
    proposal = MotorProposalArtifact(**payload, artifact_hash=stable_neural_hash(hash_payload)).model_dump(mode="python")

    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=True)).run(
        _runtime_mission(),
        user_input=_user_input([proposal]),
    )

    dumped = result.model_dump_json()

    assert "sessionid_abc123" not in dumped
    assert "token=plainvalue" not in dumped
    assert result.replan_packet is not None
    assert "nsig_planner" in result.replan_packet["browser_neural_signal_refs"]
    assert all("=" not in ref and "?" not in ref and "/" not in ref for ref in result.replan_packet["browser_neural_signal_refs"])
    assert any(ref.startswith("nsig_ref_hash_") for ref in result.replan_packet["browser_neural_signal_refs"])
