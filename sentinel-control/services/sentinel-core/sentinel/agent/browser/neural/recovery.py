from __future__ import annotations

from sentinel.agent.browser.neural.models import NeuronInputEnvelope, NeuronKind, NeuronOutputEnvelope
from sentinel.agent.browser.neural.perception import _BaseBrowserNeuron, _make_signal


class VerifierNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.VERIFIER

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        min_confidence = min([signal.confidence for signal in envelope.source_signals], default=0.0)
        flags = ["candidate_confidence_too_low"] if min_confidence < 0.30 else []
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"verifier min_confidence={min_confidence:.2f}",
            safe_payload={"source_signal_refs": refs, "min_confidence": min_confidence},
            risk_flags=flags,
            confidence=0.70 if not flags else 0.35,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])


class FailureRecoveryNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.FAILURE_RECOVERY

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        inherited_flags = sorted({flag for signal in envelope.source_signals for flag in signal.risk_flags})
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"failure_recovery inherited_flags={','.join(inherited_flags) if inherited_flags else 'none'}",
            safe_payload={"source_signal_refs": refs, "recommended_recovery": "reobserve_or_replan"},
            risk_flags=inherited_flags,
            confidence=0.45,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])
