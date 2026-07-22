from __future__ import annotations

from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.redaction import sanitize_operator_refs


class BrowserProgressRepetitionGuard:
    """Detect browser action repetition that produces no operational progress."""

    def __init__(self) -> None:
        self._no_progress_attempts: list[dict[str, Any]] = []
        self._suppression_counts: dict[str, int] = {}

    def evaluate_repetition(self, *, decision: ActionEnvelope, context: dict[str, Any]) -> dict[str, Any] | None:
        signature = _operation_signature(decision, context)
        count = sum(1 for attempt in self._no_progress_attempts if attempt.get("signature_hash") == signature)
        if count <= 0:
            return None
        return {
            "event": "browser_repeated_action_without_progress",
            "repetition_signature_hash": signature,
            "repetition_count": count,
            "suppression_count": int(self._suppression_counts.get(signature, 0)),
            "capability_id": decision.capability_id,
            "operation": decision.operation,
            "params_hash": stable_hash(dict(decision.params)),
            "state_fingerprint": _state_fingerprint(context),
            "evidence_fingerprint": _evidence_fingerprint(context),
            "recommended_control_step": _recommended_control_step(count),
            "data_not_authority": True,
            "can_execute": False,
        }

    def register_suppression(self, repeat: dict[str, Any]) -> dict[str, Any]:
        signature = str(repeat.get("repetition_signature_hash") or "")
        next_count = int(self._suppression_counts.get(signature, 0)) + 1
        self._suppression_counts[signature] = next_count
        return {
            **repeat,
            "suppression_count": next_count,
            "recommended_control_step": _recommended_control_step(next_count),
            "data_not_authority": True,
            "can_execute": False,
        }

    def record_attempt(
        self,
        *,
        decision: ActionEnvelope,
        pre_context: dict[str, Any],
        post_context: dict[str, Any],
        material_progress: bool = False,
        reported_state_or_evidence_delta: bool | None = None,
    ) -> dict[str, Any]:
        pre_state = _state_fingerprint(pre_context)
        post_state = _state_fingerprint(post_context)
        pre_evidence = _evidence_fingerprint(pre_context)
        post_evidence = _evidence_fingerprint(post_context)
        context_delta = bool(pre_state != post_state or pre_evidence != post_evidence)
        progress_detected = bool(
            material_progress
            or (reported_state_or_evidence_delta is True)
            or (reported_state_or_evidence_delta is None and context_delta)
        )
        signature_context = post_context if reported_state_or_evidence_delta is False else pre_context
        record = {
            "capability_id": decision.capability_id,
            "operation": decision.operation,
            "params_hash": stable_hash(dict(decision.params)),
            "pre_state_fingerprint": pre_state,
            "post_state_fingerprint": post_state,
            "pre_evidence_fingerprint": pre_evidence,
            "post_evidence_fingerprint": post_evidence,
            "material_progress": bool(material_progress),
            "reported_state_or_evidence_delta": reported_state_or_evidence_delta,
            "progress_detected": progress_detected,
            "signature_hash": _operation_signature(decision, signature_context),
            "data_not_authority": True,
            "can_execute": False,
        }
        if not progress_detected:
            self._no_progress_attempts.append(record)
        return dict(record)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "schema_version": "browser_progress_repetition_guard_v1",
            "no_progress_attempt_count": len(self._no_progress_attempts),
            "recent_no_progress_attempts": [
                {
                    key: value
                    for key, value in attempt.items()
                    if key
                    in {
                        "capability_id",
                        "operation",
                        "params_hash",
                        "pre_state_fingerprint",
                        "post_state_fingerprint",
                        "pre_evidence_fingerprint",
                        "post_evidence_fingerprint",
                        "material_progress",
                        "reported_state_or_evidence_delta",
                        "progress_detected",
                        "signature_hash",
                        "data_not_authority",
                        "can_execute",
                    }
                }
                for attempt in self._no_progress_attempts[-5:]
            ],
            "suppression_counts": dict(self._suppression_counts),
            "guard_rule": "normalized_action_plus_params_plus_state_plus_evidence_without_delta",
            "progress_definition": "state_fingerprint_delta_or_evidence_fingerprint_delta_or_typed_material_progress",
            "receipt_alone_counts_as_progress": False,
            "data_not_authority": True,
            "can_execute": False,
        }


def _operation_signature(decision: ActionEnvelope, context: dict[str, Any]) -> str:
    return stable_hash(
        {
            "capability_id": decision.capability_id,
            "operation": decision.operation,
            "params_hash": stable_hash(dict(decision.params)),
            "state_fingerprint": _state_fingerprint(context),
            "evidence_fingerprint": _evidence_fingerprint(context),
        }
    )


def _state_fingerprint(context: dict[str, Any]) -> str:
    operational = _operational_snapshot(context)
    if isinstance(operational, dict):
        fields = operational.get("fields")
        if isinstance(fields, dict):
            stable_fields = {
                key: _state_field_value(fields.get(key))
                for key in (
                    "current_url",
                    "page_title",
                    "page_type",
                    "session_lease_status",
                    "page_body_available",
                    "interactive_candidates",
                    "recoverable_error",
                    "provenance_and_freshness",
                )
                if isinstance(fields.get(key), dict)
            }
            if stable_fields:
                return stable_hash({"browser_progress_state_fields": stable_fields})
        value = str(operational.get("fingerprint") or "")
        if value:
            return value
    value = context.get("browser_environment_state_hash")
    if value:
        return str(value)
    return stable_hash({"state": "unknown"})


def _evidence_fingerprint(context: dict[str, Any]) -> str:
    operational = _operational_snapshot(context)
    fields = operational.get("fields") if isinstance(operational, dict) else None
    if isinstance(fields, dict):
        inventory = fields.get("public_evidence_inventory")
        if isinstance(inventory, dict):
            value = inventory.get("value")
            if isinstance(value, dict):
                refs = sanitize_operator_refs(tuple(str(ref) for ref in value.get("evidence_refs", []) if str(ref)))
                return stable_hash({"public_evidence_refs": refs, "count": value.get("count")})
    environment = context.get("browser_environment_state")
    if isinstance(environment, dict):
        snapshot = environment.get("operational_snapshot")
        if isinstance(snapshot, dict):
            nested_context = {"browser_cognitive_decision_frame": {"operational_snapshot": snapshot}}
            return _evidence_fingerprint(nested_context)
    return stable_hash({"evidence": "unknown"})


def _operational_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    frame = context.get("browser_cognitive_decision_frame")
    if isinstance(frame, dict):
        snapshot = frame.get("operational_snapshot")
        if isinstance(snapshot, dict):
            return snapshot
    skill_frame = context.get("skill_decision_frame")
    if isinstance(skill_frame, dict):
        frame = skill_frame.get("browser_cognitive_decision_frame")
        if isinstance(frame, dict):
            snapshot = frame.get("operational_snapshot")
            if isinstance(snapshot, dict):
                return snapshot
    return {}


def _state_field_value(field: Any) -> Any:
    if not isinstance(field, dict):
        return None
    return {
        "value": field.get("value"),
        "source": field.get("source"),
        "uncertainty_reason": field.get("uncertainty_reason"),
    }


def _recommended_control_step(count: int) -> str:
    if count <= 1:
        return "choose_alternate_affordance"
    if count == 2:
        return "observe_or_recover_session"
    return "declare_honest_blocker_with_attempt_history"


__all__ = ["BrowserProgressRepetitionGuard"]
