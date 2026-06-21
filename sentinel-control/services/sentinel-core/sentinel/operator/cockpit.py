from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.conversation import OperatorConversationEngine
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.kernel import MissionKernel, MissionLifecycleError
from sentinel.operator.mission_lifecycle_service import MissionLifecycleService
from sentinel.operator.models import (
    OperatorConversationSession,
    OperatorConversationState,
    OperatorIntent,
    OperatorIntentKind,
    OperatorMissionStatus,
    OperatorMode,
    OperatorTurnResult,
)
from sentinel.operator.product_execution_binding import ProductExecutionBinding
from sentinel.memory.integration import PersistentMemoryRecallAdapter
from sentinel.memory.models import PersistentMemoryRetrievalResult
from sentinel.operator.structured_output import READ_ONLY_RESEARCH_ACTIONS, READ_ONLY_RESEARCH_CAPABILITY
from sentinel.operator.models import utc_now


class LLMLiveOperatorCockpit:
    def __init__(
        self,
        *,
        run_root: Path | str,
        mode: OperatorMode,
        user_model_contract: UserModelContract | None = None,
        model_client=None,
        persistent_memory_recall_adapter: PersistentMemoryRecallAdapter | None = None,
        persistent_memory_owner_user_id: str | None = None,
        telemetry_sink: object | None = None,
        lifecycle_service: MissionLifecycleService | None = None,
        authority_approval_scope: MissionAuthorityApprovalScope | None = None,
        product_execution_binding: ProductExecutionBinding | None = None,
        require_mission_understanding_v2: bool = False,
    ) -> None:
        self.session = OperatorConversationSession(mode=mode)
        self._lifecycle_service = lifecycle_service
        self.authority_approval_scope = authority_approval_scope
        self.kernel = (
            lifecycle_service.kernel
            if lifecycle_service is not None
            else MissionKernel(run_root=run_root, telemetry_sink=telemetry_sink)
        )
        self._telemetry_sink = self.kernel.telemetry_sink
        self.product_execution_binding = product_execution_binding
        self.engine = OperatorConversationEngine(
            mode=mode,
            user_model_contract=user_model_contract,
            model_client=model_client,
            telemetry_sink=self._telemetry_sink,
            require_mission_understanding_v2=require_mission_understanding_v2,
        )
        self.active_mission_id: str | None = None
        self.active_mission_ids: list[str] = []
        self._persistent_memory_recall_adapter = persistent_memory_recall_adapter
        self._persistent_memory_owner_user_id = persistent_memory_owner_user_id
        self.last_persistent_memory_retrieval: PersistentMemoryRetrievalResult | None = None
        self.last_persistent_memory_error_hash: str | None = None
        self._legacy_deterministic_scope_compatibility = False

    def handle(self, text: str) -> OperatorTurnResult:
        normalized = text.strip().lower()
        if _is_start_confirmation(normalized):
            return self._start()
        if normalized in {"pause", "/pause", "stop for now"}:
            return self._control("pause")
        if normalized in {"resume", "continue", "reprends", "/resume"}:
            return self._control("resume")
        if normalized in {"kill", "cancel", "/kill"}:
            return self._control("kill")
        if normalized in {"status", "what are you doing?", "qu'est-ce que tu fais ?", "/status"}:
            return self._status()
        persistent_memory_context = self._recall_persistent_memory(text)
        try:
            result = self.engine.handle_user_message(
                self.session,
                text,
                persistent_memory_context=persistent_memory_context,
            )
            return self._apply_approval_scope(result)
        except ValidationError:
            return OperatorTurnResult(
                session_id=self.session.session_id,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="LLM operator output rejected by Sentinel validation. Reformule la mission ou reduis la demande.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="rejected unsafe operator output"),
                metadata={"blocked_reason": "llm_operator_output_rejected"},
            )

    def _apply_approval_scope(self, result: OperatorTurnResult) -> OperatorTurnResult:
        if result.authority_summary is None or self.authority_approval_scope is None:
            return result
        action_scopes = [result.authority_summary.allowed_actions, self.authority_approval_scope.allowed_actions]
        if result.authority_summary.metadata.get("capability_id") == READ_ONLY_RESEARCH_CAPABILITY:
            action_scopes.insert(1, list(READ_ONLY_RESEARCH_ACTIONS))
        allowed = _ordered_intersection(*action_scopes)
        if not allowed and result.metadata.get("non_product_mode") is True:
            allowed = [
                action
                for action in self.authority_approval_scope.allowed_actions
                if action not in self.authority_approval_scope.forbidden_actions
            ]
            result = result.model_copy(
                update={
                    "metadata": {
                        **result.metadata,
                        "legacy_deterministic_scope_compatibility": True,
                    }
                }
            )
            self._legacy_deterministic_scope_compatibility = True
        forbidden = list(
            dict.fromkeys(
                [
                    *result.authority_summary.forbidden_actions,
                    *self.authority_approval_scope.forbidden_actions,
                ]
            )
        )
        summary = result.authority_summary.model_copy(
            update={
                "allowed_actions": allowed,
                "forbidden_actions": forbidden,
            }
        )
        self.session.current_authority_summary = summary
        return result.model_copy(update={"authority_summary": summary})

    def _recall_persistent_memory(self, text: str) -> str | None:
        self.last_persistent_memory_retrieval = None
        self.last_persistent_memory_error_hash = None
        if self._persistent_memory_recall_adapter is None or not self._persistent_memory_owner_user_id:
            return None
        try:
            bundle = self._persistent_memory_recall_adapter.recall(
                owner_user_id=self._persistent_memory_owner_user_id,
                mission_id=self.active_mission_id or self.session.session_id,
                query_text=text,
                current_time=utc_now(),
            )
        except Exception as exc:
            self.last_persistent_memory_error_hash = stable_hash(
                {"failure_class": exc.__class__.__name__}
            )
            return None
        self.last_persistent_memory_retrieval = bundle.retrieval
        if self.active_mission_id and bundle.retrieval.hits:
            self.kernel.record_memory_retrieval(self.active_mission_id, bundle.retrieval)
        return bundle.retrieval.to_untrusted_context_block() if bundle.retrieval.hits else None

    def _start(self) -> OperatorTurnResult:
        if self.session.current_draft is None or self.session.current_authority_summary is None:
            return OperatorTurnResult(
                session_id=self.session.session_id,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="J'ai besoin d'une mission et d'un resume d'autorite avant de commencer.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="start"),
            )
        if self._lifecycle_service is not None:
            if self.authority_approval_scope is None:
                return OperatorTurnResult(
                    session_id=self.session.session_id,
                    state=OperatorConversationState.ASKING_CLARIFICATIONS,
                    reply="Explicit typed authority approval scope is required before governed mission start.",
                    intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="explicit authority approval required"),
                    metadata={"blocked_reason": "explicit_authority_approval_scope_required"},
                )
            capability_id = str(
                self.session.current_authority_summary.metadata.get(
                    "capability_id",
                    "read_only_research",
                )
            )
            operation = str(
                self.session.current_authority_summary.metadata.get(
                    "operation",
                    "inspect_repository",
                )
            )
            binding = self.product_execution_binding
            if binding is not None and (
                binding.capability_id != capability_id or binding.operation != operation
            ):
                return OperatorTurnResult(
                    session_id=self.session.session_id,
                    state=OperatorConversationState.ASKING_CLARIFICATIONS,
                    reply="Product execution binding does not match the approved mission capability.",
                    intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="product binding mismatch"),
                    metadata={"blocked_reason": "product_execution_binding_mismatch"},
                )
            if binding is None and self.session.mode is OperatorMode.LLM_OPERATOR:
                return OperatorTurnResult(
                    session_id=self.session.session_id,
                    state=OperatorConversationState.ASKING_CLARIFICATIONS,
                    reply="A validated workspace binding is required before Sentinel can start this product mission.",
                    intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text="workspace binding required"),
                    metadata={"blocked_reason": "workspace_binding_required"},
                )
            workspace_ref = (
                binding.workspace_ref
                if binding is not None
                else str(
                    self.session.current_authority_summary.metadata.get(
                        "workspace_ref",
                        "snapshot:operator_session",
                    )
                )
            )
            model_contract_ref = (
                binding.model_contract_ref
                if binding is not None
                else str(
                    self.session.current_authority_summary.metadata.get(
                        "model_contract_ref",
                        "model_contract:operator_session",
                    )
                )
            )
            lifecycle_result = self._lifecycle_service.create_mission(
                session_id=self.session.session_id,
                draft=self.session.current_draft,
                authority_summary=self.session.current_authority_summary,
                approval_scope=self.authority_approval_scope,
                policy=_default_authority_policy(self.session.current_authority_summary),
                capability_id=capability_id,
                operation=operation,
                parameters={"mission_draft_id": self.session.current_draft.draft_id},
                workspace_ref=workspace_ref,
                model_contract_ref=model_contract_ref,
            )
            record = lifecycle_result.record
        else:
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
        metadata = (
            {"legacy_deterministic_scope_compatibility": True}
            if self._legacy_deterministic_scope_compatibility
            else {}
        )
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=OperatorConversationState.MISSION_QUEUED,
            reply="Mission lancee et mise en file controlee.",
            mission_draft=self.session.current_draft,
            authority_summary=self.session.current_authority_summary,
            mission_record=record,
            metadata=metadata,
        )

    def _control(self, command: str) -> OperatorTurnResult:
        mission_id = self._single_active_mission_id()
        if mission_id is None:
            return self._needs_mission_selection()
        self._record_interruption(command)
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
        metadata = (
            {"legacy_deterministic_scope_compatibility": True}
            if self._legacy_deterministic_scope_compatibility
            else {}
        )
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=state,
            reply=reply,
            mission_record=record,
            metadata=metadata,
        )

    def _status(self) -> OperatorTurnResult:
        mission_id = self._single_active_mission_id()
        if mission_id is None:
            return self._needs_mission_selection()
        self._record_interruption("status")
        record = self.kernel.store.load_record(mission_id)
        return OperatorTurnResult(
            session_id=self.session.session_id,
            state=self.session.state,
            reply=f"Mission {record.mission_id} status: {record.status.value}.",
            mission_record=record,
        )

    def _record_interruption(self, command: str) -> None:
        if self._telemetry_sink is None or not hasattr(self._telemetry_sink, "record_operator_interruption"):
            return
        self._telemetry_sink.record_operator_interruption(session_id=self.session.session_id, command=command)

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


def _is_start_confirmation(normalized: str) -> bool:
    if normalized in {"start", "commence", "go", "oui commence", "approve", "approved"}:
        return True
    return normalized.startswith("oui") and "commence" in normalized and (
        "approuv" in normalized or "autorit" in normalized or "authority" in normalized
    )


def _ordered_intersection(*collections: list[str]) -> list[str]:
    if not collections:
        return []
    allowed_sets = [set(collection) for collection in collections[1:]]
    return [item for item in collections[0] if all(item in allowed for allowed in allowed_sets)]


def _default_authority_policy(summary) -> MissionAuthorityPolicy:
    max_duration = summary.metadata.get("max_duration_minutes", 30)
    max_actions = summary.metadata.get("max_actions", 10)
    max_cost = summary.metadata.get("max_cost_usd", 0.0)
    return MissionAuthorityPolicy(
        user_id=str(summary.metadata.get("user_id", "operator_user")),
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=list(dict.fromkeys(summary.allowed_actions)),
        forbidden_actions=list(dict.fromkeys(summary.forbidden_actions)),
        allowed_paths=["."],
        max_duration_minutes=max_duration if isinstance(max_duration, int) else 30,
        max_actions=max_actions if isinstance(max_actions, int) else 10,
        max_cost_usd=float(max_cost) if isinstance(max_cost, int | float) else 0.0,
    )
