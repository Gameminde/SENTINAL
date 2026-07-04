from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.model_led_product_action_kernel_task_loop import ProductActionKernelLoopDecisionClient
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_decision_context_primary_model_surface_uses_simple_skills() -> None:
    context = _compile(
        available_actions=(
            "read_only_research.search_text",
            "workspace_patch.apply_patch",
            "workspace_patch.run_bounded_check",
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "sentinel_loop.finish",
        )
    )

    surface = context["model_skill_surface"]

    assert context["primary_model_surface"] == "model_visible_skills"
    assert surface["primary_model_language"] == "simple_mission_skills"
    assert surface["action_envelope_language"] == "internal_runtime_only"
    assert context["model_visible_skills"] == ["read", "patch", "run_check", "send_message", "finish"]
    assert context["primary_model_recommended_next_skill"] in {"patch", "run_check", "send_message"}
    assert "." not in context["primary_model_recommended_next_skill"]
    assert all("." not in skill for skill in context["model_visible_skills"])
    assert "workspace_patch.apply_patch" not in context["model_visible_skills"]
    assert context["runtime_internal_action_map"]["patch"] == "workspace_patch.apply_patch"


def test_browser_skill_surface_prefers_search_and_extract_not_raw_primitives() -> None:
    context = _compile(
        available_actions=(
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.select_option",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "sentinel_loop.finish",
        )
    )

    surface = context["model_skill_surface"]

    assert "browse_search" in surface["model_visible_skills"]
    assert "extract" in surface["model_visible_skills"]
    assert "type_text" not in surface["model_visible_skills"]
    assert "click" not in surface["model_visible_skills"]
    assert surface["recommended_next_skills"][0] in {"browse_search", "extract"}
    assert not any(skill.startswith("real_browser") for skill in surface["model_visible_skills"])


def test_runtimehost_entrypoint_exposes_simple_skills_as_primary_surface(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    frame = host.product_task_loop_entrypoint_frame()

    assert frame["primary_model_surface"] == "model_visible_skills"
    assert frame["primary_model_language"] == "simple_mission_skills"
    assert frame["model_visible_skills"] == ["patch", "run_check", "send_message", "finish"]
    assert frame["action_envelope_language"] == "internal_runtime_only"
    assert frame["runtime_internal_action_map"]["send_message"] == "bounded_channel.send_message"
    assert frame["model_visible_available_actions"] == [
        "workspace_patch.apply_patch",
        "code_execution_sandbox.code_exec.run_profile",
        "bounded_channel.send_message",
        "sentinel_loop.finish",
    ]


def test_product_task_loop_context_keeps_action_envelope_internal(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Pack 2\n", encoding="utf-8")
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Finished after one product receipt."},
            ),
        ]
    )

    host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack2_skill_surface",
        mission_objective="Run one internal ActionEnvelope while exposing simple skills to the model.",
        decision_client=client,
        max_model_calls=3,
        max_material_actions=1,
    )

    first_context = client.contexts[0]

    assert first_context["primary_model_surface"] == "model_visible_skills"
    assert first_context["model_visible_skills"] == ["patch", "run_check", "send_message"]
    assert "code_execution_sandbox.code_exec.run_profile" not in first_context["model_visible_skills"]
    assert first_context["skill_decision_frame"]["model_skill_surface"]["recommended_next_skills"][0] == "patch"
    assert first_context["runtime_internal_action_map"]["run_check"] == "code_execution_sandbox.code_exec.run_profile"


def test_high_risk_or_unknown_actions_are_not_simple_model_skills() -> None:
    context = _compile(
        available_actions=(
            "payment_authority.spend",
            "credential_vault.read_secret",
            "external_channel.contact_supplier",
            "sentinel_loop.finish",
        )
    )

    assert context["model_visible_skills"] == ["finish"]
    assert context["model_skill_surface"]["locked_or_hidden_actions"] == [
        "payment_authority.spend",
        "credential_vault.read_secret",
        "external_channel.contact_supplier",
    ]
    assert set(context["model_skill_surface"]["hard_stop_boundaries"]) >= {
        "payment",
        "credential_access",
        "contact_supplier",
    }


def _compile(*, available_actions: tuple[str, ...]) -> dict:
    return DecisionContextCompiler().compile(
        mission_id="mission_pack2_skill_only",
        mission_objective="Use simple model-facing skills while ActionEnvelope stays internal.",
        authority=MissionAuthorityEnvelope(
            user_id="user_pack2",
            mission_title="Skill-only model surface mission",
            mission_objective="Use simple model-facing skills while ActionEnvelope stays internal.",
            allowed_actions=available_actions,
            allowed_tools=(),
            allowed_domains=("bounded.test",),
            allowed_paths=("workspace:fixture",),
            max_actions=8,
            max_recipients=1,
        ),
        observations=[],
        available_actions=available_actions,
        model_calls_used=0,
        material_actions_used=0,
        max_model_calls=5,
        max_material_actions=5,
    )
