from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_session_live"
URL = "https://example.com/session"
HTML = """
<html>
  <head><title>Session Browser</title></head>
  <body>
    <main>
      <h1>Operator Console</h1>
      <input type="text" placeholder="Email" />
      <button>Remember</button>
    </main>
  </body>
</html>
"""
SECOND_URL = "https://example.com/research"
SECOND_HTML = """
<html>
  <head><title>Research</title></head>
  <body><main><h1>Research Evidence</h1><button>Pin evidence</button></main></body>
</html>
"""
_PLAYWRIGHT_COMPAT_AVAILABLE: bool | None = None
_PLAYWRIGHT_COMPAT_SKIP_REASON = "playwright compatibility browser is not launchable in this environment"


def _require_playwright_compat_browser() -> None:
    global _PLAYWRIGHT_COMPAT_AVAILABLE
    if _PLAYWRIGHT_COMPAT_AVAILABLE is False:
        pytest.skip(_PLAYWRIGHT_COMPAT_SKIP_REASON)
    if _PLAYWRIGHT_COMPAT_AVAILABLE is True:
        return
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception:
        _PLAYWRIGHT_COMPAT_AVAILABLE = False
        pytest.skip(_PLAYWRIGHT_COMPAT_SKIP_REASON)
    _PLAYWRIGHT_COMPAT_AVAILABLE = True


def _envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_session_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Live browser session mission",
        mission_objective="Operate one governed public browser session.",
        success_criteria=["Session receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live"],
        allowed_actions=["browser_session_open", "browser_session_observe", "browser_session_interact", "browser_session_close"],
        forbidden_actions=[
            "browser_submit_form",
            "browser_login_authority",
            "browser_upload_authorized",
            "browser_download_quarantine",
            "browser_js_evaluate_sandboxed",
            "credential_access",
        ],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


class _FallbackLocator:
    def __init__(self, page: "_FallbackRolePage", *, role: str, name: str | None, exact: bool | None, nth: int) -> None:
        self.page = page
        self.role = role
        self.name = name
        self.exact = exact
        self.nth = nth

    def fill(self, text: str, *, timeout: int) -> None:
        if self.exact is True:
            raise TimeoutError("exact role/name locator missed")
        self.page.fills.append({"role": self.role, "name": self.name, "exact": self.exact, "nth": self.nth, "text": text, "timeout": timeout})

    def press(self, key: str, *, timeout: int) -> None:
        self.page.presses.append({"role": self.role, "name": self.name, "exact": self.exact, "nth": self.nth, "key": key, "timeout": timeout})


class _FallbackRoleQuery:
    def __init__(self, page: "_FallbackRolePage", *, role: str, name: str | None, exact: bool | None) -> None:
        self.page = page
        self.role = role
        self.name = name
        self.exact = exact

    def nth(self, nth: int) -> _FallbackLocator:
        return _FallbackLocator(self.page, role=self.role, name=self.name, exact=self.exact, nth=nth)


class _FallbackRolePage:
    def __init__(self) -> None:
        self.role_calls: list[dict[str, Any]] = []
        self.fills: list[dict[str, Any]] = []
        self.presses: list[dict[str, Any]] = []

    def get_by_role(self, role: str, *, name: str | None = None, exact: bool | None = None) -> _FallbackRoleQuery:
        self.role_calls.append({"role": role, "name": name, "exact": exact})
        return _FallbackRoleQuery(self, role=role, name=name, exact=exact)


class _FallbackSession:
    def __init__(self, page: _FallbackRolePage) -> None:
        self.page = page


class _KeyboardRecorder:
    def __init__(self) -> None:
        self.presses: list[dict[str, Any]] = []

    def press(self, key: str) -> None:
        self.presses.append({"key": key})


class _KeyboardFallbackLocator(_FallbackLocator):
    def press(self, key: str, *, timeout: int) -> None:
        self.page.presses.append({"role": self.role, "name": self.name, "exact": self.exact, "nth": self.nth, "key": key, "timeout": timeout})
        raise TimeoutError("role locator detached after focus")


class _KeyboardFallbackRoleQuery(_FallbackRoleQuery):
    def nth(self, nth: int) -> _KeyboardFallbackLocator:
        return _KeyboardFallbackLocator(self.page, role=self.role, name=self.name, exact=self.exact, nth=nth)


class _KeyboardFallbackPage(_FallbackRolePage):
    def __init__(self) -> None:
        super().__init__()
        self.keyboard = _KeyboardRecorder()

    def get_by_role(self, role: str, *, name: str | None = None, exact: bool | None = None) -> _KeyboardFallbackRoleQuery:
        self.role_calls.append({"role": role, "name": name, "exact": exact})
        return _KeyboardFallbackRoleQuery(self, role=role, name=name, exact=exact)


class _RoleOnlyFallbackLocator(_FallbackLocator):
    def fill(self, text: str, *, timeout: int) -> None:
        if self.name is not None:
            raise TimeoutError("named role locator missed")
        self.page.fills.append({"role": self.role, "name": self.name, "exact": self.exact, "nth": self.nth, "text": text, "timeout": timeout})


class _RoleOnlyFallbackRoleQuery(_FallbackRoleQuery):
    def nth(self, nth: int) -> _RoleOnlyFallbackLocator:
        return _RoleOnlyFallbackLocator(self.page, role=self.role, name=self.name, exact=self.exact, nth=nth)


class _RoleOnlyFallbackPage(_FallbackRolePage):
    def get_by_role(self, role: str, *, name: str | None = None, exact: bool | None = None) -> _RoleOnlyFallbackRoleQuery:
        self.role_calls.append({"role": role, "name": name, "exact": exact})
        return _RoleOnlyFallbackRoleQuery(self, role=role, name=name, exact=exact)


class _EditableFallbackLocator(_FallbackLocator):
    def fill(self, text: str, *, timeout: int) -> None:
        self.page.fills.append({"role": self.role, "name": self.name, "exact": self.exact, "nth": self.nth, "text": text, "timeout": timeout})


class _EditableFallbackQuery:
    def __init__(self, page: "_EditableFallbackPage", selector: str) -> None:
        self.page = page
        self.selector = selector

    def nth(self, nth: int) -> _EditableFallbackLocator:
        self.page.locator_nths.append({"selector_len": len(self.selector), "nth": nth})
        return _EditableFallbackLocator(self.page, role="css_editable", name=None, exact=None, nth=nth)


class _EditableRoleFailureLocator(_FallbackLocator):
    def fill(self, text: str, *, timeout: int) -> None:
        del text, timeout
        raise TimeoutError("role locator was not editable")


class _EditableRoleFailureQuery(_FallbackRoleQuery):
    def nth(self, nth: int) -> _EditableRoleFailureLocator:
        return _EditableRoleFailureLocator(self.page, role=self.role, name=self.name, exact=self.exact, nth=nth)


class _EditableFallbackPage(_FallbackRolePage):
    def __init__(self) -> None:
        super().__init__()
        self.locator_calls: list[str] = []
        self.locator_nths: list[dict[str, Any]] = []

    def get_by_role(self, role: str, *, name: str | None = None, exact: bool | None = None) -> _EditableRoleFailureQuery:
        self.role_calls.append({"role": role, "name": name, "exact": exact})
        return _EditableRoleFailureQuery(self, role=role, name=name, exact=exact)

    def locator(self, selector: str) -> _EditableFallbackQuery:
        self.locator_calls.append(selector)
        return _EditableFallbackQuery(self, selector)


class _BodyTextLocator:
    def inner_text(self, *, timeout: int) -> str:
        del timeout
        return "Search"


class _HiddenActionabilityLocator:
    def count(self) -> int:
        return 0

    def nth(self, nth: int) -> "_HiddenActionabilityLocator":
        del nth
        return self

    def is_visible(self, *, timeout: int) -> bool:
        del timeout
        return False

    def is_enabled(self, *, timeout: int) -> bool:
        del timeout
        return False


class _HiddenSearchActionabilityPage:
    def content(self) -> str:
        return '<html><body><input type="search" aria-label="Search documentation" style="display:none" /></body></html>'

    def locator(self, selector: str) -> _BodyTextLocator:
        del selector
        return _BodyTextLocator()

    def get_by_role(self, role: str, *, name: str | None = None, exact: bool | None = None) -> _FallbackRoleQuery:
        del role, name, exact
        return _HiddenActionabilityLocator()


class _LifecycleLocator:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def inner_text(self, *, timeout: int) -> str:
        del timeout
        return self._text

    def count(self) -> int:
        return 0

    def nth(self, index: int) -> "_LifecycleLocator":
        del index
        return self

    def get_attribute(self, name: str, *, timeout: int) -> str | None:
        del name, timeout
        return None

    def input_value(self, *, timeout: int) -> str:
        del timeout
        return ""


class _LifecycleFakeContext:
    def __init__(self, backend: "_LifecycleFakeBackend") -> None:
        self.backend = backend
        self.closed = False

    def new_page(self) -> "_LifecycleFakePage":
        return _LifecycleFakePage(self)

    def clear_cookies(self) -> None:
        return None

    def clear_permissions(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True
        self.backend.close_count += 1


class _LifecycleFakePage:
    def __init__(self, context: _LifecycleFakeContext) -> None:
        self.context = context
        self.url = URL

    def content(self) -> str:
        return HTML

    def locator(self, selector: str) -> _LifecycleLocator:
        if selector == "body":
            return _LifecycleLocator("Operator Console")
        return _LifecycleLocator()


class _LifecycleFakeBackend:
    backend_kind = "cloakbrowser"

    def __init__(self, *, fail_on_open_numbers: set[int] | None = None) -> None:
        self.fail_on_open_numbers = fail_on_open_numbers or set()
        self.open_count = 0
        self.close_count = 0
        self.profile_dir_hashes: list[str] = []

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ) -> Any:
        from sentinel.agent.model_execution.redaction import stable_hash
        from sentinel.organs.browser.cloak_backend import BrowserEngineSession, BrowserSessionEngineError

        del url, timeout_ms, viewport_width, viewport_height
        self.open_count += 1
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "ephemeral_profile_lock").write_text("profile material", encoding="utf-8")
        self.profile_dir_hashes.append(stable_hash(str(profile_dir)))
        if self.open_count in self.fail_on_open_numbers:
            raise BrowserSessionEngineError("fake_engine_open_failed")
        context = _LifecycleFakeContext(self)
        return BrowserEngineSession(
            backend_kind=self.backend_kind,
            context=context,
            page=context.new_page(),
            profile_dir=profile_dir,
        )


def _profile_material_paths(capture_root: Path) -> list[Path]:
    if not capture_root.exists():
        return []
    paths: list[Path] = []
    for path in capture_root.rglob("*"):
        if not path.is_file():
            continue
        if "profile" in {part.lower() for part in path.relative_to(capture_root).parts}:
            paths.append(path)
    return paths


def test_live_browser_session_falls_back_from_exact_role_name_to_fuzzy_same_role(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.FILL],
    )
    page = _FallbackRolePage()
    request = BrowserSessionRequest(
        mission=_envelope(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.FILL,
        target_role="textbox",
        target_name="Search all products",
        text="glasses under 5 euro",
        capture_screenshot=False,
    )

    manager._execute_step(_FallbackSession(page), request, timeout_ms=250)

    assert page.role_calls == [
        {"role": "textbox", "name": "Search all products", "exact": True},
        {"role": "textbox", "name": "Search all products", "exact": False},
        {"role": "textbox", "name": None, "exact": None},
    ]
    assert page.fills == [
        {"role": "textbox", "name": "Search all products", "exact": False, "nth": 0, "text": "glasses under 5 euro", "timeout": 250}
    ]


def test_live_browser_session_falls_back_to_role_only_when_accessible_name_drifts(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.FILL],
    )
    page = _RoleOnlyFallbackPage()
    request = BrowserSessionRequest(
        mission=_envelope(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.FILL,
        target_role="searchbox",
        target_name="Search documentation",
        target_nth=0,
        text="path glob",
        capture_screenshot=False,
    )

    manager._execute_step(_FallbackSession(page), request, timeout_ms=250)

    assert page.role_calls == [
        {"role": "searchbox", "name": "Search documentation", "exact": True},
        {"role": "searchbox", "name": "Search documentation", "exact": False},
        {"role": "searchbox", "name": None, "exact": None},
    ]
    assert page.fills == [{"role": "searchbox", "name": None, "exact": None, "nth": 0, "text": "path glob", "timeout": 250}]


def test_live_browser_session_falls_back_to_editable_field_when_search_role_is_not_fillable(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.FILL],
    )
    page = _EditableFallbackPage()
    request = BrowserSessionRequest(
        mission=_envelope(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.FILL,
        target_role="combobox",
        target_name="Search documentation",
        target_nth=0,
        text="path glob",
        capture_screenshot=False,
    )

    manager._execute_step(_FallbackSession(page), request, timeout_ms=250)

    assert page.locator_calls
    assert page.fills == [{"role": "css_editable", "name": None, "exact": None, "nth": 0, "text": "path glob", "timeout": 250}]


def test_live_browser_session_snapshot_marks_static_hidden_search_refs_not_visible() -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionManagerL5Live

    snapshot = BrowserSessionManagerL5Live._snapshot(_HiddenSearchActionabilityPage(), timeout_ms=250)
    search_ref = next(ref for ref in snapshot.refs.values() if ref.role == "searchbox")

    assert getattr(search_ref, "visible", None) is False
    assert getattr(search_ref, "enabled", None) is False


def test_live_browser_session_promotes_press_key_for_search_submit(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.PRESS_KEY],
    )
    page = _FallbackRolePage()
    request = BrowserSessionRequest(
        mission=_envelope(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.PRESS_KEY,
        target_role="textbox",
        target_name="Search all products",
        text="Enter",
        capture_screenshot=False,
    )

    manager._execute_step(_FallbackSession(page), request, timeout_ms=250)

    assert page.presses == [
        {"role": "textbox", "name": "Search all products", "exact": True, "nth": 0, "key": "Enter", "timeout": 250}
    ]


def test_live_browser_session_press_key_uses_page_keyboard_after_locator_detaches(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.PRESS_KEY],
    )
    page = _KeyboardFallbackPage()
    request = BrowserSessionRequest(
        mission=_envelope(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.PRESS_KEY,
        target_role="textbox",
        target_name="Search all products",
        text="Enter",
        capture_screenshot=False,
    )

    manager._execute_step(_FallbackSession(page), request, timeout_ms=250)

    assert page.presses == [
        {"role": "textbox", "name": "Search all products", "exact": True, "nth": 0, "key": "Enter", "timeout": 250},
        {"role": "textbox", "name": "Search all products", "exact": False, "nth": 0, "key": "Enter", "timeout": 250},
        {"role": "textbox", "name": None, "exact": None, "nth": 0, "key": "Enter", "timeout": 250},
    ]
    assert page.keyboard.presses == [{"key": "Enter"}]


def test_live_browser_session_persists_form_state_across_steps(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE, BrowserSessionActionKind.CLICK],
        max_steps=5,
    )

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        typed = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role="textbox",
                target_name="Email",
                text="founder@example.com",
            )
        )
        observed = manager.observe(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
            )
        )
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
            )
        )
        assert opened.accepted is True
        assert typed.accepted is True
        assert observed.accepted is True
        assert closed.accepted is True
        assert typed.receipt.before_snapshot_hash
        assert typed.receipt.after_snapshot_hash
        assert typed.finalgate_certificate is not None
        assert typed.receipt.finalgate_certificate_id == typed.finalgate_certificate.certificate_id
        assert typed.receipt.finalgate_verified is True
        assert typed.receipt.session_id == opened.session_id
        assert observed.receipt.form_state_summary_hash == typed.receipt.form_state_summary_hash
        assert observed.receipt.form_state_summary == [{"name": "Email", "role": "textbox", "value_hash": typed.receipt.typed_text_hash}]
        assert closed.receipt.closed is True
        assert list((tmp_path / "browser").rglob("*_screenshot.png"))
    finally:
        manager.close_all()


def test_live_browser_session_promotes_bounded_multitab_with_receipts(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML, SECOND_URL: SECOND_HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[
            BrowserSessionActionKind.OPEN_TAB,
            BrowserSessionActionKind.SWITCH_TAB,
            BrowserSessionActionKind.CLOSE_TAB,
        ],
        max_steps=8,
        max_tabs=2,
    )

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        new_tab = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=SECOND_URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.OPEN_TAB,
            )
        )
        overflow = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=SECOND_URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.OPEN_TAB,
            )
        )
        switched = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.SWITCH_TAB,
                tab_id=opened.receipt.tab_id,
            )
        )
        closed = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=SECOND_URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLOSE_TAB,
                tab_id=new_tab.receipt.tab_id,
            )
        )

        assert new_tab.accepted is True
        assert new_tab.receipt.tab_count == 2
        assert new_tab.receipt.tab_id != opened.receipt.tab_id
        assert overflow.accepted is False
        assert overflow.reason == "browser_session_tab_limit_reached"
        assert switched.accepted is True
        assert switched.receipt.tab_id == opened.receipt.tab_id
        assert closed.accepted is True
        assert closed.receipt.tab_count == 1
        assert all(
            result.finalgate_certificate is not None and result.finalgate_certificate.certified
            for result in (new_tab, overflow, switched, closed)
        )
    finally:
        manager.close_all()


def test_live_browser_session_multitab_does_not_cross_mission_boundary(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML, SECOND_URL: SECOND_HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.OPEN_TAB],
        max_tabs=2,
    )
    other_mission = _envelope().model_copy(update={"id": "mission_browser_session_other"})

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        forged = manager.interact(
            BrowserSessionRequest.model_construct(
                mission=other_mission,
                url=SECOND_URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.OPEN_TAB,
                target_nth=0,
                values=[],
                timeout_ms=15_000,
                capture_screenshot=True,
                authority_effect="none",
                execution_effect="none",
                can_grant_authority=False,
                can_approve_future_execution=False,
                data_not_instruction=True,
            )
        )

        assert forged.accepted is False
        assert forged.reason == "contract_mission_mismatch"
    finally:
        manager.close_all()


@pytest.mark.parametrize(
    ("mission_update", "expected_reason"),
    [
        ({"revoked_at": datetime.now(UTC)}, "mission_authority_revoked"),
        ({"expires_at": datetime.now(UTC) - timedelta(seconds=1)}, "mission_authority_expired"),
    ],
)
def test_live_browser_session_rechecks_revocation_and_expiry_before_each_step(
    tmp_path: Path,
    mission_update: dict[str, object],
    expected_reason: str,
) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.CLICK],
    )
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        blocked = manager.interact(
            BrowserSessionRequest(
                mission=_envelope().model_copy(update=mission_update),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLICK,
                target_role="button",
                target_name="Remember",
            )
        )

        assert blocked.accepted is False
        assert blocked.reason == expected_reason
        assert blocked.receipt.finalgate_verified is True
        assert blocked.finalgate_certificate is not None
        assert blocked.finalgate_certificate.certified is True
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=_envelope().model_copy(update=mission_update),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
            )
        )
        assert closed.accepted is True
        assert closed.receipt.closed is True
    finally:
        manager.close_all()


def test_live_browser_session_enforces_bounded_interaction_steps(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.CLICK],
        max_steps=1,
    )
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        first = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLICK,
                target_role="button",
                target_name="Remember",
            )
        )
        overflow = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLICK,
                target_role="button",
                target_name="Remember",
            )
        )

        assert first.accepted is True
        assert overflow.accepted is False
        assert overflow.reason == "browser_session_step_limit_reached"
        assert overflow.receipt.step_index == 1
    finally:
        manager.close_all()


def test_live_browser_session_rejects_contract_expansion_after_open(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.CLICK],
        max_steps=1,
        max_tabs=1,
    )
    expanded = contract.model_copy(update={"max_steps": 10, "max_tabs": 4})
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        blocked = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=expanded,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLICK,
                target_role="button",
                target_name="Remember",
            )
        )

        assert blocked.accepted is False
        assert blocked.reason == "browser_session_contract_mismatch"
    finally:
        manager.close_all()


def test_cloakbrowser_backend_is_primary_and_uses_persistent_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sentinel.organs.browser.cloak_backend import CloakBrowserSessionBackend

    calls: list[dict[str, object]] = []

    class _FakeResponse:
        status = 200

    class _FakePage:
        def route(self, *_args: object, **_kwargs: object) -> None:
            return None

        def goto(self, url: str, **kwargs: object) -> _FakeResponse:
            calls.append({"url": url, **kwargs})
            return _FakeResponse()

    class _FakeContext:
        def new_page(self) -> _FakePage:
            return _FakePage()

        def close(self) -> None:
            calls.append({"closed": True})

    def _launch_persistent_context(user_data_dir: str, **kwargs: object) -> _FakeContext:
        calls.append({"user_data_dir": user_data_dir, **kwargs})
        return _FakeContext()

    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_persistent_context=_launch_persistent_context),
    )

    backend = CloakBrowserSessionBackend(headless=True, humanize=True, stealth_args=True)
    session = backend.open_context(
        profile_dir=tmp_path / "profile",
        url=URL,
        timeout_ms=5_000,
        viewport_width=1440,
        viewport_height=1000,
    )

    assert session.backend_kind == "cloakbrowser"
    assert calls[0]["user_data_dir"] == str(tmp_path / "profile")
    assert calls[0]["humanize"] is True
    assert calls[0]["stealth_args"] is True
    assert calls[0]["accept_downloads"] is False
    assert calls[0]["viewport"] == {"width": 1440, "height": 1000}
    session.close()
    assert calls[-1] == {"closed": True}


def test_cloakbrowser_backend_closes_partial_context_when_page_creation_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sentinel.organs.browser.cloak_backend import BrowserSessionEngineError, CloakBrowserSessionBackend

    calls: list[dict[str, object]] = []

    class _BrokenContext:
        def new_page(self) -> object:
            raise RuntimeError("page creation failed after process launch")

        def close(self) -> None:
            calls.append({"closed": True})

    def _launch_persistent_context(user_data_dir: str, **kwargs: object) -> _BrokenContext:
        del user_data_dir, kwargs
        return _BrokenContext()

    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_persistent_context=_launch_persistent_context),
    )

    backend = CloakBrowserSessionBackend(headless=True)

    with pytest.raises(BrowserSessionEngineError, match="cloakbrowser_open_failed"):
        backend.open_context(
            profile_dir=tmp_path / "profile",
            url=URL,
            timeout_ms=5_000,
            viewport_width=1440,
            viewport_height=1000,
        )

    assert calls == [{"closed": True}]


def test_default_engine_is_cloak_and_never_silently_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    monkeypatch.setitem(sys.modules, "cloakbrowser", None)
    manager = BrowserSessionManagerL5Live(capture_root=tmp_path / "browser", document_fixtures={URL: HTML})
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    result = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

    assert result.accepted is False
    assert result.receipt.backend_kind == "cloakbrowser"
    assert result.reason.startswith("cloakbrowser_not_installed")


def test_live_browser_session_sequential_reopen_cycles_cleanup_profile_material(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    from sentinel.organs.browser.cloak_backend import BrowserSessionEngineError

    backend = _LifecycleFakeBackend()
    manager = BrowserSessionManagerL5Live(capture_root=tmp_path / "browser", backend=backend)
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    for _ in range(3):
        opened = manager.open_session(
            BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
        )
        observed = manager.observe(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                capture_screenshot=False,
            )
        )
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                capture_screenshot=False,
            )
        )

        assert opened.accepted is True
        assert observed.accepted is True
        assert closed.accepted is True
        assert closed.receipt.closed is True

    assert backend.open_count == 3
    assert backend.close_count == 3
    assert len(set(backend.profile_dir_hashes)) == 3
    assert _profile_material_paths(tmp_path / "browser") == []
    assert manager.open_session(
        BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
    ).accepted is True
    manager.close_all()
    assert _profile_material_paths(tmp_path / "browser") == []


def test_live_browser_session_reopen_failure_cleans_profile_and_next_open_is_clean(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    backend = _LifecycleFakeBackend(fail_on_open_numbers={2})
    manager = BrowserSessionManagerL5Live(capture_root=tmp_path / "browser", backend=backend)
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    first = manager.open_session(
        BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
    )
    manager.close_session(
        BrowserSessionRequest(
            mission=_envelope(),
            url=URL,
            contract=contract,
            session_id=first.session_id,
            capture_screenshot=False,
        )
    )
    failed_reopen = manager.open_session(
        BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
    )
    assert _profile_material_paths(tmp_path / "browser") == []
    clean_reopen = manager.open_session(
        BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
    )

    assert first.accepted is True
    assert failed_reopen.accepted is False
    assert failed_reopen.reason == "fake_engine_open_failed"
    assert clean_reopen.accepted is True
    assert backend.open_count == 3
    manager.close_session(
        BrowserSessionRequest(
            mission=_envelope(),
            url=URL,
            contract=contract,
            session_id=clean_reopen.session_id,
            capture_screenshot=False,
        )
    )
    manager.close_all()
    assert _profile_material_paths(tmp_path / "browser") == []


def test_live_browser_session_lifecycle_sink_records_safe_open_close_substages(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    events: list[tuple[str, str]] = []

    def _sink(stage: str, event: str, **kwargs: Any) -> None:
        del kwargs
        events.append((stage, event))

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        backend=_LifecycleFakeBackend(),
        lifecycle_event_sink=_sink,
    )
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    opened = manager.open_session(
        BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract, capture_screenshot=False)
    )
    manager.close_session(
        BrowserSessionRequest(
            mission=_envelope(),
            url=URL,
            contract=contract,
            session_id=opened.session_id,
            capture_screenshot=False,
        )
    )

    assert ("profile_lease_create", "stage_started") in events
    assert ("backend_open_context", "stage_started") in events
    assert ("session_publication", "stage_returned") in events
    assert ("old_session_disposal", "stage_returned") in events
    assert ("profile_lease_release", "stage_returned") in events
    assert ("post_close_state_reset", "stage_returned") in events


def test_live_browser_session_blocks_non_promoted_dangerous_actions(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

        result = manager.interact(
            BrowserSessionRequest.model_construct(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind="submit",
                data_not_instruction=True,
                authority_effect="none",
            )
        )

        assert result.accepted is False
        assert "not_promoted" in result.reason
        assert result.execution_effect == "none"
        assert result.finalgate_certificate is not None
        assert result.receipt.finalgate_verified is True
    finally:
        manager.close_all()


def test_live_browser_session_requires_mission_authority(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _envelope().model_copy(update={"allowed_actions": ["browser_session_open"]})
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
    )
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

        result = manager.interact(
            BrowserSessionRequest(
                mission=mission,
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role="textbox",
                target_name="Email",
                text="founder@example.com",
            )
        )

        assert result.accepted is False
        assert result.reason == "mission_authority_missing_browser_session_interact"
    finally:
        manager.close_all()


def test_cli_browser_session_demo_runs_multi_step_workflow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel.cli import main

    mission_path = tmp_path / "mission.json"
    mission_path.write_text(
        json.dumps({"preset": "operator_browser_l5_template", "mission": _envelope().model_dump(mode="json")}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "browser-session-demo",
            "--mission",
            str(mission_path),
            "--url",
            URL,
            "--run-root",
            str(tmp_path / "runs"),
            "--fixture-html",
            HTML,
            "--target-role",
            "textbox",
            "--target-name",
            "Email",
            "--text",
            "founder@example.com",
            "--engine",
            "playwright",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "browser_session_workflow" in output
    assert list((tmp_path / "runs").rglob("browser.session.result.json"))
    assert list((tmp_path / "runs").rglob("*_screenshot.png"))
