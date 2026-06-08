from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.skill_fabric import GovernedSkillFabricRuntime, SkillFabricRuntimeError
from sentinel.operator.skill_models import (
    CompiledTrajectoryProcedure,
    ProcedureManifest,
    ProcedureStep,
    SkillDeclaredAuthority,
    SkillDeclaredSideEffect,
    SkillEvidenceRequirement,
    SkillInputContract,
    SkillLifecycleStatus,
    SkillManifest,
    SkillOutputContract,
    SkillRiskProfile,
)
from sentinel.operator.skill_replay import ProcedureReplayBuilder
from sentinel.telemetry import TelemetryEventKind, TelemetryMetricKind


def test_skill_manifest_validation_and_provenance_version_pinning(tmp_path: Path) -> None:
    manifest = _skill_manifest()

    assert manifest.skill_id == "skill.market_research"
    assert manifest.version == "1.0.0"
    assert manifest.provenance.source_kind == "sentinel_native"
    assert manifest.manifest_hash
    assert manifest.authority_effect == "none"
    assert manifest.can_execute is False

    with pytest.raises(ValueError, match="skill manifest requires declared authority"):
        _skill_manifest(declared_authority=[])

    with pytest.raises(ValueError, match="skill manifest requires declared side effects"):
        _skill_manifest(declared_side_effects=[])

    with pytest.raises(ValueError, match="skill manifest cannot request authority"):
        _skill_manifest(metadata={"authority_grant": "root"})

    with pytest.raises(ValueError, match="skill manifest cannot override provider/backend/model"):
        _skill_manifest(metadata={"provider_override": "other"})

    with pytest.raises(ValueError, match="skill manifest cannot request provider fallback/AUTO"):
        _skill_manifest(metadata={"routing": "fallback/AUTO"})


def test_scanner_quarantines_unsafe_skills_and_blocks_execution(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = GovernedSkillFabricRuntime(kernel)
    unsafe = _skill_manifest(
        skill_id="skill.unsafe",
        procedure=_procedure(
            steps=[
                ProcedureStep(
                    step_id="danger",
                    title="Danger",
                    action_kind="read",
                    safe_summary="Credential access and payment expansion",
                    requested_tools=["workspace"],
                    metadata={"notes": "unsafe"},
                )
            ]
        ),
    )

    record = runtime.register_manifest(mission_id=mission_id, manifest=unsafe)
    scan = runtime.scan_skill(mission_id=mission_id, skill_id=unsafe.skill_id)

    assert scan.decision == "quarantine"
    assert scan.status is SkillLifecycleStatus.QUARANTINED
    assert record.status is SkillLifecycleStatus.DRAFT
    assert "credential" in " ".join(scan.findings).lower()
    with pytest.raises(SkillFabricRuntimeError, match="skill_quarantined"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=unsafe.skill_id,
            envelope=_envelope(mission_id),
            execution_executor=_successful_executor,
        )


def test_approval_promotion_revocation_lifecycle_and_telemetry(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = GovernedSkillFabricRuntime(kernel)
    manifest = _skill_manifest()

    runtime.register_manifest(mission_id=mission_id, manifest=manifest)
    scan = runtime.scan_skill(mission_id=mission_id, skill_id=manifest.skill_id)
    evaluation = runtime.evaluate_skill(mission_id=mission_id, skill_id=manifest.skill_id)
    approval = runtime.approve_skill(mission_id=mission_id, skill_id=manifest.skill_id, approved_by="operator")
    promotion = runtime.promote_skill(mission_id=mission_id, skill_id=manifest.skill_id, promoted_by="operator")
    revocation = runtime.revoke_skill(mission_id=mission_id, skill_id=manifest.skill_id, revoked_by="operator")

    assert scan.status is SkillLifecycleStatus.SCANNED
    assert evaluation.status is SkillLifecycleStatus.EVALUATED
    assert approval.status is SkillLifecycleStatus.APPROVED
    assert promotion.status is SkillLifecycleStatus.PROMOTED
    assert revocation.status is SkillLifecycleStatus.REVOKED
    with pytest.raises(SkillFabricRuntimeError, match="skill_revoked"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            envelope=_envelope(mission_id),
            execution_executor=_successful_executor,
        )

    event_kinds = [event.event_kind for event in kernel.telemetry_sink.store.load_events()]
    assert TelemetryEventKind.SKILL_MANIFEST_REGISTERED in event_kinds
    assert TelemetryEventKind.SKILL_SCAN_COMPLETED in event_kinds
    assert TelemetryEventKind.SKILL_APPROVED in event_kinds
    assert TelemetryEventKind.SKILL_REVOKED in event_kinds
    metric_kinds = [metric.metric_kind for metric in kernel.telemetry_sink.store.load_metrics()]
    assert TelemetryMetricKind.SKILL_SCAN_PASS_RATE in metric_kinds


def test_scanned_but_unapproved_skill_cannot_execute(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = GovernedSkillFabricRuntime(kernel)
    manifest = _skill_manifest()

    runtime.register_manifest(mission_id=mission_id, manifest=manifest)
    runtime.scan_skill(mission_id=mission_id, skill_id=manifest.skill_id)

    with pytest.raises(SkillFabricRuntimeError, match="skill_not_approved"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            envelope=_envelope(mission_id),
            execution_executor=_successful_executor,
        )


def test_approved_skill_execution_requires_mission_authority_and_runtime_executor(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = GovernedSkillFabricRuntime(kernel)
    manifest = _approved_manifest(runtime, mission_id)

    with pytest.raises(SkillFabricRuntimeError, match="missing_authority_envelope"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            envelope=None,
            execution_executor=_successful_executor,
        )

    with pytest.raises(SkillFabricRuntimeError, match="procedure_executor_required"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            envelope=_envelope(mission_id),
            execution_executor=None,
        )

    expanded = _envelope(mission_id, allowed_actions=["write"])
    with pytest.raises(SkillFabricRuntimeError, match="skill_authority_outside_mission_envelope"):
        runtime.execute_skill(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            envelope=expanded,
            execution_executor=_successful_executor,
        )

    result = runtime.execute_skill(
        mission_id=mission_id,
        skill_id=manifest.skill_id,
        envelope=_envelope(mission_id),
        execution_executor=_successful_executor,
        inputs={"topic": "AI training market"},
    )

    assert result.status == "completed"
    assert result.receipt_refs == ["receipt_skill_1"]
    assert result.finalgate_certificate_refs == ["finalgate_skill_1"]
    assert result.authority_effect == "none"
    assert result.can_execute is False
    events = kernel.store.load_events(mission_id)
    assert any(event.event_type == "skill_execution_started" for event in events)
    assert any(event.event_type == "procedure_step_completed" for event in events)


def test_skill_cannot_bypass_runtime_or_treat_memory_receipt_finalgate_as_authority(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="skill memory cannot become authority"):
        _skill_manifest(memory_refs_are_authority=True)

    with pytest.raises(ValueError, match="skill receipt/finalgate refs cannot become authority"):
        _skill_manifest(receipts_are_authority=True)

    with pytest.raises(ValueError, match="procedure step cannot call runtime directly"):
        ProcedureStep(
            step_id="bad",
            title="Bad direct runtime",
            action_kind="read",
            safe_summary="Import runtime and call dispatcher",
            requested_tools=["workspace"],
            metadata={"import": "sentinel.agent.organs.delegated_action_gate", "runtime_dispatch": True},
        )


def test_procedure_replay_reconstructs_without_reexecution_and_detects_tamper(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = GovernedSkillFabricRuntime(kernel)
    manifest = _approved_manifest(runtime, mission_id)
    calls: list[str] = []

    result = runtime.execute_skill(
        mission_id=mission_id,
        skill_id=manifest.skill_id,
        envelope=_envelope(mission_id),
        execution_executor=lambda request: _successful_executor(request, calls=calls),
    )
    replay = ProcedureReplayBuilder(kernel.store).build(mission_id, procedure_run_id=result.procedure_run_id)

    assert calls == ["execute"]
    assert replay.reexecuted_actions is False
    assert replay.skill_id == manifest.skill_id
    assert replay.receipt_refs == ["receipt_skill_1"]
    assert replay.finalgate_certificate_refs == ["finalgate_skill_1"]
    assert replay.telemetry_refs
    assert replay.timeline_valid is True

    events_path = kernel.store.mission_dir(mission_id) / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[-1])
    tampered["safe_summary"] = "tampered"
    lines[-1] = json.dumps(tampered, sort_keys=True)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tampered_replay = ProcedureReplayBuilder(kernel.store).build(mission_id, procedure_run_id=result.procedure_run_id)
    assert tampered_replay.timeline_valid is False


def test_browser_trajectory_procedure_blocks_sensitive_boundaries() -> None:
    trajectory = CompiledTrajectoryProcedure(
        trajectory_id="browser_public_observe",
        skill_id="skill.browser_public_observe",
        version="1.0.0",
        required_browser_authority=["browser_observe_public"],
        target_ref_hashes=["target_hash_1"],
        evidence_refs=["browser_evidence_1"],
        boundary_conditions=["no_login", "no_payment", "no_submit"],
    )

    assert trajectory.authority_effect == "none"
    assert trajectory.can_execute is False

    with pytest.raises(ValueError, match="browser trajectory crosses sensitive boundary"):
        CompiledTrajectoryProcedure(
            trajectory_id="browser_login",
            skill_id="skill.browser_login",
            version="1.0.0",
            required_browser_authority=["browser_login"],
            target_ref_hashes=["target_hash_1"],
            evidence_refs=["browser_evidence_1"],
            boundary_conditions=["login", "payment"],
        )


def test_skill_persistence_redacts_raw_secret_prompt_provider_response_reasoning(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe skill payload"):
        _skill_manifest(
            metadata={
                "raw_prompt": "redacted placeholder",
                "provider_response": "redacted placeholder",
                "reasoning": "redacted placeholder",
            }
        )


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    draft = MissionDraft(
        title="Skill fabric mission",
        objective="Govern a reusable market research procedure.",
        constraints=["no credentials", "no external mutation"],
    )
    authority = MissionAuthoritySummary(
        mission_id="draft_skill",
        allowed_actions=["read", "analyze", "draft"],
        forbidden_actions=["payment", "credential_unlock", "channel_send"],
        summary="Skill fabric test only.",
    )
    record = kernel.create_mission(session_id="session_skill", draft=draft, authority_summary=authority)
    return kernel, record.mission_id


def _envelope(mission_id: str, *, allowed_actions: list[str] | None = None) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_skill",
        created_at="2026-06-08T00:00:00Z",
        mission_title="Skill fabric mission",
        mission_objective="Govern a reusable market research procedure.",
        allowed_actions=allowed_actions or ["read", "analyze", "draft"],
        allowed_tools=["workspace", "memory", "harness"],
        forbidden_actions=["payment", "credential_unlock", "channel_send"],
        risk_appetite_score=10,
        max_actions=10,
        max_cost_usd=0.0,
        expires_at="2026-06-09T00:00:00Z",
    )


def _skill_manifest(
    *,
    skill_id: str = "skill.market_research",
    declared_authority: list[SkillDeclaredAuthority] | None = None,
    declared_side_effects: list[SkillDeclaredSideEffect] | None = None,
    procedure: ProcedureManifest | None = None,
    metadata: dict | None = None,
    memory_refs_are_authority: bool = False,
    receipts_are_authority: bool = False,
) -> SkillManifest:
    return SkillManifest(
        skill_id=skill_id,
        version="1.0.0",
        name="Market Research Procedure",
        safe_summary="Reusable market research and draft procedure.",
        provenance={"source_kind": "sentinel_native", "source_ref": "local:test", "content_hash": "hash_1"},
        declared_authority=declared_authority
        if declared_authority is not None
        else [SkillDeclaredAuthority(action="read"), SkillDeclaredAuthority(action="analyze"), SkillDeclaredAuthority(action="draft")],
        declared_side_effects=declared_side_effects
        if declared_side_effects is not None
        else [SkillDeclaredSideEffect(effect_kind="local_report_draft", reversible=True)],
        input_contract=SkillInputContract(required_fields=["topic"]),
        output_contract=SkillOutputContract(required_fields=["safe_summary", "evidence_refs"]),
        evidence_requirements=[SkillEvidenceRequirement(requirement="at least one source evidence ref")],
        risk_profile=SkillRiskProfile(risk_lane="low", max_risk_score=10),
        procedure=procedure or _procedure(),
        metadata=metadata or {},
        memory_refs_are_authority=memory_refs_are_authority,
        receipts_are_authority=receipts_are_authority,
    ).with_hash()


def _procedure(*, steps: list[ProcedureStep] | None = None) -> ProcedureManifest:
    return ProcedureManifest(
        procedure_id="procedure.market_research",
        version="1.0.0",
        title="Market research procedure",
        safe_summary="Read scoped context, analyze, and draft a report.",
        graph={"steps": steps or [_step("read"), _step("analyze"), _step("draft")]},
        rollback_posture={"posture": "no_external_side_effects", "reversible": True},
    )


def _step(action: str) -> ProcedureStep:
    return ProcedureStep(
        step_id=f"step_{action}",
        title=f"{action.title()} step",
        action_kind=action,
        safe_summary=f"{action.title()} inside scoped mission authority.",
        requested_tools=["workspace"] if action != "analyze" else ["memory", "harness"],
        evidence_requirements=["evidence_ref"],
    )


def _approved_manifest(runtime: GovernedSkillFabricRuntime, mission_id: str) -> SkillManifest:
    manifest = _skill_manifest()
    runtime.register_manifest(mission_id=mission_id, manifest=manifest)
    runtime.scan_skill(mission_id=mission_id, skill_id=manifest.skill_id)
    runtime.evaluate_skill(mission_id=mission_id, skill_id=manifest.skill_id)
    runtime.approve_skill(mission_id=mission_id, skill_id=manifest.skill_id, approved_by="operator")
    return manifest


def _successful_executor(request, *, calls: list[str] | None = None):
    if calls is not None:
        calls.append("execute")
    return {
        "status": "completed",
        "safe_summary": "Procedure completed with scoped evidence.",
        "receipt_refs": ["receipt_skill_1"],
        "finalgate_certificate_refs": ["finalgate_skill_1"],
        "memory_feedback_refs": ["memory_skill_1"],
        "evidence_refs": ["evidence_skill_1"],
        "step_results": [
            {"step_id": "step_read", "status": "completed", "safe_summary": "Read context."},
            {"step_id": "step_analyze", "status": "completed", "safe_summary": "Analyzed context."},
            {"step_id": "step_draft", "status": "completed", "safe_summary": "Drafted report."},
        ],
    }
