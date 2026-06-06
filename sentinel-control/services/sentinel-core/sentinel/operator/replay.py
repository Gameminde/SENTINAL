from __future__ import annotations

from pydantic import Field

from sentinel.operator.models import MissionEvent, OperatorMissionStatus
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.store import MissionRunStore
from sentinel.shared.models import SentinelModel


class MissionReplayView(SentinelModel):
    mission_id: str
    events: list[MissionEvent] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    terminal_explanation: str = "Mission is not terminal."
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    def safe_summary_text(self) -> str:
        return "\n".join(redact_operator_text(event.safe_summary) for event in self.events)


class MissionReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str) -> MissionReplayView:
        events = self._store.load_events(mission_id)
        record = self._store.load_record(mission_id)
        return MissionReplayView(
            mission_id=mission_id,
            events=events,
            tampered=not self._store.verify_timeline(mission_id),
            reexecuted_actions=False,
            receipt_refs=_dedupe(ref for event in events for ref in event.receipt_refs),
            finalgate_certificate_refs=_dedupe(ref for event in events for ref in event.finalgate_certificate_refs),
            memory_feedback_refs=_dedupe(ref for event in events for ref in event.memory_feedback_refs),
            terminal_explanation=_terminal_explanation(record.status),
        )


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _terminal_explanation(status: OperatorMissionStatus) -> str:
    if status is OperatorMissionStatus.KILLED:
        return "Mission killed by operator; replay is evidence-only and does not resume work."
    if status is OperatorMissionStatus.BLOCKED:
        return "Mission blocked; replay is evidence-only and does not bypass gates."
    if status is OperatorMissionStatus.FAILED:
        return "Mission failed; replay is evidence-only and does not retry."
    if status is OperatorMissionStatus.COMPLETED:
        return "Mission completed; replay reconstructs the proof timeline."
    return "Mission is not terminal."
