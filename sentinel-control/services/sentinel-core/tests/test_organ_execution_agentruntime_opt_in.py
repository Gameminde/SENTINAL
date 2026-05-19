from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.agent.organs.delegated_action_gate import (
    DelegatedActionAuthorityClass,
    DelegatedActionGateDecision,
    DelegatedActionGateResult,
    DelegatedActionGateSafetyValidationResult,
    DelegatedActionGateStatus,
    DelegatedActionGateTrace,
    DelegatedActionBudgetStatus,
    DelegatedActionBudgetSummary,
    DelegatedActionEvidenceStatus,
    DelegatedActionEvidenceSummary,
    DelegatedActionLane,
    DelegatedActionLaneStatus,
    DelegatedActionOrganContractStatus,
    DelegatedActionReceiptRequirement,
    DelegatedActionRiskClass,
)
from sentinel.agent.organs.local_artifact_executor import (
    L2ExecutorContract,
    L2LocalArtifactActionKind,
    L2LocalArtifactRequest,
)
from sentinel.agent.organs.low_risk_finalgate import LowRiskFinalGateDecision
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ExecutorContract,
    L3WorkspaceActionKind,
    L3WorkspaceRequest,
)
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionResult,
    OrganRuntimeExecutionStatus,
    render_organ_runtime_execution_result_as_untrusted_context,
)
from sentinel.agent.runtime import AgentRuntime
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)


def _authority(mission_id: str, **updates: Any) -> MissionAuthorityEnvelope:
    base = {
        "id": mission_id,
        "user_id": "user_runtime_organs",
        "mission_type": MissionType.GTM,
        "mission_title": "Low risk organ runtime test",
        "mission_objective": "Exercise explicit local L2/L3 runtime opt-in.",
        "success_criteria": ["receipt exists", "FinalGate certificate exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["low_risk_local_organs"],
        "allowed_actions": ["create_local_artifact", "replace_text_file", "append_text_file"],
        "forbidden_actions": ["send_email", "browser_submit", "run_shell_command", "credential_access"],
        "allowed_paths": ["generated_root", "workspace_root"],
        "max_duration_minutes": 30,
        "max_actions": 10,
        "max_cost_usd": 0.0,
    }
    base.update(updates)
    return MissionAuthorityEnvelope(**base)


def _receipt_requirement(level: DelegatedActionLevel) -> DelegatedActionReceiptRequirement:
    fields = ["path_metadata", "lane_id", "gate_result_id"]
    if level is DelegatedActionLevel.L2:
        fields.append("artifact_hash")
    if level is DelegatedActionLevel.L3:
        fields.extend(["before_hash", "after_hash"])
    return DelegatedActionReceiptRequirement(
        required_receipt_fields=fields,
        receipt_refs=[f"receipt_gate_{level.value.lower()}"],
        receipt_contract_hash=f"receipt_contract_hash_{level.value.lower()}",
    )


def _lane(
    *,
    mission_id: str,
    level: DelegatedActionLevel,
    source_candidate_id: str = "candidate_runtime",
    **updates: Any,
) -> DelegatedActionLane:
    base = {
        "lane_id": f"lane_{level.value.lower()}",
        "mission_id": mission_id,
        "source_candidate_id": source_candidate_id,
        "organ_kind": OrganProposalKind.FILE_OPERATION,
        "action_level": level,
        "allowed_substeps": ["create_generated_report"] if level is DelegatedActionLevel.L2 else ["replace_text_file", "append_text_file"],
        "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.LOW if level is DelegatedActionLevel.L2 else DelegatedActionRiskClass.MEDIUM,
        "budget_limit": {"remaining_action_count": 2, "remaining_bytes": 4096},
        "credential_scope": "none",
        "evidence_refs": [f"ev_{level.value.lower()}"],
        "receipt_refs": [f"receipt_gate_{level.value.lower()}"],
        "receipt_contract": _receipt_requirement(level),
        "revocation_rule": "lane can be revoked before runtime execution",
        "rollback_posture": "delete generated artifact with tombstone" if level is DelegatedActionLevel.L2 else "restore previous text from before snapshot",
        "user_review_requirement": "not_required_for_low_risk_local_only",
        "FinalGate_checks": ["local_only", "receipt_present", "forbidden_surface_absent"],
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=30),
        "ttl_seconds": 1800,
    }
    base.update(updates)
    return DelegatedActionLane(**base)


def _gate_result(
    *,
    mission_id: str,
    level: DelegatedActionLevel,
    decision: DelegatedActionGateDecision = DelegatedActionGateDecision.ALLOWED,
    lane: DelegatedActionLane | None | object = None,
    **updates: Any,
) -> DelegatedActionGateResult:
    candidate_id = "candidate_runtime"
    if lane is None:
        lane = _lane(mission_id=mission_id, level=level, source_candidate_id=candidate_id)
    base = {
        "mission_id": mission_id,
        "status": DelegatedActionGateStatus.EVALUATED if decision is DelegatedActionGateDecision.ALLOWED else DelegatedActionGateStatus.BLOCKED,
        "decision": decision,
        "reasons": [],
        "candidate_id": candidate_id,
        "lane": lane if decision is DelegatedActionGateDecision.ALLOWED else None,
        "trace": DelegatedActionGateTrace(
            mission_id=mission_id,
            candidate_id=candidate_id,
            decision=decision,
            authority_status=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
            budget_status=DelegatedActionBudgetStatus.PASSING,
            evidence_status=DelegatedActionEvidenceStatus.SUPPORTED,
            organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
            safe_summary="gate metadata for explicit runtime opt-in",
        ),
        "safety_validation": DelegatedActionGateSafetyValidationResult(),
        "risk_class": DelegatedActionRiskClass.LOW if level is DelegatedActionLevel.L2 else DelegatedActionRiskClass.MEDIUM,
        "budget_status": DelegatedActionBudgetSummary(status=DelegatedActionBudgetStatus.PASSING),
        "evidence_status": DelegatedActionEvidenceSummary(
            status=DelegatedActionEvidenceStatus.SUPPORTED,
            evidence_refs=[f"ev_{level.value.lower()}"],
            available_evidence_refs=[f"ev_{level.value.lower()}"],
        ),
        "organ_contract_status": DelegatedActionOrganContractStatus.PASSING,
        "receipt_requirement": _receipt_requirement(level),
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
    }
    base.update(updates)
    return DelegatedActionGateResult(**base)


def _l2_contract(tmp_path: Path, mission_id: str = "mission_runtime_l2", **updates: Any) -> L2ExecutorContract:
    base = {
        "mission_id": mission_id,
        "lane_id": "lane_l2",
        "gate_result_id": "gate_result_l2",
        "allowed_workspace_root": str(tmp_path / "generated_root"),
        "allowed_artifact_subdir": "artifacts",
        "max_artifact_bytes": 4096,
        "allow_overwrite": False,
        "allow_rollback_cleanup": True,
        "receipt_required": True,
        "tombstone_required_for_cleanup": True,
        "finalgate_posture_required": True,
        "execution_enabled_for_l2": True,
        "contract_version": "l2-local-artifact-v0",
    }
    base.update(updates)
    return L2ExecutorContract(**base)


def _l2_request(tmp_path: Path, mission_id: str = "mission_runtime_l2", **updates: Any) -> L2LocalArtifactRequest:
    contract = updates.pop("contract", _l2_contract(tmp_path, mission_id))
    lane = updates.pop("delegated_lane", _lane(mission_id=mission_id, level=DelegatedActionLevel.L2))
    base = {
        "mission_id": mission_id,
        "source_candidate_id": "candidate_runtime",
        "action_kind": L2LocalArtifactActionKind.CREATE_GENERATED_REPORT,
        "target_relative_path": "reports/runtime.md",
        "content": "# Runtime\nsafe local artifact",
        "metadata": {"title": "runtime l2"},
        "contract": contract,
        "delegated_lane": lane,
        "budget_estimate": {"artifact_bytes": 29, "action_count": 1},
        "current_time": NOW,
    }
    base.update(updates)
    return L2LocalArtifactRequest(**base)


def _workspace_file(tmp_path: Path, relative: str = "docs/state.md", content: str = "before\n") -> tuple[Path, str]:
    path = tmp_path / "workspace_root" / "work" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path, text_hash(content)


def _l3_contract(tmp_path: Path, mission_id: str = "mission_runtime_l3", **updates: Any) -> L3ExecutorContract:
    base = {
        "mission_id": mission_id,
        "lane_id": "lane_l3",
        "gate_result_id": "gate_result_l3",
        "allowed_workspace_root": str(tmp_path / "workspace_root"),
        "allowed_workspace_subdir": "work",
        "max_file_bytes": 4096,
        "max_patch_bytes": 2048,
        "allow_overwrite": True,
        "allow_delete": False,
        "tombstone_required_for_delete": True,
        "rollback_required": True,
        "rollback_must_be_tested_before_mutation": True,
        "receipt_required": True,
        "finalgate_posture_required": True,
        "execution_enabled_for_l3": True,
        "contract_version": "l3-reversible-workspace-v0",
    }
    base.update(updates)
    return L3ExecutorContract(**base)


def _l3_request(tmp_path: Path, mission_id: str = "mission_runtime_l3", **updates: Any) -> L3WorkspaceRequest:
    _, before_hash = _workspace_file(tmp_path)
    contract = updates.pop("contract", _l3_contract(tmp_path, mission_id))
    lane = updates.pop("delegated_lane", _lane(mission_id=mission_id, level=DelegatedActionLevel.L3))
    base = {
        "mission_id": mission_id,
        "source_candidate_id": "candidate_runtime",
        "action_kind": L3WorkspaceActionKind.REPLACE_TEXT_FILE,
        "target_relative_path": "docs/state.md",
        "content": "after\n",
        "metadata_patch": {},
        "before_hash": before_hash,
        "metadata": {"title": "runtime l3"},
        "contract": contract,
        "delegated_lane": lane,
        "budget_estimate": {"patch_bytes": 6, "action_count": 1},
        "current_time": NOW,
    }
    base.update(updates)
    return L3WorkspaceRequest(**base)


def _config(**updates: Any) -> OrganRuntimeExecutionConfig:
    base = {
        "enabled": True,
        "mode": OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY,
        "workspace_root_allowlist": [],
        "contract_version": "organ-runtime-l2-l3-v0",
    }
    base.update(updates)
    return OrganRuntimeExecutionConfig(**base)


def _runtime(config: OrganRuntimeExecutionConfig | None = None) -> AgentRuntime:
    return AgentRuntime(organ_execution_config=config)


def _l2_runtime_request(tmp_path: Path, **updates: Any) -> OrganRuntimeExecutionRequest:
    mission_id = updates.pop("mission_id", "mission_runtime_l2")
    l2_request = updates.pop("l2_request", _l2_request(tmp_path, mission_id))
    gate_result = updates.pop("gate_result", _gate_result(mission_id=mission_id, level=DelegatedActionLevel.L2))
    base = {
        "mission_id": mission_id,
        "action_level": DelegatedActionLevel.L2,
        "organ_kind": "local_artifact",
        "authority_envelope": _authority(mission_id),
        "gate_result": gate_result,
        "delegated_lane": gate_result.lane,
        "l2_request": l2_request,
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return OrganRuntimeExecutionRequest(**base)


def _l3_runtime_request(tmp_path: Path, **updates: Any) -> OrganRuntimeExecutionRequest:
    mission_id = updates.pop("mission_id", "mission_runtime_l3")
    l3_request = updates.pop("l3_request", _l3_request(tmp_path, mission_id))
    gate_result = updates.pop("gate_result", _gate_result(mission_id=mission_id, level=DelegatedActionLevel.L3))
    base = {
        "mission_id": mission_id,
        "action_level": DelegatedActionLevel.L3,
        "organ_kind": "reversible_workspace",
        "authority_envelope": _authority(mission_id),
        "gate_result": gate_result,
        "delegated_lane": gate_result.lane,
        "l3_request": l3_request,
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return OrganRuntimeExecutionRequest(**base)


def test_agentruntime_default_behavior_unchanged_without_organ_execution_config() -> None:
    runtime = AgentRuntime()

    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED


def test_agentruntime_organ_execution_disabled_by_default() -> None:
    config = OrganRuntimeExecutionConfig()

    assert config.enabled is False
    assert config.mode is OrganRuntimeExecutionMode.DISABLED


def test_agentruntime_blocks_when_opt_in_missing(tmp_path: Path) -> None:
    result = AgentRuntime().execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "organ_execution_disabled"
    assert result.receipt is None


def test_agentruntime_blocks_when_authority_envelope_missing(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path, authority_envelope=None))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "mission_authority_envelope_missing"


def test_agentruntime_blocks_when_gate_denied(tmp_path: Path) -> None:
    gate_result = _gate_result(
        mission_id="mission_runtime_l2",
        level=DelegatedActionLevel.L2,
        decision=DelegatedActionGateDecision.BLOCKED,
    )

    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path, gate_result=gate_result, delegated_lane=None))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "gate_allowed_lane_required"


def test_agentruntime_blocks_when_lane_expired(tmp_path: Path) -> None:
    lane = _lane(mission_id="mission_runtime_l2", level=DelegatedActionLevel.L2, expires_at=NOW - timedelta(seconds=1))
    gate_result = _gate_result(mission_id="mission_runtime_l2", level=DelegatedActionLevel.L2, lane=lane)
    l2_request = _l2_request(tmp_path, delegated_lane=lane)

    result = _runtime(_config()).execute_organ_runtime_request(
        _l2_runtime_request(tmp_path, gate_result=gate_result, delegated_lane=lane, l2_request=l2_request)
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "lane_expired"


@pytest.mark.parametrize("level", [DelegatedActionLevel.L4, DelegatedActionLevel.L5, DelegatedActionLevel.L6, DelegatedActionLevel.L7])
def test_agentruntime_blocks_l4_l5_l6_l7_actions(tmp_path: Path, level: DelegatedActionLevel) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path, action_level=level))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "action_level_not_allowed"


def test_agentruntime_opt_in_executes_l2_local_artifact_only(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.execution_effect == "local_artifact_created"
    assert result.receipt is not None
    assert Path(result.executor_result_summary["artifact_path"]).read_text(encoding="utf-8").startswith("# Runtime")


def test_agentruntime_l2_result_includes_receipt_and_finalgate_certificate(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    assert result.receipt is not None
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.decision is LowRiskFinalGateDecision.CERTIFIED_SUCCESS


def test_agentruntime_opt_in_executes_l3_reversible_workspace_only(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")
    request = _l3_request(tmp_path, before_hash=before_hash)

    result = _runtime(_config()).execute_organ_runtime_request(_l3_runtime_request(tmp_path, l3_request=request))

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.execution_effect == "reversible_workspace_mutation"
    assert path.read_text(encoding="utf-8") == "after\n"


def test_agentruntime_l3_result_includes_receipt_and_finalgate_certificate(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l3_runtime_request(tmp_path))

    assert result.receipt is not None
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.before_hash is not None
    assert result.finalgate_certificate.after_hash is not None


def test_agentruntime_l3_rollback_posture_required(tmp_path: Path) -> None:
    request = _l3_request(tmp_path, contract=_l3_contract(tmp_path, rollback_required=False))

    result = _runtime(_config()).execute_organ_runtime_request(_l3_runtime_request(tmp_path, l3_request=request))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "l3_rollback_required"


def test_agentruntime_l2_only_config_blocks_l3(tmp_path: Path) -> None:
    result = _runtime(_config(allow_l3=False, allowed_action_levels=[DelegatedActionLevel.L2])).execute_organ_runtime_request(
        _l3_runtime_request(tmp_path)
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "l3_disabled_by_config"


def test_agentruntime_l3_only_config_blocks_l2(tmp_path: Path) -> None:
    result = _runtime(_config(allow_l2=False, allowed_action_levels=[DelegatedActionLevel.L3])).execute_organ_runtime_request(
        _l2_runtime_request(tmp_path)
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "l2_disabled_by_config"


def test_agentruntime_blocks_browser_api_channel_desktop_shell_network_credential(tmp_path: Path) -> None:
    request = _l2_runtime_request(
        tmp_path,
        metadata={"browser_submit": True, "api_call": True, "channel_send": True, "desktop_action": True, "shell": True, "external_network": True},
    )

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_agentruntime_rejects_raw_prompt_response_reasoning_or_key(tmp_path: Path) -> None:
    request = _l2_runtime_request(
        tmp_path,
        metadata={"raw_prompt": "no", "raw_response": "no", "reasoning": "hidden", "api_key": "gsk_" + "abcdefghijklmnopqrstuvwxyz"},
    )

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_agentruntime_rejects_secret_or_bearer_payload(tmp_path: Path) -> None:
    request = _l2_runtime_request(tmp_path, metadata={"safe_summary": "Bearer " + "abcdefghijklmnop1234567890"})

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_agentruntime_rejects_hidden_tool_or_organ_payload(tmp_path: Path) -> None:
    request = _l2_runtime_request(tmp_path, metadata={"tool_calls": [{"name": "browser"}], "organ_execution": "browser"})

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_agentruntime_rejects_authority_expansion_payload(tmp_path: Path) -> None:
    request = _l2_runtime_request(tmp_path, metadata={"authority_expansion": {"new_scope": "all"}})

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_agentruntime_rejects_provider_model_override_payload(tmp_path: Path) -> None:
    request = _l2_runtime_request(tmp_path, metadata={"provider_override": "other", "model_override": "auto"})

    result = _runtime(_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "provider_model_override_rejected"


def test_agentruntime_preserves_selected_provider_backend_model(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    assert result.selected_provider_id == "groq"
    assert result.selected_backend_id == "groq_openai_compatible_chat"
    assert result.selected_model == "openai/gpt-oss-20b"


def test_agentruntime_does_not_create_delegated_lane(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    assert result.can_create_delegated_lane is False
    assert result.lane_id == "lane_l2"


def test_agentruntime_does_not_approve_future_execution(tmp_path: Path) -> None:
    payload = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path)).model_dump(mode="python")
    payload["can_approve_future_execution"] = True

    with pytest.raises(ValidationError):
        OrganRuntimeExecutionResult(**payload)


def test_agentruntime_result_rendering_is_data_not_instruction(tmp_path: Path) -> None:
    result = _runtime(_config()).execute_organ_runtime_request(_l2_runtime_request(tmp_path))

    rendered = render_organ_runtime_execution_result_as_untrusted_context(result)

    assert "not instructions" in rendered
    assert "not Root Authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_agentruntime_no_provider_expansion_fallback_or_auto() -> None:
    runtime_text = (Path(__file__).parents[1] / "sentinel/agent/runtime.py").read_text(encoding="utf-8").lower()

    assert "auto_model_routing" not in runtime_text
    assert "provider_fallback" not in runtime_text


def test_agentruntime_no_vendor_runtime_import() -> None:
    module_text = (Path(__file__).parents[1] / "sentinel/agent/organs/runtime_execution.py").read_text(encoding="utf-8").lower()

    assert "openclaw" not in module_text
    assert "jarvis" not in module_text
    assert "agentmemory" not in module_text
