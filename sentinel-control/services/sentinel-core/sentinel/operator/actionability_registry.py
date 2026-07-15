from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.action_power_contract import ActionAliasNormalizer
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class ActionExposureStatus(StrEnum):
    EXECUTABLE = "executable"
    HIDDEN_INTERNAL = "hidden_internal"
    LOCKED = "locked"
    MISSING_AUTHORITY = "missing_authority"
    NOT_REGISTERED = "not_registered"


class PowerSkillDescriptor(SentinelModel):
    skill_id: str
    capability_id: str
    model_visible_actions: tuple[str, ...] = Field(default_factory=tuple)
    internal_actions: tuple[str, ...] = Field(default_factory=tuple)
    aliases: dict[str, str] = Field(default_factory=dict)
    proof_requirement: str
    recovery_policy: str
    product_dispatchable: bool = False
    locked: bool = False
    lock_reason: str = ""
    hard_stop_boundaries: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _descriptor_is_map_not_power(self) -> "PowerSkillDescriptor":
        assert_data_not_authority(
            context="power_skill_descriptor",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.locked and not self.hard_stop_boundaries:
            raise ValueError("locked skills must name hard stop boundaries")
        return self

    def action_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.model_visible_actions, *self.internal_actions, *self.aliases)))


class ActionExposure(SentinelModel):
    action_name: str
    canonical_action_name: str
    skill_id: str
    capability_id: str
    operation: str
    status: ActionExposureStatus
    proof_requirement: str
    recovery_policy: str
    reason: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _exposure_is_data_only(self) -> "ActionExposure":
        assert_data_not_authority(
            context="action_exposure",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class SkillExposure(SentinelModel):
    skill_id: str
    capability_id: str
    status: ActionExposureStatus
    lock_reason: str = ""
    hard_stop_boundaries: tuple[str, ...] = Field(default_factory=tuple)
    proof_requirement: str
    recovery_policy: str
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _skill_exposure_is_data_only(self) -> "SkillExposure":
        assert_data_not_authority(
            context="skill_exposure",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class ActionabilityRegistryFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("skill_exposure_frame"))
    model_visible_actions: tuple[ActionExposure, ...] = Field(default_factory=tuple)
    hidden_internal_actions: tuple[ActionExposure, ...] = Field(default_factory=tuple)
    missing_authority_actions: tuple[ActionExposure, ...] = Field(default_factory=tuple)
    not_registered_actions: tuple[ActionExposure, ...] = Field(default_factory=tuple)
    locked_skills: tuple[SkillExposure, ...] = Field(default_factory=tuple)
    invariant: str = "model_visible_actions_require_executor_authority_proof_and_recovery_policy"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _frame_is_data_only(self) -> "ActionabilityRegistryFrame":
        assert_data_not_authority(
            context="actionability_registry_frame",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ActionabilityRegistry:
    def __init__(self, descriptors: tuple[PowerSkillDescriptor, ...]) -> None:
        self._descriptors = tuple(descriptors)
        self._normalizer = ActionAliasNormalizer()
        self._alias_map: dict[str, str] = {}
        for descriptor in self._descriptors:
            for alias, canonical in descriptor.aliases.items():
                self._alias_map[alias] = canonical

    @property
    def descriptors(self) -> tuple[PowerSkillDescriptor, ...]:
        return self._descriptors

    def normalize_action_name(self, action_name: str) -> str:
        if action_name in self._alias_map:
            return self._alias_map[action_name]
        normalized = self._normalizer.normalize_action_name(action_name)
        return self._alias_map.get(normalized, normalized)

    def compile_frame(
        self,
        *,
        available_actions: tuple[str, ...],
        granted_capabilities: tuple[str, ...] = (),
    ) -> ActionabilityRegistryFrame:
        granted = set(granted_capabilities)
        model_visible: list[ActionExposure] = []
        hidden_internal: list[ActionExposure] = []
        missing_authority: list[ActionExposure] = []
        not_registered: list[ActionExposure] = []
        locked: dict[str, SkillExposure] = {}

        for action_name in available_actions:
            canonical = self.normalize_action_name(action_name)
            descriptor = self._descriptor_for_action(canonical)
            if descriptor is None:
                not_registered.append(
                    _unknown_exposure(
                        action_name=action_name,
                        canonical_action_name=canonical,
                        status=ActionExposureStatus.NOT_REGISTERED,
                        reason="no_power_skill_descriptor",
                    )
                )
                continue
            if descriptor.locked:
                locked.setdefault(descriptor.skill_id, _locked_skill_exposure(descriptor))
                continue
            if granted and descriptor.capability_id not in granted and descriptor.skill_id not in granted:
                missing_authority.append(
                    _action_exposure(
                        descriptor=descriptor,
                        action_name=action_name,
                        canonical_action_name=canonical,
                        status=ActionExposureStatus.MISSING_AUTHORITY,
                        reason="capability_not_in_mission_authority",
                    )
                )
                continue
            if canonical in descriptor.model_visible_actions:
                model_visible.append(
                    _action_exposure(
                        descriptor=descriptor,
                        action_name=canonical,
                        canonical_action_name=canonical,
                        status=ActionExposureStatus.EXECUTABLE,
                    )
                )
                continue
            hidden_internal.append(
                _action_exposure(
                    descriptor=descriptor,
                    action_name=canonical,
                    canonical_action_name=canonical,
                    status=ActionExposureStatus.HIDDEN_INTERNAL,
                    reason="runtime_primitive_not_model_facing_skill",
                )
            )

        return ActionabilityRegistryFrame(
            model_visible_actions=tuple(_dedupe_exposures(model_visible)),
            hidden_internal_actions=tuple(_dedupe_exposures(hidden_internal)),
            missing_authority_actions=tuple(_dedupe_exposures(missing_authority)),
            not_registered_actions=tuple(_dedupe_exposures(not_registered)),
            locked_skills=tuple(locked.values()),
        )

    def _descriptor_for_action(self, canonical_action_name: str) -> PowerSkillDescriptor | None:
        for descriptor in self._descriptors:
            if canonical_action_name in descriptor.model_visible_actions or canonical_action_name in descriptor.internal_actions:
                return descriptor
        return None


def build_default_actionability_registry() -> ActionabilityRegistry:
    return ActionabilityRegistry(
        descriptors=(
            PowerSkillDescriptor(
                skill_id="sentinel_loop",
                capability_id="sentinel_loop",
                model_visible_actions=("sentinel_loop.summarize_evidence", "sentinel_loop.finish"),
                aliases={
                    "summarize": "sentinel_loop.summarize_evidence",
                    "summarize_evidence": "sentinel_loop.summarize_evidence",
                    "finish": "sentinel_loop.finish",
                    "sentinel_finish.finish": "sentinel_loop.finish",
                },
                proof_requirement="objective_receipts_grounded_summary_or_budget_truth",
                recovery_policy="summary_before_finish_when_evidence_verified",
            ),
            PowerSkillDescriptor(
                skill_id="read_only_research",
                capability_id="read_only_research",
                model_visible_actions=(
                    "read_only_research.list_directory",
                    "read_only_research.search_text",
                    "read_only_research.read_file_segment",
                    "read_only_research.finish_exploration",
                ),
                aliases={
                    "read_only.list_directory": "read_only_research.list_directory",
                    "read_only.search_text": "read_only_research.search_text",
                    "read_only.read_file_segment": "read_only_research.read_file_segment",
                    "read_only.finish_exploration": "read_only_research.finish_exploration",
                },
                proof_requirement="read_only_observation_receipt",
                recovery_policy="recover_path_ref_query_or_context",
                product_dispatchable=True,
            ),
            PowerSkillDescriptor(
                skill_id="workspace_patch",
                capability_id="workspace_patch",
                model_visible_actions=("workspace_patch.apply_patch", "workspace_patch.run_bounded_check"),
                proof_requirement="workspace_patch_or_check_receipt",
                recovery_policy="recover_patch_target_or_check_context",
            ),
            PowerSkillDescriptor(
                skill_id="code_execution_sandbox",
                capability_id="code_execution_sandbox",
                model_visible_actions=(
                    "code_execution_sandbox.code_exec.run_profile",
                    "code_execution_sandbox.code_exec.inspect_result",
                ),
                aliases={
                    "code_exec.run_profile": "code_execution_sandbox.code_exec.run_profile",
                    "code_exec.inspect_result": "code_execution_sandbox.code_exec.inspect_result",
                    "code_execution_sandbox.run_profile": "code_execution_sandbox.code_exec.run_profile",
                    "code_execution_sandbox.inspect_result": "code_execution_sandbox.code_exec.inspect_result",
                },
                proof_requirement="sandbox_execution_receipt",
                recovery_policy="recover_profile_or_bounded_check_context",
            ),
            PowerSkillDescriptor(
                skill_id="bounded_channel",
                capability_id="bounded_channel",
                model_visible_actions=("bounded_channel.send_message",),
                aliases={
                    "channel.send_message": "bounded_channel.send_message",
                    "channel_transport.send_message": "bounded_channel.send_message",
                },
                proof_requirement="delivery_receipt_and_no_resend_replay",
                recovery_policy="recover_destination_or_message_context",
            ),
            PowerSkillDescriptor(
                skill_id="worker_fleet",
                capability_id="worker_fleet",
                model_visible_actions=("worker_fleet.spawn_worker",),
                aliases={
                    "spawn_worker": "worker_fleet.spawn_worker",
                    "delegate": "worker_fleet.spawn_worker",
                    "delegate_worker": "worker_fleet.spawn_worker",
                },
                proof_requirement="worker_spawn_receipt_and_child_authority_subset",
                recovery_policy="recover_worker_role_scope_or_budget_context",
            ),
            PowerSkillDescriptor(
                skill_id="browser_control",
                capability_id="browser_control",
                model_visible_actions=(
                    "browser_control.browser.observe",
                    "browser_control.browser.assert_text",
                ),
                internal_actions=(
                    "browser_control.browser.click",
                    "browser_control.browser.type_text",
                    "browser_control.browser.select_option",
                ),
                proof_requirement="browser_observation_or_action_receipt",
                recovery_policy="recover_ref_or_browser_fixture_state",
            ),
            PowerSkillDescriptor(
                skill_id="real_browser_control",
                capability_id="real_browser_control",
                model_visible_actions=(
                    "real_browser_control.real_browser.open",
                    "real_browser_control.real_browser.observe",
                    "real_browser_control.real_browser.search",
                    "real_browser_control.real_browser.inspect_result",
                    "real_browser_control.real_browser.open_result",
                    "real_browser_control.real_browser.extract_evidence",
                    "real_browser_control.real_browser.extract_entities",
                    "real_browser_control.real_browser.extract_product_cards",
                    "real_browser_control.real_browser.verify_extraction",
                    "real_browser_control.real_browser.extract_text",
                    "real_browser_control.real_browser.assert_text",
                ),
                internal_actions=(
                    "real_browser_control.real_browser.click",
                    "real_browser_control.real_browser.type_text",
                    "real_browser_control.real_browser.select_option",
                    "real_browser_control.real_browser.press_key",
                    "real_browser_control.real_browser.wait_for_text",
                    "real_browser_control.real_browser.wait_for_load",
                    "real_browser_control.real_browser.scroll",
                ),
                aliases={
                    "real_browser.open": "real_browser_control.real_browser.open",
                    "real_browser.observe": "real_browser_control.real_browser.observe",
                    "real_browser.search": "real_browser_control.real_browser.search",
                    "real_browser.inspect_result": "real_browser_control.real_browser.inspect_result",
                    "real_browser.open_result": "real_browser_control.real_browser.open_result",
                    "real_browser.extract_evidence": "real_browser_control.real_browser.extract_evidence",
                    "real_browser.extract_entities": "real_browser_control.real_browser.extract_entities",
                    "real_browser.extract_product_cards": "real_browser_control.real_browser.extract_product_cards",
                    "real_browser.verify_extraction": "real_browser_control.real_browser.verify_extraction",
                    "real_browser.extract_text": "real_browser_control.real_browser.extract_text",
                    "real_browser.assert_text": "real_browser_control.real_browser.assert_text",
                    "real_browser.click": "real_browser_control.real_browser.click",
                    "real_browser.type_text": "real_browser_control.real_browser.type_text",
                    "real_browser.select_option": "real_browser_control.real_browser.select_option",
                    "real_browser.press_key": "real_browser_control.real_browser.press_key",
                    "real_browser.wait_for_text": "real_browser_control.real_browser.wait_for_text",
                    "real_browser.wait_for_load": "real_browser_control.real_browser.wait_for_load",
                    "real_browser.scroll": "real_browser_control.real_browser.scroll",
                },
                proof_requirement="browser_action_or_extraction_receipt",
                recovery_policy="recover_ref_actuation_world_model_or_dynamic_loading",
            ),
            _locked_skill(
                skill_id="external_api",
                capability_id="external_api",
                lock_reason="external API execution requires explicit backend, credential lease, and authority envelope",
                hard_stop_boundaries=("ungranted_network", "credential_access", "external_write"),
            ),
            _locked_skill(
                skill_id="desktop_control",
                capability_id="desktop_control",
                lock_reason="desktop action is not product-dispatchable from the generic loop",
                hard_stop_boundaries=("desktop_escape", "credential_access", "destructive_local_action"),
                aliases={"desktop.click": "desktop_control.click"},
            ),
            _locked_skill(
                skill_id="voice_runtime",
                capability_id="voice_runtime",
                lock_reason="voice runtime is not product-dispatchable from the generic loop",
                hard_stop_boundaries=("external_message", "identity_confusion", "recording_or_secret_leak"),
            ),
            _locked_skill(
                skill_id="account_authority",
                capability_id="account_authority",
                lock_reason="account authority cannot be granted by model action",
                hard_stop_boundaries=("authority_escalation", "credential_access", "account_mutation"),
            ),
            _locked_skill(
                skill_id="financial_authority",
                capability_id="financial_authority",
                lock_reason="financial authority requires special explicit grants outside the generic loop",
                hard_stop_boundaries=("payment", "checkout", "funds_transfer"),
            ),
            _locked_skill(
                skill_id="payment_authority",
                capability_id="payment_authority",
                lock_reason="payment and checkout remain hard-stopped",
                hard_stop_boundaries=("payment", "checkout", "irreversible_purchase"),
                aliases={"payment.submit": "payment_authority.submit"},
            ),
        )
    )


def _locked_skill(
    *,
    skill_id: str,
    capability_id: str,
    lock_reason: str,
    hard_stop_boundaries: tuple[str, ...],
    aliases: dict[str, str] | None = None,
) -> PowerSkillDescriptor:
    return PowerSkillDescriptor(
        skill_id=skill_id,
        capability_id=capability_id,
        model_visible_actions=(
            f"{capability_id}.call",
            f"{capability_id}.click",
            f"{capability_id}.grant",
            f"{capability_id}.submit",
        ),
        proof_requirement="explicit_future_pack_required",
        recovery_policy="hard_stop_until_authorized_runtime_exists",
        aliases=aliases or {},
        locked=True,
        lock_reason=lock_reason,
        hard_stop_boundaries=hard_stop_boundaries,
    )


def _action_exposure(
    *,
    descriptor: PowerSkillDescriptor,
    action_name: str,
    canonical_action_name: str,
    status: ActionExposureStatus,
    reason: str = "",
) -> ActionExposure:
    operation = _operation_from_canonical(canonical_action_name, descriptor.capability_id)
    return ActionExposure(
        action_name=action_name,
        canonical_action_name=canonical_action_name,
        skill_id=descriptor.skill_id,
        capability_id=descriptor.capability_id,
        operation=operation,
        status=status,
        proof_requirement=descriptor.proof_requirement,
        recovery_policy=descriptor.recovery_policy,
        reason=reason,
    )


def _unknown_exposure(
    *,
    action_name: str,
    canonical_action_name: str,
    status: ActionExposureStatus,
    reason: str,
) -> ActionExposure:
    capability_id, operation = canonical_action_name.split(".", 1) if "." in canonical_action_name else (canonical_action_name, "")
    return ActionExposure(
        action_name=action_name,
        canonical_action_name=canonical_action_name,
        skill_id="unknown",
        capability_id=capability_id,
        operation=operation,
        status=status,
        proof_requirement="unknown",
        recovery_policy="do_not_show_to_model_until_registered",
        reason=reason,
    )


def _locked_skill_exposure(descriptor: PowerSkillDescriptor) -> SkillExposure:
    return SkillExposure(
        skill_id=descriptor.skill_id,
        capability_id=descriptor.capability_id,
        status=ActionExposureStatus.LOCKED,
        lock_reason=descriptor.lock_reason,
        hard_stop_boundaries=descriptor.hard_stop_boundaries,
        proof_requirement=descriptor.proof_requirement,
        recovery_policy=descriptor.recovery_policy,
    )


def _operation_from_canonical(canonical_action_name: str, capability_id: str) -> str:
    prefix = f"{capability_id}."
    if canonical_action_name.startswith(prefix):
        return canonical_action_name[len(prefix):]
    return canonical_action_name


def _dedupe_exposures(exposures: list[ActionExposure]) -> list[ActionExposure]:
    seen: set[str] = set()
    deduped: list[ActionExposure] = []
    for exposure in exposures:
        key = f"{exposure.status.value}:{exposure.canonical_action_name}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(exposure)
    return deduped


__all__ = [
    "ActionExposure",
    "ActionExposureStatus",
    "ActionabilityRegistry",
    "ActionabilityRegistryFrame",
    "PowerSkillDescriptor",
    "SkillExposure",
    "build_default_actionability_registry",
]
