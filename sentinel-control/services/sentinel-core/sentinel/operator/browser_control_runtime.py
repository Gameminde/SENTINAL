from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.browser_control_models import (
    BrowserActionReceipt,
    BrowserAssertionReceipt,
    BrowserElementSnapshot,
    BrowserFinalCertificate,
    BrowserObservationReceipt,
)
from sentinel.operator.kernel import MissionKernel


class BrowserControlRuntimeError(RuntimeError):
    pass


FIXTURE_REF = "fixture:sentinel-browser"
SESSION_REF = "browser_session:sentinel-fixture"


@dataclass
class BrowserFixtureElement:
    ref: str
    role: str
    name: str
    visible: bool = True
    enabled: bool = True
    secret: bool = False

    @property
    def state(self) -> str:
        visibility = "visible" if self.visible else "hidden"
        enabled = "enabled" if self.enabled else "disabled"
        return f"{visibility}/{enabled}"


@dataclass
class BrowserFixtureState:
    title: str = "Sentinel Browser Fixture"
    enabled: bool = False
    input_value: str = ""
    display_text: str = ""
    selected_option: str = ""

    def state_hash(self) -> str:
        return stable_hash(
            {
                "title": self.title,
                "enabled": self.enabled,
                "input_value_hash": text_hash(self.input_value),
                "display_text_hash": text_hash(self.display_text),
                "selected_option": self.selected_option,
            }
        )


class BrowserControlRuntime:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        state: BrowserFixtureState | None = None,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.state = state or BrowserFixtureState()
        self.observe_count = 0
        self.click_count = 0
        self.type_count = 0
        self.assert_count = 0
        self.select_count = 0

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        del context
        if envelope.capability_id != "browser_control":
            raise BrowserControlRuntimeError("browser_control_capability_required")
        if envelope.operation == "browser.observe":
            return self._observe(envelope, authority=authority)
        if envelope.operation == "browser.click":
            return self._click(envelope, authority=authority)
        if envelope.operation == "browser.type_text":
            return self._type_text(envelope, authority=authority)
        if envelope.operation == "browser.select_option":
            return self._select_option(envelope, authority=authority)
        if envelope.operation == "browser.assert_text":
            return self._assert_text(envelope, authority=authority)
        if envelope.operation == "browser.finish_browser_step":
            self._require_authorized(authority, "browser.finish_browser_step")
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="completed",
                material_action=False,
                observation_summary="browser step finished.",
                result_hash=stable_hash({"operation": envelope.operation, "state_hash": self.state.state_hash()}),
            )
        raise BrowserControlRuntimeError(f"browser_control_operation_unsupported:{envelope.operation}")

    def _observe(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "browser.observe")
        self.observe_count += 1
        elements = tuple(
            BrowserElementSnapshot(ref=element.ref, role=element.role, name=element.name, state=element.state)
            for element in self._observable_elements()
        )
        summary_hash = stable_hash({"title": self.state.title, "elements": [element.safe_model_dump() for element in elements]})
        receipt = BrowserObservationReceipt(
            mission_id=self.mission_id,
            browser_session_ref=SESSION_REF,
            fixture_ref=FIXTURE_REF,
            page_title=self.state.title,
            page_state_hash=self.state.state_hash(),
            elements=elements,
            bounded_observation_summary_hash=summary_hash,
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._append_event(
            "browser_fixture_observed",
            "Bounded browser fixture observed with stable role refs.",
            metadata={"element_count": len(elements), "page_state_hash": self.state.state_hash()},
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
            observation_summary=f"browser fixture observed with {len(elements)} stable element refs.",
            result_hash=receipt.receipt_hash,
        )

    def _click(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "browser.click")
        ref = _param_ref(envelope)
        element = self._require_interactable(ref)
        if element.role != "button":
            raise BrowserControlRuntimeError("browser_click_ref_not_button")
        before = self.state.state_hash()
        if ref == "button:enable_sentinel":
            self.state.enabled = True
            if not self.state.display_text:
                self.state.display_text = "Sentinel enabled"
        after = self.state.state_hash()
        self.click_count += 1
        return self._record_action(
            envelope,
            action_kind="browser.click",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=after,
            status="completed",
            summary=f"browser click completed on stable ref {ref}.",
        )

    def _type_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "browser.type_text")
        ref = _param_ref(envelope)
        element = self._require_interactable(ref)
        if element.role not in {"textbox", "combobox"}:
            raise BrowserControlRuntimeError("browser_type_ref_not_textbox")
        text = str(envelope.params.get("text") or "")
        _reject_sensitive_text(text)
        if element.secret:
            raise BrowserControlRuntimeError("browser_secret_field_blocked")
        before = self.state.state_hash()
        self.state.input_value = text
        if self.state.enabled and text:
            self.state.display_text = text
        after = self.state.state_hash()
        self.type_count += 1
        return self._record_action(
            envelope,
            action_kind="browser.type_text",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=after,
            status="completed",
            summary=f"browser type_text completed on stable ref {ref}.",
        )

    def _select_option(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "browser.select_option")
        ref = _param_ref(envelope)
        element = self._require_interactable(ref)
        if element.role != "combobox":
            raise BrowserControlRuntimeError("browser_select_ref_not_combobox")
        option = str(envelope.params.get("option") or envelope.params.get("value") or "")
        _reject_sensitive_text(option)
        before = self.state.state_hash()
        self.state.selected_option = option
        after = self.state.state_hash()
        self.select_count += 1
        return self._record_action(
            envelope,
            action_kind="browser.select_option",
            element_ref=ref,
            before_state_hash=before,
            after_state_hash=after,
            status="completed",
            summary=f"browser select_option completed on stable ref {ref}.",
        )

    def _assert_text(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "browser.assert_text")
        text = str(envelope.params.get("text") or envelope.params.get("expected_text") or envelope.target_ref or "")
        _reject_sensitive_text(text)
        status = "passed" if text and (text in self.state.display_text or text in self.state.input_value) else "failed"
        self.assert_count += 1
        receipt = BrowserAssertionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=SESSION_REF,
            fixture_ref=FIXTURE_REF,
            assertion_kind="text_contains",
            status=status,
            expected_text_hash=text_hash(text),
            page_state_hash=self.state.state_hash(),
            bounded_observation_summary_hash=self._summary_hash(),
        )
        certificate = BrowserFinalCertificate(
            mission_id=self.mission_id,
            status="accepted" if status == "passed" else "blocked",
            accepted=status == "passed",
            reason=f"browser_assert_text_{status}",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "browser_fixture_assertion_completed",
            "Bounded browser fixture text assertion completed.",
            metadata={"status": status, "page_state_hash": self.state.state_hash(), "result_hash": receipt.result_hash},
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
            observation_summary=f"browser text assertion {status}.",
            result_hash=receipt.result_hash,
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
    ) -> ActionResult:
        receipt = BrowserActionReceipt(
            mission_id=self.mission_id,
            browser_session_ref=SESSION_REF,
            fixture_ref=FIXTURE_REF,
            stable_element_ref=element_ref,
            action_kind=action_kind,
            status=status,
            before_state_hash=before_state_hash,
            after_state_hash=after_state_hash,
            bounded_observation_summary_hash=self._summary_hash(),
        )
        certificate = BrowserFinalCertificate(
            mission_id=self.mission_id,
            status="accepted",
            accepted=True,
            reason=f"{action_kind}_completed",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "browser_fixture_action_completed",
            "Bounded browser fixture action completed.",
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
            material_action=True,
            observation_summary=summary,
            result_hash=receipt.result_hash,
        )

    def _require_authorized(self, authority: MissionAuthorityEnvelope, action_name: str) -> None:
        if authority.revoked_at is not None:
            raise BrowserControlRuntimeError("mission_authority_inactive")
        if "browser_control" not in authority.allowed_tools:
            raise BrowserControlRuntimeError("browser_control_tool_not_authorized")
        if action_name not in authority.allowed_actions and action_name.split(".", 1)[-1] not in authority.allowed_actions:
            raise BrowserControlRuntimeError("browser_control_action_not_authorized")
        if FIXTURE_REF not in authority.allowed_domains:
            raise BrowserControlRuntimeError("browser_control_fixture_not_authorized")

    def _require_interactable(self, ref: str) -> BrowserFixtureElement:
        element = self._elements().get(ref)
        if element is None:
            raise BrowserControlRuntimeError("browser_element_ref_unknown")
        if not element.visible:
            raise BrowserControlRuntimeError("browser_element_hidden")
        if not element.enabled:
            raise BrowserControlRuntimeError("browser_element_disabled")
        if element.secret:
            raise BrowserControlRuntimeError("browser_secret_field_blocked")
        return element

    def _observable_elements(self) -> tuple[BrowserFixtureElement, ...]:
        return tuple(
            element
            for element in self._elements().values()
            if element.visible and element.enabled and not element.secret and element.ref in {"button:enable_sentinel", "input:status"}
        )

    def _elements(self) -> dict[str, BrowserFixtureElement]:
        return {
            "button:enable_sentinel": BrowserFixtureElement("button:enable_sentinel", "button", "Enable Sentinel"),
            "input:status": BrowserFixtureElement("input:status", "textbox", "status"),
            "button:hidden": BrowserFixtureElement("button:hidden", "button", "Hidden", visible=False),
            "button:disabled": BrowserFixtureElement("button:disabled", "button", "Disabled", enabled=False),
            "input:secret": BrowserFixtureElement("input:secret", "textbox", "secret", secret=True),
        }

    def _summary_hash(self) -> str:
        return stable_hash(
            {
                "fixture_ref": FIXTURE_REF,
                "title": self.state.title,
                "state_hash": self.state.state_hash(),
                "observable_refs": [element.ref for element in self._observable_elements()],
            }
        )

    def _write_artifact(self, collection: str, artifact_id: str, payload: dict[str, object]) -> None:
        path = self.kernel.store.mission_dir(self.mission_id, create=True) / "browser_control" / collection / f"{artifact_id}.json"
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


def _param_ref(envelope: ActionEnvelope) -> str:
    ref = str(envelope.params.get("ref") or envelope.target_ref or "")
    if not ref:
        raise BrowserControlRuntimeError("browser_element_ref_required")
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
        raise BrowserControlRuntimeError("browser_sensitive_text_blocked")


__all__ = [
    "BrowserControlRuntime",
    "BrowserControlRuntimeError",
    "BrowserFixtureState",
    "FIXTURE_REF",
    "SESSION_REF",
]
