from __future__ import annotations

from pathlib import Path

import pytest


def test_ledger_append_only_and_hash_chained(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger = BrowserNeuralReceiptLedger(tmp_path / "ledger.jsonl")
    first = ledger.append(
        workflow_id="wf_browser",
        run_id="run_1",
        event_type="neuron_signal",
        actor_or_neuron_id="neuron_observer",
        refs={"neuron_signal_id": "nsig_1"},
        state={"summary": "observation"},
    )
    second = ledger.append(
        workflow_id="wf_browser",
        run_id="run_1",
        event_type="motor_proposal",
        actor_or_neuron_id="neuron_motor",
        refs={"neuron_signal_id": "nsig_1", "proposal_artifact_id": "mprop_1"},
        state={"summary": "proposal"},
    )

    assert first.previous_hash is None
    assert second.previous_hash == first.event_hash
    assert ledger.verify_integrity() is True


def test_ledger_hash_chain_detects_tamper(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger, BrowserNeuralLedgerIntegrityError

    path = tmp_path / "ledger.jsonl"
    ledger = BrowserNeuralReceiptLedger(path)
    ledger.append(workflow_id="wf", run_id="run", event_type="neuron_signal", actor_or_neuron_id="n1", refs={}, state={"summary": "ok"})
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("ok", "tampered"), encoding="utf-8")

    with pytest.raises(BrowserNeuralLedgerIntegrityError):
        BrowserNeuralReceiptLedger(path).verify_integrity()


def test_ledger_links_signal_to_proposal_to_receipt(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger = BrowserNeuralReceiptLedger(tmp_path / "ledger.jsonl")
    ledger.append(workflow_id="wf", run_id="run", event_type="neuron_signal", actor_or_neuron_id="observer", refs={"neuron_signal_id": "nsig_1"}, state={})
    ledger.append(workflow_id="wf", run_id="run", event_type="motor_proposal", actor_or_neuron_id="motor", refs={"neuron_signal_id": "nsig_1", "proposal_artifact_id": "mprop_1"}, state={})
    ledger.append(workflow_id="wf", run_id="run", event_type="organ_receipt", actor_or_neuron_id="browser", refs={"proposal_artifact_id": "mprop_1", "receipt_id": "receipt_1"}, state={})

    replay = ledger.replay()

    assert [event.event_type for event in replay] == ["neuron_signal", "motor_proposal", "organ_receipt"]
    assert replay[-1].refs["receipt_id"] == "receipt_1"


def test_ledger_does_not_store_raw_credentials_or_private_browser_data(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    secret = "Bearer sk-live-secret-value"
    ledger = BrowserNeuralReceiptLedger(tmp_path / "ledger.jsonl")
    event = ledger.append(
        workflow_id="wf",
        run_id="run",
        event_type="organ_receipt",
        actor_or_neuron_id="browser",
        refs={"receipt_id": "receipt_1"},
        state={"authorization": secret, "cookie": "session=private-cookie", "summary": "safe"},
    )

    raw = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8")
    assert secret not in raw
    assert "private-cookie" not in raw
    assert "secret_like_payload_suppressed" in event.risk_flags


def test_ledger_replay_reconstructs_neural_browser_trace(tmp_path: Path) -> None:
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger = BrowserNeuralReceiptLedger(tmp_path / "ledger.jsonl")
    ledger.append(workflow_id="wf", run_id="run", event_type="neuron_signal", actor_or_neuron_id="observer", refs={"neuron_signal_id": "nsig_1"}, state={})
    ledger.append(workflow_id="wf", run_id="run", event_type="finalgate_certificate", actor_or_neuron_id="finalgate", refs={"certificate_id": "fg_1"}, state={})

    replay = ledger.replay()

    assert len(replay) == 2
    assert replay[0].workflow_id == "wf"
    assert replay[1].refs["certificate_id"] == "fg_1"
