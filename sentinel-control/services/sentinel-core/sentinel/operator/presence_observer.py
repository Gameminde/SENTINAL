from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.browser_cortex_divergence_harness import build_browser_cortex_divergence_trace
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_ref, sanitize_operator_refs
from sentinel.shared.models import SentinelModel


_MAX_SUMMARY_CHARS = 360
_MAX_SAFE_ITEMS = 48
_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|/(?:Users|home|root|tmp|var|workspace)/)", re.IGNORECASE)
_SAFE_LABEL_PATTERN = re.compile(r"[^A-Za-z0-9_.:/-]+")
_FORBIDDEN_KEY_MARKERS = (
    "chain_of_thought",
    "private_chain",
    "private_thought",
    "raw_browser",
    "raw_dom",
    "raw_exception",
    "raw_prompt",
    "raw_provider",
    "reasoning",
    "system_prompt",
)
_SECRET_KEY_MARKERS = (
    "api_key",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "refresh_token",
    "secret",
    "session_token",
    "token",
)
_PROVIDER_METADATA_KEYS = (
    "provider_id",
    "backend_id",
    "model_id",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cost_micro_usd",
)
_NORMALIZED_DECISION_KEYS = (
    "capability_id",
    "operation",
    "params_hash",
    "target_ref_hash",
    "trusted_runtime_fields_available",
    "action_envelope_internal",
)


class PresenceState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    SLEEPING = "SLEEPING"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    OBSERVING = "OBSERVING"
    ACTING = "ACTING"
    VERIFYING = "VERIFYING"
    WAITING_AUTHORITY = "WAITING_AUTHORITY"
    RECOVERING = "RECOVERING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    KILLED = "KILLED"
    TELEMETRY_INCOMPLETE = "TELEMETRY_INCOMPLETE"


class PresenceEventKind(StrEnum):
    MISSION = "MISSION"
    DECISION = "DECISION"
    ACTION = "ACTION"
    OBSERVATION = "OBSERVATION"
    PROOF = "PROOF"
    BLOCKER = "BLOCKER"
    GATE = "GATE"
    TERMINAL = "TERMINAL"
    CLEANUP = "CLEANUP"
    TELEMETRY = "TELEMETRY"


class TelemetryState(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "TELEMETRY_INCOMPLETE"


class PresenceSequenceError(ValueError):
    pass


class PresenceEventV1(SentinelModel):
    """Read-only, hash-bound projection of already-persisted mission truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["presence_event_v1"] = "presence_event_v1"
    event_id: str = ""
    mission_id: str
    sequence: int = Field(ge=0)
    source_sequence: int = Field(ge=0)
    decision_index: int = Field(default=0, ge=0)
    timestamp: str
    presence_state: PresenceState
    event_kind: PresenceEventKind
    safe_summary: str = Field(min_length=1, max_length=_MAX_SUMMARY_CHARS)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    context_pack_ref: str = ""
    context_pack_hash: str = ""
    available_affordances: list[str] = Field(default_factory=list)
    normalized_decision: dict[str, Any] = Field(default_factory=dict)
    dispatch_status: str = ""
    product_receipt_ref: str = ""
    browser_receipt_ref: str = ""
    before_state_fingerprint: str = ""
    after_state_fingerprint: str = ""
    before_evidence_fingerprint: str = ""
    after_evidence_fingerprint: str = ""
    material_progress: bool | None = None
    authority_state: str = "not_present_in_safe_projection"
    blocker: str = ""
    gate_results: dict[str, str] = Field(default_factory=dict)
    first_causal_divergence_ref: str = ""
    telemetry_state: TelemetryState = TelemetryState.COMPLETE
    ledger_head: str
    source_event_hash: str
    event_hash: str = ""
    data_not_authority: bool = True
    authority_effect: Literal["none"] = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _enforce_read_only_hash_bound_projection(self) -> "PresenceEventV1":
        if (
            not self.data_not_authority
            or self.authority_effect != "none"
            or self.can_grant_authority
            or self.can_execute
        ):
            raise ValueError("presence_event_v1 is data only and cannot grant authority or execute")
        if not self.mission_id or _PATH_PATTERN.search(self.mission_id):
            raise ValueError("presence_event_v1 mission_id is not a safe reference")
        if redact_operator_text(self.safe_summary) != self.safe_summary or _PATH_PATTERN.search(self.safe_summary):
            raise ValueError("presence_event_v1 safe_summary contains forbidden material")
        payload = self.model_dump(mode="json", exclude={"event_id", "event_hash"})
        expected_id = f"presence_event_{stable_hash(payload)[:32]}"
        if self.event_id and self.event_id != expected_id:
            raise ValueError("presence_event_v1 deterministic event_id mismatch")
        if not self.event_id:
            object.__setattr__(self, "event_id", expected_id)
        expected_hash = stable_hash({**payload, "event_id": expected_id})
        if self.event_hash and self.event_hash != expected_hash:
            raise ValueError("presence_event_v1 event_hash mismatch")
        if not self.event_hash:
            object.__setattr__(self, "event_hash", expected_hash)
        return self


class PresenceReplayArchiveV1(SentinelModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["presence_replay_archive_v1"] = "presence_replay_archive_v1"
    mission_id: str
    events: tuple[PresenceEventV1, ...]
    route_view: tuple[dict[str, Any], ...]
    xray_view: tuple[dict[str, Any], ...]
    first_causal_divergence: dict[str, Any]
    replay_metadata: dict[str, Any]
    source_artifact_hashes: dict[str, str]
    archive_hash: str = ""
    data_not_authority: bool = True
    authority_effect: Literal["none"] = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _hash_archive(self) -> "PresenceReplayArchiveV1":
        if (
            not self.data_not_authority
            or self.authority_effect != "none"
            or self.can_grant_authority
            or self.can_execute
        ):
            raise ValueError("presence replay archive is data only")
        payload = self.model_dump(mode="json", exclude={"archive_hash"})
        expected = stable_hash(payload)
        if self.archive_hash and self.archive_hash != expected:
            raise ValueError("presence replay archive hash mismatch")
        if not self.archive_hash:
            object.__setattr__(self, "archive_hash", expected)
        return self


class PresenceEventBuffer:
    """Strict mission-scoped ordering, idempotent deduplication and resume."""

    def __init__(self) -> None:
        self._events: dict[str, list[PresenceEventV1]] = {}

    def publish(self, event: PresenceEventV1) -> bool:
        mission_events = self._events.setdefault(event.mission_id, [])
        if event.sequence < len(mission_events):
            existing = mission_events[event.sequence]
            if existing.event_hash == event.event_hash:
                return False
            raise PresenceSequenceError(
                f"conflicting duplicate for {event.mission_id} sequence {event.sequence}"
            )
        expected = len(mission_events)
        if event.sequence != expected:
            raise PresenceSequenceError(
                f"expected sequence {expected} for {event.mission_id}, received {event.sequence}"
            )
        mission_events.append(event)
        return True

    def resume(self, *, mission_id: str, after_sequence: int = -1) -> tuple[PresenceEventV1, ...]:
        return tuple(
            event
            for event in self._events.get(mission_id, ())
            if event.sequence > after_sequence
        )


class PresenceSidecarRelay:
    """Best-effort relay whose failure never propagates into mission execution."""

    def __init__(self, sink: Callable[[PresenceEventV1], None]) -> None:
        self._sink = sink
        self.failure_count = 0
        self.last_failure_hash = ""

    def publish(self, event: PresenceEventV1) -> bool:
        try:
            self._sink(event)
        except Exception as exc:  # observer failure is deliberately isolated
            self.failure_count += 1
            self.last_failure_hash = stable_hash(
                {
                    "exception_class": exc.__class__.__name__,
                    "event_hash": event.event_hash,
                    "failure_count": self.failure_count,
                }
            )
            return False
        return True


class PresenceJsonlJournal:
    """Append-only safe transport journal owned by the observer sidecar."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._event_hashes: dict[tuple[str, int], str] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = PresenceEventV1.model_validate_json(line)
                key = (event.mission_id, event.sequence)
                existing = self._event_hashes.get(key)
                if existing is not None and existing != event.event_hash:
                    raise PresenceSequenceError(
                        f"conflicting journal duplicate for {event.mission_id} sequence {event.sequence}"
                    )
                self._event_hashes[key] = event.event_hash

    def append(self, event: PresenceEventV1) -> bool:
        rendered = json.dumps(
            event.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        data = f"{rendered}\n".encode("utf-8")
        with self._lock:
            key = (event.mission_id, event.sequence)
            existing = self._event_hashes.get(key)
            if existing == event.event_hash:
                return False
            if existing is not None:
                raise PresenceSequenceError(
                    f"conflicting journal duplicate for {event.mission_id} sequence {event.sequence}"
                )
            mission_sequences = [
                sequence
                for mission_id, sequence in self._event_hashes
                if mission_id == event.mission_id
            ]
            expected = max(mission_sequences, default=-1) + 1
            if event.sequence != expected:
                raise PresenceSequenceError(
                    f"expected journal sequence {expected} for {event.mission_id}, received {event.sequence}"
                )
            descriptor = os.open(
                self.path,
                os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                0o600,
            )
            try:
                offset = 0
                while offset < len(data):
                    written = os.write(descriptor, data[offset:])
                    if written <= 0:
                        raise OSError("presence journal append made no progress")
                    offset += written
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._event_hashes[key] = event.event_hash
            return True

    def resume(
        self,
        *,
        mission_id: str,
        after_sequence: int = -1,
    ) -> tuple[PresenceEventV1, ...]:
        if not self.path.exists():
            return ()
        events: list[PresenceEventV1] = []
        with self._lock:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = PresenceEventV1.model_validate_json(line)
                if event.mission_id == mission_id and event.sequence > after_sequence:
                    events.append(event)
        events.sort(key=lambda event: event.sequence)
        return tuple(events)


class PresenceSnapshotSidecar:
    """Append-only live observer over snapshots persisted by the runtime.

    The sidecar never calls the runtime. Re-reading an unchanged snapshot is
    idempotent, and a failed external relay leaves the local reconnect buffer
    intact without propagating into mission execution.
    """

    def __init__(
        self,
        relay: PresenceSidecarRelay,
        *,
        projector: "PresenceProjector | None" = None,
        buffer: PresenceEventBuffer | None = None,
    ) -> None:
        self._relay = relay
        self._projector = projector or PresenceProjector()
        self._buffer = buffer or PresenceEventBuffer()
        self._source_high_watermark: dict[str, int] = {}

    def observe(
        self,
        *,
        safe_evidence_snapshot: dict[str, Any],
        proof_index: dict[str, Any],
        mission_ledger: dict[str, Any] | None = None,
    ) -> int:
        archive = self._projector.project_replay(
            safe_evidence_snapshot=safe_evidence_snapshot,
            proof_index=proof_index,
            mission_ledger=mission_ledger,
        )
        high_watermark = self._source_high_watermark.get(archive.mission_id, -1)
        emitted = 0
        for event in archive.events:
            if event.source_sequence <= high_watermark:
                continue
            if self._buffer.publish(event):
                self._relay.publish(event)
                emitted += 1
            high_watermark = event.source_sequence
        self._source_high_watermark[archive.mission_id] = high_watermark
        return emitted

    def resume(self, *, mission_id: str, after_sequence: int = -1) -> tuple[PresenceEventV1, ...]:
        return self._buffer.resume(mission_id=mission_id, after_sequence=after_sequence)


class PresenceProjector:
    """Pure projector from persisted safe artifacts to Presence Protocol V1."""

    def project_replay(
        self,
        *,
        safe_evidence_snapshot: dict[str, Any],
        proof_index: dict[str, Any],
        mission_ledger: dict[str, Any] | None = None,
    ) -> PresenceReplayArchiveV1:
        snapshot = safe_evidence_snapshot if isinstance(safe_evidence_snapshot, dict) else {}
        index = proof_index if isinstance(proof_index, dict) else {}
        ledger = mission_ledger if isinstance(mission_ledger, dict) else {}
        source_events = _strict_source_events(snapshot)
        mission_id = _mission_id(snapshot=snapshot, proof_index=index, mission_ledger=ledger)
        divergence_trace = build_browser_cortex_divergence_trace(
            safe_evidence_snapshot=snapshot,
            proof_index=index,
            mission_ledger=ledger,
        )
        first_divergence = _safe_first_divergence(divergence_trace.get("first_causal_divergence"))
        decisions = {
            _safe_int(item.get("decision_index")): item
            for item in divergence_trace.get("decisions", [])
            if isinstance(item, dict) and _safe_int(item.get("decision_index")) > 0
        }
        receipts_by_product_ref = {
            _safe_ref(item.get("product_receipt_ref")): item
            for item in index.get("material_browser_receipts", [])
            if isinstance(item, dict) and _safe_ref(item.get("product_receipt_ref"))
        }
        divergence_ref = (
            f"divergence:{first_divergence['decision_index']}:"
            f"{_safe_label(first_divergence['classification'])}"
            if first_divergence["decision_index"] > 0
            else ""
        )
        events: list[PresenceEventV1] = []
        current_decision_index = 0
        current_provider_metadata: dict[str, Any] = {}
        accepting_finalgate_seen = False
        terminal_state: PresenceState | None = None

        for projected_sequence, source_event in enumerate(source_events):
            event_type = _safe_label(source_event.get("event_type"))
            payload = _safe_mapping(source_event.get("payload"))
            if event_type == "provider_decision_received":
                current_decision_index = (
                    _safe_int(payload.get("provider_decision_count"))
                    or current_decision_index + 1
                )
                current_provider_metadata = _provider_metadata(payload)
            decision = decisions.get(current_decision_index, {})
            event_kind = _event_kind(event_type)
            operation = _operation(payload=payload, decision=decision)
            trace_receipt = _safe_mapping(decision.get("receipt"))
            product_receipt_ref = _product_receipt_ref(payload=payload, receipt=trace_receipt)
            indexed_receipt = _safe_mapping(receipts_by_product_ref.get(product_receipt_ref))
            receipt = {**trace_receipt, **indexed_receipt}
            product_receipt_ref = (
                _safe_ref(receipt.get("product_receipt_ref"))
                or product_receipt_ref
            )
            browser_receipt_ref = _safe_ref(receipt.get("browser_receipt_ref"))
            telemetry_state = _telemetry_state(
                event_type=event_type,
                operation=operation,
                browser_receipt_ref=browser_receipt_ref,
                payload=payload,
            )
            gate_results = _gate_results(
                event_type=event_type,
                payload=payload,
                proof_index=index,
                accepting_finalgate_seen=accepting_finalgate_seen,
            )
            if event_type == "FinalGate_result" and _accepting_finalgate(payload):
                accepting_finalgate_seen = True
            presence_state = _presence_state(
                event_type=event_type,
                payload=payload,
                operation=operation,
                telemetry_state=telemetry_state,
                accepting_finalgate_seen=accepting_finalgate_seen,
                terminal_state=terminal_state,
            )
            if event_type == "terminal_verdict":
                terminal_state = presence_state
            elif event_type == "cleanup_result" and terminal_state is not None:
                presence_state = terminal_state
            progress = _safe_mapping(decision.get("progress"))
            normalized_decision = _normalized_decision(decision)
            source_event_hash = _safe_ref(source_event.get("event_hash")) or stable_hash(source_event)
            blocker = _safe_blocker(payload=payload, ledger=ledger, event_type=event_type)
            event = PresenceEventV1(
                mission_id=mission_id,
                sequence=projected_sequence,
                source_sequence=_safe_int(source_event.get("sequence")),
                decision_index=current_decision_index,
                timestamp=_safe_timestamp(source_event.get("created_at")),
                presence_state=presence_state,
                event_kind=event_kind,
                safe_summary=_safe_summary(
                    event_type=event_type,
                    event_kind=event_kind,
                    decision_index=current_decision_index,
                    operation=operation,
                    payload=payload,
                    telemetry_state=telemetry_state,
                    blocker=blocker,
                ),
                provider_metadata=current_provider_metadata,
                context_pack_ref=_context_pack_ref(payload),
                context_pack_hash=_context_pack_hash(payload=payload, decision=decision),
                available_affordances=_available_affordances(decision),
                normalized_decision=normalized_decision,
                dispatch_status=_dispatch_status(event_type=event_type, payload=payload, receipt=receipt),
                product_receipt_ref=product_receipt_ref,
                browser_receipt_ref=browser_receipt_ref,
                before_state_fingerprint=_safe_ref(
                    receipt.get("before_state_hash")
                    or decision.get("pre_state_fingerprint")
                ),
                after_state_fingerprint=_safe_ref(
                    receipt.get("after_state_hash")
                    or decision.get("post_state_fingerprint")
                ),
                before_evidence_fingerprint=_safe_ref(decision.get("evidence_fingerprint_before")),
                after_evidence_fingerprint=_safe_ref(decision.get("evidence_fingerprint_after")),
                material_progress=(
                    bool(progress.get("made_progress"))
                    if "made_progress" in progress
                    else None
                ),
                authority_state=_authority_state(payload),
                blocker=blocker,
                gate_results=gate_results,
                first_causal_divergence_ref=(
                    divergence_ref
                    if current_decision_index == first_divergence["decision_index"]
                    else ""
                ),
                telemetry_state=telemetry_state,
                ledger_head=source_event_hash,
                source_event_hash=source_event_hash,
            )
            events.append(event)

        route_view = tuple(_route_projection(event) for event in events)
        xray_view = tuple(_xray_projection(event) for event in events)
        return PresenceReplayArchiveV1(
            mission_id=mission_id,
            events=tuple(events),
            route_view=route_view,
            xray_view=xray_view,
            first_causal_divergence=first_divergence,
            replay_metadata={
                "replay_mode": "artifact_history_reconstruction",
                "history_reconstructed": True,
                "effect_reexecution_attempted": False,
                "reexecuted_actions": False,
                "model_calls_delta": 0,
                "provider_calls_delta": 0,
                "receipt_writes_delta": 0,
                "finalgate_writes_delta": 0,
            },
            source_artifact_hashes={
                "safe_evidence_snapshot": stable_hash(snapshot),
                "browser_proof_index": str(index.get("proof_index_hash") or stable_hash(index)),
                "mission_ledger": stable_hash(ledger),
                "divergence_trace": stable_hash(divergence_trace),
            },
        )


def _strict_source_events(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    events = snapshot.get("events")
    if not isinstance(events, list):
        raise PresenceSequenceError("safe evidence snapshot events must be a list")
    normalized = [item for item in events if isinstance(item, dict)]
    sequences = [_safe_int(item.get("sequence")) for item in normalized]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise PresenceSequenceError("source events must have strict unique ascending sequences")
    return normalized


def _mission_id(
    *,
    snapshot: dict[str, Any],
    proof_index: dict[str, Any],
    mission_ledger: dict[str, Any],
) -> str:
    candidate = (
        mission_ledger.get("mission_id")
        or snapshot.get("run_id")
        or proof_index.get("loop_id")
        or mission_ledger.get("task_id")
        or "unknown_mission"
    )
    return _safe_ref(candidate) or "unknown_mission"


def _safe_first_divergence(value: Any) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    evidence = _safe_mapping(item.get("evidence"))
    return {
        "decision_index": _safe_int(item.get("decision_index")),
        "classification": _safe_label(item.get("classification")) or "NO_CAUSAL_DIVERGENCE_IDENTIFIED",
        "evidence": _safe_allowlisted_mapping(
            evidence,
            (
                "failure_code",
                "failure_stage",
                "material_effect_observed",
                "operation",
                "suppression_count",
                "repetition_count",
                "pre_state_fingerprint",
                "evidence_fingerprint_before",
            ),
        ),
    }


def _event_kind(event_type: str) -> PresenceEventKind:
    return {
        "run_started": PresenceEventKind.MISSION,
        "provider_decision_received": PresenceEventKind.DECISION,
        "action_envelope_accepted": PresenceEventKind.ACTION,
        "browser_action_started": PresenceEventKind.OBSERVATION,
        "runtime_failure_fact_created": PresenceEventKind.BLOCKER,
        "model_visible_failure_packet_created": PresenceEventKind.TELEMETRY,
        "material_receipt_created": PresenceEventKind.PROOF,
        "browser_progress_repetition_detected": PresenceEventKind.BLOCKER,
        "browser_proof_index_created": PresenceEventKind.PROOF,
        "FinalGate_result": PresenceEventKind.GATE,
        "terminal_verdict": PresenceEventKind.TERMINAL,
        "cleanup_result": PresenceEventKind.CLEANUP,
    }.get(event_type, PresenceEventKind.TELEMETRY)


def _presence_state(
    *,
    event_type: str,
    payload: dict[str, Any],
    operation: str,
    telemetry_state: TelemetryState,
    accepting_finalgate_seen: bool,
    terminal_state: PresenceState | None,
) -> PresenceState:
    if event_type == "run_started":
        return PresenceState.UNDERSTANDING
    if event_type == "provider_decision_received":
        return PresenceState.PLANNING
    if event_type == "action_envelope_accepted":
        return PresenceState.PLANNING
    if event_type == "browser_action_started":
        return PresenceState.OBSERVING
    if event_type == "runtime_failure_fact_created":
        return PresenceState.RECOVERING
    if event_type == "model_visible_failure_packet_created":
        return PresenceState.PLANNING
    if event_type == "material_receipt_created":
        if telemetry_state is TelemetryState.INCOMPLETE:
            return PresenceState.TELEMETRY_INCOMPLETE
        return PresenceState.BLOCKED if str(payload.get("status") or "") == "blocked" else PresenceState.VERIFYING
    if event_type == "browser_progress_repetition_detected":
        return PresenceState.RECOVERING
    if event_type == "browser_proof_index_created":
        return PresenceState.VERIFYING
    if event_type == "FinalGate_result":
        if _accepting_finalgate(payload):
            return PresenceState.VERIFYING
        if payload.get("accepted") is False:
            return PresenceState.BLOCKED
        return PresenceState.VERIFYING
    if event_type == "terminal_verdict":
        verdict = str(payload.get("verdict") or payload.get("status") or "").lower()
        if verdict in {"killed", "revoked"}:
            return PresenceState.KILLED
        if verdict in {"completed", "success", "succeeded"}:
            return PresenceState.COMPLETED if accepting_finalgate_seen else PresenceState.TELEMETRY_INCOMPLETE
        return PresenceState.BLOCKED
    if event_type == "cleanup_result" and terminal_state is not None:
        return terminal_state
    if operation.startswith("real_browser."):
        return PresenceState.OBSERVING
    return PresenceState.ACTING


def _telemetry_state(
    *,
    event_type: str,
    operation: str,
    browser_receipt_ref: str,
    payload: dict[str, Any],
) -> TelemetryState:
    if (
        event_type == "material_receipt_created"
        and operation.startswith("real_browser.")
        and not browser_receipt_ref
    ):
        return TelemetryState.INCOMPLETE
    if event_type == "browser_proof_index_created" and _safe_int(payload.get("browser_receipt_missing_count")) > 0:
        return TelemetryState.INCOMPLETE
    return TelemetryState.COMPLETE


def _gate_results(
    *,
    event_type: str,
    payload: dict[str, Any],
    proof_index: dict[str, Any],
    accepting_finalgate_seen: bool,
) -> dict[str, str]:
    if event_type == "FinalGate_result":
        if payload.get("accepted") is True:
            return {"finalgate": "PASSED"}
        if payload.get("accepted") is False:
            return {"finalgate": "FAILED"}
        status = str(payload.get("status") or "").lower()
        return {
            "action_finalgate": (
                "PASSED"
                if status in {"completed", "passed", "success", "succeeded"}
                else "FAILED"
            )
        }
    if event_type == "browser_proof_index_created":
        missing = _safe_int(
            payload.get("browser_receipt_missing_count")
            if "browser_receipt_missing_count" in payload
            else proof_index.get("browser_receipt_missing_count")
        )
        return {"material_browser_receipts": "FAILED" if missing else "PASSED"}
    if event_type == "terminal_verdict":
        return {
            "finalgate": (
                "PASSED"
                if accepting_finalgate_seen
                else TelemetryState.INCOMPLETE.value
            )
        }
    return {}


def _accepting_finalgate(payload: dict[str, Any]) -> bool:
    return payload.get("accepted") is True


def _safe_summary(
    *,
    event_type: str,
    event_kind: PresenceEventKind,
    decision_index: int,
    operation: str,
    payload: dict[str, Any],
    telemetry_state: TelemetryState,
    blocker: str,
) -> str:
    operation_label = _operation_label(operation)
    if event_type == "run_started":
        text = "Mission started from persisted authority and runtime records."
    elif event_type == "provider_decision_received":
        text = f"Decision {decision_index} was persisted."
    elif event_type == "action_envelope_accepted":
        text = f"Decision {decision_index} selected {operation_label}."
    elif event_type == "browser_action_started":
        text = f"Sentinel started {operation_label}."
    elif event_type == "runtime_failure_fact_created":
        text = f"{operation_label} failed; Sentinel recorded a typed runtime fact."
    elif event_type == "model_visible_failure_packet_created":
        text = "A safe recovery packet was persisted for the next decision."
    elif event_type == "material_receipt_created":
        if telemetry_state is TelemetryState.INCOMPLETE:
            text = f"{operation_label} ended without a readable browser receipt."
        else:
            status = _safe_label(payload.get("status")) or "recorded"
            text = f"Proof for {operation_label} was persisted with status {status}."
    elif event_type == "browser_progress_repetition_detected":
        text = f"Repeated {operation_label} was suppressed because no material progress was proven."
    elif event_type == "browser_proof_index_created":
        missing = _safe_int(payload.get("browser_receipt_missing_count"))
        text = (
            f"Proof index persisted with {missing} missing browser receipt"
            f"{'s' if missing != 1 else ''}."
        )
    elif event_type == "FinalGate_result":
        if payload.get("accepted") is True:
            text = "FinalGate accepted the terminal truth."
        elif payload.get("accepted") is False:
            text = "FinalGate rejected completion."
        else:
            text = "An action FinalGate result was persisted."
    elif event_type == "terminal_verdict":
        verdict = _safe_label(payload.get("verdict") or payload.get("status")) or "unknown"
        text = f"Mission reached terminal verdict {verdict}."
    elif event_type == "cleanup_result":
        text = "Owned runtime resources reported cleanup."
    else:
        text = f"{event_kind.value.title()} event persisted."
    if blocker and event_type in {"runtime_failure_fact_created", "terminal_verdict"}:
        text = f"{text[:-1]}: {blocker}."
    return _safe_text(text, max_chars=_MAX_SUMMARY_CHARS) or "Persisted mission event."


def _operation_label(operation: str) -> str:
    labels = {
        "real_browser.observe": "browser observation",
        "real_browser.search": "browser search",
        "real_browser.extract_evidence": "evidence extraction",
        "real_browser.verify_extraction": "evidence verification",
        "summarize_evidence": "evidence summary",
    }
    return labels.get(operation, operation.replace("_", " ") or "the selected action")


def _provider_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return _safe_allowlisted_mapping(payload, _PROVIDER_METADATA_KEYS)


def _normalized_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return _safe_allowlisted_mapping(
        _safe_mapping(decision.get("normalized_decision")),
        _NORMALIZED_DECISION_KEYS,
    )


def _available_affordances(decision: dict[str, Any]) -> list[str]:
    announced = _safe_mapping(decision.get("announced_affordances"))
    values: list[str] = []
    for key in ("recommended_browser_actions", "recovery_actions", "search_like_refs"):
        item = announced.get(key)
        if isinstance(item, list):
            values.extend(str(value) for value in item)
    return sanitize_operator_refs(values)[:_MAX_SAFE_ITEMS]


def _operation(*, payload: dict[str, Any], decision: dict[str, Any]) -> str:
    normalized = _safe_mapping(decision.get("normalized_decision"))
    receipt = _safe_mapping(decision.get("receipt"))
    return _safe_label(
        payload.get("operation")
        or normalized.get("operation")
        or receipt.get("operation")
    )


def _product_receipt_ref(*, payload: dict[str, Any], receipt: dict[str, Any]) -> str:
    refs = payload.get("receipt_refs")
    if isinstance(refs, list):
        for value in refs:
            safe = _safe_ref(value)
            if safe and ("product" in safe or not receipt.get("browser_receipt_ref")):
                return safe
    return _safe_ref(receipt.get("product_receipt_ref"))


def _context_pack_ref(payload: dict[str, Any]) -> str:
    return _safe_ref(payload.get("context_pack_ref") or payload.get("context_ref"))


def _context_pack_hash(*, payload: dict[str, Any], decision: dict[str, Any]) -> str:
    model_state = _safe_mapping(decision.get("model_state_presented"))
    return _safe_ref(
        payload.get("context_pack_hash")
        or payload.get("context_hash")
        or model_state.get("context_hash")
    )


def _dispatch_status(*, event_type: str, payload: dict[str, Any], receipt: dict[str, Any]) -> str:
    if event_type == "action_envelope_accepted":
        return "accepted"
    if event_type == "browser_action_started":
        return "started"
    if event_type == "browser_progress_repetition_detected":
        return "suppressed_repeated_action"
    return _safe_label(payload.get("status") or receipt.get("status"))


def _authority_state(payload: dict[str, Any]) -> str:
    explicit = payload.get("authority_state")
    if explicit:
        return _safe_label(explicit)
    return "not_present_in_safe_projection"


def _safe_blocker(*, payload: dict[str, Any], ledger: dict[str, Any], event_type: str) -> str:
    value = payload.get("blocked_reason") or payload.get("reason")
    if event_type == "terminal_verdict":
        value = value or ledger.get("blocked_reason")
    return _safe_text(value, max_chars=180)


def _route_projection(event: PresenceEventV1) -> dict[str, Any]:
    return {
        "schema_version": "presence_route_view_v1",
        "source_event_id": event.event_id,
        "mission_id": event.mission_id,
        "sequence": event.sequence,
        "timestamp": event.timestamp,
        "presence_state": event.presence_state.value,
        "event_kind": event.event_kind.value,
        "summary": event.safe_summary,
        "proof_state": event.telemetry_state.value,
        "blocker": event.blocker,
        "data_not_authority": True,
        "can_execute": False,
    }


def _xray_projection(event: PresenceEventV1) -> dict[str, Any]:
    return {
        "schema_version": "presence_xray_view_v1",
        "source_event_id": event.event_id,
        "mission_id": event.mission_id,
        "sequence": event.sequence,
        "source_sequence": event.source_sequence,
        "decision_index": event.decision_index,
        "timestamp": event.timestamp,
        "presence_state": event.presence_state.value,
        "event_kind": event.event_kind.value,
        "safe_summary": event.safe_summary,
        "provider_metadata": event.provider_metadata,
        "context_pack_ref": event.context_pack_ref,
        "context_pack_hash": event.context_pack_hash,
        "available_affordances": event.available_affordances,
        "normalized_decision": event.normalized_decision,
        "dispatch_status": event.dispatch_status,
        "product_receipt_ref": event.product_receipt_ref,
        "browser_receipt_ref": event.browser_receipt_ref,
        "before_state_fingerprint": event.before_state_fingerprint,
        "after_state_fingerprint": event.after_state_fingerprint,
        "before_evidence_fingerprint": event.before_evidence_fingerprint,
        "after_evidence_fingerprint": event.after_evidence_fingerprint,
        "material_progress": event.material_progress,
        "authority_state": event.authority_state,
        "blocker": event.blocker,
        "gate_results": event.gate_results,
        "first_causal_divergence_ref": event.first_causal_divergence_ref,
        "telemetry_state": event.telemetry_state.value,
        "ledger_head": event.ledger_head,
        "event_hash": event.event_hash,
        "data_not_authority": True,
        "can_execute": False,
    }


def _safe_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_allowlisted_mapping(value: dict[str, Any], allowed_keys: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in allowed_keys:
        if key not in value:
            continue
        lowered = key.lower()
        if any(marker in lowered for marker in _FORBIDDEN_KEY_MARKERS + _SECRET_KEY_MARKERS):
            continue
        item = value[key]
        if isinstance(item, bool) or item is None:
            result[key] = item
        elif isinstance(item, (int, float)):
            result[key] = item
        elif isinstance(item, str):
            result[key] = _safe_ref(item)
        elif isinstance(item, dict):
            result[key] = {
                "redacted": key,
                "sha256": stable_hash(item),
                "data_not_authority": True,
            }
    return result


def _safe_ref(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    redacted = redact_operator_text(text)
    if redacted != text or _PATH_PATTERN.search(text):
        return f"redacted_ref:{stable_hash(text)}"
    return redacted[:512]


def _safe_text(value: Any, *, max_chars: int) -> str:
    if value is None:
        return ""
    text = redact_operator_text(str(value))
    if _PATH_PATTERN.search(text):
        return f"redacted_text:{stable_hash(text)}"
    return text[:max_chars]


def _safe_label(value: Any) -> str:
    if value is None:
        return ""
    return _SAFE_LABEL_PATTERN.sub("_", str(value))[:160].strip("_")


def _safe_timestamp(value: Any) -> str:
    text = _safe_text(value, max_chars=80)
    return text or "unknown"


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "PresenceEventBuffer",
    "PresenceEventKind",
    "PresenceEventV1",
    "PresenceJsonlJournal",
    "PresenceProjector",
    "PresenceReplayArchiveV1",
    "PresenceSequenceError",
    "PresenceSidecarRelay",
    "PresenceSnapshotSidecar",
    "PresenceState",
    "TelemetryState",
]
