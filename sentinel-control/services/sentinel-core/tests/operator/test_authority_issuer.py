from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.operator.authority_issuer import (
    MissionAuthorityEnvelopeIssuer,
    MissionAuthorityPolicy,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft


def test_issuer_creates_hash_bound_envelope_record_without_scope_expansion(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory", "read_file_segment"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    policy = MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "search_text"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=6,
        max_cost_usd=0.0,
    )

    issued = issuer.issue(record.mission_id, policy=policy)

    assert issued.envelope.id == record.mission_id
    assert issued.record.version == 1
    assert issued.record.previous_envelope_ref is None
    assert issued.record.mission_id == record.mission_id
    assert issued.record.authority_summary_hash
    assert issued.record.policy_hash
    assert issued.record.envelope_hash
    assert issued.record.verify_hash()
    assert set(issued.envelope.allowed_actions) == {"list_directory", "read_file_segment"}
    assert set(issued.envelope.allowed_actions).issubset(set(policy.allowed_actions))
    assert set(issued.envelope.forbidden_actions) == {"write_file", "shell"}
    assert issuer.resolve_active(record.mission_id).id == record.mission_id
    events = kernel.store.load_events(record.mission_id)
    assert [event.event_type for event in events][-1] == "mission_authority_envelope_issued"
    stored = issuer.load_record(record.mission_id, issued.record.envelope_id)
    assert stored.verify_hash()


def test_issuer_rejects_summary_action_outside_policy(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory", "shell"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    policy = MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory"],
        forbidden_actions=["shell"],
        allowed_paths=["."],
    )

    with pytest.raises(ValueError, match="authority_summary_action_outside_policy"):
        issuer.issue(record.mission_id, policy=policy)

    assert not (kernel.store.mission_dir(record.mission_id) / "authority" / "envelopes").exists()


def test_renewal_creates_new_lineage_record_and_revocation_is_immutable(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    policy = MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory"],
        allowed_paths=["."],
        max_duration_minutes=10,
    )
    issued_v1 = issuer.issue(record.mission_id, policy=policy)

    issued_v2 = issuer.renew(
        record.mission_id,
        previous_envelope_ref=issued_v1.record.envelope_id,
        policy=policy.model_copy(update={"max_duration_minutes": 20}),
    )
    revocation = issuer.revoke(
        record.mission_id,
        envelope_ref=issued_v2.record.envelope_id,
        reason="operator_requested_stop",
    )

    assert issued_v1.record.version == 1
    assert issued_v2.record.version == 2
    assert issued_v2.record.previous_envelope_ref == issued_v1.record.envelope_id
    assert issued_v2.envelope.resolved_expires_at() > issued_v1.envelope.resolved_expires_at()
    assert revocation.revoked_envelope_ref == issued_v2.record.envelope_id
    assert revocation.verify_hash()
    with pytest.raises(ValueError, match="mission_authority_envelope_revoked"):
        issuer.resolve_active(record.mission_id)
    reloaded_v1 = issuer.load_record(record.mission_id, issued_v1.record.envelope_id)
    reloaded_v2 = issuer.load_record(record.mission_id, issued_v2.record.envelope_id)
    assert reloaded_v1.revocation_ref is None
    assert reloaded_v2.revocation_ref is None


def _mission_record(
    kernel: MissionKernel,
    *,
    allowed_actions: list[str],
):
    draft = MissionDraft(
        title="Read-only repository inspection",
        objective="Inspect repository files without mutation.",
        expected_artifacts=["evidence-linked report"],
    )
    summary = MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=allowed_actions,
        forbidden_actions=["write_file", "shell"],
        summary="Read-only authority only.",
    )
    record = kernel.create_mission(session_id="session_authority", draft=draft, authority_summary=summary)
    summary = summary.model_copy(update={"mission_id": record.mission_id})
    return kernel.store.create_record(record.model_copy(update={"authority_summary": summary}))
