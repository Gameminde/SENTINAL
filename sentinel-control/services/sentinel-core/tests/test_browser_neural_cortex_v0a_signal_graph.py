from __future__ import annotations

import inspect

import pytest


def test_neuron_signal_is_data_not_instruction() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope

    output = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0a",
            source_receipts=[{"receipt_id": "receipt_browser_1", "final_url": "https://example.com"}],
        )
    )

    signal = output.signals[0]
    assert signal.data_not_instruction is True
    assert signal.authority_effect == "none"
    assert signal.execution_effect == "none"


def test_neuron_cannot_grant_authority_execute_or_access_credentials() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron

    boundary = BrowserObservationNeuron().safety_boundary

    assert boundary.can_execute is False
    assert boundary.can_grant_authority is False
    assert boundary.can_access_credentials is False
    assert boundary.can_unlock_credentials is False
    assert boundary.can_mutate_policy is False
    assert boundary.can_create_delegated_lane is False
    assert boundary.can_call_runtime_execution is False
    assert boundary.can_call_organ_directly is False


def test_signal_graph_is_append_only_and_hash_bound() -> None:
    from sentinel.agent.browser.neural import BrowserSignalGraph, BrowserObservationNeuron, PageStateNeuron, NeuronInputEnvelope

    graph = BrowserSignalGraph(mission_id="mission_neural_v0a")
    observation = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0a",
            source_receipts=[{"receipt_id": "receipt_browser_1", "final_url": "https://example.com"}],
        )
    ).signals[0]
    graph.add_signal(observation)
    page_state = PageStateNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0a", source_signals=[observation])
    ).signals[0]
    graph.add_signal(page_state, source_signal_refs=[observation.signal_id])

    assert graph.signal_count == 2
    assert graph.edge_count == 1
    assert graph.edges[0].source_signal_id == observation.signal_id
    assert graph.edges[0].target_signal_id == page_state.signal_id
    assert graph.edges[0].edge_hash
    with pytest.raises(ValueError, match="append_only_duplicate_signal"):
        graph.add_signal(observation)


def test_browser_receipt_becomes_observation_signal() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope, NeuronKind

    output = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0a",
            source_receipts=[
                {
                    "receipt_id": "receipt_browser_1",
                    "organ_kind": "browser_session_manager_l5_live",
                    "final_url": "https://example.com/pricing",
                    "evidence_refs": ["ev_browser_1"],
                }
            ],
        )
    )

    signal = output.signals[0]
    assert signal.neuron_kind == NeuronKind.BROWSER_OBSERVATION
    assert signal.source_receipt_refs == ["receipt_browser_1"]
    assert signal.source_evidence_refs == ["ev_browser_1"]
    assert signal.payload_hash
    assert "https://example.com/pricing" in signal.payload_summary


def test_target_grounding_and_evidence_auditor_emit_ref_bound_signals() -> None:
    from sentinel.agent.browser.neural import (
        BrowserObservationNeuron,
        EvidenceAuditorNeuron,
        NeuronInputEnvelope,
        TargetGroundingNeuron,
    )

    observation = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0a",
            source_receipts=[
                {
                    "receipt_id": "receipt_browser_1",
                    "target_refs": ["target_email"],
                    "evidence_refs": ["ev_browser_1"],
                    "prompt_injection_flags": ["ignore_previous_instructions"],
                }
            ],
        )
    ).signals[0]

    target = TargetGroundingNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0a", source_signals=[observation])
    ).signals[0]
    audit = EvidenceAuditorNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_v0a", source_signals=[observation])
    ).signals[0]

    assert "target_email" in target.payload_summary
    assert target.source_signal_refs == [observation.signal_id]
    assert "prompt_injection" in audit.risk_flags
    assert audit.source_evidence_refs == ["ev_browser_1"]


def test_legacy_cortex_harvested_not_duplicated() -> None:
    from sentinel.agent.browser.cortex import BrowserEvidenceInterpreter
    from sentinel.agent.browser.neural import LegacyBrowserEvidenceInterpreterAdapter

    adapter = LegacyBrowserEvidenceInterpreterAdapter()

    assert isinstance(adapter.interpreter, BrowserEvidenceInterpreter)
    assert adapter.interpreter_class_path == "sentinel.agent.browser.cortex.BrowserEvidenceInterpreter"


def test_no_raw_credentials_or_secret_persistence() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope

    secret = "Bearer sk-live-test-secret-value"
    output = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_v0a",
            source_receipts=[
                {
                    "receipt_id": "receipt_browser_1",
                    "final_url": "https://example.com",
                    "authorization": secret,
                    "cookie": "session=secret-cookie-value",
                }
            ],
        )
    )

    serialized = output.model_dump_json()
    assert secret not in serialized
    assert "secret-cookie-value" not in serialized
    assert "secret_like_payload_suppressed" in output.signals[0].risk_flags


def test_no_neural_module_imports_runtime_execution_or_browser_organs() -> None:
    import sentinel.agent.browser.neural.blackboard as blackboard
    import sentinel.agent.browser.neural.models as models
    import sentinel.agent.browser.neural.perception as perception
    import sentinel.agent.browser.neural.signal_graph as signal_graph

    combined = "\n".join(
        inspect.getsource(module)
        for module in (blackboard, models, perception, signal_graph)
    )

    assert "from sentinel.agent.organs.runtime_execution" not in combined
    assert "import sentinel.agent.organs.runtime_execution" not in combined
    assert "BrowserSessionManagerL5Live" not in combined
    assert "BrowserFormSubmitSpecialAuthorityL6" not in combined
    assert "BrowserLoginCredentialSessionBrokerL6" not in combined
