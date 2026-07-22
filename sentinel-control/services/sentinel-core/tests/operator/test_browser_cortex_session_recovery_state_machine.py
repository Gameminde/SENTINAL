from __future__ import annotations

from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.model_led_product_action_kernel_task_loop import ProductActionKernelLoopDecisionClient
from sentinel.operator.real_browser_control_runtime import RealBrowserControlRuntimeError
from sentinel.operator.runtime_host import ProductTaskBrowserRuntimeLease, SentinelRuntimeHost


def test_browser_lease_state_machine_records_reconnect_after_degradation(monkeypatch, tmp_path: Path) -> None:
    engines: list[_ClosableEngine] = []

    def fake_factory(envelope: ActionEnvelope) -> _ClosableEngine:
        del envelope
        engine = _ClosableEngine()
        engines.append(engine)
        return engine

    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", fake_factory)
    lease = ProductTaskBrowserRuntimeLease(
        root_scope_id="scope_session_reconnect",
        root_session_id="session_reconnect",
        workspace_root=tmp_path,
    )
    envelope = _envelope()

    first = lease.engine_for(envelope)
    degraded = lease.mark_degraded(failure_code="browser_session_missing_or_closed")
    recovered = lease.recover_engine_once(envelope)
    card = lease.safe_model_dump()

    assert first is engines[0]
    assert degraded is True
    assert recovered is True
    assert card["browser_session_state"] == "RECONNECTED"
    assert card["lifecycle_state"] == "active_after_recovery"
    assert card["previous_browser_session_state"] == "RECOVERING"
    assert card["browser_session_state_history"][-3:] == ("DEGRADED", "RECOVERING", "RECONNECTED")
    assert card["open_count"] == 2
    assert card["close_count"] == 1
    assert engines[0].close_count == 1


def test_browser_lease_state_machine_blocks_after_recovery_exhaustion(monkeypatch, tmp_path: Path) -> None:
    def fake_factory(envelope: ActionEnvelope) -> _ClosableEngine:
        del envelope
        return _ClosableEngine()

    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", fake_factory)
    lease = ProductTaskBrowserRuntimeLease(
        root_scope_id="scope_session_blocked",
        root_session_id="session_blocked",
        workspace_root=tmp_path,
    )
    envelope = _envelope()

    lease.engine_for(envelope)
    lease.mark_degraded(failure_code="page_detached")
    assert lease.recover_engine_once(envelope) is True
    lease.mark_degraded(failure_code="page_detached_again")

    assert lease.recover_engine_once(envelope) is False
    assert lease.safe_model_dump()["browser_session_state"] == "BLOCKED"


def test_browser_lease_close_preserves_legacy_lifecycle_and_uppercase_state(monkeypatch, tmp_path: Path) -> None:
    def fake_factory(envelope: ActionEnvelope) -> _ClosableEngine:
        del envelope
        return _ClosableEngine()

    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", fake_factory)
    lease = ProductTaskBrowserRuntimeLease(
        root_scope_id="scope_session_close",
        root_session_id="session_close",
        workspace_root=tmp_path,
    )

    lease.engine_for(_envelope())
    lease.close()
    card = lease.safe_model_dump()

    assert card["browser_session_state"] == "CLOSED"
    assert card["lifecycle_state"] == "closed"
    assert card["global_context_lock_acquired"] is False


def test_product_path_marks_root_lease_blocked_after_bounded_body_recovery_exhausts(monkeypatch, tmp_path: Path) -> None:
    created: list[_BrokenSessionEngine] = []

    def broken_factory(envelope: ActionEnvelope) -> _BrokenSessionEngine:
        del envelope
        engine = _BrokenSessionEngine()
        created.append(engine)
        return engine

    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", broken_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = ProductActionKernelLoopDecisionClient([_envelope()])

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_bounded_recovery_exhaustion",
        mission_objective="Find official docs for pathlib Path.glob.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=1,
        max_material_actions=1,
    )
    body_card = result.dispatch_results[0].safe_context_cards["body_circuit_breaker"]["root_browser_runtime_lease"]

    assert len(created) == 2
    assert body_card["browser_session_state"] == "BLOCKED"
    assert body_card["browser_session_state_history"][-3:] == ["RECONNECTED", "DEGRADED", "BLOCKED"]
    assert body_card["last_state_transition_reason"] == "body_session_unavailable_after_bounded_recovery"


def _envelope() -> ActionEnvelope:
    return ActionEnvelope(
        capability_id="real_browser_control",
        operation="real_browser.search",
        params={"query": "pathlib glob docs", "engine_profile": "fake_product_search"},
        idempotency_key="session-recovery-state-machine",
    )


class _ClosableEngine:
    browser_backend_id = "cloak_browser"

    def __init__(self) -> None:
        self.close_count = 0

    @property
    def safe_url_origin_hash(self) -> str:
        return "safe_origin_hash"

    def close(self) -> None:
        self.close_count += 1


class _BrokenSessionEngine(_ClosableEngine):
    def observe(self):
        raise RealBrowserControlRuntimeError("browser_session_missing_or_closed")

    def open(self):
        raise RealBrowserControlRuntimeError("browser_session_missing_or_closed")
