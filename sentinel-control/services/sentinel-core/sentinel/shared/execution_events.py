from __future__ import annotations

import hashlib
import json
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
    EVIDENCE_REFS_UPDATED = "evidence_refs_updated"
    RECEIPT_REFS_UPDATED = "receipt_refs_updated"


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
    source_event_id: str
    source_event_hash: str
    event_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _hash_bound_safe_projection(self) -> "AgentExecutionEvent":
        if self.authority_effect != "none" or not self.data_not_authority or self.can_grant_authority or self.can_execute:
            raise ValueError("AgentExecutionEvent is data only and cannot grant authority or execute.")
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
        return self.terminal or self.event_kind in {
            AgentExecutionEventKind.RUNTIME_STARTED,
            AgentExecutionEventKind.PHASE_TRANSITION,
            AgentExecutionEventKind.RECEIPT_REFS_UPDATED,
        }

    @classmethod
    def from_agent_event(
        cls,
        agent_event: Any,
        *,
        run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ) -> "AgentExecutionEvent":
        event_kind = _kind_from_source_event(agent_event)
        trace_refs = [str(ref) for ref in getattr(agent_event, "trace_refs", ()) or ()]
        receipt_refs = [ref for ref in trace_refs if ref.startswith("receipt:")]
        evidence_refs = [ref for ref in trace_refs if not ref.startswith("receipt:")]
        return cls(
            event_kind=event_kind,
            mission_id=str(getattr(agent_event, "mission_id")),
            run_id=run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
            phase_before=_enum_value(getattr(agent_event, "phase_before", None)),
            phase_after=_enum_value(getattr(agent_event, "phase_after", None)),
            safe_summary=_safe_summary(getattr(agent_event, "summary", "")),
            evidence_refs=evidence_refs,
            receipt_refs=receipt_refs,
            source_event_id=str(getattr(agent_event, "id")),
            source_event_hash=str(getattr(agent_event, "event_hash")),
        )

    def operator_metadata(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_kind": self.event_kind.value,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "execution_request_id": self.execution_request_id,
            "bridge_call_id": self.bridge_call_id,
            "agent_run_id": self.agent_run_id,
            "phase_before": self.phase_before,
            "phase_after": self.phase_after,
            "evidence_refs": list(self.evidence_refs),
            "receipt_refs": list(self.receipt_refs),
            "source_event_id": self.source_event_id,
            "source_event_hash": self.source_event_hash,
            "event_hash": self.event_hash,
            "terminal": self.terminal,
            "critical": self.critical,
            "data_not_authority": True,
            "authority_effect": "none",
        }


def _kind_from_source_event(agent_event: Any) -> AgentExecutionEventKind:
    event_type = _enum_value(getattr(agent_event, "event_type", ""))
    phase_before = _enum_value(getattr(agent_event, "phase_before", None))
    phase_after = _enum_value(getattr(agent_event, "phase_after", None))
    trace_refs = [str(ref) for ref in getattr(agent_event, "trace_refs", ()) or ()]

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
    if event_type.endswith("_receipt_recorded") or any(ref.startswith("receipt:") for ref in trace_refs):
        return AgentExecutionEventKind.RECEIPT_REFS_UPDATED
    if phase_before is not None and phase_after is not None and phase_before != phase_after:
        return AgentExecutionEventKind.PHASE_TRANSITION
    if trace_refs:
        return AgentExecutionEventKind.EVIDENCE_REFS_UPDATED
    return AgentExecutionEventKind.PHASE_TRANSITION


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    rendered = getattr(value, "value", value)
    return str(rendered)


def _safe_summary(value: Any, *, limit: int = 280) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 13].rstrip() + "...[truncated]"


def _hash_event_projection(event: AgentExecutionEvent) -> str:
    payload = event.model_dump(mode="json")
    payload["event_hash"] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "AgentExecutionEvent",
    "AgentExecutionEventKind",
    "ExecutionEventSink",
]
