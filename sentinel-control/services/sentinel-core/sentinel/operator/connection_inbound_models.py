from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


def inbound_utc_now() -> datetime:
    return datetime.now(UTC)


class InboundConnectionSourceKind(StrEnum):
    CHANNEL_INBOUND_MESSAGE = "channel_inbound_message"
    EMAIL_INBOUND_MESSAGE = "email_inbound_message"
    WEBHOOK_PAYLOAD = "webhook_payload"
    BROWSER_READ_ONLY_SNAPSHOT = "browser_read_only_snapshot"
    EXTERNAL_API_READ_ONLY_RESPONSE = "external_api_read_only_response"
    VOICE_TRANSCRIPT = "voice_transcript"
    DESKTOP_OBSERVATION_SNAPSHOT = "desktop_observation_snapshot"
    OPERATOR_UPLOADED_ARTIFACT = "operator_uploaded_artifact"


class InboundQuarantineStatus(StrEnum):
    QUARANTINED = "quarantined"
    BLOCKED = "blocked"


class InboundReadOnlyReceiptStatus(StrEnum):
    RECORDED = "recorded"
    BLOCKED = "blocked"


_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_instructions", re.compile(r"\bignore\s+(previous|all|system)\s+instructions\b", re.I)),
    ("secret_exfiltration_request", re.compile(r"\b(exfiltrate|leak|reveal|dump)\s+(secret|credential|token|key)s?\b", re.I)),
    ("external_send_request", re.compile(r"\b(send|forward|post|email)\b.+\b(external|address|recipient|slack|telegram|discord)\b", re.I)),
    ("click_request", re.compile(r"\bclick\b.+\b(link|button|url)\b", re.I)),
    ("tool_request", re.compile(r"\b(use|invoke|call|execute)\b.+\b(tool|workflow|command|shell|browser)\b", re.I)),
    ("approval_request", re.compile(r"\b(approve|authorize|grant)\b.+\b(action|authority|permission)\b", re.I)),
)
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key_like", re.compile(r"\bsk-[A-Za-z0-9._-]{8,}\b", re.I)),
    ("authorization_header", re.compile(r"\bauthorization\s*:\s*", re.I)),
    ("bearer_token", re.compile(r"\bbearer\s+[A-Za-z0-9._-]+", re.I)),
    ("cookie_or_session", re.compile(r"\b(cookie|session_token|session)\s*[:=]", re.I)),
    ("password_assignment", re.compile(r"\bpassword\s*=", re.I)),
    ("private_key_material", re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----", re.I)),
    ("oauth_token", re.compile(r"\boauth_access_token\s*=", re.I)),
    ("access_token", re.compile(r"\baccess_token\s*=", re.I)),
    ("credential_assignment", re.compile(r"\b(secret|api_key|token)\s*=", re.I)),
)


class InboundDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    authority_granting: bool = False
    can_grant_authority: bool = False
    can_execute: bool = False
    can_send: bool = False
    can_write: bool = False
    registry_can_execute: bool = False
    credential_value_present: bool = False
    raw_secret_material: bool = False

    @model_validator(mode="after")
    def _inbound_data_is_not_authority(self) -> "InboundDataModel":
        if self.authority_granting:
            raise ValueError(f"{self.__class__.__name__}: authority granting is forbidden")
        if self.can_send:
            raise ValueError(f"{self.__class__.__name__}: can_send must remain false")
        if self.can_write:
            raise ValueError(f"{self.__class__.__name__}: can_write must remain false")
        if self.registry_can_execute:
            raise ValueError(f"{self.__class__.__name__}: registry cannot execute")
        if self.credential_value_present:
            raise ValueError(f"{self.__class__.__name__}: credential value persistence is forbidden")
        if self.raw_secret_material:
            raise ValueError(f"{self.__class__.__name__}: raw secret material is forbidden")
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute or self.registry_can_execute,
        )
        return self


class InboundConnectionSource(InboundDataModel):
    source_id: str
    source_kind: InboundConnectionSourceKind
    connection_id: str
    tenant_scope_id: str
    sender_label: str | None = None
    sender_label_hash: str | None = None
    sender_identity_is_authority: bool = False

    @model_validator(mode="after")
    def _source_is_safe_metadata(self) -> "InboundConnectionSource":
        for label, value in (
            ("source_id", self.source_id),
            ("connection_id", self.connection_id),
            ("tenant_scope_id", self.tenant_scope_id),
            ("sender_label", self.sender_label or ""),
        ):
            _reject_raw_secret_or_endpoint(value, label)
        if self.sender_identity_is_authority:
            raise ValueError("inbound sender identity cannot grant authority")
        if self.sender_label and self.sender_label_hash is None:
            self.sender_label_hash = text_hash(self.sender_label)
        return self

    def safe_summary(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_kind": self.source_kind.value,
            "connection_id": self.connection_id,
            "tenant_scope_id": self.tenant_scope_id,
            "sender_label_hash": self.sender_label_hash,
            "sender_identity_is_authority": self.sender_identity_is_authority,
        }


class InboundObservationEnvelope(InboundDataModel):
    observation_id: str = Field(default_factory=lambda: new_id("inbound_observation"))
    source: InboundConnectionSource
    content: str = Field(default="", exclude=True, repr=False)
    attachment_count: int = Field(default=0, ge=0)
    link_count: int = Field(default=0, ge=0)
    sender_identity_claim: str | None = None
    created_at: datetime = Field(default_factory=inbound_utc_now)

    @model_validator(mode="after")
    def _envelope_is_untrusted_input_only(self) -> "InboundObservationEnvelope":
        _reject_raw_secret_or_endpoint(self.observation_id, "observation_id")
        _reject_raw_secret_or_endpoint(self.sender_identity_claim or "", "sender_identity_claim")
        return self

    @property
    def content_hash(self) -> str:
        return text_hash(self.content)


class InboundPromptInjectionFinding(InboundDataModel):
    finding_id: str = Field(default_factory=lambda: new_id("inbound_prompt_injection"))
    labels: tuple[str, ...] = Field(default_factory=tuple)
    content_hash: str
    safe_summary: str = "Inbound prompt-injection markers recorded as untrusted evidence."
    finding_hash: str


class InboundSecretExposureFinding(InboundDataModel):
    finding_id: str = Field(default_factory=lambda: new_id("inbound_secret_exposure"))
    labels: tuple[str, ...] = Field(default_factory=tuple)
    content_hash: str
    redaction_applied: bool = True
    safe_summary: str = "Inbound secret-exposure markers recorded without secret material."
    finding_hash: str


class InboundQuarantineDecision(InboundDataModel):
    quarantine_id: str = Field(default_factory=lambda: new_id("inbound_quarantine"))
    observation_id: str
    source_kind: InboundConnectionSourceKind
    connection_id: str
    status: InboundQuarantineStatus
    content_hash: str
    prompt_injection_labels: tuple[str, ...] = Field(default_factory=tuple)
    secret_exposure_labels: tuple[str, ...] = Field(default_factory=tuple)
    decision_reason: str = "Inbound content is quarantined as untrusted evidence, not instruction."
    created_at: datetime = Field(default_factory=inbound_utc_now)
    decision_hash: str


class InboundReadOnlyEvidenceArtifact(InboundDataModel):
    evidence_id: str = Field(default_factory=lambda: new_id("inbound_evidence"))
    observation_id: str
    quarantine_ref: str
    source_kind: InboundConnectionSourceKind
    connection_id: str
    manifest_hash: str
    identity_boundary_hash: str
    content_hash: str
    bounded_preview: str
    preview_hash: str
    attachment_count: int
    link_count: int
    untrusted_content: bool = True
    instruction_authority: bool = False
    prompt_injection_labels: tuple[str, ...] = Field(default_factory=tuple)
    secret_exposure_labels: tuple[str, ...] = Field(default_factory=tuple)
    redaction_labels: tuple[str, ...] = Field(default_factory=tuple)
    artifact_hash: str

    @model_validator(mode="after")
    def _evidence_is_not_instruction(self) -> "InboundReadOnlyEvidenceArtifact":
        if self.instruction_authority:
            raise ValueError("inbound evidence cannot be instruction authority")
        return self


class InboundReadOnlyReceipt(InboundDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("inbound_receipt"))
    observation_id: str
    quarantine_ref: str
    evidence_ref: str
    connection_id: str
    source_kind: InboundConnectionSourceKind
    status: InboundReadOnlyReceiptStatus
    content_hash: str
    safe_summary: str = "Inbound read-only observation recorded as quarantined evidence."
    receipt_hash: str


class InboundIntakePolicy(InboundDataModel):
    policy_id: str = "inbound_read_only_intake_policy_v1"
    max_preview_chars: int = Field(default=240, ge=32, le=2000)
    allowed_source_kinds: tuple[InboundConnectionSourceKind, ...] = tuple(InboundConnectionSourceKind)
    create_receipt: bool = True
    quarantine_by_default: bool = True


class InboundReplayView(InboundDataModel):
    replay_id: str = Field(default_factory=lambda: new_id("inbound_replay"))
    observation_count: int
    quarantine_count: int
    evidence_count: int
    receipt_count: int
    artifact_hashes: tuple[str, ...]
    reexecuted_actions: bool = False
    provider_calls_delta: int = 0
    network_calls_delta: int = 0
    tool_calls_delta: int = 0
    receipt_writes_delta: int = 0
    evidence_writes_delta: int = 0
    quarantine_writes_delta: int = 0
    workspace_mutations_delta: int = 0


class InboundIntakeResult(InboundDataModel):
    source: InboundConnectionSource
    policy: InboundIntakePolicy
    prompt_injection_finding: InboundPromptInjectionFinding
    secret_exposure_finding: InboundSecretExposureFinding
    quarantine_decision: InboundQuarantineDecision
    evidence_artifact: InboundReadOnlyEvidenceArtifact
    receipt: InboundReadOnlyReceipt

    def material_counts(self) -> dict[str, int]:
        return {
            "quarantine": 1,
            "evidence": 1,
            "receipt": 1,
        }

    def export_safe_summary(self) -> dict[str, Any]:
        payload = {
            "source": self.source.safe_summary(),
            "policy_id": self.policy.policy_id,
            "quarantine_ref": self.quarantine_decision.quarantine_id,
            "evidence_ref": self.evidence_artifact.evidence_id,
            "receipt_ref": self.receipt.receipt_id,
            "source_kind": self.source.source_kind.value,
            "connection_id": self.source.connection_id,
            "content_hash": self.evidence_artifact.content_hash,
            "preview_hash": self.evidence_artifact.preview_hash,
            "attachment_count": self.evidence_artifact.attachment_count,
            "link_count": self.evidence_artifact.link_count,
            "prompt_injection_labels": list(self.quarantine_decision.prompt_injection_labels),
            "secret_exposure_labels": list(self.quarantine_decision.secret_exposure_labels),
            "redaction_labels": list(self.evidence_artifact.redaction_labels),
            "quarantine_status": self.quarantine_decision.status.value,
            "receipt_status": self.receipt.status.value,
            "can_execute": self.receipt.can_execute,
            "can_send": self.receipt.can_send,
            "can_write": self.receipt.can_write,
            "quarantine_hash": self.quarantine_decision.decision_hash,
            "evidence_hash": self.evidence_artifact.artifact_hash,
            "receipt_hash": self.receipt.receipt_hash,
        }
        payload["safe_export_hash"] = stable_hash(payload)
        return payload


def build_prompt_injection_labels(content: str) -> tuple[str, ...]:
    return tuple(label for label, pattern in _PROMPT_INJECTION_PATTERNS if pattern.search(content))


def build_secret_exposure_labels(content: str) -> tuple[str, ...]:
    return tuple(label for label, pattern in _SECRET_PATTERNS if pattern.search(content))


def build_bounded_preview(content: str, *, max_chars: int) -> tuple[str, tuple[str, ...]]:
    labels = build_secret_exposure_labels(content)
    if labels:
        return "[REDACTED_SECRET_LIKE_INBOUND_CONTENT]", ("credential_like_content_redacted",)
    preview = content[:max_chars]
    if len(content) > max_chars:
        marker = "...[truncated]"
        preview = content[: max_chars - len(marker)].rstrip() + marker
    return preview, ()


def artifact_hash(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


def _reject_raw_secret_or_endpoint(value: str, label: str) -> None:
    lowered = value.lower()
    if "://" in value:
        raise ValueError(f"{label} cannot contain raw endpoint values")
    for marker in ("sk-", "bearer ", "authorization", "cookie:", "session=", "password", "-----begin", "oauth_access_token", "access_token=", "api_key=", "secret="):
        if marker in lowered:
            raise ValueError(f"{label} cannot contain credential value or secret material")


__all__ = [
    "InboundConnectionSource",
    "InboundConnectionSourceKind",
    "InboundObservationEnvelope",
    "InboundQuarantineDecision",
    "InboundQuarantineStatus",
    "InboundReadOnlyEvidenceArtifact",
    "InboundReadOnlyReceipt",
    "InboundReadOnlyReceiptStatus",
    "InboundPromptInjectionFinding",
    "InboundSecretExposureFinding",
    "InboundReplayView",
    "InboundIntakePolicy",
    "InboundIntakeResult",
    "artifact_hash",
    "build_bounded_preview",
    "build_prompt_injection_labels",
    "build_secret_exposure_labels",
]
