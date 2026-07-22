from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.browser_environment_state import BrowserEnvironmentStateBuilder
from sentinel.operator.real_browser_control_runtime import RealBrowserEngineElement, RealBrowserEngineSnapshot
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_operational_snapshot_uses_unknown_for_unobserved_url_and_stable_fingerprint() -> None:
    snapshot = _snapshot()
    first = BrowserEnvironmentStateBuilder().build(
        snapshot=snapshot,
        mission_objective="Find official docs for pathlib Path.glob.",
        origin_hash=stable_hash("https://docs.example"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        available_actions=("real_browser_control.real_browser.observe", "real_browser_control.real_browser.search"),
        session_lease_status="ACTIVE",
    )
    second = BrowserEnvironmentStateBuilder().build(
        snapshot=snapshot,
        mission_objective="Find official docs for pathlib Path.glob.",
        origin_hash=stable_hash("https://docs.example"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        available_actions=("real_browser_control.real_browser.observe", "real_browser_control.real_browser.search"),
        session_lease_status="ACTIVE",
    )

    operational = first.operational_snapshot
    fields = operational["fields"]

    assert operational["schema_version"] == "browser_operational_snapshot_v1"
    assert operational["fingerprint"] == second.operational_snapshot["fingerprint"]
    assert fields["current_url"]["value"]["url"] == "unknown"
    assert fields["current_url"]["value"]["origin_hash"]
    assert fields["page_title"]["value"]["safe_title"] == "Python Docs"
    assert fields["session_lease_status"]["value"] == "ACTIVE"
    assert fields["page_body_available"]["value"]["page_available"] is True
    for field in fields.values():
        assert set(field) >= {"value", "confidence", "evidence_refs", "freshness", "source", "uncertainty_reason"}


def test_operational_snapshot_fingerprint_changes_only_for_operational_state() -> None:
    base_kwargs: dict[str, Any] = {
        "mission_objective": "Find docs.",
        "origin_hash": stable_hash("https://docs.example"),
        "selected_backend_id": "cloak_browser",
        "actual_backend_id": "cloak_browser",
        "session_backend_kind": "cloakbrowser",
        "available_actions": ("real_browser_control.real_browser.observe",),
        "session_lease_status": "ACTIVE",
    }
    first = BrowserEnvironmentStateBuilder().build(snapshot=_snapshot(), **base_kwargs)
    same = BrowserEnvironmentStateBuilder().build(snapshot=_snapshot(), **base_kwargs)
    changed = BrowserEnvironmentStateBuilder().build(
        snapshot=RealBrowserEngineSnapshot(page_title="Python Docs", state_hash="state_changed", elements=_snapshot().elements),
        **base_kwargs,
    )

    assert first.state_id != same.state_id
    assert first.operational_snapshot["fingerprint"] == same.operational_snapshot["fingerprint"]
    assert first.operational_snapshot["fingerprint"] != changed.operational_snapshot["fingerprint"]


def test_operational_snapshot_announces_only_currently_executable_affordances() -> None:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=_snapshot_without_search(),
        mission_objective="Find docs.",
        origin_hash=stable_hash("https://docs.example"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        available_actions=(
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_evidence",
            "sentinel_loop.finish",
        ),
        session_lease_status="ACTIVE",
    )

    affordances = state.operational_snapshot["fields"]["currently_executable_affordances"]["value"]
    skill_names = [item["skill"] for item in affordances]

    assert "observe" in skill_names
    assert "extract_evidence" in skill_names
    assert "search" not in skill_names
    assert "finish" not in skill_names


def test_operational_snapshot_announces_finish_only_when_proof_lane_is_eligible() -> None:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=_snapshot(),
        mission_objective="Find docs.",
        origin_hash=stable_hash("https://docs.example"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        available_actions=("sentinel_loop.finish",),
        session_lease_status="ACTIVE",
        mission_progress={
            "objective_satisfied": True,
            "verified_evidence_present": True,
            "summary_present": True,
            "finish_eligible": True,
        },
    )

    affordances = state.operational_snapshot["fields"]["currently_executable_affordances"]["value"]

    assert [item["skill"] for item in affordances] == ["finish"]


def test_operational_snapshot_records_recoverable_error_without_raw_material() -> None:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=_snapshot(),
        mission_objective="Find docs.",
        origin_hash=stable_hash("https://docs.example"),
        selected_backend_id="cloak_browser",
        actual_backend_id="cloak_browser",
        session_backend_kind="cloakbrowser",
        available_actions=("real_browser_control.real_browser.observe",),
        session_lease_status="DEGRADED",
        recoverable_error={
            "failure_code": "BODY_SESSION_UNAVAILABLE",
            "failure_stage": "session_lifecycle",
            "raw_path": "C:/Users/example/raw/profile",
            "cookie": "raw-cookie-value",
        },
    )

    serialized = str(state.safe_model_dump())

    assert state.operational_snapshot["fields"]["recoverable_error"]["value"]["failure_code"] == "BODY_SESSION_UNAVAILABLE"
    assert state.operational_snapshot["fields"]["session_lease_status"]["value"] == "DEGRADED"
    assert "C:/Users/example" not in serialized
    assert "raw-cookie-value" not in serialized


def test_product_context_exposes_operational_snapshot_to_model(tmp_path: Path) -> None:
    client = _CapturingBrowserDecisionClient(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "pathlib glob docs", "engine_profile": "fake_product_search"},
            idempotency_key="operational-snapshot:search",
        )
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_operational_snapshot",
        mission_objective="Find official docs for pathlib Path.glob.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=2,
        max_material_actions=3,
    )

    assert len(client.contexts) >= 2
    frame = client.contexts[1]["browser_cognitive_decision_frame"]

    assert frame["operational_snapshot"]["schema_version"] == "browser_operational_snapshot_v1"
    assert frame["operational_snapshot"]["fingerprint"]
    assert frame["currently_executable_affordances"]
    assert frame["currently_executable_affordances"][0]["dispatch_contract"] == "ProductActionKernel"
    assert frame["currently_executable_affordances"][0]["typed_input_contract"]
    assert frame["currently_executable_affordances"][0]["normalized_result_contract"]


class _CapturingBrowserDecisionClient:
    def __init__(self, action: ActionEnvelope) -> None:
        self.action = action
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        if len(self.contexts) == 1:
            return self.action
        return ActionEnvelope(
            capability_id="sentinel_loop",
            operation="finish",
            params={"safe_summary": "Stop after operational state capture."},
            idempotency_key="operational-snapshot:finish",
        )


def _snapshot() -> RealBrowserEngineSnapshot:
    return RealBrowserEngineSnapshot(
        page_title="Python Docs",
        state_hash="state_docs",
        elements=(
            RealBrowserEngineElement(ref="search:box", role="searchbox", name="Search", text_preview="Search docs"),
            RealBrowserEngineElement(ref="link:pathlib", role="link", name="pathlib Path.glob", text_preview="Path.glob docs"),
        ),
    )


def _snapshot_without_search() -> RealBrowserEngineSnapshot:
    return RealBrowserEngineSnapshot(
        page_title="Python Docs",
        state_hash="state_docs_no_search",
        elements=(
            RealBrowserEngineElement(ref="link:pathlib", role="link", name="pathlib Path.glob", text_preview="Path.glob docs"),
        ),
    )
