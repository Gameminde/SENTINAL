from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.models import utc_now
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class CodeExecutionProfile(SentinelModel):
    profile_id: str
    executable: str
    fixed_args_prefix: tuple[str, ...] = Field(default_factory=tuple)
    allowed_arg_kinds: tuple[str, ...] = Field(default_factory=tuple)
    workspace_required: bool = True
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_stdout_bytes: int = Field(default=4096, ge=0, le=65536)
    max_stderr_bytes: int = Field(default=4096, ge=0, le=65536)
    network_allowed: bool = False
    writes_allowed: bool = False
    env_policy: str = "minimal/redacted"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _profile_is_data_not_authority(self) -> "CodeExecutionProfile":
        assert_data_not_authority(
            context="code_execution_profile",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.network_allowed:
            raise ValueError("code execution sandbox profiles may not enable network")
        return self


class CodeExecutionRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("code_exec_request"))
    mission_id: str
    profile_id: str
    args: tuple[str, ...] = Field(default_factory=tuple)
    workspace_ref: str
    args_hash: str = ""
    request_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _request_is_data_not_authority(self) -> "CodeExecutionRequest":
        assert_data_not_authority(
            context="code_execution_request",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.args_hash:
            self.args_hash = stable_hash(list(self.args))
        if not self.request_hash:
            self.request_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "request_id": self.request_id,
            "mission_id": self.mission_id,
            "profile_id": self.profile_id,
            "args_hash": self.args_hash,
            "workspace_ref": self.workspace_ref,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["request_hash"] = self.request_hash
        return payload


class CodeExecutionResult(SentinelModel):
    result_id: str = Field(default_factory=lambda: new_id("code_exec_result"))
    mission_id: str
    profile_id: str
    args_hash: str
    exit_code: int
    duration_ms: int = Field(ge=0)
    timed_out: bool = False
    stdout_hash: str
    stderr_hash: str
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    result_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _result_is_data_not_authority(self) -> "CodeExecutionResult":
        assert_data_not_authority(
            context="code_execution_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.result_hash:
            self.result_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "result_id": self.result_id,
            "mission_id": self.mission_id,
            "profile_id": self.profile_id,
            "args_hash": self.args_hash,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
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
        return payload


class CodeExecutionReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("code_exec_receipt"))
    mission_id: str
    request_ref: str
    result_ref: str
    profile_id: str
    args_hash: str
    workspace_ref: str
    status: str
    exit_code: int
    duration_ms: int
    stdout_hash: str
    stderr_hash: str
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    result_hash: str
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_not_authority(self) -> "CodeExecutionReceipt":
        assert_data_not_authority(
            context="code_execution_receipt",
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
            "request_ref": self.request_ref,
            "result_ref": self.result_ref,
            "profile_id": self.profile_id,
            "args_hash": self.args_hash,
            "workspace_ref": self.workspace_ref,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "stdout_excerpt": redact_operator_text(self.stdout_excerpt[:240]),
            "stderr_excerpt": redact_operator_text(self.stderr_excerpt[:240]),
            "result_hash": self.result_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class CodeExecutionFinalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("code_exec_finalgate"))
    mission_id: str
    status: str
    accepted: bool
    reason: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    result_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_data_not_authority(self) -> "CodeExecutionFinalCertificate":
        assert_data_not_authority(
            context="code_execution_final_certificate",
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
            "result_refs": sanitize_operator_refs(self.result_refs),
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


__all__ = [
    "CodeExecutionFinalCertificate",
    "CodeExecutionProfile",
    "CodeExecutionReceipt",
    "CodeExecutionRequest",
    "CodeExecutionResult",
]
