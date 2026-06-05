from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sentinel.agent.organs.channel_draft_send_organ_v1 import (
    ChannelDraftSendContract,
    build_channel_power_executor,
)
from sentinel.agent.organs.external_api_read_write_organ_v1 import (
    ExternalAPIContract,
    ExternalAPITransportResponse,
    build_external_api_power_executor,
)
from sentinel.agent.organs.sandbox_shell_code_organ_v1 import build_shell_code_power_executor
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerRuntimeConfig,
    PowerRuntimeResult,
    PowerStepResult,
    PowerStepStatus,
    SentinelPowerRuntimeV0,
)
from sentinel.shared.models import new_id


def run_power_fabric_orchestration_demo(
    *,
    project_root: str | Path,
    api_call_recorder: list[str] | None = None,
    sender_call_recorder: list[str] | None = None,
) -> PowerRuntimeResult:
    """Run a contained multi-actuator demo.

    The demo proves orchestration shape, not broad ambient power. Browser and API
    are fixture-backed, shell is allowlisted, workspace writes one local report,
    and channel creates a draft without calling a sender.
    """

    root = Path(project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    plan = _demo_plan()
    executor = _build_demo_executor(root, api_call_recorder=api_call_recorder, sender_call_recorder=sender_call_recorder)
    return SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=executor,
    )


def _demo_plan() -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id="mission_power_fabric_demo",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="browser_observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe_fixture",
                ),
                PowerMissionStep(
                    step_id="api_metadata",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="external_api",
                    action_kind="request",
                    request={"method": "GET", "url": "https://api.example.com/demo/metadata"},
                    depends_on=["browser_observe"],
                ),
                PowerMissionStep(
                    step_id="shell_python_version",
                    actuator_family=PowerActuatorFamily.SHELL_SANDBOX,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="sandbox_shell_code",
                    action_kind="run_command",
                    request={"cwd": ".", "command": ["python", "--version"]},
                    depends_on=["api_metadata"],
                ),
                PowerMissionStep(
                    step_id="workspace_report",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write_report",
                    depends_on=["shell_python_version"],
                ),
                PowerMissionStep(
                    step_id="channel_draft",
                    actuator_family=PowerActuatorFamily.CHANNEL,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="channel_draft_send",
                    action_kind="draft",
                    request={
                        "mode": "draft",
                        "channel": "email",
                        "subject": "Sentinel power fabric demo",
                        "body": "Draft summary generated from demo receipts.",
                        "recipients": ["founder@example.com"],
                        "evidence_refs": ["ev_power_fabric_demo"],
                    },
                    depends_on=["workspace_report"],
                ),
            ]
        ),
    )


def _build_demo_executor(
    root: Path,
    *,
    api_call_recorder: list[str] | None,
    sender_call_recorder: list[str] | None,
) -> Any:
    api_executor = build_external_api_power_executor(
        contract=ExternalAPIContract(allowed_domains=["api.example.com"], allowed_methods=["GET"]),
        transport=_fake_api_transport(api_call_recorder),
    )
    shell_executor = build_shell_code_power_executor(project_root=root)
    channel_executor = build_channel_power_executor(
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=False),
        sender=_fake_sender(sender_call_recorder),
    )

    def _executor(step: PowerMissionStep, context: dict[str, Any]) -> PowerStepResult:
        if step.step_id == "browser_observe":
            return _with_memory(
                PowerStepResult(
                    step_id=step.step_id,
                    status=PowerStepStatus.SUCCEEDED,
                    receipt_refs=[_ref("browser_demo_receipt", step.step_id)],
                    finalgate_certificate_refs=[_ref("browser_demo_finalgate", step.step_id)],
                    safe_summary="Fixture browser observation recorded.",
                ),
                step.step_id,
            )
        if step.step_id == "api_metadata":
            return _with_memory(api_executor(step, context), step.step_id)
        if step.step_id == "shell_python_version":
            return _with_memory(shell_executor(step, context), step.step_id)
        if step.step_id == "workspace_report":
            return _workspace_report_result(root, step.step_id)
        if step.step_id == "channel_draft":
            return _with_memory(channel_executor(step, context), step.step_id)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.BLOCKED,
            blocked_reason="unknown_demo_step",
            safe_summary="Unknown demo step blocked.",
        )

    return _executor


def _fake_api_transport(api_call_recorder: list[str] | None) -> Any:
    def _transport(request: Any) -> ExternalAPITransportResponse:
        if api_call_recorder is not None:
            api_call_recorder.append(f"{request.method} {request.url}")
        return ExternalAPITransportResponse(status_code=200, headers={"content-type": "application/json"}, body=b"fixture api body")

    return _transport


def _fake_sender(sender_call_recorder: list[str] | None) -> Any:
    def _sender(request: Any) -> Any:
        if sender_call_recorder is not None:
            sender_call_recorder.append(f"{request.channel}:{len(request.recipients)}")
        raise AssertionError("demo channel sender must not be called")

    return _sender


def _workspace_report_result(root: Path, step_id: str) -> PowerStepResult:
    path = root / "POWER_FABRIC_DEMO_REPORT.md"
    content = (
        "# Power Fabric Demo Report\n\n"
        "- browser observation: fixture receipt\n"
        "- external API metadata: hash-only fixture receipt\n"
        "- shell sandbox: python version command\n"
        "- channel: draft-only, no send\n"
    )
    path.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return PowerStepResult(
        step_id=step_id,
        status=PowerStepStatus.SUCCEEDED,
        receipt_refs=[f"workspace_demo_receipt:{digest}"],
        finalgate_certificate_refs=[f"workspace_demo_finalgate:{digest[:16]}"],
        memory_feedback_refs=[f"memory:{step_id}"],
        safe_summary="Workspace demo report written with hash receipt.",
    )


def _with_memory(result: PowerStepResult, step_id: str) -> PowerStepResult:
    return result.model_copy(update={"memory_feedback_refs": [*result.memory_feedback_refs, f"memory:{step_id}"]})


def _ref(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}:{new_id('ref')}"
