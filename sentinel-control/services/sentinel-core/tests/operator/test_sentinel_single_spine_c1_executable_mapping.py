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


def test_c1_executable_mapping_artifacts_match_current_source() -> None:
    repo_root = _repo_root()
    docs = _sentinel_control_root() / "docs" / "reviews" / "deep_power_audit"
    baseline_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_BASELINE.json"
    manifest_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MANIFEST.csv"
    report_path = docs / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MAPPING_REPORT.md"
    probe = _probe_module()

    expected = json.loads(json.dumps(probe.build_baseline(repo_root), sort_keys=True))
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
    assert len(rows) == baseline["component_count"] == 29
    assert all(component["evidence_present"] for component in baseline["components"])
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
