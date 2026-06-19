from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel import cli
from sentinel.operator.daemon_models import DaemonQueueStatus
from sentinel.operator.daemon_runtime import MissionDaemonRuntimeError
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_cli_product_route_uses_single_runtime_host_lifecycle_and_pumps_daemon(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hosts: list[RecordingRuntimeHost] = []
    monkeypatch.setattr(cli, "SentinelRuntimeHost", _recording_host_factory(hosts))
    scope_path = _write_approval_scope(tmp_path)
    script_path = _write_script(tmp_path)

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--authority-scope",
            str(scope_path),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    output = capsys.readouterr()
    turns = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert len(hosts) == 1
    host = hosts[0]
    assert host.start_count == 1
    assert host.shutdown_count == 1
    assert host.pump_calls == [turns[-1]["mission_record"]["mission_id"]]

    mission_id = turns[-1]["mission_record"]["mission_id"]
    request = host.lifecycle.latest_execution_request(mission_id)
    state = host.lifecycle.derive_request_state(mission_id, request.request_id)
    active = host.authority_issuer.resolve_active(mission_id)
    queue_record = host.daemon.store.load_queue_record(mission_id)
    events = [event.event_type for event in host.kernel.store.load_events(mission_id)]

    assert state.state is MissionExecutionRequestState.CLAIMED
    assert queue_record.status is DaemonQueueStatus.RUNNING
    assert active.allowed_systems == ["local_workspace"]
    assert active.allowed_tools == ["read_only_observation"]
    assert active.allowed_actions == ["research", "draft"]
    assert active.allowed_paths == ["."]
    assert active.max_actions == 4
    assert events.index("mission_authority_envelope_issued") < events.index("mission_execution_request_prepared")
    assert events.index("mission_execution_request_prepared") < events.index("mission_queued")
    assert "mission_execution_request_claimed" in events
    assert "daemon_tick_completed" in events
    assert turns[-1]["metadata"]["internal_access_classification"] == "production_route"
    assert turns[-1]["metadata"]["runtime_host_lifecycle_ref"] == f"lifecycle:{id(host.lifecycle)}"
    assert turns[-1]["metadata"]["daemon_pickup"]["claimed"] is True


def test_cli_product_route_missing_scope_blocks_before_mission_creation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = _write_script(tmp_path)

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--script",
            str(script_path),
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    assert code == 0
    assert turns[-1]["metadata"]["blocked_reason"] == "explicit_authority_approval_scope_required"
    assert turns[-1]["metadata"]["internal_access_classification"] == "production_route"
    kernel = MissionKernel(run_root=tmp_path / "runs")
    assert kernel.list_missions() == []


def test_cli_product_route_shutdowns_on_cockpit_exception(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hosts: list[RecordingRuntimeHost] = []
    monkeypatch.setattr(cli, "SentinelRuntimeHost", _recording_host_factory(hosts))
    monkeypatch.setattr(cli.LLMLiveOperatorCockpit, "handle", _raise_cockpit_failure)

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--once",
            "Je veux lancer un business",
        ]
    )

    err = capsys.readouterr().err
    assert code == 2
    assert "cockpit_product_route_failed" in err
    assert "RuntimeError" in err
    assert len(hosts) == 1
    assert hosts[0].start_count == 1
    assert hosts[0].shutdown_count == 1
    assert hosts[0].pump_calls == []


def test_cli_product_route_shutdowns_on_pickup_failure_without_claim_or_legacy_fallback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hosts: list[FailingPumpRuntimeHost] = []
    monkeypatch.setattr(cli, "SentinelRuntimeHost", _failing_pump_host_factory(hosts))
    script_path = _write_script(tmp_path)

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    output = capsys.readouterr()
    assert code == 2
    assert "daemon_pickup_failed" in output.err
    assert "legacy" not in output.err.lower()
    assert len(hosts) == 1
    host = hosts[0]
    assert host.shutdown_count == 1
    mission_id = host.kernel.list_missions()[0].mission_id
    request = host.lifecycle.latest_execution_request(mission_id)
    state = host.lifecycle.derive_request_state(mission_id, request.request_id)
    events = [event.event_type for event in host.kernel.store.load_events(mission_id)]
    assert state.state is MissionExecutionRequestState.QUEUED
    assert "mission_execution_request_claimed" not in events


def test_cli_product_route_host_start_failure_does_not_fallback_to_legacy(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hosts: list[StartFailingRuntimeHost] = []
    monkeypatch.setattr(cli, "SentinelRuntimeHost", _start_failing_host_factory(hosts))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--once",
            "Sentinel t'es la ?",
        ]
    )

    err = capsys.readouterr().err
    assert code == 2
    assert "runtime_host_start_failed" in err
    assert "legacy" not in err.lower()
    assert len(hosts) == 1
    assert hosts[0].shutdown_count == 1
    assert MissionKernel(run_root=tmp_path / "runs").list_missions() == []


def test_cli_legacy_internal_route_is_explicit_and_classified(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--legacy-internal-direct",
            "--once",
            "Je veux lancer un business",
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    assert code == 0
    assert turns[0]["metadata"]["internal_access_classification"] == "legacy_internal"
    assert turns[0]["metadata"]["production_runtime_host_used"] is False


class RecordingRuntimeHost(SentinelRuntimeHost):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.start_count = 0
        self.shutdown_count = 0
        self.pump_calls: list[str] = []

    def start(self):  # noqa: ANN201
        self.start_count += 1
        return super().start()

    def shutdown(self):  # noqa: ANN201
        self.shutdown_count += 1
        return super().shutdown()

    def pump_daemon_once(self, mission_id: str):  # noqa: ANN201
        self.pump_calls.append(mission_id)
        return super().pump_daemon_once(mission_id)


class FailingPumpRuntimeHost(RecordingRuntimeHost):
    def pump_daemon_once(self, mission_id: str):  # noqa: ANN201
        self.pump_calls.append(mission_id)
        raise MissionDaemonRuntimeError("synthetic daemon pickup failure")


class StartFailingRuntimeHost(RecordingRuntimeHost):
    def start(self):  # noqa: ANN201
        self.start_count += 1
        raise RuntimeError("synthetic start failure")


def _recording_host_factory(hosts: list[RecordingRuntimeHost]):
    def factory(**kwargs: Any) -> RecordingRuntimeHost:
        host = RecordingRuntimeHost(**kwargs)
        hosts.append(host)
        return host

    return factory


def _failing_pump_host_factory(hosts: list[FailingPumpRuntimeHost]):
    def factory(**kwargs: Any) -> FailingPumpRuntimeHost:
        host = FailingPumpRuntimeHost(**kwargs)
        hosts.append(host)
        return host

    return factory


def _start_failing_host_factory(hosts: list[StartFailingRuntimeHost]):
    def factory(**kwargs: Any) -> StartFailingRuntimeHost:
        host = StartFailingRuntimeHost(**kwargs)
        hosts.append(host)
        return host

    return factory


def _raise_cockpit_failure(self, text: str):  # noqa: ANN001
    raise RuntimeError("synthetic cockpit failure")


def _write_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "script.txt"
    script_path.write_text("Je veux lancer un business\noui commence\n", encoding="utf-8")
    return script_path


def _write_approval_scope(tmp_path: Path) -> Path:
    scope_path = tmp_path / "approval-scope.json"
    scope_path.write_text(json.dumps(_approval_scope_payload()), encoding="utf-8")
    return scope_path


def _approval_scope_payload() -> dict[str, object]:
    return {
        "user_id": "operator_user",
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["read_only_observation"],
        "allowed_actions": ["research", "draft"],
        "forbidden_actions": ["payment", "send_email", "credential_access", "shell", "write_file"],
        "allowed_paths": ["."],
        "allowed_domains": [],
        "allowed_accounts": [],
        "allowed_data_types": [],
        "browser_v3_authority_grants": [],
        "credential_grants": [],
        "max_duration_minutes": 15,
        "max_actions": 4,
        "max_cost_usd": 0.0,
    }
