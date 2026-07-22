from __future__ import annotations

from sentinel.operator.browser_cortex_divergence_harness import build_browser_cortex_divergence_trace


def test_divergence_harness_captures_repeated_action_without_progress_and_session_failure() -> None:
    safe_evidence_snapshot = {
        "events": [
            {"sequence": 0, "event_type": "provider_decision_received", "payload": {"context_hash": "ctx1", "provider_decision_count": 1}},
            {
                "sequence": 1,
                "event_type": "action_envelope_accepted",
                "payload": {"capability_id": "real_browser_control", "operation": "real_browser.search", "params_hash": "q1"},
            },
            {
                "sequence": 2,
                "event_type": "material_receipt_created",
                "payload": {"operation": "real_browser.search", "status": "completed", "receipt_refs": ["r1"]},
            },
            {"sequence": 3, "event_type": "provider_decision_received", "payload": {"context_hash": "ctx2", "provider_decision_count": 2}},
            {
                "sequence": 4,
                "event_type": "action_envelope_accepted",
                "payload": {"capability_id": "real_browser_control", "operation": "real_browser.search", "params_hash": "q1"},
            },
            {
                "sequence": 5,
                "event_type": "runtime_failure_fact_created",
                "payload": {
                    "operation": "real_browser.search",
                    "status": "blocked",
                    "blocked_reason": "BODY_SESSION_UNAVAILABLE",
                    "runtime_failure_fact": {
                        "failure_stage": "session_lifecycle",
                        "failure_code": "real_browser_search_session_open_failed",
                        "material_effect_observed": False,
                    },
                },
            },
            {
                "sequence": 6,
                "event_type": "model_visible_failure_packet_created",
                "payload": {
                    "model_visible_body_failure_packet": {
                        "available_affordances": {"recommended_browser_actions": [], "recovery_actions": []},
                        "session_continuity": {
                            "root_lease_present": True,
                            "root_lifecycle_state": "active_after_reopen_failed",
                        },
                    }
                },
            },
            {
                "sequence": 7,
                "event_type": "material_receipt_created",
                "payload": {
                    "operation": "real_browser.search",
                    "status": "blocked",
                    "blocked_reason": "BODY_SESSION_UNAVAILABLE",
                    "receipt_refs": ["r2"],
                },
            },
        ]
    }
    proof_index = {
        "completion_truth": {"mission_objective_satisfied": False, "useful_answer_completion": False},
        "material_browser_receipts": [
            {
                "operation": "real_browser.search",
                "action_status": "completed",
                "before_state_hash": "s0",
                "after_state_hash": "s1",
                "browser_environment_state_hash": "env1",
                "root_browser_lease_id_hash": "lease",
                "backend_context_identity_hash": "ctx",
                "evidence_refs": ["e1"],
            },
            {
                "operation": "real_browser.search",
                "action_status": "recoverable_failed",
                "before_state_hash": "s1",
                "after_state_hash": "s1",
                "browser_environment_state_hash": "env1",
                "root_browser_lease_id_hash": "lease",
                "backend_context_identity_hash": "ctx",
                "evidence_refs": ["e1"],
                "typed_outcome": {"outcome_kind": "FAILED_RECOVERABLE", "failure_code": "real_browser_search_session_open_failed"},
            },
        ],
    }
    ledger = {
        "task_id": "synthetic_session_failure",
        "blocked_reason": "BODY_SESSION_UNAVAILABLE",
        "capability_sequence": [
            "real_browser_control:real_browser.search",
            "real_browser_control:real_browser.search",
        ],
    }

    trace = build_browser_cortex_divergence_trace(
        safe_evidence_snapshot=safe_evidence_snapshot,
        proof_index=proof_index,
        mission_ledger=ledger,
    )

    assert trace["schema_version"] == "browser_cortex_divergence_trace_v1"
    assert len(trace["decisions"]) == 2
    second = trace["decisions"][1]
    assert second["normalized_decision"]["operation"] == "real_browser.search"
    assert second["receipt"]["status"] == "blocked"
    assert second["session_lease_transition"]["pre_state"] == "ACTIVE"
    assert second["session_lease_transition"]["post_state"] == "DEGRADED"
    assert second["progress"]["made_progress"] is False
    assert second["progress"]["reason"] == "same_action_params_state_and_evidence"
    assert trace["first_causal_divergence"]["decision_index"] == 2
    assert trace["first_causal_divergence"]["classification"] == "REPEATED_ACTION_WITHOUT_PROGRESS"
