from __future__ import annotations

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.organ_dispatch import _resolve_runtime_organ_kind
from sentinel.agent.organs.organ_spec_registry import default_organ_spec_registry
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)


def test_organ_spec_registry_replaces_browser_branch_lookup() -> None:
    registry = default_organ_spec_registry()

    resolved = _resolve_runtime_organ_kind(
        organ_kind=OrganProposalKind.BROWSER,
        action_level=DelegatedActionLevel.L5,
        raw_candidate={"browser_organ_kind": "browser_session_manager_l5_live"},
        organ_contracts={},
        gate_result=None,
    )

    spec = registry.require("browser_session_manager")
    assert resolved == spec.organ_id
    assert spec.backend_kind == "cloakbrowser"
    assert spec.skill_binding == "browser_control"


def test_runtime_execution_uses_spec_for_known_organ() -> None:
    registry = default_organ_spec_registry()
    spec = registry.require("browser_session_manager")
    config = OrganRuntimeExecutionConfig(
        enabled=True,
        mode=OrganRuntimeExecutionMode.BROWSER_LIVE_OPERATOR_ONLY,
        allowed_action_levels=[DelegatedActionLevel.L5],
        allowed_organs=[spec.organ_id],
        allow_l2=False,
        allow_l3=False,
        allow_browser_live_operator=True,
        deny_browser=False,
        deny_network=False,
    )

    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id="mission_pack_e_runtime_known",
            action_level=DelegatedActionLevel.L5,
            organ_kind=spec.organ_id,
        ),
        config=config,
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "mission_authority_envelope_missing"
    assert result.executor_result_summary["organ_spec_id"] == spec.organ_id
    assert result.executor_result_summary["runtime_handler"] == spec.runtime_handler


def test_unknown_organ_blocks_honestly() -> None:
    config = OrganRuntimeExecutionConfig(
        enabled=True,
        mode=OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
        allowed_action_levels=[DelegatedActionLevel.L4],
        allowed_organs=["browser_readonly"],
        allow_l2=False,
        allow_l3=False,
        allow_browser_readonly=True,
    )

    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id="mission_pack_e_unknown",
            action_level=DelegatedActionLevel.L4,
            organ_kind="browser_unknown_parallel_stack",
        ),
        config=config,
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unknown_organ_not_registered"
    assert result.executor_result_summary["organ_spec_id"] is None


def test_receipt_and_finalgate_requirements_preserved() -> None:
    registry = default_organ_spec_registry()
    readonly = registry.require("browser_readonly")
    session = registry.require("browser_session_manager")

    assert readonly.receipt_kind == "browser_readonly_receipt"
    assert "browser_readonly_finalgate" in readonly.proof_requirements
    assert "no_mutation" in readonly.replay_expectations
    assert session.receipt_kind == "browser_session_receipt"
    assert "browser_session_finalgate" in session.proof_requirements
    assert "no_reopen_no_reclick_no_retype" in session.replay_expectations


def test_no_new_high_risk_surface_dispatchable_by_default() -> None:
    registry = default_organ_spec_registry()
    high_risk_organs = [
        spec for spec in registry.list_specs()
        if spec.authority_level in {"L6", "L7"} or spec.hard_stop_categories
    ]

    assert high_risk_organs
    for spec in high_risk_organs:
        assert spec.default_dispatchable is False
        assert spec.locked_reason


def test_skill_binding_metadata_available_for_decision_context() -> None:
    registry = default_organ_spec_registry()

    assert registry.require("local_artifact").skill_binding == "local_artifact"
    assert registry.require("reversible_workspace").skill_binding == "workspace_patch"
    assert registry.require("browser_session_manager").skill_binding == "browser_control"
    assert registry.require("browser_semantic_extraction").skill_binding == "browser_control"


def test_recoverable_and_hard_stop_metadata_available_from_spec() -> None:
    registry = default_organ_spec_registry()
    browser_session = registry.require("browser_session_manager")
    login = registry.require("browser_login_credential_session_broker")

    assert "locator_timeout" in browser_session.recoverable_failure_classes
    assert "stale_ref" in browser_session.recoverable_failure_classes
    assert "credential_access" in login.hard_stop_categories
    assert "login_session" in login.hard_stop_categories


def test_safe_external_registry_export_names_specs_without_execution_power() -> None:
    from sentinel.organs.registry import runtime_organ_spec_safe_export

    export = runtime_organ_spec_safe_export()
    browser_session = next(item for item in export if item["organ_id"] == "browser_session_manager")

    assert browser_session["backend_kind"] == "cloakbrowser"
    assert browser_session["registry_can_execute"] is False
    assert browser_session["can_grant_authority"] is False
    assert all("credential_value" not in item for item in export)
