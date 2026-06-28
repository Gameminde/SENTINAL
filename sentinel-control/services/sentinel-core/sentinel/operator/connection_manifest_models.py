from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class ConnectionSurfaceStatus(StrEnum):
    PRODUCT_PROVEN = "product_proven"
    IMPLEMENTED = "implemented"
    IMPLEMENTED_NOT_DISPATCHABLE = "implemented_not_dispatchable"
    PARTIAL = "partial"
    PLANNED = "planned"
    EXPERIMENTAL = "experimental"
    BLOCKED = "blocked"


class ConnectionDirection(StrEnum):
    INTERNAL = "internal"
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"
    LOCAL = "local"


class ConnectionRiskClass(StrEnum):
    C0 = "C0_internal_metadata"
    C1 = "C1_local_read_only"
    C2 = "C2_external_read_only"
    C3 = "C3_outbound_dry_run_or_provider"
    C4 = "C4_controlled_external_action"
    C5 = "C5_high_risk_privileged_or_destructive"


_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
_FORBIDDEN_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "authorization",
    "api_key=",
    "token=",
    "secret=",
    "-----begin",
)
_FORBIDDEN_PROVIDER_PAYLOAD_MARKERS = (
    "raw_provider_payload",
    "raw_response",
    "raw_prompt",
    "raw_reasoning",
    "reasoning_content",
    "provider wrapper payload",
)


class ConnectionManifest(SentinelModel):
    connection_id: str
    surface_id: str
    surface_kind: str
    owner_module: str
    runtime_class_name: str | None = None
    adapter_id: str | None = None
    current_status: ConnectionSurfaceStatus
    production_reachable: bool = False
    product_dispatchable: bool = False
    direction: ConnectionDirection
    risk_class: ConnectionRiskClass
    data_types: tuple[str, ...] = Field(default_factory=tuple)
    credential_env_names: tuple[str, ...] = Field(default_factory=tuple)
    credential_required: bool = False
    authority_required: str
    capability_id: str | None = None
    operation: str | None = None
    can_read: bool = False
    can_write: bool = False
    can_send: bool = False
    can_execute: bool = False
    external_side_effects_possible: bool = False
    requires_gate: bool = False
    requires_finalgate: bool = False
    requires_receipts: bool = False
    requires_replay: bool = False
    requires_kill_or_revocation: bool = False
    prompt_injection_exposure: str
    secret_exfiltration_exposure: str
    receipt_schema_ref: str | None = None
    replay_schema_ref: str | None = None
    approval_policy_ref: str | None = None
    allowed_destinations_policy_ref: str | None = None
    status_reason: str
    missing_to_dispatchable: tuple[str, ...] = Field(default_factory=tuple)
    fallback_auto_allowed: bool = False
    provider_native_tools_allowed: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _manifest_is_data_only(self) -> "ConnectionManifest":
        if not self.connection_id.strip() or self.connection_id != self.connection_id.strip():
            raise ValueError("connection manifest id must be stable and trimmed")
        if not self.surface_id.strip() or self.surface_id != self.surface_id.strip():
            raise ValueError("connection manifest surface_id must be stable and trimmed")
        if not self.owner_module.strip():
            raise ValueError("connection manifest owner_module is required")
        if not self.authority_required.strip():
            raise ValueError("connection manifest authority_required is required")
        if self.authority_granting:
            raise ValueError("connection manifest cannot be authority granting")
        if self.registry_can_execute:
            raise ValueError("connection manifest registry cannot execute")
        if self.fallback_auto_allowed:
            raise ValueError("connection manifest fallback/AUTO cannot be enabled")
        if self.provider_native_tools_allowed:
            raise ValueError("connection manifest provider-native tools cannot be enabled")
        assert_data_not_authority(
            context="connection_manifest",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute or self.registry_can_execute,
        )
        self._validate_credentials()
        self._validate_safe_refs()
        self._validate_high_risk_lockout()
        self._validate_dispatchable_contract()
        self._reject_raw_provider_payload_markers()
        return self

    @property
    def manifest_hash(self) -> str:
        return stable_hash(self.model_dump(mode="json"))

    def safe_summary(self) -> dict[str, Any]:
        payload = {
            "connection_id": self.connection_id,
            "surface_id": self.surface_id,
            "surface_kind": self.surface_kind,
            "owner_module": self.owner_module,
            "runtime_class_name": self.runtime_class_name,
            "adapter_id": self.adapter_id,
            "current_status": self.current_status.value,
            "production_reachable": self.production_reachable,
            "product_dispatchable": self.product_dispatchable,
            "direction": self.direction.value,
            "risk_class": self.risk_class.value,
            "data_types": list(self.data_types),
            "credential_env_names": list(self.credential_env_names),
            "credential_env_name_hashes": [text_hash(name) for name in self.credential_env_names],
            "credential_required": self.credential_required,
            "authority_required": self.authority_required,
            "capability_id": self.capability_id,
            "operation": self.operation,
            "can_read": self.can_read,
            "can_write": self.can_write,
            "can_send": self.can_send,
            "can_execute": self.can_execute,
            "external_side_effects_possible": self.external_side_effects_possible,
            "requires_gate": self.requires_gate,
            "requires_finalgate": self.requires_finalgate,
            "requires_receipts": self.requires_receipts,
            "requires_replay": self.requires_replay,
            "requires_kill_or_revocation": self.requires_kill_or_revocation,
            "prompt_injection_exposure": self.prompt_injection_exposure,
            "secret_exfiltration_exposure": self.secret_exfiltration_exposure,
            "receipt_schema_ref": self.receipt_schema_ref,
            "replay_schema_ref": self.replay_schema_ref,
            "approval_policy_ref": self.approval_policy_ref,
            "allowed_destinations_policy_ref": self.allowed_destinations_policy_ref,
            "status_reason": self.status_reason,
            "missing_to_dispatchable": list(self.missing_to_dispatchable),
            "fallback_auto_allowed": self.fallback_auto_allowed,
            "provider_native_tools_allowed": self.provider_native_tools_allowed,
            "data_not_authority": self.data_not_authority,
            "authority_granting": self.authority_granting,
            "can_grant_authority": self.can_grant_authority,
            "registry_can_execute": self.registry_can_execute,
            "manifest_hash": self.manifest_hash,
        }
        payload["safe_export_hash"] = stable_hash(payload)
        return payload

    def _validate_credentials(self) -> None:
        for name in self.credential_env_names:
            lowered = name.lower()
            if not _ENV_NAME_RE.fullmatch(name):
                raise ValueError("connection manifest credential fields must contain env/config names only")
            if any(marker in lowered for marker in _FORBIDDEN_SECRET_MARKERS):
                raise ValueError("connection manifest credential fields cannot contain credential values")
            if "://" in name or "=" in name:
                raise ValueError("connection manifest credential fields cannot contain credential values")

    def _validate_safe_refs(self) -> None:
        refs = (
            self.receipt_schema_ref,
            self.replay_schema_ref,
            self.approval_policy_ref,
            self.allowed_destinations_policy_ref,
        )
        for ref in refs:
            if not ref:
                continue
            lowered = ref.lower()
            if "://" in ref:
                raise ValueError("connection manifest raw endpoint values are not allowed")
            if any(marker in lowered for marker in _FORBIDDEN_SECRET_MARKERS):
                raise ValueError("connection manifest refs cannot contain credential values")

    def _validate_high_risk_lockout(self) -> None:
        if self.risk_class not in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}:
            return
        if self.production_reachable or self.product_dispatchable or self.adapter_id is not None:
            raise ValueError("connection manifest high-risk surfaces must remain locked by default")

    def _validate_dispatchable_contract(self) -> None:
        if not self.product_dispatchable:
            return
        if not self.production_reachable:
            raise ValueError("connection manifest dispatchable surfaces must be production reachable")
        if not self.adapter_id:
            raise ValueError("connection manifest dispatchable surfaces require an adapter id")
        if not self.requires_gate or not self.requires_finalgate or not self.requires_receipts or not self.requires_replay:
            raise ValueError("connection manifest dispatchable surfaces require gate, finalgate, receipts, and replay")

    def _reject_raw_provider_payload_markers(self) -> None:
        values = [
            self.surface_id,
            self.surface_kind,
            self.owner_module,
            self.runtime_class_name or "",
            self.adapter_id or "",
            self.authority_required,
            self.capability_id or "",
            self.operation or "",
            self.prompt_injection_exposure,
            self.secret_exfiltration_exposure,
            self.receipt_schema_ref or "",
            self.replay_schema_ref or "",
            self.approval_policy_ref or "",
            self.allowed_destinations_policy_ref or "",
            self.status_reason,
            *self.data_types,
            *self.missing_to_dispatchable,
        ]
        for value in values:
            lowered = value.lower()
            if any(marker in lowered for marker in _FORBIDDEN_PROVIDER_PAYLOAD_MARKERS):
                raise ValueError("connection manifest cannot contain raw provider payload markers")


class ConnectionManifestValidationReport(SentinelModel):
    ok: bool
    manifest_count: int
    findings: tuple[str, ...] = Field(default_factory=tuple)


class RuntimeConnectionComparisonReport(SentinelModel):
    manifest_ids: tuple[str, ...]
    runtime_connection_ids: tuple[str, ...]
    missing_runtime_connection_profiles: tuple[str, ...]
    missing_manifests_for_runtime_connections: tuple[str, ...]


class ConnectionAdapterReadinessEntry(SentinelModel):
    connection_id: str
    runtime_exists: bool
    replay_exists: bool
    manifest_exists: bool
    runtime_connection_profile_exists: bool
    unified_execution_adapter_exists: bool
    runtime_host_registered: bool
    product_dispatchable: bool
    missing_to_dispatchable: tuple[str, ...] = Field(default_factory=tuple)


class ConnectionAdapterReadinessReport(SentinelModel):
    entries: tuple[ConnectionAdapterReadinessEntry, ...] = Field(default_factory=tuple)


__all__ = [
    "ConnectionAdapterReadinessEntry",
    "ConnectionAdapterReadinessReport",
    "ConnectionDirection",
    "ConnectionManifest",
    "ConnectionManifestValidationReport",
    "ConnectionRiskClass",
    "ConnectionSurfaceStatus",
    "RuntimeConnectionComparisonReport",
]
