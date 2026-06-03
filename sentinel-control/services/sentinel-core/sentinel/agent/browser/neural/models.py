from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def stable_neural_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class NeuronKind(StrEnum):
    BROWSER_OBSERVATION = "browser_observation"
    PAGE_STATE = "page_state"
    TARGET_GROUNDING = "target_grounding"
    EVIDENCE_AUDITOR = "evidence_auditor"
    INTENT = "intent"
    RISK_BOUNDARY = "risk_boundary"
    ACTION_PLANNER = "action_planner"
    VERIFIER = "verifier"
    FAILURE_RECOVERY = "failure_recovery"
    MEMORY_RECALL = "memory_recall"
    MOTOR_PROPOSAL = "motor_proposal"


class NeuronSafetyBoundary(SentinelModel):
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_execute: bool = False
    can_grant_authority: bool = False
    can_access_credentials: bool = False
    can_unlock_credentials: bool = False
    can_mutate_policy: bool = False
    can_create_delegated_lane: bool = False
    can_call_runtime_execution: bool = False
    can_call_organ_directly: bool = False

    @model_validator(mode="after")
    def _must_remain_cognitive_only(self) -> "NeuronSafetyBoundary":
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("neuron_boundary_effect_must_be_none")
        forbidden_flags = [
            self.can_execute,
            self.can_grant_authority,
            self.can_access_credentials,
            self.can_unlock_credentials,
            self.can_mutate_policy,
            self.can_create_delegated_lane,
            self.can_call_runtime_execution,
            self.can_call_organ_directly,
        ]
        if any(forbidden_flags):
            raise ValueError("neuron_boundary_cannot_enable_authority_or_execution")
        return self


class NeuronSignal(SentinelModel):
    signal_id: str = Field(default_factory=lambda: new_id("nsig"))
    mission_id: str
    neuron_id: str
    neuron_kind: NeuronKind
    source_signal_refs: list[str] = Field(default_factory=list)
    source_evidence_refs: list[str] = Field(default_factory=list)
    source_receipt_refs: list[str] = Field(default_factory=list)
    payload_summary: str
    payload_hash: str
    safe_payload: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    signal_hash: str

    @model_validator(mode="after")
    def _signal_is_data_not_instruction(self) -> "NeuronSignal":
        if not self.data_not_instruction:
            raise ValueError("neuron_signal_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("neuron_signal_cannot_have_authority_or_execution_effect")
        if stable_neural_hash(self.safe_payload) != self.payload_hash:
            raise ValueError("neuron_signal_payload_hash_mismatch")
        expected = stable_neural_hash(
            {
                "signal_id": self.signal_id,
                "mission_id": self.mission_id,
                "neuron_id": self.neuron_id,
                "neuron_kind": self.neuron_kind,
                "source_signal_refs": self.source_signal_refs,
                "source_evidence_refs": self.source_evidence_refs,
                "source_receipt_refs": self.source_receipt_refs,
                "payload_summary": self.payload_summary,
                "payload_hash": self.payload_hash,
                "risk_flags": self.risk_flags,
                "confidence": self.confidence,
            }
        )
        if self.signal_hash != expected:
            raise ValueError("neuron_signal_hash_mismatch")
        return self


class NeuronGraphEdge(SentinelModel):
    edge_id: str = Field(default_factory=lambda: new_id("nedge"))
    mission_id: str
    source_signal_id: str
    target_signal_id: str
    source_signal_hash: str
    target_signal_hash: str
    edge_hash: str

    @model_validator(mode="after")
    def _edge_hash_is_bound(self) -> "NeuronGraphEdge":
        expected = stable_neural_hash(
            {
                "mission_id": self.mission_id,
                "source_signal_id": self.source_signal_id,
                "target_signal_id": self.target_signal_id,
                "source_signal_hash": self.source_signal_hash,
                "target_signal_hash": self.target_signal_hash,
            }
        )
        if self.edge_hash != expected:
            raise ValueError("neuron_graph_edge_hash_mismatch")
        return self


class NeuronInputEnvelope(SentinelModel):
    mission_id: str
    source_receipts: list[dict[str, Any]] = Field(default_factory=list)
    source_signals: list[NeuronSignal] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _input_envelope_is_data_only(self) -> "NeuronInputEnvelope":
        if not self.data_not_instruction:
            raise ValueError("neuron_envelope_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("neuron_envelope_cannot_have_authority_or_execution_effect")
        return self


class NeuronOutputEnvelope(SentinelModel):
    mission_id: str
    neuron_id: str
    neuron_kind: NeuronKind
    signals: list[NeuronSignal]
    activation_id: str = Field(default_factory=lambda: new_id("nact"))
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _output_envelope_is_data_only(self) -> "NeuronOutputEnvelope":
        if not self.data_not_instruction:
            raise ValueError("neuron_envelope_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("neuron_envelope_cannot_have_authority_or_execution_effect")
        return self


class NeuronActivationRecord(SentinelModel):
    activation_id: str = Field(default_factory=lambda: new_id("nact"))
    mission_id: str
    neuron_id: str
    neuron_kind: NeuronKind
    input_hash: str
    output_signal_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _activation_record_is_data_only(self) -> "NeuronActivationRecord":
        if not self.data_not_instruction:
            raise ValueError("neuron_activation_record_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("neuron_activation_record_cannot_have_authority_or_execution_effect")
        return self


class BrowserSignalGraph(SentinelModel):
    mission_id: str
    signals: list[NeuronSignal] = Field(default_factory=list)
    edges: list[NeuronGraphEdge] = Field(default_factory=list)
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _graph_is_data_only(self) -> "BrowserSignalGraph":
        if not self.data_not_instruction:
            raise ValueError("signal_graph_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("signal_graph_cannot_have_authority_or_execution_effect")
        by_id = {signal.signal_id: signal for signal in self.signals}
        for edge in self.edges:
            source = by_id.get(edge.source_signal_id)
            if source is None:
                raise ValueError("signal_graph_edge_missing_source")
            target = by_id.get(edge.target_signal_id)
            if target is None:
                raise ValueError("signal_graph_edge_missing_target")
            if edge.mission_id != self.mission_id or source.mission_id != self.mission_id or target.mission_id != self.mission_id:
                raise ValueError("signal_graph_edge_mission_mismatch")
            if edge.source_signal_hash != source.signal_hash:
                raise ValueError("signal_graph_edge_source_hash_mismatch")
            if edge.target_signal_hash != target.signal_hash:
                raise ValueError("signal_graph_edge_target_hash_mismatch")
        return self

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def add_signal(self, signal: NeuronSignal, *, source_signal_refs: list[str] | None = None) -> None:
        if signal.mission_id != self.mission_id:
            raise ValueError("signal_graph_mission_mismatch")
        if any(existing.signal_id == signal.signal_id for existing in self.signals):
            raise ValueError("append_only_duplicate_signal")
        source_signal_refs = source_signal_refs or []
        known = {existing.signal_id: existing for existing in self.signals}
        for source_id in source_signal_refs:
            if source_id not in known:
                raise ValueError("signal_graph_missing_source_signal")
        self.signals.append(signal)
        for source_id in source_signal_refs:
            source = known[source_id]
            edge_hash = stable_neural_hash(
                {
                    "mission_id": self.mission_id,
                    "source_signal_id": source.signal_id,
                    "target_signal_id": signal.signal_id,
                    "source_signal_hash": source.signal_hash,
                    "target_signal_hash": signal.signal_hash,
                }
            )
            self.edges.append(
                NeuronGraphEdge(
                    mission_id=self.mission_id,
                    source_signal_id=source.signal_id,
                    target_signal_id=signal.signal_id,
                    source_signal_hash=source.signal_hash,
                    target_signal_hash=signal.signal_hash,
                    edge_hash=edge_hash,
                )
            )
