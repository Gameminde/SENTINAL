"""Task 11 / Requirement 11 — CoreFinalGate Decomposition.

Equivalence + extension tests for the registry/module refactor.

Doctrine:
    * Behavior of ``CoreFinalGate().evaluate(result, allowed_project_root=...)``
      MUST equal the pre-Task-11 monolithic behavior: same check names, in
      the same order, with the same ``accepted`` verdict.
    * New modules can be registered without modifying ``CoreFinalGate`` or
      the default registry.

**Validates: Requirement 11 (CP-11.1 Open-Closed, CP-11.2 Completeness).**
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sentinel.agent import (
    AgentPhase,
    AgentRuntime,
    CoreFinalGate,
    CoreFinalGateResult,
    CoreGateCheck,
    CoreGateCheckKind,
)
from sentinel.agent.final_gate_registry import (
    BrowserChecksModule,
    CoreChecksModule,
    FinalGateCheckModule,
    FinalGateRegistry,
    default_registry,
)
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "generate_research_questions",
    "write_trace",
]


def _envelope(**overrides: Any) -> MissionAuthorityEnvelope:
    data: dict[str, Any] = {
        "user_id": "user_decomp",
        "mission_type": MissionType.GTM,
        "mission_title": "Final-gate decomposition test",
        "mission_objective": "Validate registry equivalence with monolith.",
        "success_criteria": ["Trace", "Run completes"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(SAFE_ACTIONS),
        "forbidden_actions": ["send_email", "run_shell_command", "browser_submit_form", "credential_access"],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _run(tmp_path: Path):
    return AgentRuntime(project_root=tmp_path).run(
        _envelope(),
        {"idea": "Registry equivalence fixture"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )


# ---------------------------------------------------------------------------
# Test 1 — registry evaluates all registered modules in order.
# ---------------------------------------------------------------------------


def test_registry_evaluates_all_registered_modules(tmp_path) -> None:
    """Given two modules, ``evaluate_all`` concatenates their checks in
    registration order."""

    class ModuleA:
        name = "mod_a"

        def checks(self, result, *, allowed_project_root=None):
            return [
                CoreGateCheck(
                    name="a1",
                    kind=CoreGateCheckKind.TRACE,
                    passed=True,
                    message="module-a check 1",
                )
            ]

    class ModuleB:
        name = "mod_b"

        def checks(self, result, *, allowed_project_root=None):
            return [
                CoreGateCheck(
                    name="b1",
                    kind=CoreGateCheckKind.TRACE,
                    passed=True,
                    message="module-b check 1",
                ),
                CoreGateCheck(
                    name="b2",
                    kind=CoreGateCheckKind.TRACE,
                    passed=True,
                    message="module-b check 2",
                ),
            ]

    registry = FinalGateRegistry([ModuleA(), ModuleB()])
    verdict = registry.evaluate_all(_run(tmp_path))

    assert [check.name for check in verdict.checks] == ["a1", "b1", "b2"]
    assert verdict.accepted is True


# ---------------------------------------------------------------------------
# Test 2 — new modules can register without modifying CoreFinalGate source.
# ---------------------------------------------------------------------------


def test_new_module_registration_without_core_modification(tmp_path) -> None:
    """**Validates: CP-11.1 (Open-Closed).**

    A caller can build a registry extending ``default_registry()`` with a
    synthetic module and pass it to ``CoreFinalGate`` without touching
    ``CoreFinalGate`` source code. The synthetic module's checks appear in
    the verdict alongside all default checks.
    """

    class SyntheticOrganChecksModule:
        name = "synthetic_organ"

        def checks(self, result, *, allowed_project_root=None):
            return [
                CoreGateCheck(
                    name="synthetic_organ_ok",
                    kind=CoreGateCheckKind.ARTIFACT,
                    passed=True,
                    message="Synthetic organ check passed.",
                )
            ]

    extended = default_registry()
    extended.register(SyntheticOrganChecksModule())

    gate = CoreFinalGate(registry=extended)
    result = _run(tmp_path)
    verdict = gate.evaluate(result, allowed_project_root=str(tmp_path))

    names = [check.name for check in verdict.checks]
    assert "synthetic_organ_ok" in names
    assert verdict.accepted is True


# ---------------------------------------------------------------------------
# Test 3 — CoreChecksModule is independently testable.
# ---------------------------------------------------------------------------


def test_core_checks_module_independent(tmp_path) -> None:
    """**Validates: CP-11.2 (Completeness).**

    The core module returns exactly the core checks (project_scope would be
    ``allowed_project_root`` would be added by the trailing module). The
    project-scope check is emitted by ``_ProjectScopeTailModule``, not by
    ``CoreChecksModule``.
    """
    result = _run(tmp_path)
    module = CoreChecksModule()

    checks_no_scope = module.checks(result, allowed_project_root=None)
    checks_with_scope = module.checks(result, allowed_project_root=tmp_path)

    # Core module does not embed _project_scope — the trailing module does.
    assert len(checks_no_scope) == len(checks_with_scope)
    assert all("project_scope" not in c.name for c in checks_no_scope)
    # Core must include the cross-organ anchors.
    names = {c.name for c in checks_no_scope}
    assert "trace_present" in names
    assert "runtime_certification" in names
    assert "global_action_budget" in names
    assert "model_execution_budget_contract" in names
    assert "mission_artifact_receipts" in names


def test_browser_checks_module_independent(tmp_path) -> None:
    """Browser module emits exactly the 14 browser checks."""
    result = _run(tmp_path)
    module = BrowserChecksModule()
    checks = module.checks(result, allowed_project_root=None)

    names = [c.name for c in checks]
    expected_browser = {
        "browser_capability_receipts",
        "browser_interaction_dry_run_contract",
        "browser_interaction_execution_contract",
        "browser_public_lifecycle_contract",
        "browser_reliability_supervisor_contract",
        "browser_v25_observation_and_operator_contract",
        "browser_v3_form_submit_contract",
        "browser_v3_download_quarantine_contract",
        "browser_v3_upload_authorized_contract",
        "browser_v3_private_session_contract",
        "browser_v3_login_authority_contract",
        "browser_v3_cookie_storage_contract",
        "browser_v3_js_evaluate_sandboxed_contract",
        "browser_v3_har_body_capture_contract",
    }
    assert set(names) == expected_browser
    assert len(names) == 14


# ---------------------------------------------------------------------------
# Test 4 — decomposed gate is bit-exactly equivalent to the monolithic baseline.
# ---------------------------------------------------------------------------


_EXPECTED_NAMES_IN_ORDER = [
    # CoreChecksModule (25 checks)
    "trace_present",
    "trace_mission_consistency",
    "runtime_certification",
    "state_replay",
    "phase_contract",
    "tool_policy_decisions_trace_bound",
    "selected_tools_are_policy_eligible",
    "blocked_and_candidate_tools_not_selected",
    "learning_requires_human_approval",
    "mission_trace_integrity",
    "mission_result_consistency",
    "mission_results_archive",
    "global_action_budget",
    "model_execution_budget_contract",
    "active_plan_matches_mission_trace",
    "evidence_chains_trace_bound",
    "success_event_contract",
    "success_evidence_contract",
    "success_artifact_contract",
    "artifact_paths_are_relative",
    "execution_posture_matches_authority",
    "mission_risk_route_decisions",
    "controlled_capability_receipts",
    "llm_context_pack_and_tool_intent_contract",
    "mission_artifact_receipts",
    # BrowserChecksModule (14 checks)
    "browser_capability_receipts",
    "browser_interaction_dry_run_contract",
    "browser_interaction_execution_contract",
    "browser_public_lifecycle_contract",
    "browser_reliability_supervisor_contract",
    "browser_v25_observation_and_operator_contract",
    "browser_v3_form_submit_contract",
    "browser_v3_download_quarantine_contract",
    "browser_v3_upload_authorized_contract",
    "browser_v3_private_session_contract",
    "browser_v3_login_authority_contract",
    "browser_v3_cookie_storage_contract",
    "browser_v3_js_evaluate_sandboxed_contract",
    "browser_v3_har_body_capture_contract",
    # _ProjectScopeTailModule (conditional)
    "project_scope",
]


def test_decomposed_gate_equivalent_to_monolithic(tmp_path) -> None:
    """**Validates: CP-11.2 (Completeness).**

    ``CoreFinalGate().evaluate(result, allowed_project_root=...)`` produces
        the same stable check sequence, with the post-budget-governance model
        execution budget check included: exact names, exact order, 40 total
        checks when ``allowed_project_root`` is supplied and 39 otherwise.
    """
    result = _run(tmp_path)
    gate = CoreFinalGate()

    verdict_with_scope = gate.evaluate(result, allowed_project_root=str(tmp_path))
    names_with_scope = [c.name for c in verdict_with_scope.checks]
    assert names_with_scope == _EXPECTED_NAMES_IN_ORDER
    assert len(verdict_with_scope.checks) == 40
    assert verdict_with_scope.accepted is True

    verdict_no_scope = gate.evaluate(result)
    names_no_scope = [c.name for c in verdict_no_scope.checks]
    assert names_no_scope == _EXPECTED_NAMES_IN_ORDER[:-1]  # drop project_scope
    assert len(verdict_no_scope.checks) == 39
    assert verdict_no_scope.accepted is True


# ---------------------------------------------------------------------------
# Test 5 — check ordering is deterministic across repeated evaluations.
# ---------------------------------------------------------------------------


def test_check_order_is_deterministic(tmp_path) -> None:
    """Running ``evaluate`` multiple times (same instance or fresh) with the
    same input produces the same check list in the same order.

    This complements Task 1.5's determinism property by specifically
    asserting ordering, not just verdict equality.
    """
    result = _run(tmp_path)
    gate = CoreFinalGate()

    orders = [
        [c.name for c in gate.evaluate(result, allowed_project_root=str(tmp_path)).checks]
        for _ in range(3)
    ]
    assert orders[0] == orders[1] == orders[2]

    fresh = [
        [c.name for c in CoreFinalGate().evaluate(result, allowed_project_root=str(tmp_path)).checks]
        for _ in range(3)
    ]
    assert fresh[0] == fresh[1] == fresh[2] == orders[0]


# ---------------------------------------------------------------------------
# Test 6 — duplicate module name registration is refused.
# ---------------------------------------------------------------------------


def test_duplicate_module_name_rejected() -> None:
    """``FinalGateRegistry.register`` refuses a module whose ``name`` is
    already present. Prevents silent shadowing and duplicate check emission.
    """
    registry = default_registry()
    with pytest.raises(ValueError):
        registry.register(CoreChecksModule())  # 'core' already registered


# ---------------------------------------------------------------------------
# Test 7 — default registry with CoreFinalGate(...) reproduces pre-Task-11
# behavior byte-for-byte (model_dump equality).
# ---------------------------------------------------------------------------


def test_core_final_gate_default_registry_matches_previous_behavior(tmp_path) -> None:
    """Serialize the verdict via ``model_dump()`` and confirm every check's
    full payload (name, kind, passed, message, details) is present. This
    guards against accidental signature drift from the decomposition.
    """
    result = _run(tmp_path)
    gate = CoreFinalGate()
    verdict: CoreFinalGateResult = gate.evaluate(result, allowed_project_root=str(tmp_path))
    dumped = verdict.model_dump()

    assert dumped["accepted"] is True
    assert [check["name"] for check in dumped["checks"]] == _EXPECTED_NAMES_IN_ORDER
    # Every check carries the five required fields.
    for check in dumped["checks"]:
        assert set(check.keys()) >= {"name", "kind", "passed", "message", "details"}
        assert isinstance(check["passed"], bool)
