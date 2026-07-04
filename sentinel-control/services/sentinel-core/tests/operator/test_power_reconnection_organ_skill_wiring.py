from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.browser_backend_selector import select_browser_backend
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_pack_c_skill_registry_lists_read_patch_code_channel_browser() -> None:
    registry = build_default_power_skill_registry()

    bindings = {binding.skill_id: binding for binding in registry.bindings}

    assert {
        "read_only_research",
        "workspace_patch",
        "code_execution_sandbox",
        "bounded_channel",
        "real_browser_control",
    } <= set(bindings)
    assert bindings["read_only_research"].product_reachable is True
    assert bindings["workspace_patch"].task_loop_reachable is True
    assert bindings["code_execution_sandbox"].task_loop_reachable is True
    assert bindings["bounded_channel"].task_loop_reachable is True
    assert bindings["real_browser_control"].task_loop_reachable is True
    assert bindings["real_browser_control"].preferred_backend_id == "cloak_browser"
    assert bindings["real_browser_control"].model_visible_backend_id == "browser_skill"
    assert bindings["real_browser_control"].can_execute is False
    assert bindings["real_browser_control"].can_grant_authority is False


def test_pack_c_browser_backend_selector_prefers_cloak_when_available() -> None:
    selection = select_browser_backend(
        available_backend_modules={
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        }
    )

    assert selection.preferred_backend_id == "cloak_browser"
    assert selection.model_visible_backend_id == "browser_skill"
    assert selection.playwright_requires_explicit_compatibility is True
    assert "cloak_browser" in {candidate.backend_id for candidate in selection.candidates}
    assert selection.can_execute is False


def test_pack_c_playwright_backend_requires_explicit_compatibility_selection() -> None:
    selection = select_browser_backend(
        available_backend_modules={
            "sentinel.operator.real_browser_control_runtime",
        }
    )

    assert selection.preferred_backend_id is None
    assert selection.playwright_requires_explicit_compatibility is True
    assert selection.compatibility_backend_id == "playwright_real_browser_engine"
    assert selection.selection_reason == "cloak_browser_backend_unavailable"


def test_pack_c_runtime_host_product_adapters_stay_read_only_only(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    assert host.adapter_registry.adapter_ids() == ("read_only_research_adapter",)

    registry = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry)
    frame = registry.compile_backend_frame(
        available_actions=(
            "read_only_research.list_directory",
            "workspace_patch.apply_patch",
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
            "external_api.call",
        ),
        granted_capabilities=(
            "read_only_research",
            "workspace_patch",
            "code_execution_sandbox",
            "bounded_channel",
            "real_browser_control",
            "external_api",
        ),
    )

    by_skill = {item["skill_id"]: item for item in frame["skill_backends"]}

    assert by_skill["read_only_research"]["product_reachable"] is True
    assert by_skill["read_only_research"]["adapter_id"] == "read_only_research_adapter"
    assert by_skill["workspace_patch"]["product_reachable"] is False
    assert by_skill["workspace_patch"]["task_loop_reachable"] is True
    assert by_skill["real_browser_control"]["product_reachable"] is False
    assert by_skill["external_api"]["locked"] is True
    assert by_skill["external_api"]["dispatch_enabled"] is False


def test_pack_c_decision_context_exposes_safe_power_skill_backend_frame() -> None:
    authority = MissionAuthorityEnvelope(
        user_id="user_pack_c",
        mission_title="Organ to skill wiring",
        mission_objective="Use product skills without exposing backend plumbing.",
        allowed_actions=(
            "read_only_research.list_directory",
            "workspace_patch.apply_patch",
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
        ),
        allowed_tools=(),
        allowed_domains=(),
        allowed_paths=("workspace:fixture",),
        max_actions=5,
        max_recipients=1,
    )

    context = DecisionContextCompiler().compile(
        mission_id="mission_pack_c",
        mission_objective="Use product skills without exposing backend plumbing.",
        authority=authority,
        observations=[],
        available_actions=(
            "read_only_research.list_directory",
            "workspace_patch.apply_patch",
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
        ),
        model_calls_used=0,
        material_actions_used=0,
        max_model_calls=5,
        max_material_actions=5,
    )

    backend_frame = context["power_skill_backend_frame"]
    by_skill = {item["skill_id"]: item for item in backend_frame["skill_backends"]}

    assert backend_frame["invariant"] == "skills_map_to_organs_and_backends_without_granting_authority"
    assert by_skill["real_browser_control"]["model_visible_backend_id"] == "browser_skill"
    assert by_skill["real_browser_control"]["preferred_backend_id"] == "cloak_browser"
    assert by_skill["workspace_patch"]["owner_module"] == "sentinel.operator.workspace_patch_runtime"
    assert all(item["can_execute"] is False for item in backend_frame["skill_backends"])
    assert "raw_provider" not in str(backend_frame).lower()
    assert "authorization" not in str(backend_frame).lower()


def test_pack3_backend_frame_consumes_organ_spec_metadata_for_browser_skill() -> None:
    authority = MissionAuthorityEnvelope(
        user_id="user_pack3",
        mission_title="Organ spec backend truth",
        mission_objective="Expose browser backend truth from organ specs.",
        allowed_actions=("real_browser_control.real_browser.search",),
        allowed_tools=("real_browser_control",),
        allowed_domains=(),
        allowed_paths=(),
        max_actions=3,
        max_recipients=1,
    )

    context = DecisionContextCompiler().compile(
        mission_id="mission_pack3",
        mission_objective="Expose browser backend truth from organ specs.",
        authority=authority,
        observations=[],
        available_actions=("real_browser_control.real_browser.search",),
        model_calls_used=0,
        material_actions_used=0,
        max_model_calls=3,
        max_material_actions=3,
    )

    browser_backend = {
        item["skill_id"]: item
        for item in context["power_skill_backend_frame"]["skill_backends"]
    }["real_browser_control"]

    assert "browser_session_manager" in browser_backend["organ_spec_refs"]
    assert "browser_semantic_extraction" in browser_backend["organ_spec_refs"]
    assert "browser_session_receipt" in browser_backend["organ_receipt_kinds"]
    assert "locator_timeout" in browser_backend["organ_recoverable_failure_classes"]
    assert "payment" in browser_backend["organ_hard_stop_categories"]
    assert browser_backend["dispatch_enabled"] is False
    assert browser_backend["can_execute"] is False
