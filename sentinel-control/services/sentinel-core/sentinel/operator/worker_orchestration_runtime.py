from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.mission_workspace_runtime import MissionWorkspaceRuntime
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.operator.worker_fleet import WorkerFleetRuntime
from sentinel.operator.worker_models import (
    WorkerBudget,
    WorkerDeadline,
    WorkerEvidencePacket,
    WorkerExecutionContext,
    WorkerExecutionMode,
    WorkerFleetConfig,
    WorkerResult,
    WorkerResultContract,
    WorkerRole,
    WorkerScope,
    WorkerSpawnRequest,
    WorkerTask,
    WorkerTaskStatus,
)
from sentinel.shared.models import SentinelModel, new_id


MODEL_WORKER_ROLES: dict[str, tuple[WorkerRole, WorkerExecutionMode]] = {
    "researcher": (WorkerRole.RESEARCHER, WorkerExecutionMode.RESEARCH),
    "browser_operator": (WorkerRole.POWER_OPERATOR, WorkerExecutionMode.POWER_RUNTIME),
    "code_fixer": (WorkerRole.POWER_OPERATOR, WorkerExecutionMode.POWER_RUNTIME),
    "verifier": (WorkerRole.VERIFIER, WorkerExecutionMode.VERIFICATION),
    "report_writer": (WorkerRole.ANALYST, WorkerExecutionMode.ANALYSIS),
}

WORKER_HARD_BOUNDARY_MARKERS = (
    "account",
    "checkout",
    "contact supplier",
    "contact_supplier",
    "credential",
    "login",
    "password",
    "payment",
    "secret",
    "spend",
)


class WorkerOrchestrationReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("worker_fleet_receipt"))
    mission_id: str
    execution_request_id: str
    decision_id: str
    action_id: str
    worker_fleet_run_id: str
    worker_id: str
    worker_role: str
    requested_skill_scope: list[str] = Field(default_factory=list)
    delegated_skill_scope: list[str] = Field(default_factory=list)
    mission_workspace_ref: str
    mission_workspace_hash: str
    worker_pool_ref: str
    worker_pool_hash: str
    child_authority: dict[str, Any]
    child_authority_hash: str
    authority_expanded: bool = False
    worker_result_hash: str
    result_summary_hash: str
    product_dispatch_owner: str = "product_action_kernel_adapter"
    simple_skill: str = "spawn_worker"
    internal_action_id: str = "worker_fleet.spawn_worker"
    status: str = "completed"
    replay_behavior: str = "no_respawn_no_reexecute_on_replay"
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "WorkerOrchestrationReceipt":
        assert_data_not_authority(
            context="worker_orchestration_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def with_hash(self) -> "WorkerOrchestrationReceipt":
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "decision_id": self.decision_id,
            "action_id": self.action_id,
            "worker_fleet_run_id": self.worker_fleet_run_id,
            "worker_id": self.worker_id,
            "worker_role": redact_operator_text(self.worker_role),
            "requested_skill_scope": sanitize_operator_refs(self.requested_skill_scope),
            "delegated_skill_scope": sanitize_operator_refs(self.delegated_skill_scope),
            "mission_workspace_ref": self.mission_workspace_ref,
            "mission_workspace_hash": self.mission_workspace_hash,
            "worker_pool_ref": self.worker_pool_ref,
            "worker_pool_hash": self.worker_pool_hash,
            "child_authority": self.child_authority,
            "child_authority_hash": self.child_authority_hash,
            "authority_expanded": self.authority_expanded,
            "worker_result_hash": self.worker_result_hash,
            "result_summary_hash": self.result_summary_hash,
            "product_dispatch_owner": self.product_dispatch_owner,
            "simple_skill": self.simple_skill,
            "internal_action_id": self.internal_action_id,
            "status": self.status,
            "replay_behavior": self.replay_behavior,
            "receipt_hash": self.receipt_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class WorkerOrchestrationRuntime:
    """Product-spine worker delegation bridge.

    This runtime does not create new authority and does not run provider calls.
    It turns a model-visible `spawn_worker` skill into a local worker-fleet run
    with a strictly reduced child authority and product receipts.
    """

    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        workspace_root: Path,
        product_context: dict[str, Any],
    ) -> None:
        self._kernel = kernel
        self._mission_id = mission_id
        self._workspace_root = workspace_root
        self._product_context = dict(product_context)

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        params = dict(envelope.params)
        public_role = _public_worker_role(params)
        worker_role, execution_mode = _worker_role(public_role)
        objective = redact_operator_text(str(params.get("objective") or "Run a bounded worker subtask."))
        requested_skills = _requested_skills(params)

        manifest = MissionWorkspaceRuntime(self._kernel).prepare(
            mission_id=self._mission_id,
            workspace_root=self._workspace_root,
            allowed_domains=tuple(authority.allowed_domains or ()),
        )
        manifest_payload = manifest.safe_model_dump()
        worker_pool = _mission_workspace_worker_pool_handle(manifest_payload)
        delegated_skills = _delegated_worker_skills(requested_skills, authority)
        task = WorkerTask(
            task_id="worker_task_1",
            role=worker_role,
            execution_mode=execution_mode,
            objective=objective,
            scope=WorkerScope(
                allowed_actions=_worker_allowed_actions(authority),
                allowed_tools=["worker_fleet"] if "worker_fleet" in set(authority.allowed_tools or []) else [],
                allowed_systems=[item for item in ["local_workspace"] if item in set(authority.allowed_systems or [])],
                allowed_paths=[str(self._workspace_root)] if str(self._workspace_root) in set(authority.allowed_paths or []) else [],
                allowed_domains=[domain for domain in ("local.worker",) if domain in set(authority.allowed_domains or [])],
            ),
            budget=WorkerBudget(max_actions=min(int(params.get("max_actions") or 1), 1), max_cost_usd=0.0),
            deadline=WorkerDeadline(timeout_seconds=60),
            result_contract=WorkerResultContract(
                required_evidence_refs=0,
                require_receipt_refs_for_execution=False,
                require_finalgate_refs_for_execution=False,
            ),
            metadata={"requested_skill_scope": requested_skills, "delegated_skill_scope": delegated_skills},
        )
        spawn_request = WorkerSpawnRequest(
            mission_id=self._mission_id,
            requested_by="model_led_product_action_kernel",
            tasks=[task],
            safe_reason=f"Spawn {public_role} worker inside mission workspace.",
            config=WorkerFleetConfig(max_workers=1, require_certified_telemetry=False),
            metadata={"mission_workspace_ref": manifest.manifest_id, "worker_pool_ref": worker_pool.get("safe_ref")},
        )
        fleet = WorkerFleetRuntime(self._kernel, config=spawn_request.config)
        run = fleet.run(
            mission_id=self._mission_id,
            parent_envelope=authority,
            spawn_request=spawn_request,
            worker_executor=_local_worker_executor,
        )
        if run.status.value != "completed" or not run.worker_results or not run.child_authority_envelopes:
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="blocked",
                material_action=False,
                blocked_reason=run.blocked_reason or f"worker_fleet_{run.status.value}",
                observation_summary="Worker fleet did not complete.",
            )

        child = run.child_authority_envelopes[0]
        worker_result = run.worker_results[0]
        receipt = WorkerOrchestrationReceipt(
            mission_id=self._mission_id,
            execution_request_id=str(context.get("execution_request_id") or ""),
            decision_id=str(context.get("decision_id") or ""),
            action_id=envelope.action_id,
            worker_fleet_run_id=run.worker_fleet_run_id,
            worker_id=child.worker_id,
            worker_role=public_role,
            requested_skill_scope=requested_skills,
            delegated_skill_scope=delegated_skills,
            mission_workspace_ref=manifest.manifest_id,
            mission_workspace_hash=manifest.manifest_hash,
            worker_pool_ref=str(worker_pool.get("safe_ref") or ""),
            worker_pool_hash=stable_hash(worker_pool),
            child_authority=child.safe_model_dump(),
            child_authority_hash=child.authority_hash,
            authority_expanded=False,
            worker_result_hash=worker_result.result_hash,
            result_summary_hash=text_hash(worker_result.safe_summary),
        ).with_hash()
        receipt_path = (
            self._kernel.store.mission_dir(self._mission_id, create=True)
            / "worker_fleet"
            / "receipts"
            / f"{receipt.receipt_id}.json"
        )
        self._kernel.store.atomic_write_json(receipt_path, receipt.safe_model_dump())
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(receipt.receipt_id,),
            evidence_refs=(run.worker_fleet_run_id,),
            material_action=True,
            observation_summary=f"Spawned {public_role} worker with reduced authority.",
            context_cards={
                "worker_orchestration": {
                    "worker_role": public_role,
                    "worker_fleet_run_id": run.worker_fleet_run_id,
                    "delegated_skill_scope": delegated_skills,
                    "child_authority_hash": child.authority_hash,
                    "worker_pool_ref_hash": stable_hash(worker_pool.get("safe_ref") or ""),
                }
            },
        )


def worker_orchestration_preflight(params: dict[str, Any]) -> str | None:
    rendered = " ".join(_flatten_strings(params)).lower()
    if any(marker in rendered for marker in WORKER_HARD_BOUNDARY_MARKERS):
        return "worker_fleet_hard_boundary_requested"
    public_role = str(params.get("role") or "").strip().lower()
    if public_role and public_role not in MODEL_WORKER_ROLES:
        return "worker_fleet_role_not_supported"
    return None


def _local_worker_executor(context: WorkerExecutionContext) -> WorkerResult:
    return WorkerResult(
        worker_id=context.worker_id,
        task_id=context.task_id,
        status=WorkerTaskStatus.COMPLETED,
        result_contract_id=context.result_contract.contract_id,
        safe_summary=f"{context.role.value} completed bounded local worker task.",
        output={
            "worker_role": context.role.value,
            "delegated_action_count": len(context.child_authority.allowed_actions),
            "child_scope_hash": stable_hash(context.child_authority.allowed_actions),
        },
        evidence_packet=WorkerEvidencePacket(),
        actions_used=min(context.budget.max_actions, 1),
        cost_usd=0.0,
    )


def _public_worker_role(params: dict[str, Any]) -> str:
    role = str(params.get("role") or "researcher").strip().lower()
    return role if role in MODEL_WORKER_ROLES else "researcher"


def _worker_role(public_role: str) -> tuple[WorkerRole, WorkerExecutionMode]:
    return MODEL_WORKER_ROLES.get(public_role, MODEL_WORKER_ROLES["researcher"])


def _requested_skills(params: dict[str, Any]) -> list[str]:
    value = params.get("delegated_skills")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple):
        return list(dict.fromkeys(str(item) for item in value if str(item).strip()))
    return []


def _delegated_worker_skills(requested_skills: list[str], authority: MissionAuthorityEnvelope) -> list[str]:
    delegated: list[str] = []
    if "worker_fleet" in set(authority.allowed_tools or []) and "worker_fleet.spawn_worker" in set(authority.allowed_actions or []):
        delegated.append("spawn_worker")
    return [skill for skill in dict.fromkeys(delegated) if not requested_skills or skill in set(requested_skills) or skill == "spawn_worker"]


def _worker_allowed_actions(authority: MissionAuthorityEnvelope) -> list[str]:
    return [action for action in ("worker_fleet.spawn_worker",) if action in set(authority.allowed_actions or [])]


def _mission_workspace_worker_pool_handle(manifest: dict[str, Any]) -> dict[str, Any]:
    for handle in manifest.get("handles", []):
        if isinstance(handle, dict) and handle.get("kind") == "worker_pool":
            return handle
    raise RuntimeError("mission_workspace_worker_pool_handle_missing")


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        output: list[str] = []
        for key, child in value.items():
            output.append(str(key))
            output.extend(_flatten_strings(child))
        return output
    if isinstance(value, list | tuple | set):
        output: list[str] = []
        for child in value:
            output.extend(_flatten_strings(child))
        return output
    return [str(value)] if value is not None else []


__all__ = [
    "WorkerOrchestrationReceipt",
    "WorkerOrchestrationRuntime",
    "worker_orchestration_preflight",
]
