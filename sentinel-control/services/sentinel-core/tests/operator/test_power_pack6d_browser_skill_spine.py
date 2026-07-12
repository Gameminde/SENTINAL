from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.actionability_registry import build_default_actionability_registry
from sentinel.operator.browser_backend_selector import CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE, select_browser_backend
from sentinel.operator.browser_decision_frame import BrowserDecisionFrameCompiler
from sentinel.operator.browser_model_native_control_loop import map_browser_model_native_intent
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.real_browser_attempt_evaluation import (
    VerifiedExtractionCompletionAttemptMetrics,
    browser_receipts_backend_match,
    evaluate_verified_extraction_completion_attempt,
)
from sentinel.operator.real_browser_control_replay import RealBrowserControlReplayView
from sentinel.operator import real_browser_control_runtime as real_browser_runtime_module
from sentinel.operator.real_browser_control_runtime import (
    BrowserSessionManagerRealBrowserEngine,
    CLOAK_BROWSER_BACKEND_ID,
    InMemoryRealBrowserEngine,
    PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
    RealBrowserControlRuntime,
    RealBrowserControlRuntimeError,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
    check_cloak_session_readiness,
)


def test_browser_skill_frame_prefers_search_inspect_extract_over_type_click() -> None:
    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        _HardProductSearchEngine().open(),
        mission_objective="Search Alibaba for glasses under 5 EUR.",
        origin_hash="origin_hash",
    )

    frame = BrowserDecisionFrameCompiler().compile(
        mission_objective="Search Alibaba for glasses under 5 EUR.",
        world_model=world_model,
        available_actions=_browser_actions(),
        progress_state="real_browser_opened_world_model_ready",
    )
    dumped = frame.safe_model_dump()
    actions = [candidate["action"] for candidate in dumped["candidate_actions"]]

    assert actions[:4] == [
        "real_browser.observe",
        "real_browser.search",
        "real_browser.inspect_result",
        "real_browser.open_result",
    ]
    assert "real_browser.extract_product_cards" in actions
    assert "real_browser.verify_extraction" in actions
    assert "real_browser.type_text" not in actions
    assert "real_browser.click" not in actions
    example_operations = [example["operation"] for example in dumped["exact_action_envelope_examples"]]
    assert "real_browser.search" in example_operations
    assert "real_browser.extract_product_cards" in example_operations
    assert "real_browser.type_text" not in example_operations


def test_browser_skill_actions_are_backed_by_actionability_registry() -> None:
    frame = build_default_actionability_registry().compile_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )
    visible = {item.canonical_action_name for item in frame.model_visible_actions}
    internal = {item.canonical_action_name for item in frame.hidden_internal_actions}

    assert {
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.open_result",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
    }.issubset(visible)
    assert {
        "real_browser_control.real_browser.type_text",
        "real_browser_control.real_browser.click",
        "real_browser_control.real_browser.press_key",
    }.issubset(internal)


def test_browser_skill_consumes_power_skill_backend_frame() -> None:
    actionability = build_default_actionability_registry()
    backend_frame = build_default_power_skill_registry().compile_backend_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
        actionability_registry=actionability,
    )

    browser_backend = _backend_by_skill(backend_frame, "real_browser_control")

    assert browser_backend["model_visible_backend_id"] == "browser_skill"
    assert browser_backend["task_loop_reachable"] is True
    assert "CloakBrowser" in browser_backend["organ_refs"]


def test_browser_skill_selects_cloak_session_backend_when_available() -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    assert selection.preferred_backend_id == "cloak_browser"
    assert selection.model_visible_backend_id == "browser_skill"


def test_cloak_available_selected_as_product_backend(tmp_path: Path) -> None:
    selection = select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE))
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=_FakeBrowserSessionManager(),
    )

    fixture = _BrowserSkillFixture(tmp_path, engine=engine, backend_selection=selection)

    assert fixture.runtime.selected_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert fixture.runtime.actual_backend_id == CLOAK_BROWSER_BACKEND_ID


def test_cloak_selected_actual_backend_must_match(tmp_path: Path) -> None:
    selection = select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE))

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_backend_selection_mismatch"):
        _BrowserSkillFixture(
            tmp_path,
            engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
            backend_selection=selection,
            selected_backend_id=CLOAK_BROWSER_BACKEND_ID,
        )


def test_backend_frame_preferred_cloak_must_match_actual_backend_or_block(tmp_path: Path) -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_backend_selection_mismatch"):
        _BrowserSkillFixture(
            tmp_path,
            engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
            backend_selection=selection,
        )


def test_playwright_actual_engine_requires_explicit_compatibility_selection(tmp_path: Path) -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
        backend_selection=selection,
        selected_backend_id=PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
    )

    assert fixture.runtime.selected_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    assert opened.status == "completed"


def test_no_silent_cloak_to_playwright_fallback(tmp_path: Path) -> None:
    selection = select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE))

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_backend_selection_mismatch:selected=cloak_browser:actual=playwright_real_browser_engine"):
        _BrowserSkillFixture(
            tmp_path,
            engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
            backend_selection=selection,
        )


def test_playwright_backend_requires_explicit_compatibility_selection() -> None:
    selection = select_browser_backend(available_backend_modules=("sentinel.operator.real_browser_control_runtime",))

    assert selection.preferred_backend_id is None
    assert selection.compatibility_backend_id == "playwright_real_browser_engine"
    assert selection.playwright_requires_explicit_compatibility is True


def test_real_browser_search_dispatches_to_selected_backend(tmp_path: Path) -> None:
    manager = _FakeBrowserSessionManager()
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
    )
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=engine,
        backend_selection=select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)),
    )

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert manager.open_calls == 1
    assert manager.observe_calls >= 1
    assert ("fill", "Search products", "glasses under 5 euro") in manager.interact_calls
    assert ("type", "Search products", "glasses under 5 euro") not in manager.interact_calls
    assert ("open_tab", "", "") not in manager.interact_calls


def test_search_material_receipt_records_backend_truth(tmp_path: Path) -> None:
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=_FakeBrowserSessionManager(),
    )
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=engine,
        backend_selection=select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)),
    )

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )
    receipt = fixture.load_action_receipt(result.receipt_refs[0])

    assert receipt["action_kind"] == "real_browser.search"
    assert receipt["selected_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert receipt["actual_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert receipt["session_backend_kind"] == "cloakbrowser"


def test_browser_session_manager_l5_used_for_live_backend_when_available(tmp_path: Path) -> None:
    manager = _FakeBrowserSessionManager()
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
    )
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=engine,
        backend_selection=select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)),
    )

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"), authority=fixture.authority, context={})

    assert manager.open_calls == 1
    assert manager.observe_calls >= 1
    assert fixture.runtime.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert engine.session_manager_backend_kind == "cloakbrowser"


def test_browser_session_devtools_metadata_is_exposed_as_safe_context(tmp_path: Path) -> None:
    manager = _FakeBrowserSessionManager()
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
    )
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=engine,
        backend_selection=select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)),
    )

    result = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    devtools = result.context_cards["browser_devtools_context"]
    assert devtools["source"] == "browser_session_manager_l5"
    assert devtools["backend_kind"] == "cloakbrowser"
    assert devtools["page_target_count"] == 1
    assert devtools["snapshot_hash"] == "fake_a11y_snapshot_hash"
    assert devtools["network_ledger_hash"] == "fake_network_ledger_hash"
    assert devtools["console_ledger_hash"] == "fake_console_ledger_hash"
    assert devtools["safe_metadata"]["network_event_count"] == 2
    assert devtools["safe_metadata"]["console_error_count"] == 1
    persisted = str(devtools).lower()
    assert "bounded.example.test" not in persisted
    assert "fake_bsess_cloak" not in persisted
    assert "raw_dom" not in persisted
    assert "screenshot_bytes" not in persisted
    assert "cookie" not in persisted
    assert "password" not in persisted


def test_browser_session_devtools_metadata_failure_does_not_block_browser_action(tmp_path: Path) -> None:
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=_FailingDevToolsBrowserSessionManager(),
    )
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=engine,
        backend_selection=select_browser_backend(available_backend_modules=(CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)),
    )

    result = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    devtools = result.context_cards["browser_devtools_context"]
    assert devtools["available"] is False
    assert devtools["failure_code"] == "browser_devtools_metadata_unavailable"
    assert "diagnostic_hash" in devtools
    assert "raw_devtools_stack" not in str(devtools).lower()


def test_cloak_readiness_gate_blocks_before_provider_when_bootstrap_missing(tmp_path: Path) -> None:
    class _FailingCloakSessionManager:
        backend_kind = "cloakbrowser"

        def __init__(self) -> None:
            self.open_calls = 0

        def open_session(self, request: Any) -> Any:
            del request
            self.open_calls += 1
            raise RuntimeError("remote bootstrap download closed by host")

        def close_all(self) -> None:
            pass

    manager = _FailingCloakSessionManager()

    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
        capture_root=tmp_path / "capture",
    )

    assert readiness.ready is False
    assert readiness.provider_call_allowed is False
    assert readiness.failure_code == "CLOAK_SESSION_BOOTSTRAP_NOT_READY"
    assert readiness.selected_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert manager.open_calls == 1
    assert not list((tmp_path / "capture").rglob("*cookie*"))
    assert not list((tmp_path / "capture").rglob("*session*"))


def test_cloak_readiness_gate_passes_when_fake_cloak_session_opens(tmp_path: Path) -> None:
    manager = _FakeBrowserSessionManager()

    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
        capture_root=tmp_path / "capture",
    )

    assert readiness.ready is True
    assert readiness.provider_call_allowed is True
    assert readiness.failure_code is None
    assert readiness.selected_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.session_backend_kind == "cloakbrowser"
    assert readiness.readiness_receipt_hash
    assert manager.open_calls == 1


def test_cloak_engine_close_removes_profile_material(tmp_path: Path) -> None:
    class _ClosableFakeBrowserSessionManager(_FakeBrowserSessionManager):
        def __init__(self) -> None:
            super().__init__()
            self.close_calls = 0

        def close_all(self) -> None:
            self.close_calls += 1

    capture_root = tmp_path / "capture"
    profile_cache = capture_root / "browser_capture" / "profile" / "Default" / "Cache"
    profile_cache.mkdir(parents=True)
    (profile_cache / "cache.txt").write_text("session cache material", encoding="utf-8")
    manager = _ClosableFakeBrowserSessionManager()
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url="https://bounded.example.test/catalog",
        session_manager=manager,
        capture_root=capture_root,
    )

    engine.close()

    assert manager.close_calls == 1
    assert not (capture_root / "browser_capture" / "profile").exists()


def test_backend_match_ignores_open_receipt_without_backend_truth() -> None:
    receipts = (
        {"receipt_kind": "real_browser_open", "action": "real_browser.open"},
        {
            "receipt_kind": "real_browser_action",
            "action": "real_browser.search",
            "selected_backend_id": CLOAK_BROWSER_BACKEND_ID,
            "actual_backend_id": CLOAK_BROWSER_BACKEND_ID,
            "session_backend_kind": "cloakbrowser",
        },
    )

    assert browser_receipts_backend_match(receipts, expected_backend_id=CLOAK_BROWSER_BACKEND_ID) is True


def test_cloak_bootstrap_download_failure_does_not_consume_provider_call(tmp_path: Path) -> None:
    provider_call_count = 0

    class _FailingCloakSessionManager:
        backend_kind = "cloakbrowser"

        def open_session(self, request: Any) -> Any:
            del request
            raise RuntimeError("download failed before provider")

    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        session_manager=_FailingCloakSessionManager(),
        capture_root=tmp_path / "capture",
    )
    if readiness.provider_call_allowed:
        provider_call_count += 1

    assert readiness.failure_code == "CLOAK_SESSION_BOOTSTRAP_NOT_READY"
    assert provider_call_count == 0


def test_cloak_binary_missing_blocks_before_session_manager_construction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provider_call_count = 0
    manager_build_count = 0

    def _missing_binary_info() -> dict[str, Any]:
        return {
            "installed": False,
            "version": "146.0.test",
            "bundled_version": "146.0.test",
            "platform": "windows-x64",
            "tier": "free",
            "cache_dir": "C:/Users/example/.cloakbrowser/chromium",
            "download_url": "https://cloakbrowser.example/download.zip",
        }

    def _build_should_not_happen(**_: Any) -> Any:
        nonlocal manager_build_count
        manager_build_count += 1
        raise AssertionError("session manager should not be built when Cloak binary is missing")

    monkeypatch.setattr(real_browser_runtime_module, "_cloak_binary_info", _missing_binary_info)
    monkeypatch.setattr(real_browser_runtime_module, "_build_browser_session_manager", _build_should_not_happen)

    cache_path = tmp_path / "readiness.json"
    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        capture_root=tmp_path / "capture",
        cache_path=cache_path,
    )
    if readiness.provider_call_allowed:
        provider_call_count += 1

    assert readiness.ready is False
    assert readiness.provider_call_allowed is False
    assert readiness.failure_code == "CLOAK_BINARY_NOT_INSTALLED"
    assert readiness.selected_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.actual_backend_id == ""
    assert provider_call_count == 0
    assert manager_build_count == 0
    cache_text = cache_path.read_text(encoding="utf-8")
    assert "bounded.example.test" not in cache_text
    assert "cloakbrowser.example" not in cache_text
    assert "C:/Users/example" not in cache_text


def test_cloak_local_binary_override_allows_readiness_without_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_binary = tmp_path / "Local Chrome" / "chrome.exe"
    local_binary.parent.mkdir(parents=True)
    local_binary.write_bytes(b"fake local browser executable")
    manager = _FakeBrowserSessionManager()

    def _not_installed_but_path_present() -> dict[str, Any]:
        return {
            "installed": False,
            "version": "146.0.test",
            "bundled_version": "146.0.test",
            "platform": "windows-x64",
            "tier": "free",
            "cache_dir": "C:/Users/example/.cloakbrowser/chromium",
            "download_url": "https://cloakbrowser.example/download.zip",
            "path": str(local_binary),
        }

    monkeypatch.setenv("CLOAKBROWSER_BINARY_PATH", str(local_binary))
    monkeypatch.setattr(real_browser_runtime_module, "_cloak_binary_info", _not_installed_but_path_present)
    monkeypatch.setattr(real_browser_runtime_module, "_build_browser_session_manager", lambda **_: manager)

    cache_path = tmp_path / "readiness.json"
    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        capture_root=tmp_path / "capture",
        cache_path=cache_path,
        prepare_binary=False,
    )

    assert readiness.ready is True
    assert readiness.provider_call_allowed is True
    assert readiness.failure_code is None
    assert readiness.selected_backend_id == readiness.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert manager.open_calls == 1
    cache_text = cache_path.read_text(encoding="utf-8")
    assert str(local_binary) not in cache_text
    assert "cloakbrowser.example" not in cache_text


def test_cloak_readiness_safe_receipts_do_not_count_as_profile_material(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_binary = tmp_path / "chrome.exe"
    local_binary.write_bytes(b"fake local browser executable")
    manager = _FakeBrowserSessionManager()

    def _path_override_info() -> dict[str, Any]:
        return {
            "installed": False,
            "version": "146.0.test",
            "bundled_version": "146.0.test",
            "platform": "windows-x64",
            "tier": "free",
            "path": str(local_binary),
        }

    def _build_manager_with_safe_artifacts(**kwargs: Any) -> Any:
        capture_root = Path(kwargs["capture_root"])
        safe_dir = capture_root / "bs" / "safe_session"
        safe_dir.mkdir(parents=True, exist_ok=True)
        (safe_dir / "0000_open_snapshot.json").write_text("{}", encoding="utf-8")
        (safe_dir / "0000_open_receipt.json").write_text("{}", encoding="utf-8")
        return manager

    monkeypatch.setenv("CLOAKBROWSER_BINARY_PATH", str(local_binary))
    monkeypatch.setattr(real_browser_runtime_module, "_cloak_binary_info", _path_override_info)
    monkeypatch.setattr(real_browser_runtime_module, "_build_browser_session_manager", _build_manager_with_safe_artifacts)

    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        capture_root=tmp_path / "capture",
        prepare_binary=False,
    )

    assert readiness.ready is True
    assert readiness.profile_material_persisted is False


def test_cloak_binary_bootstrap_failure_preserves_safe_child_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    class _CompletedProcess:
        returncode = 1
        stdout = '{"exception_class":"SSLError","reason_hash":"abc123"}\n'
        stderr = "raw transport failure with https://cloakbrowser.example/download.zip"

    monkeypatch.setattr(
        real_browser_runtime_module.subprocess,
        "run",
        lambda *_args, **_kwargs: _CompletedProcess(),
    )

    ready, failure_code, diagnostics = real_browser_runtime_module._ensure_cloak_binary_with_wall_timeout(timeout_ms=1000)

    assert ready is False
    assert failure_code == "CLOAK_BINARY_BOOTSTRAP_FAILED"
    assert diagnostics["exception_class"] == "SSLError"
    assert diagnostics["reason_hash"] == "abc123"
    assert "cloakbrowser.example" not in str(diagnostics)


def test_cloak_readiness_gate_times_out_without_hanging_parent(tmp_path: Path) -> None:
    class _HangingCloakSessionManager:
        backend_kind = "cloakbrowser"

        def __init__(self) -> None:
            self.open_calls = 0
            self.started = threading.Event()
            self.release = threading.Event()

        def open_session(self, request: Any) -> Any:
            del request
            self.open_calls += 1
            self.started.set()
            self.release.wait(timeout=5.0)
            raise RuntimeError("late bootstrap download finished after readiness wall timeout")

        def close_all(self) -> None:
            pass

    manager = _HangingCloakSessionManager()
    cache_path = tmp_path / "readiness.json"
    started_at = time.monotonic()

    try:
        readiness = check_cloak_session_readiness(
            target_url="https://bounded.example.test/catalog",
            session_manager=manager,
            capture_root=tmp_path / "capture",
            cache_path=cache_path,
            timeout_ms=30_000,
            wall_timeout_ms=100,
        )
    finally:
        manager.release.set()

    elapsed = time.monotonic() - started_at

    assert manager.started.wait(timeout=0.5)
    assert elapsed < 1.5
    assert manager.open_calls == 1
    assert readiness.ready is False
    assert readiness.provider_call_allowed is False
    assert readiness.failure_code == "CLOAK_SESSION_READINESS_TIMEOUT"
    assert readiness.selected_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.receipt_backend_match is False
    assert readiness.profile_material_persisted is False
    cache_text = cache_path.read_text(encoding="utf-8")
    assert "bounded.example.test" not in cache_text
    assert "CLOAK_SESSION_READINESS_TIMEOUT" in cache_text


def test_cloak_readiness_timeout_removes_sensitive_profile_dirs(tmp_path: Path) -> None:
    class _ProfileWritingHangingManager:
        backend_kind = "cloakbrowser"

        def __init__(self, capture_root: Path) -> None:
            self.capture_root = capture_root
            self.started = threading.Event()
            self.release = threading.Event()

        def open_session(self, request: Any) -> Any:
            del request
            sensitive_dir = self.capture_root / "bs" / "session_timeout" / "Local Storage"
            sensitive_dir.mkdir(parents=True, exist_ok=True)
            (sensitive_dir / "leveldb.log").write_text("profile material", encoding="utf-8")
            self.started.set()
            self.release.wait(timeout=5.0)
            raise RuntimeError("late session completion after readiness timeout")

        def close_all(self) -> None:
            pass

    capture_root = tmp_path / "capture"
    manager = _ProfileWritingHangingManager(capture_root)

    try:
        readiness = check_cloak_session_readiness(
            target_url="https://bounded.example.test/catalog",
            session_manager=manager,
            capture_root=capture_root,
            timeout_ms=30_000,
            wall_timeout_ms=100,
        )
    finally:
        manager.release.set()

    assert manager.started.wait(timeout=0.5)
    assert readiness.ready is False
    assert readiness.failure_code == "CLOAK_SESSION_READINESS_TIMEOUT"
    assert readiness.profile_material_persisted is False
    assert not (capture_root / "bs" / "session_timeout" / "Local Storage").exists()


def test_cloak_selected_actual_backend_receipt_matches_after_ready(tmp_path: Path) -> None:
    readiness = check_cloak_session_readiness(
        target_url="https://bounded.example.test/catalog",
        session_manager=_FakeBrowserSessionManager(),
        capture_root=tmp_path / "capture",
    )

    assert readiness.ready is True
    assert readiness.selected_backend_id == readiness.actual_backend_id == CLOAK_BROWSER_BACKEND_ID
    assert readiness.receipt_backend_match is True


def test_playwright_compat_tests_do_not_mark_product_backend_proven(tmp_path: Path) -> None:
    selection = select_browser_backend(available_backend_modules=(PLAYWRIGHT_BROWSER_MODULE,))
    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
        backend_selection=selection,
        selected_backend_id=PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
    )

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    backend_execution = opened.context_cards["browser_backend_execution"]

    assert backend_execution["actual_backend_id"] == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID
    assert backend_execution["compatibility_only"] is True
    assert backend_execution["product_backend_proven"] is False


def test_real_browser_search_material_receipt_when_backend_actuates(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert result.material_action is True
    assert result.receipt_refs
    assert fixture.load_action_receipt(result.receipt_refs[0])["action_kind"] == "real_browser.search"


def test_search_success_records_material_navigation_or_search_receipt(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )
    receipt = fixture.load_action_receipt(result.receipt_refs[0])

    assert result.status == "completed"
    assert result.material_action is True
    assert result.context_cards["browser_world_model_summary"]["product_or_result_candidate_count"] >= 1
    assert receipt["action_kind"] == "real_browser.search"
    assert receipt["status"] == "completed"


def test_real_browser_search_ranks_search_like_refs_and_tries_alternates(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_AlternateSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert result.operation == "real_browser.search"
    assert fixture.engine.attempted_refs[:2] == ["input:broken_search", "input:search"]
    assert fixture.engine.search_query == "glasses under 5 euro"
    assert fixture.load_action_receipt(result.receipt_refs[0])["action_kind"] == "real_browser.search"


def test_real_browser_search_focuses_fills_or_types_and_presses_enter_or_search_button(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert fixture.engine.type_count == 1
    assert fixture.engine.press_count == 1
    assert fixture.engine.results_visible is True
    assert "search submitted" in result.observation_summary


def test_locator_timeout_returns_recoverable_observation_not_terminal_block(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "recoverable_failed"
    assert result.recoverable is True
    assert result.failure_class is ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE
    assert result.blocked_reason == "real_browser_search_actuation_failed"
    assert result.recovery_observation


def test_search_recoverable_failure_updates_decision_context(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    failed = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, failed],
        available_actions=_browser_actions(),
        model_calls_used=2,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=1,
        max_recovery_turns=2,
    )

    assert failed.status == "recoverable_failed"
    assert context["recoverable_observations"][-1]["failure_code"] == "real_browser_search_actuation_failed"
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.extract_product_cards"


def test_search_failure_with_relevant_cards_continues_to_extract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    failed = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, failed], recovery_turns_used=1)
    cards = context["browser_world_model"]["product_or_result_candidate_cards"]

    assert failed.recoverable is True
    assert cards[0]["relevance_to_objective"] in {"relevant", "partial"}
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.extract_product_cards"


def test_recovery_observation_refreshes_world_model_and_decision_context(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()
    context = decisions.contexts[2]

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert context["recoverable_observations"]
    assert context["browser_world_model_summary"]["search_like_refs"]
    assert "real_browser_control.real_browser.search" in context["skill_decision_frame"]["recommended_next_actions"]


def test_recovery_budget_exhaustion_blocks_honestly_without_fake_success(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=0).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "RECOVERY_BUDGET_EXHAUSTED"
    assert result.receipt_refs == tuple(ref for ref in result.receipt_refs if "fake" not in ref)
    assert fixture.engine.type_count == 0


def test_two_search_failures_with_product_cards_recommends_extract_not_repeat_search(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    failures = [
        fixture.runtime.execute(
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            authority=fixture.authority,
            context={},
        )
        for _ in range(2)
    ]
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, *failures],
        available_actions=_browser_actions(),
        model_calls_used=3,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=2,
        max_recovery_turns=3,
    )

    assert all(result.status == "recoverable_failed" for result in failures)
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.extract_product_cards"
    assert context["skill_decision_frame"]["recommended_next_actions"][0] == "real_browser_control.real_browser.extract_product_cards"


def test_extract_product_cards_can_run_from_existing_world_model_cards(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    assert opened.context_cards["browser_world_model"]["product_or_result_candidate_cards"]
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )

    assert extracted.status == "completed"
    assert extracted.context_cards["browser_world_model"]["product_or_result_candidate_cards"]


def test_product_extraction_card_captures_title_price_moq_supplier_caveats_when_visible(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    cards = result.context_cards["browser_world_model"]["product_or_result_candidate_cards"]

    assert result.status == "completed"
    assert cards[0]["title"] == "Polarized sunglasses"
    assert cards[0]["visible_price"] == "$4.80"
    assert cards[0]["minimum_order"] == "10 pieces"
    assert cards[0]["supplier_or_store"] == "Yiwu Test Store"
    assert "shipping not included" in cards[0]["caveats"]


def test_relevance_fields_added_to_product_cards(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    card = result.context_cards["browser_world_model"]["product_or_result_candidate_cards"][0]

    assert card["title"] == "Polarized sunglasses"
    assert card["visible_price"] == "$4.80"
    assert card["currency_or_unit"] == "USD/visible"
    assert card["minimum_order"] == "10 pieces"
    assert card["supplier_or_store"] == "Yiwu Test Store"
    assert card["relevance_to_objective"] in {"relevant", "partial"}
    assert card["price_condition_supported"] == "unknown"
    assert card["objective_relevance_assessed"] is True
    assert card["evidence_ref_hash"]


def test_lunettes_product_card_is_relevant_when_objective_is_glasses() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Alibaba Results",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:lunettes",
                role="link",
                name="Lunettes optiques carrees classiques MOQ 20 pieces",
                text_preview=(
                    "Lunettes optiques carrees classiques 117,57-161,65 DA per piece "
                    "MOQ 20 pieces Supplier Vision Test Store"
                ),
            ),
        ),
    )

    card = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    ).product_or_result_candidate_cards[0]

    assert card.title.startswith("Lunettes optiques")
    assert card.relevance_to_objective in {"relevant", "partial"}
    assert card.visible_price == "unknown"
    assert card.price_condition_supported == "unknown"
    assert card.minimum_order == "20 pieces"


def test_extracted_text_segments_prefer_product_cards_over_generic_alibaba_text() -> None:
    extracted_text = (
        "Pourquoi Alibaba.com Assistance Centre acheteur Conditions generales "
        "Telecharger application. "
        "Lunettes optiques carrees classiques. Price EUR 4.50 per piece. "
        "MOQ 20 pieces. Supplier Vision Test Store. Shipping not included."
    )
    snapshot = RealBrowserEngineSnapshot(
        page_title="Alibaba Search",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement("input:search", "textbox", "Search products"),
        ),
    )

    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
        extracted_text=extracted_text,
    )
    card = world_model.product_or_result_candidate_cards[0]

    assert card.title.startswith("Lunettes optiques")
    assert "Pourquoi Alibaba" not in card.title
    assert card.visible_price == "EUR 4.50"
    assert card.price_condition_supported == "supported"


def test_under_price_claim_requires_visible_price_evidence() -> None:
    euro_snapshot = RealBrowserEngineSnapshot(
        page_title="Euro Results",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:euro",
                role="link",
                name="Budget sunglasses EUR 4.50",
                text_preview="Budget sunglasses EUR 4.50 per piece MOQ 2 pieces Supplier Euro Store",
            ),
        ),
    )
    usd_snapshot = RealBrowserEngineSnapshot(
        page_title="USD Results",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:usd",
                role="link",
                name="Polarized sunglasses $4.80",
                text_preview="Polarized sunglasses $4.80 per piece MOQ 10 pieces Supplier Yiwu Test Store",
            ),
        ),
    )

    euro_card = BrowserWorldModelBuilder().build_from_snapshot(
        euro_snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    ).product_or_result_candidate_cards[0]
    usd_card = BrowserWorldModelBuilder().build_from_snapshot(
        usd_snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    ).product_or_result_candidate_cards[0]

    assert euro_card.price_condition_supported == "supported"
    assert usd_card.price_condition_supported == "unknown"


def test_finish_available_after_verify_extraction_and_summary(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, extracted, verified, summary],
        available_actions=_browser_actions(),
        model_calls_used=3,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
    )

    assert verified.status == "passed"
    assert context["finish_available"] is True
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.finish"


def test_5h_completion_lane_harness_accepts_extract_verify_summary_finish() -> None:
    metrics = VerifiedExtractionCompletionAttemptMetrics(
        extract_product_cards_count=1,
        verify_extraction_count=1,
        summarize_evidence_count=1,
        summary_present=True,
        finish_present=True,
        mission_status="completed",
        replay_no_react=True,
        high_risk_scan_clean=True,
        search_or_navigation_evidence=False,
    )

    verdict = evaluate_verified_extraction_completion_attempt(metrics)

    assert verdict.accepted is True
    assert verdict.verdict == "VALID_SUCCESS"
    assert "search_or_navigation_evidence" not in verdict.required_fields


def test_verified_extraction_routes_to_summary_when_summary_missing(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified])

    assert context["finish_available"] is False
    assert context["completion_requirements"]["has_grounded_evidence_summary"] is False
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.summarize_evidence"

    mapping = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "sentinel_loop"
    assert mapping.envelope.operation == "summarize_evidence"


def test_verified_extraction_and_summary_routes_to_finish(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified, summary])

    assert context["finish_available"] is True
    assert context["completion_requirements"]["has_grounded_evidence_summary"] is True
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.finish"

    mapping = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "sentinel_loop"
    assert mapping.envelope.operation == "finish"


def test_ambiguous_intent_after_verify_does_not_search(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified])

    mapping = map_browser_model_native_intent("I will continue with the safest next step.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "sentinel_loop"
    assert mapping.envelope.operation == "summarize_evidence"


def test_open_search_demoted_after_verified_extraction(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified])

    for model_output in (
        "Open the page again.",
        "Search Alibaba again.",
        {"capability_id": "real_browser_control", "operation": "real_browser.search", "params": {}},
    ):
        mapping = map_browser_model_native_intent(model_output, context=context)
        assert mapping.envelope is not None
        assert mapping.envelope.capability_id == "sentinel_loop"
        assert mapping.envelope.operation == "summarize_evidence"


def test_finish_without_summary_recovers_to_summary_lane(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "I will extract the visible product cards now.",
            "Verify the extracted cards.",
            "I have enough evidence, summarize and finish.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence
    assert result.capability_sequence[-1] == "sentinel_loop:finish"


def test_finish_without_verified_extraction_recovers_to_verify_not_fake_success(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "I will extract the visible product cards now.",
            "I have enough evidence, summarize and finish.",
            "I have enough evidence, summarize and finish.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "real_browser_control:real_browser.verify_extraction" in result.capability_sequence
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence
    assert result.capability_sequence[-1] == "sentinel_loop:finish"


def test_recovery_budget_does_not_preempt_summary_finish_after_verify(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            {"capability_id": "real_browser_control", "operation": "real_browser.search", "params": {}},
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=1).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.blocked_reason is None
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence
    assert result.capability_sequence[-1] == "sentinel_loop:finish"


def test_finalgate_not_written_before_completion_lane_attempt(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            {"capability_id": "real_browser_control", "operation": "real_browser.search", "params": {}},
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=1).run()
    mission_text = _mission_text(fixture.kernel, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "RECOVERY_BUDGET_EXHAUSTED" not in mission_text
    assert "model_led_task_loop_blocked" not in mission_text
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence


def test_summary_grounded_in_extracted_cards_unknowns_preserved(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )

    grounded = summary.context_cards["grounded_evidence_summary"]

    assert grounded["card_count"] >= 1
    assert grounded["cards"][0]["title"] == "Polarized sunglasses"
    assert grounded["cards"][0]["visible_price"] == "$4.80"
    assert grounded["cards"][0]["minimum_order"] == "10 pieces"
    assert grounded["cards"][0]["supplier_or_store"] == "Yiwu Test Store"
    assert grounded["cards"][0]["relevance_to_objective"] in {"relevant", "partial"}
    assert grounded["cards"][0]["price_condition_supported"] == "unknown"
    assert grounded["objective_relevance_assessed"] is True
    assert grounded["under_price_condition_supported_by_visible_evidence"] in {"unknown", "mixed"}

    sparse_fixture = _BrowserSkillFixture(tmp_path / "sparse", engine=_SparseProductSearchEngine())
    sparse_opened = sparse_fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=sparse_fixture.authority,
        context={},
    )
    sparse_extracted = sparse_fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=sparse_fixture.authority,
        context=sparse_opened.context_cards,
    )
    sparse_verified = sparse_fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=sparse_fixture.authority,
        context=sparse_extracted.context_cards,
    )
    sparse_summary = sparse_fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=sparse_fixture.authority,
        context=_compile_browser_context(sparse_fixture, observations=[sparse_opened, sparse_extracted, sparse_verified]),
    )

    sparse_grounded = sparse_summary.context_cards["grounded_evidence_summary"]

    assert sparse_grounded["cards"][0]["title"] == "Minimal glasses listing"
    assert sparse_grounded["cards"][0]["visible_price"] == "unknown"
    assert sparse_grounded["cards"][0]["minimum_order"] == "unknown"
    assert sparse_grounded["cards"][0]["supplier_or_store"] == "unknown"
    assert sparse_grounded["cards"][0]["price_condition_supported"] == "unknown"


def test_product_extraction_card_uses_unknown_fields_without_hallucination() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Sparse Search",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:sparse",
                role="link",
                name="Minimal glasses listing",
                text_preview="Minimal glasses listing",
            ),
        ),
    )

    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    )
    card = world_model.product_or_result_candidate_cards[0]

    assert card.title == "Minimal glasses listing"
    assert card.visible_price == "unknown"
    assert card.minimum_order == "unknown"
    assert card.supplier_or_store == "unknown"
    assert card.price_condition_supported == "unknown"


def test_unknown_price_preserved_as_unknown() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Unknown Price",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:unknown",
                role="link",
                name="Minimal glasses listing",
                text_preview="Minimal glasses listing supplier unknown price pending",
            ),
        ),
    )

    card = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    ).product_or_result_candidate_cards[0]

    assert card.visible_price == "unknown"
    assert card.currency_or_unit == "unknown"
    assert card.price_condition_supported == "unknown"


def test_summary_grounded_in_verified_cards_and_relevance(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )

    grounded = summary.context_cards["grounded_evidence_summary"]

    assert grounded["matched_products"]
    assert grounded["uncertain_products"]
    assert grounded["under_price_condition_supported_by_visible_evidence"] == "unknown"
    assert grounded["summary_text"]
    assert "Unknown fields remain unknown" in grounded["summary_text"]


def test_visible_irrelevant_cards_do_not_fake_success(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_IrrelevantProductSearchEngine())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified, summary])

    assert summary.context_cards["grounded_evidence_summary"]["matched_products"] == []
    assert context["completion_requirements"]["has_objective_relevance_assessment"] is True
    assert context["completion_requirements"]["has_relevant_product_evidence"] is False
    assert context["finish_available"] is False
    assert context["primary_model_recommended_next_action"] in {
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
    }


def test_relevance_gap_after_search_does_not_repeat_search_as_primary(tmp_path: Path) -> None:
    class _IrrelevantAfterSearchEngine(_IrrelevantProductSearchEngine):
        def click(self, ref: str) -> RealBrowserEngineSnapshot:
            self._require_interactable(ref)
            self.click_count += 1
            return self._snapshot()

        def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
            self._require_editable(ref)
            self.press_count += 1
            return self._snapshot()

    fixture = _BrowserSkillFixture(tmp_path, engine=_IrrelevantAfterSearchEngine())
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    summary = fixture.action_kernel.execute(
        ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified]),
    )
    searched = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context=_compile_browser_context(fixture, observations=[opened, extracted, verified, summary]),
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified, summary, searched])

    assert context["completion_requirements"]["requires_relevant_product_evidence"] is True
    assert context["primary_model_recommended_next_action"] != "real_browser_control.real_browser.search"

    mapping = map_browser_model_native_intent("I will continue with the strongest safe next step.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.operation != "real_browser.search"


def test_finish_requires_relevance_assessment(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    stale_summary = ActionResult(
        action_id="action_stale_summary",
        capability_id="sentinel_loop",
        operation="summarize_evidence",
        status="completed",
        context_cards={
            "grounded_evidence_summary": {
                "summary_kind": "grounded_browser_evidence_summary",
                "card_count": 1,
                "cards": [{"title": "Polarized sunglasses"}],
            }
        },
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted, verified, stale_summary])

    assert context["completion_requirements"]["has_grounded_evidence_summary"] is True
    assert context["completion_requirements"]["has_objective_relevance_assessment"] is False
    assert context["finish_available"] is False
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.summarize_evidence"


def test_browser_research_proof_accepts_extraction_card_and_summary(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "one product card evaluated"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert decisions.contexts[-1]["objective_satisfied"] is True
    assert decisions.contexts[-1]["finish_available"] is True


def test_login_contact_payment_and_credential_actions_remain_hard_stops(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    blocked = [
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open", params={"url": "https://example.com/login"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.search", params={"query": "contact supplier"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.contact_supplier", params={}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.checkout", params={}),
    ]

    for envelope in blocked:
        with pytest.raises(RealBrowserControlRuntimeError):
            fixture.runtime.execute(envelope, authority=fixture.authority, context={})


def test_browser_replay_no_reopen_no_reclick_no_retype_no_resubmit_no_reextract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.search", params={"query": "glasses under 5 euro"}),
        authority=fixture.authority,
        context={},
    )
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context={},
    )

    replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert replay.browser_open_delta == 0
    assert replay.browser_click_delta == 0
    assert replay.browser_type_delta == 0
    assert replay.browser_press_delta == 0
    assert replay.browser_extract_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert loop_replay.real_browser_open_delta == 0
    assert loop_replay.real_browser_type_delta == 0
    assert loop_replay.real_browser_extract_delta == 0
    assert loop_replay.receipt_writes_delta == 0


def test_no_raw_dom_screenshot_cookie_session_provider_reasoning_persisted(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    persisted = _real_browser_artifact_text(fixture.kernel, fixture.mission_id).lower()

    for marker in ("raw_provider", "reasoning_content", "session_token", "screenshot", "<html", "<body"):
        assert marker not in persisted


def test_natural_intent_extract_visible_cards_maps_to_extract_product_cards(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will extract the visible product cards now.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "real_browser_control"
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_visible_product_cards_and_ambiguous_intent_maps_to_extract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])
    context["primary_model_recommended_next_action"] = "real_browser_control.real_browser.open"
    context["recommended_next_action"] = "real_browser_control.real_browser.search"

    mapping = map_browser_model_native_intent("I will continue with the visible results.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_open_intent_with_visible_cards_demotes_open_to_extract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will open the visible products and extract their details.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_natural_intent_search_under_price_maps_to_search_with_query(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent("Search for glasses under 5 euro.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "real_browser_control"
    assert mapping.envelope.operation == "real_browser.search"
    assert mapping.envelope.params["query"] == "glasses under 5 euro"


def test_natural_intent_verify_cards_maps_to_verify_extraction(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted])

    mapping = map_browser_model_native_intent("Verify the extracted cards.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.verify_extraction"


def test_natural_intent_finish_requires_verified_evidence(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    before_verify = _compile_browser_context(fixture, observations=[opened, extracted])

    premature = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=before_verify)

    assert premature.envelope is not None
    assert premature.envelope.operation == "real_browser.verify_extraction"

    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    after_verify = _compile_browser_context(fixture, observations=[opened, extracted, verified])

    summary = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=after_verify)

    assert summary.envelope is not None
    assert summary.envelope.capability_id == "sentinel_loop"
    assert summary.envelope.operation == "summarize_evidence"

    summary_result = fixture.action_kernel.execute(
        summary.envelope,
        authority=fixture.authority,
        context=after_verify,
    )
    after_summary = _compile_browser_context(fixture, observations=[opened, extracted, verified, summary_result])

    finish = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=after_summary)

    assert finish.envelope is not None
    assert finish.envelope.capability_id == "sentinel_loop"
    assert finish.envelope.operation == "finish"


def test_ambiguous_safe_intent_uses_primary_skill_recommendation(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will continue with the best safe next step.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"
    assert context["primary_model_recommended_next_action"] != (
        f"{mapping.envelope.capability_id}.{mapping.envelope.operation}"
    )


def test_safe_ambiguous_intent_without_recommendation_recovers_not_blocks() -> None:
    mapping = map_browser_model_native_intent(
        "I will continue with the best safe browser move.",
        context={
            "available_actions": [
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.extract_product_cards",
            ],
            "decision_context_primary_truth": "skill_decision_frame",
        },
    )

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.observe"
    assert mapping.safe_diagnostics["fallback_reason"] == "BROWSER_INTENT_NO_SAFE_RECOMMENDATION_RECOVERED"


def test_raw_browser_primitives_not_primary_model_schema(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])
    operation_schema = context["allowed_action_schema"]["operation"]

    assert "real_browser.search" in operation_schema
    assert "real_browser.extract_product_cards" in operation_schema
    assert "real_browser.verify_extraction" in operation_schema
    assert "real_browser.type_text" not in operation_schema
    assert "real_browser.click" not in operation_schema


def test_hidden_or_disabled_ref_recovers_but_secret_ref_hard_stops(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=InMemoryRealBrowserEngine())
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    for ref in ("button:hidden", "button:disabled"):
        result = fixture.runtime.execute(
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", target_ref=ref),
            authority=fixture.authority,
            context={},
        )
        assert result.recoverable is True
        assert result.failure_class is ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_secret_field_blocked"):
        fixture.runtime.execute(
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                target_ref="input:masked",
                params={"text": "not-a-secret"},
            ),
            authority=fixture.authority,
            context={},
        )


def test_hard_boundary_intent_blocks_contact_supplier_payment_login_credentials(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    context = _compile_browser_context(fixture, observations=[])

    for intent in (
        "Log in to Alibaba with credentials.",
        "Contact the supplier about this product.",
        "Add it to cart and checkout with payment.",
        "Use the cookie/session to continue.",
    ):
        mapping = map_browser_model_native_intent(intent, context=context)
        assert mapping.blocked is True
        assert mapping.blocked_reason == "BROWSER_INTENT_HARD_BOUNDARY"
        assert mapping.envelope is None


def test_metadata_reply_with_natural_intent_is_parsed_without_raw_persistence(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent(
        {
            "metadata": {"finish_reason": "stop"},
            "reply": "I will extract the visible product cards now.",
        },
        context=context,
    )

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"
    diagnostics_text = str(mapping.safe_diagnostics)
    assert "I will extract the visible product cards now" not in diagnostics_text
    assert "raw_provider" not in diagnostics_text
    assert "reasoning" not in diagnostics_text


def test_provider_empty_visible_content_before_material_action_recovers_or_blocks_cleanly(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent(
        {
            "content_extraction_source": "unsupported",
            "visible_content_char_count": 0,
            "raw_text_hash": "hash_only",
            "reasoning_hash": "reasoning_hash_only",
        },
        context=context,
    )

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == ""
    assert mapping.envelope.operation == ""
    assert mapping.safe_diagnostics["failure_code"] == "PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION"


def test_empty_visible_content_does_not_trigger_raw_open_without_recovery_context(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    empty_provider_payload = {
        "content_extraction_source": "unsupported",
        "visible_content_char_count": 0,
        "raw_text_hash": "hash_only",
    }
    decisions = _RawNativeIntentDecisionClient(
        [
            empty_provider_payload,
            empty_provider_payload,
            empty_provider_payload,
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_CORRECTION_BUDGET_EXHAUSTED"
    assert "real_browser_control:real_browser.open" not in result.capability_sequence
    assert result.failure_diagnostics["failure_code"] == "PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION"
    assert fixture.engine.open_count == 0


def test_action_envelope_remains_internal_runtime_format(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent("Search for glasses under 5 euro.", context=context)

    assert isinstance(mapping.envelope, ActionEnvelope)
    assert mapping.safe_diagnostics["model_input_kind"] == "natural_intent"
    assert mapping.safe_diagnostics["internal_runtime_format"] == "ActionEnvelope"


def test_no_raw_provider_output_or_reasoning_persisted(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent(
        {"reply": "Search for glasses under 5 euro.", "metadata": {"safe_provider_latency_ms": 12}},
        context=context,
    )

    persisted = str(mapping.safe_model_dump()).lower()
    assert "search for glasses under 5 euro" not in persisted
    assert "raw_provider" not in persisted
    assert "raw_response" not in persisted
    assert "reasoning_content" not in persisted


def test_replay_no_react_still_holds(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            {"metadata": {"finish_reason": "stop"}, "reply": "I will extract the visible product cards now."},
            {"reply": "Verify the extracted cards."},
            {"reply": "I have enough evidence, summarize and finish."},
            {"reply": "I have enough evidence, summarize and finish."},
        ]
    )

    result = fixture.loop(decisions).run()
    replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert replay.browser_open_delta == 0
    assert replay.browser_type_delta == 0
    assert replay.browser_extract_delta == 0
    assert replay.receipt_writes_delta == 0
    assert loop_replay.model_calls_delta == 0
    assert loop_replay.real_browser_open_delta == 0
    assert loop_replay.real_browser_extract_delta == 0


def test_loop_guard_does_not_preempt_first_extraction_when_cards_visible(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            "I have enough evidence, summarize and finish.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert "real_browser_control:real_browser.search" in result.capability_sequence
    assert "real_browser_control:real_browser.extract_product_cards" in result.capability_sequence
    assert result.receipt_refs


def test_finalgate_not_written_for_recoverable_pre_extraction_miss(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            "I have enough evidence, summarize and finish.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()
    mission_text = _mission_text(fixture.kernel, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "RECOVERY_BUDGET_EXHAUSTED" not in mission_text
    assert "BROWSER_INTENT_NO_SAFE_RECOMMENDATION" not in mission_text
    assert "model_led_task_loop_blocked" not in mission_text


def test_pack_a_f_regressions_still_pass() -> None:
    actionability_frame = build_default_actionability_registry().compile_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )
    backend_frame = build_default_power_skill_registry().compile_backend_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )

    assert actionability_frame.invariant == "model_visible_actions_require_executor_authority_proof_and_recovery_policy"
    assert _backend_by_skill(backend_frame, "real_browser_control")["proof_contract"] == "RealBrowserActionReceipt"


def _backend_by_skill(frame: dict[str, Any], skill_id: str) -> dict[str, Any]:
    for backend in frame.get("skill_backends", []):
        if backend.get("skill_id") == skill_id:
            return backend
    raise AssertionError(f"missing backend for {skill_id}")


def _browser_actions() -> tuple[str, ...]:
    return (
        "real_browser_control.real_browser.open",
        "real_browser_control.real_browser.observe",
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.open_result",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
        "real_browser_control.real_browser.extract_text",
        "real_browser_control.real_browser.assert_text",
        "real_browser_control.real_browser.click",
        "real_browser_control.real_browser.type_text",
        "real_browser_control.real_browser.press_key",
        "real_browser_control.real_browser.wait_for_text",
        "sentinel_loop.summarize_evidence",
        "sentinel_loop.finish",
    )


def _compile_browser_context(
    fixture: "_BrowserSkillFixture",
    *,
    observations: list[Any],
    model_calls_used: int = 0,
    material_actions_used: int = 0,
    recovery_turns_used: int = 0,
    max_recovery_turns: int = 2,
) -> dict[str, Any]:
    return DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=observations,
        available_actions=_browser_actions(),
        model_calls_used=model_calls_used,
        material_actions_used=material_actions_used,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=recovery_turns_used,
        max_recovery_turns=max_recovery_turns,
        correction_turns_used=0,
        max_correction_turns=2,
    )


class _RawNativeIntentDecisionClient:
    def __init__(self, intents: list[Any]) -> None:
        self._intents = list(intents)
        self.call_count = 0
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> Any:
        self.contexts.append(context)
        self.call_count += 1
        if not self._intents:
            raise AssertionError("native intent decisions exhausted")
        return self._intents.pop(0)


class _FakeBrowserSessionManager:
    backend_kind = "cloakbrowser"

    def __init__(self) -> None:
        self.open_calls = 0
        self.observe_calls = 0
        self.devtools_calls: list[str] = []
        self.interact_calls: list[tuple[str, str, str]] = []
        self._session_id = "fake_bsess_cloak"
        self._searched = False

    def open_session(self, request: Any) -> Any:
        self.open_calls += 1
        return self._result(request, action_kind="open")

    def observe(self, request: Any) -> Any:
        self.observe_calls += 1
        return self._result(request, action_kind="observe")

    def interact(self, request: Any) -> Any:
        action = _request_value(request, "action_kind")
        target = _request_value(request, "target_name") or _request_value(request, "target_role") or ""
        text = _request_value(request, "text") or ""
        self.interact_calls.append((str(action), str(target), str(text)))
        if str(action) in {"fill", "type"} and text:
            self._searched = True
        if str(action) == "wait_for_text":
            self._searched = True
        return self._result(request, action_kind=str(action))

    def _result(self, request: Any, *, action_kind: str) -> Any:
        text = _PRODUCT_TEXT if self._searched else "Catalog search page. Search products."
        elements = (
            RealBrowserEngineElement("input:search", "textbox", "Search products", value_preview="glasses under 5 euro" if self._searched else ""),
            RealBrowserEngineElement("button:search", "button", "Search", text_preview="Search"),
            RealBrowserEngineElement(
                "link:glasses_card",
                "link",
                "Polarized sunglasses $4.80 MOQ 10 pieces",
                text_preview="Polarized sunglasses $4.80 MOQ 10 pieces Yiwu Test Store shipping not included" if self._searched else "",
                visible=self._searched,
                enabled=self._searched,
            ),
        )
        receipt = SimpleNamespace(
            backend_kind=self.backend_kind,
            action_kind=action_kind,
            session_id=self._session_id,
            safe_summary=text,
            page_title="Alibaba fake catalog",
            page_state_hash=f"fake_cloak_state_{action_kind}_{int(self._searched)}",
            elements=elements,
        )
        return SimpleNamespace(
            accepted=True,
            status="executed",
            reason=f"fake_{action_kind}",
            session_id=self._session_id,
            receipt=receipt,
        )

    def devtools_metadata_for_session(
        self,
        *,
        mission_id: str,
        session_id: str,
        capability: str,
        timeout_ms: int = 15_000,
    ) -> dict[str, Any] | None:
        del mission_id, timeout_ms
        if session_id != self._session_id:
            return None
        self.devtools_calls.append(capability)
        return {
            "backend_kind": self.backend_kind,
            "page_target_count": 1,
            "snapshot_hash": "fake_a11y_snapshot_hash",
            "screenshot_hash": None,
            "network_ledger_hash": "fake_network_ledger_hash" if capability == "network_ledger" else None,
            "console_ledger_hash": "fake_console_ledger_hash" if capability == "console_ledger" else None,
            "performance_trace_hash": "fake_performance_trace_hash" if capability == "performance_trace" else None,
            "safe_metadata": {
                "source_backend_kind": self.backend_kind,
                "session_ref": "hashed_session_ref_only",
                "url_hash": "url_hash_only",
                "title_hash": "title_hash_only",
                "step_index": 1,
                "network_event_count": 2,
                "network_failure_count": 0,
                "console_message_count": 2,
                "console_error_count": 1,
            },
        }


class _FailingDevToolsBrowserSessionManager(_FakeBrowserSessionManager):
    def devtools_metadata_for_session(
        self,
        *,
        mission_id: str,
        session_id: str,
        capability: str,
        timeout_ms: int = 15_000,
    ) -> dict[str, Any] | None:
        del mission_id, session_id, capability, timeout_ms
        raise RuntimeError("raw_devtools_stack_should_not_persist")


def _request_value(request: Any, name: str) -> Any:
    value = getattr(request, name, None)
    if value is None and isinstance(request, dict):
        value = request.get(name)
    if hasattr(value, "value"):
        return value.value
    return value


class _BrowserSkillFixture:
    def __init__(
        self,
        tmp_path: Path,
        *,
        engine: Any,
        backend_selection: Any | None = None,
        selected_backend_id: str | None = None,
    ) -> None:
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack6d",
            draft=MissionDraft(
                title="Model-led browser skill spine",
                objective="Search a bounded catalog page for glasses under 5 EUR and extract one relevant product card.",
                constraints=["bounded browser URL", "receipts always", "no login/contact/payment"],
                expected_artifacts=["real browser action receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack6d",
                allowed_actions=[
                    "real_browser.open",
                    "real_browser.observe",
                    "real_browser.search",
                    "real_browser.inspect_result",
                    "real_browser.open_result",
                    "real_browser.extract_product_cards",
                    "real_browser.verify_extraction",
                    "real_browser.extract_text",
                    "real_browser.assert_text",
                    "real_browser.click",
                    "real_browser.type_text",
                    "real_browser.press_key",
                    "real_browser.wait_for_text",
                    "finish",
                ],
                forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
                summary="Bounded browser skill search/extraction is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.engine = engine
        runtime_kwargs: dict[str, Any] = {
            "kernel": self.kernel,
            "mission_id": self.mission_id,
            "engine": self.engine,
            "bounded_url_ref": "env:SENTINEL_BROWSER_TEST_URL",
        }
        if backend_selection is not None:
            runtime_kwargs["browser_backend_selection"] = backend_selection
        if selected_backend_id is not None:
            runtime_kwargs["selected_backend_id"] = selected_backend_id
        self.runtime = RealBrowserControlRuntime(**runtime_kwargs)
        self.action_kernel = ActionKernel(
            executors={
                "real_browser_control": lambda envelope, context: self.runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                )
            }
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led browser skill spine",
            mission_objective="Search a bounded catalog page for glasses under 5 EUR and extract one relevant product card.",
            allowed_tools=["real_browser_control"],
            allowed_actions=[action.replace("real_browser_control.", "") for action in _browser_actions() if action != "sentinel_loop.finish"]
            + ["finish"],
            forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
            allowed_domains=["real_browser:bounded_test_url"],
            max_actions=12,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

    def loop(self, decisions: ModelLedTaskDecisionClient, *, max_recovery_turns: int = 2) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decisions,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=8, max_material_actions=4, max_recovery_turns=max_recovery_turns)),
            available_actions=_browser_actions(),
        )

    def load_action_receipt(self, receipt_ref: str) -> dict[str, Any]:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        import json

        return json.loads(path.read_text(encoding="utf-8"))


class _HardProductSearchEngine(InMemoryRealBrowserEngine):
    def __init__(self, *, results_visible: bool = True) -> None:
        super().__init__()
        self.search_query = ""
        self.results_visible = results_visible
        self.display_text = "Catalog search page."
        if results_visible:
            self.display_text = _PRODUCT_TEXT

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        elements = [
            RealBrowserEngineElement("input:search", "textbox", "Search products", value_preview=self.search_query),
            RealBrowserEngineElement("button:search", "button", "Search", text_preview="Search"),
        ]
        if self.results_visible:
            elements.append(
                RealBrowserEngineElement(
                    "link:glasses_card",
                    "link",
                    "Polarized sunglasses $4.80 MOQ 10 pieces",
                    text_preview="Polarized sunglasses $4.80 MOQ 10 pieces Yiwu Test Store shipping not included",
                )
            )
        elements.append(RealBrowserEngineElement("input:secret", "textbox", "password", secret=True))
        return tuple(elements)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self._require_editable(ref)
        self.type_count += 1
        self.search_query = text
        self.status_value = text
        return self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        self._require_editable(ref)
        self.press_count += 1
        if key == "Enter" and self.search_query:
            self.results_visible = True
            self.display_text = _PRODUCT_TEXT
        return self._snapshot()

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        element = self._require_interactable(ref)
        self.click_count += 1
        if element.ref == "button:search" and self.search_query:
            self.results_visible = True
            self.display_text = _PRODUCT_TEXT
        return self._snapshot()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self._require_open()
        self.extract_count += 1
        return self.display_text, self._snapshot()


class _AlternateSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=False)
        self.attempted_refs: list[str] = []

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:broken_search", "textbox", "Search broken"),
            *super()._elements(),
        )

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self.attempted_refs.append(ref)
        if ref == "input:broken_search":
            raise RealBrowserControlRuntimeError("real_browser_locator_timeout")
        return super().type_text(ref, text)


class _TimeoutSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=False)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        del ref, text
        raise RealBrowserControlRuntimeError("real_browser_locator_timeout")


class _TimeoutSearchEngineWithCards(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=True)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        del ref, text
        raise RealBrowserControlRuntimeError("real_browser_locator_timeout")


class _SparseProductSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=True)
        self.display_text = "Minimal glasses listing"

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:search", "textbox", "Search products", value_preview=self.search_query),
            RealBrowserEngineElement("link:sparse", "link", "Minimal glasses listing", text_preview="Minimal glasses listing"),
        )


class _IrrelevantProductSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=True)
        self.display_text = (
            "Search results for glasses under 5 euro. "
            "Industrial steel bolts. Price EUR 1.20 per unit. MOQ 100 pieces. "
            "Supplier Hardware Test Store."
        )

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:search", "textbox", "Search products", value_preview=self.search_query),
            RealBrowserEngineElement(
                "link:bolts",
                "link",
                "Industrial steel bolts EUR 1.20 MOQ 100 pieces",
                text_preview="Industrial steel bolts EUR 1.20 MOQ 100 pieces Supplier Hardware Test Store",
            ),
        )


class _PlaywrightCompatibilitySearchEngine(_HardProductSearchEngine):
    browser_backend_id = "playwright_real_browser_engine"


_PRODUCT_TEXT = (
    "Search results for glasses under 5 euro. Polarized sunglasses. "
    "Price $4.80 per piece. MOQ 10 pieces. Supplier Yiwu Test Store. "
    "Caveats: shipping not included, customization unclear."
)


def _mission_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


def _real_browser_artifact_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id) / "real_browser_control"
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
