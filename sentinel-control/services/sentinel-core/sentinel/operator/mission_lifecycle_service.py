from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.authority_issuer import (
    MissionAuthorityApprovalScope,
    IssuedMissionAuthority,
    MissionAuthorityEnvelopeIssuer,
    MissionAuthorityEnvelopeRecord,
    MissionAuthorityPolicy,
)
from sentinel.operator.daemon_runtime import MissionDaemonRuntime
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    MissionRecord,
)
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id


class MissionExecutionRequestState(StrEnum):
    PREPARED = "prepared"
    QUEUED = "queued"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ORPHANED_PREPARED = "orphaned_prepared"


class MissionExecutionRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("mission_exec_req"))
    mission_id: str
    capability_id: str
    operation: str
    parameter_hash: str
    workspace_ref: str
    model_contract_ref: str
    authority_envelope_ref: str
    prepared: bool = True
    request_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _request_is_data_only(self) -> "MissionExecutionRequest":
        assert_data_not_authority(
            context="mission_execution_request",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.capability_id.strip() or not self.operation.strip():
            raise ValueError("mission execution request requires capability and operation")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "mission_id": self.mission_id,
            "capability_id": redact_operator_text(self.capability_id),
            "operation": redact_operator_text(self.operation),
            "parameter_hash": self.parameter_hash,
            "workspace_ref": redact_operator_text(self.workspace_ref),
            "model_contract_ref": redact_operator_text(self.model_contract_ref),
            "authority_envelope_ref": self.authority_envelope_ref,
            "prepared": self.prepared,
            "request_hash": self.request_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "MissionExecutionRequest":
        payload = self.safe_model_dump()
        payload["request_hash"] = ""
        return self.model_copy(update={"request_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["request_hash"]
        payload["request_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class MissionLifecycleCreateResult(SentinelModel):
    record: MissionRecord
    authority: IssuedMissionAuthority
    authority_record: MissionAuthorityEnvelopeRecord
    execution_request: MissionExecutionRequest


class MissionExecutionRequestStateView(SentinelModel):
    request_id: str
    mission_id: str
    state: MissionExecutionRequestState
    event_refs: list[str] = Field(default_factory=list)
    safe_summary: str


class MissionLifecycleService:
    def __init__(
        self,
        kernel: MissionKernel,
        *,
        authority_issuer: MissionAuthorityEnvelopeIssuer | None = None,
        daemon_runtime: MissionDaemonRuntime | None = None,
    ) -> None:
        self.kernel = kernel
        self.authority_issuer = authority_issuer or MissionAuthorityEnvelopeIssuer(kernel)
        self.daemon_runtime = daemon_runtime

    def create_mission(
        self,
        *,
        session_id: str,
        draft: MissionDraft,
        authority_summary: MissionAuthoritySummary,
        approval_scope: MissionAuthorityApprovalScope,
        policy: MissionAuthorityPolicy,
        capability_id: str,
        operation: str,
        parameters: dict[str, Any],
        workspace_ref: str,
        model_contract_ref: str,
    ) -> MissionLifecycleCreateResult:
        reject_operator_control_payload(parameters, context="mission_execution_request_parameters")
        mission_id = new_id("mission")
        bound_summary = authority_summary.model_copy(update={"mission_id": mission_id})
        record = self.kernel.create_mission(
            mission_id=mission_id,
            session_id=session_id,
            draft=draft,
            authority_summary=bound_summary,
        )
        authority = self.authority_issuer.issue(record.mission_id, approval_scope=approval_scope, policy=policy)
        execution_request = MissionExecutionRequest(
            mission_id=record.mission_id,
            capability_id=capability_id,
            operation=operation,
            parameter_hash=stable_hash(redact_operator_value(parameters)),
            workspace_ref=workspace_ref,
            model_contract_ref=model_contract_ref,
            authority_envelope_ref=authority.record.envelope_id,
        ).with_hash()
        self._persist_execution_request(execution_request)
        self.kernel.store.append_event(
            record.mission_id,
            event_type="mission_execution_request_prepared",
            safe_summary="Mission execution request prepared before enqueue.",
            metadata={
                "request_id": execution_request.request_id,
                "capability_id": execution_request.capability_id,
                "operation": execution_request.operation,
                "parameter_hash": execution_request.parameter_hash,
                "authority_envelope_ref": execution_request.authority_envelope_ref,
                "request_hash": execution_request.request_hash,
            },
        )
        try:
            record = self.kernel.enqueue(
                record.mission_id,
                metadata={
                    "execution_request_id": execution_request.request_id,
                    "capability_id": execution_request.capability_id,
                    "operation": execution_request.operation,
                    "authority_envelope_ref": execution_request.authority_envelope_ref,
                    "request_hash": execution_request.request_hash,
                },
            )
        except Exception:
            self._record_enqueue_failed(record.mission_id, execution_request)
            raise
        if self.daemon_runtime is not None:
            self.daemon_runtime.enqueue(
                record.mission_id,
                safe_reason="Mission queued by lifecycle service after authority issuance.",
                metadata={
                    "execution_request_id": execution_request.request_id,
                    "capability_id": execution_request.capability_id,
                    "operation": execution_request.operation,
                    "authority_envelope_ref": execution_request.authority_envelope_ref,
                },
            )
        return MissionLifecycleCreateResult(
            record=record,
            authority=authority,
            authority_record=authority.record,
            execution_request=execution_request,
        )

    def load_execution_request(self, mission_id: str, request_id: str) -> MissionExecutionRequest:
        payload = json.loads(self._request_path(mission_id, request_id).read_text(encoding="utf-8"))
        request = MissionExecutionRequest.model_validate(payload)
        if not request.verify_hash():
            raise ValueError("mission execution request hash mismatch")
        return request

    def latest_execution_request(self, mission_id: str) -> MissionExecutionRequest:
        requests = self.list_execution_requests(mission_id)
        if not requests:
            raise ValueError("mission_execution_request_missing")
        return requests[-1]

    def list_execution_requests(self, mission_id: str) -> list[MissionExecutionRequest]:
        root = self._request_root(mission_id)
        if not root.exists():
            return []
        requests = [
            MissionExecutionRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(root.glob("*.json"))
        ]
        for request in requests:
            if not request.verify_hash():
                raise ValueError("mission execution request hash mismatch")
        return sorted(requests, key=lambda item: item.request_id)

    def mark_request_claimed(self, mission_id: str, request_id: str) -> MissionExecutionRequestStateView:
        request = self.load_execution_request(mission_id, request_id)
        event = self.kernel.store.append_event(
            mission_id,
            event_type="mission_execution_request_claimed",
            safe_summary="Mission execution request claimed after daemon lease claim.",
            metadata={
                "execution_request_id": request.request_id,
                "request_hash": request.request_hash,
            },
        )
        return self.derive_request_state(mission_id, request_id, extra_event_refs=[event.event_id])

    def derive_request_state(
        self,
        mission_id: str,
        request_id: str,
        *,
        extra_event_refs: list[str] | None = None,
    ) -> MissionExecutionRequestStateView:
        request = self.load_execution_request(mission_id, request_id)
        events = self.kernel.store.load_events(mission_id)
        event_refs = [
            event.event_id
            for event in events
            if event.metadata.get("execution_request_id") == request.request_id
            or event.metadata.get("request_id") == request.request_id
        ]
        if extra_event_refs:
            event_refs.extend(extra_event_refs)
        event_types = [
            event.event_type
            for event in events
            if event.metadata.get("execution_request_id") == request.request_id
            or event.metadata.get("request_id") == request.request_id
        ]
        if "mission_execution_request_claimed" in event_types:
            state = MissionExecutionRequestState.CLAIMED
        elif "mission_queued" in event_types:
            state = MissionExecutionRequestState.QUEUED
        elif (
            "mission_execution_request_enqueue_failed" in event_types
            or "mission_execution_request_reconciliation_orphaned" in event_types
        ):
            state = MissionExecutionRequestState.ORPHANED_PREPARED
        elif "mission_execution_request_prepared" in event_types:
            state = MissionExecutionRequestState.PREPARED
        else:
            state = MissionExecutionRequestState.PREPARED
        return MissionExecutionRequestStateView(
            request_id=request.request_id,
            mission_id=mission_id,
            state=state,
            event_refs=list(dict.fromkeys(event_refs)),
            safe_summary=f"Mission execution request state derived as {state.value}.",
        )

    def _persist_execution_request(self, request: MissionExecutionRequest) -> None:
        self.kernel.store.atomic_write_json(
            self._request_path(request.mission_id, request.request_id),
            request.safe_model_dump(),
        )

    def _record_enqueue_failed(self, mission_id: str, request: MissionExecutionRequest) -> None:
        self.kernel.store.append_event(
            mission_id,
            event_type="mission_execution_request_enqueue_failed",
            safe_summary="Mission execution request enqueue failed after request preparation.",
            metadata={
                "execution_request_id": request.request_id,
                "request_hash": request.request_hash,
                "failure_code": "mission_kernel_enqueue_failed",
            },
        )

    def _request_root(self, mission_id: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "execution_requests"

    def _request_path(self, mission_id: str, request_id: str) -> Path:
        return self._request_root(mission_id) / f"{request_id}.json"


__all__ = [
    "MissionExecutionRequest",
    "MissionExecutionRequestState",
    "MissionExecutionRequestStateView",
    "MissionLifecycleCreateResult",
    "MissionLifecycleService",
]
