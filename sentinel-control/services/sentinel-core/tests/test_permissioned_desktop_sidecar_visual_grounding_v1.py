from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.desktop_sidecar import DesktopSidecarRuntime, DesktopSidecarRuntimeError
from sentinel.operator.desktop_sidecar_models import (
    DesktopActionApproval,
    DesktopActionKind,
    DesktopActionPolicy,
    DesktopActionRequest,
    DesktopCapabilityProfile,
    DesktopControlMode,
    DesktopMonitoringPolicy,
    DesktopObservationRequest,
    DesktopPermissionPolicy,
    DesktopRegionRef,
    DesktopSidecarConfig,
    DesktopSidecarKind,
    DesktopSidecarMaturity,
    DesktopVisualGroundingRequest,
    MetricAvailability,
)
from sentinel.operator.desktop_sidecar_replay import DesktopSidecarReplayBuilder
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_sidecar_registration_models_future_full_user_delegated_modes(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)

    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())

    assert config.maturity is DesktopSidecarMaturity.INJECTED_TRANSPORT
    assert config.capability_profile.supports_observation is True
    assert config.capability_profile.supports_monitoring is True
    assert config.capability_profile.supports_visual_grounding is True
    assert config.capability_profile.supports_action_preview is True
    assert config.capability_profile.supports_injected_actions is True
    assert DesktopControlMode.OBSERVE_ONLY in config.permission_policy.allowed_modes
    assert DesktopControlMode.MONITOR_ONLY in config.permission_policy.allowed_modes
    assert DesktopControlMode.DELEGATED_SESSION_OPERATOR in config.permission_policy.allowed_modes
    assert DesktopControlMode.CONTINUOUS_SUPERVISION_OPERATOR in config.permission_policy.allowed_modes
    assert config.permission_policy.always_on_allowed is True
    assert config.permission_policy.production_always_on_ready is False
    assert runtime.store.verify_timeline(mission_id)


def test_observation_requires_permission_policy_and_blocks_hidden_ambient_loop(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)

    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_sidecar_not_registered"):
        runtime.observe_desktop(
            mission_id=mission_id,
            request=_observation_request(),
            envelope=_envelope(mission_id),
        )

    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_hidden_or_ambient_capture_blocked"):
        runtime.observe_desktop(
            mission_id=mission_id,
            request=_observation_request(ambient_loop=True, operator_visible=False),
            envelope=_envelope(mission_id),
        )

    result = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )

    assert backend.observe_calls == 1
    assert result.status == "observed"
    assert result.screenshot_ref is not None
    assert result.screenshot_ref.screenshot_hash
    assert result.screenshot_ref.raw_screenshot_persisted is False
    assert result.receipt is not None
    assert result.receipt.verify_hash()
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.decision == "observed"


def test_observation_blocks_revocation_kill_blocked_app_and_raw_screenshot_persistence(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config(blocked_apps=["Password Manager"]))

    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_authority_revoked"):
        runtime.observe_desktop(
            mission_id=mission_id,
            request=_observation_request(sidecar_id=config.sidecar_id),
            envelope=_envelope(mission_id, revoked=True),
        )
    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_observation_blocked_app"):
        runtime.observe_desktop(
            mission_id=mission_id,
            request=_observation_request(sidecar_id=config.sidecar_id, app_ref="Password Manager"),
            envelope=_envelope(mission_id),
        )

    result = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )
    persisted = _mission_text(runtime, mission_id)

    assert backend.observe_calls == 1
    assert result.screenshot_ref is not None
    assert result.screenshot_ref.raw_screenshot_persisted is False
    assert "sensitive-fixture-marker-1234567890" not in persisted
    assert "raw_screenshot_bytes" not in persisted


def test_monitoring_snapshot_supports_system_app_window_process_and_unknown_metrics(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())

    snapshot = runtime.capture_monitoring_snapshot(
        mission_id=mission_id,
        sidecar_id=config.sidecar_id,
        envelope=_envelope(mission_id),
    )

    assert backend.monitor_calls == 1
    assert snapshot.system_snapshot.platform_system
    assert snapshot.system_snapshot.display_count >= 1
    assert snapshot.system_snapshot.current_session_ref_hash
    assert snapshot.processes
    assert snapshot.windows
    assert snapshot.apps
    assert snapshot.hardware_metrics.cpu_percent.status is MetricAvailability.AVAILABLE
    assert snapshot.hardware_metrics.gpu_percent.status in {MetricAvailability.UNKNOWN, MetricAvailability.UNSUPPORTED}
    assert snapshot.sensor_snapshot.temperature_c.status in {MetricAvailability.UNKNOWN, MetricAvailability.UNSUPPORTED}
    assert snapshot.clock_snapshot.system_time_hash
    assert snapshot.monitoring_receipt is not None
    assert snapshot.monitoring_receipt.verify_hash()


def test_visual_grounding_returns_evidence_linked_candidates_and_ambiguity_blocks(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    observation = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )

    grounded = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=config.sidecar_id,
            observation_id=observation.observation_id,
            target_description="Launch button",
            evidence_refs=[observation.receipt.receipt_id],
        ),
    )

    assert grounded.status == "grounded"
    assert grounded.target_candidates
    assert grounded.target_candidates[0].evidence_refs == [observation.receipt.receipt_id]
    assert grounded.target_candidates[0].confidence_score >= 0.8
    assert grounded.action_executed is False

    ambiguous = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=config.sidecar_id,
            observation_id=observation.observation_id,
            target_description="ambiguous duplicated icon",
            evidence_refs=[observation.receipt.receipt_id],
            ambiguity_threshold=0.95,
        ),
    )
    assert ambiguous.status == "needs_operator_checkpoint"
    assert ambiguous.action_executed is False


def test_action_preview_proposal_and_injected_action_require_authority_allowlist_and_approval(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    observation = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )
    grounded = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=config.sidecar_id,
            observation_id=observation.observation_id,
            target_description="Launch button",
            evidence_refs=[observation.receipt.receipt_id],
        ),
    )

    preview = runtime.preview_action(
        mission_id=mission_id,
        request=DesktopActionRequest(
            sidecar_id=config.sidecar_id,
            action_kind=DesktopActionKind.CLICK_REGION,
            target_candidate_id=grounded.target_candidates[0].target_id,
            app_ref="Code",
            window_ref="Sentinel",
            evidence_refs=[grounded.grounding_receipt.receipt_id],
        ),
    )
    assert backend.action_calls == 0
    assert preview.action_proposal is not None
    assert preview.action_proposal.can_execute is False

    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_action_authority_missing"):
        runtime.execute_action(mission_id=mission_id, request=preview.action_request, envelope=None)

    with pytest.raises(DesktopSidecarRuntimeError, match="operator_approval_required"):
        runtime.execute_action(mission_id=mission_id, request=preview.action_request, envelope=_envelope(mission_id))

    approval = runtime.approve_action(
        mission_id=mission_id,
        approval=DesktopActionApproval(
            sidecar_id=config.sidecar_id,
            preview_id=preview.preview_id,
            approved_by="operator_youcef",
            approval_source="operator",
        ),
    )
    result = runtime.execute_action(
        mission_id=mission_id,
        request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
        envelope=_envelope(mission_id),
    )

    assert backend.action_calls == 1
    assert result.status == "completed"
    assert result.before_after_evidence is not None
    assert result.before_after_evidence.before_hash
    assert result.before_after_evidence.after_hash
    assert result.receipt is not None
    assert result.receipt.verify_hash()
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.decision == "observed"


def test_delegated_session_mode_allows_scoped_multi_action_without_each_step_approval(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(
        mission_id=mission_id,
        config=_sidecar_config(
            mode=DesktopControlMode.DELEGATED_SESSION_OPERATOR,
            action_policy=DesktopActionPolicy(approval_required_for_each_action=False),
        ),
    )
    observation = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )
    grounded = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=config.sidecar_id,
            observation_id=observation.observation_id,
            target_description="Launch button",
            evidence_refs=[observation.receipt.receipt_id],
        ),
    )
    preview = runtime.preview_action(
        mission_id=mission_id,
        request=DesktopActionRequest(
            sidecar_id=config.sidecar_id,
            action_kind=DesktopActionKind.WAIT,
            target_candidate_id=grounded.target_candidates[0].target_id,
            app_ref="Code",
            window_ref="Sentinel",
            evidence_refs=[grounded.grounding_receipt.receipt_id],
        ),
    )

    result = runtime.execute_action(mission_id=mission_id, request=preview.action_request, envelope=_envelope(mission_id))

    assert backend.action_calls == 1
    assert result.status == "completed"
    assert result.action_kind is DesktopActionKind.WAIT


@pytest.mark.parametrize("approval_source", ["llm", "memory", "worker", "skill", "daemon", "scheduler", "channel_adapter"])
def test_non_operator_sources_cannot_approve_or_direct_control_desktop(tmp_path: Path, approval_source: str) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())

    with pytest.raises(ValueError, match="operator approval source required"):
        DesktopActionApproval(
            sidecar_id=config.sidecar_id,
            preview_id="desktop_preview_bad",
            approval_source=approval_source,
            approved_by=approval_source,
        )


def test_sensitive_region_blocks_live_action_and_requires_checkpoint(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    observation = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(
            sidecar_id=config.sidecar_id,
            regions=[DesktopRegionRef(label="password_field", x=10, y=10, width=200, height=20, sensitive=True)],
        ),
        envelope=_envelope(mission_id),
    )
    grounded = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=config.sidecar_id,
            observation_id=observation.observation_id,
            target_description="password field",
            evidence_refs=[observation.receipt.receipt_id],
        ),
    )
    preview = runtime.preview_action(
        mission_id=mission_id,
        request=DesktopActionRequest(
            sidecar_id=config.sidecar_id,
            action_kind=DesktopActionKind.TYPE_TEXT,
            target_candidate_id=grounded.target_candidates[0].target_id,
            app_ref="Code",
            window_ref="Sentinel",
            text="hello",
            evidence_refs=[grounded.grounding_receipt.receipt_id],
        ),
    )
    approval = runtime.approve_action(
        mission_id=mission_id,
        approval=DesktopActionApproval(sidecar_id=config.sidecar_id, preview_id=preview.preview_id),
    )

    result = runtime.execute_action(
        mission_id=mission_id,
        request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
        envelope=_envelope(mission_id),
    )

    assert backend.action_calls == 0
    assert result.status == "blocked"
    assert result.blocked_reason == "sensitive_region_blocked"
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.decision == "sensitive_region_blocked"


def test_action_blocks_after_kill_revocation_or_disallowed_app(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    preview = _preview(runtime, mission_id, config.sidecar_id)
    approval = runtime.approve_action(
        mission_id=mission_id,
        approval=DesktopActionApproval(sidecar_id=config.sidecar_id, preview_id=preview.preview_id),
    )

    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_authority_revoked"):
        runtime.execute_action(
            mission_id=mission_id,
            request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
            envelope=_envelope(mission_id, revoked=True),
        )

    runtime.kill_sidecar(mission_id=mission_id, sidecar_id=config.sidecar_id, reason="operator kill")
    with pytest.raises(DesktopSidecarRuntimeError, match="desktop_sidecar_killed"):
        runtime.execute_action(
            mission_id=mission_id,
            request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
            envelope=_envelope(mission_id),
        )
    assert backend.action_calls == 0


def test_replay_reconstructs_without_new_screenshot_or_action(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    preview = _preview(runtime, mission_id, config.sidecar_id)
    approval = runtime.approve_action(
        mission_id=mission_id,
        approval=DesktopActionApproval(sidecar_id=config.sidecar_id, preview_id=preview.preview_id),
    )
    runtime.execute_action(
        mission_id=mission_id,
        request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
        envelope=_envelope(mission_id),
    )
    before_observe = backend.observe_calls
    before_action = backend.action_calls

    replay = DesktopSidecarReplayBuilder(runtime.store).build(mission_id)

    assert replay.observations
    assert replay.grounding_results
    assert replay.action_results
    assert replay.receipts
    assert replay.finalgate_refs
    assert replay.recaptured_screenshots is False
    assert replay.reexecuted_actions is False
    assert backend.observe_calls == before_observe
    assert backend.action_calls == before_action
    assert replay.tampered is False


def test_telemetry_records_desktop_events_and_metrics(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_sidecar(mission_id=mission_id, config=_sidecar_config())
    preview = _preview(runtime, mission_id, config.sidecar_id)
    approval = runtime.approve_action(
        mission_id=mission_id,
        approval=DesktopActionApproval(sidecar_id=config.sidecar_id, preview_id=preview.preview_id),
    )
    runtime.execute_action(
        mission_id=mission_id,
        request=preview.action_request.model_copy(update={"approval_id": approval.approval_id}),
        envelope=_envelope(mission_id),
    )

    snapshot = runtime.store.telemetry_sink.store.snapshot()
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_SIDECAR_REGISTERED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_OBSERVATION_COMPLETED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_GROUNDING_COMPLETED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.DESKTOP_ACTION_COMPLETED.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_OBSERVATION_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_ACTION_SUCCESS_RATE.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.DESKTOP_RECEIPT_COMPLETENESS.value] >= 1


def test_raw_secret_prompt_provider_response_reasoning_and_control_payload_persistence_blocked(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_sidecar(
        mission_id=mission_id,
        config=_sidecar_config(metadata={"raw_prompt_hash": "ok", "provider_response_hash": "hash-only"}),
    )
    runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=config.sidecar_id),
        envelope=_envelope(mission_id),
    )
    persisted = _mission_text(runtime, mission_id)
    forbidden = [
        "secret-value-1234567890",
        "raw_screenshot_bytes",
        "raw_ocr_text",
        '"raw_prompt"',
        "raw_provider_response",
        "raw_reasoning",
        "credential_value",
        "api_key",
    ]
    assert all(item not in persisted for item in forbidden)

    with pytest.raises(ValueError):
        DesktopSidecarConfig(
            sidecar_id="desktop_bad",
            kind=DesktopSidecarKind.INJECTED_TRANSPORT,
            maturity=DesktopSidecarMaturity.INJECTED_TRANSPORT,
            display_name="Bad",
            metadata={"raw_token": "secret-value-1234567890"},
        )


class FakeDesktopBackend:
    def __init__(self) -> None:
        self.observe_calls = 0
        self.monitor_calls = 0
        self.action_calls = 0

    def observe(self, request: DesktopObservationRequest) -> dict[str, Any]:
        self.observe_calls += 1
        return {
            "screenshot_bytes": b"fake-desktop-png sensitive-fixture-marker-1234567890",
            "display_ref": "display:main",
            "window_ref": request.window_ref,
            "app_ref": request.app_ref,
            "regions": [region.safe_model_dump() for region in request.regions],
            "safe_text_snippets": ["Launch button", "Status ready"],
        }

    def monitor(self) -> dict[str, Any]:
        self.monitor_calls += 1
        return {
            "platform_system": "Windows",
            "display_count": 2,
            "active_window_title": "Sentinel",
            "visible_windows": ["Sentinel", "Browser"],
            "running_apps": ["Code", "Browser"],
            "processes": [{"pid": 123, "name": "Code", "cpu_percent": 1.5, "memory_mb": 256}],
            "cpu_percent": 17.0,
            "ram_used_mb": 8192,
            "disk_used_percent": 50.0,
            "network_rx_kbps": 12.5,
            "battery_percent": None,
            "gpu_percent": None,
            "temperature_c": None,
        }

    def perform_action(self, request: DesktopActionRequest) -> dict[str, Any]:
        self.action_calls += 1
        return {
            "status": "completed",
            "before_hash": "b" * 64,
            "after_hash": "a" * 64,
            "safe_summary": f"Performed {request.action_kind.value}",
        }


def _runtime(tmp_path: Path) -> tuple[DesktopSidecarRuntime, str, FakeDesktopBackend]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_desktop",
        draft=MissionDraft(
            title="Use a permissioned desktop sidecar",
            objective="Observe, ground, preview, and execute guarded desktop sidecar actions.",
            constraints=["no hidden capture", "no ambient host authority", "no credential harvesting"],
            expected_artifacts=["desktop receipt", "desktop replay"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="desktop_mission",
            allowed_actions=["desktop_observe", "desktop_monitor", "desktop_ground", "desktop_preview", "desktop_action"],
            forbidden_actions=["credential_unlock", "payment", "trading", "account_creation", "keylogging"],
            summary="Desktop actions require explicit mission authority, policy, approval, telemetry, receipts, and FinalGate.",
        ),
    )
    backend = FakeDesktopBackend()
    runtime = DesktopSidecarRuntime(kernel, backends={"desktop_fake": backend})
    return runtime, record.mission_id, backend


def _sidecar_config(
    *,
    blocked_apps: list[str] | None = None,
    mode: DesktopControlMode = DesktopControlMode.APPROVED_ACTION_OPERATOR,
    action_policy: DesktopActionPolicy | None = None,
    metadata: dict[str, Any] | None = None,
) -> DesktopSidecarConfig:
    return DesktopSidecarConfig(
        sidecar_id="desktop_fake",
        kind=DesktopSidecarKind.INJECTED_TRANSPORT,
        maturity=DesktopSidecarMaturity.INJECTED_TRANSPORT,
        display_name="Injected desktop sidecar",
        capability_profile=DesktopCapabilityProfile(
            supports_observation=True,
            supports_monitoring=True,
            supports_visual_grounding=True,
            supports_action_preview=True,
            supports_injected_actions=True,
            supports_live_opt_in_actions=False,
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
            blocked_apps=blocked_apps or [],
            allowed_windows=["Sentinel", "Browser"],
            allowed_displays=["display:main"],
            persist_full_screenshot_allowed=False,
            persist_full_ocr_text_allowed=False,
            always_on_allowed=True,
            production_always_on_ready=False,
            monitoring_policy=DesktopMonitoringPolicy(
                always_on_allowed=True,
                cadence_seconds=30,
                allowed_metrics=["cpu", "ram", "disk", "network", "gpu", "temperature", "battery", "clock", "process", "window"],
                retention_policy="hash_and_summary_only",
            ),
        ),
        action_policy=action_policy or DesktopActionPolicy(
            allowed_action_kinds=[DesktopActionKind.CLICK_REGION, DesktopActionKind.TYPE_TEXT, DesktopActionKind.WAIT],
            approval_required_for_each_action=True,
        ),
        metadata=metadata or {},
    )


def _observation_request(
    *,
    sidecar_id: str = "desktop_fake",
    app_ref: str = "Code",
    window_ref: str = "Sentinel",
    ambient_loop: bool = False,
    operator_visible: bool = True,
    regions: list[DesktopRegionRef] | None = None,
) -> DesktopObservationRequest:
    return DesktopObservationRequest(
        sidecar_id=sidecar_id,
        app_ref=app_ref,
        window_ref=window_ref,
        display_ref="display:main",
        regions=regions or [DesktopRegionRef(label="launch_button", x=100, y=120, width=80, height=24)],
        purpose="ground target",
        operator_visible=operator_visible,
        ambient_loop=ambient_loop,
    )


def _preview(runtime: DesktopSidecarRuntime, mission_id: str, sidecar_id: str):
    observation = runtime.observe_desktop(
        mission_id=mission_id,
        request=_observation_request(sidecar_id=sidecar_id),
        envelope=_envelope(mission_id),
    )
    grounded = runtime.ground_visual_target(
        mission_id=mission_id,
        request=DesktopVisualGroundingRequest(
            sidecar_id=sidecar_id,
            observation_id=observation.observation_id,
            target_description="Launch button",
            evidence_refs=[observation.receipt.receipt_id],
        ),
    )
    return runtime.preview_action(
        mission_id=mission_id,
        request=DesktopActionRequest(
            sidecar_id=sidecar_id,
            action_kind=DesktopActionKind.CLICK_REGION,
            target_candidate_id=grounded.target_candidates[0].target_id,
            app_ref="Code",
            window_ref="Sentinel",
            evidence_refs=[grounded.grounding_receipt.receipt_id],
        ),
    )


def _envelope(mission_id: str, *, revoked: bool = False, expired: bool = False) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Desktop sidecar mission",
        mission_objective="Use a permissioned desktop sidecar with visual grounding.",
        allowed_tools=["desktop_sidecar", "desktop_fake"],
        allowed_actions=["desktop_observe", "desktop_monitor", "desktop_ground", "desktop_preview", "desktop_action"],
        forbidden_actions=["credential_unlock", "payment", "trading", "account_creation", "keylogging"],
        allowed_domains=[],
        max_actions=20,
        created_at=now - timedelta(minutes=10) if expired else now,
        expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        revoked_at=now if revoked else None,
    )


def _mission_text(runtime: DesktopSidecarRuntime, mission_id: str) -> str:
    root = runtime.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))
