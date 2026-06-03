from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest


def test_neural_envelopes_and_graph_reject_authority_or_execution_effects() -> None:
    from sentinel.agent.browser.neural import BrowserSignalGraph, NeuronInputEnvelope, NeuronKind, NeuronOutputEnvelope

    with pytest.raises(ValueError, match="neuron_envelope_cannot_have_authority_or_execution_effect"):
        NeuronInputEnvelope(mission_id="mission_neural_audit", authority_effect="grant")

    with pytest.raises(ValueError, match="neuron_envelope_cannot_have_authority_or_execution_effect"):
        NeuronOutputEnvelope(
            mission_id="mission_neural_audit",
            neuron_id="neuron_output",
            neuron_kind=NeuronKind.VERIFIER,
            signals=[],
            execution_effect="execute",
        )

    with pytest.raises(ValueError, match="signal_graph_cannot_have_authority_or_execution_effect"):
        BrowserSignalGraph(mission_id="mission_neural_audit", authority_effect="grant")


def test_nested_model_receipt_payload_is_redacted_in_observation_signal() -> None:
    from pydantic import BaseModel

    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope

    class SecretCarrier(BaseModel):
        authorization: str
        safe_summary: str

    secret = "Bearer sk-live-nested-neural-secret"
    output = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(
            mission_id="mission_neural_audit",
            source_receipts=[
                {
                    "receipt_id": "receipt_nested_secret",
                    "nested": SecretCarrier(authorization=secret, safe_summary="safe"),
                }
            ],
        )
    )

    serialized = output.model_dump_json()

    assert secret not in serialized
    assert output.signals[0].safe_payload["nested"]["authorization"] == "[REDACTED]"
    assert "secret_like_payload_suppressed" in output.signals[0].risk_flags


def test_signal_hash_binds_safe_payload() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, NeuronInputEnvelope, NeuronSignal

    signal = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_audit", source_receipts=[{"receipt_id": "receipt_1", "target_refs": ["target_a"]}])
    ).signals[0]
    payload = signal.model_dump(mode="python")
    payload["safe_payload"]["target_refs"] = ["target_forged"]

    with pytest.raises(ValueError, match="neuron_signal_payload_hash_mismatch"):
        NeuronSignal.model_validate(payload)


def test_graph_edges_are_hash_bound_and_ref_bound() -> None:
    from sentinel.agent.browser.neural import BrowserObservationNeuron, BrowserSignalGraph, NeuronGraphEdge, NeuronInputEnvelope
    from sentinel.agent.browser.neural.models import stable_neural_hash

    signal = BrowserObservationNeuron().activate(
        NeuronInputEnvelope(mission_id="mission_neural_audit", source_receipts=[{"receipt_id": "receipt_1"}])
    ).signals[0]
    edge_payload = {
        "mission_id": "mission_neural_audit",
        "source_signal_id": "missing",
        "target_signal_id": signal.signal_id,
        "source_signal_hash": "missing_hash",
        "target_signal_hash": signal.signal_hash,
    }
    edge = NeuronGraphEdge(**edge_payload, edge_hash=stable_neural_hash(edge_payload))

    with pytest.raises(ValueError, match="signal_graph_edge_missing_source"):
        BrowserSignalGraph(mission_id="mission_neural_audit", signals=[signal], edges=[edge])

    bad_edge_payload = {
        "mission_id": "mission_neural_audit",
        "source_signal_id": signal.signal_id,
        "target_signal_id": signal.signal_id,
        "source_signal_hash": signal.signal_hash,
        "target_signal_hash": signal.signal_hash,
    }
    with pytest.raises(ValueError, match="neuron_graph_edge_hash_mismatch"):
        NeuronGraphEdge(**bad_edge_payload, edge_hash="bad")


def test_blackboard_rejects_authority_effect_and_mission_mismatch() -> None:
    from sentinel.agent.browser.neural import BrowserEvidenceBlackboard, BrowserSignalGraph

    with pytest.raises(ValueError, match="browser_evidence_blackboard_cannot_have_authority_or_execution_effect"):
        BrowserEvidenceBlackboard(
            mission_id="mission_neural_audit",
            signal_graph=BrowserSignalGraph(mission_id="mission_neural_audit"),
            authority_effect="grant",
        )

    with pytest.raises(ValueError, match="browser_evidence_blackboard_mission_mismatch"):
        BrowserEvidenceBlackboard(
            mission_id="mission_neural_audit",
            signal_graph=BrowserSignalGraph(mission_id="other_mission"),
        )


def test_motor_proposal_data_not_instruction_is_enforced() -> None:
    from sentinel.agent.browser.neural import MotorProposalArtifact, motor_proposal_artifact_to_browser_step_candidate
    from sentinel.agent.browser.neural.models import stable_neural_hash

    payload = {
        "proposal_artifact_id": "mprop_bad_data_flag",
        "mission_id": "mission_neural_audit",
        "organ_kind": "browser_session_manager",
        "action_level": "L5",
        "target_ref": "target_browser",
        "source_signal_refs": ["nsig_1"],
        "source_evidence_refs": ["ev_1"],
        "required_authority": "L5_browser_operator",
        "risk_flags": [],
        "expected_receipt_type": "BrowserSessionReceipt",
        "verification_plan": {"expected": "receipt_and_finalgate_required"},
        "url": "https://example.com",
        "action_kind": "open",
        "allowed_domains": ["example.com"],
        "target_role": None,
        "target_name": None,
        "text": None,
    }
    bad_payload = {**payload, "data_not_instruction": False}

    with pytest.raises(ValueError, match="motor_proposal_must_be_data_not_instruction"):
        MotorProposalArtifact(**bad_payload, artifact_hash=stable_neural_hash(payload))

    artifact_dict = {**bad_payload, "artifact_hash": stable_neural_hash(payload)}
    assert motor_proposal_artifact_to_browser_step_candidate(artifact_dict) is None


def test_squad_models_reject_direct_execution_or_authority_flags() -> None:
    from sentinel.agent.browser.neural import BrowserSquadRole, BrowserSquadRoleKind, BrowserSquadRoleOutput

    with pytest.raises(ValueError, match="browser_squad_role_cannot_enable_execution_or_authority"):
        BrowserSquadRole(
            mission_id="mission_squad_audit",
            authority_envelope_id="env_1",
            role_kind=BrowserSquadRoleKind.OPERATOR,
            can_execute=True,
        )

    with pytest.raises(ValueError, match="browser_squad_output_cannot_enable_execution_or_authority"):
        BrowserSquadRoleOutput(
            mission_id="mission_squad_audit",
            authority_envelope_id="env_1",
            role_kind=BrowserSquadRoleKind.OPERATOR,
            source_signal_refs=[],
            summary="unsafe output",
            can_call_runtime_execution=True,
        )


def test_gauntlet_models_reject_execution_or_authority_claims() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralGauntletCase, BrowserNeuralGauntletReport

    with pytest.raises(ValueError, match="browser_neural_gauntlet_case_cannot_execute"):
        BrowserNeuralGauntletCase(case_id="bad", description="bad", expected_path=["observe"], can_execute=True)

    with pytest.raises(ValueError, match="browser_neural_gauntlet_report_cannot_claim_execution"):
        BrowserNeuralGauntletReport(case_count=0, passed_count=0, case_results=[], live_payment_execution_complete=True)


def test_ledger_events_reject_authority_or_future_execution_flags() -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralLedgerEvent

    with pytest.raises(ValueError, match="browser_neural_ledger_event_cannot_enable_authority_or_execution"):
        BrowserNeuralLedgerEvent(
            workflow_id="wf",
            run_id="run",
            event_type="bad",
            actor_or_neuron_id="actor",
            previous_hash=None,
            event_hash="hash",
            can_grant_authority=True,
        )

    with pytest.raises(ValueError, match="browser_neural_ledger_event_cannot_enable_authority_or_execution"):
        BrowserNeuralLedgerEvent(
            workflow_id="wf",
            run_id="run",
            event_type="bad",
            actor_or_neuron_id="actor",
            previous_hash=None,
            event_hash="hash",
            can_approve_future_execution=True,
        )


def test_ledger_redacts_secret_like_refs_and_model_state(tmp_path: Path) -> None:
    from pydantic import BaseModel

    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    class SecretCarrier(BaseModel):
        authorization: str
        safe_summary: str

    secret = "Bearer sk-live-neural-audit-secret"
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = BrowserNeuralReceiptLedger(ledger_path)
    event = ledger.append(
        workflow_id="wf",
        run_id="run",
        event_type="secret_redaction",
        actor_or_neuron_id="audit",
        refs={"authorization": secret, "safe_ref": "receipt_1"},
        state={"carrier": SecretCarrier(authorization=secret, safe_summary="ok")},
    )

    raw = ledger_path.read_text(encoding="utf-8")

    assert secret not in raw
    assert event.refs["authorization"] == "[REDACTED]"
    assert event.state["carrier"]["authorization"] == "[REDACTED]"
    assert "secret_like_payload_suppressed" in event.risk_flags


def test_malicious_ledger_line_with_authority_flag_fails_replay(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger
    from sentinel.agent.browser.neural.models import stable_neural_hash

    payload = {
        "event_id": "bnledger_bad",
        "workflow_id": "wf",
        "run_id": "run",
        "call_id": None,
        "event_type": "bad",
        "actor_or_neuron_id": "actor",
        "refs": {},
        "state": {},
        "risk_flags": [],
        "previous_hash": None,
        "created_at": datetime.now(UTC).isoformat(),
        "data_not_instruction": True,
        "authority_effect": "none",
        "execution_effect": "none",
        "can_grant_authority": True,
        "can_approve_future_execution": False,
    }
    payload["event_hash"] = stable_neural_hash(payload)
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="browser_neural_ledger_event_cannot_enable_authority_or_execution"):
        BrowserNeuralReceiptLedger(ledger_path).replay()


def test_ledger_concurrent_appends_preserve_hash_chain(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger_path = tmp_path / "ledger.jsonl"

    def append_event(index: int) -> None:
        BrowserNeuralReceiptLedger(ledger_path).append(
            workflow_id="wf",
            run_id="run",
            event_type="concurrent_event",
            actor_or_neuron_id=f"actor_{index}",
            refs={"index": str(index)},
            state={"summary": f"event {index}"},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append_event, range(32)))

    ledger = BrowserNeuralReceiptLedger(ledger_path)
    replay = ledger.replay()

    assert len(replay) == 32
    assert ledger.verify_integrity() is True
