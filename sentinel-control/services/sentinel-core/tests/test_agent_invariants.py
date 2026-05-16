from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.agent import AgentState, CapabilityNeed, InvariantChecker, InvariantViolation, LearningProposal
from sentinel.agent.phases import AgentPhase
from sentinel.mission import MissionAction, MissionAuthorityEnvelope
from sentinel.shared.enums import ConfidenceLevel, ExternalityLevel, MissionMode, MissionType, ReversibilityLevel, SensitivityLevel


SAFE_ACTIONS = ["create_project_folder", "generate_gtm_pack"]


def envelope(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Agent core test",
        "mission_objective": "Test agent core.",
        "mode": MissionMode.SAFE,
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["run_shell_command"],
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def action(env: MissionAuthorityEnvelope, action_type: str = "create_project_folder", tool: str = "safe_file_writer") -> MissionAction:
    return MissionAction(
        mission_id=env.id,
        action_type=action_type,
        tool=tool,
        intent="test",
        expected_output="done",
        reversibility=ReversibilityLevel.LOCAL_WRITE_REVERSIBLE,
        externality=ExternalityLevel.INTERNAL_LOCAL,
        sensitivity=SensitivityLevel.INTERNAL,
        confidence=ConfidenceLevel.HIGH,
    )


def test_check_authority_decision_documented():
    """Task 10 / F-A3.1 — the removal of ``check_authority`` as live
    safety code is recorded in ``CURRENT_STATE_LOCK.md``. This test
    locks the doctrine that a future refactor must not silently
    reintroduce the method as a live check without updating the
    canonical-chokepoint documentation.
    """
    lock_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "docs"
        / "CURRENT_STATE_LOCK.md"
    )
    assert lock_path.is_file(), f"CURRENT_STATE_LOCK.md not found at {lock_path}"
    content = lock_path.read_text(encoding="utf-8")
    assert "Task 10" in content or "F-A3.1" in content, (
        "CURRENT_STATE_LOCK.md is missing the Task 10 / F-A3.1 decision record."
    )
    assert "check_authority" in content, (
        "CURRENT_STATE_LOCK.md must reference check_authority in the "
        "removal rationale so readers can find it by grep."
    )


def test_no_dead_safety_code_in_invariants():
    """``InvariantChecker.check_authority`` MUST NOT be callable as a
    silent no-op or duplicate of the router check. It has been
    converted to an error stub that fails loudly and directs readers
    to the canonical chokepoints. This test locks that contract —
    removing the stub entirely is fine if every caller is migrated,
    but ``check_authority`` must not exist as live duplicative code.
    """
    checker = InvariantChecker()
    env = envelope()
    act = action(env)

    # The method still exists as a name (for error-directed migration),
    # but calling it MUST raise. A silent/duplicate implementation
    # would be a regression.
    with pytest.raises(NotImplementedError) as excinfo:
        checker.check_authority(env, act)
    message = str(excinfo.value)
    # The error message directs the reader to the canonical enforcers.
    assert "RiskRouter" in message or "MissionScopeChecker" in message
    assert "OrganAuthorityEvaluator" in message


def test_check_authority_method_removed_and_no_production_call_sites_exist():
    """AST-walk all production ``sentinel/`` source and confirm no
    module calls ``InvariantChecker.check_authority`` or any alias
    of it. Tests may still reference the method name to verify the
    error-stub behavior."""
    import ast

    sentinel_root = Path(__file__).resolve().parent.parent / "sentinel"
    assert sentinel_root.is_dir(), f"Expected sentinel/ at {sentinel_root}."

    production_call_sites: list[tuple[str, int]] = []
    for path in sentinel_root.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — defensive
            continue
        # Skip the definition site itself.
        if path.name == "invariants.py":
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "check_authority":
                production_call_sites.append((str(path), node.lineno))
            elif isinstance(node, ast.Name) and node.id == "check_authority":
                production_call_sites.append((str(path), node.lineno))

    assert production_call_sites == [], (
        "Production code must not reference check_authority. Offenders: "
        + repr(production_call_sites)
    )


def test_router_enforces_action_in_authority_as_canonical_chokepoint():
    """Belt-and-braces: confirm the canonical chokepoint
    (:meth:`RiskRouter.route`) actually rejects out-of-scope actions.
    If this test ever fails, removing ``check_authority`` would be a
    regression because the canonical replacement would be broken.
    """
    from sentinel.mission.autonomy import AutonomyEngine
    from sentinel.mission.models import MissionState
    from sentinel.shared.enums import MissionActionRoute, MissionStatus

    env = envelope()
    # An out-of-scope action ("run_shell_command" is in
    # env.forbidden_actions AND in BLACK_ZONE_ACTIONS).
    forbidden_action = action(env, "run_shell_command", "shell")
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)

    engine = AutonomyEngine()
    decision = engine.decide(env, state, forbidden_action)

    # The router routes forbidden/black-zone actions to BLOCK with a
    # 100.0 risk score. That is the canonical enforcement Task 10
    # defers to.
    assert decision.route == MissionActionRoute.BLOCK
    assert decision.risk_score == 100.0


def test_memory_context_cannot_expand_authority():
    env = envelope()

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_memory_not_authority(env, ["create_project_folder", "send_email"])


def test_context_capabilities_must_derive_from_allowed_actions():
    env = envelope()

    InvariantChecker().check_capabilities_derive_from_authority(
        env,
        ["local_workspace_write", "gtm_pack_generation"],
    )

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_capabilities_derive_from_authority(
            env,
            ["local_workspace_write", "browser_research"],
        )


def test_missing_capability_must_explain_absence():
    need = CapabilityNeed(name="browser_research", reason="future", available=False)

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_capability_declarations([need])


def test_learning_proposal_must_require_human_approval():
    proposal = LearningProposal(
        observed_failure="test",
        proposed_change="unsafe auto change",
        requires_human_approval=False,
    )

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_learning_proposals([proposal])


def test_bounded_repair_invariant_blocks_overrun():
    state = AgentState(mission_id="mission_001", repair_cycles=2, max_repair_cycles=1)

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_bounded_repair(state)


def test_completion_invariant_requires_successful_mission_result():
    state = AgentState(mission_id="mission_001", phase=AgentPhase.COMPLETED)

    with pytest.raises(InvariantViolation):
        InvariantChecker().check_completion(state, None)
