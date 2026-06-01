from __future__ import annotations

import inspect


def _page_state_signal():
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope, PageStateNeuron, TargetGroundingNeuron

    observation = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0b",
            source_receipts=[
                {
                    "receipt_id": "receipt_browser_1",
                    "final_url": "https://example.com/search",
                    "target_refs": ["target_search"],
                    "evidence_refs": ["ev_browser_1"],
                }
            ],
        )
    ).signals[0]
    page_state = PageStateNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[observation])
    ).signals[0]
    target = TargetGroundingNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[observation])
    ).signals[0]
    return observation, page_state, target


def test_planner_neuron_outputs_candidate_signal_only() -> None:
    from sentinel.agent.browser.neural import ActionPlannerNeuron, NeuronInputEnvelope, NeuronKind

    observation, page_state, target = _page_state_signal()
    signal = ActionPlannerNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[observation, page_state, target])
    ).signals[0]

    assert signal.neuron_kind == NeuronKind.ACTION_PLANNER
    assert signal.data_not_instruction is True
    assert signal.authority_effect == "none"
    assert signal.execution_effect == "none"
    assert signal.safe_payload["candidate_action"] == "browser_l5_interaction_proposal"


def test_verifier_neuron_rejects_weak_candidate_without_authority_effect() -> None:
    from sentinel.agent.browser.neural import NeuronInputEnvelope, TargetGroundingNeuron, VerifierNeuron

    weak = TargetGroundingNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[])
    ).signals[0]
    signal = VerifierNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[weak])
    ).signals[0]

    assert "candidate_confidence_too_low" in signal.risk_flags
    assert signal.authority_effect == "none"
    assert signal.execution_effect == "none"


def test_risk_boundary_neuron_detects_login_payment_captcha() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope, RiskBoundaryNeuron

    risky = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0b",
            source_receipts=[
                {
                    "receipt_id": "receipt_risky",
                    "final_url": "https://example.com/login-payment-captcha-checkout",
                }
            ],
        )
    ).signals[0]
    signal = RiskBoundaryNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[risky])
    ).signals[0]

    assert {"auth_wall", "payment_boundary", "captcha_boundary"}.issubset(set(signal.risk_flags))
    assert signal.authority_effect == "none"


def test_motor_proposal_neuron_emits_proposal_artifact_only() -> None:
    from sentinel.agent.browser.neural import ActionPlannerNeuron, MotorProposalNeuron, NeuronInputEnvelope

    observation, page_state, target = _page_state_signal()
    planner_signal = ActionPlannerNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[observation, page_state, target])
    ).signals[0]
    output = MotorProposalNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0b", source_signals=[planner_signal])
    )

    signal = output.signals[0]
    proposal = output.proposal_artifacts[0]
    assert signal.safe_payload["proposal_artifact_id"] == proposal.proposal_artifact_id
    assert proposal.organ_kind == "browser_session_manager"
    assert proposal.action_level == "L5"
    assert proposal.dispatch_required is True
    assert proposal.can_execute is False
    assert proposal.authority_effect == "none"


def test_motor_proposal_still_requires_dispatcher_gate_runtime() -> None:
    from sentinel.agent.browser.neural import MotorProposalNeuron

    neuron = MotorProposalNeuron()

    assert neuron.safety_boundary.can_execute is False
    assert neuron.safety_boundary.can_call_organ_directly is False
    assert neuron.safety_boundary.can_call_runtime_execution is False


def test_no_neural_planning_module_imports_runtime_execution_or_browser_organs() -> None:
    import sentinel.agent.browser.neural.motor_proposal as motor_proposal
    import sentinel.agent.browser.neural.planning as planning
    import sentinel.agent.browser.neural.recovery as recovery
    import sentinel.agent.browser.neural.risk as risk

    combined = "\n".join(inspect.getsource(module) for module in (motor_proposal, planning, recovery, risk))

    assert "from sentinel.agent.organs.runtime_execution" not in combined
    assert "import sentinel.agent.organs.runtime_execution" not in combined
    assert "BrowserSessionManagerL5Live" not in combined
    assert "BrowserFormSubmitSpecialAuthorityL6" not in combined
    assert "BrowserLoginCredentialSessionBrokerL6" not in combined
