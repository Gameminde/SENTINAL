from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.gate_sequence import GateSequence, GateVerdict
from sentinel.mission.models import MissionAction, MissionAuthorityEnvelope, MissionState
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus, utc_now
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized
from sentinel.telemetry import TelemetryCertificationError

SENSITIVE_SNAPSHOT_NAMES = frozenset(
    {
        ".codex",
        ".env",
        ".env.local",
        ".git",
        ".sentinel-runs",
        "credentials.json",
        "read_only_spine",
        "secrets.json",
    }
)
READ_ONLY_SAFE_EXCERPT_MAX_CHARS = 4_000


class ReadOnlyActionKind(StrEnum):
    LIST_DIRECTORY = "list_directory"
    READ_FILE_SEGMENT = "read_file_segment"
    FINISH_REPORT = "finish_report"


class ReadOnlyFailureCode(StrEnum):
    READ_TARGET_NOT_FOUND = "READ_TARGET_NOT_FOUND"
    READ_TARGET_WRONG_KIND = "READ_TARGET_WRONG_KIND"
    READ_SEGMENT_INVALID = "READ_SEGMENT_INVALID"
    READ_ACCESS_BLOCKED = "READ_ACCESS_BLOCKED"
    SNAPSHOT_CHANGED = "SNAPSHOT_CHANGED"
    READ_BACKEND_FAILURE = "READ_BACKEND_FAILURE"
    READ_INTERNAL_RUNTIME_FAILURE = "READ_INTERNAL_RUNTIME_FAILURE"
    BRIDGE_INTERNAL_FAILURE = "BRIDGE_INTERNAL_FAILURE"
    RECEIPT_PERSISTENCE_FAILED = "RECEIPT_PERSISTENCE_FAILED"
    FINALGATE_PERSISTENCE_FAILED = "FINALGATE_PERSISTENCE_FAILED"
    READ_MODEL_DECISION_TIMEOUT = "READ_MODEL_DECISION_TIMEOUT"
    READ_MODEL_DECISION_ERROR = "READ_MODEL_DECISION_ERROR"
    READ_DECISION_EXHAUSTED = "READ_DECISION_EXHAUSTED"
    READ_MAX_TURNS_EXHAUSTED = "READ_MAX_TURNS_EXHAUSTED"
    TERMINAL_REPORT_EMPTY = "TERMINAL_REPORT_EMPTY"
    TERMINAL_REPORT_UNSUPPORTED_ACTION_CLAIM = "TERMINAL_REPORT_UNSUPPORTED_ACTION_CLAIM"
    TERMINAL_REPORT_UNKNOWN_EVIDENCE_REF = "TERMINAL_REPORT_UNKNOWN_EVIDENCE_REF"
    RUNTIME_TERMINAL_BLOCKED = "RUNTIME_TERMINAL_BLOCKED"
    REPORT_EMPTY = "REPORT_EMPTY"
    REPORT_UNSAFE_CLAIM = "REPORT_UNSAFE_CLAIM"
    REPORT_UNKNOWN_EVIDENCE = "REPORT_UNKNOWN_EVIDENCE"
    RUNTIME_STOPPED = "RUNTIME_STOPPED"


class ReadOnlySpineError(RuntimeError):
    """Raised when the production-spine read-only session fails closed."""

    def __init__(
        self,
        failure_code: ReadOnlyFailureCode | str,
        *,
        phase: str = "unknown",
        exception_class: str | None = None,
        legacy_reason: str | None = None,
    ) -> None:
        code = failure_code.value if isinstance(failure_code, ReadOnlyFailureCode) else str(failure_code)
        self.failure_code = code
        self.phase = phase
        self.exception_class = exception_class
        self.legacy_reason = legacy_reason
        super().__init__(code)


class ReadOnlyDecision(SentinelModel):
    action: ReadOnlyActionKind
    arguments: dict[str, Any] = Field(default_factory=dict)
    operator_message: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_advisory(self) -> ReadOnlyDecision:
        assert_data_not_authority(
            context="read_only_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.arguments, context="read_only_decision")
        return self


class ReadOnlyDecisionClient:
    def __init__(self, decisions: list[ReadOnlyDecision]) -> None:
        self._decisions = list(decisions)
        self.call_count = 0

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        del context
        self.call_count += 1
        if not self._decisions:
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_DECISION_EXHAUSTED, phase="model_decision")
        return self._decisions.pop(0)


class ReadOnlyActionReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("readonly_receipt"))
    mission_id: str
    action: ReadOnlyActionKind
    status: str
    evidence_refs: list[str] = Field(default_factory=list)
    observation_hash: str | None = None
    blocked_reason: str | None = None
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_evidence_only(self) -> ReadOnlyActionReceipt:
        assert_data_not_authority(
            context="read_only_action_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.authority_effect != "none" or self.can_grant_authority:
            raise ValueError("read-only receipt cannot become future permission")
        return self

    def with_hash(self) -> ReadOnlyActionReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        return self.with_hash().receipt_hash == self.receipt_hash

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "action": self.action.value,
            "status": self.status,
            "evidence_refs": sanitize_operator_refs(self.evidence_refs),
            "observation_hash": self.observation_hash,
            "blocked_reason": redact_operator_text(self.blocked_reason or "") or None,
            "receipt_hash": self.receipt_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ReadOnlyFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("readonly_finalgate"))
    mission_id: str
    status: str
    accepted: bool
    receipt_refs: list[str] = Field(default_factory=list)
    reason: str
    certificate_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @property
    def id(self) -> str:
        return self.certificate_id

    @model_validator(mode="after")
    def _finalgate_is_evidence_only(self) -> ReadOnlyFinalGateCertificate:
        assert_data_not_authority(
            context="read_only_finalgate_certificate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.can_grant_authority:
            raise ValueError("read-only FinalGate cannot become future permission")
        return self

    def with_hash(self) -> ReadOnlyFinalGateCertificate:
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        return self.with_hash().certificate_hash == self.certificate_hash

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "mission_id": self.mission_id,
            "status": self.status,
            "accepted": self.accepted,
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "reason": redact_operator_text(self.reason),
            "certificate_hash": self.certificate_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ReadOnlyDecisionCheckpoint(SentinelModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("rochk"))
    mission_id: str
    run_id: str
    decision_hash: str
    canonical_action_name: str
    argument_key_names: list[str] = Field(default_factory=list)
    evidence_ref_count: int = 0
    safe_target_kind: str = "none"
    parser_status: str = "parsed"
    canonicalization_status: str = "canonicalized"
    runtime_phase: str = "post_parse_pre_gate"
    authority_reference_hash: str | None = None
    model_call_index: int = 0
    checkpoint_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _checkpoint_is_evidence_only(self) -> ReadOnlyDecisionCheckpoint:
        assert_data_not_authority(
            context="read_only_decision_checkpoint",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def with_hash(self) -> ReadOnlyDecisionCheckpoint:
        payload = self.safe_model_dump()
        payload["checkpoint_hash"] = ""
        return self.model_copy(update={"checkpoint_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        return self.with_hash().checkpoint_hash == self.checkpoint_hash

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "decision_hash": self.decision_hash,
            "canonical_action_name": self.canonical_action_name,
            "argument_key_names": list(self.argument_key_names),
            "evidence_ref_count": self.evidence_ref_count,
            "safe_target_kind": self.safe_target_kind,
            "parser_status": self.parser_status,
            "canonicalization_status": self.canonicalization_status,
            "runtime_phase": self.runtime_phase,
            "authority_reference_hash": self.authority_reference_hash,
            "model_call_index": self.model_call_index,
            "checkpoint_hash": self.checkpoint_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ReadOnlyFailedAttemptEvidence(SentinelModel):
    attempt_id: str = Field(default_factory=lambda: new_id("rofail"))
    mission_id: str
    run_id: str
    decision_checkpoint_ref: str | None = None
    failure_code: str
    runtime_phase: str
    proof_kind: str = "failed_action_attempt"
    exception_class: str | None = None
    successful_action_receipt_ref: str | None = None
    attempt_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _failed_attempt_is_evidence_only(self) -> ReadOnlyFailedAttemptEvidence:
        assert_data_not_authority(
            context="read_only_failed_attempt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def with_hash(self) -> ReadOnlyFailedAttemptEvidence:
        payload = self.safe_model_dump()
        payload["attempt_hash"] = ""
        return self.model_copy(update={"attempt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        return self.with_hash().attempt_hash == self.attempt_hash

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "decision_checkpoint_ref": self.decision_checkpoint_ref,
            "failure_code": self.failure_code,
            "runtime_phase": self.runtime_phase,
            "proof_kind": self.proof_kind,
            "exception_class": self.exception_class,
            "successful_action_receipt_ref": self.successful_action_receipt_ref,
            "attempt_hash": self.attempt_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ReadOnlyEmergencyTerminalRecord(SentinelModel):
    emergency_id: str = Field(default_factory=lambda: new_id("roterm"))
    mission_id: str
    run_id: str
    status: str = "emergency_blocked"
    accepted: bool = False
    original_failure_code: str
    emergency_failure_code: str
    normal_finalgate_persistence_failed: bool = True
    emergency_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _emergency_terminal_is_evidence_only(self) -> ReadOnlyEmergencyTerminalRecord:
        assert_data_not_authority(
            context="read_only_emergency_terminal",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def with_hash(self) -> ReadOnlyEmergencyTerminalRecord:
        payload = self.safe_model_dump()
        payload["emergency_hash"] = ""
        return self.model_copy(update={"emergency_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        return self.with_hash().emergency_hash == self.emergency_hash

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "emergency_id": self.emergency_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "status": self.status,
            "accepted": self.accepted,
            "original_failure_code": self.original_failure_code,
            "emergency_failure_code": self.emergency_failure_code,
            "normal_finalgate_persistence_failed": self.normal_finalgate_persistence_failed,
            "emergency_hash": self.emergency_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ReadOnlyProductionSpineResult(SentinelModel):
    mission_id: str
    status: str
    bridge_status: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    finalgate_status: str | None = None
    blocked_reason: str | None = None


class ReadOnlyReplayView(SentinelModel):
    mission_id: str
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    receipt_count: int = 0
    finalgate_count: int = 0
    failed_attempt_count: int = 0
    emergency_terminal_count: int = 0
    model_calls_before_replay: int = 0
    model_calls_after_replay: int = 0
    tool_calls_before_replay: int = 0
    tool_calls_after_replay: int = 0
    receipt_writes_before_replay: int = 0
    receipt_writes_after_replay: int = 0
    failed_attempt_writes_before_replay: int = 0
    failed_attempt_writes_after_replay: int = 0
    finalgate_writes_before_replay: int = 0
    finalgate_writes_after_replay: int = 0
    emergency_terminal_writes_before_replay: int = 0
    emergency_terminal_writes_after_replay: int = 0
    event_count_before_replay: int = 0
    event_count_after_replay: int = 0
    mission_status_before_replay: str | None = None
    mission_status_after_replay: str | None = None
    reexecuted: bool = False


class ReadOnlyProductionSpineSession:
    def __init__(
        self,
        *,
        cockpit: LLMLiveOperatorCockpit,
        mission_id: str,
        snapshot_root: Path | str,
        decision_client: ReadOnlyDecisionClient,
        max_turns: int = 16,
        deadline_at: datetime | None = None,
        now_provider: Callable[[], datetime] = utc_now,
        excluded_paths: list[str | Path] | None = None,
    ) -> None:
        self.cockpit = cockpit
        self.kernel: MissionKernel = cockpit.kernel
        self.mission_id = mission_id
        self.run_id = new_id("readonly_run")
        self.snapshot_root = Path(snapshot_root).resolve()
        self.decision_client = decision_client
        self.max_turns = max_turns
        self.deadline_at = deadline_at
        self._now_provider = now_provider
        self._observations: list[dict[str, Any]] = []
        self._receipt_refs: list[str] = []
        self._finalgate_refs: list[str] = []
        self._last_finalgate: ReadOnlyFinalGateCertificate | None = None
        self._latest_decision_checkpoint_ref: str | None = None
        self._failed_attempt_refs: list[str] = []
        self._emergency_terminal_refs: list[str] = []
        self._active_envelope: MissionAuthorityEnvelope | None = None
        self.tool_call_count = 0
        self._evidence_ref_by_hash: dict[str, str] = {}
        self._excluded_roots = [
            self._resolve_excluded_path(path)
            for path in (excluded_paths or [])
        ]
        self._snapshot_fingerprint = self._calculate_snapshot_fingerprint()

    def run_via_agent_runtime(self, *, envelope: MissionAuthorityEnvelope) -> ReadOnlyProductionSpineResult:
        runtime = _ReadOnlyAgentRuntime(self)
        bridge_result = OperatorAgentRuntimeBridge(self.kernel, runtime=runtime).run(
            self.mission_id,
            envelope=envelope,
            user_input={
                "mode": "read_only_operator_production_spine",
                "snapshot_ref": text_hash(str(self.snapshot_root)),
            },
            update_mission_status=False,
        )
        if bridge_result.status != "completed":
            blocked_reason = bridge_result.blocked_reason
            if blocked_reason == "agentruntime_reported_failure" and runtime.last_result is not None:
                blocked_reason = runtime.last_result.blocked_reason or blocked_reason
            if runtime.last_result is not None:
                self._finalize_blocked_status_if_open()
                return runtime.last_result.model_copy(
                    update={
                        "bridge_status": bridge_result.status,
                        "blocked_reason": blocked_reason,
                        "receipt_refs": list(runtime.last_result.receipt_refs),
                        "finalgate_refs": list(runtime.last_result.finalgate_refs),
                        "finalgate_status": "rejected",
                    }
                )
            if blocked_reason == "agentruntime_bridge_failure":
                blocked = self._record_blocked(
                    ReadOnlySpineError(
                        ReadOnlyFailureCode.BRIDGE_INTERNAL_FAILURE,
                        phase="bridge_runtime",
                    )
                )
                return blocked.model_copy(update={"bridge_status": bridge_result.status})
            blocked = self._record_blocked(str(blocked_reason or "agentruntime_bridge_blocked"))
            return blocked.model_copy(update={"bridge_status": bridge_result.status})
        return ReadOnlyProductionSpineResult(
            mission_id=self.mission_id,
            status="completed",
            bridge_status=bridge_result.status,
            receipt_refs=list(bridge_result.receipt_refs),
            finalgate_refs=list(bridge_result.finalgate_certificate_refs),
            finalgate_status="accepted",
        )

    def run(self) -> ReadOnlyProductionSpineResult:
        try:
            self._require_runtime_open()
            self.kernel.update_status(self.mission_id, OperatorMissionStatus.RUNNING, "Read-only spine session started.")
            self.kernel.store.append_event(
                self.mission_id,
                event_type="read_only_spine_session_started",
                safe_summary="Read-only production-spine session started.",
                metadata={"snapshot_hash": text_hash(str(self.snapshot_root))},
            )

            for _ in range(self.max_turns):
                self._require_runtime_open()
                try:
                    decision = self.decision_client.complete(self._context())
                except ReadOnlySpineError:
                    raise
                except TimeoutError as exc:
                    raise ReadOnlySpineError(
                        ReadOnlyFailureCode.READ_MODEL_DECISION_TIMEOUT,
                        phase="model_decision",
                        exception_class=exc.__class__.__name__,
                        legacy_reason="model_decision_timeout",
                    ) from exc
                except Exception as exc:  # noqa: BLE001
                    raise ReadOnlySpineError(
                        ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                        phase="model_decision",
                        exception_class=exc.__class__.__name__,
                        legacy_reason="model_decision_error",
                    ) from exc
                self._record_decision_checkpoint(decision)
                self._require_runtime_open()

                if decision.action is ReadOnlyActionKind.FINISH_REPORT:
                    self._validate_terminal_report(decision.operator_message or "", decision.evidence_refs)
                    try:
                        receipt = self._record_receipt(
                            action=decision.action,
                            status="success",
                            observation={"operator_message": decision.operator_message or ""},
                            evidence_refs=[obs["evidence_ref"] for obs in self._observations],
                        )
                    except Exception as exc:  # noqa: BLE001
                        raise ReadOnlySpineError(
                            ReadOnlyFailureCode.RECEIPT_PERSISTENCE_FAILED,
                            phase="receipt_persistence",
                            exception_class=exc.__class__.__name__,
                        ) from exc
                    try:
                        certificate = self._record_finalgate(
                            receipt_refs=[*self._receipt_refs, receipt.receipt_id],
                            status="accepted",
                            accepted=True,
                            reason="terminal_read_only_report_has_action_receipts",
                        )
                    except Exception as exc:  # noqa: BLE001
                        raise ReadOnlySpineError(
                            ReadOnlyFailureCode.FINALGATE_PERSISTENCE_FAILED,
                            phase="finalgate_persistence",
                            exception_class=exc.__class__.__name__,
                        ) from exc
                    self.kernel.update_status(
                        self.mission_id,
                        OperatorMissionStatus.COMPLETED,
                        "Read-only spine mission completed with terminal FinalGate.",
                    )
                    return ReadOnlyProductionSpineResult(
                        mission_id=self.mission_id,
                        status="completed",
                        receipt_refs=[*self._receipt_refs],
                        finalgate_refs=[certificate.certificate_id],
                        finalgate_status="accepted" if certificate.accepted else "rejected",
                    )

                observation = self._execute_read_only_action(decision)
                self._require_runtime_open()
                self._observations.append(observation)
                try:
                    self._record_receipt(
                        action=decision.action,
                        status="success",
                        observation=observation,
                        evidence_refs=[observation["evidence_ref"]],
                    )
                except Exception as exc:  # noqa: BLE001
                    raise ReadOnlySpineError(
                        ReadOnlyFailureCode.RECEIPT_PERSISTENCE_FAILED,
                        phase="receipt_persistence",
                        exception_class=exc.__class__.__name__,
                    ) from exc

            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_MAX_TURNS_EXHAUSTED, phase="turn_budget")
        except ReadOnlySpineError as exc:
            return self._record_blocked(exc, terminalize=self._active_envelope is None)
        except Exception as exc:  # noqa: BLE001
            return self._record_blocked(
                ReadOnlySpineError(
                    ReadOnlyFailureCode.READ_INTERNAL_RUNTIME_FAILURE,
                    phase="unexpected_runtime",
                    exception_class=exc.__class__.__name__,
                ),
                terminalize=self._active_envelope is None,
            )

    def _run_inside_bridge(self, _envelope: MissionAuthorityEnvelope) -> ReadOnlyProductionSpineResult:
        self._active_envelope = _envelope
        try:
            return self.run()
        finally:
            self._active_envelope = None

    def _load_last_finalgate(self, finalgate_refs: list[str]) -> ReadOnlyFinalGateCertificate | None:
        if not finalgate_refs:
            return None
        return self._last_finalgate

    def _finalize_blocked_status_if_open(self) -> None:
        if not self.kernel.is_terminal(self.mission_id):
            self.kernel.update_status(
                self.mission_id,
                OperatorMissionStatus.BLOCKED,
                "Read-only spine session blocked.",
            )

    def _record_blocked(
        self,
        error: ReadOnlySpineError | str,
        *,
        terminalize: bool = True,
    ) -> ReadOnlyProductionSpineResult:
        if isinstance(error, ReadOnlySpineError):
            reason = error.legacy_reason or error.failure_code
            phase = error.phase
            exception_class = error.exception_class
        else:
            reason = str(error)
            phase = "unknown"
            exception_class = None
        proof_code = _proof_failure_code(reason)
        if self._latest_decision_checkpoint_ref is not None:
            self._record_failed_attempt(
                proof_code,
                phase=_safe_runtime_phase(phase),
                proof_kind=_proof_kind(reason, phase),
                exception_class=exception_class,
            )
        finalgate_refs: list[str] = []
        try:
            certificate = self._record_finalgate(
                receipt_refs=[*self._receipt_refs],
                status="blocked",
                accepted=False,
                reason=reason,
            )
            finalgate_refs = [certificate.certificate_id]
        except Exception as exc:  # noqa: BLE001
            self._record_emergency_terminal(
                original_failure_code=proof_code,
                emergency_failure_code=ReadOnlyFailureCode.FINALGATE_PERSISTENCE_FAILED.value,
                exception_class=exc.__class__.__name__,
            )
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_blocked",
            safe_summary="Read-only production-spine session blocked before material action.",
            metadata={
                "blocked": True,
                "blocked_reason_hash": text_hash(reason),
                "typed_failure_code": proof_code,
                "runtime_phase": _safe_runtime_phase(phase),
                "exception_class": exception_class,
            },
            finalgate_certificate_refs=finalgate_refs,
        )
        if terminalize:
            self._finalize_blocked_status_if_open()
        return ReadOnlyProductionSpineResult(
            mission_id=self.mission_id,
            status="blocked",
            receipt_refs=[*self._receipt_refs],
            finalgate_refs=finalgate_refs,
            finalgate_status="rejected",
            blocked_reason=reason,
        )

    def _record_decision_checkpoint(self, decision: ReadOnlyDecision) -> ReadOnlyDecisionCheckpoint:
        argument_key_names = sorted(str(key) for key in decision.arguments)
        decision_hash = stable_hash(
            {
                "action": decision.action.value,
                "argument_key_names": argument_key_names,
                "evidence_ref_count": len(sanitize_operator_refs(decision.evidence_refs)),
                "operator_message_hash": text_hash(decision.operator_message or ""),
            }
        )
        authority_reference = self._active_envelope.id if self._active_envelope is not None else self.mission_id
        checkpoint = ReadOnlyDecisionCheckpoint(
            mission_id=self.mission_id,
            run_id=self.run_id,
            decision_hash=decision_hash,
            canonical_action_name=decision.action.value,
            argument_key_names=argument_key_names,
            evidence_ref_count=len(sanitize_operator_refs(decision.evidence_refs)),
            safe_target_kind=self._safe_target_kind(decision),
            authority_reference_hash=text_hash(authority_reference),
            model_call_index=self.decision_client.call_count,
        ).with_hash()
        self._write_artifact("decision_checkpoints", checkpoint.checkpoint_id, checkpoint.safe_model_dump())
        self._latest_decision_checkpoint_ref = checkpoint.checkpoint_id
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_decision_checkpointed",
            safe_summary="Read-only decision checkpoint recorded after parse and before Gate.",
            metadata={
                "checkpoint_hash": checkpoint.checkpoint_hash,
                "action": checkpoint.canonical_action_name,
                "runtime_phase": checkpoint.runtime_phase,
            },
        )
        return checkpoint

    def _record_failed_attempt(
        self,
        failure_code: str,
        *,
        phase: str,
        proof_kind: str = "failed_action_attempt",
        exception_class: str | None = None,
    ) -> ReadOnlyFailedAttemptEvidence:
        if self._failed_attempt_refs:
            return self._load_failed_attempt(self._failed_attempt_refs[-1])
        failed_attempt = ReadOnlyFailedAttemptEvidence(
            mission_id=self.mission_id,
            run_id=self.run_id,
            decision_checkpoint_ref=self._latest_decision_checkpoint_ref,
            failure_code=failure_code,
            runtime_phase=phase,
            proof_kind=proof_kind,
            exception_class=exception_class,
            successful_action_receipt_ref=None,
        ).with_hash()
        self._write_artifact("failed_attempts", failed_attempt.attempt_id, failed_attempt.safe_model_dump())
        self._failed_attempt_refs.append(failed_attempt.attempt_id)
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_failed_attempt_recorded",
            safe_summary="Read-only failed action-attempt evidence recorded.",
            metadata={
                "attempt_id": failed_attempt.attempt_id,
                "failure_code": failure_code,
                "runtime_phase": phase,
                "attempt_hash": failed_attempt.attempt_hash,
            },
        )
        return failed_attempt

    def _record_emergency_terminal(
        self,
        *,
        original_failure_code: str,
        emergency_failure_code: str,
        exception_class: str | None = None,
    ) -> ReadOnlyEmergencyTerminalRecord:
        emergency = ReadOnlyEmergencyTerminalRecord(
            mission_id=self.mission_id,
            run_id=self.run_id,
            original_failure_code=original_failure_code,
            emergency_failure_code=emergency_failure_code,
        ).with_hash()
        self._write_artifact("emergency_terminal", emergency.emergency_id, emergency.safe_model_dump())
        self._emergency_terminal_refs.append(emergency.emergency_id)
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_emergency_terminal_recorded",
            safe_summary="Read-only emergency terminal record persisted after FinalGate write failure.",
            metadata={
                "emergency_id": emergency.emergency_id,
                "original_failure_code": original_failure_code,
                "emergency_failure_code": emergency_failure_code,
                "exception_class": exception_class,
                "emergency_hash": emergency.emergency_hash,
            },
        )
        return emergency

    def build_replay(self) -> ReadOnlyReplayView:
        model_calls_before = self.decision_client.call_count
        tool_calls_before = self.tool_call_count
        event_count_before = len(self.kernel.store.load_events(self.mission_id))
        mission_status_before = self.kernel.store.load_record(self.mission_id).status.value
        receipt_writes_before = self._artifact_write_count("receipts")
        failed_attempt_writes_before = self._artifact_write_count("failed_attempts")
        finalgate_writes_before = self._artifact_write_count("finalgate")
        emergency_terminal_writes_before = self._artifact_write_count("emergency_terminal")
        events = self.kernel.store.load_events(self.mission_id)
        receipt_refs = _dedupe(
            ref
            for event in events
            if event.event_type == "read_only_spine_action_receipted"
            for ref in event.receipt_refs
        )
        failed_attempt_refs = _dedupe(
            str(event.metadata.get("attempt_id") or "")
            for event in events
            if event.event_type == "read_only_spine_failed_attempt_recorded"
        )
        failed_attempt_refs = [ref for ref in failed_attempt_refs if ref]
        finalgate_refs = _dedupe(
            ref
            for event in events
            if event.event_type == "read_only_spine_finalgate_certified"
            for ref in event.finalgate_certificate_refs
        )
        emergency_terminal_refs = _dedupe(
            str(event.metadata.get("emergency_id") or "")
            for event in events
            if event.event_type == "read_only_spine_emergency_terminal_recorded"
        )
        emergency_terminal_refs = [ref for ref in emergency_terminal_refs if ref]
        self._verify_replay_artifacts(
            receipt_refs=receipt_refs,
            finalgate_refs=finalgate_refs,
            failed_attempt_refs=failed_attempt_refs,
            emergency_terminal_refs=emergency_terminal_refs,
        )
        return ReadOnlyReplayView(
            mission_id=self.mission_id,
            receipt_refs=receipt_refs,
            finalgate_refs=finalgate_refs,
            receipt_count=len(receipt_refs),
            finalgate_count=len(finalgate_refs),
            failed_attempt_count=len(failed_attempt_refs),
            emergency_terminal_count=len(emergency_terminal_refs),
            model_calls_before_replay=model_calls_before,
            model_calls_after_replay=self.decision_client.call_count,
            tool_calls_before_replay=tool_calls_before,
            tool_calls_after_replay=self.tool_call_count,
            receipt_writes_before_replay=receipt_writes_before,
            receipt_writes_after_replay=self._artifact_write_count("receipts"),
            failed_attempt_writes_before_replay=failed_attempt_writes_before,
            failed_attempt_writes_after_replay=self._artifact_write_count("failed_attempts"),
            finalgate_writes_before_replay=finalgate_writes_before,
            finalgate_writes_after_replay=self._artifact_write_count("finalgate"),
            emergency_terminal_writes_before_replay=emergency_terminal_writes_before,
            emergency_terminal_writes_after_replay=self._artifact_write_count("emergency_terminal"),
            event_count_before_replay=event_count_before,
            event_count_after_replay=len(self.kernel.store.load_events(self.mission_id)),
            mission_status_before_replay=mission_status_before,
            mission_status_after_replay=self.kernel.store.load_record(self.mission_id).status.value,
            reexecuted=False,
        )

    def _context(self) -> dict[str, Any]:
        record = self.kernel.store.load_record(self.mission_id)
        return {
            "mission_id": self.mission_id,
            "status": record.status.value,
            "observations": list(self._observations),
            "receipt_refs": list(self._receipt_refs),
            "legal_actions": [item.value for item in ReadOnlyActionKind],
        }

    def _safe_target_kind(self, decision: ReadOnlyDecision) -> str:
        if decision.action is ReadOnlyActionKind.FINISH_REPORT:
            return "terminal_report"
        path_value = decision.arguments.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            return "none"
        if path_value == ".":
            return "snapshot_root"
        suffix = Path(path_value).suffix.lower().lstrip(".")
        if suffix:
            return f"file_extension:{suffix[:24]}"
        if path_value.endswith(("/", "\\")):
            return "directory_like"
        return "path_like"

    def _execute_read_only_action(self, decision: ReadOnlyDecision) -> dict[str, Any]:
        self._gate(decision)
        self.tool_call_count += 1
        try:
            if decision.action is ReadOnlyActionKind.LIST_DIRECTORY:
                path = self._resolve_path(str(decision.arguments.get("path", ".")))
                self._require_directory_target(path)
                entries = self._list_directory_entries(path)
                observation = {"path": self._relative(path), "entries": entries}
            elif decision.action is ReadOnlyActionKind.READ_FILE_SEGMENT:
                path = self._resolve_path(str(decision.arguments.get("path", "")))
                start_line = self._read_positive_int(decision.arguments.get("start_line", 1))
                line_count = self._read_positive_int(decision.arguments.get("line_count", 40))
                self._require_file_target(path)
                lines = self._read_file_lines(path)
                start_index = start_line - 1
                retained = lines[start_index : start_index + line_count]
                excerpt = redact_operator_text("\n".join(retained))
                truncated = len(excerpt) > READ_ONLY_SAFE_EXCERPT_MAX_CHARS
                safe_excerpt = excerpt[:READ_ONLY_SAFE_EXCERPT_MAX_CHARS]
                observation = {
                    "path": self._relative(path),
                    "start_line": start_line,
                    "line_count": len(retained),
                    "content_hash": text_hash("\n".join(retained)),
                    "safe_excerpt": safe_excerpt,
                    "safe_excerpt_char_count": len(safe_excerpt),
                    "safe_excerpt_truncated": truncated,
                }
            else:
                raise ReadOnlySpineError(
                    ReadOnlyFailureCode.READ_ACCESS_BLOCKED,
                    phase="action_validation",
                    legacy_reason=f"unsupported_read_only_action:{decision.action.value}",
                )
        except ReadOnlySpineError:
            raise
        except (OSError, UnicodeError) as exc:
            raise self._typed_backend_exception(exc) from exc
        except Exception as exc:  # noqa: BLE001
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_INTERNAL_RUNTIME_FAILURE,
                phase="tool_execution",
                exception_class=exc.__class__.__name__,
            ) from exc
        observation_hash = stable_hash(redact_operator_value(observation))
        existing_ref = self._evidence_ref_by_hash.get(observation_hash)
        evidence_ref = existing_ref or new_id("readonly_evidence")
        observation = {
            "evidence_ref": evidence_ref,
            "action": decision.action.value,
            "duplicate_evidence": existing_ref is not None,
            "evidence_content_hash": observation_hash,
            **observation,
        }
        if existing_ref is None:
            self._evidence_ref_by_hash[observation_hash] = evidence_ref
            self._write_artifact("evidence", evidence_ref, observation)
        return observation

    def _read_positive_int(self, value: object) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_SEGMENT_INVALID,
                phase="action_validation",
                exception_class=exc.__class__.__name__,
            ) from exc
        if parsed < 1:
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_SEGMENT_INVALID, phase="action_validation")
        return parsed

    def _require_directory_target(self, path: Path) -> None:
        if not path.exists():
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_TARGET_NOT_FOUND, phase="target_validation")
        if not path.is_dir():
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_TARGET_WRONG_KIND, phase="target_validation")

    def _require_file_target(self, path: Path) -> None:
        if not path.exists():
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_TARGET_NOT_FOUND, phase="target_validation")
        if not path.is_file():
            raise ReadOnlySpineError(ReadOnlyFailureCode.READ_TARGET_WRONG_KIND, phase="target_validation")

    def _list_directory_entries(self, path: Path) -> list[str]:
        return sorted(child.name for child in path.iterdir())

    def _read_file_lines(self, path: Path) -> list[str]:
        return path.read_text(encoding="utf-8").splitlines()

    def _typed_backend_exception(self, exc: OSError | UnicodeError) -> ReadOnlySpineError:
        if self._calculate_snapshot_fingerprint() != self._snapshot_fingerprint:
            return ReadOnlySpineError(
                ReadOnlyFailureCode.SNAPSHOT_CHANGED,
                phase="tool_execution",
                exception_class=exc.__class__.__name__,
            )
        return ReadOnlySpineError(
            ReadOnlyFailureCode.READ_BACKEND_FAILURE,
            phase="tool_execution",
            exception_class=exc.__class__.__name__,
        )

    def _gate(self, decision: ReadOnlyDecision) -> None:
        self._require_runtime_open()
        if self._active_envelope is not None:
            gate_result = GateSequence.default(
                project_root=self.snapshot_root,
                known_tools={"read_only_observation"},
            ).evaluate(
                _mission_action_from_decision(self.mission_id, decision),
                self._active_envelope,
                MissionState(mission_id=self.mission_id),
            )
            if gate_result.terminal_verdict is not GateVerdict.PASS:
                blocking = gate_result.blocking_gate
                gate_name = blocking.gate_name if blocking is not None else "unknown"
                raise ReadOnlySpineError(f"gate_sequence:{gate_name}:{gate_result.terminal_verdict.value}")
        record = self.kernel.store.load_record(self.mission_id)
        allowed_actions = set(record.authority_summary.allowed_actions if record.authority_summary else [])
        forbidden_actions = set(record.authority_summary.forbidden_actions if record.authority_summary else [])
        if decision.action.value in forbidden_actions:
            raise ReadOnlySpineError(f"read_only_action_forbidden:{decision.action.value}")
        if decision.action.value not in allowed_actions:
            raise ReadOnlySpineError(f"read_only_action_outside_authority:{decision.action.value}")
        if decision.action is ReadOnlyActionKind.READ_FILE_SEGMENT and "path" not in decision.arguments:
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_SEGMENT_INVALID,
                phase="action_validation",
                legacy_reason="read_file_segment_path_required",
            )

    def _record_receipt(
        self,
        *,
        action: ReadOnlyActionKind,
        status: str,
        observation: dict[str, Any],
        evidence_refs: list[str],
    ) -> ReadOnlyActionReceipt:
        receipt = ReadOnlyActionReceipt(
            mission_id=self.mission_id,
            action=action,
            status=status,
            evidence_refs=evidence_refs,
            observation_hash=stable_hash(redact_operator_value(observation)),
        ).with_hash()
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._receipt_refs.append(receipt.receipt_id)
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_action_receipted",
            safe_summary=f"Read-only action {action.value} recorded with receipt.",
            metadata={
                "action": action.value,
                "status": status,
                "observation_hash": receipt.observation_hash,
                "evidence_refs": evidence_refs,
                "duplicate_evidence": bool(observation.get("duplicate_evidence", False)),
            },
            receipt_refs=[receipt.receipt_id],
        )
        return receipt

    def _validate_terminal_report(self, operator_message: str, evidence_refs: list[str]) -> None:
        if not operator_message.strip():
            raise ReadOnlySpineError("terminal_report_empty")
        scan = scan_forbidden_payload_categorized(
            {"operator_message": operator_message},
            path="$.terminal_report",
        )
        rejected = [
            *scan[OrganSafetyScanCategory.SECRET.value],
            *scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value],
            *scan[OrganSafetyScanCategory.EXTERNAL_ACTION.value],
            *scan[OrganSafetyScanCategory.CREDENTIAL_DANGEROUS.value],
            *scan[OrganSafetyScanCategory.UNSAFE_PAYLOAD.value],
        ]
        lowered = operator_message.lower()
        unsupported_action_claim = any(
            phrase in lowered
            for phrase in (
                "i wrote",
                "wrote ",
                "modified ",
                "deleted ",
                "sent ",
                "emailed",
                "paid ",
                "logged in",
            )
        )
        if rejected or unsupported_action_claim:
            raise ReadOnlySpineError("terminal_report_unsupported_action_claim")
        known_refs = {obs["evidence_ref"] for obs in self._observations}
        if any(ref not in known_refs for ref in evidence_refs):
            raise ReadOnlySpineError("terminal_report_unknown_evidence_ref")

    def _record_finalgate(
        self,
        *,
        receipt_refs: list[str],
        status: str,
        accepted: bool,
        reason: str,
    ) -> ReadOnlyFinalGateCertificate:
        certificate = ReadOnlyFinalGateCertificate(
            mission_id=self.mission_id,
            status=status,
            accepted=accepted,
            receipt_refs=receipt_refs,
            reason=reason,
        ).with_hash()
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._finalgate_refs.append(certificate.certificate_id)
        self._last_finalgate = certificate
        self.kernel.store.append_event(
            self.mission_id,
            event_type="read_only_spine_finalgate_certified",
            safe_summary="Read-only spine terminal FinalGate certificate recorded.",
            metadata={"accepted": certificate.accepted, "certificate_hash": certificate.certificate_hash},
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        return certificate

    def _artifact_root(self) -> Path:
        return self.kernel.store.mission_dir(self.mission_id, create=True) / "read_only_spine"

    def _write_artifact(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        self.kernel.store.atomic_write_json(self._artifact_root() / collection / f"{item_id}.json", payload)

    def _artifact_path(self, collection: str, item_id: str) -> Path:
        return self._artifact_root() / collection / f"{item_id}.json"

    def _artifact_write_count(self, collection: str) -> int:
        root = self._artifact_root() / collection
        if not root.exists():
            return 0
        return len(list(root.glob("*.json")))

    def _verify_replay_artifacts(
        self,
        *,
        receipt_refs: list[str],
        finalgate_refs: list[str],
        failed_attempt_refs: list[str],
        emergency_terminal_refs: list[str],
    ) -> None:
        for receipt_ref in receipt_refs:
            receipt = self._load_receipt(receipt_ref)
            if receipt.mission_id != self.mission_id:
                raise ReadOnlySpineError("read_only_replay_receipt_mission_mismatch")
            if not receipt.verify_hash():
                raise ReadOnlySpineError("read_only_replay_receipt_hash_mismatch")
        for failed_attempt_ref in failed_attempt_refs:
            failed_attempt = self._load_failed_attempt(failed_attempt_ref)
            if failed_attempt.mission_id != self.mission_id:
                raise ReadOnlySpineError("read_only_replay_failed_attempt_mission_mismatch")
            if not failed_attempt.verify_hash():
                raise ReadOnlySpineError("read_only_replay_failed_attempt_hash_mismatch")
        for finalgate_ref in finalgate_refs:
            certificate = self._load_finalgate(finalgate_ref)
            if certificate.mission_id != self.mission_id:
                raise ReadOnlySpineError("read_only_replay_finalgate_mission_mismatch")
            if not certificate.verify_hash():
                raise ReadOnlySpineError("read_only_replay_finalgate_hash_mismatch")
        for emergency_terminal_ref in emergency_terminal_refs:
            emergency = self._load_emergency_terminal(emergency_terminal_ref)
            if emergency.mission_id != self.mission_id:
                raise ReadOnlySpineError("read_only_replay_emergency_terminal_mission_mismatch")
            if not emergency.verify_hash():
                raise ReadOnlySpineError("read_only_replay_emergency_terminal_hash_mismatch")

    def _load_receipt(self, receipt_ref: str) -> ReadOnlyActionReceipt:
        path = self._artifact_path("receipts", receipt_ref)
        if not path.exists():
            raise ReadOnlySpineError("read_only_replay_missing_receipt")
        return ReadOnlyActionReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _load_failed_attempt(self, failed_attempt_ref: str) -> ReadOnlyFailedAttemptEvidence:
        path = self._artifact_path("failed_attempts", failed_attempt_ref)
        if not path.exists():
            raise ReadOnlySpineError("read_only_replay_missing_failed_attempt")
        return ReadOnlyFailedAttemptEvidence.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _load_finalgate(self, finalgate_ref: str) -> ReadOnlyFinalGateCertificate:
        path = self._artifact_path("finalgate", finalgate_ref)
        if not path.exists():
            raise ReadOnlySpineError("read_only_replay_missing_finalgate")
        return ReadOnlyFinalGateCertificate.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _load_emergency_terminal(self, emergency_terminal_ref: str) -> ReadOnlyEmergencyTerminalRecord:
        path = self._artifact_path("emergency_terminal", emergency_terminal_ref)
        if not path.exists():
            raise ReadOnlySpineError("read_only_replay_missing_emergency_terminal")
        return ReadOnlyEmergencyTerminalRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _require_unblocked(self) -> None:
        reason = self.kernel.terminal_block_reason(self.mission_id)
        if reason:
            raise ReadOnlySpineError(reason)

    def _require_runtime_open(self) -> None:
        self._require_unblocked()
        self._require_authority_active()
        self._require_deadline()
        self._require_certified_telemetry()
        self._require_snapshot_unchanged()

    def _require_authority_active(self) -> None:
        if self._active_envelope is None:
            return
        if self._active_envelope.revoked_at is not None:
            raise ReadOnlySpineError("mission_authority_envelope_inactive")
        if datetime.now(UTC) > self._active_envelope.resolved_expires_at():
            raise ReadOnlySpineError("mission_authority_envelope_inactive")

    def _require_deadline(self) -> None:
        if self.deadline_at is None:
            return
        if self._now_provider() > self.deadline_at:
            raise ReadOnlySpineError("deadline_exhausted")

    def _require_certified_telemetry(self) -> None:
        telemetry = self.kernel.telemetry_sink
        if telemetry is None or not hasattr(telemetry, "require_certified_mode"):
            raise ReadOnlySpineError("telemetry_certified_mode_required")
        try:
            telemetry.require_certified_mode()
        except TelemetryCertificationError as exc:
            raise ReadOnlySpineError("telemetry_certified_mode_required") from exc

    def _require_snapshot_unchanged(self) -> None:
        if self._calculate_snapshot_fingerprint() != self._snapshot_fingerprint:
            raise ReadOnlySpineError(ReadOnlyFailureCode.SNAPSHOT_CHANGED, phase="snapshot_validation")

    def _resolve_path(self, requested: str) -> Path:
        raw = Path(requested)
        if raw.is_absolute():
            raise ReadOnlySpineError("absolute_path_blocked")
        path = (self.snapshot_root / raw).resolve()
        if path != self.snapshot_root and self.snapshot_root not in path.parents:
            raise ReadOnlySpineError("snapshot_path_escape_blocked")
        self._reject_sensitive_or_excluded_path(path)
        return path

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.snapshot_root)).replace("\\", "/") if path != self.snapshot_root else "."

    def _resolve_excluded_path(self, requested: str | Path) -> Path:
        raw = Path(requested)
        if raw.is_absolute():
            raise ReadOnlySpineError("excluded_path_must_be_snapshot_relative")
        path = (self.snapshot_root / raw).resolve()
        if path != self.snapshot_root and self.snapshot_root not in path.parents:
            raise ReadOnlySpineError("excluded_path_escapes_snapshot")
        return path

    def _reject_sensitive_or_excluded_path(self, path: Path) -> None:
        relative_parts = {part.lower() for part in path.relative_to(self.snapshot_root).parts}
        if relative_parts & SENSITIVE_SNAPSHOT_NAMES:
            raise ReadOnlySpineError("snapshot_sensitive_path_blocked")
        for excluded_root in self._excluded_roots:
            if path == excluded_root or excluded_root in path.parents:
                raise ReadOnlySpineError("snapshot_excluded_path_blocked")

    def _calculate_snapshot_fingerprint(self) -> str:
        rows: list[str] = []
        for root, dirnames, filenames in os.walk(self.snapshot_root, followlinks=False):
            root_path = Path(root)
            dirnames[:] = [
                dirname
                for dirname in sorted(dirnames)
                if not self._is_sensitive_or_excluded_snapshot_entry(root_path / dirname)
            ]
            for dirname in dirnames:
                directory = root_path / dirname
                rel = directory.relative_to(self.snapshot_root).as_posix()
                if directory.is_symlink():
                    rows.append(f"L|{rel}|{os.readlink(directory)}")
                else:
                    rows.append(f"D|{rel}")
            for filename in sorted(filenames):
                file_path = root_path / filename
                if self._is_sensitive_or_excluded_snapshot_entry(file_path):
                    continue
                rel = file_path.relative_to(self.snapshot_root).as_posix()
                if file_path.is_symlink():
                    rows.append(f"L|{rel}|{os.readlink(file_path)}")
                    continue
                if file_path.is_file():
                    rows.append(f"F|{rel}|{stable_hash(file_path.read_bytes())}")
        return stable_hash(rows)

    def _is_sensitive_or_excluded_snapshot_entry(self, path: Path) -> bool:
        rel_parts = {part.lower() for part in path.relative_to(self.snapshot_root).parts}
        if rel_parts & SENSITIVE_SNAPSHOT_NAMES:
            return True
        resolved = path.resolve()
        return any(resolved == root or root in resolved.parents for root in self._excluded_roots)


class _ReadOnlyAgentRuntime:
    def __init__(self, session: ReadOnlyProductionSpineSession) -> None:
        self._session = session
        self.last_result: ReadOnlyProductionSpineResult | None = None

    def run(
        self,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        *,
        execution_event_sink: Any | None = None,
        execution_run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ) -> Any:
        del user_input
        event_bus = EventBus(
            envelope.id,
            execution_event_sink=execution_event_sink,
            execution_run_id=execution_run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
        )
        event_bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "Read-only operator runtime started.",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
        )
        try:
            result = self._session._run_inside_bridge(envelope)
        except Exception:
            event_bus.append(
                AgentEventType.AGENT_FAILED,
                "Read-only operator runtime failed.",
                phase_before=AgentPhase.INITIALIZED,
                phase_after=AgentPhase.FAILED,
            )
            raise
        self.last_result = result
        if result.status == "completed":
            terminal_event_type = AgentEventType.AGENT_COMPLETED
            terminal_phase = AgentPhase.COMPLETED
        else:
            terminal_event_type = AgentEventType.AGENT_BLOCKED
            terminal_phase = AgentPhase.BLOCKED
        event_bus.append(
            terminal_event_type,
            "Read-only operator runtime reached terminal state.",
            phase_before=AgentPhase.INITIALIZED,
            phase_after=terminal_phase,
            trace_refs=list(result.receipt_refs) + list(result.finalgate_refs),
        )
        finalgate = self._session._load_last_finalgate(result.finalgate_refs)
        return _ReadOnlyRuntimeResult(
            success=result.status == "completed",
            receipt_refs=result.receipt_refs,
            final_gate_certification=finalgate,
            memory_feedback_result=None,
            artifact_paths=[],
        )


class _ReadOnlyRuntimeResult:
    def __init__(
        self,
        *,
        success: bool,
        receipt_refs: list[str],
        final_gate_certification: ReadOnlyFinalGateCertificate | None,
        memory_feedback_result: Any | None,
        artifact_paths: list[str],
    ) -> None:
        self.success = success
        self.receipt_refs = receipt_refs
        self.final_gate_certification = final_gate_certification
        self.memory_feedback_result = memory_feedback_result
        self.artifact_paths = artifact_paths


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


_LEGACY_FAILURE_CODE_MAP = {
    "model_decision_error": ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR.value,
    "model_decision_timeout": ReadOnlyFailureCode.READ_MODEL_DECISION_TIMEOUT.value,
    "read_only_decision_exhausted": ReadOnlyFailureCode.READ_DECISION_EXHAUSTED.value,
    "read_only_max_turns_exhausted": ReadOnlyFailureCode.READ_MAX_TURNS_EXHAUSTED.value,
    "snapshot_drift_detected": ReadOnlyFailureCode.SNAPSHOT_CHANGED.value,
    "terminal_report_empty": ReadOnlyFailureCode.REPORT_EMPTY.value,
    "terminal_report_unsupported_action_claim": ReadOnlyFailureCode.REPORT_UNSAFE_CLAIM.value,
    "terminal_report_unknown_evidence_ref": ReadOnlyFailureCode.REPORT_UNKNOWN_EVIDENCE.value,
}


def _proof_failure_code(reason: str) -> str:
    if reason in {item.value for item in ReadOnlyFailureCode}:
        return reason
    if reason in _LEGACY_FAILURE_CODE_MAP:
        return _LEGACY_FAILURE_CODE_MAP[reason]
    if reason.startswith("operator_mission_terminal:"):
        return ReadOnlyFailureCode.RUNTIME_STOPPED.value
    if reason.startswith("gate_sequence:") or reason.startswith("read_only_action_"):
        return ReadOnlyFailureCode.READ_ACCESS_BLOCKED.value
    if reason.startswith("mission_authority_envelope_"):
        return ReadOnlyFailureCode.READ_ACCESS_BLOCKED.value
    return ReadOnlyFailureCode.READ_INTERNAL_RUNTIME_FAILURE.value


def _proof_kind(reason: str, phase: str) -> str:
    if reason.startswith("gate_sequence:"):
        return "gate_denial"
    if "gate" in phase.lower():
        return "gate_denial"
    if reason.startswith("terminal_report_"):
        return "terminal_report_rejection"
    if reason.startswith("mission_authority_envelope_"):
        return "authority_recheck_block"
    if reason.startswith("operator_mission_terminal:"):
        return "runtime_terminal_recheck"
    return "failed_action_attempt"


def _safe_runtime_phase(phase: str) -> str:
    return phase if phase.replace("_", "").isalnum() else "runtime_terminal"


def _mission_action_from_decision(mission_id: str, decision: ReadOnlyDecision) -> MissionAction:
    target = str(decision.arguments.get("path", ".")) if decision.arguments else "."
    return MissionAction(
        mission_id=mission_id,
        action_type=decision.action.value,
        tool="read_only_observation",
        intent=f"read-only {decision.action.value}",
        target=target,
        input=redact_operator_value(decision.arguments),
        expected_output="bounded read-only evidence",
    )
