from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.mission.cancellation import CancellationToken
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


class PowerActuatorCapabilityLevel(StrEnum):
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"


class PowerActuatorFamily(StrEnum):
    BROWSER = "browser"
    SHELL_SANDBOX = "shell_sandbox"
    CODE_EXECUTION = "code_execution"
    EXTERNAL_API = "external_api"
    CHANNEL = "channel"
    WORKSPACE = "workspace"
    CREDENTIAL_REF = "credential_ref"


class PowerStepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"
    ABORTED = "aborted"


class PowerRuntimeStatus(StrEnum):
    NOT_STARTED = "not_started"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    ABORTED = "aborted"


class PowerMissionStep(SentinelModel):
    step_id: str
    actuator_family: PowerActuatorFamily
    capability_level: PowerActuatorCapabilityLevel
    organ_kind: str
    action_kind: str
    request: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    retry_budget: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    safe_summary: str | None = None
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _step_is_not_authority_or_raw_payload(self) -> PowerMissionStep:
        if self.authority_effect != "none":
            raise ValueError("power mission step cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("power mission step must remain data-not-instruction")
        _reject_control_plane_payload(self.request, path=f"$.steps[{self.step_id}].request")
        _reject_control_plane_payload(
            {
                "organ_kind": self.organ_kind,
                "action_kind": self.action_kind,
                "safe_summary": self.safe_summary,
            },
            path=f"$.steps[{self.step_id}].metadata",
        )
        return self


class PowerMissionGraph(SentinelModel):
    steps: list[PowerMissionStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_step_ids(self) -> PowerMissionGraph:
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError(f"duplicate power mission step id: {step.step_id}")
            seen.add(step.step_id)
        return self


class PowerMissionPlan(SentinelModel):
    mission_id: str
    graph: PowerMissionGraph
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _plan_is_not_authority(self) -> PowerMissionPlan:
        if self.authority_effect != "none":
            raise ValueError("power mission plan cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("power mission plan must remain data-not-instruction")
        return self


class PowerStepResult(SentinelModel):
    step_id: str
    status: PowerStepStatus
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    safe_summary: str = ""
    attempt_count: int = Field(default=1, ge=0)
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_execute_more: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _result_cannot_grant_authority(self) -> PowerStepResult:
        if self.authority_effect != "none":
            raise ValueError("power step result cannot grant authority")
        if self.can_grant_authority or self.can_approve_future_execution or self.can_execute_more:
            raise ValueError("power step result cannot approve or extend execution")
        if self.data_not_instruction is not True:
            raise ValueError("power step result must remain data-not-instruction")
        _reject_control_plane_payload(
            {
                "receipt_refs": self.receipt_refs,
                "finalgate_certificate_refs": self.finalgate_certificate_refs,
                "memory_feedback_refs": self.memory_feedback_refs,
                "blocked_reason": self.blocked_reason,
                "safe_summary": self.safe_summary,
            },
            path=f"$.step_results[{self.step_id}]",
        )
        return self


class PowerMissionTimelineItem(SentinelModel):
    event_id: str = Field(default_factory=lambda: new_id("power_event"))
    mission_id: str
    sequence: int = Field(ge=0)
    step_id: str | None = None
    event_type: str
    safe_summary: str
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    previous_hash: str | None = None
    event_hash: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _timeline_item_is_data(self) -> PowerMissionTimelineItem:
        if self.authority_effect != "none":
            raise ValueError("power timeline item cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("power timeline item must remain data-not-instruction")
        return self


class PowerMissionTimeline(SentinelModel):
    mission_id: str
    items: list[PowerMissionTimelineItem] = Field(default_factory=list)

    def record(
        self,
        event_type: str,
        safe_summary: str,
        *,
        step_id: str | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
        blocked_reason: str | None = None,
    ) -> PowerMissionTimelineItem:
        previous_hash = self.items[-1].event_hash if self.items else None
        item = PowerMissionTimelineItem(
            mission_id=self.mission_id,
            sequence=len(self.items),
            step_id=step_id,
            event_type=event_type,
            safe_summary=safe_summary,
            receipt_refs=list(receipt_refs or []),
            finalgate_certificate_refs=list(finalgate_certificate_refs or []),
            memory_feedback_refs=list(memory_feedback_refs or []),
            blocked_reason=blocked_reason,
            previous_hash=previous_hash,
        )
        item = item.model_copy(update={"event_hash": _hash_timeline_item(item)})
        self.items.append(item)
        return item

    def verify_chain(self) -> bool:
        previous_hash: str | None = None
        for index, item in enumerate(self.items):
            if item.sequence != index:
                return False
            if item.previous_hash != previous_hash:
                return False
            if _hash_timeline_item(item) != item.event_hash:
                return False
            previous_hash = item.event_hash
        return True


class PowerRuntimeConfig(SentinelModel):
    enabled: bool = False
    default_retry_budget: int = Field(default=0, ge=0)
    fail_fast: bool = True
    record_memory_feedback_refs: bool = True
    max_steps: int = Field(default=50, ge=1)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _config_is_not_authority(self) -> PowerRuntimeConfig:
        if self.authority_effect != "none":
            raise ValueError("power runtime config cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("power runtime config must remain data-not-instruction")
        return self


class PowerRuntimeResult(SentinelModel):
    mission_id: str
    status: PowerRuntimeStatus
    step_results: list[PowerStepResult] = Field(default_factory=list)
    timeline: PowerMissionTimeline
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    replan_ready: bool = True
    automatic_replan_executed: bool = False
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_execute_more: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _runtime_result_is_not_authority(self) -> PowerRuntimeResult:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("power runtime result cannot grant authority or execute more")
        if self.can_grant_authority or self.can_approve_future_execution or self.can_execute_more:
            raise ValueError("power runtime result cannot approve future execution")
        if self.automatic_replan_executed is not False:
            raise ValueError("power runtime v0 does not execute automatic replans")
        if self.data_not_instruction is not True:
            raise ValueError("power runtime result must remain data-not-instruction")
        return self


PowerActuatorExecutor = Callable[[PowerMissionStep, dict[str, Any]], PowerStepResult]
PowerMemoryFeedbackBuilder = Callable[[PowerMissionStep, PowerStepResult, dict[str, Any]], list[str]]


class SentinelPowerRuntimeV0:
    """Mission-level actuator orchestrator.

    V0 deliberately does not know how to browse, call APIs, send messages, or
    run shell commands. It sequences typed power steps and delegates execution
    to an injected executor, making the orchestration layer testable without
    opening a hidden authority path.
    """

    def run(
        self,
        plan: PowerMissionPlan,
        *,
        config: PowerRuntimeConfig | None = None,
        actuator_executor: PowerActuatorExecutor | None = None,
        cancellation_token: CancellationToken | None = None,
        memory_feedback_builder: PowerMemoryFeedbackBuilder | None = None,
    ) -> PowerRuntimeResult:
        runtime_config = config or PowerRuntimeConfig()
        timeline = PowerMissionTimeline(mission_id=plan.mission_id)
        if not runtime_config.enabled:
            timeline.record("runtime_not_started", "Power runtime disabled by default.")
            return self._result(plan, PowerRuntimeStatus.NOT_STARTED, [], timeline)

        validation_error = self._validate_orderable(plan.graph)
        if validation_error:
            timeline.record("runtime_blocked", validation_error, blocked_reason=validation_error)
            return self._result(plan, PowerRuntimeStatus.BLOCKED, [], timeline, blocked_reason=validation_error)
        if len(plan.graph.steps) > runtime_config.max_steps:
            reason = "max_steps_exceeded"
            timeline.record("runtime_blocked", reason, blocked_reason=reason)
            return self._result(plan, PowerRuntimeStatus.BLOCKED, [], timeline, blocked_reason=reason)

        ordered_steps = self._topological_order(plan.graph)
        context: dict[str, Any] = {
            "mission_id": plan.mission_id,
            "runtime_config": runtime_config.model_dump(mode="json"),
        }
        step_results: list[PowerStepResult] = []

        for step in ordered_steps:
            if cancellation_token is not None and cancellation_token.is_cancelled:
                aborted = self._aborted_step(step)
                step_results.append(aborted)
                timeline.record(
                    "step_aborted",
                    "Kill switch cancelled before step execution.",
                    step_id=step.step_id,
                    blocked_reason=aborted.blocked_reason,
                )
                return self._result(
                    plan,
                    PowerRuntimeStatus.ABORTED,
                    step_results,
                    timeline,
                    blocked_reason="kill_switch_cancelled",
                )

            if actuator_executor is None:
                blocked = PowerStepResult(
                    step_id=step.step_id,
                    status=PowerStepStatus.BLOCKED,
                    blocked_reason="power_runtime_executor_missing",
                    safe_summary="No actuator executor was injected; step failed closed.",
                )
                step_results.append(blocked)
                timeline.record(
                    "step_blocked",
                    blocked.safe_summary,
                    step_id=step.step_id,
                    blocked_reason=blocked.blocked_reason,
                )
                return self._result(
                    plan,
                    PowerRuntimeStatus.BLOCKED,
                    step_results,
                    timeline,
                    blocked_reason=blocked.blocked_reason,
                )

            timeline.record("step_started", f"Power step {step.step_id} started.", step_id=step.step_id)
            step_result = self._execute_with_retries(
                step,
                context,
                actuator_executor,
                max(step.retry_budget, runtime_config.default_retry_budget),
            )
            if memory_feedback_builder is not None and runtime_config.record_memory_feedback_refs:
                refs = memory_feedback_builder(step, step_result, context)
                if refs:
                    step_result = step_result.model_copy(
                        update={
                            "memory_feedback_refs": [
                                *step_result.memory_feedback_refs,
                                *[str(ref) for ref in refs],
                            ]
                        }
                    )
            step_results.append(step_result)
            timeline.record(
                self._event_type_for_step_result(step_result),
                step_result.safe_summary,
                step_id=step.step_id,
                receipt_refs=step_result.receipt_refs,
                finalgate_certificate_refs=step_result.finalgate_certificate_refs,
                memory_feedback_refs=step_result.memory_feedback_refs,
                blocked_reason=step_result.blocked_reason,
            )

            if step_result.status is PowerStepStatus.SUCCEEDED:
                continue
            if step_result.status is PowerStepStatus.BLOCKED:
                return self._result(
                    plan,
                    PowerRuntimeStatus.BLOCKED,
                    step_results,
                    timeline,
                    blocked_reason=step_result.blocked_reason,
                )
            return self._result(
                plan,
                PowerRuntimeStatus.FAILED,
                step_results,
                timeline,
                blocked_reason=step_result.blocked_reason,
            )

        return self._result(plan, PowerRuntimeStatus.COMPLETED, step_results, timeline)

    def _execute_with_retries(
        self,
        step: PowerMissionStep,
        context: dict[str, Any],
        actuator_executor: PowerActuatorExecutor,
        retry_budget: int,
    ) -> PowerStepResult:
        attempts_allowed = retry_budget + 1
        last_result: PowerStepResult | None = None
        for attempt in range(1, attempts_allowed + 1):
            try:
                result = actuator_executor(step, deepcopy(context))
            except Exception as exc:  # pragma: no cover - exact exception type is executor owned.
                result = PowerStepResult(
                    step_id=step.step_id,
                    status=PowerStepStatus.FAILED,
                    blocked_reason=exc.__class__.__name__,
                    safe_summary="Actuator executor raised a sanitized failure.",
                )
            if not isinstance(result, PowerStepResult):
                result = PowerStepResult(
                    step_id=step.step_id,
                    status=PowerStepStatus.FAILED,
                    blocked_reason="executor_invalid_result",
                    safe_summary="Actuator executor returned an invalid result.",
                )
            elif result.step_id != step.step_id:
                result = PowerStepResult(
                    step_id=step.step_id,
                    status=PowerStepStatus.FAILED,
                    blocked_reason="executor_step_id_mismatch",
                    safe_summary="Executor returned a result for the wrong step.",
                )
            result = result.model_copy(update={"attempt_count": attempt})
            last_result = result
            if result.status is PowerStepStatus.SUCCEEDED:
                return result
            if result.status is PowerStepStatus.BLOCKED:
                return result
        assert last_result is not None
        return last_result

    def _validate_orderable(self, graph: PowerMissionGraph) -> str | None:
        step_ids = {step.step_id for step in graph.steps}
        for step in graph.steps:
            for dependency in step.depends_on:
                if dependency not in step_ids:
                    return f"unknown_dependency:{dependency}"
        ordered = self._topological_order(graph)
        if len(ordered) != len(graph.steps):
            return "cycle_detected"
        return None

    def _topological_order(self, graph: PowerMissionGraph) -> list[PowerMissionStep]:
        steps_by_id = {step.step_id: step for step in graph.steps}
        remaining = set(steps_by_id)
        ordered: list[PowerMissionStep] = []
        while remaining:
            ready = [
                step
                for step in graph.steps
                if step.step_id in remaining and all(dependency not in remaining for dependency in step.depends_on)
            ]
            if not ready:
                break
            for step in ready:
                ordered.append(step)
                remaining.remove(step.step_id)
        return ordered

    @staticmethod
    def _event_type_for_step_result(result: PowerStepResult) -> str:
        if result.status is PowerStepStatus.SUCCEEDED:
            return "step_succeeded"
        if result.status is PowerStepStatus.BLOCKED:
            return "step_blocked"
        if result.status is PowerStepStatus.ABORTED:
            return "step_aborted"
        return "step_failed"

    @staticmethod
    def _aborted_step(step: PowerMissionStep) -> PowerStepResult:
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.ABORTED,
            blocked_reason="kill_switch_cancelled",
            safe_summary="Kill switch cancelled before step execution.",
        )

    @staticmethod
    def _result(
        plan: PowerMissionPlan,
        status: PowerRuntimeStatus,
        step_results: list[PowerStepResult],
        timeline: PowerMissionTimeline,
        *,
        blocked_reason: str | None = None,
    ) -> PowerRuntimeResult:
        return PowerRuntimeResult(
            mission_id=plan.mission_id,
            status=status,
            step_results=step_results,
            timeline=timeline,
            receipt_refs=_flatten_refs(step_results, "receipt_refs"),
            finalgate_certificate_refs=_flatten_refs(step_results, "finalgate_certificate_refs"),
            memory_feedback_refs=_flatten_refs(step_results, "memory_feedback_refs"),
            blocked_reason=blocked_reason,
        )


def _flatten_refs(step_results: list[PowerStepResult], field_name: str) -> list[str]:
    refs: list[str] = []
    for result in step_results:
        refs.extend(getattr(result, field_name))
    return refs


def _reject_control_plane_payload(payload: Any, *, path: str) -> None:
    scan = scan_forbidden_payload_categorized(payload, path=path)
    rejected = [
        *scan[OrganSafetyScanCategory.SECRET.value],
        *scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value],
        *scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value],
        *scan[OrganSafetyScanCategory.UNSAFE_PAYLOAD.value],
    ]
    if rejected:
        raise ValueError("power runtime payload rejected at " + ",".join(rejected))


def _hash_timeline_item(item: PowerMissionTimelineItem) -> str:
    payload = item.model_dump(mode="json")
    payload.pop("event_hash", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
