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
        objective_satisfied = _objective_satisfied(
            code_execution_results=code_execution_results,
            workspace_patch_results=workspace_patch_results,
            workspace_verification_results=workspace_verification_results,
            read_only_verification_results=read_only_verification_results,
        )
        progress_guidance = _progress_guidance(
            objective_satisfied=objective_satisfied,
            code_execution_results=code_execution_results,
            workspace_patch_results=workspace_patch_results,
            workspace_verification_results=workspace_verification_results,
            read_only_verification_results=read_only_verification_results,
        )
        return {
            "mission_id": mission_id,
            "mission_objective": mission_objective,
            "available_actions": list(available_actions),
            "objective_satisfied": objective_satisfied,
            "finish_available": objective_satisfied,
            "recommended_next_action": "sentinel_loop.finish" if objective_satisfied else None,
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
        }


def _objective_satisfied(
    *,
    code_execution_results: list[ActionResult],
    workspace_patch_results: list[ActionResult],
    workspace_verification_results: list[ActionResult],
    read_only_verification_results: list[ActionResult],
) -> bool:
    has_code_execution = any(result.receipt_refs and result.status in {"passed", "completed"} for result in code_execution_results)
    has_patch = any(result.receipt_refs and result.status in {"completed", "passed"} for result in workspace_patch_results)
    has_verification = any(
        result.receipt_refs and result.status in {"completed", "passed"}
        for result in [*workspace_verification_results, *read_only_verification_results]
    )
    return has_code_execution and has_patch and has_verification


def _progress_guidance(
    *,
    objective_satisfied: bool,
    code_execution_results: list[ActionResult],
    workspace_patch_results: list[ActionResult],
    workspace_verification_results: list[ActionResult],
    read_only_verification_results: list[ActionResult],
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
        for result in [*workspace_verification_results, *read_only_verification_results]
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


def _profile_id_from_summary(summary: str) -> str:
    prefix = "code execution profile "
    if not summary.startswith(prefix):
        return "unknown"
    remainder = summary[len(prefix) :]
    return remainder.split(" ", 1)[0] or "unknown"


__all__ = ["DecisionContextCompiler"]
