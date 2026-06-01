from __future__ import annotations

from sentinel.agent.browser.neural.models import NeuronInputEnvelope, NeuronKind, NeuronOutputEnvelope
from sentinel.agent.browser.neural.perception import _BaseBrowserNeuron, _list, _make_signal


class IntentNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.INTENT

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"intent_context sources={len(refs)}",
            safe_payload={"source_signal_refs": refs},
            risk_flags=[],
            confidence=0.50,
            source_signal_refs=refs,
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])


class ActionPlannerNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.ACTION_PLANNER

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        target_refs = sorted({target for signal in envelope.source_signals for target in _list(signal.safe_payload.get("target_refs"))})
        evidence_refs = sorted({ref for signal in envelope.source_signals for ref in signal.source_evidence_refs})
        receipt_refs = sorted({ref for signal in envelope.source_signals for ref in signal.source_receipt_refs})
        candidate_action = "browser_l5_interaction_proposal"
        target_ref = target_refs[0] if target_refs else None
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"planner_candidate action={candidate_action} target={target_ref or 'none'}",
            safe_payload={
                "candidate_action": candidate_action,
                "target_ref": target_ref,
                "source_signal_refs": refs,
                "source_evidence_refs": evidence_refs,
                "required_authority": "L5",
            },
            risk_flags=[],
            confidence=0.58 if target_ref else 0.25,
            source_signal_refs=refs,
            source_evidence_refs=evidence_refs,
            source_receipt_refs=receipt_refs,
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])


class MemoryRecallNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.MEMORY_RECALL

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"memory_recall_context source_signals={len(refs)}",
            safe_payload={"source_signal_refs": refs, "memory_context_only": True},
            risk_flags=[],
            confidence=0.40,
            source_signal_refs=refs,
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])
