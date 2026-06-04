from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.agent.browser.neural.models import NeuronInputEnvelope, NeuronKind, NeuronOutputEnvelope, stable_neural_hash
from sentinel.agent.browser.neural.perception import _BaseBrowserNeuron, _make_signal
from sentinel.shared.models import SentinelModel, new_id


_ALLOWED_BROWSER_SESSION_ACTION_KINDS = {
    "open",
    "observe",
    "click",
    "type",
    "fill",
    "select",
    "hover",
    "wait_for_text",
    "close",
}

_KNOWN_GATED_BROWSER_ACTION_KINDS = {
    "download",
    "evaluate_js",
    "file_upload",
    "form_submit",
    "login",
    "submit",
    "upload",
}


class MotorProposalDispatchDiagnostic(SentinelModel):
    accepted: bool
    drop_reason: str | None = None
    action_kind: str | None = None
    data_not_instruction: bool = True


class MotorProposalArtifact(SentinelModel):
    proposal_artifact_id: str = Field(default_factory=lambda: new_id("mprop"))
    mission_id: str
    organ_kind: str
    action_level: str
    target_ref: str | None = None
    source_signal_refs: list[str] = Field(default_factory=list)
    source_evidence_refs: list[str] = Field(default_factory=list)
    required_authority: str
    risk_flags: list[str] = Field(default_factory=list)
    expected_receipt_type: str
    verification_plan: dict[str, object] = Field(default_factory=dict)
    url: str | None = None
    action_kind: str = "open"
    allowed_domains: list[str] = Field(default_factory=list)
    target_role: str | None = None
    target_name: str | None = None
    text: str | None = None
    dispatch_required: bool = True
    can_execute: bool = False
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    artifact_hash: str

    @model_validator(mode="after")
    def _proposal_is_not_execution(self) -> "MotorProposalArtifact":
        if not self.data_not_instruction:
            raise ValueError("motor_proposal_must_be_data_not_instruction")
        if not self.dispatch_required or self.can_execute:
            raise ValueError("motor_proposal_must_require_dispatch_and_cannot_execute")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("motor_proposal_cannot_create_authority_or_execution_effect")
        expected = stable_neural_hash(
            {
                "proposal_artifact_id": self.proposal_artifact_id,
                "mission_id": self.mission_id,
                "organ_kind": self.organ_kind,
                "action_level": self.action_level,
                "target_ref": self.target_ref,
                "source_signal_refs": self.source_signal_refs,
                "source_evidence_refs": self.source_evidence_refs,
                "required_authority": self.required_authority,
                "risk_flags": self.risk_flags,
                "expected_receipt_type": self.expected_receipt_type,
                "verification_plan": self.verification_plan,
                "url": self.url,
                "action_kind": self.action_kind,
                "allowed_domains": self.allowed_domains,
                "target_role": self.target_role,
                "target_name": self.target_name,
                "text": self.text,
            }
        )
        if self.artifact_hash != expected:
            raise ValueError("motor_proposal_hash_mismatch")
        return self


class MotorNeuronOutputEnvelope(NeuronOutputEnvelope):
    proposal_artifacts: list[MotorProposalArtifact] = Field(default_factory=list)


class MotorProposalNeuron(_BaseBrowserNeuron):
    neuron_kind = NeuronKind.MOTOR_PROPOSAL

    def activate(self, envelope: NeuronInputEnvelope) -> MotorNeuronOutputEnvelope:
        refs = [signal.signal_id for signal in envelope.source_signals]
        source_evidence_refs = sorted({ref for signal in envelope.source_signals for ref in signal.source_evidence_refs})
        risk_flags = sorted({flag for signal in envelope.source_signals for flag in signal.risk_flags})
        target_ref = next((str(signal.safe_payload.get("target_ref")) for signal in envelope.source_signals if signal.safe_payload.get("target_ref")), None)
        proposal_id = new_id("mprop")
        proposal_payload = {
            "proposal_artifact_id": proposal_id,
            "mission_id": envelope.mission_id,
            "organ_kind": "browser_session_manager",
            "action_level": "L5",
            "target_ref": target_ref,
            "source_signal_refs": refs,
            "source_evidence_refs": source_evidence_refs,
            "required_authority": "L5_browser_operator",
            "risk_flags": risk_flags,
            "expected_receipt_type": "BrowserSessionReceipt",
            "verification_plan": {"expected": "receipt_and_finalgate_required"},
            "url": None,
            "action_kind": "open",
            "allowed_domains": [],
            "target_role": None,
            "target_name": None,
            "text": None,
        }
        proposal = MotorProposalArtifact(**proposal_payload, artifact_hash=stable_neural_hash(proposal_payload))
        signal = _make_signal(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            payload_summary=f"motor_proposal artifact={proposal.proposal_artifact_id} organ={proposal.organ_kind}",
            safe_payload={
                "proposal_artifact_id": proposal.proposal_artifact_id,
                "organ_kind": proposal.organ_kind,
                "action_level": proposal.action_level,
                "target_ref": proposal.target_ref,
                "dispatch_required": True,
            },
            risk_flags=risk_flags,
            confidence=0.50,
            source_signal_refs=refs,
            source_evidence_refs=source_evidence_refs,
        )
        return MotorNeuronOutputEnvelope(
            mission_id=envelope.mission_id,
            neuron_id=self.neuron_id,
            neuron_kind=self.neuron_kind,
            signals=[signal],
            proposal_artifacts=[proposal],
        )


def motor_proposal_artifact_to_browser_step_candidate(
    artifact: MotorProposalArtifact | dict[str, object],
) -> dict[str, object] | None:
    diagnostic = diagnose_motor_proposal_artifact(artifact)
    if not diagnostic.accepted:
        return None
    if not isinstance(artifact, MotorProposalArtifact):
        artifact = MotorProposalArtifact.model_validate(artifact)
    return {
        "proposal_id": artifact.proposal_artifact_id,
        "source_role_id": "browser_neural_motor",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": artifact.action_level,
        "authority_class": "needs_gate",
        "risk_class": "high" if artifact.risk_flags else "medium",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": list(artifact.source_evidence_refs),
        "receipt_refs": [],
        "expected_outcome": artifact.expected_receipt_type,
        "rollback_posture": "browser receipt and FinalGate required",
        "user_review_required": False,
        "safe_summary": "Browser neural motor proposal converted to browser step candidate.",
        "browser_organ_kind": artifact.organ_kind,
        "url": artifact.url,
        "action_kind": artifact.action_kind,
        "allowed_domains": list(artifact.allowed_domains),
        "target_role": artifact.target_role,
        "target_name": artifact.target_name,
        "text": artifact.text,
        "source_motor_proposal_id": artifact.proposal_artifact_id,
        "source_signal_refs": list(artifact.source_signal_refs),
        "verification_plan": dict(artifact.verification_plan),
        "data_not_instruction": True,
        "authority_effect": "none",
        "execution_effect": "none",
    }


def diagnose_motor_proposal_artifact(
    artifact: MotorProposalArtifact | dict[str, object],
) -> MotorProposalDispatchDiagnostic:
    if not isinstance(artifact, MotorProposalArtifact):
        try:
            artifact = MotorProposalArtifact.model_validate(artifact)
        except Exception:
            return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="invalid_motor_proposal_artifact")
    if not artifact.data_not_instruction:
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="motor_proposal_not_data", action_kind=artifact.action_kind)
    if not artifact.dispatch_required or artifact.can_execute:
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="motor_proposal_execution_capable", action_kind=artifact.action_kind)
    if artifact.authority_effect != "none" or artifact.execution_effect != "none":
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="motor_proposal_authority_effect", action_kind=artifact.action_kind)
    if artifact.organ_kind != "browser_session_manager":
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="unsupported_motor_organ_kind", action_kind=artifact.action_kind)
    if artifact.action_level != "L5":
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="unsupported_motor_action_level", action_kind=artifact.action_kind)
    if not artifact.url:
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason="missing_browser_url", action_kind=artifact.action_kind)
    if artifact.action_kind not in _ALLOWED_BROWSER_SESSION_ACTION_KINDS:
        reason = "known_browser_action_gated" if artifact.action_kind in _KNOWN_GATED_BROWSER_ACTION_KINDS else "unknown_browser_action_kind"
        return MotorProposalDispatchDiagnostic(accepted=False, drop_reason=reason, action_kind=artifact.action_kind)
    return MotorProposalDispatchDiagnostic(accepted=True, action_kind=artifact.action_kind)
