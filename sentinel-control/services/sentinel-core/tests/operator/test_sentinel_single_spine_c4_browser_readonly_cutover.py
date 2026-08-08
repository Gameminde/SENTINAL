from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
from sentinel.operator.canonical_core import (
    RootMissionCancellationToken,
    build_workspace_browser_readonly_capability_graph,
    run_canonical_product_mission,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus


class ScriptedModelClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("scripted model decision exhausted")
        return self._decisions.pop(0)


def test_browser_readonly_route_uses_single_spine_and_returns_state_next_turn(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    backend = FakeBrowserReadOnlyBackend(
        allowed_origins=("sqlite.org",),
        page_title="SQLite Generated Columns",
        evidence_cards=(
            {
                "evidence_id": "sqlite_generated_columns_doc",
                "kind": "documentation_page",
                "title": "Generated Columns",
                "summary": "SQLite generated columns are computed from expressions.",
                "confidence": 0.92,
            },
        ),
    )
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
            {"capability": "real_browser_control", "operation": "real_browser.extract_evidence", "arguments": {}},
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite generated columns are computed from expressions."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Find official SQLite documentation about generated columns.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c4_browser_single_spine",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    second_turn_state = model.requests[1].canonical_state.safe_model_dump()

    assert result.status == "completed"
    assert result.provider_decision_count == 3
    assert result.material_action_count == 2
    assert [receipt.capability for receipt in result.receipts] == [
        "real_browser_control",
        "real_browser_control",
    ]
    assert [receipt.operation for receipt in result.receipts] == [
        "real_browser.observe",
        "real_browser.extract_evidence",
    ]
    assert all(receipt.material_action is False for receipt in result.receipts)
    assert record.status is OperatorMissionStatus.COMPLETED
    assert record.receipt_refs == [receipt.receipt_id for receipt in result.receipts]
    assert result.proof_root.receipt_refs == tuple(record.receipt_refs)
    assert result.proof_root.receipt_artifacts_verified is True
    assert second_turn_state["browser_environment_state"]["browser"]["selected_backend_id"] == "fake_browser_readonly"
    assert second_turn_state["browser_environment_state"]["page"]["title"] == "SQLite Generated Columns"
    assert second_turn_state["browser_environment_state"]["affordance_graph"]["available"] >= [
        "real_browser.observe",
        "real_browser.extract_evidence",
    ]
    assert model.requests[0].canonical_state.model_visible_affordances.count("real_browser_control.real_browser.observe") == 1
    assert backend.call_log == ["real_browser.observe", "real_browser.extract_evidence"]
    assert backend.provider_calls == 0
    assert backend.real_browser_runs == 0
    assert backend.external_network_calls == 0
    assert backend.cleanup_count == 1
    assert any(event.event_type == "canonical_browser_readonly_cleanup_completed" for event in events)


def test_browser_authority_denial_blocks_before_backend_call(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",))
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Observe a public page.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c4_browser_denial",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_authority_required:browser_read"
    assert backend.call_log == []
    assert result.receipts == ()


def test_browser_unknown_mutating_capability_is_quarantined_and_never_simulated(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",))
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.type_text", "arguments": {"ref": "input:q"}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Try a mutating browser operation.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=MissionKernel(run_root=tmp_path / "runs"),
        session_id="c4_browser_mutation_quarantine",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "CAPABILITY_QUARANTINED"
    assert result.blocked_capability == "real_browser_control.real_browser.type_text"
    assert backend.call_log == []


def test_browser_follow_link_cannot_activate_button_or_cross_origin(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    graph = build_workspace_browser_readonly_capability_graph()
    backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",))
    button_model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.open_result", "arguments": {"ref": "button:delete"}},
        ]
    )
    cross_origin_model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"target_origin": "evil.example"},
            },
        ]
    )

    button_result = run_canonical_product_mission(
        objective="Follow a link only.",
        workspace_root=workspace,
        model_client=button_model,
        provider_model="scripted-local/model",
        kernel=MissionKernel(run_root=tmp_path / "runs_button"),
        session_id="c4_browser_button_block",
        capability_graph=graph,
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )
    cross_origin_result = run_canonical_product_mission(
        objective="Navigate within an allowed origin only.",
        workspace_root=workspace,
        model_client=cross_origin_model,
        provider_model="scripted-local/model",
        kernel=MissionKernel(run_root=tmp_path / "runs_cross_origin"),
        session_id="c4_browser_cross_origin_block",
        capability_graph=graph,
        browser_readonly_backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert button_result.status == "blocked"
    assert button_result.blocked_reason_detail == "browser_follow_ref_not_link"
    assert backend.call_log == []
    assert cross_origin_result.status == "blocked"
    assert cross_origin_result.blocked_reason_detail == "browser_origin_transition_not_authorized"


def test_browser_cancellation_during_fake_effect_terminalizes_and_cleans_once(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    token = RootMissionCancellationToken()
    backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",), cancel_during_next_call=token)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
            {"capability": "real_browser_control", "operation": "real_browser.extract_evidence", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Cancellation should stop the browser route.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=MissionKernel(run_root=tmp_path / "runs"),
        session_id="c4_browser_cancel",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        cancellation_token=token,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "root_mission_cancelled_during_browser_effect"
    assert len(model.requests) == 1
    assert backend.call_log == ["real_browser.observe"]
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert result.cleanup_completed is True


def test_browser_fake_backend_cannot_create_material_success(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",), material_action_override=True)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Fake browser must not certify material browser power.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=MissionKernel(run_root=tmp_path / "runs"),
        session_id="c4_browser_fake_material",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert result.blocked_reason_detail == "canonical_simulated_backend_cannot_create_material_receipt"
    assert result.receipts == ()


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text("local fixture only\n", encoding="utf-8")
    return workspace
