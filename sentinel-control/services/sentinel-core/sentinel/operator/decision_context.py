from __future__ import annotations

from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionResult


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
            if result.operation == "real_browser.extract_text" and result.status in {"completed", "passed", "success"} and result.receipt_refs
        ]
        real_browser_cards = _latest_real_browser_context_cards(real_browser_results)
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
            objective_satisfied = bool(real_browser_assertion_results or real_browser_extraction_results)
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
        return {
            "mission_id": mission_id,
            "mission_objective": mission_objective,
            "available_actions": list(available_actions),
            "objective_satisfied": objective_satisfied,
            "finish_available": objective_satisfied,
            "recommended_next_action": (
                "sentinel_loop.finish"
                if objective_satisfied
                else (progress_guidance["next_recommended_actions"][0] if progress_guidance["next_recommended_actions"] else None)
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
                "model_calls": max(max_model_calls - model_calls_used, 0),
                "material_actions": max(max_material_actions - material_actions_used, 0),
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
            "browser_world_model_summary": real_browser_cards.get("browser_world_model_summary") if real_browser_mode else {},
            "browser_decision_frame": real_browser_cards.get("browser_decision_frame") if real_browser_mode else {},
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
    has_assertion = any(result.status == "passed" for result in real_browser_assertion_results)
    has_extraction = any(result.status in {"completed", "passed", "success"} for result in real_browser_extraction_results)
    completion_requirements = {
        "requires_real_browser_open_receipt": not has_open,
        "requires_real_browser_observation_receipt": not has_observation,
        "requires_real_browser_action_receipt": not has_action,
        "requires_real_browser_assertion_or_extraction_receipt": not (has_assertion or has_extraction),
        "requires_finish_action": True,
        "has_real_browser_open_receipt": has_open,
        "has_real_browser_observation_receipt": has_observation,
        "has_real_browser_action_receipt": has_action,
        "has_real_browser_assertion_receipt": has_assertion,
        "has_real_browser_extraction_receipt": has_extraction,
    }
    if objective_satisfied:
        return {
            "progress_state": "real_browser_objective_satisfied",
            "next_recommended_actions": ["sentinel_loop.finish"],
            "objective_remaining_steps": [],
            "completion_requirements": completion_requirements,
        }
    if has_action and not has_assertion:
        return {
            "progress_state": "real_browser_action_needs_assertion",
            "next_recommended_actions": [
                "real_browser_control.real_browser.assert_text",
                "real_browser_control.real_browser.extract_text",
                "real_browser_control.real_browser.wait_for_text",
            ],
            "objective_remaining_steps": ["assert or extract bounded real browser state", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_observation and not has_action:
        return {
            "progress_state": "real_browser_observed_needs_action",
            "next_recommended_actions": [
                "real_browser_control.real_browser.type_text",
                "real_browser_control.real_browser.click",
                "real_browser_control.real_browser.select_option",
                "real_browser_control.real_browser.press_key",
                "real_browser_control.real_browser.extract_text",
            ],
            "objective_remaining_steps": ["act using stable ref", "assert or extract browser state", "finish"],
            "completion_requirements": completion_requirements,
        }
    if has_open and not has_observation:
        return {
            "progress_state": "real_browser_opened_world_model_ready",
            "next_recommended_actions": [
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.extract_text",
            ],
            "objective_remaining_steps": ["use browser world model", "act or extract with stable refs", "finish"],
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


def _latest_real_browser_context_cards(real_browser_results: list[ActionResult]) -> dict[str, Any]:
    for result in reversed(real_browser_results):
        if result.context_cards:
            return result.context_cards
    return {}


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
        "operation": "real_browser.open | real_browser.observe | real_browser.click | real_browser.type_text | real_browser.press_key | real_browser.wait_for_text | real_browser.wait_for_load | real_browser.scroll | real_browser.extract_text | real_browser.assert_text",
        "params": {"ref": "stable ref when needed", "text": "bounded text when needed"},
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
