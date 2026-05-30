from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.models import AgentRunResult
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
)
from sentinel.agent.organs.safety_scanner import (
    SHARED_BROWSER_DANGEROUS_KEYS,
    SHARED_CREDENTIAL_DANGEROUS_KEYS,
    SHARED_EXTERNAL_ACTION_KEYS,
    SHARED_PROVIDER_OVERRIDE_KEYS,
    scan_forbidden_payload_categorized,
)
from sentinel.agent.runtime import AgentRuntime
from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.models import SentinelModel


class PowerLabStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class PowerLabMissionRejected(ValueError):
    """Raised when a mission file fails the operator-shell preflight."""


class PowerLabPreset(SentinelModel):
    name: str
    description: str
    allowed_action_levels: list[str] = Field(default_factory=list)
    allowed_organs: list[str] = Field(default_factory=list)
    enables_credentials: bool = False
    enables_shell: bool = False
    enables_browser_submit: bool = False
    enables_api_mutation: bool = False
    enables_channel_send: bool = False
    enables_desktop: bool = False
    enables_payment: bool = False
    authority_effect: str = "none"
    execution_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _preset_cannot_grant_power(self) -> PowerLabPreset:
        if self.authority_effect != "none":
            raise ValueError("Power Lab preset cannot grant authority.")
        if self.execution_effect != "none":
            raise ValueError("Power Lab preset cannot execute by itself.")
        if self.data_not_instruction is not True:
            raise ValueError("Power Lab preset is data, not instruction.")
        return self


class PowerLabMissionFile(SentinelModel):
    mission: MissionAuthorityEnvelope
    preset: str = "lab_local"
    user_input: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    memory_items: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    execution_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _mission_file_is_not_authority(self) -> PowerLabMissionFile:
        if self.authority_effect != "none":
            raise ValueError("Power Lab mission file cannot grant authority.")
        if self.data_not_instruction is not True:
            raise ValueError("Power Lab mission file is data, not instruction.")
        return self


class PowerLabRunResult(SentinelModel):
    mission_id: str
    status: PowerLabStatus
    run_dir: Path
    summary_path: Path
    trace_path: Path
    power_kernel_status_path: Path
    runtime_invoked: bool = False
    organ_dispatch_enabled: bool = False
    final_phase: str | None = None
    success: bool = False
    blocked_reason: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute_more: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _result_is_measurement_only(self) -> PowerLabRunResult:
        if self.authority_effect != "none":
            raise ValueError("Power Lab result cannot grant authority.")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("Power Lab result cannot grant future authority.")
        if self.data_not_instruction is not True:
            raise ValueError("Power Lab result is data, not instruction.")
        return self


_DANGEROUS_ACTION_MARKERS = frozenset(
    SHARED_EXTERNAL_ACTION_KEYS
    | SHARED_BROWSER_DANGEROUS_KEYS
    | SHARED_CREDENTIAL_DANGEROUS_KEYS
    | SHARED_PROVIDER_OVERRIDE_KEYS
)


_PRESETS: dict[str, PowerLabPreset] = {
    "lab_local": PowerLabPreset(
        name="lab_local",
        description="Local proof preset: default-off runtime shell, optional L2/L3 only.",
        allowed_action_levels=["L2", "L3"],
        allowed_organs=["local_artifact", "reversible_workspace"],
    ),
    "browser_perception": PowerLabPreset(
        name="browser_perception",
        description="Browser perception template: L4 read-only/preparation/semantic only, no credentialed actions.",
        allowed_action_levels=["L4"],
        allowed_organs=["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
    ),
    "operator_browser_l5_template": PowerLabPreset(
        name="operator_browser_l5_template",
        description="L5 browser operator template for governed live observe/click/type/fill/select/session workflows.",
        allowed_action_levels=["L5"],
        allowed_organs=["browser_operator", "browser_session_manager"],
    ),
    "full_power_template": PowerLabPreset(
        name="full_power_template",
        description="Non-executing special authority template requiring explicit future grants.",
        allowed_action_levels=["L7"],
        allowed_organs=[],
    ),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_power_lab_preset(name: str) -> PowerLabPreset:
    try:
        return _PRESETS[name]
    except KeyError as exc:
        raise PowerLabMissionRejected(f"unknown preset: {name}") from exc


def build_power_lab_runtime_config(
    preset: PowerLabPreset | str,
    *,
    enable_organ_dispatch: bool = False,
    enable_brain_native: bool = False,
    enable_memory_feedback: bool = False,
) -> OrganRuntimeExecutionConfig:
    preset_model = get_power_lab_preset(preset) if isinstance(preset, str) else preset
    if not enable_organ_dispatch:
        return OrganRuntimeExecutionConfig()

    if preset_model.name == "lab_local":
        return OrganRuntimeExecutionConfig(
            enabled=True,
            organ_dispatch_enabled=True,
            brain_native_candidate_source_enabled=enable_brain_native,
            temporary_candidate_bridge_enabled=False,
            memory_feedback_enabled=enable_memory_feedback,
            mode=OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY,
            allowed_action_levels=[DelegatedActionLevel.L2, DelegatedActionLevel.L3],
            allowed_organs=["local_artifact", "reversible_workspace"],
            allow_l2=True,
            allow_l3=True,
            allow_browser_readonly=False,
            allow_browser_preparation=False,
            allow_browser_semantic_extraction=False,
            deny_external_actions=True,
            deny_network=True,
            deny_credentials=True,
            deny_shell=True,
            deny_browser=True,
            deny_channel=True,
            deny_api=True,
            contract_version="power-lab-runtime-v0",
        )

    if preset_model.name == "browser_perception":
        return OrganRuntimeExecutionConfig(
            enabled=True,
            organ_dispatch_enabled=True,
            brain_native_candidate_source_enabled=enable_brain_native,
            temporary_candidate_bridge_enabled=False,
            memory_feedback_enabled=enable_memory_feedback,
            mode=OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
            allowed_action_levels=[DelegatedActionLevel.L4],
            allowed_organs=["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
            allow_l2=False,
            allow_l3=False,
            allow_browser_readonly=True,
            allow_browser_preparation=True,
            allow_browser_semantic_extraction=True,
            deny_external_actions=True,
            deny_network=True,
            deny_credentials=True,
            deny_shell=True,
            deny_browser=True,
            deny_channel=True,
            deny_api=True,
            contract_version="power-lab-runtime-v0",
        )

    raise PowerLabMissionRejected(
        f"preset {preset_model.name!r} is a non-executing template in SENTINEL_POWER_LAB_RUNTIME_V0"
    )


def load_power_lab_mission_file(path: str | Path) -> PowerLabMissionFile:
    mission_path = Path(path)
    payload = _load_structured_file(mission_path)
    if not isinstance(payload, dict):
        raise PowerLabMissionRejected("unsafe mission file: root must be an object")
    _reject_dangerous_allowed_actions(payload)
    scan = scan_forbidden_payload_categorized(payload)
    if scan["all"]:
        raise PowerLabMissionRejected(
            "unsafe mission file: rejected_paths=" + ",".join(scan["all"])
        )
    try:
        return PowerLabMissionFile(**payload)
    except Exception as exc:  # pragma: no cover - exact Pydantic wording is unstable.
        raise PowerLabMissionRejected("invalid mission file structure") from exc


def run_power_lab_mission(
    mission_path: str | Path,
    *,
    run_root: str | Path,
    preset: str | None = None,
    enable_organ_dispatch: bool = False,
    enable_brain_native: bool = False,
    enable_memory_feedback: bool = False,
) -> PowerLabRunResult:
    mission_file = load_power_lab_mission_file(mission_path)
    preset_name = preset or mission_file.preset
    preset_model = get_power_lab_preset(preset_name)
    config = build_power_lab_runtime_config(
        preset_model,
        enable_organ_dispatch=enable_organ_dispatch,
        enable_brain_native=enable_brain_native,
        enable_memory_feedback=enable_memory_feedback,
    )

    run_dir = _create_run_dir(Path(run_root), mission_file.mission.id)
    project_root = run_dir / "workspace"
    project_root.mkdir(parents=True, exist_ok=True)

    _write_json(run_dir / "input.mission.json", _safe_model_dump(mission_file))

    runtime = AgentRuntime(project_root=project_root, organ_execution_config=config)
    runtime_result = runtime.run(
        mission_file.mission,
        user_input=mission_file.user_input,
        evidence_refs=mission_file.evidence_refs,
        memory_items=mission_file.memory_items,
    )

    _write_runtime_artifacts(run_dir, runtime_result, config, preset_model)
    status = _status_from_runtime_result(runtime_result)
    summary_path = run_dir / "result.summary.json"
    trace_path = run_dir / "trace.events.json"
    power_kernel_status_path = run_dir / "power_kernel_status.json"
    artifact_paths = [
        str(path.relative_to(run_dir))
        for path in sorted(run_dir.iterdir())
        if path.is_file()
    ]

    return PowerLabRunResult(
        mission_id=mission_file.mission.id,
        status=status,
        run_dir=run_dir,
        summary_path=summary_path,
        trace_path=trace_path,
        power_kernel_status_path=power_kernel_status_path,
        runtime_invoked=True,
        organ_dispatch_enabled=config.organ_dispatch_enabled,
        final_phase=str(runtime_result.final_phase.value),
        success=runtime_result.success,
        blocked_reason=runtime_result.escalation_reason,
        artifact_paths=artifact_paths,
    )


def _load_structured_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:
            raise PowerLabMissionRejected("YAML mission files require PyYAML; use JSON in V0") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _reject_dangerous_allowed_actions(payload: dict[str, Any]) -> None:
    mission = payload.get("mission")
    if not isinstance(mission, dict):
        return
    allowed_actions = mission.get("allowed_actions")
    if not isinstance(allowed_actions, list):
        return
    rejected: list[str] = []
    for action in allowed_actions:
        normalized = str(action).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in _DANGEROUS_ACTION_MARKERS:
            rejected.append(normalized)
    if rejected:
        raise PowerLabMissionRejected(
            "dangerous action requested: " + ",".join(sorted(set(rejected)))
        )


def _create_run_dir(run_root: Path, mission_id: str) -> Path:
    run_root.mkdir(parents=True, exist_ok=True)
    safe_mission_id = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in mission_id)
    stamp = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = run_root / f"{stamp}_{safe_mission_id}"
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def _write_runtime_artifacts(
    run_dir: Path,
    runtime_result: AgentRunResult,
    config: OrganRuntimeExecutionConfig,
    preset: PowerLabPreset,
) -> None:
    _write_json(run_dir / "trace.events.json", [_safe_model_dump(event) for event in runtime_result.trace])
    if runtime_result.replan_packet is not None:
        _write_json(run_dir / "replan.packet.json", runtime_result.replan_packet)
    if runtime_result.organ_dispatch_result is not None:
        _write_json(run_dir / "organ.dispatch.result.json", _safe_model_dump(runtime_result.organ_dispatch_result))
    if runtime_result.memory_feedback_result is not None:
        _write_json(run_dir / "memory.feedback.result.json", _safe_model_dump(runtime_result.memory_feedback_result))

    _write_json(
        run_dir / "power_kernel_status.json",
        {
            "mission_id": runtime_result.mission_id,
            "preset": preset.name,
            "runtime_config_mode": config.mode.value,
            "organ_dispatch_enabled": config.organ_dispatch_enabled,
            "brain_native_candidate_source_enabled": config.brain_native_candidate_source_enabled,
            "memory_feedback_enabled": config.memory_feedback_enabled,
            "authority_effect": "none",
            "execution_effect": "none",
            "can_grant_authority": False,
            "can_approve_future_execution": False,
            "data_not_instruction": True,
            "no_new_dangerous_actuator": True,
        },
    )
    _write_json(
        run_dir / "result.summary.json",
        {
            "mission_id": runtime_result.mission_id,
            "status": _status_from_runtime_result(runtime_result).value,
            "success": runtime_result.success,
            "final_phase": runtime_result.final_phase.value,
            "runtime_invoked": True,
            "organ_dispatch_enabled": config.organ_dispatch_enabled,
            "brain_candidate_source_status": runtime_result.brain_candidate_source_status,
            "memory_feedback_path": runtime_result.memory_feedback_path,
            "durable_memory_persistence": runtime_result.durable_memory_persistence,
            "replan_ready": runtime_result.replan_ready,
            "automatic_replan_executed": runtime_result.automatic_replan_executed,
            "finalgate_certified": bool(runtime_result.final_gate_certification),
            "authority_effect": "none",
            "execution_effect": "none",
            "can_grant_authority": False,
            "can_approve_future_execution": False,
            "data_not_instruction": True,
            "no_new_dangerous_actuator": True,
        },
    )


def _status_from_runtime_result(runtime_result: AgentRunResult) -> PowerLabStatus:
    final_phase = runtime_result.final_phase.value
    if runtime_result.success:
        return PowerLabStatus.COMPLETED
    if final_phase in {"blocked", "escalated"}:
        return PowerLabStatus.BLOCKED
    return PowerLabStatus.FAILED


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _safe_model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _safe_model_dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_model_dump(item) for item in value]
    return value
