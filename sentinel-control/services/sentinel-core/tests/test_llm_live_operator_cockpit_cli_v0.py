from __future__ import annotations

import json
from pathlib import Path

from sentinel.cli import main


def test_cockpit_cli_greeting(tmp_path: Path, capsys) -> None:
    code = main(["cockpit", "--run-root", str(tmp_path), "--deterministic-test-mode", "--once", "Sentinel t'es la ?"])

    output = capsys.readouterr().out
    assert code == 0
    assert "je suis la" in output.lower()


def test_cockpit_cli_deterministic_test_mode(tmp_path: Path, capsys) -> None:
    code = main(["chat", "--run-root", str(tmp_path), "--deterministic-test-mode", "--once", "Je veux lancer un business"])

    output = capsys.readouterr().out
    assert code == 0
    assert "mode test deterministe" in output.lower()


def test_cockpit_cli_start_runs_mission(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "mission lancee" in output.lower()


def test_cockpit_cli_status(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\nstatus\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "status: queued" in output.lower()


def test_cockpit_cli_timeline(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\n/timeline\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "mission_created" in output


def test_cockpit_cli_replay(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\n/replay\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "Replay" in output


def test_cockpit_cli_pause_resume_kill(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\npause\nresume\nkill\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "Mission paused" in output
    assert "Mission resumed" in output
    assert "Mission killed" in output


def test_cockpit_cli_secret_redaction(tmp_path: Path, capsys) -> None:
    code = main([
        "cockpit",
        "--run-root",
        str(tmp_path),
        "--deterministic-test-mode",
        "--once",
        "Authorization: Bearer secret_token_123456789",
    ])

    output = capsys.readouterr().out
    assert code == 0
    assert "Bearer" not in output
    assert "secret_token" not in output


def test_cockpit_cli_no_manual_mission_id_for_single_active_mission(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\nstatus\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script), "--json"])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert code == 0
    assert payload[-1]["mission_record"]["mission_id"]
