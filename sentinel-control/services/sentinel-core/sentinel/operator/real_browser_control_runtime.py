from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.browser_decision_frame import BrowserDecisionFrameCompiler
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.kernel import MissionKernel
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


class RealBrowserControlRuntime:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        engine: RealBrowserEngine,
        bounded_url_ref: str = "env:SENTINEL_BROWSER_TEST_URL",
        session_ref: str = DEFAULT_SESSION_REF,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.engine = engine
        self.bounded_url_ref = bounded_url_ref
        self.session_ref = session_ref

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        if envelope.capability_id != "real_browser_control":
            raise RealBrowserControlRuntimeError("real_browser_control_capability_required")
        if envelope.operation == "real_browser.open":
            return self._open(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.observe":
            return self._observe(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.click":
            return self._click(envelope, authority=authority)
        if envelope.operation == "real_browser.type_text":
            return self._type_text(envelope, authority=authority)
        if envelope.operation == "real_browser.select_option":
            return self._select_option(envelope, authority=authority)
        if envelope.operation == "real_browser.assert_text":
            return self._assert_text(envelope, authority=authority)
        if envelope.operation == "real_browser.extract_text":
            return self._extract_text(envelope, authority=authority, context=context)
        if envelope.operation == "real_browser.press_key":
            return self._press_key(envelope, authority=authority)
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

    def _click(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.click")
        ref = _param_ref(envelope)
        before = self.engine.observe().state_hash
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

    def _type_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.type_text")
        ref = _param_ref(envelope)
        text = str(envelope.params.get("text") or "")
        _reject_sensitive_text(text)
        before = self.engine.observe().state_hash
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

    def _select_option(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.select_option")
        ref = _param_ref(envelope)
        option = str(envelope.params.get("option") or envelope.params.get("value") or "")
        _reject_sensitive_text(option)
        before = self.engine.observe().state_hash
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

    def _press_key(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "real_browser.press_key")
        ref = _param_ref(envelope)
        key = str(envelope.params.get("key") or envelope.params.get("keyboard_key") or "")
        if key not in {"Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"}:
            raise RealBrowserControlRuntimeError("real_browser_key_not_allowed")
        before = self.engine.observe().state_hash
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
    ) -> ActionResult:
        receipt = RealBrowserActionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=self.session_ref,
            bounded_url_ref=self.bounded_url_ref,
            safe_url_origin_hash=self.engine.safe_url_origin_hash,
            stable_element_ref=element_ref,
            action_kind=action_kind,
            status=status,
            before_state_hash=before_state_hash,
            after_state_hash=after_state_hash,
            bounded_observation_summary_hash=stable_hash(
                {
                    "safe_url_origin_hash": self.engine.safe_url_origin_hash,
                    "after_state_hash": after_state_hash,
                    "action_kind": action_kind,
                    "element_ref_hash": text_hash(element_ref),
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
            context_cards=context_cards or {},
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
        world_dump = world_model.model_dump(mode="json")
        frame_dump = frame.model_dump(mode="json")
        self._write_artifact("world_models", world_model.world_model_id, world_dump)
        self._write_artifact("decision_frames", frame.frame_id, frame_dump)
        return {
            "browser_world_model": world_dump,
            "browser_world_model_summary": world_model.compact_summary(),
            "browser_decision_frame": frame_dump,
        }

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
    "InMemoryRealBrowserEngine",
    "PlaywrightRealBrowserEngine",
    "RealBrowserControlRuntime",
    "RealBrowserControlRuntimeError",
    "RealBrowserEngineElement",
    "RealBrowserEngineSnapshot",
    "build_playwright_real_browser_engine_from_env",
]
