from __future__ import annotations

from pathlib import Path

from sentinel.agent.event_bus import EventBus
from sentinel.agent.evidence_ranker import sanitize_context_text
from sentinel.agent.events import AgentEventType
from sentinel.agent.models import AgentContext, WorkerResult, WorkerTask
from sentinel.agent.phases import AgentPhase
from sentinel.mission.models import MissionPlan, MissionTraceEvent
from sentinel.mission.runner import MissionRunner
from sentinel.shared.enums import MissionTraceEventType


class _EventBusMissionTraceEventSink:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def emit_mission_trace_event(self, event: MissionTraceEvent) -> None:
        self._event_bus.project_mission_trace_event(event)


class WorkerCoordinator:
    def __init__(self, project_root: str | Path | None = None, runner: MissionRunner | None = None) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.runner = runner or MissionRunner(project_root=self.project_root)

    def run_mission_worker(self, context: AgentContext, event_bus: EventBus, *, plan: MissionPlan | None = None) -> WorkerResult:
        task = WorkerTask(
            worker_type="mission_runner",
            mission_id=context.mission.id,
            input_refs=context.evidence_refs,
            expected_output="MissionRunner result",
            allowed_actions=context.mission.allowed_actions,
            allowed_tools=context.mission.allowed_tools,
            success_criteria=context.mission.success_criteria,
        )
        event_bus.append(
            AgentEventType.WORKER_STARTED,
            "Mission worker started.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={"task_id": task.id, "worker_type": task.worker_type, "plan_step_ids": [step.id for step in plan.steps] if plan else []},
        )
        try:
            result = self.runner.run_mission(
                context.mission,
                idea=context.user_input.get("idea"),
                evidence_refs=context.evidence_refs,
                plan=plan,
                mission_trace_event_sink=_EventBusMissionTraceEventSink(event_bus),
            )
        except Exception as exc:
            event_bus.append(
                AgentEventType.WORKER_COMPLETED,
                "Mission worker failed before producing a MissionRunResult.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "task_id": task.id,
                    "success": False,
                    "project_path": None,
                    "action_count": 0,
                    "executed_action_ids": [],
                    "error_type": type(exc).__name__,
                    "error": sanitize_context_text(str(exc)),
                },
            )
            raise
        executed_action_ids = [
            event.action_id
            for event in result.trace_events
            if event.event_type == MissionTraceEventType.ACTION_EXECUTED and event.action_id
        ]
        event_bus.append(
            AgentEventType.WORKER_COMPLETED,
            "Mission worker completed.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.ARTIFACT_REVIEWING,
            payload={
                "task_id": task.id,
                "success": result.success,
                "project_path": result.project_path,
                "action_count": result.state.action_count,
                "executed_action_ids": executed_action_ids,
            },
            trace_refs=[event.id for event in result.trace_events],
        )
        return WorkerResult(
            task_id=task.id,
            status="completed" if result.success else "failed",
            output_refs=[result.project_path],
            trace_refs=[event.id for event in result.trace_events],
            mission_result=result,
        )
