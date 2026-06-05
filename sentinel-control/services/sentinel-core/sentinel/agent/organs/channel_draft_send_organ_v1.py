from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from sentinel.power.runtime import PowerStepResult, PowerStepStatus
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import SHARED_SECRET_LIKE_PATTERN, scan_secret_like_text


class ChannelDraftSendStatus(StrEnum):
    DRAFT_CREATED = "draft_created"
    SENT = "sent"
    BLOCKED = "blocked"
    FAILED = "failed"


class ChannelDraftSendRequest(SentinelModel):
    mission_id: str
    mode: str = "draft"
    channel: str
    subject: str | None = None
    body: str
    recipients: list[str] = Field(default_factory=list)
    recipient_provenance: dict[str, str] = Field(default_factory=dict)
    send_authority_ref: str | None = None
    evidence_refs: list[str]
    objective_tags: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @field_validator("mode")
    @classmethod
    def _mode_lower(cls, value: str) -> str:
        mode = value.strip().lower()
        if mode not in {"draft", "send"}:
            raise ValueError("channel mode must be draft or send")
        return mode

    @field_validator("channel")
    @classmethod
    def _channel_lower(cls, value: str) -> str:
        channel = value.strip().lower()
        if not channel:
            raise ValueError("channel is required")
        return channel

    @model_validator(mode="after")
    def _request_is_safe(self) -> ChannelDraftSendRequest:
        if self.authority_effect != "none":
            raise ValueError("channel request cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("channel request must remain data-not-instruction")
        if not self.evidence_refs:
            raise ValueError("channel request requires evidence refs")
        for path, value in {
            "$.subject": self.subject or "",
            "$.body": self.body,
            "$.send_authority_ref": self.send_authority_ref or "",
        }.items():
            if scan_secret_like_text(value, path=path):
                raise ValueError("channel request contains secret-like text")
        return self


class ChannelDraftSendContract(SentinelModel):
    allowed_channels: list[str]
    send_authorized: bool = False
    max_recipients_per_window: int = Field(default=10, ge=0)
    require_recipient_provenance: bool = True
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @field_validator("allowed_channels")
    @classmethod
    def _allowed_channels_lower(cls, value: list[str]) -> list[str]:
        return [channel.strip().lower() for channel in value if channel.strip()]

    @model_validator(mode="after")
    def _contract_is_not_authority(self) -> ChannelDraftSendContract:
        if self.authority_effect != "none":
            raise ValueError("channel contract cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("channel contract must remain data-not-instruction")
        if not self.allowed_channels:
            raise ValueError("channel contract requires allowed_channels")
        return self


class ChannelSendTransportRequest(SentinelModel):
    channel: str
    subject: str | None = None
    body: str
    recipients: list[str]


class ChannelSendTransportReceipt(SentinelModel):
    delivery_ref: str


class ChannelRateLimitLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str], int] = {}

    def consume(self, *, mission_id: str, channel: str, count: int, limit: int) -> bool:
        key = (mission_id, channel)
        with self._lock:
            current = self._counts.get(key, 0)
            if current + count > limit:
                return False
            self._counts[key] = current + count
            return True


class ChannelDraftSendReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("channel_receipt"))
    mission_id: str
    mode: str
    channel: str
    draft_hash: str
    subject_hash: str | None = None
    body_sha256: str
    recipient_hashes: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    send_attempted: bool = False
    delivery_ref: str | None = None
    send_authority_ref: str | None = None
    compliance_reasons: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    execution_effect: str = "channel_send"  # receipt records effect; result remains non-authority.
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _receipt_is_safe(self) -> ChannelDraftSendReceipt:
        if self.authority_effect != "none":
            raise ValueError("channel receipt cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("channel receipt must remain data-not-instruction")
        return self


class ChannelDraftSendFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("channel_finalgate"))
    mission_id: str
    passed: bool
    status: ChannelDraftSendStatus
    receipt_ref: str | None = None
    failures: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_instruction: bool = True


class ChannelDraftSendResult(SentinelModel):
    mission_id: str
    status: ChannelDraftSendStatus
    receipt: ChannelDraftSendReceipt | None = None
    finalgate_certificate: ChannelDraftSendFinalGateCertificate | None = None
    blocked_reason: str | None = None
    safe_summary: str = ""
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _result_is_not_authority(self) -> ChannelDraftSendResult:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("channel result cannot grant authority or execute more")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("channel result cannot approve future execution")
        if self.data_not_instruction is not True:
            raise ValueError("channel result must remain data-not-instruction")
        return self


ChannelSender = Callable[[ChannelSendTransportRequest], ChannelSendTransportReceipt]


class ChannelDraftSendFinalGate:
    def certify(self, result: ChannelDraftSendResult) -> ChannelDraftSendFinalGateCertificate:
        failures: list[str] = []
        if result.status in {ChannelDraftSendStatus.DRAFT_CREATED, ChannelDraftSendStatus.SENT, ChannelDraftSendStatus.FAILED} and result.receipt is None:
            failures.append("missing_channel_receipt")
        if result.receipt is not None:
            if not result.receipt.draft_hash or not result.receipt.body_sha256:
                failures.append("missing_draft_or_body_hash")
            if result.receipt.send_attempted and not result.receipt.delivery_ref:
                failures.append("missing_delivery_ref")
        return ChannelDraftSendFinalGateCertificate(
            mission_id=result.mission_id,
            passed=not failures,
            status=result.status,
            receipt_ref=result.receipt.receipt_id if result.receipt else None,
            failures=failures,
        )


class ChannelDraftSendOrganV1:
    organ_kind = "channel_draft_send"

    def __init__(
        self,
        *,
        sender: ChannelSender | None = None,
        rate_ledger: ChannelRateLimitLedger | None = None,
    ) -> None:
        self._sender = sender
        self._rate_ledger = rate_ledger or ChannelRateLimitLedger()

    def execute(self, request: ChannelDraftSendRequest, *, contract: ChannelDraftSendContract) -> ChannelDraftSendResult:
        block_reason = self._block_reason(request, contract)
        if block_reason:
            return self._blocked(request, block_reason)

        if request.mode == "draft":
            receipt = _build_receipt(request, send_attempted=False)
            result = ChannelDraftSendResult(
                mission_id=request.mission_id,
                status=ChannelDraftSendStatus.DRAFT_CREATED,
                receipt=receipt,
                safe_summary="Channel draft created; no send attempted.",
            )
            return result.model_copy(update={"finalgate_certificate": ChannelDraftSendFinalGate().certify(result)})

        if self._sender is None:
            return self._blocked(request, "channel_sender_missing")
        if not self._rate_ledger.consume(
            mission_id=request.mission_id,
            channel=request.channel,
            count=len(request.recipients),
            limit=contract.max_recipients_per_window,
        ):
            return self._blocked(request, "rate_limit_exhausted")

        try:
            delivery = self._sender(
                ChannelSendTransportRequest(
                    channel=request.channel,
                    subject=request.subject,
                    body=request.body,
                    recipients=list(request.recipients),
                )
            )
            receipt = _build_receipt(
                request,
                send_attempted=True,
                delivery_ref=delivery.delivery_ref,
            )
            result = ChannelDraftSendResult(
                mission_id=request.mission_id,
                status=ChannelDraftSendStatus.SENT,
                receipt=receipt,
                safe_summary="Channel message sent through injected sender.",
            )
        except Exception as exc:  # pragma: no cover - connector specific.
            receipt = _build_receipt(request, send_attempted=True, delivery_ref=None)
            result = ChannelDraftSendResult(
                mission_id=request.mission_id,
                status=ChannelDraftSendStatus.FAILED,
                receipt=receipt,
                blocked_reason=exc.__class__.__name__,
                safe_summary="Channel sender failed with sanitized error class.",
            )
        return result.model_copy(update={"finalgate_certificate": ChannelDraftSendFinalGate().certify(result)})

    def _block_reason(self, request: ChannelDraftSendRequest, contract: ChannelDraftSendContract) -> str | None:
        if request.channel not in contract.allowed_channels:
            return "channel_not_allowed"
        compliance_reasons = _compliance_reasons(request)
        if compliance_reasons:
            return "compliance_blocked"
        if request.mode == "send":
            if not contract.send_authorized or not request.send_authority_ref:
                return "send_authority_missing"
            if contract.require_recipient_provenance:
                missing = [recipient for recipient in request.recipients if recipient not in request.recipient_provenance]
                if missing:
                    return "missing_recipient_provenance"
            if not request.recipients:
                return "missing_recipients"
        return None

    @staticmethod
    def _blocked(request: ChannelDraftSendRequest, reason: str) -> ChannelDraftSendResult:
        result = ChannelDraftSendResult(
            mission_id=request.mission_id,
            status=ChannelDraftSendStatus.BLOCKED,
            blocked_reason=reason,
            safe_summary=f"Channel action blocked: {reason}.",
        )
        return result.model_copy(update={"finalgate_certificate": ChannelDraftSendFinalGate().certify(result)})


def build_channel_power_executor(
    *,
    contract: ChannelDraftSendContract,
    sender: ChannelSender | None = None,
    rate_ledger: ChannelRateLimitLedger | None = None,
) -> Any:
    organ = ChannelDraftSendOrganV1(sender=sender, rate_ledger=rate_ledger)

    def _executor(step: Any, context: dict[str, Any]) -> PowerStepResult:
        payload = dict(getattr(step, "request", {}) or {})
        request = ChannelDraftSendRequest(
            mission_id=str(context.get("mission_id") or "mission_unknown"),
            mode=str(payload.get("mode") or "draft"),
            channel=str(payload.get("channel") or ""),
            subject=payload.get("subject"),
            body=str(payload.get("body") or ""),
            recipients=list(payload.get("recipients") or []),
            recipient_provenance=dict(payload.get("recipient_provenance") or {}),
            send_authority_ref=payload.get("send_authority_ref"),
            evidence_refs=list(payload.get("evidence_refs") or []),
            objective_tags=list(payload.get("objective_tags") or []),
        )
        result = organ.execute(request, contract=contract)
        status = PowerStepStatus.SUCCEEDED if result.status in {ChannelDraftSendStatus.DRAFT_CREATED, ChannelDraftSendStatus.SENT} else PowerStepStatus.FAILED
        if result.status is ChannelDraftSendStatus.BLOCKED:
            status = PowerStepStatus.BLOCKED
        return PowerStepResult(
            step_id=step.step_id,
            status=status,
            receipt_refs=[result.receipt.receipt_id] if result.receipt else [],
            finalgate_certificate_refs=[result.finalgate_certificate.certificate_id] if result.finalgate_certificate else [],
            blocked_reason=result.blocked_reason,
            safe_summary=result.safe_summary,
        )

    return _executor


def _build_receipt(
    request: ChannelDraftSendRequest,
    *,
    send_attempted: bool,
    delivery_ref: str | None = None,
) -> ChannelDraftSendReceipt:
    compliance_reasons = _compliance_reasons(request)
    return ChannelDraftSendReceipt(
        mission_id=request.mission_id,
        mode=request.mode,
        channel=request.channel,
        draft_hash=_stable_hash(
            {
                "channel": request.channel,
                "subject_hash": _optional_hash(request.subject),
                "body_sha256": _sha256_text(request.body),
                "recipient_hashes": [_sha256_text(recipient) for recipient in request.recipients],
            }
        ),
        subject_hash=_optional_hash(request.subject),
        body_sha256=_sha256_text(request.body),
        recipient_hashes=[_sha256_text(recipient) for recipient in request.recipients],
        evidence_refs=list(request.evidence_refs),
        send_attempted=send_attempted,
        delivery_ref=delivery_ref,
        send_authority_ref=request.send_authority_ref,
        compliance_reasons=compliance_reasons or ["channel_compliance_clear"],
    )


def _compliance_reasons(request: ChannelDraftSendRequest) -> list[str]:
    haystack = " ".join([request.subject or "", request.body, *request.objective_tags]).lower().replace(" ", "_")
    reasons: list[str] = []
    for label, markers in {
        "spam": {"spam", "mass_spam", "illegal_spam"},
        "deceptive_outreach": {"deceptive", "deception", "misleading"},
        "hidden_identity": {"hide_identity", "hidden_identity", "anonymous_sender"},
        "credential_capture": {"credential_capture", "capture_credentials", "phishing", "api_key"},
    }.items():
        if any(marker in haystack for marker in markers):
            reasons.append(label)
    if SHARED_SECRET_LIKE_PATTERN.search(haystack):
        reasons.append("secret_like_content")
    return sorted(set(reasons))


def _optional_hash(value: str | None) -> str | None:
    return _sha256_text(value) if value is not None else None


def _sha256_text(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
