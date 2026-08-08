from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

_SOURCE_LINE_RE = re.compile(r"(?P<path>[\w./\\-]+\.py):\d+")


def _repo_root() -> Path:
    return Path(__file__).parents[5]


def _sentinel_control_root() -> Path:
    return Path(__file__).parents[4]


def _probe_module() -> Any:
    probe_path = (
        _sentinel_control_root()
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "sentinel_single_spine_c1_probe.py"
    )
    spec = importlib.util.spec_from_file_location("sentinel_single_spine_c1_probe", probe_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_source_locations(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_source_locations(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_source_locations(item) for item in value]
    if isinstance(value, str):
        return _SOURCE_LINE_RE.sub(lambda match: f"{match.group('path')}:<line>", value)
    return value


def test_c1_executable_mapping_artifacts_remain_preserved_historical_baseline() -> None:
    docs = _sentinel_control_root() / "docs" / "reviews" / "deep_power_audit"
    baseline_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_BASELINE.json"
    manifest_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MANIFEST.csv"
    report_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MAPPING_REPORT.md"

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    report = report_path.read_text(encoding="utf-8")
    joined_artifacts = "\n".join(
        [
            baseline_path.read_text(encoding="utf-8"),
            manifest_path.read_text(encoding="utf-8"),
            report,
        ]
    )

    assert len(rows) == baseline["component_count"] == 29
    assert all(component["evidence_present"] for component in baseline["components"])
    assert baseline["wave"] == "C1_EXECUTABLE_MAPPING"
    assert "C:\\" not in joined_artifacts
    assert "provider_calls = 0" in report
    assert "browser_runs = 0" in report
    assert "FIXED_PROVEN = 0/65" in report


def test_c1_executable_mapping_publishes_real_multi_spine_baseline() -> None:
    baseline_path = (
        _sentinel_control_root()
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_BASELINE.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    metrics = baseline["metrics"]

    assert metrics["executable_cognitive_spines"]["count"] == 2
    assert metrics["model_decision_loops"]["count"] == 4
    assert metrics["capability_registries"]["count"] == 3
    assert metrics["effect_dispatch_owners"]["count"] == 3
    assert metrics["public_entrypoint_bypasses"]["count"] == 5
    assert metrics["duplicate_workspace_backends"]["count"] == 2
    assert metrics["hardcoded_prompt_capability_lists"]["count"] == 1
    assert metrics["fake_material_success_routes"]["count"] == 2
    assert metrics["unclassified_effect_paths"]["count"] == 15
    assert baseline["provider_calls"] == 0
    assert baseline["browser_runs"] == 0


def test_c1_manifest_classifies_first_c2_candidates_without_deleting_them() -> None:
    manifest_path = (
        _sentinel_control_root()
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MANIFEST.csv"
    )
    rows = {row["component"]: row for row in csv.DictReader(manifest_path.open(encoding="utf-8"))}

    assert rows["public_cli_browser_demos"]["decision"] == "ARCHIVE_RESEARCH"
    assert rows["legacy_model_led_task_loop"]["decision"] == "MIGRATE"
    assert rows["root_runtime_workspace_effect_executor"]["decision"] == "MIGRATE"
    assert rows["cli_root_allowed_actions_list"]["decision"] == "MIGRATE"
    assert rows["local_channel_transport"]["decision"] == "MIGRATE"
    assert all(row["deletion_gate"] for row in rows.values())
    assert not any(row["decision"] == "DELETE" for row in rows.values())


def test_c2_qualified_callers_reject_textual_symbol_false_positives(tmp_path: Path) -> None:
    probe = _probe_module()
    source_root = tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    operator = source_root / "operator"
    operator.mkdir(parents=True)
    target = operator / "canonical_core.py"
    target.write_text(
        "class RootMissionRuntime:\n"
        "    def _execute(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    false_file = operator / "false_positive.py"
    false_file.write_text(
        "def _execute():\n"
        "    return 'local helper only'\n"
        "allowed_actions = ['workspace.read']\n"
        "ActionKernel = 'text only'\n"
        "MissionKernel = 'text only'\n",
        encoding="utf-8",
    )
    true_file = operator / "true_caller.py"
    true_file.write_text(
        "from sentinel.operator.canonical_core import RootMissionRuntime\n"
        "from sentinel.operator.action_kernel import ActionKernel as ProductKernel\n"
        "import sentinel.operator.kernel as kernel_mod\n\n"
        "class Runner:\n"
        "    def build(self):\n"
        "        runtime = RootMissionRuntime\n"
        "        product_kernel = ProductKernel()\n"
        "        mission_kernel = kernel_mod.MissionKernel(run_root='safe')\n"
        "        return runtime, product_kernel, mission_kernel\n",
        encoding="utf-8",
    )
    action_kernel = operator / "action_kernel.py"
    action_kernel.write_text("class ActionKernel:\n    pass\n", encoding="utf-8")
    kernel = operator / "kernel.py"
    kernel.write_text("class MissionKernel:\n    pass\n", encoding="utf-8")
    text_by_path = {
        path: path.read_text(encoding="utf-8")
        for path in (target, false_file, true_file, action_kernel, kernel)
    }

    execute_callers = probe.qualified_callers_for_symbol(tmp_path, "RootMissionRuntime", target, text_by_path)
    action_callers = probe.qualified_callers_for_symbol(tmp_path, "ActionKernel", action_kernel, text_by_path)
    mission_callers = probe.qualified_callers_for_symbol(tmp_path, "MissionKernel", kernel, text_by_path)

    assert all("false_positive.py" not in item["source"] for item in execute_callers)
    assert all("false_positive.py" not in item["source"] for item in action_callers)
    assert all("false_positive.py" not in item["source"] for item in mission_callers)
    assert action_callers == [
        {
            "caller": "sentinel.operator.true_caller::Runner.build",
            "source": "sentinel/operator/true_caller.py:8",
            "target": "sentinel.operator.action_kernel.ActionKernel",
            "call_kind": "constructor_call",
            "resolution": "QUALIFIED",
        }
    ]
    assert mission_callers == [
        {
            "caller": "sentinel.operator.true_caller::Runner.build",
            "source": "sentinel/operator/true_caller.py:9",
            "target": "sentinel.operator.kernel.MissionKernel",
            "call_kind": "attribute_call",
            "resolution": "QUALIFIED",
        }
    ]


def test_c2_qualified_callers_resolve_method_calls_on_typed_instances(tmp_path: Path) -> None:
    probe = _probe_module()
    source_root = tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    operator = source_root / "operator"
    operator.mkdir(parents=True)
    runtime_host = operator / "runtime_host.py"
    runtime_host.write_text(
        "class SentinelRuntimeHost:\n"
        "    def run_product_action_kernel_task_loop(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    caller = operator / "public_entrypoint.py"
    caller.write_text(
        "from sentinel.operator.runtime_host import SentinelRuntimeHost\n\n"
        "def run():\n"
        "    host = SentinelRuntimeHost()\n"
        "    alias = host\n"
        "    alias.run_product_action_kernel_task_loop()\n",
        encoding="utf-8",
    )
    false_file = operator / "false_positive.py"
    false_file.write_text(
        "class Other:\n"
        "    def run_product_action_kernel_task_loop(self):\n"
        "        pass\n\n"
        "def run(other):\n"
        "    other.run_product_action_kernel_task_loop()\n",
        encoding="utf-8",
    )
    text_by_path = {
        path: path.read_text(encoding="utf-8")
        for path in (runtime_host, caller, false_file)
    }

    callers = probe.qualified_callers_for_symbol(
        tmp_path,
        "run_product_action_kernel_task_loop",
        runtime_host,
        text_by_path,
    )

    assert callers == [
        {
            "caller": "sentinel.operator.public_entrypoint::run",
            "source": "sentinel/operator/public_entrypoint.py:6",
            "target": (
                "sentinel.operator.runtime_host.SentinelRuntimeHost."
                "run_product_action_kernel_task_loop"
            ),
            "call_kind": "method_call",
            "resolution": "QUALIFIED",
        }
    ]


def test_c2_pre_corrected_baseline_uses_discriminating_metric_semantics() -> None:
    baseline_path = (
        _sentinel_control_root()
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_BASELINE.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    metrics = baseline["metrics"]

    assert baseline["wave"] == "C1R_C2_PRE_EXECUTABLE_MAPPING"
    assert metrics["model_decision_loop"]["count"] == 4
    assert metrics["model_decision_client"]["count"] == 2
    assert "product_model_native_decision_client" not in metrics["model_decision_loop"]["components"]
    assert "real_provider_canonical_decision_client" not in metrics["model_decision_loop"]["components"]
    assert metrics["capability_registry"]["count"] == 2
    assert "workspace_read_capability_graph_builder" not in metrics["capability_registry"]["components"]
    assert metrics["duplicate_capability_backend"]["count"] == 0
    assert metrics["workspace_duplicate_owner_per_capability_id"]["count"] == 0
    assert metrics["public_entrypoint_bypass"]["count"] == 4
    assert metrics["canonical_product_run_bypass"]["count"] == 0
    assert metrics["hardcoded_cli_capability_list"]["count"] == 1
    assert all("/" in item for item in metrics["unclassified_effect_paths"]["components"])


def test_c2_pre_manifest_separates_host_class_and_cli_provider_duplicate() -> None:
    manifest_path = (
        _sentinel_control_root()
        / "docs"
        / "reviews"
        / "deep_power_audit"
        / "SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_MANIFEST.csv"
    )
    rows = {row["component"]: row for row in csv.DictReader(manifest_path.open(encoding="utf-8"))}

    assert rows["runtime_host_class"]["decision"] == "KEEP"
    assert rows["runtime_host_product_task_loop_method"]["decision"] == "MIGRATE_DELETE"
    assert rows["canonical_provider_request_builder"]["decision"] == "KEEP"
    assert rows["cli_private_real_provider_canonical_decision_client"]["decision"] == "MIGRATE_DELETE"
    assert rows["workspace_readonly_runtime"]["decision"] == "KEEP"
    assert rows["workspace_patch_runtime"]["decision"] == "KEEP"


def test_c2_workspace_compression_artifacts_match_current_source() -> None:
    repo_root = _repo_root()
    docs = _sentinel_control_root() / "docs" / "reviews" / "deep_power_audit"
    baseline_path = docs / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_BASELINE.json"
    manifest_path = docs / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_MANIFEST.csv"
    report_path = docs / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_REPORT.md"
    probe = _probe_module()

    expected = json.loads(json.dumps(probe.build_c2_workspace_compression_baseline(repo_root), sort_keys=True))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    report = report_path.read_text(encoding="utf-8")
    joined_artifacts = "\n".join(
        [
            baseline_path.read_text(encoding="utf-8"),
            manifest_path.read_text(encoding="utf-8"),
            report,
        ]
    )

    assert _normalize_source_locations(baseline) == _normalize_source_locations(expected)
    assert len(rows) == baseline["component_count"] == 28
    assert baseline["wave"] == "C2_WORKSPACE_COMPRESSION"
    assert baseline["c2_gates"]["canonical_product_run_bypass"] is False
    assert baseline["c2_gates"]["root_direct_workspace_effect_executor_absent"] is True
    assert baseline["c2_gates"]["hardcoded_cli_capability_list_absent"] is True
    assert baseline["c2_gates"]["public_canonical_legacy_action_envelope_usage_absent"] is True
    assert baseline["c2_gates"]["duplicate_owner_per_workspace_capability_id"] == 0
    assert baseline["c2_gates"]["fake_material_success_on_workspace_public_route"] == 0
    assert baseline["global_finding_counts"]["FIXED_PROVEN"] == "0/65"
    assert "C:\\" not in joined_artifacts
    assert "provider_calls = 0" in report
    assert "browser_runs = 0" in report


def test_c2_workspace_compression_gates_are_replayable_not_constant_defaults() -> None:
    repo_root = _repo_root()
    probe = _probe_module()
    baseline = probe.build_c2_workspace_compression_baseline(repo_root)
    evidence = baseline["c2_gate_evidence"]
    attestations = baseline["run_attestations"]

    product_gate = evidence["canonical_product_run_bypass"]
    assert product_gate["source"] == "behavioral_probe"
    assert product_gate["probe_status"] == "PASSED"
    assert product_gate["value"] is False
    assert product_gate["route_trace"]["root_mission_record_count"] == 1
    assert product_gate["route_trace"]["product_action_kernel_dispatch_count"] == 1
    assert product_gate["route_trace"]["receipt_linked_to_root"] is True
    assert product_gate["route_trace"]["observation_visible_to_next_turn"] is True

    fake_gate = evidence["fake_material_success_on_workspace_public_route"]
    assert fake_gate["source"] == "negative_behavioral_probe"
    assert fake_gate["probe_status"] == "PASSED"
    assert fake_gate["value"] == 0
    assert fake_gate["fake_backend_material_receipt_created"] is False

    assert attestations["provider_calls"] == {
        "value": 0,
        "status": "ZERO_RECORDED",
        "source": "scripted_local_behavioral_probe",
    }
    assert attestations["browser_runs"] == {
        "value": 0,
        "status": "ZERO_RECORDED",
        "source": "workspace_only_behavioral_probe",
    }


def test_c2_workspace_owner_metric_is_derived_from_executable_graph() -> None:
    repo_root = _repo_root()
    probe = _probe_module()
    baseline = probe.build_c2_workspace_compression_baseline(repo_root)
    owner_metric = baseline["metrics"]["workspace_duplicate_owner_per_capability_id"]

    assert owner_metric["source"] == "ExecutableCapabilityGraph.routes"
    assert owner_metric["count"] == 0
    assert set(owner_metric["owners_by_capability"]) >= {
        "workspace.list",
        "workspace.read",
        "workspace.search",
        "sentinel_loop.finish",
    }
    for capability_id in ("workspace.list", "workspace.read", "workspace.search"):
        owner = owner_metric["owners_by_capability"][capability_id][0]
        assert owner["registration_source"] == "ExecutableCapabilityGraph.routes"
        assert owner["callable_owner"] == "ProductActionKernel:workspace"
        assert owner["authority_schema"] == "workspace_read"
        assert owner["backend"] == "workspace_read_only"
        assert owner["receipt_contract"] == "canonical_core_workspace_receipt_v1"


def test_c2_workspace_metrics_split_unmigrated_surfaces_from_proven_bypasses() -> None:
    repo_root = _repo_root()
    probe = _probe_module()
    baseline = probe.build_c2_workspace_compression_baseline(repo_root)
    metrics = baseline["metrics"]

    assert "public_entrypoint_bypass" not in metrics
    assert metrics["proven_public_effect_bypasses"]["count"] == 0
    assert "public_cli_canonical_product_run" not in metrics["unmigrated_public_surfaces"]["components"]
    assert "public_cli_cockpit_chat" in metrics["unmigrated_public_surfaces"]["components"]
    assert metrics["unknown_public_routes"]["count"] >= 0
    assert "hardcoded_cli_capability_list" not in metrics
    assert metrics["public_canonical_route_hardcoded_capability_list"]["count"] == 0
    assert metrics["other_hardcoded_capability_surfaces"]["count"] >= 0
    assert metrics["authority_allowed_actions_fields"]["count"] >= 1


def test_c3_product_loop_artifacts_are_replayable_and_classified() -> None:
    repo_root = _repo_root()
    docs = _sentinel_control_root() / "docs" / "reviews" / "deep_power_audit"
    baseline_path = docs / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_BASELINE.json"
    manifest_path = docs / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_MANIFEST.csv"
    report_path = docs / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_REPORT.md"
    probe = _probe_module()

    expected = json.loads(json.dumps(probe.build_c3_product_loop_compression_baseline(repo_root), sort_keys=True))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    report = report_path.read_text(encoding="utf-8")
    joined_artifacts = "\n".join(
        [
            baseline_path.read_text(encoding="utf-8"),
            manifest_path.read_text(encoding="utf-8"),
            report,
        ]
    )

    baseline_for_compare = json.loads(json.dumps(baseline, sort_keys=True))
    expected_for_compare = json.loads(json.dumps(expected, sort_keys=True))
    for payload in (baseline_for_compare, expected_for_compare):
        taxonomy = payload["head_taxonomy"]
        taxonomy["artifact_generation_head"] = "<runtime-dependent>"
        taxonomy["current_worktree_head"] = "<runtime-dependent>"
        taxonomy["current_remote_head"] = "<runtime-dependent>"
    assert _normalize_source_locations(baseline_for_compare) == _normalize_source_locations(expected_for_compare)
    assert baseline["wave"] == "C3_PRODUCT_LOOP_AND_DECISION_CLIENT_COMPRESSION"
    assert baseline["current_phase"] == "C3S_REPLAYABLE_PROOF_SEAL"
    assert baseline["head_taxonomy"]["current_worktree_head"]
    assert baseline["head_taxonomy"]["implementation_tested_head"] == "88ee94f1768c962246b54c918b27dd4374a29a5e"
    assert baseline["head_taxonomy"]["documentation_head"] == "b7c24e0a5baecd43fbb317cb0ddfc16743da0a58"
    assert baseline["commit_taxonomy"]["deletion_commits"] == ["88ee94f1768c962246b54c918b27dd4374a29a5e"]

    evidence = baseline["c3_gate_evidence"]
    for gate in (
        "product_workspace_cognition_loops",
        "production_canonical_decision_clients",
        "runtimehost_cognitive_methods_on_migrated_routes",
        "legacy_action_envelope_usage_in_product_core",
        "canonical_product_run_bypass",
        "canonical_dev_run_bypass",
        "workspace_duplicate_owner_per_capability_id",
        "fake_material_success_on_migrated_surfaces",
        "proof_root_linked_to_root_mission_record",
    ):
        item = evidence[gate]
        assert item["evidence_class"] in {
            "STATIC_PROBE",
            "BEHAVIORAL_PROBE",
            "NEGATIVE_BEHAVIORAL_PROBE",
            "RUN_ATTESTATION",
        }
        assert item["status"] in {"PASS", "RECORDED"}
        assert item["source_location"]

    assert baseline["run_attestations"]["provider_calls"] == {
        "value": 0,
        "status": "ZERO_RECORDED",
        "evidence_class": "RUN_ATTESTATION",
        "source": "C3 migrated-surface scripted local probe",
    }
    assert baseline["run_attestations"]["browser_runs"] == {
        "value": 0,
        "status": "ZERO_RECORDED",
        "evidence_class": "RUN_ATTESTATION",
        "source": "C3 workspace-only migrated-surface probe",
    }
    assert baseline["qualified_callers_and_deletions"]["unknown_remaining"] == []
    assert {
        item["symbol"] for item in baseline["qualified_callers_and_deletions"]["deleted_symbols"]
    } >= {
        "sentinel.cli::_RealProviderCanonicalDecisionClient",
        "sentinel.operator.canonical_core::RootMissionRuntime._action_envelope_for_decision",
    }
    assert all(row["source"] != "derived" for row in rows)
    assert "## Gate Evidence Classes" in report
    assert "## Qualified Callers And Deletions" in report
    assert "C:\\" not in joined_artifacts
    assert "provider_calls = 0" in report
    assert "browser_runs = 0" in report


def test_c4_browser_readonly_cutover_artifacts_match_current_source() -> None:
    repo_root = _repo_root()
    docs = _sentinel_control_root() / "docs" / "reviews" / "deep_power_audit"
    baseline_path = docs / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_BASELINE.json"
    manifest_path = docs / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_MANIFEST.csv"
    report_path = docs / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_REPORT.md"
    probe = _probe_module()

    expected = json.loads(json.dumps(probe.build_c4_browser_readonly_cutover_baseline(repo_root), sort_keys=True))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    report = report_path.read_text(encoding="utf-8")
    joined_artifacts = "\n".join(
        [
            baseline_path.read_text(encoding="utf-8"),
            manifest_path.read_text(encoding="utf-8"),
            report,
        ]
    )

    baseline_for_compare = json.loads(json.dumps(baseline, sort_keys=True))
    expected_for_compare = json.loads(json.dumps(expected, sort_keys=True))
    for payload in (baseline_for_compare, expected_for_compare):
        taxonomy = payload["head_taxonomy"]
        taxonomy["artifact_generation_head"] = "<runtime-dependent>"
        taxonomy["current_worktree_head"] = "<runtime-dependent>"
        taxonomy["current_remote_head"] = "<runtime-dependent>"
    assert baseline_for_compare == expected_for_compare
    assert baseline["wave"] == "C4_BROWSER_READONLY_SINGLE_SPINE_CUTOVER"
    assert baseline["provider_calls"] == 0
    assert baseline["real_browser_runs"] == 0
    assert baseline["external_network_calls"] == 0
    assert baseline["global_finding_counts"]["FIXED_PROVEN"] == "0/65"
    gates = baseline["c4_gates"]
    assert gates["shared_product_browser_cognition_loops"] == 1
    assert gates["browser_specific_public_cognition_loops"] == 0
    assert gates["production_canonical_decision_clients"] == 1
    assert gates["browser_capability_registries"] == 1
    assert gates["browser_duplicate_owner_per_capability_id"] == 0
    assert gates["browser_effect_dispatch_owner"] == "ProductActionKernel"
    assert gates["browser_authority_denial_before_backend"] is True
    assert gates["browser_observation_visible_next_model_turn"] is True
    assert gates["browser_receipt_linked_to_root_mission_record"] is True
    assert gates["browser_environment_secret_leaks"] == 0
    assert gates["browser_fake_material_success"] == 0
    assert gates["canonical_browser_public_bypass"] is False
    assert gates["physical_browser_boundaries"] == "NOT_RUN"
    assert baseline["behavioral_probe"]["probe_status"] == "PASSED"
    assert baseline["guard_probe"]["provider_calls"] == 0
    assert baseline["guard_probe"]["real_browser_runs"] == 0
    assert baseline["guard_probe"]["external_network_calls"] == 0
    assert rows
    assert {row["decision"] for row in rows} >= {"KEEP", "MIGRATE", "ARCHIVE_RESEARCH"}
    assert "BrowserEnvironmentState" in report
    assert "physical Browser boundaries = NOT_RUN" in report
    assert "C:\\" not in joined_artifacts
    assert "provider_calls = 0" in report
    assert "browser_runs = 0" in report
