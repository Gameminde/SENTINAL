from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.credential_vault import CredentialVaultRuntime, CredentialVaultRuntimeError
from sentinel.operator.credential_vault_models import (
    CredentialConsumerKind,
    CredentialScopePolicy,
    CredentialUseRiskProfile,
    CredentialVaultConfig,
    CredentialVaultMaturity,
    SecretFinalGateDecision,
    SecretKind,
    SecretSensitivity,
    SecretUseContext,
    SecretUsePolicy,
    VaultLockState,
    VaultUnlockPolicy,
)
from sentinel.operator.credential_vault_replay import CredentialVaultReplayBuilder
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_vault_initialization_and_lock_unlock_lifecycle(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)

    config = runtime.initialize_vault(mission_id=mission_id, config=_vault_config())
    requested = runtime.request_unlock(
        mission_id=mission_id,
        policy=VaultUnlockPolicy(ttl_seconds=60, allowed_purposes=["external_api_read"]),
        purpose="external_api_read",
        requested_by="operator",
    )
    unlocked = runtime.approve_unlock_session(
        mission_id=mission_id,
        unlock_session_id=requested.unlock_session_id,
        approval_source="operator",
    )
    expired = runtime.expire_unlock_session(
        mission_id=mission_id,
        unlock_session_id=unlocked.unlock_session_id,
        at_time=unlocked.expires_at + timedelta(seconds=1),
    )

    assert config.maturity is CredentialVaultMaturity.FAKE_SEALED_STORE
    assert requested.state is VaultLockState.UNLOCK_REQUESTED
    assert unlocked.state is VaultLockState.UNLOCKED_FOR_SESSION
    assert unlocked.unlock_session_is_authority is False
    assert expired.state is VaultLockState.EXPIRED
    assert runtime.store.verify_timeline(mission_id)


def test_secret_registration_metadata_and_fake_sealed_store_blocks_plaintext(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    runtime.initialize_vault(mission_id=mission_id, config=_vault_config())
    secret_material = _fake_secret()

    metadata = runtime.register_secret(
        mission_id=mission_id,
        kind=SecretKind.API_KEY,
        label="Read only market data API",
        scope_policy=_scope_policy(),
        use_policy=_use_policy(),
        sensitivity=SecretSensitivity.HIGH,
        provenance="operator_supplied_test_fixture",
        secret_material=secret_material,
    )

    assert metadata.kind is SecretKind.API_KEY
    assert metadata.material_envelope.storage_maturity is CredentialVaultMaturity.FAKE_SEALED_STORE
    assert metadata.material_envelope.raw_secret_persisted is False
    assert metadata.secret_ref.redacted_label.startswith("secret_ref:")
    assert metadata.secret_handle.can_grant_authority is False
    persisted = _mission_text(runtime, mission_id)
    assert secret_material not in persisted
    assert "plaintext" not in persisted.lower()
    assert "raw_secret" not in persisted


def test_secret_models_reject_raw_secret_persistence_fields(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    runtime.initialize_vault(mission_id=mission_id, config=_vault_config())

    with pytest.raises(ValueError, match="raw secret"):
        runtime.register_secret(
            mission_id=mission_id,
            kind=SecretKind.API_KEY,
            label="bad",
            scope_policy=_scope_policy(),
            use_policy=_use_policy(),
            sensitivity=SecretSensitivity.HIGH,
            provenance="operator",
            metadata={"raw_" + "secret": _fake_secret()},
        )


def test_secret_kind_scope_sensitivity_models_block_high_risk_by_default(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    runtime.initialize_vault(mission_id=mission_id, config=_vault_config())
    high_risk = runtime.register_secret(
        mission_id=mission_id,
        kind=SecretKind.TRADING_API_KEY_REF,
        label="Trading credential ref",
        scope_policy=_scope_policy(),
        use_policy=_use_policy(allowed_kinds=[SecretKind.TRADING_API_KEY_REF]),
        sensitivity=SecretSensitivity.SPECIAL_AUTHORITY,
        provenance="operator_metadata_only",
    )
    unlocked = _unlock(runtime, mission_id)

    with pytest.raises(CredentialVaultRuntimeError, match="secret_kind_blocked"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=high_risk.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="external_api_read",
            requested_scope=["read:market_data"],
            envelope=_envelope(mission_id),
            unlock_session_id=unlocked.unlock_session_id,
        )


def test_secret_access_requires_mission_authority_envelope(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)

    with pytest.raises(CredentialVaultRuntimeError, match="mission_authority_required"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=metadata.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="external_api_read",
            requested_scope=["read:market_data"],
            envelope=None,
            unlock_session_id=unlocked.unlock_session_id,
        )


def test_secret_access_requires_purpose_scope_and_consumer_allowlist(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)

    with pytest.raises(CredentialVaultRuntimeError, match="purpose_not_allowed"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=metadata.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="send_email",
            requested_scope=["read:market_data"],
            envelope=_envelope(mission_id),
            unlock_session_id=unlocked.unlock_session_id,
        )
    with pytest.raises(CredentialVaultRuntimeError, match="scope_not_allowed"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=metadata.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="external_api_read",
            requested_scope=["write:market_data"],
            envelope=_envelope(mission_id),
            unlock_session_id=unlocked.unlock_session_id,
        )
    with pytest.raises(CredentialVaultRuntimeError, match="consumer_not_allowed"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=metadata.secret_id,
            consumer_kind=CredentialConsumerKind.CHANNEL_ADAPTER,
            consumer_ref="smtp_adapter",
            purpose="external_api_read",
            requested_scope=["read:market_data"],
            envelope=_envelope(mission_id),
            unlock_session_id=unlocked.unlock_session_id,
        )


def test_secret_access_rejects_expired_and_revoked_secret(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    expired = runtime.mark_secret_expired(
        mission_id=mission_id,
        secret_id=metadata.secret_id,
        at_time=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(CredentialVaultRuntimeError, match="secret_expired"):
        runtime.request_secret_access(
            mission_id=mission_id,
            secret_id=expired.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="external_api_read",
            requested_scope=["read:market_data"],
            envelope=_envelope(mission_id),
            unlock_session_id=unlocked.unlock_session_id,
        )

    runtime2, mission_id2, metadata2, unlocked2 = _runtime_with_secret(tmp_path)
    runtime2.revoke_secret(mission_id=mission_id2, secret_id=metadata2.secret_id, reason="operator revoked")
    with pytest.raises(CredentialVaultRuntimeError, match="secret_revoked"):
        runtime2.request_secret_access(
            mission_id=mission_id2,
            secret_id=metadata2.secret_id,
            consumer_kind=CredentialConsumerKind.EXTERNAL_API,
            consumer_ref="external_api_organ",
            purpose="external_api_read",
            requested_scope=["read:market_data"],
            envelope=_envelope(mission_id2),
            unlock_session_id=unlocked2.unlock_session_id,
        )


def test_secret_lease_creation_expiry_and_kill_revocation(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=5)
    expired = runtime.expire_secret_lease(
        mission_id=mission_id,
        lease_id=lease.lease_id,
        at_time=lease.expires_at + timedelta(seconds=1),
    )
    grant2 = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease2 = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant2.grant_id, ttl_seconds=60)
    killed = runtime.invalidate_active_leases_after_kill(mission_id=mission_id, reason="operator kill")

    assert lease.secret_handle.secret_id == metadata.secret_id
    assert expired.state.value == "expired"
    assert lease2.lease_id in [item.lease_id for item in killed]
    assert all(item.state.value == "revoked" for item in killed)


def test_secret_broker_checkout_returns_handles_and_tokens_not_raw_secret(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)

    checkout = runtime.checkout_secret(
        mission_id=mission_id,
        lease_id=lease.lease_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="external_api_organ",
    )

    assert checkout.raw_secret_materialized is False
    assert checkout.secret_value is None
    assert checkout.checkout_token.token_hash
    assert checkout.secret_handle.secret_id == metadata.secret_id
    assert _fake_secret() not in checkout.safe_model_dump().__repr__()


def test_secret_material_never_appears_in_telemetry_receipt_replay_memory_worker_or_prompt_context(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    checkout = runtime.checkout_secret(
        mission_id=mission_id,
        lease_id=lease.lease_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="external_api_organ",
    )
    receipt = runtime.record_secret_use(
        mission_id=mission_id,
        checkout_token_id=checkout.checkout_token.checkout_token_id,
        status="used",
    )
    replay = CredentialVaultReplayBuilder(runtime.store).build(mission_id)

    safe_surfaces = [
        _mission_text(runtime, mission_id),
        receipt.safe_model_dump(),
        replay.safe_model_dump(),
        runtime.build_memory_summary(mission_id=mission_id, secret_id=metadata.secret_id),
        runtime.build_worker_context(mission_id=mission_id, secret_id=metadata.secret_id),
        runtime.build_model_prompt_context(mission_id=mission_id, secret_id=metadata.secret_id),
    ]
    rendered = "\n".join(str(surface) for surface in safe_surfaces)
    assert _fake_secret() not in rendered
    assert "raw_secret" not in rendered
    assert "provider_response" not in rendered
    assert replay.materialized_secret is False
    assert replay.unlocked_vault is False


@pytest.mark.parametrize("source", ["voice", "desktop", "channel", "skill", "daemon", "scheduler", "memory", "llm"])
def test_advisory_surfaces_cannot_unlock_or_ambiently_use_secret(tmp_path: Path, source: str) -> None:
    runtime, mission_id, metadata, _unlocked = _runtime_with_secret(tmp_path)

    with pytest.raises(CredentialVaultRuntimeError, match="credential_advisory_surface_blocked"):
        runtime.request_advisory_surface_secret_use(
            mission_id=mission_id,
            secret_id=metadata.secret_id,
            source=source,
            requested_action="unlock_or_use",
        )


def test_channel_cannot_use_secret_without_valid_lease(tmp_path: Path) -> None:
    runtime, mission_id, metadata, _unlocked = _runtime_with_secret(tmp_path)

    with pytest.raises(CredentialVaultRuntimeError, match="secret_lease_required"):
        runtime.checkout_secret(
            mission_id=mission_id,
            lease_id="missing_lease",
            consumer_kind=CredentialConsumerKind.CHANNEL_ADAPTER,
            consumer_ref="smtp_adapter",
        )


def test_finalgate_certifies_terminal_secret_decisions(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    checkout = runtime.checkout_secret(
        mission_id=mission_id,
        lease_id=lease.lease_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="external_api_organ",
    )
    receipt = runtime.record_secret_use(
        mission_id=mission_id,
        checkout_token_id=checkout.checkout_token.checkout_token_id,
        status="used",
    )

    assert receipt.finalgate_certificate is not None
    assert receipt.finalgate_certificate.decision is SecretFinalGateDecision.USED
    assert receipt.finalgate_certificate.can_grant_authority is False
    assert receipt.finalgate_certificate.receipt_hash == receipt.receipt_hash


def test_replay_reconstructs_without_secret_materialization_or_external_actions(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    lease = runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    checkout = runtime.checkout_secret(
        mission_id=mission_id,
        lease_id=lease.lease_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="external_api_organ",
    )
    runtime.record_secret_use(
        mission_id=mission_id,
        checkout_token_id=checkout.checkout_token.checkout_token_id,
        status="used",
    )

    replay = CredentialVaultReplayBuilder(runtime.store).build(mission_id)

    assert replay.secret_metadata
    assert replay.unlock_sessions
    assert replay.leases
    assert replay.use_receipts
    assert replay.materialized_secret is False
    assert replay.called_os_keychain is False
    assert replay.called_provider_api is False
    assert replay.replayed_login is False
    assert replay.sent_channel_message is False
    assert replay.filled_desktop_field is False
    assert replay.invoked_model_provider is False


def test_leak_scanner_catches_fake_secret_canaries(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    runtime.initialize_vault(mission_id=mission_id, config=_vault_config())

    canary = _fake_secret()
    result = runtime.scan_for_secret_leaks(
        mission_id=mission_id,
        payload={"safe": "metadata", "leak": canary},
    )

    assert result.findings
    assert result.raw_secret_persisted is False
    assert all(canary not in str(finding) for finding in result.findings)
    persisted = _mission_text(runtime, mission_id)
    assert canary not in persisted


def test_telemetry_records_vault_events_and_metrics_without_secret_material(tmp_path: Path) -> None:
    runtime, mission_id, metadata, unlocked = _runtime_with_secret(tmp_path)
    grant = _grant(runtime, mission_id, metadata.secret_id, unlocked.unlock_session_id)
    runtime.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    snapshot = runtime.kernel.telemetry_sink.certified_mode_status()

    assert snapshot.event_counts_by_kind[TelemetryEventKind.SECRET_REGISTERED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.SECRET_ACCESS_GRANTED.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.CREDENTIAL_VAULT_SECRET_COUNT.value] >= 1
    assert _fake_secret() not in _mission_text(runtime, mission_id)


def _runtime(tmp_path: Path) -> tuple[CredentialVaultRuntime, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session-credential-vault",
        draft=MissionDraft(
            title="Credential vault test mission",
            objective="Exercise durable credential vault contracts.",
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="mission-summary",
            allowed_actions=["credential_use", "external_api_read"],
            forbidden_actions=["payment", "trading", "account_creation"],
            summary="Credential test authority summary.",
        ),
    )
    runtime = CredentialVaultRuntime(kernel)
    return runtime, record.mission_id


def _runtime_with_secret(tmp_path: Path) -> tuple[CredentialVaultRuntime, str, Any, Any]:
    runtime, mission_id = _runtime(tmp_path)
    runtime.initialize_vault(mission_id=mission_id, config=_vault_config())
    metadata = runtime.register_secret(
        mission_id=mission_id,
        kind=SecretKind.API_KEY,
        label="Read only market data API",
        scope_policy=_scope_policy(),
        use_policy=_use_policy(),
        sensitivity=SecretSensitivity.HIGH,
        provenance="operator_supplied_test_fixture",
        secret_material=_fake_secret(),
    )
    unlocked = _unlock(runtime, mission_id)
    return runtime, mission_id, metadata, unlocked


def _vault_config() -> CredentialVaultConfig:
    return CredentialVaultConfig(
        vault_id="vault-test",
        maturity=CredentialVaultMaturity.FAKE_SEALED_STORE,
        durable_metadata=True,
        durable_raw_secret_persistence=False,
    )


def _scope_policy() -> CredentialScopePolicy:
    return CredentialScopePolicy(
        allowed_consumers=[CredentialConsumerKind.EXTERNAL_API],
        allowed_consumer_refs=["external_api_organ"],
        allowed_purposes=["external_api_read"],
        allowed_scopes=["read:market_data"],
        blocked_kinds=[SecretKind.PAYMENT_METHOD_REF, SecretKind.TRADING_API_KEY_REF, SecretKind.DEVICE_PAIRING_SECRET],
    )


def _use_policy(*, allowed_kinds: list[SecretKind] | None = None) -> SecretUsePolicy:
    return SecretUsePolicy(
        allowed_purposes=["external_api_read"],
        allowed_kinds=allowed_kinds or [SecretKind.API_KEY],
        max_lease_seconds=120,
        require_unlock_session=True,
        require_operator_approval=False,
        risk_profile=CredentialUseRiskProfile.LOW,
    )


def _unlock(runtime: CredentialVaultRuntime, mission_id: str) -> Any:
    requested = runtime.request_unlock(
        mission_id=mission_id,
        policy=VaultUnlockPolicy(ttl_seconds=120, allowed_purposes=["external_api_read"]),
        purpose="external_api_read",
        requested_by="operator",
    )
    return runtime.approve_unlock_session(
        mission_id=mission_id,
        unlock_session_id=requested.unlock_session_id,
        approval_source="operator",
    )


def _grant(runtime: CredentialVaultRuntime, mission_id: str, secret_id: str, unlock_session_id: str) -> Any:
    return runtime.request_secret_access(
        mission_id=mission_id,
        secret_id=secret_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="external_api_organ",
        purpose="external_api_read",
        requested_scope=["read:market_data"],
        envelope=_envelope(mission_id),
        unlock_session_id=unlock_session_id,
        context=SecretUseContext(target_ref="api.example.test", evidence_refs=["ev-secret-use"]),
    )


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user-test",
        mission_title="Credential vault test mission",
        mission_objective="Use read-only market data credential under explicit authority.",
        allowed_systems=["credential_vault", "secret_broker", "external_api_organ"],
        allowed_tools=["secret_broker", "external_api_organ"],
        allowed_actions=["credential_use", "external_api_read", "read:market_data"],
        forbidden_actions=["payment", "trading", "account_creation", "desktop_secret_fill"],
        allowed_domains=["api.example.test"],
        max_duration_minutes=30,
    )


def _mission_text(runtime: CredentialVaultRuntime, mission_id: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in runtime.store.mission_dir(mission_id).rglob("*") if path.is_file())


def _fake_secret() -> str:
    return "sk-" + ("A" * 20)
