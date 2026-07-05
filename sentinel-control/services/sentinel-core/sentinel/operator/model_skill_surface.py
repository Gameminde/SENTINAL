from __future__ import annotations

from typing import Any


MODEL_SKILL_ORDER = (
    "read",
    "create_file",
    "patch",
    "run_check",
    "browse_search",
    "extract",
    "send_message",
    "spawn_worker",
    "remember",
    "finish",
)

_ACTION_TO_MODEL_SKILL = {
    "read_only_research.list_directory": "read",
    "read_only_research.search_text": "read",
    "read_only_research.read_file_segment": "read",
    "read_only_research.finish_exploration": "finish",
    "workspace_patch.create_file": "create_file",
    "workspace_patch.apply_patch": "patch",
    "workspace_patch.run_bounded_check": "run_check",
    "code_execution_sandbox.code_exec.run_profile": "run_check",
    "code_execution_sandbox.code_exec.inspect_result": "run_check",
    "bounded_channel.send_message": "send_message",
    "browser_control.browser.observe": "browse_search",
    "browser_control.browser.assert_text": "extract",
    "real_browser_control.real_browser.open": "browse_search",
    "real_browser_control.real_browser.observe": "browse_search",
    "real_browser_control.real_browser.search": "browse_search",
    "real_browser_control.real_browser.inspect_result": "browse_search",
    "real_browser_control.real_browser.open_result": "browse_search",
    "real_browser_control.real_browser.extract_product_cards": "extract",
    "real_browser_control.real_browser.verify_extraction": "extract",
    "real_browser_control.real_browser.extract_text": "extract",
    "real_browser_control.real_browser.assert_text": "extract",
    "worker_fleet.spawn_worker": "spawn_worker",
    "sentinel_loop.summarize_evidence": "finish",
    "sentinel_loop.finish": "finish",
}

_HARD_STOP_MARKERS = {
    "account": "account_mutation",
    "checkout": "checkout",
    "contact_supplier": "contact_supplier",
    "credential": "credential_access",
    "login": "login",
    "password": "credential_access",
    "payment": "payment",
    "secret": "credential_access",
    "spend": "payment",
}


def compile_model_skill_surface(
    *,
    model_visible_actions: list[str] | tuple[str, ...],
    recommended_actions: list[str] | tuple[str, ...],
    hidden_internal_actions: list[str] | tuple[str, ...] = (),
    hard_stop_boundaries: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Compile the simple model-facing skill language.

    Canonical action names remain the runtime language; this frame gives the
    model a compact product vocabulary and keeps the canonical mapping out of
    the primary model surface.
    """

    visible_actions = _dedupe(str(action) for action in model_visible_actions if str(action))
    hidden_actions = _dedupe(str(action) for action in hidden_internal_actions if str(action))
    skill_action_map = _skill_action_map(visible_actions)
    visible_skills = _ordered(skill_action_map)
    recommended_skills = _recommended_skills(
        recommended_actions=recommended_actions,
        visible_skills=visible_skills,
    )
    locked_or_hidden = _locked_or_hidden_actions(
        visible_actions=visible_actions,
        hidden_actions=hidden_actions,
    )
    boundaries = _dedupe(
        [
            *[str(boundary) for boundary in hard_stop_boundaries if str(boundary)],
            *_hard_stop_boundaries_for_actions(locked_or_hidden),
        ]
    )
    return {
        "frame_version": "model_skill_surface_v1",
        "primary_model_surface": "model_visible_skills",
        "primary_model_language": "simple_mission_skills",
        "action_envelope_language": "internal_runtime_only",
        "model_visible_skills": visible_skills,
        "recommended_next_skills": recommended_skills,
        "primary_recommended_skill": recommended_skills[0] if recommended_skills else None,
        "runtime_internal_action_map": skill_action_map,
        "compatibility_canonical_actions": visible_actions,
        "locked_or_hidden_actions": locked_or_hidden,
        "hard_stop_boundaries": boundaries,
        "invariant": "model_uses_simple_skills_action_envelope_stays_internal",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def model_skill_for_action(action_name: str) -> str | None:
    return _ACTION_TO_MODEL_SKILL.get(action_name)


def _skill_action_map(actions: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for action in actions:
        skill = model_skill_for_action(action)
        if skill is None:
            continue
        mapping.setdefault(skill, action)
    return {skill: mapping[skill] for skill in MODEL_SKILL_ORDER if skill in mapping}


def _recommended_skills(
    *,
    recommended_actions: list[str] | tuple[str, ...],
    visible_skills: list[str],
) -> list[str]:
    recommended: list[str] = []
    visible = set(visible_skills)
    for action in recommended_actions:
        skill = model_skill_for_action(str(action))
        if skill in visible:
            recommended.append(skill)
    if recommended:
        return _ordered({skill: skill for skill in recommended})
    return visible_skills[:1]


def _locked_or_hidden_actions(*, visible_actions: list[str], hidden_actions: list[str]) -> list[str]:
    unsupported = [
        action
        for action in visible_actions
        if model_skill_for_action(action) is None or _hard_stop_boundaries_for_actions([action])
    ]
    return _dedupe([*hidden_actions, *unsupported])


def _hard_stop_boundaries_for_actions(actions: list[str]) -> list[str]:
    boundaries: list[str] = []
    for action in actions:
        lowered = action.lower()
        boundaries.extend(boundary for marker, boundary in _HARD_STOP_MARKERS.items() if marker in lowered)
    return _dedupe(boundaries)


def _ordered(mapping: dict[str, Any]) -> list[str]:
    return [skill for skill in MODEL_SKILL_ORDER if skill in mapping]


def _dedupe(items: Any) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


__all__ = ["compile_model_skill_surface", "model_skill_for_action"]
