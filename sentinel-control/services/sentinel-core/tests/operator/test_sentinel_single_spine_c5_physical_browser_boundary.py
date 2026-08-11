from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.canonical_browser_readonly_adapter import PhysicalBrowserReadOnlyBackend
from sentinel.operator.canonical_core import (
    RootMissionCancellationToken,
    build_workspace_browser_readonly_capability_graph,
    run_canonical_product_mission,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.real_browser_control_runtime import (
    BOUNDED_URL_AUTHORITY_REF,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
    SENTINEL_CHROMIUM_BACKEND_ID,
    build_canonical_real_browser_engine_from_env,
)


class ScriptedModelClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("scripted model decision exhausted")
        return self._decisions.pop(0)


class InstrumentedSentinelChromiumReadOnlyEngine:
    browser_backend_id = SENTINEL_CHROMIUM_BACKEND_ID
    session_manager_backend_kind = "sentinel_chromium"

    def __init__(self) -> None:
        self.open_count = 0
        self.observe_count = 0
        self.click_count = 0
        self.type_count = 0
        self.assert_count = 0
        self.select_count = 0
        self.extract_count = 0
        self.press_count = 0
        self.wait_count = 0
        self.scroll_count = 0
        self.close_count = 0
        self.bound_authority: Any | None = None
        self.bound_root_session_id = ""
        self.closed = False

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash({"scheme": "https", "host": "sqlite.org", "port": None})

    def bind_authority(self, authority: Any) -> None:
        self.bound_authority = authority

    def bind_root_session_id(self, root_session_id: str) -> None:
        self.bound_root_session_id = root_session_id

    def open(self) -> RealBrowserEngineSnapshot:
        self.open_count += 1
        self.closed = False
        return self._snapshot("open")

    def observe(self) -> RealBrowserEngineSnapshot:
        self.observe_count += 1
        return self._snapshot("observe")

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self.extract_count += 1
        return (
            "SQLite generated columns are columns whose values are computed from expressions.",
            self._snapshot("extract"),
        )

    def close(self) -> None:
        self.close_count += 1
        self.closed = True

    def _snapshot(self, stage: str) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title="SQLite Generated Columns",
            state_hash=stable_hash({"stage": stage, "open_count": self.open_count, "extract_count": self.extract_count}),
            elements=(
                RealBrowserEngineElement(
                    ref="link:generated-columns",
                    role="link",
                    name="Generated Columns",
                    text_preview="Generated Columns",
                ),
            ),
        )


class CancellingSentinelChromiumReadOnlyEngine(InstrumentedSentinelChromiumReadOnlyEngine):
    def __init__(self, token: RootMissionCancellationToken) -> None:
        super().__init__()
        self._token = token

    def observe(self) -> RealBrowserEngineSnapshot:
        snapshot = super().observe()
        self._token.cancel("operator_cancelled_during_physical_browser_effect")
        return snapshot


def test_canonical_browser_engine_factory_does_not_require_cloak_configuration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://sqlite.org/gencol.html")
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)
    monkeypatch.delenv("SENTINEL_REQUIRE_CLOAKBROWSER_BINARY_PATH", raising=False)

    engine = build_canonical_real_browser_engine_from_env(capture_root=tmp_path / "capture")

    assert engine.browser_backend_id == SENTINEL_CHROMIUM_BACKEND_ID
    assert engine.session_manager_backend_kind == "sentinel_chromium"


def test_physical_browser_readonly_backend_runs_through_single_spine_with_sovereign_receipts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.open", "arguments": {}},
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
        session_id="c5_physical_browser_single_spine",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    third_turn_state = model.requests[2].canonical_state.safe_model_dump()
    real_browser_receipts = sorted(
        (kernel.store.mission_dir(result.root_mission_id) / "real_browser_control" / "receipts").glob("*.json")
    )
    first_browser_receipt = json.loads(real_browser_receipts[0].read_text(encoding="utf-8"))

    assert result.status == "completed"
    assert result.provider_decision_count == 4
    assert result.material_action_count == 3
    assert record.status is OperatorMissionStatus.COMPLETED
    assert result.proof_root.root_mission_id == record.mission_id
    assert result.proof_root.receipt_refs == tuple(record.receipt_refs)
    assert result.proof_root.receipt_artifacts_verified is True
    assert engine.bound_authority is not None
    assert BOUNDED_URL_AUTHORITY_REF in engine.bound_authority.allowed_domains
    assert "real_browser.open" in engine.bound_authority.allowed_actions
    assert engine.open_count == 1
    assert engine.observe_count >= 1
    assert engine.extract_count == 1
    assert engine.close_count == 1
    assert backend.provider_calls == 0
    assert backend.real_browser_runs == 3
    assert backend.external_network_calls == 0
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert real_browser_receipts
    assert first_browser_receipt["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert first_browser_receipt["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert first_browser_receipt["session_backend_kind"] == "sentinel_chromium"
    assert first_browser_receipt.get("backend_mismatch") is False
    assert all(receipt.capability == "real_browser_control" for receipt in result.receipts)
    assert result.receipts[0].safe_observation["backend_kind"] == "physical"
    assert result.receipts[0].safe_observation["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert result.receipts[0].safe_observation["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert third_turn_state["browser_environment_state"]["browser"]["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert third_turn_state["browser_environment_state"]["browser"]["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert any(event.event_type == "canonical_browser_readonly_cleanup_completed" for event in events)


def test_physical_browser_authority_carries_concrete_backend_origins_to_session_manager(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org", "www.sqlite.org"),
    )
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.open", "arguments": {}},
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "Browser authority includes concrete backend origins."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Open a bounded public browser target.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_concrete_origin_authority",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert engine.bound_authority is not None
    assert BOUNDED_URL_AUTHORITY_REF in engine.bound_authority.allowed_domains
    assert "sqlite.org" in engine.bound_authority.allowed_domains
    assert "www.sqlite.org" in engine.bound_authority.allowed_domains


def test_physical_browser_authority_denial_blocks_before_engine_call(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.open", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Browser read authority must be required before any physical browser effect.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_authority_denial",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_authority_required:browser_read"
    assert engine.open_count == 0
    assert engine.observe_count == 0
    assert backend.real_browser_runs == 0
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert result.cleanup_completed is True


def test_physical_browser_cancellation_after_dispatch_preserves_terminal_receipt_and_cleans_up(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    token = RootMissionCancellationToken()
    engine = CancellingSentinelChromiumReadOnlyEngine(token)
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Cancellation during a physical browser effect must clean up without fabricating completion.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_cancellation",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
        cancellation_token=token,
    )

    real_browser_receipts = sorted(
        (kernel.store.mission_dir(result.root_mission_id) / "real_browser_control" / "receipts").glob("*.json")
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "root_mission_cancelled_during_browser_effect"
    assert engine.observe_count == 1
    assert engine.close_count == 1
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert result.cleanup_completed is True
    assert real_browser_receipts
    assert result.receipts == ()


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text("local fixture only\n", encoding="utf-8")
    return workspace
