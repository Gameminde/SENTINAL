from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionRecord
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.shared.models import SentinelModel, new_id


def authority_utc_now() -> datetime:
    return datetime.now(UTC)


class MissionAuthorityPolicy(SentinelModel):
    user_id: str
    mission_type: MissionType = MissionType.GTM
    mode: MissionMode = MissionMode.SAFE
    allowed_systems: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=lambda: ["."])
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_accounts: list[str] = Field(default_factory=list)
    allowed_data_types: list[str] = Field(default_factory=list)
    max_duration_minutes: int = Field(default=30, ge=1)
    max_actions: int = Field(default=10, ge=1)
    max_cost_usd: float = Field(default=0.0, ge=0.0)
    max_recipients: int = Field(default=0, ge=0)
    risk_appetite_score: float = Field(default=25.0, ge=0.0, le=100.0)
    trace_level: str = "standard"
    rollback_preference: str = "metadata_only"
    emergency_stop_enabled: bool = True
    policy_id: str = "default_pack1_authority_policy"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _policy_is_not_authority(self) -> "MissionAuthorityPolicy":
        assert_data_not_authority(
            context="mission_authority_policy",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.model_dump(mode="python"), context="mission_authority_policy")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["user_id"] = redact_operator_text(str(payload.get("user_id", "")))
        payload["policy_id"] = redact_operator_text(str(payload.get("policy_id", "")))
        return redact_operator_value(payload)

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.safe_model_dump())


class MissionAuthorityEnvelopeRecord(SentinelModel):
    envelope_id: str = Field(default_factory=lambda: new_id("authority_envelope"))
    version: int = Field(ge=1)
    mission_id: str
    previous_envelope_ref: str | None = None
    authority_summary_hash: str
    policy_hash: str
    issued_at: datetime = Field(default_factory=authority_utc_now)
    expires_at: datetime
    revocation_ref: str | None = None
    envelope_hash: str
    envelope_payload: dict[str, Any] = Field(default_factory=dict)
    record_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _record_is_proof_not_authority(self) -> "MissionAuthorityEnvelopeRecord":
        assert_data_not_authority(
            context="mission_authority_envelope_record",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "version": self.version,
            "mission_id": self.mission_id,
            "previous_envelope_ref": self.previous_envelope_ref,
            "authority_summary_hash": self.authority_summary_hash,
            "policy_hash": self.policy_hash,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "revocation_ref": self.revocation_ref,
            "envelope_hash": self.envelope_hash,
            "envelope_payload": redact_operator_value(self.envelope_payload),
            "record_hash": self.record_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "MissionAuthorityEnvelopeRecord":
        payload = self.safe_model_dump()
        payload["record_hash"] = ""
        return self.model_copy(update={"record_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["record_hash"]
        payload["record_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class MissionAuthorityRevocationRecord(SentinelModel):
    revocation_ref: str = Field(default_factory=lambda: new_id("authority_revocation"))
    mission_id: str
    revoked_envelope_ref: str
    reason: str
    revoked_at: datetime = Field(default_factory=authority_utc_now)
    revocation_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _revocation_is_proof_not_authority(self) -> "MissionAuthorityRevocationRecord":
        assert_data_not_authority(
            context="mission_authority_revocation_record",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "revocation_ref": self.revocation_ref,
            "mission_id": self.mission_id,
            "revoked_envelope_ref": self.revoked_envelope_ref,
            "reason": redact_operator_text(self.reason),
            "revoked_at": self.revoked_at.isoformat(),
            "revocation_hash": self.revocation_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "MissionAuthorityRevocationRecord":
        payload = self.safe_model_dump()
        payload["revocation_hash"] = ""
        return self.model_copy(update={"revocation_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["revocation_hash"]
        payload["revocation_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class IssuedMissionAuthority(SentinelModel):
    envelope: MissionAuthorityEnvelope
    record: MissionAuthorityEnvelopeRecord


class MissionAuthorityEnvelopeIssuer:
    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel

    def issue(self, mission_id: str, *, policy: MissionAuthorityPolicy) -> IssuedMissionAuthority:
        record = self.kernel.store.load_record(mission_id)
        summary = _require_authority_summary(record)
        _assert_summary_within_policy(summary, policy)
        version = self._next_version(mission_id)
        issued_at = authority_utc_now()
        envelope = _build_envelope(record, summary, policy, issued_at=issued_at)
        envelope_record = self._record_for_envelope(
            mission_id=mission_id,
            envelope=envelope,
            summary=summary,
            policy=policy,
            version=version,
            previous_envelope_ref=None,
        )
        self._persist_record(envelope_record)
        self.kernel.store.append_event(
            mission_id,
            event_type="mission_authority_envelope_issued",
            safe_summary="Mission authority envelope issued from approved summary and policy.",
            metadata={
                "envelope_id": envelope_record.envelope_id,
                "version": envelope_record.version,
                "authority_summary_hash": envelope_record.authority_summary_hash,
                "policy_hash": envelope_record.policy_hash,
                "envelope_hash": envelope_record.envelope_hash,
            },
        )
        return IssuedMissionAuthority(envelope=envelope, record=envelope_record)

    def renew(
        self,
        mission_id: str,
        *,
        previous_envelope_ref: str,
        policy: MissionAuthorityPolicy,
    ) -> IssuedMissionAuthority:
        previous = self.load_record(mission_id, previous_envelope_ref)
        if self._is_envelope_revoked(mission_id, previous.envelope_id):
            raise ValueError("mission_authority_envelope_revoked")
        record = self.kernel.store.load_record(mission_id)
        summary = _require_authority_summary(record)
        _assert_summary_within_policy(summary, policy)
        issued_at = authority_utc_now()
        envelope = _build_envelope(record, summary, policy, issued_at=issued_at)
        envelope_record = self._record_for_envelope(
            mission_id=mission_id,
            envelope=envelope,
            summary=summary,
            policy=policy,
            version=previous.version + 1,
            previous_envelope_ref=previous.envelope_id,
        )
        self._persist_record(envelope_record)
        self.kernel.store.append_event(
            mission_id,
            event_type="mission_authority_envelope_renewed",
            safe_summary="Mission authority envelope renewed as a new immutable version.",
            metadata={
                "envelope_id": envelope_record.envelope_id,
                "previous_envelope_ref": previous.envelope_id,
                "version": envelope_record.version,
                "policy_hash": envelope_record.policy_hash,
            },
        )
        return IssuedMissionAuthority(envelope=envelope, record=envelope_record)

    def revoke(self, mission_id: str, *, envelope_ref: str, reason: str) -> MissionAuthorityRevocationRecord:
        record = self.load_record(mission_id, envelope_ref)
        if self._is_envelope_revoked(mission_id, record.envelope_id):
            raise ValueError("mission_authority_envelope_already_revoked")
        revocation = MissionAuthorityRevocationRecord(
            mission_id=mission_id,
            revoked_envelope_ref=envelope_ref,
            reason=reason,
        ).with_hash()
        self.kernel.store.atomic_write_json(
            self._revocation_path(mission_id, revocation.revocation_ref),
            revocation.safe_model_dump(),
        )
        self.kernel.store.append_event(
            mission_id,
            event_type="mission_authority_envelope_revoked",
            safe_summary="Mission authority envelope revocation recorded.",
            metadata={
                "revocation_ref": revocation.revocation_ref,
                "revoked_envelope_ref": envelope_ref,
                "revocation_hash": revocation.revocation_hash,
            },
        )
        return revocation

    def resolve_active(self, mission_id: str) -> MissionAuthorityEnvelope:
        records = self.list_records(mission_id)
        if not records:
            raise ValueError("mission_authority_envelope_missing")
        latest = records[-1]
        if self._is_envelope_revoked(mission_id, latest.envelope_id):
            raise ValueError("mission_authority_envelope_revoked")
        if authority_utc_now() > latest.expires_at:
            raise ValueError("mission_authority_envelope_expired")
        return MissionAuthorityEnvelope.model_validate(latest.envelope_payload)

    def load_record(self, mission_id: str, envelope_ref: str) -> MissionAuthorityEnvelopeRecord:
        path = self._envelope_path(mission_id, envelope_ref)
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = MissionAuthorityEnvelopeRecord.model_validate(payload)
        if not record.verify_hash():
            raise ValueError("mission authority envelope record hash mismatch")
        return record

    def list_records(self, mission_id: str) -> list[MissionAuthorityEnvelopeRecord]:
        root = self._envelope_root(mission_id)
        if not root.exists():
            return []
        records = [
            MissionAuthorityEnvelopeRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(root.glob("*.json"))
        ]
        for record in records:
            if not record.verify_hash():
                raise ValueError("mission authority envelope record hash mismatch")
        return sorted(records, key=lambda item: (item.version, item.issued_at, item.envelope_id))

    def list_revocations(self, mission_id: str) -> list[MissionAuthorityRevocationRecord]:
        root = self._revocation_root(mission_id)
        if not root.exists():
            return []
        revocations = [
            MissionAuthorityRevocationRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(root.glob("*.json"))
        ]
        for revocation in revocations:
            if not revocation.verify_hash():
                raise ValueError("mission authority revocation record hash mismatch")
        return sorted(revocations, key=lambda item: (item.revoked_at, item.revocation_ref))

    def _is_envelope_revoked(self, mission_id: str, envelope_ref: str) -> bool:
        return any(
            revocation.revoked_envelope_ref == envelope_ref
            for revocation in self.list_revocations(mission_id)
        )

    def _record_for_envelope(
        self,
        *,
        mission_id: str,
        envelope: MissionAuthorityEnvelope,
        summary: MissionAuthoritySummary,
        policy: MissionAuthorityPolicy,
        version: int,
        previous_envelope_ref: str | None,
    ) -> MissionAuthorityEnvelopeRecord:
        envelope_payload = envelope.model_dump(mode="json")
        return MissionAuthorityEnvelopeRecord(
            version=version,
            mission_id=mission_id,
            previous_envelope_ref=previous_envelope_ref,
            authority_summary_hash=stable_hash(summary.model_dump(mode="json")),
            policy_hash=policy.policy_hash,
            issued_at=envelope.created_at,
            expires_at=envelope.resolved_expires_at(),
            envelope_hash=stable_hash(envelope_payload),
            envelope_payload=envelope_payload,
        ).with_hash()

    def _persist_record(self, record: MissionAuthorityEnvelopeRecord) -> None:
        self.kernel.store.atomic_write_json(
            self._envelope_path(record.mission_id, record.envelope_id),
            record.safe_model_dump(),
        )

    def _next_version(self, mission_id: str) -> int:
        records = self.list_records(mission_id)
        return 1 if not records else max(record.version for record in records) + 1

    def _envelope_root(self, mission_id: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "authority" / "envelopes"

    def _envelope_path(self, mission_id: str, envelope_ref: str) -> Path:
        return self._envelope_root(mission_id) / f"{envelope_ref}.json"

    def _revocation_path(self, mission_id: str, revocation_ref: str) -> Path:
        return self._revocation_root(mission_id) / f"{revocation_ref}.json"

    def _revocation_root(self, mission_id: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "authority" / "revocations"


def _require_authority_summary(record: MissionRecord) -> MissionAuthoritySummary:
    if record.authority_summary is None:
        raise ValueError("mission_authority_summary_required")
    return record.authority_summary


def _assert_summary_within_policy(summary: MissionAuthoritySummary, policy: MissionAuthorityPolicy) -> None:
    summary_actions = set(summary.allowed_actions)
    policy_actions = set(policy.allowed_actions)
    forbidden_actions = set(summary.forbidden_actions) | set(policy.forbidden_actions)
    if not summary_actions:
        raise ValueError("authority_summary_actions_required")
    if not summary_actions.issubset(policy_actions):
        raise ValueError("authority_summary_action_outside_policy")
    if summary_actions & forbidden_actions:
        raise ValueError("authority_summary_action_forbidden")


def _build_envelope(
    record: MissionRecord,
    summary: MissionAuthoritySummary,
    policy: MissionAuthorityPolicy,
    *,
    issued_at: datetime,
) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=record.mission_id,
        user_id=policy.user_id,
        mission_type=policy.mission_type,
        mission_title=record.draft.title,
        mission_objective=record.draft.objective,
        success_criteria=list(record.draft.expected_artifacts),
        mode=policy.mode,
        allowed_systems=list(policy.allowed_systems),
        allowed_tools=list(policy.allowed_tools),
        allowed_actions=list(dict.fromkeys(summary.allowed_actions)),
        forbidden_actions=list(dict.fromkeys([*summary.forbidden_actions, *policy.forbidden_actions])),
        allowed_paths=list(policy.allowed_paths),
        allowed_domains=list(policy.allowed_domains),
        allowed_accounts=list(policy.allowed_accounts),
        allowed_data_types=list(policy.allowed_data_types),
        max_duration_minutes=policy.max_duration_minutes,
        max_actions=policy.max_actions,
        max_cost_usd=policy.max_cost_usd,
        max_recipients=policy.max_recipients,
        risk_appetite_score=policy.risk_appetite_score,
        rollback_preference=policy.rollback_preference,
        trace_level=policy.trace_level,
        emergency_stop_enabled=policy.emergency_stop_enabled,
        created_at=issued_at,
        expires_at=issued_at + timedelta(minutes=policy.max_duration_minutes),
    )


__all__ = [
    "IssuedMissionAuthority",
    "MissionAuthorityEnvelopeIssuer",
    "MissionAuthorityEnvelopeRecord",
    "MissionAuthorityPolicy",
    "MissionAuthorityRevocationRecord",
]
