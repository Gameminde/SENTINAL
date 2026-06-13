from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.credential_vault import CredentialVaultRuntime
from sentinel.operator.credential_vault_models import (
    CredentialConsumerKind,
    CredentialScopePolicy,
    CredentialUseRiskProfile,
    CredentialVaultConfig,
    CredentialVaultMaturity,
    SecretKind,
    SecretSensitivity,
    SecretUseContext,
    SecretUsePolicy,
    VaultUnlockPolicy,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft


def test_modes_and_config_are_data_not_authority(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntime
    from sentinel.operator.account_authority_models import (
        AccountAuthorityConfig,
        AccountAuthorityMode,
        AccountSurfaceKind,
    )

    runtime, mission_id = _runtime(tmp_path)
    config = runtime.register_config(
        mission_id=mission_id,
        config=AccountAuthorityConfig(
            default_mode=AccountAuthorityMode.PLAN_ONLY,
            allowed_modes=[AccountAuthorityMode.PLAN_ONLY, AccountAuthorityMode.SANDBOX_ONLY],
            allowed_domains=["accounts.example.test"],
            allowed_surfaces=[AccountSurfaceKind.BROWSER],
        ),
    )

    assert config.data_not_authority is True
    assert config.can_grant_authority is False
    assert config.can_execute is False
    assert AccountAuthorityMode.DISABLED.value == "disabled"
    assert AccountAuthorityMode.DELEGATED_ACCOUNT_CREATION_SESSION.value == "delegated_account_creation_session"
    assert isinstance(runtime, AccountAuthorityRuntime)


def test_login_requires_mission_authority_envelope(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError, match="mission_authority_required"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(),
            envelope=None,
        )


def test_login_plan_uses_credential_vault_lease_and_final_consumer_checkout(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)
    vault, secret_id, unlock_session_id = _credential_vault_with_login_secret(runtime.kernel, mission_id)
    grant = vault.request_secret_access(
        mission_id=mission_id,
        secret_id=secret_id,
        consumer_kind=CredentialConsumerKind.BROWSER_LOGIN,
        consumer_ref="account_authority_final_consumer",
        purpose="account_login",
        requested_scope=["login:accounts.example.test"],
        envelope=_envelope(mission_id),
        unlock_session_id=unlock_session_id,
        context=SecretUseContext(target_ref="accounts.example.test", evidence_refs=["ev-login-target"]),
    )
    lease = vault.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)

    plan = runtime.plan_login(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_login_request(credential_lease_id=lease.lease_id),
        envelope=_envelope(mission_id),
    )
    result = runtime.execute_login(
        mission_id=mission_id,
        plan_id=plan.plan_id,
        envelope=_envelope(mission_id),
        credential_vault=vault,
        credential_lease_id=lease.lease_id,
    )

    assert plan.credential_requirement is not None
    assert plan.credential_requirement.requires_credential is True
    assert result.accepted is True
    assert result.receipt.credential_lease_ref_hash
    assert result.receipt.secret_use_receipt_ref
    assert result.receipt.raw_credential_persisted is False
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.certified is True
    assert "sk-" not in _mission_text(runtime, mission_id)


def test_login_blocks_missing_or_revoked_credential_lease(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)
    vault, secret_id, unlock_session_id = _credential_vault_with_login_secret(runtime.kernel, mission_id)
    grant = vault.request_secret_access(
        mission_id=mission_id,
        secret_id=secret_id,
        consumer_kind=CredentialConsumerKind.BROWSER_LOGIN,
        consumer_ref="account_authority_final_consumer",
        purpose="account_login",
        requested_scope=["login:accounts.example.test"],
        envelope=_envelope(mission_id),
        unlock_session_id=unlock_session_id,
    )
    lease = vault.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    vault.invalidate_active_leases_after_kill(mission_id=mission_id, reason="operator kill")

    with pytest.raises(AccountAuthorityRuntimeError, match="credential_lease_required"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(credential_lease_id=None),
            envelope=_envelope(mission_id),
        )

    plan = runtime.plan_login(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_login_request(credential_lease_id=lease.lease_id),
        envelope=_envelope(mission_id),
    )
    with pytest.raises(AccountAuthorityRuntimeError, match="secret_lease_not_active"):
        runtime.execute_login(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            envelope=_envelope(mission_id),
            credential_vault=vault,
            credential_lease_id=lease.lease_id,
        )


def test_login_rejects_service_and_surface_outside_config(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError
    from sentinel.operator.account_authority_models import AccountSurfaceKind

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError, match="account_service_not_allowed"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(credential_lease_id="lease-ref", service_name="Other Service"),
            envelope=_envelope(mission_id),
        )

    with pytest.raises(AccountAuthorityRuntimeError, match="account_surface_not_allowed"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(credential_lease_id="lease-ref", surface_kind=AccountSurfaceKind.DESKTOP),
            envelope=_envelope(mission_id),
        )


def test_account_creation_rejects_surface_outside_config(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError
    from sentinel.operator.account_authority_models import AccountSurfaceKind

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError, match="account_surface_not_allowed"):
        runtime.plan_account_creation(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_creation_request(surface_kind=AccountSurfaceKind.DESKTOP),
            envelope=_envelope(mission_id),
        )


def test_login_rejects_credential_lease_scope_for_different_target(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)
    vault, secret_id, unlock_session_id = _credential_vault_with_login_secret(
        runtime.kernel,
        mission_id,
        allowed_scopes=["login:other.example.test"],
    )
    grant = vault.request_secret_access(
        mission_id=mission_id,
        secret_id=secret_id,
        consumer_kind=CredentialConsumerKind.BROWSER_LOGIN,
        consumer_ref="account_authority_final_consumer",
        purpose="account_login",
        requested_scope=["login:other.example.test"],
        envelope=_envelope(mission_id),
        unlock_session_id=unlock_session_id,
        context=SecretUseContext(target_ref="other.example.test", evidence_refs=["ev-other-login-target"]),
    )
    lease = vault.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)
    plan = runtime.plan_login(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_login_request(credential_lease_id=lease.lease_id),
        envelope=_envelope(mission_id),
    )

    with pytest.raises(AccountAuthorityRuntimeError, match="credential_lease_scope_mismatch"):
        runtime.execute_login(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            envelope=_envelope(mission_id),
            credential_vault=vault,
            credential_lease_id=lease.lease_id,
        )


def test_login_plan_persists_hash_only_credential_lease_ref(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)

    plan = runtime.plan_login(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_login_request(credential_lease_id="lease-secret-capability-ref"),
        envelope=_envelope(mission_id),
    )
    persisted = _mission_text(runtime, mission_id)

    assert plan.credential_lease_ref is None
    assert plan.credential_lease_ref_hash
    assert "lease-secret-capability-ref" not in persisted


def test_login_blocks_after_kill_or_authority_expiry(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)
    runtime.kernel.kill(mission_id)
    with pytest.raises(AccountAuthorityRuntimeError, match="mission_killed"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(credential_lease_id="lease-ref"),
            envelope=_envelope(mission_id),
        )

    runtime2, mission_id2 = _runtime(tmp_path)
    config2 = _register_login_config(runtime2, mission_id2)
    expired = _envelope(mission_id2).model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    with pytest.raises(AccountAuthorityRuntimeError, match="mission_authority_expired"):
        runtime2.plan_login(
            mission_id=mission_id2,
            config_id=config2.config_id,
            request=_login_request(credential_lease_id="lease-ref"),
            envelope=expired,
        )


@pytest.mark.parametrize(
    "boundary, reason",
    [
        ("mfa", "mfa_checkpoint_required"),
        ("otp", "otp_checkpoint_required"),
        ("captcha", "captcha_checkpoint_required"),
        ("kyc", "kyc_checkpoint_required"),
        ("passkey", "passkey_user_presence_required"),
    ],
)
def test_human_boundaries_create_checkpoints_instead_of_bypass(tmp_path: Path, boundary: str, reason: str) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)

    plan = runtime.plan_login(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_login_request(credential_lease_id="lease-ref", boundary_descriptors=[boundary]),
        envelope=_envelope(mission_id),
    )

    assert plan.status.value == "checkpoint_required"
    assert plan.checkpoints
    assert reason in {checkpoint.reason for checkpoint in plan.checkpoints}
    assert all(checkpoint.bypass_allowed is False for checkpoint in plan.checkpoints)


def test_oauth_oidc_descriptor_is_safe_metadata_only(tmp_path: Path) -> None:
    from sentinel.operator.account_authority_models import OAuthFlowDescriptor, PKCEStateDescriptor

    descriptor = OAuthFlowDescriptor(
        provider_hash="provider_hash",
        redirect_uri_ref="redirect-ref",
        state_ref="state-ref",
        nonce_ref="nonce-ref",
        pkce=PKCEStateDescriptor(code_challenge_ref="challenge-ref", code_verifier_ref_hash="verifier-hash"),
        consent_checkpoint_required=True,
    )

    dumped = descriptor.safe_model_dump()
    assert dumped["token_exchange_live"] is False
    assert dumped["access_token_persisted"] is False
    assert dumped["refresh_token_persisted"] is False
    assert "secret" not in str(dumped).lower()
    assert "token_value" not in str(dumped).lower()


def test_account_creation_requires_identity_truth_terms_and_operator_owned_profile(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError
    from sentinel.operator.account_authority_models import AccountCreationRequest

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError, match="identity_profile_ref_required"):
        runtime.plan_account_creation(
            mission_id=mission_id,
            config_id=config.config_id,
            request=AccountCreationRequest(
                target_url="https://accounts.example.test/signup",
                service_name="Example Accounts",
                operator_approval_ref="approval-ref",
                terms_ack_ref="terms-ref",
                operator_owned_profile_authorized=True,
            ),
            envelope=_envelope(mission_id),
        )

    with pytest.raises(AccountAuthorityRuntimeError, match="terms_ack_ref_required"):
        runtime.plan_account_creation(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_creation_request(terms_ack_ref=None),
            envelope=_envelope(mission_id),
        )

    plan = runtime.plan_account_creation(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_creation_request(),
        envelope=_envelope(mission_id),
    )
    assert plan.identity_truth_policy.operator_owned_profile_required is True
    assert plan.status.value == "ready"


@pytest.mark.parametrize(
    "abuse_text",
    [
        "create 100 fake accounts",
        "ban evasion signup",
        "credential stuffing login",
        "bypass captcha",
        "fake identity KYC",
        "session cookie theft",
    ],
)
def test_account_creation_and_login_abuse_patterns_are_blocked(tmp_path: Path, abuse_text: str) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError):
        runtime.plan_account_creation(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_creation_request(operator_note=abuse_text),
            envelope=_envelope(mission_id),
        )


@pytest.mark.parametrize("source", ["voice", "desktop", "channel", "skill", "worker", "daemon", "scheduler", "memory", "llm"])
def test_advisory_surfaces_cannot_trigger_or_approve_account_actions(tmp_path: Path, source: str) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)

    with pytest.raises(AccountAuthorityRuntimeError, match="account_advisory_surface_blocked"):
        runtime.request_advisory_surface_account_action(
            mission_id=mission_id,
            source=source,
            requested_action="login_or_create_account",
        )


def test_account_result_memory_receipt_finalgate_telemetry_and_replay_are_not_authority(tmp_path: Path) -> None:
    from sentinel.operator.account_authority_replay import AccountAuthorityReplayBuilder

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)
    plan = runtime.plan_account_creation(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_creation_request(),
        envelope=_envelope(mission_id),
    )
    result = runtime.execute_account_creation(mission_id=mission_id, plan_id=plan.plan_id, envelope=_envelope(mission_id))
    replay = AccountAuthorityReplayBuilder(runtime.store).build(mission_id)
    memory_summary = runtime.build_memory_summary(mission_id=mission_id, session_ref=result.session_binding.session_ref)

    assert result.accepted is True
    assert result.receipt.can_grant_authority is False
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.can_grant_authority is False
    assert memory_summary["memory_is_authority"] is False
    assert replay.replayed_login is False
    assert replay.created_live_account is False
    assert replay.materialized_credential is False
    assert replay.called_provider_api is False
    assert replay.executed_browser_action is False
    assert runtime.store.verify_timeline(mission_id)


def test_account_material_execution_requires_certified_telemetry_before_receipts(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)
    plan = runtime.plan_account_creation(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_creation_request(),
        envelope=_envelope(mission_id),
    )
    runtime.kernel.telemetry_sink.store.enabled = False

    with pytest.raises(AccountAuthorityRuntimeError, match="telemetry_certified_mode_required"):
        runtime.execute_account_creation(mission_id=mission_id, plan_id=plan.plan_id, envelope=_envelope(mission_id))

    receipt_root = runtime.store.mission_dir(mission_id, create=True) / "account_authority" / "account_creation_receipts"
    assert not receipt_root.exists()


def test_raw_sensitive_values_are_rejected_or_redacted_before_persistence(tmp_path: Path) -> None:
    from sentinel.operator.account_authority import AccountAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_login_config(runtime, mission_id)

    with pytest.raises(AccountAuthorityRuntimeError, match="unsafe_account_flow_payload"):
        runtime.plan_login(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_login_request(credential_lease_id="lease-ref", operator_note="password=sk-" + "A" * 20),
            envelope=_envelope(mission_id),
        )

    persisted = _mission_text(runtime, mission_id)
    assert "sk-" + "A" * 20 not in persisted
    assert "provider_response" not in persisted
    assert "raw_prompt" not in persisted
    assert "reasoning" not in persisted


def test_telemetry_records_account_events_and_metrics(tmp_path: Path) -> None:
    from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind

    runtime, mission_id = _runtime(tmp_path)
    config = _register_account_creation_config(runtime, mission_id)
    plan = runtime.plan_account_creation(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_creation_request(),
        envelope=_envelope(mission_id),
    )
    runtime.execute_account_creation(mission_id=mission_id, plan_id=plan.plan_id, envelope=_envelope(mission_id))
    snapshot = runtime.kernel.telemetry_sink.certified_mode_status()

    assert snapshot.event_counts_by_kind[TelemetryEventKind.ACCOUNT_CREATION_PLAN_CREATED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.ACCOUNT_CREATION_COMPLETED.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.ACCOUNT_FLOW_CHECKPOINT_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.ACCOUNT_CREATION_SUCCESS_RATE.value] >= 1


def _runtime(tmp_path: Path):
    from sentinel.operator.account_authority import AccountAuthorityRuntime

    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session-account-authority",
        draft=MissionDraft(
            title="Account authority test mission",
            objective="Exercise governed login and account creation authority.",
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="mission-summary",
            allowed_actions=["account_login", "account_creation", "credential_use"],
            forbidden_actions=["payment", "trading", "account_farming"],
            summary="Account authority test summary.",
        ),
    )
    return AccountAuthorityRuntime(kernel), record.mission_id


def _register_login_config(runtime, mission_id: str):
    from sentinel.operator.account_authority_models import AccountAuthorityConfig, AccountAuthorityMode, AccountSurfaceKind

    return runtime.register_config(
        mission_id=mission_id,
        config=AccountAuthorityConfig(
            default_mode=AccountAuthorityMode.DELEGATED_LOGIN_SESSION,
            allowed_modes=[
                AccountAuthorityMode.PLAN_ONLY,
                AccountAuthorityMode.OPERATOR_ASSISTED_LOGIN,
                AccountAuthorityMode.DELEGATED_LOGIN_SESSION,
            ],
            allowed_domains=["accounts.example.test"],
            allowed_services=["Example Accounts"],
            allowed_surfaces=[AccountSurfaceKind.BROWSER],
        ),
    )


def _register_account_creation_config(runtime, mission_id: str):
    from sentinel.operator.account_authority_models import AccountAuthorityConfig, AccountAuthorityMode, AccountSurfaceKind

    return runtime.register_config(
        mission_id=mission_id,
        config=AccountAuthorityConfig(
            default_mode=AccountAuthorityMode.SANDBOX_ONLY,
            allowed_modes=[
                AccountAuthorityMode.PLAN_ONLY,
                AccountAuthorityMode.SANDBOX_ONLY,
                AccountAuthorityMode.OPERATOR_ASSISTED_ACCOUNT_CREATION,
            ],
            allowed_domains=["accounts.example.test"],
            allowed_services=["Example Accounts"],
            allowed_surfaces=[AccountSurfaceKind.BROWSER],
            sandbox_accounts_allowed=True,
            disposable_accounts_allowed=True,
        ),
    )


def _login_request(**overrides):
    from sentinel.operator.account_authority_models import AccountLoginRequest, AccountProviderKind, AccountSurfaceKind

    data = dict(
        target_url="https://accounts.example.test/login",
        service_name="Example Accounts",
        provider_kind=AccountProviderKind.SANDBOX,
        surface_kind=AccountSurfaceKind.BROWSER,
        credential_lease_id="lease-ref",
        target_evidence_refs=["ev-login-form"],
        operator_note="operator-owned sandbox login",
    )
    data.update(overrides)
    return AccountLoginRequest(**data)


def _creation_request(**overrides):
    from sentinel.operator.account_authority_models import AccountCreationRequest, AccountProviderKind, AccountSurfaceKind

    data = dict(
        target_url="https://accounts.example.test/signup",
        service_name="Example Accounts",
        provider_kind=AccountProviderKind.SANDBOX,
        surface_kind=AccountSurfaceKind.BROWSER,
        operator_approval_ref="approval-ref",
        identity_profile_ref="operator-profile-ref",
        terms_ack_ref="terms-ref",
        operator_owned_profile_authorized=True,
        sandbox_account=True,
        disposable_account=True,
        before_evidence_refs=["ev-signup-form"],
        operator_note="operator-owned sandbox account",
    )
    data.update(overrides)
    return AccountCreationRequest(**data)


def _credential_vault_with_login_secret(
    kernel: MissionKernel,
    mission_id: str,
    *,
    allowed_scopes: list[str] | None = None,
):
    vault = CredentialVaultRuntime(kernel)
    vault.initialize_vault(mission_id=mission_id, config=CredentialVaultConfig(vault_id="account-vault", maturity=CredentialVaultMaturity.FAKE_SEALED_STORE))
    metadata = vault.register_secret(
        mission_id=mission_id,
        kind=SecretKind.USERNAME_PASSWORD,
        label="Example account login",
        scope_policy=CredentialScopePolicy(
            allowed_consumers=[CredentialConsumerKind.BROWSER_LOGIN],
            allowed_consumer_refs=["account_authority_final_consumer"],
            allowed_purposes=["account_login"],
            allowed_scopes=allowed_scopes or ["login:accounts.example.test"],
        ),
        use_policy=SecretUsePolicy(
            allowed_purposes=["account_login"],
            allowed_kinds=[SecretKind.USERNAME_PASSWORD],
            max_lease_seconds=120,
            require_unlock_session=True,
            require_operator_approval=False,
            risk_profile=CredentialUseRiskProfile.SPECIAL_AUTHORITY,
        ),
        sensitivity=SecretSensitivity.SPECIAL_AUTHORITY,
        provenance="operator_supplied_test_fixture",
        secret_material="sk-" + ("B" * 20),
    )
    requested = vault.request_unlock(
        mission_id=mission_id,
        policy=VaultUnlockPolicy(ttl_seconds=120, allowed_purposes=["account_login"]),
        purpose="account_login",
        requested_by="operator",
    )
    unlocked = vault.approve_unlock_session(
        mission_id=mission_id,
        unlock_session_id=requested.unlock_session_id,
        approval_source="operator",
    )
    return vault, metadata.secret_id, unlocked.unlock_session_id


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user-account-authority",
        mission_title="Account authority mission",
        mission_objective="Use operator-owned sandbox account flows under explicit authority.",
        allowed_systems=["account_authority", "credential_vault", "secret_broker", "browser"],
        allowed_tools=["account_authority", "secret_broker", "browser_login_credential_session_broker_l6", "browser_account_creation_special_authority_l7"],
        allowed_actions=["account_login", "account_creation", "credential_use", "login:accounts.example.test"],
        forbidden_actions=["payment", "trading", "credential_stuffing", "account_farming", "captcha_bypass"],
        allowed_domains=["accounts.example.test"],
        max_duration_minutes=30,
    )


def _mission_text(runtime, mission_id: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in runtime.store.mission_dir(mission_id, create=True).rglob("*") if path.is_file())
