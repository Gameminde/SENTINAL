from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, model_validator

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionManagerL5Live
from sentinel.agent.organs.safety_scanner import scan_forbidden_payload_categorized
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.models import SentinelModel, new_id


class BrowserFileQuarantineActionKind(StrEnum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class BrowserFileQuarantineStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrowserFileQuarantineFinalGateDecision(StrEnum):
    CERTIFIED_SUCCESS = "certified_success"
    CERTIFIED_BLOCKED = "certified_blocked"
    REJECTED_UNSAFE_RECEIPT = "rejected_unsafe_receipt"


class BrowserFileQuarantineContract(SentinelModel):
    mission_id: str
    allowed_domains: list[str]
    approved_upload_root: str
    approved_download_quarantine_root: str
    allow_upload: bool = False
    allow_download: bool = False
    max_file_bytes: int = Field(default=10_000_000, ge=1)
    receipt_required: bool = True
    finalgate_required: bool = True
    forbid_executables: bool = True
    contract_version: str = "browser-download-upload-quarantine-l6-v1"
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_contract(self) -> BrowserFileQuarantineContract:
        if not self.allowed_domains:
            raise ValueError("Browser file quarantine contract requires allowed domains.")
        if not self.receipt_required or not self.finalgate_required:
            raise ValueError("Browser file quarantine contract requires receipts and FinalGate posture.")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("Browser file quarantine contract cannot grant authority or execute by itself.")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("Browser file quarantine contract cannot grant future authority.")
        self.allowed_domains = sorted({domain.strip().lower() for domain in self.allowed_domains if domain.strip()})
        return self


class BrowserFileQuarantineRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("bfilereq"))
    mission: MissionAuthorityEnvelope
    url: str
    session_id: str
    contract: BrowserFileQuarantineContract
    action_kind: BrowserFileQuarantineActionKind
    target_role: str
    target_name: str | None = None
    local_upload_path: str | None = None
    operator_note: str | None = None
    timeout_ms: int = Field(default=15_000, ge=1, le=120_000)
    capture_screenshot: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_request(self) -> BrowserFileQuarantineRequest:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("Browser file quarantine request cannot grant authority or execute by itself.")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("Browser file quarantine request cannot grant future authority.")
        return self


class BrowserFileQuarantineSafetyValidationResult(SentinelModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    execution_effect: str = "none"
    data_not_instruction: bool = True


class BrowserFileQuarantineReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("bfilerec"))
    mission_id: str
    request_id: str
    session_id: str | None = None
    backend_kind: str | None = None
    action_level: DelegatedActionLevel = DelegatedActionLevel.L6
    action_kind: BrowserFileQuarantineActionKind
    status: BrowserFileQuarantineStatus
    url_hash: str
    before_snapshot_hash: str | None = None
    after_snapshot_hash: str | None = None
    screenshot_artifact_id: str | None = None
    after_screenshot_artifact_id: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    file_hash: str | None = None
    file_size_bytes: int | None = None
    quarantine_path_metadata: dict[str, str] = Field(default_factory=dict)
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


class BrowserFileQuarantineFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("bfilefg"))
    mission_id: str
    receipt_id: str
    decision: BrowserFileQuarantineFinalGateDecision
    certified: bool
    reasons: list[str] = Field(default_factory=list)
    receipt_hash: str
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    data_not_instruction: bool = True


class BrowserFileQuarantineResult(SentinelModel):
    accepted: bool
    status: BrowserFileQuarantineStatus
    reason: str
    mission_id: str
    session_id: str | None = None
    action_level: DelegatedActionLevel = DelegatedActionLevel.L6
    receipt: BrowserFileQuarantineReceipt
    finalgate_certificate: BrowserFileQuarantineFinalGateCertificate | None = None
    safety_validation: BrowserFileQuarantineSafetyValidationResult
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    data_not_instruction: bool = True


class BrowserFileQuarantineFinalGate:
    def certify(self, receipt: BrowserFileQuarantineReceipt) -> BrowserFileQuarantineFinalGateCertificate:
        reasons: list[str] = []
        if receipt.status == BrowserFileQuarantineStatus.COMPLETED and not receipt.file_hash:
            reasons.append("missing_file_hash")
        if receipt.status == BrowserFileQuarantineStatus.COMPLETED and not (receipt.before_snapshot_hash and receipt.after_snapshot_hash):
            reasons.append("missing_before_after_hash")
        if receipt.authority_effect != "none" or receipt.can_grant_authority or receipt.can_approve_future_execution:
            reasons.append("receipt_can_grant_or_expand_authority")
        scan = scan_forbidden_payload_categorized(receipt.model_dump(mode="python", exclude={"mission_id", "request_id", "receipt_id", "session_id", "blocked_reason", "safe_summary"}))
        if scan["all"]:
            reasons.append("unsafe_receipt_payload")
        if reasons:
            decision = BrowserFileQuarantineFinalGateDecision.REJECTED_UNSAFE_RECEIPT
            certified = False
        elif receipt.status == BrowserFileQuarantineStatus.BLOCKED:
            decision = BrowserFileQuarantineFinalGateDecision.CERTIFIED_BLOCKED
            certified = True
        else:
            decision = BrowserFileQuarantineFinalGateDecision.CERTIFIED_SUCCESS
            certified = True
        return BrowserFileQuarantineFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=certified,
            reasons=reasons,
            receipt_hash=stable_hash(receipt.model_dump(mode="json")),
        )


class BrowserFileQuarantineOrganL6:
    organ_id = "browser_download_upload_quarantine_l6_v1"

    def __init__(self) -> None:
        self._finalgate = BrowserFileQuarantineFinalGate()

    def execute(self, request: BrowserFileQuarantineRequest | dict[str, Any], *, session_manager: BrowserSessionManagerL5Live | None = None) -> BrowserFileQuarantineResult:
        req = _coerce_request(request)
        safety = self.validate_request(req)
        if session_manager is None:
            safety.reasons.append("browser_session_manager_required")
            safety.valid = False
        if not safety.valid:
            return self._blocked(req, safety, safety.reasons[0])
        try:
            payload = self._execute_quarantined(req, session_manager=session_manager)
        except Exception as exc:
            return self._blocked(req, BrowserFileQuarantineSafetyValidationResult(valid=False, reasons=[f"browser_file_quarantine_failed:{type(exc).__name__}"]), f"browser_file_quarantine_failed:{type(exc).__name__}")
        receipt = BrowserFileQuarantineReceipt(
            mission_id=req.mission.id,
            request_id=req.request_id,
            session_id=req.session_id,
            backend_kind=str(payload["backend_kind"]),
            action_kind=req.action_kind,
            status=BrowserFileQuarantineStatus.COMPLETED,
            url_hash=str(payload["url_hash"]),
            before_snapshot_hash=str(payload["before_snapshot_hash"]),
            after_snapshot_hash=str(payload["after_snapshot_hash"]),
            screenshot_artifact_id=payload["screenshot_artifact_id"],
            after_screenshot_artifact_id=payload["after_screenshot_artifact_id"],
            artifact_paths=list(payload["artifact_paths"]),
            file_hash=str(payload["file_hash"]),
            file_size_bytes=int(payload["file_size_bytes"]),
            quarantine_path_metadata=dict(payload.get("quarantine_path_metadata") or {}),
            finalgate_verified=True,
            safe_summary=f"Browser file {req.action_kind.value} completed through quarantine controls.",
            execution_effect=f"browser_file_{req.action_kind.value}_quarantined",
        )
        certificate = self._certify_receipt(receipt)
        return BrowserFileQuarantineResult(
            accepted=certificate.certified,
            status=BrowserFileQuarantineStatus.COMPLETED if certificate.certified else BrowserFileQuarantineStatus.FAILED,
            reason=f"browser_file_{req.action_kind.value}_quarantined" if certificate.certified else "browser_file_quarantine_finalgate_rejected",
            mission_id=req.mission.id,
            session_id=req.session_id,
            receipt=receipt,
            finalgate_certificate=certificate,
            safety_validation=safety,
            execution_effect=receipt.execution_effect if certificate.certified else "none",
        )

    def validate_request(self, request: BrowserFileQuarantineRequest | dict[str, Any]) -> BrowserFileQuarantineSafetyValidationResult:
        req = _coerce_request(request)
        reasons: list[str] = []
        rejected: list[str] = []
        scan = scan_forbidden_payload_categorized({"target_role": req.target_role, "target_name": req.target_name, "operator_note": req.operator_note})
        if scan["all"]:
            reasons.append("unsafe_browser_file_quarantine_payload")
            rejected.extend(scan["all"])
        if req.contract.mission_id != req.mission.id:
            reasons.append("contract_mission_mismatch")
        host = (urlparse(req.url).hostname or "").lower()
        if host not in req.contract.allowed_domains or host not in [domain.lower() for domain in req.mission.allowed_domains]:
            reasons.append("browser_file_domain_not_authorized")
        required_action = f"browser_file_{req.action_kind.value}_quarantine"
        if "browser_download_upload_quarantine_l6" not in req.mission.allowed_tools:
            reasons.append("mission_tool_missing_browser_download_upload_quarantine_l6")
        if required_action not in req.mission.allowed_actions:
            reasons.append(f"mission_authority_missing_{required_action}")
        if req.action_kind is BrowserFileQuarantineActionKind.UPLOAD:
            if not req.contract.allow_upload:
                reasons.append("contract_does_not_allow_upload")
            if not req.local_upload_path:
                reasons.append("upload_path_required")
            else:
                reasons.extend(_validate_upload_path(req))
        if req.action_kind is BrowserFileQuarantineActionKind.DOWNLOAD and not req.contract.allow_download:
            reasons.append("contract_does_not_allow_download")
        return BrowserFileQuarantineSafetyValidationResult(valid=not reasons, reasons=list(dict.fromkeys(reasons)), rejected_paths=sorted(set(rejected)))

    def _execute_quarantined(self, req: BrowserFileQuarantineRequest, *, session_manager: BrowserSessionManagerL5Live) -> dict[str, Any]:
        if req.action_kind is BrowserFileQuarantineActionKind.UPLOAD:
            assert req.local_upload_path is not None
            return session_manager.upload_file_quarantine_special_authority(
                mission_id=req.mission.id,
                session_id=req.session_id,
                target_role=req.target_role,
                target_name=req.target_name,
                local_upload_path=req.local_upload_path,
                timeout_ms=req.timeout_ms,
                capture_screenshot=req.capture_screenshot,
            )
        return session_manager.download_file_quarantine_special_authority(
            mission_id=req.mission.id,
            session_id=req.session_id,
            target_role=req.target_role,
            target_name=req.target_name,
            quarantine_root=req.contract.approved_download_quarantine_root,
            max_file_bytes=req.contract.max_file_bytes,
            forbid_executables=req.contract.forbid_executables,
            timeout_ms=req.timeout_ms,
            capture_screenshot=req.capture_screenshot,
        )

    def produce_receipt(self, request: BrowserFileQuarantineRequest | dict[str, Any], *, blocked_reason: str) -> BrowserFileQuarantineReceipt:
        req = _coerce_request(request)
        return BrowserFileQuarantineReceipt(
            mission_id=req.mission.id,
            request_id=req.request_id,
            session_id=req.session_id,
            action_kind=req.action_kind,
            status=BrowserFileQuarantineStatus.BLOCKED,
            url_hash=stable_hash(req.url),
            blocked_reason=blocked_reason,
            finalgate_verified=True,
            safe_summary=f"Browser file quarantine blocked: {blocked_reason}.",
        )

    def _blocked(self, req: BrowserFileQuarantineRequest, safety: BrowserFileQuarantineSafetyValidationResult, reason: str) -> BrowserFileQuarantineResult:
        receipt = self.produce_receipt(req, blocked_reason=reason)
        certificate = self._certify_receipt(receipt)
        return BrowserFileQuarantineResult(
            accepted=False,
            status=BrowserFileQuarantineStatus.BLOCKED,
            reason=reason,
            mission_id=req.mission.id,
            session_id=req.session_id,
            receipt=receipt,
            finalgate_certificate=certificate,
            safety_validation=safety,
        )

    def _certify_receipt(self, receipt: BrowserFileQuarantineReceipt) -> BrowserFileQuarantineFinalGateCertificate:
        certificate = self._finalgate.certify(receipt)
        receipt.finalgate_verified = certificate.certified
        receipt.finalgate_certificate_id = certificate.certificate_id
        return certificate


def _validate_upload_path(req: BrowserFileQuarantineRequest) -> list[str]:
    path = Path(str(req.local_upload_path)).resolve()
    root = Path(req.contract.approved_upload_root).resolve()
    reasons: list[str] = []
    try:
        path.relative_to(root)
    except ValueError:
        reasons.append("upload_path_outside_approved_root")
        return reasons
    if not path.is_file():
        reasons.append("upload_path_not_file")
        return reasons
    if path.stat().st_size > req.contract.max_file_bytes:
        reasons.append("upload_file_too_large")
    if req.contract.forbid_executables and path.suffix.lower() in {".exe", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs"}:
        reasons.append("upload_executable_extension_blocked")
    return reasons


def _coerce_request(request: BrowserFileQuarantineRequest | dict[str, Any]) -> BrowserFileQuarantineRequest:
    return request if isinstance(request, BrowserFileQuarantineRequest) else BrowserFileQuarantineRequest.model_validate(request)
