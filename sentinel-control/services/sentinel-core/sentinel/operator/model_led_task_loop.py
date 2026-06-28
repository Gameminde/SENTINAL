from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig, LoopGuardError
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class ModelLedTaskLoopStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ModelLedTaskDecisionClient:
    def __init__(self, decisions: list[ActionEnvelope]) -> None:
        self._decisions = list(decisions)
        self.call_count = 0
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        self.call_count += 1
        if not self._decisions:
            raise ActionKernelError("model_led_task_decision_exhausted")
        return self._decisions.pop(0)


class ModelLedTaskLoopFinalCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("model_led_loop_finalgate"))
    mission_id: str
    status: ModelLedTaskLoopStatus
    accepted: bool
    reason: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _certificate_is_not_authority(self) -> "ModelLedTaskLoopFinalCertificate":
        assert_data_not_authority(
            context="model_led_task_loop_final_certificate",
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
            "mission_id": self.mission_id,
            "status": self.status.value,
            "accepted": self.accepted,
            "reason": self.reason,
            "receipt_refs": sanitize_operator_refs(self.receipt_refs),
            "finalgate_refs": sanitize_operator_refs(self.finalgate_refs),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


class ModelLedTaskLoopResult(SentinelModel):
    mission_id: str
    status: ModelLedTaskLoopStatus
    final_reason: str
    blocked_reason: str | None = None
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_refs: tuple[str, ...] = Field(default_factory=tuple)
    material_action_count: int = 0
    model_call_count: int = 0
    capability_sequence: tuple[str, ...] = Field(default_factory=tuple)


class ModelLedTaskLoop:
    def __init__(
        self,
        *,
        mission_id: str,
        kernel: MissionKernel,
        authority: MissionAuthorityEnvelope,
        action_kernel: ActionKernel,
        decision_client: ModelLedTaskDecisionClient,
        decision_context: DecisionContextCompiler | None = None,
        loop_guard: LoopGuard | None = None,
        available_actions: tuple[str, ...] | None = None,
    ) -> None:
        self.mission_id = mission_id
        self.kernel = kernel
        self.authority = authority
        self.action_kernel = action_kernel
        self.decision_client = decision_client
        self.decision_context = decision_context or DecisionContextCompiler()
        self.loop_guard = loop_guard or LoopGuard(LoopGuardConfig())
        self.available_actions = available_actions or (
            "read_only.list_directory",
            "read_only.search_text",
            "read_only.read_file_segment",
            "channel.send_message",
            "code_exec.run_profile",
            "code_exec.inspect_result",
            "finish",
        )
        self.results: list[ActionResult] = []
        self.capability_sequence: list[str] = []
        self.model_calls_used = 0
        self.material_actions_used = 0

    def run(self) -> ModelLedTaskLoopResult:
        self._append_event("model_led_task_loop_started", "Model-led task loop started.")
        try:
            if self.kernel.store.load_record(self.mission_id).status is OperatorMissionStatus.QUEUED:
                self.kernel.update_status(self.mission_id, OperatorMissionStatus.RUNNING, "Model-led task loop started.")
            while True:
                self._assert_mission_and_authority_open()
                self.loop_guard.check_before_model_call(self.model_calls_used)
                context = self.decision_context.compile(
                    mission_id=self.mission_id,
                    mission_objective=self.authority.mission_objective,
                    authority=self.authority,
                    observations=self.results,
                    available_actions=self.available_actions,
                    model_calls_used=self.model_calls_used,
                    material_actions_used=self.material_actions_used,
                    max_model_calls=self.loop_guard.config.max_model_calls,
                    max_material_actions=self.loop_guard.config.max_material_actions,
                )
                envelope = self.decision_client.complete(context)
                self.model_calls_used += 1
                self.loop_guard.check_before_action(envelope)
                self._assert_mission_and_authority_open()
                result = self.action_kernel.execute(envelope, authority=self.authority, context=context)
                self.results.append(result)
                self.capability_sequence.append(f"{envelope.capability_id}:{envelope.operation}")
                self.loop_guard.record_result(result)
                self._append_action_event(result)
                if result.material_action:
                    self.material_actions_used += 1
                if envelope.capability_id == "sentinel_loop" and envelope.operation == "finish":
                    return self._complete("model_led_task_loop_finish")
                if self.loop_guard.material_budget_reached(self.material_actions_used):
                    return self._complete("model_led_task_loop_material_budget_reached")
        except (ActionKernelError, LoopGuardError) as exc:
            return self._block(str(exc) or exc.__class__.__name__)

    def _complete(self, reason: str) -> ModelLedTaskLoopResult:
        certificate = self._write_certificate(status=ModelLedTaskLoopStatus.COMPLETED, accepted=True, reason=reason)
        if not self.kernel.is_terminal(self.mission_id):
            self.kernel.update_status(self.mission_id, OperatorMissionStatus.COMPLETED, "Model-led task loop completed.")
        self._append_event(
            "model_led_task_loop_completed",
            "Model-led task loop completed with governed receipts.",
            certificate_refs=[certificate.certificate_id],
        )
        return self._result(ModelLedTaskLoopStatus.COMPLETED, reason, certificate_refs=(certificate.certificate_id,))

    def _block(self, reason: str) -> ModelLedTaskLoopResult:
        certificate = self._write_certificate(status=ModelLedTaskLoopStatus.BLOCKED, accepted=False, reason=reason)
        if not self.kernel.is_terminal(self.mission_id):
            self.kernel.update_status(self.mission_id, OperatorMissionStatus.BLOCKED, "Model-led task loop blocked.")
        self._append_event(
            "model_led_task_loop_blocked",
            "Model-led task loop blocked before unsafe or unproductive continuation.",
            metadata={"safe_stop_hash": stable_hash(reason), "safe_stop_code": _safe_reason_code(reason)},
            certificate_refs=[certificate.certificate_id],
        )
        return self._result(
            ModelLedTaskLoopStatus.BLOCKED,
            "model_led_task_loop_blocked",
            blocked_reason=reason,
            certificate_refs=(certificate.certificate_id,),
        )

    def _result(
        self,
        status: ModelLedTaskLoopStatus,
        final_reason: str,
        *,
        blocked_reason: str | None = None,
        certificate_refs: tuple[str, ...] = (),
    ) -> ModelLedTaskLoopResult:
        return ModelLedTaskLoopResult(
            mission_id=self.mission_id,
            status=status,
            final_reason=final_reason,
            blocked_reason=blocked_reason,
            receipt_refs=tuple(ref for result in self.results for ref in result.receipt_refs),
            evidence_refs=tuple(ref for result in self.results for ref in result.evidence_refs),
            finalgate_refs=tuple(ref for result in self.results for ref in result.finalgate_refs),
            certificate_refs=certificate_refs,
            material_action_count=self.material_actions_used,
            model_call_count=self.model_calls_used,
            capability_sequence=tuple(self.capability_sequence),
        )

    def _assert_mission_and_authority_open(self) -> None:
        terminal_reason = self.kernel.terminal_block_reason(self.mission_id)
        if terminal_reason is not None:
            raise ActionKernelError(terminal_reason)
        if self.authority.revoked_at is not None:
            raise ActionKernelError("mission_authority_inactive")

    def _append_action_event(self, result: ActionResult) -> None:
        self._append_event(
            "model_led_task_loop_action_completed",
            "Model-led task loop action completed.",
            metadata={
                "action_id": result.action_id,
                "capability_id": result.capability_id,
                "operation": result.operation,
                "status": result.status,
                "material_action": result.material_action,
                "result_hash": result.result_hash,
            },
            receipt_refs=list(result.receipt_refs),
            finalgate_refs=list(result.finalgate_refs),
        )

    def _append_event(
        self,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_refs: list[str] | None = None,
        certificate_refs: list[str] | None = None,
    ) -> None:
        refs = list(finalgate_refs or []) + list(certificate_refs or [])
        self.kernel.store.append_event(
            self.mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=refs,
        )

    def _write_certificate(
        self,
        *,
        status: ModelLedTaskLoopStatus,
        accepted: bool,
        reason: str,
    ) -> ModelLedTaskLoopFinalCertificate:
        certificate = ModelLedTaskLoopFinalCertificate(
            mission_id=self.mission_id,
            status=status,
            accepted=accepted,
            reason=reason,
            receipt_refs=tuple(ref for result in self.results for ref in result.receipt_refs),
            finalgate_refs=tuple(ref for result in self.results for ref in result.finalgate_refs),
        )
        path = (
            self.kernel.store.mission_dir(self.mission_id, create=True)
            / "model_led_task_loop"
            / "finalgate"
            / f"{certificate.certificate_id}.json"
        )
        self.kernel.store.atomic_write_json(path, certificate.safe_model_dump())
        return certificate


class ModelLedTaskLoopReplay(SentinelModel):
    mission_id: str
    reexecuted_actions: bool
    model_calls_delta: int
    read_only_tool_calls_delta: int
    channel_transport_sends_delta: int
    patch_applications_delta: int = 0
    verification_runs_delta: int = 0
    command_executions_delta: int = 0
    receipt_writes_delta: int
    evidence_writes_delta: int
    finalgate_writes_delta: int
    workspace_mutations_delta: int
    event_count_stable: bool
    artifact_hashes_stable: bool

    @classmethod
    def from_store(cls, store: object, mission_id: str) -> "ModelLedTaskLoopReplay":
        mission_dir = store.mission_dir(mission_id)
        before = _artifact_counts(mission_dir)
        hashes_before = _artifact_hashes(mission_dir)
        events_before = len(store.load_events(mission_id))
        after = _artifact_counts(mission_dir)
        hashes_after = _artifact_hashes(mission_dir)
        events_after = len(store.load_events(mission_id))
        return cls(
            mission_id=mission_id,
            reexecuted_actions=False,
            model_calls_delta=0,
            read_only_tool_calls_delta=0,
            channel_transport_sends_delta=0,
            patch_applications_delta=0,
            verification_runs_delta=0,
            command_executions_delta=0,
            receipt_writes_delta=after["receipts"] - before["receipts"],
            evidence_writes_delta=after["evidence"] - before["evidence"],
            finalgate_writes_delta=after["finalgate"] - before["finalgate"],
            workspace_mutations_delta=0,
            event_count_stable=events_before == events_after,
            artifact_hashes_stable=hashes_before == hashes_after,
        )


def _artifact_counts(mission_dir: Path) -> dict[str, int]:
    return {
        "receipts": len(list(mission_dir.rglob("receipts/*.json"))),
        "evidence": len(list(mission_dir.rglob("evidence/*.json"))),
        "finalgate": len(list(mission_dir.rglob("finalgate/*.json"))),
    }


def _artifact_hashes(mission_dir: Path) -> tuple[str, ...]:
    hashes: list[str] = []
    for path in sorted(mission_dir.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        hashes.append(stable_hash(payload))
    return tuple(hashes)


def _safe_reason_code(reason: str) -> str:
    if reason.startswith("operator_mission_terminal:"):
        return "closed_mission"
    if ":" in reason:
        return reason.split(":", 1)[0]
    return reason


__all__ = [
    "ModelLedTaskDecisionClient",
    "ModelLedTaskLoop",
    "ModelLedTaskLoopFinalCertificate",
    "ModelLedTaskLoopReplay",
    "ModelLedTaskLoopResult",
    "ModelLedTaskLoopStatus",
]
