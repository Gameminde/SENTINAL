from __future__ import annotations

import json
import hashlib
import inspect
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel import cli
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.canonical_core import (
    CanonicalCapabilityRoute,
    CanonicalDecision,
    CanonicalCoreError,
    CanonicalDecisionRequest,
    DecisionOrigin,
    DecisionProtocol,
    EffectKind,
    ExecutableCapabilityGraph,
    RootMissionRuntime,
    RootMissionCancellationToken,
    build_workspace_browser_readonly_capability_graph,
    build_workspace_read_capability_graph,
    run_canonical_dev_mission,
    run_canonical_product_mission,
)
from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
from sentinel.operator.product_model_native_decision_client import ProductModelNativeDecisionClient
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.code_execution_sandbox_runtime import CodeExecutionSandboxRuntime
from sentinel.operator.kernel import MissionKernel


class ScriptedModelClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("scripted model decision exhausted")
        return self._decisions.pop(0)


class CancellingModelClient:
    def __init__(self, token: RootMissionCancellationToken, decision: dict[str, Any]) -> None:
        self._token = token
        self._decision = decision
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        self._token.cancel("operator_revoked_during_provider_turn")
        return self._decision


class FailingModelClient:
    def complete(self, request: Any) -> dict[str, Any]:
        raise CanonicalCoreError("canonical_provider_decision_json_missing")


class RaisingDispatchModelClient:
    def complete(self, request: Any) -> dict[str, Any]:
        return {"capability": "workspace", "operation": "read", "arguments": {"path": "missing.md"}}


class NarrativeThenDecisionModelClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if len(self.requests) == 1:
            raise ActionKernelError("CANONICAL_DECISION_TRANSPORT_REJECTED:narrative_only_response")
        if len(self.requests) == 2:
            return {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}}
        return {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Needle found."}}


def _ledger_closure_gate_violations(entry: dict[str, Any]) -> list[str]:
    status = entry.get("status")
    violations: list[str] = []
    if status == "FIXED_PROVEN":
        for field in (
            "fixed_proven_commit",
            "acceptance_probe",
            "integration_or_live_probe",
            "proof_artifacts",
            "responsible_files_symbols",
        ):
            if not entry.get(field):
                violations.append(field)
    if status == "SUPERSEDED_BY_CANONICAL_REPLACEMENT":
        for field in (
            "canonical_replacement_gate",
            "callers_migrated_proof",
            "absence_of_bypass_probe",
            "implementation_commits",
            "deletion_commits",
            "proof_commits",
            "superseded_commit",
        ):
            if not entry.get(field):
                violations.append(field)
    return violations


def test_stage0_finding_ledger_contains_all_65_findings() -> None:
    ledger_path = (
        Path(__file__).parents[4]
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json"
    )

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert ledger["baseline_commit"] == "efdbd558abddbc38cea7e506ff8cb8dfe8ef93fa"
    assert len(ledger["entries"]) == 65
    assert len({entry["id"] for entry in ledger["entries"]}) == 65
    assert ledger["severity_counts"] == {"P0": 15, "P1": 44, "P2": 6}
    c2_truth = ledger["single_spine_c2_workspace_compression"]
    assert c2_truth["code_head"] == "fa5f51bf8145f63d24fe83742719d1e0d45349e6"
    assert c2_truth["c2_implementation_tested_head_preserved"] == c2_truth["code_head"]
    assert c2_truth["c2_published_documentation_head_preserved"] == (
        "7480f31132ec2b20262d7465905f4fb8275139a3"
    )
    c3_truth = ledger["single_spine_c3_product_loop_decision_client_compression"]
    c4_truth = ledger["single_spine_c4_browser_readonly_cutover"]
    c4s_truth = ledger["single_spine_c4s_browser_readonly_proof_seal"]
    c5a_repair_truth = ledger["single_spine_c5a_timeout_containment_repair"]
    c5a_target_truth = ledger["single_spine_c5a_target_closed_root_cause"]
    assert ledger["current_head"] == c5a_target_truth["attestation_head"]
    assert ledger["current_worktree_or_commit"] == c5a_target_truth["attestation_head"]
    assert ledger["proof_runtime_head"] == c5a_target_truth["attestation_head"]
    assert ledger["implementation_tested_head"] == c5a_target_truth["attestation_head"]
    entries = ledger["entries"]
    status_counts = dict(sorted(Counter(entry["status"] for entry in entries).items()))
    proof_tier_counts = dict(sorted(Counter(entry["proof_tier"] for entry in entries).items()))
    fixed_entries = [entry for entry in entries if entry["status"] == "FIXED_PROVEN"]
    assert ledger["fixed_proven_count"] == len(fixed_entries) == 0
    assert ledger["status_counts"] == status_counts == {"CONFIRMED_CURRENT": 9, "IMPLEMENTING": 8, "OPEN": 48}
    assert ledger["proof_tier_counts"] == proof_tier_counts
    assert ledger["fixed_proven_by_severity"] == {"P0": 0, "P1": 0, "P2": 0}
    assert c3_truth["implementation_head_before_report"] in ledger["ledger_commit_classes"]["implementation_commits"]
    assert c3_truth["implementation_head_before_report"] in ledger["ledger_commit_classes"]["ledger_commits"]
    assert c3_truth["provider_calls"] == 0
    assert c3_truth["browser_runs"] == 0
    assert c3_truth["remaining_open_truth"]["FIXED_PROVEN"] == "0/65"
    assert c3_truth["remaining_open_truth"]["C-P1-17"] == "IMPLEMENTING"
    assert c3_truth["remaining_open_truth"]["P0-07"] == "IMPLEMENTING"
    assert c4_truth["provider_calls"] == 0
    assert c4_truth["browser_runs"] == 0
    assert c4_truth["real_browser_runs"] == 0
    assert c4_truth["external_network_calls"] == 0
    assert c4_truth["fixed_proven_count"] == 0
    assert c4_truth["gates"]["browser_effect_dispatch_owner"] == "ProductActionKernel"
    assert c4_truth["gates"]["canonical_browser_public_bypass"] is False
    assert c4_truth["gates"]["physical_browser_boundaries"] == "NOT_RUN"
    assert c4_truth["remaining_open_truth"]["P0-04"] == "CONFIRMED_CURRENT_PHYSICAL_BROWSER_NOT_REPAIRED_BY_FAKE_C4_ROUTE"
    assert c4_truth["implementation_head_before_report"] in ledger["ledger_commit_classes"]["implementation_commits"]
    assert c4_truth["implementation_head_before_report"] in ledger["ledger_commit_classes"]["ledger_commits"]
    assert c4s_truth["status"] == "C4_BROWSER_READONLY_PROOF_SEALED_LOCAL"
    assert c4s_truth["fixed_proven_count"] == 0
    assert c4s_truth["provider_calls"] == 0
    assert c4s_truth["browser_runs"] == 0
    assert c4s_truth["implementation_tested_head"] == c4_truth["implementation_head_before_report"]
    assert c4s_truth["published_remote_head_before_seal"] == "dfa4479af31349f10932691da38ef771e8a74519"
    assert c4s_truth["proof_artifacts"] == c4_truth["proof_artifacts"]
    assert all(item["status"] in {"PASSED", "UNAVAILABLE"} for item in c4s_truth["validation_results"])
    assert c5a_repair_truth["status"] == (
        "TIMEOUT_CONTAINMENT_REPAIRED_LOCAL_WITH_HISTORICAL_NEXT_BLOCKER_NOT_REPRODUCED"
    )
    assert c5a_repair_truth["provider_calls"] == 0
    assert c5a_repair_truth["browser_runs"] == 0
    assert c5a_repair_truth["live_probe_after_repair"]["ready"] is False
    assert c5a_repair_truth["live_probe_after_repair"]["attempts"] == 3
    assert c5a_repair_truth["live_probe_after_repair"]["timeout_reproduced_after_repair"] is False
    assert c5a_repair_truth["live_probe_after_repair"]["attempt_3_first_failure"] == "cloak_open_context:TargetClosedError:new_process_launch"
    assert c5a_repair_truth["live_probe_after_repair"]["followup_status"] == (
        "PRIOR_TARGET_CLOSED_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE"
    )
    assert c5a_repair_truth["live_probe_after_repair"]["followup_ready_count"] == 3
    assert c5a_repair_truth["deterministic_gates"]["owned_child_process_boundary"] is True
    assert c5a_repair_truth["deterministic_gates"]["late_publication_blocked"] is True
    assert c5a_repair_truth["deterministic_gates"]["cleanup_failure_visible"] is True
    assert c5a_target_truth["status"] == "PRIOR_TARGET_CLOSED_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE"
    assert c5a_target_truth["provider_calls"] == 0
    assert c5a_target_truth["sqlite_mission"] == "NOT_RUN"
    assert c5a_target_truth["c5b"] == "NOT_STARTED"
    assert c5a_target_truth["root_cause_proven"] is False
    assert c5a_target_truth["deterministic_gates"]["new_process_launch_failure_terminalized"] is True
    assert c5a_target_truth["deterministic_gates"]["context_creation_failure_terminalized"] is True
    assert c5a_target_truth["deterministic_gates"]["backend_selected_truth_on_pre_receipt_failure"] is True
    assert c5a_target_truth["deterministic_gates"]["receipt_backend_match_not_claimed_before_receipt"] is True
    assert c5a_target_truth["live_probe_after_instrumentation"]["attempts"] == 3
    assert c5a_target_truth["live_probe_after_instrumentation"]["ready_count"] == 3
    assert c5a_target_truth["live_probe_after_instrumentation"]["all_ready"] is True
    assert c5a_target_truth["live_probe_after_instrumentation"]["context_operational"] is True
    assert c5a_target_truth["live_probe_after_instrumentation"]["page_operational"] is True
    assert c5a_target_truth["live_probe_after_instrumentation"]["read_only_observation"] is True
    assert c5a_target_truth["live_probe_after_instrumentation"]["cleanup_success_count"] == 3
    assert c5a_target_truth["live_probe_after_instrumentation"]["profile_material_persisted_count"] == 0
    assert c5a_target_truth["live_probe_after_instrumentation"]["target_closed_reproduced"] is False
    assert (c5a_truth := ledger["single_spine_c5a_physical_browser_boundary"])
    assert c5a_truth["live_cloak_readiness"] == "READY_3_OF_3_AFTER_TARGET_CLOSED_WAVE"
    assert c5a_truth["status"] == "PHYSICAL_BROWSER_BOUNDARY_ADAPTER_LOCAL_PLUS_LIVE_READINESS_READY_3_OF_3"
    assert c5a_truth["latest_pushed_head_before_c5a_root_cause"] == (
        "fb3561f1bfdaee7a004a3bddacf8c39cbd8f057f"
    )
    assert c5a_truth["product_browser_missions"] == 0
    assert c5a_truth["live_cloak_readiness_probes"] == 3
    assert c5a_truth["live_cloak_runs"] == "3_LIVE_CLOAK_READINESS_PROBES"
    assert c5a_truth["remaining_open_truth"]["Browser physical/Cloak live proof"] == (
        "C5A_LIVE_READINESS_READY_3_OF_3_CONTEXT_PAGE_OBSERVE_CLEANUP"
    )
    assert c5a_truth["remaining_open_truth"]["readiness timeout root cause"] == (
        "ROOT_CAUSE_PROVEN_TIMEOUT_CONTAINMENT_RACE_REPAIRED_LOCAL"
    )
    assert c5a_truth["remaining_open_truth"]["new process TargetClosedError"] == (
        "PRIOR_BLOCKER_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE"
    )
    assert "b4f4baaceb6deb38f038a81321eb81d3ad21723b" in ledger["ledger_commit_classes"]["deletion_commits"]
    assert "4c587859eee9ddda5c356572549153137373f695" in ledger["ledger_commit_classes"]["ledger_commits"]
    assert "fe28a144445168aa75bc3f9c02e1e4626466e5db" in ledger["ledger_commit_classes"]["proof_commits"]
    assert c5a_repair_truth["source_head_before_repair"] in ledger["ledger_commit_classes"]["implementation_commits"]
    assert c5a_repair_truth["attestation_head"] in ledger["ledger_commit_classes"]["ledger_commits"]
    assert c5a_target_truth["source_head_before_wave"] in ledger["ledger_commit_classes"]["implementation_commits"]
    assert c5a_target_truth["attestation_head"] in ledger["ledger_commit_classes"]["ledger_commits"]
    assert c2_truth["c2s_seal_commit"] in ledger["ledger_commit_classes"]["implementation_commits"]
    assert c2_truth["c2s_seal_commit"] in ledger["ledger_commit_classes"]["ledger_commits"]
    slice_ids = [item["slice_id"] for item in ledger["methodological_reconciliation"]["slices"]]
    assert slice_ids[:3] == [
        "SLICE_0A_STAGE0_LEDGER_AND_LOCAL_VERTICAL_SKELETON",
        "SLICE_0B_ROOT_CANCELLATION_SEAM",
        "SLICE_0C_CODE_SANDBOX_PHYSICAL_BOUNDARY_PROBE_AND_QUARANTINE",
    ]
    assert "SLICE_0E_KERNEL_BACKED_PRODUCT_ROUTE_PROVIDER_AUTH_BLOCKED" in slice_ids
    by_id = {entry["id"]: entry for entry in entries}
    assert by_id["P0-01"]["status"] == "IMPLEMENTING"
    assert by_id["P0-02"]["status"] == "CONFIRMED_CURRENT"
    assert by_id["P0-02"]["chosen_invariant"] == "do_not_expose_unproven_code_exec_as_canonical_power"
    assert by_id["P0-03"]["status"] == "IMPLEMENTING"
    assert by_id["P0-07"]["status"] == "IMPLEMENTING"
    assert by_id["P0-08"]["status"] == "CONFIRMED_CURRENT"
    assert by_id["C-P0-01"]["status"] == "IMPLEMENTING"
    assert by_id["C-P0-06"]["status"] == "IMPLEMENTING"
    assert by_id["P1-25"]["status"] == "IMPLEMENTING"
    tranche = ledger["canonical_core_vertical_product_tranche"]
    assert tranche["status"] == "T3_REAL_MODEL_CANONICAL_SLICE_PROVEN_BUT_P0_01_NOT_CLOSED"
    assert tranche["checkpoint_head"] == "fe28a144445168aa75bc3f9c02e1e4626466e5db"
    assert tranche["tested_runtime_head"] == "b721ce62343316bcdbe9c792af8a0967c8ae1680"
    assert tranche["attestation_head"] == "fe28a144445168aa75bc3f9c02e1e4626466e5db"
    assert tranche["provider_failure_diagnosis"]["classification"] == "VALID_REAL_MODEL_CANONICAL_SLICE_PROVEN"
    assert tranche["p0_01_fixed_proven"] is False
    forbidden_credential_hash_prefix = "credential_" + "safe_hash"
    assert not any(key.startswith(forbidden_credential_hash_prefix) for key in tranche["provider_failure_diagnosis"])
    assert tranche["provider_authenticated"] is True
    assert tranche["model_native_decisions_accepted"] is True
    assert tranche["workspace_actions"] == 1
    assert tranche["model_selected_finish"] is True
    assert tranche["receipt_integrity_verified"] is True
    assert "explicit_provider_retries_after_0701297e" not in tranche
    assert {item["model_id"] for item in tranche["explicit_provider_attempts_after_checkpoint"]} == {
        "qwen-plus",
        "glm-5.2",
        "deepseek-v4-pro",
    }
    qwen_attempt = next(
        item
        for item in tranche["explicit_provider_attempts_after_checkpoint"]
        if item["attempt_id"] == "canonical_core_real_provider_v13_qwen_north_star_fixture_receipt_fixed"
    )
    assert qwen_attempt["model_native_decisions_accepted"] is True
    assert qwen_attempt["material_action_count"] == 1
    assert qwen_attempt["model_selected_finish"] is True
    assert qwen_attempt["receipt_artifacts_verified"] is True
    assert by_id["P0-01"]["fixed_proven_commit"] == ""
    assert by_id["C-P0-01"]["fixed_proven_commit"] == ""
    assert by_id["C-P0-06"]["fixed_proven_commit"] == ""
    assert by_id["P0-07"]["fixed_proven_commit"] == ""
    assert by_id["P0-01"]["temporary_bridge_status"] == "ROLLBACK_POINT_NOT_FINAL_ARCHITECTURE"
    assert by_id["P0-01"]["historical_acceptance_probe"] == [
        "public request",
        "ProductModelNativeDecisionClient",
        "legacy RuntimeHost task loop",
        "ProductActionKernel",
        "receipt",
    ]
    assert by_id["P0-01"]["canonical_replacement_gate"] == [
        "public request",
        "RuntimeHost",
        "RootMissionRuntime",
        "canonical model decision client",
        "ExecutableCapabilityGraph",
        "AuthorityKernel",
        "ProductActionKernel effect execution",
        "unique backend",
        "receipt/proof",
        "terminalization",
        "cleanup",
    ]
    assert "fe28a144445168aa75bc3f9c02e1e4626466e5db" in by_id["P0-01"]["slice_status_history"][-1]["head"]
    queue_by_id = {item["finding_id"]: item for item in ledger["fixed_proven_candidate_queue"]}
    assert queue_by_id["P0-01"]["candidate_reason"].startswith("C2 compressed the local workspace public route")
    assert "several executable cognitive spines still coexist" in queue_by_id["C-P0-01"]["candidate_reason"]
    assert "Workspace read/list/search tranche is proven" in queue_by_id["C-P0-06"]["candidate_reason"]
    assert "authenticity is still local/recomputable" in queue_by_id["P0-07"]["candidate_reason"]
    assert ledger["post_session_publication_truth"] == {
        "branch": "sentinel-dev-max-power-canonical-core-v1",
        "temporary_bridge_commit_published": "c08f6c9cf61daea71bef7913285ba4a6e94712c6",
        "documentation_checkpoint_published": "4c587859eee9ddda5c356572549153137373f695",
        "historical_reports_may_retain_push_pending": True,
        "appendix_required_when_historical_report_says_push_pending": True,
    }
    assert ledger["single_spine_compression_campaign"]["legacy_bridge_final_architecture"] is False
    assert ledger["single_spine_compression_campaign"]["no_finding_closure_in_c0_c1"] is True
    required_fields = {
        "target_wave",
        "depends_on",
        "status",
        "change_commits",
        "acceptance_probe",
        "integration_or_live_probe",
        "proof_artifacts",
        "fixed_proven_commit",
        "remaining_risk",
    }
    for entry in entries:
        assert required_fields <= set(entry), entry["id"]
        assert entry["target_wave"] in {"W1", "W2", "W3", "W4", "W5"}
        assert isinstance(entry["depends_on"], list)
        assert isinstance(entry["change_commits"], list)
        assert isinstance(entry["proof_artifacts"], list)
        assert isinstance(entry["fixed_proven_commit"], str)
        assert _ledger_closure_gate_violations(entry) == []
    assert ledger["published_counters_after_commit"] == {
        "checkpoint_commit": ledger["current_worktree_or_commit"],
        "P0 fixed / 15": "0/15",
        "P1 fixed / 44": "0/44",
        "P2 fixed / 6": "0/6",
        "total FIXED_PROVEN / 65": "0/65",
    }


def test_ledger_validator_rejects_fixed_or_superseded_without_required_proof_fields() -> None:
    incomplete_fixed = {
        "status": "FIXED_PROVEN",
        "fixed_proven_commit": "",
        "acceptance_probe": "unit only",
        "integration_or_live_probe": "",
        "proof_artifacts": [],
        "responsible_files_symbols": [],
    }
    incomplete_superseded = {
        "status": "SUPERSEDED_BY_CANONICAL_REPLACEMENT",
        "canonical_replacement_gate": [],
        "callers_migrated_proof": "",
        "absence_of_bypass_probe": "",
        "implementation_commits": [],
        "deletion_commits": [],
        "proof_commits": [],
        "superseded_commit": "",
    }
    valid_open = {
        "status": "IMPLEMENTING",
        "fixed_proven_commit": "",
    }

    assert set(_ledger_closure_gate_violations(incomplete_fixed)) == {
        "fixed_proven_commit",
        "integration_or_live_probe",
        "proof_artifacts",
        "responsible_files_symbols",
    }
    assert set(_ledger_closure_gate_violations(incomplete_superseded)) == {
        "canonical_replacement_gate",
        "callers_migrated_proof",
        "absence_of_bypass_probe",
        "implementation_commits",
        "deletion_commits",
        "proof_commits",
        "superseded_commit",
    }
    assert _ledger_closure_gate_violations(valid_open) == []


def test_provider_client_required_before_first_cognitive_turn(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(CanonicalCoreError, match="canonical_model_client_required"):
        run_canonical_dev_mission(
            objective="List the workspace.",
            workspace_root=workspace,
            model_client=None,
            provider_model="missing-provider",
        )


def test_product_missing_model_client_terminalizes_existing_mission_record(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    result = run_canonical_product_mission(
        objective="The product route must terminalize even without a model client.",
        workspace_root=workspace,
        model_client=None,
        provider_model="missing-provider",
        kernel=kernel,
        session_id="session_missing_client",
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)

    assert result.status == "blocked"
    assert result.final_reason == "MODEL_DECISION_FAILED"
    assert result.blocked_reason_detail == "canonical_model_client_required"
    assert result.cleanup_completed is True
    assert record.status is OperatorMissionStatus.BLOCKED
    assert any(event.event_type == "canonical_model_decision_failed" for event in events)
    assert any(event.event_type == "canonical_cleanup_completed" for event in events)


def test_root_cancellation_before_provider_call_blocks_without_decision(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    token = RootMissionCancellationToken()
    token.cancel("operator_revoked_before_provider_turn")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="This mission is revoked before the model sees state.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        cancellation_token=token,
    )

    assert result.status == "blocked"
    assert result.final_reason == "ROOT_MISSION_CANCELLED"
    assert result.cancellation_reason == "operator_revoked_before_provider_turn"
    assert result.provider_decision_count == 0
    assert result.material_action_count == 0
    assert result.cleanup_completed is True
    assert model.requests == []


def test_root_cancellation_during_model_turn_prevents_material_action(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    token = RootMissionCancellationToken()
    model = CancellingModelClient(
        token,
        {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
    )

    result = run_canonical_dev_mission(
        objective="This mission is revoked while the model is selecting an action.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        cancellation_token=token,
    )

    assert result.status == "blocked"
    assert result.final_reason == "ROOT_MISSION_CANCELLED"
    assert result.cancellation_reason == "operator_revoked_during_provider_turn"
    assert result.provider_decision_count == 1
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True


def test_root_mission_exists_before_first_model_decision_and_state_is_presented(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
            {"capability": "workspace", "operation": "read", "arguments": {"path": "notes/topic.md"}},
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Observed workspace evidence."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Understand the small workspace from files.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        max_provider_decisions=6,
        max_material_actions=6,
    )

    assert result.status == "completed"
    assert result.cleanup_completed is True
    assert result.root_mission_id.startswith("root_mission_")
    assert result.root_created_before_first_provider_call is True
    assert [request.canonical_state.root_mission_id for request in model.requests] == [
        result.root_mission_id,
        result.root_mission_id,
        result.root_mission_id,
        result.root_mission_id,
    ]
    assert model.requests[0].canonical_state.provider_decision_count == 0
    assert model.requests[0].canonical_state.model_visible_affordances == (
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    )
    assert result.decisions[0].decision_origin is DecisionOrigin.MODEL_SELECTED
    assert result.decisions[0].provider_model == "test-provider/model"
    assert model.requests[1].canonical_state.recent_observations[0]["entries"] == ("notes/", "src/")


def test_product_vertical_slice_persists_mission_record_receipts_proof_and_terminal_state(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "search",
                "arguments": {"query": "needle"},
                "expected_state_delta": "matching workspace evidence",
            },
            {
                "capability": "workspace",
                "operation": "read",
                "arguments": {"path": "notes/topic.md", "max_chars": 500},
                "expected_state_delta": "human-readable file evidence",
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "The workspace notes contain the needle."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Find and summarize the needle evidence from the governed workspace.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_canonical_product",
        max_provider_decisions=6,
        max_material_actions=6,
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    event_types = [event.event_type for event in events]
    receipt_dir = kernel.store.mission_dir(result.root_mission_id) / "canonical_receipts"
    proof_root_path = kernel.store.mission_dir(result.root_mission_id) / "mission_proof_root.json"

    assert result.status == "completed"
    assert result.root_created_before_first_provider_call is True
    assert result.mission_record_created_before_provider is True
    assert result.provider_decision_count == 3
    assert result.material_action_count == 2
    assert {decision.decision_protocol for decision in result.decisions} == {
        DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1
    }
    assert {decision.decision_origin for decision in result.decisions} == {DecisionOrigin.MODEL_SELECTED}
    assert [receipt.operation for receipt in result.receipts] == ["search", "read"]
    assert model.requests[1].canonical_state.recent_observations[0]["match_count"] == 2
    assert model.requests[1].canonical_state.recent_observations[0]["matches"][0]["path"] == "notes/topic.md"
    assert "content_excerpt" in model.requests[2].canonical_state.recent_observations[-1]
    assert all((receipt_dir / f"{receipt.receipt_id}.json").exists() for receipt in result.receipts)
    assert proof_root_path.exists()
    assert result.proof_root.integrity_model == "mission_kernel_receipt_timeline_v1"
    assert result.proof_root.kernel_timeline_verified is True
    assert result.proof_root.receipt_artifacts_verified is True
    assert result.proof_root.record_hash_verified is True
    assert result.proof_root.authentic_external_ledger is False
    assert result.proof_root.proof_gaps == ("external_append_only_signer_missing",)
    assert record.status is OperatorMissionStatus.COMPLETED
    assert record.receipt_refs == [receipt.receipt_id for receipt in result.receipts]
    assert kernel.store.verify_timeline(result.root_mission_id) is True
    assert "mission_created" in event_types
    assert "mission_running" in event_types
    assert event_types.count("canonical_decision_accepted") == 3
    assert event_types.count("canonical_effect_receipt_persisted") == 2
    assert "canonical_cleanup_completed" in event_types


def test_product_mission_persists_known_north_star_precondition_before_provider(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    north_star = docs / "SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md"
    north_star.write_text("MODEL = brain\nSENTINEL = body\n", encoding="utf-8")
    kernel = MissionKernel(run_root=tmp_path / "runs")
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "read",
                "arguments": {"path": "docs/SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md"},
            },
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Done."}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Find the Cognitive OS North Star document.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_north_star_precondition",
    )

    precondition_event = next(
        event for event in kernel.store.load_events(result.root_mission_id)
        if event.event_type == "canonical_workspace_precondition_verified"
    )
    assert precondition_event.metadata == {
        "precondition": "known_document_present",
        "relative_path": "docs/SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md",
        "sha256": hashlib.sha256(north_star.read_bytes()).hexdigest(),
    }
    assert str(workspace) not in json.dumps(precondition_event.metadata)
    assert model.requests[0].canonical_state.recent_observations[0]["relative_path"] == (
        "docs/SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md"
    )


def test_product_vertical_slice_provider_failure_terminalizes_record_and_cleanup(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    result = run_canonical_product_mission(
        objective="Fail after the product mission exists.",
        workspace_root=workspace,
        model_client=FailingModelClient(),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_canonical_product_failure",
        max_provider_decisions=3,
        max_material_actions=3,
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    event_types = [event.event_type for event in events]

    assert result.status == "blocked"
    assert result.final_reason == "MODEL_DECISION_FAILED"
    assert result.provider_decision_count == 1
    assert result.material_action_count == 0
    assert result.cleanup_completed is True
    assert record.status is OperatorMissionStatus.BLOCKED
    assert "canonical_model_decision_failed" in event_types
    assert "canonical_cleanup_completed" in event_types
    failure_event = next(event for event in events if event.event_type == "canonical_model_decision_failed")
    assert failure_event.metadata["failure_stage"] == "provider_or_decision_normalization"
    assert failure_event.metadata["failure_code"] == "canonical_provider_decision_json_missing"
    assert failure_event.metadata["exception_class"] == "CanonicalCoreError"
    assert "exception_hash" in failure_event.metadata


def test_product_workspace_dispatch_failure_terminalizes_record_and_cleanup(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    result = run_canonical_product_mission(
        objective="Try a missing file and prove the root mission does not stay running.",
        workspace_root=workspace,
        model_client=RaisingDispatchModelClient(),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_dispatch_failure",
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    failure_event = next(event for event in events if event.event_type == "canonical_effect_failed")

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.provider_decision_count == 1
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True
    assert record.status is OperatorMissionStatus.BLOCKED
    assert failure_event.metadata["failure_stage"] == "product_action_kernel_dispatch"
    assert failure_event.metadata["failure_code"] == "workspace_path_not_found"
    assert any(event.event_type == "canonical_cleanup_completed" for event in events)


def test_product_receipt_persistence_failure_terminalizes_record_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    original_atomic_write_json = kernel.store.atomic_write_json

    def fail_receipt_write(path: Path, payload: dict[str, Any]) -> None:
        if path.name.startswith("canonical_effect_receipt_"):
            raise OSError("synthetic receipt write failure")
        original_atomic_write_json(path, payload)

    monkeypatch.setattr(kernel.store, "atomic_write_json", fail_receipt_write)

    result = run_canonical_product_mission(
        objective="Receipt persistence failure must be terminal and safe.",
        workspace_root=workspace,
        model_client=ScriptedModelClient(
            [{"capability": "workspace", "operation": "list", "arguments": {"path": "."}}]
        ),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_receipt_failure",
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    failure_event = next(event for event in events if event.event_type == "canonical_effect_failed")

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True
    assert record.status is OperatorMissionStatus.BLOCKED
    assert failure_event.metadata["failure_stage"] == "receipt_persistence"
    assert failure_event.metadata["failure_code"] == "OSError"


def test_capability_graph_is_generated_from_executable_routes() -> None:
    graph = build_workspace_read_capability_graph()

    assert graph.model_visible_affordances() == (
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    )
    assert graph.resolve("workspace", "list").effect_kind is EffectKind.REAL
    assert graph.resolve("workspace", "read").materiality_verifier == "workspace_path_observed"
    assert graph.resolve("workspace", "search").proof_contract == "canonical_core_workspace_receipt_v1"
    assert graph.resolve("sentinel_loop", "finish").effect_kind is EffectKind.PROPOSAL
    assert graph.model_visible_operation_schemas()[0]["affordance"] == "workspace.list"
    assert "arguments_schema" in graph.model_visible_operation_schemas()[0]
    assert all(not hasattr(route, "executor") for route in graph.routes)
    assert {route.executor_id for route in graph.routes} == {
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    }
    assert len({(route.capability, route.operation) for route in graph.routes}) == len(graph.routes)


def test_runtime_dispatch_uses_registered_callable_not_hardcoded_if_chain(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    runtime = RootMissionRuntime(objective="Dispatch through registered callables.", workspace_root=workspace, provider_model="test/model")
    route = runtime.capability_graph.resolve("workspace", "list")

    assert route.executor_id == "workspace.list"
    assert runtime.workspace_capability_owner(route) == "ProductActionKernel:workspace"


def test_c2_root_runtime_no_longer_owns_direct_workspace_effect_executor() -> None:
    source = inspect.getsource(RootMissionRuntime)

    assert "def _execute(" not in source
    assert "def _workspace_list(" not in source
    assert "def _workspace_read(" not in source
    assert "def _workspace_search(" not in source


def test_c2_workspace_effect_dispatches_through_product_action_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    calls: list[tuple[str, str]] = []
    original_execute = ActionKernel.execute

    def spy_execute(self: ActionKernel, envelope: ActionEnvelope, **kwargs: Any):
        calls.append((envelope.capability_id, envelope.operation))
        return original_execute(self, envelope, **kwargs)

    monkeypatch.setattr(ActionKernel, "execute", spy_execute)

    result = run_canonical_product_mission(
        objective="List the workspace through the canonical product route.",
        workspace_root=workspace,
        model_client=ScriptedModelClient(
            [
                {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
                {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Listed."}},
            ]
        ),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_c2_product_kernel_dispatch",
    )

    assert result.status == "completed"
    assert calls == [("workspace", "list")]
    assert result.receipts[0].safe_observation["product_action_kernel_dispatch"] is True
    assert result.receipts[0].safe_observation["product_action_result_hash"]


def test_c2_product_route_blocks_before_backend_when_workspace_authority_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    backend_calls: list[str] = []
    original_execute = ActionKernel.execute

    def spy_execute(self: ActionKernel, envelope: ActionEnvelope, **kwargs: Any):
        backend_calls.append(f"{envelope.capability_id}.{envelope.operation}")
        return original_execute(self, envelope, **kwargs)

    monkeypatch.setattr(ActionKernel, "execute", spy_execute)

    result = run_canonical_product_mission(
        objective="Authority denial must happen before workspace backend dispatch.",
        workspace_root=workspace,
        model_client=ScriptedModelClient(
            [{"capability": "workspace", "operation": "list", "arguments": {"path": "."}}]
        ),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_c2_authority_denied",
        granted_authorities=("none",),
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_authority_required:workspace_read"
    assert backend_calls == []


def test_c2_product_route_rejects_simulated_material_backend_proof(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    runtime = RootMissionRuntime(
        objective="A fake backend must not certify material workspace proof.",
        workspace_root=workspace,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_c2_fake_backend",
        allow_legacy_action_envelope=False,
    )

    def fake_workspace_executor(envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            material_action=True,
            observation_summary="Simulated workspace material receipt.",
            context_cards={
                "simulated_backend": True,
                "workspace_readonly_observation": {
                    "backend_kind": "simulated",
                    "entries": ("fake.md",),
                },
            },
        )

    runtime._product_action_kernel = ActionKernel({"workspace": fake_workspace_executor})

    result = runtime.run(
        model_client=ScriptedModelClient(
            [
                {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
                {
                    "capability": "sentinel_loop",
                    "operation": "finish",
                    "arguments": {"answer": "Fake evidence should not allow finish."},
                },
            ]
        )
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_simulated_backend_cannot_create_material_receipt"
    assert result.material_action_count == 0
    assert result.receipts == ()


def test_c2_public_product_route_rejects_legacy_action_envelope_decisions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    result = run_canonical_product_mission(
        objective="Public canonical route must not consume legacy ActionEnvelope decisions.",
        workspace_root=workspace,
        model_client=ScriptedModelClient(
            [ActionEnvelope(capability_id="workspace", operation="list", params={"path": "."})]
        ),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_c2_legacy_envelope_rejected",
    )

    assert result.status == "blocked"
    assert result.final_reason == "MODEL_DECISION_FAILED"
    assert result.blocked_reason_detail == "legacy_action_envelope_not_allowed_on_public_canonical_route"


def test_c3_root_runtime_product_dispatch_uses_typed_kernel_request() -> None:
    source = inspect.getsource(RootMissionRuntime._execute_product_kernel_action)

    assert ".execute_typed(" in source
    assert "_action_envelope_for_decision" not in source
    assert not hasattr(RootMissionRuntime, "_action_envelope_for_decision")


def test_c3_workspace_graph_routes_have_single_callable_owner_and_authority() -> None:
    graph = build_workspace_read_capability_graph()
    owners = Counter(route.affordance for route in graph.routes)
    runtime = RootMissionRuntime(
        objective="Inspect executable workspace registrations.",
        workspace_root=Path.cwd(),
        provider_model="test-provider/model",
    )

    assert owners
    assert all(count == 1 for count in owners.values())
    for route in graph.routes:
        assert route.executor_id
        assert route.required_authority
        assert route.proof_contract
        assert route.capability == "workspace" or route.capability == "sentinel_loop"
        if route.effect_kind is EffectKind.REAL:
            assert route.capability in runtime._product_action_kernel._executors


def test_c3_migrated_public_surfaces_do_not_use_runtimehost_cognitive_loop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sentinel.operator.runtime_host import SentinelRuntimeHost

    def forbidden_loop(*_: Any, **__: Any) -> None:
        raise AssertionError("migrated canonical workspace route invoked legacy RuntimeHost cognitive loop")

    monkeypatch.setattr(SentinelRuntimeHost, "run_product_action_kernel_task_loop", forbidden_loop)
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "list", "arguments": {"path": "."}}),
                json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Done."}}),
            ]
        ),
        encoding="utf-8",
    )

    dev_code = cli.main(
        [
            "canonical-dev-run",
            "--objective",
            "Confirm dev surface uses the canonical root loop.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "dev-runs"),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-local/model",
            "--json",
        ]
    )
    product_script = tmp_path / "product-decisions.jsonl"
    product_script.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    product_code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Confirm product surface uses the canonical root loop.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "product-runs"),
            "--decision-script",
            str(product_script),
            "--provider-model",
            "scripted-local/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payloads = [json.loads(line) for line in output.out.splitlines() if line.strip()]
    assert dev_code == 0
    assert product_code == 0
    assert [payload["public_product_spine"]["public_surface"] for payload in payloads] == [
        "canonical-dev-run",
        "canonical-product-run",
    ]
    assert all(payload["public_product_spine"]["runtimehost_cognition"] is False for payload in payloads)


def test_c3_cli_has_single_production_canonical_provider_client() -> None:
    source = inspect.getsource(cli)

    assert "_RealProviderCanonicalDecisionClient" not in source
    assert "ProductModelNativeDecisionClient.for_canonical_decisions" in source
    assert "_canonical_real_model_request(" not in source
    assert "_canonical_product_provider_prompt(" not in source


def test_model_decision_accepts_registered_affordance_operation_without_capability(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"operation": "workspace.search", "arguments": {"query": "needle", "path": "."}},
            {"operation": "sentinel_loop.finish", "arguments": {"answer": "Done."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Use compact registered affordance operations.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.status == "completed"
    assert [decision.selected_capability for decision in result.decisions] == ["workspace", "sentinel_loop"]
    assert [decision.selected_operation for decision in result.decisions] == ["search", "finish"]


def test_product_action_envelope_decision_is_consumed_without_parallel_model_protocol(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            ActionEnvelope(capability_id="workspace", operation="list", params={"path": "."}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"answer": "Listed via product envelope."}),
        ]
    )

    result = run_canonical_dev_mission(
        objective="List the workspace through the normalized product action language.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.status == "completed"
    assert result.decisions[0].selected_capability == "workspace"
    assert result.decisions[0].selected_operation == "list"
    assert result.decisions[0].arguments == {"path": "."}
    assert result.decisions[0].decision_origin is DecisionOrigin.MODEL_SELECTED
    assert result.receipts[0].operation == "list"


def test_workspace_list_read_search_are_generic_not_scenario_choreography(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "src"}},
            {"capability": "workspace", "operation": "read", "arguments": {"path": "src/pkg/module.py"}},
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Needle found in generic tree."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Find where the needle appears.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        max_provider_decisions=6,
        max_material_actions=6,
    )

    assert result.status == "completed"
    assert result.cleanup_completed is True
    assert [receipt.operation for receipt in result.receipts[:3]] == ["list", "read", "search"]
    assert result.receipts[0].safe_observation["entries"] == ("pkg/",)
    assert result.receipts[1].safe_observation["path"] == "src/pkg/module.py"
    assert result.receipts[2].safe_observation["match_count"] == 2
    assert all("app.py" not in receipt.safe_summary for receipt in result.receipts)
    assert all("tests/test_app.py" not in receipt.safe_summary for receipt in result.receipts)


def test_workspace_read_cannot_escape_root(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (tmp_path / "outside.txt").write_text("outside needle must not be read\n", encoding="utf-8")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "read", "arguments": {"path": "../outside.txt"}},
        ]
    )

    with pytest.raises(CanonicalCoreError, match="workspace_path_outside_root"):
        run_canonical_dev_mission(
            objective="Try to read outside the governed workspace.",
            workspace_root=workspace,
            model_client=model,
            provider_model="test-provider/model",
        )


def test_workspace_search_skips_symlink_or_junction_escape(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("needle outside workspace must not be searchable\n", encoding="utf-8")
    link = workspace / "linked_outside.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable in this environment: {exc.__class__.__name__}")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle", "path": "."}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Done."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Search must not follow a link outside the governed workspace.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    observation = result.receipts[0].safe_observation
    assert observation["match_count"] == 2
    assert observation["skipped_outside_root_count"] == 1
    assert all(match["path"] != "linked_outside.txt" for match in observation["matches"])


def test_workspace_search_applies_file_and_byte_limits(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "big.txt").write_text("needle " * 1000, encoding="utf-8")
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "search",
                "arguments": {"query": "needle", "path": ".", "max_files": 1, "max_bytes_per_file": 8},
            },
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Done."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Search with strict resource limits.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    observation = result.receipts[0].safe_observation
    assert observation["files_examined_count"] == 1
    assert observation["skipped_max_files_count"] >= 1
    assert observation["skipped_too_large_count"] in {0, 1}


def test_workspace_search_reports_path_content_and_normalized_term_matches(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    docs = workspace / "docs" / "reviews" / "deep_power_audit"
    docs.mkdir(parents=True)
    north_star = docs / "SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md"
    north_star.write_text(
        "# Sentinel Cognitive Operating System North Star V1\n\n"
        "MODEL = reasoning, imagination and strategy.\n"
        "SENTINEL = body, senses, runtime, evidence and laws.\n",
        encoding="utf-8",
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "search",
                "arguments": {"query": "Cognitive OS North Star", "path": "."},
            },
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Found."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Find the North Star document.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    observation = result.receipts[0].safe_observation
    assert observation["search_scope"] == {
        "path": ".",
        "channels": ("filename_path", "content", "normalized_terms"),
    }
    assert observation["files_examined_count"] == 1
    assert observation["path_match_count"] == 1
    assert observation["content_match_count"] == 1
    assert observation["normalized_term_match_count"] == 1
    assert observation["matches"][0]["path"] == "docs/reviews/deep_power_audit/SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md"
    assert observation["matches"][0]["match_channels"] == ("filename_path", "content", "normalized_terms")


def test_progress_state_marks_exact_duplicate_search_without_new_evidence_as_no_progress(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "search", "arguments": {"query": "missing phrase"}},
            {"capability": "workspace", "operation": "search", "arguments": {"query": "missing phrase"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "No evidence found."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Search for a missing phrase and avoid blind repetition.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        max_provider_decisions=4,
        max_material_actions=4,
    )

    second_request_state = model.requests[2].canonical_state
    last_observation = second_request_state.recent_observations[-1]
    assert last_observation["progress_classification"] == "NO_PROGRESS"
    assert second_request_state.duplicate_no_progress_count == 1
    assert second_request_state.observations_without_novelty == 1
    assert second_request_state.objective_unresolved is True
    assert second_request_state.finish_available is False
    assert "workspace.search" in second_request_state.action_signatures_attempted[0]
    assert second_request_state.paths_explored == ()


def test_model_narrative_non_decision_is_returned_as_replan_observation_without_dispatch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    model = NarrativeThenDecisionModelClient()

    result = run_canonical_product_mission(
        objective="Find the needle evidence without inventing an action for a narrative-only model response.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/qwen-like",
        kernel=kernel,
        session_id="session_narrative_replan",
        max_provider_decisions=4,
        max_material_actions=4,
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert result.provider_decision_count == 3
    assert result.material_action_count == 1
    assert len(result.receipts) == 1
    assert result.receipts[0].operation == "search"
    second_turn_observations = model.requests[1].canonical_state.recent_observations
    assert second_turn_observations[-1]["typed_outcome"] == "MODEL_EXPRESSION_NON_DECISION"
    assert second_turn_observations[-1]["recovery_instruction"] == "replan_or_select_available_affordance"
    assert second_turn_observations[-1]["material_action_observed"] is False
    assert result.cleanup_completed is True


def test_model_invalid_arguments_are_returned_as_replan_observation_without_dispatch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.open", "arguments": {}},
            {"capability": "real_browser_control", "operation": "real_browser.open", "arguments": {"target_origin": "sqlite.org"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Opened the authorized site."}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Open the authorized SQLite site.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        kernel=kernel,
        session_id="session_invalid_args_replan",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
        granted_authorities=("workspace_read", "browser_read", "none"),
        max_provider_decisions=4,
        max_material_actions=4,
    )

    assert result.status == "completed"
    assert result.provider_decision_count == 3
    assert result.material_action_count == 1
    assert result.receipts[0].operation == "real_browser.open"
    second_turn_observation = model.requests[1].canonical_state.recent_observations[-1]
    assert second_turn_observation["typed_outcome"] == "MODEL_EXPRESSION_NON_DECISION"
    assert second_turn_observation["transport_rejection_reason"] == "invalid_arguments"
    assert second_turn_observation["argument_validation_error"] == "required_argument_missing"
    assert second_turn_observation["product_action_kernel_dispatch"] is False


def test_initial_browser_state_only_advertises_executable_browser_affordances(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "No browser action taken."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="Open SQLite docs before searching.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
        granted_authorities=("workspace_read", "browser_read", "none"),
        max_provider_decisions=1,
        max_material_actions=1,
    )

    first_state = model.requests[0].canonical_state
    affordances = set(first_state.model_visible_affordances)
    assert "real_browser_control.real_browser.open" in affordances
    assert "real_browser_control.real_browser.observe" in affordances
    assert "real_browser_control.real_browser.search" not in affordances
    assert "real_browser_control.real_browser.extract_evidence" not in affordances
    open_schema = next(
        schema
        for schema in first_state.model_visible_operation_schemas
        if schema["operation"] == "real_browser.open"
    )
    target_origin_schema = open_schema["arguments_schema"]["properties"]["target_origin"]
    assert target_origin_schema["default"] == "sqlite.org"
    assert target_origin_schema["enum"] == ["sqlite.org"]
    assert result.status == "blocked"
    assert result.material_action_count == 0


def test_browser_initial_prompt_shows_only_executable_open_with_authorized_origin(tmp_path: Path) -> None:
    captured_requests: list[Any] = []

    class FakeModelClient:
        def complete(self, request: Any) -> dict[str, str]:
            captured_requests.append(request)
            return {"content": '{"capability":"sentinel_loop","operation":"finish","arguments":{"answer":"stop"}}'}

    workspace = _workspace(tmp_path)
    runtime = RootMissionRuntime(
        objective="Open SQLite docs before searching.",
        workspace_root=workspace,
        provider_model="aliyun_dashscope/qwen-plus",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
        granted_authorities=("workspace_read", "browser_read", "none"),
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=FakeModelClient(),
        provider_id="aliyun_dashscope",
        backend_id="aliyun_openai_compatible_chat",
        model_id="qwen-plus",
    )

    runtime.run(model_client=client)

    prompt = captured_requests[0].prompt_text_in_memory_only
    assert 'browser.open(target_origin="sqlite.org")' in prompt
    assert "browser.search(query=" not in prompt
    assert "browser.extract_evidence(" not in prompt


def test_model_non_decision_observation_includes_safe_bridge_telemetry(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    raw_model = ScriptedModelClient(
        [
            {"content": '{"arguments":{"unsupported":"value"}}'},
            {"content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}'},
            {"content": '{"capability":"sentinel_loop","operation":"finish","arguments":{"answer":"blocked honestly"}}'},
        ]
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=raw_model,
        provider_id="aliyun_dashscope",
        backend_id="aliyun_openai_compatible_chat",
        model_id="qwen-plus",
    )

    kernel = MissionKernel(run_root=tmp_path / "runs")
    result = run_canonical_product_mission(
        objective="Open SQLite docs before searching.",
        workspace_root=workspace,
        model_client=client,
        provider_model="aliyun_dashscope/qwen-plus",
        kernel=kernel,
        session_id="session_bridge_telemetry",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
        granted_authorities=("workspace_read", "browser_read", "none"),
        max_provider_decisions=4,
        max_material_actions=2,
    )

    assert result.status == "completed"
    events_path = tmp_path / "runs" / result.root_mission_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    bridge_observation = next(
        event["metadata"]
        for event in events
        if event["event_type"] == "canonical_model_expression_non_decision"
    )
    assert bridge_observation["transport_rejection_reason"] == "invalid_arguments"
    assert bridge_observation["argument_validation_error"] == "no_compatible_route"
    assert bridge_observation["bridge_candidate_count"] == 0
    assert bridge_observation["bridge_source_expression_type"] == "partial_json"
    assert bridge_observation["bridge_selection_basis"] == "unique_schema_compatible_candidate"
    assert bridge_observation["raw_provider_material_persisted"] is False
    assert "unsupported" not in str(bridge_observation)
    assert "value" not in str(bridge_observation)


def test_product_receipt_integrity_rejects_deleted_or_modified_receipt_artifact(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Needle found."}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Produce a receipt then verify tampering detection.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_receipt_integrity",
    )
    runtime = RootMissionRuntime(
        objective="Verify receipts.",
        workspace_root=workspace,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_receipt_integrity_checker",
    )
    runtime.root_mission_id = result.root_mission_id

    assert runtime._receipt_artifacts_verified(tuple(receipt.receipt_id for receipt in result.receipts)) is True

    receipt_path = kernel.store.mission_dir(result.root_mission_id) / "canonical_receipts" / f"{result.receipts[0].receipt_id}.json"
    original = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_path.unlink()
    assert runtime._receipt_artifacts_verified(tuple(receipt.receipt_id for receipt in result.receipts)) is False

    receipt_path.write_text(json.dumps({**original, "status": "tampered"}, indent=2), encoding="utf-8")
    assert runtime._receipt_artifacts_verified(tuple(receipt.receipt_id for receipt in result.receipts)) is False


def test_product_receipt_integrity_supports_long_run_root_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    deep_run_root = tmp_path / ("very_long_canonical_core_run_root_" * 5) / ("nested_receipts_" * 4)
    kernel = MissionKernel(run_root=deep_run_root)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Needle found."}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Produce a receipt under a long run root.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_long_receipt_integrity",
    )

    assert result.proof_root.receipt_artifacts_verified is True


def test_product_dispatch_enforces_mission_grant_before_real_effect(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    result = run_canonical_product_mission(
        objective="Workspace read should be blocked without workspace_read authority.",
        workspace_root=workspace,
        model_client=ScriptedModelClient(
            [{"capability": "workspace", "operation": "list", "arguments": {"path": "."}}]
        ),
        provider_model="scripted-real-shape/model",
        kernel=kernel,
        session_id="session_no_grant",
        granted_authorities=("none",),
    )

    record = kernel.store.load_record(result.root_mission_id)

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_authority_required:workspace_read"
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert record.status is OperatorMissionStatus.BLOCKED


def test_model_payload_cannot_self_grant_authority(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {
                "capability": "workspace",
                "operation": "list",
                "arguments": {"path": "."},
                "authority_effect": "grant_new_authority",
                "can_grant_authority": True,
            },
        ]
    )

    with pytest.raises(ValueError, match="authority effect must remain none"):
        run_canonical_dev_mission(
            objective="Model tries to self-grant authority.",
            workspace_root=workspace,
            model_client=model,
            provider_model="test-provider/model",
        )


def test_stage2_probe_confirms_current_code_exec_is_not_physical_sandbox_and_core_quarantines_it(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside_canary.txt"
    outside.write_text("outside canary readable only when the sandbox is not physical\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "tests" / "test_escape.py").write_text(
        "from pathlib import Path\n\n"
        "def test_can_read_outside_workspace():\n"
        f"    assert Path({str(outside)!r}).read_text(encoding='utf-8').startswith('outside canary')\n",
        encoding="utf-8",
    )
    kernel = MissionKernel(run_root=tmp_path / "runs")
    mission = kernel.create_mission(session_id="session_code_probe", draft=_draft())
    authority = _authority(mission.mission_id, workspace)
    runtime = CodeExecutionSandboxRuntime(
        kernel=kernel,
        mission_id=mission.mission_id,
        workspace_root=workspace,
    )

    result = runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params={"profile_id": "pytest_file", "args": ["tests/test_escape.py"]},
        ),
        authority=authority,
        context={},
    )
    graph = build_workspace_read_capability_graph()

    assert result.status == "passed"
    assert graph.quarantined_capability("code_execution_sandbox", "code_exec.run_profile").reason == (
        "physical_sandbox_not_proven"
    )
    with pytest.raises(CanonicalCoreError, match="canonical_capability_quarantined"):
        graph.resolve("code_execution_sandbox", "code_exec.run_profile")


def test_model_selected_quarantined_code_capability_returns_typed_blocker(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {
                "capability": "code_execution_sandbox",
                "operation": "code_exec.run_profile",
                "arguments": {"profile_id": "pytest_file", "args": ["tests/test_smoke.py"]},
            },
        ]
    )

    result = run_canonical_dev_mission(
        objective="Run code only if the canonical core can prove a physical sandbox.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.status == "blocked"
    assert result.final_reason == "CAPABILITY_QUARANTINED"
    assert result.blocked_capability == "code_execution_sandbox.code_exec.run_profile"
    assert result.blocked_reason_detail == "physical_sandbox_not_proven"
    assert result.material_action_count == 0
    assert result.receipts == ()
    assert result.cleanup_completed is True


def test_initial_proof_root_is_explicitly_non_authentic_placeholder(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    model = ScriptedModelClient(
        [
            {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
            {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Listed workspace."}},
        ]
    )

    result = run_canonical_dev_mission(
        objective="List the workspace.",
        workspace_root=workspace,
        model_client=model,
        provider_model="test-provider/model",
    )

    assert result.proof_root.integrity_model == "non_authentic_placeholder"
    assert result.proof_root.authentic_external_ledger is False
    assert result.proof_root.receipt_refs == tuple(receipt.receipt_id for receipt in result.receipts)
    assert result.proof_root.proof_gaps == ("external_append_only_signer_missing",)


def test_public_dev_cli_entrypoint_runs_canonical_core_vertical_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "list", "arguments": {"path": "."}}),
                json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "CLI slice done."}}),
            ]
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "canonical-dev-run",
            "--objective",
            "Exercise the canonical core from the public dev CLI.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "runs"),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-local/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert payload["status"] == "completed"
    assert payload["mission_record_created_before_provider"] is True
    assert payload["provider_decision_count"] == 2
    assert payload["root_created_before_first_provider_call"] is True
    assert payload["cleanup_completed"] is True
    assert payload["public_product_spine"]["strategy"] == "RUNTIMEHOST_HOSTS_ROOTMISSIONRUNTIME_CANONICAL_WORKSPACE"
    assert payload["public_product_spine"]["runtime_entrypoint"] == "RootMissionRuntime.run"
    assert payload["public_product_spine"]["runtimehost_cognition"] is False
    assert payload["product_receipt_refs"]
    assert payload["proof_root"]["integrity_model"] == "mission_kernel_receipt_timeline_v1"


def test_public_product_cli_entrypoint_uses_kernel_backed_vertical_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}}),
                json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "CLI product slice done."}}),
            ]
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Exercise the kernel-backed canonical product slice.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "runs"),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-real-shape/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert code == 0
    assert output.err == ""
    assert payload["status"] == "completed"
    assert payload["mission_record_created_before_provider"] is True
    assert payload["provider_decision_count"] == 2
    assert payload["material_action_count"] == 1
    assert payload["proof_root"]["integrity_model"] == "mission_kernel_receipt_timeline_v1"
    assert payload["proof_root"]["receipt_artifacts_verified"] is True
    assert payload["cleanup_completed"] is True


def test_public_product_cli_entrypoint_reaches_single_canonical_workspace_spine(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}}),
                json.dumps(
                    {
                        "capability": "sentinel_loop",
                        "operation": "finish",
                        "arguments": {"answer": "Public product route finished."},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    run_root = tmp_path / "runs"

    code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Discriminate the public product path from a parallel canonical loop.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(run_root),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-product-model-native/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)
    event_types: list[str] = []
    for event_path in run_root.rglob("events.jsonl"):
        for line in event_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            event_types.append(event.get("event_type") or event.get("event_kind"))

    assert code == 0
    assert payload["status"] == "completed"
    assert payload["public_product_spine"]["strategy"] == "RUNTIMEHOST_HOSTS_ROOTMISSIONRUNTIME_CANONICAL_WORKSPACE"
    assert payload["public_product_spine"]["decision_client"] == "_JsonlCanonicalDecisionScriptClient"
    assert payload["public_product_spine"]["runtime_entrypoint"] == "RootMissionRuntime.run"
    assert payload["public_product_spine"]["model_decision_protocol"] == "CanonicalDecision"
    assert payload["public_product_spine"]["capability_dispatch"] == "ProductActionKernel"
    assert payload["public_product_spine"]["legacy_action_envelope_adapter"] is False
    assert payload["public_product_spine"]["runtimehost_cognition"] is False
    assert payload["mission_record_created_before_provider"] is True
    assert len(payload["mission_ids"]) == 1
    assert payload["root_mission_id"] == payload["mission_ids"][0]
    assert payload["product_receipt_refs"]
    assert "canonical_decision_accepted" in event_types
    assert "canonical_effect_receipt_persisted" in event_types
    assert "canonical_cleanup_completed" in event_types
    receipt_files = list(run_root.rglob("canonical_receipts/*.json"))
    assert len(receipt_files) == len(payload["product_receipt_refs"])


def test_public_product_cli_projects_runtime_state_for_web_cutover(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}}),
                json.dumps(
                    {
                        "capability": "sentinel_loop",
                        "operation": "finish",
                        "arguments": {"answer": "The public product received a canonical answer."},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Return a canonical product answer to the web dashboard.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "runs"),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-product-model/model",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)

    assert code == 0
    assert payload["status"] == "completed"
    assert payload["current_stage"] == "terminal_completed"
    assert payload["provider_model"] == "scripted-product-model/model"
    assert payload["authority_scope"]["granted_authorities"] == ["workspace_read", "none"]
    assert payload["model_visible_affordances"] == [
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    ]
    assert payload["completed_actions"] == [
        {
            "receipt_id": payload["product_receipt_refs"][0],
            "capability": "workspace",
            "operation": "search",
            "status": "completed",
            "material_action": True,
            "evidence_refs": payload["evidence_refs"],
        }
    ]
    assert payload["terminal_answer"] == "The public product received a canonical answer."
    assert payload["proof_root"]["receipt_artifacts_verified"] is True
    assert payload["cleanup_completed"] is True


def test_public_product_cli_real_provider_mode_uses_product_native_transport(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    captured_requests: list[Any] = []

    class FakeCatalogModelClient:
        def __init__(self, **_: Any) -> None:
            pass

        def complete(self, request: Any) -> dict[str, Any]:
            captured_requests.append(request)
            if len(captured_requests) == 1:
                return {"content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}'}
            return {
                "content": (
                    '{"capability":"sentinel_loop","operation":"finish",'
                    '"arguments":{"answer":"Real-provider-shaped CLI product slice done."}}'
                )
            }

    monkeypatch.setattr(cli, "OperatorCatalogModelClient", FakeCatalogModelClient)

    code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Exercise the real-provider-shaped canonical product slice.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "runs"),
            "--provider-id",
            "aliyun_dashscope",
            "--backend-id",
            "aliyun_openai_compatible_chat",
            "--model-id",
            "glm-5.2",
            "--max-provider-decisions",
            "4",
            "--max-material-actions",
            "4",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert code == 0
    assert len(captured_requests) == 2
    assert captured_requests[0].runtime == "product_model_native_decision"
    assert captured_requests[0].request_metadata["raw_text_transport"] == "product_model_native_intent_v1"
    assert captured_requests[0].request_metadata["canonical_decision_transport_profiles"] == [
        "strict_json_content",
        "fenced_strict_json",
    ]
    assert captured_requests[0].request_metadata["provider_native_tool_call_decode_enabled"] is False
    assert captured_requests[0].request_metadata["model_visible_affordances"] == [
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    ]
    prompt = captured_requests[0].prompt_text_in_memory_only
    assert "Allowed operations are generated from Sentinel's executable capability graph" in prompt
    assert "You do not need to speak Sentinel's internal IR" in prompt
    assert "Action: <affordance>" in prompt
    assert "function-like calls such as browser.open" in prompt
    assert "Decision menu (graph-derived)" in prompt
    assert "workspace.search(query=\"...\")" in prompt
    assert len(prompt) < 7000
    assert "Return exactly one JSON object" not in prompt
    assert "model_visible_operation_schemas" in prompt
    assert "workspace.search" in prompt
    assert "- {\"capability\":\"workspace\"" not in prompt
    assert captured_requests[0].provider_id == "aliyun_dashscope"
    assert captured_requests[0].backend_id == "aliyun_openai_compatible_chat"
    assert captured_requests[0].model_id == "glm-5.2"
    assert payload["status"] == "completed"
    assert payload["public_product_spine"]["decision_client"] == "ProductModelNativeDecisionClient"
    assert payload["public_product_spine"]["runtime_entrypoint"] == "RootMissionRuntime.run"
    assert payload["public_product_spine"]["legacy_action_envelope_adapter"] is False
    assert payload["proof_root"]["integrity_model"] == "mission_kernel_receipt_timeline_v1"


def test_product_model_native_decision_client_can_emit_canonical_decision(tmp_path: Path) -> None:
    captured_requests: list[Any] = []

    class FakeModelClient:
        def complete(self, request: Any) -> dict[str, str]:
            captured_requests.append(request)
            return {
                "content": (
                    '{"capability":"workspace","operation":"search",'
                    '"arguments":{"query":"needle"},"expected_state_delta":"matches"}'
                )
            }

    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=FakeModelClient(),
        provider_id="aliyun_dashscope",
        backend_id="aliyun_openai_compatible_chat",
        model_id="qwen-plus",
    )
    workspace = _workspace(tmp_path)
    runtime = RootMissionRuntime(
        objective="Find needle.",
        workspace_root=workspace,
        provider_model="aliyun_dashscope/qwen-plus",
    )
    request = CanonicalDecisionRequest(
        root_mission_id=runtime.root_mission_id,
        provider_model="aliyun_dashscope/qwen-plus",
        canonical_state=runtime.compile_state(),
        prompt_summary="test",
        cancellation_ref=runtime.cancellation_token.safe_ref,
    )

    decision = client.complete(request)

    assert isinstance(decision, CanonicalDecision)
    assert len(captured_requests) == 1
    assert captured_requests[0].runtime == "product_model_native_decision"
    assert decision.decision_protocol is DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1
    assert decision.decision_origin is DecisionOrigin.MODEL_SELECTED
    assert decision.selected_capability == "workspace"
    assert decision.selected_operation == "search"
    assert decision.arguments == {"query": "needle"}


def test_canonical_decision_client_accepts_openai_strict_json_content_with_safe_shape_telemetry(
    tmp_path: Path,
) -> None:
    raw_content = json.dumps(
        {
            "capability": "workspace",
            "operation": "search",
            "arguments": {"query": "needle"},
            "expected_state_delta": "matches",
        }
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient(
            [
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": raw_content},
                        }
                    ],
                }
            ]
        ),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content",),
    )

    decision = client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "workspace"
    assert decision.selected_operation == "search"
    assert decision.arguments == {"query": "needle"}
    assert telemetry["response_root_type"] == "dict"
    assert telemetry["choices_count"] == 1
    assert telemetry["message_present"] is True
    assert telemetry["content_present"] is True
    assert telemetry["content_type"] == "str"
    assert telemetry["tool_calls_present"] is False
    assert telemetry["reasoning_content_present"] is False
    assert telemetry["finish_reason"] == "stop"
    assert telemetry["content_length_bucket"] == "1-255"
    assert telemetry["json_detected"] is True
    assert telemetry["json_root_type"] == "dict"
    assert telemetry["canonical_fields_present"] == ["arguments", "capability", "operation"]
    assert telemetry["canonical_fields_missing"] == []
    assert telemetry["extraction_stage"] == "strict_json_content"
    assert telemetry["typed_rejection_reason"] == ""
    assert "needle" not in str(telemetry)
    assert "raw_content" not in client.safe_diagnostics[-1]


def test_openrouter_canonical_decision_client_uses_generic_openai_compatible_transport(tmp_path: Path) -> None:
    raw_content = json.dumps(
        {
            "capability": "workspace",
            "operation": "search",
            "arguments": {"query": "needle"},
        }
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": raw_content}]),
        provider_id="openrouter",
        backend_id="openrouter_chat_completions",
        model_id="z-ai/glm-5.2",
    )

    decision = client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "workspace"
    assert decision.selected_operation == "search"
    assert telemetry["supported_transport_profiles"] == ["strict_json_content", "fenced_strict_json"]
    assert telemetry["raw_provider_material_persisted"] is False


def test_canonical_decision_client_accepts_fenced_json_only_when_profile_allows(
    tmp_path: Path,
) -> None:
    fenced = (
        "```json\n"
        '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}'
        "\n```"
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": fenced}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("fenced_strict_json",),
    )

    decision = client.complete(_canonical_request(tmp_path))

    assert decision.selected_capability == "workspace"
    assert decision.selected_operation == "search"
    assert client.safe_diagnostics[-1]["canonical_decision_transport"]["extraction_stage"] == "fenced_strict_json"


def test_canonical_decision_client_accepts_native_tool_call_only_when_profile_allows(
    tmp_path: Path,
) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient(
            [
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "type": "function",
                                        "function": {
                                            "name": "workspace.search",
                                            "arguments": '{"query":"needle"}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        ),
        provider_id="unit_provider",
        backend_id="unit_native_tool_backend",
        model_id="unit-tool-model",
        canonical_transport_profiles=("native_tool_call",),
    )

    decision = client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "workspace"
    assert decision.selected_operation == "search"
    assert decision.arguments == {"query": "needle"}
    assert telemetry["tool_calls_present"] is True
    assert telemetry["tool_calls_count"] == 1
    assert telemetry["extraction_stage"] == "native_tool_call"
    assert telemetry["decision_origin_chain"][:2] == [
        "provider_transport:native_tool_call",
        "tool_name_explicitly_encoded_capability_operation",
    ]
    assert "selection_basis:explicit_action_name" in telemetry["decision_origin_chain"]
    assert "capability_graph_route_verified" in telemetry["decision_origin_chain"]
    assert "arguments_schema_verified" in telemetry["decision_origin_chain"]
    assert telemetry["decision_origin_chain"][-1] == "decision_origin:model_selected"


@pytest.mark.parametrize(
    ("raw_output", "profiles", "reason"),
    [
        (
            {"content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}'},
            ("unsupported",),
            "unsupported_transport",
        ),
        ({"choices": [{"message": {"role": "assistant"}}]}, ("strict_json_content",), "content_absent"),
        ({"content": '{"capability":"workspace","operation":"search","arguments":'}, ("strict_json_content",), "malformed_json"),
        ({"content": "I will search for the answer."}, ("strict_json_content",), "narrative_only_response"),
        (
            {"content": '{"capability":"shell","operation":"run","arguments":{"query":"needle"}}'},
            ("strict_json_content",),
            "unknown_capability",
        ),
        (
            {"content": '{"capability":"workspace","operation":"patch","arguments":{"path":"README.md"}}'},
            ("strict_json_content",),
            "unavailable_operation",
        ),
        (
            {"content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle","extra":"x"}}'},
            ("strict_json_content",),
            "invalid_arguments",
        ),
        (
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}',
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {"name": "workspace.search", "arguments": '{"query":"needle"}'},
                                }
                            ],
                        }
                    }
                ],
            },
            ("native_tool_call", "strict_json_content"),
            "multiple_candidate_decisions",
        ),
        (
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"capability":"workspace","operation":"search","arguments":{"query":"needle"}}',
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {"name": "workspace.search", "arguments": '{"query":"needle"}'},
                                }
                            ],
                        }
                    }
                ],
            },
            ("strict_json_content",),
            "unsupported_transport",
        ),
    ],
)
def test_canonical_decision_transport_rejects_partial_or_ambiguous_outputs(
    tmp_path: Path,
    raw_output: dict[str, Any],
    profiles: tuple[str, ...],
    reason: str,
) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([raw_output]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=profiles,
    )

    with pytest.raises(ActionKernelError, match=reason):
        client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert telemetry["typed_rejection_reason"] == reason
    assert client.safe_diagnostics[-1]["mapped_action"] is None
    assert "needle" not in str(telemetry)


def test_canonical_decision_transport_rejects_unadvertised_tool_call_without_inventing_action(
    tmp_path: Path,
) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "type": "function",
                                        "function": {"name": "search", "arguments": '{"query":"needle"}'},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        ),
        provider_id="unit_provider",
        backend_id="unit_native_tool_backend",
        model_id="unit-tool-model",
        canonical_transport_profiles=("native_tool_call",),
    )

    with pytest.raises(ActionKernelError, match="capability_missing"):
        client.complete(_canonical_request(tmp_path))

    assert client.safe_diagnostics[-1]["mapped_action"] is None


def test_unknown_provider_profile_is_unsupported_without_silent_json_assumption(tmp_path: Path) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient(
            [
                {
                    "content": json.dumps(
                        {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}}
                    )
                }
            ]
        ),
        provider_id="unknown_provider",
        backend_id="unknown_backend",
        model_id="unknown_model",
    )

    with pytest.raises(ActionKernelError, match="unsupported_transport"):
        client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert telemetry["supported_transport_profiles"] == ["unsupported"]
    assert telemetry["typed_rejection_reason"] == "unsupported_transport"
    assert client.safe_diagnostics[-1]["mapped_action"] is None


def test_model_expression_bridge_accepts_arguments_only_when_one_schema_candidate_exists(tmp_path: Path) -> None:
    graph = ExecutableCapabilityGraph(
        routes=(
            _probe_route("select", required=("signal",), properties={"signal": {"type": "string"}}),
        )
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": '{"arguments":{"signal":"ready"}}'}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content",),
    )

    decision = client.complete(_canonical_request(tmp_path, capability_graph=graph))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "protocol_probe"
    assert decision.selected_operation == "select"
    assert decision.arguments == {"signal": "ready"}
    assert telemetry["selection_basis"] == "unique_schema_compatible_candidate"
    assert telemetry["candidate_count"] == 1
    assert telemetry["source_expression_type"] == "partial_json"


def test_model_expression_bridge_rejects_arguments_only_when_schema_candidate_is_ambiguous(tmp_path: Path) -> None:
    graph = ExecutableCapabilityGraph(
        routes=(
            _probe_route(
                "select",
                required=("signal",),
                properties={"signal": {"type": "string"}},
            ),
            CanonicalCapabilityRoute(
                capability="alternate_probe",
                operation="select",
                executor_id="alternate_probe.select",
                effect_kind=EffectKind.PROPOSAL,
                backend_mode="test_only_no_executor",
                required_authority="none",
                arguments_schema={
                    "type": "object",
                    "properties": {"signal": {"type": "string"}},
                    "required": ["signal"],
                    "additionalProperties": False,
                },
                preconditions=("test_only",),
                readiness_probe="always_available",
                materiality_verifier="none",
                proof_contract="test_only",
                recovery_policy="none",
                cleanup_contract="none",
            ),
        )
    )
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": '{"arguments":{"signal":"ready"}}'}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content",),
    )

    with pytest.raises(ActionKernelError, match="ambiguous_intent"):
        client.complete(_canonical_request(tmp_path, capability_graph=graph))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert telemetry["typed_rejection_reason"] == "ambiguous_intent"
    assert telemetry["candidate_count"] == 2
    assert client.safe_diagnostics[-1]["mapped_action"] is None


def test_model_expression_bridge_accepts_function_like_browser_intent_without_playwright_exposure(
    tmp_path: Path,
) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": 'browser.open(url="https://sqlite.org")'}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content", "fenced_strict_json"),
    )

    decision = client.complete(
        _canonical_request(tmp_path, capability_graph=build_workspace_browser_readonly_capability_graph())
    )

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "real_browser_control"
    assert decision.selected_operation == "real_browser.open"
    assert decision.arguments == {"target_origin": "https://sqlite.org"}
    assert telemetry["selection_basis"] == "explicit_action_name"
    assert telemetry["argument_aliases_applied"] == {"url": "target_origin"}
    assert "playwright" not in str(telemetry).lower()


def test_model_expression_bridge_accepts_json_action_field_with_function_like_browser_intent(
    tmp_path: Path,
) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": '{"action":"browser.open(target_origin=\\"sqlite.org\\")"}'}]),
        provider_id="aliyun_dashscope",
        backend_id="aliyun_openai_compatible_chat",
        model_id="qwen-plus",
        canonical_transport_profiles=("strict_json_content", "fenced_strict_json"),
    )

    decision = client.complete(
        _canonical_request(tmp_path, capability_graph=build_workspace_browser_readonly_capability_graph())
    )

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "real_browser_control"
    assert decision.selected_operation == "real_browser.open"
    assert decision.arguments == {"target_origin": "sqlite.org"}
    assert telemetry["selection_basis"] == "explicit_action_name"
    assert telemetry["source_expression_type"] == "partial_json"


def test_model_expression_bridge_accepts_react_style_action_with_json_arguments(tmp_path: Path) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient(
            [{"content": 'Action: real_browser.open\nArguments: {"target_origin":"sqlite.org"}'}]
        ),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content", "fenced_strict_json"),
    )

    decision = client.complete(
        _canonical_request(tmp_path, capability_graph=build_workspace_browser_readonly_capability_graph())
    )

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "real_browser_control"
    assert decision.selected_operation == "real_browser.open"
    assert decision.arguments == {"target_origin": "sqlite.org"}
    assert telemetry["source_expression_type"] == "react_action"
    assert telemetry["selection_basis"] == "explicit_action_name"


def test_model_expression_bridge_preserves_final_answer_as_finish_intent(tmp_path: Path) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": "Final answer: Generated columns are defined by SQLite."}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content", "fenced_strict_json"),
    )

    decision = client.complete(_canonical_request(tmp_path))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert decision.selected_capability == "sentinel_loop"
    assert decision.selected_operation == "finish"
    assert decision.arguments == {"answer": "Generated columns are defined by SQLite."}
    assert telemetry["source_expression_type"] == "final_answer"
    assert telemetry["selection_basis"] == "explicit_final_answer"


def test_model_expression_bridge_does_not_invent_missing_material_arguments(tmp_path: Path) -> None:
    client = ProductModelNativeDecisionClient.for_canonical_decisions(
        model_client=ScriptedModelClient([{"content": "Action: real_browser.search"}]),
        provider_id="nvidia",
        backend_id="nvidia_openai_compatible_chat",
        model_id="minimaxai/minimax-m3",
        canonical_transport_profiles=("strict_json_content", "fenced_strict_json"),
    )

    with pytest.raises(ActionKernelError, match="invalid_arguments"):
        client.complete(_canonical_request(tmp_path, capability_graph=build_workspace_browser_readonly_capability_graph()))

    telemetry = client.safe_diagnostics[-1]["canonical_decision_transport"]
    assert telemetry["typed_rejection_reason"] == "invalid_arguments"
    assert client.safe_diagnostics[-1]["mapped_action"] is None


def test_provider_failure_diagnostics_preserve_safe_auth_cause() -> None:
    with pytest.raises(CanonicalCoreError, match="credential_rejected_http_401"):
        cli._extract_canonical_json_decision(
            {
                "provider_failure": True,
                "provider_failure_category": "PROVIDER_AUTH_ERROR",
                "http_status": 401,
            }
        )

    with pytest.raises(CanonicalCoreError, match="model_or_workspace_unauthorized_http_403"):
        cli._extract_canonical_json_decision(
            {
                "provider_failure": True,
                "provider_failure_category": "PROVIDER_AUTH_ERROR",
                "http_status": 403,
            }
        )


def _canonical_request(
    tmp_path: Path,
    *,
    capability_graph: ExecutableCapabilityGraph | None = None,
) -> CanonicalDecisionRequest:
    workspace = _workspace(tmp_path)
    runtime = RootMissionRuntime(
        objective="Find needle.",
        workspace_root=workspace,
        provider_model="provider/model",
        capability_graph=capability_graph,
    )
    return CanonicalDecisionRequest(
        root_mission_id=runtime.root_mission_id,
        provider_model="provider/model",
        canonical_state=runtime.compile_state(),
        prompt_summary="test",
        cancellation_ref=runtime.cancellation_token.safe_ref,
    )


def _probe_route(
    operation: str,
    *,
    required: tuple[str, ...] = (),
    properties: dict[str, Any] | None = None,
) -> CanonicalCapabilityRoute:
    return CanonicalCapabilityRoute(
        capability="protocol_probe",
        operation=operation,
        executor_id=f"protocol_probe.{operation}",
        effect_kind=EffectKind.PROPOSAL,
        backend_mode="test_only_no_executor",
        required_authority="none",
        arguments_schema={
            "type": "object",
            "properties": properties or {},
            "required": list(required),
            "additionalProperties": False,
        },
        preconditions=("test_only",),
        readiness_probe="always_available",
        materiality_verifier="none",
        proof_contract="test_only",
        recovery_policy="none",
        cleanup_contract="none",
    )


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "src" / "pkg").mkdir(parents=True)
    (workspace / "notes").mkdir()
    (workspace / "src" / "pkg" / "module.py").write_text(
        "VALUE = 'needle from module'\n",
        encoding="utf-8",
    )
    (workspace / "notes" / "topic.md").write_text(
        "# Topic\n\nThe needle also appears in notes.\n",
        encoding="utf-8",
    )
    return workspace


def _draft():
    from sentinel.operator.models import MissionDraft

    return MissionDraft(
        title="Canonical core code sandbox boundary probe",
        objective="Probe whether code execution is physically confined.",
        constraints=["temporary canary only"],
        expected_artifacts=["typed probe result"],
    )


def _authority(mission_id: str, workspace: Path) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Canonical core code sandbox boundary probe",
        mission_objective="Probe whether code execution is physically confined.",
        allowed_tools=["code_execution_sandbox"],
        allowed_actions=["code_exec.run_profile"],
        forbidden_actions=["network", "credential_access", "package_install"],
        allowed_paths=[str(workspace)],
        max_actions=2,
        created_at=now,
        expires_at=now.replace(year=now.year + 1),
    )
