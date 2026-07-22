from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.browser_progress_guard import BrowserProgressRepetitionGuard
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.real_browser_control_runtime import RealBrowserEngineElement, RealBrowserEngineSnapshot
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_progress_guard_detects_repeated_action_without_state_or_evidence_delta() -> None:
    guard = BrowserProgressRepetitionGuard()
    decision = _search_envelope()
    context = _context(state="state:a", evidence=("evidence:a",))

    guard.record_attempt(decision=decision, pre_context=context, post_context=_context(state="state:a", evidence=("evidence:a",)))
    repeat = guard.evaluate_repetition(decision=decision, context=context)

    assert repeat is not None
    assert repeat["repetition_count"] == 1
    assert repeat["recommended_control_step"] == "choose_alternate_affordance"


def test_progress_guard_resets_when_state_or_evidence_changes() -> None:
    guard = BrowserProgressRepetitionGuard()
    decision = _search_envelope()

    guard.record_attempt(
        decision=decision,
        pre_context=_context(state="state:a", evidence=("evidence:a",)),
        post_context=_context(state="state:b", evidence=("evidence:a",)),
    )

    assert guard.evaluate_repetition(decision=decision, context=_context(state="state:b", evidence=("evidence:a",))) is None


def test_product_loop_reobserves_then_blocks_repeated_browser_action_without_progress(monkeypatch, tmp_path: Path) -> None:
    engines: list[_NoProgressSearchEngine] = []

    def fake_factory(envelope: ActionEnvelope) -> _NoProgressSearchEngine:
        del envelope
        engine = _NoProgressSearchEngine()
        engines.append(engine)
        return engine

    monkeypatch.setattr(runtime_host_module, "_product_browser_engine", fake_factory)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = ProductActionKernelLoopDecisionClient([_search_envelope(), _search_envelope(), _search_envelope(), _search_envelope()])

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_repeated_no_progress",
        mission_objective="Find official docs for pathlib Path.glob.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=4,
        max_material_actions=4,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS"
    assert result.capability_sequence.count("real_browser_control:real_browser.search") == 1
    assert "real_browser_control:real_browser.observe" in result.capability_sequence
    assert engines[0].type_count == 1
    assert engines[0].observe_count >= 1


def _search_envelope() -> ActionEnvelope:
    return ActionEnvelope(
        capability_id="real_browser_control",
        operation="real_browser.search",
        params={"query": "pathlib glob docs", "engine_profile": "fake_product_search"},
        idempotency_key="progress-guard:search",
    )


def _context(*, state: str, evidence: tuple[str, ...]) -> dict[str, Any]:
    return {
        "browser_cognitive_decision_frame": {
            "operational_snapshot": {
                "fingerprint": state,
                "fields": {
                    "public_evidence_inventory": {
                        "value": {"evidence_refs": list(evidence), "count": len(evidence)}
                    }
                },
            }
        }
    }


class _NoProgressSearchEngine:
    browser_backend_id = "cloak_browser"

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
        self._opened = False

    @property
    def safe_url_origin_hash(self) -> str:
        return "safe_origin_hash"

    @property
    def last_typed_text_hash(self) -> str:
        return ""

    def bind_authority(self, authority) -> None:
        del authority

    def open(self) -> RealBrowserEngineSnapshot:
        self._opened = True
        self.open_count += 1
        return self._snapshot()

    def observe(self) -> RealBrowserEngineSnapshot:
        if not self._opened:
            return self.open()
        self.observe_count += 1
        return self._snapshot()

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        del ref, text
        self.type_count += 1
        return self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        del ref, key
        self.press_count += 1
        return self._snapshot()

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        self.wait_count += 1
        return self._snapshot()

    def close(self) -> None:
        self._opened = False

    def _snapshot(self) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title="No Progress Docs",
            state_hash="state_no_progress",
            elements=(
                RealBrowserEngineElement(
                    ref="search:box",
                    role="searchbox",
                    name="Search",
                    text_preview="Search docs",
                    value_preview="pathlib glob docs",
                ),
            ),
        )
