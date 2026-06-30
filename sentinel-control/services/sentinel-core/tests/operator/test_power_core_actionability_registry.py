from __future__ import annotations

from sentinel.operator.actionability_registry import (
    ActionExposureStatus,
    build_default_actionability_registry,
)
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.mission.models import MissionAuthorityEnvelope


def test_registry_exposes_only_runtime_available_model_facing_actions() -> None:
    registry = build_default_actionability_registry()

    frame = registry.compile_frame(
        available_actions=(
            "read_only.list_directory",
            "workspace_patch.apply_patch",
            "code_exec.run_profile",
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.search",
            "bounded_channel.send_message",
        ),
        granted_capabilities=(
            "read_only_research",
            "workspace_patch",
            "code_execution_sandbox",
            "real_browser_control",
            "bounded_channel",
        ),
    )

    visible_actions = {item.action_name for item in frame.model_visible_actions}
    hidden_actions = {item.action_name for item in frame.hidden_internal_actions}

    assert "read_only_research.list_directory" in visible_actions
    assert "workspace_patch.apply_patch" in visible_actions
    assert "code_execution_sandbox.code_exec.run_profile" in visible_actions
    assert "bounded_channel.send_message" in visible_actions
    assert "real_browser_control.real_browser.search" in visible_actions
    assert "real_browser_control.real_browser.type_text" not in visible_actions
    assert "real_browser_control.real_browser.type_text" in hidden_actions
    assert all(item.status is ActionExposureStatus.EXECUTABLE for item in frame.model_visible_actions)


def test_registry_normalizes_aliases_to_canonical_skills() -> None:
    registry = build_default_actionability_registry()

    assert registry.normalize_action_name("read_only.search_text") == "read_only_research.search_text"
    assert registry.normalize_action_name("code_exec.run_profile") == "code_execution_sandbox.code_exec.run_profile"
    assert registry.normalize_action_name("channel_transport.send_message") == "bounded_channel.send_message"
    assert registry.normalize_action_name("real_browser.type_text") == "real_browser_control.real_browser.type_text"


def test_registry_keeps_high_risk_surfaces_locked_and_non_visible() -> None:
    registry = build_default_actionability_registry()

    frame = registry.compile_frame(
        available_actions=(
            "external_api.call",
            "desktop.click",
            "payment.submit",
            "account_authority.grant",
        ),
        granted_capabilities=(
            "external_api",
            "desktop_control",
            "payment_authority",
            "account_authority",
        ),
    )

    assert frame.model_visible_actions == ()
    locked_skill_ids = {skill.skill_id for skill in frame.locked_skills}
    assert {"external_api", "desktop_control", "payment_authority", "account_authority"} <= locked_skill_ids
    assert all(skill.status is ActionExposureStatus.LOCKED for skill in frame.locked_skills)
    assert all(skill.hard_stop_boundaries for skill in frame.locked_skills)


def test_decision_context_carries_global_skill_exposure_frame() -> None:
    authority = MissionAuthorityEnvelope(
        user_id="user_skill_frame",
        mission_title="Skill frame mission",
        mission_objective="Patch and verify the fixture.",
        allowed_actions=(
            "read_only_research.list_directory",
            "workspace_patch.apply_patch",
            "code_execution_sandbox.code_exec.run_profile",
            "real_browser_control.real_browser.search",
        ),
        allowed_tools=(),
        allowed_domains=(),
        allowed_paths=("workspace:fixture",),
        max_actions=5,
        max_recipients=0,
    )

    context = DecisionContextCompiler().compile(
        mission_id="mission_skill_frame",
        mission_objective="Patch and verify the fixture.",
        authority=authority,
        observations=[],
        available_actions=(
            "read_only.list_directory",
            "workspace_patch.apply_patch",
            "code_exec.run_profile",
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.search",
        ),
        model_calls_used=0,
        material_actions_used=0,
        max_model_calls=5,
        max_material_actions=5,
    )

    frame = context["skill_exposure_frame"]
    visible = {item["action_name"] for item in frame["model_visible_actions"]}
    hidden = {item["action_name"] for item in frame["hidden_internal_actions"]}

    assert "read_only_research.list_directory" in visible
    assert "workspace_patch.apply_patch" in visible
    assert "code_execution_sandbox.code_exec.run_profile" in visible
    assert "real_browser_control.real_browser.search" in visible
    assert "real_browser_control.real_browser.type_text" in hidden
    assert context["model_visible_recommended_next_action"] in visible | {"sentinel_loop.finish", None}
    assert context["recommended_next_action"] == "real_browser_control.real_browser.open"
