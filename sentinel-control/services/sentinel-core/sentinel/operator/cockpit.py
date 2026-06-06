from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from sentinel.agent.model_contract import UserModelContract
from sentinel.operator.conversation import OperatorConversationEngine
from sentinel.operator.kernel import MissionKernel, MissionLifecycleError
from sentinel.operator.models import (
    OperatorConversationSession,
    OperatorConversationState,
    OperatorIntent,
    OperatorIntentKind,
    OperatorMissionStatus,
    OperatorMode,
    OperatorTurnResult,
)


class LLMLiveOperatorCockpit:
    def __init__(
        self,
        *,
        run_root: Path | str,
        mode: OperatorMode,
        user_model_contract: UserModelContract | None = None,
        model_client=None,
    ) -> None:
        self.session = OperatorConversationSession(mode=mode)
        self.kernel = MissionKernel(run_root=run_root)
        self.engine = OperatorConversationEngine(
            mode=mode,
            user_model_contract=user_model_contract,
            model_client=model_client,
        )
        self.active_mission_id: str | None = None
        self.active_mission_ids: list[str] = []

    def handle(self, text: str) -> OperatorTurnResult:
        normalized = text.strip().lower()
        if normalized in {"start", "commence", "go", "oui commence"}:
            return self._start()
        if normalized in {"pause", "/pause", "stop for now"}:
            return self._control("pause")
        if normalized in {"resume", "continue", "reprends", "/resume"}:
            return self._control("resume")
        if normalized in {"kill", "cancel", "/kill"}:
            return self._control("kill")
        if normalized in {"status", "what are you doing?", "qu'est-ce que tu fais ?", "/status"}:
            return self._status()
        try:
            return self.engine.handle_user_message(self.session, text)
        except ValidationError:
            return OperatorTurnResult(
                session_id=self.session.session_id,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="LLM operator output rejected by Sentinel validation. Reformule la mission ou reduis la demande.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="rejected unsafe operator output"),
                metadata={"blocked_reason": "llm_operator_output_rejected"},
            )

    def _start(self) -> OperatorTurnResult:
        if self.session.current_draft is None or self.session.current_authority_summary is None:
            return OperatorTurnResult(
                session_id=self.session.session_id,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="J'ai besoin d'une mission et d'un resume d'autorite avant de commencer.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="start"),
            )
        record = self.kernel.create_mission(
            session_id=self.session.session_id,
            draft=self.session.current_draft,
            authority_summary=self.session.current_authority_summary,
        )
        record = self.kernel.enqueue(record.mission_id)
        self.active_mission_id = record.mission_id
        if record.mission_id not in self.active_mission_ids:
            self.active_mission_ids.append(record.mission_id)
        self.session.active_mission_id = record.mission_id
        self.session.state = OperatorConversationState.MISSION_QUEUED
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=OperatorConversationState.MISSION_QUEUED,
            reply="Mission lancee et mise en file controlee.",
            mission_draft=self.session.current_draft,
            authority_summary=self.session.current_authority_summary,
            mission_record=record,
        )

    def _control(self, command: str) -> OperatorTurnResult:
        mission_id = self._single_active_mission_id()
        if mission_id is None:
            return self._needs_mission_selection()
        if command == "pause":
            target = self.kernel.pause
            state = OperatorConversationState.MISSION_PAUSED
            reply = "Mission paused."
        elif command == "resume":
            target = self.kernel.resume
            state = OperatorConversationState.MISSION_QUEUED
            reply = "Mission resumed."
        else:
            target = self.kernel.kill
            state = OperatorConversationState.MISSION_KILLED
            reply = "Mission killed."
        try:
            record = target(mission_id)
        except MissionLifecycleError as exc:
            record = self.kernel.store.load_record(mission_id)
            state = _state_for_record_status(record.status, fallback=self.session.state)
            reply = f"Mission cannot change state: {exc}"
        self.session.state = state
        return OperatorTurnResult(session_id=self.session.session_id, state=state, reply=reply, mission_record=record)

    def _status(self) -> OperatorTurnResult:
        mission_id = self._single_active_mission_id()
        if mission_id is None:
            return self._needs_mission_selection()
        record = self.kernel.store.load_record(mission_id)
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=self.session.state,
            reply=f"Mission {record.mission_id} status: {record.status.value}.",
            mission_record=record,
        )

    def _single_active_mission_id(self) -> str | None:
        active = [mission_id for mission_id in self.active_mission_ids if mission_id]
        if len(active) == 1:
            return active[0]
        if len(active) == 0:
            return self.active_mission_id
        return None

    def _needs_mission_selection(self) -> OperatorTurnResult:
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=self.session.state,
            reply="Which mission should I use? Multiple active missions need disambiguation.",
            intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="mission disambiguation"),
        )


def _state_for_record_status(
    status: OperatorMissionStatus,
    *,
    fallback: OperatorConversationState,
) -> OperatorConversationState:
    if status is OperatorMissionStatus.KILLED:
        return OperatorConversationState.MISSION_KILLED
    if status is OperatorMissionStatus.PAUSED:
        return OperatorConversationState.MISSION_PAUSED
    if status is OperatorMissionStatus.COMPLETED:
        return OperatorConversationState.MISSION_COMPLETED
    if status is OperatorMissionStatus.FAILED:
        return OperatorConversationState.MISSION_FAILED
    if status is OperatorMissionStatus.BLOCKED:
        return OperatorConversationState.MISSION_BLOCKED
    if status is OperatorMissionStatus.QUEUED:
        return OperatorConversationState.MISSION_QUEUED
    if status is OperatorMissionStatus.RUNNING:
        return OperatorConversationState.MISSION_RUNNING
    return fallback
