from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.operator.authority_issuer import (
    MissionAuthorityApprovalScope,
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

    issued = issuer.issue(record.mission_id, approval_scope=_approval_scope(), policy=policy)

    assert issued.envelope.id == record.mission_id
    assert issued.record.version == 1
    assert issued.record.previous_envelope_ref is None
    assert issued.record.mission_id == record.mission_id
    assert issued.record.authority_summary_hash
    assert issued.record.policy_hash
    assert issued.record.authority_approval_scope_hash
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
    record = _mission_record(kernel, allowed_actions=["list_directory", "export_report"])
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
        issuer.issue(
            record.mission_id,
            approval_scope=_approval_scope(allowed_actions=["list_directory", "export_report"]),
            policy=policy,
        )

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
    issued_v1 = issuer.issue(record.mission_id, approval_scope=_approval_scope(), policy=policy)

    issued_v2 = issuer.renew(
        record.mission_id,
        previous_envelope_ref=issued_v1.record.envelope_id,
        expected_current_envelope_ref=issued_v1.record.envelope_id,
        approval_scope=_approval_scope(max_duration_minutes=20),
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


def test_authority_scope_intersects_policy_and_never_broadens_from_policy(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory", "read_file_segment"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    approval_scope = _approval_scope(
        allowed_systems=["local_workspace", "browser"],
        allowed_tools=["read_only_observation", "browser_readonly"],
        allowed_actions=["list_directory", "read_file_segment"],
        forbidden_actions=["write_file"],
        allowed_paths=[".", "docs"],
        allowed_domains=["example.com", "sentinel.local"],
        max_duration_minutes=20,
        max_actions=9,
        max_cost_usd=5.0,
        browser_v3_authority_grants=[{"id": "browser-grant-1", "authority_class": "observe"}],
    )
    policy = MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace", "external_saas"],
        allowed_tools=["read_only_observation", "browser_readonly"],
        allowed_actions=["list_directory", "read_file_segment", "export_report"],
        forbidden_actions=["archive_report"],
        allowed_paths=[".", "secrets"],
        allowed_domains=["example.com", "unapproved.example"],
        allowed_accounts=["policy_account"],
        allowed_data_types=["public_repo"],
        max_duration_minutes=15,
        max_actions=4,
        max_cost_usd=1.0,
        browser_v3_authority_grants=[{"id": "browser-grant-1", "authority_class": "observe"}],
        credential_grants=[{"id": "credential-grant-policy", "authority_class": "metadata_only"}],
    )

    issued = issuer.issue(record.mission_id, approval_scope=approval_scope, policy=policy)

    assert issued.envelope.allowed_systems == ["local_workspace"]
    assert issued.envelope.allowed_tools == ["read_only_observation", "browser_readonly"]
    assert issued.envelope.allowed_actions == ["list_directory", "read_file_segment"]
    assert issued.envelope.forbidden_actions == ["write_file", "shell", "archive_report"]
    assert issued.envelope.allowed_paths == ["."]
    assert issued.envelope.allowed_domains == ["example.com"]
    assert issued.envelope.allowed_accounts == []
    assert issued.envelope.allowed_data_types == []
    assert issued.envelope.max_duration_minutes == 15
    assert issued.envelope.max_actions == 4
    assert issued.envelope.max_cost_usd == 1.0
    assert issued.envelope.browser_v3_authority_grants == [{"id": "browser-grant-1", "authority_class": "observe"}]
    assert issued.envelope.credential_grants == []
    assert issued.record.authority_approval_scope_hash == approval_scope.approval_scope_hash


def test_authority_artifact_persistence_failure_does_not_emit_issued_event(tmp_path: Path) -> None:
    class _FailingPersistIssuer(MissionAuthorityEnvelopeIssuer):
        def _persist_record(self, record):  # noqa: ANN001
            raise OSError("synthetic authority artifact persistence failure")

    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory"])
    issuer = _FailingPersistIssuer(kernel)

    with pytest.raises(OSError, match="synthetic authority artifact persistence failure"):
        issuer.issue(record.mission_id, approval_scope=_approval_scope(), policy=_policy())

    event_types = [event.event_type for event in kernel.store.load_events(record.mission_id)]
    assert "mission_authority_envelope_issued" not in event_types
    assert issuer.list_records(record.mission_id) == []


def test_loaded_authority_record_hash_is_verified(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    issued = issuer.issue(record.mission_id, approval_scope=_approval_scope(), policy=_policy())
    envelope_path = (
        kernel.store.mission_dir(record.mission_id)
        / "authority"
        / "envelopes"
        / f"{issued.record.envelope_id}.json"
    )
    payload = json.loads(envelope_path.read_text(encoding="utf-8"))
    payload["policy_hash"] = "tampered_policy_hash"
    envelope_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="mission authority envelope record hash mismatch"):
        issuer.load_record(record.mission_id, issued.record.envelope_id)


def test_renewal_rejects_stale_revoked_or_expired_lineage(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = _mission_record(kernel, allowed_actions=["list_directory"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    issued_v1 = issuer.issue(record.mission_id, approval_scope=_approval_scope(), policy=_policy(max_duration_minutes=10))
    issued_v2 = issuer.renew(
        record.mission_id,
        previous_envelope_ref=issued_v1.record.envelope_id,
        expected_current_envelope_ref=issued_v1.record.envelope_id,
        approval_scope=_approval_scope(max_duration_minutes=10),
        policy=_policy(max_duration_minutes=10),
    )

    with pytest.raises(ValueError, match="mission_authority_envelope_conflict"):
        issuer.renew(
            record.mission_id,
            previous_envelope_ref=issued_v1.record.envelope_id,
            expected_current_envelope_ref=issued_v1.record.envelope_id,
            approval_scope=_approval_scope(max_duration_minutes=10),
            policy=_policy(max_duration_minutes=10),
        )

    issuer.revoke(record.mission_id, envelope_ref=issued_v2.record.envelope_id, reason="operator_stop")
    with pytest.raises(ValueError, match="mission_authority_envelope_revoked"):
        issuer.renew(
            record.mission_id,
            previous_envelope_ref=issued_v2.record.envelope_id,
            expected_current_envelope_ref=issued_v2.record.envelope_id,
            approval_scope=_approval_scope(max_duration_minutes=10),
            policy=_policy(max_duration_minutes=10),
        )

    expired_record = _mission_record(kernel, allowed_actions=["list_directory"])
    expired = issuer.issue(expired_record.mission_id, approval_scope=_approval_scope(), policy=_policy(max_duration_minutes=1))
    expired_payload = expired.record.model_copy(
        update={
            "issued_at": datetime(2020, 1, 1, tzinfo=UTC),
            "expires_at": datetime(2020, 1, 1, 0, 1, tzinfo=UTC),
        }
    ).with_hash()
    issuer._persist_record(expired_payload)
    with pytest.raises(ValueError, match="mission_authority_envelope_expired"):
        issuer.renew(
            expired_record.mission_id,
            previous_envelope_ref=expired.record.envelope_id,
            expected_current_envelope_ref=expired.record.envelope_id,
            approval_scope=_approval_scope(max_duration_minutes=1),
            policy=_policy(max_duration_minutes=1),
        )


def test_cross_mission_envelope_reference_is_rejected(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record_a = _mission_record(kernel, allowed_actions=["list_directory"])
    record_b = _mission_record(kernel, allowed_actions=["list_directory"])
    issuer = MissionAuthorityEnvelopeIssuer(kernel)
    issued_b = issuer.issue(record_b.mission_id, approval_scope=_approval_scope(), policy=_policy())

    with pytest.raises(ValueError):
        issuer.revoke(record_a.mission_id, envelope_ref=issued_b.record.envelope_id, reason="wrong_mission")


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


def _approval_scope(
    *,
    allowed_systems: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
    forbidden_actions: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    allowed_domains: list[str] | None = None,
    allowed_accounts: list[str] | None = None,
    allowed_data_types: list[str] | None = None,
    max_duration_minutes: int = 10,
    max_actions: int = 6,
    max_cost_usd: float = 0.0,
    browser_v3_authority_grants: list[dict[str, str]] | None = None,
) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=allowed_systems or ["local_workspace"],
        allowed_tools=allowed_tools or ["read_only_observation"],
        allowed_actions=allowed_actions or ["list_directory", "read_file_segment"],
        forbidden_actions=forbidden_actions or ["write_file", "shell"],
        allowed_paths=allowed_paths or ["."],
        allowed_domains=allowed_domains or [],
        allowed_accounts=allowed_accounts or [],
        allowed_data_types=allowed_data_types or [],
        max_duration_minutes=max_duration_minutes,
        max_actions=max_actions,
        max_cost_usd=max_cost_usd,
        browser_v3_authority_grants=browser_v3_authority_grants or [],
    )


def _policy(*, max_duration_minutes: int = 10) -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=max_duration_minutes,
        max_actions=6,
        max_cost_usd=0.0,
    )
