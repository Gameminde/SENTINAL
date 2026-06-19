from __future__ import annotations

from typing import Any

from sentinel.operator.store import MissionRunStore
from sentinel.shared.execution_events import AgentExecutionEvent


AGENT_EVENT_SPINE_PERSISTENCE_FAILED = "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"


class AgentEventBridgeError(RuntimeError):
    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class AgentEventBridgePersistenceError(AgentEventBridgeError):
    def __init__(self, safe_message: str = "AgentRuntime execution event spine persistence failed.") -> None:
        super().__init__(AGENT_EVENT_SPINE_PERSISTENCE_FAILED, safe_message)


class OperatorAgentEventBridge:
    """Validate and persist AgentRuntime event projections into MissionRunStore.

    This bridge is intentionally one-way. It records observations and refs in
    the canonical operator run ledger, but it never mutates MissionKernel
    product status and never treats AgentRuntime events as authority.
    """

    def __init__(
        self,
        *,
        store: MissionRunStore,
        mission_id: str,
        run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ) -> None:
        self._store = store
        self._mission_id = mission_id
        self._run_id = run_id
        self._execution_request_id = execution_request_id
        self._bridge_call_id = bridge_call_id
        self._agent_run_id = agent_run_id
        self._seen_source_event_ids: set[str] = set()
        self._terminal_seen = False
        self._closed = False
        self._projected_event_ids: list[str] = []

    @property
    def projected_event_ids(self) -> tuple[str, ...]:
        return tuple(self._projected_event_ids)

    @property
    def projected_count(self) -> int:
        return len(self._projected_event_ids)

    def emit(self, event: AgentExecutionEvent) -> None:
        self._validate_event(event)
        try:
            persisted = self._store.append_event(
                self._mission_id,
                event_type="agentruntime_execution_event_observed",
                safe_summary=event.safe_summary,
                metadata=event.operator_metadata(),
                receipt_refs=event.receipt_refs,
            )
        except Exception as exc:  # noqa: BLE001
            raise AgentEventBridgePersistenceError() from exc
        self._projected_event_ids.append(persisted.event_id)
        self._seen_source_event_ids.add(event.source_event_id)
        if event.terminal:
            self._terminal_seen = True

    def close(self) -> None:
        self._closed = True

    def _validate_event(self, event: AgentExecutionEvent) -> None:
        if self._closed:
            raise AgentEventBridgePersistenceError("AgentRuntime event bridge is closed.")
        if self._terminal_seen:
            raise AgentEventBridgePersistenceError("AgentRuntime emitted an event after terminal projection.")
        if event.mission_id != self._mission_id:
            raise AgentEventBridgePersistenceError("AgentRuntime event mission correlation failed.")
        if event.run_id != self._run_id:
            raise AgentEventBridgePersistenceError("AgentRuntime event run correlation failed.")
        if event.execution_request_id != self._execution_request_id:
            raise AgentEventBridgePersistenceError("AgentRuntime event execution request correlation failed.")
        if event.bridge_call_id != self._bridge_call_id:
            raise AgentEventBridgePersistenceError("AgentRuntime event bridge call correlation failed.")
        if event.agent_run_id != self._agent_run_id:
            raise AgentEventBridgePersistenceError("AgentRuntime event agent run correlation failed.")
        if not event.source_event_id or not event.source_event_hash:
            raise AgentEventBridgePersistenceError("AgentRuntime event source hash anchor missing.")
        if event.source_event_id in self._seen_source_event_ids:
            raise AgentEventBridgePersistenceError("AgentRuntime duplicate source event rejected.")
        _reject_unsafe_projection_metadata(event.operator_metadata())


def _reject_unsafe_projection_metadata(metadata: dict[str, Any]) -> None:
    serialized = str(metadata).lower()
    forbidden_markers = (
        "raw_prompt",
        "raw provider",
        "raw_provider",
        "raw_response",
        "provider_response",
        "authorization",
        "bearer ",
        "password",
        "api_key",
        "secret",
        "reasoning",
        "chain_of_thought",
    )
    if any(marker in serialized for marker in forbidden_markers):
        raise AgentEventBridgePersistenceError("AgentRuntime projection contained forbidden raw material marker.")


__all__ = [
    "AGENT_EVENT_SPINE_PERSISTENCE_FAILED",
    "AgentEventBridgeError",
    "AgentEventBridgePersistenceError",
    "OperatorAgentEventBridge",
]
