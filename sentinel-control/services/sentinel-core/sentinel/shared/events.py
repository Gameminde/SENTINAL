"""Shared event primitives for the Sentinel platform.

Task 13 / Requirement 13 — Event Bus Primitives Layer Extraction (F-A2.2).

This module is the single home for the event-ledger primitives:

* :class:`AgentPhase` — pure phase label enum (cognitive state-machine rules
  like ``ALLOWED_PHASE_TRANSITIONS`` remain in :mod:`sentinel.agent.phases`).
* :class:`AgentEventType` — event-type enum.
* :class:`AgentEvent` — frozen pydantic model used as the ledger row type.
* :class:`TraceIntegrityError` — raised by :class:`EventBus` on per-append
  integrity failure (Task 7 / Requirement 7).
* :class:`EventBus` — the hash-chained truth ledger. ``append`` uses an O(1)
  tail-integrity fast path and falls back to full-chain audit only when the
  private ledger list has been externally mutated.

Layering rule
-------------
``sentinel.shared.events`` MUST NOT import anything from ``sentinel.agent.*``
or ``sentinel.mission.*`` or ``sentinel.organs.*``. It is the canonical
downward-facing layer for event-ledger primitives. Organs and the agent
cognitive layer both import *from* here.

Backward compatibility is preserved via re-export shims in
``sentinel.agent.events``, ``sentinel.agent.event_bus``, and
``sentinel.agent.exceptions``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, field_serializer, field_validator

from sentinel.shared.models import SentinelModel, new_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenDict(dict):
    """JSON-compatible immutable dict used for event payloads."""

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("AgentEvent payload is immutable.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenDict:
        return self


class FrozenList(list):
    """JSON-compatible immutable list used for nested event payload values."""

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("AgentEvent payload is immutable.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    clear = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenList:
        return self


def _freeze_nested(value: Any) -> Any:
    if isinstance(value, (FrozenDict, FrozenList)):
        return value
    if isinstance(value, dict):
        return FrozenDict({str(key): _freeze_nested(item) for key, item in value.items()})
    if isinstance(value, list | tuple | set):
        return FrozenList([_freeze_nested(item) for item in value])
    return value


def _thaw_nested(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_nested(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_thaw_nested(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# AgentPhase — moved from sentinel/agent/phases.py. The cognitive
# state-machine helpers (``can_transition``, ``ALLOWED_PHASE_TRANSITIONS``,
# ``ABSORBING_PHASES``) remain in the agent layer because they encode
# cognitive-cycle rules, not platform primitives.
# ---------------------------------------------------------------------------


class AgentPhase(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    CONTEXT_BUILDING = "context_building"
    ORIENTING = "orienting"
    METHOD_SELECTING = "method_selecting"
    CAPABILITY_SELECTING = "capability_selecting"
    TOOL_SELECTING = "tool_selecting"
    HYPOTHESIS_VERIFYING = "hypothesis_verifying"
    ACTION_SCORING = "action_scoring"
    EFFORT_ROUTING = "effort_routing"
    PLANNING = "planning"
    PLAN_REVIEWING = "plan_reviewing"
    EXECUTING = "executing"
    ARTIFACT_REVIEWING = "artifact_reviewing"
    REPAIRING = "repairing"
    SUCCESS_EVALUATING = "success_evaluating"
    LEARNING_PROPOSING = "learning_proposing"
    ORGAN_DISPATCHING = "organ_dispatching"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    PAUSED = "paused"
    STOPPED = "stopped"
    REVOKED = "revoked"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# AgentEventType — moved verbatim from sentinel/agent/events.py.
# ---------------------------------------------------------------------------


class AgentEventType(StrEnum):
    AGENT_INITIALIZED = "agent_initialized"
    EXECUTION_POSTURE_SELECTED = "execution_posture_selected"
    CONTEXT_BUILT = "context_built"
    CONTEXT_COMPRESSED = "context_compressed"
    ORIENTATION_COMPLETED = "orientation_completed"
    METHODS_SELECTED = "methods_selected"
    CAPABILITIES_SELECTED = "capabilities_selected"
    TOOL_CALL_CANONICALIZED = "tool_call_canonicalized"
    CONTEXT_PACK_ASSEMBLED = "context_pack_assembled"
    CONTEXT_PACK_VALIDATED = "context_pack_validated"
    CONTEXT_PACK_REJECTED = "context_pack_rejected"
    CONTEXT_PACK_REHYDRATED = "context_pack_rehydrated"
    TOOL_INTENT_COMPILED = "tool_intent_compiled"
    TOOL_INTENT_COMPILATION_REJECTED = "tool_intent_compilation_rejected"
    LLM_REASONING_DRAFTED = "llm_reasoning_drafted"
    LLM_VERIFICATION_DRAFTED = "llm_verification_drafted"
    TOOL_POLICY_DECIDED = "tool_policy_decided"
    TOOLS_SELECTED = "tools_selected"
    BROWSER_URL_CLASSIFIED = "browser_url_classified"
    BROWSER_EVIDENCE_COLLECTED = "browser_evidence_collected"
    BROWSER_EVIDENCE_REJECTED = "browser_evidence_rejected"
    BROWSER_SNAPSHOT_CAPTURED = "browser_snapshot_captured"
    BROWSER_SNAPSHOT_REJECTED = "browser_snapshot_rejected"
    BROWSER_INTERACTION_PLAN_CREATED = "browser_interaction_plan_created"
    BROWSER_INTERACTION_EXECUTED = "browser_interaction_executed"
    BROWSER_INTERACTION_REJECTED = "browser_interaction_rejected"
    BROWSER_PUBLIC_SESSION_STARTED = "browser_public_session_started"
    BROWSER_PUBLIC_TAB_OPENED = "browser_public_tab_opened"
    BROWSER_PUBLIC_TAB_NAVIGATED = "browser_public_tab_navigated"
    BROWSER_PUBLIC_TAB_CLOSED = "browser_public_tab_closed"
    BROWSER_PUBLIC_SESSION_CLOSED = "browser_public_session_closed"
    BROWSER_PUBLIC_LIFECYCLE_REJECTED = "browser_public_lifecycle_rejected"
    BROWSER_POOL_LEASED = "browser_pool_leased"
    BROWSER_POOL_RELEASED = "browser_pool_released"
    BROWSER_HEALTH_CHECKED = "browser_health_checked"
    BROWSER_OPERATION_RETRIED = "browser_operation_retried"
    BROWSER_SUPERVISOR_REJECTED = "browser_supervisor_rejected"
    BROWSER_UI_OBSERVATION_CAPTURED = "browser_ui_observation_captured"
    BROWSER_UI_OBSERVATION_REJECTED = "browser_ui_observation_rejected"
    BROWSER_CDP_AX_TREE_CAPTURED = "browser_cdp_ax_tree_captured"
    BROWSER_DOM_SNAPSHOT_CAPTURED = "browser_dom_snapshot_captured"
    BROWSER_VISUAL_OBSERVATION_CAPTURED = "browser_visual_observation_captured"
    BROWSER_ADVANCED_POOL_STARTED = "browser_advanced_pool_started"
    BROWSER_ADVANCED_POOL_LEASED = "browser_advanced_pool_leased"
    BROWSER_ADVANCED_POOL_RELEASED = "browser_advanced_pool_released"
    BROWSER_MULTITAB_STRATEGY_EXECUTED = "browser_multitab_strategy_executed"
    BROWSER_VERIFICATION_COMPLETED = "browser_verification_completed"
    BROWSER_LOOP_DETECTED = "browser_loop_detected"
    BROWSER_FORM_SUBMIT_EXECUTED = "browser_form_submit_executed"
    BROWSER_FORM_SUBMIT_REJECTED = "browser_form_submit_rejected"
    BROWSER_DOWNLOAD_QUARANTINED = "browser_download_quarantined"
    BROWSER_DOWNLOAD_REJECTED = "browser_download_rejected"
    BROWSER_UPLOAD_AUTHORIZED_EXECUTED = "browser_upload_authorized_executed"
    BROWSER_UPLOAD_AUTHORIZED_REJECTED = "browser_upload_authorized_rejected"
    BROWSER_PRIVATE_SESSION_STARTED = "browser_private_session_started"
    BROWSER_PRIVATE_SESSION_CLOSED = "browser_private_session_closed"
    BROWSER_PRIVATE_SESSION_REJECTED = "browser_private_session_rejected"
    BROWSER_LOGIN_AUTHORITY_EXECUTED = "browser_login_authority_executed"
    BROWSER_LOGIN_AUTHORITY_REJECTED = "browser_login_authority_rejected"
    BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED = "browser_cookie_storage_contract_applied"
    BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED = "browser_cookie_storage_contract_rejected"
    BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED = "browser_js_evaluate_sandboxed_executed"
    BROWSER_JS_EVALUATE_SANDBOXED_REJECTED = "browser_js_evaluate_sandboxed_rejected"
    BROWSER_HAR_BODY_CAPTURED = "browser_har_body_captured"
    BROWSER_HAR_BODY_CAPTURE_REJECTED = "browser_har_body_capture_rejected"
    BROWSER_OPERATOR_ROUTE_STARTED = "browser_operator_route_started"
    BROWSER_OPERATOR_ROUTE_PREPARED = "browser_operator_route_prepared"
    BROWSER_OPERATOR_ROUTE_COMPLETED = "browser_operator_route_completed"
    BROWSER_OPERATOR_ROUTE_REJECTED = "browser_operator_route_rejected"
    BROWSER_CORTEX_INTERPRETED = "browser_cortex_interpreted"
    BROWSER_ORGAN_POWER_GOVERNED = "browser_organ_power_governed"
    BROWSER_ORGAN_MISUSE_CLASSIFIED = "browser_organ_misuse_classified"
    BROWSER_ORGAN_RECEIPT_RECORDED = "browser_organ_receipt_recorded"
    BROWSER_ORGAN_DETECTION_BENCH_RUN = "browser_organ_detection_bench_run"
    HYPOTHESES_GENERATED = "hypotheses_generated"
    HYPOTHESES_VERIFIED = "hypotheses_verified"
    HYPOTHESES_REVIEWED = "hypotheses_reviewed"
    WORLD_MODEL_SIMULATED = "world_model_simulated"
    OBJECTIVE_SCORED = "objective_scored"
    MISSION_ENTROPY_ESTIMATED = "mission_entropy_estimated"
    AGENT_COUNT_ROUTED = "agent_count_routed"
    AGENT_SOCIETY_PLANNED = "agent_society_planned"
    AGENT_ROLE_ASSIGNED = "agent_role_assigned"
    WORKSPACE_SNAPSHOT_CREATED = "workspace_snapshot_created"
    WORKSPACE_BROADCAST_PREPARED = "workspace_broadcast_prepared"
    WORKSPACE_DELTA_APPLIED = "workspace_delta_applied"
    BELIEF_STATE_UPDATED = "belief_state_updated"
    DEBATE_ROUTED = "debate_routed"
    MOA_LAYER_COMPLETED = "moa_layer_completed"
    DEBATE_AGGREGATED = "debate_aggregated"
    EPISTEMIC_ACTION_SCORED = "epistemic_action_scored"
    RESOURCEFULNESS_ROUTED = "resourcefulness_routed"
    FALLBACK_PLAN_CREATED = "fallback_plan_created"
    TOOL_SUBSTITUTION_PROPOSED = "tool_substitution_proposed"
    PARTIAL_SUCCESS_DECLARED = "partial_success_declared"
    AUTHORITY_EXTENSION_PROPOSED = "authority_extension_proposed"
    SKILL_PROCEDURE_MATCHED = "skill_procedure_matched"
    BRAINBENCH_CASE_RUN = "brainbench_case_run"
    BRAINBENCH_REPORT_CREATED = "brainbench_report_created"
    ORGAN_CONTRACT_REGISTERED = "organ_contract_registered"
    ORGAN_AUTHORITY_EVALUATED = "organ_authority_evaluated"
    ORGAN_RISK_PROFILED = "organ_risk_profiled"
    ORGAN_DRY_RUN_RECORDED = "organ_dry_run_recorded"
    ORGAN_EXECUTION_RECEIPT_RECORDED = "organ_execution_receipt_recorded"
    ORGAN_PROMOTION_EVALUATED = "organ_promotion_evaluated"
    ORGAN_KILL_SWITCH_TRIGGERED = "organ_kill_switch_triggered"
    ORGAN_HARVEST_REFERENCE_RECORDED = "organ_harvest_reference_recorded"
    ORGAN_HARVEST_CANDIDATE_CLASSIFIED = "organ_harvest_candidate_classified"
    ORGAN_HARVEST_MATRIX_BUILT = "organ_harvest_matrix_built"
    ORGAN_IMPLEMENTATION_ALIGNMENT_BUILT = "organ_implementation_alignment_built"
    DESKTOP_AGENTLAB_HARVEST_BUILT = "desktop_agentlab_harvest_built"
    DESKTOP_SIDECAR_BLUEPRINT_BUILT = "desktop_sidecar_blueprint_built"
    EXTERNAL_API_REQUEST_PLANNED = "external_api_request_planned"
    EXTERNAL_API_DRY_RUN_RECORDED = "external_api_dry_run_recorded"
    CHANNEL_DRAFT_CREATED = "channel_draft_created"
    CHANNEL_SEND_GATED = "channel_send_gated"
    CHANNEL_INBOUND_CLASSIFIED = "channel_inbound_classified"
    CREDENTIAL_REF_REGISTERED = "credential_ref_registered"
    CREDENTIAL_GRANT_EVALUATED = "credential_grant_evaluated"
    CREDENTIAL_GRANT_REVOKED = "credential_grant_revoked"
    CAPITAL_SIGNAL_RECORDED = "capital_signal_recorded"
    CAPITAL_BUDGET_REALLOCATED = "capital_budget_reallocated"
    CAPITAL_SPEND_PROPOSED = "capital_spend_proposed"
    SPEND_REQUEST_EVALUATED = "spend_request_evaluated"
    SPEND_RECEIPT_RECORDED = "spend_receipt_recorded"
    SPEND_KILL_SWITCH_TRIGGERED = "spend_kill_switch_triggered"
    TRADING_AUTHORITY_EVALUATED = "trading_authority_evaluated"
    PAPER_TRADE_RECORDED = "paper_trade_recorded"
    TRADING_RECEIPT_RECORDED = "trading_receipt_recorded"
    TRADINGAGENTS_PATTERN_HARVESTED = "tradingagents_pattern_harvested"
    TRADING_FIRM_PLAN_CREATED = "trading_firm_plan_created"
    TRADING_SIGNAL_PARSED = "trading_signal_parsed"
    TRADING_DATA_VENDOR_ROUTED = "trading_data_vendor_routed"
    TRADING_OUTCOME_MEMORY_RECORDED = "trading_outcome_memory_recorded"
    EFFORT_ROUTED = "effort_routed"
    PLAN_CREATED = "plan_created"
    PLAN_REVIEWED = "plan_reviewed"
    WORKER_STARTED = "worker_started"
    WORKER_COMPLETED = "worker_completed"
    ARTIFACT_CAPTURED = "artifact_captured"
    ARTIFACT_CAPTURE_DUPLICATE = "artifact_capture_duplicate"
    ARTIFACT_CAPTURE_REJECTED = "artifact_capture_rejected"
    ARTIFACT_CAPTURE_INDEX_WRITTEN = "artifact_capture_index_written"
    CONTROLLED_CAPABILITY_EXECUTED = "controlled_capability_executed"
    CONTROLLED_CAPABILITY_REJECTED = "controlled_capability_rejected"
    ARTIFACTS_REVIEWED = "artifacts_reviewed"
    REPAIR_DECIDED = "repair_decided"
    REPAIR_EXECUTED = "repair_executed"
    SUCCESS_EVALUATED = "success_evaluated"
    LEARNING_PROPOSED = "learning_proposed"
    EVIDENCE_CHAIN_BUILT = "evidence_chain_built"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_BLOCKED = "agent_blocked"
    AGENT_ESCALATED = "agent_escalated"
    AGENT_REVOKED = "agent_revoked"

    # ------------------------------------------------------------------
    # sentinel-performance-runtime-foundation (Task 1.2) — additive
    # event families. Appended at the end to preserve the existing
    # member order/values above. New members only; nothing renamed,
    # renumbered, reordered, or removed.
    # ------------------------------------------------------------------

    # Performance (Req 1.6, 12.8)
    PERFORMANCE_TRACE_EMITTED = "performance_trace_emitted"
    PERFORMANCE_RECEIPT_RECORDED = "performance_receipt_recorded"

    # Cache (Req 2.5, 3.6)
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_EVICTED = "cache_evicted"
    CACHE_CORRECTNESS_VIOLATION = "cache_correctness_violation"
    CACHE_INVALIDATION_BULK_WARNING = "cache_invalidation_bulk_warning"

    # Cold-Store (Req 4.4, 5.7, 5.8)
    COLD_STORE_PERSISTENCE_FAILED = "cold_store_persistence_failed"
    RECEIPT_INDEX_INCONSISTENCY = "receipt_index_inconsistency"
    RECEIPT_INDEX_HEALTH_CHECK = "receipt_index_health_check"

    # Artifact (Req 6.6, 6.7, 6.8, 12.4)
    ARTIFACT_INTEGRITY_ERROR = "artifact_integrity_error"
    ARTIFACT_REJECTED = "artifact_rejected"

    # Queue/Backpressure (Req 8.2, 8.4, 8.6, 8.7)
    QUEUE_BACKPRESSURE_APPLIED = "queue_backpressure_applied"
    QUEUE_BACKPRESSURE_CLEARED = "queue_backpressure_cleared"

    # Budget (Req 10.3, 10.5, 10.7, 10.8)
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_EXHAUSTED = "budget_exhausted"

    # Organ-Action (Req 7.4, 7.5, 7.8)
    ORGAN_ACTION_TIMEOUT = "organ_action_timeout"
    ORGAN_ACTION_FAILED = "organ_action_failed"
    ORGAN_ACTION_CANCELLED = "organ_action_cancelled"

    # Organ-Dispatch (SENTINEL-POWER-ACTIVATION-01 wiring)
    ORGAN_DISPATCH_COMPLETED = "organ_dispatch_completed"
    ORGAN_DISPATCH_SKIPPED = "organ_dispatch_skipped"

    # Authority/KillSwitch (Req 12.5, 12.7)
    AUTHORITY_VIOLATION = "authority_violation"
    KILL_SWITCH_BLOCKED = "kill_switch_blocked"


# ---------------------------------------------------------------------------
# TraceIntegrityError — moved from sentinel/agent/exceptions.py.
# ---------------------------------------------------------------------------


class TraceIntegrityError(RuntimeError):
    """Raised when the EventBus detects mid-run tampering on append.

    Task 7 / Requirement 7 (F-A3.3, CP-7.1 Immediate Detection).

    Before each :meth:`EventBus.append` commits a new event, the full existing
    chain is re-verified. If a previous event has been mutated (e.g. via
    ``model_copy`` replacement in ``_events``, or via ``object.__setattr__``
    bypassing pydantic freezing), the ``previous_hash`` anchor the new event
    would use is no longer consistent. This error is raised immediately so
    the tampered state cannot be hidden behind a fresh append.

    :meth:`EventBus.verify_chain` remains as a belt-and-braces full-chain
    audit (CP-7.2 Chain Integrity).
    """


# ---------------------------------------------------------------------------
# AgentEvent — moved from sentinel/agent/models.py.
# ---------------------------------------------------------------------------


class AgentEvent(SentinelModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: new_id("aev"))
    mission_id: str
    sequence: int = Field(ge=0)
    logical_time: int = Field(ge=0)
    event_type: AgentEventType
    phase_before: AgentPhase | None = None
    phase_after: AgentPhase | None = None
    actor: str = "sentinel_agent"
    summary: str
    payload: Any = Field(default_factory=dict)
    trace_refs: tuple[str, ...] = Field(default_factory=tuple)
    parent_event_id: str | None = None
    previous_hash: str | None = None
    event_hash: str
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("payload", mode="before")
    @classmethod
    def _freeze_payload(cls, value: Any) -> Any:
        if value is None:
            value = {}
        if not isinstance(value, Mapping):
            raise ValueError("AgentEvent payload must be a mapping.")
        return _freeze_nested(value)

    @field_serializer("payload")
    def _serialize_payload(self, value: Any) -> dict[str, Any]:
        return _thaw_nested(value)

    @field_validator("trace_refs", mode="before")
    @classmethod
    def _freeze_trace_refs(cls, value: Any) -> tuple[str, ...]:
        return tuple(str(item) for item in (value or []))


# ---------------------------------------------------------------------------
# EventBus — moved from sentinel/agent/event_bus.py. Task 7 per-append
# chain integrity check preserved.
# ---------------------------------------------------------------------------


class _TrackedEventList(list["AgentEvent"]):
    """Private ledger list that marks external mutations dirty.

    EventBus itself appends through ``append_untracked``. Direct private-list
    mutations in tests or adversarial code mark the list dirty so the next
    public append can run a full-chain audit without imposing O(n) work on
    every normal append.
    """

    dirty: bool

    def __init__(self) -> None:
        super().__init__()
        self.dirty = False

    def append_untracked(self, event: "AgentEvent") -> None:
        super().append(event)

    def mark_clean(self) -> None:
        self.dirty = False

    def _mark_dirty(self) -> None:
        self.dirty = True

    def __setitem__(self, key: Any, value: Any) -> None:
        self._mark_dirty()
        super().__setitem__(key, value)

    def __delitem__(self, key: Any) -> None:
        self._mark_dirty()
        super().__delitem__(key)

    def append(self, value: Any) -> None:
        self._mark_dirty()
        super().append(value)

    def extend(self, values: Any) -> None:
        self._mark_dirty()
        super().extend(values)

    def insert(self, index: int, value: Any) -> None:
        self._mark_dirty()
        super().insert(index, value)

    def pop(self, index: int = -1) -> Any:
        self._mark_dirty()
        return super().pop(index)

    def clear(self) -> None:
        self._mark_dirty()
        super().clear()

    def remove(self, value: Any) -> None:
        self._mark_dirty()
        super().remove(value)

    def reverse(self) -> None:
        self._mark_dirty()
        super().reverse()

    def sort(self, *args: Any, **kwargs: Any) -> None:
        self._mark_dirty()
        super().sort(*args, **kwargs)

    def __iadd__(self, values: Any) -> "_TrackedEventList":
        self._mark_dirty()
        return super().__iadd__(values)


class EventBus:
    def __init__(self, mission_id: str) -> None:
        self.mission_id = mission_id
        self._events: _TrackedEventList = _TrackedEventList()
        self._last_hash: str | None = None

    def append(
        self,
        event_type: AgentEventType,
        summary: str,
        *,
        phase_before: AgentPhase | None = None,
        phase_after: AgentPhase | None = None,
        payload: dict[str, Any] | None = None,
        trace_refs: list[str] | None = None,
        parent_event_id: str | None = None,
        actor: str = "sentinel_agent",
        copy_payload: bool = True,
    ) -> AgentEvent:
        self._assert_append_integrity()
        sequence = len(self._events)
        event_data = {
            "id": new_id("aev"),
            "mission_id": self.mission_id,
            "sequence": sequence,
            "logical_time": sequence,
            "event_type": event_type,
            "phase_before": phase_before,
            "phase_after": phase_after,
            "actor": actor,
            "summary": summary,
            "payload": deepcopy(payload) if payload is not None and copy_payload else (payload or {}),
            "trace_refs": list(trace_refs) if trace_refs is not None else [],
            "parent_event_id": parent_event_id,
            "previous_hash": self._last_hash,
            "event_hash": "",
            "created_at": datetime.now(UTC),
        }
        hash_payload = dict(event_data)
        hash_payload.pop("event_hash", None)
        event_hash = self._hash_unfrozen_payload(hash_payload)
        event_data["event_hash"] = event_hash
        event = AgentEvent(**event_data)
        self._events.append_untracked(event)
        self._last_hash = event_hash
        return event

    def _assert_append_integrity(self) -> None:
        """Fast integrity gate before linking a new event.

        Normal appends verify only the tail anchor and tail hash. If the
        private ledger list was externally mutated, the next append pays the
        full-chain audit cost and refuses to append onto a tampered chain.
        """
        if self._events.dirty:
            self._assert_chain_integrity()
            self._events.mark_clean()
            return
        if not self._events:
            if self._last_hash is not None:
                raise TraceIntegrityError(
                    "trace_integrity_error: EventBus tail anchor is set but "
                    "no events are stored; refusing to append."
                )
            return
        tail = self._events[-1]
        if tail.sequence != len(self._events) - 1 or tail.logical_time != len(self._events) - 1:
            raise TraceIntegrityError(
                "trace_integrity_error: EventBus tail event has "
                "non-monotonic sequence/logical_time."
            )
        expected_previous = self._events[-2].event_hash if len(self._events) > 1 else None
        if tail.previous_hash != expected_previous:
            raise TraceIntegrityError(
                "trace_integrity_error: EventBus tail previous_hash does not "
                "match prior event_hash."
            )
        event_data = tail.model_dump()
        stored_hash = event_data.pop("event_hash")
        if self._hash_payload(event_data) != stored_hash:
            raise TraceIntegrityError(
                "trace_integrity_error: EventBus tail stored event_hash does "
                "not match recomputed hash; refusing to append."
            )
        if self._last_hash != stored_hash:
            raise TraceIntegrityError(
                "trace_integrity_error: EventBus tail anchor does not match "
                "the chain's terminal event_hash."
            )

    def _assert_chain_integrity(self) -> None:
        """Verify the current chain for audit or dirty-list recovery.

        This O(len(events)) check is used by ``verify_chain`` semantics and by
        ``append`` only when the private ledger list has been externally
        mutated. Normal append traffic uses ``_assert_append_integrity``.
        """
        if not self._events:
            if self._last_hash is not None:
                raise TraceIntegrityError(
                    "trace_integrity_error: EventBus tail anchor is set but "
                    "no events are stored; refusing to append."
                )
            return
        previous_hash: str | None = None
        for index, event in enumerate(self._events):
            if event.sequence != index or event.logical_time != index:
                raise TraceIntegrityError(
                    f"trace_integrity_error: event at position {index} has "
                    "non-monotonic sequence/logical_time."
                )
            if event.previous_hash != previous_hash:
                raise TraceIntegrityError(
                    f"trace_integrity_error: event at position {index} "
                    "previous_hash does not match prior event_hash."
                )
            event_data = event.model_dump()
            stored_hash = event_data.pop("event_hash")
            recomputed = self._hash_payload(event_data)
            if recomputed != stored_hash:
                raise TraceIntegrityError(
                    f"trace_integrity_error: event at position {index} "
                    "stored event_hash does not match recomputed hash; "
                    "refusing to append onto a tampered chain."
                )
            previous_hash = stored_hash
        if self._last_hash != previous_hash:
            raise TraceIntegrityError(
                "trace_integrity_error: EventBus tail anchor does not match "
                "the chain's terminal event_hash."
            )

    def events(self) -> tuple[AgentEvent, ...]:
        return tuple(self._events)

    def last(self) -> AgentEvent | None:
        return self._events[-1] if self._events else None

    def verify_chain(self) -> bool:
        return self.verify_events(self._events)

    @classmethod
    def verify_events(cls, events: Iterable[AgentEvent]) -> bool:
        previous_hash: str | None = None
        for index, event in enumerate(events):
            if event.sequence != index or event.logical_time != index:
                return False
            if event.previous_hash != previous_hash:
                return False
            event_data = event.model_dump()
            event_hash = event_data.pop("event_hash")
            if cls._hash_payload(event_data) != event_hash:
                return False
            previous_hash = event_hash
        return True

    @staticmethod
    def _hash_payload(payload: Mapping[str, Any]) -> str:
        serializable = _thaw_nested(payload)
        serializable.pop("event_hash", None)
        canonical = json.dumps(serializable, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_unfrozen_payload(payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "AgentEvent",
    "AgentEventType",
    "AgentPhase",
    "EventBus",
    "TraceIntegrityError",
    "utc_now",
]
