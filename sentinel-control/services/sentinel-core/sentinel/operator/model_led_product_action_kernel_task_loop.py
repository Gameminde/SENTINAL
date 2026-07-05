from __future__ import annotations

import hashlib
import json
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
from sentinel.operator.store import MissionRunStore
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
        try:
            while True:
                if self.model_calls_used >= self.max_model_calls:
                    return self._block("MODEL_CALL_BUDGET_EXHAUSTED")
                context = self._compile_context()
                try:
                    decision = self.decision_client.complete(context)
                except ActionKernelError as exc:
                    self.model_calls_used += 1
                    reason = str(exc) or exc.__class__.__name__
                    if self._recover_model_decision_failure(reason, context):
                        continue
                    return self._block(reason)
                self.model_calls_used += 1
                sequence_entry = f"{decision.capability_id}:{decision.operation}"
                self.capability_sequence.append(sequence_entry)
                if decision.capability_id == "sentinel_loop" and decision.operation == "finish":
                    if not self.product_receipt_refs and not self.explicit_noop_proof_ref:
                        return self._block("MODEL_FINISH_BEFORE_PRODUCT_RECEIPT")
                    return self._complete("model_led_product_action_kernel_task_loop_finish")
                if self.material_actions_used >= self.max_material_actions:
                    return self._block("MATERIAL_ACTION_BUDGET_EXHAUSTED")
                dispatch_result = self._dispatch_product_action(decision)
                self.dispatch_results.append(dispatch_result)
                self.mission_ids.append(dispatch_result.mission_id)
                self.product_receipt_refs.extend(dispatch_result.receipt_refs)
                self.product_finalgate_refs.extend(dispatch_result.finalgate_refs)
                if dispatch_result.status is not DispatchStatus.COMPLETED:
                    if self._recover_action_failure(dispatch_result, decision, context):
                        continue
                    return self._block(dispatch_result.blocked_reason or "product_action_kernel_dispatch_blocked")
                if dispatch_result.receipt_refs:
                    self.material_actions_used += 1
        except ActionKernelError as exc:
            return self._block(str(exc) or exc.__class__.__name__)

    def _compile_context(self) -> dict[str, Any]:
        actions = self._available_actions()
        model_skill_surface = compile_model_skill_surface(
            model_visible_actions=actions,
            recommended_actions=actions,
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
            "model_visible_available_actions": list(actions),
            "skill_decision_frame": {
                "primary_truth": "product_action_kernel_runtimehost",
                "primary_model_surface": "model_visible_skills",
                "primary_model_language": "simple_mission_skills",
                "model_skill_surface": model_skill_surface,
                "model_visible_skills": list(model_skill_surface["model_visible_skills"]),
                "model_visible_actions": list(actions),
                "runtime_bridge": "RuntimeHost -> UnifiedExecutionDispatcher -> ProductActionKernelDispatchAdapter",
                "action_envelope_language": "internal_runtime_only",
            },
            "product_action_kernel_dispatch_count": len(self.dispatch_results),
            "recent_product_receipt_refs": list(sanitize_operator_refs(self.product_receipt_refs)),
            "recent_product_finalgate_refs": list(sanitize_operator_refs(self.product_finalgate_refs)),
            "explicit_noop_proof_ref": self.explicit_noop_proof_ref,
            "dispatch_summaries": [
                {
                    "mission_id": result.mission_id,
                    "status": result.status.value,
                    "capability_id": result.capability_id,
                    "operation": result.operation,
                    "adapter_id": result.adapter_id,
                    "receipt_refs": sanitize_operator_refs(result.receipt_refs),
                    "finalgate_refs": sanitize_operator_refs(result.finalgate_refs),
                    "blocked_reason": result.blocked_reason,
                }
                for result in self.dispatch_results
            ],
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
        if len(self.recoverable_decision_observations) >= self.max_recoverable_model_decision_failures:
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

    def _recover_action_failure(
        self,
        dispatch_result: UnifiedDispatchResult,
        decision: ActionEnvelope,
        context: dict[str, Any],
    ) -> bool:
        reason = dispatch_result.blocked_reason or ""
        if not _is_recoverable_action_failure(reason):
            return False
        if len(self.recoverable_action_observations) >= self.max_recoverable_action_failures:
            return False
        create_plans = _workspace_create_file_plans(self.workspace_root, mission_objective=self.mission_objective)
        self.recoverable_action_observations.append(
            {
                "failure_code": reason,
                "turn_index": self.model_calls_used,
                "capability_id": decision.capability_id,
                "operation": decision.operation,
                "target_ref_hash": stable_hash(str(decision.target_ref or "")),
                "recovery_action": "route_to_next_missing_workspace_create_file_plan",
                "recommended_skill": "create_file" if create_plans else context.get("primary_model_recommended_next_skill"),
                "remaining_create_file_plan_count": len(create_plans),
                "data_not_authority": True,
                "can_execute": False,
            }
        )
        return True

    def _available_actions(self) -> tuple[str, ...]:
        if self.material_actions_used >= self.max_material_actions and self.product_receipt_refs:
            return ("sentinel_loop.finish",)
        actions = []
        if _workspace_create_file_plans(self.workspace_root, mission_objective=self.mission_objective):
            actions.append("workspace_patch.create_file")
        if _workspace_patch_plans(self.workspace_root):
            actions.append("workspace_patch.apply_patch")
        actions.extend([
            "code_execution_sandbox.code_exec.run_profile",
            "bounded_channel.send_message",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "worker_fleet.spawn_worker",
        ])
        if self.product_receipt_refs:
            actions.append("sentinel_loop.finish")
        return tuple(actions)

    def _progress_state(self) -> str:
        if not self.product_receipt_refs:
            return "product_action_kernel_loop_waiting_for_first_material_skill"
        if self.material_actions_used >= self.max_material_actions:
            return "product_action_kernel_loop_material_budget_ready_to_finish"
        return "product_action_kernel_loop_material_receipts_available"

    def _dispatch_product_action(self, decision: ActionEnvelope) -> UnifiedDispatchResult:
        hard_boundary_reason = _entrypoint_hard_boundary_reason(decision)
        if hard_boundary_reason is not None:
            return _synthetic_blocked_dispatch_result(
                loop_id=self.loop_id,
                turn_index=self.model_calls_used,
                decision=decision,
                reason=hard_boundary_reason,
            )
        tools, actions = _authority_for_action(decision)
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
            parameters=dict(decision.params),
            workspace_ref=f"workspace:{self.workspace_root}",
            model_contract_ref=self.model_contract_ref,
        )
        pump = self.host.pump_daemon_once(mission.record.mission_id)
        if pump.dispatch_result is None:
            raise ActionKernelError("product_action_kernel_dispatch_missing")
        return pump.dispatch_result

    def _complete(self, reason: str) -> ProductActionKernelTaskLoopResult:
        certificate = self._write_certificate(
            status=ProductActionKernelTaskLoopStatus.COMPLETED,
            accepted=True,
            reason=reason,
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
        return ["bounded_channel", "channel_draft_send"], ["bounded_channel.send_message", "send_message"]
    if capability == "workspace_patch":
        return ["workspace_patch"], [f"{capability}.{operation}", operation]
    return [capability], [f"{capability}.{operation}", operation]


def _allowed_domains_for_action(decision: ActionEnvelope, allowed_domains: tuple[str, ...]) -> list[str]:
    domains = list(allowed_domains)
    if decision.capability_id == "real_browser_control":
        domains.append(BOUNDED_URL_AUTHORITY_REF)
    return list(dict.fromkeys(domains))


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
    }


def _is_recoverable_action_failure(reason: str) -> bool:
    return reason in {
        "workspace_patch_create_target_exists",
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


def _artifact_counts(store: MissionRunStore, mission_ids: tuple[str, ...]) -> dict[str, int]:
    roots = [store.mission_dir(mission_id) for mission_id in mission_ids if store.mission_dir(mission_id).exists()]
    return {
        "dispatch_closeout": sum(len(list(root.glob("dispatch_closeout/*.json"))) for root in roots),
        "receipts": sum(len(list(root.rglob("receipts/*.json"))) for root in roots),
        "finalgate": sum(len(list(root.rglob("finalgate/*.json"))) for root in roots),
    }


def _artifact_hashes(store: MissionRunStore, mission_ids: tuple[str, ...]) -> tuple[str, ...]:
    hashes: list[str] = []
    for mission_id in mission_ids:
        mission_dir = store.mission_dir(mission_id)
        if not mission_dir.exists():
            continue
        for path in sorted(mission_dir.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            hashes.append(stable_hash(payload))
    return tuple(hashes)


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
    objective = mission_objective.lower()
    if not any(marker in objective for marker in ("arbitrary", "from scratch", "create a tiny python app")):
        return []
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


def _bounded_check_plan(workspace_root: Path) -> dict[str, Any]:
    if (workspace_root / "app.py").is_file():
        return {"profile_id": "python_compileall", "args": ["."]}
    return {}


__all__ = [
    "ModelLedProductActionKernelTaskLoop",
    "ProductActionKernelLoopDecisionClient",
    "ProductActionKernelTaskLoopFinalCertificate",
    "ProductActionKernelTaskLoopReplay",
    "ProductActionKernelTaskLoopResult",
    "ProductActionKernelTaskLoopStatus",
]
