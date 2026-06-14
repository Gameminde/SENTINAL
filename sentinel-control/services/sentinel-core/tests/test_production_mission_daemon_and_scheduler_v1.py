from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.daemon_models import (
    DaemonLeaseOwner,
    DaemonQueueStatus,
    DeadLetterReason,
    MissionDaemonConfig,
    SchedulerDecisionKind,
)
from sentinel.operator.daemon_replay import DaemonReplayBuilder
from sentinel.operator.daemon_runtime import MissionDaemonRuntime, MissionDaemonRuntimeError
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.scheduler import ProactiveSchedulerRuntime, ProactiveTrigger
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
)
from sentinel.telemetry import TelemetryEventKind, TelemetryKernel


def test_daemon_requires_verified_telemetry_and_valid_lease_before_tick(tmp_path: Path) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry", enabled=False)
    kernel, mission_id = _kernel_with_mission(tmp_path, telemetry_sink=telemetry)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))

    assert daemon.certified_mode_snapshot().certified_mode is False
    with pytest.raises(MissionDaemonRuntimeError, match="daemon_certified_telemetry_required"):
        daemon.claim_lease(mission_id)

    healthy_kernel, healthy_mission_id = _kernel_with_mission(tmp_path / "healthy")
    healthy_daemon = MissionDaemonRuntime(healthy_kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    with pytest.raises(MissionDaemonRuntimeError, match="daemon_lease_required"):
        healthy_daemon.tick(healthy_mission_id, current_envelope=_envelope(healthy_mission_id))


def test_daemon_rejects_authority_envelope_for_another_mission(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id)
    daemon.claim_lease(mission_id)

    with pytest.raises(MissionDaemonRuntimeError, match="mission_authority_mismatch"):
        daemon.tick(mission_id, current_envelope=_envelope("another_mission"))

    assert daemon.store.load_queue_record(mission_id).status is DaemonQueueStatus.QUEUED


def test_daemon_rejects_tampered_mission_record_before_tick(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id)
    daemon.claim_lease(mission_id)
    record_path = kernel.store.run_root / mission_id / "record.json"
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["status"] = "completed"
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MissionDaemonRuntimeError, match="mission_record_tampered"):
        daemon.tick(mission_id, current_envelope=_envelope(mission_id))


def test_daemon_claims_renews_heartbeats_and_blocks_double_owner(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    owner_a = DaemonLeaseOwner(owner_id="daemon_a")
    owner_b = DaemonLeaseOwner(owner_id="daemon_b")
    daemon_a = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id=owner_a.owner_id, lease_ttl_seconds=30))
    daemon_b = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id=owner_b.owner_id, lease_ttl_seconds=30))

    lease = daemon_a.claim_lease(mission_id, now=_now())
    heartbeat = daemon_a.emit_heartbeat(mission_id, now=_now() + timedelta(seconds=5))
    renewed = daemon_a.renew_lease(mission_id, now=_now() + timedelta(seconds=10))

    assert lease.owner.owner_id == "daemon_a"
    assert heartbeat.lease_id == lease.lease_id
    assert renewed.expires_at > lease.expires_at
    with pytest.raises(MissionDaemonRuntimeError, match="daemon_lease_owned_by_another_daemon"):
        daemon_b.claim_lease(mission_id, now=_now() + timedelta(seconds=11))

    event_kinds = [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]
    assert "daemon_lease_claimed" in event_kinds
    assert "daemon_heartbeat_emitted" in event_kinds
    assert "daemon_lease_renewed" in event_kinds


def test_stale_lease_takeover_requires_expiry_proof(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon_a = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a", lease_ttl_seconds=10))
    daemon_b = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_b", lease_ttl_seconds=10))
    daemon_a.claim_lease(mission_id, now=_now())

    with pytest.raises(MissionDaemonRuntimeError, match="daemon_lease_owned_by_another_daemon"):
        daemon_b.claim_lease(mission_id, now=_now() + timedelta(seconds=9))

    takeover = daemon_b.claim_lease(mission_id, now=_now() + timedelta(seconds=11), allow_stale_takeover=True)

    assert takeover.owner.owner_id == "daemon_b"
    assert takeover.takeover_of_owner_id == "daemon_a"
    event_kinds = [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]
    assert "daemon_lease_expired" in event_kinds
    assert "daemon_lease_claimed" in event_kinds


def test_daemon_tick_respects_pause_kill_revocation_and_dead_letter(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id)
    lease = daemon.claim_lease(mission_id)
    tick_now = lease.claimed_at + timedelta(seconds=1)
    kernel.pause(mission_id)

    paused = daemon.tick(mission_id, current_envelope=_envelope(mission_id, now=tick_now), now=tick_now)
    assert paused.status is DaemonQueueStatus.PAUSED
    assert paused.executed is False

    kernel.resume(mission_id)
    revoked = _envelope(mission_id, now=tick_now).model_copy(update={"revoked_at": tick_now})
    blocked = daemon.tick(mission_id, current_envelope=revoked, now=tick_now)
    assert blocked.status is DaemonQueueStatus.DEAD_LETTER
    assert blocked.dead_letter_reason is DeadLetterReason.AUTHORITY_REVOKED

    replay = DaemonReplayBuilder(kernel.store).build(mission_id)
    assert replay.reexecuted_actions is False
    assert any(item.reason is DeadLetterReason.AUTHORITY_REVOKED for item in replay.dead_letters)


def test_daemon_ticks_existing_workflow_only_through_workflow_runtime(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    envelope = _envelope(mission_id)
    workflow_runtime = DurableMissionWorkflowRuntime(kernel)
    workflow = workflow_runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=_power_plan(mission_id),
        executor_contract_id="workspace-contract",
    )
    daemon = MissionDaemonRuntime(kernel, workflow_runtime=workflow_runtime, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id, workflow_id=workflow.workflow_id)
    lease = daemon.claim_lease(mission_id)
    tick_now = lease.claimed_at + timedelta(seconds=1)

    result = daemon.tick(mission_id, current_envelope=_envelope(mission_id, now=tick_now), workflow_id=workflow.workflow_id, now=tick_now)

    assert result.workflow_id == workflow.workflow_id
    assert result.used_direct_organ_path is False
    assert result.executed is True
    assert kernel.store.verify_timeline(mission_id) is True
    assert any(event.event_type == "daemon_tick_completed" for event in kernel.store.load_events(mission_id))


def test_scheduler_is_proposal_only_and_rejects_authority_execution_payloads(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    scheduler = ProactiveSchedulerRuntime(kernel)

    decision = scheduler.evaluate(
        ProactiveTrigger(
            mission_id=mission_id,
            trigger_type="scheduled_review",
            safe_reason="Review stalled mission progress.",
        )
    )

    assert decision.kind is SchedulerDecisionKind.PROPOSED
    assert decision.proposal is not None
    assert decision.proposal.can_execute is False
    assert decision.proposal.can_grant_authority is False

    rejected = scheduler.evaluate(
        ProactiveTrigger(
            mission_id=mission_id,
            trigger_type="unsafe_direct_execution",
            safe_reason="Run this directly.",
            metadata={"organ_call": {"kind": "browser", "action": "send"}},
        )
    )

    assert rejected.kind is SchedulerDecisionKind.REJECTED
    assert rejected.proposal is None
    assert "unsafe_scheduler_payload" in rejected.reasons
    assert any(event.event_type == "scheduler_proposal_rejected" for event in kernel.store.load_events(mission_id))


def test_daemon_replay_detects_tamper_without_reexecution(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id)
    daemon.claim_lease(mission_id)
    daemon.emit_heartbeat(mission_id)

    clean = DaemonReplayBuilder(kernel.store).build(mission_id)
    assert clean.tampered is False
    assert clean.reexecuted_actions is False
    assert clean.leases
    assert clean.heartbeats

    path = kernel.store.mission_dir(mission_id) / "events.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace("daemon_heartbeat_emitted", "daemon_heartbeat_changed", 1), encoding="utf-8")
    tampered = DaemonReplayBuilder(kernel.store).build(mission_id)
    assert tampered.tampered is True
    assert tampered.reexecuted_actions is False


def test_daemon_persistence_redacts_secrets_prompts_provider_responses_and_reasoning(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(
        mission_id,
        safe_reason="OPENAI_API_KEY=sk-test-1234567890",
        metadata={
            "raw_prompt": "Bearer raw-prompt-token",
            "provider_response": "session_token=raw-provider-token",
            "reasoning": "cookie: raw-cookie-token",
        },
    )
    daemon.claim_lease(mission_id)
    daemon.emit_heartbeat(mission_id, safe_summary="Bearer raw-heartbeat-token")

    payload = (kernel.store.mission_dir(mission_id) / "daemon").read_text(encoding="utf-8") if False else "\n".join(
        path.read_text(encoding="utf-8")
        for path in (kernel.store.mission_dir(mission_id) / "daemon").rglob("*.json")
    )
    payload += "\n" + "\n".join(event.safe_summary for event in kernel.store.load_events(mission_id))

    assert "sk-test-1234567890" not in payload
    assert "raw-prompt-token" not in payload
    assert "raw-provider-token" not in payload
    assert "raw-cookie-token" not in payload
    assert "raw-heartbeat-token" not in payload
    assert "[REDACTED_SECRET]" in payload


def test_daemon_status_surfaces_queue_lease_heartbeat_and_dead_letter(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    daemon = MissionDaemonRuntime(kernel, config=MissionDaemonConfig(owner_id="daemon_a"))
    daemon.enqueue(mission_id)
    lease = daemon.claim_lease(mission_id)
    heartbeat = daemon.emit_heartbeat(mission_id)
    daemon.dead_letter(mission_id, reason=DeadLetterReason.UNRECOVERABLE_WORKFLOW, safe_summary="Workflow cannot recover.")

    status = daemon.status_view()

    assert mission_id in [record.mission_id for record in status.queue]
    assert lease.lease_id in [record.lease_id for record in status.leases]
    assert heartbeat.heartbeat_id in [record.heartbeat_id for record in status.heartbeats]
    assert any(record.mission_id == mission_id for record in status.dead_letters)
    assert status.certified_mode.certified_mode is True


def _now() -> datetime:
    return datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def _kernel_with_mission(tmp_path: Path, *, telemetry_sink: TelemetryKernel | None = None) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path, telemetry_sink=telemetry_sink)
    record = kernel.create_mission(
        session_id="session_daemon",
        draft=MissionDraft(
            title="Daemon mission",
            objective="Run a production daemon lifecycle test.",
            constraints=["no payment", "no provider fallback"],
            expected_artifacts=["daemon status"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="draft_daemon",
            allowed_actions=["read", "write"],
            forbidden_actions=["payment", "credential_unlock"],
            summary="Daemon test only.",
        ),
    )
    return kernel, record.mission_id


def _envelope(mission_id: str, *, now: datetime | None = None) -> MissionAuthorityEnvelope:
    now = now or _now()
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_daemon",
        mission_title="Daemon mission",
        mission_objective="Run a production daemon lifecycle test.",
        allowed_systems=["workspace"],
        allowed_tools=["workspace"],
        allowed_actions=["read", "write"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=60,
        max_actions=10,
        max_cost_usd=1.0,
        max_recipients=0,
        created_at=now,
        expires_at=now + timedelta(minutes=60),
    )


def _power_plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="daemon_workspace_read",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="workspace",
                    action_kind="read",
                    request={"path": "data/generated_projects/daemon.txt"},
                    estimated_cost_usd=0.0,
                    safe_summary="Daemon reads an authorized workspace artifact.",
                )
            ]
        ),
    )
