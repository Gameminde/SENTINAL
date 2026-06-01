from __future__ import annotations

from typing import Any

from sentinel.agent.browser.cortex import BrowserEvidenceInterpreter
from sentinel.agent.browser.neural.models import (
    NeuronInputEnvelope,
    NeuronKind,
    NeuronOutputEnvelope,
    NeuronSafetyBoundary,
    NeuronSignal,
    stable_neural_hash,
)
from sentinel.agent.organs.safety_scanner import scan_secret_like_text
from sentinel.shared.models import new_id


_SECRETISH_KEYS = {
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "password",
    "secret",
    "session",
    "token",
    "api_key",
    "bearer",
}


def _to_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {"value": dumped}
    return value if isinstance(value, dict) else {"value": value}


def _sanitize(value: Any, *, key: str = "$", risk_flags: set[str]) -> Any:
    key_l = key.lower()
    if any(marker in key_l for marker in _SECRETISH_KEYS):
        risk_flags.add("secret_like_payload_suppressed")
        return "[REDACTED]"
    if isinstance(value, str):
        findings = scan_secret_like_text(value, path=key)
        if findings:
            risk_flags.add("secret_like_payload_suppressed")
            return "[REDACTED]"
        return value
    if isinstance(value, dict):
        return {str(k): _sanitize(v, key=str(k), risk_flags=risk_flags) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item, key=key, risk_flags=risk_flags) for item in value]
    return value


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple | set):
        return [str(item) for item in value]
    return [str(value)]


def _receipt_id(receipt: dict[str, Any]) -> str:
    return str(receipt.get("receipt_id") or receipt.get("id") or receipt.get("request_id") or new_id("receipt_ref"))


def _make_signal(
    *,
    mission_id: str,
    neuron_id: str,
    neuron_kind: NeuronKind,
    payload_summary: str,
    safe_payload: dict[str, Any],
    risk_flags: list[str],
    confidence: float,
    source_signal_refs: list[str] | None = None,
    source_evidence_refs: list[str] | None = None,
    source_receipt_refs: list[str] | None = None,
) -> NeuronSignal:
    signal_id = new_id("nsig")
    payload_hash = stable_neural_hash(safe_payload)
    risk_flags = sorted(set(risk_flags))
    source_signal_refs = source_signal_refs or []
    source_evidence_refs = source_evidence_refs or []
    source_receipt_refs = source_receipt_refs or []
    signal_hash = stable_neural_hash(
        {
            "signal_id": signal_id,
            "mission_id": mission_id,
            "neuron_id": neuron_id,
            "neuron_kind": neuron_kind,
            "source_signal_refs": source_signal_refs,
            "source_evidence_refs": source_evidence_refs,
            "source_receipt_refs": source_receipt_refs,
            "payload_summary": payload_summary,
            "payload_hash": payload_hash,
            "risk_flags": risk_flags,
            "confidence": confidence,
        }
    )
    return NeuronSignal(
        signal_id=signal_id,
        mission_id=mission_id,
        neuron_id=neuron_id,
        neuron_kind=neuron_kind,
        source_signal_refs=source_signal_refs,
        source_evidence_refs=source_evidence_refs,
        source_receipt_refs=source_receipt_refs,
        payload_summary=payload_summary,
        payload_hash=payload_hash,
        safe_payload=safe_payload,
        risk_flags=risk_flags,
        confidence=confidence,
        signal_hash=signal_hash,
    )


class LegacyBrowserEvidenceInterpreterAdapter:
    interpreter_class_path = "sentinel.agent.browser.cortex.BrowserEvidenceInterpreter"

    def __init__(self, interpreter: BrowserEvidenceInterpreter | None = None) -> None:
        self.interpreter = interpreter or BrowserEvidenceInterpreter()


class _BaseBrowserNeuron:
    neuron_kind: NeuronKind

    def __init__(self, neuron_id: str | None = None) -> None:
        self.neuron_id = neuron_id or new_id("neuron")
        self.safety_boundary = NeuronSafetyBoundary()


class BrowserObservationNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.BROWSER_OBSERVATION

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        signals: list[NeuronSignal] = []
        for raw_receipt in envelope.source_receipts:
            receipt = _to_mapping(raw_receipt)
            risk_flags: set[str] = set()
            safe_payload = _sanitize(receipt, risk_flags=risk_flags)
            prompt_flags = _list(receipt.get("prompt_injection_flags"))
            if prompt_flags:
                risk_flags.add("prompt_injection")
            receipt_ref = _receipt_id(receipt)
            evidence_refs = [*_list(receipt.get("evidence_refs")), *_list(receipt.get("source_evidence_refs"))]
            target_refs = _list(receipt.get("target_refs"))
            summary_parts = [f"receipt={receipt_ref}"]
            if receipt.get("organ_kind"):
                summary_parts.append(f"organ={receipt.get('organ_kind')}")
            if receipt.get("final_url"):
                summary_parts.append(f"url={receipt.get('final_url')}")
            if target_refs:
                summary_parts.append(f"targets={','.join(target_refs)}")
            signal = _make_signal(
                mission_id=envelope.mission_id,
                neuron_id=self.neuron_id,
                neuron_kind=self.neuron_kind,
                payload_summary="; ".join(summary_parts),
                safe_payload=safe_payload,
                risk_flags=sorted(risk_flags),
                confidence=0.72 if not risk_flags else 0.42,
                source_evidence_refs=sorted(set(evidence_refs)),
                source_receipt_refs=[receipt_ref],
            )
            signals.append(signal)
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=signals)


class PageStateNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.PAGE_STATE

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        urls = [str(signal.safe_payload.get("final_url")) for signal in envelope.source_signals if signal.safe_payload.get("final_url")]
        safe_payload = {"source_signal_refs": refs, "urls": urls}
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"page_state sources={len(refs)} urls={','.join(urls)}",
            safe_payload=safe_payload,
            risk_flags=[],
            confidence=0.64,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])


class TargetGroundingNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.TARGET_GROUNDING

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        targets = sorted({target for signal in envelope.source_signals for target in _list(signal.safe_payload.get("target_refs"))})
        safe_payload = {"source_signal_refs": refs, "target_refs": targets}
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"target_grounding targets={','.join(targets) if targets else 'none'}",
            safe_payload=safe_payload,
            risk_flags=[],
            confidence=0.60 if targets else 0.20,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])


class EvidenceAuditorNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.EVIDENCE_AUDITOR

    def activate(self, envelope: NeuronInputEnvelope) -> NeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        inherited_flags = sorted({flag for signal in envelope.source_signals for flag in signal.risk_flags})
        safe_payload = {"source_signal_refs": refs, "inherited_risk_flags": inherited_flags}
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"evidence_audit risk_flags={','.join(inherited_flags) if inherited_flags else 'none'}",
            safe_payload=safe_payload,
            risk_flags=inherited_flags,
            confidence=0.50 if inherited_flags else 0.76,
            source_signal_refs=refs,
            source_evidence_refs=sorted({ref for source in envelope.source_signals for ref in source.source_evidence_refs}),
            source_receipt_refs=sorted({ref for source in envelope.source_signals for ref in source.source_receipt_refs}),
        )
        return NeuronOutputEnvelope(mission_id=envelope.mission_id, neuron_id=self.neuron_id, neuron_kind=self.neuron_kind, signals=[signal])
