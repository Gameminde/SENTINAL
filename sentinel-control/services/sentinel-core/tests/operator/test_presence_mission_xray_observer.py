from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel.operator.presence_observer import (
    PresenceEventBuffer,
    PresenceEventKind,
    PresenceEventV1,
    PresenceJsonlJournal,
    PresenceProjector,
    PresenceSequenceError,
    PresenceSidecarRelay,
    PresenceSnapshotSidecar,
    PresenceState,
    TelemetryState,
)
from sentinel.operator.presence_observer_cli import main as presence_observer_main


def test_historical_mdn_replay_names_decision_five_and_missing_receipts_honestly() -> None:
    archive = PresenceProjector().project_replay(
        safe_evidence_snapshot=_historical_mdn_safe_snapshot(),
        proof_index=_historical_mdn_proof_index(),
        mission_ledger={
            "task_id": "mdn_css_has",
            "blocked_reason": "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
        },
    )

    assert archive.first_causal_divergence["decision_index"] == 5
    assert archive.first_causal_divergence["classification"] == "BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS"
    missing = [
        event
        for event in archive.events
        if event.normalized_decision.get("operation") == "real_browser.observe"
        and event.event_kind is PresenceEventKind.PROOF
        and event.telemetry_state is TelemetryState.INCOMPLETE
        and event.product_receipt_ref
    ]
    assert [event.decision_index for event in missing] == [5, 7]
    assert all(event.product_receipt_ref for event in missing)
    assert all(not event.browser_receipt_ref for event in missing)
    assert archive.events[-1].presence_state is PresenceState.BLOCKED
    assert archive.events[-1].presence_state is not PresenceState.COMPLETED
    assert archive.replay_metadata == {
        "replay_mode": "artifact_history_reconstruction",
        "history_reconstructed": True,
        "effect_reexecution_attempted": False,
        "reexecuted_actions": False,
        "model_calls_delta": 0,
        "provider_calls_delta": 0,
        "receipt_writes_delta": 0,
        "finalgate_writes_delta": 0,
    }
    assert archive.route_view
    assert archive.xray_view
    assert all(item["source_event_id"] == archive.events[index].event_id for index, item in enumerate(archive.route_view))
    assert all(item["source_event_id"] == archive.events[index].event_id for index, item in enumerate(archive.xray_view))


def test_new_observe_failure_replay_exposes_typed_terminal_receipt() -> None:
    archive = PresenceProjector().project_replay(
        safe_evidence_snapshot={
            "run_id": "observe_receipt",
            "events": [
                _source_event(0, "provider_decision_received", {"context_hash": "ctx-1", "provider_decision_count": 1}),
                _source_event(
                    1,
                    "action_envelope_accepted",
                    {
                        "capability_id": "real_browser_control",
                        "operation": "real_browser.observe",
                        "params_hash": "params-1",
                    },
                ),
                _source_event(2, "browser_action_started", {"operation": "real_browser.observe"}),
                _source_event(
                    3,
                    "runtime_failure_fact_created",
                    {
                        "operation": "real_browser.observe",
                        "status": "blocked",
                        "blocked_reason": "real_browser_observe_snapshot_failed",
                        "runtime_failure_fact": {
                            "failure_code": "real_browser_observe_snapshot_failed",
                            "failure_stage": "browser_runtime_observe",
                            "material_effect_observed": False,
                        },
                        "receipt_refs": ["product_receipt_observe_1"],
                    },
                ),
                _source_event(
                    4,
                    "material_receipt_created",
                    {
                        "operation": "real_browser.observe",
                        "status": "blocked",
                        "receipt_refs": ["product_receipt_observe_1"],
                    },
                ),
                _source_event(
                    5,
                    "FinalGate_result",
                    {"accepted": False, "status": "blocked", "reason": "real_browser_observe_snapshot_failed"},
                ),
                _source_event(
                    6,
                    "terminal_verdict",
                    {"verdict": "blocked", "blocked_reason": "real_browser_observe_snapshot_failed"},
                ),
            ],
        },
        proof_index={
            "loop_id": "observe_receipt",
            "status": "blocked",
            "browser_receipt_missing_count": 0,
            "completion_truth": {
                "honest_blocker_present": True,
                "loop_closed": True,
                "useful_answer_completion": False,
            },
            "material_browser_receipts": [
                {
                    "operation": "real_browser.observe",
                    "action_status": "typed_observation_failure",
                    "browser_receipt_readable": True,
                    "browser_receipt_ref": "real_browser_action_observe_1",
                    "product_receipt_ref": "product_receipt_observe_1",
                    "receipt_hash": "receipt-hash-1",
                    "before_state_hash": "state-1",
                    "after_state_hash": "state-1",
                    "evidence_delta": {"changed": False, "added_refs": []},
                    "typed_observation": {
                        "outcome_kind": "typed_observation_failure",
                        "failure_code": "real_browser_observe_snapshot_failed",
                        "failure_stage": "browser_runtime_observe",
                        "exception_class": "RealBrowserControlRuntimeError",
                        "exception_hash": "exception-hash-1",
                    },
                }
            ],
        },
        mission_ledger={"task_id": "observe_receipt", "blocked_reason": "real_browser_observe_snapshot_failed"},
    )

    proof = next(event for event in archive.events if event.event_kind is PresenceEventKind.PROOF)
    assert proof.telemetry_state is TelemetryState.COMPLETE
    assert proof.browser_receipt_ref == "real_browser_action_observe_1"
    assert proof.product_receipt_ref == "product_receipt_observe_1"
    assert proof.before_state_fingerprint == proof.after_state_fingerprint == "state-1"
    assert proof.material_progress is False
    assert archive.first_causal_divergence["decision_index"] == 1
    assert archive.first_causal_divergence["classification"] == "BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS"


def test_browser_dispatch_preparation_and_runner_exception_are_projected_honestly() -> None:
    archive = PresenceProjector().project_replay(
        safe_evidence_snapshot={
            "run_id": "sqlite_runner_exception",
            "events": [
                _source_event(0, "provider_decision_received", {"context_hash": "ctx-1", "provider_decision_count": 1}),
                _source_event(
                    1,
                    "action_envelope_accepted",
                    {
                        "capability_id": "real_browser_control",
                        "operation": "real_browser.search",
                        "params_hash": "params-search",
                    },
                ),
                _source_event(2, "browser_action_requested", {"operation": "real_browser.search"}),
                _source_event(3, "action_dispatch_preparing", {"operation": "real_browser.search"}),
                _source_event(
                    4,
                    "terminal_verdict",
                    {
                        "verdict": "blocked",
                        "blocked_reason": "mission_workspace_root_not_found",
                        "exception_class": "ValueError",
                        "exception_hash": "safe-exception-hash",
                    },
                ),
            ],
        },
        proof_index={"loop_id": "sqlite_runner_exception", "completion_truth": {}, "material_browser_receipts": []},
        mission_ledger={"task_id": "sqlite_runner_exception", "blocked_reason": "mission_workspace_root_not_found"},
    )

    requested = next(event for event in archive.events if event.source_sequence == 2)
    preparing = next(event for event in archive.events if event.source_sequence == 3)
    terminal = archive.events[-1]
    assert requested.event_kind is PresenceEventKind.ACTION
    assert requested.presence_state is PresenceState.PLANNING
    assert requested.dispatch_status == "requested"
    assert preparing.event_kind is PresenceEventKind.ACTION
    assert preparing.presence_state is PresenceState.ACTING
    assert preparing.dispatch_status == "preparing"
    assert terminal.event_kind is PresenceEventKind.TERMINAL
    assert terminal.presence_state is PresenceState.BLOCKED
    assert terminal.blocker == "mission_workspace_root_not_found"


def test_event_buffer_enforces_order_deduplicates_and_resumes_after_sequence() -> None:
    buffer = PresenceEventBuffer()
    first = _presence_event(sequence=0, summary="Mission persisted")
    second = _presence_event(sequence=1, summary="Decision persisted")

    assert buffer.publish(first) is True
    assert buffer.publish(first) is False
    with pytest.raises(PresenceSequenceError, match="conflicting duplicate"):
        buffer.publish(_presence_event(sequence=0, summary="Conflicting event"))
    with pytest.raises(PresenceSequenceError, match="expected sequence 1"):
        buffer.publish(_presence_event(sequence=2, summary="Gap"))
    assert buffer.publish(second) is True
    assert buffer.resume(mission_id="mission-test", after_sequence=0) == (second,)
    assert buffer.resume(mission_id="mission-test", after_sequence=1) == ()


def test_projection_redacts_forbidden_raw_material_secrets_and_paths() -> None:
    cookie_value = "session" + "id=abcdef1234567890"
    credential_value = "sk-" + "testvalue1234567890abcdef"
    archive = PresenceProjector().project_replay(
        safe_evidence_snapshot={
            "run_id": "redaction",
            "events": [
                _source_event(
                    0,
                    "provider_decision_received",
                    {
                        "provider_decision_count": 1,
                        "provider_id": "test-provider",
                        "model_id": "test-model",
                        "context_hash": "ctx-safe",
                        "raw_prompt": "SYSTEM SECRET PROMPT",
                        "chain_of_thought": "PRIVATE REASONING",
                        "cookie": cookie_value,
                        "credential": credential_value,
                        "local_path": "C:\\Users\\private\\runtime\\session.json",
                    },
                ),
                _source_event(1, "terminal_verdict", {"verdict": "blocked", "blocked_reason": "SAFE_BLOCKER"}),
            ],
        },
        proof_index={"loop_id": "redaction", "completion_truth": {}, "material_browser_receipts": []},
        mission_ledger={"task_id": "redaction", "blocked_reason": "SAFE_BLOCKER"},
    )

    rendered = json.dumps(archive.model_dump(mode="json"), sort_keys=True)
    assert "SYSTEM SECRET PROMPT" not in rendered
    assert "PRIVATE REASONING" not in rendered
    assert cookie_value not in rendered
    assert credential_value not in rendered
    assert "C:\\\\Users\\\\private" not in rendered
    assert "test-provider" in rendered
    assert "test-model" in rendered


def test_completed_presence_requires_persisted_accepting_finalgate() -> None:
    without_gate = PresenceProjector().project_replay(
        safe_evidence_snapshot={
            "run_id": "false-complete",
            "events": [
                _source_event(
                    0,
                    "FinalGate_result",
                    {
                        "status": "completed",
                        "operation": "real_browser.verify_extraction",
                        "finalgate_refs": ["action_finalgate_only"],
                    },
                ),
                _source_event(1, "terminal_verdict", {"verdict": "completed"}),
            ],
        },
        proof_index={
            "loop_id": "false-complete",
            "completion_truth": {"useful_answer_completion": True, "loop_closed": True},
            "material_browser_receipts": [],
        },
        mission_ledger={"task_id": "false-complete", "status": "completed"},
    )
    assert without_gate.events[-1].presence_state is PresenceState.TELEMETRY_INCOMPLETE
    assert without_gate.events[-1].gate_results["finalgate"] == TelemetryState.INCOMPLETE.value

    with_gate = PresenceProjector().project_replay(
        safe_evidence_snapshot={
            "run_id": "certified-complete",
            "events": [
                _source_event(0, "FinalGate_result", {"accepted": True, "status": "completed"}),
                _source_event(1, "terminal_verdict", {"verdict": "completed"}),
            ],
        },
        proof_index={
            "loop_id": "certified-complete",
            "completion_truth": {"useful_answer_completion": True, "loop_closed": True},
            "material_browser_receipts": [],
        },
        mission_ledger={"task_id": "certified-complete", "status": "completed"},
    )
    assert with_gate.events[-1].presence_state is PresenceState.COMPLETED
    assert with_gate.events[-1].gate_results["finalgate"] == "PASSED"


def test_sidecar_relay_failure_cannot_affect_mission_state() -> None:
    mission_state = {"status": "running", "actions": 4}

    def broken_sink(_: PresenceEventV1) -> None:
        raise RuntimeError("observer unavailable")

    relay = PresenceSidecarRelay(broken_sink)
    assert relay.publish(_presence_event(sequence=0, summary="Mission persists independently")) is False
    assert relay.failure_count == 1
    assert relay.last_failure_hash
    assert mission_state == {"status": "running", "actions": 4}


def test_snapshot_sidecar_emits_only_new_persisted_events_and_supports_reconnect() -> None:
    delivered: list[PresenceEventV1] = []
    sidecar = PresenceSnapshotSidecar(PresenceSidecarRelay(delivered.append))
    first_snapshot = {
        "run_id": "live-observer",
        "events": [
            _source_event(0, "run_started", {}),
            _source_event(1, "provider_decision_received", {"provider_decision_count": 1, "context_hash": "ctx-1"}),
        ],
    }
    proof_index = {
        "loop_id": "live-observer",
        "completion_truth": {},
        "material_browser_receipts": [],
    }
    ledger = {"task_id": "live-observer"}

    assert sidecar.observe(
        safe_evidence_snapshot=first_snapshot,
        proof_index=proof_index,
        mission_ledger=ledger,
    ) == 2
    assert sidecar.observe(
        safe_evidence_snapshot=first_snapshot,
        proof_index=proof_index,
        mission_ledger=ledger,
    ) == 0

    completed_snapshot = {
        **first_snapshot,
        "events": [
            *first_snapshot["events"],
            _source_event(2, "FinalGate_result", {"accepted": False, "status": "blocked"}),
            _source_event(3, "terminal_verdict", {"verdict": "blocked", "blocked_reason": "SAFE_BLOCKER"}),
        ],
    }
    assert sidecar.observe(
        safe_evidence_snapshot=completed_snapshot,
        proof_index=proof_index,
        mission_ledger={**ledger, "blocked_reason": "SAFE_BLOCKER"},
    ) == 2
    assert [event.sequence for event in delivered] == [0, 1, 2, 3]
    assert [event.sequence for event in sidecar.resume(mission_id="live-observer", after_sequence=1)] == [2, 3]


def test_safe_jsonl_journal_is_append_only_and_resumable(tmp_path: Path) -> None:
    journal = PresenceJsonlJournal(tmp_path / "presence" / "events.jsonl")
    first = _presence_event(sequence=0, summary="Mission persisted")
    second = _presence_event(sequence=1, summary="Proof persisted")

    journal.append(first)
    journal.append(second)
    restarted = PresenceJsonlJournal(journal.path)
    assert restarted.append(first) is False
    with pytest.raises(PresenceSequenceError, match="conflicting journal duplicate"):
        restarted.append(_presence_event(sequence=1, summary="Conflicting proof"))

    assert restarted.resume(mission_id="mission-test", after_sequence=0) == (second,)
    rendered = journal.path.read_text(encoding="utf-8")
    assert rendered.count("\n") == 2
    assert '"schema_version":"presence_event_v1"' in rendered
    assert '"can_execute":false' in rendered


def test_observer_cli_once_projects_persisted_files_without_runtime_calls(
    tmp_path: Path,
    capsys: Any,
) -> None:
    snapshot_path = tmp_path / "safe_evidence_snapshot.json"
    proof_path = tmp_path / "safe_browser_proof_index.json"
    ledger_path = tmp_path / "mission_ledger.json"
    journal_path = tmp_path / "presence" / "events.jsonl"
    snapshot_path.write_text(
        json.dumps(
            {
                "run_id": "cli-live-test",
                "events": [
                    _source_event(0, "run_started", {}),
                    _source_event(
                        1,
                        "terminal_verdict",
                        {"verdict": "blocked", "blocked_reason": "SAFE_BLOCKER"},
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    proof_path.write_text(
        json.dumps(
            {
                "loop_id": "cli-loop",
                "completion_truth": {},
                "material_browser_receipts": [],
            }
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps({"task_id": "cli-task", "blocked_reason": "SAFE_BLOCKER"}),
        encoding="utf-8",
    )

    result = presence_observer_main(
        [
            "--snapshot",
            str(snapshot_path),
            "--proof-index",
            str(proof_path),
            "--mission-ledger",
            str(ledger_path),
            "--journal",
            str(journal_path),
            "--once",
        ]
    )

    assert result == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "observer_once_completed"
    assert summary["events_emitted"] == 2
    assert summary["relay_failure_count"] == 0
    events = PresenceJsonlJournal(journal_path).resume(
        mission_id="cli-live-test",
        after_sequence=-1,
    )
    assert [event.sequence for event in events] == [0, 1]


def _presence_event(*, sequence: int, summary: str) -> PresenceEventV1:
    return PresenceEventV1(
        mission_id="mission-test",
        sequence=sequence,
        source_sequence=sequence,
        timestamp=f"2026-07-22T18:37:{sequence:02d}+00:00",
        presence_state=PresenceState.PLANNING,
        event_kind=PresenceEventKind.DECISION,
        safe_summary=summary,
        ledger_head=f"ledger-{sequence}",
        source_event_hash=f"source-{sequence}",
    )


def _source_event(sequence: int, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_type": event_type,
        "created_at": f"2026-07-22T18:{sequence // 60:02d}:{sequence % 60:02d}+00:00",
        "payload": payload,
        "event_hash": f"source-event-hash-{sequence}",
    }


def _historical_mdn_safe_snapshot() -> dict[str, Any]:
    events = [
        _source_event(0, "run_started", {"session_id": "safe-session-hash"}),
        _source_event(1, "provider_decision_received", {"context_hash": "ctx-1", "provider_decision_count": 1}),
        _source_event(2, "action_envelope_accepted", {"capability_id": "real_browser_control", "operation": "real_browser.search", "params_hash": "params-search"}),
        _source_event(3, "material_receipt_created", {"operation": "real_browser.search", "status": "blocked", "receipt_refs": ["product-search"]}),
        _source_event(4, "provider_decision_received", {"context_hash": "ctx-2", "provider_decision_count": 2}),
        _source_event(5, "action_envelope_accepted", {"capability_id": "real_browser_control", "operation": "real_browser.extract_evidence", "params_hash": "params-extract"}),
        _source_event(6, "material_receipt_created", {"operation": "real_browser.extract_evidence", "status": "completed", "receipt_refs": ["product-extract"]}),
        _source_event(7, "provider_decision_received", {"context_hash": "ctx-3", "provider_decision_count": 3}),
        _source_event(8, "action_envelope_accepted", {"capability_id": "real_browser_control", "operation": "real_browser.verify_extraction", "params_hash": "params-verify"}),
        _source_event(9, "material_receipt_created", {"operation": "real_browser.verify_extraction", "status": "completed", "receipt_refs": ["product-verify"]}),
        _source_event(10, "provider_decision_received", {"context_hash": "ctx-4", "provider_decision_count": 4}),
        _source_event(11, "action_envelope_accepted", {"capability_id": "sentinel_loop", "operation": "summarize_evidence", "params_hash": "params-summary"}),
        _source_event(12, "material_receipt_created", {"operation": "summarize_evidence", "status": "completed", "receipt_refs": ["product-summary"]}),
        _source_event(13, "provider_decision_received", {"context_hash": "ctx-5", "provider_decision_count": 5}),
        _source_event(14, "action_envelope_accepted", {"capability_id": "real_browser_control", "operation": "real_browser.observe", "params_hash": "params-observe"}),
        _source_event(15, "browser_action_started", {"operation": "real_browser.observe"}),
        _source_event(
            16,
            "runtime_failure_fact_created",
            {
                "operation": "real_browser.observe",
                "status": "blocked",
                "blocked_reason": "real_browser_runtime_dispatch_exception",
                "receipt_refs": ["product-observe-missing-1"],
                "runtime_failure_fact": {
                    "failure_code": "real_browser_runtime_dispatch_exception",
                    "failure_stage": "browser_runtime_observe",
                    "material_effect_observed": False,
                },
            },
        ),
        _source_event(17, "material_receipt_created", {"operation": "real_browser.observe", "status": "blocked", "receipt_refs": ["product-observe-missing-1"]}),
        _source_event(18, "provider_decision_received", {"context_hash": "ctx-6", "provider_decision_count": 6}),
        _source_event(
            19,
            "browser_progress_repetition_detected",
            {
                "operation": "real_browser.observe",
                "params_hash": "params-observe",
                "repetition_count": 1,
                "suppression_count": 1,
                "recommended_control_step": "choose_alternate_affordance",
            },
        ),
        _source_event(20, "provider_decision_received", {"context_hash": "ctx-7", "provider_decision_count": 7}),
        _source_event(21, "action_envelope_accepted", {"capability_id": "real_browser_control", "operation": "real_browser.observe", "params_hash": "params-observe-recovery"}),
        _source_event(22, "browser_action_started", {"operation": "real_browser.observe"}),
        _source_event(
            23,
            "runtime_failure_fact_created",
            {
                "operation": "real_browser.observe",
                "status": "blocked",
                "blocked_reason": "real_browser_runtime_dispatch_exception",
                "receipt_refs": ["product-observe-missing-2"],
                "runtime_failure_fact": {
                    "failure_code": "real_browser_runtime_dispatch_exception",
                    "failure_stage": "browser_runtime_observe",
                    "material_effect_observed": False,
                },
            },
        ),
        _source_event(24, "material_receipt_created", {"operation": "real_browser.observe", "status": "blocked", "receipt_refs": ["product-observe-missing-2"]}),
        _source_event(25, "provider_decision_received", {"context_hash": "ctx-8", "provider_decision_count": 8}),
        _source_event(
            26,
            "browser_progress_repetition_detected",
            {
                "operation": "real_browser.observe",
                "params_hash": "params-observe",
                "repetition_count": 1,
                "suppression_count": 3,
                "recommended_control_step": "declare_honest_blocker_with_attempt_history",
            },
        ),
        _source_event(
            27,
            "browser_proof_index_created",
            {
                "browser_receipt_missing_count": 2,
                "browser_receipt_readable_count": 3,
                "material_browser_receipt_count": 5,
            },
        ),
        _source_event(
            28,
            "FinalGate_result",
            {
                "accepted": False,
                "status": "blocked",
                "reason": "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
            },
        ),
        _source_event(
            29,
            "terminal_verdict",
            {
                "verdict": "blocked",
                "blocked_reason": "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
            },
        ),
    ]
    return {
        "schema_version": "crash-safe-live-run-evidence/v1",
        "run_id": "brp_v1_mdn_css_has",
        "event_count": len(events),
        "events": events,
        "latest_event_hash": events[-1]["event_hash"],
        "source_artifact_hash": "d4e48ee30b3eb93c6a95b15ff82a690313a57b3b923516da94277d21d431d25f",
    }


def _historical_mdn_proof_index() -> dict[str, Any]:
    state = "83bf54c3d16e26c6952284f41dcdff1d15e84f47e9a55441dbe2af1a80881e1e"
    return {
        "schema_version": "browser_proof_index_v1",
        "loop_id": "product_action_kernel_task_loop_814c1643e19d48a0a942ca6b795cbef6",
        "status": "blocked",
        "final_reason": "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
        "browser_receipt_missing_count": 2,
        "browser_receipt_readable_count": 3,
        "material_browser_receipt_count": 5,
        "completion_truth": {
            "browser_receipt_missing_count": 2,
            "browser_receipt_readable_count": 3,
            "honest_blocker_present": False,
            "loop_closed": False,
            "mission_objective_satisfied": False,
            "useful_answer_completion": False,
        },
        "material_browser_receipts": [
            {
                "operation": "real_browser.search",
                "action_status": "recoverable_failed",
                "browser_receipt_readable": True,
                "browser_receipt_ref": "browser-search",
                "product_receipt_ref": "product-search",
                "receipt_hash": "receipt-search",
                "before_state_hash": "state-0",
                "after_state_hash": "state-0",
                "evidence_refs": ["browser_search_failure:safe"],
            },
            {
                "operation": "real_browser.extract_evidence",
                "action_status": "completed",
                "browser_receipt_readable": True,
                "browser_receipt_ref": "browser-extract",
                "product_receipt_ref": "product-extract",
                "receipt_hash": "receipt-extract",
                "before_state_hash": state,
                "after_state_hash": state,
                "evidence_refs": ["browser_env_state:safe"],
            },
            {
                "operation": "real_browser.verify_extraction",
                "action_status": "passed",
                "browser_receipt_readable": True,
                "browser_receipt_ref": "browser-verify",
                "product_receipt_ref": "product-verify",
                "receipt_hash": "receipt-verify",
                "before_state_hash": state,
                "after_state_hash": state,
                "evidence_refs": ["browser_env_state:safe"],
            },
            {
                "operation": "real_browser.observe",
                "action_status": None,
                "browser_receipt_readable": False,
                "browser_receipt_ref": "",
                "product_receipt_ref": "product-observe-missing-1",
            },
            {
                "operation": "real_browser.observe",
                "action_status": None,
                "browser_receipt_readable": False,
                "browser_receipt_ref": "",
                "product_receipt_ref": "product-observe-missing-2",
            },
        ],
    }
