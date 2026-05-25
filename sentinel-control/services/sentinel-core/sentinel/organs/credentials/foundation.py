from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.credentials.vault_policy import CredentialAccessSource
from sentinel.shared.models import SentinelModel, new_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class MissionAuthorityGrantScope(StrEnum):
    MISSION = "mission"
    ORGAN = "organ"
    ACTION_LEVEL = "action_level"
    DOMAIN = "domain"
    ACTION = "action"
    CREDENTIAL_REF = "credential_ref"


class MissionAuthorityGrantStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REJECTED = "rejected"
    METADATA_ONLY = "metadata_only"


class CredentialGrantScope(StrEnum):
    MISSION = "mission"
    ORGAN = "organ"
    ACTION_LEVEL = "action_level"
    DOMAIN = "domain"
    ACTION = "action"
    CREDENTIAL_REF = "credential_ref"


class CredentialGrantStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REJECTED = "rejected"
    METADATA_ONLY = "metadata_only"


class CredentialAccessDecision(StrEnum):
    ALLOWED_METADATA_ONLY = "allowed_metadata_only"
    BLOCKED_MISSING_GRANT = "blocked_missing_grant"
    BLOCKED_EXPIRED = "blocked_expired"
    BLOCKED_REVOKED = "blocked_revoked"
    BLOCKED_SCOPE_MISMATCH = "blocked_scope_mismatch"
    BLOCKED_SOURCE = "blocked_source"
    BLOCKED_USE_COUNT = "blocked_use_count"
    REJECTED_UNSAFE_PAYLOAD = "rejected_unsafe_payload"


class AuthorityCredentialSafetyValidationResult(SentinelModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    payload_hash: str | None = None
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> AuthorityCredentialSafetyValidationResult:
        _assert_no_authority_or_execution(self)
        return self


class MissionAuthorityGrant(SentinelModel):
    grant_id: str = Field(default_factory=lambda: new_id("authgrant"))
    mission_id: str
    allowed_organs: list[str] = Field(default_factory=list)
    allowed_action_levels: list[str] = Field(default_factory=list)
    domain_scope: list[str] = Field(default_factory=list)
    action_scope: list[str] = Field(default_factory=list)
    credential_ref_id: str | None = None
    expires_at: datetime | None = None
    ttl_seconds: int | None = Field(default=None, ge=0)
    status: MissionAuthorityGrantStatus = MissionAuthorityGrantStatus.ACTIVE
    revoked_at: datetime | None = None
    user_approval_required: bool = True
    finalgate_required: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Mission authority grant metadata only."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_scope(self) -> MissionAuthorityGrant:
        _assert_no_authority_or_execution(self)
        if not self.mission_id.strip():
            raise ValueError("MissionAuthorityGrant requires mission scope.")
        if not self.allowed_organs:
            raise ValueError("MissionAuthorityGrant requires organ scope.")
        if not self.allowed_action_levels:
            raise ValueError("MissionAuthorityGrant requires action level scope.")
        if not self.action_scope:
            raise ValueError("MissionAuthorityGrant requires action scope.")
        if self.status is MissionAuthorityGrantStatus.REVOKED and self.revoked_at is None:
            raise ValueError("Revoked mission authority grants require revoked_at.")
        return self


class CredentialGrant(SentinelModel):
    grant_id: str = Field(default_factory=lambda: new_id("credgrant"))
    mission_id: str
    credential_ref_id: str
    allowed_organs: list[str] = Field(default_factory=list)
    allowed_action_levels: list[str] = Field(default_factory=list)
    domain_scope: list[str] = Field(default_factory=list)
    action_scope: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    ttl_seconds: int | None = Field(default=None, ge=0)
    max_use_count: int = Field(default=1, ge=0)
    used_count: int = Field(default=0, ge=0)
    status: CredentialGrantStatus = CredentialGrantStatus.ACTIVE
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
    user_approval_required: bool = True
    finalgate_required: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Credential grant metadata only. It does not contain or unlock a credential value."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_scope(self) -> CredentialGrant:
        _assert_no_authority_or_execution(self)
        if not self.mission_id.strip():
            raise ValueError("CredentialGrant requires mission scope.")
        if not self.credential_ref_id.strip():
            raise ValueError("CredentialGrant requires credential ref scope.")
        if not self.allowed_organs:
            raise ValueError("CredentialGrant requires organ scope.")
        if not self.allowed_action_levels:
            raise ValueError("CredentialGrant requires action level scope.")
        if not self.action_scope:
            raise ValueError("CredentialGrant requires action scope.")
        if self.status is CredentialGrantStatus.REVOKED and self.revoked_at is None:
            raise ValueError("Revoked credential grants require revoked_at.")
        return self

    def is_expired(self, current_time: datetime | None = None) -> bool:
        now = current_time or utc_now()
        return self.expires_at is not None and now > self.expires_at

    def is_revoked(self) -> bool:
        return self.status is CredentialGrantStatus.REVOKED or self.revoked_at is not None


class CredentialAccessRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("credreq"))
    mission_id: str
    credential_ref_id: str
    organ_kind: str
    action_level: str
    domain: str | None = None
    action: str
    source: CredentialAccessSource = CredentialAccessSource.ORGAN_RUNTIME
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    selected_provider_id: str | None = None
    selected_backend_id: str | None = None
    selected_model: str | None = None
    safe_summary: str = "Credential request metadata only."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_request(self) -> CredentialAccessRequest:
        _assert_no_authority_or_execution(self)
        if not self.mission_id.strip():
            raise ValueError("CredentialAccessRequest requires mission scope.")
        if not self.credential_ref_id.strip():
            raise ValueError("CredentialAccessRequest requires credential ref scope.")
        if not self.organ_kind.strip():
            raise ValueError("CredentialAccessRequest requires organ scope.")
        if not self.action.strip():
            raise ValueError("CredentialAccessRequest requires action scope.")
        return self


class CredentialAccessProof(SentinelModel):
    proof_id: str = Field(default_factory=lambda: new_id("credproof"))
    credential_ref_id: str
    mission_id: str
    organ_kind: str
    action_level: str
    action_scope: list[str] = Field(default_factory=list)
    domain_scope: list[str] = Field(default_factory=list)
    grant_id: str | None = None
    request_id: str | None = None
    accessed_at: datetime = Field(default_factory=utc_now)
    proof_hash: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Credential proof metadata only; no credential value is present."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_proof(self) -> CredentialAccessProof:
        _assert_no_authority_or_execution(self)
        if not self.credential_ref_id.strip():
            raise ValueError("CredentialAccessProof requires credential ref scope.")
        if not self.mission_id.strip():
            raise ValueError("CredentialAccessProof requires mission scope.")
        if not self.organ_kind.strip():
            raise ValueError("CredentialAccessProof requires organ scope.")
        if not self.action_scope:
            raise ValueError("CredentialAccessProof requires action scope.")
        if not self.proof_hash:
            self.proof_hash = _stable_hash(self._hash_payload())
        return self

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "credential_ref_id": self.credential_ref_id,
            "mission_id": self.mission_id,
            "organ_kind": self.organ_kind,
            "action_level": self.action_level,
            "action_scope": sorted(self.action_scope),
            "domain_scope": sorted(self.domain_scope),
            "grant_id": self.grant_id,
            "request_id": self.request_id,
            "accessed_at": self.accessed_at.isoformat(),
        }


class CredentialRevocation(SentinelModel):
    revocation_id: str = Field(default_factory=lambda: new_id("credrevoke"))
    mission_id: str
    credential_ref_id: str
    grant_id: str
    reason: str
    revoked_at: datetime = Field(default_factory=utc_now)
    status: MissionAuthorityGrantStatus = MissionAuthorityGrantStatus.REVOKED
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_revocation(self) -> CredentialRevocation:
        _assert_no_authority_or_execution(self)
        if not self.reason.strip():
            raise ValueError("CredentialRevocation requires a reason.")
        return self

    @classmethod
    def revoke(
        cls,
        grant: CredentialGrant,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> CredentialRevocation:
        return cls(
            mission_id=grant.mission_id,
            credential_ref_id=grant.credential_ref_id,
            grant_id=grant.grant_id,
            reason=reason,
            revoked_at=revoked_at or utc_now(),
        )


class CredentialAuditReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("credaudit"))
    mission_id: str
    credential_ref_id: str
    grant_id: str | None = None
    decision: CredentialAccessDecision | str
    proof: CredentialAccessProof | None = None
    proof_id: str | None = None
    revocation_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
    secret_accessed: bool = False
    secret_value: str | None = None
    receipt_hash: str = ""
    safe_summary: str = "Credential audit receipt metadata only."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_receipt(self) -> CredentialAuditReceipt:
        _assert_no_authority_or_execution(self)
        if self.secret_accessed or self.secret_value is not None:
            raise ValueError("CredentialAuditReceipt cannot contain or access secret value.")
        if self.proof is not None and self.proof_id is None:
            self.proof_id = self.proof.proof_id
        expected = _stable_hash(self._hash_payload())
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("CredentialAuditReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    @classmethod
    def from_revocation(
        cls,
        revocation: CredentialRevocation,
        *,
        trace_refs: list[str] | None = None,
    ) -> CredentialAuditReceipt:
        return cls(
            mission_id=revocation.mission_id,
            credential_ref_id=revocation.credential_ref_id,
            grant_id=revocation.grant_id,
            decision=CredentialAccessDecision.BLOCKED_REVOKED,
            revocation_id=revocation.revocation_id,
            reasons=[revocation.reason],
            trace_refs=trace_refs or [],
        )

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "credential_ref_id": self.credential_ref_id,
            "grant_id": self.grant_id,
            "decision": self.decision.value if hasattr(self.decision, "value") else str(self.decision),
            "proof_id": self.proof_id,
            "revocation_id": self.revocation_id,
            "reasons": list(self.reasons),
            "evidence_refs": list(self.evidence_refs),
            "receipt_refs": list(self.receipt_refs),
            "trace_refs": list(self.trace_refs),
            "secret_accessed": self.secret_accessed,
        }


class AuthorityPreset(SentinelModel):
    preset_id: str = Field(default_factory=lambda: new_id("authpreset"))
    name: str
    allowed_action_levels: list[str] = Field(default_factory=list)
    allowed_organs: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    credential_grants: list[CredentialGrant] = Field(default_factory=list)
    credential_use_enabled: bool = False
    execution_enabled: bool = False
    root_authority_required: bool = True
    finalgate_required: bool = True
    safe_summary: str = "Authority preset metadata only."
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate_preset(self) -> AuthorityPreset:
        _assert_no_authority_or_execution(self)
        if not self.name.strip():
            raise ValueError("AuthorityPreset requires a name.")
        return self


class AuthorityPresetFactory:
    @staticmethod
    def development_local() -> AuthorityPreset:
        return AuthorityPreset(
            name="development_local",
            allowed_action_levels=["L2", "L3"],
            allowed_organs=["local_artifact", "reversible_workspace"],
            forbidden_actions=["browser", "api", "channel_send", "desktop", "shell", "payment", "credential_use"],
            credential_use_enabled=False,
            execution_enabled=False,
            safe_summary="Development local preset allows only L2/L3 metadata and local low-risk execution when separately opted in.",
        )

    @staticmethod
    def browser_perception() -> AuthorityPreset:
        return AuthorityPreset(
            name="browser_perception",
            allowed_action_levels=["L4"],
            allowed_organs=["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
            forbidden_actions=["submit", "login", "upload", "download", "api_mutation", "channel_send", "credential_use"],
            credential_use_enabled=False,
            execution_enabled=False,
            safe_summary="Browser perception preset allows L4 read-only/preparation/semantic metadata without credentials.",
        )

    @staticmethod
    def operator_browser_l5_template() -> AuthorityPreset:
        return AuthorityPreset(
            name="operator_browser_l5_template",
            allowed_action_levels=["L5"],
            allowed_organs=["browser_navigation", "browser_click", "browser_type"],
            forbidden_actions=["submit", "login", "payment", "credential_use"],
            credential_use_enabled=False,
            execution_enabled=False,
            safe_summary="Operator browser L5 template is non-executing until explicit mission authority and grants are supplied.",
        )

    @staticmethod
    def full_power_template() -> AuthorityPreset:
        return AuthorityPreset(
            name="full_power_template",
            allowed_action_levels=["L2", "L3", "L4", "L5", "L6", "L7"],
            allowed_organs=["template_only"],
            forbidden_actions=[
                "browser_login",
                "browser_submit",
                "api_mutation",
                "channel_send",
                "shell",
                "desktop",
                "payment",
                "spend",
                "trade",
                "credential_use",
            ],
            credential_use_enabled=False,
            execution_enabled=False,
            safe_summary="Full power template is non-executing and requires explicit future grants per organ/action.",
        )


def evaluate_credential_access(
    request: CredentialAccessRequest | dict[str, Any],
    grants: list[CredentialGrant | dict[str, Any]],
    *,
    current_time: datetime | None = None,
) -> CredentialAuditReceipt:
    if not isinstance(request, CredentialAccessRequest):
        request = CredentialAccessRequest.model_validate(request)
    normalized_grants = [
        grant if isinstance(grant, CredentialGrant) else CredentialGrant.model_validate(grant)
        for grant in grants
    ]
    now = current_time or utc_now()
    grant = next(
        (
            candidate
            for candidate in normalized_grants
            if candidate.credential_ref_id == request.credential_ref_id and candidate.mission_id == request.mission_id
        ),
        None,
    )
    if request.source is not CredentialAccessSource.ORGAN_RUNTIME:
        return _audit_receipt(
            request=request,
            grant=grant,
            decision=CredentialAccessDecision.BLOCKED_SOURCE,
            reasons=[f"credential_source_blocked:{request.source.value}"],
        )
    if grant is None:
        return _audit_receipt(
            request=request,
            grant=None,
            decision=CredentialAccessDecision.BLOCKED_MISSING_GRANT,
            reasons=["credential_grant_missing"],
        )
    if grant.is_revoked():
        return _audit_receipt(
            request=request,
            grant=grant,
            decision=CredentialAccessDecision.BLOCKED_REVOKED,
            reasons=["credential_grant_revoked"],
        )
    if grant.is_expired(now):
        return _audit_receipt(
            request=request,
            grant=grant,
            decision=CredentialAccessDecision.BLOCKED_EXPIRED,
            reasons=["credential_grant_expired"],
        )
    if grant.used_count >= grant.max_use_count:
        return _audit_receipt(
            request=request,
            grant=grant,
            decision=CredentialAccessDecision.BLOCKED_USE_COUNT,
            reasons=["credential_grant_use_count_exhausted"],
        )
    if not _scope_matches(request=request, grant=grant):
        return _audit_receipt(
            request=request,
            grant=grant,
            decision=CredentialAccessDecision.BLOCKED_SCOPE_MISMATCH,
            reasons=["credential_grant_scope_mismatch"],
        )

    proof = CredentialAccessProof(
        credential_ref_id=request.credential_ref_id,
        mission_id=request.mission_id,
        organ_kind=request.organ_kind,
        action_level=request.action_level,
        action_scope=[request.action],
        domain_scope=[request.domain] if request.domain else [],
        grant_id=grant.grant_id,
        request_id=request.request_id,
        evidence_refs=[*grant.evidence_refs, *request.evidence_refs],
        receipt_refs=[*grant.receipt_refs, *request.receipt_refs],
    )
    return _audit_receipt(
        request=request,
        grant=grant,
        decision=CredentialAccessDecision.ALLOWED_METADATA_ONLY,
        reasons=["credential_reference_allowed_metadata_only"],
        proof=proof,
    )


def validate_authority_credential_payload(
    payload: Any,
    *,
    source: str = "operator",
) -> AuthorityCredentialSafetyValidationResult:
    rejected_paths = _scan_forbidden_payload(payload)
    reasons: list[str] = []
    if rejected_paths:
        reasons.append("forbidden_authority_credential_payload")
    if source in {"memory", "receipt", "replay", "checkpoint"} and _contains_grant_creation(payload):
        reasons.append("source_cannot_create_credential_grant")
    sanitized = _sanitize_for_hash(payload)
    return AuthorityCredentialSafetyValidationResult(
        valid=not reasons,
        reasons=reasons,
        rejected_paths=rejected_paths,
        payload_hash=_stable_hash(sanitized),
    )


def validate_credential_proof_for_finalgate(
    *,
    proof: CredentialAccessProof | dict[str, Any] | None,
    mission_id: str,
    expected_credential_ref_id: str | None = None,
) -> AuthorityCredentialSafetyValidationResult:
    if proof is None:
        return AuthorityCredentialSafetyValidationResult(
            valid=False,
            reasons=["credential_proof_missing"],
            rejected_paths=["$.proof"],
        )
    try:
        normalized = proof if isinstance(proof, CredentialAccessProof) else CredentialAccessProof.model_validate(proof)
    except Exception:
        return AuthorityCredentialSafetyValidationResult(
            valid=False,
            reasons=["credential_proof_invalid"],
            rejected_paths=["$.proof"],
        )
    reasons: list[str] = []
    if normalized.mission_id != mission_id:
        reasons.append("credential_proof_mission_mismatch")
    if expected_credential_ref_id is not None and normalized.credential_ref_id != expected_credential_ref_id:
        reasons.append("credential_proof_ref_mismatch")
    return AuthorityCredentialSafetyValidationResult(
        valid=not reasons,
        reasons=reasons,
        payload_hash=_stable_hash(normalized.model_dump(mode="json")),
    )


def _audit_receipt(
    *,
    request: CredentialAccessRequest,
    grant: CredentialGrant | None,
    decision: CredentialAccessDecision,
    reasons: list[str],
    proof: CredentialAccessProof | None = None,
) -> CredentialAuditReceipt:
    return CredentialAuditReceipt(
        mission_id=request.mission_id,
        credential_ref_id=request.credential_ref_id,
        grant_id=grant.grant_id if grant is not None else None,
        decision=decision,
        proof=proof,
        reasons=reasons,
        evidence_refs=[*(grant.evidence_refs if grant is not None else []), *request.evidence_refs],
        receipt_refs=[*(grant.receipt_refs if grant is not None else []), *request.receipt_refs],
    )


def _scope_matches(*, request: CredentialAccessRequest, grant: CredentialGrant) -> bool:
    if request.organ_kind not in set(grant.allowed_organs):
        return False
    if request.action_level not in {str(level) for level in grant.allowed_action_levels}:
        return False
    if request.action not in set(grant.action_scope):
        return False
    if request.domain and grant.domain_scope and request.domain not in set(grant.domain_scope):
        return False
    return True


def _assert_no_authority_or_execution(model: Any) -> None:
    if getattr(model, "authority_effect", "none") != "none":
        raise ValueError("Credential authority foundation cannot grant authority.")
    if getattr(model, "execution_effect", "none") != "none":
        raise ValueError("Credential authority foundation cannot execute.")
    for field, message in {
        "can_grant_authority": "grant authority",
        "can_approve_execution": "approve execution",
        "can_approve_future_execution": "approve future execution",
        "can_create_delegated_lane": "create delegated lanes",
        "can_execute": "execute",
        "can_override_provider_model": "override provider/model",
    }.items():
        if bool(getattr(model, field, False)):
            raise ValueError(f"Credential authority foundation cannot {message}.")
    if getattr(model, "data_not_instruction", True) is not True:
        raise ValueError("Credential authority foundation data is not instruction.")


def _contains_grant_creation(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower()
            if normalized in {"credential_grants", "credentialgrant", "mission_authority_grants", "missionauthoritygrant"}:
                return True
            if _contains_grant_creation(value):
                return True
    if isinstance(payload, list | tuple | set):
        return any(_contains_grant_creation(value) for value in payload)
    return False


def _scan_forbidden_payload(payload: Any, path: str = "$") -> list[str]:
    rejected: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{key}"
            if normalized in _FORBIDDEN_KEYS and value not in (None, False, "", [], {}):
                rejected.append(child_path)
                continue
            rejected.extend(_scan_forbidden_payload(value, child_path))
        return rejected
    if isinstance(payload, list | tuple | set):
        for index, value in enumerate(payload):
            rejected.extend(_scan_forbidden_payload(value, f"{path}[{index}]"))
        return rejected
    if isinstance(payload, str) and _SECRET_LIKE_TEXT.search(payload):
        rejected.append(path)
    return rejected


def _sanitize_for_hash(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return _sanitize_for_hash(payload.model_dump(mode="json"))
    if isinstance(payload, dict):
        return {str(key): _sanitize_for_hash(value) for key, value in sorted(payload.items(), key=lambda item: str(item[0]))}
    if isinstance(payload, list | tuple | set):
        return [_sanitize_for_hash(value) for value in payload]
    if isinstance(payload, datetime):
        return payload.isoformat()
    return payload


def _stable_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "backend_override",
    "bearer",
    "browser_login",
    "browser_submit",
    "chain_of_thought",
    "credential_value",
    "direct_action",
    "execute_now",
    "model_override",
    "password",
    "payment",
    "provider_override",
    "raw_prompt",
    "raw_response",
    "reasoning",
    "secret",
    "secret_value",
    "send_email",
    "shell",
    "terminal",
    "thinking",
    "token",
    "tool_calls",
}

_SECRET_LIKE_TEXT = re.compile(
    r"(Bearer\s+[A-Za-z0-9_\-]{12,}|gsk_[A-Za-z0-9]+|nvapi-[A-Za-z0-9]+|sk-or-v1-[A-Za-z0-9]+|sk-[A-Za-z0-9]{16,})",
    re.IGNORECASE,
)
