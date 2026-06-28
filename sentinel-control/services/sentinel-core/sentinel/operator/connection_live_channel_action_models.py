from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class LiveChannelActionDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    authority_granting: bool = False
    can_grant_authority: bool = False
    can_execute: bool = False
    can_send: bool = False
    can_write: bool = False
    credential_value_present: bool = False
    raw_secret_material: bool = False
    registry_can_execute: bool = False
    fallback_auto_allowed: bool = False
    provider_native_tools_allowed: bool = False

    @model_validator(mode="after")
    def _data_model_is_not_authority(self) -> "LiveChannelActionDataModel":
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
        if self.fallback_auto_allowed:
            raise ValueError(f"{self.__class__.__name__}: fallback/AUTO is forbidden")
        if self.provider_native_tools_allowed:
            raise ValueError(f"{self.__class__.__name__}: provider-native tools are forbidden")
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute or self.registry_can_execute,
        )
        return self


class LiveChannelSendDecision(LiveChannelActionDataModel):
    decision_id: str = Field(default_factory=lambda: new_id("live_channel_decision"))
    action: str
    adapter_id: str
    channel: str
    body: str = Field(exclude=True, repr=False)
    recipients: tuple[str, ...] = Field(exclude=True, repr=False)
    recipient_provenance: dict[str, str] = Field(default_factory=dict, exclude=True, repr=False)
    subject: str | None = Field(default=None, exclude=True, repr=False)
    thread_ref: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def _decision_is_bounded_send_message(self) -> "LiveChannelSendDecision":
        if self.action != "send_message":
            raise ValueError("unsupported live channel action")
        for label, value in (
            ("decision_id", self.decision_id),
            ("adapter_id", self.adapter_id),
            ("channel", self.channel),
            ("body", self.body),
            ("subject", self.subject or ""),
            ("thread_ref", self.thread_ref or ""),
            ("idempotency_key", self.idempotency_key or ""),
        ):
            _reject_secret_material(value, label)
        if not self.evidence_refs:
            raise ValueError("live channel send decision requires evidence refs")
        for recipient in self.recipients:
            _reject_secret_material(recipient, "recipient")
        for key, value in self.recipient_provenance.items():
            _reject_secret_material(key, "recipient_provenance")
            _reject_secret_material(value, "recipient_provenance")
        for evidence_ref in self.evidence_refs:
            _reject_secret_material(evidence_ref, "evidence_refs")
        if not self.recipients:
            raise ValueError("live channel send decision requires recipients")
        return self

    @property
    def body_hash(self) -> str:
        return text_hash(self.body)

    @property
    def recipient_hashes(self) -> tuple[str, ...]:
        return tuple(text_hash(recipient.strip().lower()) for recipient in self.recipients)

    def safe_summary(self) -> dict[str, Any]:
        payload = {
            "decision_id": self.decision_id,
            "action": self.action,
            "adapter_id": self.adapter_id,
            "channel": self.channel,
            "body_hash": self.body_hash,
            "recipient_hashes": list(self.recipient_hashes),
            "recipient_count": len(self.recipients),
            "thread_ref_hash": text_hash(self.thread_ref or ""),
            "evidence_refs": list(self.evidence_refs),
            "idempotency_key_hash": text_hash(self.idempotency_key or ""),
            "fallback_auto_allowed": self.fallback_auto_allowed,
            "provider_native_tools_allowed": self.provider_native_tools_allowed,
        }
        payload["decision_safe_hash"] = stable_hash(payload)
        return payload


class LiveChannelActionResult(LiveChannelActionDataModel):
    action_result_id: str = Field(default_factory=lambda: new_id("live_channel_action_result"))
    decision_id: str
    action: str
    status: str
    model_led: bool
    per_message_approval_required: bool
    draft_ref: str
    channel_send_result_ref: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    delivery_ref_hash: str | None = None
    result_hash: str

    @model_validator(mode="after")
    def _result_is_receipt_metadata_not_authority(self) -> "LiveChannelActionResult":
        if self.status != "sent":
            raise ValueError("live channel action result currently records successful sends only")
        if self.per_message_approval_required:
            raise ValueError("model-led channel action result cannot require per-message approval")
        return self


def live_channel_hash(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


def _reject_secret_material(value: str, label: str) -> None:
    lowered = value.lower()
    for marker in (
        "sk-",
        "bearer ",
        "authorization",
        "cookie:",
        "session=",
        "session_token",
        "password",
        "-----begin",
        "oauth_access_token",
        "access_token=",
        "api_key=",
        "secret=",
        "provider_native_tools",
        "provider-native tools",
        "fallback:auto",
    ):
        if marker in lowered:
            raise ValueError(f"{label} cannot contain credential value or secret material")


__all__ = [
    "LiveChannelActionResult",
    "LiveChannelSendDecision",
    "live_channel_hash",
]
