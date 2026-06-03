from __future__ import annotations

import pytest

from sentinel.agent import AgentEventType, AgentPhase, EventBus, audit_agent_trace


def test_event_bus_appends_with_monotonic_logical_time():
    bus = EventBus("mission_001")

    first = bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.", phase_after=AgentPhase.INITIALIZED)
    second = bus.append(
        AgentEventType.CONTEXT_BUILT,
        "Context built.",
        phase_before=AgentPhase.INITIALIZED,
        phase_after=AgentPhase.CONTEXT_BUILDING,
    )

    assert first.sequence == 0
    assert first.logical_time == 0
    assert second.sequence == 1
    assert second.logical_time == 1
    assert second.previous_hash == first.event_hash
    assert bus.verify_chain() is True


def test_event_bus_events_returns_immutable_tuple_view():
    bus = EventBus("mission_001")
    bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")

    events = bus.events()

    assert isinstance(events, tuple)
    assert len(events) == 1


def test_event_bus_append_isolates_payload_from_caller_mutation():
    bus = EventBus("mission_001")
    payload = {"nested": {"value": "original"}}
    trace_refs = ["trace_1"]

    event = bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.", payload=payload, trace_refs=trace_refs)
    payload["nested"]["value"] = "mutated"
    trace_refs.append("trace_2")

    assert event.payload == {"nested": {"value": "original"}}
    assert event.trace_refs == ("trace_1",)
    assert bus.verify_chain() is True


def test_event_bus_returned_event_payload_cannot_be_mutated_to_bypass_chain():
    bus = EventBus("mission_001")
    first = bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.", payload={"nested": {"value": "original"}})
    bus.append(AgentEventType.CONTEXT_BUILT, "Context built.")

    with pytest.raises(TypeError):
        first.payload["nested"]["value"] = "mutated"

    bus.append(AgentEventType.AGENT_BLOCKED, "After attempted payload mutation.")
    assert bus.verify_chain() is True


def test_event_bus_returned_event_top_level_payload_cannot_be_mutated_to_bypass_chain():
    bus = EventBus("mission_001")
    first = bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.", payload={"value": "original"})
    bus.append(AgentEventType.CONTEXT_BUILT, "Context built.")

    with pytest.raises(TypeError):
        first.payload["value"] = "mutated"

    bus.append(AgentEventType.AGENT_BLOCKED, "After attempted payload mutation.")
    assert bus.verify_chain() is True


def test_event_bus_rejects_non_mapping_payload():
    bus = EventBus("mission_001")

    with pytest.raises(ValueError, match="payload must be a mapping"):
        bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.", payload=["not", "mapping"])  # type: ignore[arg-type]


def test_event_bus_chain_detects_internal_tampering():
    bus = EventBus("mission_001")
    bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")
    original = bus._events[0]
    bus._events[0] = original.model_copy(update={"summary": "tampered"})

    assert bus.verify_chain() is False


def test_agent_trace_audit_accepts_terminal_hash_chain():
    bus = EventBus("mission_001")
    bus.append(
        AgentEventType.AGENT_INITIALIZED,
        "Initialized.",
        phase_before=AgentPhase.CREATED,
        phase_after=AgentPhase.INITIALIZED,
    )
    bus.append(
        AgentEventType.CONTEXT_BUILT,
        "Context built.",
        phase_before=AgentPhase.INITIALIZED,
        phase_after=AgentPhase.CONTEXT_BUILDING,
    )
    bus.append(
        AgentEventType.AGENT_BLOCKED,
        "Blocked.",
        phase_before=AgentPhase.CONTEXT_BUILDING,
        phase_after=AgentPhase.BLOCKED,
    )

    audit = audit_agent_trace(bus.events())

    assert audit.accepted is True
    assert audit.integrity_ok is True
    assert audit.mission_id == "mission_001"
    assert audit.final_event_type == AgentEventType.AGENT_BLOCKED
    assert audit.final_phase == AgentPhase.BLOCKED
    assert audit.phase_path == [AgentPhase.CREATED, AgentPhase.INITIALIZED, AgentPhase.CONTEXT_BUILDING, AgentPhase.BLOCKED]


def test_agent_trace_audit_rejects_non_terminal_trace():
    bus = EventBus("mission_001")
    bus.append(
        AgentEventType.AGENT_INITIALIZED,
        "Initialized.",
        phase_before=AgentPhase.CREATED,
        phase_after=AgentPhase.INITIALIZED,
    )

    audit = audit_agent_trace(bus.events())

    assert audit.accepted is False
    assert "trace_not_terminal" in audit.errors
    assert "terminal_event_missing" in audit.errors


def test_agent_trace_audit_rejects_tampered_trace():
    bus = EventBus("mission_001")
    bus.append(
        AgentEventType.AGENT_FAILED,
        "Failed.",
        phase_before=AgentPhase.LEARNING_PROPOSING,
        phase_after=AgentPhase.FAILED,
    )
    original = bus._events[0]
    bus._events[0] = original.model_copy(update={"summary": "tampered"})

    audit = audit_agent_trace(bus.events())

    assert audit.accepted is False
    assert "hash_chain_invalid" in audit.errors
