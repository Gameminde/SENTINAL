from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

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


def test_cockpit_cli_llm_mode_uses_explicit_model_contract(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_ollama_contract()), encoding="utf-8")
    recorder = RecordingHttpxClient(_provider_payload(_valid_llm_output()))
    monkeypatch.setattr("httpx.Client", recorder)

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--model-contract", str(contract_path), "--once", "Je veux lancer un business"])

    output = capsys.readouterr().out
    assert code == 0
    assert "clarifier la mission" in output.lower()
    assert recorder.calls[0]["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in recorder.calls[0]["headers"]


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


def test_cockpit_cli_help(tmp_path: Path, capsys) -> None:
    code = main(["cockpit", "--run-root", str(tmp_path), "--deterministic-test-mode", "--once", "/help"])

    output = capsys.readouterr().out
    assert code == 0
    assert "/status" in output
    assert "/timeline" in output


def test_cockpit_cli_missions(tmp_path: Path, capsys) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Je veux lancer un business\noui commence\n/missions\n", encoding="utf-8")

    code = main(["cockpit", "--run-root", str(tmp_path / "runs"), "--deterministic-test-mode", "--script", str(script)])

    output = capsys.readouterr().out
    assert code == 0
    assert "Missions" in output
    assert "queued" in output


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


class RecordingHttpxClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *_args: Any, **_kwargs: Any) -> RecordingHttpxClient:
        return self

    def __enter__(self) -> RecordingHttpxClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _Response(self.payload)


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)
        self.request = httpx.Request("POST", "http://localhost:11434")

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def _ollama_contract() -> dict[str, object]:
    model = "llama3.2"
    return {
        "selected_provider_id": "ollama",
        "selected_backend_id": "ollama_openai_compatible_chat",
        "selected_model": model,
        "cost_profile": {
            "model_name": model,
            "input_usd_per_1m": 0.0,
            "output_usd_per_1m": 0.0,
            "context_window_tokens": 32000,
        },
        "capability_profile": {
            "model_name": model,
            "context_window_tokens": 32000,
            "supports_tool_calling": False,
        },
        "context_budget_policy": {
            "max_decision_frame_tokens": 4000,
            "max_tool_schema_tokens": 500,
            "max_evidence_tokens": 2000,
            "reserve_output_tokens": 500,
        },
        "quality_expectation": {
            "expected_quality": "operator_v0",
            "minimum_evidence_refs": 0,
            "retry_budget": 0,
        },
    }


def _provider_payload(content: dict[str, object]) -> dict[str, object]:
    return {
        "id": "chatcmpl_unit",
        "model": "llama3.2",
        "choices": [{"message": {"content": json.dumps(content)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }


def _valid_llm_output() -> dict[str, object]:
    return {
        "reply": "Tres bien. Je vais clarifier la mission avant de commencer.",
        "intent": {"kind": "draft_mission", "text": "launch AI training business"},
        "mission_draft": {
            "title": "AI training business launch",
            "objective": "Research the target market and prepare launch artifacts.",
            "constraints": ["no payment", "no real outbound send"],
            "expected_artifacts": ["market summary", "launch plan"],
        },
        "authority_summary": {
            "mission_id": "mission_llm",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only; no external send or payment.",
        },
    }
