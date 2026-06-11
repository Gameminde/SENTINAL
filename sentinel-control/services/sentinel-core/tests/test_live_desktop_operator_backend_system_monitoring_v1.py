from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.desktop_sidecar import DesktopSidecarRuntime
from sentinel.operator.desktop_sidecar_models import (
    DesktopActionKind,
    DesktopActionPolicy,
    DesktopControlMode,
    DesktopMetricValue,
    DesktopMonitoringPolicy,
    DesktopPermissionPolicy,
    DesktopSidecarConfig,
    DesktopSidecarKind,
    DesktopSidecarMaturity,
    MetricAvailability,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.live_desktop_backend import (
    FakeInjectedLiveDesktopBackend,
    LiveDesktopBackendRegistry,
    LiveDesktopBackendRuntime,
    LiveDesktopBackendRuntimeError,
)
from sentinel.operator.live_desktop_backend_models import (
    DesktopActionApprovalRecord,
    DesktopActionCommand,
    DesktopActionIdempotencyKey,
    DesktopActionSafetyCheck,
    DesktopBenchmarkScenario,
    DesktopControlMode,
    DesktopMonitoringPolicy,
    DesktopOperatorSessionPolicy,
    DesktopPermissionProfile,
    DesktopPermissionUiShape,
    DesktopServiceSupervisorShape,
    DesktopTrayServiceShape,
    LiveDesktopBackendCapabilityProfile,
    LiveDesktopBackendConfig,
    LiveDesktopBackendKind,
    LiveDesktopBackendMaturity,
)
from sentinel.operator.live_desktop_backend_replay import LiveDesktopBackendReplayBuilder
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_live_backend_registration_models_maturity_control_modes_and_ui_shapes(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)

    config = runtime.register_backend(mission_id=mission_id, config=_backend_config())
    permission_shape = runtime.create_permission_ui_shape(mission_id=mission_id, backend_id=config.backend_id)
    tray_shape = runtime.create_tray_service_shape(mission_id=mission_id, backend_id=config.backend_id)
    service_shape = runtime.create_service_supervisor_shape(mission_id=mission_id, backend_id=config.backend_id)

    assert config.maturity is LiveDesktopBackendMaturity.LOCAL_MONITORING_BACKEND
    assert config.capability_profile.supports_system_monitoring is True
    assert config.capability_profile.supports_fake_actions is True
    assert config.capability_profile.supports_live_opt_in_actions is False
    assert DesktopControlMode.MONITOR_ONLY in config.permission_policy.allowed_modes
    assert DesktopControlMode.CONTINUOUS_SUPERVISION_OPERATOR in config.permission_policy.allowed_modes
    assert isinstance(permission_shape, DesktopPermissionUiShape)
    assert permission_shape.operator_visible is True
    assert isinstance(tray_shape, DesktopTrayServiceShape)
    assert tray_shape.monitoring_enabled is False
    assert isinstance(service_shape, DesktopServiceSupervisorShape)
    assert service_shape.production_os_service_ready is False
    assert runtime.store.verify_timeline(mission_id)


def test_system_snapshot_safe_local_behavior_and_unknown_metrics(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config())

    result = runtime.capture_system_snapshot(
        mission_id=mission_id,
        backend_id=config.backend_id,
        envelope=_envelope(mission_id),
    )

    assert backend.system_snapshot_calls == 1
    assert result.system_snapshot.platform_system
    assert result.system_snapshot.current_session_ref_hash
    assert result.system_snapshot.display_count >= 1
    assert result.processes
    assert result.windows
    assert result.apps
    assert result.hardware_metrics.cpu_percent.status is MetricAvailability.AVAILABLE
    assert result.hardware_metrics.gpu_percent.status in {MetricAvailability.UNKNOWN, MetricAvailability.UNSUPPORTED}
    assert result.sensor_snapshot.temperature_c.status in {MetricAvailability.UNKNOWN, MetricAvailability.UNSUPPORTED}
    assert result.monitoring_receipt is not None
    assert result.monitoring_receipt.verify_hash()
    persisted = _mission_text(runtime, mission_id)
    assert "provider_key" not in persisted
    assert "raw_screenshot" not in persisted


def test_monitoring_policy_requires_explicit_enablement_and_blocks_after_kill_revocation(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config())

    with pytest.raises(LiveDesktopBackendRuntimeError, match="desktop_monitoring_not_enabled"):
        runtime.start_monitoring_session(
            mission_id=mission_id,
            backend_id=config.backend_id,
            policy=_operator_policy(monitoring_enabled=False),
            envelope=_envelope(mission_id),
        )

    session = runtime.start_monitoring_session(
        mission_id=mission_id,
        backend_id=config.backend_id,
        policy=_operator_policy(monitoring_enabled=True, always_on_allowed=True),
        envelope=_envelope(mission_id),
    )
    tick = runtime.tick_monitoring_session(
        mission_id=mission_id,
        session_id=session.session_id,
        envelope=_envelope(mission_id),
    )
    assert tick.result is not None
    assert tick.result.monitoring_receipt is not None

    runtime.kill_backend(mission_id=mission_id, backend_id=config.backend_id, reason="operator stop")
    with pytest.raises(LiveDesktopBackendRuntimeError, match="desktop_live_backend_killed"):
        runtime.tick_monitoring_session(
            mission_id=mission_id,
            session_id=session.session_id,
            envelope=_envelope(mission_id),
        )

    runtime2, mission_id2, _backend2 = _runtime(tmp_path)
    config2 = runtime2.register_backend(mission_id=mission_id2, config=_backend_config())
    session2 = runtime2.start_monitoring_session(
        mission_id=mission_id2,
        backend_id=config2.backend_id,
        policy=_operator_policy(monitoring_enabled=True),
        envelope=_envelope(mission_id2),
    )
    with pytest.raises(LiveDesktopBackendRuntimeError, match="desktop_authority_revoked"):
        runtime2.tick_monitoring_session(
            mission_id=mission_id2,
            session_id=session2.session_id,
            envelope=_envelope(mission_id2, revoked=True),
        )


def test_action_planning_and_fake_execution_require_authority_mode_allowlist_and_approval(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR))
    session = runtime.start_operator_session(
        mission_id=mission_id,
        backend_id=config.backend_id,
        policy=_operator_policy(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR),
        envelope=_envelope(mission_id),
    )
    command = _command(config.backend_id)

    with pytest.raises(LiveDesktopBackendRuntimeError, match="desktop_action_authority_missing"):
        runtime.plan_action(mission_id=mission_id, session_id=session.session_id, command=command, envelope=None)

    plan = runtime.plan_action(mission_id=mission_id, session_id=session.session_id, command=command, envelope=_envelope(mission_id))
    assert all(isinstance(check, DesktopActionSafetyCheck) for check in plan.safety_checks)
    assert plan.approval_required is True
    assert backend.action_calls == 0

    with pytest.raises(LiveDesktopBackendRuntimeError, match="operator_approval_required"):
        runtime.execute_action_plan(
            mission_id=mission_id,
            session_id=session.session_id,
            plan_id=plan.plan_id,
            envelope=_envelope(mission_id),
        )

    approval = runtime.approve_action_plan(
        mission_id=mission_id,
        approval=DesktopActionApprovalRecord(plan_id=plan.plan_id, approved=True, approval_source="operator"),
    )
    result = runtime.execute_action_plan(
        mission_id=mission_id,
        session_id=session.session_id,
        plan_id=plan.plan_id,
        approval_id=approval.approval_id,
        envelope=_envelope(mission_id),
    )

    assert backend.action_calls == 1
    assert result.status == "completed"
    assert result.before_after_evidence is not None
    assert result.action_receipt is not None
    assert result.action_receipt.verify_hash()
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_live_actions_are_skipped_by_default_and_sensitive_clipboard_raw_storage_blocked(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR))
    session = runtime.start_operator_session(
        mission_id=mission_id,
        backend_id=config.backend_id,
        policy=_operator_policy(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR),
        envelope=_envelope(mission_id),
    )

    sensitive = _command(config.backend_id, region_label="password_field", action_kind=DesktopActionKind.TYPE_TEXT)
    blocked_plan = runtime.plan_action(
        mission_id=mission_id,
        session_id=session.session_id,
        command=sensitive,
        envelope=_envelope(mission_id),
    )
    assert blocked_plan.blocked_reason == "sensitive_region_blocked"

    with pytest.raises(ValueError, match="desktop live action backend is opt-in"):
        LiveDesktopBackendConfig(
            backend_id="live_bad",
            sidecar_id="desktop_fake",
            kind=LiveDesktopBackendKind.LIVE_OPT_IN_ACTION_BACKEND,
            maturity=LiveDesktopBackendMaturity.LIVE_OPT_IN_ACTION_BACKEND,
            display_name="Unsafe live backend",
            explicit_live_opt_in=False,
        )
    with pytest.raises(ValueError):
        DesktopActionCommand(
            backend_id=config.backend_id,
            action_kind=DesktopActionKind.COPY_PASTE,
            app_ref="Code",
            window_ref="Sentinel",
            target_region_label="launch_button",
            clipboard_text="secret-token-1234567890",
            evidence_refs=["receipt_ref"],
        )

    persisted = _mission_text(runtime, mission_id)
    assert "secret-token-1234567890" not in persisted
    assert "raw_provider_response" not in persisted
    assert "raw_reasoning" not in persisted


@pytest.mark.parametrize("source", ["llm", "memory", "worker", "skill", "daemon", "scheduler", "channel_adapter"])
def test_non_operator_sources_cannot_direct_control_desktop(tmp_path: Path, source: str) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR))
    session = runtime.start_operator_session(
        mission_id=mission_id,
        backend_id=config.backend_id,
        policy=_operator_policy(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR),
        envelope=_envelope(mission_id),
    )

    with pytest.raises(LiveDesktopBackendRuntimeError, match="operator_control_source_required"):
        runtime.plan_action(
            mission_id=mission_id,
            session_id=session.session_id,
            command=_command(config.backend_id, requested_by=source),
            envelope=_envelope(mission_id),
        )


def test_benchmark_gauntlet_runs_on_fake_backend_and_replay_never_reacts(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR))

    run = runtime.run_benchmark_gauntlet(
        mission_id=mission_id,
        backend_id=config.backend_id,
        scenario=DesktopBenchmarkScenario.standard_fake_gauntlet(),
        envelope=_envelope(mission_id),
    )
    before_snapshot_calls = backend.system_snapshot_calls
    before_action_calls = backend.action_calls

    replay = LiveDesktopBackendReplayBuilder(runtime.store).build(mission_id)

    assert run.result is not None
    assert run.result.pass_rate == 1.0
    assert run.result.replay_no_reaction_verified is True
    assert replay.benchmark_runs
    assert replay.recollected_system_metrics is False
    assert replay.reexecuted_actions is False
    assert backend.system_snapshot_calls == before_snapshot_calls
    assert backend.action_calls == before_action_calls


def test_telemetry_records_live_desktop_events_and_metrics(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_backend(mission_id=mission_id, config=_backend_config(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR))
    session = runtime.start_operator_session(
        mission_id=mission_id,
        backend_id=config.backend_id,
        policy=_operator_policy(mode=DesktopControlMode.APPROVED_ACTION_OPERATOR, monitoring_enabled=True),
        envelope=_envelope(mission_id),
    )
    runtime.capture_system_snapshot(mission_id=mission_id, backend_id=config.backend_id, envelope=_envelope(mission_id))
    runtime.tick_monitoring_session(mission_id=mission_id, session_id=session.session_id, envelope=_envelope(mission_id))
    run = runtime.run_benchmark_gauntlet(
        mission_id=mission_id,
        backend_id=config.backend_id,
        scenario=DesktopBenchmarkScenario.standard_fake_gauntlet(),
        envelope=_envelope(mission_id),
    )

    snapshot = runtime.store.telemetry_sink.store.snapshot()
    assert snapshot.event_counts_by_kind[TelemetryEventKind.LIVE_DESKTOP_BACKEND_REGISTERED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_SYSTEM_SNAPSHOT_COMPLETED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_MONITORING_TICK_COMPLETED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_BENCHMARK_COMPLETED.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_SYSTEM_SNAPSHOT_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_MONITORING_TICK_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_BENCHMARK_PASS_RATE.value] >= 1
    assert run.result is not None


class FakeLiveBackend:
    def __init__(self) -> None:
        self.system_snapshot_calls = 0
        self.action_calls = 0

    def system_snapshot(self) -> dict[str, Any]:
        self.system_snapshot_calls += 1
        return {
            "platform_system": "Windows",
            "display_count": 2,
            "active_window_title": "Sentinel",
            "visible_windows": ["Sentinel", "Browser"],
            "running_apps": ["Code", "Browser"],
            "processes": [
                {"pid": 123, "name": "Code", "cpu_percent": 1.5, "memory_mb": 256},
                {"pid": 456, "name": "Browser", "cpu_percent": 3.0, "memory_mb": 512},
            ],
            "cpu_percent": 17.0,
            "ram_used_mb": 8192,
            "disk_used_percent": 50.0,
            "network_rx_kbps": 12.5,
            "battery_percent": None,
            "gpu_percent": None,
            "temperature_c": None,
            "fan_rpm": None,
        }

    def perform_action(self, command: DesktopActionCommand) -> dict[str, Any]:
        self.action_calls += 1
        return {
            "status": "completed",
            "before_hash": "b" * 64,
            "after_hash": "a" * 64,
            "safe_summary": f"Performed {command.action_kind.value} through fake live backend.",
        }


def _runtime(tmp_path: Path) -> tuple[LiveDesktopBackendRuntime, str, FakeLiveBackend]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_live_desktop",
        draft=MissionDraft(
            title="Use a live desktop backend foundation",
            objective="Monitor the local system and execute fake desktop operator actions under authority.",
            constraints=["no hidden capture", "no keylogger", "no credential harvesting"],
            expected_artifacts=["live desktop receipt", "live desktop replay"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="live_desktop_mission",
            allowed_actions=["desktop_observe", "desktop_monitor", "desktop_action", "desktop_benchmark"],
            forbidden_actions=["credential_unlock", "payment", "trading", "account_creation", "keylogging"],
            summary="Live desktop backend requires authority, policy, telemetry, receipts, FinalGate, and replay.",
        ),
    )
    backend = FakeLiveBackend()
    sidecar_runtime = DesktopSidecarRuntime(kernel)
    runtime = LiveDesktopBackendRuntime(
        kernel,
        sidecar_runtime=sidecar_runtime,
        registry=LiveDesktopBackendRegistry(backends={"live_fake": FakeInjectedLiveDesktopBackend(backend)}),
    )
    return runtime, record.mission_id, backend


def _backend_config(*, mode: DesktopControlMode = DesktopControlMode.MONITOR_ONLY) -> LiveDesktopBackendConfig:
    return LiveDesktopBackendConfig(
        backend_id="live_fake",
        sidecar_id="desktop_fake",
        kind=LiveDesktopBackendKind.INJECTED_TRANSPORT,
        maturity=LiveDesktopBackendMaturity.LOCAL_MONITORING_BACKEND,
        display_name="Injected live desktop backend",
        capability_profile=LiveDesktopBackendCapabilityProfile(
            supports_live_observation=True,
            supports_system_monitoring=True,
            supports_fake_actions=True,
            supports_live_opt_in_actions=False,
            supports_service_shape=True,
            supports_tray_shape=True,
        ),
        permission_policy=DesktopPermissionPolicy(
            active_mode=mode,
            allowed_modes=[
                DesktopControlMode.OBSERVE_ONLY,
                DesktopControlMode.MONITOR_ONLY,
                DesktopControlMode.ASSISTED_OPERATOR,
                DesktopControlMode.APPROVED_ACTION_OPERATOR,
                DesktopControlMode.DELEGATED_SESSION_OPERATOR,
                DesktopControlMode.CONTINUOUS_SUPERVISION_OPERATOR,
            ],
            allowed_apps=["Code", "Browser"],
            allowed_windows=["Sentinel", "Browser"],
            allowed_displays=["display:main"],
            always_on_allowed=True,
            production_always_on_ready=False,
            monitoring_policy=DesktopMonitoringPolicy(always_on_allowed=True, cadence_seconds=30),
        ),
        action_policy=DesktopActionPolicy(
            allowed_action_kinds=[
                DesktopActionKind.CLICK_REGION,
                DesktopActionKind.TYPE_TEXT,
                DesktopActionKind.HOTKEY,
                DesktopActionKind.WAIT,
            ],
            approval_required_for_each_action=True,
        ),
        permission_profile=DesktopPermissionProfile(
            monitoring_enabled=False,
            blocked_apps=["Password Manager"],
            retention_policy="hash_and_summary_only",
        ),
    )


def _operator_policy(
    *,
    mode: DesktopControlMode = DesktopControlMode.MONITOR_ONLY,
    monitoring_enabled: bool = False,
    always_on_allowed: bool = False,
) -> DesktopOperatorSessionPolicy:
    return DesktopOperatorSessionPolicy(
        control_mode=mode,
        monitoring_enabled=monitoring_enabled,
        always_on_allowed=always_on_allowed,
        allowed_apps=["Code", "Browser"],
        allowed_windows=["Sentinel", "Browser"],
        allowed_action_kinds=[DesktopActionKind.CLICK_REGION, DesktopActionKind.TYPE_TEXT, DesktopActionKind.HOTKEY, DesktopActionKind.WAIT],
    )


def _command(
    backend_id: str,
    *,
    action_kind: DesktopActionKind = DesktopActionKind.CLICK_REGION,
    requested_by: str = "operator",
    region_label: str = "launch_button",
) -> DesktopActionCommand:
    return DesktopActionCommand(
        backend_id=backend_id,
        action_kind=action_kind,
        app_ref="Code",
        window_ref="Sentinel",
        target_region_label=region_label,
        idempotency_key=DesktopActionIdempotencyKey.from_command("mission", backend_id, action_kind.value, region_label),
        requested_by=requested_by,
        text="hello" if action_kind is DesktopActionKind.TYPE_TEXT else None,
        hotkey="ctrl+l" if action_kind is DesktopActionKind.HOTKEY else None,
        evidence_refs=["desktop_receipt_ref"],
    )


def _envelope(mission_id: str, *, revoked: bool = False, expired: bool = False) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Live desktop backend mission",
        mission_objective="Monitor and operate the desktop through a governed live backend foundation.",
        allowed_tools=["desktop_sidecar", "live_desktop_backend", "desktop_fake", "live_fake"],
        allowed_actions=["desktop_observe", "desktop_monitor", "desktop_action", "desktop_benchmark"],
        forbidden_actions=["credential_unlock", "payment", "trading", "account_creation", "keylogging"],
        allowed_domains=[],
        max_actions=50,
        created_at=now - timedelta(minutes=10) if expired else now,
        expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        revoked_at=now if revoked else None,
    )


def _mission_text(runtime: LiveDesktopBackendRuntime, mission_id: str) -> str:
    root = runtime.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))
