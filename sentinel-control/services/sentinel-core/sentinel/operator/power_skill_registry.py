from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.organs.organ_spec_registry import OrganSpecRegistry, default_organ_spec_registry
from sentinel.operator.actionability_registry import ActionabilityRegistry, build_default_actionability_registry
from sentinel.operator.browser_backend_selector import BrowserBackendSelection, select_browser_backend
from sentinel.operator.runtime_connections import RuntimeConnectionRegistry, build_default_runtime_connection_registry
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class PowerSkillBackendBinding(SentinelModel):
    skill_id: str
    capability_id: str
    model_visible_backend_id: str
    preferred_backend_id: str | None = None
    compatibility_backend_id: str | None = None
    runtime_connection_id: str | None = None
    adapter_id: str | None = None
    owner_module: str
    owner_symbol: str | None = None
    organ_refs: tuple[str, ...] = Field(default_factory=tuple)
    organ_spec_refs: tuple[str, ...] = Field(default_factory=tuple)
    organ_receipt_kinds: tuple[str, ...] = Field(default_factory=tuple)
    organ_proof_requirements: tuple[str, ...] = Field(default_factory=tuple)
    organ_replay_expectations: tuple[str, ...] = Field(default_factory=tuple)
    organ_recoverable_failure_classes: tuple[str, ...] = Field(default_factory=tuple)
    organ_hard_stop_categories: tuple[str, ...] = Field(default_factory=tuple)
    backend_candidates: tuple[str, ...] = Field(default_factory=tuple)
    product_reachable: bool = False
    task_loop_reachable: bool = False
    dispatch_enabled: bool = False
    locked: bool = False
    lock_reason: str = ""
    limitations: tuple[str, ...] = Field(default_factory=tuple)
    proof_contract: str
    replay_contract: str
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _binding_is_data_only(self) -> "PowerSkillBackendBinding":
        assert_data_not_authority(
            context="power_skill_backend_binding",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.dispatch_enabled:
            raise ValueError("PowerSkillRegistry cannot enable dispatch.")
        if self.locked and not self.lock_reason:
            raise ValueError("locked skill backend bindings must explain the lock reason")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PowerSkillBackendFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("power_skill_backend_frame"))
    skill_backends: tuple[PowerSkillBackendBinding, ...] = Field(default_factory=tuple)
    missing_backend_actions: tuple[str, ...] = Field(default_factory=tuple)
    invariant: str = "skills_map_to_organs_and_backends_without_granting_authority"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _frame_is_data_only(self) -> "PowerSkillBackendFrame":
        assert_data_not_authority(
            context="power_skill_backend_frame",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PowerSkillRegistry(SentinelModel):
    bindings: tuple[PowerSkillBackendBinding, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "PowerSkillRegistry":
        ids = [binding.skill_id for binding in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("PowerSkillRegistry cannot contain duplicate skill ids.")
        return self

    def get(self, skill_id: str) -> PowerSkillBackendBinding:
        for binding in self.bindings:
            if binding.skill_id == skill_id:
                return binding
        raise KeyError(f"Unknown power skill `{skill_id}`.")

    def compile_backend_frame(
        self,
        *,
        available_actions: tuple[str, ...],
        granted_capabilities: tuple[str, ...] = (),
        actionability_registry: ActionabilityRegistry | None = None,
    ) -> dict[str, Any]:
        actionability = actionability_registry or build_default_actionability_registry()
        granted = set(granted_capabilities)
        selected: dict[str, PowerSkillBackendBinding] = {}
        missing: list[str] = []
        for action_name in available_actions:
            canonical = actionability.normalize_action_name(action_name)
            skill_id = _skill_id_for_action(actionability, canonical)
            if skill_id is None:
                missing.append(canonical)
                continue
            binding = self._binding_for_skill(skill_id)
            if binding is None:
                missing.append(canonical)
                continue
            if granted and binding.capability_id not in granted and binding.skill_id not in granted:
                continue
            selected.setdefault(binding.skill_id, binding)
        return PowerSkillBackendFrame(
            skill_backends=tuple(selected[key] for key in sorted(selected)),
            missing_backend_actions=tuple(dict.fromkeys(missing)),
        ).safe_model_dump()

    def _binding_for_skill(self, skill_id: str) -> PowerSkillBackendBinding | None:
        for binding in self.bindings:
            if binding.skill_id == skill_id:
                return binding
        return None


def build_default_power_skill_registry(
    *,
    runtime_connection_registry: RuntimeConnectionRegistry | None = None,
    browser_backend_selection: BrowserBackendSelection | None = None,
    organ_spec_registry: OrganSpecRegistry | None = None,
) -> PowerSkillRegistry:
    runtime_registry = runtime_connection_registry or build_default_runtime_connection_registry()
    browser_selection = browser_backend_selection or select_browser_backend()
    organ_registry = organ_spec_registry or default_organ_spec_registry()
    bindings = (
        _sentinel_loop_binding(),
        _read_only_binding(runtime_registry),
        _workspace_patch_binding(runtime_registry),
        _runtime_or_local_binding(
            runtime_registry,
            skill_id="code_execution_sandbox",
            capability_id="code_execution_sandbox",
            model_visible_backend_id="code_execution_skill",
            owner_module="sentinel.operator.code_execution_sandbox_runtime",
            owner_symbol="CodeExecutionSandboxRuntime",
            backend_candidates=("code_execution_sandbox_runtime",),
            proof_contract="CodeExecutionSandboxReceipt",
            replay_contract="ModelLedTaskLoopReplay code execution deltas",
        ),
        _runtime_or_local_binding(
            runtime_registry,
            skill_id="bounded_channel",
            capability_id="bounded_channel",
            model_visible_backend_id="bounded_channel_skill",
            owner_module="sentinel.operator.connection_live_channel_action_runtime",
            owner_symbol="BoundedChannelActionRuntime",
            backend_candidates=("local_channel_transport", "webhook_channel_transport", "telegram_channel_transport"),
            proof_contract="ChannelDeliveryReceipt",
            replay_contract="ConnectionLiveChannelReplayView no-resend deltas",
        ),
        _runtime_or_local_binding(
            runtime_registry,
            skill_id="worker_fleet",
            capability_id="worker_fleet",
            model_visible_backend_id="worker_fleet_skill",
            owner_module="sentinel.operator.worker_orchestration_runtime",
            owner_symbol="WorkerOrchestrationRuntime",
            backend_candidates=("worker_fleet_runtime", "local_worker_fleet_runtime"),
            proof_contract="WorkerOrchestrationReceipt",
            replay_contract="ProductActionKernelTaskLoopReplay no-respawn/no-reexecute",
        ),
        _local_binding(
            skill_id="browser_control",
            capability_id="browser_control",
            model_visible_backend_id="browser_fixture_skill",
            owner_module="sentinel.operator.browser_control_runtime",
            owner_symbol="BrowserControlRuntime",
            backend_candidates=("in_memory_browser_fixture",),
            proof_contract="BrowserActionReceipt",
            replay_contract="BrowserControlReplayView no-reclick deltas",
        ),
        _real_browser_binding(browser_selection),
        _locked_binding(
            skill_id="external_api",
            capability_id="external_api",
            owner_module="sentinel.operator.connection_manifest_registry",
            lock_reason="external API skills require a future explicit runtime adapter and credential lease",
        ),
        _locked_binding(
            skill_id="desktop_control",
            capability_id="desktop_control",
            owner_module="sentinel.operator.connection_manifest_registry",
            lock_reason="desktop control remains locked until a bounded desktop runtime is product-proven",
        ),
        _locked_binding(
            skill_id="voice_runtime",
            capability_id="voice_runtime",
            owner_module="sentinel.operator.connection_manifest_registry",
            lock_reason="voice runtime remains locked until a bounded voice transport is product-proven",
        ),
        _locked_binding(
            skill_id="account_authority",
            capability_id="account_authority",
            owner_module="sentinel.operator.connection_identity_registry",
            lock_reason="account authority cannot be granted by model-visible actions",
        ),
        _locked_binding(
            skill_id="financial_authority",
            capability_id="financial_authority",
            owner_module="sentinel.operator.connection_identity_registry",
            lock_reason="financial authority requires special explicit grants and is not dispatchable",
        ),
        _locked_binding(
            skill_id="payment_authority",
            capability_id="payment_authority",
            owner_module="sentinel.operator.connection_identity_registry",
            lock_reason="payment and checkout remain hard-stopped",
        ),
    )
    return PowerSkillRegistry(
        bindings=tuple(_with_organ_metadata(binding, organ_registry=organ_registry) for binding in bindings)
    )


def _sentinel_loop_binding() -> PowerSkillBackendBinding:
    return PowerSkillBackendBinding(
        skill_id="sentinel_loop",
        capability_id="sentinel_loop",
        model_visible_backend_id="model_led_task_loop",
        owner_module="sentinel.operator.model_led_task_loop",
        owner_symbol="ModelLedTaskLoop",
        task_loop_reachable=True,
        backend_candidates=("model_led_task_loop",),
        proof_contract="ModelLedTaskLoopFinalCertificate",
        replay_contract="ModelLedTaskLoopReplay",
    )


def _runtime_or_local_binding(
    runtime_registry: RuntimeConnectionRegistry,
    *,
    skill_id: str,
    capability_id: str,
    model_visible_backend_id: str,
    owner_module: str,
    owner_symbol: str,
    backend_candidates: tuple[str, ...],
    proof_contract: str,
    replay_contract: str,
) -> PowerSkillBackendBinding:
    try:
        runtime_profile = runtime_registry.get(skill_id)
    except KeyError:
        return _local_binding(
            skill_id=skill_id,
            capability_id=capability_id,
            model_visible_backend_id=model_visible_backend_id,
            owner_module=owner_module,
            owner_symbol=owner_symbol,
            backend_candidates=backend_candidates,
            proof_contract=proof_contract,
            replay_contract=replay_contract,
        )
    return PowerSkillBackendBinding(
        skill_id=skill_id,
        capability_id=capability_id,
        model_visible_backend_id=model_visible_backend_id,
        runtime_connection_id=runtime_profile.connection_id,
        adapter_id=runtime_profile.adapter_id,
        owner_module=runtime_profile.owner_module,
        owner_symbol=runtime_profile.owner_symbol,
        organ_refs=runtime_profile.organ_registry_refs,
        backend_candidates=(*backend_candidates, "product_action_kernel_adapter"),
        product_reachable=runtime_profile.production_reachable,
        task_loop_reachable=True,
        proof_contract=runtime_profile.receipt_contract,
        replay_contract=runtime_profile.replay_adapter,
        limitations=runtime_profile.limitations,
    )


def _read_only_binding(runtime_registry: RuntimeConnectionRegistry) -> PowerSkillBackendBinding:
    runtime_profile = runtime_registry.get("read_only_research")
    return PowerSkillBackendBinding(
        skill_id="read_only_research",
        capability_id="read_only_research",
        model_visible_backend_id="read_only_research_skill",
        runtime_connection_id=runtime_profile.connection_id,
        adapter_id=runtime_profile.adapter_id,
        owner_module=runtime_profile.owner_module,
        owner_symbol=runtime_profile.owner_symbol,
        organ_refs=runtime_profile.organ_registry_refs,
        backend_candidates=("read_only_research_adapter", "ReadOnlyProductionSpineSession"),
        product_reachable=runtime_profile.production_reachable,
        task_loop_reachable=True,
        proof_contract=runtime_profile.receipt_contract,
        replay_contract=runtime_profile.replay_adapter,
        limitations=runtime_profile.limitations,
    )


def _workspace_patch_binding(runtime_registry: RuntimeConnectionRegistry) -> PowerSkillBackendBinding:
    try:
        runtime_profile = runtime_registry.get("workspace_patch")
    except KeyError:
        return _local_binding(
            skill_id="workspace_patch",
            capability_id="workspace_patch",
            model_visible_backend_id="workspace_patch_skill",
            owner_module="sentinel.operator.workspace_patch_runtime",
            owner_symbol="WorkspacePatchRuntime",
            backend_candidates=("workspace_patch_runtime",),
            proof_contract="WorkspacePatchReceipt",
            replay_contract="ModelLedTaskLoopReplay workspace patch deltas",
        )
    return PowerSkillBackendBinding(
        skill_id="workspace_patch",
        capability_id="workspace_patch",
        model_visible_backend_id="workspace_patch_skill",
        runtime_connection_id=runtime_profile.connection_id,
        adapter_id=runtime_profile.adapter_id,
        owner_module=runtime_profile.owner_module,
        owner_symbol=runtime_profile.owner_symbol,
        organ_refs=runtime_profile.organ_registry_refs,
        backend_candidates=("workspace_patch_runtime", "product_action_kernel_adapter"),
        product_reachable=runtime_profile.production_reachable,
        task_loop_reachable=True,
        proof_contract=runtime_profile.receipt_contract,
        replay_contract=runtime_profile.replay_adapter,
        limitations=runtime_profile.limitations,
    )


def _local_binding(
    *,
    skill_id: str,
    capability_id: str,
    model_visible_backend_id: str,
    owner_module: str,
    owner_symbol: str,
    backend_candidates: tuple[str, ...],
    proof_contract: str,
    replay_contract: str,
) -> PowerSkillBackendBinding:
    return PowerSkillBackendBinding(
        skill_id=skill_id,
        capability_id=capability_id,
        model_visible_backend_id=model_visible_backend_id,
        owner_module=owner_module,
        owner_symbol=owner_symbol,
        backend_candidates=backend_candidates,
        task_loop_reachable=True,
        proof_contract=proof_contract,
        replay_contract=replay_contract,
        limitations=("reachable from generic model-led task loop; not registered as a RuntimeHost product adapter",),
    )


def _real_browser_binding(browser_selection: BrowserBackendSelection) -> PowerSkillBackendBinding:
    return PowerSkillBackendBinding(
        skill_id="real_browser_control",
        capability_id="real_browser_control",
        model_visible_backend_id=browser_selection.model_visible_backend_id,
        preferred_backend_id=browser_selection.preferred_backend_id,
        compatibility_backend_id=browser_selection.compatibility_backend_id,
        runtime_connection_id="real_browser_control",
        owner_module="sentinel.operator.real_browser_control_runtime",
        owner_symbol="RealBrowserControlRuntime",
        organ_refs=("BrowserSessionManagerL5Live", "CloakBrowser", "BrowserWorldModelBuilder"),
        backend_candidates=tuple(candidate.backend_id for candidate in browser_selection.candidates),
        product_reachable=True,
        task_loop_reachable=True,
        proof_contract="RealBrowserActionReceipt",
        replay_contract="RealBrowserControlReplayView no-reopen/no-reclick/no-retype deltas",
        limitations=(
            "model-visible backend is browser_skill; low-level Playwright refs remain internal",
            browser_selection.selection_reason,
        ),
    )


def _locked_binding(
    *,
    skill_id: str,
    capability_id: str,
    owner_module: str,
    lock_reason: str,
) -> PowerSkillBackendBinding:
    return PowerSkillBackendBinding(
        skill_id=skill_id,
        capability_id=capability_id,
        model_visible_backend_id=f"{skill_id}_locked",
        owner_module=owner_module,
        backend_candidates=(),
        locked=True,
        lock_reason=lock_reason,
        proof_contract="future_pack_required",
        replay_contract="not_dispatchable",
    )


def _skill_id_for_action(actionability: ActionabilityRegistry, canonical_action_name: str) -> str | None:
    for descriptor in actionability.descriptors:
        if canonical_action_name in descriptor.action_names():
            return descriptor.skill_id
    return None


def _with_organ_metadata(
    binding: PowerSkillBackendBinding,
    *,
    organ_registry: OrganSpecRegistry,
) -> PowerSkillBackendBinding:
    specs = [
        spec
        for spec in organ_registry.list_specs()
        if spec.skill_binding in _organ_skill_bindings(binding.skill_id)
    ]
    if not specs:
        return binding

    return binding.model_copy(
        update={
            "organ_spec_refs": _dedupe(spec.organ_id for spec in specs),
            "organ_receipt_kinds": _dedupe(spec.receipt_kind for spec in specs),
            "organ_proof_requirements": _dedupe(
                requirement
                for spec in specs
                for requirement in spec.proof_requirements
            ),
            "organ_replay_expectations": _dedupe(
                expectation
                for spec in specs
                for expectation in spec.replay_expectations
            ),
            "organ_recoverable_failure_classes": _dedupe(
                failure_class
                for spec in specs
                for failure_class in spec.recoverable_failure_classes
            ),
            "organ_hard_stop_categories": _dedupe(
                category
                for spec in specs
                for category in spec.hard_stop_categories
            ),
        }
    )


def _organ_skill_bindings(skill_id: str) -> tuple[str, ...]:
    if skill_id == "real_browser_control":
        return ("browser_control",)
    return (skill_id,)


def _dedupe(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


__all__ = [
    "PowerSkillBackendBinding",
    "PowerSkillBackendFrame",
    "PowerSkillRegistry",
    "build_default_power_skill_registry",
]
