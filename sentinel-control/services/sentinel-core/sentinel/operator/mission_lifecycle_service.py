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
    DISPATCH_DECIDED = "dispatch_decided"
    DISPATCH_RUNNING = "dispatch_running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ORPHANED_PREPARED = "orphaned_prepared"


_EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT = "stop_after_first_material_receipt"
_EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE = "low_friction_read_only_power_mode"
_EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT = "model_led_read_only_autopilot"
_EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS = "max_material_receipts"
_EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS = "max_provider_decision_calls"
_EXECUTION_OPTION_GENERATE_READ_ONLY_MISSION_SUMMARY = "generate_read_only_mission_summary"
_EXECUTION_OPTION_WRITE_OPERATOR_MEMORY_CANDIDATE = "write_operator_memory_candidate"
_EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS = "provider_decision_timeout_seconds"
PROVIDER_DECISION_TIMEOUT_SECONDS_MIN = 5
PROVIDER_DECISION_TIMEOUT_SECONDS_MAX = 180
_SAFE_EXECUTION_OPTION_KEYS = frozenset(
    {
        _EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT,
        _EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE,
        _EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT,
        _EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS,
        _EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS,
        _EXECUTION_OPTION_GENERATE_READ_ONLY_MISSION_SUMMARY,
        _EXECUTION_OPTION_WRITE_OPERATOR_MEMORY_CANDIDATE,
        _EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS,
    }
)


class MissionExecutionRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("mission_exec_req"))
    mission_id: str
    capability_id: str
    operation: str
    parameter_hash: str
    workspace_ref: str
    model_contract_ref: str
    authority_envelope_ref: str
    execution_options: dict[str, Any] = Field(default_factory=dict)
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
        self.execution_options = _normalize_execution_options(self.execution_options)
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
            "execution_options": redact_operator_value(self.execution_options),
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
        execution_options: dict[str, Any] | None = None,
    ) -> MissionLifecycleCreateResult:
        reject_operator_control_payload(parameters, context="mission_execution_request_parameters")
        normalized_execution_options = _normalize_execution_options(execution_options or {})
        _validate_execution_options_for_route(
            normalized_execution_options,
            capability_id=capability_id,
            operation=operation,
        )
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
            execution_options=normalized_execution_options,
        ).with_hash()
        self._persist_execution_request(execution_request)
        self._persist_execution_request_parameters(execution_request, parameters)
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
                "execution_option_keys": sorted(normalized_execution_options),
                "execution_options_hash": stable_hash(redact_operator_value(normalized_execution_options)),
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
                    "execution_option_keys": sorted(normalized_execution_options),
                    "execution_options_hash": stable_hash(redact_operator_value(normalized_execution_options)),
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

    def load_execution_parameters(self, mission_id: str, request_id: str) -> dict[str, Any]:
        request = self.load_execution_request(mission_id, request_id)
        path = self._parameters_path(mission_id, request_id)
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        parameters = payload.get("parameters")
        if not isinstance(parameters, dict):
            raise ValueError("mission execution parameters payload invalid")
        if payload.get("parameter_hash") != request.parameter_hash:
            raise ValueError("mission execution parameters hash mismatch")
        if stable_hash(redact_operator_value(parameters)) != request.parameter_hash:
            raise ValueError("mission execution parameters hash mismatch")
        reject_operator_control_payload(parameters, context="mission_execution_request_parameters")
        return dict(parameters)

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
        closeout_statuses = [
            str(event.metadata.get("status") or "")
            for event in events
            if event.event_type == "mission_dispatch_closeout_persisted"
            and (
                event.metadata.get("execution_request_id") == request.request_id
                or event.metadata.get("request_id") == request.request_id
            )
        ]
        if "completed" in closeout_statuses:
            state = MissionExecutionRequestState.COMPLETED
        elif closeout_statuses or "mission_dispatch_failed" in event_types:
            state = MissionExecutionRequestState.BLOCKED
        elif "mission_dispatch_started" in event_types:
            state = MissionExecutionRequestState.DISPATCH_RUNNING
        elif "mission_dispatch_decision_persisted" in event_types:
            state = MissionExecutionRequestState.DISPATCH_DECIDED
        elif "mission_execution_request_claimed" in event_types:
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

    def _persist_execution_request_parameters(
        self,
        request: MissionExecutionRequest,
        parameters: dict[str, Any],
    ) -> None:
        safe_parameters = redact_operator_value(parameters)
        self.kernel.store.atomic_write_json(
            self._parameters_path(request.mission_id, request.request_id),
            {
                "request_id": request.request_id,
                "mission_id": request.mission_id,
                "parameter_hash": stable_hash(safe_parameters),
                "parameters": safe_parameters,
                "data_not_authority": True,
                "authority_effect": "none",
                "can_execute": False,
            },
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

    def _parameters_path(self, mission_id: str, request_id: str) -> Path:
        return (
            self.kernel.store.mission_dir(mission_id, create=True)
            / "execution_request_parameters"
            / f"{request_id}.json"
        )


def _normalize_execution_options(options: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(options, dict):
        raise ValueError("mission execution options must be a JSON object")
    unknown = sorted(str(key) for key in options if str(key) not in _SAFE_EXECUTION_OPTION_KEYS)
    if unknown:
        raise ValueError(f"mission execution options contain unsupported keys: {','.join(unknown)}")
    normalized: dict[str, Any] = {}
    if _EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT in options:
        value = options[_EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT]
        if not isinstance(value, bool):
            raise ValueError("stop_after_first_material_receipt must be boolean")
        normalized[_EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT] = value
    if _EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE in options:
        value = options[_EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE]
        if not isinstance(value, bool):
            raise ValueError("low_friction_read_only_power_mode must be boolean")
        normalized[_EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE] = value
    if _EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT in options:
        value = options[_EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT]
        if not isinstance(value, bool):
            raise ValueError("model_led_read_only_autopilot must be boolean")
        normalized[_EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT] = value
    if _EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS in options:
        normalized[_EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS] = _normalize_positive_execution_limit(
            options[_EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS],
            field_name=_EXECUTION_OPTION_MAX_MATERIAL_RECEIPTS,
        )
    if _EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS in options:
        normalized[_EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS] = _normalize_positive_execution_limit(
            options[_EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS],
            field_name=_EXECUTION_OPTION_MAX_PROVIDER_DECISION_CALLS,
        )
    if _EXECUTION_OPTION_GENERATE_READ_ONLY_MISSION_SUMMARY in options:
        value = options[_EXECUTION_OPTION_GENERATE_READ_ONLY_MISSION_SUMMARY]
        if not isinstance(value, bool):
            raise ValueError("generate_read_only_mission_summary must be boolean")
        normalized[_EXECUTION_OPTION_GENERATE_READ_ONLY_MISSION_SUMMARY] = value
    if _EXECUTION_OPTION_WRITE_OPERATOR_MEMORY_CANDIDATE in options:
        value = options[_EXECUTION_OPTION_WRITE_OPERATOR_MEMORY_CANDIDATE]
        if not isinstance(value, bool):
            raise ValueError("write_operator_memory_candidate must be boolean")
        normalized[_EXECUTION_OPTION_WRITE_OPERATOR_MEMORY_CANDIDATE] = value
    if _EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS in options:
        normalized[_EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS] = _normalize_bounded_execution_limit(
            options[_EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS],
            field_name=_EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS,
            minimum=PROVIDER_DECISION_TIMEOUT_SECONDS_MIN,
            maximum=PROVIDER_DECISION_TIMEOUT_SECONDS_MAX,
        )
    return normalized


def _normalize_positive_execution_limit(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if parsed < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return parsed


def _normalize_bounded_execution_limit(value: Any, *, field_name: str, minimum: int, maximum: int) -> int:
    parsed = _normalize_positive_execution_limit(value, field_name=field_name)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _validate_execution_options_for_route(
    options: dict[str, Any],
    *,
    capability_id: str,
    operation: str,
) -> None:
    read_only_route = capability_id == "read_only_research" and operation == "inspect_repository"
    if (
        _EXECUTION_OPTION_PROVIDER_DECISION_TIMEOUT_SECONDS in options
        and options.get(_EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT) is not True
    ):
        raise ValueError("provider_decision_timeout_seconds requires model_led_read_only_autopilot")
    if options.get(_EXECUTION_OPTION_MODEL_LED_READ_ONLY_AUTOPILOT) is True:
        if not read_only_route:
            raise ValueError("model_led_read_only_autopilot requires read_only_research inspect_repository route")
        if options.get(_EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT) is True:
            raise ValueError("model_led_read_only_autopilot cannot combine with first-receipt mode")
        if options.get(_EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE) is not True:
            raise ValueError("model_led_read_only_autopilot requires low_friction_read_only_power_mode")
        return
    if options.get(_EXECUTION_OPTION_LOW_FRICTION_READ_ONLY_POWER_MODE) is not True:
        return
    if (
        options.get(_EXECUTION_OPTION_STOP_AFTER_FIRST_RECEIPT) is not True
        or not read_only_route
    ):
        raise ValueError(
            "low_friction_read_only_power_mode requires read_only_research inspect_repository first-receipt mode"
        )


__all__ = [
    "MissionExecutionRequest",
    "MissionExecutionRequestState",
    "MissionExecutionRequestStateView",
    "MissionLifecycleCreateResult",
    "MissionLifecycleService",
]
