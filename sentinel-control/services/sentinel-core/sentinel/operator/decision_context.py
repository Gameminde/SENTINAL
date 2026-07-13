from __future__ import annotations

from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.actionability_registry import build_default_actionability_registry
from sentinel.operator.action_kernel import ActionResult
from sentinel.operator.action_power_contract import ActionAliasNormalizer
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.skill_decision_frame import compile_skill_decision_frame


class DecisionContextCompiler:
    def compile(
        self,
        *,
        mission_id: str,
        mission_objective: str,
        authority: MissionAuthorityEnvelope,
        observations: list[ActionResult],
        available_actions: tuple[str, ...],
        model_calls_used: int,
        material_actions_used: int,
        max_model_calls: int,
        max_material_actions: int,
        recovery_turns_used: int = 0,
        max_recovery_turns: int = 0,
        correction_turns_used: int = 0,
        max_correction_turns: int = 0,
    ) -> dict[str, Any]:
        previous = observations[-1] if observations else None
        sequenced_observations = list(enumerate(observations))
        workspace_patch_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "workspace_patch" and result.operation == "apply_patch"
        ]
        workspace_verification_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "workspace_patch" and result.operation == "run_bounded_check"
        ]
        read_only_verification_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "read_only_research"
            and result.operation in {"search_text", "read_file_segment", "list_directory"}
            and result.receipt_refs
        ]
        code_execution_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "code_execution_sandbox" and result.operation == "code_exec.run_profile"
        ]
        browser_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "browser_control"
        ]
        real_browser_results = [
            result
            for result in observations[-6:]
            if result.capability_id == "real_browser_control"
        ]
        channel_results = [
            result
            for result in observations[-6:]
            if result.capability_id in {"bounded_channel", "channel_transport"}
        ]
        channel_delivery_results = [
            result
            for result in channel_results
            if result.operation == "send_message" and result.status in {"completed", "passed", "success"} and result.receipt_refs
        ]
        recoverable_results = [result for result in observations[-6:] if result.recoverable]
        latest_recoverable = recoverable_results[-1] if recoverable_results else None
        browser_action_results = [
            result
            for result in browser_results
            if result.operation in {"browser.click", "browser.type_text", "browser.select_option"} and result.receipt_refs
        ]
        browser_assertion_results = [
            result
            for result in browser_results
            if result.operation == "browser.assert_text" and result.status == "passed" and result.receipt_refs
        ]
        real_browser_action_results = [
            result
            for result in real_browser_results
            if result.operation
            in {
                "real_browser.click",
                "real_browser.type_text",
                "real_browser.select_option",
                "real_browser.press_key",
                "real_browser.scroll",
                "real_browser.search",
                "real_browser.inspect_result",
                "real_browser.open_result",
            }
            and result.receipt_refs
        ]
        real_browser_assertion_results = [
            result
            for result in real_browser_results
            if result.operation == "real_browser.assert_text" and result.status == "passed" and result.receipt_refs
        ]
        real_browser_extraction_results = [
            result
            for result in real_browser_results
            if result.operation in {"real_browser.extract_text", "real_browser.extract_product_cards", "real_browser.verify_extraction"}
            and result.status in {"completed", "passed", "success"}
            and result.receipt_refs
        ]
        real_browser_verified_extraction_results = [
            result
            for result in real_browser_results
            if result.operation == "real_browser.verify_extraction"
            and result.status in {"completed", "passed", "success"}
            and result.receipt_refs
        ]
        grounded_summary_results = [
            result
            for result in observations
            if result.capability_id == "sentinel_loop"
            and result.operation == "summarize_evidence"
            and result.status in {"completed", "passed", "success"}
        ]
        real_browser_cards = _latest_real_browser_context_cards(real_browser_results)
        browser_environment_state = _safe_browser_environment_state(
            real_browser_cards.get("browser_environment_state")
        )
        browser_environment_state_hash = (
            str(real_browser_cards.get("browser_environment_state_hash") or "")
            if browser_environment_state
            else ""
        )
        browser_environment_memory = _browser_environment_memory(real_browser_results)
        grounded_evidence_summary = _grounded_evidence_summary(grounded_summary_results)
        latest_patch_index = _latest_success_index(
            sequenced_observations,
            capability_id="workspace_patch",
            operation="apply_patch",
        )
        post_patch_verification_results = _post_patch_verification_results(
            sequenced_observations,
            latest_patch_index=latest_patch_index,
        )
        browser_mode = _is_browser_mode(available_actions=available_actions, observations=observations)
        real_browser_mode = _is_real_browser_mode(available_actions=available_actions, observations=observations)
        patch_objective_satisfied = _objective_satisfied(
            code_execution_results=code_execution_results,
            workspace_patch_results=workspace_patch_results,
            post_patch_verification_results=post_patch_verification_results,
        )
        channel_mode = _is_channel_mode(available_actions=available_actions, observations=observations)
        if real_browser_mode:
            objective_satisfied = bool(
                real_browser_assertion_results
                or (
                    real_browser_verified_extraction_results
                    and grounded_summary_results
                    and grounded_evidence_summary["objective_relevance_assessed"] is True
                )
            )
        elif browser_mode:
            objective_satisfied = bool(browser_assertion_results)
        elif channel_mode:
            objective_satisfied = bool(channel_delivery_results)
        else:
            objective_satisfied = patch_objective_satisfied
        progress_guidance = (
            _real_browser_progress_guidance(
                objective_satisfied=objective_satisfied,
                real_browser_results=real_browser_results,
                real_browser_action_results=real_browser_action_results,
                real_browser_assertion_results=real_browser_assertion_results,
                real_browser_extraction_results=real_browser_extraction_results,
                real_browser_verified_extraction_results=real_browser_verified_extraction_results,
                grounded_summary_results=grounded_summary_results,
                grounded_evidence_summary=grounded_evidence_summary,
            )
            if real_browser_mode
            else _browser_progress_guidance(
                objective_satisfied=objective_satisfied,
                browser_results=browser_results,
                browser_action_results=browser_action_results,
                browser_assertion_results=browser_assertion_results,
            )
            if browser_mode
            else _channel_progress_guidance(
                objective_satisfied=objective_satisfied,
                channel_delivery_results=channel_delivery_results,
            )
            if channel_mode
            else _progress_guidance(
                objective_satisfied=objective_satisfied,
                code_execution_results=code_execution_results,
                workspace_patch_results=workspace_patch_results,
                read_only_verification_results=read_only_verification_results,
                post_patch_verification_results=post_patch_verification_results,
            )
        )
        actionability_registry = build_default_actionability_registry()
        skill_exposure_frame = actionability_registry.compile_frame(
            available_actions=available_actions,
            granted_capabilities=_granted_capabilities(authority),
        )
        power_skill_backend_frame = build_default_power_skill_registry().compile_backend_frame(
            available_actions=available_actions,
            granted_capabilities=_granted_capabilities(authority),
            actionability_registry=actionability_registry,
        )
        budget_remaining = {
            "model_calls": max(max_model_calls - model_calls_used, 0),
            "material_actions": max(max_material_actions - material_actions_used, 0),
            "recovery_turns": max(max_recovery_turns - recovery_turns_used, 0),
            "correction_turns": max(max_correction_turns - correction_turns_used, 0),
        }
        recoverable_failure_history = [_recoverable_failure_summary(result) for result in recoverable_results]
        skill_decision_frame = compile_skill_decision_frame(
            mission_objective=mission_objective,
            progress_state=progress_guidance["progress_state"],
            available_actions=available_actions,
            legacy_next_recommended_actions=progress_guidance["next_recommended_actions"],
            objective_satisfied=objective_satisfied,
            finish_available=objective_satisfied,
            skill_exposure_frame=skill_exposure_frame,
            power_skill_backend_frame=power_skill_backend_frame,
            observations=observations,
            completion_requirements=progress_guidance["completion_requirements"],
            budget_remaining=budget_remaining,
            recoverable_observations=recoverable_failure_history,
        )
        model_visible_available_actions = [
            str(item.get("canonical_action_name") or item.get("action_name") or "")
            for item in skill_exposure_frame.safe_model_dump().get("model_visible_actions", [])
            if str(item.get("canonical_action_name") or item.get("action_name") or "")
        ]
        model_visible_next_actions = list(skill_decision_frame["recommended_next_actions"])
        model_skill_surface = dict(skill_decision_frame["model_skill_surface"])
        model_visible_skills = list(model_skill_surface["model_visible_skills"])
        model_visible_next_skills = list(model_skill_surface["recommended_next_skills"])
        return {
            "mission_id": mission_id,
            "mission_objective": mission_objective,
            "available_actions": list(available_actions),
            "runtime_available_actions": list(available_actions),
            "model_visible_available_actions": model_visible_available_actions,
            "primary_model_surface": "model_visible_skills",
            "primary_model_language": "simple_mission_skills",
            "action_envelope_language": "internal_runtime_only",
            "model_skill_surface": model_skill_surface,
            "model_visible_skills": model_visible_skills,
            "primary_model_next_recommended_skills": model_visible_next_skills,
            "primary_model_recommended_next_skill": (
                model_visible_next_skills[0] if model_visible_next_skills else None
            ),
            "model_visible_next_recommended_skills": model_visible_next_skills,
            "model_visible_recommended_next_skill": (
                model_visible_next_skills[0] if model_visible_next_skills else None
            ),
            "runtime_internal_action_map": dict(model_skill_surface["runtime_internal_action_map"]),
            "decision_context_primary_truth": "skill_decision_frame",
            "skill_exposure_frame": skill_exposure_frame.safe_model_dump(),
            "power_skill_backend_frame": power_skill_backend_frame,
            "skill_decision_frame": skill_decision_frame,
            "legacy_recommended_next_action": (
                "sentinel_loop.finish"
                if objective_satisfied
                else (progress_guidance["next_recommended_actions"][0] if progress_guidance["next_recommended_actions"] else None)
            ),
            "legacy_next_recommended_actions": progress_guidance["next_recommended_actions"],
            "primary_model_next_recommended_actions": model_visible_next_actions,
            "primary_model_recommended_next_action": model_visible_next_actions[0] if model_visible_next_actions else None,
            "model_visible_next_recommended_actions": model_visible_next_actions,
            "model_visible_recommended_next_action": (
                model_visible_next_actions[0] if model_visible_next_actions else None
            ),
            "objective_satisfied": objective_satisfied,
            "finish_available": objective_satisfied,
            "recommended_next_action": (
                model_visible_next_actions[0]
                if model_visible_next_actions
                else None
            ),
            "progress_state": progress_guidance["progress_state"],
            "next_recommended_actions": progress_guidance["next_recommended_actions"],
            "objective_remaining_steps": progress_guidance["objective_remaining_steps"],
            "completion_requirements": progress_guidance["completion_requirements"],
            "finish_instruction": (
                "Objective receipts are satisfied. Emit sentinel_loop.finish now; do not spend another material action."
                if objective_satisfied
                else ""
            ),
            "authority_summary": {
                "allowed_actions": list(authority.allowed_actions),
                "allowed_tools": list(authority.allowed_tools),
                "allowed_domains": list(authority.allowed_domains),
                "allowed_paths_count": len(authority.allowed_paths),
                "max_actions": authority.max_actions,
                "max_recipients": authority.max_recipients,
            },
            "previous_receipt_refs": [ref for result in observations for ref in result.receipt_refs],
            "bounded_observation_summaries": [
                {
                    "capability_id": result.capability_id,
                    "operation": result.operation,
                    "status": result.status,
                    "receipt_count": len(result.receipt_refs),
                    "evidence_count": len(result.evidence_refs),
                    "summary": result.observation_summary[:500],
                }
                for result in observations[-6:]
            ],
            "last_action_status": previous.status if previous is not None else None,
            "budget_remaining": {
                "model_calls": budget_remaining["model_calls"],
                "material_actions": budget_remaining["material_actions"],
                "recovery_turns": budget_remaining["recovery_turns"],
                "correction_turns": budget_remaining["correction_turns"],
            },
            "channel_grant_summary": {
                "allowed_domains": list(authority.allowed_domains),
                "max_recipients": authority.max_recipients,
            },
            "read_only_workspace_summary": {
                "allowed_paths_count": len(authority.allowed_paths),
            },
            "workspace_patch_summary": [
                {
                    "operation": result.operation,
                    "status": result.status,
                    "receipt_count": len(result.receipt_refs),
                    "evidence_count": len(result.evidence_refs),
                    "summary": result.observation_summary[:500],
                    "result_hash": result.result_hash,
                }
                for result in workspace_patch_results
            ],
            "workspace_verification_summary": [
                {
                    "operation": result.operation,
                    "status": result.status,
                    "receipt_count": len(result.receipt_refs),
                    "summary": result.observation_summary[:500],
                    "result_hash": result.result_hash,
                }
                for result in workspace_verification_results
            ],
            "read_only_verification_summary": [
                {
                    "operation": result.operation,
                    "status": result.status,
                    "receipt_count": len(result.receipt_refs),
                    "summary": result.observation_summary[:500],
                    "result_hash": result.result_hash,
                }
                for result in read_only_verification_results
            ],
            "code_execution_summary": [
                {
                    "operation": result.operation,
                    "status": result.status,
                    "profile_id": _profile_id_from_summary(result.observation_summary),
                    "receipt_count": len(result.receipt_refs),
                    "summary": result.observation_summary[:500],
                    "result_hash": result.result_hash,
                }
                for result in code_execution_results
            ],
            "browser_control_summary": _browser_summary(browser_results),
            "real_browser_control_summary": _real_browser_summary(real_browser_results),
            "grounded_evidence_summary": grounded_evidence_summary,
            "browser_world_model_summary": real_browser_cards.get("browser_world_model_summary") if real_browser_mode else {},
            "browser_world_model": real_browser_cards.get("browser_world_model") if real_browser_mode else {},
            "browser_environment_state": browser_environment_state if real_browser_mode else {},
            "browser_environment_state_hash": browser_environment_state_hash if real_browser_mode else "",
            "browser_environment_memory": browser_environment_memory if real_browser_mode else {},
            "browser_decision_frame": real_browser_cards.get("browser_decision_frame") if real_browser_mode else {},
            "browser_actionability_registry": real_browser_cards.get("browser_actionability_registry") if real_browser_mode else {},
            "actionability_frame": real_browser_cards.get("actionability_frame") if real_browser_mode else {},
            "last_recoverable_failure": _recoverable_failure_summary(latest_recoverable),
            "recoverable_observations": [_recoverable_failure_summary(result) for result in recoverable_results],
            "recoverable_failure_history": [_recoverable_failure_summary(result) for result in recoverable_results],
            "top_stable_refs": _top_stable_refs(real_browser_cards),
            "top_action_candidates": _top_action_candidates(real_browser_cards),
            "top_link_candidates": _top_link_candidates(real_browser_cards),
            "search_like_controls": _search_like_controls(real_browser_cards),
            "blocker_signals": _blocker_signals(real_browser_cards),
            "allowed_action_schema": _allowed_action_schema(real_browser_mode=real_browser_mode),
            "channel_delivery_summary": _channel_summary(channel_results),
        }


def _objective_satisfied(
    *,
    code_execution_results: list[ActionResult],
    workspace_patch_results: list[ActionResult],
    post_patch_verification_results: list[ActionResult],
) -> bool:
    has_code_execution = any(result.receipt_refs and result.status in {"passed", "completed"} for result in code_execution_results)
    has_patch = any(result.receipt_refs and result.status in {"completed", "passed"} for result in workspace_patch_results)
    has_verification = any(result.receipt_refs and result.status in {"completed", "passed"} for result in post_patch_verification_results)
    return has_code_execution and has_patch and has_verification


def _recoverable_failure_summary(result: ActionResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "capability_id": result.capability_id,
        "operation": result.operation,
        "status": result.status,
        "failure_class": result.failure_class.value if result.failure_class else None,
        "failure_code": result.failure_code,
        "blocked_reason": result.blocked_reason,
        "summary": result.observation_summary[:500],
        "recommended_next_actions": list(result.recommended_next_actions),
        "recovery_observation": result.recovery_observation,
    }


def _latest_success_index(
    sequenced_observations: list[tuple[int, ActionResult]],
    *,
    capability_id: str,
    operation: str,
) -> int | None:
    return next(
        (
            index
            for index, result in reversed(sequenced_observations)
            if result.capability_id == capability_id
            and result.operation == operation
            and result.receipt_refs
            and result.status in {"completed", "passed", "success"}
        ),
        None,
    )


def _post_patch_verification_results(
    sequenced_observations: list[tuple[int, ActionResult]],
    *,
    latest_patch_index: int | None,
) -> list[ActionResult]:
    if latest_patch_index is None:
        return []
    return [
        result
        for index, result in sequenced_observations
        if index > latest_patch_index and _is_post_patch_verification_result(result)
    ]


def _is_post_patch_verification_result(result: ActionResult) -> bool:
    if not result.receipt_refs or result.status not in {"completed", "passed", "success"}:
        return False
    if result.capability_id == "workspace_patch" and result.operation == "run_bounded_check":
        return True
    if result.capability_id == "code_execution_sandbox" and result.operation == "code_exec.run_profile":
        return True
    return result.capability_id == "read_only_research" and result.operation in {"search_text", "read_file_segment"}


def _progress_guidance(
    *,
    objective_satisfied: bool,
    code_execution_results: list[ActionResult],
    workspace_patch_results: list[ActionResult],
    read_only_verification_results: list[ActionResult],
    post_patch_verification_results: list[ActionResult],
) -> dict[str, Any]:
    has_read_only_observation = any(
        result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in read_only_verification_results
    )
    has_code_execution = any(
        result.receipt_refs and result.status in {"completed", "passed", "success"} for result in code_execution_results
    )
    has_patch = any(
        result.receipt_refs and result.status in {"completed", "passed", "success"} for result in workspace_patch_results
    )
    has_verification = any(
        result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in post_patch_verification_results
    )
    completion_requirements = {
        "requires_code_execution_receipt": not has_code_execution,
        "requires_workspace_patch_receipt": not has_patch,
        "requires_verification_receipt": not has_verification,
        "requires_finish_action": True,
        "has_read_only_observation_receipt": has_read_only_observation,
        "has_code_execution_receipt": has_code_execution,
        "has_workspace_patch_receipt": has_patch,
        "has_verification_receipt": has_verification,
        "post_patch_verification_receipt_count": sum(1 for result in post_patch_verification_results if result.receipt_refs),
    }
    if objective_satisfied:
        return {
            "progress_state": "objective_satisfied",
            "next_recommended_actions": ["sentinel_loop.finish"],
            "objective_remaining_steps": [],
            "completion_requirements": completion_requirements,
        }
    if has_patch and not has_verification:
        return {
            "progress_state": "patch_applied_needs_verification",
            "next_recommended_actions": [
                "workspace_patch.run_bounded_check",
                "read_only_research.search_text",
                "read_only_research.read_file_segment",
            ],
            "objective_remaining_steps": ["run bounded check", "verify marker changed", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_code_execution and not has_patch:
        return {
            "progress_state": "code_execution_collected",
            "next_recommended_actions": ["workspace_patch.apply_patch", "read_only_research.read_file_segment"],
            "objective_remaining_steps": ["patch workspace target", "run bounded check", "verify marker changed", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_read_only_observation and not has_code_execution:
        return {
            "progress_state": "initial_observation_collected",
            "next_recommended_actions": [
                "code_execution_sandbox.code_exec.run_profile",
                "workspace_patch.apply_patch",
                "workspace_patch.run_bounded_check",
                "read_only_research.search_text",
            ],
            "objective_remaining_steps": [
                "run bounded code execution",
                "patch workspace target",
                "run bounded check",
                "verify marker changed",
                "finish",
            ],
            "completion_requirements": completion_requirements,
        }
    return {
        "progress_state": "not_started",
        "next_recommended_actions": [
            "read_only_research.list_directory",
            "read_only_research.read_file_segment",
            "code_execution_sandbox.code_exec.run_profile",
        ],
        "objective_remaining_steps": [
            "collect initial read-only observation",
            "run bounded code execution",
            "patch workspace target",
            "run bounded check",
            "verify marker changed",
            "finish",
        ],
        "completion_requirements": completion_requirements,
    }


def _is_browser_mode(*, available_actions: tuple[str, ...], observations: list[ActionResult]) -> bool:
    if any(result.capability_id == "browser_control" for result in observations):
        return True
    return any(action.startswith("browser_control.") for action in available_actions)


def _is_real_browser_mode(*, available_actions: tuple[str, ...], observations: list[ActionResult]) -> bool:
    if any(result.capability_id == "real_browser_control" for result in observations):
        return True
    return any(action.startswith("real_browser_control.") for action in available_actions)


def _is_channel_mode(*, available_actions: tuple[str, ...], observations: list[ActionResult]) -> bool:
    if any(result.capability_id in {"bounded_channel", "channel_transport"} for result in observations):
        return True
    return any(action.startswith(("bounded_channel.", "channel_transport.", "channel.")) for action in available_actions)


def _granted_capabilities(authority: MissionAuthorityEnvelope) -> tuple[str, ...]:
    normalizer = ActionAliasNormalizer()
    names = [*authority.allowed_actions, *authority.allowed_tools, *authority.allowed_systems]
    capabilities: set[str] = set()
    for name in names:
        if not name:
            continue
        normalized = normalizer.normalize_action_name(str(name))
        capability = normalized.split(".", 1)[0]
        capabilities.add(capability)
        capabilities.update(_legacy_grant_capability_aliases(str(name), normalized))
    return tuple(sorted(capabilities))


def _legacy_grant_capability_aliases(raw_name: str, normalized_name: str) -> set[str]:
    lowered = raw_name.strip().lower()
    normalized = normalized_name.strip().lower()
    aliases: set[str] = set()
    if lowered in {"channel_send", "channel_draft_send"} or lowered.startswith("channel:"):
        aliases.add("bounded_channel")
    if lowered in {"list_directory", "search_text", "read_file_segment", "finish_exploration"}:
        aliases.add("read_only_research")
    if lowered.startswith("real_browser.") or normalized.startswith("real_browser_control."):
        aliases.add("real_browser_control")
    if lowered.startswith("browser.") or normalized.startswith("browser_control."):
        aliases.add("browser_control")
    if lowered in {"apply_patch", "run_bounded_check"} or normalized.startswith("workspace_patch."):
        aliases.add("workspace_patch")
    if lowered.startswith("code_exec.") or normalized.startswith("code_execution_sandbox."):
        aliases.add("code_execution_sandbox")
    return aliases


def _model_visible_next_actions(
    next_recommended_actions: list[str],
    *,
    skill_exposure_frame: Any,
    actionability_registry: Any,
) -> list[str]:
    visible = {item.canonical_action_name for item in skill_exposure_frame.model_visible_actions}
    ordered: list[str] = []
    for action in next_recommended_actions:
        canonical = actionability_registry.normalize_action_name(str(action))
        if canonical not in visible or canonical in ordered:
            continue
        ordered.append(canonical)
    if ordered:
        return ordered
    return [item.canonical_action_name for item in skill_exposure_frame.model_visible_actions[:1]]


def _channel_progress_guidance(
    *,
    objective_satisfied: bool,
    channel_delivery_results: list[ActionResult],
) -> dict[str, Any]:
    has_send = any(
        result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in channel_delivery_results
    )
    completion_requirements = {
        "requires_channel_send_receipt": not has_send,
        "requires_finish_action": True,
        "has_channel_send_receipt": has_send,
        "channel_send_receipt_count": sum(1 for result in channel_delivery_results if result.receipt_refs),
    }
    if objective_satisfied:
        return {
            "progress_state": "channel_delivery_succeeded_needs_finish",
            "next_recommended_actions": ["sentinel_loop.finish"],
            "objective_remaining_steps": [],
            "completion_requirements": completion_requirements,
        }
    return {
        "progress_state": "channel_send_not_started",
        "next_recommended_actions": ["bounded_channel.send_message"],
        "objective_remaining_steps": ["send one bounded message to the granted destination", "finish"],
        "completion_requirements": completion_requirements,
    }


def _browser_progress_guidance(
    *,
    objective_satisfied: bool,
    browser_results: list[ActionResult],
    browser_action_results: list[ActionResult],
    browser_assertion_results: list[ActionResult],
) -> dict[str, Any]:
    has_observation = any(
        result.operation == "browser.observe" and result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in browser_results
    )
    has_action = any(result.status in {"completed", "passed", "success"} for result in browser_action_results)
    has_assertion = any(result.status == "passed" for result in browser_assertion_results)
    completion_requirements = {
        "requires_browser_observation_receipt": not has_observation,
        "requires_browser_action_receipt": not has_action,
        "requires_browser_assertion_receipt": not has_assertion,
        "requires_finish_action": True,
        "has_browser_observation_receipt": has_observation,
        "has_browser_action_receipt": has_action,
        "has_browser_assertion_receipt": has_assertion,
    }
    if objective_satisfied:
        return {
            "progress_state": "browser_objective_satisfied",
            "next_recommended_actions": ["sentinel_loop.finish"],
            "objective_remaining_steps": [],
            "completion_requirements": completion_requirements,
        }
    if has_action and not has_assertion:
        return {
            "progress_state": "browser_action_needs_assertion",
            "next_recommended_actions": ["browser_control.browser.assert_text"],
            "objective_remaining_steps": ["assert browser fixture state changed", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_observation and not has_action:
        return {
            "progress_state": "browser_observed_needs_action",
            "next_recommended_actions": [
                "browser_control.browser.click",
                "browser_control.browser.type_text",
            ],
            "objective_remaining_steps": ["click or type using stable ref", "assert browser fixture state changed", "finish"],
            "completion_requirements": completion_requirements,
        }
    return {
        "progress_state": "browser_not_started",
        "next_recommended_actions": ["browser_control.browser.observe"],
        "objective_remaining_steps": ["observe browser fixture", "click or type using stable ref", "assert browser fixture state changed", "finish"],
        "completion_requirements": completion_requirements,
    }


def _real_browser_progress_guidance(
    *,
    objective_satisfied: bool,
    real_browser_results: list[ActionResult],
    real_browser_action_results: list[ActionResult],
    real_browser_assertion_results: list[ActionResult],
    real_browser_extraction_results: list[ActionResult],
    real_browser_verified_extraction_results: list[ActionResult],
    grounded_summary_results: list[ActionResult],
    grounded_evidence_summary: dict[str, Any],
) -> dict[str, Any]:
    has_open = any(
        result.operation == "real_browser.open" and result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in real_browser_results
    )
    has_observation = any(
        result.operation == "real_browser.observe" and result.receipt_refs and result.status in {"completed", "passed", "success"}
        for result in real_browser_results
    )
    has_action = any(result.status in {"completed", "passed", "success"} for result in real_browser_action_results)
    has_search_action = any(
        result.operation == "real_browser.search" and result.status in {"completed", "passed", "success"}
        for result in real_browser_action_results
    )
    has_assertion = any(result.status == "passed" for result in real_browser_assertion_results)
    has_extraction = any(result.status in {"completed", "passed", "success"} for result in real_browser_extraction_results)
    has_verified_extraction = any(
        result.status in {"completed", "passed", "success"}
        for result in real_browser_verified_extraction_results
    )
    has_grounded_summary = any(result.status in {"completed", "passed", "success"} for result in grounded_summary_results)
    has_relevance_assessment = bool(grounded_evidence_summary.get("objective_relevance_assessed") is True)
    has_relevant_product_evidence = bool(grounded_evidence_summary.get("has_relevant_product_evidence") is True)
    completion_requirements = {
        "requires_real_browser_open_receipt": not has_open,
        "requires_real_browser_observation_receipt": not has_observation,
        "requires_real_browser_action_receipt": not has_action,
        "requires_real_browser_assertion_or_extraction_receipt": not (has_assertion or has_extraction),
        "requires_real_browser_verified_extraction_receipt": has_extraction and not has_verified_extraction,
        "requires_grounded_evidence_summary": has_verified_extraction
        and (not has_grounded_summary or not has_relevance_assessment),
        "requires_objective_relevance_assessment": has_verified_extraction
        and has_grounded_summary
        and not has_relevance_assessment,
        "requires_relevant_product_evidence": False,
        "requires_finish_action": True,
        "has_real_browser_open_receipt": has_open,
        "has_real_browser_observation_receipt": has_observation,
        "has_real_browser_action_receipt": has_action,
        "has_real_browser_search_receipt": has_search_action,
        "has_real_browser_assertion_receipt": has_assertion,
        "has_real_browser_extraction_receipt": has_extraction,
        "has_real_browser_verified_extraction_receipt": has_verified_extraction,
        "has_grounded_evidence_summary": has_grounded_summary,
        "has_objective_relevance_assessment": has_relevance_assessment,
        "has_relevant_product_evidence": has_relevant_product_evidence,
        "under_price_condition_supported_by_visible_evidence": grounded_evidence_summary.get(
            "under_price_condition_supported_by_visible_evidence"
        ),
    }
    if objective_satisfied:
        return {
            "progress_state": "real_browser_objective_satisfied",
            "next_recommended_actions": ["sentinel_loop.finish"],
            "objective_remaining_steps": [],
            "completion_requirements": completion_requirements,
        }
    if has_verified_extraction and (not has_grounded_summary or not has_relevance_assessment):
        return {
            "progress_state": "real_browser_verified_extraction_needs_summary",
            "next_recommended_actions": ["sentinel_loop.summarize_evidence"],
            "objective_remaining_steps": ["summarize grounded extraction evidence", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_verified_extraction and has_grounded_summary and not has_relevant_product_evidence:
        next_recommended_actions = [
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
        ]
        objective_remaining_steps = [
            "search or inspect for product cards relevant to the mission objective",
            "extract/verify relevant cards",
            "summarize grounded evidence",
            "finish",
        ]
        if has_search_action:
            next_recommended_actions = [
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.search",
            ]
            objective_remaining_steps = [
                "extract or inspect the latest search-visible cards before repeating search",
                "verify any newly relevant cards",
                "summarize grounded relevance",
                "finish",
            ]
        return {
            "progress_state": "real_browser_verified_extraction_needs_relevant_products",
            "next_recommended_actions": next_recommended_actions,
            "objective_remaining_steps": objective_remaining_steps,
            "completion_requirements": completion_requirements,
        }
    if has_extraction and not has_verified_extraction:
        return {
            "progress_state": "real_browser_extraction_needs_verification",
            "next_recommended_actions": ["real_browser_control.real_browser.verify_extraction"],
            "objective_remaining_steps": ["verify extracted product cards", "summarize grounded evidence", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_action and not has_assertion:
        return {
            "progress_state": "real_browser_action_needs_assertion",
            "next_recommended_actions": [
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
                "real_browser_control.real_browser.assert_text",
            ],
            "objective_remaining_steps": ["extract/verify bounded product cards or assert browser state", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_observation and not has_action:
        return {
            "progress_state": "real_browser_observed_needs_action",
            "next_recommended_actions": [
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.extract_product_cards",
            ],
            "objective_remaining_steps": ["use browser skill action", "extract/verify browser state", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_open and not has_observation:
        return {
            "progress_state": "real_browser_opened_world_model_ready",
            "next_recommended_actions": [
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.extract_product_cards",
            ],
            "objective_remaining_steps": ["use browser world model", "search or extract product cards", "finish"],
            "completion_requirements": completion_requirements,
        }
    return {
        "progress_state": "real_browser_not_started",
        "next_recommended_actions": ["real_browser_control.real_browser.open"],
        "objective_remaining_steps": ["open bounded page", "observe stable refs", "act using stable ref", "assert state changed", "finish"],
        "completion_requirements": completion_requirements,
    }


def _browser_summary(browser_results: list[ActionResult]) -> dict[str, Any]:
    latest_observation = next((result for result in reversed(browser_results) if result.operation == "browser.observe"), None)
    latest_action = next(
        (
            result
            for result in reversed(browser_results)
            if result.operation in {"browser.click", "browser.type_text", "browser.select_option"}
        ),
        None,
    )
    latest_assertion = next((result for result in reversed(browser_results) if result.operation == "browser.assert_text"), None)
    return {
        "latest_observation": _browser_result_summary(latest_observation, include_element_count=True),
        "latest_action": _browser_result_summary(latest_action),
        "latest_assertion": _browser_result_summary(latest_assertion),
        "receipt_count": sum(len(result.receipt_refs) for result in browser_results),
    }


def _browser_result_summary(result: ActionResult | None, *, include_element_count: bool = False) -> dict[str, Any] | None:
    if result is None:
        return None
    payload: dict[str, Any] = {
        "operation": result.operation,
        "status": result.status,
        "receipt_count": len(result.receipt_refs),
        "summary": result.observation_summary[:500],
        "result_hash": result.result_hash,
    }
    if include_element_count:
        payload["element_count"] = _element_count_from_summary(result.observation_summary)
    return payload


def _real_browser_summary(real_browser_results: list[ActionResult]) -> dict[str, Any]:
    latest_open = next((result for result in reversed(real_browser_results) if result.operation == "real_browser.open"), None)
    latest_observation = next((result for result in reversed(real_browser_results) if result.operation == "real_browser.observe"), None)
    latest_action = next(
        (
            result
            for result in reversed(real_browser_results)
            if result.operation
            in {
                "real_browser.click",
                "real_browser.type_text",
                "real_browser.select_option",
                "real_browser.press_key",
                "real_browser.scroll",
                "real_browser.wait_for_text",
                "real_browser.wait_for_load",
                "real_browser.extract_text",
                "real_browser.search",
                "real_browser.inspect_result",
                "real_browser.open_result",
                "real_browser.extract_product_cards",
                "real_browser.verify_extraction",
            }
        ),
        None,
    )
    latest_assertion = next((result for result in reversed(real_browser_results) if result.operation == "real_browser.assert_text"), None)
    return {
        "latest_open": _browser_result_summary(latest_open),
        "latest_observation": _browser_result_summary(latest_observation, include_element_count=True),
        "latest_action": _browser_result_summary(latest_action),
        "latest_assertion": _browser_result_summary(latest_assertion),
        "receipt_count": sum(len(result.receipt_refs) for result in real_browser_results),
    }


def _grounded_evidence_summary(summary_results: list[ActionResult]) -> dict[str, Any]:
    latest = next((result for result in reversed(summary_results)), None)
    if latest is None:
        return {
            "present": False,
            "card_count": 0,
            "summary_hash": None,
            "objective_relevance_assessed": False,
            "has_relevant_product_evidence": False,
            "under_price_condition_supported_by_visible_evidence": "unknown",
        }
    summary = latest.context_cards.get("grounded_evidence_summary")
    card_count = 0
    objective_relevance_assessed = False
    has_relevant_product_evidence = False
    under_price_support = "unknown"
    if isinstance(summary, dict):
        try:
            card_count = int(summary.get("card_count") or 0)
        except (TypeError, ValueError):
            card_count = 0
        objective_relevance_assessed = bool(summary.get("objective_relevance_assessed") is True)
        has_relevant_product_evidence = bool(summary.get("has_relevant_product_evidence") is True)
        under_price_support = str(summary.get("under_price_condition_supported_by_visible_evidence") or "unknown")
    return {
        "present": True,
        "operation": latest.operation,
        "status": latest.status,
        "receipt_count": len(latest.receipt_refs),
        "summary_hash": latest.result_hash,
        "card_count": card_count,
        "objective_relevance_assessed": objective_relevance_assessed,
        "has_relevant_product_evidence": has_relevant_product_evidence,
        "under_price_condition_supported_by_visible_evidence": under_price_support,
    }


def _latest_real_browser_context_cards(real_browser_results: list[ActionResult]) -> dict[str, Any]:
    for result in reversed(real_browser_results):
        if result.context_cards:
            return result.context_cards
    return {}


def _browser_environment_memory(real_browser_results: list[ActionResult]) -> dict[str, Any]:
    entries = _browser_environment_entries(real_browser_results)
    if not entries:
        return {
            "present": False,
            "state_count": 0,
            "latest_state_hash": "",
            "previous_state_hash": "",
            "state_changed": False,
        }
    latest = entries[-1]
    previous = entries[-2] if len(entries) > 1 else None
    latest_state = latest["state"]
    previous_state = previous["state"] if previous is not None else None
    latest_page = _state_section(latest_state, "page_state")
    previous_page = _state_section(previous_state, "page_state") if previous_state else {}
    latest_extraction = _state_section(latest_state, "extraction_graph")
    latest_session = _state_section(latest_state, "session_graph")
    latest_recoverable = next((entry for entry in reversed(entries) if entry["result"].recoverable), None)
    return {
        "present": True,
        "state_count": len(entries),
        "latest_state_hash": latest["state_hash"],
        "previous_state_hash": previous["state_hash"] if previous is not None else "",
        "state_changed": bool(previous is not None and previous["state_hash"] != latest["state_hash"]),
        "latest_page_kind_guess": str(latest_page.get("page_kind_guess") or ""),
        "latest_stable_ref_count": _safe_int(latest_page.get("stable_ref_count")),
        "stable_ref_count_delta": _safe_int(latest_page.get("stable_ref_count"))
        - _safe_int(previous_page.get("stable_ref_count")),
        "latest_product_or_result_candidate_count": _safe_int(
            latest_extraction.get("product_or_result_candidate_count")
        ),
        "latest_relevant_product_candidate_count": _safe_int(
            latest_extraction.get("relevant_product_candidate_count")
        ),
        "latest_cookie_count": _safe_int(latest_session.get("cookie_count"))
        or _safe_len(latest_session.get("cookies")),
        "latest_storage_key_count": _safe_int(latest_session.get("storage_key_count"))
        or _safe_len(latest_session.get("storage_keys")),
        "recommended_recovery_skills": [
            str(skill)
            for skill in latest_state.get("recommended_model_skills", [])
            if isinstance(skill, str)
        ][:6],
        "latest_recoverable_state_hash": latest_recoverable["state_hash"] if latest_recoverable else "",
        "latest_recoverable_failure_code": latest_recoverable["result"].failure_code if latest_recoverable else "",
    }


def _browser_environment_entries(real_browser_results: list[ActionResult]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for result in real_browser_results:
        cards = result.context_cards if isinstance(result.context_cards, dict) else {}
        state = _safe_browser_environment_state(cards.get("browser_environment_state"))
        if not state:
            continue
        state_hash = str(cards.get("browser_environment_state_hash") or stable_hash(state))
        entries.append({"result": result, "state": state, "state_hash": state_hash})
    return entries


def _safe_browser_environment_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _drop_raw_browser_values(value)


def _drop_raw_browser_values(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in {"value", "cookie_value", "storage_value", "session_token"}:
                continue
            if lowered.startswith("raw_") and lowered not in {"raw_material_persisted"}:
                continue
            safe[key_text] = _drop_raw_browser_values(child)
        return safe
    if isinstance(value, list):
        return [_drop_raw_browser_values(item) for item in value]
    return value


def _state_section(state: dict[str, Any] | None, name: str) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    section = state.get(name)
    return section if isinstance(section, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _top_stable_refs(cards: dict[str, Any]) -> list[dict[str, Any]]:
    frame = cards.get("browser_decision_frame")
    if isinstance(frame, dict):
        top_refs = frame.get("top_refs")
        if isinstance(top_refs, list):
            return top_refs[:12]
    world = cards.get("browser_world_model")
    if isinstance(world, dict):
        refs = world.get("stable_refs")
        if isinstance(refs, list):
            return refs[:12]
    return []


def _top_action_candidates(cards: dict[str, Any]) -> list[dict[str, Any]]:
    frame = cards.get("browser_decision_frame")
    if not isinstance(frame, dict):
        return []
    candidates = frame.get("candidate_actions")
    return candidates[:12] if isinstance(candidates, list) else []


def _top_link_candidates(cards: dict[str, Any]) -> list[str]:
    world = cards.get("browser_world_model")
    if not isinstance(world, dict):
        return []
    refs = world.get("link_refs")
    return refs[:12] if isinstance(refs, list) else []


def _search_like_controls(cards: dict[str, Any]) -> list[str]:
    world = cards.get("browser_world_model")
    if not isinstance(world, dict):
        return []
    refs = world.get("search_like_refs")
    return refs[:12] if isinstance(refs, list) else []


def _blocker_signals(cards: dict[str, Any]) -> list[str]:
    frame = cards.get("browser_decision_frame")
    if isinstance(frame, dict):
        blockers = frame.get("blockers")
        if isinstance(blockers, list):
            return blockers
    world = cards.get("browser_world_model")
    if not isinstance(world, dict):
        return []
    blockers: list[str] = []
    for key in ("modal_or_consent_signals", "captcha_or_login_signals", "dynamic_loading_signals"):
        value = world.get(key)
        if isinstance(value, list):
            blockers.extend(str(item) for item in value)
    return blockers


def _allowed_action_schema(*, real_browser_mode: bool) -> dict[str, Any]:
    if not real_browser_mode:
        return {}
    return {
        "capability_id": "real_browser_control",
        "operation": "real_browser.open | real_browser.observe | real_browser.search | real_browser.inspect_result | real_browser.open_result | real_browser.extract_product_cards | real_browser.verify_extraction",
        "params": {"query": "bounded search query when searching", "ref": "stable result ref when inspecting/opening"},
        "internal_runtime_note": "click/type/select/press/wait/scroll are internal fallback primitives, not the primary model-facing browser path.",
    }


def _element_count_from_summary(summary: str) -> int:
    parts = summary.split()
    for index, part in enumerate(parts):
        if part == "with" and index + 1 < len(parts):
            try:
                return int(parts[index + 1])
            except ValueError:
                return 0
    return 0


def _channel_summary(channel_results: list[ActionResult]) -> dict[str, Any]:
    latest_send = next((result for result in reversed(channel_results) if result.operation == "send_message"), None)
    return {
        "latest_send": _channel_result_summary(latest_send),
        "send_count": sum(1 for result in channel_results if result.operation == "send_message" and result.receipt_refs),
        "receipt_count": sum(len(result.receipt_refs) for result in channel_results),
    }


def _channel_result_summary(result: ActionResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "operation": result.operation,
        "status": result.status,
        "delivery_status": "sent" if result.status in {"completed", "passed", "success"} and result.receipt_refs else result.status,
        "delivery_receipt_ref": result.receipt_refs[0] if result.receipt_refs else None,
        "delivery_ref_hash": _delivery_ref_hash_from_summary(result.observation_summary),
        "receipt_count": len(result.receipt_refs),
        "finalgate_count": len(result.finalgate_refs),
        "summary": result.observation_summary[:500],
        "result_hash": result.result_hash,
    }


def _delivery_ref_hash_from_summary(summary: str) -> str | None:
    marker = "delivery_ref_hash="
    if marker not in summary:
        return None
    value = summary.split(marker, 1)[1].split(".", 1)[0].strip()
    return value or None


def _profile_id_from_summary(summary: str) -> str:
    prefix = "code execution profile "
    if not summary.startswith(prefix):
        return "unknown"
    remainder = summary[len(prefix) :]
    return remainder.split(" ", 1)[0] or "unknown"


__all__ = ["DecisionContextCompiler"]
