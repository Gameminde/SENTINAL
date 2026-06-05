from __future__ import annotations

from pathlib import Path


def test_power_fabric_demo_runs_multi_actuator_timeline(tmp_path: Path) -> None:
    from sentinel.power.demo import run_power_fabric_orchestration_demo

    result = run_power_fabric_orchestration_demo(project_root=tmp_path)

    assert result.status == "completed"
    assert [step.step_id for step in result.step_results] == [
        "browser_observe",
        "api_metadata",
        "shell_python_version",
        "workspace_report",
        "channel_draft",
    ]
    assert len(result.receipt_refs) >= 5
    assert len(result.finalgate_certificate_refs) >= 5
    assert len(result.memory_feedback_refs) >= 5
    assert result.timeline.verify_chain() is True
    assert (tmp_path / "POWER_FABRIC_DEMO_REPORT.md").is_file()


def test_power_fabric_demo_uses_no_real_sender_and_no_real_network(tmp_path: Path) -> None:
    from sentinel.power.demo import run_power_fabric_orchestration_demo

    api_calls: list[str] = []
    sender_calls: list[str] = []

    result = run_power_fabric_orchestration_demo(
        project_root=tmp_path,
        api_call_recorder=api_calls,
        sender_call_recorder=sender_calls,
    )

    assert result.status == "completed"
    assert api_calls == ["GET https://api.example.com/demo/metadata"]
    assert sender_calls == []
    assert "fixture api body" not in str(result.model_dump(mode="json"))
    assert "founder@example.com" not in str(result.model_dump(mode="json"))
