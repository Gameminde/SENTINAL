from __future__ import annotations

from typing import Any


BROWSER_COGNITIVE_AFFORDANCE_ORDER = (
    "observe",
    "navigate",
    "search",
    "follow",
    "inspect",
    "extract_evidence",
    "verify",
    "recover_session",
    "finish",
)


_AFFORDANCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "observe": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.observe",
        "typed_input_contract": {"params": {}, "model_semantic_data_allowed": True},
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "fresh BrowserEnvironmentState and stable candidate refs",
        },
        "receipt_kind": "real_browser_observation",
        "state_delta_contract": ("fresh_observation", "state_fingerprint"),
        "evidence_delta_contract": ("candidate_refs", "safe_page_summary"),
        "recoverable_failure_classes": ("session_degraded", "page_detached", "ordinary_timeout"),
    },
    "navigate": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.open",
        "typed_input_contract": {
            "params": {"target": "bounded mission origin or authority ref"},
            "raw_url_authority_grant": False,
        },
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "bounded origin state and page identity",
        },
        "receipt_kind": "real_browser_open",
        "state_delta_contract": ("origin_state", "page_identity"),
        "evidence_delta_contract": ("safe_origin_hash", "page_title_hash"),
        "recoverable_failure_classes": ("session_open_failed", "page_creation_failed"),
    },
    "search": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.search",
        "typed_input_contract": {
            "params": {"query": "inert model semantic data", "ref": "optional stable search ref"},
            "query_is_authority": False,
        },
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "typed search materiality and refreshed BrowserEnvironmentState",
        },
        "receipt_kind": "real_browser_action",
        "state_delta_contract": ("input_write", "submission_attempt", "request_or_result_delta"),
        "evidence_delta_contract": ("typed_search_outcome", "result_region_refs"),
        "recoverable_failure_classes": ("stale_ref", "hidden_control", "ordinary_timeout", "no_search_control"),
    },
    "follow": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.open_result",
        "typed_input_contract": {"params": {"ref": "stable link or result ref"}},
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "new page state or recoverable ref failure",
        },
        "receipt_kind": "real_browser_action",
        "state_delta_contract": ("navigation_or_page_state_delta",),
        "evidence_delta_contract": ("followed_ref_hash", "post_state_hash"),
        "recoverable_failure_classes": ("stale_ref", "link_unavailable", "navigation_uncertain"),
    },
    "inspect": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.inspect_result",
        "typed_input_contract": {"params": {"ref": "stable link, result or entity ref"}},
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "bounded details for selected result/entity",
        },
        "receipt_kind": "real_browser_action",
        "state_delta_contract": ("selected_candidate", "state_fingerprint"),
        "evidence_delta_contract": ("candidate_detail_refs",),
        "recoverable_failure_classes": ("stale_ref", "candidate_missing", "detail_unavailable"),
    },
    "extract_evidence": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.extract_evidence",
        "typed_input_contract": {
            "params": {"entity_kind": "optional model-proposed semantic kind", "scope": "current safe page"},
            "open_world_entity_kinds": True,
        },
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "open-world evidence/entity cards with confidence and unknowns",
        },
        "receipt_kind": "real_browser_action",
        "state_delta_contract": ("evidence_inventory_delta",),
        "evidence_delta_contract": ("entity_cards", "claim_support_refs", "unknowns"),
        "recoverable_failure_classes": ("empty_page", "unsupported_page_shape", "extraction_uncertain"),
    },
    "verify": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.verify_extraction",
        "typed_input_contract": {"params": {"evidence_refs": "optional extracted evidence refs"}},
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "verification status, contradictions and missing evidence",
        },
        "receipt_kind": "real_browser_action",
        "state_delta_contract": ("verified_state_delta",),
        "evidence_delta_contract": ("verified_refs", "contradictions", "unknowns"),
        "recoverable_failure_classes": ("missing_evidence_refs", "verification_incomplete"),
    },
    "recover_session": {
        "capability_id": "real_browser_control",
        "operation": "real_browser.recover_session",
        "typed_input_contract": {"params": {"failure_ref": "runtime failure fact ref"}},
        "normalized_result_contract": {
            "status": "completed | recoverable | blocked",
            "returns": "lease state transition and fresh observation when possible",
        },
        "receipt_kind": "real_browser_recovery",
        "state_delta_contract": ("lease_state_transition", "fresh_observation"),
        "evidence_delta_contract": ("recovery_receipt", "continuity_identity_hashes"),
        "recoverable_failure_classes": ("lease_degraded", "page_detached", "context_stale"),
    },
    "finish": {
        "capability_id": "sentinel_loop",
        "operation": "finish",
        "typed_input_contract": {
            "params": {"safe_summary": "grounded answer or truthful blocker summary"},
            "requires_proof_gate": True,
        },
        "normalized_result_contract": {
            "status": "completed | blocked",
            "returns": "FinalGate result and replay eligibility",
        },
        "receipt_kind": "product_task_loop_finalgate",
        "state_delta_contract": ("terminal_state",),
        "evidence_delta_contract": ("claim_evidence_matrix", "finalgate_certificate"),
        "recoverable_failure_classes": ("summary_missing", "proof_incomplete"),
    },
}


def compile_executable_browser_affordances(
    *,
    available_actions: tuple[str, ...],
    page_available: bool,
    body_available: bool,
    session_lease_status: str,
    action_graph: Any,
    extraction_graph: Any,
    recoverable_error: dict[str, Any] | None,
    mission_progress: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    allowed = set(str(action) for action in available_actions if str(action))
    return [
        _affordance(skill, reason=reason)
        for skill, reason in (
            ("observe", _observe_reason(allowed, page_available, session_lease_status)),
            ("navigate", _navigate_reason(allowed, session_lease_status)),
            ("search", _search_reason(allowed, body_available, action_graph)),
            ("follow", _follow_reason(allowed, body_available, action_graph)),
            ("inspect", _inspect_reason(allowed, body_available, action_graph, extraction_graph)),
            ("extract_evidence", _extract_reason(allowed, body_available)),
            ("verify", _verify_reason(allowed, extraction_graph)),
            ("recover_session", _recover_session_reason(allowed, recoverable_error)),
            ("finish", _finish_reason(allowed, mission_progress, recoverable_error)),
        )
        if reason
    ]


def browser_affordance_contract_catalog() -> tuple[dict[str, Any], ...]:
    return tuple(_affordance(skill, available_now=False, reason="catalog_contract_only") for skill in BROWSER_COGNITIVE_AFFORDANCE_ORDER)


def _affordance(skill: str, *, reason: str, available_now: bool = True) -> dict[str, Any]:
    definition = _AFFORDANCE_DEFINITIONS[skill]
    return {
        "skill": skill,
        "capability_id": definition["capability_id"],
        "operation": definition["operation"],
        "precondition_status": "satisfied" if available_now else "not_evaluated",
        "reason": reason,
        "typed_input_contract": definition["typed_input_contract"],
        "normalized_result_contract": definition["normalized_result_contract"],
        "receipt_kind": definition["receipt_kind"],
        "state_delta_contract": list(definition["state_delta_contract"]),
        "evidence_delta_contract": list(definition["evidence_delta_contract"]),
        "recoverable_failure_classes": list(definition["recoverable_failure_classes"]),
        "blocked_failure_classes": ["authority_boundary", "hard_effect_boundary", "proof_tampering"],
        "dispatch_contract": "ProductActionKernel",
        "model_strategy_role": "affordance_not_forced_trajectory",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def _observe_reason(allowed: set[str], page_available: bool, session_lease_status: str) -> str:
    if not _action_allowed(allowed, "real_browser.observe"):
        return ""
    if _safe_lease_status(session_lease_status) in {"BLOCKED", "CLOSED"}:
        return ""
    if not page_available:
        return ""
    return "page available for fresh observation"


def _navigate_reason(allowed: set[str], session_lease_status: str) -> str:
    if not _action_allowed(allowed, "real_browser.open"):
        return ""
    if _safe_lease_status(session_lease_status) == "BLOCKED":
        return ""
    return "bounded navigation/open authority is available"


def _search_reason(allowed: set[str], body_available: bool, action_graph: Any) -> str:
    if not _action_allowed(allowed, "real_browser.search") or not body_available:
        return ""
    search_refs = tuple(getattr(action_graph, "search_like_refs", ()) or ())
    if not search_refs:
        return ""
    return f"search-like control observed count={len(search_refs)}"


def _follow_reason(allowed: set[str], body_available: bool, action_graph: Any) -> str:
    if not _action_allowed(allowed, "real_browser.open_result") or not body_available:
        return ""
    link_refs = tuple(getattr(action_graph, "link_refs", ()) or ())
    if not link_refs:
        return ""
    return f"safe link/result refs observed count={len(link_refs)}"


def _inspect_reason(allowed: set[str], body_available: bool, action_graph: Any, extraction_graph: Any) -> str:
    if not _action_allowed(allowed, "real_browser.inspect_result") or not body_available:
        return ""
    link_refs = tuple(getattr(action_graph, "link_refs", ()) or ())
    candidate_count = int(getattr(extraction_graph, "product_or_result_candidate_count", 0) or 0)
    if not link_refs and candidate_count <= 0:
        return ""
    return "result, link or entity candidate is available for inspection"


def _extract_reason(allowed: set[str], body_available: bool) -> str:
    if not _action_allowed(allowed, "real_browser.extract_evidence") or not body_available:
        return ""
    return "page body or safe visible text is available"


def _verify_reason(allowed: set[str], extraction_graph: Any) -> str:
    if not _action_allowed(allowed, "real_browser.verify_extraction"):
        return ""
    candidate_count = int(getattr(extraction_graph, "product_or_result_candidate_count", 0) or 0)
    if candidate_count <= 0:
        return ""
    return f"candidate evidence exists count={candidate_count}"


def _recover_session_reason(allowed: set[str], recoverable_error: dict[str, Any] | None) -> str:
    if not _action_allowed(allowed, "real_browser.recover_session"):
        return ""
    if not isinstance(recoverable_error, dict) or not recoverable_error:
        return ""
    return "recoverable body error present and recovery action is registered"


def _finish_reason(
    allowed: set[str],
    mission_progress: dict[str, Any] | None,
    recoverable_error: dict[str, Any] | None,
) -> str:
    if not _action_allowed(allowed, "sentinel_loop.finish"):
        return ""
    if not isinstance(mission_progress, dict):
        return ""
    finish_eligible = _progress_truthy(mission_progress.get("finish_eligible"))
    honest_blocker = _progress_truthy(mission_progress.get("honest_blocker_present"))
    if honest_blocker and finish_eligible:
        return "honest terminal blocker is supported by evidence"
    if recoverable_error:
        return ""
    if (
        finish_eligible
        and _progress_truthy(mission_progress.get("objective_satisfied"))
        and _progress_truthy(mission_progress.get("verified_evidence_present"))
        and _progress_truthy(mission_progress.get("summary_present"))
    ):
        return "verified evidence and grounded summary satisfy the proof lane"
    return ""


def _action_allowed(allowed: set[str], operation: str) -> bool:
    return operation in allowed or f"real_browser_control.{operation}" in allowed or (
        operation == "sentinel_loop.finish" and "sentinel_loop.finish" in allowed
    )


def _safe_lease_status(value: str) -> str:
    rendered = str(value or "unknown").upper()
    if rendered in {"ACTIVE", "DEGRADED", "RECOVERING", "RECONNECTED", "BLOCKED", "CLOSED"}:
        return rendered
    return "unknown"


def _progress_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "satisfied", "present", "eligible"}
    return bool(value)


__all__ = [
    "BROWSER_COGNITIVE_AFFORDANCE_ORDER",
    "browser_affordance_contract_catalog",
    "compile_executable_browser_affordances",
]
