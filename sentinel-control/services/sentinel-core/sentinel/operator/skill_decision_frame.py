from __future__ import annotations

from typing import Any

from sentinel.operator.action_kernel import ActionResult


def compile_skill_decision_frame(
    *,
    mission_objective: str,
    progress_state: str,
    legacy_next_recommended_actions: list[str],
    objective_satisfied: bool,
    finish_available: bool,
    skill_exposure_frame: Any,
    power_skill_backend_frame: dict[str, Any],
    observations: list[ActionResult],
    completion_requirements: dict[str, Any],
    budget_remaining: dict[str, int],
    recoverable_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    visible_actions = [_exposure_action(item) for item in getattr(skill_exposure_frame, "model_visible_actions", ())]
    hidden_internal_actions = [_exposure_action(item) for item in getattr(skill_exposure_frame, "hidden_internal_actions", ())]
    visible_by_skill = _actions_by_skill(getattr(skill_exposure_frame, "model_visible_actions", ()))
    internal_by_skill = _actions_by_skill(getattr(skill_exposure_frame, "hidden_internal_actions", ()))
    backends = {
        str(item.get("skill_id")): item
        for item in power_skill_backend_frame.get("skill_backends", [])
        if isinstance(item, dict) and item.get("skill_id")
    }
    skill_ids = tuple(sorted({*visible_by_skill, *backends}))
    skill_frames = {
        skill_id: _skill_frame(
            skill_id=skill_id,
            visible_actions=visible_by_skill.get(skill_id, []),
            internal_actions=internal_by_skill.get(skill_id, []),
            backend=backends.get(skill_id, {}),
            progress_state=progress_state,
            objective_satisfied=objective_satisfied,
            completion_requirements=completion_requirements,
        )
        for skill_id in skill_ids
    }
    recommended = _primary_recommendations(
        skill_frames=skill_frames,
        visible_actions=visible_actions,
        recoverable_observations=recoverable_observations,
        objective_satisfied=objective_satisfied,
        legacy_next_recommended_actions=legacy_next_recommended_actions,
        completion_requirements=completion_requirements,
    )
    return {
        "frame_version": "skill_decision_frame_v1",
        "primary_truth": "skill_decision_frame",
        "mission_objective": mission_objective,
        "current_progress_state": progress_state,
        "available_skills": list(skill_ids),
        "executable_skills": [
            skill_id
            for skill_id in skill_ids
            if not bool(skill_frames[skill_id].get("locked")) and skill_frames[skill_id].get("model_visible_actions")
        ],
        "skill_frames": skill_frames,
        "recommended_next_actions": recommended,
        "legacy_next_recommended_actions": legacy_next_recommended_actions,
        "recent_receipts": _recent_receipts(observations),
        "recoverable_observations": recoverable_observations,
        "proof_requirements": _proof_requirements(skill_frames),
        "finish_available": finish_available,
        "hard_stop_boundaries": _hard_stop_boundaries(skill_exposure_frame),
        "budget_remaining": budget_remaining,
        "completion_requirements": completion_requirements,
        "invariant": "model_consumes_skill_frames_before_legacy_primitive_recommendations",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def _skill_frame(
    *,
    skill_id: str,
    visible_actions: list[str],
    internal_actions: list[str],
    backend: dict[str, Any],
    progress_state: str,
    objective_satisfied: bool,
    completion_requirements: dict[str, Any],
) -> dict[str, Any]:
    if skill_id == "workspace_patch":
        proof = ["workspace_patch_receipt", "post_patch_verification_receipt"]
        recommended = _workspace_patch_recommendations(visible_actions, completion_requirements, objective_satisfied)
    elif skill_id == "code_execution_sandbox":
        proof = ["sandbox_execution_receipt", "bounded_check_or_verification_receipt"]
        recommended = _first_available(visible_actions, ["code_execution_sandbox.code_exec.run_profile"])
    elif skill_id == "bounded_channel":
        proof = ["delivery_receipt", "no_resend_replay_proof", "finish_action"]
        recommended = _channel_recommendations(visible_actions, completion_requirements, objective_satisfied)
    elif skill_id == "real_browser_control":
        proof = ["browser_action_or_extraction_receipt"]
        recommended = _real_browser_recommendations(visible_actions, progress_state, objective_satisfied)
    elif skill_id == "browser_control":
        proof = ["browser_observation_or_action_receipt"]
        recommended = _first_available(visible_actions, ["browser_control.browser.observe", "browser_control.browser.assert_text"])
    elif skill_id == "read_only_research":
        proof = ["read_only_observation_receipt"]
        recommended = _first_available(
            visible_actions,
            [
                "read_only_research.list_directory",
                "read_only_research.search_text",
                "read_only_research.read_file_segment",
                "read_only_research.finish_exploration",
            ],
        )
    elif skill_id == "sentinel_loop":
        proof = ["grounded_summary_then_finish_action_after_objective_proof"]
        recommended = _sentinel_loop_recommendations(visible_actions, completion_requirements, objective_satisfied)
    else:
        proof = [str(backend.get("proof_contract") or "future_pack_required")]
        recommended = _first_available(visible_actions, visible_actions)
    return {
        "skill_id": skill_id,
        "model_visible_actions": visible_actions,
        "internal_actions": internal_actions,
        "recommended_next_actions": recommended,
        "proof_requirements": proof,
        "completion_requirements": completion_requirements,
        "backend": {
            "model_visible_backend_id": backend.get("model_visible_backend_id"),
            "preferred_backend_id": backend.get("preferred_backend_id"),
            "compatibility_backend_id": backend.get("compatibility_backend_id"),
            "owner_module": backend.get("owner_module"),
            "product_reachable": bool(backend.get("product_reachable")),
            "task_loop_reachable": bool(backend.get("task_loop_reachable")),
            "dispatch_enabled": bool(backend.get("dispatch_enabled")),
        },
        "locked": bool(backend.get("locked")),
        "lock_reason": str(backend.get("lock_reason") or ""),
    }


def _primary_recommendations(
    *,
    skill_frames: dict[str, dict[str, Any]],
    visible_actions: list[str],
    recoverable_observations: list[dict[str, Any]],
    objective_satisfied: bool,
    legacy_next_recommended_actions: list[str],
    completion_requirements: dict[str, Any],
) -> list[str]:
    if objective_satisfied and "sentinel_loop.finish" in visible_actions:
        return ["sentinel_loop.finish"]
    if (
        completion_requirements.get("requires_grounded_evidence_summary") is True
        and "sentinel_loop.summarize_evidence" in visible_actions
    ):
        return ["sentinel_loop.summarize_evidence"]
    if completion_requirements.get("requires_relevant_product_evidence") is True:
        preferred_recovery_actions = [
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
        ]
        if completion_requirements.get("has_real_browser_search_receipt") is True:
            preferred_recovery_actions = [
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.search",
            ]
        browser_recovery = _first_available(
            visible_actions,
            preferred_recovery_actions,
        )
        if browser_recovery:
            return browser_recovery
    for recoverable in reversed(recoverable_observations):
        recovered = [
            action
            for action in recoverable.get("recommended_next_actions", [])
            if action in visible_actions
        ]
        if recovered:
            return _dedupe(recovered)
    for skill_id in (
        "real_browser_control",
        "browser_control",
        "bounded_channel",
        "workspace_patch",
        "code_execution_sandbox",
        "read_only_research",
        "sentinel_loop",
    ):
        recommendations = [
            action
            for action in skill_frames.get(skill_id, {}).get("recommended_next_actions", [])
            if action in visible_actions or action == "sentinel_loop.finish"
        ]
        if recommendations:
            return _dedupe(recommendations)
    filtered_legacy = [action for action in legacy_next_recommended_actions if action in visible_actions]
    if filtered_legacy:
        return _dedupe(filtered_legacy)
    return visible_actions[:1]


def _real_browser_recommendations(visible_actions: list[str], progress_state: str, objective_satisfied: bool) -> list[str]:
    if objective_satisfied:
        return _first_available(visible_actions, ["sentinel_loop.finish"])
    if progress_state == "real_browser_verified_extraction_needs_summary":
        return _first_available(visible_actions, ["sentinel_loop.summarize_evidence"])
    if progress_state == "real_browser_extraction_needs_verification":
        return _first_available(visible_actions, ["real_browser_control.real_browser.verify_extraction"])
    if progress_state == "real_browser_verified_extraction_needs_relevant_products":
        return _first_available(
            visible_actions,
            [
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.extract_product_cards",
            ],
        )
    if progress_state == "real_browser_not_started":
        return _first_available(
            visible_actions,
            [
                "real_browser_control.real_browser.open",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.extract_product_cards",
            ],
        )
    if progress_state == "real_browser_opened_world_model_ready":
        return _first_available(
            visible_actions,
            [
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.extract_product_cards",
            ],
        )
    if progress_state in {"real_browser_observed_needs_action", "real_browser_action_needs_assertion"}:
        return _first_available(
            visible_actions,
            [
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
                "real_browser_control.real_browser.assert_text",
            ],
        )
    return _first_available(
        visible_actions,
        [
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.open",
        ],
    )


def _sentinel_loop_recommendations(
    visible_actions: list[str],
    completion_requirements: dict[str, Any],
    objective_satisfied: bool,
) -> list[str]:
    if (
        completion_requirements.get("requires_grounded_evidence_summary") is True
        and "sentinel_loop.summarize_evidence" in visible_actions
    ):
        return ["sentinel_loop.summarize_evidence"]
    if objective_satisfied and "sentinel_loop.finish" in visible_actions:
        return ["sentinel_loop.finish"]
    return []


def _workspace_patch_recommendations(
    visible_actions: list[str],
    completion_requirements: dict[str, Any],
    objective_satisfied: bool,
) -> list[str]:
    if objective_satisfied:
        return _first_available(visible_actions, ["sentinel_loop.finish"])
    if completion_requirements.get("requires_workspace_patch_receipt") is not False:
        return _first_available(visible_actions, ["workspace_patch.apply_patch"])
    if completion_requirements.get("requires_verification_receipt") is not False:
        return _first_available(visible_actions, ["workspace_patch.run_bounded_check"])
    return []


def _channel_recommendations(
    visible_actions: list[str],
    completion_requirements: dict[str, Any],
    objective_satisfied: bool,
) -> list[str]:
    if objective_satisfied or completion_requirements.get("has_channel_send_receipt") is True:
        return ["sentinel_loop.finish"]
    return _first_available(visible_actions, ["bounded_channel.send_message"])


def _first_available(visible_actions: list[str], preference: list[str]) -> list[str]:
    return [action for action in preference if action in visible_actions]


def _actions_by_skill(exposures: Any) -> dict[str, list[str]]:
    by_skill: dict[str, list[str]] = {}
    for exposure in exposures:
        skill_id = str(getattr(exposure, "skill_id", ""))
        action = _exposure_action(exposure)
        if skill_id and action:
            by_skill.setdefault(skill_id, []).append(action)
    return {skill_id: _dedupe(actions) for skill_id, actions in by_skill.items()}


def _exposure_action(exposure: Any) -> str:
    return str(getattr(exposure, "canonical_action_name", "") or getattr(exposure, "action_name", ""))


def _recent_receipts(observations: list[ActionResult]) -> list[str]:
    receipts: list[str] = []
    for result in observations[-6:]:
        receipts.extend(result.receipt_refs)
    return receipts


def _proof_requirements(skill_frames: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    return {
        skill_id: list(frame.get("proof_requirements", []))
        for skill_id, frame in sorted(skill_frames.items())
        if frame.get("proof_requirements")
    }


def _hard_stop_boundaries(skill_exposure_frame: Any) -> list[str]:
    boundaries: list[str] = []
    for skill in getattr(skill_exposure_frame, "locked_skills", ()):
        boundaries.extend(str(item) for item in getattr(skill, "hard_stop_boundaries", ()))
    boundaries.extend(
        [
            "workspace_escape",
            "credential_access",
            "payment",
            "checkout",
            "provider_native_tools",
            "fallback_auto",
        ]
    )
    return _dedupe(boundaries)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


__all__ = ["compile_skill_decision_frame"]
