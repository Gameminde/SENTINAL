from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.decision_context import DecisionContextCompiler


def test_decision_context_prefers_model_visible_skill_actions() -> None:
    context = _compile(
        available_actions=(
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "sentinel_loop.finish",
        )
    )

    frame = context["skill_decision_frame"]

    assert context["decision_context_primary_truth"] == "skill_decision_frame"
    assert context["primary_model_recommended_next_action"] == frame["recommended_next_actions"][0]
    assert context["model_visible_recommended_next_action"] == context["primary_model_recommended_next_action"]
    assert "real_browser_control.real_browser.type_text" not in frame["recommended_next_actions"]
    assert "real_browser_control.real_browser.click" not in frame["recommended_next_actions"]
    assert set(frame["available_skills"]) >= {"real_browser_control", "sentinel_loop"}


def test_legacy_recommended_actions_do_not_override_skill_frame() -> None:
    observed = _result(
        capability_id="real_browser_control",
        operation="real_browser.observe",
        receipt_refs=("real_browser_observation_receipt",),
        context_cards={
            "browser_decision_frame": {
                "top_refs": [{"ref": "input:search", "role": "searchbox", "name": "search"}],
                "candidate_actions": [{"action": "real_browser.search", "ref": "input:search"}],
            },
            "browser_world_model": {
                "stable_refs": [{"ref": "input:search", "role": "searchbox", "name": "search"}],
                "search_like_refs": ["input:search"],
            },
        },
    )
    context = _compile(
        observations=[observed],
        available_actions=(
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.extract_text",
            "sentinel_loop.finish",
        ),
    )

    assert context["legacy_next_recommended_actions"][:2] == [
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
    ]
    assert context["skill_decision_frame"]["recommended_next_actions"][:2] == [
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.extract_product_cards",
    ]
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.search"


def test_browser_research_frame_prefers_search_extract_not_type_text() -> None:
    context = _compile(
        observations=[
            _result("real_browser_control", "real_browser.open", receipt_refs=("open_receipt",)),
            _result("real_browser_control", "real_browser.observe", receipt_refs=("observe_receipt",)),
        ],
        available_actions=(
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.select_option",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.extract_text",
            "sentinel_loop.finish",
        ),
    )

    browser_frame = context["skill_decision_frame"]["skill_frames"]["real_browser_control"]

    assert browser_frame["recommended_next_actions"][:3] == [
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.extract_product_cards",
    ]
    assert "real_browser_control.real_browser.type_text" in browser_frame["internal_actions"]
    assert "real_browser_control.real_browser.type_text" not in browser_frame["recommended_next_actions"]
    assert browser_frame["proof_requirements"] == ["browser_action_or_extraction_receipt"]


def test_workspace_patch_frame_requires_patch_plus_verification() -> None:
    context = _compile(
        available_actions=(
            "workspace_patch.apply_patch",
            "workspace_patch.run_bounded_check",
            "sentinel_loop.finish",
        ),
    )

    workspace_frame = context["skill_decision_frame"]["skill_frames"]["workspace_patch"]

    assert workspace_frame["proof_requirements"] == [
        "workspace_patch_receipt",
        "post_patch_verification_receipt",
    ]
    assert workspace_frame["recommended_next_actions"] == ["workspace_patch.apply_patch"]
    assert workspace_frame["completion_requirements"]["requires_workspace_patch_receipt"] is True
    assert workspace_frame["completion_requirements"]["requires_verification_receipt"] is True


def test_code_exec_frame_requires_run_plus_bounded_check() -> None:
    context = _compile(
        available_actions=(
            "code_execution_sandbox.code_exec.run_profile",
            "workspace_patch.run_bounded_check",
            "sentinel_loop.finish",
        ),
    )

    code_frame = context["skill_decision_frame"]["skill_frames"]["code_execution_sandbox"]

    assert code_frame["proof_requirements"] == [
        "sandbox_execution_receipt",
        "bounded_check_or_verification_receipt",
    ]
    assert code_frame["recommended_next_actions"] == [
        "code_execution_sandbox.code_exec.run_profile"
    ]
    assert code_frame["completion_requirements"]["requires_code_execution_receipt"] is True
    assert code_frame["completion_requirements"]["requires_verification_receipt"] is True


def test_read_only_frame_is_supporting_evidence_skill_in_mixed_power_loop() -> None:
    context = _compile(
        available_actions=(
            "read_only_research.list_directory",
            "read_only_research.search_text",
            "read_only_research.read_file_segment",
            "workspace_patch.apply_patch",
            "workspace_patch.run_bounded_check",
            "code_execution_sandbox.code_exec.run_profile",
            "sentinel_loop.finish",
        ),
    )

    read_only_frame = context["skill_decision_frame"]["skill_frames"]["read_only_research"]

    assert read_only_frame["model_facing_role"] == "supporting_evidence_skill"
    assert read_only_frame["architecture_role"] == "evidence_skill_not_product_center"
    assert context["primary_model_recommended_next_action"] != "read_only_research.list_directory"
    assert context["recommended_next_action"] == context["primary_model_recommended_next_action"]


def test_channel_frame_requires_delivery_then_finish() -> None:
    sent = _result(
        capability_id="bounded_channel",
        operation="send_message",
        status="completed",
        receipt_refs=("channel_receipt",),
    )
    context = _compile(
        observations=[sent],
        available_actions=("bounded_channel.send_message", "sentinel_loop.finish"),
    )

    channel_frame = context["skill_decision_frame"]["skill_frames"]["bounded_channel"]

    assert channel_frame["proof_requirements"] == [
        "delivery_receipt",
        "no_resend_replay_proof",
        "finish_action",
    ]
    assert channel_frame["recommended_next_actions"] == ["sentinel_loop.finish"]
    assert channel_frame["completion_requirements"]["has_channel_send_receipt"] is True
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.finish"


def test_finish_available_only_after_skill_proof() -> None:
    before = _compile(
        available_actions=("workspace_patch.apply_patch", "sentinel_loop.finish"),
    )
    after = _compile(
        observations=[
            _result("code_execution_sandbox", "code_exec.run_profile", receipt_refs=("code_receipt",)),
            _result("workspace_patch", "apply_patch", receipt_refs=("patch_receipt",)),
            _result("workspace_patch", "run_bounded_check", receipt_refs=("check_receipt",)),
        ],
        available_actions=(
            "code_execution_sandbox.code_exec.run_profile",
            "workspace_patch.apply_patch",
            "workspace_patch.run_bounded_check",
            "sentinel_loop.finish",
        ),
    )

    assert before["skill_decision_frame"]["finish_available"] is False
    assert before["primary_model_recommended_next_action"] != "sentinel_loop.finish"
    assert after["skill_decision_frame"]["finish_available"] is True
    assert after["primary_model_recommended_next_action"] == "sentinel_loop.finish"


def test_recoverable_observations_are_visible_to_next_model_turn() -> None:
    recoverable = _result(
        capability_id="real_browser_control",
        operation="real_browser.search",
        status="recoverable_failed",
        recoverable=True,
        failure_class=ActionFailureClass.RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE,
        failure_code="LOCATOR_TIMEOUT",
        recommended_next_actions=(
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
        ),
    )
    context = _compile(
        observations=[recoverable],
        available_actions=(
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "sentinel_loop.finish",
        ),
        max_recovery_turns=2,
        recovery_turns_used=1,
    )

    frame = context["skill_decision_frame"]

    assert frame["recoverable_observations"][0]["failure_code"] == "LOCATOR_TIMEOUT"
    assert frame["recoverable_observations"][0]["recommended_next_actions"] == [
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.extract_product_cards",
    ]
    assert frame["budget_remaining"]["recovery_turns"] == 1
    assert frame["recommended_next_actions"][0] == "real_browser_control.real_browser.search"


def _compile(
    *,
    observations: list[ActionResult] | None = None,
    available_actions: tuple[str, ...],
    recovery_turns_used: int = 0,
    max_recovery_turns: int = 0,
) -> dict:
    return DecisionContextCompiler().compile(
        mission_id="mission_pack_d",
        mission_objective="Use skill-first context to complete the mission.",
        authority=_authority(available_actions),
        observations=observations or [],
        available_actions=available_actions,
        model_calls_used=0,
        material_actions_used=0,
        max_model_calls=5,
        max_material_actions=5,
        recovery_turns_used=recovery_turns_used,
        max_recovery_turns=max_recovery_turns,
    )


def _authority(available_actions: tuple[str, ...]) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="user_pack_d",
        mission_title="Skill frame mission",
        mission_objective="Use skill-first context to complete the mission.",
        allowed_actions=available_actions,
        allowed_tools=(),
        allowed_domains=("bounded.test",),
        allowed_paths=("workspace:fixture",),
        max_actions=8,
        max_recipients=1,
    )


def _result(
    capability_id: str,
    operation: str,
    *,
    status: str = "completed",
    receipt_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    recoverable: bool = False,
    failure_class: ActionFailureClass | None = None,
    failure_code: str | None = None,
    recommended_next_actions: tuple[str, ...] = (),
    context_cards: dict | None = None,
) -> ActionResult:
    return ActionResult(
        action_id=f"action_{capability_id}_{operation}".replace(".", "_"),
        capability_id=capability_id,
        operation=operation,
        status=status,
        receipt_refs=receipt_refs,
        evidence_refs=evidence_refs,
        material_action=bool(receipt_refs and operation not in {"real_browser.open", "real_browser.observe"}),
        observation_summary=f"{capability_id}:{operation}:{status}",
        failure_class=failure_class,
        failure_code=failure_code,
        recoverable=recoverable,
        recovery_observation={
            "failure_code": failure_code,
            "safe_summary": "recoverable in-scope miss",
        }
        if recoverable
        else {},
        recommended_next_actions=recommended_next_actions,
        context_cards=context_cards or {},
    )
