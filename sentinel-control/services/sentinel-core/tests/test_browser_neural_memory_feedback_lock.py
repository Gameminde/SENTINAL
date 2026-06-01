from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentRuntime

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
