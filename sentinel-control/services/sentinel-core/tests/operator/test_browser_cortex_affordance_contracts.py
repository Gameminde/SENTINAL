from __future__ import annotations

from sentinel.operator.browser_affordance_contracts import (
    BROWSER_COGNITIVE_AFFORDANCE_ORDER,
    compile_executable_browser_affordances,
)
from sentinel.operator.browser_environment_state import BrowserActionGraph, BrowserExtractionGraph


def test_browser_affordance_contracts_are_distinct_product_kernel_routes() -> None:
    affordances = compile_executable_browser_affordances(
        available_actions=(
            "real_browser_control.real_browser.open",
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.extract_evidence",
            "real_browser_control.real_browser.verify_extraction",
            "sentinel_loop.finish",
        ),
        page_available=True,
        body_available=True,
        session_lease_status="ACTIVE",
        action_graph=BrowserActionGraph(search_like_refs=("search:box",), link_refs=("link:docs",)),
        extraction_graph=BrowserExtractionGraph(product_or_result_candidate_count=1),
        recoverable_error=None,
        mission_progress={
            "objective_satisfied": True,
            "verified_evidence_present": True,
            "summary_present": True,
            "finish_eligible": True,
        },
    )

    by_skill = {item["skill"]: item for item in affordances}

    assert [item["skill"] for item in affordances] == [
        skill for skill in BROWSER_COGNITIVE_AFFORDANCE_ORDER if skill != "recover_session"
    ]
    assert by_skill["navigate"]["operation"] == "real_browser.open"
    assert by_skill["follow"]["operation"] == "real_browser.open_result"
    assert by_skill["extract_evidence"]["operation"] == "real_browser.extract_evidence"
    for item in affordances:
        assert item["dispatch_contract"] == "ProductActionKernel"
        assert item["model_strategy_role"] == "affordance_not_forced_trajectory"
        assert item["typed_input_contract"]
        assert item["normalized_result_contract"]
        assert item["receipt_kind"]
        assert item["state_delta_contract"]
        assert item["evidence_delta_contract"]


def test_browser_affordance_contracts_hide_non_executable_actions() -> None:
    affordances = compile_executable_browser_affordances(
        available_actions=(
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_evidence",
        ),
        page_available=True,
        body_available=True,
        session_lease_status="ACTIVE",
        action_graph=BrowserActionGraph(link_refs=("link:docs",)),
        extraction_graph=BrowserExtractionGraph(product_or_result_candidate_count=0),
        recoverable_error=None,
        mission_progress=None,
    )

    skills = [item["skill"] for item in affordances]

    assert "observe" in skills
    assert "follow" in skills
    assert "extract_evidence" in skills
    assert "search" not in skills
    assert "verify" not in skills
    assert "finish" not in skills


def test_recover_session_contract_requires_real_available_action() -> None:
    without_runtime_action = compile_executable_browser_affordances(
        available_actions=("real_browser_control.real_browser.observe",),
        page_available=True,
        body_available=True,
        session_lease_status="DEGRADED",
        action_graph=BrowserActionGraph(),
        extraction_graph=BrowserExtractionGraph(),
        recoverable_error={"failure_code": "BODY_SESSION_UNAVAILABLE"},
        mission_progress=None,
    )
    with_runtime_action = compile_executable_browser_affordances(
        available_actions=("real_browser_control.real_browser.recover_session",),
        page_available=True,
        body_available=True,
        session_lease_status="DEGRADED",
        action_graph=BrowserActionGraph(),
        extraction_graph=BrowserExtractionGraph(),
        recoverable_error={"failure_code": "BODY_SESSION_UNAVAILABLE"},
        mission_progress=None,
    )

    assert "recover_session" not in [item["skill"] for item in without_runtime_action]
    assert "recover_session" in [item["skill"] for item in with_runtime_action]


def test_finish_affordance_contract_requires_proof_lane_eligibility() -> None:
    not_ready = compile_executable_browser_affordances(
        available_actions=("sentinel_loop.finish",),
        page_available=True,
        body_available=True,
        session_lease_status="ACTIVE",
        action_graph=BrowserActionGraph(),
        extraction_graph=BrowserExtractionGraph(product_or_result_candidate_count=2),
        recoverable_error=None,
        mission_progress={"verified_evidence_present": True},
    )
    ready = compile_executable_browser_affordances(
        available_actions=("sentinel_loop.finish",),
        page_available=True,
        body_available=True,
        session_lease_status="ACTIVE",
        action_graph=BrowserActionGraph(),
        extraction_graph=BrowserExtractionGraph(product_or_result_candidate_count=2),
        recoverable_error=None,
        mission_progress={
            "objective_satisfied": True,
            "verified_evidence_present": True,
            "summary_present": True,
            "finish_eligible": True,
        },
    )

    assert "finish" not in [item["skill"] for item in not_ready]
    assert "finish" in [item["skill"] for item in ready]
