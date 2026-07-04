from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.shared.models import SentinelModel


class OrganRuntimeSpec(SentinelModel):
    organ_id: str
    request_model: str
    runtime_handler: str
    authority_level: str
    backend_kind: str
    skill_binding: str
    proof_requirements: list[str] = Field(default_factory=list)
    receipt_kind: str
    replay_expectations: list[str] = Field(default_factory=list)
    recoverable_failure_classes: list[str] = Field(default_factory=list)
    hard_stop_categories: list[str] = Field(default_factory=list)
    default_dispatchable: bool = False
    locked_reason: str | None = None
    aliases: list[str] = Field(default_factory=list)
    request_field: str | None = None
    data_not_authority: bool = True
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _keep_spec_data_only(self) -> OrganRuntimeSpec:
        if self.data_not_authority is not True:
            raise ValueError("Organ runtime specs are data, not authority.")
        if self.authority_granting or self.can_grant_authority or self.registry_can_execute:
            raise ValueError("Organ runtime specs cannot grant authority or execute.")
        if not self.default_dispatchable and not self.locked_reason:
            raise ValueError("Non-dispatchable organ specs must state a locked_reason.")
        return self

    def matches(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized == self.organ_id or normalized in set(self.aliases)

    def safe_export(self) -> dict[str, Any]:
        return {
            "organ_id": self.organ_id,
            "request_model": self.request_model,
            "runtime_handler": self.runtime_handler,
            "authority_level": self.authority_level,
            "backend_kind": self.backend_kind,
            "skill_binding": self.skill_binding,
            "proof_requirements": list(self.proof_requirements),
            "receipt_kind": self.receipt_kind,
            "replay_expectations": list(self.replay_expectations),
            "recoverable_failure_classes": list(self.recoverable_failure_classes),
            "hard_stop_categories": list(self.hard_stop_categories),
            "default_dispatchable": self.default_dispatchable,
            "locked_reason": self.locked_reason,
            "aliases": list(self.aliases),
            "request_field": self.request_field,
            "data_not_authority": self.data_not_authority,
            "authority_granting": self.authority_granting,
            "can_grant_authority": self.can_grant_authority,
            "registry_can_execute": self.registry_can_execute,
        }


class OrganSpecRegistry(SentinelModel):
    specs: dict[str, OrganRuntimeSpec] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _keep_registry_data_only(self) -> OrganSpecRegistry:
        if self.data_not_authority is not True:
            raise ValueError("Organ spec registry is data, not authority.")
        if self.authority_granting or self.can_grant_authority or self.registry_can_execute:
            raise ValueError("Organ spec registry cannot grant authority or execute.")
        return self

    def get(self, organ_id_or_alias: str | None) -> OrganRuntimeSpec | None:
        if not organ_id_or_alias:
            return None
        normalized = organ_id_or_alias.strip().lower()
        if normalized in self.specs:
            return self.specs[normalized]
        for spec in self.specs.values():
            if spec.matches(normalized):
                return spec
        return None

    def require(self, organ_id_or_alias: str) -> OrganRuntimeSpec:
        spec = self.get(organ_id_or_alias)
        if spec is None:
            raise KeyError(f"unknown organ runtime spec: {organ_id_or_alias}")
        return spec

    def list_specs(self) -> list[OrganRuntimeSpec]:
        return list(self.specs.values())

    def safe_export(self) -> list[dict[str, Any]]:
        return [spec.safe_export() for spec in self.list_specs()]

    def resolve_browser_runtime_organ_id(
        self,
        *,
        action_level: DelegatedActionLevel,
        raw_candidate: dict[str, Any],
        organ_contracts: dict[str, dict[str, Any]],
        selected_backend_id: str | None = None,
    ) -> str:
        explicit = str(
            raw_candidate.get("browser_organ_kind")
            or raw_candidate.get("runtime_organ_kind")
            or raw_candidate.get("organ_runtime_kind")
            or ""
        ).strip().lower()
        if explicit:
            explicit_spec = self.get(explicit)
            if explicit_spec is not None:
                return explicit_spec.organ_id

        backend_id = selected_backend_id or ""
        if "session" in backend_id or "cloak" in backend_id:
            return "browser_session_manager"
        if "semantic_extraction" in backend_id:
            return "browser_semantic_extraction"
        if "preparation" in backend_id:
            return "browser_preparation"

        for organ_id in ("browser_semantic_extraction", "browser_preparation", "browser_session_manager"):
            contract = organ_contracts.get(organ_id)
            if isinstance(contract, dict) and contract.get("available"):
                spec = self.get(organ_id)
                if spec is not None and spec.authority_level == action_level.value:
                    return spec.organ_id

        if action_level is DelegatedActionLevel.L5:
            return "browser_session_manager"
        return "browser_readonly"


def _spec(
    organ_id: str,
    *,
    request_model: str,
    runtime_handler: str,
    authority_level: str,
    backend_kind: str,
    skill_binding: str,
    proof_requirements: list[str],
    receipt_kind: str,
    replay_expectations: list[str],
    recoverable_failure_classes: list[str] | None = None,
    hard_stop_categories: list[str] | None = None,
    default_dispatchable: bool,
    locked_reason: str | None = None,
    aliases: list[str] | None = None,
    request_field: str | None = None,
) -> OrganRuntimeSpec:
    return OrganRuntimeSpec(
        organ_id=organ_id,
        request_model=request_model,
        runtime_handler=runtime_handler,
        authority_level=authority_level,
        backend_kind=backend_kind,
        skill_binding=skill_binding,
        proof_requirements=proof_requirements,
        receipt_kind=receipt_kind,
        replay_expectations=replay_expectations,
        recoverable_failure_classes=recoverable_failure_classes or [],
        hard_stop_categories=hard_stop_categories or [],
        default_dispatchable=default_dispatchable,
        locked_reason=locked_reason,
        aliases=aliases or [],
        request_field=request_field,
    )


def default_organ_spec_registry() -> OrganSpecRegistry:
    specs = [
        _spec(
            "local_artifact",
            request_model="L2LocalArtifactRequest",
            runtime_handler="execute_l2",
            authority_level="L2",
            backend_kind="local_artifact_executor",
            skill_binding="local_artifact",
            proof_requirements=["low_risk_finalgate", "local_artifact_receipt"],
            receipt_kind="local_artifact_receipt",
            replay_expectations=["no_duplicate_file_write"],
            default_dispatchable=True,
            request_field="l2_request",
        ),
        _spec(
            "reversible_workspace",
            request_model="L3WorkspaceRequest",
            runtime_handler="execute_l3",
            authority_level="L3",
            backend_kind="reversible_workspace_executor",
            skill_binding="workspace_patch",
            proof_requirements=["low_risk_finalgate", "workspace_patch_receipt"],
            receipt_kind="workspace_patch_receipt",
            replay_expectations=["no_reapply_patch"],
            recoverable_failure_classes=["stale_file_hash", "patch_context_miss"],
            default_dispatchable=True,
            request_field="l3_request",
        ),
        _spec(
            "worker_fleet_backend",
            request_model="WorkerSpawnRequest",
            runtime_handler="WorkerOrchestrationRuntime.execute",
            authority_level="L3",
            backend_kind="worker_fleet_runtime",
            skill_binding="worker_fleet",
            proof_requirements=["worker_spawn_receipt", "child_authority_subset", "product_action_kernel_finalgate"],
            receipt_kind="worker_orchestration_receipt",
            replay_expectations=["no_respawn_on_replay", "no_worker_reexecute_on_replay"],
            recoverable_failure_classes=["worker_role_missing", "worker_scope_mismatch", "worker_budget_exhausted"],
            hard_stop_categories=["authority_expansion", "nested_worker_spawn", "payment", "credential_access"],
            default_dispatchable=True,
            aliases=["worker_fleet", "worker_orchestration", "spawn_worker"],
            request_field="worker_spawn_request",
        ),
        _spec(
            "browser_readonly",
            request_model="BrowserReadOnlyRequest",
            runtime_handler="execute_browser_readonly",
            authority_level="L4",
            backend_kind="browser_readonly_fetcher",
            skill_binding="browser_control",
            proof_requirements=["browser_readonly_finalgate", "browser_readonly_receipt"],
            receipt_kind="browser_readonly_receipt",
            replay_expectations=["no_mutation", "no_refetch_on_replay"],
            recoverable_failure_classes=["fetch_timeout", "dynamic_loading_not_captured"],
            default_dispatchable=True,
            aliases=["browser_readonly_public"],
            request_field="browser_readonly_request",
        ),
        _spec(
            "browser_preparation",
            request_model="BrowserPreparationRequest",
            runtime_handler="execute_browser_preparation",
            authority_level="L4",
            backend_kind="browser_preparation_organ",
            skill_binding="browser_control",
            proof_requirements=["browser_preparation_finalgate", "browser_preparation_receipt"],
            receipt_kind="browser_preparation_receipt",
            replay_expectations=["no_navigation_on_replay"],
            recoverable_failure_classes=["candidate_ref_missing", "weak_action_candidate"],
            default_dispatchable=True,
            request_field="browser_preparation_request",
        ),
        _spec(
            "browser_semantic_extraction",
            request_model="BrowserSemanticExtractionRequest",
            runtime_handler="execute_browser_semantic_extraction",
            authority_level="L4",
            backend_kind="browser_semantic_extraction_organ",
            skill_binding="browser_control",
            proof_requirements=["browser_semantic_extraction_finalgate", "browser_semantic_extraction_receipt"],
            receipt_kind="browser_semantic_extraction_receipt",
            replay_expectations=["no_reextract_on_replay"],
            recoverable_failure_classes=["extraction_too_shallow", "source_receipt_missing"],
            default_dispatchable=True,
            request_field="browser_semantic_extraction_request",
        ),
        _spec(
            "browser_session_manager",
            request_model="BrowserSessionRequest",
            runtime_handler="execute_browser_session_manager",
            authority_level="L5",
            backend_kind="cloakbrowser",
            skill_binding="browser_control",
            proof_requirements=["browser_session_finalgate", "browser_session_receipt"],
            receipt_kind="browser_session_receipt",
            replay_expectations=["no_reopen_no_reclick_no_retype"],
            recoverable_failure_classes=["locator_timeout", "stale_ref", "hidden_or_disabled_ref", "page_load_timeout"],
            default_dispatchable=False,
            locked_reason="requires explicit browser L5 mission authority and runtime opt-in",
            aliases=["browser_session_manager_l5_live", "browser_l5_live_session", "cloakbrowser_session"],
            request_field="browser_session_request",
        ),
        _spec(
            "browser_form_submit_special_authority",
            request_model="BrowserFormSubmitRequest",
            runtime_handler="execute_browser_form_submit",
            authority_level="L6",
            backend_kind="browser_form_submit_organ",
            skill_binding="browser_control",
            proof_requirements=["browser_form_submit_finalgate", "browser_form_submit_receipt"],
            receipt_kind="browser_form_submit_receipt",
            replay_expectations=["no_resubmit_on_replay"],
            recoverable_failure_classes=["submit_target_missing"],
            hard_stop_categories=["external_send", "form_submit", "personal_data"],
            default_dispatchable=False,
            locked_reason="form submission crosses external-send boundary",
            request_field="browser_form_submit_request",
        ),
        _spec(
            "browser_login_credential_session_broker",
            request_model="BrowserLoginCredentialSessionRequest",
            runtime_handler="execute_browser_login",
            authority_level="L6",
            backend_kind="browser_login_session_broker",
            skill_binding="browser_control",
            proof_requirements=["browser_login_finalgate", "browser_login_receipt"],
            receipt_kind="browser_login_receipt",
            replay_expectations=["no_login_on_replay"],
            hard_stop_categories=["credential_access", "login_session"],
            default_dispatchable=False,
            locked_reason="login/session credentials require special authority",
            request_field="browser_login_request",
        ),
        _spec(
            "browser_download_upload_quarantine",
            request_model="BrowserFileQuarantineRequest",
            runtime_handler="execute_browser_file_quarantine",
            authority_level="L6",
            backend_kind="browser_download_upload_quarantine",
            skill_binding="browser_control",
            proof_requirements=["browser_file_quarantine_finalgate", "browser_file_quarantine_receipt"],
            receipt_kind="browser_file_quarantine_receipt",
            replay_expectations=["no_download_upload_on_replay"],
            hard_stop_categories=["file_upload", "file_download", "external_file_transfer"],
            default_dispatchable=False,
            locked_reason="file transfer requires explicit quarantine authority",
            request_field="browser_file_quarantine_request",
        ),
        _spec(
            "browser_js_sandbox_special_authority",
            request_model="BrowserJSSandboxRequest",
            runtime_handler="execute_browser_js_sandbox",
            authority_level="L6",
            backend_kind="browser_js_sandbox",
            skill_binding="browser_control",
            proof_requirements=["browser_js_sandbox_finalgate", "browser_js_sandbox_receipt"],
            receipt_kind="browser_js_sandbox_receipt",
            replay_expectations=["no_js_execution_on_replay"],
            recoverable_failure_classes=["sandbox_timeout"],
            hard_stop_categories=["javascript_execution"],
            default_dispatchable=False,
            locked_reason="browser JavaScript execution requires special authority",
            request_field="browser_js_sandbox_request",
        ),
        _spec(
            "browser_payment_spend_special_authority",
            request_model="BrowserPaymentSpendRequest",
            runtime_handler="locked_no_runtime_handler",
            authority_level="L7",
            backend_kind="locked_payment_boundary",
            skill_binding="browser_control",
            proof_requirements=["payment_special_authority", "spend_receipt", "human_grant"],
            receipt_kind="payment_locked_receipt",
            replay_expectations=["no_payment_on_replay"],
            hard_stop_categories=["payment", "spend", "checkout"],
            default_dispatchable=False,
            locked_reason="payment/spend is locked out of default dispatch",
        ),
    ]
    return OrganSpecRegistry(specs={spec.organ_id: spec for spec in specs})
