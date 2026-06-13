from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.credential_vault_models import (
    CredentialConsumerKind,
    CredentialConsumerRef,
    CredentialScopePolicy,
    CredentialUseRiskProfile,
    CredentialVaultConfig,
    CredentialVaultMaturity,
    HIGH_RISK_SECRET_KINDS,
    SecretAccessGrant,
    SecretAccessLease,
    SecretAccessLeaseState,
    SecretAccessRequest,
    SecretCheckoutResult,
    SecretCheckoutToken,
    SecretFinalGateCertificate,
    SecretFinalGateDecision,
    SecretKind,
    SecretLeakScanResult,
    SecretMetadata,
    SecretRevocationRecord,
    SecretSensitivity,
    SecretUseContext,
    SecretUsePolicy,
    SecretUseReceipt,
    SecretVersionState,
    VaultLockState,
    VaultOperatorApproval,
    VaultUnlockPolicy,
    VaultUnlockSession,
    build_material_envelope,
    build_secret_metadata,
    scan_payload_for_secret_leaks,
    vault_utc_now,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.store import MissionRunStore
from sentinel.shared.models import new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized
from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class CredentialVaultRuntimeError(ValueError):
    """Raised when credential vault behavior would violate Sentinel boundaries."""


class CredentialVaultStore:
    def __init__(self, mission_store: MissionRunStore) -> None:
        self._mission_store = mission_store

    def verify_timeline(self, mission_id: str) -> bool:
        return self._mission_store.verify_timeline(mission_id)

    def mission_dir(self, mission_id: str) -> Path:
        return self._mission_store.mission_dir(mission_id, create=True)

    def append_event(
        self,
        mission_id: str,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ) -> None:
        self._mission_store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=_safe_event_metadata(metadata or {}),
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
        )

    def write(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self._mission_store.atomic_write_json(self.item_path(mission_id, category, name), payload)

    def item_path(self, mission_id: str, category: str, name: str) -> Path:
        root = self.root(mission_id) / category
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{stable_hash({'credential_vault_item': name})[:24]}.json"

    def root(self, mission_id: str) -> Path:
        return self._mission_store.mission_dir(mission_id, create=True) / "credential_vault"


def _safe_event_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if str(key) in {"lease_id", "credential_lease_id"}:
            safe[f"{key}_hash"] = stable_hash(value)
            continue
        probe = {key: value}
        scan = scan_forbidden_payload_categorized(probe, path="$")
        if scan[OrganSafetyScanCategory.ALL.value]:
            safe[f"{key}_hash"] = stable_hash(value)
        else:
            safe[key] = value
    return safe


class CredentialVaultRuntime:
    """Sentinel-native credential metadata vault and scoped secret broker.

    V1 persists durable metadata and fake sealed refs only. It never persists or
    returns raw secret material.
    """

    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel
        self.store = CredentialVaultStore(kernel.store)
        self._lease_id_by_hash: dict[str, str] = {}

    def initialize_vault(self, *, mission_id: str, config: CredentialVaultConfig) -> CredentialVaultConfig:
        self.kernel.store.load_record(mission_id)
        config = config.with_hash()
        self.store.write(mission_id, "configs", config.vault_id, config.safe_model_dump())
        self.store.append_event(
            mission_id,
            "credential_vault_initialized",
            "Credential vault initialized with durable metadata and no raw secret persistence.",
            metadata={"vault_id": config.vault_id, "maturity": config.maturity.value, "config_hash": config.config_hash},
        )
        self._record_metric(mission_id, TelemetryMetricKind.CREDENTIAL_VAULT_SECRET_COUNT, len(self._load_all(mission_id, "secrets", SecretMetadata)), "Credential vault secret count sample.")
        return config

    def request_unlock(
        self,
        *,
        mission_id: str,
        policy: VaultUnlockPolicy,
        purpose: str,
        requested_by: str,
    ) -> VaultUnlockSession:
        config = self._load_config(mission_id)
        normalized = purpose.strip().lower().replace(" ", "_")
        if normalized not in policy.allowed_purposes:
            raise CredentialVaultRuntimeError("vault_unlock_purpose_not_allowed")
        now = vault_utc_now()
        session = VaultUnlockSession(
            mission_id=mission_id,
            vault_id=config.vault_id,
            purpose=normalized,
            state=VaultLockState.UNLOCK_REQUESTED,
            requested_by=requested_by,
            requested_at=now,
            expires_at=now + timedelta(seconds=policy.ttl_seconds),
        ).with_hash()
        self.store.write(mission_id, "unlock_sessions", session.unlock_session_id, session.safe_model_dump())
        self.store.append_event(
            mission_id,
            "credential_vault_unlock_requested",
            "Credential vault unlock requested as scoped operator-visible session.",
            metadata={"vault_id": config.vault_id, "unlock_session_id": session.unlock_session_id, "purpose": session.purpose},
        )
        return session

    def approve_unlock_session(
        self,
        *,
        mission_id: str,
        unlock_session_id: str,
        approval_source: str,
    ) -> VaultUnlockSession:
        session = self._load_one(mission_id, "unlock_sessions", unlock_session_id, VaultUnlockSession)
        approval = VaultOperatorApproval(unlock_session_id=unlock_session_id, approval_source=approval_source).with_hash()
        updated = session.model_copy(
            update={
                "state": VaultLockState.UNLOCKED_FOR_SESSION,
                "approved_at": approval.approved_at,
                "approval_ref": approval.approval_id,
                "session_hash": "",
            }
        ).with_hash()
        self.store.write(mission_id, "approvals", approval.approval_id, approval.safe_model_dump())
        self.store.write(mission_id, "unlock_sessions", updated.unlock_session_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "credential_vault_unlocked",
            "Credential vault unlock session approved; session remains scoped and temporary.",
            metadata={"unlock_session_id": updated.unlock_session_id, "approval_ref": approval.approval_id},
        )
        self._record_metric(mission_id, TelemetryMetricKind.CREDENTIAL_VAULT_UNLOCK_COUNT, 1, "Credential vault unlock count sample.")
        return updated

    def expire_unlock_session(
        self,
        *,
        mission_id: str,
        unlock_session_id: str,
        at_time: datetime | None = None,
    ) -> VaultUnlockSession:
        session = self._load_one(mission_id, "unlock_sessions", unlock_session_id, VaultUnlockSession)
        updated = session.model_copy(update={"state": VaultLockState.EXPIRED, "session_hash": ""}).with_hash()
        self.store.write(mission_id, "unlock_sessions", unlock_session_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "credential_vault_unlock_expired",
            "Credential vault unlock session expired.",
            metadata={"unlock_session_id": unlock_session_id, "at_time": (at_time or vault_utc_now()).isoformat()},
        )
        return updated

    def revoke_unlock_session(self, *, mission_id: str, unlock_session_id: str, reason: str) -> VaultUnlockSession:
        session = self._load_one(mission_id, "unlock_sessions", unlock_session_id, VaultUnlockSession)
        updated = session.model_copy(update={"state": VaultLockState.REVOKED, "revoked_at": vault_utc_now(), "session_hash": ""}).with_hash()
        self.store.write(mission_id, "unlock_sessions", unlock_session_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "credential_vault_locked",
            "Credential vault unlock session revoked.",
            metadata={"unlock_session_id": unlock_session_id, "reason_hash": stable_hash(reason)},
        )
        return updated

    def register_secret(
        self,
        *,
        mission_id: str,
        kind: SecretKind,
        label: str,
        scope_policy: CredentialScopePolicy,
        use_policy: SecretUsePolicy,
        sensitivity: SecretSensitivity,
        provenance: str,
        secret_material: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> SecretMetadata:
        config = self._load_config(mission_id)
        self._reject_secret_payload(metadata or {})
        material = build_material_envelope(secret_material, maturity=config.maturity)
        record = build_secret_metadata(
            vault_id=config.vault_id,
            mission_id=mission_id,
            kind=kind,
            label=label,
            sensitivity=sensitivity,
            provenance=provenance,
            scope_policy=scope_policy,
            use_policy=use_policy,
            material_envelope=material,
            expires_at=expires_at,
        )
        self.store.write(mission_id, "secrets", record.secret_id, record.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_registered",
            "Secret metadata registered with fake sealed material ref.",
            metadata={"secret_id": record.secret_id, "kind_hash": stable_hash(record.kind.value), "metadata_hash": record.metadata_hash},
        )
        self._record_metric(mission_id, TelemetryMetricKind.CREDENTIAL_VAULT_SECRET_COUNT, len(self._load_all(mission_id, "secrets", SecretMetadata)), "Credential vault secret count sample.")
        return record

    def request_secret_access(
        self,
        *,
        mission_id: str,
        secret_id: str,
        consumer_kind: CredentialConsumerKind,
        consumer_ref: str,
        purpose: str,
        requested_scope: list[str],
        envelope: MissionAuthorityEnvelope | None,
        unlock_session_id: str | None,
        context: SecretUseContext | None = None,
    ) -> SecretAccessGrant:
        metadata = self._load_secret(mission_id, secret_id)
        self._assert_secret_available(metadata)
        special_authority_kind_allowed = (
            metadata.kind in HIGH_RISK_SECRET_KINDS
            and metadata.use_policy.risk_profile is CredentialUseRiskProfile.SPECIAL_AUTHORITY
            and metadata.kind in set(metadata.use_policy.allowed_kinds)
        )
        if metadata.kind in HIGH_RISK_SECRET_KINDS and not special_authority_kind_allowed:
            raise CredentialVaultRuntimeError("secret_kind_blocked")
        if metadata.kind not in HIGH_RISK_SECRET_KINDS and metadata.kind in set(metadata.scope_policy.blocked_kinds):
            raise CredentialVaultRuntimeError("secret_kind_blocked")
        if purpose not in set(metadata.scope_policy.allowed_purposes) or purpose not in set(metadata.use_policy.allowed_purposes):
            raise CredentialVaultRuntimeError("purpose_not_allowed")
        if metadata.kind not in set(metadata.use_policy.allowed_kinds):
            raise CredentialVaultRuntimeError("secret_kind_not_allowed")
        if not set(requested_scope).issubset(set(metadata.scope_policy.allowed_scopes)):
            raise CredentialVaultRuntimeError("scope_not_allowed")
        if consumer_kind not in set(metadata.scope_policy.allowed_consumers):
            raise CredentialVaultRuntimeError("consumer_not_allowed")
        if metadata.scope_policy.allowed_consumer_refs and consumer_ref not in set(metadata.scope_policy.allowed_consumer_refs):
            raise CredentialVaultRuntimeError("consumer_not_allowed")
        self._assert_authority(mission_id, envelope, purpose=purpose)
        if metadata.use_policy.require_unlock_session:
            self._assert_unlock_session(mission_id, unlock_session_id, purpose=purpose)
        request = SecretAccessRequest(
            mission_id=mission_id,
            secret_id=secret_id,
            consumer=CredentialConsumerRef(consumer_kind=consumer_kind, consumer_ref=consumer_ref),
            purpose=purpose,
            requested_scope=requested_scope,
            unlock_session_id=unlock_session_id,
            context=context or SecretUseContext(),
        ).with_hash()
        grant = SecretAccessGrant(
            request_id=request.request_id,
            mission_id=mission_id,
            secret_id=secret_id,
            secret_handle=metadata.secret_handle,
            consumer=request.consumer,
            purpose=purpose,
            granted_scope=list(requested_scope),
            unlock_session_id=unlock_session_id,
            expires_at=vault_utc_now() + timedelta(seconds=metadata.use_policy.max_lease_seconds),
        ).with_hash()
        self.store.write(mission_id, "access_requests", request.request_id, request.safe_model_dump())
        self.store.write(mission_id, "grants", grant.grant_id, grant.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_access_requested",
            "Secret access requested through broker.",
            metadata={
                "secret_id": secret_id,
                "request_id": request.request_id,
                "consumer_kind_hash": stable_hash(consumer_kind.value),
                "purpose_hash": stable_hash(purpose),
            },
        )
        self.store.append_event(
            mission_id,
            "secret_access_granted",
            "Secret access granted as handle-only metadata; no raw secret exposed.",
            metadata={"secret_id": secret_id, "grant_id": grant.grant_id, "request_id": request.request_id},
        )
        self._record_metric(mission_id, TelemetryMetricKind.SECRET_ACCESS_REQUEST_COUNT, 1, "Secret access request count sample.")
        return grant

    def create_secret_lease(self, *, mission_id: str, grant_id: str, ttl_seconds: int) -> SecretAccessLease:
        grant = self._load_one(mission_id, "grants", grant_id, SecretAccessGrant)
        metadata = self._load_secret(mission_id, grant.secret_id)
        ttl = min(ttl_seconds, metadata.use_policy.max_lease_seconds)
        lease = SecretAccessLease(
            grant_id=grant_id,
            mission_id=mission_id,
            secret_id=grant.secret_id,
            secret_handle=grant.secret_handle,
            lease_ref_hash=stable_hash(new_lease_id := new_id("secret_lease")),
            lease_id=new_lease_id,
            expires_at=vault_utc_now() + timedelta(seconds=ttl),
        ).with_hash()
        self._lease_id_by_hash[lease.lease_ref_hash] = lease.lease_id
        self.store.write(mission_id, "leases", lease.lease_id, lease.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_lease_created",
            "Secret lease created for scoped final-consumer access.",
            metadata={"secret_id": lease.secret_id, "grant_id": grant_id, "lease_id": lease.lease_id},
        )
        self._record_metric(mission_id, TelemetryMetricKind.SECRET_LEASE_ACTIVE_COUNT, len(self._active_leases(mission_id)), "Secret active lease count sample.")
        return lease

    def expire_secret_lease(
        self,
        *,
        mission_id: str,
        lease_id: str,
        at_time: datetime | None = None,
    ) -> SecretAccessLease:
        lease = self._load_one(mission_id, "leases", lease_id, SecretAccessLease)
        updated = lease.model_copy(update={"state": SecretAccessLeaseState.EXPIRED, "lease_hash": ""}).with_hash()
        self.store.write(mission_id, "leases", lease_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_lease_expired",
            "Secret lease expired.",
            metadata={"lease_id": lease_id, "secret_id": lease.secret_id, "at_time": (at_time or vault_utc_now()).isoformat()},
        )
        return updated

    def invalidate_active_leases_after_kill(self, *, mission_id: str, reason: str) -> list[SecretAccessLease]:
        revoked: list[SecretAccessLease] = []
        for lease in self._load_all(mission_id, "leases", SecretAccessLease):
            if lease.state is not SecretAccessLeaseState.ACTIVE:
                continue
            updated = lease.model_copy(update={"state": SecretAccessLeaseState.REVOKED, "revoked_at": vault_utc_now(), "lease_hash": ""}).with_hash()
            self.store.write(mission_id, "leases", lease.lease_id, updated.safe_model_dump())
            revoked.append(updated)
            self.store.append_event(
                mission_id,
                "secret_lease_revoked",
                "Secret lease revoked after kill switch.",
                metadata={"lease_id": lease.lease_id, "secret_id": lease.secret_id, "reason_hash": stable_hash(reason)},
            )
        if revoked:
            self._record_metric(mission_id, TelemetryMetricKind.SECRET_LEASE_REVOCATION_COUNT, len(revoked), "Secret lease revocation count sample.")
        return revoked

    def checkout_secret(
        self,
        *,
        mission_id: str,
        lease_id: str,
        consumer_kind: CredentialConsumerKind,
        consumer_ref: str,
    ) -> SecretCheckoutResult:
        try:
            lease = self._load_one(mission_id, "leases", lease_id, SecretAccessLease)
        except FileNotFoundError as exc:
            raise CredentialVaultRuntimeError("secret_lease_required") from exc
        if not lease.is_active():
            raise CredentialVaultRuntimeError("secret_lease_not_active")
        grant = self._load_one(mission_id, "grants", lease.grant_id, SecretAccessGrant)
        if grant.consumer.consumer_kind is not consumer_kind or grant.consumer.consumer_ref != consumer_ref:
            raise CredentialVaultRuntimeError("consumer_not_allowed")
        token = SecretCheckoutToken(
            lease_id=lease_id,
            lease_ref_hash=stable_hash(lease_id),
            token_hash=stable_hash({"lease_id": lease_id, "mission_id": mission_id, "consumer_ref": consumer_ref}),
            expires_at=lease.expires_at,
        )
        result = SecretCheckoutResult(
            mission_id=mission_id,
            lease_id=lease_id,
            lease_ref_hash=stable_hash(lease_id),
            secret_handle=lease.secret_handle,
            checkout_token=token,
            consumer=CredentialConsumerRef(consumer_kind=consumer_kind, consumer_ref=consumer_ref),
        ).with_hash()
        self.store.write(mission_id, "checkouts", result.checkout_result_id, result.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_checkout_started",
            "Secret checkout started for final consumer as handle/token metadata only.",
            metadata={"lease_id": lease_id, "checkout_result_id": result.checkout_result_id},
        )
        self.store.append_event(
            mission_id,
            "secret_checkout_completed",
            "Secret checkout completed without raw secret materialization.",
            metadata={"lease_id": lease_id, "checkout_token_id": token.checkout_token_id},
        )
        self._record_metric(mission_id, TelemetryMetricKind.SECRET_CHECKOUT_COUNT, 1, "Secret checkout count sample.")
        return result

    def assert_lease_matches_scope(
        self,
        *,
        mission_id: str,
        lease_id: str,
        expected_purpose: str,
        expected_scope: list[str],
        expected_consumer_kind: CredentialConsumerKind,
        expected_consumer_ref: str,
    ) -> None:
        lease = self._load_one(mission_id, "leases", lease_id, SecretAccessLease)
        if not lease.verify_hash():
            raise CredentialVaultRuntimeError("secret_lease_hash_mismatch")
        if not lease.is_active():
            raise CredentialVaultRuntimeError("secret_lease_not_active")
        grant = self._load_one(mission_id, "grants", lease.grant_id, SecretAccessGrant)
        if not grant.verify_hash():
            raise CredentialVaultRuntimeError("secret_grant_hash_mismatch")
        if grant.secret_id != lease.secret_id:
            raise CredentialVaultRuntimeError("credential_lease_scope_mismatch")
        if grant.consumer.consumer_kind is not expected_consumer_kind or grant.consumer.consumer_ref != expected_consumer_ref:
            raise CredentialVaultRuntimeError("consumer_not_allowed")
        if grant.purpose != expected_purpose:
            raise CredentialVaultRuntimeError("credential_lease_scope_mismatch")
        if not set(expected_scope).issubset(set(grant.granted_scope)):
            raise CredentialVaultRuntimeError("credential_lease_scope_mismatch")
        metadata = self._load_secret(mission_id, lease.secret_id)
        if not set(expected_scope).issubset(set(metadata.scope_policy.allowed_scopes)):
            raise CredentialVaultRuntimeError("credential_lease_scope_mismatch")

    def record_secret_use(self, *, mission_id: str, checkout_token_id: str, status: str) -> SecretUseReceipt:
        checkout = next(
            (item for item in self._load_all(mission_id, "checkouts", SecretCheckoutResult) if item.checkout_token.checkout_token_id == checkout_token_id),
            None,
        )
        if checkout is None:
            raise CredentialVaultRuntimeError("secret_checkout_not_found")
        lease_id = checkout.lease_id or self._lease_id_by_hash.get(str(checkout.lease_ref_hash or ""))
        if not lease_id:
            raise CredentialVaultRuntimeError("secret_lease_required")
        lease = self._load_one(mission_id, "leases", lease_id, SecretAccessLease)
        grant = self._load_one(mission_id, "grants", lease.grant_id, SecretAccessGrant)
        metadata = self._load_secret(mission_id, lease.secret_id)
        receipt = SecretUseReceipt(
            mission_id=mission_id,
            secret_id=lease.secret_id,
            secret_kind=metadata.kind,
            consumer=checkout.consumer,
            purpose=grant.purpose,
            scope_hash=metadata.secret_handle.scope_hash,
            grant_id=grant.grant_id,
            lease_id=lease.lease_id,
            checkout_token_id=checkout_token_id,
            expiry=lease.expires_at,
            revocation_status="revoked" if lease.revoked_at else "active",
            policy_hash=metadata.use_policy.policy_hash,
            status=status,
            lease_ref_hash=stable_hash(lease.lease_id),
        ).with_hash()
        decision = SecretFinalGateDecision.USED if status == "used" else SecretFinalGateDecision.FAILED
        finalgate = SecretFinalGateCertificate(
            mission_id=mission_id,
            secret_id=lease.secret_id,
            decision=decision,
            passed=status == "used",
            receipt_ref=receipt.receipt_id,
            receipt_hash=receipt.receipt_hash,
            safe_summary=f"Secret FinalGate decision: {decision.value}.",
        ).with_hash()
        receipt = receipt.model_copy(update={"finalgate_certificate": finalgate})
        self.store.write(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self.store.write(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        updated_lease = lease.model_copy(update={"state": SecretAccessLeaseState.USED, "used_at": vault_utc_now(), "lease_hash": ""}).with_hash()
        self.store.write(mission_id, "leases", lease.lease_id, updated_lease.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_use_completed" if status == "used" else "secret_use_failed",
            "Secret use terminal decision recorded without secret material.",
            metadata={"secret_id": lease.secret_id, "lease_id": lease.lease_id, "status": status},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        return receipt

    def mark_secret_expired(self, *, mission_id: str, secret_id: str, at_time: datetime) -> SecretMetadata:
        metadata = self._load_secret(mission_id, secret_id)
        updated = metadata.model_copy(
            update={
                "expiry_policy": metadata.expiry_policy.model_copy(update={"expires_at": at_time}),
                "version": metadata.version.model_copy(update={"expires_at": at_time, "state": SecretVersionState.EXPIRED, "version_hash": ""}).with_hash(),
                "metadata_hash": "",
            }
        ).with_hash()
        self.store.write(mission_id, "secrets", secret_id, updated.safe_model_dump())
        return updated

    def revoke_secret(self, *, mission_id: str, secret_id: str, reason: str) -> SecretRevocationRecord:
        metadata = self._load_secret(mission_id, secret_id)
        revocation = SecretRevocationRecord(secret_id=secret_id, mission_id=mission_id, reason=reason).with_hash()
        updated = metadata.model_copy(
            update={
                "revoked_at": revocation.revoked_at,
                "revocation_ref": revocation.revocation_id,
                "version": metadata.version.model_copy(update={"state": SecretVersionState.REVOKED, "version_hash": ""}).with_hash(),
                "metadata_hash": "",
            }
        ).with_hash()
        self.store.write(mission_id, "revocations", revocation.revocation_id, revocation.safe_model_dump())
        self.store.write(mission_id, "secrets", secret_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_revoked",
            "Secret metadata revoked; future access fails closed.",
            metadata={"secret_id": secret_id, "revocation_id": revocation.revocation_id},
        )
        return revocation

    def mark_rotation_required(self, *, mission_id: str, secret_id: str, reason: str) -> SecretMetadata:
        metadata = self._load_secret(mission_id, secret_id)
        updated = metadata.model_copy(
            update={
                "rotation_policy": metadata.rotation_policy.model_copy(update={"rotation_required": True, "rotation_status": "rotation_required_metadata_only_v1"}),
                "version": metadata.version.model_copy(update={"state": SecretVersionState.ROTATION_REQUIRED, "version_hash": ""}).with_hash(),
                "metadata_hash": "",
            }
        ).with_hash()
        self.store.write(mission_id, "secrets", secret_id, updated.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_rotation_required",
            "Secret rotation marked required as metadata only.",
            metadata={"secret_id": secret_id, "reason_hash": stable_hash(reason)},
        )
        self._record_metric(mission_id, TelemetryMetricKind.SECRET_ROTATION_DUE_COUNT, 1, "Secret rotation due count sample.")
        return updated

    def scan_for_secret_leaks(self, *, mission_id: str, payload: Any) -> SecretLeakScanResult:
        result = scan_payload_for_secret_leaks(payload, mission_id=mission_id)
        self.store.write(mission_id, "leak_scans", result.scan_id, result.safe_model_dump())
        self.store.append_event(
            mission_id,
            "secret_leak_scan_completed",
            "Secret leak scan completed with redacted findings only.",
            metadata={"scan_id": result.scan_id, "finding_count": len(result.findings), "payload_hash": result.payload_hash},
        )
        self._record_metric(mission_id, TelemetryMetricKind.SECRET_LEAK_SCAN_FINDINGS_COUNT, len(result.findings), "Secret leak scan findings count sample.")
        return result

    def build_memory_summary(self, *, mission_id: str, secret_id: str) -> dict[str, Any]:
        metadata = self._load_secret(mission_id, secret_id)
        return {
            "mission_id": mission_id,
            "secret_id": secret_id,
            "kind": metadata.kind.value,
            "redacted_label": metadata.secret_ref.redacted_label,
            "scope_hash": metadata.secret_handle.scope_hash,
            "revocation_status": "revoked" if metadata.is_revoked else "active",
            "memory_is_authority": False,
        }

    def build_worker_context(self, *, mission_id: str, secret_id: str) -> dict[str, Any]:
        summary = self.build_memory_summary(mission_id=mission_id, secret_id=secret_id)
        summary.update({"worker_can_materialize_secret": False, "worker_result_can_be_authority": False})
        return summary

    def build_model_prompt_context(self, *, mission_id: str, secret_id: str) -> dict[str, Any]:
        summary = self.build_memory_summary(mission_id=mission_id, secret_id=secret_id)
        summary.update({"llm_sees_secret_material": False, "prompt_contains_secret_material": False})
        return summary

    def request_advisory_surface_secret_use(self, *, mission_id: str, secret_id: str, source: str, requested_action: str) -> None:
        self.kernel.store.load_record(mission_id)
        self._load_secret(mission_id, secret_id)
        blocked = {"voice", "desktop", "channel", "skill", "daemon", "scheduler", "memory", "llm"}
        if source in blocked:
            raise CredentialVaultRuntimeError("credential_advisory_surface_blocked")
        raise CredentialVaultRuntimeError("credential_surface_not_approved")

    def _assert_authority(self, mission_id: str, envelope: MissionAuthorityEnvelope | None, *, purpose: str) -> None:
        if envelope is None:
            raise CredentialVaultRuntimeError("mission_authority_required")
        if envelope.id != mission_id:
            raise CredentialVaultRuntimeError("mission_authority_mismatch")
        if envelope.revoked_at is not None:
            raise CredentialVaultRuntimeError("mission_authority_revoked")
        now = datetime.now(UTC)
        if envelope.expires_at is not None and envelope.expires_at <= now:
            raise CredentialVaultRuntimeError("mission_authority_expired")
        allowed_actions = set(envelope.allowed_actions)
        if "credential_use" not in allowed_actions or purpose not in allowed_actions:
            raise CredentialVaultRuntimeError("mission_authority_missing_credential_scope")
        allowed_tools = set(envelope.allowed_tools)
        if "secret_broker" not in allowed_tools:
            raise CredentialVaultRuntimeError("mission_authority_missing_secret_broker")
        self.kernel.store.load_record(mission_id)

    def _assert_unlock_session(self, mission_id: str, unlock_session_id: str | None, *, purpose: str) -> VaultUnlockSession:
        if not unlock_session_id:
            raise CredentialVaultRuntimeError("vault_unlock_session_required")
        session = self._load_one(mission_id, "unlock_sessions", unlock_session_id, VaultUnlockSession)
        if session.purpose != purpose:
            raise CredentialVaultRuntimeError("vault_unlock_purpose_mismatch")
        if not session.is_active():
            raise CredentialVaultRuntimeError("vault_unlock_session_not_active")
        return session

    def _assert_secret_available(self, metadata: SecretMetadata) -> None:
        if metadata.is_revoked:
            raise CredentialVaultRuntimeError("secret_revoked")
        if metadata.is_expired():
            raise CredentialVaultRuntimeError("secret_expired")

    def _active_leases(self, mission_id: str) -> list[SecretAccessLease]:
        return [lease for lease in self._load_all(mission_id, "leases", SecretAccessLease) if lease.is_active()]

    def _load_config(self, mission_id: str) -> CredentialVaultConfig:
        configs = self._load_all(mission_id, "configs", CredentialVaultConfig)
        if not configs:
            raise CredentialVaultRuntimeError("credential_vault_not_initialized")
        config = configs[0]
        if not config.verify_hash():
            raise CredentialVaultRuntimeError("credential_vault_config_hash_mismatch")
        return config

    def _load_secret(self, mission_id: str, secret_id: str) -> SecretMetadata:
        secret = self._load_one(mission_id, "secrets", secret_id, SecretMetadata)
        if not secret.verify_hash():
            raise CredentialVaultRuntimeError("secret_metadata_hash_mismatch")
        return secret

    def _load_one(self, mission_id: str, category: str, item_id: str, model: Any) -> Any:
        item = model.model_validate_json(self.store.item_path(mission_id, category, item_id).read_text(encoding="utf-8"))
        if category == "leases" and isinstance(item, SecretAccessLease):
            lease_ref_hash = stable_hash(item_id)
            self._lease_id_by_hash[lease_ref_hash] = item_id
            return item.model_copy(update={"lease_id": item_id, "lease_ref_hash": lease_ref_hash})
        return item

    def _load_all(self, mission_id: str, category: str, model: Any) -> list[Any]:
        path = self.store.root(mission_id) / category
        if not path.exists():
            return []
        items = [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
        if category == "leases":
            rendered: list[Any] = []
            for item in items:
                if isinstance(item, SecretAccessLease) and item.lease_ref_hash in self._lease_id_by_hash:
                    rendered.append(item.model_copy(update={"lease_id": self._lease_id_by_hash[item.lease_ref_hash]}))
                else:
                    rendered.append(item)
            return rendered
        return items

    def _reject_secret_payload(self, payload: dict[str, Any]) -> None:
        scan = scan_forbidden_payload_categorized(payload, path="$")
        if scan[OrganSafetyScanCategory.SECRET.value] or scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]:
            raise ValueError("raw secret or provider override blocked")

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = self.kernel.store.telemetry_sink
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.CREDENTIAL_VAULT,
                domain=TelemetryDomain.SAFETY,
                metric_kind=metric_kind,
                value=value,
                unit=unit,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
