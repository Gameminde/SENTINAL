from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


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

    assert baseline == expected
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
