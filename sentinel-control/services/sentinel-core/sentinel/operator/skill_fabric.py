from __future__ import annotations

import json
from typing import Any, Callable

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.operator.skill_models import (
    ProcedureRun,
    SkillApprovalRecord,
    SkillExecutionPlan,
    SkillExecutionReceipt,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutionStatus,
    SkillFabricConfig,
    SkillLifecycleRecord,
    SkillLifecycleStatus,
    SkillManifest,
    SkillPromotionRecord,
    SkillQuarantineRecord,
    SkillRevocationRecord,
    SkillSandboxEvaluation,
    SkillScanDecision,
    SkillScannerResult,
    SkillScorecard,
    skill_utc_now,
)
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
)
from sentinel.telemetry import (
    TelemetryDomain,
    TelemetryMetricKind,
    TelemetryMetricSample,
    TelemetrySourceSurface,
)


ProcedureExecutor = Callable[[SkillExecutionRequest], dict[str, Any]]


class SkillFabricRuntimeError(ValueError):
    pass


class GovernedSkillFabricRuntime:
    """Sentinel-native governed skill/procedure fabric.

    Skills are reusable governed contracts. They do not execute by themselves,
    do not create authority, and do not bypass the existing runtime/proof spine.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        config: SkillFabricConfig | None = None,
        harness_runtime: object | None = None,
        worker_fleet_runtime: object | None = None,
        workflow_store: object | None = None,
        memory_adapter: object | None = None,
    ) -> None:
        self.kernel = kernel
        self.config = config or SkillFabricConfig()
        self.harness_runtime = harness_runtime
        self.worker_fleet_runtime = worker_fleet_runtime
        self.workflow_store = workflow_store
        self.memory_adapter = memory_adapter

    def register_manifest(self, *, mission_id: str, manifest: SkillManifest) -> SkillLifecycleRecord:
        self._assert_supported_mission(mission_id)
        manifest = manifest.with_hash()
        self._write_json(mission_id, "manifests", manifest.skill_id, manifest.safe_model_dump())
        record = self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=SkillLifecycleStatus.DRAFT,
            reason="manifest_registered",
        )
        self._append_event(
            mission_id,
            event_type="skill_manifest_registered",
            safe_summary="Skill manifest registered.",
            metadata={
                "skill_id": manifest.skill_id,
                "version": manifest.version,
                "manifest_hash": manifest.manifest_hash,
                "provenance_hash": stable_hash(manifest.provenance.safe_model_dump() if hasattr(manifest.provenance, "safe_model_dump") else manifest.provenance.model_dump(mode="json")),
            },
        )
        return record

    def scan_skill(self, *, mission_id: str, skill_id: str) -> SkillScannerResult:
        manifest = self._load_manifest(mission_id, skill_id)
        findings = self._scan_manifest(manifest)
        decision = SkillScanDecision.QUARANTINE if findings else SkillScanDecision.PASS
        status = SkillLifecycleStatus.QUARANTINED if findings else SkillLifecycleStatus.SCANNED
        result = SkillScannerResult(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=status,
            decision=decision,
            findings=findings,
        ).with_hash()
        self._write_json(mission_id, "scan_results", result.scanner_result_id, result.safe_model_dump())
        self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=status,
            reason="scan_completed",
        )
        if findings:
            quarantine = SkillQuarantineRecord(
                mission_id=mission_id,
                skill_id=manifest.skill_id,
                version=manifest.version,
                reasons=findings,
            )
            self._write_json(mission_id, "quarantine", quarantine.quarantine_id, quarantine.model_dump(mode="json"))
            self._append_event(
                mission_id,
                event_type="skill_quarantined",
                safe_summary="Skill quarantined by scanner.",
                metadata={
                    "skill_id": manifest.skill_id,
                    "finding_count": len(findings),
                    "findings_hash": stable_hash(findings),
                },
            )
        self._append_event(
            mission_id,
            event_type="skill_scan_completed",
            safe_summary="Skill scan completed.",
            metadata={"skill_id": manifest.skill_id, "decision": decision.value, "finding_count": len(findings)},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.SKILL_SCAN_PASS_RATE,
            value=1.0 if not findings else 0.0,
            safe_summary="Skill scan pass rate sample.",
            metadata={"skill_id": manifest.skill_id},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.SKILL_QUARANTINE_RATE,
            value=1.0 if findings else 0.0,
            safe_summary="Skill quarantine rate sample.",
            metadata={"skill_id": manifest.skill_id},
        )
        return result

    def evaluate_skill(self, *, mission_id: str, skill_id: str) -> SkillSandboxEvaluation:
        manifest = self._load_manifest(mission_id, skill_id)
        self._assert_not_quarantined_or_revoked(mission_id, skill_id)
        status = self._load_status(mission_id, skill_id)
        if status.status not in {SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.EVALUATED, SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.PROMOTED}:
            raise SkillFabricRuntimeError("skill_scan_required")
        evaluation = SkillSandboxEvaluation(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            passed=True,
            findings=["dry_run_manifest_contracts_valid"],
        )
        self._write_json(mission_id, "evaluations", evaluation.evaluation_id, evaluation.model_dump(mode="json"))
        scorecard = SkillScorecard(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            scan_passed=True,
            evaluation_passed=True,
            rollback_ready=manifest.procedure.rollback_posture.reversible,
            authority_declared=bool(manifest.declared_authority),
            side_effects_declared=bool(manifest.declared_side_effects),
            evidence_declared=bool(manifest.evidence_requirements),
        )
        self._write_json(mission_id, "scorecards", scorecard.scorecard_id, scorecard.model_dump(mode="json"))
        self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=SkillLifecycleStatus.EVALUATED,
            reason="evaluation_completed",
        )
        self._append_event(
            mission_id,
            event_type="skill_evaluation_completed",
            safe_summary="Skill dry-run evaluation completed.",
            metadata={"skill_id": manifest.skill_id, "evaluation_id": evaluation.evaluation_id, "scorecard_id": scorecard.scorecard_id},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.SKILL_EVAL_SUCCESS_RATE,
            value=1.0,
            safe_summary="Skill eval success sample.",
            metadata={"skill_id": manifest.skill_id},
        )
        return evaluation

    def approve_skill(self, *, mission_id: str, skill_id: str, approved_by: str) -> SkillApprovalRecord:
        manifest = self._load_manifest(mission_id, skill_id)
        self._assert_not_quarantined_or_revoked(mission_id, skill_id)
        status = self._load_status(mission_id, skill_id)
        if status.status not in {SkillLifecycleStatus.EVALUATED, SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.PROMOTED}:
            raise SkillFabricRuntimeError("skill_evaluation_required")
        approval = SkillApprovalRecord(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            approved_by=approved_by,
        )
        self._write_json(mission_id, "approvals", approval.approval_id, approval.model_dump(mode="json"))
        self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=SkillLifecycleStatus.APPROVED,
            reason="skill_approved",
        )
        self._append_event(
            mission_id,
            event_type="skill_approved",
            safe_summary="Skill approved for controlled execution.",
            metadata={"skill_id": manifest.skill_id, "approval_id": approval.approval_id},
        )
        return approval

    def promote_skill(self, *, mission_id: str, skill_id: str, promoted_by: str) -> SkillPromotionRecord:
        manifest = self._load_manifest(mission_id, skill_id)
        self._assert_not_quarantined_or_revoked(mission_id, skill_id)
        status = self._load_status(mission_id, skill_id)
        if status.status not in {SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.PROMOTED}:
            raise SkillFabricRuntimeError("skill_approval_required")
        promotion = SkillPromotionRecord(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            promoted_by=promoted_by,
        )
        self._write_json(mission_id, "promotions", promotion.promotion_id, promotion.model_dump(mode="json"))
        self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=SkillLifecycleStatus.PROMOTED,
            reason="skill_promoted",
        )
        self._append_event(
            mission_id,
            event_type="skill_promoted",
            safe_summary="Skill promoted for recommendation.",
            metadata={"skill_id": manifest.skill_id, "promotion_id": promotion.promotion_id},
        )
        return promotion

    def revoke_skill(self, *, mission_id: str, skill_id: str, revoked_by: str, reason: str = "operator_revoked") -> SkillRevocationRecord:
        manifest = self._load_manifest(mission_id, skill_id)
        revocation = SkillRevocationRecord(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            revoked_by=revoked_by,
            reason=reason,
        )
        self._write_json(mission_id, "revocations", revocation.revocation_id, revocation.model_dump(mode="json"))
        self._set_status(
            mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=SkillLifecycleStatus.REVOKED,
            reason="skill_revoked",
        )
        self._append_event(
            mission_id,
            event_type="skill_revoked",
            safe_summary="Skill revoked.",
            metadata={"skill_id": manifest.skill_id, "revocation_id": revocation.revocation_id},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.SKILL_REVOCATION_COUNT,
            value=1.0,
            safe_summary="Skill revocation count sample.",
            metadata={"skill_id": manifest.skill_id},
        )
        return revocation

    def execute_skill(
        self,
        *,
        mission_id: str,
        skill_id: str,
        envelope: MissionAuthorityEnvelope | None,
        execution_executor: ProcedureExecutor | None,
        inputs: dict[str, Any] | None = None,
        requested_by: str = "operator",
    ) -> SkillExecutionResult:
        manifest = self._load_manifest(mission_id, skill_id)
        if envelope is None:
            raise SkillFabricRuntimeError("missing_authority_envelope")
        if execution_executor is None:
            raise SkillFabricRuntimeError("procedure_executor_required")
        self._assert_envelope_matches(mission_id, envelope)
        self._assert_status_executable(mission_id, skill_id)
        self._assert_skill_inside_envelope(manifest, envelope)
        request = SkillExecutionRequest(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            inputs=inputs or {},
            requested_by=requested_by,
            parent_envelope_id=envelope.id,
        )
        self._write_json(mission_id, "execution_requests", request.request_id, request.model_dump(mode="json"))
        plan = SkillExecutionPlan(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            procedure_id=manifest.procedure.procedure_id,
            step_ids=[step.step_id for step in manifest.procedure.graph.steps],
            declared_actions=[authority.action for authority in manifest.declared_authority],
            rollback_posture=manifest.procedure.rollback_posture,
        )
        self._write_json(mission_id, "execution_plans", plan.plan_id, plan.model_dump(mode="json"))
        run = ProcedureRun(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            procedure_id=manifest.procedure.procedure_id,
            status=SkillExecutionStatus.RUNNING,
            rollback_posture=manifest.procedure.rollback_posture,
        )
        self._write_json(mission_id, "procedure_runs", run.procedure_run_id, run.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="skill_execution_requested",
            safe_summary="Skill execution requested.",
            metadata={"skill_id": manifest.skill_id, "request_id": request.request_id, "procedure_run_id": run.procedure_run_id},
        )
        self._append_event(
            mission_id,
            event_type="skill_execution_started",
            safe_summary="Skill execution started through governed runtime path.",
            metadata={"skill_id": manifest.skill_id, "procedure_run_id": run.procedure_run_id},
        )
        for step in manifest.procedure.graph.steps:
            self._append_event(
                mission_id,
                event_type="procedure_step_started",
                safe_summary=f"Procedure step {step.step_id} started.",
                metadata={"skill_id": manifest.skill_id, "procedure_run_id": run.procedure_run_id, "step_id": step.step_id},
            )
        try:
            executor_payload = execution_executor(request)
        except Exception as exc:  # noqa: BLE001
            return self._blocked_result(
                mission_id=mission_id,
                manifest=manifest,
                run=run,
                reason=f"procedure_executor_failed:{exc.__class__.__name__}",
            )
        result = self._normalize_execution_result(mission_id=mission_id, manifest=manifest, run=run, payload=executor_payload)
        safe_payload = redact_operator_value(executor_payload)
        for step_result in list(safe_payload.get("step_results") or []):
            self._append_event(
                mission_id,
                event_type="procedure_step_completed" if step_result.get("status") == "completed" else "procedure_step_failed",
                safe_summary=step_result.get("safe_summary", "Procedure step completed."),
                metadata={
                    "skill_id": manifest.skill_id,
                    "procedure_run_id": run.procedure_run_id,
                    "step_id": step_result.get("step_id"),
                    "status": step_result.get("status"),
                },
            )
        self._append_event(
            mission_id,
            event_type="skill_execution_completed" if result.status is SkillExecutionStatus.COMPLETED else "skill_execution_failed",
            safe_summary=result.safe_summary,
            metadata={"skill_id": manifest.skill_id, "procedure_run_id": run.procedure_run_id, "result_id": result.result_id},
            receipt_refs=result.receipt_refs,
            finalgate_certificate_refs=result.finalgate_certificate_refs,
            memory_feedback_refs=result.memory_feedback_refs,
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.SKILL_EXECUTION_SUCCESS_RATE,
            value=1.0 if result.status is SkillExecutionStatus.COMPLETED else 0.0,
            safe_summary="Skill execution success sample.",
            metadata={"skill_id": manifest.skill_id},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.PROCEDURE_REUSE_COUNT,
            value=1.0,
            safe_summary="Procedure reuse count sample.",
            metadata={"skill_id": manifest.skill_id, "procedure_id": manifest.procedure.procedure_id},
        )
        return result

    def _normalize_execution_result(
        self,
        *,
        mission_id: str,
        manifest: SkillManifest,
        run: ProcedureRun,
        payload: dict[str, Any],
    ) -> SkillExecutionResult:
        payload = redact_operator_value(payload)
        scan = scan_forbidden_payload_categorized(payload, path="$")
        if scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value] or scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]:
            return self._blocked_result(mission_id=mission_id, manifest=manifest, run=run, reason="procedure_result_unsafe")
        status_text = str(payload.get("status", "completed")).lower()
        status = SkillExecutionStatus.COMPLETED if status_text == "completed" else SkillExecutionStatus.FAILED
        receipt_refs = list(payload.get("receipt_refs") or [])
        finalgate_refs = list(payload.get("finalgate_certificate_refs") or [])
        memory_refs = list(payload.get("memory_feedback_refs") or [])
        if self.config.require_receipts_for_execution and not receipt_refs:
            return self._blocked_result(mission_id=mission_id, manifest=manifest, run=run, reason="procedure_receipt_required")
        if self.config.require_finalgate_for_execution and not finalgate_refs:
            return self._blocked_result(mission_id=mission_id, manifest=manifest, run=run, reason="procedure_finalgate_required")
        step_results = list(payload.get("step_results") or [])
        updated_run = run.model_copy(
            update={
                "status": status,
                "step_results": step_results,
                "receipt_refs": receipt_refs,
                "finalgate_certificate_refs": finalgate_refs,
                "memory_feedback_refs": memory_refs,
                "evidence_refs": list(payload.get("evidence_refs") or []),
                "updated_at": skill_utc_now(),
                "run_hash": "",
            }
        ).with_hash()
        self._write_json(mission_id, "procedure_runs", updated_run.procedure_run_id, updated_run.safe_model_dump())
        receipt = SkillExecutionReceipt(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            procedure_run_id=updated_run.procedure_run_id,
            status=status,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
        ).with_hash()
        self._write_json(mission_id, "execution_receipts", receipt.receipt_id, receipt.safe_model_dump())
        result = SkillExecutionResult(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            procedure_run_id=updated_run.procedure_run_id,
            status=status,
            safe_summary=str(payload.get("safe_summary") or "Skill execution completed."),
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
            evidence_refs=list(payload.get("evidence_refs") or []),
        ).with_hash()
        self._write_json(mission_id, "execution_results", result.result_id, result.safe_model_dump())
        return result

    def _blocked_result(self, *, mission_id: str, manifest: SkillManifest, run: ProcedureRun, reason: str) -> SkillExecutionResult:
        updated_run = run.model_copy(
            update={
                "status": SkillExecutionStatus.BLOCKED,
                "updated_at": skill_utc_now(),
                "run_hash": "",
            }
        ).with_hash()
        self._write_json(mission_id, "procedure_runs", updated_run.procedure_run_id, updated_run.safe_model_dump())
        result = SkillExecutionResult(
            mission_id=mission_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            procedure_run_id=updated_run.procedure_run_id,
            status=SkillExecutionStatus.BLOCKED,
            safe_summary="Skill execution blocked.",
            blocked_reason=reason,
        ).with_hash()
        self._write_json(mission_id, "execution_results", result.result_id, result.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="skill_execution_blocked",
            safe_summary="Skill execution blocked.",
            metadata={"skill_id": manifest.skill_id, "procedure_run_id": updated_run.procedure_run_id, "reason": reason},
        )
        raise SkillFabricRuntimeError(reason)

    def _assert_status_executable(self, mission_id: str, skill_id: str) -> None:
        status = self._load_status(mission_id, skill_id)
        if status.status is SkillLifecycleStatus.REVOKED:
            raise SkillFabricRuntimeError("skill_revoked")
        if status.status is SkillLifecycleStatus.QUARANTINED:
            raise SkillFabricRuntimeError("skill_quarantined")
        if status.status not in {SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.PROMOTED}:
            raise SkillFabricRuntimeError("skill_not_approved")

    def _assert_not_quarantined_or_revoked(self, mission_id: str, skill_id: str) -> None:
        status = self._load_status(mission_id, skill_id)
        if status.status is SkillLifecycleStatus.QUARANTINED:
            raise SkillFabricRuntimeError("skill_quarantined")
        if status.status is SkillLifecycleStatus.REVOKED:
            raise SkillFabricRuntimeError("skill_revoked")

    def _assert_skill_inside_envelope(self, manifest: SkillManifest, envelope: MissionAuthorityEnvelope) -> None:
        envelope_actions = set(getattr(envelope, "allowed_actions", []) or [])
        envelope_tools = set(getattr(envelope, "allowed_tools", []) or [])
        declared_actions = {authority.action for authority in manifest.declared_authority}
        declared_tools = {authority.tool for authority in manifest.declared_authority if authority.tool}
        step_tools = {tool for step in manifest.procedure.graph.steps for tool in step.requested_tools}
        if not declared_actions.issubset(envelope_actions):
            raise SkillFabricRuntimeError("skill_authority_outside_mission_envelope")
        if declared_tools and not declared_tools.issubset(envelope_tools):
            raise SkillFabricRuntimeError("skill_authority_outside_mission_envelope")
        if step_tools and not step_tools.issubset(envelope_tools):
            raise SkillFabricRuntimeError("skill_authority_outside_mission_envelope")
        if getattr(envelope, "revoked_at", None) is not None:
            raise SkillFabricRuntimeError("mission_authority_revoked")

    def _assert_envelope_matches(self, mission_id: str, envelope: MissionAuthorityEnvelope) -> None:
        if envelope.id != mission_id:
            raise SkillFabricRuntimeError("mission_authority_envelope_mismatch")

    def _assert_supported_mission(self, mission_id: str) -> None:
        if self.config.require_existing_mission:
            self.kernel.store.load_record(mission_id)
        if self.kernel.is_terminal(mission_id):
            raise SkillFabricRuntimeError("mission_terminal")

    def _scan_manifest(self, manifest: SkillManifest) -> list[str]:
        payload = manifest.safe_model_dump()
        scan = scan_forbidden_payload_categorized(payload, path="$")
        findings = list(scan[OrganSafetyScanCategory.ALL.value])
        text = json.dumps(payload, sort_keys=True).lower()
        semantic_rules = {
            "authority_expansion": "authority expansion",
            "mission_envelope_expansion": "mission envelope expansion",
            "credential": "credential request",
            "payment": "payment request",
            "trading": "trading request",
            "desktop": "desktop action",
            "remote_plugin": "remote plugin loading",
            "dynamic import": "dynamic import",
            "fallback/auto": "provider fallback/AUTO",
            "provider override": "provider override",
            "memory as authority": "memory-as-authority",
            "receipt as authority": "receipt-as-authority",
            "finalgate as authority": "FinalGate-as-authority",
        }
        for needle, finding in semantic_rules.items():
            if needle in text:
                findings.append(finding)
        return list(dict.fromkeys(redact_operator_text(finding) for finding in findings))

    def _load_manifest(self, mission_id: str, skill_id: str) -> SkillManifest:
        path = self._path(mission_id, "manifests", skill_id)
        manifest = SkillManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if not manifest.verify_hash():
            raise SkillFabricRuntimeError("skill_manifest_hash_mismatch")
        return manifest

    def _load_status(self, mission_id: str, skill_id: str) -> SkillLifecycleRecord:
        path = self._path(mission_id, "status", skill_id)
        if not path.exists():
            raise SkillFabricRuntimeError("skill_not_registered")
        return SkillLifecycleRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _set_status(
        self,
        mission_id: str,
        *,
        skill_id: str,
        version: str,
        status: SkillLifecycleStatus,
        reason: str,
    ) -> SkillLifecycleRecord:
        record = SkillLifecycleRecord(
            mission_id=mission_id,
            skill_id=skill_id,
            version=version,
            status=status,
            reason=reason,
        ).with_hash()
        self._write_json(mission_id, "status", skill_id, record.safe_model_dump())
        return record

    def _write_json(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        path = self._path(mission_id, category, name)
        self.kernel.store.atomic_write_json(path, payload)

    def _path(self, mission_id: str, category: str, name: str):
        safe_name = stable_hash(name)[:24]
        return self.kernel.store.mission_dir(mission_id, create=True) / "skill_fabric" / category / f"{safe_name}.json"

    def _append_event(
        self,
        mission_id: str,
        *,
        event_type: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ):
        return self.kernel.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=redact_operator_text(safe_summary),
            metadata=redact_operator_value(metadata or {}),
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
            memory_feedback_refs=memory_feedback_refs or [],
        )

    def _record_metric(
        self,
        mission_id: str,
        *,
        metric_kind: TelemetryMetricKind,
        value: float,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = getattr(self.kernel, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.SKILL_FABRIC,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=metric_kind,
                value=value,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
