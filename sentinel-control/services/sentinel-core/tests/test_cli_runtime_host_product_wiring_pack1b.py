from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
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
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--deterministic-test-mode",
            "--authority-scope",
            str(scope_path),
            "--workspace",
            str(workspace),
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

    assert state.state is MissionExecutionRequestState.COMPLETED
    assert request.workspace_ref == f"workspace:{workspace.resolve()}"
    assert queue_record.status is DaemonQueueStatus.RUNNING
    assert active.allowed_systems == ["local_workspace"]
    assert active.allowed_tools == ["read_only_observation"]
    assert active.allowed_actions == ["list_directory", "read_file_segment", "search_text", "finish_exploration"]
    assert active.allowed_paths == ["."]
    assert active.max_actions == 4
    assert events.index("mission_authority_envelope_issued") < events.index("mission_execution_request_prepared")
    assert events.index("mission_execution_request_prepared") < events.index("mission_queued")
    assert "mission_execution_request_claimed" in events
    assert "mission_dispatch_decision_persisted" in events
    assert "mission_dispatch_closeout_persisted" in events
    assert turns[-1]["metadata"]["internal_access_classification"] == "production_route"
    assert turns[-1]["metadata"]["runtime_host_lifecycle_ref"] == f"lifecycle:{id(host.lifecycle)}"
    assert turns[-1]["metadata"]["daemon_pickup"]["claimed"] is True
    assert turns[-1]["metadata"]["daemon_pickup"]["dispatch_status"] == "completed"
    assert turns[-1]["metadata"]["daemon_pickup"]["dispatch_adapter_id"] == "read_only_research_adapter"


def test_cli_llm_product_route_wires_same_model_contract_into_pack3_execution_clients(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Research target\ncommand registry lives here\n", encoding="utf-8")
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text("Understand this repo\noui commence\n", encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, workspace))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    output = capsys.readouterr()
    turns = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert len(model_clients) == 1
    client = model_clients[0]
    lanes = [call.request_metadata.get("read_only_lane") for call in client.calls]
    assert lanes == [None, "exploration_decision", "exploration_decision", "final_report"]
    assert {call.user_model_contract_id for call in client.calls} == {_model_contract().id}
    assert client.decision_calls == 2
    assert client.report_calls == 1
    assert turns[-1]["metadata"]["daemon_pickup"]["dispatch_status"] == "completed"
    run_root = tmp_path / "runs"
    mission_id = turns[-1]["mission_record"]["mission_id"]
    request_file = next(run_root.rglob("mission_exec_req_*.json"))
    request_payload = json.loads(request_file.read_text(encoding="utf-8"))
    assert request_payload["workspace_ref"] == f"workspace:{workspace.resolve()}"
    assert request_payload["model_contract_ref"].startswith(
        "model_contract:unit_provider:unit_backend:unit/read-only-model:"
    )
    assert request_payload["model_contract_ref"] != "model_contract:operator_session"
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((run_root / "missions" / mission_id).rglob("*.json"))
    )
    assert "RAW_PROVIDER_WRAPPER_SHOULD_NOT_PERSIST" not in persisted
    assert "RAW_REASONING_SHOULD_NOT_PERSIST" not in persisted


def test_cli_explicit_bootstrap_creates_mission_without_cockpit_provider_call(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Research target\ncommand registry lives here\n", encoding="utf-8")
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = _write_explicit_bootstrap_script(tmp_path)
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, workspace))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--explicit-mission-bootstrap",
            "--json",
        ]
    )

    output = capsys.readouterr()
    turns = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert len(model_clients) == 1
    client = model_clients[0]
    lanes = [call.request_metadata.get("read_only_lane") for call in client.calls]
    assert lanes == ["exploration_decision", "exploration_decision", "final_report"]
    assert "read_only_research_decision_v1" in client.calls[0].prompt_text_in_memory_only
    assert client.decision_calls == 2
    assert client.report_calls == 1
    assert turns[0]["metadata"]["conversation_outcome"] == "explicit_bootstrap_draft_created"
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_dispatched"
    assert turns[-1]["metadata"]["daemon_pickup"]["dispatch_status"] == "completed"

    mission_id = turns[-1]["mission_record"]["mission_id"]
    request_payload = json.loads(next((tmp_path / "runs").rglob("mission_exec_req_*.json")).read_text(encoding="utf-8"))
    assert request_payload["capability_id"] == "read_only_research"
    assert request_payload["operation"] == "inspect_repository"
    assert request_payload["workspace_ref"] == f"workspace:{workspace.resolve()}"
    assert request_payload["model_contract_ref"].startswith(
        "model_contract:unit_provider:unit_backend:unit/read-only-model:"
    )
    assert request_payload["workspace_ref"] != "snapshot:operator_session"
    assert request_payload["model_contract_ref"] != "model_contract:operator_session"

    authority = turns[-1]["mission_record"]["authority_summary"]
    assert authority["allowed_actions"] == ["list_directory", "read_file_segment", "search_text", "finish_exploration"]
    assert "write_file" in authority["forbidden_actions"]
    assert authority["metadata"]["bootstrap_protocol"] == "explicit_product_mission_bootstrap_v1"


@pytest.mark.parametrize(
    ("argv_remove", "expected_reason"),
    [
        ("--workspace", "explicit_bootstrap_requires_workspace"),
        ("--authority-scope", "explicit_bootstrap_requires_authority_scope"),
        ("--model-contract", "explicit_bootstrap_requires_model_contract"),
    ],
)
def test_cli_explicit_bootstrap_requires_product_bindings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    argv_remove: str,
    expected_reason: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, workspace))
    argv = [
        "cockpit",
        "--run-root",
        str(tmp_path / "runs"),
        "--model-contract",
        str(contract_path),
        "--authority-scope",
        str(_write_approval_scope(tmp_path)),
        "--workspace",
        str(workspace),
        "--script",
        str(_write_explicit_bootstrap_script(tmp_path)),
        "--explicit-mission-bootstrap",
        "--json",
    ]
    index = argv.index(argv_remove)
    del argv[index : index + 2]

    code = cli.main(argv)

    turns = json.loads(capsys.readouterr().out)
    assert code == 2
    assert turns[-1]["metadata"]["blocked_reason"] == expected_reason
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created"
    assert model_clients == []
    assert not (tmp_path / "runs" / "missions").exists()


@pytest.mark.parametrize(
    ("script_text", "expected_reason"),
    [
        ("Understand this repository deeply.\n", "explicit_bootstrap_requires_two_script_turns"),
        ("Understand this repository deeply.\nmaybe later\n", "explicit_bootstrap_approval_missing_or_ambiguous"),
    ],
)
def test_cli_explicit_bootstrap_requires_exact_script_and_ascii_start(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    script_text: str,
    expected_reason: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text(script_text, encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, workspace))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--explicit-mission-bootstrap",
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    expected_code = 0 if expected_reason == "explicit_bootstrap_approval_missing_or_ambiguous" else 2
    assert code == expected_code
    assert turns[-1]["metadata"]["blocked_reason"] == expected_reason
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created_approval_missing"
    assert model_clients == [] or model_clients[0].calls == []
    assert not (tmp_path / "runs" / "missions").exists()


def test_cli_llm_product_route_requires_v2_mission_understanding_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text("Understand this repository deeply.\noui commence\n", encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(
        cli,
        "OperatorCatalogModelClient",
        _product_model_client_factory(model_clients, workspace, cockpit_output={}),
    )

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    output = capsys.readouterr()
    turns = json.loads(output.out)
    diagnostic_turn = next(
        turn for turn in turns if "structured_output_diagnostics" in turn.get("metadata", {})
    )
    diagnostics = diagnostic_turn["metadata"]["structured_output_diagnostics"]
    assert code == 0
    assert output.err == ""
    assert len(model_clients) == 1
    assert len(model_clients[0].calls) == 1
    assert diagnostics["protocol_version"] == "cockpit_mission_understanding_v2"
    assert diagnostics["parse_stage"] == "mission_understanding_v2_validation"
    assert "protocol_version" in diagnostics["missing_required_field_names"]
    assert "kind" in diagnostics["missing_required_field_names"]
    assert "reply" in diagnostics["missing_required_field_names"]
    assert diagnostics["top_level_key_names"] == []
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created"
    assert "legacy_operator_decision_validation" not in json.dumps(turns, sort_keys=True)
    assert not (tmp_path / "runs" / "missions").exists()


def test_cli_llm_product_route_v2_failure_diagnostics_include_extraction_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text("Understand this repository deeply.\noui commence\n", encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(
        cli,
        "OperatorCatalogModelClient",
        _product_model_client_factory(
            model_clients,
            workspace,
            cockpit_output={
                "raw_text_hash": "unit_hash",
                "visible_content_char_count": 0,
                "content_extraction_source": "choices[0].message.content",
                "normalization_strategy": "empty_visible_content",
                "finish_reason": "stop",
                "output_truncated": False,
            },
        ),
    )

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    diagnostics = next(
        turn["metadata"]["structured_output_diagnostics"]
        for turn in turns
        if "structured_output_diagnostics" in turn.get("metadata", {})
    )
    rendered = json.dumps(diagnostics, sort_keys=True)
    assert code == 0
    assert diagnostics["parse_stage"] == "mission_understanding_v2_validation"
    assert diagnostics["content_extraction_source"] == "choices[0].message.content"
    assert diagnostics["normalization_strategy"] == "empty_visible_content"
    assert diagnostics["visible_content_length"] == 0
    assert diagnostics["finish_reason"] == "stop"
    assert diagnostics["output_truncated"] is False
    assert "raw_text_hash" not in rendered
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created"


def test_cli_llm_product_route_rejects_model_supplied_bindings_with_v2_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text("Understand this repository deeply.\noui commence\n", encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(
        cli,
        "OperatorCatalogModelClient",
        _product_model_client_factory(
            model_clients,
            workspace,
            cockpit_output={
                "protocol_version": "cockpit_mission_understanding_v2",
                "kind": "draft_mission",
                "reply": "Mission draft ready.",
                "title": "Repository architecture research",
                "objective": "Map repository packages.",
                "requested_capability": "read_only_research",
                "workspace_ref": f"workspace:{workspace}",
                "model_contract_ref": "model_contract:model_supplied",
                "approval_scope": {"allowed_actions": ["write_file"]},
                "can_execute": True,
            },
        ),
    )

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    diagnostic_turn = next(
        turn for turn in turns if "structured_output_diagnostics" in turn.get("metadata", {})
    )
    diagnostics = diagnostic_turn["metadata"]["structured_output_diagnostics"]
    assert code == 0
    assert len(model_clients) == 1
    assert len(model_clients[0].calls) == 1
    assert diagnostics["parse_stage"] == "mission_understanding_v2_validation"
    assert diagnostics["protocol_version"] == "cockpit_mission_understanding_v2"
    assert diagnostics["unknown_field_names"] == [
        "approval_scope",
        "can_execute",
        "model_contract_ref",
        "workspace_ref",
    ]
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created"
    assert not (tmp_path / "runs" / "missions").exists()


def test_cli_llm_product_route_prompt_is_v2_product_protocol(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    script_path = tmp_path / "script.txt"
    script_path.write_text("Understand this repository deeply.\noui commence\n", encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, workspace))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(workspace),
            "--script",
            str(script_path),
            "--json",
        ]
    )

    capsys.readouterr()
    assert code == 0
    first_prompt = model_clients[0].calls[0].prompt_text_in_memory_only
    assert "cockpit_mission_understanding_v2" in first_prompt
    assert "Allowed top-level keys are exactly:" in first_prompt
    assert "Use this minimal JSON skeleton for a read-only research mission:" in first_prompt
    assert "Return exactly one JSON object." in first_prompt
    assert "No Markdown." in first_prompt
    assert "No prose outside JSON." in first_prompt
    assert "No authority." in first_prompt
    assert "No workspace." in first_prompt
    assert "No credentials." in first_prompt
    assert '"kind": "draft_mission"' in first_prompt
    assert '"reply": "Mission draft ready for approval."' in first_prompt
    assert '"requested_capability": "read_only_research"' in first_prompt
    assert "\"required_fields\": [\"protocol_version\", \"kind\", \"reply\"]" in first_prompt
    assert "\"draft_mission_required_fields\": [\"title\", \"objective\", \"requested_capability\"]" in first_prompt
    assert "OperatorLLMDecisionResult" not in first_prompt
    assert "MissionStartProposal" not in first_prompt
    assert "OperatorIntent" not in first_prompt
    assert "MissionDraft" not in first_prompt
    assert "MissionAuthoritySummary" not in first_prompt


def test_cli_llm_product_route_missing_workspace_blocks_before_request_creation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    model_clients: list[RecordingProductModelClient] = []
    monkeypatch.setattr(cli, "OperatorCatalogModelClient", _product_model_client_factory(model_clients, tmp_path))

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--script",
            str(_write_script(tmp_path)),
            "--json",
        ]
    )

    turns = json.loads(capsys.readouterr().out)
    assert code == 0
    assert len(model_clients) == 1
    assert len(model_clients[0].calls) == 1
    assert turns[-1]["metadata"]["blocked_reason"] == "workspace_binding_required"
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created_workspace_missing"
    assert not (tmp_path / "runs" / "missions").exists()


def test_cli_product_workspace_binding_rejects_file_and_outside_scope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract_path = tmp_path / "model-contract.json"
    contract_path.write_text(json.dumps(_model_contract().model_dump(mode="json")), encoding="utf-8")
    missing_workspace = tmp_path / "missing-workspace"

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs-missing"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(missing_workspace),
            "--script",
            str(_write_script(tmp_path)),
            "--json",
        ]
    )
    turns = json.loads(capsys.readouterr().out)
    assert code == 2
    assert turns[-1]["metadata"]["blocked_reason"] == "workspace_not_found"
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created_workspace_missing"

    file_workspace = tmp_path / "not-a-dir.txt"
    file_workspace.write_text("not a workspace", encoding="utf-8")

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs-file"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path)),
            "--workspace",
            str(file_workspace),
            "--script",
            str(_write_script(tmp_path)),
            "--json",
        ]
    )
    turns = json.loads(capsys.readouterr().out)
    assert code == 2
    assert turns[-1]["metadata"]["blocked_reason"] == "workspace_not_directory"
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created_workspace_missing"

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_scope = tmp_path / "outside-scope"
    outside_scope.mkdir()

    code = cli.main(
        [
            "cockpit",
            "--run-root",
            str(tmp_path / "runs-scope"),
            "--model-contract",
            str(contract_path),
            "--authority-scope",
            str(_write_approval_scope(tmp_path, allowed_paths=[str(outside_scope)])),
            "--workspace",
            str(workspace),
            "--script",
            str(_write_script(tmp_path)),
            "--json",
        ]
    )
    turns = json.loads(capsys.readouterr().out)
    assert code == 2
    assert turns[-1]["metadata"]["blocked_reason"] == "workspace_outside_approved_scope"
    assert turns[-1]["metadata"]["conversation_outcome"] == "mission_not_created_workspace_outside_scope"


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


def _write_explicit_bootstrap_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "explicit-bootstrap-script.txt"
    script_path.write_text(
        (
            "Understand this repository deeply. Map its major packages and responsibilities. "
            "Trace how commands are declared, registered, parsed and executed. Identify at least one "
            "high-impact architectural risk, defect or maintainability gap. Produce an evidence-linked "
            "technical report with prioritized engineering recommendations. Use governed read-only research only.\n"
            "start\n"
        ),
        encoding="utf-8",
    )
    return script_path


def _write_approval_scope(tmp_path: Path, *, allowed_paths: list[str] | None = None) -> Path:
    scope_path = tmp_path / "approval-scope.json"
    scope_path.write_text(json.dumps(_approval_scope_payload(allowed_paths=allowed_paths)), encoding="utf-8")
    return scope_path


def _model_contract() -> UserModelContract:
    model = "unit/read-only-model"
    return UserModelContract(
        id="umodel_pack3_cli",
        selected_provider_id="unit_provider",
        selected_backend_id="unit_backend",
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=32_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="pack3_product_wiring",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


class RecordingProductModelClient:
    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        workspace: Path,
        cockpit_output: dict[str, object] | None = None,
    ) -> None:
        self.contract = user_model_contract
        self.workspace = workspace
        self.cockpit_output = cockpit_output
        self.calls = []
        self.decision_calls = 0
        self.report_calls = 0

    def complete(self, request):  # noqa: ANN001, ANN201
        self.calls.append(request)
        lane = request.request_metadata.get("read_only_lane")
        if lane == "exploration_decision":
            self.decision_calls += 1
            if self.decision_calls == 1:
                return {
                    "action": "list_directory",
                    "arguments": {"path": "."},
                    "evidence_refs": [],
                    "raw_provider_response": "RAW_PROVIDER_WRAPPER_SHOULD_NOT_PERSIST",
                    "reasoning_content": "RAW_REASONING_SHOULD_NOT_PERSIST",
                }
            return {
                "action": "finish_exploration",
                "arguments": {},
                "evidence_refs": [],
                "raw_provider_response": "RAW_PROVIDER_WRAPPER_SHOULD_NOT_PERSIST",
                "reasoning_content": "RAW_REASONING_SHOULD_NOT_PERSIST",
            }
        if lane == "final_report":
            self.report_calls += 1
            evidence_refs = list(request.request_metadata["evidence_refs"])
            return {
                "report_text": f"Report cites {', '.join(evidence_refs)}: repository overview completed.",
                "evidence_refs": evidence_refs,
                "raw_provider_response": "RAW_PROVIDER_WRAPPER_SHOULD_NOT_PERSIST",
                "reasoning_content": "RAW_REASONING_SHOULD_NOT_PERSIST",
            }
        if self.cockpit_output is not None:
            return dict(self.cockpit_output)
        return {
            "protocol_version": "cockpit_mission_understanding_v2",
            "kind": "draft_mission",
            "reply": "Mission draft ready.",
            "title": "Read-only product mission",
            "objective": "Inspect the repository and produce an evidence-linked report.",
            "constraints": ["read-only"],
            "expected_artifacts": ["evidence-linked report"],
            "requested_capability": "read_only_research",
            "clarification_questions": [],
        }


def _product_model_client_factory(
    model_clients: list[RecordingProductModelClient],
    workspace: Path,
    *,
    cockpit_output: dict[str, object] | None = None,
):
    def factory(*, user_model_contract: UserModelContract, **_kwargs) -> RecordingProductModelClient:  # noqa: ANN001
        client = RecordingProductModelClient(
            user_model_contract=user_model_contract,
            workspace=workspace,
            cockpit_output=cockpit_output,
        )
        model_clients.append(client)
        return client

    return factory


def _approval_scope_payload(*, allowed_paths: list[str] | None = None) -> dict[str, object]:
    return {
        "user_id": "operator_user",
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["read_only_observation"],
        "allowed_actions": ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        "forbidden_actions": ["payment", "send_email", "credential_access", "shell", "write_file"],
        "allowed_paths": allowed_paths or ["."],
        "allowed_domains": [],
        "allowed_accounts": [],
        "allowed_data_types": [],
        "browser_v3_authority_grants": [],
        "credential_grants": [],
        "max_duration_minutes": 15,
        "max_actions": 4,
        "max_cost_usd": 0.0,
    }
