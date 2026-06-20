from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any, Protocol

from pydantic import ConfigDict, Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class AgentExecutionEventKind(StrEnum):
    RUNTIME_STARTED = "runtime_started"
    PHASE_TRANSITION = "phase_transition"
    RUNTIME_COMPLETED = "runtime_completed"
    RUNTIME_BLOCKED = "runtime_blocked"
    RUNTIME_FAILED = "runtime_failed"
    RUNTIME_REVOKED = "runtime_revoked"
    RUNTIME_ESCALATED = "runtime_escalated"
    WORKER_STARTED = "worker_started"
    WORKER_COMPLETED = "worker_completed"
    ORGAN_DISPATCH_COMPLETED = "organ_dispatch_completed"
    ORGAN_DISPATCH_SKIPPED = "organ_dispatch_skipped"
    CONTROLLED_CAPABILITY_EXECUTED = "controlled_capability_executed"
    CONTROLLED_CAPABILITY_REJECTED = "controlled_capability_rejected"
    ARTIFACT_CAPTURED = "artifact_captured"
    ARTIFACT_CAPTURE_REJECTED = "artifact_capture_rejected"
    ACTION_ROUTED = "action_routed"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    ACTION_ESCALATED = "action_escalated"
    MISSION_RUNNER_COMPLETED = "mission_runner_completed"
    MISSION_RUNNER_FAILED = "mission_runner_failed"
    EVIDENCE_REFS_UPDATED = "evidence_refs_updated"
    RECEIPT_REFS_UPDATED = "receipt_refs_updated"


class ExecutionActivityOutcome(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CLOSED_UNKNOWN = "closed_unknown"


class RefVerificationStatus(StrEnum):
    UNVERIFIED_SOURCE_REFS = "unverified_source_refs"


class ExecutionEventSink(Protocol):
    def emit(self, event: "AgentExecutionEvent") -> None:
        """Persist or relay a safe execution event projection."""


_TERMINAL_KINDS = {
    AgentExecutionEventKind.RUNTIME_COMPLETED,
    AgentExecutionEventKind.RUNTIME_BLOCKED,
    AgentExecutionEventKind.RUNTIME_FAILED,
    AgentExecutionEventKind.RUNTIME_REVOKED,
    AgentExecutionEventKind.RUNTIME_ESCALATED,
}


class AgentExecutionEvent(SentinelModel):
    """Safe product-facing projection of an AgentRuntime source event.

    The projection intentionally excludes source payloads. AgentEvent payloads
    can contain local runtime detail, tool arguments, or model-facing context;
    Pack 2A exposes only correlation ids, phases, safe summaries, refs, and
    source hash anchors.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=lambda: new_id("agent_exec_event"))
    event_kind: AgentExecutionEventKind
    mission_id: str
    run_id: str
    execution_request_id: str | None = None
    bridge_call_id: str
    agent_run_id: str
    phase_before: str | None = None
    phase_after: str | None = None
    safe_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    capability_refs: list[str] = Field(default_factory=list)
    worker_refs: list[str] = Field(default_factory=list)
    organ_refs: list[str] = Field(default_factory=list)
    action_refs: list[str] = Field(default_factory=list)
    source_ledger: str = "agent_runtime_event_bus"
    source_event_id: str
    source_event_hash: str
    source_event_type: str
    source_sequence: int = Field(ge=0)
    source_logical_time: int = Field(ge=0)
    source_parent_event_id: str | None = None
    activity_kind: str
    activity_outcome: ExecutionActivityOutcome = ExecutionActivityOutcome.CLOSED_UNKNOWN
    ref_verification_status: RefVerificationStatus = RefVerificationStatus.UNVERIFIED_SOURCE_REFS
    event_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _hash_bound_safe_projection(self) -> "AgentExecutionEvent":
        if self.authority_effect != "none" or not self.data_not_authority or self.can_grant_authority or self.can_execute:
            raise ValueError("AgentExecutionEvent is data only and cannot grant authority or execute.")
        if self.activity_kind != self.event_kind.value:
            raise ValueError("AgentExecutionEvent activity kind must match event kind.")
        if not self.source_ledger or not _SAFE_REF_PATTERN.fullmatch(self.source_ledger):
            raise ValueError("AgentExecutionEvent source ledger is not safe.")
        if not self.source_event_type or not _SAFE_REF_PATTERN.fullmatch(self.source_event_type):
            raise ValueError("AgentExecutionEvent source event type is not safe.")
        if self.source_parent_event_id is not None and not _SAFE_REF_PATTERN.fullmatch(self.source_parent_event_id):
            raise ValueError("AgentExecutionEvent source parent ref is not safe.")
        expected = _hash_event_projection(self)
        if self.event_hash and self.event_hash != expected:
            raise ValueError("AgentExecutionEvent hash mismatch.")
        if not self.event_hash:
            object.__setattr__(self, "event_hash", expected)
        return self

    @property
    def terminal(self) -> bool:
        return self.event_kind in _TERMINAL_KINDS

    @property
    def critical(self) -> bool:
        return True

    @classmethod
    def from_agent_event(
        cls,
        agent_event: Any,
        *,
        run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ) -> "AgentExecutionEvent | None":
        event_kind = _kind_from_source_event(agent_event)
        if event_kind is None:
            return None
        trace_refs = [str(ref) for ref in getattr(agent_event, "trace_refs", ()) or ()]
        receipt_refs = _safe_prefixed_refs(trace_refs, "receipt:")
        artifact_refs = _safe_prefixed_refs(trace_refs, "artifact:")
        capability_refs = _safe_prefixed_refs(trace_refs, "capability:")
        worker_refs = _safe_prefixed_refs(trace_refs, "worker:")
        organ_refs = _safe_prefixed_refs(trace_refs, "organ:")
        action_refs = _safe_prefixed_refs(trace_refs, "action:")
        evidence_refs = _safe_refs(
            ref
            for ref in trace_refs
            if not ref.startswith(("receipt:", "artifact:", "capability:", "worker:", "organ:", "action:"))
        )
        phase_before = _validated_phase(getattr(agent_event, "phase_before", None))
        phase_after = _validated_phase(getattr(agent_event, "phase_after", None))
        source_event_type = str(_enum_value(getattr(agent_event, "event_type", "")) or "")
        activity_outcome = _activity_outcome_from_agent_event(event_kind, agent_event)
        return cls(
            event_kind=event_kind,
            mission_id=str(getattr(agent_event, "mission_id")),
            run_id=run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
            phase_before=phase_before,
            phase_after=phase_after,
            evidence_refs=evidence_refs,
            receipt_refs=receipt_refs,
            artifact_refs=artifact_refs,
            capability_refs=capability_refs,
            worker_refs=worker_refs,
            organ_refs=organ_refs,
            action_refs=action_refs,
            source_event_id=str(getattr(agent_event, "id")),
            source_event_hash=str(getattr(agent_event, "event_hash")),
            source_event_type=_safe_source_event_label(source_event_type),
            source_sequence=int(getattr(agent_event, "sequence")),
            source_logical_time=int(getattr(agent_event, "logical_time")),
            source_parent_event_id=getattr(agent_event, "parent_event_id", None),
            activity_kind=event_kind.value,
            activity_outcome=activity_outcome,
            safe_summary=_deterministic_summary(
                event_kind,
                phase_before=phase_before,
                phase_after=phase_after,
                activity_outcome=activity_outcome,
            ),
        )

    @classmethod
    def from_mission_trace_event(
        cls,
        mission_trace_event: Any,
        *,
        run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ) -> "AgentExecutionEvent | None":
        event_kind = _kind_from_mission_trace_event(mission_trace_event)
        if event_kind is None:
            return None
        source_event_type = str(_enum_value(getattr(mission_trace_event, "event_type", "")) or "")
        activity_outcome = _activity_outcome_from_mission_trace_event(event_kind)
        action_refs = _safe_refs(
            [f"action:{getattr(mission_trace_event, 'action_id', '')}"]
            if getattr(mission_trace_event, "action_id", None)
            else []
        )
        return cls(
            event_kind=event_kind,
            mission_id=str(getattr(mission_trace_event, "mission_id")),
            run_id=run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
            phase_before=None,
            phase_after=None,
            safe_summary=_deterministic_summary(
                event_kind,
                phase_before=None,
                phase_after=None,
                activity_outcome=activity_outcome,
            ),
            evidence_refs=[],
            receipt_refs=[],
            artifact_refs=[],
            capability_refs=[],
            worker_refs=[],
            organ_refs=[],
            action_refs=action_refs,
            source_ledger="mission_trace_timeline",
            source_event_id=str(getattr(mission_trace_event, "id")),
            source_event_hash=str(getattr(mission_trace_event, "event_hash")),
            source_event_type=_safe_source_event_label(source_event_type),
            source_sequence=int(getattr(mission_trace_event, "sequence")),
            source_logical_time=int(getattr(mission_trace_event, "logical_time")),
            source_parent_event_id=None,
            activity_kind=event_kind.value,
            activity_outcome=activity_outcome,
        )

    def operator_metadata(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_kind": self.event_kind.value,
            "safe_summary": self.safe_summary,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "execution_request_id": self.execution_request_id,
            "bridge_call_id": self.bridge_call_id,
            "agent_run_id": self.agent_run_id,
            "phase_before": self.phase_before,
            "phase_after": self.phase_after,
            "evidence_refs": list(self.evidence_refs),
            "receipt_refs": list(self.receipt_refs),
            "artifact_refs": list(self.artifact_refs),
            "capability_refs": list(self.capability_refs),
            "worker_refs": list(self.worker_refs),
            "organ_refs": list(self.organ_refs),
            "action_refs": list(self.action_refs),
            "source_ledger": self.source_ledger,
            "source_event_id": self.source_event_id,
            "source_event_hash": self.source_event_hash,
            "source_event_type": self.source_event_type,
            "source_sequence": self.source_sequence,
            "source_logical_time": self.source_logical_time,
            "source_parent_event_id": self.source_parent_event_id,
            "activity_kind": self.activity_kind,
            "activity_outcome": self.activity_outcome.value,
            "ref_verification_status": self.ref_verification_status.value,
            "event_hash": self.event_hash,
            "terminal": self.terminal,
            "critical": self.critical,
            "data_not_authority": True,
            "authority_effect": "none",
        }


def _kind_from_source_event(agent_event: Any) -> AgentExecutionEventKind | None:
    event_type = _enum_value(getattr(agent_event, "event_type", ""))
    phase_before = _validated_phase(getattr(agent_event, "phase_before", None))
    phase_after = _validated_phase(getattr(agent_event, "phase_after", None))
    trace_refs = [str(ref) for ref in getattr(agent_event, "trace_refs", ()) or ()]
    receipt_refs = _safe_prefixed_refs(trace_refs, "receipt:")
    evidence_refs = _safe_refs(
        ref
        for ref in trace_refs
        if not ref.startswith(("receipt:", "artifact:", "capability:", "worker:", "organ:", "browser:", "memory:"))
    )

    if event_type == "agent_initialized":
        return AgentExecutionEventKind.RUNTIME_STARTED
    if event_type == "agent_completed":
        return AgentExecutionEventKind.RUNTIME_COMPLETED
    if event_type == "agent_failed":
        return AgentExecutionEventKind.RUNTIME_FAILED
    if event_type == "agent_blocked":
        return AgentExecutionEventKind.RUNTIME_BLOCKED
    if event_type == "agent_revoked":
        return AgentExecutionEventKind.RUNTIME_REVOKED
    if event_type == "agent_escalated":
        return AgentExecutionEventKind.RUNTIME_ESCALATED
    if _source_event_is_pack2b_source_only(event_type):
        return None
    material_kind = _material_kind_from_source_type(event_type)
    if material_kind is not None:
        return material_kind
    if phase_before is not None and phase_after is not None and phase_before != phase_after:
        return AgentExecutionEventKind.PHASE_TRANSITION
    if receipt_refs:
        return AgentExecutionEventKind.RECEIPT_REFS_UPDATED
    if evidence_refs:
        return AgentExecutionEventKind.EVIDENCE_REFS_UPDATED
    return None


def _material_kind_from_source_type(event_type: str | None) -> AgentExecutionEventKind | None:
    mapping = {
        "worker_started": AgentExecutionEventKind.WORKER_STARTED,
        "worker_completed": AgentExecutionEventKind.WORKER_COMPLETED,
        "organ_dispatch_completed": AgentExecutionEventKind.ORGAN_DISPATCH_COMPLETED,
        "organ_dispatch_skipped": AgentExecutionEventKind.ORGAN_DISPATCH_SKIPPED,
        "controlled_capability_executed": AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED,
        "controlled_capability_rejected": AgentExecutionEventKind.CONTROLLED_CAPABILITY_REJECTED,
        "artifact_captured": AgentExecutionEventKind.ARTIFACT_CAPTURED,
        "artifact_capture_rejected": AgentExecutionEventKind.ARTIFACT_CAPTURE_REJECTED,
    }
    return mapping.get(event_type or "")


def _kind_from_mission_trace_event(mission_trace_event: Any) -> AgentExecutionEventKind | None:
    mapping = {
        "action_routed": AgentExecutionEventKind.ACTION_ROUTED,
        "action_executed": AgentExecutionEventKind.ACTION_EXECUTED,
        "action_blocked": AgentExecutionEventKind.ACTION_BLOCKED,
        "action_escalated": AgentExecutionEventKind.ACTION_ESCALATED,
        "mission_completed": AgentExecutionEventKind.MISSION_RUNNER_COMPLETED,
        "mission_failed": AgentExecutionEventKind.MISSION_RUNNER_FAILED,
    }
    return mapping.get(str(_enum_value(getattr(mission_trace_event, "event_type", "")) or ""))


def _source_event_is_pack2b_source_only(event_type: str | None) -> bool:
    if not event_type:
        return False
    if event_type.startswith("browser_"):
        return True
    return event_type in {
        "artifact_capture_duplicate",
        "artifact_capture_index_written",
        "learning_proposed",
        "organ_execution_receipt_recorded",
    }


def _activity_outcome_from_agent_event(event_kind: AgentExecutionEventKind, agent_event: Any) -> ExecutionActivityOutcome:
    if event_kind is AgentExecutionEventKind.WORKER_STARTED:
        return ExecutionActivityOutcome.STARTED
    if event_kind is AgentExecutionEventKind.WORKER_COMPLETED:
        payload = getattr(agent_event, "payload", {}) or {}
        success = payload.get("success") if hasattr(payload, "get") else None
        if success is True:
            return ExecutionActivityOutcome.SUCCEEDED
        if success is False:
            return ExecutionActivityOutcome.FAILED
        return ExecutionActivityOutcome.CLOSED_UNKNOWN
    if event_kind in {
        AgentExecutionEventKind.RUNTIME_STARTED,
        AgentExecutionEventKind.PHASE_TRANSITION,
    }:
        return ExecutionActivityOutcome.STARTED
    if event_kind in {
        AgentExecutionEventKind.RUNTIME_COMPLETED,
        AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED,
        AgentExecutionEventKind.ARTIFACT_CAPTURED,
        AgentExecutionEventKind.ORGAN_DISPATCH_COMPLETED,
    }:
        return ExecutionActivityOutcome.SUCCEEDED
    if event_kind in {
        AgentExecutionEventKind.RUNTIME_FAILED,
        AgentExecutionEventKind.MISSION_RUNNER_FAILED,
    }:
        return ExecutionActivityOutcome.FAILED
    if event_kind is AgentExecutionEventKind.RUNTIME_BLOCKED:
        return ExecutionActivityOutcome.BLOCKED
    if event_kind is AgentExecutionEventKind.RUNTIME_ESCALATED:
        return ExecutionActivityOutcome.ESCALATED
    if event_kind in {
        AgentExecutionEventKind.CONTROLLED_CAPABILITY_REJECTED,
        AgentExecutionEventKind.ARTIFACT_CAPTURE_REJECTED,
    }:
        return ExecutionActivityOutcome.REJECTED
    if event_kind is AgentExecutionEventKind.ORGAN_DISPATCH_SKIPPED:
        return ExecutionActivityOutcome.SKIPPED
    return ExecutionActivityOutcome.CLOSED_UNKNOWN


def _activity_outcome_from_mission_trace_event(event_kind: AgentExecutionEventKind) -> ExecutionActivityOutcome:
    if event_kind in {
        AgentExecutionEventKind.ACTION_EXECUTED,
        AgentExecutionEventKind.MISSION_RUNNER_COMPLETED,
    }:
        return ExecutionActivityOutcome.SUCCEEDED
    if event_kind is AgentExecutionEventKind.ACTION_BLOCKED:
        return ExecutionActivityOutcome.BLOCKED
    if event_kind is AgentExecutionEventKind.ACTION_ESCALATED:
        return ExecutionActivityOutcome.ESCALATED
    if event_kind is AgentExecutionEventKind.MISSION_RUNNER_FAILED:
        return ExecutionActivityOutcome.FAILED
    return ExecutionActivityOutcome.CLOSED_UNKNOWN


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    rendered = getattr(value, "value", value)
    return str(rendered)


_KNOWN_PHASE_VALUES = {
    "created",
    "initialized",
    "context_building",
    "orienting",
    "method_selecting",
    "capability_selecting",
    "tool_selecting",
    "hypothesis_verifying",
    "action_scoring",
    "effort_routing",
    "planning",
    "plan_reviewing",
    "executing",
    "artifact_reviewing",
    "repairing",
    "success_evaluating",
    "learning_proposing",
    "organ_dispatching",
    "completed",
    "escalated",
    "paused",
    "stopped",
    "revoked",
    "blocked",
    "failed",
}


def _validated_phase(value: Any) -> str | None:
    rendered = _enum_value(value)
    if rendered in _KNOWN_PHASE_VALUES:
        return rendered
    return None


_SAFE_REF_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,79}$")
_UNSAFE_REF_MARKERS = (
    "://",
    "\\",
    "/",
    "?",
    "&",
    "=",
    "authorization",
    "bearer",
    "password",
    "provider_response",
    "raw_prompt",
    "raw_response",
    "reasoning",
    "secret",
    "token",
)


def _safe_refs(values: Any, *, limit: int = 8) -> list[str]:
    refs: list[str] = []
    for value in values:
        text = str(value or "").strip()
        lowered = text.lower()
        if not text or len(text) > 80:
            continue
        if any(char.isspace() for char in text):
            continue
        if any(marker in lowered for marker in _UNSAFE_REF_MARKERS):
            continue
        if not _SAFE_REF_PATTERN.fullmatch(text):
            continue
        refs.append(text)
        if len(refs) >= limit:
            break
    return refs


def _safe_prefixed_refs(values: Any, prefix: str, *, limit: int = 8) -> list[str]:
    return _safe_refs((value for value in values if str(value).startswith(prefix)), limit=limit)


def _safe_source_event_label(event_type: str) -> str:
    if event_type == "organ_execution_receipt_recorded":
        return "organ_receipt_recorded"
    return event_type


def _deterministic_summary(
    event_kind: AgentExecutionEventKind,
    *,
    phase_before: str | None,
    phase_after: str | None,
    activity_outcome: ExecutionActivityOutcome = ExecutionActivityOutcome.CLOSED_UNKNOWN,
) -> str:
    if event_kind is AgentExecutionEventKind.RUNTIME_STARTED:
        return "Agent runtime started."
    if event_kind is AgentExecutionEventKind.PHASE_TRANSITION:
        return f"Agent runtime phase changed from {phase_before} to {phase_after}."
    if event_kind is AgentExecutionEventKind.RECEIPT_REFS_UPDATED:
        return "Agent runtime receipt references were updated."
    if event_kind is AgentExecutionEventKind.EVIDENCE_REFS_UPDATED:
        return "Agent runtime evidence references were updated."
    if event_kind is AgentExecutionEventKind.WORKER_STARTED:
        return "Agent runtime worker started."
    if event_kind is AgentExecutionEventKind.WORKER_COMPLETED:
        if activity_outcome is ExecutionActivityOutcome.SUCCEEDED:
            return "Agent worker lifecycle closed successfully."
        if activity_outcome is ExecutionActivityOutcome.FAILED:
            return "Agent worker lifecycle closed with failure."
        return "Agent worker lifecycle closed with unknown outcome."
    if event_kind is AgentExecutionEventKind.ORGAN_DISPATCH_COMPLETED:
        return "Agent runtime organ dispatch completed."
    if event_kind is AgentExecutionEventKind.ORGAN_DISPATCH_SKIPPED:
        return "Agent runtime organ dispatch skipped."
    if event_kind is AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED:
        return "Agent runtime controlled capability executed."
    if event_kind is AgentExecutionEventKind.CONTROLLED_CAPABILITY_REJECTED:
        return "Agent runtime controlled capability rejected."
    if event_kind is AgentExecutionEventKind.ARTIFACT_CAPTURED:
        return "Agent runtime artifact captured."
    if event_kind is AgentExecutionEventKind.ARTIFACT_CAPTURE_REJECTED:
        return "Agent runtime artifact capture rejected."
    if event_kind is AgentExecutionEventKind.ACTION_ROUTED:
        return "Mission runner action routed."
    if event_kind is AgentExecutionEventKind.ACTION_EXECUTED:
        return "Mission runner action executed."
    if event_kind is AgentExecutionEventKind.ACTION_BLOCKED:
        return "Mission runner action blocked."
    if event_kind is AgentExecutionEventKind.ACTION_ESCALATED:
        return "Mission runner action escalated."
    if event_kind is AgentExecutionEventKind.MISSION_RUNNER_COMPLETED:
        return "Mission runner completed."
    if event_kind is AgentExecutionEventKind.MISSION_RUNNER_FAILED:
        return "Mission runner failed."
    if event_kind is AgentExecutionEventKind.RUNTIME_COMPLETED:
        return "Agent runtime reached completed final state."
    if event_kind is AgentExecutionEventKind.RUNTIME_FAILED:
        return "Agent runtime reached failed final state."
    if event_kind is AgentExecutionEventKind.RUNTIME_BLOCKED:
        return "Agent runtime reached blocked final state."
    if event_kind is AgentExecutionEventKind.RUNTIME_REVOKED:
        return "Agent runtime reached revoked final state."
    if event_kind is AgentExecutionEventKind.RUNTIME_ESCALATED:
        return "Agent runtime reached escalated final state."
    return "Agent runtime event observed."


def _hash_event_projection(event: AgentExecutionEvent) -> str:
    payload = event.model_dump(mode="json")
    payload["event_hash"] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "AgentExecutionEvent",
    "AgentExecutionEventKind",
    "ExecutionActivityOutcome",
    "ExecutionEventSink",
    "RefVerificationStatus",
]
