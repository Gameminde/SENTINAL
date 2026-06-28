from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import utc_now
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class WorkspacePatchProposal(SentinelModel):
    proposal_id: str = Field(default_factory=lambda: new_id("workspace_patch_proposal"))
    mission_id: str
    target_path: str
    expected_base_hash: str
    before_hash: str
    patch_hash: str
    patch_kind: str = "exact_text_replace"
    declared_target_paths: tuple[str, ...] = Field(default_factory=tuple)
    proposal_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _proposal_is_data_only(self) -> "WorkspacePatchProposal":
        assert_data_not_authority(
            context="workspace_patch_proposal",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.proposal_hash:
            self.proposal_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "proposal_id": self.proposal_id,
            "mission_id": self.mission_id,
            "target_path": _safe_workspace_path(self.target_path),
            "expected_base_hash": self.expected_base_hash,
            "before_hash": self.before_hash,
            "patch_hash": self.patch_hash,
            "patch_kind": self.patch_kind,
            "declared_target_paths": [_safe_workspace_path(item) for item in self.declared_target_paths],
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["proposal_hash"] = self.proposal_hash
        return payload


class WorkspacePatchEvidence(SentinelModel):
    evidence_id: str = Field(default_factory=lambda: new_id("workspace_patch_evidence"))
    mission_id: str
    target_path: str
    before_hash: str
    after_hash: str
    patch_hash: str
    byte_delta: int
    line_delta: int
    evidence_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _evidence_is_data_only(self) -> "WorkspacePatchEvidence":
        assert_data_not_authority(
            context="workspace_patch_evidence",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.evidence_hash:
            self.evidence_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False)) == self.evidence_hash

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "evidence_id": self.evidence_id,
            "mission_id": self.mission_id,
            "target_path": _safe_workspace_path(self.target_path),
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "patch_hash": self.patch_hash,
            "byte_delta": self.byte_delta,
            "line_delta": self.line_delta,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["evidence_hash"] = self.evidence_hash
        return payload


class WorkspacePatchReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("workspace_patch_receipt"))
    mission_id: str
    target_path: str
    status: str
    before_hash: str
    after_hash: str
    patch_hash: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "WorkspacePatchReceipt":
        assert_data_not_authority(
            context="workspace_patch_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False)) == self.receipt_hash

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "target_path": _safe_workspace_path(self.target_path),
            "status": self.status,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "patch_hash": self.patch_hash,
            "evidence_refs": sanitize_operator_refs(self.evidence_refs),
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class WorkspacePatchCheckResult(SentinelModel):
    command_id: str
    args: tuple[str, ...] = Field(default_factory=tuple)
    exit_status: int
    duration_ms: int = Field(default=0, ge=0)
    stdout: str = ""
    stderr: str = ""
    cwd_hash: str | None = None


class WorkspacePatchVerificationReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("workspace_patch_verification"))
    mission_id: str
    command_id: str
    args: tuple[str, ...] = Field(default_factory=tuple)
    status: str
    exit_status: int
    duration_ms: int
    stdout_hash: str
    stderr_hash: str
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    result_hash: str = ""
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _verification_is_data_only(self) -> "WorkspacePatchVerificationReceipt":
        assert_data_not_authority(
            context="workspace_patch_verification_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
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
            "command_id": self.command_id,
            "args": [redact_operator_text(item) for item in self.args],
            "status": self.status,
            "exit_status": self.exit_status,
            "duration_ms": self.duration_ms,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "stdout_excerpt": redact_operator_text(self.stdout_excerpt[:240]),
            "stderr_excerpt": redact_operator_text(self.stderr_excerpt[:240]),
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


class WorkspacePatchFinalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("workspace_patch_finalgate"))
    mission_id: str
    status: str
    accepted: bool
    reason: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_data_only(self) -> "WorkspacePatchFinalCertificate":
        assert_data_not_authority(
            context="workspace_patch_final_certificate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.certificate_hash:
            self.certificate_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def verify_hash(self) -> bool:
        return stable_hash(self.safe_model_dump(include_hash=False)) == self.certificate_hash

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "certificate_id": self.certificate_id,
            "mission_id": self.mission_id,
            "status": self.status,
            "accepted": self.accepted,
            "reason": redact_operator_text(self.reason),
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "evidence_refs": sanitize_operator_refs(self.evidence_refs),
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


def _safe_workspace_path(value: str) -> str:
    text = value.replace("\\", "/").strip() or "."
    if text.startswith("/") or text.startswith("../") or "/../" in text or text == "..":
        return f"path_hash:{text_hash(text)}"
    return redact_operator_text(text[:240])


__all__ = [
    "WorkspacePatchCheckResult",
    "WorkspacePatchEvidence",
    "WorkspacePatchFinalCertificate",
    "WorkspacePatchProposal",
    "WorkspacePatchReceipt",
    "WorkspacePatchVerificationReceipt",
]
