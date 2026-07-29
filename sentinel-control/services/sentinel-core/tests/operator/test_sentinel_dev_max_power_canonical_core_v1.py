from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel import cli
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.canonical_core import (
    CanonicalCoreError,
    DecisionOrigin,
    EffectKind,
    RootMissionCancellationToken,
    build_workspace_read_capability_graph,
    run_canonical_dev_mission,
)
from sentinel.operator.code_execution_sandbox_runtime import CodeExecutionSandboxRuntime
from sentinel.operator.kernel import MissionKernel


class ScriptedModelClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("scripted model decision exhausted")
        return self._decisions.pop(0)


class CancellingModelClient:
    def __init__(self, token: RootMissionCancellationToken, decision: dict[str, Any]) -> None:
        self._token = token
        self._decision = decision
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        self._token.cancel("operator_revoked_during_provider_turn")
        return self._decision


def test_stage0_finding_ledger_contains_all_65_findings() -> None:
    ledger_path = (
        Path(__file__).parents[4]
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json"
    )

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert ledger["baseline_commit"] == "efdbd558abddbc38cea7e506ff8cb8dfe8ef93fa"
    assert len(ledger["entries"]) == 65
    assert len({entry["id"] for entry in ledger["entries"]}) == 65
    assert ledger["severity_counts"] == {"P0": 15, "P1": 44, "P2": 6}
    assert ledger["status_counts"] == {"OPEN": 65}


def test_provider_client_required_before_first_cognitive_turn(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(CanonicalCoreError, match="canonical_model_client_required"):
        run_canonical_dev_mission(
            objective="List the workspace.",
            workspace_root=workspace,
            model_client=None,
            provider_model="missing-provider",
        )


def test_root_cancellation_before_provider_call_blocks_without_decision(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    token = RootMissionCancellationToken()
    token.cancel("operator_revoked_before_provider_turn")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="This mission is revoked before the model sees state.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        cancellation_token=token,
    )

    assert result.status == "blocked"
    assert result.final_reason == "ROOT_MISSION_CANCELLED"
    assert result.cancellation_reason == "operator_revoked_before_provider_turn"
    assert result.provider_decision_count == 0
    assert result.material_action_count == 0
    assert result.cleanup_completed is True
    assert model.requests == []


def test_root_cancellation_during_model_turn_prevents_material_action(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    token = RootMissionCancellationToken()
    model = CancellingModelClient(
        token,
        {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
    )

    result = run_canonical_dev_mission(
        objective="This mission is revoked while the model is selecting an action.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        cancellation_token=token,
    )

    assert result.status == "blocked"
    assert result.final_reason == "ROOT_MISSION_CANCELLED"
    assert result.cancellation_reason == "operator_revoked_during_provider_turn"
    assert result.provider_decision_count == 1
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True


def test_root_mission_exists_before_first_model_decision_and_state_is_presented(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
            {"capability": "workspace", "operation": "read", "arguments": {"path": "notes/topic.md"}},
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Observed workspace evidence."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Understand the small workspace from files.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        max_provider_decisions=6,
        max_material_actions=6,
    )

    assert result.status == "completed"
    assert result.cleanup_completed is True
    assert result.root_mission_id.startswith("root_mission_")
    assert result.root_created_before_first_provider_call is True
    assert [request.canonical_state.root_mission_id for request in model.requests] == [
        result.root_mission_id,
        result.root_mission_id,
        result.root_mission_id,
        result.root_mission_id,
    ]
    assert model.requests[0].canonical_state.provider_decision_count == 0
    assert model.requests[0].canonical_state.model_visible_affordances == (
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    )
    assert result.decisions[0].decision_origin is DecisionOrigin.MODEL_SELECTED
    assert result.decisions[0].provider_model == "test-provider/model"


def test_capability_graph_is_generated_from_executable_routes() -> None:
    graph = build_workspace_read_capability_graph()

    assert graph.model_visible_affordances() == (
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    )
    assert graph.resolve("workspace", "list").effect_kind is EffectKind.REAL
    assert graph.resolve("workspace", "read").materiality_verifier == "workspace_path_observed"
    assert graph.resolve("workspace", "search").proof_contract == "canonical_core_workspace_receipt_v1"
    assert graph.resolve("sentinel_loop", "finish").effect_kind is EffectKind.PROPOSAL
    assert len({(route.capability, route.operation) for route in graph.routes}) == len(graph.routes)


def test_product_action_envelope_decision_is_consumed_without_parallel_model_protocol(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            ActionEnvelope(capability_id="workspace", operation="list", params={"path": "."}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"answer": "Listed via product envelope."}),
        ]
    )

    result = run_canonical_dev_mission(
        objective="List the workspace through the normalized product action language.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.status == "completed"
    assert result.decisions[0].selected_capability == "workspace"
    assert result.decisions[0].selected_operation == "list"
    assert result.decisions[0].arguments == {"path": "."}
    assert result.decisions[0].decision_origin is DecisionOrigin.MODEL_SELECTED
    assert result.receipts[0].operation == "list"


def test_workspace_list_read_search_are_generic_not_scenario_choreography(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "src"}},
            {"capability": "workspace", "operation": "read", "arguments": {"path": "src/pkg/module.py"}},
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Needle found in generic tree."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Find where the needle appears.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        max_provider_decisions=6,
        max_material_actions=6,
    )

    assert result.status == "completed"
    assert result.cleanup_completed is True
    assert [receipt.operation for receipt in result.receipts[:3]] == ["list", "read", "search"]
    assert result.receipts[0].safe_observation["entries"] == ("pkg/",)
    assert result.receipts[1].safe_observation["path"] == "src/pkg/module.py"
    assert result.receipts[2].safe_observation["match_count"] == 2
    assert all("app.py" not in receipt.safe_summary for receipt in result.receipts)
    assert all("tests/test_app.py" not in receipt.safe_summary for receipt in result.receipts)


def test_workspace_read_cannot_escape_root(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (tmp_path / "outside.txt").write_text("outside needle must not be read\n", encoding="utf-8")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "read", "arguments": {"path": "../outside.txt"}},
        ]
    )

    with pytest.raises(CanonicalCoreError, match="workspace_path_outside_root"):
        run_canonical_dev_mission(
            objective="Try to read outside the governed workspace.",
            workspace_root=workspace,
            model_client=model,
            provider_model="test-provider/model",
        )


def test_model_payload_cannot_self_grant_authority(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "list",
                "arguments": {"path": "."},
                "authority_effect": "grant_new_authority",
                "can_grant_authority": True,
            },
        ]
    )

    with pytest.raises(ValueError, match="authority effect must remain none"):
        run_canonical_dev_mission(
            objective="Model tries to self-grant authority.",
            workspace_root=workspace,
            model_client=model,
            provider_model="test-provider/model",
        )


def test_stage2_probe_confirms_current_code_exec_is_not_physical_sandbox_and_core_quarantines_it(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside_canary.txt"
    outside.write_text("outside canary readable only when the sandbox is not physical\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "tests" / "test_escape.py").write_text(
        "from pathlib import Path\n\n"
        "def test_can_read_outside_workspace():\n"
        f"    assert Path({str(outside)!r}).read_text(encoding='utf-8').startswith('outside canary')\n",
        encoding="utf-8",
    )
    kernel = MissionKernel(run_root=tmp_path / "runs")
    mission = kernel.create_mission(session_id="session_code_probe", draft=_draft())
    authority = _authority(mission.mission_id, workspace)
    runtime = CodeExecutionSandboxRuntime(
        kernel=kernel,
        mission_id=mission.mission_id,
        workspace_root=workspace,
    )

    result = runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params={"profile_id": "pytest_file", "args": ["tests/test_escape.py"]},
        ),
        authority=authority,
        context={},
    )
    graph = build_workspace_read_capability_graph()

    assert result.status == "passed"
    assert graph.quarantined_capability("code_execution_sandbox", "code_exec.run_profile").reason == (
        "physical_sandbox_not_proven"
    )
    with pytest.raises(CanonicalCoreError, match="canonical_capability_quarantined"):
        graph.resolve("code_execution_sandbox", "code_exec.run_profile")


def test_model_selected_quarantined_code_capability_returns_typed_blocker(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {
                "capability": "code_execution_sandbox",
                "operation": "code_exec.run_profile",
                "arguments": {"profile_id": "pytest_file", "args": ["tests/test_smoke.py"]},
            },
        ]
    )

    result = run_canonical_dev_mission(
        objective="Run code only if the canonical core can prove a physical sandbox.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.status == "blocked"
    assert result.final_reason == "CAPABILITY_QUARANTINED"
    assert result.blocked_capability == "code_execution_sandbox.code_exec.run_profile"
    assert result.blocked_reason_detail == "physical_sandbox_not_proven"
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True


def test_initial_proof_root_is_explicitly_non_authentic_placeholder(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Listed workspace."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="List the workspace.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.proof_root.integrity_model == "non_authentic_placeholder"
    assert result.proof_root.authentic_external_ledger is False
    assert result.proof_root.receipt_refs == tuple(receipt.receipt_id for receipt in result.receipts)
    assert result.proof_root.proof_gaps == ("external_append_only_signer_missing",)


def test_public_dev_cli_entrypoint_runs_canonical_core_vertical_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "list", "arguments": {"path": "."}}),
                json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "CLI slice done."}}),
            ]
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "canonical-dev-run",
            "--objective",
            "Exercise the canonical core from the public dev CLI.",
            "--workspace",
            str(workspace),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-local/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert payload["status"] == "completed"
    assert payload["provider_decision_count"] == 2
    assert payload["root_created_before_first_provider_call"] is True
    assert payload["cleanup_completed"] is True
    assert payload["receipts"][0]["capability"] == "workspace"
    assert payload["proof_root"]["integrity_model"] == "non_authentic_placeholder"


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "src" / "pkg").mkdir(parents=True)
    (workspace / "notes").mkdir()
    (workspace / "src" / "pkg" / "module.py").write_text(
        "VALUE = 'needle from module'\n",
        encoding="utf-8",
    )
    (workspace / "notes" / "topic.md").write_text(
        "# Topic\n\nThe needle also appears in notes.\n",
        encoding="utf-8",
    )
    return workspace


def _draft():
    from sentinel.operator.models import MissionDraft

    return MissionDraft(
        title="Canonical core code sandbox boundary probe",
        objective="Probe whether code execution is physically confined.",
        constraints=["temporary canary only"],
        expected_artifacts=["typed probe result"],
    )


def _authority(mission_id: str, workspace: Path) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Canonical core code sandbox boundary probe",
        mission_objective="Probe whether code execution is physically confined.",
        allowed_tools=["code_execution_sandbox"],
        allowed_actions=["code_exec.run_profile"],
        forbidden_actions=["network", "credential_access", "package_install"],
        allowed_paths=[str(workspace)],
        max_actions=2,
        created_at=now,
        expires_at=now.replace(year=now.year + 1),
    )
