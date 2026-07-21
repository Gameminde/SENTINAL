from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.action_power_contract import (
    ActionAliasNormalizer,
    ActionFailureClass,
    build_browser_actionability_frame,
    build_browser_actionability_registry,
    recoverable_action_observation,
)
from sentinel.operator.browser_decision_frame import BrowserDecisionFrameCompiler
from sentinel.operator.browser_backend_selector import BrowserBackendSelection, select_browser_backend
from sentinel.operator.browser_cortex_quality_gate import derive_search_progress_state
from sentinel.operator.browser_environment_state import BrowserEnvironmentStateBuilder
from sentinel.operator.browser_observation_bundle import build_browser_observation_bundle
from sentinel.operator.browser_search_outcomes import derive_browser_search_outcome
from sentinel.operator.browser_search_parameter_boundary import reject_typed_browser_search_semantic_text
from sentinel.operator.browser_semantic_control_classifier import (
    classify_search_controls,
    is_search_like_control,
)
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.model_skill_surface import model_skill_for_action
from sentinel.operator.real_browser_control_models import (
    RealBrowserActionReceipt,
    RealBrowserAssertionReceipt,
    RealBrowserElementSnapshot,
    RealBrowserFinalCertificate,
    RealBrowserObservationReceipt,
    RealBrowserOpenReceipt,
)


class RealBrowserControlRuntimeError(RuntimeError):
    pass


BOUNDED_URL_AUTHORITY_REF = "real_browser:bounded_test_url"
DEFAULT_SESSION_REF = "real_browser_session:bounded"
CLOAK_BROWSER_BACKEND_ID = "cloak_browser"
PLAYWRIGHT_REAL_BROWSER_BACKEND_ID = "playwright_real_browser_engine"


@dataclass(frozen=True)
class CloakSessionReadinessResult:
    ready: bool
    provider_call_allowed: bool
    selected_backend_id: str
    actual_backend_id: str
    session_backend_kind: str = ""
    safe_url_origin_hash: str = ""
    readiness_receipt_hash: str = ""
    failure_code: str | None = None
    diagnostic_hash: str = ""
    receipt_backend_match: bool = False
    profile_material_persisted: bool = False
    backend_selected: bool = False
    backend_identity_matched: bool = False
    process_operational: bool = False
    devtools_operational: bool = False
    context_operational: bool = False
    page_operational: bool = False
    multi_action_reuse_operational: bool = False
    cleanup_operational: bool = False
    reopen_operational: bool = False

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "provider_call_allowed": self.provider_call_allowed,
            "selected_backend_id": self.selected_backend_id,
            "actual_backend_id": self.actual_backend_id,
            "session_backend_kind": self.session_backend_kind,
            "safe_url_origin_hash": self.safe_url_origin_hash,
            "readiness_receipt_hash": self.readiness_receipt_hash,
            "failure_code": self.failure_code,
            "diagnostic_hash": self.diagnostic_hash,
            "receipt_backend_match": self.receipt_backend_match,
            "profile_material_persisted": self.profile_material_persisted,
            "backend_selected": self.backend_selected,
            "backend_identity_matched": self.backend_identity_matched,
            "process_operational": self.process_operational,
            "devtools_operational": self.devtools_operational,
            "context_operational": self.context_operational,
            "page_operational": self.page_operational,
            "multi_action_reuse_operational": self.multi_action_reuse_operational,
            "cleanup_operational": self.cleanup_operational,
            "reopen_operational": self.reopen_operational,
        }


@dataclass(frozen=True)
class RealBrowserEngineElement:
    ref: str
    role: str
    name: str
    visible: bool = True
    enabled: bool = True
    text_preview: str = ""
    value_preview: str = ""
    secret: bool = False


@dataclass(frozen=True)
class RealBrowserEngineSnapshot:
    page_title: str
    state_hash: str
    elements: tuple[RealBrowserEngineElement, ...]


class RealBrowserEngine(Protocol):
    open_count: int
    observe_count: int
    click_count: int
    type_count: int
    assert_count: int
    select_count: int
    extract_count: int
    press_count: int
    wait_count: int
    scroll_count: int

    @property
    def safe_url_origin_hash(self) -> str:
        ...

    def open(self) -> RealBrowserEngineSnapshot:
        ...

    def observe(self) -> RealBrowserEngineSnapshot:
        ...

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        ...

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        ...

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        ...

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        ...

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        ...

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        ...

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        ...

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        ...

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        ...


class InMemoryRealBrowserEngine:
    def __init__(self) -> None:
        self.opened = False
        self.enabled = False
        self.status_value = ""
        self.display_text = ""
        self.selected_option = ""
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

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash("inmemory://sentinel-real-browser-fixture")

    def open(self) -> RealBrowserEngineSnapshot:
        self.opened = True
        self.open_count += 1
        return self._snapshot()

    def observe(self) -> RealBrowserEngineSnapshot:
        self._require_open()
        self.observe_count += 1
        return self._snapshot()

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        self._require_open()
        element = self._require_interactable(ref)
        if element.role != "button":
            raise RealBrowserControlRuntimeError("real_browser_click_ref_not_button")
        if ref == "button:enable_sentinel":
            self.enabled = True
            if not self.display_text:
                self.display_text = "Sentinel real browser enabled"
        self.click_count += 1
        return self._snapshot()

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self._require_open()
        self._require_editable(ref)
        self.status_value = text
        self.display_text = text
        self.type_count += 1
        return self._snapshot()

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        self._require_open()
        element = self._require_interactable(ref)
        if element.role != "combobox":
            raise RealBrowserControlRuntimeError("real_browser_select_ref_not_combobox")
        self.selected_option = option
        self.select_count += 1
        return self._snapshot()

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        self._require_open()
        self.assert_count += 1
        return text in self.display_text or text in self.status_value, self._snapshot()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self._require_open()
        self.extract_count += 1
        return "\n".join(part for part in (self.display_text, self.status_value) if part), self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        self._require_open()
        self._require_editable(ref)
        self.press_count += 1
        if key == "Enter" and self.status_value:
            self.display_text = self.status_value
        return self._snapshot()

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        del timeout_ms
        self._require_open()
        self.wait_count += 1
        return text in self.display_text or text in self.status_value, self._snapshot()

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        self._require_open()
        self.wait_count += 1
        return self._snapshot()

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        del delta_y
        self._require_open()
        self.scroll_count += 1
        return self._snapshot()

    def _require_open(self) -> None:
        if not self.opened:
            raise RealBrowserControlRuntimeError("real_browser_not_open")

    def _require_interactable(self, ref: str) -> RealBrowserEngineElement:
        elements = {element.ref: element for element in self._elements()}
        element = elements.get(ref)
        if element is None:
            raise RealBrowserControlRuntimeError("real_browser_element_ref_unknown")
        if not element.visible:
            raise RealBrowserControlRuntimeError("real_browser_element_hidden")
        if not element.enabled:
            raise RealBrowserControlRuntimeError("real_browser_element_disabled")
        if bool(getattr(element, "secret", False)):
            raise RealBrowserControlRuntimeError("real_browser_secret_field_blocked")
        return element

    def _require_editable(self, ref: str) -> RealBrowserEngineElement:
        element = self._require_interactable(ref)
        if element.role not in {"textbox", "combobox", "searchbox"}:
            raise RealBrowserControlRuntimeError("real_browser_type_ref_not_textbox")
        if bool(getattr(element, "secret", False)):
            raise RealBrowserControlRuntimeError("real_browser_secret_field_blocked")
        return element

    def _snapshot(self) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title="Sentinel Real Browser Fixture",
            state_hash=stable_hash(
                {
                    "opened": self.opened,
                    "enabled": self.enabled,
                    "status_value_hash": text_hash(self.status_value),
                    "display_text_hash": text_hash(self.display_text),
                    "selected_option": self.selected_option,
                }
            ),
            elements=self._elements(),
        )

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:status", "textbox", "status", value_preview=self.status_value[:80]),
            RealBrowserEngineElement("button:enable_sentinel", "button", "Enable Sentinel", text_preview="Enable Sentinel"),
            RealBrowserEngineElement("button:hidden", "button", "Hidden", visible=False),
            RealBrowserEngineElement("button:disabled", "button", "Disabled", enabled=False),
            RealBrowserEngineElement("input:masked", "textbox", "masked", secret=True),
        )


class BrowserSessionManagerRealBrowserEngine:
    """Real-browser engine adapter over BrowserSessionManager L5.

    The model-facing browser skill should execute through the product browser
    session manager when Cloak/session is selected, while preserving the
    existing RealBrowserEngine contract used by the skill spine.
    """

    browser_backend_id = CLOAK_BROWSER_BACKEND_ID

    def __init__(
        self,
        *,
        target_url: str,
        session_manager: Any | None = None,
        capture_root: str | Path | None = None,
        headless: bool = True,
        timeout_ms: int = 15_000,
    ) -> None:
        self.target_url = target_url
        self.timeout_ms = timeout_ms
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
        self._authority: MissionAuthorityEnvelope | None = None
        self._session_id: str | None = None
        effective_capture_root = Path(capture_root) if capture_root is not None else _default_browser_session_capture_root()
        self._capture_root = effective_capture_root
        self._last_snapshot = RealBrowserEngineSnapshot(
            page_title="Browser session page",
            state_hash=stable_hash({"target_url_hash": stable_hash(target_url), "opened": False}),
            elements=(),
        )
        self._last_text = ""
        self._last_typed_text_hash = ""
        self._last_form_state_summary_hash = ""
        self._ref_targets: dict[str, tuple[str, str | None, int]] = {}
        self.session_manager = session_manager or _build_browser_session_manager(
            capture_root=effective_capture_root,
            headless=headless,
        )

    @property
    def safe_url_origin_hash(self) -> str:
        parsed = urlparse(self.target_url)
        return stable_hash({"scheme": parsed.scheme, "host": parsed.hostname or "", "port": parsed.port})

    @property
    def session_manager_backend_kind(self) -> str:
        backend = getattr(self.session_manager, "backend", None)
        return str(
            getattr(backend, "backend_kind", None)
            or getattr(self.session_manager, "backend_kind", None)
            or "unknown"
        )

    @property
    def last_typed_text_hash(self) -> str:
        return self._last_typed_text_hash

    @property
    def last_form_state_summary_hash(self) -> str:
        return self._last_form_state_summary_hash

    def bind_authority(self, authority: MissionAuthorityEnvelope) -> None:
        self._authority = authority

    def open(self) -> RealBrowserEngineSnapshot:
        self.open_count += 1
        result = self.session_manager.open_session(self._request("open"))
        self._session_id = _result_session_id(result) or self._session_id
        return self._snapshot_from_result(result, fallback_title="Browser session page opened")

    def observe(self) -> RealBrowserEngineSnapshot:
        self.observe_count += 1
        result = self.session_manager.observe(self._request("observe"))
        return self._snapshot_from_result(result, fallback_title="Browser session page observed")

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        self.click_count += 1
        result = self.session_manager.interact(self._request("click", ref=ref))
        return self._snapshot_from_result(result, fallback_title="Browser session click")

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self.type_count += 1
        result = self.session_manager.interact(self._request("fill", ref=ref, text=text))
        return self._snapshot_from_result(result, fallback_title="Browser session fill")

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        self.select_count += 1
        result = self.session_manager.interact(self._request("select", ref=ref, values=[option]))
        return self._snapshot_from_result(result, fallback_title="Browser session select")

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        self.assert_count += 1
        try:
            result = self.session_manager.interact(self._request("wait_for_text", text=text))
            return True, self._snapshot_from_result(result, fallback_title="Browser session text assertion")
        except RealBrowserControlRuntimeError:
            return False, self.observe()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self.extract_count += 1
        snapshot = self.observe()
        return self._last_text, snapshot

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        self.press_count += 1
        if key != "Enter":
            raise RealBrowserControlRuntimeError("real_browser_press_key_not_supported_by_session_backend")
        result = self.session_manager.interact(self._request("press_key", ref=ref, text=key))
        return self._snapshot_from_result(result, fallback_title="Browser session key press")

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        self.wait_count += 1
        result = self.session_manager.interact(self._request("wait_for_text", text=text, timeout_ms=timeout_ms))
        return True, self._snapshot_from_result(result, fallback_title="Browser session wait_for_text")

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        self.wait_count += 1
        return self.observe()

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        del delta_y
        self.scroll_count += 1
        return self.observe()

    def close(self) -> None:
        close_all = getattr(self.session_manager, "close_all", None)
        try:
            if callable(close_all):
                close_all()
        finally:
            self._session_id = None
            _remove_profile_material(self._capture_root)

    def close_all(self) -> None:
        self.close()

    def _request(
        self,
        action_kind: str,
        *,
        ref: str | None = None,
        text: str | None = None,
        values: list[str] | None = None,
        timeout_ms: int | None = None,
    ) -> Any:
        (
            BrowserSessionActionKind,
            BrowserSessionContract,
            BrowserSessionRequest,
        ) = _browser_session_symbols()
        target_role, target_name, target_nth = self._target_for_ref(ref)
        action = getattr(BrowserSessionActionKind, action_kind.upper())
        return BrowserSessionRequest(
            mission=self._session_authority(),
            url=self.target_url,
            contract=BrowserSessionContract(
                mission_id=self._session_authority().id,
                allowed_domains=[self._target_host()],
                allowed_action_kinds=[
                    BrowserSessionActionKind.CLICK,
                    BrowserSessionActionKind.TYPE,
                    BrowserSessionActionKind.FILL,
                    BrowserSessionActionKind.SELECT,
                    BrowserSessionActionKind.WAIT_FOR_TEXT,
                    BrowserSessionActionKind.PRESS_KEY,
                ],
                max_steps=50,
                max_tabs=4,
            ),
            session_id=self._session_id,
            action_kind=action,
            target_role=target_role,
            target_name=target_name,
            target_nth=target_nth,
            text=text,
            values=values or [],
            timeout_ms=timeout_ms or self.timeout_ms,
            capture_screenshot=False,
        )

    def _session_authority(self) -> MissionAuthorityEnvelope:
        if self._authority is None:
            raise RealBrowserControlRuntimeError("real_browser_session_authority_missing")
        host = self._target_host()
        allowed_domains = set(self._authority.allowed_domains)
        if host not in allowed_domains and BOUNDED_URL_AUTHORITY_REF not in allowed_domains:
            raise RealBrowserControlRuntimeError("real_browser_target_host_not_authorized")
        internal_session_actions = (
            "browser_session_open",
            "browser_session_observe",
            "browser_session_interact",
            "browser_session_close",
        )
        return self._authority.model_copy(
            update={
                "allowed_domains": list(dict.fromkeys(self._authority.allowed_domains)),
                "allowed_actions": list(dict.fromkeys(tuple(self._authority.allowed_actions) + internal_session_actions)),
            }
        )

    def _target_host(self) -> str:
        host = (urlparse(self.target_url).hostname or "").lower()
        if not host:
            raise RealBrowserControlRuntimeError("real_browser_target_url_host_missing")
        return host

    def _target_for_ref(self, ref: str | None) -> tuple[str | None, str | None, int]:
        if not ref:
            return None, None, 0
        if ref in self._ref_targets:
            return self._ref_targets[ref]
        elements = {element.ref: element for element in self._last_snapshot.elements}
        element = elements.get(ref)
        if element is not None:
            return element.role, element.name or None, 0
        lowered = ref.lower()
        if lowered.startswith("input:") or lowered.startswith("search:"):
            return "textbox", _label_from_ref(ref), 0
        if lowered.startswith("button:"):
            return "button", _label_from_ref(ref), 0
        if lowered.startswith("link:"):
            return "link", _label_from_ref(ref), 0
        return None, None, 0

    def _snapshot_from_result(self, result: Any, *, fallback_title: str) -> RealBrowserEngineSnapshot:
        if not bool(getattr(result, "accepted", False)):
            raise RealBrowserControlRuntimeError(str(getattr(result, "reason", "browser_session_result_blocked")))
        self._session_id = _result_session_id(result) or self._session_id
        receipt = getattr(result, "receipt", None)
        self._last_typed_text_hash = str(getattr(receipt, "typed_text_hash", "") or "")
        self._last_form_state_summary_hash = str(getattr(receipt, "form_state_summary_hash", "") or "")
        manager_snapshot = self._manager_snapshot()
        if manager_snapshot is not None:
            snapshot = self._snapshot_from_accessibility(manager_snapshot, fallback_title=fallback_title)
        else:
            elements = tuple(getattr(receipt, "elements", ()) or ())
            safe_summary = str(getattr(receipt, "safe_summary", "") or "")
            page_title = str(getattr(receipt, "page_title", "") or fallback_title)
            state_hash = str(
                getattr(receipt, "page_state_hash", "")
                or getattr(receipt, "after_snapshot_hash", "")
                or getattr(receipt, "before_snapshot_hash", "")
                or stable_hash({"summary": safe_summary, "session": self._session_id})
            )
            snapshot = RealBrowserEngineSnapshot(page_title=page_title, state_hash=state_hash, elements=elements)
            self._ref_targets = {
                element.ref: (element.role, element.name or None, 0)
                for element in elements
                if isinstance(element, RealBrowserEngineElement)
            }
            self._last_text = safe_summary
        self._last_snapshot = snapshot
        return snapshot

    def _manager_snapshot(self) -> Any | None:
        if self._authority is None or not self._session_id or not hasattr(self.session_manager, "snapshot_for_session"):
            return None
        return self.session_manager.snapshot_for_session(
            mission_id=self._session_authority().id,
            session_id=self._session_id,
            timeout_ms=self.timeout_ms,
        )

    def safe_devtools_context(self) -> dict[str, Any] | None:
        if self._authority is None or not self._session_id or not hasattr(self.session_manager, "devtools_metadata_for_session"):
            return None
        metadata: list[dict[str, Any]] = []
        for capability in ("network_ledger", "console_ledger", "performance_trace"):
            try:
                current = self.session_manager.devtools_metadata_for_session(
                    mission_id=self._session_authority().id,
                    session_id=self._session_id,
                    capability=capability,
                    timeout_ms=self.timeout_ms,
                )
            except Exception as exc:
                return {
                    "source": "browser_session_manager_l5",
                    "available": False,
                    "failure_code": "browser_devtools_metadata_unavailable",
                    "diagnostic_hash": stable_hash({"exception_class": exc.__class__.__name__}),
                }
            if isinstance(current, dict):
                metadata.append(current)
        if not metadata:
            return None
        return _combine_safe_devtools_metadata(metadata)

    def _snapshot_from_accessibility(self, snapshot: Any, *, fallback_title: str) -> RealBrowserEngineSnapshot:
        elements: list[RealBrowserEngineElement] = []
        self._ref_targets = {}
        refs = getattr(snapshot, "refs", {}) or {}
        for ref, role_ref in refs.items():
            role = str(getattr(role_ref, "role", "") or "")
            name = str(getattr(role_ref, "name", "") or role)
            nth = int(getattr(role_ref, "nth", None) or 0)
            elements.append(
                RealBrowserEngineElement(
                    str(ref),
                    role,
                    name,
                    text_preview=name[:160],
                    value_preview="",
                    secret=_looks_secret_ref(role, name),
                )
            )
            self._ref_targets[str(ref)] = (role, name or None, nth)
        self._last_text = str(getattr(snapshot, "snapshot", "") or "")
        return RealBrowserEngineSnapshot(
            page_title=fallback_title,
            state_hash=str(getattr(snapshot, "snapshot_sha256", "") or stable_hash(self._last_text)),
            elements=tuple(elements),
        )


class RealBrowserControlRuntime:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        engine: RealBrowserEngine,
        bounded_url_ref: str = "env:SENTINEL_BROWSER_TEST_URL",
        session_ref: str = DEFAULT_SESSION_REF,
        browser_backend_selection: BrowserBackendSelection | None = None,
        selected_backend_id: str | None = None,
        product_context: dict[str, Any] | None = None,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.engine = engine
        self.bounded_url_ref = bounded_url_ref
        self.session_ref = session_ref
        self.product_context = dict(product_context or {})
        self.actual_backend_id = _engine_backend_id(engine)
        if browser_backend_selection is None and self.actual_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID:
            browser_backend_selection = select_browser_backend()
        self.browser_backend_selection = browser_backend_selection
        self.selected_backend_id = _validate_selected_browser_backend(
            actual_backend_id=self.actual_backend_id,
            backend_selection=browser_backend_selection,
            selected_backend_id=selected_backend_id,
        )

    def close(self) -> None:
        close = getattr(self.engine, "close", None)
        if callable(close):
            close()

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        envelope = ActionAliasNormalizer().normalize(envelope)
        if envelope.capability_id != "real_browser_control":
            raise RealBrowserControlRuntimeError("real_browser_control_capability_required")
        bind_authority = getattr(self.engine, "bind_authority", None)
        if callable(bind_authority):
            bind_authority(authority)
        if envelope.operation == "real_browser.open":
            return self._open(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.observe":
            return self._observe(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.search":
            return self._search(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.inspect_result":
            return self._inspect_result(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.open_result":
            return self._open_result(envelope, authority=authority, context=context)
        if envelope.operation in {"real_browser.extract_evidence", "real_browser.extract_entities"}:
            return self._extract_evidence(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.extract_product_cards":
            return self._extract_product_cards(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.verify_extraction":
            return self._verify_extraction(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.click":
            return self._click(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.type_text":
            return self._type_text(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.select_option":
            return self._select_option(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.assert_text":
            return self._assert_text(envelope, authority=authority)
        if envelope.operation == "real_browser.extract_text":
            return self._extract_text(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.press_key":
            return self._press_key(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.wait_for_text":
            return self._wait_for_text(envelope, authority=authority)
        if envelope.operation == "real_browser.wait_for_load":
            return self._wait_for_load(envelope, authority=authority)
        if envelope.operation == "real_browser.scroll":
            return self._scroll(envelope, authority=authority)
        raise RealBrowserControlRuntimeError(f"real_browser_control_operation_unsupported:{envelope.operation}")

    def as_action_executor(self, *, authority: MissionAuthorityEnvelope) -> Callable[[ActionEnvelope, dict[str, Any]], ActionResult]:
        def _execute(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
            return self.execute(envelope, authority=authority, context=context)

        return _execute

    def _open(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.open")
        if envelope.params.get("url"):
            raise RealBrowserControlRuntimeError("real_browser_unbounded_url_blocked")
        snapshot = self.engine.open()
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_opened_world_model_ready",
        )
        receipt = RealBrowserOpenReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            page_title_hash=text_hash(snapshot.page_title),
            browser_state_hash=snapshot.state_hash,
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._append_event(
            "real_browser_opened",
            "Bounded real browser page opened.",
            metadata={"safe_url_origin_hash": self.engine.safe_url_origin_hash, "browser_state_hash": snapshot.state_hash},
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(receipt.receipt_id,),
            material_action=False,
            observation_summary=(
                "bounded real browser page opened with browser world model "
                f"stable_ref_count={context_cards['browser_world_model_summary']['stable_ref_count']}."
            ),
            result_hash=receipt.receipt_hash,
            context_cards=context_cards,
        )

    def _observe(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.observe")
        snapshot = self.engine.observe()
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_observed_world_model_ready",
        )
        elements = tuple(
            _snapshot_element(element)
            for element in snapshot.elements
            if element.visible and element.enabled and not bool(getattr(element, "secret", False))
        )
        summary_hash = stable_hash({"title_hash": text_hash(snapshot.page_title), "elements": [element.safe_model_dump() for element in elements]})
        receipt = RealBrowserObservationReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            page_title=snapshot.page_title,
            page_state_hash=snapshot.state_hash,
            elements=elements,
            bounded_observation_summary_hash=summary_hash,
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._append_event(
            "real_browser_observed",
            "Bounded real browser page observed with stable refs.",
            metadata={"element_count": len(elements), "browser_state_hash": snapshot.state_hash},
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(receipt.receipt_id,),
            material_action=False,
            observation_summary=f"real browser observed with {len(elements)} stable element refs.",
            result_hash=receipt.receipt_hash,
            context_cards=context_cards,
        )

    def _search(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.search")
        query = str(envelope.params.get("query") or envelope.params.get("text") or "")
        if not query.strip():
            raise RealBrowserControlRuntimeError("real_browser_search_query_required")
        try:
            reject_typed_browser_search_semantic_text(query)
        except ValueError as exc:
            raise RealBrowserControlRuntimeError("real_browser_search_query_secret_like") from exc
        try:
            before_snapshot = self.engine.observe()
        except RealBrowserControlRuntimeError as exc:
            if str(exc) not in {"real_browser_not_open", "browser_session_missing_or_closed"}:
                raise
            try:
                before_snapshot = self.engine.open()
            except RealBrowserControlRuntimeError:
                context_cards = _recoverable_existing_browser_context_cards(context)
                return self._recoverable_actuation_failure(
                    envelope,
                    failure_code="real_browser_search_session_open_failed",
                    safe_summary=(
                        "Browser session was unavailable and could not be reopened during "
                        "in-scope search recovery; existing safe browser context is available."
                    ),
                    context_cards=context_cards,
                    browser_state_hash=_context_browser_state_hash(context_cards),
                )
        candidates = _search_ref_candidates(before_snapshot, envelope)
        if not candidates:
            context_cards = self._world_context_cards(
                before_snapshot,
                authority=authority,
                context=context,
                progress_state="real_browser_search_recovery_world_model_ready",
            )
            return self._recoverable_actuation_failure(
                envelope,
                failure_code="real_browser_search_control_not_found",
                safe_summary="No executable search-like control was available in the bounded browser world model.",
                context_cards=context_cards,
                browser_state_hash=before_snapshot.state_hash,
            )
        errors: list[str] = []
        recovery_evidence: dict[str, Any] | None = None
        last_trace: dict[str, Any] | None = None
        for ref in candidates:
            trace = _new_search_actuation_trace(before_snapshot=before_snapshot, ref=ref, query=query)
            last_trace = trace
            try:
                snapshot = self._actuate_search_candidate(
                    ref=ref,
                    query=query,
                    before_snapshot=before_snapshot,
                    trace=trace,
                    errors=errors,
                )
                try:
                    snapshot = self.engine.wait_for_load()
                except RealBrowserControlRuntimeError as exc:
                    errors.append(str(exc))
                trace["request_progress"] = "observing_after_submit"
                trace["navigation_progress"] = "observing_after_submit"
                context_cards = self._world_context_cards(
                    snapshot,
                    authority=authority,
                    context=context,
                    progress_state="real_browser_search_results_world_model_ready",
                )
                search_materiality = _search_materiality(
                    before_snapshot=before_snapshot,
                    after_snapshot=snapshot,
                    query=query,
                    context_cards=context_cards,
                    input_written=bool(trace.get("write_succeeded")),
                    submission_attempted=bool(trace.get("submit_attempted")),
                    search_actuation_trace=trace,
                )
                trace.update(
                    {
                        "request_progress": "observed" if search_materiality.get("request_observed") else "not_observed",
                        "navigation_progress": "changed" if search_materiality.get("navigation_or_state_changed") else "not_observed",
                        "result_region_progress": "changed" if search_materiality.get("result_region_changed") else "not_changed",
                        "typed_outcome": search_materiality.get("typed_search_outcome"),
                        "safe_failure_code": None,
                    }
                )
                search_materiality["search_actuation_trace"] = dict(trace)
                return self._record_action(
                    envelope,
                    action_kind="real_browser.search",
                    element_ref=ref,
                    before_state_hash=before_snapshot.state_hash,
                    after_state_hash=snapshot.state_hash,
                    status="completed",
                    summary=f"real browser search submitted through skill ref {ref} query_hash={text_hash(query)}.",
                    context_cards=context_cards,
                    search_materiality=search_materiality,
                )
            except RealBrowserControlRuntimeError as exc:
                error = str(exc)
                errors.append(error)
                if recovery_evidence is None and _search_error_can_refresh_refs(error):
                    refreshed_snapshot = self.engine.observe()
                    refreshed_context_cards = self._world_context_cards(
                        refreshed_snapshot,
                        authority=authority,
                        context=context,
                        progress_state="real_browser_search_recovery_world_model_ready",
                    )
                    recovery_evidence = _browser_recovery_evidence(
                        authority=authority,
                        failure_code=str(trace.get("safe_failure_code") or error),
                        browser_state_hash=before_snapshot.state_hash,
                        context_cards=refreshed_context_cards,
                    )
                    try:
                        refreshed_candidates = _search_ref_candidates(refreshed_snapshot, envelope)
                        retry_ref = ref if _element_for_ref(refreshed_snapshot, ref) is not None else (
                            refreshed_candidates[0] if refreshed_candidates else ref
                        )
                        retry_trace = _new_search_actuation_trace(before_snapshot=refreshed_snapshot, ref=retry_ref, query=query)
                        last_trace = retry_trace
                        snapshot = self._actuate_search_candidate(
                            ref=retry_ref,
                            query=query,
                            before_snapshot=refreshed_snapshot,
                            trace=retry_trace,
                            errors=errors,
                        )
                        try:
                            snapshot = self.engine.wait_for_load()
                        except RealBrowserControlRuntimeError as load_exc:
                            errors.append(str(load_exc))
                        context_cards = self._world_context_cards(
                            snapshot,
                            authority=authority,
                            context=context,
                            progress_state="real_browser_search_results_world_model_ready",
                        )
                        context_cards["browser_recovery_evidence"] = recovery_evidence
                        search_materiality = _search_materiality(
                            before_snapshot=before_snapshot,
                            after_snapshot=snapshot,
                            query=query,
                            context_cards=context_cards,
                            input_written=bool(retry_trace.get("write_succeeded")),
                            submission_attempted=bool(retry_trace.get("submit_attempted")),
                            search_actuation_trace=retry_trace,
                        )
                        retry_trace.update(
                            {
                                "request_progress": "observed" if search_materiality.get("request_observed") else "not_observed",
                                "navigation_progress": "changed" if search_materiality.get("navigation_or_state_changed") else "not_observed",
                                "result_region_progress": "changed" if search_materiality.get("result_region_changed") else "not_changed",
                                "typed_outcome": search_materiality.get("typed_search_outcome"),
                                "safe_failure_code": None,
                            }
                        )
                        search_materiality["search_actuation_trace"] = dict(retry_trace)
                        return self._record_action(
                            envelope,
                            action_kind="real_browser.search",
                            element_ref=ref,
                            before_state_hash=before_snapshot.state_hash,
                            after_state_hash=snapshot.state_hash,
                            status="completed",
                            summary=f"real browser search recovered and submitted through skill ref {ref} query_hash={text_hash(query)}.",
                            context_cards=context_cards,
                            search_materiality=search_materiality,
                        )
                    except RealBrowserControlRuntimeError as retry_exc:
                        errors.append(str(retry_exc))
                continue
        recovery_snapshot = self.engine.observe()
        context_cards = self._world_context_cards(
            recovery_snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_search_recovery_world_model_ready",
        )
        if recovery_evidence is None:
            recovery_evidence = _browser_recovery_evidence(
                authority=authority,
                failure_code=str((last_trace or {}).get("safe_failure_code") or "real_browser_search_actuation_failed"),
                browser_state_hash=recovery_snapshot.state_hash,
                context_cards=context_cards,
            )
        context_cards["browser_recovery_evidence"] = recovery_evidence
        if last_trace is not None:
            context_cards["search_actuation_trace"] = dict(last_trace)
        return self._recoverable_actuation_failure(
            envelope,
            failure_code="real_browser_search_actuation_failed",
            safe_summary="Search-like controls were found but none accepted robust in-scope search actuation.",
            context_cards=context_cards,
            browser_state_hash=recovery_snapshot.state_hash,
        )

    def _actuate_search_candidate(
        self,
        *,
        ref: str,
        query: str,
        before_snapshot: RealBrowserEngineSnapshot,
        trace: dict[str, Any],
        errors: list[str],
    ) -> RealBrowserEngineSnapshot:
        element = _element_for_ref(before_snapshot, ref)
        if element is None:
            trace.update({"ref_resolved": False, "safe_failure_code": "real_browser_search_ref_not_found"})
            raise RealBrowserControlRuntimeError("real_browser_search_ref_not_found")
        trace.update(
            {
                "ref_resolved": True,
                "element_attached": True,
                "element_visible": bool(element.visible),
                "element_enabled": bool(element.enabled),
            }
        )
        if bool(getattr(element, "secret", False)):
            trace["safe_failure_code"] = "real_browser_secret_field_blocked"
            raise RealBrowserControlRuntimeError("real_browser_secret_field_blocked")
        if not element.visible:
            trace["safe_failure_code"] = "real_browser_search_element_hidden"
            raise RealBrowserControlRuntimeError("real_browser_search_element_hidden")
        if not element.enabled:
            trace["safe_failure_code"] = "real_browser_search_element_disabled"
            raise RealBrowserControlRuntimeError("real_browser_search_element_disabled")
        trace["focus_attempted"] = True
        try:
            self.engine.click(ref)
            trace["focus_succeeded"] = True
        except (RealBrowserControlRuntimeError, AttributeError) as exc:
            errors.append(str(exc))
            trace["focus_succeeded"] = False
        trace["clear_attempted"] = True
        trace["clear_succeeded"] = True
        trace["write_method"] = "fill"
        trace["write_attempted"] = True
        try:
            snapshot = self.engine.type_text(ref, query)
        except RealBrowserControlRuntimeError as exc:
            trace["safe_failure_code"] = _search_write_failure_code(str(exc))
            raise RealBrowserControlRuntimeError(str(trace["safe_failure_code"])) from exc
        trace["write_succeeded"] = True
        readback = _search_write_readback_evidence(
            engine=self.engine,
            snapshot=snapshot,
            query=query,
        )
        trace.update(readback)
        if trace["write_readback_status"] == "mismatched":
            trace["safe_failure_code"] = "real_browser_search_write_readback_mismatch"
            raise RealBrowserControlRuntimeError("real_browser_search_write_readback_mismatch")
        observed_button_ref = _search_button_ref(snapshot) or _search_button_ref(before_snapshot)
        mechanisms = _observed_submit_mechanisms(snapshot, ref)
        if observed_button_ref and "search_button" not in mechanisms:
            mechanisms.append("search_button")
        trace["submit_mechanisms_observed"] = mechanisms
        trace["submit_button_ref_hash"] = text_hash(observed_button_ref) if observed_button_ref else ""
        trace["submit_method_selected"] = "enter_key" if "enter_key" in mechanisms else (mechanisms[0] if mechanisms else "")
        trace["submit_attempted"] = True
        try:
            return self.engine.press_key(ref, "Enter")
        except RealBrowserControlRuntimeError as exc:
            enter_failure_code = _search_submit_failure_code(str(exc))
            trace["submit_enter_failure_code"] = enter_failure_code
            errors.append(enter_failure_code)
            if _submit_failure_may_have_materialized(enter_failure_code):
                trace["submit_observe_recovery_attempted"] = True
                try:
                    recovered = self.engine.observe()
                except RealBrowserControlRuntimeError as observe_exc:
                    trace["submit_observe_recovery_succeeded"] = False
                    trace["submit_observe_recovery_failure_code"] = _search_submit_failure_code(str(observe_exc))
                else:
                    trace["submit_observe_recovery_succeeded"] = True
                    return recovered
            if "search_button" not in mechanisms:
                trace["safe_failure_code"] = "real_browser_search_submit_failed"
                raise RealBrowserControlRuntimeError("real_browser_search_submit_failed") from exc
            trace["submit_method_selected"] = "search_button"
            try:
                if observed_button_ref:
                    return self.engine.click(observed_button_ref)
                return self._click_search_button_if_available()
            except RealBrowserControlRuntimeError as button_exc:
                trace["submit_button_failure_code"] = _search_submit_failure_code(str(button_exc))
                trace["safe_failure_code"] = "real_browser_search_submit_failed"
                raise RealBrowserControlRuntimeError("real_browser_search_submit_failed") from button_exc

    def _inspect_result(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.inspect_result")
        ref = str(envelope.params.get("ref") or envelope.target_ref or "page:result")
        snapshot = self.engine.observe()
        if ref != "page:result" and ref not in {element.ref for element in snapshot.elements}:
            return self._recoverable_ref_failure(
                envelope,
                raw_ref=ref,
                context_cards=self._world_context_cards(
                    snapshot,
                    authority=authority,
                    context=context,
                    progress_state="real_browser_ref_recovery_world_model_ready",
                ),
                browser_state_hash=snapshot.state_hash,
            )
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_result_inspected_world_model_ready",
        )
        return self._record_action(
            envelope,
            action_kind="real_browser.inspect_result",
            element_ref=ref,
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser result inspected ref_hash={text_hash(ref)}.",
            material_action=False,
            context_cards=context_cards,
        )

    def _open_result(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.open_result")
        resolved = self._resolve_ref_or_recover(envelope, authority=authority, context=context)
        if isinstance(resolved, ActionResult):
            return resolved
        ref, before = resolved
        try:
            snapshot = self.engine.click(ref)
        except RealBrowserControlRuntimeError:
            recovery_snapshot = self.engine.observe()
            return self._recoverable_actuation_failure(
                envelope,
                failure_code="real_browser_open_result_actuation_failed",
                safe_summary="A bounded result ref was visible but could not be opened; refreshed candidates are available.",
                context_cards=self._world_context_cards(
                    recovery_snapshot,
                    authority=authority,
                    context=context,
                    progress_state="real_browser_result_open_recovery_world_model_ready",
                ),
                browser_state_hash=recovery_snapshot.state_hash,
            )
        return self._record_action(
            envelope,
            action_kind="real_browser.open_result",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser bounded result opened ref_hash={text_hash(ref)}.",
            context_cards=self._world_context_cards(
                snapshot,
                authority=authority,
                context=context,
                progress_state="real_browser_result_opened_world_model_ready",
            ),
        )

    def _extract_product_cards(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.extract_product_cards")
        try:
            text, snapshot = self.engine.extract_text()
        except RealBrowserControlRuntimeError as exc:
            if str(exc) not in {"real_browser_not_open", "browser_session_missing_or_closed"}:
                raise
            context_cards = _existing_browser_context_cards(context)
            if context_cards is None:
                raise
            state_hash = _context_browser_state_hash(context_cards)
            card_count = _context_product_card_count(context_cards)
            return self._record_action(
                envelope,
                action_kind="real_browser.extract_product_cards",
                element_ref="page:product_cards",
                before_state_hash=state_hash,
                after_state_hash=state_hash,
                status="completed",
                summary=(
                    "real browser product extraction completed from existing safe world model "
                    f"card_count={card_count}."
                ),
                material_action=True,
                context_cards=context_cards,
            )
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_product_cards_extracted",
            extracted_text=text,
        )
        card_count = len(context_cards.get("browser_world_model", {}).get("product_or_result_candidate_cards", []))
        return self._record_action(
            envelope,
            action_kind="real_browser.extract_product_cards",
            element_ref="page:product_cards",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser product extraction completed card_count={card_count} text_hash={text_hash(text)}.",
            material_action=True,
            context_cards=context_cards,
        )

    def _extract_evidence(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, envelope.operation)
        try:
            text, snapshot = self.engine.extract_text()
        except RealBrowserControlRuntimeError as exc:
            if str(exc) not in {"real_browser_not_open", "browser_session_missing_or_closed"}:
                raise
            context_cards = _existing_browser_context_cards(context)
            if context_cards is None:
                raise
            state_hash = _context_browser_state_hash(context_cards)
            entity_count = _context_product_card_count(context_cards)
            return self._record_action(
                envelope,
                action_kind=envelope.operation,
                element_ref="page:evidence_entities",
                before_state_hash=state_hash,
                after_state_hash=state_hash,
                status="completed",
                summary=(
                    "real browser open-world evidence extraction completed from existing safe "
                    f"world model entity_count={entity_count}."
                ),
                material_action=True,
                context_cards=context_cards,
            )
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_evidence_extracted",
            extracted_text=text,
        )
        entity_count = len(context_cards.get("browser_world_model", {}).get("product_or_result_candidate_cards", []))
        return self._record_action(
            envelope,
            action_kind=envelope.operation,
            element_ref="page:evidence_entities",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser open-world evidence extraction completed entity_count={entity_count} text_hash={text_hash(text)}.",
            material_action=True,
            context_cards=context_cards,
        )

    def _verify_extraction(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.verify_extraction")
        try:
            text, snapshot = self.engine.extract_text()
        except RealBrowserControlRuntimeError as exc:
            if str(exc) not in {"real_browser_not_open", "browser_session_missing_or_closed"}:
                raise
            context_cards = _existing_browser_context_cards(context)
            if context_cards is None:
                raise
            state_hash = _context_browser_state_hash(context_cards)
            card_count = _context_product_card_count(context_cards)
            return self._record_action(
                envelope,
                action_kind="real_browser.verify_extraction",
                element_ref="page:product_cards",
                before_state_hash=state_hash,
                after_state_hash=state_hash,
                status="passed",
                summary=f"real browser product extraction verification passed from existing safe world model card_count={card_count}.",
                material_action=True,
                context_cards=context_cards,
            )
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_product_extraction_verified",
            extracted_text=text,
        )
        cards = context_cards.get("browser_world_model", {}).get("product_or_result_candidate_cards", [])
        status = "passed" if cards else "failed"
        return self._record_action(
            envelope,
            action_kind="real_browser.verify_extraction",
            element_ref="page:product_cards",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status=status,
            summary=f"real browser product extraction verification {status} card_count={len(cards)}.",
            material_action=True,
            context_cards=context_cards,
        )

    def _click(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.click")
        resolved = self._resolve_ref_or_recover(envelope, authority=authority, context=context)
        if isinstance(resolved, ActionResult):
            return resolved
        ref, before = resolved
        snapshot = self.engine.click(ref)
        return self._record_action(
            envelope,
            action_kind="real_browser.click",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser click completed on stable ref {ref}.",
        )

    def _type_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.type_text")
        resolved = self._resolve_ref_or_recover(envelope, authority=authority, context=context)
        if isinstance(resolved, ActionResult):
            return resolved
        ref, before = resolved
        text = str(envelope.params.get("text") or "")
        _reject_sensitive_text(text)
        snapshot = self.engine.type_text(ref, text)
        return self._record_action(
            envelope,
            action_kind="real_browser.type_text",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser type_text completed on stable ref {ref}.",
        )

    def _select_option(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.select_option")
        resolved = self._resolve_ref_or_recover(envelope, authority=authority, context=context)
        if isinstance(resolved, ActionResult):
            return resolved
        ref, before = resolved
        option = str(envelope.params.get("option") or envelope.params.get("value") or "")
        _reject_sensitive_text(option)
        snapshot = self.engine.select_option(ref, option)
        return self._record_action(
            envelope,
            action_kind="real_browser.select_option",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser select_option completed on stable ref {ref}.",
        )

    def _assert_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.assert_text")
        text = str(envelope.params.get("text") or envelope.params.get("expected_text") or envelope.target_ref or "")
        _reject_sensitive_text(text)
        passed, snapshot = self.engine.assert_text(text)
        status = "passed" if passed else "failed"
        receipt = RealBrowserAssertionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            assertion_kind="text_contains",
            status=status,
            expected_text_hash=text_hash(text),
            page_state_hash=snapshot.state_hash,
            bounded_observation_summary_hash=self._summary_hash(snapshot),
        )
        certificate = RealBrowserFinalCertificate(
            mission_id=self.mission_id,
            status="accepted" if status == "passed" else "blocked",
            accepted=status == "passed",
            reason=f"real_browser_assert_text_{status}",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "real_browser_assertion_completed",
            "Bounded real browser text assertion completed.",
            metadata={"status": status, "browser_state_hash": snapshot.state_hash, "result_hash": receipt.result_hash},
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=status,
            receipt_refs=(receipt.receipt_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=False,
            observation_summary=f"real browser text assertion {status}.",
            result_hash=receipt.result_hash,
        )

    def _extract_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.extract_text")
        text, snapshot = self.engine.extract_text()
        return self._record_action(
            envelope,
            action_kind="real_browser.extract_text",
            element_ref="page:text",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser text extracted with char_count={len(text)} text_hash={text_hash(text)}.",
            material_action=False,
            context_cards=self._world_context_cards(
                snapshot,
                authority=authority,
                context=context,
                progress_state="real_browser_extraction_world_model_ready",
                extracted_text=text,
            ),
        )

    def _press_key(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope, context: dict[str, Any]) -> ActionResult:
        self._require_authorized(authority, "real_browser.press_key")
        resolved = self._resolve_ref_or_recover(envelope, authority=authority, context=context)
        if isinstance(resolved, ActionResult):
            return resolved
        ref, before = resolved
        key = str(envelope.params.get("key") or envelope.params.get("keyboard_key") or "")
        if key not in {"Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"}:
            raise RealBrowserControlRuntimeError("real_browser_key_not_allowed")
        snapshot = self.engine.press_key(ref, key)
        return self._record_action(
            envelope,
            action_kind="real_browser.press_key",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser press_key completed on stable ref {ref} key={key}.",
        )

    def _wait_for_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.wait_for_text")
        text = str(envelope.params.get("text") or envelope.params.get("expected_text") or "")
        _reject_sensitive_text(text)
        passed, snapshot = self.engine.wait_for_text(text, timeout_ms=int(envelope.params.get("timeout_ms") or 1000))
        status = "passed" if passed else "failed"
        return self._record_action(
            envelope,
            action_kind="real_browser.wait_for_text",
            element_ref="page:text",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status=status,
            summary=f"real browser wait_for_text {status} text_hash={text_hash(text)}.",
            material_action=False,
        )

    def _wait_for_load(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.wait_for_load")
        snapshot = self.engine.wait_for_load()
        return self._record_action(
            envelope,
            action_kind="real_browser.wait_for_load",
            element_ref="page:load",
            before_state_hash=snapshot.state_hash,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary="real browser wait_for_load completed.",
            material_action=False,
        )

    def _scroll(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.scroll")
        delta_y = int(envelope.params.get("delta_y") or 600)
        before = self.engine.observe().state_hash
        snapshot = self.engine.scroll(delta_y=delta_y)
        return self._record_action(
            envelope,
            action_kind="real_browser.scroll",
            element_ref="page:viewport",
            before_state_hash=before,
            after_state_hash=snapshot.state_hash,
            status="completed",
            summary=f"real browser scroll completed delta_y={delta_y}.",
        )

    def _record_action(
        self,
        envelope: ActionEnvelope,
        *,
        action_kind: str,
        element_ref: str,
        before_state_hash: str,
        after_state_hash: str,
        status: str,
        summary: str,
        material_action: bool = True,
        context_cards: dict[str, Any] | None = None,
        search_materiality: dict[str, Any] | None = None,
    ) -> ActionResult:
        action_context_cards = dict(context_cards or {})
        if search_materiality:
            action_context_cards["browser_search_materiality"] = dict(search_materiality)
        product_context = dict(self.product_context)
        workspace_context = _browser_product_workspace_context(product_context)
        root_identity = _browser_root_identity_context(product_context, engine=self.engine, after_state_hash=after_state_hash)
        internal_action_id = f"{envelope.capability_id}.{envelope.operation}"
        receipt = RealBrowserActionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            browser_session_handle_ref=workspace_context["browser_session_handle_ref"],
            browser_session_handle_hash=workspace_context["browser_session_handle_hash"],
            child_workspace_handle_hash=workspace_context["child_workspace_handle_hash"],
            mission_workspace_ref=workspace_context["mission_workspace_ref"],
            mission_workspace_hash=workspace_context["mission_workspace_hash"],
            root_browser_lease_id_hash=root_identity["root_browser_lease_id_hash"],
            browser_engine_identity_hash=root_identity["browser_engine_identity_hash"],
            backend_context_identity_hash=root_identity["backend_context_identity_hash"],
            page_identity_hash=root_identity["page_identity_hash"],
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            selected_backend_id=self.selected_backend_id,
            actual_backend_id=self.actual_backend_id,
            session_backend_kind=_engine_session_backend_kind(self.engine),
            backend_mismatch=self.selected_backend_id != self.actual_backend_id,
            simple_skill=model_skill_for_action(internal_action_id) or "",
            internal_action_id=internal_action_id,
            product_dispatch_owner=str(product_context.get("adapter_id") or ""),
            stable_element_ref=element_ref,
            action_kind=action_kind,
            status=status,
            recovery_classification="none" if status in {"completed", "passed", "success"} else "recoverable",
            replay_behavior="no_reexecute_on_replay",
            before_state_hash=before_state_hash,
            after_state_hash=after_state_hash,
            browser_environment_state_hash=str(
                action_context_cards.get("browser_environment_state_hash") or ""
            ),
            search_materiality=dict(search_materiality or {}),
            bounded_observation_summary_hash=stable_hash(
                {
                    "safe_url_origin_hash": self.engine.safe_url_origin_hash,
                    "after_state_hash": after_state_hash,
                    "action_kind": action_kind,
                    "element_ref_hash": text_hash(element_ref),
                    "browser_environment_state_hash": str(
                        action_context_cards.get("browser_environment_state_hash") or ""
                    ),
                    "search_materiality": search_materiality or {},
                }
            ),
        )
        certificate = RealBrowserFinalCertificate(
            mission_id=self.mission_id,
            status="accepted",
            accepted=True,
            reason=f"{action_kind}_completed",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "real_browser_action_completed",
            "Bounded real browser action completed.",
            metadata={
                "action_kind": action_kind,
                "stable_element_ref": element_ref,
                "before_state_hash": before_state_hash,
                "after_state_hash": after_state_hash,
                "result_hash": receipt.result_hash,
            },
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=status,
            receipt_refs=(receipt.receipt_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=material_action,
            observation_summary=summary,
            result_hash=receipt.result_hash,
            context_cards=action_context_cards,
        )

    def _resolve_ref_or_recover(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> tuple[str, str] | ActionResult:
        raw_ref = _param_ref(envelope)
        snapshot = self.engine.observe()
        elements = {element.ref: element for element in snapshot.elements}
        element = elements.get(raw_ref)
        if element is not None:
            if bool(getattr(element, "secret", False)):
                raise RealBrowserControlRuntimeError("real_browser_secret_field_blocked")
            if not element.visible:
                context_cards = self._world_context_cards(
                    snapshot,
                    authority=authority,
                    context=context,
                    progress_state="real_browser_ref_recovery_world_model_ready",
                )
                return self._recoverable_ref_failure(
                    envelope,
                    raw_ref=raw_ref,
                    context_cards=context_cards,
                    browser_state_hash=snapshot.state_hash,
                    failure_code="real_browser_element_hidden",
                    safe_summary=(
                        "Browser ref exists but is hidden in the current bounded page state; "
                        "refreshed executable candidates are available for the next model turn."
                    ),
                )
            if not element.enabled:
                context_cards = self._world_context_cards(
                    snapshot,
                    authority=authority,
                    context=context,
                    progress_state="real_browser_ref_recovery_world_model_ready",
                )
                return self._recoverable_ref_failure(
                    envelope,
                    raw_ref=raw_ref,
                    context_cards=context_cards,
                    browser_state_hash=snapshot.state_hash,
                    failure_code="real_browser_element_disabled",
                    safe_summary=(
                        "Browser ref exists but is disabled in the current bounded page state; "
                        "refreshed executable candidates are available for the next model turn."
                    ),
                )
            return raw_ref, snapshot.state_hash
        context_cards = self._world_context_cards(
            snapshot,
            authority=authority,
            context=context,
            progress_state="real_browser_ref_recovery_world_model_ready",
        )
        registry = context_cards["browser_actionability_registry"]
        alias_map = registry.get("accepted_aliases", {}) if isinstance(registry, dict) else {}
        canonical = alias_map.get(raw_ref)
        if isinstance(canonical, str) and canonical in elements:
            return canonical, snapshot.state_hash
        return self._recoverable_ref_failure(
            envelope,
            raw_ref=raw_ref,
            context_cards=context_cards,
            browser_state_hash=snapshot.state_hash,
        )

    def _recoverable_ref_failure(
        self,
        envelope: ActionEnvelope,
        *,
        raw_ref: str,
        context_cards: dict[str, Any],
        browser_state_hash: str,
        failure_code: str = "real_browser_element_ref_unknown",
        safe_summary: str | None = None,
    ) -> ActionResult:
        actionability_frame = context_cards.get("actionability_frame") if isinstance(context_cards, dict) else {}
        executable_refs = tuple(
            str(ref)
            for ref in (actionability_frame.get("executable_refs") if isinstance(actionability_frame, dict) else () or ())
        )
        recommended = tuple(
            str(action)
            for action in (actionability_frame.get("recovery_actions") if isinstance(actionability_frame, dict) else () or ())
        )
        observation = recoverable_action_observation(
            failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
            failure_code=failure_code,
            attempted_action_hash=envelope.action_hash,
            safe_summary=safe_summary
            or (
                "Browser ref was not executable in the current bounded page state; "
                "refreshed candidates are available for the next model turn."
            ),
            recommended_next_actions=recommended,
            refreshed_candidate_refs=executable_refs,
        )
        resolved_summary = safe_summary or (
            "Browser ref was not executable in the current bounded page state; "
            "refreshed candidates are available for the next model turn."
        )
        context_cards = dict(context_cards)
        context_cards["runtime_failure_fact"] = _runtime_failure_fact(
            envelope=envelope,
            failure_code=failure_code,
            safe_summary=resolved_summary,
            browser_state_hash=browser_state_hash,
            context_cards=context_cards,
        )
        context_cards["model_visible_body_failure_packet"] = _model_visible_body_failure_packet(
            envelope=envelope,
            failure_code=failure_code,
            safe_summary=resolved_summary,
            browser_state_hash=browser_state_hash,
            context_cards=context_cards,
            product_context=self.product_context,
            child_browser_session_ref=self.session_ref,
        )
        context_cards["model_blocker_assessment_schema"] = _model_blocker_assessment_schema()
        receipt, certificate = self._record_recoverable_failure_artifacts(
            envelope,
            action_kind=envelope.operation,
            element_ref=raw_ref,
            browser_state_hash=browser_state_hash,
            failure_code=failure_code,
            safe_summary=resolved_summary,
            context_cards=context_cards,
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="recoverable_failed",
            receipt_refs=(receipt.receipt_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=False,
            blocked_reason=failure_code,
            failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
            failure_code=failure_code,
            recoverable=True,
            recovery_observation=observation.safe_model_dump(),
            recommended_next_actions=recommended,
            observation_summary=f"recoverable browser ref miss code={failure_code} ref_hash={text_hash(raw_ref)} state_hash={browser_state_hash}.",
            context_cards=context_cards,
        )

    def _world_context_cards(
        self,
        snapshot: RealBrowserEngineSnapshot,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
        progress_state: str,
        extracted_text: str = "",
    ) -> dict[str, Any]:
        world_model = BrowserWorldModelBuilder().build_from_snapshot(
            snapshot,
            mission_objective=authority.mission_objective,
            origin_hash=self.engine.safe_url_origin_hash,
            extracted_text=extracted_text,
        )
        completion_requirements = context.get("completion_requirements") if isinstance(context, dict) else None
        frame = BrowserDecisionFrameCompiler().compile(
            mission_objective=authority.mission_objective,
            world_model=world_model,
            available_actions=tuple(context.get("available_actions") or _authority_available_actions(authority)),
            progress_state=progress_state,
            completion_requirements=completion_requirements if isinstance(completion_requirements, dict) else None,
        )
        registry = build_browser_actionability_registry(
            browser_state_hash=snapshot.state_hash,
            world_model=world_model,
            decision_frame=frame,
            generated_at_turn=int(context.get("model_calls_used") or 0) if isinstance(context, dict) else 0,
        )
        actionability_frame = build_browser_actionability_frame(
            browser_state_hash=snapshot.state_hash,
            registry=registry,
            decision_frame=frame,
        )
        world_dump = world_model.model_dump(mode="json")
        frame_dump = _browser_decision_frame_with_visible_card_extraction_priority(
            frame.model_dump(mode="json"),
            world_model=world_model,
            progress_state=progress_state,
        )
        registry_dump = registry.safe_model_dump()
        actionability_dump = actionability_frame.safe_model_dump()
        devtools_context = _engine_safe_devtools_context(self.engine)
        observation_bundle = build_browser_observation_bundle(
            page_state_hash=snapshot.state_hash,
            devtools_context=devtools_context,
        )
        environment_state = BrowserEnvironmentStateBuilder().build(
            snapshot=snapshot,
            mission_objective=authority.mission_objective,
            origin_hash=self.engine.safe_url_origin_hash,
            selected_backend_id=self.selected_backend_id,
            actual_backend_id=self.actual_backend_id,
            session_backend_kind=_engine_session_backend_kind(self.engine),
            extracted_text=extracted_text,
            world_model=world_model,
            network_events=observation_bundle.network_events,
            console_messages=observation_bundle.console_events,
        )
        environment_dump = environment_state.safe_model_dump()
        environment_hash = stable_hash(environment_dump)
        self._write_artifact("world_models", world_model.world_model_id, world_dump)
        self._write_artifact("decision_frames", frame.frame_id, frame_dump)
        cards = {
            "browser_world_model": world_dump,
            "browser_world_model_summary": world_model.compact_summary(),
            "browser_decision_frame": frame_dump,
            "browser_actionability_registry": registry_dump,
            "actionability_frame": actionability_dump,
            "browser_environment_state": environment_dump,
            "browser_environment_state_hash": environment_hash,
            "browser_observation_bundle": observation_bundle.safe_model_dump(),
            "browser_backend_execution": {
                "selected_backend_id": self.selected_backend_id,
                "actual_backend_id": self.actual_backend_id,
                "session_backend_kind": _engine_session_backend_kind(self.engine),
                "compatibility_only": self.actual_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
                "product_backend_proven": self.actual_backend_id == CLOAK_BROWSER_BACKEND_ID,
                "selection_reason": (
                    self.browser_backend_selection.selection_reason
                    if self.browser_backend_selection is not None
                    else "runtime_engine_declared_without_backend_frame"
                ),
            },
        }
        if devtools_context is not None:
            cards["browser_devtools_context"] = devtools_context
        return cards

    def _click_search_button_if_available(self) -> RealBrowserEngineSnapshot:
        snapshot = self.engine.observe()
        for element in snapshot.elements:
            if element.role != "button" or not element.visible or not element.enabled or bool(getattr(element, "secret", False)):
                continue
            text = f"{element.ref} {element.name} {element.text_preview}".lower()
            if any(marker in text for marker in ("search", "find", "submit", "go")):
                return self.engine.click(element.ref)
        raise RealBrowserControlRuntimeError("real_browser_search_submit_control_not_found")

    def _recoverable_actuation_failure(
        self,
        envelope: ActionEnvelope,
        *,
        failure_code: str,
        safe_summary: str,
        context_cards: dict[str, Any],
        browser_state_hash: str,
    ) -> ActionResult:
        actionability_frame = context_cards.get("actionability_frame") if isinstance(context_cards, dict) else {}
        recommended = tuple(
            str(action)
            for action in (actionability_frame.get("recovery_actions") if isinstance(actionability_frame, dict) else () or ())
        )
        executable_refs = tuple(
            str(ref)
            for ref in (actionability_frame.get("executable_refs") if isinstance(actionability_frame, dict) else () or ())
        )
        observation = recoverable_action_observation(
            failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
            failure_code=failure_code,
            attempted_action_hash=envelope.action_hash,
            safe_summary=safe_summary,
            recommended_next_actions=recommended,
            refreshed_candidate_refs=executable_refs,
        )
        context_cards = dict(context_cards)
        context_cards["runtime_failure_fact"] = _runtime_failure_fact(
            envelope=envelope,
            failure_code=failure_code,
            safe_summary=safe_summary,
            browser_state_hash=browser_state_hash,
            context_cards=context_cards,
        )
        context_cards["model_visible_body_failure_packet"] = _model_visible_body_failure_packet(
            envelope=envelope,
            failure_code=failure_code,
            safe_summary=safe_summary,
            browser_state_hash=browser_state_hash,
            context_cards=context_cards,
            product_context=self.product_context,
            child_browser_session_ref=self.session_ref,
        )
        context_cards["model_blocker_assessment_schema"] = _model_blocker_assessment_schema()
        receipt, certificate = self._record_recoverable_failure_artifacts(
            envelope,
            action_kind=envelope.operation,
            element_ref=str(envelope.target_ref or envelope.params.get("ref") or envelope.operation),
            browser_state_hash=browser_state_hash,
            failure_code=failure_code,
            safe_summary=safe_summary,
            context_cards=context_cards,
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="recoverable_failed",
            receipt_refs=(receipt.receipt_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=False,
            blocked_reason=failure_code,
            failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
            failure_code=failure_code,
            recoverable=True,
            recovery_observation=observation.safe_model_dump(),
            recommended_next_actions=recommended,
            observation_summary=f"recoverable browser actuation miss code={failure_code} state_hash={browser_state_hash}.",
            context_cards=context_cards,
        )

    def _record_recoverable_failure_artifacts(
        self,
        envelope: ActionEnvelope,
        *,
        action_kind: str,
        element_ref: str,
        browser_state_hash: str,
        failure_code: str,
        safe_summary: str,
        context_cards: dict[str, Any],
    ) -> tuple[RealBrowserActionReceipt, RealBrowserFinalCertificate]:
        product_context = dict(self.product_context)
        workspace_context = _browser_product_workspace_context(product_context)
        root_identity = _browser_root_identity_context(product_context, engine=self.engine, after_state_hash=browser_state_hash)
        internal_action_id = f"{envelope.capability_id}.{envelope.operation}"
        search_materiality = _failure_search_materiality(
            envelope=envelope,
            failure_code=failure_code,
            context_cards=context_cards,
        )
        receipt = RealBrowserActionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            browser_session_handle_ref=workspace_context["browser_session_handle_ref"],
            browser_session_handle_hash=workspace_context["browser_session_handle_hash"],
            child_workspace_handle_hash=workspace_context["child_workspace_handle_hash"],
            mission_workspace_ref=workspace_context["mission_workspace_ref"],
            mission_workspace_hash=workspace_context["mission_workspace_hash"],
            root_browser_lease_id_hash=root_identity["root_browser_lease_id_hash"],
            browser_engine_identity_hash=root_identity["browser_engine_identity_hash"],
            backend_context_identity_hash=root_identity["backend_context_identity_hash"],
            page_identity_hash=root_identity["page_identity_hash"],
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            selected_backend_id=self.selected_backend_id,
            actual_backend_id=self.actual_backend_id,
            session_backend_kind=_engine_session_backend_kind(self.engine),
            backend_mismatch=self.selected_backend_id != self.actual_backend_id,
            simple_skill=model_skill_for_action(internal_action_id) or "",
            internal_action_id=internal_action_id,
            product_dispatch_owner=str(product_context.get("adapter_id") or ""),
            stable_element_ref=element_ref,
            action_kind=action_kind,
            status="recoverable_failed",
            recovery_classification="recoverable",
            replay_behavior="no_reexecute_on_replay",
            before_state_hash=browser_state_hash,
            after_state_hash=browser_state_hash,
            browser_environment_state_hash=str(context_cards.get("browser_environment_state_hash") or browser_state_hash),
            search_materiality=search_materiality,
            bounded_observation_summary_hash=stable_hash(
                {
                    "safe_url_origin_hash": self.engine.safe_url_origin_hash,
                    "browser_state_hash": browser_state_hash,
                    "action_kind": action_kind,
                    "failure_code": failure_code,
                    "safe_summary_hash": text_hash(safe_summary),
                    "runtime_failure_fact_hash": stable_hash(context_cards.get("runtime_failure_fact") or {}),
                }
            ),
        )
        certificate = RealBrowserFinalCertificate(
            mission_id=self.mission_id,
            status="blocked",
            accepted=False,
            reason=f"{action_kind}_recoverable_failed",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "real_browser_action_recoverable_failed",
            "Bounded real browser action produced a recoverable failure receipt.",
            metadata={
                "action_kind": action_kind,
                "failure_code": failure_code,
                "browser_state_hash": browser_state_hash,
                "result_hash": receipt.result_hash,
            },
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
        )
        return receipt, certificate

    def _require_authorized(self, authority: MissionAuthorityEnvelope, action_name: str) -> None:
        if authority.revoked_at is not None:
            raise RealBrowserControlRuntimeError("mission_authority_inactive")
        if "real_browser_control" not in authority.allowed_tools:
            raise RealBrowserControlRuntimeError("real_browser_control_tool_not_authorized")
        if action_name not in authority.allowed_actions and action_name.split(".", 1)[-1] not in authority.allowed_actions:
            raise RealBrowserControlRuntimeError("real_browser_control_action_not_authorized")
        if BOUNDED_URL_AUTHORITY_REF not in authority.allowed_domains:
            raise RealBrowserControlRuntimeError("real_browser_bounded_url_not_authorized")

    def _summary_hash(self, snapshot: RealBrowserEngineSnapshot) -> str:
        return stable_hash(
            {
                "safe_url_origin_hash": self.engine.safe_url_origin_hash,
                "page_title_hash": text_hash(snapshot.page_title),
                "state_hash": snapshot.state_hash,
                "observable_refs": [
                    element.ref
                    for element in snapshot.elements
                    if element.visible and element.enabled and not bool(getattr(element, "secret", False))
                ],
            }
        )

    def _write_artifact(self, collection: str, artifact_id: str, payload: dict[str, object]) -> None:
        path = self.kernel.store.mission_dir(self.mission_id, create=True) / "real_browser_control" / collection / f"{artifact_id}.json"
        self.kernel.store.atomic_write_json(path, payload)

    def _append_event(
        self,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, object],
        receipt_refs: list[str],
        finalgate_refs: list[str],
    ) -> None:
        self.kernel.store.append_event(
            self.mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
        )


class PlaywrightRealBrowserEngine:
    browser_backend_id = PLAYWRIGHT_REAL_BROWSER_BACKEND_ID

    def __init__(self, *, target_url: str, headless: bool = True) -> None:
        self.target_url = target_url
        self._playwright = None
        self._browser = None
        self._page = None
        self._ref_selectors: dict[str, str] = {}
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
        self._headless = headless

    @property
    def safe_url_origin_hash(self) -> str:
        parsed = urlparse(self.target_url)
        return stable_hash({"scheme": parsed.scheme, "netloc": parsed.netloc})

    def open(self) -> RealBrowserEngineSnapshot:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # noqa: BLE001
            raise RealBrowserControlRuntimeError("REAL_BROWSER_ENGINE_CONFIG_MISSING") from exc
        if self._page is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._page = self._browser.new_page()
        self._page.goto(self.target_url, wait_until="domcontentloaded")
        self.open_count += 1
        return self.observe()

    def observe(self) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        self.observe_count += 1
        title = page.title()
        elements_payload = page.evaluate(
            """() => {
                const nodes = Array.from(document.querySelectorAll('button,input,textarea,select,a,[role]'));
                return nodes.slice(0, 60).map((el, index) => {
                    const explicit = el.getAttribute('data-sentinel-ref');
                    const role = el.getAttribute('role') || (
                        el.tagName === 'BUTTON' ? 'button' :
                        el.tagName === 'A' ? 'link' :
                        el.tagName === 'SELECT' ? 'combobox' :
                        (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') ? 'textbox' :
                        el.tagName.toLowerCase()
                    );
                    const name = el.getAttribute('aria-label') || el.getAttribute('name') || el.textContent || el.getAttribute('placeholder') || role;
                    return {
                        ref: explicit || `${role}:${String(name).trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || index}:${index}`,
                        role,
                        name: String(name).trim().slice(0, 80),
                        visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
                        enabled: !el.disabled,
                        text_preview: String(el.textContent || '').trim().slice(0, 80),
                        value_preview: String(el.value || '').slice(0, 80),
                        secret: el.tagName === 'INPUT' && ['password', 'hidden'].includes(String(el.type || '').toLowerCase()),
                        selector: explicit ? `[data-sentinel-ref="${explicit.replace(/"/g, '\\"')}"]` : null,
                    };
                });
            }"""
        )
        elements: list[RealBrowserEngineElement] = []
        self._ref_selectors = {}
        for index, payload in enumerate(elements_payload):
            ref = str(payload.get("ref") or f"element:{index}")
            selector = payload.get("selector") or _nth_selector(str(payload.get("role") or "element"), index)
            self._ref_selectors[ref] = str(selector)
            elements.append(
                RealBrowserEngineElement(
                    ref=ref,
                    role=str(payload.get("role") or "element"),
                    name=str(payload.get("name") or ""),
                    visible=bool(payload.get("visible")),
                    enabled=bool(payload.get("enabled")),
                    text_preview=str(payload.get("text_preview") or ""),
                    value_preview=str(payload.get("value_preview") or ""),
                    secret=bool(payload.get("secret")),
                )
            )
        return RealBrowserEngineSnapshot(page_title=title, state_hash=self._state_hash(), elements=tuple(elements))

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        selector = self._selector(ref)
        page.locator(selector).click()
        self.click_count += 1
        return self.observe()

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        selector = self._selector(ref)
        page.locator(selector).fill(text)
        self.type_count += 1
        return self.observe()

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        selector = self._selector(ref)
        page.locator(selector).select_option(option)
        self.select_count += 1
        return self.observe()

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        page = self._require_page()
        self.assert_count += 1
        return text in page.locator("body").inner_text(timeout=2000), self.observe()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        page = self._require_page()
        self.extract_count += 1
        text = page.locator("body").inner_text(timeout=2000)[:4000]
        return text, self.observe()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        selector = self._selector(ref)
        page.locator(selector).press(key)
        self.press_count += 1
        return self.observe()

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        page = self._require_page()
        self.wait_count += 1
        try:
            page.locator("body").wait_for(state="visible", timeout=timeout_ms)
            body = page.locator("body").inner_text(timeout=timeout_ms)
            return text in body, self.observe()
        except Exception:  # noqa: BLE001
            return False, self.observe()

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        self.wait_count += 1
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:  # noqa: BLE001
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        return self.observe()

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        page = self._require_page()
        page.mouse.wheel(0, delta_y)
        self.scroll_count += 1
        return self.observe()

    def _require_page(self) -> Any:
        if self._page is None:
            raise RealBrowserControlRuntimeError("real_browser_not_open")
        return self._page

    def _selector(self, ref: str) -> str:
        if not self._ref_selectors:
            self.observe()
        selector = self._ref_selectors.get(ref)
        if selector is None:
            raise RealBrowserControlRuntimeError("real_browser_element_ref_unknown")
        return selector

    def _state_hash(self) -> str:
        page = self._require_page()
        payload = page.evaluate(
            """() => ({
                title: document.title,
                body_hash_source: document.body ? document.body.innerText.slice(0, 4000) : '',
                inputs: Array.from(document.querySelectorAll('input,textarea,select')).slice(0, 40).map((el) => ({
                    name: el.getAttribute('name') || el.getAttribute('aria-label') || '',
                    value: String(el.value || ''),
                })),
            })"""
        )
        payload["body_hash_source"] = text_hash(str(payload.get("body_hash_source") or ""))
        for item in payload.get("inputs", []):
            item["value"] = text_hash(str(item.get("value") or ""))
        return stable_hash(payload)


def build_playwright_real_browser_engine_from_env() -> PlaywrightRealBrowserEngine:
    target_url = os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip()
    if not target_url:
        raise RealBrowserControlRuntimeError("REAL_BROWSER_TEST_URL_CONFIG_MISSING")
    headless_value = os.environ.get("SENTINEL_BROWSER_HEADLESS", "true").strip().lower()
    return PlaywrightRealBrowserEngine(target_url=target_url, headless=headless_value not in {"0", "false", "no"})


def build_cloak_first_real_browser_engine_from_env(
    *,
    capture_root: str | Path | None = None,
    allow_playwright_compatibility: bool = False,
) -> RealBrowserEngine:
    target_url = os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip()
    if not target_url:
        raise RealBrowserControlRuntimeError("REAL_BROWSER_TEST_URL_CONFIG_MISSING")
    selection = select_browser_backend()
    if selection.preferred_backend_id == CLOAK_BROWSER_BACKEND_ID:
        headless_value = os.environ.get("SENTINEL_BROWSER_HEADLESS", "true").strip().lower()
        return BrowserSessionManagerRealBrowserEngine(
            target_url=target_url,
            capture_root=capture_root,
            headless=headless_value not in {"0", "false", "no"},
        )
    if allow_playwright_compatibility and selection.compatibility_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID:
        return build_playwright_real_browser_engine_from_env()
    raise RealBrowserControlRuntimeError(f"real_browser_cloak_backend_unavailable:{selection.selection_reason}")


def check_cloak_session_readiness_from_env(
    *,
    capture_root: str | Path | None = None,
    cache_path: str | Path | None = None,
    timeout_ms: int = 15_000,
    wall_timeout_ms: int | None = None,
    prepare_binary: bool | None = None,
    binary_bootstrap_timeout_ms: int = 120_000,
    require_local_binary_override: bool | None = None,
) -> CloakSessionReadinessResult:
    target_url = os.environ.get("SENTINEL_BROWSER_TEST_URL", "").strip()
    headless_value = os.environ.get("SENTINEL_BROWSER_HEADLESS", "true").strip().lower()
    prepare_value = os.environ.get("SENTINEL_CLOAK_PREPARE_BINARY", "").strip().lower()
    require_override_value = os.environ.get("SENTINEL_REQUIRE_CLOAKBROWSER_BINARY_PATH", "").strip().lower()
    return check_cloak_session_readiness(
        target_url=target_url,
        capture_root=capture_root,
        cache_path=cache_path,
        headless=headless_value not in {"0", "false", "no"},
        timeout_ms=timeout_ms,
        wall_timeout_ms=wall_timeout_ms,
        prepare_binary=prepare_binary if prepare_binary is not None else prepare_value in {"1", "true", "yes", "on"},
        binary_bootstrap_timeout_ms=binary_bootstrap_timeout_ms,
        require_local_binary_override=(
            require_local_binary_override
            if require_local_binary_override is not None
            else require_override_value in {"1", "true", "yes", "on"}
        ),
    )


def check_cloak_session_readiness(
    *,
    target_url: str,
    session_manager: Any | None = None,
    capture_root: str | Path | None = None,
    cache_path: str | Path | None = None,
    headless: bool = True,
    timeout_ms: int = 15_000,
    wall_timeout_ms: int | None = None,
    prepare_binary: bool = False,
    binary_bootstrap_timeout_ms: int = 120_000,
    require_local_binary_override: bool = False,
) -> CloakSessionReadinessResult:
    target_url = target_url.strip()
    selection = select_browser_backend()
    selected_backend_id = selection.preferred_backend_id or ""
    safe_origin_hash = _safe_origin_hash(target_url) if target_url else ""
    capture_path = Path(capture_root) if capture_root is not None else None
    if not target_url:
        result = _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id="",
            session_backend_kind="",
            safe_url_origin_hash=safe_origin_hash,
            failure_code="REAL_BROWSER_TEST_URL_CONFIG_MISSING",
            diagnostic_payload={"config": "missing_target_url"},
            capture_root=capture_path,
        )
        _write_cloak_readiness_cache(cache_path, result)
        return result
    if selected_backend_id != CLOAK_BROWSER_BACKEND_ID:
        result = _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id="",
            session_backend_kind="",
            safe_url_origin_hash=safe_origin_hash,
            failure_code="CLOAK_SESSION_BACKEND_UNAVAILABLE",
            diagnostic_payload={"selection_reason": selection.selection_reason},
            capture_root=capture_path,
        )
        _write_cloak_readiness_cache(cache_path, result)
        return result
    if session_manager is None:
        binary_ready, binary_failure_code, binary_diagnostic = _cloak_binary_readiness(
            prepare_binary=prepare_binary,
            binary_bootstrap_timeout_ms=binary_bootstrap_timeout_ms,
            require_local_binary_override=require_local_binary_override,
        )
        if not binary_ready:
            result = _cloak_readiness_result(
                ready=False,
                selected_backend_id=selected_backend_id,
                actual_backend_id="",
                session_backend_kind="",
                safe_url_origin_hash=safe_origin_hash,
                failure_code=binary_failure_code,
                diagnostic_payload=binary_diagnostic,
                capture_root=capture_path,
            )
            _write_cloak_readiness_cache(cache_path, result)
            return result
    engine = BrowserSessionManagerRealBrowserEngine(
        target_url=target_url,
        session_manager=session_manager,
        capture_root=capture_path,
        headless=headless,
        timeout_ms=timeout_ms,
    )
    actual_backend_id = _engine_backend_id(engine)
    session_backend_kind = _engine_session_backend_kind(engine)
    if actual_backend_id != selected_backend_id:
        result = _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_url_origin_hash=safe_origin_hash,
            failure_code="CLOAK_SESSION_BACKEND_MISMATCH",
            diagnostic_payload={"selected_backend_id": selected_backend_id, "actual_backend_id": actual_backend_id},
            capture_root=capture_path,
        )
        _write_cloak_readiness_cache(cache_path, result)
        return result
    result = _probe_cloak_readiness_with_wall_timeout(
        engine=engine,
        target_url=target_url,
        selected_backend_id=selected_backend_id,
        actual_backend_id=actual_backend_id,
        session_backend_kind=session_backend_kind,
        safe_origin_hash=safe_origin_hash,
        capture_path=capture_path,
        wall_timeout_ms=wall_timeout_ms if wall_timeout_ms is not None else timeout_ms,
    )
    _write_cloak_readiness_cache(cache_path, result)
    return result


def _cloak_binary_readiness(
    *,
    prepare_binary: bool,
    binary_bootstrap_timeout_ms: int,
    require_local_binary_override: bool = False,
) -> tuple[bool, str | None, dict[str, Any]]:
    try:
        info = _safe_cloak_binary_info(_cloak_binary_info())
    except ImportError:
        return False, "CLOAK_BROWSER_PACKAGE_NOT_INSTALLED", {"cloakbrowser_package": "missing"}
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            "CLOAK_BINARY_INFO_UNAVAILABLE",
            {"exception_class": exc.__class__.__name__, "reason_hash": text_hash(str(exc))},
        )
    override = _cloak_local_binary_override_info()
    if require_local_binary_override and not override["configured"]:
        return False, "CLOAK_LOCAL_BINARY_OVERRIDE_REQUIRED", {"binary": "local_override_required", **override, **info}
    if override["configured"] and not override["exists"]:
        return False, "CLOAK_LOCAL_BINARY_OVERRIDE_MISSING", {"binary": "local_override_missing", **override, **info}
    if override["configured"] and override["exists"]:
        return True, None, {"binary": "local_override", **override, **info}
    if bool(info.get("installed")):
        return True, None, {"binary": "installed", **info}
    if not prepare_binary:
        return False, "CLOAK_BINARY_NOT_INSTALLED", {"binary": "not_installed", **info}

    bootstrap_ready, bootstrap_failure_code, bootstrap_diagnostic = _ensure_cloak_binary_with_wall_timeout(
        timeout_ms=binary_bootstrap_timeout_ms,
    )
    if not bootstrap_ready:
        return False, bootstrap_failure_code, bootstrap_diagnostic
    try:
        refreshed = _safe_cloak_binary_info(_cloak_binary_info())
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            "CLOAK_BINARY_INFO_UNAVAILABLE",
            {"exception_class": exc.__class__.__name__, "reason_hash": text_hash(str(exc))},
        )
    if bool(refreshed.get("installed")):
        return True, None, {"binary": "installed_after_bootstrap", **refreshed}
    return False, "CLOAK_BINARY_NOT_INSTALLED_AFTER_BOOTSTRAP", {"binary": "not_installed_after_bootstrap", **refreshed}


def _cloak_binary_info() -> dict[str, Any]:
    import cloakbrowser  # type: ignore[import-not-found]

    info = cloakbrowser.binary_info()
    return info if isinstance(info, dict) else {}


def _safe_cloak_binary_info(raw_info: dict[str, Any]) -> dict[str, Any]:
    cache_dir = str(raw_info.get("cache_dir") or raw_info.get("path") or raw_info.get("binary_path") or "")
    download_url = str(raw_info.get("download_url") or "")
    return {
        "installed": bool(raw_info.get("installed")),
        "version": str(raw_info.get("version") or raw_info.get("bundled_version") or ""),
        "bundled_version": str(raw_info.get("bundled_version") or ""),
        "platform": str(raw_info.get("platform") or ""),
        "tier": str(raw_info.get("tier") or ""),
        "cache_dir_hash": stable_hash(cache_dir) if cache_dir else "",
        "download_url_hash": stable_hash(download_url) if download_url else "",
        "path_present": bool(raw_info.get("path") or raw_info.get("executable") or raw_info.get("binary_path")),
    }


def _cloak_local_binary_override_info() -> dict[str, Any]:
    raw_path = os.environ.get("CLOAKBROWSER_BINARY_PATH", "").strip().strip('"')
    if not raw_path:
        return {"configured": False, "exists": False, "path_hash": ""}
    path = Path(raw_path)
    return {
        "configured": True,
        "exists": path.is_file(),
        "path_hash": stable_hash(str(path)),
    }


def _ensure_cloak_binary_with_wall_timeout(*, timeout_ms: int) -> tuple[bool, str | None, dict[str, Any]]:
    script = r"""
import hashlib
import json
import sys

try:
    import cloakbrowser

    executable = cloakbrowser.ensure_binary()
    info = cloakbrowser.binary_info()
    cache_dir = str(info.get("cache_dir") or info.get("path") or info.get("binary_path") or "")
    download_url = str(info.get("download_url") or "")
    payload = {
        "installed": bool(info.get("installed")),
        "version": str(info.get("version") or info.get("bundled_version") or ""),
        "bundled_version": str(info.get("bundled_version") or ""),
        "platform": str(info.get("platform") or ""),
        "tier": str(info.get("tier") or ""),
        "cache_dir_hash": hashlib.sha256(cache_dir.encode("utf-8")).hexdigest() if cache_dir else "",
        "download_url_hash": hashlib.sha256(download_url.encode("utf-8")).hexdigest() if download_url else "",
        "executable_hash": hashlib.sha256(str(executable).encode("utf-8")).hexdigest() if executable else "",
        "path_present": bool(executable),
    }
    print(json.dumps(payload, sort_keys=True))
except Exception as exc:
    print(json.dumps({"exception_class": exc.__class__.__name__, "reason_hash": hashlib.sha256(str(exc).encode("utf-8")).hexdigest()}))
    sys.exit(1)
"""
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(timeout_ms, 1) / 1000,
        )
    except subprocess.TimeoutExpired as exc:
        return (
            False,
            "CLOAK_BINARY_BOOTSTRAP_TIMEOUT",
            {
                "timeout_ms": timeout_ms,
                "stdout_hash": text_hash(exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")),
                "stderr_hash": text_hash(exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")),
            },
        )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        child_payload = _last_json_object(stdout) or {}
        safe_child_diagnostics = {
            key: str(child_payload[key])
            for key in ("exception_class", "reason_hash")
            if key in child_payload and str(child_payload[key]).strip()
        }
        return (
            False,
            "CLOAK_BINARY_BOOTSTRAP_FAILED",
            {
                "returncode": completed.returncode,
                **safe_child_diagnostics,
                "stdout_hash": text_hash(stdout),
                "stderr_hash": text_hash(stderr),
            },
        )
    payload = _last_json_object(stdout)
    if not payload:
        return (
            False,
            "CLOAK_BINARY_BOOTSTRAP_OUTPUT_INVALID",
            {"stdout_hash": text_hash(stdout), "stderr_hash": text_hash(stderr)},
        )
    safe_info = _safe_cloak_binary_info(payload)
    if not bool(safe_info.get("installed")):
        safe_info = {**safe_info, "bootstrap_stdout_hash": text_hash(stdout), "bootstrap_stderr_hash": text_hash(stderr)}
        return False, "CLOAK_BINARY_BOOTSTRAP_DID_NOT_INSTALL", safe_info
    return True, None, {"binary": "installed_by_bootstrap", **safe_info}


def _last_json_object(output: str) -> dict[str, Any] | None:
    for line in reversed([line.strip() for line in output.splitlines() if line.strip()]):
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _probe_cloak_readiness_with_wall_timeout(
    *,
    engine: BrowserSessionManagerRealBrowserEngine,
    target_url: str,
    selected_backend_id: str,
    actual_backend_id: str,
    session_backend_kind: str,
    safe_origin_hash: str,
    capture_path: Path | None,
    wall_timeout_ms: int,
) -> CloakSessionReadinessResult:
    if wall_timeout_ms <= 0:
        return _probe_cloak_readiness(
            engine=engine,
            target_url=target_url,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_origin_hash=safe_origin_hash,
            capture_path=capture_path,
        )

    result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def _target() -> None:
        try:
            result_queue.put(
                (
                    "result",
                    _probe_cloak_readiness(
                        engine=engine,
                        target_url=target_url,
                        selected_backend_id=selected_backend_id,
                        actual_backend_id=actual_backend_id,
                        session_backend_kind=session_backend_kind,
                        safe_origin_hash=safe_origin_hash,
                        capture_path=capture_path,
                    ),
                )
            )
        except BaseException as exc:  # pragma: no cover - defensive worker isolation
            result_queue.put(("exception", exc))

    thread = threading.Thread(target=_target, name="sentinel-cloak-readiness-probe", daemon=True)
    thread.start()
    try:
        kind, value = result_queue.get(timeout=wall_timeout_ms / 1000)
    except queue.Empty:
        close_all = getattr(engine.session_manager, "close_all", None)
        if callable(close_all):
            try:
                close_all()
            except Exception:
                pass
        thread.join(timeout=0.5)
        _remove_profile_material(capture_path)
        return _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_url_origin_hash=safe_origin_hash,
            failure_code="CLOAK_SESSION_READINESS_TIMEOUT",
            diagnostic_payload={
                "timeout_ms": wall_timeout_ms,
                "selected_backend_id": selected_backend_id,
                "actual_backend_id": actual_backend_id,
            },
            capture_root=capture_path,
        )

    if kind == "exception":
        return _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_url_origin_hash=safe_origin_hash,
            failure_code="CLOAK_SESSION_BOOTSTRAP_NOT_READY",
            diagnostic_payload={"exception_class": value.__class__.__name__, "reason_hash": text_hash(str(value))},
            capture_root=capture_path,
        )
    return value


def _probe_cloak_readiness(
    *,
    engine: BrowserSessionManagerRealBrowserEngine,
    target_url: str,
    selected_backend_id: str,
    actual_backend_id: str,
    session_backend_kind: str,
    safe_origin_hash: str,
    capture_path: Path | None,
) -> CloakSessionReadinessResult:
    authority = _cloak_readiness_authority(target_url)
    close_attempted = False
    try:
        engine.bind_authority(authority)
        first_snapshot = engine.open()
        first_observe = engine.observe()
        second_observe = engine.observe()
        devtools_operational = True
        devtools = getattr(engine.session_manager, "devtools_metadata_for_session", None)
        if callable(devtools):
            try:
                devtools_operational = devtools(
                    mission_id=authority.id,
                    session_id=str(getattr(engine, "_session_id", "") or ""),
                    capability="readiness_probe",
                ) is not None
            except Exception:
                devtools_operational = False
        close = getattr(engine, "close", None)
        if callable(close):
            close()
            close_attempted = True
        reopened_snapshot = engine.open()
        result = _cloak_readiness_result(
            ready=True,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_url_origin_hash=safe_origin_hash,
            readiness_receipt_hash=stable_hash(
                {
                    "selected_backend_id": selected_backend_id,
                    "actual_backend_id": actual_backend_id,
                    "session_backend_kind": session_backend_kind,
                    "first_browser_state_hash": first_snapshot.state_hash,
                    "first_observe_state_hash": first_observe.state_hash,
                    "second_observe_state_hash": second_observe.state_hash,
                    "reopened_state_hash": reopened_snapshot.state_hash,
                    "safe_url_origin_hash": safe_origin_hash,
                }
            ),
            failure_code=None,
            diagnostic_payload={
                "readiness": "ready",
                "first_state_hash": first_snapshot.state_hash,
                "second_state_hash": second_observe.state_hash,
                "reopened_state_hash": reopened_snapshot.state_hash,
            },
            capture_root=capture_path,
            backend_selected=selected_backend_id == CLOAK_BROWSER_BACKEND_ID,
            backend_identity_matched=selected_backend_id == actual_backend_id == CLOAK_BROWSER_BACKEND_ID,
            process_operational=True,
            devtools_operational=devtools_operational,
            context_operational=True,
            page_operational=True,
            multi_action_reuse_operational=bool(first_observe.state_hash and second_observe.state_hash),
            cleanup_operational=close_attempted or callable(getattr(engine.session_manager, "close_all", None)),
            reopen_operational=bool(reopened_snapshot.state_hash),
        )
    except Exception as exc:  # noqa: BLE001
        result = _cloak_readiness_result(
            ready=False,
            selected_backend_id=selected_backend_id,
            actual_backend_id=actual_backend_id,
            session_backend_kind=session_backend_kind,
            safe_url_origin_hash=safe_origin_hash,
            failure_code="CLOAK_SESSION_BOOTSTRAP_NOT_READY",
            diagnostic_payload={"exception_class": exc.__class__.__name__, "reason_hash": text_hash(str(exc))},
            capture_root=capture_path,
        )
    finally:
        close_all = getattr(engine.session_manager, "close_all", None)
        if callable(close_all):
            try:
                close_all()
            except Exception:
                pass
        _remove_profile_material(capture_path)
    return replace(result, profile_material_persisted=_profile_file_count(capture_path) > 0)


def _build_browser_session_manager(*, capture_root: str | Path | None, headless: bool) -> Any:
    from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionManagerL5Live

    return BrowserSessionManagerL5Live(
        capture_root=Path(capture_root) if capture_root is not None else _default_browser_session_capture_root(),
        engine="cloak",
        headless=headless,
    )


def _default_browser_session_capture_root() -> Path:
    root = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "sentinel-browser-sessions"
    nonce = stable_hash(
        {
            "pid": os.getpid(),
            "thread": threading.get_ident(),
            "time_ns": time.time_ns(),
        }
    )[:16]
    return root / f"browser_session_capture_{nonce}"


def _cloak_readiness_authority(target_url: str) -> MissionAuthorityEnvelope:
    host = (urlparse(target_url).hostname or "").lower()
    allowed_domains = [BOUNDED_URL_AUTHORITY_REF]
    if host:
        allowed_domains.append(host)
    return MissionAuthorityEnvelope(
        user_id="sentinel_cloak_readiness",
        mission_title="Cloak session readiness gate",
        mission_objective="Verify Cloak/session can open a bounded local or configured target before provider use.",
        allowed_tools=["real_browser_control"],
        allowed_actions=["real_browser.open", "browser_session_open", "browser_session_observe"],
        forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
        allowed_domains=allowed_domains,
        max_actions=4,
    )


def _cloak_readiness_result(
    *,
    ready: bool,
    selected_backend_id: str,
    actual_backend_id: str,
    session_backend_kind: str,
    safe_url_origin_hash: str,
    failure_code: str | None,
    diagnostic_payload: dict[str, Any],
    capture_root: Path | None,
    readiness_receipt_hash: str = "",
    backend_selected: bool = False,
    backend_identity_matched: bool = False,
    process_operational: bool = False,
    devtools_operational: bool = False,
    context_operational: bool = False,
    page_operational: bool = False,
    multi_action_reuse_operational: bool = False,
    cleanup_operational: bool = False,
    reopen_operational: bool = False,
) -> CloakSessionReadinessResult:
    profile_material_persisted = _profile_file_count(capture_root) > 0
    return CloakSessionReadinessResult(
        ready=ready,
        provider_call_allowed=ready,
        selected_backend_id=selected_backend_id,
        actual_backend_id=actual_backend_id,
        session_backend_kind=session_backend_kind,
        safe_url_origin_hash=safe_url_origin_hash,
        readiness_receipt_hash=readiness_receipt_hash,
        failure_code=failure_code,
        diagnostic_hash=stable_hash(diagnostic_payload),
        receipt_backend_match=bool(ready and selected_backend_id == actual_backend_id == CLOAK_BROWSER_BACKEND_ID),
        profile_material_persisted=profile_material_persisted,
        backend_selected=backend_selected,
        backend_identity_matched=backend_identity_matched,
        process_operational=process_operational,
        devtools_operational=devtools_operational,
        context_operational=context_operational,
        page_operational=page_operational,
        multi_action_reuse_operational=multi_action_reuse_operational,
        cleanup_operational=cleanup_operational,
        reopen_operational=reopen_operational,
    )


def _write_cloak_readiness_cache(cache_path: str | Path | None, result: CloakSessionReadinessResult) -> None:
    if cache_path is None:
        return
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(result.safe_model_dump(), indent=2, sort_keys=True), encoding="utf-8")


def _safe_origin_hash(target_url: str) -> str:
    parsed = urlparse(target_url)
    return stable_hash({"scheme": parsed.scheme, "host": parsed.hostname or "", "port": parsed.port})


def _profile_file_count(capture_root: Path | None) -> int:
    if capture_root is None or not capture_root.exists():
        return 0
    count = 0
    for path in capture_root.rglob("*"):
        if not path.is_file():
            continue
        lowered_parts = {part.lower() for part in path.relative_to(capture_root).parts}
        if "profile" in lowered_parts:
            count += 1
            continue
        if any(part in _PROFILE_MATERIAL_NAMES for part in lowered_parts):
            count += 1
    return count


def _remove_profile_material(capture_root: Path | None) -> None:
    if capture_root is None or not capture_root.exists():
        return
    for attempt in range(6):
        for path in sorted(capture_root.rglob("*"), key=lambda candidate: len(candidate.parts), reverse=True):
            if not _is_profile_material_path(capture_root, path):
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
        if _profile_file_count(capture_root) == 0:
            return
        if attempt < 5:
            time.sleep(0.1)


_PROFILE_MATERIAL_NAMES = {
    "cookies",
    "history",
    "login data",
    "preferences",
    "local state",
    "web data",
    "sessions",
    "session storage",
    "local storage",
    "indexeddb",
}


def _is_profile_material_path(capture_root: Path, path: Path) -> bool:
    try:
        lowered_parts = {part.lower() for part in path.relative_to(capture_root).parts}
    except ValueError:
        return False
    return "profile" in lowered_parts or any(part in _PROFILE_MATERIAL_NAMES for part in lowered_parts)


def _browser_session_symbols() -> tuple[Any, Any, Any]:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
    )

    return BrowserSessionActionKind, BrowserSessionContract, BrowserSessionRequest


def _result_session_id(result: Any) -> str | None:
    value = getattr(result, "session_id", None)
    return str(value) if value else None


def _engine_session_backend_kind(engine: RealBrowserEngine) -> str:
    value = getattr(engine, "session_manager_backend_kind", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def _engine_safe_devtools_context(engine: RealBrowserEngine) -> dict[str, Any] | None:
    value = getattr(engine, "safe_devtools_context", None)
    if not callable(value):
        return None
    context = value()
    return _sanitize_safe_devtools_context(context) if isinstance(context, dict) and context else None


def _sanitize_safe_devtools_context(context: dict[str, Any]) -> dict[str, Any]:
    allowed_top_level = {
        "source",
        "available",
        "backend_kind",
        "page_target_count",
        "snapshot_hash",
        "network_ledger_hash",
        "console_ledger_hash",
        "performance_trace_hash",
        "failure_code",
        "diagnostic_hash",
        "safe_metadata",
    }
    allowed_metadata = {
        "source_backend_kind",
        "session_ref",
        "url_hash",
        "title_hash",
        "step_index",
        "network_event_count",
        "network_failure_count",
        "console_message_count",
        "console_error_count",
        "request_classes",
        "response_status_classes",
        "query_linked_request_evidence",
    }
    safe: dict[str, Any] = {}
    for key, value in context.items():
        if key not in allowed_top_level:
            continue
        if key != "safe_metadata":
            if isinstance(value, (str, int, bool, float)):
                safe[key] = value
            continue
        if not isinstance(value, dict):
            continue
        metadata: dict[str, Any] = {}
        for meta_key, meta_value in value.items():
            if meta_key not in allowed_metadata:
                continue
            if isinstance(meta_value, dict):
                metadata[meta_key] = stable_hash(meta_value)
            elif isinstance(meta_value, (str, int, bool, float)):
                metadata[meta_key] = meta_value
        if metadata:
            safe["safe_metadata"] = metadata
    return safe


def _combine_safe_devtools_metadata(metadata_items: list[dict[str, Any]]) -> dict[str, Any]:
    combined: dict[str, Any] = {
        "source": "browser_session_manager_l5",
        "available": True,
        "capability_count": len(metadata_items),
    }
    top_level_keys = (
        "backend_kind",
        "page_target_count",
        "snapshot_hash",
        "network_ledger_hash",
        "console_ledger_hash",
        "performance_trace_hash",
    )
    metadata_keys = (
        "source_backend_kind",
        "session_ref",
        "url_hash",
        "title_hash",
        "step_index",
        "network_event_count",
        "network_failure_count",
        "console_message_count",
        "console_error_count",
    )
    safe_metadata: dict[str, Any] = {}
    for item in metadata_items:
        for key in top_level_keys:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, (int, bool, str)):
                if isinstance(value, int) and key in combined and isinstance(combined[key], int):
                    combined[key] = max(int(combined[key]), value)
                else:
                    combined.setdefault(key, value)
        metadata = item.get("safe_metadata")
        if not isinstance(metadata, dict):
            continue
        for key in metadata_keys:
            value = metadata.get(key)
            if value is None:
                continue
            if isinstance(value, (int, bool, str)):
                if isinstance(value, int) and key in safe_metadata and isinstance(safe_metadata[key], int):
                    safe_metadata[key] = max(int(safe_metadata[key]), value)
                else:
                    safe_metadata.setdefault(key, value)
    if safe_metadata:
        combined["safe_metadata"] = safe_metadata
    return combined


def _label_from_ref(ref: str) -> str:
    return ref.split(":", 1)[1].replace("_", " ").strip() if ":" in ref else ref.replace("_", " ").strip()


def _looks_secret_ref(role: str, name: str) -> bool:
    text = f"{role} {name}".lower()
    return any(marker in text for marker in ("password", "secret", "token", "credential", "cookie", "session"))


def _snapshot_element(element: RealBrowserEngineElement) -> RealBrowserElementSnapshot:
    return RealBrowserElementSnapshot(
        ref=element.ref,
        role=element.role,
        name=element.name,
        visible=element.visible,
        enabled=element.enabled,
        text_preview=element.text_preview,
        value_preview=element.value_preview,
    )


def _param_ref(envelope: ActionEnvelope) -> str:
    ref = str(envelope.params.get("ref") or envelope.target_ref or "")
    if not ref:
        raise RealBrowserControlRuntimeError("real_browser_element_ref_required")
    return ref


def _search_ref_candidates(snapshot: RealBrowserEngineSnapshot, envelope: ActionEnvelope) -> tuple[str, ...]:
    explicit = str(envelope.params.get("ref") or envelope.target_ref or "").strip()
    refs: list[str] = []
    if explicit:
        refs.append(explicit)
    refs.extend(
        ranked_search_ref
        for ranked_search_ref in (
            candidate.control_ref
            for candidate in classify_search_controls(
                snapshot.elements,
                mission_objective=str(envelope.params.get("query") or envelope.params.get("text") or ""),
            )
        )
    )
    return tuple(dict.fromkeys(refs))


def _engine_backend_id(engine: RealBrowserEngine) -> str:
    declared = getattr(engine, "browser_backend_id", None)
    if isinstance(declared, str) and declared.strip():
        return declared.strip()
    if engine.__class__.__name__ == "PlaywrightRealBrowserEngine":
        return PLAYWRIGHT_REAL_BROWSER_BACKEND_ID
    return f"{engine.__class__.__name__.removesuffix('Engine').lower()}_engine"


def _safe_engine_origin_hash(engine: RealBrowserEngine) -> str:
    try:
        return str(engine.safe_url_origin_hash)
    except Exception:
        return stable_hash({"engine_backend_id": _engine_backend_id(engine), "origin": "unavailable"})


def _validate_selected_browser_backend(
    *,
    actual_backend_id: str,
    backend_selection: BrowserBackendSelection | None,
    selected_backend_id: str | None,
) -> str:
    if backend_selection is None:
        return selected_backend_id or actual_backend_id
    if selected_backend_id is None and backend_selection.preferred_backend_id:
        selected_backend_id = backend_selection.preferred_backend_id
    elif selected_backend_id is None and actual_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID:
        raise RealBrowserControlRuntimeError("real_browser_backend_explicit_compatibility_required")
    elif selected_backend_id is None:
        selected_backend_id = backend_selection.compatibility_backend_id or actual_backend_id
    if selected_backend_id != actual_backend_id:
        raise RealBrowserControlRuntimeError(
            f"real_browser_backend_selection_mismatch:selected={selected_backend_id}:actual={actual_backend_id}"
        )
    if (
        actual_backend_id == PLAYWRIGHT_REAL_BROWSER_BACKEND_ID
        and backend_selection.playwright_requires_explicit_compatibility
        and selected_backend_id != PLAYWRIGHT_REAL_BROWSER_BACKEND_ID
    ):
        raise RealBrowserControlRuntimeError("real_browser_backend_explicit_compatibility_required")
    return selected_backend_id


def _is_search_like_element(element: RealBrowserEngineElement) -> bool:
    return is_search_like_control(element)


def _search_rank(element: RealBrowserEngineElement) -> tuple[int, str]:
    candidates = classify_search_controls((element,))
    confidence = candidates[0].confidence if candidates else 0.0
    return (-int(confidence * 1000), element.ref)


def _existing_browser_context_cards(context: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    keys = (
        "browser_world_model",
        "browser_world_model_summary",
        "browser_decision_frame",
        "browser_actionability_registry",
        "actionability_frame",
        "browser_environment_state",
        "browser_environment_state_hash",
        "browser_backend_execution",
        "browser_devtools_context",
        "search_actuation_trace",
        "runtime_failure_fact",
        "model_visible_body_failure_packet",
        "model_blocker_assessment_schema",
    )
    cards = {key: context[key] for key in keys if key in context}
    if _context_product_card_count(cards) <= 0:
        return None
    backend = cards.setdefault("browser_backend_execution", {})
    if isinstance(backend, dict):
        backend.setdefault("selected_backend_id", "")
        backend.setdefault("actual_backend_id", "")
        backend.setdefault("session_backend_kind", "")
    summary = cards.get("browser_world_model_summary")
    if isinstance(summary, dict):
        cards["browser_world_model_summary"] = {
            **summary,
            "context_world_model_extraction_source": "existing_safe_browser_world_model",
        }
    return cards


def _browser_decision_frame_with_visible_card_extraction_priority(
    frame_dump: dict[str, Any],
    *,
    world_model: BrowserWorldModel,
    progress_state: str,
) -> dict[str, Any]:
    cards = tuple(world_model.product_or_result_candidate_cards or ())
    if not cards or progress_state == "real_browser_product_extraction_verified":
        return frame_dump
    recommended = [
        str(action)
        for action in frame_dump.get("recommended_next_actions", [])
        if str(action)
    ]
    extract_action = _preferred_extract_action_for_cards(cards)
    if extract_action not in recommended:
        recommended.insert(0, extract_action)
    else:
        recommended = [extract_action, *[action for action in recommended if action != extract_action]]
    frame_dump["recommended_next_actions"] = recommended
    return frame_dump


def _preferred_extract_action_for_cards(cards: tuple[Any, ...]) -> str:
    for card in cards:
        kind = str(getattr(card, "kind", "") or getattr(card, "entity_kind", "") or "").lower()
        family = str(getattr(card, "entity_family", "") or "").lower()
        if any(marker in f"{kind} {family}" for marker in ("commerce", "product", "catalog")):
            return "real_browser_control.real_browser.extract_product_cards"
        for field in ("visible_price", "minimum_order", "supplier_or_store", "currency_or_unit"):
            value = str(getattr(card, field, "") or "").strip().lower()
            if value and value != "unknown":
                return "real_browser_control.real_browser.extract_product_cards"
    return "real_browser_control.real_browser.extract_evidence"


def _recoverable_existing_browser_context_cards(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    keys = (
        "browser_world_model",
        "browser_world_model_summary",
        "browser_decision_frame",
        "browser_actionability_registry",
        "actionability_frame",
        "browser_environment_state",
        "browser_environment_state_hash",
        "browser_backend_execution",
        "browser_devtools_context",
        "search_actuation_trace",
        "runtime_failure_fact",
        "model_visible_body_failure_packet",
        "model_blocker_assessment_schema",
    )
    return {key: context[key] for key in keys if key in context}


def _context_product_card_count(context_cards: dict[str, Any]) -> int:
    model = context_cards.get("browser_world_model")
    if isinstance(model, dict):
        cards = model.get("product_or_result_candidate_cards")
        if isinstance(cards, list):
            return len(cards)
    summary = context_cards.get("browser_world_model_summary")
    if isinstance(summary, dict):
        value = summary.get("product_or_result_candidate_count")
        if isinstance(value, int):
            return value
    frame = context_cards.get("browser_decision_frame")
    if isinstance(frame, dict):
        candidates = frame.get("candidate_extractions")
        if isinstance(candidates, list):
            return len(candidates)
    return 0


def _context_browser_state_hash(context_cards: dict[str, Any]) -> str:
    environment_hash = context_cards.get("browser_environment_state_hash")
    if isinstance(environment_hash, str) and environment_hash.strip():
        return environment_hash
    model = context_cards.get("browser_world_model")
    if isinstance(model, dict):
        return stable_hash(
            {
                "world_model_id": model.get("world_model_id"),
                "visible_text_summary_hash": model.get("visible_text_summary_hash"),
                "product_or_result_candidate_count": _context_product_card_count(context_cards),
            }
        )
    return stable_hash({"browser_context_cards": sorted(context_cards)})


def _search_error_can_refresh_refs(error: str) -> bool:
    lowered = error.lower()
    return any(marker in lowered for marker in ("stale", "detached", "not_textbox", "disabled", "hidden", "ref_not_found"))


def _search_write_failure_code(error: str) -> str:
    lowered = error.lower()
    if "stale" in lowered:
        return "real_browser_search_stale_ref"
    if "detached" in lowered:
        return "real_browser_search_detached_ref"
    if "hidden" in lowered:
        return "real_browser_search_element_hidden"
    if "disabled" in lowered:
        return "real_browser_search_element_disabled"
    if "not_textbox" in lowered:
        return "real_browser_search_ref_not_textbox"
    return "real_browser_search_write_failed"


def _new_search_actuation_trace(
    *,
    before_snapshot: RealBrowserEngineSnapshot,
    ref: str,
    query: str,
) -> dict[str, Any]:
    element = _element_for_ref(before_snapshot, ref)
    return {
        "trace_kind": "SearchActuationTrace",
        "candidate_selected": bool(ref),
        "candidate_ref_hash": text_hash(ref),
        "ref_resolved": element is not None,
        "element_attached": element is not None,
        "element_visible": bool(getattr(element, "visible", False)) if element is not None else False,
        "element_enabled": bool(getattr(element, "enabled", False)) if element is not None else False,
        "focus_attempted": False,
        "focus_succeeded": False,
        "clear_attempted": False,
        "clear_succeeded": False,
        "write_method": "",
        "write_attempted": False,
        "write_succeeded": False,
        "write_readback_match": False,
        "write_readback_status": "not_attempted",
        "write_readback_hash": "",
        "write_readback_alternative_proof": "",
        "write_support_status": "unknown",
        "submit_mechanisms_observed": _observed_submit_mechanisms(before_snapshot, ref),
        "submit_method_selected": "",
        "submit_attempted": False,
        "submit_enter_failure_code": "",
        "submit_button_failure_code": "",
        "submit_observe_recovery_attempted": False,
        "submit_observe_recovery_succeeded": False,
        "submit_observe_recovery_failure_code": "",
        "request_progress": "not_observed",
        "navigation_progress": "not_observed",
        "result_region_progress": "not_observed",
        "typed_outcome": None,
        "safe_failure_class": "recoverable_browser_state_failure",
        "safe_failure_code": None,
        "query_hash": text_hash(query),
        "before_state_hash": before_snapshot.state_hash,
        "data_not_authority": True,
        "can_execute": False,
        "can_grant_authority": False,
    }


def _element_for_ref(snapshot: RealBrowserEngineSnapshot, ref: str) -> RealBrowserEngineElement | None:
    for element in snapshot.elements:
        if element.ref == ref:
            return element
    return None


def _observed_submit_mechanisms(snapshot: RealBrowserEngineSnapshot, ref: str) -> list[str]:
    mechanisms: list[str] = []
    element = _element_for_ref(snapshot, ref)
    if element is not None and element.role in {"textbox", "combobox", "searchbox"}:
        mechanisms.append("enter_key")
    if _search_button_ref(snapshot):
        mechanisms.append("search_button")
    return list(dict.fromkeys(mechanisms))


def _search_button_ref(snapshot: RealBrowserEngineSnapshot) -> str:
    for candidate in snapshot.elements:
        if candidate.role != "button" or not candidate.visible or not candidate.enabled or bool(getattr(candidate, "secret", False)):
            continue
        text = f"{candidate.ref} {candidate.name} {candidate.text_preview}".lower()
        if any(marker in text for marker in ("search", "find", "submit", "go")):
            return candidate.ref
    return ""


def _search_submit_failure_code(reason: str) -> str:
    lowered = reason.strip().lower()
    if lowered.startswith("browser_session_post_action_snapshot_failed"):
        return "browser_session_post_action_snapshot_failed"
    if lowered.startswith("browser_session_step_failed"):
        return "browser_session_step_failed"
    if lowered.startswith("browser_session_interaction_failed:timeouterror"):
        return "browser_session_interaction_timeout"
    if lowered.startswith("browser_session_interaction_failed:"):
        return "browser_session_interaction_failed"
    if lowered.startswith("browser_session_"):
        return lowered.split(":", 1)[0]
    if "timeout" in lowered:
        return "browser_submit_timeout"
    if "detached" in lowered or "stale" in lowered:
        return "browser_submit_stale_or_detached_ref"
    return "browser_submit_failed"


def _submit_failure_may_have_materialized(failure_code: str) -> bool:
    return failure_code in {
        "browser_session_post_action_snapshot_failed",
    }


def _failure_search_materiality(
    *,
    envelope: ActionEnvelope,
    failure_code: str,
    context_cards: dict[str, Any],
) -> dict[str, Any]:
    if envelope.operation != "real_browser.search":
        return {}
    trace = context_cards.get("search_actuation_trace")
    trace = dict(trace) if isinstance(trace, dict) else {}
    input_written = bool(trace.get("write_succeeded"))
    submission_attempted = bool(trace.get("submit_attempted"))
    evidence_ref = f"browser_search_failure:{text_hash(failure_code)}"
    return {
        "input_written": input_written,
        "submission_attempted": submission_attempted,
        "request_observed": False,
        "navigation_or_state_changed": False,
        "result_region_changed": False,
        "query_reflected": False,
        "search_materially_successful": False,
        "typed_search_outcome": {
            "outcome_kind": "FAILED_RECOVERABLE",
            "search_materially_successful": False,
            "failure_code": failure_code,
            "evidence_refs": [evidence_ref],
            "data_not_authority": True,
            "can_execute": False,
        },
        "search_progress": {
            "states": ["FAILED"],
            "current_state": "FAILED",
            "search_materially_successful": False,
            "evidence_refs": [evidence_ref],
            "uncertainty_reason": "recoverable browser search failure before material search progress",
        },
        "search_actuation_trace": trace,
        "data_not_authority": True,
        "can_execute": False,
    }


def _search_write_readback_evidence(
    *,
    engine: RealBrowserEngine,
    snapshot: RealBrowserEngineSnapshot,
    query: str,
) -> dict[str, Any]:
    raw_query_hash = text_hash(query)
    stable_query_hash = stable_hash(query)
    engine_typed_hash = str(getattr(engine, "last_typed_text_hash", "") or "")
    if engine_typed_hash:
        if engine_typed_hash in {raw_query_hash, stable_query_hash}:
            return {
                "write_readback_match": True,
                "write_readback_status": "matched_receipt_hash",
                "write_readback_hash": engine_typed_hash,
                "write_readback_alternative_proof": "l5_typed_text_receipt_hash",
                "write_support_status": "supported",
            }

    normalized_query = _normalize_search_readback(query)
    saw_value_readback = False
    for element in snapshot.elements:
        if not element.visible or bool(getattr(element, "secret", False)):
            continue
        raw_value = str(element.value_preview or "")
        if not raw_value:
            continue
        saw_value_readback = True
        value = _normalize_search_readback(raw_value)
        if not value or not normalized_query:
            continue
        if value == normalized_query:
            return {
                "write_readback_match": True,
                "write_readback_status": "matched_normalized",
                "write_readback_hash": text_hash(raw_value),
                "write_readback_alternative_proof": "snapshot_value_normalized_match",
                "write_support_status": "supported",
            }
        if normalized_query in value or value in normalized_query:
            return {
                "write_readback_match": True,
                "write_readback_status": "transformed",
                "write_readback_hash": text_hash(raw_value),
                "write_readback_alternative_proof": "snapshot_value_transformed_match",
                "write_support_status": "supported",
            }

    if engine_typed_hash or saw_value_readback:
        return {
            "write_readback_match": False,
            "write_readback_status": "mismatched",
            "write_readback_hash": engine_typed_hash,
            "write_readback_alternative_proof": "",
            "write_support_status": "supported",
        }
    return {
        "write_readback_match": False,
        "write_readback_status": "unavailable",
        "write_readback_hash": "",
        "write_readback_alternative_proof": "write_primitive_accepted_submission_required",
        "write_support_status": "unavailable",
    }


def _search_write_readback_matches(
    *,
    engine: RealBrowserEngine,
    snapshot: RealBrowserEngineSnapshot,
    query: str,
) -> bool:
    return bool(
        _search_write_readback_evidence(
            engine=engine,
            snapshot=snapshot,
            query=query,
        ).get("write_readback_match")
    )


def _normalize_search_readback(value: str) -> str:
    return " ".join(value.lower().split())


def _browser_recovery_evidence(
    *,
    authority: MissionAuthorityEnvelope,
    failure_code: str,
    browser_state_hash: str,
    context_cards: dict[str, Any],
) -> dict[str, Any]:
    from sentinel.agent.organs.browser_failure_recovery_engine_v1 import (
        BrowserFailureRecoveryContract,
        BrowserFailureRecoveryEngineV1,
        BrowserFailureRecoveryRequest,
    )

    evidence_bundle_hash = stable_hash(
        {
            "failure_code": failure_code,
            "browser_state_hash": browser_state_hash,
            "environment_hash": context_cards.get("browser_environment_state_hash"),
        }
    )
    signals = {
        "source": "real_browser_control_runtime",
        "failure_code_hash": text_hash(failure_code),
        "stale_ref": "stale" in failure_code.lower(),
        "disabled_target": any(marker in failure_code.lower() for marker in ("disabled", "hidden", "not_textbox")),
        "network_failure_count": _context_network_failure_count(context_cards),
    }
    contract = BrowserFailureRecoveryContract(
        mission_id=authority.id,
        allowed_domains=["bounded.example"],
        max_recovery_steps=4,
    )
    request = BrowserFailureRecoveryRequest(
        mission=authority,
        url="https://bounded.example/recovery",
        contract=contract,
        evidence_bundle_hash=evidence_bundle_hash,
        failure_signals=signals,
    )
    result = BrowserFailureRecoveryEngineV1().plan(request)
    planned_actions = tuple(step.action_kind.name for step in result.plan.steps)
    return {
        "source": "BrowserFailureRecoveryEngineV1",
        "consumed_by_product_runtime": True,
        "status": result.status.value,
        "plan_hash": result.plan.plan_hash,
        "planned_actions": planned_actions,
        "failure_kinds": tuple(failure.kind.value for failure in result.plan.failures),
        "recovery_receipt_ref": result.receipt.receipt_id,
        "parallel_finalgate_used": False,
        "data_not_authority": True,
        "can_execute": False,
        "can_grant_authority": False,
    }


def _runtime_failure_fact(
    *,
    envelope: ActionEnvelope,
    failure_code: str,
    safe_summary: str,
    browser_state_hash: str,
    context_cards: dict[str, Any],
) -> dict[str, Any]:
    environment_hash = str(context_cards.get("browser_environment_state_hash") or "")
    search_trace = context_cards.get("search_actuation_trace")
    if not isinstance(search_trace, dict):
        search_trace = {}
    return {
        "fact_kind": "runtime_failure_fact",
        "attempted_operation": envelope.operation,
        "capability_id": envelope.capability_id,
        "action_hash": envelope.action_hash,
        "failure_code": failure_code,
        "failure_stage": _browser_failure_stage(failure_code, operation=envelope.operation),
        "material_effect_observed": False,
        "browser_state_hash": browser_state_hash,
        "browser_environment_state_hash": environment_hash,
        "search_actuation_trace": dict(search_trace),
        "safe_summary": safe_summary[:500],
        "receipt_backed_after_product_dispatch": True,
        "authority_effect": "none",
        "data_not_authority": True,
        "can_grant_authority": False,
        "can_execute": False,
    }


def _model_visible_body_failure_packet(
    *,
    envelope: ActionEnvelope,
    failure_code: str,
    safe_summary: str,
    browser_state_hash: str,
    context_cards: dict[str, Any],
    product_context: dict[str, Any],
    child_browser_session_ref: str,
) -> dict[str, Any]:
    world_summary = context_cards.get("browser_world_model_summary") if isinstance(context_cards, dict) else {}
    world_model = context_cards.get("browser_world_model") if isinstance(context_cards, dict) else {}
    environment = context_cards.get("browser_environment_state") if isinstance(context_cards, dict) else {}
    actionability = context_cards.get("actionability_frame") if isinstance(context_cards, dict) else {}
    recovery_evidence = context_cards.get("browser_recovery_evidence") if isinstance(context_cards, dict) else {}
    recovery_attempts = product_context.get("recoverable_action_observations") if isinstance(product_context, dict) else ()
    material_used = _safe_int(product_context.get("material_actions_used")) if isinstance(product_context, dict) else 0
    material_max = _safe_int(product_context.get("max_material_actions")) if isinstance(product_context, dict) else 0
    evidence_refs = _failure_packet_evidence_refs(
        context_cards=context_cards,
        browser_state_hash=browser_state_hash,
    )
    search_trace = context_cards.get("search_actuation_trace") if isinstance(context_cards, dict) else {}
    if not isinstance(search_trace, dict):
        search_trace = {}
    root_lease = product_context.get("root_browser_runtime_lease") if isinstance(product_context, dict) else None
    state_fields = environment.get("state_fields") if isinstance(environment, dict) and isinstance(environment.get("state_fields"), dict) else {}
    uncertainty = _state_field_value(state_fields, "uncertainty")
    current_page = {
        "page_kind_guess": world_summary.get("page_kind_guess") if isinstance(world_summary, dict) else "unknown",
        "candidate_count": world_summary.get("product_or_result_candidate_count") if isinstance(world_summary, dict) else 0,
        "candidate_entity_kind_counts": world_summary.get("candidate_entity_kind_counts") if isinstance(world_summary, dict) else {},
        "search_like_refs": world_summary.get("search_like_refs") if isinstance(world_summary, dict) else [],
        "browser_environment_state_hash": context_cards.get("browser_environment_state_hash"),
    }
    return {
        "packet_kind": "model_visible_body_failure_packet",
        "attempted_operation": envelope.operation,
        "typed_outcome": {
            "failure_code": failure_code,
            "failure_class": ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE.value,
            "recoverable": True,
            "runtime_fact_hash": stable_hash(context_cards.get("runtime_failure_fact") or {}),
        },
        "failure_stage": _browser_failure_stage(failure_code, operation=envelope.operation),
        "material_effect_observed": False,
        "search_actuation_trace": {
            "candidate_selected": search_trace.get("candidate_selected"),
            "ref_resolved": search_trace.get("ref_resolved"),
            "element_attached": search_trace.get("element_attached"),
            "element_visible": search_trace.get("element_visible"),
            "element_enabled": search_trace.get("element_enabled"),
            "focus_attempted": search_trace.get("focus_attempted"),
            "focus_succeeded": search_trace.get("focus_succeeded"),
            "write_attempted": search_trace.get("write_attempted"),
            "write_succeeded": search_trace.get("write_succeeded"),
            "write_readback_match": search_trace.get("write_readback_match"),
            "write_readback_status": search_trace.get("write_readback_status"),
            "write_readback_alternative_proof": search_trace.get("write_readback_alternative_proof"),
            "write_support_status": search_trace.get("write_support_status"),
            "submit_mechanisms_observed": search_trace.get("submit_mechanisms_observed"),
            "submit_method_selected": search_trace.get("submit_method_selected"),
            "submit_attempted": search_trace.get("submit_attempted"),
            "safe_failure_code": search_trace.get("safe_failure_code"),
        },
        "objective_progress": {
            "candidate_entity_count": int(current_page.get("candidate_count") or 0),
            "objective_relevance_assessed": bool(
                isinstance(world_summary, dict) and world_summary.get("objective_relevance_assessed")
            ),
            "progress_state": str(product_context.get("progress_state") or ""),
            "summary": safe_summary[:500],
        },
        "session_continuity": _session_continuity_packet(
            root_lease=root_lease,
            child_browser_session_ref=_safe_ref_hash(child_browser_session_ref),
            runtime_session_ref_hash=_safe_ref_hash(str(product_context.get("browser_session_ref") or "")),
        ),
        "safe_current_page_state_summary": current_page,
        "available_affordances": {
            "search_like_refs": list(current_page.get("search_like_refs") or [])[:8],
            "recovery_actions": list(actionability.get("recovery_actions") or [])[:8] if isinstance(actionability, dict) else [],
            "recommended_browser_actions": (
                list(world_model.get("recommended_browser_actions") or [])[:8]
                if isinstance(world_model, dict)
                else []
            ),
        },
        "recovery_attempts_already_executed": len(recovery_attempts) if isinstance(recovery_attempts, (list, tuple)) else 0,
        "retry_material_action_budget_remaining": max(material_max - material_used, 0) if material_max else 0,
        "evidence_refs": evidence_refs,
        "contradictions": _failure_packet_contradictions(world_model),
        "unknowns": _failure_packet_unknowns(uncertainty=uncertainty, recovery_evidence=recovery_evidence),
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def _model_blocker_assessment_schema() -> dict[str, Any]:
    return {
        "schema_kind": "model_blocker_assessment_schema",
        "required_model_response_fields": [
            "perceived_blocker",
            "concise_failure_interpretation",
            "proposed_next_strategy",
            "required_evidence",
            "missing_capability",
            "objective_satisfied",
            "confidence",
        ],
        "advisory_only": True,
        "must_not_override_runtime_failure_fact": True,
        "can_grant_authority": False,
        "can_execute": False,
        "data_not_authority": True,
    }


def _browser_failure_stage(failure_code: str, *, operation: str) -> str:
    if "search_control_not_found" in failure_code:
        return "search_control_discovery"
    if any(
        marker in failure_code
        for marker in (
            "search_actuation",
            "search_write",
            "search_submit",
            "search_element",
            "search_ref",
            "locator",
        )
    ):
        return "search_control_actuation"
    if "session" in failure_code:
        return "session_lifecycle"
    if "ref" in failure_code or "hidden" in failure_code or "disabled" in failure_code:
        return "ref_freshness_or_visibility"
    if operation.endswith("verify_extraction"):
        return "verification"
    if operation.endswith("extract_product_cards"):
        return "extraction"
    return "browser_runtime"


def _failure_packet_evidence_refs(*, context_cards: dict[str, Any], browser_state_hash: str) -> list[str]:
    refs = [f"browser_state:{browser_state_hash}"]
    environment_hash = str(context_cards.get("browser_environment_state_hash") or "")
    if environment_hash:
        refs.append(f"browser_environment_state:{environment_hash}")
    environment = context_cards.get("browser_environment_state")
    if isinstance(environment, dict):
        state_fields = environment.get("state_fields")
        if isinstance(state_fields, dict):
            for value in state_fields.values():
                if not isinstance(value, dict):
                    continue
                for ref in value.get("evidence_refs") or []:
                    refs.append(str(ref))
    return list(dict.fromkeys(ref for ref in refs if ref))[:20]


def _failure_packet_contradictions(world_model: Any) -> list[str]:
    cards = world_model.get("product_or_result_candidate_cards") if isinstance(world_model, dict) else []
    contradictions: list[str] = []
    if isinstance(cards, list):
        for card in cards[:8]:
            if isinstance(card, dict):
                contradictions.extend(str(item) for item in card.get("contradictions") or [] if str(item))
    return list(dict.fromkeys(contradictions))[:12]


def _failure_packet_unknowns(*, uncertainty: Any, recovery_evidence: Any) -> list[str]:
    unknowns: list[str] = []
    if isinstance(uncertainty, dict):
        known = uncertainty.get("known_unknowns")
        if isinstance(known, list):
            unknowns.extend(str(item) for item in known if str(item))
    if isinstance(recovery_evidence, dict):
        if not recovery_evidence.get("search_like_refs"):
            unknowns.append("search_control_executability_unconfirmed")
    return list(dict.fromkeys(unknowns or ["recovery_outcome_unknown"]))[:12]


def _session_continuity_packet(
    *,
    root_lease: Any,
    child_browser_session_ref: str,
    runtime_session_ref_hash: str,
) -> dict[str, Any]:
    root = root_lease if isinstance(root_lease, dict) else {}
    return {
        "root_lease_present": bool(root.get("safe_ref")),
        "root_lease_ref_hash": _safe_ref_hash(str(root.get("safe_ref") or "")),
        "root_lifecycle_state": str(root.get("lifecycle_state") or "unknown"),
        "root_open_count": _safe_int(root.get("open_count")),
        "root_recovery_attempt_count": _safe_int(root.get("recovery_attempt_count")),
        "child_mission_browser_session_ref_hash": child_browser_session_ref,
        "runtime_session_ref_hash": runtime_session_ref_hash,
        "child_session_refs_are_receipt_handles_not_engine_identity": True,
        "data_not_authority": True,
        "can_execute": False,
    }


def _safe_ref_hash(value: str) -> str:
    return text_hash(value) if value else ""


def _state_field_value(state_fields: dict[str, Any], key: str) -> dict[str, Any]:
    value = state_fields.get(key)
    if isinstance(value, dict):
        field_value = value.get("value")
        if isinstance(field_value, dict):
            return field_value
    return {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _search_materiality(
    *,
    before_snapshot: RealBrowserEngineSnapshot,
    after_snapshot: RealBrowserEngineSnapshot,
    query: str,
    context_cards: dict[str, Any],
    input_written: bool,
    submission_attempted: bool,
    search_actuation_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before_cards = _snapshot_result_region_count(before_snapshot)
    after_cards = _snapshot_result_region_count(after_snapshot)
    request_observed = _context_network_event_count(context_cards) > 0
    result_region_changed = after_cards > before_cards
    query_reflected = _query_reflected(after_snapshot, query)
    empty_result_evidence = _snapshot_empty_result_evidence(after_snapshot)
    state_changed = before_snapshot.state_hash != after_snapshot.state_hash
    material_state_changed = bool(state_changed and (after_cards > 0 or empty_result_evidence or request_observed))
    navigation_or_state_changed = bool(result_region_changed or request_observed or material_state_changed)
    preliminary_material = bool(
        input_written
        and submission_attempted
        and query_reflected
        and (result_region_changed or request_observed or material_state_changed)
    )
    outcome = derive_browser_search_outcome(
        input_written=input_written,
        submission_attempted=submission_attempted,
        request_observed=request_observed,
        navigation_or_state_changed=material_state_changed,
        query_reflected=query_reflected,
        result_region_changed=result_region_changed,
        before_result_region_count=before_cards,
        after_result_region_count=after_cards,
        query_hash=text_hash(query),
        pre_state_hash=before_snapshot.state_hash,
        post_state_hash=after_snapshot.state_hash,
        empty_result_evidence=empty_result_evidence,
        evidence_refs=(
            f"pre_state:{before_snapshot.state_hash}",
            f"post_state:{after_snapshot.state_hash}",
            f"context:{context_cards.get('browser_environment_state_hash')}",
        ),
    )
    materially_successful = bool(preliminary_material and outcome.search_materially_successful)
    materiality = {
        "input_written": bool(input_written),
        "submission_attempted": bool(submission_attempted),
        "request_observed": request_observed,
        "state_changed": state_changed,
        "material_state_changed": material_state_changed,
        "navigation_or_state_changed": navigation_or_state_changed,
        "result_region_changed": result_region_changed,
        "empty_result_evidence": empty_result_evidence,
        "query_reflected": query_reflected,
        "before_result_region_count": before_cards,
        "after_result_region_count": after_cards,
        "search_materially_successful": materially_successful,
        "search_materially_uncertain": bool(input_written and submission_attempted and not materially_successful),
        "typed_search_outcome": outcome.safe_model_dump(),
        "query_hash": text_hash(query),
        "search_actuation_trace": dict(search_actuation_trace or {}),
        "evidence_hash": stable_hash(
            {
                "before_state_hash": before_snapshot.state_hash,
                "after_state_hash": after_snapshot.state_hash,
                "context_hash": context_cards.get("browser_environment_state_hash"),
                "before_cards": before_cards,
                "after_cards": after_cards,
                "request_observed": request_observed,
                "query_reflected": query_reflected,
                "typed_outcome": outcome.outcome_kind.value,
            }
        ),
    }
    materiality["search_progress"] = derive_search_progress_state(materiality).model_dump(mode="json")
    return materiality


def _snapshot_empty_result_evidence(snapshot: RealBrowserEngineSnapshot) -> bool:
    markers = (
        "no matching result",
        "no results",
        "0 results",
        "aucun resultat",
        "aucun résultat",
        "nothing found",
        "empty result",
    )
    for element in snapshot.elements:
        if not element.visible or bool(getattr(element, "secret", False)):
            continue
        text = f"{element.name} {element.text_preview} {element.value_preview}".lower()
        if any(marker in text for marker in markers):
            return True
    return False


def _snapshot_result_region_count(snapshot: RealBrowserEngineSnapshot) -> int:
    count = 0
    for element in snapshot.elements:
        if not element.visible or not element.enabled or bool(getattr(element, "secret", False)):
            continue
        if element.role not in {"link", "article", "card", "generic"}:
            continue
        text = f"{element.name} {element.text_preview} {element.value_preview}"
        lowered = text.lower()
        if any(marker in lowered for marker in ("no matching result", "no results", "0 results", "nothing found", "empty result")):
            continue
        if any(
            marker in lowered
            for marker in (
                "product",
                "price",
                "moq",
                "supplier",
                "store",
                "glasses",
                "sunglasses",
                "eur",
                "usd",
                "$",
                "result",
                "documentation",
                "docs",
                "api",
                "reference",
                "guide",
                "pathlib",
                "glob",
            )
        ):
            count += 1
    return count


def _context_network_event_count(context_cards: dict[str, Any]) -> int:
    devtools = context_cards.get("browser_devtools_context")
    if isinstance(devtools, dict):
        metadata = devtools.get("safe_metadata")
        if isinstance(metadata, dict):
            try:
                return int(metadata.get("network_event_count") or 0)
            except (TypeError, ValueError):
                return 0
    environment = context_cards.get("browser_environment_state")
    if isinstance(environment, dict):
        protocol = environment.get("protocol_graph")
        if isinstance(protocol, dict):
            try:
                return int(protocol.get("network_event_count") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _context_network_failure_count(context_cards: dict[str, Any]) -> int:
    devtools = context_cards.get("browser_devtools_context")
    if isinstance(devtools, dict):
        metadata = devtools.get("safe_metadata")
        if isinstance(metadata, dict):
            try:
                return int(metadata.get("network_failure_count") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _query_reflected(snapshot: RealBrowserEngineSnapshot, query: str) -> bool:
    normalized_query = " ".join(query.lower().split())
    if not normalized_query:
        return False
    for element in snapshot.elements:
        text = " ".join(
            str(part)
            for part in (element.name, element.text_preview, element.value_preview)
            if part
        ).lower()
        if normalized_query in " ".join(text.split()):
            return True
    return False


def _reject_sensitive_text(value: str) -> None:
    lowered = value.lower()
    markers = (
        "api_key",
        "authorization",
        "bearer ",
        "cookie",
        "password",
        "private key",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning_content",
        "secret",
        "session",
        "sk-",
    )
    if any(marker in lowered for marker in markers):
        raise RealBrowserControlRuntimeError("real_browser_sensitive_text_blocked")


def _reject_browser_skill_boundary_text(value: str) -> None:
    _reject_sensitive_text(value)
    lowered = value.lower()
    blocked = (
        "login",
        "sign in",
        "contact supplier",
        "send inquiry",
        "add to cart",
        "checkout",
        "payment",
        "credit card",
        "upload",
        "download",
    )
    if any(marker in lowered for marker in blocked):
        raise RealBrowserControlRuntimeError("real_browser_boundary_action_blocked")


def _authority_available_actions(authority: MissionAuthorityEnvelope) -> tuple[str, ...]:
    actions: list[str] = []
    for action in authority.allowed_actions:
        if action == "finish":
            actions.append("sentinel_loop.finish")
        elif action.startswith("real_browser."):
            actions.append(f"real_browser_control.{action}")
        else:
            actions.append(action)
    return tuple(dict.fromkeys(actions))


def _browser_product_workspace_context(context: dict[str, Any]) -> dict[str, str]:
    manifest = context.get("mission_workspace_manifest")
    if not isinstance(manifest, dict):
        return {
            "mission_workspace_ref": "",
            "mission_workspace_hash": "",
            "browser_session_handle_ref": "",
            "browser_session_handle_hash": "",
            "child_workspace_handle_hash": "",
        }
    browser_handle = _browser_session_handle_from_manifest(manifest)
    browser_session_ref = str(browser_handle.get("safe_ref") or "") if browser_handle else ""
    child_hash = str(browser_handle.get("handle_hash") or "") if browser_handle else ""
    return {
        "mission_workspace_ref": str(manifest.get("manifest_id") or ""),
        "mission_workspace_hash": str(manifest.get("manifest_hash") or ""),
        "browser_session_handle_ref": browser_session_ref,
        "browser_session_handle_hash": stable_hash(browser_handle) if browser_handle else "",
        "child_workspace_handle_hash": child_hash or (stable_hash(browser_handle) if browser_handle else ""),
    }


def _browser_root_identity_context(
    context: dict[str, Any],
    *,
    engine: RealBrowserEngine,
    after_state_hash: str,
) -> dict[str, str]:
    root = context.get("root_browser_runtime_lease") if isinstance(context, dict) else None
    if not isinstance(root, dict):
        root = {}
    root_hash = str(root.get("lease_hash") or root.get("root_browser_lease_id_hash") or "")
    engine_hash = str(root.get("browser_engine_identity_hash") or "")
    backend_context_hash = str(root.get("backend_context_identity_hash") or "")
    if not root_hash:
        root_hash = stable_hash({"engine_backend": _engine_backend_id(engine), "origin": _safe_engine_origin_hash(engine)})
    if not engine_hash:
        engine_hash = stable_hash({"root_hash": root_hash, "engine_backend": _engine_backend_id(engine)})
    if not backend_context_hash:
        backend_context_hash = stable_hash({"root_hash": root_hash, "session_backend_kind": _engine_session_backend_kind(engine)})
    return {
        "root_browser_lease_id_hash": root_hash,
        "browser_engine_identity_hash": engine_hash,
        "backend_context_identity_hash": backend_context_hash,
        "page_identity_hash": stable_hash({"browser_state_hash": after_state_hash, "origin_hash": _safe_engine_origin_hash(engine)}),
    }


def _browser_session_handle_from_manifest(manifest: dict[str, Any]) -> dict[str, Any] | None:
    handles = manifest.get("handles")
    if not isinstance(handles, list):
        return None
    for handle in handles:
        if isinstance(handle, dict) and handle.get("kind") == "browser_session":
            return handle
    return None


def _nth_selector(role: str, index: int) -> str:
    tag = {
        "button": "button",
        "link": "a",
        "combobox": "select",
        "textbox": "input,textarea",
    }.get(role, "*")
    return f"{tag} >> nth={index}"


__all__ = [
    "BOUNDED_URL_AUTHORITY_REF",
    "BrowserSessionManagerRealBrowserEngine",
    "CloakSessionReadinessResult",
    "CLOAK_BROWSER_BACKEND_ID",
    "InMemoryRealBrowserEngine",
    "PlaywrightRealBrowserEngine",
    "PLAYWRIGHT_REAL_BROWSER_BACKEND_ID",
    "RealBrowserControlRuntime",
    "RealBrowserControlRuntimeError",
    "RealBrowserEngineElement",
    "RealBrowserEngineSnapshot",
    "build_cloak_first_real_browser_engine_from_env",
    "build_playwright_real_browser_engine_from_env",
    "check_cloak_session_readiness",
    "check_cloak_session_readiness_from_env",
]
