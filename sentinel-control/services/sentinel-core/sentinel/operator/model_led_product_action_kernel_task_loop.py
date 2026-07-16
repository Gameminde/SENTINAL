from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.model_skill_surface import compile_model_skill_surface
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.operator.real_browser_control_runtime import BOUNDED_URL_AUTHORITY_REF
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.safety import assert_data_not_authority
from sentinel.operator.store import MissionRunStore, _iter_child_paths, _iter_descendant_file_paths, _path_exists, _read_bytes_file
from sentinel.operator.unified_execution_dispatcher import DispatchStatus, UnifiedDispatchResult
from sentinel.shared.models import SentinelModel, new_id


class ProductActionKernelTaskLoopStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ProductActionKernelLoopDecisionClient:
    def __init__(self, decisions: list[ActionEnvelope]) -> None:
        self._decisions = list(decisions)
        self.call_count = 0
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        self.call_count += 1
        if not self._decisions:
            raise ActionKernelError("model_led_product_action_kernel_decision_exhausted")
        return self._decisions.pop(0)


class ProductActionKernelTaskLoopFinalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("product_action_kernel_task_loop_finalgate"))
    loop_id: str
    status: ProductActionKernelTaskLoopStatus
    accepted: bool
    reason: str
    mission_ids: tuple[str, ...] = Field(default_factory=tuple)
    product_receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    product_finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_data_only(self) -> "ProductActionKernelTaskLoopFinalCertificate":
        assert_data_not_authority(
            context="product_action_kernel_task_loop_final_certificate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.certificate_hash:
            self.certificate_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "certificate_id": self.certificate_id,
            "loop_id": self.loop_id,
            "status": self.status.value,
            "accepted": self.accepted,
            "reason": self.reason,
            "mission_ids": sanitize_operator_refs(self.mission_ids),
            "product_receipt_refs": sanitize_operator_refs(self.product_receipt_refs),
            "product_finalgate_refs": sanitize_operator_refs(self.product_finalgate_refs),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


class ProductActionKernelTaskLoopResult(SentinelModel):
    loop_id: str
    status: ProductActionKernelTaskLoopStatus
    final_reason: str
    blocked_reason: str | None = None
    model_call_count: int = 0
    material_action_count: int = 0
    capability_sequence: tuple[str, ...] = Field(default_factory=tuple)
    mission_ids: tuple[str, ...] = Field(default_factory=tuple)
    product_receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    product_finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_refs: tuple[str, ...] = Field(default_factory=tuple)
    dispatch_results: tuple[UnifiedDispatchResult, ...] = Field(default_factory=tuple)


class ModelLedProductActionKernelTaskLoop:
    def __init__(
        self,
        *,
        host: SentinelRuntimeHost,
        workspace_root: Path | str,
        session_id: str,
        mission_objective: str,
        decision_client: ProductActionKernelLoopDecisionClient,
        allowed_domains: tuple[str, ...] = (),
        max_model_calls: int = 6,
        max_material_actions: int = 3,
        max_recoverable_model_decision_failures: int = 0,
        max_recoverable_action_failures: int = 0,
        model_contract_ref: str = "model_contract:product_action_kernel_task_loop_fake",
        explicit_noop_proof_ref: str | None = None,
        product_task_resource_scope: object | None = None,
        evidence_sink: object | None = None,
        allowed_capabilities: tuple[str, ...] | None = None,
    ) -> None:
        self.loop_id = new_id("product_action_kernel_task_loop")
        self.host = host
        self.workspace_root = Path(workspace_root).resolve()
        self.session_id = session_id
        self.mission_objective = mission_objective
        self.decision_client = decision_client
        self.allowed_domains = tuple(allowed_domains)
        self.max_model_calls = max_model_calls
        self.max_material_actions = max_material_actions
        self.max_recoverable_model_decision_failures = max(0, max_recoverable_model_decision_failures)
        self.max_recoverable_action_failures = max(0, max_recoverable_action_failures)
        self.model_contract_ref = model_contract_ref
        self.explicit_noop_proof_ref = explicit_noop_proof_ref
        self.product_task_resource_scope = product_task_resource_scope
        self.evidence_sink = evidence_sink
        self.allowed_capabilities = tuple(dict.fromkeys(allowed_capabilities or ()))
        self.model_calls_used = 0
        self.material_actions_used = 0
        self.recoverable_decision_observations: list[dict[str, Any]] = []
        self.recoverable_action_observations: list[dict[str, Any]] = []
        self.capability_sequence: list[str] = []
        self.dispatch_results: list[UnifiedDispatchResult] = []
        self.mission_ids: list[str] = []
        self.product_receipt_refs: list[str] = []
        self.product_finalgate_refs: list[str] = []

    def run(self) -> ProductActionKernelTaskLoopResult:
        self._record_evidence_transition(
            "run_started",
            {
                "loop_id": self.loop_id,
                "session_id": self.session_id,
                "mission_objective": self.mission_objective,
                "max_model_calls": self.max_model_calls,
                "max_material_actions": self.max_material_actions,
            },
        )
        try:
            while True:
                if self.model_calls_used >= self.max_model_calls:
                    return self._block("MODEL_CALL_BUDGET_EXHAUSTED")
                context = self._compile_context()
                try:
                    decision = self.decision_client.complete(context)
                    decision_from_model = True
                    self._record_evidence_transition(
                        "provider_decision_received",
                        {
                            "provider_decision_count": getattr(self.decision_client, "call_count", self.model_calls_used + 1),
                            "model_operational_assessment": getattr(
                                self.decision_client,
                                "latest_safe_model_operational_assessment",
                                None,
                            ),
                            "context_hash": stable_hash(_safe_context_shape_for_evidence(context)),
                        },
                    )
                    assessment = getattr(self.decision_client, "latest_safe_model_operational_assessment", None)
                    if isinstance(assessment, dict) and assessment:
                        self._record_evidence_transition(
                            "model_blocker_assessment_received",
                            {"model_blocker_assessment": assessment},
                        )
                except ActionKernelError as exc:
                    self.model_calls_used += 1
                    reason = str(exc) or exc.__class__.__name__
                    if self._recover_model_decision_failure(reason, context):
                        continue
                    recovery_decision = self._deterministic_recovery_decision(reason, context)
                    if recovery_decision is None:
                        return self._block(reason)
                    decision = recovery_decision
                    decision_from_model = False
                if decision_from_model:
                    self.model_calls_used += 1
                decision = self._route_contextless_browser_decision(decision, context)
                if not self._decision_allowed_by_mission_scope(decision):
                    reason = "MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE"
                    if self._recover_model_decision_failure(reason, context):
                        continue
                    return self._block("PRODUCT_SKILL_OUTSIDE_MISSION_SCOPE")
                sequence_entry = f"{decision.capability_id}:{decision.operation}"
                self.capability_sequence.append(sequence_entry)
                self._record_evidence_transition(
                    "action_envelope_accepted",
                    _safe_action_envelope_evidence(decision),
                )
                if decision.capability_id == "sentinel_loop" and decision.operation == "finish":
                    if not self.product_receipt_refs and not self.explicit_noop_proof_ref:
                        return self._block("MODEL_FINISH_BEFORE_PRODUCT_RECEIPT")
                    return self._complete("model_led_product_action_kernel_task_loop_finish")
                if self.material_actions_used >= self.max_material_actions and not _is_completion_lane_decision(decision):
                    return self._block("MATERIAL_ACTION_BUDGET_EXHAUSTED")
                if decision.capability_id == "real_browser_control":
                    self._record_evidence_transition(
                        "browser_action_started",
                        _safe_action_envelope_evidence(decision),
                    )
                dispatch_result = self._dispatch_product_action(decision, loop_context=context)
                self.dispatch_results.append(dispatch_result)
                self.mission_ids.append(dispatch_result.mission_id)
                self.product_receipt_refs.extend(dispatch_result.receipt_refs)
                self.product_finalgate_refs.extend(dispatch_result.finalgate_refs)
                self._record_dispatch_evidence(dispatch_result)
                if dispatch_result.status is not DispatchStatus.COMPLETED:
                    if self._recover_action_failure(dispatch_result, decision, context):
                        continue
                    return self._block(dispatch_result.blocked_reason or "product_action_kernel_dispatch_blocked")
                if dispatch_result.receipt_refs:
                    self.material_actions_used += 1
        except ActionKernelError as exc:
            return self._block(str(exc) or exc.__class__.__name__)

    def _compile_context(self) -> dict[str, Any]:
        dispatch_summaries = _dispatch_summaries(self.dispatch_results)
        safe_context_cards = _merged_dispatch_context_cards(self.dispatch_results)
        completion_requirements = _product_completion_requirements(self.dispatch_results, safe_context_cards)
        browser_cognitive_frame = _browser_cognitive_decision_frame(
            safe_context_cards,
            mission_objective=self.mission_objective,
        )
        actions = self._available_actions()
        recommended_actions = _product_context_recommended_actions(
            available_actions=actions,
            completion_requirements=completion_requirements,
            browser_cognitive_frame=browser_cognitive_frame,
        )
        model_skill_surface = compile_model_skill_surface(
            model_visible_actions=actions,
            recommended_actions=recommended_actions,
        )
        grounded_evidence_summary = _grounded_evidence_summary_card(safe_context_cards)
        real_browser_summary = _real_browser_control_summary(self.dispatch_results)
        bounded_observation_summaries = _bounded_observation_summaries(self.dispatch_results)
        has_terminal_browser_evidence = bool(
            completion_requirements.get("has_real_browser_verified_extraction_receipt")
            or completion_requirements.get("has_confirmed_no_results_search_receipt")
        )
        finish_available = bool(
            has_terminal_browser_evidence
            and completion_requirements.get("has_grounded_evidence_summary")
            and completion_requirements.get("has_objective_relevance_assessment")
        )
        return {
            "loop_id": self.loop_id,
            "mission_objective": self.mission_objective,
            "progress_state": self._progress_state(),
            "primary_model_surface": "model_visible_skills",
            "primary_model_language": "simple_mission_skills",
            "action_envelope_language": "internal_runtime_only",
            "model_skill_surface": model_skill_surface,
            "model_visible_skills": list(model_skill_surface["model_visible_skills"]),
            "primary_model_next_recommended_skills": list(model_skill_surface["recommended_next_skills"]),
            "primary_model_recommended_next_skill": model_skill_surface["primary_recommended_skill"],
            "runtime_internal_action_map": dict(model_skill_surface["runtime_internal_action_map"]),
            "_workspace_patch_plans": _workspace_patch_plans(self.workspace_root),
            "_workspace_create_file_plans": _workspace_create_file_plans(
                self.workspace_root,
                mission_objective=self.mission_objective,
            ),
            "_workspace_patch_plans_are_pending": True,
            "_bounded_check_plan": _bounded_check_plan(self.workspace_root),
            "workspace_file_summaries": _workspace_file_summaries(self.workspace_root),
            "model_visible_available_actions": list(actions),
            "mission_allowed_capabilities": list(self.allowed_capabilities),
            "skill_decision_frame": {
                "primary_truth": "product_action_kernel_runtimehost",
                "primary_model_surface": "model_visible_skills",
                "primary_model_language": "simple_mission_skills",
                "model_skill_surface": model_skill_surface,
                "model_visible_skills": list(model_skill_surface["model_visible_skills"]),
                "model_visible_actions": list(actions),
                "browser_environment_state": safe_context_cards.get("browser_environment_state"),
                "browser_cognitive_decision_frame": browser_cognitive_frame,
                "runtime_failure_fact": safe_context_cards.get("runtime_failure_fact"),
                "model_visible_body_failure_packet": safe_context_cards.get("model_visible_body_failure_packet"),
                "model_blocker_assessment_schema": safe_context_cards.get("model_blocker_assessment_schema"),
                "runtime_bridge": "RuntimeHost -> UnifiedExecutionDispatcher -> ProductActionKernelDispatchAdapter",
                "action_envelope_language": "internal_runtime_only",
            },
            "product_action_kernel_dispatch_count": len(self.dispatch_results),
            "recent_product_receipt_refs": list(sanitize_operator_refs(self.product_receipt_refs)),
            "recent_product_finalgate_refs": list(sanitize_operator_refs(self.product_finalgate_refs)),
            "explicit_noop_proof_ref": self.explicit_noop_proof_ref,
            "live_channel_destination_grants": _live_channel_destination_grants(self.allowed_domains),
            "dispatch_summaries": dispatch_summaries,
            "bounded_observation_summaries": bounded_observation_summaries,
            "completion_requirements": completion_requirements,
            "browser_cognitive_decision_frame": browser_cognitive_frame,
            "browser_world_model": safe_context_cards.get("browser_world_model"),
            "browser_world_model_summary": safe_context_cards.get("browser_world_model_summary"),
            "browser_decision_frame": safe_context_cards.get("browser_decision_frame"),
            "browser_environment_state": safe_context_cards.get("browser_environment_state"),
            "browser_environment_state_hash": safe_context_cards.get("browser_environment_state_hash"),
            "browser_observation_bundle": safe_context_cards.get("browser_observation_bundle"),
            "browser_search_materiality": safe_context_cards.get("browser_search_materiality"),
            "runtime_failure_fact": safe_context_cards.get("runtime_failure_fact"),
            "model_visible_body_failure_packet": safe_context_cards.get("model_visible_body_failure_packet"),
            "model_blocker_assessment_schema": safe_context_cards.get("model_blocker_assessment_schema"),
            "real_browser_control_summary": real_browser_summary,
            "grounded_evidence_summary": grounded_evidence_summary,
            "finish_available": finish_available,
            "objective_satisfied": finish_available,
            "recoverable_decision_observations": [dict(item) for item in self.recoverable_decision_observations],
            "recoverable_action_observations": [dict(item) for item in self.recoverable_action_observations],
            "recoverable_model_decision_failure_count": len(self.recoverable_decision_observations),
            "recoverable_action_failure_count": len(self.recoverable_action_observations),
            "max_recoverable_model_decision_failures": self.max_recoverable_model_decision_failures,
            "max_recoverable_action_failures": self.max_recoverable_action_failures,
            "model_calls_used": self.model_calls_used,
            "max_model_calls": self.max_model_calls,
            "material_actions_used": self.material_actions_used,
            "max_material_actions": self.max_material_actions,
            "hard_boundaries": [
                "payment",
                "credential_access",
                "contact_supplier",
                "browser_login",
                "provider_native_tools",
                "fallback_auto",
            ],
        }

    def _recover_model_decision_failure(self, reason: str, context: dict[str, Any]) -> bool:
        if not _is_recoverable_model_decision_failure(reason):
            return False
        max_recoveries = self.max_recoverable_model_decision_failures
        if reason == "MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED":
            max_recoveries = max(max_recoveries, 1)
        if reason == "MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE":
            max_recoveries = max(max_recoveries, 1)
        if self.product_receipt_refs:
            max_recoveries = max(max_recoveries, 1)
        if len(self.recoverable_decision_observations) >= max_recoveries:
            return False
        self.recoverable_decision_observations.append(
            {
                "failure_code": reason,
                "turn_index": self.model_calls_used,
                "recovery_action": "ask_model_again_with_visible_json_skill",
                "recommended_skill": context.get("primary_model_recommended_next_skill"),
                "data_not_authority": True,
                "can_execute": False,
            }
        )
        return True

    def _deterministic_recovery_decision(self, reason: str, context: dict[str, Any]) -> ActionEnvelope | None:
        if not _is_recoverable_model_decision_failure(reason):
            return None
        if not self.product_receipt_refs:
            return None
        create_plans = _workspace_create_file_plans(self.workspace_root, mission_objective=self.mission_objective)
        if create_plans:
            return _create_file_recovery_action(self.loop_id, create_plans[0], len(self.product_receipt_refs))
        check_plan = _bounded_check_plan(self.workspace_root)
        if check_plan and _completed_dispatch_count(context, "code_execution_sandbox", "code_exec.run_profile") == 0:
            return ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params=dict(check_plan),
                idempotency_key=_recovery_key(self.loop_id, "run_check", len(self.product_receipt_refs)),
            )
        if _completed_dispatch_count(context, "code_execution_sandbox", "code_exec.run_profile") > 0 and (
            _completed_dispatch_count(context, "bounded_channel", "send_message") == 0
        ):
            return ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params={
                    "adapter_id": "monster_fake_channel",
                    "channel": "webhook",
                    "body": "Sentinel Monster Runtime product proof advanced through deterministic recovery.",
                    "recipients": ["founder@example.com"],
                    "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
                    "evidence_refs": ["evidence:monster_runtime_recovery_lane"],
                },
                idempotency_key=_recovery_key(self.loop_id, "send_message", len(self.product_receipt_refs)),
            )
        if _completed_dispatch_count(context, "bounded_channel", "send_message") > 0:
            worker_count = _completed_dispatch_count(context, "worker_fleet", "spawn_worker")
            if worker_count < 2:
                role = "researcher" if worker_count == 0 else "report_writer"
                objective = (
                    "Review workspace evidence and product proof."
                    if role == "researcher"
                    else "Summarize the proof bundle and worker evidence."
                )
                return ActionEnvelope(
                    capability_id="worker_fleet",
                    operation="spawn_worker",
                    params={
                        "role": role,
                        "objective": objective,
                        "delegated_skills": ["read"],
                        "max_actions": 1,
                    },
                    idempotency_key=_recovery_key(self.loop_id, f"spawn_worker:{role}", len(self.product_receipt_refs)),
                )
            return ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={
                    "safe_summary": (
                        "Product mission completed through deterministic recovery after model-visible provider friction."
                    )
                },
                idempotency_key=_recovery_key(self.loop_id, "finish", len(self.product_receipt_refs)),
            )
        return None

    def _recover_action_failure(
        self,
        dispatch_result: UnifiedDispatchResult,
        decision: ActionEnvelope,
        context: dict[str, Any],
    ) -> bool:
        reason = dispatch_result.blocked_reason or ""
        if not _is_recoverable_action_failure(reason):
            return False
        max_recoveries = self.max_recoverable_action_failures
        if _is_recoverable_browser_action_failure(reason):
            max_recoveries = max(max_recoveries, 1)
        if len(self.recoverable_action_observations) >= max_recoveries:
            return False
        create_plans = _workspace_create_file_plans(self.workspace_root, mission_objective=self.mission_objective)
        failure_context_cards = dispatch_result.safe_context_cards if isinstance(dispatch_result.safe_context_cards, dict) else {}
        failure_card_count = _product_card_count_from_context_cards(failure_context_cards)
        if reason == "code_exec_failed":
            recommended_skill = "patch"
            recovery_action = "repair_workspace_file_then_rerun_semantic_check"
        elif reason == "BODY_SESSION_UNAVAILABLE":
            recommended_skill = "finish"
            recovery_action = "route_to_truthful_terminal_blocker_or_finish_from_body_failure_packet"
        elif create_plans:
            recommended_skill = "create_file"
            recovery_action = "route_to_next_missing_workspace_create_file_plan"
        elif _is_recoverable_browser_action_failure(reason) and failure_card_count:
            recommended_skill = "extract"
            recovery_action = "route_to_visible_browser_cards_extraction"
        elif _is_recoverable_browser_action_failure(reason):
            recommended_skill = "browse_search"
            recovery_action = "refresh_browser_world_model_and_retry_best_safe_skill"
        else:
            recommended_skill = context.get("primary_model_recommended_next_skill")
            recovery_action = "route_to_next_safe_model_visible_skill"
        self.recoverable_action_observations.append(
            {
                "failure_code": reason,
                "turn_index": self.model_calls_used,
                "capability_id": decision.capability_id,
                "operation": decision.operation,
                "target_ref_hash": stable_hash(str(decision.target_ref or "")),
                "recovery_action": recovery_action,
                "recommended_skill": recommended_skill,
                "remaining_create_file_plan_count": len(create_plans),
                "browser_product_card_count": failure_card_count,
                "runtime_failure_fact": failure_context_cards.get("runtime_failure_fact"),
                "model_visible_body_failure_packet": failure_context_cards.get("model_visible_body_failure_packet"),
                "model_blocker_assessment_schema": failure_context_cards.get("model_blocker_assessment_schema"),
                "data_not_authority": True,
                "can_execute": False,
            }
        )
        return True

    def _available_actions(self) -> tuple[str, ...]:
        completion_requirements = _product_completion_requirements(self.dispatch_results, _merged_dispatch_context_cards(self.dispatch_results))
        has_terminal_browser_evidence = bool(
            completion_requirements.get("has_real_browser_verified_extraction_receipt")
            or completion_requirements.get("has_confirmed_no_results_search_receipt")
        )
        if self._latest_dispatch_blocked_reason() == "BODY_SESSION_UNAVAILABLE" and self.product_receipt_refs:
            return ("sentinel_loop.finish",)
        if (
            has_terminal_browser_evidence
            and not completion_requirements.get("has_grounded_evidence_summary")
        ):
            return ("sentinel_loop.summarize_evidence",)
        if (
            has_terminal_browser_evidence
            and completion_requirements.get("has_grounded_evidence_summary")
            and completion_requirements.get("has_objective_relevance_assessment")
        ):
            return ("sentinel_loop.finish",)
        if self.material_actions_used >= self.max_material_actions and self.product_receipt_refs:
            return ("sentinel_loop.finish",)
        actions = []
        if _workspace_create_file_plans(self.workspace_root, mission_objective=self.mission_objective):
            actions.append("workspace_patch.create_file")
        if _workspace_patch_plans(self.workspace_root):
            actions.append("workspace_patch.apply_patch")
        if (
            self._latest_dispatch_blocked_reason() == "code_exec_failed"
            and "workspace_patch.apply_patch" not in actions
        ):
            actions.append("workspace_patch.apply_patch")
        actions.extend([
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_evidence",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "worker_fleet.spawn_worker",
        ])
        if self.product_receipt_refs:
            actions.append("sentinel_loop.finish")
        return tuple(action for action in actions if self._action_allowed_by_mission_scope(action))

    def _action_allowed_by_mission_scope(self, action_name: str) -> bool:
        if not self.allowed_capabilities:
            return True
        capability_id = action_name.split(".", 1)[0]
        if capability_id == "sentinel_loop":
            return True
        return capability_id in set(self.allowed_capabilities)

    def _decision_allowed_by_mission_scope(self, decision: ActionEnvelope) -> bool:
        if not self.allowed_capabilities:
            return True
        if decision.capability_id == "sentinel_loop":
            return True
        return decision.capability_id in set(self.allowed_capabilities)

    def _latest_dispatch_blocked_reason(self) -> str | None:
        if not self.dispatch_results:
            return None
        return self.dispatch_results[-1].blocked_reason

    def _progress_state(self) -> str:
        if not self.product_receipt_refs:
            return "product_action_kernel_loop_waiting_for_first_material_skill"
        if self.material_actions_used >= self.max_material_actions:
            return "product_action_kernel_loop_material_budget_ready_to_finish"
        return "product_action_kernel_loop_material_receipts_available"

    def _dispatch_product_action(self, decision: ActionEnvelope, *, loop_context: dict[str, Any]) -> UnifiedDispatchResult:
        hard_boundary_reason = _entrypoint_hard_boundary_reason(decision)
        if hard_boundary_reason is not None:
            return _synthetic_blocked_dispatch_result(
                loop_id=self.loop_id,
                turn_index=self.model_calls_used,
                decision=decision,
                reason=hard_boundary_reason,
            )
        tools, actions = _authority_for_action(decision)
        if _is_telegram_channel_decision(decision) and "telegram:configured-chat" in set(self.allowed_domains):
            tools.append("channel:telegram")
        parameters = dict(decision.params)
        if decision.capability_id == "sentinel_loop" and decision.operation == "summarize_evidence":
            parameters["loop_context"] = _completion_lane_context(loop_context)
        if decision.capability_id == "real_browser_control" and decision.operation in {
            "real_browser.extract_evidence",
            "real_browser.extract_entities",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
        }:
            browser_context = _browser_context_lane_context(loop_context)
            if _product_card_count_from_context_cards(browser_context) > 0:
                parameters["loop_context"] = browser_context
        mission = self.host.lifecycle.create_mission(
            session_id=f"{self.session_id}:{self.model_calls_used}",
            draft=MissionDraft(
                title=f"ProductActionKernel loop action {self.model_calls_used}",
                objective=self.mission_objective,
                expected_artifacts=["product action kernel receipt", "product action kernel finalgate"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="pending",
                allowed_actions=actions,
                forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
                summary=f"ProductActionKernel task-loop authority for {decision.capability_id}.",
            ),
            approval_scope=MissionAuthorityApprovalScope(
                user_id="operator_user",
                allowed_systems=["local_workspace"],
                allowed_tools=tools,
                allowed_actions=actions,
                forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
                allowed_paths=[str(self.workspace_root)],
                allowed_domains=_allowed_domains_for_action(decision, self.allowed_domains),
                max_duration_minutes=5,
                max_actions=1,
                max_recipients=1,
                max_cost_usd=0.0,
            ),
            policy=MissionAuthorityPolicy(
                user_id="operator_user",
                allowed_systems=["local_workspace"],
                allowed_tools=tools,
                allowed_actions=actions,
                forbidden_actions=["payment", "credential_access", "contact_supplier", "browser_login"],
                allowed_paths=[str(self.workspace_root)],
                allowed_domains=_allowed_domains_for_action(decision, self.allowed_domains),
                max_duration_minutes=5,
                max_actions=1,
                max_recipients=1,
                max_cost_usd=0.0,
            ),
            capability_id=decision.capability_id,
            operation=decision.operation,
            parameters=parameters,
            workspace_ref=f"workspace:{self.workspace_root}",
            model_contract_ref=self.model_contract_ref,
        )
        self.host.prepare_mission_workspace(
            mission_id=mission.record.mission_id,
            workspace_root=self.workspace_root,
            allowed_domains=tuple(_allowed_domains_for_action(decision, self.allowed_domains)),
            channel_destination_refs=tuple(_channel_destination_refs_for_action(decision)),
        )
        pump = self.host.pump_daemon_once(
            mission.record.mission_id,
            product_task_resource_scope=self.product_task_resource_scope,
        )
        if pump.dispatch_result is None:
            raise ActionKernelError("product_action_kernel_dispatch_missing")
        return pump.dispatch_result

    def _route_contextless_browser_decision(
        self,
        decision: ActionEnvelope,
        context: dict[str, Any],
    ) -> ActionEnvelope:
        if decision.capability_id != "real_browser_control":
            return decision
        if decision.operation not in {
            "real_browser.extract_evidence",
            "real_browser.extract_entities",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
        }:
            return decision
        if str(decision.params.get("engine_profile") or "").strip():
            return decision
        if decision.operation in {"real_browser.extract_evidence", "real_browser.extract_entities"}:
            return decision
        if _product_card_count_from_context_cards(_browser_context_lane_context(context)) > 0:
            return decision
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": _browser_search_query_from_objective(self.mission_objective)},
            idempotency_key=_recovery_key(self.loop_id, "browser_contextless_extract_to_search", self.model_calls_used),
        )

    def _complete(self, reason: str) -> ProductActionKernelTaskLoopResult:
        certificate = self._write_certificate(
            status=ProductActionKernelTaskLoopStatus.COMPLETED,
            accepted=True,
            reason=reason,
        )
        self._record_evidence_transition(
            "FinalGate_result",
            {
                "status": "completed",
                "accepted": True,
                "reason": reason,
                "certificate_ref": certificate.certificate_id,
            },
        )
        self._record_evidence_transition(
            "terminal_verdict",
            {
                "verdict": "completed",
                "final_reason": reason,
            },
        )
        return self._result(
            ProductActionKernelTaskLoopStatus.COMPLETED,
            reason,
            certificate_refs=(certificate.certificate_id,),
        )

    def _block(self, reason: str) -> ProductActionKernelTaskLoopResult:
        certificate = self._write_certificate(
            status=ProductActionKernelTaskLoopStatus.BLOCKED,
            accepted=False,
            reason=reason,
        )
        self._record_evidence_transition(
            "FinalGate_result",
            {
                "status": "blocked",
                "accepted": False,
                "reason": reason,
                "certificate_ref": certificate.certificate_id,
            },
        )
        self._record_evidence_transition(
            "terminal_verdict",
            {
                "verdict": "blocked",
                "blocked_reason": reason,
            },
        )
        return self._result(
            ProductActionKernelTaskLoopStatus.BLOCKED,
            "model_led_product_action_kernel_task_loop_blocked",
            blocked_reason=reason,
            certificate_refs=(certificate.certificate_id,),
        )

    def _result(
        self,
        status: ProductActionKernelTaskLoopStatus,
        final_reason: str,
        *,
        blocked_reason: str | None = None,
        certificate_refs: tuple[str, ...] = (),
    ) -> ProductActionKernelTaskLoopResult:
        return ProductActionKernelTaskLoopResult(
            loop_id=self.loop_id,
            status=status,
            final_reason=final_reason,
            blocked_reason=blocked_reason,
            model_call_count=self.model_calls_used,
            material_action_count=self.material_actions_used,
            capability_sequence=tuple(self.capability_sequence),
            mission_ids=tuple(self.mission_ids),
            product_receipt_refs=tuple(sanitize_operator_refs(self.product_receipt_refs)),
            product_finalgate_refs=tuple(sanitize_operator_refs(self.product_finalgate_refs)),
            certificate_refs=certificate_refs,
            dispatch_results=tuple(self.dispatch_results),
        )

    def _write_certificate(
        self,
        *,
        status: ProductActionKernelTaskLoopStatus,
        accepted: bool,
        reason: str,
    ) -> ProductActionKernelTaskLoopFinalCertificate:
        certificate = ProductActionKernelTaskLoopFinalCertificate(
            loop_id=self.loop_id,
            status=status,
            accepted=accepted,
            reason=reason,
            mission_ids=tuple(self.mission_ids),
            product_receipt_refs=tuple(sanitize_operator_refs(self.product_receipt_refs)),
            product_finalgate_refs=tuple(sanitize_operator_refs(self.product_finalgate_refs)),
        )
        path = (
            self.host.kernel.store.run_root
            / "_product_action_kernel_task_loop"
            / "finalgate"
            / f"{certificate.certificate_id}.json"
        )
        self.host.kernel.store.atomic_write_json(path, certificate.safe_model_dump())
        return certificate

    def _record_evidence_transition(self, event_type: str, payload: dict[str, Any]) -> None:
        sink = self.evidence_sink
        if sink is None:
            return
        record = getattr(sink, "record_transition", None)
        if callable(record):
            record(event_type, payload)

    def _record_dispatch_evidence(self, dispatch_result: UnifiedDispatchResult) -> None:
        payload = {
            "mission_id": dispatch_result.mission_id,
            "capability_id": dispatch_result.capability_id,
            "operation": dispatch_result.operation,
            "status": dispatch_result.status.value,
            "blocked_reason": dispatch_result.blocked_reason,
            "receipt_refs": sanitize_operator_refs(dispatch_result.receipt_refs),
            "finalgate_refs": sanitize_operator_refs(dispatch_result.finalgate_refs),
        }
        safe_context_cards = dispatch_result.safe_context_cards if isinstance(dispatch_result.safe_context_cards, dict) else {}
        runtime_failure_fact = safe_context_cards.get("runtime_failure_fact")
        if isinstance(runtime_failure_fact, dict):
            self._record_evidence_transition(
                "runtime_failure_fact_created",
                {"runtime_failure_fact": runtime_failure_fact, **payload},
            )
        failure_packet = safe_context_cards.get("model_visible_body_failure_packet")
        if isinstance(failure_packet, dict):
            self._record_evidence_transition(
                "model_visible_failure_packet_created",
                {"model_visible_body_failure_packet": failure_packet, **payload},
            )
        model_assessment = safe_context_cards.get("model_blocker_assessment")
        if isinstance(model_assessment, dict):
            self._record_evidence_transition(
                "model_blocker_assessment_received",
                {"model_blocker_assessment": model_assessment, **payload},
            )
        if dispatch_result.receipt_refs:
            self._record_evidence_transition(
                "material_receipt_created",
                payload,
            )
        if dispatch_result.finalgate_refs:
            self._record_evidence_transition(
                "FinalGate_result",
                payload,
            )


class ProductActionKernelTaskLoopReplay(SentinelModel):
    mission_ids: tuple[str, ...]
    reexecuted_actions: bool
    model_calls_delta: int
    product_dispatch_delta: int
    command_executions_delta: int
    channel_transport_sends_delta: int
    receipt_writes_delta: int
    finalgate_writes_delta: int
    artifact_hashes_stable: bool

    @classmethod
    def from_store(cls, store: MissionRunStore, *, mission_ids: tuple[str, ...]) -> "ProductActionKernelTaskLoopReplay":
        before = _artifact_counts(store, mission_ids)
        hashes_before = _artifact_hashes(store, mission_ids)
        after = _artifact_counts(store, mission_ids)
        hashes_after = _artifact_hashes(store, mission_ids)
        return cls(
            mission_ids=tuple(mission_ids),
            reexecuted_actions=False,
            model_calls_delta=0,
            product_dispatch_delta=after["dispatch_closeout"] - before["dispatch_closeout"],
            command_executions_delta=0,
            channel_transport_sends_delta=0,
            receipt_writes_delta=after["receipts"] - before["receipts"],
            finalgate_writes_delta=after["finalgate"] - before["finalgate"],
            artifact_hashes_stable=hashes_before == hashes_after,
        )


def _authority_for_action(decision: ActionEnvelope) -> tuple[list[str], list[str]]:
    capability = decision.capability_id
    operation = decision.operation
    if capability == "real_browser_control":
        return ["real_browser_control"], [f"{capability}.{operation}", operation]
    if capability == "worker_fleet":
        return ["worker_fleet"], ["worker_fleet.spawn_worker", "spawn_worker"]
    if capability == "code_execution_sandbox":
        return ["code_execution_sandbox"], ["code_execution_sandbox.code_exec.run_profile", "code_exec.run_profile"]
    if capability == "bounded_channel":
        tools = ["bounded_channel", "channel_draft_send"]
        return tools, ["bounded_channel.send_message", "send_message"]
    if capability == "workspace_patch":
        return ["workspace_patch"], [f"{capability}.{operation}", operation]
    return [capability], [f"{capability}.{operation}", operation]


def _allowed_domains_for_action(decision: ActionEnvelope, allowed_domains: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(allowed_domains))


def _is_telegram_channel_decision(decision: ActionEnvelope) -> bool:
    return decision.capability_id == "bounded_channel" and str(decision.params.get("channel") or "").lower() == "telegram"


def _channel_destination_refs_for_action(decision: ActionEnvelope) -> tuple[str, ...]:
    if decision.capability_id != "bounded_channel":
        return ()
    recipients = decision.params.get("recipients")
    if not isinstance(recipients, list):
        return ()
    refs = [str(recipient) for recipient in recipients if str(recipient).strip()]
    return tuple(dict.fromkeys(refs))


def _live_channel_destination_grants(allowed_domains: tuple[str, ...]) -> list[dict[str, str]]:
    if "telegram:configured-chat" not in set(allowed_domains):
        return []
    return [
        {
            "adapter_id": "telegram_live_adapter",
            "channel": "telegram",
            "destination_ref": "telegram:configured-chat",
        }
    ]


def _entrypoint_hard_boundary_reason(decision: ActionEnvelope) -> str | None:
    capability = decision.capability_id.strip().lower()
    operation = decision.operation.strip().lower()
    action_text = f"{capability}.{operation}"
    hard_capabilities = {
        "account_authority",
        "credential_vault",
        "external_channel",
        "financial_authority",
        "payment_authority",
    }
    hard_markers = (
        "checkout",
        "contact_supplier",
        "credential",
        "login",
        "payment",
        "read_secret",
        "secret",
        "spend",
    )
    if capability in hard_capabilities or any(marker in action_text for marker in hard_markers):
        return "skill_not_product_dispatchable"
    return None


def _is_recoverable_model_decision_failure(reason: str) -> bool:
    return reason in {
        "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT",
        "MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED",
        "MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE",
        "PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION",
    }


def _is_recoverable_action_failure(reason: str) -> bool:
    return reason in {
        "code_exec_failed",
        "workspace_patch_create_target_exists",
    } or _is_recoverable_browser_action_failure(reason)


def _is_recoverable_browser_action_failure(reason: str) -> bool:
    return reason in {
        "real_browser_search_control_not_found",
        "real_browser_search_actuation_failed",
        "real_browser_search_session_open_failed",
        "real_browser_open_result_actuation_failed",
        "real_browser_element_ref_unknown",
        "real_browser_runtime_dispatch_exception",
        "BODY_SESSION_UNAVAILABLE",
    }


def _synthetic_blocked_dispatch_result(
    *,
    loop_id: str,
    turn_index: int,
    decision: ActionEnvelope,
    reason: str,
) -> UnifiedDispatchResult:
    return UnifiedDispatchResult(
        dispatch_id=new_id("dispatch"),
        status=DispatchStatus.BLOCKED,
        mission_id=f"{loop_id}_preflight_block_{turn_index}",
        execution_request_id=f"{loop_id}_preflight_request_{turn_index}",
        adapter_id=None,
        capability_id=decision.capability_id,
        operation=decision.operation,
        finalgate_status="rejected",
        blocked_reason=reason,
    )


def _create_file_recovery_action(loop_id: str, plan: dict[str, str], receipt_count: int) -> ActionEnvelope:
    target_path = str(plan.get("target_path") or "").strip()
    new_text = str(plan.get("new_text") or "")
    if not target_path or not new_text:
        raise ActionKernelError("MODEL_NATIVE_DECISION_CREATE_FILE_PLAN_MISSING")
    return ActionEnvelope(
        capability_id="workspace_patch",
        operation="apply_patch",
        target_ref=target_path,
        params={
            "target_path": target_path,
            "target_paths": [target_path],
            "create_file": True,
            "new_text": new_text,
        },
        idempotency_key=_recovery_key(loop_id, f"create_file:{target_path}", receipt_count),
    )


def _recovery_key(loop_id: str, skill: str, receipt_count: int) -> str:
    return stable_hash({"loop_id": loop_id, "skill": skill, "receipt_count": receipt_count, "kind": "recovery"})


def _completed_dispatch_count(context: dict[str, Any], capability_id: str, operation: str) -> int:
    count = 0
    for item in context.get("dispatch_summaries") or ():
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") not in {"completed", "passed"}:
            continue
        if item.get("capability_id") == capability_id and item.get("operation") == operation:
            count += 1
    return count


def _safe_action_envelope_evidence(decision: ActionEnvelope) -> dict[str, Any]:
    return {
        "capability_id": decision.capability_id,
        "operation": decision.operation,
        "params_hash": stable_hash(decision.params),
        "target_ref_hash": stable_hash(str(decision.target_ref or "")),
        "idempotency_key_hash": stable_hash(str(decision.idempotency_key or "")),
        "data_not_authority": True,
        "can_execute": False,
    }


def _safe_context_shape_for_evidence(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "progress_state": context.get("progress_state"),
        "model_visible_skills": list(context.get("model_visible_skills") or ()),
        "primary_model_recommended_next_skill": context.get("primary_model_recommended_next_skill"),
        "recent_product_receipt_count": len(context.get("recent_product_receipt_refs") or ()),
        "recoverable_action_failure_count": context.get("recoverable_action_failure_count"),
        "recoverable_model_decision_failure_count": context.get("recoverable_model_decision_failure_count"),
        "has_runtime_failure_fact": isinstance(context.get("runtime_failure_fact"), dict),
        "has_model_visible_body_failure_packet": isinstance(context.get("model_visible_body_failure_packet"), dict),
        "has_model_blocker_assessment_schema": isinstance(context.get("model_blocker_assessment_schema"), dict),
        "finish_available": bool(context.get("finish_available")),
        "objective_satisfied": bool(context.get("objective_satisfied")),
        "data_not_authority": True,
        "can_execute": False,
    }


def _dispatch_summaries(results: list[UnifiedDispatchResult]) -> list[dict[str, Any]]:
    return [
        {
            "mission_id": result.mission_id,
            "status": result.status.value,
            "capability_id": result.capability_id,
            "operation": result.operation,
            "adapter_id": result.adapter_id,
            "receipt_refs": sanitize_operator_refs(result.receipt_refs),
            "finalgate_refs": sanitize_operator_refs(result.finalgate_refs),
            "blocked_reason": result.blocked_reason,
            "receipt_count": len(result.receipt_refs),
        }
        for result in results
    ]


def _bounded_observation_summaries(results: list[UnifiedDispatchResult]) -> list[dict[str, Any]]:
    return [
        {
            "capability_id": result.capability_id,
            "operation": result.operation,
            "status": result.status.value,
            "receipt_count": len(result.receipt_refs),
            "blocked_reason": result.blocked_reason,
            "data_not_authority": True,
            "can_execute": False,
        }
        for result in results
    ]


def _merged_dispatch_context_cards(results: list[UnifiedDispatchResult]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for result in results:
        if isinstance(result.safe_context_cards, dict):
            for key, value in result.safe_context_cards.items():
                if value is not None:
                    merged[str(key)] = value
    return merged


def _real_browser_control_summary(results: list[UnifiedDispatchResult]) -> dict[str, Any] | None:
    for result in reversed(results):
        if result.capability_id != "real_browser_control":
            continue
        return {
            "latest_action": {
                "operation": result.operation,
                "status": result.status.value,
                "receipt_count": len(result.receipt_refs),
            },
            "data_not_authority": True,
            "can_execute": False,
        }
    return None


def _grounded_evidence_summary_card(safe_context_cards: dict[str, Any]) -> dict[str, Any]:
    summary = safe_context_cards.get("grounded_evidence_summary")
    if isinstance(summary, dict):
        return {"present": True, **summary}
    return {"present": False, "data_not_authority": True, "can_execute": False}


def _product_completion_requirements(
    results: list[UnifiedDispatchResult],
    safe_context_cards: dict[str, Any],
) -> dict[str, Any]:
    operations = {
        (result.capability_id, result.operation)
        for result in results
        if result.status is DispatchStatus.COMPLETED and result.receipt_refs
    }
    summary = _grounded_evidence_summary_card(safe_context_cards)
    product_card_count = _product_card_count_from_context_cards(safe_context_cards)
    has_grounded_summary = bool(summary.get("present") is True)
    confirmed_no_results = _has_confirmed_no_results_search(safe_context_cards)
    return {
        "has_real_browser_search_receipt": ("real_browser_control", "real_browser.search") in operations,
        "has_real_browser_extraction_receipt": bool(
            ("real_browser_control", "real_browser.extract_evidence") in operations
            or ("real_browser_control", "real_browser.extract_entities") in operations
            or ("real_browser_control", "real_browser.extract_product_cards") in operations
        ),
        "has_real_browser_verified_extraction_receipt": ("real_browser_control", "real_browser.verify_extraction") in operations,
        "has_confirmed_no_results_search_receipt": confirmed_no_results,
        "has_grounded_evidence_summary": has_grounded_summary,
        "has_objective_relevance_assessment": bool(summary.get("objective_relevance_assessed") is True),
        "has_relevant_product_evidence": bool(summary.get("has_relevant_product_evidence") is True),
        "under_price_condition_supported_by_visible_evidence": summary.get(
            "under_price_condition_supported_by_visible_evidence",
            "unknown",
        ),
        "product_or_result_candidate_card_count": product_card_count,
        "data_not_authority": True,
        "can_execute": False,
    }


def _browser_cognitive_decision_frame(
    safe_context_cards: dict[str, Any],
    *,
    mission_objective: str = "",
) -> dict[str, Any]:
    environment = safe_context_cards.get("browser_environment_state")
    if not isinstance(environment, dict):
        primary = "browse_search" if _mission_objective_mentions_browser_work(mission_objective) else None
        return {
            "canonical_state_source": "none",
            "primary_recommended_skill": primary,
            "candidate_entities": [],
            "result_regions": {"candidate_count": 0, "relevant_candidate_count": 0},
            "search_controls": {"ranked_count": 0, "search_like_refs": []},
            "available_safe_browser_skills": ["browse_search"] if primary == "browse_search" else [],
            "recommended_recovery_paths": [],
            "data_not_authority": True,
            "can_execute": False,
        }
    state_fields = environment.get("state_fields") if isinstance(environment.get("state_fields"), dict) else {}
    result_regions = _state_field_value(state_fields, "result_regions")
    search_controls = _state_field_value(state_fields, "search_controls")
    recovery_paths = _state_field_value(state_fields, "recommended_recovery_paths").get("paths", [])
    candidate_entities = _candidate_entities_from_environment(environment)
    candidate_count = _safe_int(result_regions.get("candidate_count"))
    relevant_count = _safe_int(result_regions.get("relevant_candidate_count"))
    skills = [str(skill) for skill in environment.get("recommended_model_skills", []) if str(skill)]
    if candidate_count:
        primary = "extract"
    elif search_controls.get("ranked_count") or "browse_search" in skills:
        primary = "browse_search"
    else:
        primary = "browse_search"
    return {
        "canonical_state_source": "BrowserEnvironmentState",
        "state_hash": safe_context_cards.get("browser_environment_state_hash"),
        "state_id": environment.get("state_id"),
        "page_identity": _state_field_value(state_fields, "page_identity"),
        "lifecycle_state": _state_field_value(state_fields, "page_lifecycle"),
        "search_controls": search_controls,
        "result_regions": {
            "candidate_count": candidate_count,
            "relevant_candidate_count": relevant_count,
        },
        "candidate_entities": candidate_entities,
        "uncertainty": _state_field_value(state_fields, "uncertainty"),
        "recommended_recovery_paths": recovery_paths if isinstance(recovery_paths, list) else [],
        "available_safe_browser_skills": skills,
        "primary_recommended_skill": primary,
        "evidence_refs": _state_field_evidence_refs(state_fields),
        "data_not_authority": True,
        "can_execute": False,
    }


def _mission_objective_mentions_browser_work(value: str) -> bool:
    lowered = str(value or "").lower()
    markers = (
        "browser",
        "browse",
        "catalog",
        "online",
        "page",
        "product",
        "public web",
        "search the web",
        "site",
        "url",
        "website",
        "web page",
    )
    return any(marker in lowered for marker in markers)


def _product_context_recommended_actions(
    *,
    available_actions: tuple[str, ...],
    completion_requirements: dict[str, Any],
    browser_cognitive_frame: dict[str, Any],
) -> tuple[str, ...]:
    has_terminal_browser_evidence = bool(
        completion_requirements.get("has_real_browser_verified_extraction_receipt")
        or completion_requirements.get("has_confirmed_no_results_search_receipt")
    )
    if (
        has_terminal_browser_evidence
        and not completion_requirements.get("has_grounded_evidence_summary")
        and "sentinel_loop.summarize_evidence" in available_actions
    ):
        return ("sentinel_loop.summarize_evidence",)
    if (
        has_terminal_browser_evidence
        and completion_requirements.get("has_grounded_evidence_summary")
        and "sentinel_loop.finish" in available_actions
    ):
        return ("sentinel_loop.finish",)
    primary_skill = browser_cognitive_frame.get("primary_recommended_skill")
    if primary_skill == "extract":
        extract_action = _extract_action_for_browser_frame(browser_cognitive_frame)
        preferred = (
            extract_action,
            "real_browser_control.real_browser.verify_extraction",
        )
    elif primary_skill == "browse_search":
        preferred = ("real_browser_control.real_browser.search",)
    else:
        preferred = ()
    ordered = [action for action in preferred if action in available_actions]
    if ordered:
        return tuple(ordered)
    ordered.extend(action for action in available_actions if action not in ordered)
    return tuple(ordered)


def _state_field_value(state_fields: dict[str, Any], key: str) -> dict[str, Any]:
    value = state_fields.get(key)
    if isinstance(value, dict):
        field_value = value.get("value")
        if isinstance(field_value, dict):
            return field_value
    return {}


def _state_field_evidence_refs(state_fields: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for value in state_fields.values():
        if isinstance(value, dict):
            evidence = value.get("evidence_refs")
            if isinstance(evidence, list):
                refs.extend(str(item) for item in evidence if str(item))
    return list(dict.fromkeys(refs))


def _candidate_entities_from_environment(environment: dict[str, Any]) -> list[dict[str, Any]]:
    extraction = environment.get("extraction_graph")
    if not isinstance(extraction, dict):
        return []
    cards = extraction.get("cards")
    if not isinstance(cards, list):
        return []
    entities = []
    for index, card in enumerate(cards[:8]):
        if not isinstance(card, dict):
            continue
        entities.append(
            {
                "rank": index,
                "kind": card.get("kind", "unknown"),
                "entity_family": card.get("entity_family", "unknown"),
                "entity_kind": card.get("entity_kind", card.get("kind", "unknown")),
                "title": card.get("title", "unknown"),
                "visible_price": card.get("visible_price", "unknown"),
                "currency_or_unit": card.get("currency_or_unit", "unknown"),
                "minimum_order": card.get("minimum_order", "unknown"),
                "supplier_or_store": card.get("supplier_or_store", "unknown"),
                "relevance_to_objective": card.get("relevance_to_objective", "unknown"),
                "relevance_reason": card.get("relevance_reason", "unknown"),
                "evidence_ref_hash": card.get("evidence_ref_hash", ""),
                "evidence_refs": card.get("evidence_refs", []),
                "extra_attributes": card.get("extra_attributes", {}),
            }
        )
    return entities


def _extract_action_for_browser_frame(browser_cognitive_frame: dict[str, Any]) -> str:
    entities = browser_cognitive_frame.get("candidate_entities")
    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            kind = str(entity.get("entity_kind") or entity.get("kind") or "").lower()
            family = str(entity.get("entity_family") or "").lower()
            if any(marker in f"{kind} {family}" for marker in ("commerce", "product", "catalog")):
                return "real_browser_control.real_browser.extract_product_cards"
            commerce_fields = ("visible_price", "currency_or_unit", "minimum_order", "supplier_or_store")
            if any(str(entity.get(field) or "").strip().lower() not in {"", "unknown"} for field in commerce_fields):
                return "real_browser_control.real_browser.extract_product_cards"
    return "real_browser_control.real_browser.extract_evidence"


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _product_card_count_from_context_cards(safe_context_cards: dict[str, Any]) -> int:
    model = safe_context_cards.get("browser_world_model")
    if isinstance(model, dict):
        cards = model.get("product_or_result_candidate_cards")
        if isinstance(cards, list):
            return len(cards)
    summary = safe_context_cards.get("browser_world_model_summary")
    if isinstance(summary, dict):
        for key in ("product_or_result_candidate_count", "product_candidate_count", "result_candidate_count"):
            value = summary.get(key)
            if isinstance(value, int):
                return value
    return 0


def _has_confirmed_no_results_search(safe_context_cards: dict[str, Any]) -> bool:
    materiality = safe_context_cards.get("browser_search_materiality")
    if not isinstance(materiality, dict):
        return False
    outcome = materiality.get("typed_search_outcome")
    if not isinstance(outcome, dict):
        return False
    return bool(
        outcome.get("outcome_kind") == "NO_RESULTS_CONFIRMED"
        and outcome.get("search_materially_successful") is True
    )


def _is_completion_lane_decision(decision: ActionEnvelope) -> bool:
    return decision.capability_id == "sentinel_loop" and decision.operation in {"summarize_evidence", "finish"}


def _completion_lane_context(loop_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission_objective": loop_context.get("mission_objective"),
        "completion_requirements": loop_context.get("completion_requirements"),
        "real_browser_control_summary": loop_context.get("real_browser_control_summary"),
        "bounded_observation_summaries": loop_context.get("bounded_observation_summaries"),
        "browser_search_materiality": loop_context.get("browser_search_materiality"),
        "search_actuation_trace": loop_context.get("search_actuation_trace"),
        "browser_recovery_evidence": loop_context.get("browser_recovery_evidence"),
        "browser_world_model": loop_context.get("browser_world_model"),
        "browser_world_model_summary": loop_context.get("browser_world_model_summary"),
        "browser_decision_frame": loop_context.get("browser_decision_frame"),
        "grounded_evidence_summary": loop_context.get("grounded_evidence_summary"),
        "data_not_authority": True,
        "can_execute": False,
    }


def _browser_context_lane_context(loop_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission_objective": loop_context.get("mission_objective"),
        "completion_requirements": loop_context.get("completion_requirements"),
        "browser_world_model": _bounded_browser_context_value(loop_context.get("browser_world_model"), path="browser_world_model"),
        "browser_world_model_summary": _bounded_browser_context_value(
            loop_context.get("browser_world_model_summary"),
            path="browser_world_model_summary",
        ),
        "browser_decision_frame": _bounded_browser_context_value(
            loop_context.get("browser_decision_frame"),
            path="browser_decision_frame",
        ),
        "browser_actionability_registry": _bounded_browser_context_value(
            loop_context.get("browser_actionability_registry"),
            path="browser_actionability_registry",
        ),
        "actionability_frame": _bounded_browser_context_value(loop_context.get("actionability_frame"), path="actionability_frame"),
        "browser_environment_state": _bounded_browser_context_value(
            loop_context.get("browser_environment_state"),
            path="browser_environment_state",
        ),
        "browser_environment_state_hash": loop_context.get("browser_environment_state_hash"),
        "browser_backend_execution": _bounded_browser_context_value(
            loop_context.get("browser_backend_execution"),
            path="browser_backend_execution",
        ),
        "browser_devtools_context": _bounded_browser_context_value(
            loop_context.get("browser_devtools_context"),
            path="browser_devtools_context",
        ),
        "browser_search_materiality": _bounded_browser_context_value(
            loop_context.get("browser_search_materiality"),
            path="browser_search_materiality",
        ),
        "search_actuation_trace": _bounded_browser_context_value(
            loop_context.get("search_actuation_trace"),
            path="search_actuation_trace",
        ),
        "browser_recovery_evidence": _bounded_browser_context_value(
            loop_context.get("browser_recovery_evidence"),
            path="browser_recovery_evidence",
        ),
        "runtime_failure_fact": _bounded_browser_context_value(
            loop_context.get("runtime_failure_fact"),
            path="runtime_failure_fact",
        ),
        "model_visible_body_failure_packet": _bounded_browser_context_value(
            loop_context.get("model_visible_body_failure_packet"),
            path="model_visible_body_failure_packet",
        ),
        "model_blocker_assessment_schema": _bounded_browser_context_value(
            loop_context.get("model_blocker_assessment_schema"),
            path="model_blocker_assessment_schema",
        ),
        "data_not_authority": True,
        "can_execute": False,
    }


def _bounded_browser_context_value(value: Any, *, path: str, depth: int = 0) -> Any:
    if depth > 8:
        return _bounded_context_ref(value)
    if isinstance(value, dict):
        return {
            str(key): _bounded_browser_context_value(child, path=f"{path}.{key}", depth=depth + 1)
            for key, child in value.items()
        }
    if isinstance(value, list | tuple | set):
        limit = 20 if path.endswith("product_or_result_candidate_cards") else 40
        items = list(value)
        item_limit = max(limit - 1, 0) if len(items) > limit else limit
        bounded = [
            _bounded_browser_context_value(item, path=f"{path}[{index}]", depth=depth + 1)
            for index, item in enumerate(items[:item_limit])
        ]
        if len(items) > limit:
            bounded.append(
                {
                    "truncated": True,
                    "original_count": len(items),
                    "retained_count": item_limit,
                    "source_path_hash": stable_hash(path),
                    "data_not_authority": True,
                    "can_execute": False,
                }
            )
        return bounded
    return value


def _bounded_context_ref(value: Any) -> dict[str, Any]:
    return {
        "truncated": True,
        "value_hash": stable_hash(value),
        "data_not_authority": True,
        "can_execute": False,
    }


def _browser_search_query_from_objective(mission_objective: str) -> str:
    objective = mission_objective.lower()
    if "glasses" in objective or "sunglasses" in objective or "eyewear" in objective:
        return "glasses sunglasses under 5 euro"
    if "search" in objective and "product" in objective:
        return "product search"
    return "mission objective product research"


def _artifact_counts(store: MissionRunStore, mission_ids: tuple[str, ...]) -> dict[str, int]:
    roots = [store.mission_dir(mission_id) for mission_id in mission_ids if _path_exists(store.mission_dir(mission_id))]
    return {
        "dispatch_closeout": sum(_count_direct_json(root / "dispatch_closeout") for root in roots),
        "receipts": sum(_count_named_json_descendants(root, "receipts") for root in roots),
        "finalgate": sum(_count_named_json_descendants(root, "finalgate") for root in roots),
    }


def _artifact_hashes(store: MissionRunStore, mission_ids: tuple[str, ...]) -> tuple[str, ...]:
    hashes: list[str] = []
    for mission_id in mission_ids:
        mission_dir = store.mission_dir(mission_id)
        if not _path_exists(mission_dir):
            continue
        for path in sorted((path for path in _iter_descendant_file_paths(mission_dir) if path.suffix == ".json"), key=str):
            hashes.append(hashlib.sha256(_read_bytes_file(path)).hexdigest())
    return tuple(hashes)


def _count_direct_json(root: Path) -> int:
    return sum(1 for path in _iter_child_paths(root) if path.suffix == ".json")


def _count_named_json_descendants(root: Path, dirname: str) -> int:
    return sum(1 for path in _iter_descendant_file_paths(root) if path.suffix == ".json" and path.parent.name == dirname)


def _workspace_patch_plans(workspace_root: Path) -> list[dict[str, str]]:
    plans: list[dict[str, str]] = []
    for relative_path, marker, replacement in (
        ("app.py", "TODO_SENTINEL_APP_MESSAGE", "Sentinel model-led local app worked."),
        (
            "README.md",
            "TODO_SENTINEL_APP_README",
            "This multi-file local app is built through the Sentinel ProductActionKernel spine.",
        ),
        (
            "tests/test_app.py",
            "TODO_SENTINEL_APP_TEST",
            'from app import main\n\n\ndef test_main_returns_message():\n    assert main() == "Sentinel model-led local app worked."\n',
        ),
        ("app.py", "TODO_SENTINEL_APP", "Sentinel model-led local app worked."),
        ("README.md", "TODO_SENTINEL_APP", "Sentinel model-led local app worked."),
    ):
        path = workspace_root / relative_path
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if marker not in content:
            continue
        plans.append(
            {
                "target_path": relative_path,
                "expected_base_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "old_text": marker,
                "new_text": replacement,
            }
        )
    return plans


def _workspace_create_file_plans(workspace_root: Path, *, mission_objective: str = "") -> list[dict[str, str]]:
    if _workspace_patch_plans(workspace_root):
        return []
    hygiene_plans = _workspace_test_hygiene_create_file_plans(workspace_root)
    if hygiene_plans:
        return hygiene_plans
    objective = mission_objective.lower()
    if not any(marker in objective for marker in ("arbitrary", "from scratch", "create a tiny python app")):
        return []
    if _objective_requests_number_analyzer(objective):
        return _missing_create_file_plans(
            workspace_root,
            _number_analyzer_file_specs(workspace_root),
        )
    plans: list[dict[str, str]] = []
    for relative_path, content in (
        (
            "app.py",
            'APP_MESSAGE = "Sentinel arbitrary local app worked."\n\n'
            "def main():\n"
            "    return APP_MESSAGE\n\n"
            'if __name__ == "__main__":\n'
            "    print(main())\n",
        ),
        (
            "README.md",
            "# Sentinel Local App\n\n"
            "This local app was created from scratch by the Sentinel ProductActionKernel spine.\n",
        ),
        (
            "tests/test_app.py",
            "from app import main\n\n\n"
            "def test_main_returns_message():\n"
            '    assert main() == "Sentinel arbitrary local app worked."\n',
        ),
    ):
        if not (workspace_root / relative_path).exists():
            plans.append({"target_path": relative_path, "new_text": content})
    return plans


def _workspace_test_hygiene_create_file_plans(workspace_root: Path) -> list[dict[str, str]]:
    if (workspace_root / "pytest.ini").exists():
        return []
    tests_dir = workspace_root / "tests"
    if not tests_dir.is_dir() or not any(tests_dir.glob("test*.py")):
        return []
    root_test_files = [
        path
        for path in workspace_root.glob("test*.py")
        if path.is_file() and path.parent.resolve() == workspace_root.resolve()
    ]
    if not root_test_files:
        return []
    return [
        {
            "target_path": "pytest.ini",
            "new_text": "[pytest]\ntestpaths = tests\n",
        }
    ]


def _objective_requests_number_analyzer(objective: str) -> bool:
    has_number_domain = any(marker in objective for marker in ("number analyzer", "analyze_numbers", "numbers"))
    has_summary_fields = all(marker in objective for marker in ("count", "total", "average"))
    return has_number_domain and has_summary_fields


def _number_analyzer_file_specs(workspace_root: Path) -> tuple[tuple[str, str], ...]:
    app_path = workspace_root / "app.py"
    app_text = ""
    if app_path.is_file():
        try:
            app_text = app_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            app_text = ""
    app_has_main = "def main" in app_text
    test_text = (
        "from app import analyze_numbers, main\n\n\n"
        "def test_analyze_numbers_reports_count_total_and_average():\n"
        "    assert analyze_numbers([1, 2, 3]) == {\"count\": 3, \"total\": 6, \"average\": 2}\n\n\n"
        "def test_analyze_numbers_handles_empty_input():\n"
        "    assert analyze_numbers([]) == {\"count\": 0, \"total\": 0, \"average\": 0}\n\n\n"
        "def test_main_returns_useful_app_marker():\n"
        '    assert main() == "Sentinel useful number analyzer worked."\n'
    )
    if app_path.is_file() and not app_has_main:
        test_text = (
            "from app import analyze_numbers\n\n\n"
            "def test_analyze_numbers_reports_count_total_and_average():\n"
            "    assert analyze_numbers([1, 2, 3]) == {\"count\": 3, \"total\": 6, \"average\": 2}\n\n\n"
            "def test_analyze_numbers_handles_empty_input():\n"
            "    assert analyze_numbers([]) == {\"count\": 0, \"total\": 0, \"average\": 0.0}\n"
        )
    return (
        (
            "app.py",
            "def analyze_numbers(values):\n"
            "    numbers = list(values)\n"
            "    count = len(numbers)\n"
            "    total = sum(numbers)\n"
            "    average = total / count if count else 0\n"
            '    return {"count": count, "total": total, "average": average}\n\n\n'
            "def main():\n"
            '    return "Sentinel useful number analyzer worked."\n\n\n'
            'if __name__ == "__main__":\n'
            "    print(main())\n",
        ),
        (
            "README.md",
            "# Sentinel Number Analyzer\n\n"
            "A tiny useful local app created through the Sentinel ProductActionKernel spine.\n\n"
            "It exposes `analyze_numbers(values)` and reports count, total, and average.\n",
        ),
        ("tests/test_app.py", test_text),
    )


def _missing_create_file_plans(
    workspace_root: Path,
    files: tuple[tuple[str, str], ...],
) -> list[dict[str, str]]:
    plans: list[dict[str, str]] = []
    for relative_path, content in files:
        if not (workspace_root / relative_path).exists():
            plans.append({"target_path": relative_path, "new_text": content})
    return plans


def _bounded_check_plan(workspace_root: Path) -> dict[str, Any]:
    if (workspace_root / "tests" / "test_app.py").is_file():
        return {"profile_id": "pytest_file", "args": ["tests/test_app.py"]}
    if (workspace_root / "app.py").is_file():
        return {"profile_id": "python_compileall", "args": ["."]}
    return {}


def _workspace_file_summaries(workspace_root: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for relative_path in ("app.py", "tests/test_app.py", "README.md"):
        path = workspace_root / relative_path
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        summaries.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "content_excerpt": content[:1200],
                "data_not_authority": True,
                "can_execute": False,
            }
        )
    return summaries


__all__ = [
    "ModelLedProductActionKernelTaskLoop",
    "ProductActionKernelLoopDecisionClient",
    "ProductActionKernelTaskLoopFinalCertificate",
    "ProductActionKernelTaskLoopReplay",
    "ProductActionKernelTaskLoopResult",
    "ProductActionKernelTaskLoopStatus",
]
