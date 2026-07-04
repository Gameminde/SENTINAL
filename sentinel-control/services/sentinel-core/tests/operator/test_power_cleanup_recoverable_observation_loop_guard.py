from __future__ import annotations

import pytest

from sentinel.operator.action_kernel import ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig, LoopGuardError


def test_recoverable_observation_with_next_actions_counts_as_productive_recovery() -> None:
    guard = LoopGuard(LoopGuardConfig(max_no_progress_turns=0))

    guard.record_result(
        ActionResult(
            action_id="action_recoverable",
            capability_id="real_browser_control",
            operation="real_browser.search",
            status="recoverable_failed",
            material_action=False,
            recoverable=True,
            failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
            failure_code="real_browser_search_actuation_failed",
            recommended_next_actions=(
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
            ),
            recovery_observation={
                "safe_summary": "Search failed, but product cards are visible.",
                "refreshed_candidate_refs": ["card:0"],
            },
            observation_summary="recoverable browser miss with a live extraction lane.",
        )
    )

    assert guard.no_progress_turns == 0


def test_recoverable_observation_without_recovery_lane_still_counts_as_no_progress() -> None:
    guard = LoopGuard(LoopGuardConfig(max_no_progress_turns=0))

    with pytest.raises(LoopGuardError, match="loop_guard_no_progress"):
        guard.record_result(
            ActionResult(
                action_id="action_empty_recovery",
                capability_id="real_browser_control",
                operation="real_browser.search",
                status="recoverable_failed",
                material_action=False,
                recoverable=True,
                failure_class=ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE,
                failure_code="real_browser_search_actuation_failed",
                observation_summary="recoverable miss without a next action.",
            )
        )
