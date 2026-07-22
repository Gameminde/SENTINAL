from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import utc_now
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class RealBrowserElementSnapshot(SentinelModel):
    ref: str
    role: str
    name: str
    visible: bool
    enabled: bool
    text_preview: str = ""
    value_preview: str = ""

    def safe_model_dump(self) -> dict[str, object]:
        return {
            "ref": _safe_browser_ref(self.ref),
            "role": redact_operator_text(self.role),
            "name": redact_operator_text(self.name),
            "visible": self.visible,
            "enabled": self.enabled,
            "text_preview": _safe_preview(self.text_preview),
            "value_preview": _safe_preview(self.value_preview),
        }


class RealBrowserOpenReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("real_browser_open"))
    mission_id: str
    browser_session_ref: str
    bounded_url_ref: str
    safe_url_origin_hash: str
    page_title_hash: str
    browser_state_hash: str
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "RealBrowserOpenReceipt":
        _assert_data_only("real_browser_open_receipt", self)
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False)) == self.receipt_hash

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "browser_session_ref": _safe_browser_ref(self.browser_session_ref),
            "bounded_url_ref": _safe_browser_ref(self.bounded_url_ref),
            "safe_url_origin_hash": self.safe_url_origin_hash,
            "page_title_hash": self.page_title_hash,
            "browser_state_hash": self.browser_state_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class RealBrowserObservationReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("real_browser_observation"))
    mission_id: str
    browser_session_ref: str
    browser_session_handle_ref: str = ""
    browser_session_handle_hash: str = ""
    child_workspace_handle_hash: str = ""
    mission_workspace_ref: str = ""
    mission_workspace_hash: str = ""
    root_browser_lease_id_hash: str = ""
    browser_engine_identity_hash: str = ""
    backend_context_identity_hash: str = ""
    page_identity_hash: str = ""
    bounded_url_ref: str
    safe_url_origin_hash: str
    selected_backend_id: str = ""
    actual_backend_id: str = ""
    session_backend_kind: str = ""
    backend_mismatch: bool = False
    simple_skill: str = ""
    internal_action_id: str = ""
    product_dispatch_owner: str = ""
    stable_element_ref: str = "page:observation"
    action_kind: str = "real_browser.observe"
    operation: str = "real_browser.observe"
    status: str = "observation_success"
    failure_code: str = ""
    recovery_classification: str = "none"
    replay_behavior: str = "no_reexecute_on_replay"
    page_title: str
    page_state_hash: str
    elements: tuple[RealBrowserElementSnapshot, ...] = Field(default_factory=tuple)
    before_state_hash: str = ""
    after_state_hash: str = ""
    browser_environment_state_hash: str = ""
    typed_observation: dict[str, object] = Field(default_factory=dict)
    evidence_delta: dict[str, object] = Field(default_factory=dict)
    exception_class: str = ""
    exception_hash: str = ""
    bounded_observation_summary_hash: str
    result_hash: str = ""
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "RealBrowserObservationReceipt":
        _assert_data_only("real_browser_observation_receipt", self)
        if not self.before_state_hash:
            self.before_state_hash = self.page_state_hash
        if not self.after_state_hash:
            self.after_state_hash = self.page_state_hash
        if not self.browser_environment_state_hash:
            self.browser_environment_state_hash = self.after_state_hash
        if not self.result_hash:
            self.result_hash = stable_hash(self.safe_model_dump(include_hash=False, include_result_hash=False))
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=False, include_result_hash=True))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False, include_result_hash=True)) == self.receipt_hash

    def safe_model_dump(self, *, include_hash: bool = True, include_result_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "browser_session_ref": _safe_browser_ref(self.browser_session_ref),
            "browser_session_handle_ref": _safe_browser_ref(self.browser_session_handle_ref),
            "browser_session_handle_hash": self.browser_session_handle_hash,
            "child_workspace_handle_hash": self.child_workspace_handle_hash,
            "mission_workspace_ref": _safe_browser_ref(self.mission_workspace_ref),
            "mission_workspace_hash": self.mission_workspace_hash,
            "root_browser_lease_id_hash": self.root_browser_lease_id_hash,
            "browser_engine_identity_hash": self.browser_engine_identity_hash,
            "backend_context_identity_hash": self.backend_context_identity_hash,
            "page_identity_hash": self.page_identity_hash,
            "bounded_url_ref": _safe_browser_ref(self.bounded_url_ref),
            "safe_url_origin_hash": self.safe_url_origin_hash,
            "selected_backend_id": redact_operator_text(self.selected_backend_id),
            "actual_backend_id": redact_operator_text(self.actual_backend_id),
            "session_backend_kind": redact_operator_text(self.session_backend_kind),
            "backend_mismatch": self.backend_mismatch,
            "simple_skill": redact_operator_text(self.simple_skill),
            "internal_action_id": redact_operator_text(self.internal_action_id),
            "product_dispatch_owner": redact_operator_text(self.product_dispatch_owner),
            "stable_element_ref": _safe_browser_ref(self.stable_element_ref),
            "action_kind": redact_operator_text(self.action_kind),
            "operation": redact_operator_text(self.operation),
            "status": redact_operator_text(self.status),
            "failure_code": redact_operator_text(self.failure_code),
            "recovery_classification": redact_operator_text(self.recovery_classification),
            "replay_behavior": redact_operator_text(self.replay_behavior),
            "page_title": redact_operator_text(self.page_title),
            "page_state_hash": self.page_state_hash,
            "elements": [element.safe_model_dump() for element in self.elements],
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "browser_environment_state_hash": self.browser_environment_state_hash,
            "typed_observation": dict(self.typed_observation),
            "evidence_delta": dict(self.evidence_delta),
            "exception_class": redact_operator_text(self.exception_class),
            "exception_hash": self.exception_hash,
            "bounded_observation_summary_hash": self.bounded_observation_summary_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_result_hash:
            payload["result_hash"] = self.result_hash
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class RealBrowserActionReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("real_browser_action"))
    mission_id: str
    browser_session_ref: str
    browser_session_handle_ref: str = ""
    browser_session_handle_hash: str = ""
    child_workspace_handle_hash: str = ""
    mission_workspace_ref: str = ""
    mission_workspace_hash: str = ""
    root_browser_lease_id_hash: str = ""
    browser_engine_identity_hash: str = ""
    backend_context_identity_hash: str = ""
    page_identity_hash: str = ""
    bounded_url_ref: str
    safe_url_origin_hash: str
    selected_backend_id: str = ""
    actual_backend_id: str = ""
    session_backend_kind: str = ""
    backend_mismatch: bool = False
    simple_skill: str = ""
    internal_action_id: str = ""
    product_dispatch_owner: str = ""
    stable_element_ref: str
    action_kind: str
    operation: str = ""
    status: str
    failure_code: str = ""
    recovery_classification: str = "none"
    replay_behavior: str = "no_reexecute_on_replay"
    before_state_hash: str
    after_state_hash: str
    browser_environment_state_hash: str = ""
    search_materiality: dict[str, object] = Field(default_factory=dict)
    typed_observation: dict[str, object] = Field(default_factory=dict)
    evidence_delta: dict[str, object] = Field(default_factory=dict)
    exception_class: str = ""
    exception_hash: str = ""
    bounded_observation_summary_hash: str
    result_hash: str = ""
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "RealBrowserActionReceipt":
        _assert_data_only("real_browser_action_receipt", self)
        if not self.result_hash:
            self.result_hash = stable_hash(self.safe_model_dump(include_hash=False, include_receipt_hash=False))
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=True, include_receipt_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=True, include_receipt_hash=False)) == self.receipt_hash

    def safe_model_dump(self, *, include_hash: bool = True, include_receipt_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "browser_session_ref": _safe_browser_ref(self.browser_session_ref),
            "browser_session_handle_ref": _safe_browser_ref(self.browser_session_handle_ref),
            "browser_session_handle_hash": self.browser_session_handle_hash,
            "child_workspace_handle_hash": self.child_workspace_handle_hash,
            "mission_workspace_ref": _safe_browser_ref(self.mission_workspace_ref),
            "mission_workspace_hash": self.mission_workspace_hash,
            "root_browser_lease_id_hash": self.root_browser_lease_id_hash,
            "browser_engine_identity_hash": self.browser_engine_identity_hash,
            "backend_context_identity_hash": self.backend_context_identity_hash,
            "page_identity_hash": self.page_identity_hash,
            "bounded_url_ref": _safe_browser_ref(self.bounded_url_ref),
            "safe_url_origin_hash": self.safe_url_origin_hash,
            "selected_backend_id": redact_operator_text(self.selected_backend_id),
            "actual_backend_id": redact_operator_text(self.actual_backend_id),
            "session_backend_kind": redact_operator_text(self.session_backend_kind),
            "backend_mismatch": self.backend_mismatch,
            "simple_skill": redact_operator_text(self.simple_skill),
            "internal_action_id": redact_operator_text(self.internal_action_id),
            "product_dispatch_owner": redact_operator_text(self.product_dispatch_owner),
            "stable_element_ref": _safe_browser_ref(self.stable_element_ref),
            "action_kind": redact_operator_text(self.action_kind),
            "operation": redact_operator_text(self.operation or self.action_kind),
            "status": redact_operator_text(self.status),
            "failure_code": redact_operator_text(self.failure_code),
            "recovery_classification": redact_operator_text(self.recovery_classification),
            "replay_behavior": redact_operator_text(self.replay_behavior),
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "browser_environment_state_hash": self.browser_environment_state_hash,
            "search_materiality": dict(self.search_materiality),
            "typed_observation": dict(self.typed_observation),
            "evidence_delta": dict(self.evidence_delta),
            "exception_class": redact_operator_text(self.exception_class),
            "exception_hash": self.exception_hash,
            "bounded_observation_summary_hash": self.bounded_observation_summary_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        if include_receipt_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class RealBrowserAssertionReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("real_browser_assertion"))
    mission_id: str
    browser_session_ref: str
    bounded_url_ref: str
    safe_url_origin_hash: str
    assertion_kind: str
    status: str
    expected_text_hash: str
    page_state_hash: str
    bounded_observation_summary_hash: str
    result_hash: str = ""
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "RealBrowserAssertionReceipt":
        _assert_data_only("real_browser_assertion_receipt", self)
        if not self.result_hash:
            self.result_hash = stable_hash(self.safe_model_dump(include_hash=False, include_receipt_hash=False))
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=True, include_receipt_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=True, include_receipt_hash=False)) == self.receipt_hash

    def safe_model_dump(self, *, include_hash: bool = True, include_receipt_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "browser_session_ref": _safe_browser_ref(self.browser_session_ref),
            "bounded_url_ref": _safe_browser_ref(self.bounded_url_ref),
            "safe_url_origin_hash": self.safe_url_origin_hash,
            "assertion_kind": redact_operator_text(self.assertion_kind),
            "status": redact_operator_text(self.status),
            "expected_text_hash": self.expected_text_hash,
            "page_state_hash": self.page_state_hash,
            "bounded_observation_summary_hash": self.bounded_observation_summary_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        if include_receipt_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class RealBrowserFinalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("real_browser_finalgate"))
    mission_id: str
    status: str
    accepted: bool
    reason: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_data_only(self) -> "RealBrowserFinalCertificate":
        _assert_data_only("real_browser_final_certificate", self)
        if not self.certificate_hash:
            self.certificate_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False)) == self.certificate_hash

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "certificate_id": self.certificate_id,
            "mission_id": self.mission_id,
            "status": redact_operator_text(self.status),
            "accepted": self.accepted,
            "reason": redact_operator_text(self.reason),
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


def _assert_data_only(context: str, payload: object) -> None:
    assert_data_not_authority(
        context=context,
        authority_effect=getattr(payload, "authority_effect"),
        data_not_authority=getattr(payload, "data_not_authority"),
        can_grant_authority=getattr(payload, "can_grant_authority"),
        can_execute=getattr(payload, "can_execute"),
    )


def _safe_browser_ref(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "empty_ref"
    if text.startswith(("mission_workspace:", "real_browser_session:")):
        return redact_operator_text(text[:240])
    lowered = text.lower()
    if any(marker in lowered for marker in ("cookie", "session", "password", "secret", "authorization", "bearer")):
        return f"real_browser_ref_hash:{text_hash(text)}"
    return redact_operator_text(text[:240])


def _safe_preview(value: str) -> str:
    text = str(value or "")[:120]
    lowered = text.lower()
    if any(marker in lowered for marker in ("cookie", "session", "password", "secret", "authorization", "bearer", "sk-")):
        return f"preview_hash:{text_hash(text)}"
    return redact_operator_text(text)


__all__ = [
    "RealBrowserActionReceipt",
    "RealBrowserAssertionReceipt",
    "RealBrowserElementSnapshot",
    "RealBrowserFinalCertificate",
    "RealBrowserObservationReceipt",
    "RealBrowserOpenReceipt",
]
