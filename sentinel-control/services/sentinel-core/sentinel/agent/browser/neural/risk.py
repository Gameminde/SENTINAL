from __future__ import annotations

from sentinel.agent.browser.neural.models import NeuronInputEnvelope, NeuronKind, NeuronOutputEnvelope
from sentinel.agent.browser.neural.perception import _BaseBrowserNeuron, _make_signal


_BOUNDARY_KEYWORDS = {
    "auth_wall": ("login", "sign in", "password", "authentication"),
    "payment_boundary": ("payment", "checkout", "credit card", "billing"),
    "captcha_boundary": ("captcha", "recaptcha", "challenge"),
    "credential_boundary": ("credential", "token", "secret"),
}


class RiskBoundaryNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.RISK_BOUNDARY

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        text = " ".join([signal.payload_summary for signal in envelope.source_signals]).lower()
        flags = sorted({flag for flag, keywords in _BOUNDARY_KEYWORDS.items() if any(keyword in text for keyword in keywords)})
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"risk_boundary flags={','.join(flags) if flags else 'none'}",
            safe_payload={"source_signal_refs": refs, "boundary_flags": flags},
            risk_flags=flags,
            confidence=0.80 if flags else 0.55,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])
