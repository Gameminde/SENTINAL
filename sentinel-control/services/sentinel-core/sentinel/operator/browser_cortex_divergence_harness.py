from __future__ import annotations

from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import sanitize_operator_refs


_SCHEMA_VERSION = "browser_cortex_divergence_trace_v1"
_UNKNOWN = "unknown"


def build_browser_cortex_divergence_trace(
    *,
    safe_evidence_snapshot: dict[str, Any],
    proof_index: dict[str, Any],
    mission_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct a safe per-decision divergence trace from existing artifacts.

    The harness is observational: it consumes persisted safe events and proof
    index entries, then names the first causal divergence it can support. It
    never replays effects and never infers raw browser state that was not
    captured by a receipt or safe evidence event.
    """

    events = _events(safe_evidence_snapshot)
    receipts = _material_browser_receipts(proof_index)
    ledger = mission_ledger if isinstance(mission_ledger, dict) else {}
    receipt_cursor = 0
    decisions: list[dict[str, Any]] = []
    current_decision: dict[str, Any] | None = None
    current_evidence_refs: set[str] = set()
    seen_signatures: dict[str, int] = {}
    latest_state = _UNKNOWN
    latest_session = _session_identity({})
    latest_failure_packet: dict[str, Any] = {}

    for event in events:
        event_type = str(event.get("event_type") or "")
        payload = _payload(event)

        if event_type == "provider_decision_received":
            if current_decision is not None:
                decisions.append(current_decision)
            current_decision = _new_decision(
                index=len(decisions) + 1,
                payload=payload,
                latest_state=latest_state,
                evidence_refs=current_evidence_refs,
                latest_session=latest_session,
                latest_failure_packet=latest_failure_packet,
            )
            continue

        if current_decision is None:
            continue

        if event_type == "action_envelope_accepted":
            current_decision["normalized_decision"] = _normalized_decision(payload)
            current_decision["product_action"] = _product_action_from_payload(payload)
            continue

        if event_type == "browser_action_started":
            current_decision["product_action"] = _merge_dicts(
                current_decision.get("product_action"),
                {
                    "operation": str(payload.get("operation") or current_decision["normalized_decision"].get("operation") or ""),
                    "status": "started",
                },
            )
            continue

        if event_type == "runtime_failure_fact_created":
            failure_fact = _runtime_failure_fact(payload)
            current_decision["runtime_failure_fact"] = failure_fact
            current_decision["receipt"] = _receipt_from_failure(payload, failure_fact)
            continue

        if event_type == "model_visible_failure_packet_created":
            latest_failure_packet = _model_visible_failure_packet(payload)
            current_decision["model_state_presented"]["last_failure_packet_shape"] = _packet_shape(latest_failure_packet)
            current_decision["announced_affordances"] = _affordances_from_packet(latest_failure_packet)
            continue

        if event_type == "material_receipt_created":
            receipt, receipt_cursor = _next_receipt_for_event(
                payload=payload,
                receipts=receipts,
                start=receipt_cursor,
            )
            _apply_receipt_to_decision(
                current_decision,
                receipt=receipt,
                event_payload=payload,
                current_evidence_refs=current_evidence_refs,
                seen_signatures=seen_signatures,
            )
            latest_state = current_decision.get("post_state_fingerprint") or latest_state
            latest_session = _session_identity(receipt)
            continue

        if event_type == "browser_progress_repetition_detected":
            _apply_progress_guard_suppression(current_decision, payload)
            continue

    if current_decision is not None:
        decisions.append(current_decision)

    _finalize_missing_progress(decisions, seen_signatures)
    return {
        "schema_version": _SCHEMA_VERSION,
        "task_id": str(ledger.get("task_id") or proof_index.get("loop_id") or _UNKNOWN),
        "blocked_reason": str(ledger.get("blocked_reason") or ""),
        "source_event_count": len(events),
        "material_receipt_count": len(receipts),
        "decisions": decisions,
        "first_causal_divergence": _first_causal_divergence(decisions),
        "completion_truth": proof_index.get("completion_truth") if isinstance(proof_index.get("completion_truth"), dict) else {},
        "artifact_hashes": {
            "safe_evidence_snapshot_hash": stable_hash(safe_evidence_snapshot),
            "proof_index_hash": str(proof_index.get("proof_index_hash") or stable_hash(proof_index)),
            "mission_ledger_hash": stable_hash(ledger),
        },
        "instrumentation_gaps": _instrumentation_gaps(decisions),
        "data_not_authority": True,
        "can_execute": False,
    }


def _new_decision(
    *,
    index: int,
    payload: dict[str, Any],
    latest_state: str,
    evidence_refs: set[str],
    latest_session: dict[str, Any],
    latest_failure_packet: dict[str, Any],
) -> dict[str, Any]:
    return {
        "decision_index": index,
        "provider_decision_count": _safe_int(payload.get("provider_decision_count")) or index,
        "pre_state_fingerprint": latest_state,
        "model_state_presented": {
            "context_hash": str(payload.get("context_hash") or ""),
            "full_state_available": False,
            "full_state_reason": "safe_evidence_snapshot_records_context_hash_not_full_model_prompt",
            "previous_failure_packet_shape": _packet_shape(latest_failure_packet),
        },
        "announced_affordances": _affordances_from_packet(latest_failure_packet),
        "raw_decision": {
            "raw_decision_available": False,
            "reason": "raw_provider_output_not_persisted_by_design",
        },
        "normalized_decision": {},
        "product_action": {},
        "receipt": {},
        "post_state_fingerprint": latest_state,
        "evidence_fingerprint_before": _evidence_fingerprint(evidence_refs),
        "evidence_fingerprint_after": _evidence_fingerprint(evidence_refs),
        "session_lease_transition": {
            "pre_state": _session_state_from_identity(latest_session),
            "post_state": _session_state_from_identity(latest_session),
            "pre_identity": latest_session,
            "post_identity": latest_session,
        },
        "progress": {"made_progress": False, "reason": "awaiting_material_receipt"},
        "finish_eligibility": {"eligible": False, "reason": "no_finish_receipt_for_decision"},
        "runtime_failure_fact": {},
    }


def _apply_receipt_to_decision(
    decision: dict[str, Any],
    *,
    receipt: dict[str, Any],
    event_payload: dict[str, Any],
    current_evidence_refs: set[str],
    seen_signatures: dict[str, int],
) -> None:
    before = str(receipt.get("before_state_hash") or decision.get("pre_state_fingerprint") or _UNKNOWN)
    after = str(receipt.get("after_state_hash") or before or _UNKNOWN)
    operation = str(
        receipt.get("operation")
        or event_payload.get("operation")
        or decision.get("normalized_decision", {}).get("operation")
        or ""
    )
    status = str(event_payload.get("status") or receipt.get("action_status") or "")
    evidence_before = set(current_evidence_refs)
    evidence_delta = receipt.get("evidence_delta") if isinstance(receipt.get("evidence_delta"), dict) else {}
    if evidence_delta and evidence_delta.get("changed") is False:
        evidence_after = set(evidence_before)
    elif evidence_delta and evidence_delta.get("changed") is True:
        evidence_after = evidence_before | set(
            sanitize_operator_refs(_list_of_strings(evidence_delta.get("added_refs")))
        )
    else:
        evidence_after = evidence_before | set(_evidence_refs(receipt))
    decision["pre_state_fingerprint"] = before
    decision["post_state_fingerprint"] = after
    decision["evidence_fingerprint_before"] = _evidence_fingerprint(evidence_before)
    decision["evidence_fingerprint_after"] = _evidence_fingerprint(evidence_after)
    decision["product_action"] = _merge_dicts(
        decision.get("product_action"),
        {
            "operation": operation,
            "status": "completed" if status == "completed" else status or _UNKNOWN,
            "receipt_refs": sanitize_operator_refs(_list_of_strings(event_payload.get("receipt_refs"))),
        },
    )
    decision["receipt"] = {
        "status": _receipt_status(status),
        "operation": operation,
        "typed_outcome": _safe_typed_outcome(receipt),
        "evidence_delta": evidence_delta,
        "blocked_reason": str(event_payload.get("blocked_reason") or receipt.get("blocked_reason") or ""),
        "receipt_refs": sanitize_operator_refs(_list_of_strings(event_payload.get("receipt_refs"))),
        "browser_receipt_ref": str(receipt.get("browser_receipt_ref") or ""),
        "receipt_hash": str(receipt.get("receipt_hash") or ""),
    }
    decision["session_lease_transition"] = {
        "pre_state": _session_state_before(receipt),
        "post_state": _session_state_after(receipt, status=status, event_payload=event_payload),
        "pre_identity": _session_identity(receipt),
        "post_identity": _session_identity(receipt),
    }
    decision["progress"] = _progress_for_decision(
        decision=decision,
        before=before,
        after=after,
        evidence_before=evidence_before,
        evidence_after=evidence_after,
        seen_signatures=seen_signatures,
    )
    decision["finish_eligibility"] = _finish_eligibility_from_receipt(receipt)
    current_evidence_refs.clear()
    current_evidence_refs.update(evidence_after)


def _apply_progress_guard_suppression(decision: dict[str, Any], payload: dict[str, Any]) -> None:
    normalized = decision.get("normalized_decision") if isinstance(decision.get("normalized_decision"), dict) else {}
    if not normalized:
        decision["normalized_decision"] = _normalized_decision(payload)
    decision["product_action"] = _merge_dicts(
        decision.get("product_action"),
        {
            "operation": str(payload.get("operation") or decision["normalized_decision"].get("operation") or ""),
            "status": "suppressed_repeated_action",
            "suppression_count": _safe_int(payload.get("suppression_count")),
            "repetition_signature_hash": str(payload.get("repetition_signature_hash") or ""),
        },
    )
    decision["receipt"] = {
        "status": "suppressed_repeated_action",
        "operation": str(payload.get("operation") or decision["normalized_decision"].get("operation") or ""),
        "typed_outcome": {},
        "blocked_reason": "",
        "receipt_refs": [],
        "browser_receipt_ref": "",
        "receipt_hash": "",
    }
    decision["progress"] = {
        "made_progress": False,
        "reason": "suppressed_repeated_action",
        "repetition_count": _safe_int(payload.get("repetition_count")),
        "suppression_count": _safe_int(payload.get("suppression_count")),
        "recommended_control_step": str(payload.get("recommended_control_step") or ""),
        "state_changed": False,
        "evidence_changed": False,
    }


def _progress_for_decision(
    *,
    decision: dict[str, Any],
    before: str,
    after: str,
    evidence_before: set[str],
    evidence_after: set[str],
    seen_signatures: dict[str, int],
) -> dict[str, Any]:
    state_changed = bool(before and after and before != after)
    evidence_changed = evidence_before != evidence_after
    signature = _decision_signature(decision)
    previous_index = seen_signatures.get(signature)
    seen_signatures.setdefault(signature, _safe_int(decision.get("decision_index")))
    if previous_index is not None and not state_changed and not evidence_changed:
        return {
            "made_progress": False,
            "reason": "same_action_params_state_and_evidence",
            "first_seen_decision_index": previous_index,
            "state_changed": False,
            "evidence_changed": False,
        }
    if state_changed or evidence_changed:
        return {
            "made_progress": True,
            "reason": "state_or_evidence_delta",
            "state_changed": state_changed,
            "evidence_changed": evidence_changed,
        }
    return {
        "made_progress": False,
        "reason": "no_state_or_evidence_delta",
        "state_changed": False,
        "evidence_changed": False,
    }


def _finalize_missing_progress(decisions: list[dict[str, Any]], seen_signatures: dict[str, int]) -> None:
    for decision in decisions:
        if decision.get("progress", {}).get("reason") != "awaiting_material_receipt":
            continue
        normalized = decision.get("normalized_decision") if isinstance(decision.get("normalized_decision"), dict) else {}
        if not normalized:
            decision["progress"] = {
                "made_progress": False,
                "reason": "decision_absent",
                "state_changed": False,
                "evidence_changed": False,
            }
            continue
        failure = decision.get("runtime_failure_fact") if isinstance(decision.get("runtime_failure_fact"), dict) else {}
        if failure:
            decision["progress"] = {
                "made_progress": False,
                "reason": str(failure.get("failure_code") or "runtime_failure_without_material_progress"),
                "state_changed": False,
                "evidence_changed": False,
            }
            continue
        signature = _decision_signature(decision)
        previous_index = seen_signatures.get(signature)
        if previous_index is not None:
            decision["progress"] = {
                "made_progress": False,
                "reason": "same_action_params_state_and_evidence",
                "first_seen_decision_index": previous_index,
                "state_changed": False,
                "evidence_changed": False,
            }
        seen_signatures.setdefault(signature, _safe_int(decision.get("decision_index")))


def _first_causal_divergence(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    for decision in decisions:
        failure = decision.get("runtime_failure_fact") if isinstance(decision.get("runtime_failure_fact"), dict) else {}
        receipt = decision.get("receipt") if isinstance(decision.get("receipt"), dict) else {}
        typed = receipt.get("typed_outcome") if isinstance(receipt.get("typed_outcome"), dict) else {}
        failure_stage = str(failure.get("failure_stage") or typed.get("failure_stage") or "")
        failure_code = str(failure.get("failure_code") or typed.get("failure_code") or "")
        if failure_stage == "browser_runtime_observe" or failure_code.startswith("real_browser_observe_"):
            return {
                "decision_index": _safe_int(decision.get("decision_index")),
                "classification": "BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS",
                "evidence": {
                    "failure_code": failure_code,
                    "failure_stage": failure_stage or "browser_runtime_observe",
                    "material_effect_observed": bool(failure.get("material_effect_observed")),
                },
            }
    for decision in decisions:
        progress = decision.get("progress") if isinstance(decision.get("progress"), dict) else {}
        if progress.get("reason") == "suppressed_repeated_action":
            return {
                "decision_index": _safe_int(decision.get("decision_index")),
                "classification": "REPEATED_ACTION_SUPPRESSED_WITHOUT_PROGRESS",
                "evidence": {
                    "operation": str(decision.get("normalized_decision", {}).get("operation") or ""),
                    "suppression_count": _safe_int(progress.get("suppression_count")),
                    "repetition_count": _safe_int(progress.get("repetition_count")),
                },
            }
    for decision in decisions:
        progress = decision.get("progress") if isinstance(decision.get("progress"), dict) else {}
        if progress.get("reason") == "same_action_params_state_and_evidence":
            return {
                "decision_index": _safe_int(decision.get("decision_index")),
                "classification": "REPEATED_ACTION_WITHOUT_PROGRESS",
                "evidence": {
                    "operation": str(decision.get("normalized_decision", {}).get("operation") or ""),
                    "pre_state_fingerprint": str(decision.get("pre_state_fingerprint") or ""),
                    "evidence_fingerprint_before": str(decision.get("evidence_fingerprint_before") or ""),
                },
            }
    for decision in decisions:
        failure = decision.get("runtime_failure_fact") if isinstance(decision.get("runtime_failure_fact"), dict) else {}
        affordances = decision.get("announced_affordances") if isinstance(decision.get("announced_affordances"), dict) else {}
        if (
            failure.get("failure_stage") == "session_lifecycle"
            and not affordances.get("recovery_actions")
        ):
            return {
                "decision_index": _safe_int(decision.get("decision_index")),
                "classification": "SESSION_FAILURE_WITHOUT_RECOVERY_AFFORDANCE",
                "evidence": {
                    "failure_code": str(failure.get("failure_code") or ""),
                    "material_effect_observed": bool(failure.get("material_effect_observed")),
                },
            }
    return {
        "decision_index": 0,
        "classification": "NO_CAUSAL_DIVERGENCE_IDENTIFIED",
        "evidence": {},
    }


def _events(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    events = snapshot.get("events") if isinstance(snapshot, dict) else []
    if not isinstance(events, list):
        return []
    return sorted((item for item in events if isinstance(item, dict)), key=lambda item: _safe_int(item.get("sequence")))


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _material_browser_receipts(index: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = index.get("material_browser_receipts") if isinstance(index, dict) else []
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def _next_receipt_for_event(
    *,
    payload: dict[str, Any],
    receipts: list[dict[str, Any]],
    start: int,
) -> tuple[dict[str, Any], int]:
    operation = str(payload.get("operation") or "")
    status = str(payload.get("status") or "")
    for index in range(start, len(receipts)):
        receipt = receipts[index]
        if operation and str(receipt.get("operation") or "") != operation:
            continue
        if status and not _status_matches(receipt_status=str(receipt.get("action_status") or ""), event_status=status):
            continue
        return receipt, index + 1
    return {}, start


def _normalized_decision(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability_id": str(payload.get("capability_id") or ""),
        "operation": str(payload.get("operation") or ""),
        "params_hash": str(payload.get("params_hash") or ""),
        "target_ref_hash": str(payload.get("target_ref_hash") or ""),
        "trusted_runtime_fields_available": False,
        "action_envelope_internal": True,
    }


def _product_action_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": str(payload.get("operation") or ""),
        "status": "accepted",
        "capability_id": str(payload.get("capability_id") or ""),
    }


def _receipt_from_failure(payload: dict[str, Any], failure_fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _receipt_status(str(payload.get("status") or "")),
        "operation": str(payload.get("operation") or ""),
        "blocked_reason": str(payload.get("blocked_reason") or ""),
        "typed_outcome": {
            "outcome_kind": "FAILED_RECOVERABLE" if failure_fact.get("retryable") is not False else "FAILED_BLOCKED",
            "failure_code": str(failure_fact.get("failure_code") or ""),
        },
        "receipt_refs": [],
    }


def _runtime_failure_fact(payload: dict[str, Any]) -> dict[str, Any]:
    fact = payload.get("runtime_failure_fact")
    if not isinstance(fact, dict):
        fact = payload
    return {
        "failure_stage": str(fact.get("failure_stage") or ""),
        "failure_code": str(fact.get("failure_code") or payload.get("blocked_reason") or ""),
        "material_effect_observed": bool(fact.get("material_effect_observed")),
        "retryable": fact.get("retryable") if isinstance(fact.get("retryable"), bool) else None,
        "resource_kind": str(fact.get("resource_kind") or ""),
    }


def _model_visible_failure_packet(payload: dict[str, Any]) -> dict[str, Any]:
    packet = payload.get("model_visible_body_failure_packet")
    return packet if isinstance(packet, dict) else {}


def _affordances_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet:
        return {
            "recommended_browser_actions": "unknown",
            "recovery_actions": "unknown",
            "source": "no_failure_packet_available",
        }
    available = packet.get("available_affordances") if isinstance(packet.get("available_affordances"), dict) else {}
    current_page = (
        packet.get("safe_current_page_state_summary")
        if isinstance(packet.get("safe_current_page_state_summary"), dict)
        else {}
    )
    recommended = _list_of_strings(available.get("recommended_browser_actions"))
    recovery = _list_of_strings(available.get("recovery_actions"))
    if not recommended:
        recommended = _list_of_strings(available.get("safe_browser_skills"))
    if not recovery:
        recovery = _list_of_strings(available.get("recommended_recovery"))
    if not recovery:
        recovery = _list_of_strings(available.get("recovery_affordances"))
    search_refs = _list_of_strings(available.get("search_like_refs"))
    if not search_refs:
        search_refs = _list_of_strings(current_page.get("search_like_refs"))
    return {
        "recommended_browser_actions": sanitize_operator_refs(recommended),
        "recovery_actions": sanitize_operator_refs(recovery),
        "search_like_refs": sanitize_operator_refs(search_refs),
        "source": "model_visible_body_failure_packet",
    }


def _packet_shape(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet:
        return {"available": False, "top_level_keys": []}
    return {
        "available": True,
        "top_level_keys": sorted(str(key) for key in packet.keys())[:40],
        "packet_hash": stable_hash(packet),
    }


def _safe_typed_outcome(receipt: dict[str, Any]) -> dict[str, Any]:
    outcome = receipt.get("typed_outcome")
    if not isinstance(outcome, dict):
        outcome = receipt.get("typed_observation")
    if not isinstance(outcome, dict):
        return {}
    allowed = {
        "outcome_kind",
        "failure_code",
        "failure_stage",
        "resource_kind",
        "exception_class",
        "exception_hash",
        "material_effect_observed",
        "input_written",
        "submission_attempted",
        "search_materially_successful",
        "search_materially_uncertain",
    }
    return {key: outcome.get(key) for key in allowed if key in outcome}


def _session_identity(receipt: dict[str, Any]) -> dict[str, str]:
    return {
        "root_browser_lease_id_hash": str(receipt.get("root_browser_lease_id_hash") or ""),
        "browser_engine_identity_hash": str(receipt.get("browser_engine_identity_hash") or ""),
        "backend_context_identity_hash": str(receipt.get("backend_context_identity_hash") or ""),
        "page_identity_hash": str(receipt.get("page_identity_hash") or ""),
        "child_workspace_handle_hash": str(receipt.get("child_workspace_handle_hash") or ""),
    }


def _session_state_before(receipt: dict[str, Any]) -> str:
    if receipt.get("root_browser_lease_id_hash") or receipt.get("backend_context_identity_hash"):
        return "ACTIVE"
    return _UNKNOWN


def _session_state_after(receipt: dict[str, Any], *, status: str, event_payload: dict[str, Any]) -> str:
    if str(event_payload.get("blocked_reason") or "").upper() == "BODY_SESSION_UNAVAILABLE":
        return "DEGRADED"
    if str(status or "").lower() in {"recoverable_failed", "blocked", "failed"}:
        outcome = _safe_typed_outcome(receipt)
        if str(outcome.get("failure_code") or "").endswith("session_open_failed"):
            return "DEGRADED"
    if receipt.get("root_browser_lease_id_hash") or receipt.get("backend_context_identity_hash"):
        return "ACTIVE"
    return _UNKNOWN


def _session_state_from_identity(identity: dict[str, Any]) -> str:
    return "ACTIVE" if identity.get("root_browser_lease_id_hash") or identity.get("backend_context_identity_hash") else _UNKNOWN


def _finish_eligibility_from_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    truth = receipt.get("completion_truth") if isinstance(receipt.get("completion_truth"), dict) else {}
    if truth:
        eligible = bool(truth.get("mission_objective_satisfied") or truth.get("honest_blocker_present"))
        return {"eligible": eligible, "reason": "completion_truth_available"}
    return {"eligible": False, "reason": "no_completion_truth_on_receipt"}


def _decision_signature(decision: dict[str, Any]) -> str:
    normalized = decision.get("normalized_decision") if isinstance(decision.get("normalized_decision"), dict) else {}
    state = str(decision.get("post_state_fingerprint") or decision.get("pre_state_fingerprint") or "")
    evidence = str(decision.get("evidence_fingerprint_after") or decision.get("evidence_fingerprint_before") or "")
    return stable_hash(
        {
            "operation": normalized.get("operation"),
            "params_hash": normalized.get("params_hash"),
            "target_ref_hash": normalized.get("target_ref_hash"),
            "state": state,
            "evidence": evidence,
        }
    )


def _evidence_refs(receipt: dict[str, Any]) -> list[str]:
    return sanitize_operator_refs(_list_of_strings(receipt.get("evidence_refs")))


def _evidence_fingerprint(evidence_refs: set[str]) -> str:
    return stable_hash(sorted(evidence_refs))


def _receipt_status(value: str) -> str:
    lowered = str(value or "").lower()
    if lowered in {"recoverable_failed", "blocked", "failed"}:
        return "blocked" if lowered == "blocked" else lowered
    if lowered in {"observation_success", "typed_observation_failure"}:
        return lowered
    if lowered == "completed":
        return "completed"
    return lowered or _UNKNOWN


def _status_matches(*, receipt_status: str, event_status: str) -> bool:
    receipt = _receipt_status(receipt_status)
    event = _receipt_status(event_status)
    if receipt == event:
        return True
    if receipt == "typed_observation_failure" and event in {"blocked", "recoverable_failed", "failed"}:
        return True
    return {receipt, event} <= {"blocked", "recoverable_failed", "failed"}


def _instrumentation_gaps(decisions: list[dict[str, Any]]) -> list[str]:
    gaps: set[str] = set()
    for decision in decisions:
        if decision.get("raw_decision", {}).get("raw_decision_available") is False:
            gaps.add("raw_decision_not_persisted_by_design")
        if decision.get("model_state_presented", {}).get("full_state_available") is False:
            gaps.add("full_model_presented_state_not_persisted")
        affordances = decision.get("announced_affordances")
        if isinstance(affordances, dict) and affordances.get("recommended_browser_actions") == "unknown":
            gaps.add("announced_affordances_unknown_without_failure_packet")
    return sorted(gaps)


def _merge_dicts(first: Any, second: dict[str, Any]) -> dict[str, Any]:
    merged = dict(first) if isinstance(first, dict) else {}
    merged.update(second)
    return merged


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list | tuple | set):
        return []
    return [str(item) for item in value if str(item)]


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


__all__ = ["build_browser_cortex_divergence_trace"]
