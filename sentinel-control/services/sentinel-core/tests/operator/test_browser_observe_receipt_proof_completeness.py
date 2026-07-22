from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.browser_cortex_divergence_harness import build_browser_cortex_divergence_trace
from sentinel.operator.live_run_evidence_sink import CrashSafeBoundedLiveRunEvidenceSink
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.real_browser_control_runtime import RealBrowserControlRuntimeError
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_observe_failure_has_terminal_browser_receipt_and_first_divergence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://developer.mozilla.org/en-US/")
    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", lambda _envelope: _ObserveFailingCloakEngine())
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "safe_evidence", run_id="observe_receipt")

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="observe-receipt-proof",
        mission_objective="Observe the bounded public browser page and report a truthful blocker if the body cannot observe.",
        decision_client=ProductActionKernelLoopDecisionClient([_observe(), _observe(), _observe(), _observe(), _observe()]),
        allowed_domains=("developer.mozilla.org", "real_browser:bounded_test_url"),
        allowed_capabilities=("real_browser_control", "sentinel_loop"),
        max_model_calls=5,
        max_material_actions=4,
        max_recoverable_action_failures=3,
        evidence_sink=sink,
    )
    host.shutdown()

    index_path = host.kernel.store.run_root / "_browser_proof_index" / f"{result.loop_id}.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    snapshot = json.loads((sink.run_dir / "safe_evidence_snapshot.json").read_text(encoding="utf-8"))
    trace = build_browser_cortex_divergence_trace(
        safe_evidence_snapshot=snapshot,
        proof_index=index,
        mission_ledger={"task_id": "observe_receipt", "blocked_reason": result.blocked_reason},
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS"
    assert index["browser_receipt_missing_count"] == 0
    observe_entries = [entry for entry in index["material_browser_receipts"] if entry["operation"] == "real_browser.observe"]
    assert len(observe_entries) == 2
    assert all(entry["browser_receipt_readable"] is True for entry in observe_entries)
    assert all(entry["action_status"] == "typed_observation_failure" for entry in observe_entries)
    first = observe_entries[0]
    assert first["typed_observation"]["outcome_kind"] == "typed_observation_failure"
    assert first["typed_observation"]["failure_code"] == "real_browser_observe_snapshot_failed"
    assert first["typed_observation"]["exception_class"] == "RealBrowserControlRuntimeError"
    assert first["typed_observation"]["exception_hash"]
    assert first["before_state_hash"]
    assert first["after_state_hash"] == first["before_state_hash"]
    assert first["root_browser_lease_id_hash"]
    assert first["backend_context_identity_hash"]
    assert first["evidence_delta"]["changed"] is False
    assert first["product_receipt_ref"]
    assert first["freshness"]
    assert trace["first_causal_divergence"]["decision_index"] == 1
    assert trace["first_causal_divergence"]["classification"] == "BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS"
    assert trace["decisions"][1]["progress"]["reason"] == "suppressed_repeated_action"
    assert trace["completion_truth"]["honest_blocker_present"] is True
    assert trace["completion_truth"]["loop_closed"] is True


def _observe() -> ActionEnvelope:
    return ActionEnvelope(
        capability_id="real_browser_control",
        operation="real_browser.observe",
        idempotency_key="observe-receipt-proof",
    )


class _ObserveFailingCloakEngine:
    browser_backend_id = "cloak_browser"
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"
    safe_url_origin_hash = "mdn-origin-hash"

    def bind_authority(self, authority: object) -> None:
        self.authority = authority

    def observe(self) -> object:
        raise RealBrowserControlRuntimeError("browser_session_post_action_snapshot_failed:RuntimeError")

    def close(self) -> None:
        self.closed = True
