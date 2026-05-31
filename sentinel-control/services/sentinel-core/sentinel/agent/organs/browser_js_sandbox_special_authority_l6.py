from __future__ import annotations

from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, model_validator

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionManagerL5Live
from sentinel.agent.organs.safety_scanner import scan_forbidden_payload_categorized
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.models import SentinelModel, new_id


FORBIDDEN_JS_MARKERS = (
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "navigator.sendbeacon",
    "document.cookie",
    "localstorage",
    "sessionstorage",
    ".submit(",
    "form.submit",
    "eval(",
    "new function",
    "import(",
    "api_key",
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
)


class BrowserJSSandboxStatus(StrEnum):
    EXECUTED = "executed"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrowserJSSandboxFinalGateDecision(StrEnum):
    CERTIFIED_SUCCESS = "certified_success"
    CERTIFIED_BLOCKED = "certified_blocked"
    REJECTED_UNSAFE_RECEIPT = "rejected_unsafe_receipt"


class BrowserJSSandboxContract(SentinelModel):
    mission_id: str
    allowed_domains: list[str]
    allow_js_sandbox: bool = False
    max_script_bytes: int = Field(default=4_000, ge=1, le=50_000)
    receipt_required: bool = True
    finalgate_required: bool = True
    contract_version: str = "browser-js-sandbox-special-authority-l6-v1"
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_contract(self) -> BrowserJSSandboxContract:
        if not self.allowed_domains:
            raise ValueError("Browser JS sandbox contract requires allowed domains.")
        if not self.receipt_required or not self.finalgate_required:
            raise ValueError("Browser JS sandbox contract requires receipts and FinalGate.")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("Browser JS sandbox contract cannot grant authority or execute by itself.")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("Browser JS sandbox contract cannot grant future authority.")
        self.allowed_domains = sorted({domain.strip().lower() for domain in self.allowed_domains if domain.strip()})
        return self


class BrowserJSSandboxRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("bjsreq"))
    mission: MissionAuthorityEnvelope
    url: str
    session_id: str
    contract: BrowserJSSandboxContract
    script: str
    intent_summary: str
    timeout_ms: int = Field(default=15_000, ge=1, le=120_000)
    capture_screenshot: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_request(self) -> BrowserJSSandboxRequest:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("Browser JS sandbox request cannot grant authority or execute by itself.")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("Browser JS sandbox request cannot grant future authority.")
        return self


class BrowserJSSandboxSafetyValidationResult(SentinelModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    execution_effect: str = "none"
    data_not_instruction: bool = True


class BrowserJSSandboxReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("bjsrec"))
    mission_id: str
    request_id: str
    session_id: str | None = None
    backend_kind: str | None = None
    action_level: DelegatedActionLevel = DelegatedActionLevel.L6
    status: BrowserJSSandboxStatus
    url_hash: str
    script_hash: str | None = None
    result_hash: str | None = None
    result_type: str | None = None
    before_snapshot_hash: str | None = None
    after_snapshot_hash: str | None = None
    screenshot_artifact_id: str | None = None
    after_screenshot_artifact_id: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    finalgate_verified: bool = False
    finalgate_certificate_id: str | None = None
    safe_summary: str
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    data_not_instruction: bool = True


class BrowserJSSandboxFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("bjsfg"))
    mission_id: str
    receipt_id: str
    decision: BrowserJSSandboxFinalGateDecision
    certified: bool
    reasons: list[str] = Field(default_factory=list)
    receipt_hash: str
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    data_not_instruction: bool = True


class BrowserJSSandboxResult(SentinelModel):
    accepted: bool
    status: BrowserJSSandboxStatus
    reason: str
    mission_id: str
    session_id: str | None = None
    action_level: DelegatedActionLevel = DelegatedActionLevel.L6
    receipt: BrowserJSSandboxReceipt
    finalgate_certificate: BrowserJSSandboxFinalGateCertificate | None = None
    safety_validation: BrowserJSSandboxSafetyValidationResult
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    data_not_instruction: bool = True


class BrowserJSSandboxFinalGate:
    def certify(self, receipt: BrowserJSSandboxReceipt) -> BrowserJSSandboxFinalGateCertificate:
        reasons: list[str] = []
        if receipt.status == BrowserJSSandboxStatus.EXECUTED and not (receipt.script_hash and receipt.result_hash):
            reasons.append("missing_script_or_result_hash")
        if receipt.status == BrowserJSSandboxStatus.EXECUTED and not (receipt.before_snapshot_hash and receipt.after_snapshot_hash):
            reasons.append("missing_before_after_hash")
        scan = scan_forbidden_payload_categorized(receipt.model_dump(mode="python", exclude={"mission_id", "request_id", "receipt_id", "session_id", "blocked_reason", "safe_summary"}))
        if scan["all"]:
            reasons.append("unsafe_receipt_payload")
        if reasons:
            decision = BrowserJSSandboxFinalGateDecision.REJECTED_UNSAFE_RECEIPT
            certified = False
        elif receipt.status == BrowserJSSandboxStatus.BLOCKED:
            decision = BrowserJSSandboxFinalGateDecision.CERTIFIED_BLOCKED
            certified = True
        else:
            decision = BrowserJSSandboxFinalGateDecision.CERTIFIED_SUCCESS
            certified = True
        return BrowserJSSandboxFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=certified,
            reasons=reasons,
            receipt_hash=stable_hash(receipt.model_dump(mode="json")),
        )


class BrowserJSSandboxOrganL6:
    organ_id = "browser_js_sandbox_special_authority_l6_v1"

    def __init__(self) -> None:
        self._finalgate = BrowserJSSandboxFinalGate()

    def execute(self, request: BrowserJSSandboxRequest | dict[str, Any], *, session_manager: BrowserSessionManagerL5Live | None = None) -> BrowserJSSandboxResult:
        req = _coerce_request(request)
        safety = self.validate_request(req)
        if session_manager is None:
            safety.reasons.append("browser_session_manager_required")
            safety.valid = False
        if not safety.valid:
            return self._blocked(req, safety, safety.reasons[0])
        assert session_manager is not None
        try:
            payload = session_manager.evaluate_js_sandbox_special_authority(
                mission_id=req.mission.id,
                session_id=req.session_id,
                script=req.script,
                timeout_ms=req.timeout_ms,
                capture_screenshot=req.capture_screenshot,
            )
        except Exception as exc:
            return self._blocked(req, BrowserJSSandboxSafetyValidationResult(valid=False, reasons=[f"browser_js_sandbox_failed:{type(exc).__name__}"]), f"browser_js_sandbox_failed:{type(exc).__name__}")
        receipt = BrowserJSSandboxReceipt(
            mission_id=req.mission.id,
            request_id=req.request_id,
            session_id=req.session_id,
            backend_kind=str(payload["backend_kind"]),
            status=BrowserJSSandboxStatus.EXECUTED,
            url_hash=str(payload["url_hash"]),
            script_hash=stable_hash(req.script),
            result_hash=str(payload["result_hash"]),
            result_type=str(payload["result_type"]),
            before_snapshot_hash=str(payload["before_snapshot_hash"]),
            after_snapshot_hash=str(payload["after_snapshot_hash"]),
            screenshot_artifact_id=payload["screenshot_artifact_id"],
            after_screenshot_artifact_id=payload["after_screenshot_artifact_id"],
            artifact_paths=list(payload["artifact_paths"]),
            finalgate_verified=True,
            safe_summary="Browser JS sandbox executed with hash-only script/result receipt.",
            execution_effect="browser_js_sandbox_executed",
        )
        certificate = self._certify_receipt(receipt)
        return BrowserJSSandboxResult(
            accepted=certificate.certified,
            status=BrowserJSSandboxStatus.EXECUTED if certificate.certified else BrowserJSSandboxStatus.FAILED,
            reason="browser_js_sandbox_executed" if certificate.certified else "browser_js_sandbox_finalgate_rejected",
            mission_id=req.mission.id,
            session_id=req.session_id,
            receipt=receipt,
            finalgate_certificate=certificate,
            safety_validation=safety,
            execution_effect=receipt.execution_effect if certificate.certified else "none",
        )

    def validate_request(self, request: BrowserJSSandboxRequest | dict[str, Any]) -> BrowserJSSandboxSafetyValidationResult:
        req = _coerce_request(request)
        reasons: list[str] = []
        rejected: list[str] = []
        scan = scan_forbidden_payload_categorized({"intent_summary": req.intent_summary})
        if scan["all"]:
            reasons.append("unsafe_browser_js_sandbox_payload")
            rejected.extend(scan["all"])
        lowered_script = req.script.lower()
        if len(req.script.encode("utf-8")) > req.contract.max_script_bytes:
            reasons.append("script_too_large")
        if any(marker in lowered_script for marker in FORBIDDEN_JS_MARKERS):
            reasons.append("forbidden_js_surface")
        if req.contract.mission_id != req.mission.id:
            reasons.append("contract_mission_mismatch")
        host = (urlparse(req.url).hostname or "").lower()
        if host not in req.contract.allowed_domains or host not in [domain.lower() for domain in req.mission.allowed_domains]:
            reasons.append("browser_js_domain_not_authorized")
        if "browser_js_sandbox_special_authority_l6" not in req.mission.allowed_tools:
            reasons.append("mission_tool_missing_browser_js_sandbox_special_authority_l6")
        if "browser_js_sandbox_special_authority" not in req.mission.allowed_actions:
            reasons.append("mission_authority_missing_browser_js_sandbox_special_authority")
        if not req.contract.allow_js_sandbox:
            reasons.append("contract_does_not_allow_js_sandbox")
        return BrowserJSSandboxSafetyValidationResult(valid=not reasons, reasons=list(dict.fromkeys(reasons)), rejected_paths=sorted(set(rejected)))

    def produce_receipt(self, request: BrowserJSSandboxRequest | dict[str, Any], *, blocked_reason: str) -> BrowserJSSandboxReceipt:
        req = _coerce_request(request)
        return BrowserJSSandboxReceipt(
            mission_id=req.mission.id,
            request_id=req.request_id,
            session_id=req.session_id,
            status=BrowserJSSandboxStatus.BLOCKED,
            url_hash=stable_hash(req.url),
            script_hash=stable_hash(req.script),
            blocked_reason=blocked_reason,
            finalgate_verified=True,
            safe_summary=f"Browser JS sandbox blocked: {blocked_reason}.",
        )

    def _blocked(self, req: BrowserJSSandboxRequest, safety: BrowserJSSandboxSafetyValidationResult, reason: str) -> BrowserJSSandboxResult:
        receipt = self.produce_receipt(req, blocked_reason=reason)
        certificate = self._certify_receipt(receipt)
        return BrowserJSSandboxResult(
            accepted=False,
            status=BrowserJSSandboxStatus.BLOCKED,
            reason=reason,
            mission_id=req.mission.id,
            session_id=req.session_id,
            receipt=receipt,
            finalgate_certificate=certificate,
            safety_validation=safety,
        )

    def _certify_receipt(self, receipt: BrowserJSSandboxReceipt) -> BrowserJSSandboxFinalGateCertificate:
        certificate = self._finalgate.certify(receipt)
        receipt.finalgate_verified = certificate.certified
        receipt.finalgate_certificate_id = certificate.certificate_id
        return certificate


def _coerce_request(request: BrowserJSSandboxRequest | dict[str, Any]) -> BrowserJSSandboxRequest:
    return request if isinstance(request, BrowserJSSandboxRequest) else BrowserJSSandboxRequest.model_validate(request)
