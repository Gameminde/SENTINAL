from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.decision_context import DecisionContextCompiler


def test_decision_context_exposes_latest_browser_environment_state() -> None:
    latest_state = _environment_state("search_results", stable_ref_count=4)

    context = _compile(
        [
            _browser_result(
                operation="real_browser.search",
                context_cards={
                    "browser_environment_state": latest_state,
                    "browser_environment_state_hash": stable_hash(latest_state),
                },
            )
        ]
    )

    assert context["browser_environment_state"] == latest_state
    assert context["browser_environment_state_hash"] == stable_hash(latest_state)
    assert context["browser_environment_memory"]["latest_state_hash"] == stable_hash(latest_state)
    assert context["browser_environment_memory"]["latest_page_kind_guess"] == "search_results"


def test_decision_context_tracks_environment_state_history_and_delta() -> None:
    previous_state = _environment_state("landing", stable_ref_count=1)
    latest_state = _environment_state("search_results", stable_ref_count=6)

    context = _compile(
        [
            _browser_result(
                operation="real_browser.open",
                context_cards={
                    "browser_environment_state": previous_state,
                    "browser_environment_state_hash": stable_hash(previous_state),
                },
            ),
            _browser_result(
                operation="real_browser.search",
                context_cards={
                    "browser_environment_state": latest_state,
                    "browser_environment_state_hash": stable_hash(latest_state),
                },
            ),
        ]
    )

    memory = context["browser_environment_memory"]

    assert memory["state_count"] == 2
    assert memory["previous_state_hash"] == stable_hash(previous_state)
    assert memory["latest_state_hash"] == stable_hash(latest_state)
    assert memory["state_changed"] is True
    assert memory["stable_ref_count_delta"] == 5


def test_recoverable_browser_state_is_visible_to_next_model_turn() -> None:
    state = _environment_state("search_results", stable_ref_count=3)

    context = _compile(
        [
            _browser_result(
                operation="real_browser.search",
                status="recoverable_failed",
                recoverable=True,
                failure_code="real_browser_search_actuation_failed",
                context_cards={
                    "browser_environment_state": state,
                    "browser_environment_state_hash": stable_hash(state),
                },
            )
        ]
    )

    memory = context["browser_environment_memory"]

    assert memory["latest_recoverable_state_hash"] == stable_hash(state)
    assert memory["latest_recoverable_failure_code"] == "real_browser_search_actuation_failed"
    assert memory["recommended_recovery_skills"] == ["extract", "browse_search"]


def test_browser_environment_memory_does_not_expose_raw_values() -> None:
    state = _environment_state("search_results", stable_ref_count=2)
    state["session_graph"]["cookies"] = [{"name_hash": stable_hash("x-session"), "value": "raw-cookie-value"}]
    state["session_graph"]["storage_keys"] = [{"key_hash": stable_hash("cart"), "value": "raw-storage-value"}]

    context = _compile(
        [
            _browser_result(
                operation="real_browser.extract_product_cards",
                context_cards={
                    "browser_environment_state": state,
                    "browser_environment_state_hash": stable_hash(state),
                },
            )
        ]
    )

    serialized = json.dumps(context["browser_environment_memory"], sort_keys=True)

    assert "raw-cookie-value" not in serialized
    assert "raw-storage-value" not in serialized
    assert context["browser_environment_memory"]["latest_cookie_count"] == 1
    assert context["browser_environment_memory"]["latest_storage_key_count"] == 1


def _compile(observations: list[ActionResult]) -> dict[str, object]:
    authority = MissionAuthorityEnvelope(
        user_id="user_youcef",
        mission_title="Browser Cortex Pack 3",
        mission_objective="Search a bounded product page for glasses under 5 EUR and extract relevant product cards.",
        allowed_tools=["real_browser_control"],
        allowed_actions=[
            "real_browser.open",
            "real_browser.search",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
            "finish",
        ],
        forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
        allowed_domains=["real_browser:bounded_test_url"],
        max_actions=8,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    return DecisionContextCompiler().compile(
        mission_id="mission_browser_cortex_pack3",
        mission_objective=authority.mission_objective,
        authority=authority,
        observations=observations,
        available_actions=(
            "real_browser_control.real_browser.open",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "sentinel_loop.finish",
        ),
        model_calls_used=1,
        material_actions_used=1,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=0,
        max_recovery_turns=2,
    )


def _browser_result(
    *,
    operation: str,
    context_cards: dict[str, object],
    status: str = "completed",
    recoverable: bool = False,
    failure_code: str = "",
) -> ActionResult:
    return ActionResult(
        action_id=f"act_{operation}",
        capability_id="real_browser_control",
        operation=operation,
        status=status,
        receipt_refs=("receipt_1",) if not recoverable else (),
        material_action=operation in {"real_browser.search", "real_browser.extract_product_cards"},
        failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE if recoverable else None,
        failure_code=failure_code,
        recoverable=recoverable,
        observation_summary=f"{operation} {status}",
        result_hash=stable_hash({"operation": operation, "status": status}),
        context_cards=context_cards,
    )


def _environment_state(page_kind: str, *, stable_ref_count: int) -> dict[str, object]:
    return {
        "state_id": f"browser_env_state_{page_kind}_{stable_ref_count}",
        "backend_truth": {
            "selected_backend_id": "cloak_browser",
            "actual_backend_id": "cloak_browser",
            "session_backend_kind": "cloakbrowser",
            "product_backend_proven": True,
        },
        "page_state": {
            "page_state_hash": stable_hash({"page_kind": page_kind, "stable_ref_count": stable_ref_count}),
            "origin_hash": stable_hash("https://bounded.example"),
            "page_kind_guess": page_kind,
            "title_hash_or_safe_title": "Bounded Product Page",
            "visible_text_summary_hash": stable_hash(page_kind),
            "stable_ref_count": stable_ref_count,
        },
        "action_graph": {
            "search_like_refs": ["input:search"] if stable_ref_count else [],
            "link_refs": ["link:result_1"],
            "recommended_browser_actions": ["real_browser.extract_product_cards"],
        },
        "extraction_graph": {
            "product_or_result_candidate_count": 1,
            "relevant_product_candidate_count": 1,
        },
        "protocol_graph": {"network_event_count": 0, "console_event_count": 0},
        "session_graph": {"cookie_count": 0, "storage_key_count": 0, "cookies": [], "storage_keys": []},
        "blocker_graph": {"hard_boundary_signals": []},
        "visual_graph": {"visual_refs_available": False},
        "recommended_model_skills": ["extract", "browse_search"],
        "raw_material_persisted": False,
        "can_execute": False,
    }
