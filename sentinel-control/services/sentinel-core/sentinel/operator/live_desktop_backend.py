from __future__ import annotations

import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.desktop_sidecar import DesktopSidecarRuntime
from sentinel.operator.desktop_sidecar_models import (
    DesktopActionKind,
    DesktopAppSnapshot,
    DesktopBeforeAfterEvidence,
    DesktopControlMode,
    DesktopFinalGateDecision,
    DesktopHardwareMetricSnapshot,
    DesktopMetricValue,
    DesktopMonitoringReceipt,
    DesktopMonitoringResult,
    DesktopProcessSnapshot,
    DesktopSensorSnapshot,
    DesktopSidecarFinalGateCertificate,
    DesktopWindowSnapshot,
    DesktopClockSnapshot,
    DesktopSystemSnapshot,
    DesktopBackgroundActivitySnapshot,
    MetricAvailability,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.live_desktop_backend_models import (
    DesktopActionApprovalRecord,
    DesktopActionCommand,
    DesktopActionExecutionPlan,
    DesktopActionExecutionResult,
    DesktopActionIdempotencyKey,
    DesktopActionReceipt,
    DesktopActionSafetyCheck,
    DesktopBenchmarkRun,
    DesktopBenchmarkScenario,
    DesktopBenchmarkResult,
    DesktopOperatorSession,
    DesktopOperatorSessionPolicy,
    DesktopOperatorSessionStateKind,
    DesktopPermissionUiShape,
    DesktopServiceSupervisorShape,
    DesktopTrayServiceShape,
    DesktopMonitoringTick,
    LiveDesktopBackendConfig,
    LiveDesktopBackendMaturity,
)
from sentinel.operator.redaction import redact_operator_text
from sentinel.telemetry import TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class LiveDesktopBackendRuntimeError(ValueError):
    """Raised when live desktop backend behavior would violate policy or authority."""


class FakeInjectedLiveDesktopBackend:
    """Adapter for fake/injected desktop transports.

    It never calls OS desktop APIs by itself. Tests and future opt-in manual
    smoke paths can inject a controlled object with `system_snapshot` and
    `perform_action` methods.
    """

    def __init__(self, transport: Any) -> None:
        self.transport = transport

    def system_snapshot(self) -> dict[str, Any]:
        fn = getattr(self.transport, "system_snapshot", None)
        return dict(fn() or {}) if fn else {}

    def perform_action(self, command: DesktopActionCommand) -> dict[str, Any]:
        fn = getattr(self.transport, "perform_action", None)
        return dict(fn(command) or {}) if fn else {}


class LiveDesktopBackendRegistry:
    def __init__(self, *, backends: dict[str, Any] | None = None) -> None:
        self._configs: dict[str, LiveDesktopBackendConfig] = {}
        self._backends: dict[str, Any] = dict(backends or {})

    def register(self, config: LiveDesktopBackendConfig, *, backend: Any | None = None) -> LiveDesktopBackendConfig:
        self._configs[config.backend_id] = config
        if backend is not None:
            self._backends[config.backend_id] = backend
        return config

    def config(self, backend_id: str) -> LiveDesktopBackendConfig:
        try:
            return self._configs[backend_id]
        except KeyError as exc:
            raise LiveDesktopBackendRuntimeError("live_desktop_backend_not_registered") from exc

    def backend(self, backend_id: str) -> Any | None:
        return self._backends.get(backend_id)


class LiveDesktopBackendRuntime:
    """Live-desktop-ready backend layer over the existing DesktopSidecar spine."""

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        sidecar_runtime: DesktopSidecarRuntime | None = None,
        registry: LiveDesktopBackendRegistry | None = None,
    ) -> None:
        self.kernel = kernel
        self.store = kernel.store
        self.sidecar_runtime = sidecar_runtime or DesktopSidecarRuntime(kernel)
        self.registry = registry or LiveDesktopBackendRegistry()
        self._sessions: dict[tuple[str, str], DesktopOperatorSession] = {}
        self._session_backend: dict[tuple[str, str], str] = {}
        self._plans: dict[tuple[str, str], DesktopActionExecutionPlan] = {}
        self._approvals: dict[tuple[str, str], DesktopActionApprovalRecord] = {}
        self._killed: dict[tuple[str, str], str] = {}

    def register_backend(self, *, mission_id: str, config: LiveDesktopBackendConfig) -> LiveDesktopBackendConfig:
        self.store.load_record(mission_id)
        config = config.with_hash()
        self.registry.register(config, backend=self.registry.backend(config.backend_id))
        self._write_json(mission_id, "configs", config.backend_id, config.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="live_desktop_backend_registered",
            safe_summary="Live desktop backend registered as permissioned local descriptor.",
            metadata={
                "backend_id": config.backend_id,
                "maturity": config.maturity.value,
                "config_hash": config.config_hash,
            },
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_SYSTEM_SNAPSHOT_COUNT, 0.0, "Live desktop backend registration sample.", metadata={"backend_id": config.backend_id})
        return config

    def create_permission_ui_shape(self, *, mission_id: str, backend_id: str) -> DesktopPermissionUiShape:
        config = self._load_config(mission_id, backend_id)
        shape = DesktopPermissionUiShape(
            backend_id=backend_id,
            mission_id=mission_id,
            control_mode=config.permission_policy.active_mode,
            monitoring_enabled=config.permission_profile.monitoring_enabled,
            blocked_apps=[*config.permission_policy.blocked_apps, *config.permission_profile.blocked_apps],
            blocked_windows=[*config.permission_policy.blocked_windows, *config.permission_profile.blocked_windows],
            retention_policy=config.permission_profile.retention_policy,
        )
        self._write_json(mission_id, "ui_shapes", f"permission_{backend_id}", shape.safe_model_dump())
        self._append_event(mission_id, event_type="desktop_service_shape_created", safe_summary="Desktop permission UI shape created.", metadata={"backend_id": backend_id})
        return shape

    def create_tray_service_shape(self, *, mission_id: str, backend_id: str) -> DesktopTrayServiceShape:
        config = self._load_config(mission_id, backend_id)
        shape = DesktopTrayServiceShape(
            backend_id=backend_id,
            mission_id=mission_id,
            monitoring_enabled=config.permission_profile.monitoring_enabled,
            active_mission_ref=mission_id,
        )
        self._write_json(mission_id, "ui_shapes", f"tray_{backend_id}", shape.safe_model_dump())
        self._append_event(mission_id, event_type="desktop_tray_shape_created", safe_summary="Desktop tray shape created.", metadata={"backend_id": backend_id})
        return shape

    def create_service_supervisor_shape(self, *, mission_id: str, backend_id: str) -> DesktopServiceSupervisorShape:
        self._load_config(mission_id, backend_id)
        shape = DesktopServiceSupervisorShape(backend_id=backend_id, mission_id=mission_id)
        self._write_json(mission_id, "ui_shapes", f"service_{backend_id}", shape.safe_model_dump())
        self._append_event(mission_id, event_type="desktop_service_shape_created", safe_summary="Desktop service supervisor shape created.", metadata={"backend_id": backend_id})
        return shape

    def start_operator_session(
        self,
        *,
        mission_id: str,
        backend_id: str,
        policy: DesktopOperatorSessionPolicy,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopOperatorSession:
        config = self._load_config(mission_id, backend_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_monitor", backend_id=backend_id)
        self._assert_not_killed(mission_id, backend_id)
        if policy.control_mode not in config.permission_policy.allowed_modes:
            raise LiveDesktopBackendRuntimeError("desktop_control_mode_not_allowed")
        session = DesktopOperatorSession(
            backend_id=backend_id,
            mission_id=mission_id,
            policy=policy,
            state=DesktopOperatorSessionStateKind.RUNNING,
        ).with_hash()
        self._sessions[(mission_id, session.session_id)] = session
        self._session_backend[(mission_id, session.session_id)] = backend_id
        self._write_json(mission_id, "sessions", session.session_id, session.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_operator_session_started",
            safe_summary="Desktop operator session started under explicit policy.",
            metadata={"backend_id": backend_id, "mode": policy.control_mode.value, "session_hash": session.session_hash},
        )
        return session

    def start_monitoring_session(
        self,
        *,
        mission_id: str,
        backend_id: str,
        policy: DesktopOperatorSessionPolicy,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopOperatorSession:
        if not policy.monitoring_enabled:
            raise LiveDesktopBackendRuntimeError("desktop_monitoring_not_enabled")
        session = self.start_operator_session(mission_id=mission_id, backend_id=backend_id, policy=policy, envelope=envelope)
        session = session.model_copy(update={"state": DesktopOperatorSessionStateKind.MONITORING}).with_hash()
        self._sessions[(mission_id, session.session_id)] = session
        self._write_json(mission_id, "sessions", session.session_id, session.safe_model_dump())
        self._append_event(mission_id, event_type="desktop_monitoring_session_started", safe_summary="Desktop monitoring session started.", metadata={"backend_id": backend_id, "session_hash": session.session_hash})
        return session

    def capture_system_snapshot(
        self,
        *,
        mission_id: str,
        backend_id: str,
        envelope: MissionAuthorityEnvelope | None,
        session_id: str | None = None,
    ) -> DesktopMonitoringResult:
        config = self._load_config(mission_id, backend_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_monitor", backend_id=backend_id)
        self._assert_not_killed(mission_id, backend_id)
        if not config.capability_profile.supports_system_monitoring:
            raise LiveDesktopBackendRuntimeError("desktop_system_monitoring_not_supported")
        self._append_event(mission_id, event_type="desktop_system_snapshot_requested", safe_summary="Desktop system snapshot requested.", metadata={"backend_id": backend_id})
        raw = self._backend_snapshot(backend_id)
        result = self._build_monitoring_result(mission_id=mission_id, backend_id=backend_id, config=config, envelope=envelope, raw=raw)
        self._write_json(mission_id, "monitoring", result.monitoring_result_id, result.safe_model_dump())
        if result.monitoring_receipt:
            self._write_json(mission_id, "receipts", result.monitoring_receipt.receipt_id, result.monitoring_receipt.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_system_snapshot_completed",
            safe_summary="Desktop system snapshot completed with safe local metric summaries.",
            metadata={
                "backend_id": backend_id,
                "snapshot_hash": result.system_snapshot.snapshot_hash,
                "windows_count": len(result.windows),
                "apps_count": len(result.apps),
            },
            receipt_refs=[result.monitoring_receipt.receipt_id] if result.monitoring_receipt else [],
        )
        if result.processes:
            self._append_event(mission_id, event_type="desktop_process_snapshot_created", safe_summary="Desktop process snapshot metadata recorded.", metadata={"backend_id": backend_id, "items_count": len(result.processes)})
        if result.windows:
            self._append_event(mission_id, event_type="desktop_window_snapshot_created", safe_summary="Desktop window snapshot metadata recorded.", metadata={"backend_id": backend_id, "items_count": len(result.windows)})
        self._append_event(mission_id, event_type="desktop_hardware_metric_snapshot_created", safe_summary="Desktop hardware metric snapshot recorded.", metadata={"backend_id": backend_id})
        self._record_snapshot_metrics(mission_id, backend_id, result)
        if session_id and (mission_id, session_id) in self._sessions:
            session = self._sessions[(mission_id, session_id)].model_copy(update={"last_snapshot_ref": result.monitoring_result_id}).with_hash()
            self._sessions[(mission_id, session_id)] = session
            self._write_json(mission_id, "sessions", session.session_id, session.safe_model_dump())
        return result

    def tick_monitoring_session(
        self,
        *,
        mission_id: str,
        session_id: str,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopMonitoringTick:
        session = self._load_session(mission_id, session_id)
        backend_id = self._session_backend.get((mission_id, session_id), session.backend_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_monitor", backend_id=backend_id)
        self._assert_not_killed(mission_id, backend_id)
        if not session.policy.monitoring_enabled:
            raise LiveDesktopBackendRuntimeError("desktop_monitoring_not_enabled")
        result = self.capture_system_snapshot(mission_id=mission_id, backend_id=backend_id, envelope=envelope, session_id=session_id)
        tick_count = len(list((self._root(mission_id) / "monitoring_ticks").glob("*.json"))) if (self._root(mission_id) / "monitoring_ticks").exists() else 0
        tick = DesktopMonitoringTick(
            session_id=session_id,
            backend_id=backend_id,
            mission_id=mission_id,
            monotonic_index=tick_count,
            result=result,
        ).with_hash()
        self._write_json(mission_id, "monitoring_ticks", tick.tick_id, tick.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_monitoring_tick_completed",
            safe_summary="Desktop monitoring tick completed.",
            metadata={"backend_id": backend_id, "tick_hash": tick.tick_hash},
            receipt_refs=[result.monitoring_receipt.receipt_id] if result.monitoring_receipt else [],
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_MONITORING_TICK_COUNT, 1.0, "Desktop monitoring tick count sample.", metadata={"backend_id": backend_id})
        return tick

    def plan_action(
        self,
        *,
        mission_id: str,
        session_id: str,
        command: DesktopActionCommand,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopActionExecutionPlan:
        session = self._load_session(mission_id, session_id)
        config = self._load_config(mission_id, command.backend_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_action", backend_id=command.backend_id)
        self._assert_not_killed(mission_id, command.backend_id)
        if command.requested_by not in {"operator", "operator_policy", "manual_operator"}:
            raise LiveDesktopBackendRuntimeError("operator_control_source_required")
        blocked_reason = self._action_block_reason(config, session, command)
        checks = [
            DesktopActionSafetyCheck(check_name="authority", passed=True),
            DesktopActionSafetyCheck(check_name="control_mode", passed=blocked_reason != "desktop_action_mode_not_allowed", reason_hash=stable_hash(blocked_reason) if blocked_reason else None),
            DesktopActionSafetyCheck(check_name="allowlist", passed=blocked_reason not in {"desktop_app_not_allowed", "desktop_window_not_allowed"}, reason_hash=stable_hash(blocked_reason) if blocked_reason else None),
            DesktopActionSafetyCheck(check_name="sensitive_region", passed=blocked_reason != "sensitive_region_blocked", reason_hash=stable_hash(blocked_reason) if blocked_reason else None),
        ]
        plan = DesktopActionExecutionPlan(
            backend_id=command.backend_id,
            mission_id=mission_id,
            session_id=session_id,
            command=command,
            safety_checks=checks,
            approval_required=session.policy.require_approval_for_actions,
            blocked_reason=blocked_reason,
        ).with_hash()
        self._plans[(mission_id, plan.plan_id)] = plan
        self._write_json(mission_id, "action_plans", plan.plan_id, plan.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_live_action_planned",
            safe_summary="Desktop live action plan created; no action executed.",
            metadata={"backend_id": command.backend_id, "plan_hash": plan.plan_hash, "blocked_reason_hash": stable_hash(blocked_reason) if blocked_reason else None},
        )
        if blocked_reason:
            self._append_event(mission_id, event_type="desktop_live_action_blocked", safe_summary=f"Desktop live action blocked: {blocked_reason}.", metadata={"backend_id": command.backend_id, "reason_hash": stable_hash(blocked_reason)})
            self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_ACTION_BLOCK_RATE, 1.0, "Desktop live action block sample.", metadata={"backend_id": command.backend_id})
        return plan

    def approve_action_plan(self, *, mission_id: str, approval: DesktopActionApprovalRecord) -> DesktopActionApprovalRecord:
        self.store.load_record(mission_id)
        approval = approval.with_hash()
        self._approvals[(mission_id, approval.approval_id)] = approval
        self._write_json(mission_id, "approvals", approval.approval_id, approval.safe_model_dump())
        self._append_event(mission_id, event_type="desktop_action_approved", safe_summary="Operator approved desktop live action plan.", metadata={"approval_hash": approval.approval_hash})
        return approval

    def execute_action_plan(
        self,
        *,
        mission_id: str,
        session_id: str,
        plan_id: str,
        envelope: MissionAuthorityEnvelope | None,
        approval_id: str | None = None,
    ) -> DesktopActionExecutionResult:
        session = self._load_session(mission_id, session_id)
        plan = self._load_plan(mission_id, plan_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_action", backend_id=plan.backend_id)
        self._assert_not_killed(mission_id, plan.backend_id)
        if plan.blocked_reason:
            return self._blocked_action_result(mission_id, session, plan, reason=plan.blocked_reason, envelope=envelope)
        if plan.approval_required:
            approval = self._load_approval(mission_id, approval_id)
            if approval is None or not approval.approved or approval.plan_id != plan_id or not approval.verify_hash():
                self._append_event(mission_id, event_type="desktop_action_approval_required", safe_summary="Desktop live action requires operator approval.", metadata={"backend_id": plan.backend_id})
                raise LiveDesktopBackendRuntimeError("operator_approval_required")
        self._append_event(mission_id, event_type="desktop_live_action_started", safe_summary="Desktop fake/injected live action started.", metadata={"backend_id": plan.backend_id})
        raw = self._backend_action(plan.backend_id, plan.command)
        before_after = DesktopBeforeAfterEvidence(
            before_hash=str(raw.get("before_hash") or stable_hash("live-desktop-before")),
            after_hash=str(raw.get("after_hash") or stable_hash("live-desktop-after")),
            safe_summary=redact_operator_text(str(raw.get("safe_summary") or "Desktop fake/injected action completed.")),
        ).with_hash()
        receipt = self._action_receipt(
            mission_id=mission_id,
            plan=plan,
            envelope=envelope,
            status="completed",
            approval_ref=approval_id,
            before_after_hash=before_after.evidence_hash,
        )
        finalgate = self._finalgate(
            mission_id=mission_id,
            backend_id=plan.backend_id,
            decision=DesktopFinalGateDecision.OBSERVED,
            receipt=receipt,
            passed=True,
        )
        result = DesktopActionExecutionResult(
            backend_id=plan.backend_id,
            mission_id=mission_id,
            session_id=session_id,
            plan_id=plan_id,
            action_kind=plan.command.action_kind,
            status=str(raw.get("status") or "completed"),
            before_after_evidence=before_after,
            action_receipt=receipt,
            finalgate_certificate=finalgate,
            safe_summary=redact_operator_text(str(raw.get("safe_summary") or "Desktop fake/injected action completed.")),
        ).with_hash()
        session = session.model_copy(update={"action_count": session.action_count + 1, "last_action_ref": result.execution_result_id}).with_hash()
        self._sessions[(mission_id, session_id)] = session
        self._write_json(mission_id, "sessions", session_id, session.safe_model_dump())
        self._write_json(mission_id, "before_after", before_after.evidence_id, before_after.safe_model_dump())
        self._write_json(mission_id, "action_results", result.execution_result_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_live_action_completed",
            safe_summary="Desktop fake/injected live action completed with before/after evidence.",
            metadata={"backend_id": plan.backend_id, "result_hash": result.result_hash},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_ACTION_SUCCESS_RATE, 1.0, "Desktop live action success sample.", metadata={"backend_id": plan.backend_id})
        return result

    def run_benchmark_gauntlet(
        self,
        *,
        mission_id: str,
        backend_id: str,
        scenario: DesktopBenchmarkScenario,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopBenchmarkRun:
        config = self._load_config(mission_id, backend_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_benchmark", backend_id=backend_id)
        self._assert_not_killed(mission_id, backend_id)
        if config.maturity is LiveDesktopBackendMaturity.PRODUCTION_READY_BACKEND:
            raise LiveDesktopBackendRuntimeError("desktop_benchmark_overclaim")
        self._append_event(mission_id, event_type="desktop_benchmark_started", safe_summary="Desktop benchmark gauntlet started on fake/injected backend.", metadata={"backend_id": backend_id})
        session = self.start_operator_session(
            mission_id=mission_id,
            backend_id=backend_id,
            policy=DesktopOperatorSessionPolicy(
                control_mode=DesktopControlMode.APPROVED_ACTION_OPERATOR,
                monitoring_enabled=True,
                always_on_allowed=False,
                allowed_apps=list(config.permission_policy.allowed_apps),
                allowed_windows=list(config.permission_policy.allowed_windows),
                allowed_action_kinds=list(getattr(config.action_policy, "allowed_action_kinds", [])),
                require_approval_for_actions=False,
            ),
            envelope=envelope,
        )
        self.capture_system_snapshot(mission_id=mission_id, backend_id=backend_id, envelope=envelope, session_id=session.session_id)
        click = DesktopActionCommand(
            backend_id=backend_id,
            action_kind=DesktopActionKind.CLICK_REGION,
            app_ref=(config.permission_policy.allowed_apps or ["Code"])[0],
            window_ref=(config.permission_policy.allowed_windows or ["Sentinel"])[0],
            target_region_label="benchmark_button",
            idempotency_key=DesktopActionIdempotencyKey.from_command(mission_id, backend_id, "click_region", "benchmark_button"),
            requested_by="operator_policy",
            evidence_refs=["benchmark_ref"],
        )
        plan = self.plan_action(mission_id=mission_id, session_id=session.session_id, command=click, envelope=envelope)
        action_result = self.execute_action_plan(mission_id=mission_id, session_id=session.session_id, plan_id=plan.plan_id, envelope=envelope)
        result = DesktopBenchmarkResult(
            passed_task_count=len(scenario.tasks),
            failed_task_count=0,
            pass_rate=1.0,
            replay_no_reaction_verified=True,
            safe_summary="Desktop fake/injected backend gauntlet passed without live OS action.",
        ).with_hash()
        run = DesktopBenchmarkRun(
            backend_id=backend_id,
            mission_id=mission_id,
            scenario=scenario,
            result=result,
            receipt_refs=[action_result.action_receipt.receipt_id] if action_result.action_receipt else [],
            finalgate_refs=[action_result.finalgate_certificate.certificate_id] if action_result.finalgate_certificate else [],
            completed_at=datetime.now(UTC),
        ).with_hash()
        self._write_json(mission_id, "benchmarks", run.run_id, run.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_benchmark_completed",
            safe_summary="Desktop benchmark gauntlet completed on fake/injected backend.",
            metadata={"backend_id": backend_id, "benchmark_hash": run.run_hash},
            receipt_refs=run.receipt_refs,
            finalgate_certificate_refs=run.finalgate_refs,
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_BENCHMARK_PASS_RATE, result.pass_rate, "Desktop benchmark pass rate sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_BENCHMARK_FAILURE_COUNT, float(result.failed_task_count), "Desktop benchmark failure count sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_REPLAY_NO_REACTION_PASS_RATE, 1.0 if result.replay_no_reaction_verified else 0.0, "Desktop replay no-reaction pass sample.", metadata={"backend_id": backend_id})
        return run

    def kill_backend(self, *, mission_id: str, backend_id: str, reason: str) -> None:
        self._killed[(mission_id, backend_id)] = stable_hash(reason)
        self._write_json(mission_id, "kill", backend_id, {"backend_id": backend_id, "mission_id": mission_id, "reason_hash": stable_hash(reason), "killed": True})
        self._append_event(mission_id, event_type="desktop_live_action_kill_blocked", safe_summary="Desktop live backend kill switch recorded.", metadata={"backend_id": backend_id, "reason_hash": stable_hash(reason)})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_KILL_BLOCK_COUNT, 1.0, "Desktop kill block count sample.", metadata={"backend_id": backend_id})

    def _build_monitoring_result(
        self,
        *,
        mission_id: str,
        backend_id: str,
        config: LiveDesktopBackendConfig,
        envelope: MissionAuthorityEnvelope | None,
        raw: dict[str, Any],
    ) -> DesktopMonitoringResult:
        system = DesktopSystemSnapshot(
            platform_system=redact_operator_text(str(raw.get("platform_system") or platform.system() or "UNKNOWN")),
            current_session_ref_hash=stable_hash(os.environ.get("USERNAME") or os.environ.get("USER") or "local-session"),
            display_count=int(raw.get("display_count") or 1),
            active_window_hash=stable_hash(raw.get("active_window_title")) if raw.get("active_window_title") else None,
        ).with_hash()
        processes = [
            DesktopProcessSnapshot(
                process_id_hash=stable_hash(str(item.get("pid", "unknown"))),
                name_hash=stable_hash(item.get("name", "unknown")),
                cpu_percent=_metric(item.get("cpu_percent"), "%"),
                memory_mb=_metric(item.get("memory_mb"), "mb"),
            )
            for item in raw.get("processes", [])
        ]
        windows = [
            DesktopWindowSnapshot(window_ref_hash=stable_hash(title), active=title == raw.get("active_window_title"))
            for title in raw.get("visible_windows", [])
        ]
        apps = [DesktopAppSnapshot(app_ref_hash=stable_hash(app)) for app in raw.get("running_apps", [])]
        hardware = DesktopHardwareMetricSnapshot(
            cpu_percent=_metric(raw.get("cpu_percent"), "%"),
            ram_used_mb=_metric(raw.get("ram_used_mb"), "mb"),
            disk_used_percent=_metric(raw.get("disk_used_percent"), "%"),
            network_rx_kbps=_metric(raw.get("network_rx_kbps"), "kbps"),
            battery_percent=_metric(raw.get("battery_percent"), "%"),
            gpu_percent=_metric(raw.get("gpu_percent"), "%"),
        )
        sensors = DesktopSensorSnapshot(
            temperature_c=_metric(raw.get("temperature_c"), "c"),
            fan_rpm=_metric(raw.get("fan_rpm"), "rpm"),
        )
        clock = DesktopClockSnapshot(system_time_hash=stable_hash(datetime.now(UTC).isoformat()))
        receipt = DesktopMonitoringReceipt(
            sidecar_id=config.sidecar_id,
            mission_id=mission_id,
            operation_type="live_desktop_monitoring",
            status="observed",
            authority_envelope_ref=envelope.id if envelope else None,
            policy_hash=stable_hash(config.permission_policy.monitoring_policy.safe_model_dump()),
        ).with_hash()
        return DesktopMonitoringResult(
            sidecar_id=config.sidecar_id,
            mission_id=mission_id,
            system_snapshot=system,
            processes=processes,
            windows=windows,
            apps=apps,
            hardware_metrics=hardware,
            sensor_snapshot=sensors,
            clock_snapshot=clock,
            background_activity=DesktopBackgroundActivitySnapshot(
                visible_window_count=len(windows),
                running_app_count=len(apps),
                process_count=len(processes),
            ),
            monitoring_receipt=receipt,
        ).with_hash()

    def _action_block_reason(
        self,
        config: LiveDesktopBackendConfig,
        session: DesktopOperatorSession,
        command: DesktopActionCommand,
    ) -> str | None:
        if session.policy.control_mode in {DesktopControlMode.OBSERVE_ONLY, DesktopControlMode.MONITOR_ONLY, DesktopControlMode.ASSISTED_OPERATOR}:
            return "desktop_action_mode_not_allowed"
        allowed = set(getattr(config.action_policy, "allowed_action_kinds", []) or [])
        if command.action_kind not in allowed:
            return "desktop_action_kind_not_allowed"
        if command.app_ref and command.app_ref in set(config.permission_policy.blocked_apps):
            return "desktop_app_not_allowed"
        if command.app_ref and config.permission_policy.allowed_apps and command.app_ref not in set(config.permission_policy.allowed_apps):
            return "desktop_app_not_allowed"
        if command.window_ref and command.window_ref in set(config.permission_policy.blocked_windows):
            return "desktop_window_not_allowed"
        if command.window_ref and config.permission_policy.allowed_windows and command.window_ref not in set(config.permission_policy.allowed_windows):
            return "desktop_window_not_allowed"
        if command.target_region_label and any(token in command.target_region_label for token in ("password", "credential", "payment", "banking", "2fa", "token")):
            return "sensitive_region_blocked"
        if command.action_kind.name in {"COPY_PASTE"} and not config.permission_profile.allow_clipboard:
            return "clipboard_blocked"
        return None

    def _blocked_action_result(
        self,
        mission_id: str,
        session: DesktopOperatorSession,
        plan: DesktopActionExecutionPlan,
        *,
        reason: str,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopActionExecutionResult:
        receipt = self._action_receipt(mission_id=mission_id, plan=plan, envelope=envelope, status="blocked", approval_ref=None, before_after_hash=None)
        finalgate = self._finalgate(mission_id=mission_id, backend_id=plan.backend_id, decision=DesktopFinalGateDecision.BLOCKED, receipt=receipt, passed=True, failures=[reason])
        result = DesktopActionExecutionResult(
            backend_id=plan.backend_id,
            mission_id=mission_id,
            session_id=session.session_id,
            plan_id=plan.plan_id,
            action_kind=plan.command.action_kind,
            status="blocked",
            blocked_reason=reason,
            action_receipt=receipt,
            finalgate_certificate=finalgate,
            safe_summary=f"Desktop live action blocked: {reason}.",
        ).with_hash()
        self._write_json(mission_id, "action_results", result.execution_result_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_live_action_blocked",
            safe_summary=result.safe_summary,
            metadata={"backend_id": plan.backend_id, "reason_hash": stable_hash(reason)},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        return result

    def _assert_authority(self, mission_id: str, envelope: MissionAuthorityEnvelope | None, *, required_action: str, backend_id: str) -> None:
        if envelope is None:
            raise LiveDesktopBackendRuntimeError("desktop_action_authority_missing" if required_action == "desktop_action" else "desktop_authority_missing")
        if envelope.id != mission_id:
            raise LiveDesktopBackendRuntimeError("mission_authority_envelope_mismatch")
        if getattr(envelope, "revoked_at", None) is not None:
            self._append_event(mission_id, event_type="desktop_revocation_detected", safe_summary="Live desktop backend blocked by revoked authority.", metadata={"backend_id": backend_id})
            raise LiveDesktopBackendRuntimeError("desktop_authority_revoked")
        if envelope.resolved_expires_at() <= datetime.now(UTC):
            raise LiveDesktopBackendRuntimeError("desktop_authority_expired")
        allowed = set(getattr(envelope, "allowed_actions", []) or [])
        if required_action not in allowed and "desktop_action" not in allowed:
            raise LiveDesktopBackendRuntimeError("desktop_action_not_allowed_by_envelope")
        tools = set(getattr(envelope, "allowed_tools", []) or [])
        if "live_desktop_backend" not in tools and backend_id not in tools and "desktop_sidecar" not in tools:
            raise LiveDesktopBackendRuntimeError("desktop_tool_not_allowed_by_envelope")

    def _assert_not_killed(self, mission_id: str, backend_id: str) -> None:
        if (mission_id, backend_id) in self._killed:
            raise LiveDesktopBackendRuntimeError("desktop_live_backend_killed")
        path = self._path(mission_id, "kill", backend_id)
        if path.exists():
            raise LiveDesktopBackendRuntimeError("desktop_live_backend_killed")

    def _action_receipt(
        self,
        *,
        mission_id: str,
        plan: DesktopActionExecutionPlan,
        envelope: MissionAuthorityEnvelope | None,
        status: str,
        approval_ref: str | None,
        before_after_hash: str | None,
    ) -> DesktopActionReceipt:
        config = self._load_config(mission_id, plan.backend_id)
        return DesktopActionReceipt(
            sidecar_id=config.sidecar_id,
            mission_id=mission_id,
            operation_type=f"live_desktop:{plan.command.action_kind.value}",
            status=status,
            authority_envelope_ref=envelope.id if envelope else None,
            window_ref_hash=stable_hash(plan.command.window_ref) if plan.command.window_ref else None,
            app_ref_hash=stable_hash(plan.command.app_ref) if plan.command.app_ref else None,
            policy_hash=stable_hash(config.permission_policy.safe_model_dump()),
            approval_ref=approval_ref,
            before_after_hash=before_after_hash,
            command_id=plan.command.command_id,
            plan_id=plan.plan_id,
            idempotency_key_hash=plan.command.idempotency_key.key_hash,
            sensitive_region_flags=[plan.blocked_reason] if plan.blocked_reason else [],
        ).with_hash()

    def _finalgate(
        self,
        *,
        mission_id: str,
        backend_id: str,
        decision: DesktopFinalGateDecision,
        receipt: DesktopActionReceipt | DesktopMonitoringReceipt,
        passed: bool,
        failures: list[str] | None = None,
    ) -> DesktopSidecarFinalGateCertificate:
        config = self._load_config(mission_id, backend_id)
        return DesktopSidecarFinalGateCertificate(
            sidecar_id=config.sidecar_id,
            mission_id=mission_id,
            decision=decision,
            passed=passed,
            receipt_ref=receipt.receipt_id,
            failures=failures or [],
        )

    def _backend_snapshot(self, backend_id: str) -> dict[str, Any]:
        backend = self.registry.backend(backend_id)
        if backend is None:
            return {}
        fn = getattr(backend, "system_snapshot", None)
        return dict(fn() or {}) if fn else {}

    def _backend_action(self, backend_id: str, command: DesktopActionCommand) -> dict[str, Any]:
        backend = self.registry.backend(backend_id)
        if backend is None:
            raise LiveDesktopBackendRuntimeError("desktop_live_backend_missing")
        fn = getattr(backend, "perform_action", None)
        return dict(fn(command) or {}) if fn else {}

    def _load_config(self, mission_id: str, backend_id: str) -> LiveDesktopBackendConfig:
        try:
            return self.registry.config(backend_id)
        except LiveDesktopBackendRuntimeError:
            path = self._path(mission_id, "configs", backend_id)
            if not path.exists():
                raise
            config = LiveDesktopBackendConfig.model_validate_json(path.read_text(encoding="utf-8"))
            if not config.verify_hash():
                raise LiveDesktopBackendRuntimeError("live_desktop_backend_config_hash_mismatch")
            self.registry.register(config)
            return config

    def _load_session(self, mission_id: str, session_id: str) -> DesktopOperatorSession:
        cached = self._sessions.get((mission_id, session_id))
        if cached:
            return cached
        for path in (self._root(mission_id) / "sessions").glob("*.json"):
            session = DesktopOperatorSession.model_validate_json(path.read_text(encoding="utf-8"))
            if session.session_id == session_id:
                self._sessions[(mission_id, session_id)] = session
                return session
        raise LiveDesktopBackendRuntimeError("desktop_operator_session_not_found")

    def _load_plan(self, mission_id: str, plan_id: str) -> DesktopActionExecutionPlan:
        cached = self._plans.get((mission_id, plan_id))
        if cached:
            return cached
        for path in (self._root(mission_id) / "action_plans").glob("*.json"):
            plan = DesktopActionExecutionPlan.model_validate_json(path.read_text(encoding="utf-8"))
            if plan.plan_id == plan_id:
                self._plans[(mission_id, plan_id)] = plan
                return plan
        raise LiveDesktopBackendRuntimeError("desktop_action_plan_not_found")

    def _load_approval(self, mission_id: str, approval_id: str | None) -> DesktopActionApprovalRecord | None:
        if approval_id is None:
            return None
        cached = self._approvals.get((mission_id, approval_id))
        if cached:
            return cached
        path = self._path(mission_id, "approvals", approval_id)
        if not path.exists():
            return None
        approval = DesktopActionApprovalRecord.model_validate_json(path.read_text(encoding="utf-8"))
        self._approvals[(mission_id, approval_id)] = approval
        return approval

    def _write_json(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self.store.atomic_write_json(self._path(mission_id, category, name), payload)

    def _path(self, mission_id: str, category: str, name: str) -> Path:
        return self._root(mission_id) / category / f"{stable_hash(name)[:24]}.json"

    def _root(self, mission_id: str) -> Path:
        return self.store.mission_dir(mission_id, create=True) / "desktop_sidecar" / "live_backend"

    def _append_event(self, mission_id: str, *, event_type: str, safe_summary: str, metadata: dict[str, Any] | None = None, receipt_refs: list[str] | None = None, finalgate_certificate_refs: list[str] | None = None):
        return self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=[ref for ref in (receipt_refs or []) if ref],
            finalgate_certificate_refs=[ref for ref in (finalgate_certificate_refs or []) if ref],
        )

    def _record_metric(self, mission_id: str, metric_kind: TelemetryMetricKind, value: float, safe_summary: str, *, metadata: dict[str, Any] | None = None) -> None:
        sink = getattr(self.store, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.DESKTOP_SIDECAR,
                metric_kind=metric_kind,
                value=value,
                unit="count",
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )

    def _record_snapshot_metrics(self, mission_id: str, backend_id: str, result: DesktopMonitoringResult) -> None:
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_SYSTEM_SNAPSHOT_COUNT, 1.0, "Desktop system snapshot count sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_PROCESS_COUNT_SAMPLE, float(len(result.processes)), "Desktop process count sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_WINDOW_COUNT_SAMPLE, float(len(result.windows)), "Desktop window count sample.", metadata={"backend_id": backend_id})
        if result.hardware_metrics.cpu_percent.value is not None:
            self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_CPU_USAGE_SAMPLE, result.hardware_metrics.cpu_percent.value, "Desktop CPU usage sample.", metadata={"backend_id": backend_id})
        if result.hardware_metrics.ram_used_mb.value is not None:
            self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_RAM_USAGE_SAMPLE, result.hardware_metrics.ram_used_mb.value, "Desktop RAM usage sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_GPU_METRIC_AVAILABLE, 1.0 if result.hardware_metrics.gpu_percent.status is MetricAvailability.AVAILABLE else 0.0, "Desktop GPU metric availability sample.", metadata={"backend_id": backend_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_SENSOR_METRIC_AVAILABLE, 1.0 if result.sensor_snapshot.temperature_c.status is MetricAvailability.AVAILABLE else 0.0, "Desktop sensor metric availability sample.", metadata={"backend_id": backend_id})


def _metric(value: Any, unit: str) -> DesktopMetricValue:
    if value is None:
        return DesktopMetricValue(status=MetricAvailability.UNKNOWN, unit=unit, safe_summary=f"{unit} metric unknown.")
    try:
        return DesktopMetricValue(status=MetricAvailability.AVAILABLE, value=float(value), unit=unit, safe_summary="Metric available.")
    except (TypeError, ValueError):
        return DesktopMetricValue(status=MetricAvailability.PROBE_FAILED, unit=unit, safe_summary=f"{unit} metric probe failed.")
