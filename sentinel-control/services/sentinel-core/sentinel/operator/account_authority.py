from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.account_authority_models import (
    AccountAuthorityConfig,
    AccountAuthorityFinalGateCertificate,
    AccountAuthorityFinalGateDecision,
    AccountCreationPlan,
    AccountCreationReceipt,
    AccountCreationRequest,
    AccountCreationResult,
    AccountCreationStep,
    AccountFlowIdempotencyKey,
    AccountFlowKind,
    AccountIdentityTruthPolicy,
    AccountLoginPlan,
    AccountLoginReceipt,
    AccountLoginRequest,
    AccountLoginResult,
    AccountLoginStep,
    AccountPlanStatus,
    AccountProviderKind,
    AccountSessionBinding,
    AccountSessionRef,
    AccountSessionState,
    DisposableAccountPolicy,
    HumanCheckpoint,
    LoginCredentialRequirement,
    SandboxAccountPolicy,
    account_utc_now,
    build_checkpoints,
    scan_account_flow_payload,
)
from sentinel.operator.credential_vault import CredentialVaultRuntime, CredentialVaultRuntimeError
from sentinel.operator.credential_vault_models import CredentialConsumerKind
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.operator.store import MissionRunStore
from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class AccountAuthorityRuntimeError(ValueError):
    """Raised when account/login special authority would violate Sentinel boundaries."""


class AccountAuthorityStore:
    def __init__(self, mission_store: MissionRunStore) -> None:
        self._mission_store = mission_store

    def verify_timeline(self, mission_id: str) -> bool:
        return self._mission_store.verify_timeline(mission_id)

    def mission_dir(self, mission_id: str, *, create: bool = True) -> Path:
        return self._mission_store.mission_dir(mission_id, create=create)

    def root(self, mission_id: str) -> Path:
        return self._mission_store.mission_dir(mission_id, create=True) / "account_authority"

    def item_path(self, mission_id: str, category: str, name: str) -> Path:
        root = self.root(mission_id) / category
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{stable_hash({'account_authority_item': name})[:24]}.json"

    def write(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self._mission_store.atomic_write_json(self.item_path(mission_id, category, name), payload)

    def append_event(
        self,
        mission_id: str,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ) -> None:
        self._mission_store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
        )


class AccountAuthorityRuntime:
    """Governed account-login/account-creation coordinator over Sentinel's existing spine."""

    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel
        self.store = AccountAuthorityStore(kernel.store)

    def register_config(self, *, mission_id: str, config: AccountAuthorityConfig) -> AccountAuthorityConfig:
        self.kernel.store.load_record(mission_id)
        config = config.with_hash()
        self.store.write(mission_id, "configs", config.config_id, config.safe_model_dump())
        self.store.append_event(
            mission_id,
            "account_authority_config_registered",
            "Account authority config registered as special-authority metadata.",
            metadata={"config_id": config.config_id, "config_hash": config.config_hash, "default_mode": config.default_mode.value},
        )
        return config

    def plan_login(
        self,
        *,
        mission_id: str,
        config_id: str,
        request: AccountLoginRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> AccountLoginPlan:
        config = self._load_config(mission_id, config_id)
        self._assert_authority(
            mission_id,
            envelope,
            action="account_login",
            tool="account_authority",
            domain=_hostname(request.target_url),
            config=config,
        )
        self._scan_or_raise(request.safe_model_dump())
        self._assert_config_request_scope(config=config, service_name=request.service_name, surface_kind=request.surface_kind)
        if not request.credential_lease_id:
            raise AccountAuthorityRuntimeError("credential_lease_required")
        checkpoints = self._persist_checkpoints(mission_id, build_checkpoints(mission_id, request.boundary_descriptors), "account_login_checkpoint_created")
        status = AccountPlanStatus.CHECKPOINT_REQUIRED if checkpoints else AccountPlanStatus.READY
        target_domain = _hostname(request.target_url)
        plan = AccountLoginPlan(
            mission_id=mission_id,
            request_id=request.request_id,
            config_id=config_id,
            status=status,
            target_domain=target_domain,
            target_url_hash=stable_hash(request.target_url),
            service_hash=stable_hash(request.service_name.lower()),
            provider_kind=request.provider_kind,
            surface_kind=request.surface_kind,
            credential_requirement=LoginCredentialRequirement(),
            credential_lease_ref=None,
            credential_lease_ref_hash=stable_hash(request.credential_lease_id),
            steps=[
                AccountLoginStep(action="validate_authority", target_ref_hash=stable_hash(target_domain)),
                AccountLoginStep(action="bind_credential_lease", target_ref_hash=stable_hash(request.credential_lease_id)),
                AccountLoginStep(action="fake_injected_login_consumer", target_ref_hash=stable_hash(request.target_url)),
            ],
            checkpoints=checkpoints,
            safety_scan=scan_account_flow_payload(request.safe_model_dump()),
            idempotency_key=AccountFlowIdempotencyKey(
                mission_id=mission_id,
                flow_kind=AccountFlowKind.LOGIN,
                target_hash=stable_hash({"url": request.target_url, "service": request.service_name}),
            ).with_hash(),
        ).with_hash()
        self.store.write(mission_id, "login_plans", plan.plan_id, plan.safe_model_dump())
        self.store.append_event(
            mission_id,
            "account_login_plan_created",
            "Account login plan created; execution remains gated by authority and credential lease.",
            metadata={"plan_id": plan.plan_id, "status": plan.status.value, "checkpoint_count": len(checkpoints)},
        )
        self._record_metric(mission_id, TelemetryMetricKind.ACCOUNT_FLOW_CHECKPOINT_COUNT, len(checkpoints), "Account flow checkpoint count sample.")
        return plan

    def execute_login(
        self,
        *,
        mission_id: str,
        plan_id: str,
        envelope: MissionAuthorityEnvelope | None,
        credential_vault: CredentialVaultRuntime,
        credential_lease_id: str | None = None,
    ) -> AccountLoginResult:
        plan = self._load_one(mission_id, "login_plans", plan_id, AccountLoginPlan)
        if not plan.verify_hash():
            raise AccountAuthorityRuntimeError("account_login_plan_hash_mismatch")
        config = self._load_config(mission_id, plan.config_id)
        self._assert_authority(mission_id, envelope, action="account_login", tool="account_authority", domain=plan.target_domain, config=config)
        self._assert_certified_telemetry()
        if plan.status is AccountPlanStatus.CHECKPOINT_REQUIRED:
            raise AccountAuthorityRuntimeError("human_checkpoint_required")
        self._assert_plan_not_executed(mission_id, "login_receipts", plan.plan_id, AccountLoginReceipt)
        if not credential_lease_id:
            raise AccountAuthorityRuntimeError("credential_lease_required")
        if stable_hash(credential_lease_id) != plan.credential_lease_ref_hash:
            raise AccountAuthorityRuntimeError("credential_lease_hash_mismatch")
        try:
            credential_vault.assert_lease_matches_scope(
                mission_id=mission_id,
                lease_id=credential_lease_id,
                expected_purpose="account_login",
                expected_scope=[f"login:{plan.target_domain}"],
                expected_consumer_kind=CredentialConsumerKind.BROWSER_LOGIN,
                expected_consumer_ref="account_authority_final_consumer",
            )
            checkout = credential_vault.checkout_secret(
                mission_id=mission_id,
                lease_id=credential_lease_id,
                consumer_kind=CredentialConsumerKind.BROWSER_LOGIN,
                consumer_ref="account_authority_final_consumer",
            )
            secret_use = credential_vault.record_secret_use(
                mission_id=mission_id,
                checkout_token_id=checkout.checkout_token.checkout_token_id,
                status="used",
            )
        except CredentialVaultRuntimeError as exc:
            raise AccountAuthorityRuntimeError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive fail-closed bridge
            raise AccountAuthorityRuntimeError(f"credential_vault_checkout_failed:{type(exc).__name__}") from exc
        session = AccountSessionRef(
            service_hash=plan.service_hash,
            target_domain=plan.target_domain,
        ).with_hash()
        receipt = AccountLoginReceipt(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            status=AccountPlanStatus.EXECUTED,
            target_domain=plan.target_domain,
            target_url_hash=plan.target_url_hash,
            service_hash=plan.service_hash,
            provider_kind=plan.provider_kind,
            session_ref=session.session_ref,
            credential_lease_ref_hash=plan.credential_lease_ref_hash,
            secret_use_receipt_ref=secret_use.receipt_id,
            checkout_result_ref=checkout.checkout_result_id,
            checkpoint_refs=[checkpoint.checkpoint_id for checkpoint in plan.checkpoints],
            safe_summary="Account login completed through fake/injected final consumer and scoped credential lease.",
        ).with_hash()
        certificate = self._certify_login(receipt)
        binding = AccountSessionBinding(
            mission_id=mission_id,
            session_ref=session.session_ref,
            state=AccountSessionState.ACTIVE,
            service_hash=plan.service_hash,
            provider_kind=plan.provider_kind,
            target_domain=plan.target_domain,
            credential_lease_ref_hash=plan.credential_lease_ref_hash,
            receipt_ref=receipt.receipt_id,
            finalgate_ref=certificate.certificate_id,
        ).with_hash()
        self.store.write(mission_id, "login_receipts", receipt.receipt_id, receipt.safe_model_dump())
        self.store.write(mission_id, "finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self.store.write(mission_id, "session_bindings", binding.binding_id, binding.safe_model_dump())
        self.store.append_event(
            mission_id,
            "account_session_bound",
            "Account session binding recorded as safe ref metadata.",
            metadata={"session_ref": binding.session_ref, "binding_id": binding.binding_id},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self.store.append_event(
            mission_id,
            "account_login_completed",
            "Account login completed without raw credential persistence.",
            metadata={"plan_id": plan.plan_id, "session_ref": session.session_ref},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.ACCOUNT_CREDENTIAL_LEASE_BIND_COUNT, 1, "Account credential lease bind count sample.")
        self._record_metric(mission_id, TelemetryMetricKind.ACCOUNT_LOGIN_SUCCESS_RATE, 1.0, "Account login success rate sample.")
        return AccountLoginResult(
            accepted=certificate.certified,
            status=AccountPlanStatus.EXECUTED if certificate.certified else AccountPlanStatus.FAILED,
            reason="account_login_completed" if certificate.certified else "account_login_finalgate_rejected",
            mission_id=mission_id,
            receipt=receipt,
            session_binding=binding,
            finalgate_certificate=certificate,
        )

    def plan_account_creation(
        self,
        *,
        mission_id: str,
        config_id: str,
        request: AccountCreationRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> AccountCreationPlan:
        config = self._load_config(mission_id, config_id)
        self._assert_authority(
            mission_id,
            envelope,
            action="account_creation",
            tool="account_authority",
            domain=_hostname(request.target_url),
            config=config,
        )
        self._scan_or_raise(request.safe_model_dump())
        self._assert_config_request_scope(config=config, service_name=request.service_name, surface_kind=request.surface_kind)
        if request.service_name not in set(config.allowed_services):
            raise AccountAuthorityRuntimeError("account_service_not_allowed")
        if not request.operator_owned_profile_authorized:
            raise AccountAuthorityRuntimeError("operator_owned_profile_required")
        if not request.identity_profile_ref:
            raise AccountAuthorityRuntimeError("identity_profile_ref_required")
        if not request.terms_ack_ref:
            raise AccountAuthorityRuntimeError("terms_ack_ref_required")
        if not request.operator_approval_ref:
            raise AccountAuthorityRuntimeError("operator_approval_ref_required")
        if request.sandbox_account and not config.sandbox_accounts_allowed:
            raise AccountAuthorityRuntimeError("sandbox_account_not_allowed")
        if request.disposable_account and not config.disposable_accounts_allowed:
            raise AccountAuthorityRuntimeError("disposable_account_not_allowed")
        target_domain = _hostname(request.target_url)
        checkpoints: list[HumanCheckpoint] = []
        plan = AccountCreationPlan(
            mission_id=mission_id,
            request_id=request.request_id,
            config_id=config_id,
            status=AccountPlanStatus.READY,
            target_domain=target_domain,
            target_url_hash=stable_hash(request.target_url),
            service_hash=stable_hash(request.service_name.lower()),
            provider_kind=request.provider_kind,
            surface_kind=request.surface_kind,
            identity_truth_policy=AccountIdentityTruthPolicy(operator_owned_profile_required=True),
            sandbox_policy=SandboxAccountPolicy(sandbox_allowed=request.sandbox_account),
            disposable_policy=DisposableAccountPolicy(disposable_allowed=request.disposable_account),
            terms_ack_ref=request.terms_ack_ref,
            identity_profile_ref_hash=stable_hash(request.identity_profile_ref),
            operator_approval_ref=request.operator_approval_ref,
            steps=[
                AccountCreationStep(action="validate_identity_truth", field_plan_hash=stable_hash("identity_truth")),
                AccountCreationStep(action="validate_terms_ack", field_plan_hash=stable_hash(request.terms_ack_ref)),
                AccountCreationStep(action="fake_injected_account_creation", field_plan_hash=stable_hash(request.before_evidence_refs)),
            ],
            checkpoints=checkpoints,
            safety_scan=scan_account_flow_payload(request.safe_model_dump()),
            idempotency_key=AccountFlowIdempotencyKey(
                mission_id=mission_id,
                flow_kind=AccountFlowKind.ACCOUNT_CREATION,
                target_hash=stable_hash({"url": request.target_url, "service": request.service_name}),
            ).with_hash(),
        ).with_hash()
        self.store.write(mission_id, "account_creation_plans", plan.plan_id, plan.safe_model_dump())
        self.store.append_event(
            mission_id,
            "account_creation_plan_created",
            "Account creation plan created for sandbox/fake-injected execution only.",
            metadata={"plan_id": plan.plan_id, "status": plan.status.value},
        )
        self._record_metric(mission_id, TelemetryMetricKind.ACCOUNT_FLOW_CHECKPOINT_COUNT, 0, "Account flow checkpoint count sample.")
        return plan

    def execute_account_creation(
        self,
        *,
        mission_id: str,
        plan_id: str,
        envelope: MissionAuthorityEnvelope | None,
    ) -> AccountCreationResult:
        plan = self._load_one(mission_id, "account_creation_plans", plan_id, AccountCreationPlan)
        if not plan.verify_hash():
            raise AccountAuthorityRuntimeError("account_creation_plan_hash_mismatch")
        config = self._load_config(mission_id, plan.config_id)
        self._assert_authority(mission_id, envelope, action="account_creation", tool="account_authority", domain=plan.target_domain, config=config)
        self._assert_certified_telemetry()
        if plan.status is AccountPlanStatus.CHECKPOINT_REQUIRED:
            raise AccountAuthorityRuntimeError("human_checkpoint_required")
        self._assert_plan_not_executed(mission_id, "account_creation_receipts", plan.plan_id, AccountCreationReceipt)
        account_creation_hash = stable_hash({"mission_id": mission_id, "plan_id": plan_id, "service_hash": plan.service_hash})
        session = AccountSessionRef(service_hash=plan.service_hash, target_domain=plan.target_domain).with_hash()
        receipt = AccountCreationReceipt(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            status=AccountPlanStatus.EXECUTED,
            target_domain=plan.target_domain,
            target_url_hash=plan.target_url_hash,
            service_hash=plan.service_hash,
            provider_kind=plan.provider_kind,
            session_ref=session.session_ref,
            identity_profile_ref_hash=plan.identity_profile_ref_hash,
            terms_ack_ref=plan.terms_ack_ref,
            operator_approval_ref=plan.operator_approval_ref,
            checkpoint_refs=[checkpoint.checkpoint_id for checkpoint in plan.checkpoints],
            account_creation_hash=account_creation_hash,
            safe_summary="Account creation completed in fake/injected sandbox-authority runtime.",
        ).with_hash()
        certificate = self._certify_creation(receipt)
        binding = AccountSessionBinding(
            mission_id=mission_id,
            session_ref=session.session_ref,
            state=AccountSessionState.BOUND,
            service_hash=plan.service_hash,
            provider_kind=plan.provider_kind,
            target_domain=plan.target_domain,
            receipt_ref=receipt.receipt_id,
            finalgate_ref=certificate.certificate_id,
        ).with_hash()
        self.store.write(mission_id, "account_creation_receipts", receipt.receipt_id, receipt.safe_model_dump())
        self.store.write(mission_id, "finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self.store.write(mission_id, "session_bindings", binding.binding_id, binding.safe_model_dump())
        self.store.append_event(
            mission_id,
            "account_session_bound",
            "Account session binding recorded after fake/injected account creation.",
            metadata={"session_ref": binding.session_ref, "binding_id": binding.binding_id},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self.store.append_event(
            mission_id,
            "account_creation_completed",
            "Account creation completed without live public-site call or raw credential persistence.",
            metadata={"plan_id": plan.plan_id, "session_ref": session.session_ref},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.ACCOUNT_CREATION_SUCCESS_RATE, 1.0, "Account creation success rate sample.")
        return AccountCreationResult(
            accepted=certificate.certified,
            status=AccountPlanStatus.EXECUTED if certificate.certified else AccountPlanStatus.FAILED,
            reason="account_creation_completed" if certificate.certified else "account_creation_finalgate_rejected",
            mission_id=mission_id,
            receipt=receipt,
            session_binding=binding,
            finalgate_certificate=certificate,
        )

    def build_memory_summary(self, *, mission_id: str, session_ref: str) -> dict[str, Any]:
        self.kernel.store.load_record(mission_id)
        return {
            "mission_id": mission_id,
            "session_ref_hash": stable_hash(session_ref),
            "memory_is_authority": False,
            "credential_material_in_memory": False,
            "account_authority_effect": "none",
        }

    def request_advisory_surface_account_action(self, *, mission_id: str, source: str, requested_action: str) -> None:
        self.kernel.store.load_record(mission_id)
        blocked = {"voice", "desktop", "channel", "skill", "worker", "daemon", "scheduler", "memory", "llm"}
        if source in blocked:
            raise AccountAuthorityRuntimeError("account_advisory_surface_blocked")
        raise AccountAuthorityRuntimeError("account_surface_not_approved")

    def _load_config(self, mission_id: str, config_id: str) -> AccountAuthorityConfig:
        config = self._load_one(mission_id, "configs", config_id, AccountAuthorityConfig)
        if not config.verify_hash():
            raise AccountAuthorityRuntimeError("account_authority_config_hash_mismatch")
        return config

    def _load_one(self, mission_id: str, category: str, item_id: str, model: Any) -> Any:
        return model.model_validate_json(self.store.item_path(mission_id, category, item_id).read_text(encoding="utf-8"))

    def _load_all(self, mission_id: str, category: str, model: Any) -> list[Any]:
        root = self.store.root(mission_id) / category
        if not root.exists():
            return []
        return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(root.glob("*.json"))]

    def _assert_plan_not_executed(self, mission_id: str, category: str, plan_id: str, model: Any) -> None:
        for receipt in self._load_all(mission_id, category, model):
            if getattr(receipt, "plan_id", None) == plan_id:
                raise AccountAuthorityRuntimeError("account_plan_already_executed")

    def _persist_checkpoints(self, mission_id: str, checkpoints: list[HumanCheckpoint], event_type: str) -> list[HumanCheckpoint]:
        for checkpoint in checkpoints:
            self.store.write(mission_id, "checkpoints", checkpoint.checkpoint_id, checkpoint.safe_model_dump())
            self.store.append_event(
                mission_id,
                event_type,
                "Account flow human checkpoint created.",
                metadata={"checkpoint_id": checkpoint.checkpoint_id, "reason": checkpoint.reason, "kind": checkpoint.checkpoint_kind},
            )
        return checkpoints

    def _assert_authority(
        self,
        mission_id: str,
        envelope: MissionAuthorityEnvelope | None,
        *,
        action: str,
        tool: str,
        domain: str,
        config: AccountAuthorityConfig,
    ) -> None:
        if envelope is None:
            raise AccountAuthorityRuntimeError("mission_authority_required")
        if envelope.id != mission_id:
            raise AccountAuthorityRuntimeError("mission_authority_mismatch")
        if envelope.revoked_at is not None:
            raise AccountAuthorityRuntimeError("mission_authority_revoked")
        if envelope.expires_at is not None and envelope.expires_at <= account_utc_now():
            raise AccountAuthorityRuntimeError("mission_authority_expired")
        record = self.kernel.store.load_record(mission_id)
        if record.status is OperatorMissionStatus.KILLED:
            raise AccountAuthorityRuntimeError("mission_killed")
        if self.kernel.is_terminal(mission_id):
            raise AccountAuthorityRuntimeError(f"mission_terminal:{record.status.value}")
        if tool not in set(envelope.allowed_tools):
            raise AccountAuthorityRuntimeError("mission_authority_missing_account_authority_tool")
        if action not in set(envelope.allowed_actions):
            raise AccountAuthorityRuntimeError("mission_authority_missing_account_action")
        if domain not in set(envelope.allowed_domains):
            raise AccountAuthorityRuntimeError("mission_authority_domain_not_allowed")
        if domain not in set(config.allowed_domains):
            raise AccountAuthorityRuntimeError("account_config_domain_not_allowed")
        if action == "account_login" and config.default_mode.value not in {"operator_assisted_login", "delegated_login_session", "plan_only", "sandbox_only"}:
            raise AccountAuthorityRuntimeError("account_login_mode_not_allowed")
        if action == "account_creation" and config.default_mode.value not in {"operator_assisted_account_creation", "delegated_account_creation_session", "plan_only", "sandbox_only"}:
            raise AccountAuthorityRuntimeError("account_creation_mode_not_allowed")

    def _assert_config_request_scope(
        self,
        *,
        config: AccountAuthorityConfig,
        service_name: str,
        surface_kind: Any,
    ) -> None:
        if config.allowed_services and service_name.lower() not in {service.lower() for service in config.allowed_services}:
            raise AccountAuthorityRuntimeError("account_service_not_allowed")
        if surface_kind not in set(config.allowed_surfaces):
            raise AccountAuthorityRuntimeError("account_surface_not_allowed")

    def _assert_certified_telemetry(self) -> None:
        sink = getattr(self.kernel, "telemetry_sink", None)
        if sink is None:
            raise AccountAuthorityRuntimeError("telemetry_certified_mode_required")
        try:
            if hasattr(sink, "require_material_execution"):
                sink.require_material_execution("account_authority")
            elif hasattr(sink, "require_certified_mode"):
                sink.require_certified_mode()
            else:
                raise AccountAuthorityRuntimeError("telemetry_certified_mode_required")
        except Exception as exc:
            raise AccountAuthorityRuntimeError("telemetry_certified_mode_required") from exc

    def _scan_or_raise(self, payload: Any) -> None:
        if "[REDACTED_SECRET]" in str(payload):
            raise AccountAuthorityRuntimeError("unsafe_account_flow_payload:redaction_hit")
        scan = scan_account_flow_payload(payload)
        if not scan.valid:
            raise AccountAuthorityRuntimeError(f"unsafe_account_flow_payload:{','.join(scan.reasons)}")

    def _certify_login(self, receipt: AccountLoginReceipt) -> AccountAuthorityFinalGateCertificate:
        reasons: list[str] = []
        if receipt.authority_effect != "none" or receipt.can_grant_authority or receipt.can_execute:
            reasons.append("receipt_authority_violation")
        if receipt.raw_credential_persisted or receipt.raw_token_persisted or receipt.raw_session_cookie_persisted:
            reasons.append("receipt_sensitive_material_persisted")
        if receipt.status is AccountPlanStatus.EXECUTED and not (receipt.credential_lease_ref_hash and receipt.secret_use_receipt_ref):
            reasons.append("receipt_missing_credential_proof_refs")
        decision = AccountAuthorityFinalGateDecision.REJECTED_UNSAFE_RECEIPT if reasons else AccountAuthorityFinalGateDecision.CERTIFIED_LOGIN
        certificate = AccountAuthorityFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=not reasons,
            reasons=reasons,
            receipt_hash=receipt.receipt_hash,
        ).with_hash()
        self.store.append_event(
            receipt.mission_id,
            "account_flow_finalgate_certified",
            "Account login FinalGate certificate recorded.",
            metadata={"receipt_id": receipt.receipt_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        return certificate

    def _certify_creation(self, receipt: AccountCreationReceipt) -> AccountAuthorityFinalGateCertificate:
        reasons: list[str] = []
        if receipt.authority_effect != "none" or receipt.can_grant_authority or receipt.can_execute:
            reasons.append("receipt_authority_violation")
        if receipt.raw_credential_persisted or receipt.raw_token_persisted or receipt.live_public_site_called:
            reasons.append("receipt_sensitive_or_live_public_site_violation")
        if receipt.status is AccountPlanStatus.EXECUTED and not receipt.account_creation_hash:
            reasons.append("receipt_missing_account_creation_hash")
        decision = AccountAuthorityFinalGateDecision.REJECTED_UNSAFE_RECEIPT if reasons else AccountAuthorityFinalGateDecision.CERTIFIED_ACCOUNT_CREATED
        certificate = AccountAuthorityFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=not reasons,
            reasons=reasons,
            receipt_hash=receipt.receipt_hash,
        ).with_hash()
        self.store.append_event(
            receipt.mission_id,
            "account_flow_finalgate_certified",
            "Account creation FinalGate certificate recorded.",
            metadata={"receipt_id": receipt.receipt_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        return certificate

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = self.kernel.store.telemetry_sink
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.ACCOUNT_AUTHORITY,
                domain=TelemetryDomain.SAFETY,
                metric_kind=metric_kind,
                value=value,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


__all__ = [
    "AccountAuthorityRuntime",
    "AccountAuthorityRuntimeError",
    "AccountAuthorityStore",
]
