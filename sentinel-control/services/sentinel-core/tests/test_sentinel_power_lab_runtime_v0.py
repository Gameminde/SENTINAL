from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope


def _mission_payload(**overrides: object) -> dict[str, object]:
    mission = {
        "id": "mission_power_lab_test",
        "user_id": "user_power_lab",
        "mission_title": "Power Lab smoke mission",
        "mission_objective": "Run Sentinel Power Lab smoke path.",
        "success_criteria": ["run artifact exists"],
        "allowed_actions": [],
        "allowed_tools": [],
        "forbidden_actions": [
            "browser_submit",
            "browser_login",
            "api_call",
            "channel_send",
            "shell",
            "desktop_action",
            "payment",
        ],
        "allowed_paths": ["data/generated_projects"],
        "max_actions": 3,
        "max_cost_usd": 0.0,
    }
    mission.update(overrides)
    return {
        "preset": "lab_local",
        "mission": mission,
        "user_input": {"objective": "safe smoke run"},
    }


def _write_mission(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_power_lab_runs_json_mission_and_writes_artifacts(tmp_path: Path) -> None:
    from sentinel.power_lab import run_power_lab_mission

    mission_path = _write_mission(tmp_path / "mission.json", _mission_payload())

    result = run_power_lab_mission(mission_path, run_root=tmp_path / "runs")

    assert result.status in {"completed", "blocked", "failed"}
    assert result.mission_id == "mission_power_lab_test"
    assert result.run_dir.exists()
    assert (result.run_dir / "input.mission.json").is_file()
    assert (result.run_dir / "result.summary.json").is_file()
    assert (result.run_dir / "trace.events.json").is_file()
    assert (result.run_dir / "power_kernel_status.json").is_file()
    assert result.authority_effect == "none"
    assert result.data_not_instruction is True

    summary = json.loads((result.run_dir / "result.summary.json").read_text(encoding="utf-8"))
    assert summary["mission_id"] == "mission_power_lab_test"
    assert summary["runtime_invoked"] is True
    assert summary["organ_dispatch_enabled"] is False
    assert summary["no_new_dangerous_actuator"] is True


def test_power_lab_default_preset_does_not_enable_dangerous_power() -> None:
    from sentinel.power_lab import build_power_lab_runtime_config, get_power_lab_preset

    preset = get_power_lab_preset("lab_local")
    config = build_power_lab_runtime_config(preset)

    assert preset.name == "lab_local"
    assert preset.enables_credentials is False
    assert preset.enables_shell is False
    assert preset.enables_browser_submit is False
    assert preset.enables_api_mutation is False
    assert preset.enables_channel_send is False
    assert preset.enables_desktop is False
    assert config.enabled is False
    assert config.organ_dispatch_enabled is False
    assert config.deny_shell is True
    assert config.deny_credentials is True
    assert config.deny_api is True
    assert config.deny_browser is True
    assert config.deny_channel is True


def test_power_lab_can_enable_existing_local_organs_only_with_explicit_opt_in() -> None:
    from sentinel.power_lab import build_power_lab_runtime_config, get_power_lab_preset
    from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionMode

    preset = get_power_lab_preset("lab_local")
    config = build_power_lab_runtime_config(preset, enable_organ_dispatch=True)

    assert config.enabled is True
    assert config.organ_dispatch_enabled is True
    assert config.mode is OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY
    assert config.allow_l2 is True
    assert config.allow_l3 is True
    assert config.allow_browser_readonly is False
    assert config.allow_browser_preparation is False
    assert config.allow_browser_semantic_extraction is False
    assert config.deny_shell is True
    assert config.deny_credentials is True


def test_power_lab_rejects_secret_like_input_without_echoing_secret(tmp_path: Path) -> None:
    from sentinel.power_lab import PowerLabMissionRejected, run_power_lab_mission

    secret_value = "Bearer " + "sk-test-" + "abcdefghijklmnopqrstuvwxyz123456"
    payload = _mission_payload()
    payload["user_input"] = {"authorization": secret_value}
    mission_path = _write_mission(tmp_path / "mission.json", payload)

    with pytest.raises(PowerLabMissionRejected) as exc:
        run_power_lab_mission(mission_path, run_root=tmp_path / "runs")

    message = str(exc.value)
    assert "unsafe mission file" in message
    assert secret_value not in message


def test_power_lab_rejects_forbidden_dangerous_actions(tmp_path: Path) -> None:
    from sentinel.power_lab import PowerLabMissionRejected, run_power_lab_mission

    mission_path = _write_mission(
        tmp_path / "mission.json",
        _mission_payload(allowed_actions=["browser_submit", "shell", "api_call"]),
    )

    with pytest.raises(PowerLabMissionRejected) as exc:
        run_power_lab_mission(mission_path, run_root=tmp_path / "runs")

    assert "dangerous action requested" in str(exc.value)


def test_power_lab_cli_entrypoint_runs_mission(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel.cli import main

    mission_path = _write_mission(tmp_path / "mission.json", _mission_payload())
    run_root = tmp_path / "runs"

    exit_code = main(["run", "--mission", str(mission_path), "--run-root", str(run_root)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "mission_power_lab_test" in captured.out
    assert "run_dir=" in captured.out
    assert run_root.exists()


def test_power_lab_input_builds_real_authority_envelope(tmp_path: Path) -> None:
    from sentinel.power_lab import load_power_lab_mission_file

    mission_path = _write_mission(tmp_path / "mission.json", _mission_payload())

    mission_file = load_power_lab_mission_file(mission_path)

    assert isinstance(mission_file.mission, MissionAuthorityEnvelope)
    assert mission_file.mission.id == "mission_power_lab_test"
    assert mission_file.authority_effect == "none"
    assert mission_file.data_not_instruction is True
