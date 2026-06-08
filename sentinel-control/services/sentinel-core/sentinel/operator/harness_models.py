from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import (
    redact_operator_text,
    redact_operator_value,
    sanitize_operator_refs,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
)
from sentinel.telemetry.redaction import sanitize_telemetry_value


def harness_utc_now() -> datetime:
    return datetime.now(UTC)


class AmplificationHarnessConfig(SentinelModel):
    require_existing_mission: bool = True
    require_certified_telemetry: bool = True
    persist_raw_artifacts: bool = False
    persist_raw_tool_outputs: bool = False
    max_context_items: int = Field(default=24, ge=1, le=512)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _config_is_data_only(self) -> AmplificationHarnessConfig:
        _assert_harness_data_only(self, "amplification_harness_config")
        if self.persist_raw_artifacts or self.persist_raw_tool_outputs:
            raise ValueError("harness config cannot persist raw artifacts or tool outputs in V1")
        return self


class AmplificationSession(SentinelModel):
    session_id: str = Field(default_factory=lambda: new_id("harness_session"))
    mission_id: str
    parent_envelope_id: str
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    memory_context_refs: list[str] = Field(default_factory=list)
    state_refs: list[str] = Field(default_factory=list)
    status: str = "running"
    safe_summary: str = "Amplification harness session started."
    created_at: datetime = Field(default_factory=harness_utc_now)
    updated_at: datetime = Field(default_factory=harness_utc_now)
    session_hash: str = ""
    memory_is_authority: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _session_is_data_only(self) -> AmplificationSession:
        _assert_harness_data_only(self, "amplification_session")
        if self.memory_is_authority:
            raise ValueError("harness memory context cannot become authority")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.memory_context_refs = sanitize_operator_refs(self.memory_context_refs)
        self.state_refs = sanitize_operator_refs(self.state_refs)
        return self

    def with_hash(self) -> AmplificationSession:
        payload = self.safe_model_dump()
        payload["session_hash"] = ""
        return self.model_copy(update={"session_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["session_hash"]
        payload["session_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mission_id": self.mission_id,
            "parent_envelope_id": self.parent_envelope_id,
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "model_id": self.model_id,
            "memory_context_refs": self.memory_context_refs,
            "state_refs": self.state_refs,
            "status": self.status,
            "safe_summary": self.safe_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "session_hash": self.session_hash,
            "memory_is_authority": self.memory_is_authority,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class AmplificationStateRef(SentinelModel):
    state_ref: str = Field(default_factory=lambda: new_id("harness_state"))
    mission_id: str
    session_id: str
    ref_kind: str
    target_hash: str
    safe_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _state_ref_is_data_only(self) -> AmplificationStateRef:
        _assert_harness_data_only(self, "amplification_state_ref")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self


class ContentAddressedArtifact(SentinelModel):
    artifact_ref: str = Field(default_factory=lambda: new_id("harness_artifact"))
    mission_id: str
    logical_path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str = "text/plain"
    safe_excerpt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=harness_utc_now)
    artifact_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @classmethod
    def from_bytes(
        cls,
        *,
        mission_id: str,
        logical_path: str,
        content: bytes,
        media_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> ContentAddressedArtifact:
        text = content.decode("utf-8", errors="replace")
        return cls(
            mission_id=mission_id,
            logical_path=logical_path,
            sha256=stable_hash(text),
            size_bytes=len(content),
            media_type=media_type,
            safe_excerpt=redact_operator_text(text[:240]),
            metadata=metadata or {},
            evidence_refs=evidence_refs or [],
        ).with_hash()

    @model_validator(mode="after")
    def _artifact_is_data_only(self) -> ContentAddressedArtifact:
        _assert_harness_data_only(self, "content_addressed_artifact")
        self.logical_path = _safe_logical_path(self.logical_path)
        self.safe_excerpt = redact_operator_text(self.safe_excerpt)
        self.metadata = _sanitize_harness_payload(self.metadata, context="content_addressed_artifact")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self

    def with_hash(self) -> ContentAddressedArtifact:
        payload = self.safe_model_dump()
        payload["artifact_hash"] = ""
        return self.model_copy(update={"artifact_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["artifact_hash"]
        payload["artifact_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "artifact_ref": self.artifact_ref,
            "mission_id": self.mission_id,
            "logical_path": self.logical_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "safe_excerpt": self.safe_excerpt,
            "metadata": self.metadata,
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at.isoformat(),
            "artifact_hash": self.artifact_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class HashAnchoredEdit(SentinelModel):
    edit_id: str = Field(default_factory=lambda: new_id("harness_edit"))
    mission_id: str
    artifact_ref: str
    base_sha256: str
    expected_sha256: str
    safe_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _edit_is_data_only(self) -> HashAnchoredEdit:
        _assert_harness_data_only(self, "hash_anchored_edit")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self


class HashAnchoredPatch(HashAnchoredEdit):
    replacement_text: str = Field(exclude=True, repr=False)

    @property
    def replacement_text_hash(self) -> str:
        return stable_hash(self.replacement_text)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "edit_id": self.edit_id,
            "mission_id": self.mission_id,
            "artifact_ref": self.artifact_ref,
            "base_sha256": self.base_sha256,
            "expected_sha256": self.expected_sha256,
            "replacement_text_hash": self.replacement_text_hash,
            "safe_summary": self.safe_summary,
            "evidence_refs": self.evidence_refs,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class HashAnchoredEditVerification(SentinelModel):
    verification_id: str = Field(default_factory=lambda: new_id("harness_edit_verification"))
    mission_id: str
    session_id: str
    edit_id: str
    artifact_ref: str
    status: str
    before_sha256: str | None = None
    expected_sha256: str | None = None
    after_sha256: str | None = None
    reject_reason: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=harness_utc_now)
    verification_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _verification_is_data_only(self) -> HashAnchoredEditVerification:
        _assert_harness_data_only(self, "hash_anchored_edit_verification")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self

    def with_hash(self) -> HashAnchoredEditVerification:
        payload = self.safe_model_dump()
        payload["verification_hash"] = ""
        return self.model_copy(update={"verification_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["verification_hash"]
        payload["verification_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "edit_id": self.edit_id,
            "artifact_ref": self.artifact_ref,
            "status": self.status,
            "before_sha256": self.before_sha256,
            "expected_sha256": self.expected_sha256,
            "after_sha256": self.after_sha256,
            "reject_reason": self.reject_reason,
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at.isoformat(),
            "verification_hash": self.verification_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class AnalysisKernelConfig(SentinelModel):
    kernel_name: str
    input_refs: list[str] = Field(default_factory=list)
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_shell: bool = False
    allow_credentials: bool = False
    allow_provider_keys: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _kernel_config_is_data_only(self) -> AnalysisKernelConfig:
        _assert_harness_data_only(self, "analysis_kernel_config")
        self.kernel_name = redact_operator_text(self.kernel_name)
        self.input_refs = sanitize_operator_refs(self.input_refs)
        self.metadata = _sanitize_harness_payload(self.metadata, context="analysis_kernel_config")
        return self

    @property
    def requests_ambient_access(self) -> bool:
        return any(
            [
                self.allow_network,
                self.allow_filesystem,
                self.allow_shell,
                self.allow_credentials,
                self.allow_provider_keys,
            ]
        )


class AnalysisKernelSession(SentinelModel):
    kernel_session_id: str = Field(default_factory=lambda: new_id("harness_kernel"))
    mission_id: str
    session_id: str
    kernel_name: str
    input_refs: list[str] = Field(default_factory=list)
    status: str = "started"
    started_at: datetime = Field(default_factory=harness_utc_now)
    kernel_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _kernel_session_is_data_only(self) -> AnalysisKernelSession:
        _assert_harness_data_only(self, "analysis_kernel_session")
        self.kernel_name = redact_operator_text(self.kernel_name)
        self.input_refs = sanitize_operator_refs(self.input_refs)
        return self

    def with_hash(self) -> AnalysisKernelSession:
        payload = self.safe_model_dump()
        payload["kernel_hash"] = ""
        return self.model_copy(update={"kernel_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["kernel_hash"]
        payload["kernel_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "kernel_session_id": self.kernel_session_id,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "kernel_name": self.kernel_name,
            "input_refs": self.input_refs,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "kernel_hash": self.kernel_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class AnalysisKernelResult(SentinelModel):
    kernel_result_id: str = Field(default_factory=lambda: new_id("harness_kernel_result"))
    mission_id: str
    session_id: str
    kernel_session_id: str | None = None
    status: str
    safe_summary: str
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=harness_utc_now)
    result_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _kernel_result_is_data_only(self) -> AnalysisKernelResult:
        _assert_harness_data_only(self, "analysis_kernel_result")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.output = _sanitize_harness_payload(self.output, context="analysis_kernel_result")
        self.evidence_refs = sanitize_operator_refs([*self.evidence_refs, *self.output.get("evidence_refs", [])])
        return self

    def with_hash(self) -> AnalysisKernelResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "kernel_result_id": self.kernel_result_id,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "kernel_session_id": self.kernel_session_id,
            "status": self.status,
            "safe_summary": self.safe_summary,
            "output": self.output,
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at.isoformat(),
            "result_hash": self.result_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ToolOutputEnvelope(SentinelModel):
    tool_result_ref: str = Field(default_factory=lambda: new_id("harness_tool"))
    mission_id: str
    tool_name: str
    safe_summary: str
    raw_output_bytes: int = Field(ge=0)
    minimized_output: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    output_hash: str = ""
    raw_output_persisted: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _tool_output_is_data_only(self) -> ToolOutputEnvelope:
        _assert_harness_data_only(self, "tool_output_envelope")
        self.tool_name = redact_operator_text(self.tool_name)
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.minimized_output = _sanitize_harness_payload(self.minimized_output, context="tool_output_envelope")
        if _contains_authority_request(self.minimized_output):
            raise ValueError("harness output cannot request authority")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        if self.raw_output_persisted:
            raise ValueError("harness tool output cannot persist raw output in V1")
        return self

    def with_hash(self) -> ToolOutputEnvelope:
        payload = self.safe_model_dump()
        payload["output_hash"] = ""
        return self.model_copy(update={"output_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["output_hash"]
        payload["output_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "tool_result_ref": self.tool_result_ref,
            "mission_id": self.mission_id,
            "tool_name": self.tool_name,
            "safe_summary": self.safe_summary,
            "raw_output_bytes": self.raw_output_bytes,
            "minimized_output": self.minimized_output,
            "evidence_refs": self.evidence_refs,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "output_hash": self.output_hash,
            "raw_output_persisted": self.raw_output_persisted,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class MinimizedToolResult(ToolOutputEnvelope):
    minimized: bool = True
    persisted_output_bytes: int = 0

    def safe_model_dump(self) -> dict[str, Any]:
        payload = super().safe_model_dump()
        payload["minimized"] = self.minimized
        payload["persisted_output_bytes"] = self.persisted_output_bytes
        return payload


class EvidenceLinkedDiagnostic(SentinelModel):
    diagnostic_id: str = Field(default_factory=lambda: new_id("harness_diag"))
    mission_id: str
    source: str
    safe_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _diagnostic_is_data_only(self) -> EvidenceLinkedDiagnostic:
        _assert_harness_data_only(self, "evidence_linked_diagnostic")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        return self


class HarnessWorkerRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("harness_worker_request"))
    mission_id: str
    objective: str
    result_contract: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _worker_request_is_data_only(self) -> HarnessWorkerRequest:
        _assert_harness_data_only(self, "harness_worker_request")
        self.objective = redact_operator_text(self.objective)
        if _contains_provider_override(self.result_contract) or _contains_provider_override(self.metadata):
            raise ValueError("harness worker request cannot contain provider/backend/model override")
        self.result_contract = _sanitize_harness_payload(self.result_contract, context="harness_worker_request_contract")
        self.metadata = _sanitize_harness_payload(self.metadata, context="harness_worker_request")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self


class HarnessWorkerResult(SentinelModel):
    worker_result_ref: str = Field(default_factory=lambda: new_id("harness_worker_result"))
    request_id: str
    mission_id: str
    safe_summary: str
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    conflict_key: str | None = None
    child_authority_subset: bool = True
    minimized: bool = True
    result_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _worker_result_is_data_only(self) -> HarnessWorkerResult:
        _assert_harness_data_only(self, "harness_worker_result")
        if self.child_authority_subset is not True:
            raise ValueError("harness worker result must preserve child authority subset")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.output = _sanitize_harness_payload(self.output, context="harness_worker_result")
        if _contains_authority_request(self.output):
            raise ValueError("harness output cannot request authority")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self

    def with_hash(self) -> HarnessWorkerResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "worker_result_ref": self.worker_result_ref,
            "request_id": self.request_id,
            "mission_id": self.mission_id,
            "safe_summary": self.safe_summary,
            "output": self.output,
            "evidence_refs": self.evidence_refs,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "conflict_key": self.conflict_key,
            "child_authority_subset": self.child_authority_subset,
            "minimized": self.minimized,
            "result_hash": self.result_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class HarnessConflictRecord(SentinelModel):
    conflict_id: str = Field(default_factory=lambda: new_id("harness_conflict"))
    conflict_key: str
    result_refs: list[str]
    result_hashes: list[str]
    safe_summary: str
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _conflict_is_data_only(self) -> HarnessConflictRecord:
        _assert_harness_data_only(self, "harness_conflict_record")
        self.result_refs = sanitize_operator_refs(self.result_refs)
        self.result_hashes = sanitize_operator_refs(self.result_hashes)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class HarnessMergeDecision(SentinelModel):
    merge_decision_id: str = Field(default_factory=lambda: new_id("harness_merge"))
    mission_id: str
    session_id: str
    outcome: str
    reasons: list[str] = Field(default_factory=list)
    result_refs: list[str] = Field(default_factory=list)
    conflict_records: list[HarnessConflictRecord] = Field(default_factory=list)
    merge_success: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _merge_is_data_only(self) -> HarnessMergeDecision:
        _assert_harness_data_only(self, "harness_merge_decision")
        self.result_refs = sanitize_operator_refs(self.result_refs)
        self.reasons = [redact_operator_text(str(reason)) for reason in self.reasons]
        return self


class HarnessCompressionPolicy(SentinelModel):
    max_items: int = Field(default=8, ge=1, le=128)
    max_summary_chars: int = Field(default=480, ge=16, le=5000)
    preserve_required_refs: bool = True
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _policy_is_data_only(self) -> HarnessCompressionPolicy:
        _assert_harness_data_only(self, "harness_compression_policy")
        return self


class HarnessContextPack(SentinelModel):
    context_pack_id: str = Field(default_factory=lambda: new_id("harness_context"))
    mission_id: str
    session_id: str
    safe_goal: str
    safe_context_items: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    required_refs: list[str] = Field(default_factory=list)
    required_refs_preserved: list[str] = Field(default_factory=list)
    compressed: bool = False
    estimated_tokens_saved: int = Field(default=0, ge=0)
    context_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _context_pack_is_data_only(self) -> HarnessContextPack:
        _assert_harness_data_only(self, "harness_context_pack")
        self.safe_goal = redact_operator_text(self.safe_goal)
        self.safe_context_items = [redact_operator_text(str(item)) for item in self.safe_context_items]
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        self.required_refs = sanitize_operator_refs(self.required_refs)
        self.required_refs_preserved = sanitize_operator_refs(self.required_refs_preserved)
        return self

    def with_hash(self) -> HarnessContextPack:
        payload = self.safe_model_dump()
        payload["context_hash"] = ""
        return self.model_copy(update={"context_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["context_hash"]
        payload["context_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "context_pack_id": self.context_pack_id,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "safe_goal": self.safe_goal,
            "safe_context_items": self.safe_context_items,
            "evidence_refs": self.evidence_refs,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "required_refs": self.required_refs,
            "required_refs_preserved": self.required_refs_preserved,
            "compressed": self.compressed,
            "estimated_tokens_saved": self.estimated_tokens_saved,
            "context_hash": self.context_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class HarnessTelemetrySummary(SentinelModel):
    mission_id: str
    session_id: str
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    safe_summary: str
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _telemetry_summary_is_data_only(self) -> HarnessTelemetrySummary:
        _assert_harness_data_only(self, "harness_telemetry_summary")
        self.event_refs = sanitize_operator_refs(self.event_refs)
        self.metric_refs = sanitize_operator_refs(self.metric_refs)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class HarnessReplayView(SentinelModel):
    mission_id: str
    session_id: str
    session: AmplificationSession
    artifact_refs: list[str] = Field(default_factory=list)
    edit_refs: list[str] = Field(default_factory=list)
    kernel_result_refs: list[str] = Field(default_factory=list)
    tool_result_refs: list[str] = Field(default_factory=list)
    worker_result_refs: list[str] = Field(default_factory=list)
    merge_decision_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _replay_is_data_only(self) -> HarnessReplayView:
        _assert_harness_data_only(self, "harness_replay_view")
        if self.reexecuted_actions:
            raise ValueError("harness replay must not re-execute actions")
        return self


def _assert_harness_data_only(value: Any, context: str) -> None:
    assert_data_not_authority(
        context=context,
        authority_effect=getattr(value, "authority_effect", "none"),
        data_not_authority=getattr(value, "data_not_authority", False),
        can_grant_authority=getattr(value, "can_grant_authority", False),
        can_execute=getattr(value, "can_execute", False),
    )


def _sanitize_harness_payload(value: Any, *, context: str) -> Any:
    sanitized, _, _ = sanitize_telemetry_value(redact_operator_value(value), path=f"$.{context}")
    if _contains_authority_request(sanitized):
        raise ValueError("harness output cannot request authority")
    return sanitized


def _contains_authority_request(value: Any) -> bool:
    scan = scan_forbidden_payload_categorized(value, path="$.harness")
    return bool(
        scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value]
        or scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]
        or scan[OrganSafetyScanCategory.EXTERNAL_ACTION.value]
        or scan[OrganSafetyScanCategory.BROWSER_DANGEROUS.value]
        or scan[OrganSafetyScanCategory.CREDENTIAL_DANGEROUS.value]
        or _contains_control_key(value)
    )


def _contains_provider_override(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in {"provider", "provider_id", "backend", "backend_id", "model", "model_id"}:
                return True
            if _contains_provider_override(item):
                return True
    if isinstance(value, list | tuple | set):
        return any(_contains_provider_override(item) for item in value)
    return False


def _contains_control_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in {
                "authority_grant",
                "authority_expansion",
                "grant_authority",
                "can_execute",
                "execute",
                "organ_call",
                "direct_organ_call",
                "unlock_credentials",
                "credential_unlock",
                "provider_override",
                "backend_override",
                "model_override",
            }:
                return True
            if _contains_control_key(item):
                return True
    if isinstance(value, list | tuple | set):
        return any(_contains_control_key(item) for item in value)
    return False


def _safe_logical_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or ":" in normalized:
        raise ValueError("harness logical path escapes mission scope")
    return str(path)
