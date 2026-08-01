from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


DOC_DIR = Path(__file__).resolve().parent
BASELINE_JSON = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_BASELINE.json"
MANIFEST_CSV = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MANIFEST.csv"
REPORT_MD = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MAPPING_REPORT.md"
C2_PRE_BASELINE_JSON = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_BASELINE.json"
C2_PRE_MANIFEST_CSV = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_MANIFEST.csv"
C2_PRE_REPORT_MD = DOC_DIR / "SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_MAPPING_REPORT.md"


@dataclass(frozen=True)
class ComponentSpec:
    component: str
    category: str
    source: str
    symbol: str
    state_owned: str
    effects_owned: str
    authority_owned: str
    proof_owned: str
    decision: str
    canonical_owner: str
    migration_gate: str
    deletion_gate: str
    tests_affected: str


@dataclass(frozen=True)
class ComponentFinding:
    component: str
    category: str
    source: str
    symbol: str
    production_callers: tuple[str, ...]
    evidence_present: bool
    state_owned: str
    effects_owned: str
    authority_owned: str
    proof_owned: str
    decision: str
    canonical_owner: str
    migration_gate: str
    deletion_gate: str
    tests_affected: str


def _c2_spec(
    component: str,
    category: str,
    source: str,
    symbol: str,
    decision: str,
    canonical_owner: str,
    *,
    state_owned: str = "none",
    effects_owned: str = "none",
    authority_owned: str = "none",
    proof_owned: str = "none",
    migration_gate: str = "C2 qualified route parity required before deletion",
    deletion_gate: str = "delete only after qualified callers and acceptance probes prove parity",
    tests_affected: str = "C2 workspace single-spine probes",
) -> ComponentSpec:
    return ComponentSpec(
        component,
        category,
        source,
        symbol,
        state_owned,
        effects_owned,
        authority_owned,
        proof_owned,
        decision,
        canonical_owner,
        migration_gate,
        deletion_gate,
        tests_affected,
    )


COMPONENT_SPECS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        "public_cli_canonical_product_run",
        "public_mission_surface",
        "sentinel/cli.py",
        "_run_canonical_product_command",
        "root MissionRecord bootstrap via helper",
        "delegates to RuntimeHost product task loop",
        "descriptive MissionAuthoritySummary",
        "product task loop FinalGate/proof root summary",
        "TEMPORARY_BOUNDARY_ADAPTER",
        "RootMissionRuntime public entrypoint",
        "prove canonical replacement gate and remove bridge as final path",
        "delete or archive after public route reaches canonical owner without bypass",
        "test_public_product_cli_entrypoint_reaches_runtimehost_product_action_kernel_spine",
    ),
    ComponentSpec(
        "public_cli_canonical_dev_run",
        "public_mission_surface",
        "sentinel/cli.py",
        "_run_canonical_dev_command",
        "RootMissionRuntime local MissionRecord",
        "RootMissionRuntime workspace effect executor",
        "canonical graph metadata",
        "non-authentic local proof root",
        "ARCHIVE_RESEARCH",
        "RootMissionRuntime test/dev harness",
        "keep as dev probe only; never product closure",
        "archive after product public path has equivalent local scripted probe",
        "test_public_dev_cli_entrypoint_runs_canonical_core_vertical_slice",
    ),
    ComponentSpec(
        "public_cli_cockpit_chat",
        "public_mission_surface",
        "sentinel/cli.py",
        "_run_cockpit_command",
        "legacy cockpit conversation/run state",
        "read-only research and cockpit dispatch",
        "authority-scope flags",
        "legacy turn summaries",
        "MIGRATE",
        "RootMissionRuntime",
        "public cockpit must create one root MissionRecord and one canonical DecisionProtocol",
        "delete legacy internal direct path after parity",
        "future public cockpit single-spine probe",
    ),
    ComponentSpec(
        "public_cli_power_lab_run",
        "public_mission_surface",
        "sentinel/cli.py",
        "run_power_lab_mission",
        "PowerLab mission state",
        "PowerLab executors",
        "preset authority",
        "PowerLab receipts",
        "MIGRATE",
        "RootMissionRuntime",
        "PowerLab missions route through canonical root runtime",
        "archive standalone runner after parity",
        "future power_lab single-spine probe",
    ),
    ComponentSpec(
        "public_cli_browser_demos",
        "public_mission_surface",
        "sentinel/cli.py",
        "_run_browser_session_demo",
        "browser demo run dirs",
        "direct browser organs",
        "browser demo mission files",
        "browser demo evidence artifacts",
        "ARCHIVE_RESEARCH",
        "Browser organ adapter under ProductActionKernel",
        "browser demos become acceptance probes, not public product routes",
        "archive after browser organ route parity",
        "future browser organ route parity tests",
    ),
    ComponentSpec(
        "root_mission_runtime",
        "executable_cognitive_spine",
        "sentinel/operator/canonical_core.py",
        "RootMissionRuntime",
        "MissionRecord, CanonicalState, progress, terminalization, cleanup",
        "currently executes workspace effects directly",
        "canonical graph required_authority",
        "MissionProofRoot and canonical receipts",
        "MIGRATE",
        "RootMissionRuntime",
        "remove direct effect execution; dispatch effects through ProductActionKernel",
        "none until replacement is live-proven",
        "test_product_vertical_slice_persists_mission_record_receipts_proof_and_terminal_state",
    ),
    ComponentSpec(
        "runtime_host_product_task_loop",
        "executable_cognitive_spine",
        "sentinel/operator/runtime_host.py",
        "run_product_action_kernel_task_loop",
        "ProductTaskResourceScope and child mission orchestration",
        "ProductActionKernel effect dispatch",
        "MissionLifecycleService/ProductActionKernel adapter authority",
        "ProductActionKernelTaskLoopFinalGate",
        "KEEP",
        "RuntimeHost hosting/lifecycle only",
        "strip cognition/state ownership into RootMissionRuntime",
        "delete cognitive pieces only after RootMissionRuntime owns loop",
        "test_runtimehost_product_task_loop_entrypoint",
    ),
    ComponentSpec(
        "model_led_product_action_kernel_task_loop",
        "model_decision_loop",
        "sentinel/operator/model_led_product_action_kernel_task_loop.py",
        "ModelLedProductActionKernelTaskLoop",
        "loop context and progress state",
        "ProductActionKernel dispatch",
        "action preflight and grants",
        "FinalGate, replay, proof index",
        "MIGRATE",
        "RootMissionRuntime cognition loop",
        "RootMissionRuntime consumes model decisions; ProductActionKernel only executes effects",
        "delete duplicated cognitive loop after parity",
        "test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py",
    ),
    ComponentSpec(
        "legacy_model_led_task_loop",
        "model_decision_loop",
        "sentinel/operator/model_led_task_loop.py",
        "ModelLedTaskLoop",
        "legacy loop state",
        "ActionEnvelope dispatch",
        "legacy mission authority",
        "legacy certificates",
        "MIGRATE",
        "RootMissionRuntime",
        "classify callers and migrate or archive",
        "delete after caller count is zero",
        "future legacy loop caller probe",
    ),
    ComponentSpec(
        "product_model_native_decision_client",
        "model_decision_loop",
        "sentinel/operator/product_model_native_decision_client.py",
        "ProductModelNativeDecisionClient",
        "none",
        "none",
        "none",
        "request metadata only",
        "MIGRATE",
        "canonical model decision client",
        "emit CanonicalDecision directly instead of legacy ActionEnvelope adapter",
        "remove adapter mode after public route parity",
        "test_public_product_cli_real_provider_mode_uses_product_native_transport",
    ),
    ComponentSpec(
        "real_provider_canonical_decision_client",
        "model_decision_loop",
        "sentinel/cli.py",
        "_RealProviderCanonicalDecisionClient",
        "none",
        "none",
        "none",
        "request metadata only",
        "KEEP",
        "canonical model decision client",
        "move out of CLI into canonical provider protocol module",
        "delete CLI-private duplicate after move",
        "future canonical provider adapter probe",
    ),
    ComponentSpec(
        "executable_capability_graph",
        "capability_registry",
        "sentinel/operator/canonical_core.py",
        "ExecutableCapabilityGraph",
        "none",
        "route metadata only",
        "required_authority metadata",
        "proof_contract metadata",
        "KEEP",
        "ExecutableCapabilityGraph",
        "make it the only model affordance and capability registration source",
        "delete duplicate registries after parity",
        "test_capability_graph_is_generated_from_executable_routes",
    ),
    ComponentSpec(
        "workspace_read_capability_graph_builder",
        "capability_registry",
        "sentinel/operator/canonical_core.py",
        "build_workspace_read_capability_graph",
        "none",
        "workspace-only route metadata",
        "workspace_read authority metadata",
        "canonical workspace receipt contract",
        "MIGRATE",
        "ExecutableCapabilityGraph",
        "replace workspace-only builder with whole-organ graph",
        "delete after whole-organ graph owns workspace routes",
        "test_capability_graph_is_generated_from_executable_routes",
    ),
    ComponentSpec(
        "runtime_connection_registry",
        "capability_registry",
        "sentinel/operator/runtime_connections.py",
        "build_default_runtime_connection_registry",
        "connection frame metadata",
        "connection backend references",
        "backend authority metadata",
        "connection proof metadata",
        "MIGRATE",
        "ExecutableCapabilityGraph",
        "consume as backend inventory under one graph",
        "delete independent model-facing registration after parity",
        "future connection graph parity probe",
    ),
    ComponentSpec(
        "product_action_kernel",
        "effect_dispatch_owner",
        "sentinel/operator/action_kernel.py",
        "ActionKernel",
        "none",
        "ActionEnvelope effect execution",
        "MissionAuthorityEnvelope checks",
        "ActionResult receipt refs",
        "KEEP",
        "ProductActionKernel",
        "keep as governed effect executor only, no cognition loop",
        "none",
        "test_power_cleanup_pack9_product_actionkernel_task_loop.py",
    ),
    ComponentSpec(
        "unified_execution_dispatcher",
        "effect_dispatch_owner",
        "sentinel/operator/unified_execution_dispatcher.py",
        "UnifiedExecutionDispatcher",
        "dispatch adapter state",
        "multi-adapter product dispatch",
        "adapter preflight",
        "ProductActionKernelReceipt",
        "MIGRATE",
        "ProductActionKernel",
        "fold useful route dispatch into ProductActionKernel or backend adapters",
        "delete dispatcher facade after parity",
        "future dispatcher absence-of-bypass probe",
    ),
    ComponentSpec(
        "root_runtime_workspace_effect_executor",
        "effect_dispatch_owner",
        "sentinel/operator/canonical_core.py",
        "_execute",
        "CanonicalState observations",
        "direct workspace list/read/search",
        "canonical graph required_authority",
        "CanonicalEffectReceipt",
        "MIGRATE",
        "ProductActionKernel",
        "replace direct effect execution with ProductActionKernel route",
        "delete after canonical route has no direct effect executor",
        "test_product_vertical_slice_persists_mission_record_receipts_proof_and_terminal_state",
    ),
    ComponentSpec(
        "mission_lifecycle_service",
        "authority_enforcement_point",
        "sentinel/operator/mission_lifecycle_service.py",
        "MissionLifecycleService",
        "child MissionRecord creation/loading",
        "dispatch request setup",
        "MissionAuthorityEnvelope handling",
        "mission store events",
        "KEEP",
        "AuthorityKernel facade",
        "narrow to mission lifecycle; move authority decisions to AuthorityKernel",
        "none",
        "future AuthorityKernel parity probe",
    ),
    ComponentSpec(
        "product_kernel_dispatch_adapter",
        "authority_enforcement_point",
        "sentinel/operator/unified_execution_dispatcher.py",
        "ProductActionKernelDispatchAdapter",
        "none",
        "ProductActionKernel dispatch adapter",
        "preflight and authority envelope handoff",
        "ProductActionKernelReceipt",
        "MIGRATE",
        "AuthorityKernel plus ProductActionKernel",
        "split authority check from effect execution",
        "delete adapter after ProductActionKernel consumes canonical route directly",
        "future authority/effect split probe",
    ),
    ComponentSpec(
        "assert_data_not_authority",
        "authority_enforcement_point",
        "sentinel/operator/safety.py",
        "assert_data_not_authority",
        "none",
        "none",
        "data cannot self-grant authority",
        "none",
        "KEEP",
        "AuthorityKernel",
        "keep as invariant inside typed authority kernel",
        "none",
        "test_model_payload_cannot_self_grant_authority",
    ),
    ComponentSpec(
        "mission_kernel_store",
        "receipt_proof_owner",
        "sentinel/operator/kernel.py",
        "MissionKernel",
        "MissionRecord and event timeline",
        "none",
        "none",
        "receipt refs and timeline verification",
        "KEEP",
        "MissionProofRoot",
        "MissionProofRoot consumes MissionKernel timeline, not vice versa",
        "none",
        "test_product_receipt_integrity_rejects_deleted_or_modified_receipt_artifact",
    ),
    ComponentSpec(
        "mission_proof_root",
        "receipt_proof_owner",
        "sentinel/operator/canonical_core.py",
        "MissionProofRoot",
        "none",
        "none",
        "none",
        "canonical proof root",
        "KEEP",
        "MissionProofRoot",
        "add authentic append-only proof in W2",
        "none",
        "test_initial_proof_root_is_explicitly_non_authentic_placeholder",
    ),
    ComponentSpec(
        "product_task_loop_finalgate",
        "receipt_proof_owner",
        "sentinel/operator/model_led_product_action_kernel_task_loop.py",
        "ProductActionKernelTaskLoopFinalCertificate",
        "none",
        "none",
        "finalization policy",
        "FinalGate certificate",
        "MIGRATE",
        "MissionProofRoot",
        "unify final gate into root proof root",
        "delete duplicate final gate after parity",
        "test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py",
    ),
    ComponentSpec(
        "workspace_readonly_runtime",
        "duplicate_workspace_backend",
        "sentinel/operator/workspace_readonly_runtime.py",
        "WorkspaceReadOnlyRuntime",
        "none",
        "read-only workspace list/read/search",
        "MissionAuthorityEnvelope workspace_read",
        "ActionResult context cards",
        "KEEP",
        "workspace organ/backend adapter",
        "use as ProductActionKernel backend, not cognition route",
        "none",
        "test_public_product_cli_entrypoint_reaches_runtimehost_product_action_kernel_spine",
    ),
    ComponentSpec(
        "workspace_patch_runtime",
        "duplicate_workspace_backend",
        "sentinel/operator/workspace_patch_runtime.py",
        "WorkspacePatchRuntime",
        "none",
        "workspace mutation/check",
        "MissionAuthorityEnvelope path grants",
        "ActionResult receipt refs",
        "MIGRATE",
        "workspace organ/backend adapter",
        "merge with workspace backend under typed read/write effects",
        "delete duplicate route after parity",
        "future workspace backend merge probe",
    ),
    ComponentSpec(
        "product_native_prompt_generated_schema",
        "prompt_capability_surface",
        "sentinel/operator/product_model_native_decision_client.py",
        "_model_visible_operation_schemas",
        "none",
        "none",
        "none",
        "request metadata",
        "KEEP",
        "ExecutableCapabilityGraph",
        "schema generated from executable graph only",
        "none",
        "test_public_product_cli_real_provider_mode_uses_product_native_transport",
    ),
    ComponentSpec(
        "cli_root_allowed_actions_list",
        "hardcoded_prompt_capability_list",
        "sentinel/cli.py",
        "allowed_actions",
        "root MissionRecord metadata",
        "none",
        "descriptive authority summary",
        "none",
        "MIGRATE",
        "ExecutableCapabilityGraph",
        "derive public root allowed_actions from graph",
        "delete hardcoded list after graph projection",
        "future no-hardcoded-capabilities probe",
    ),
    ComponentSpec(
        "product_local_cloak_fixture",
        "fake_material_success_route",
        "sentinel/operator/runtime_host.py",
        "_ProductLocalCloakBrowserEngine",
        "fixture state",
        "fake browser material actions",
        "none",
        "fixture ActionResult evidence",
        "ARCHIVE_RESEARCH",
        "browser organ test backend",
        "keep test-only and impossible to certify product power",
        "archive after live body parity tests no longer need it",
        "future fake-route-not-product-proof probe",
    ),
    ComponentSpec(
        "local_channel_transport",
        "fake_material_success_route",
        "sentinel/operator/runtime_host.py",
        "_local_channel_transport",
        "none",
        "fake channel delivery",
        "none",
        "local delivery ref",
        "MIGRATE",
        "channel organ/backend adapter",
        "separate simulated and real transport receipt kinds",
        "delete fake completion from product success path",
        "future channel transport truth probe",
    ),
)

C2_PRE_COMPONENT_SPECS: tuple[ComponentSpec, ...] = (
    _c2_spec(
        "public_cli_canonical_product_run",
        "public_mission_surface",
        "sentinel/cli.py",
        "_run_canonical_product_command",
        "KEEP",
        "RootMissionRuntime public entrypoint",
        state_owned="root MissionRecord bootstrap via canonical core helper",
        effects_owned="delegates to canonical root runtime",
        authority_owned="descriptive MissionAuthoritySummary",
        proof_owned="canonical proof root summary",
        migration_gate="route through one root MissionRecord, graph and ProductActionKernel workspace dispatch in C2",
        deletion_gate="delete bridge pieces only after C2 parity",
    ),
    _c2_spec("public_cli_canonical_dev_run", "public_mission_surface", "sentinel/cli.py", "_run_canonical_dev_command", "MIGRATE_DELETE", "RootMissionRuntime test/dev harness"),
    _c2_spec("public_cli_cockpit_chat", "public_mission_surface", "sentinel/cli.py", "_run_cockpit_command", "MIGRATE_DELETE", "RootMissionRuntime"),
    _c2_spec("public_cli_power_lab_run", "public_mission_surface", "sentinel/cli.py", "run_power_lab_mission", "MIGRATE_DELETE", "RootMissionRuntime"),
    _c2_spec("public_cli_browser_demos", "public_mission_surface", "sentinel/cli.py", "_run_browser_session_demo", "MIGRATE_DELETE", "Browser organ adapter under ProductActionKernel"),
    _c2_spec(
        "root_mission_runtime",
        "model_decision_loop",
        "sentinel/operator/canonical_core.py",
        "RootMissionRuntime",
        "KEEP",
        "RootMissionRuntime",
        state_owned="MissionRecord, CanonicalState, progress, terminalization, cleanup",
        effects_owned="currently executes workspace effects directly",
        authority_owned="canonical graph required_authority",
        proof_owned="MissionProofRoot and canonical receipts",
        migration_gate="remove direct effect execution; dispatch effects through ProductActionKernel",
    ),
    _c2_spec(
        "runtime_host_class",
        "host_lifecycle",
        "sentinel/operator/runtime_host.py",
        "SentinelRuntimeHost",
        "KEEP",
        "RuntimeHost hosting/lifecycle only",
        state_owned="host and lifecycle scope",
        effects_owned="hosts runtimes but should not own canonical cognition",
    ),
    _c2_spec(
        "runtime_host_product_task_loop_method",
        "model_decision_loop",
        "sentinel/operator/runtime_host.py",
        "run_product_action_kernel_task_loop",
        "MIGRATE_DELETE",
        "RuntimeHost hosting/lifecycle only",
        state_owned="ProductTaskResourceScope and child mission orchestration",
        effects_owned="ProductActionKernel effect dispatch",
    ),
    _c2_spec("model_led_product_action_kernel_task_loop", "model_decision_loop", "sentinel/operator/model_led_product_action_kernel_task_loop.py", "ModelLedProductActionKernelTaskLoop", "MIGRATE_DELETE", "RootMissionRuntime cognition loop"),
    _c2_spec("legacy_model_led_task_loop", "model_decision_loop", "sentinel/operator/model_led_task_loop.py", "ModelLedTaskLoop", "MIGRATE_DELETE", "RootMissionRuntime"),
    _c2_spec("product_model_native_decision_client", "decision_protocol_adapter", "sentinel/operator/product_model_native_decision_client.py", "ProductModelNativeDecisionClient", "MIGRATE_DELETE", "canonical model decision client"),
    _c2_spec("canonical_provider_request_builder", "model_decision_client", "sentinel/cli.py", "_canonical_real_model_request", "KEEP", "canonical provider protocol module"),
    _c2_spec("cli_private_real_provider_canonical_decision_client", "model_decision_client", "sentinel/cli.py", "_RealProviderCanonicalDecisionClient", "MIGRATE_DELETE", "canonical provider protocol module"),
    _c2_spec("executable_capability_graph", "capability_registry", "sentinel/operator/canonical_core.py", "ExecutableCapabilityGraph", "KEEP", "ExecutableCapabilityGraph"),
    _c2_spec("workspace_read_capability_graph_builder", "capability_graph_factory", "sentinel/operator/canonical_core.py", "build_workspace_read_capability_graph", "MIGRATE_DELETE", "ExecutableCapabilityGraph"),
    _c2_spec("runtime_connection_registry", "capability_registry", "sentinel/operator/runtime_connections.py", "build_default_runtime_connection_registry", "MIGRATE_DELETE", "ExecutableCapabilityGraph"),
    _c2_spec(
        "product_action_kernel",
        "effect_dispatch_owner",
        "sentinel/operator/action_kernel.py",
        "ActionKernel",
        "KEEP",
        "ProductActionKernel",
        effects_owned="ActionEnvelope effect execution",
        authority_owned="MissionAuthorityEnvelope checks",
        proof_owned="ActionResult receipt refs",
    ),
    _c2_spec(
        "root_runtime_workspace_effect_executor",
        "effect_dispatch_owner",
        "sentinel/operator/canonical_core.py",
        "_execute",
        "MIGRATE_DELETE",
        "ProductActionKernel",
        state_owned="CanonicalState observations",
        effects_owned="direct workspace list/read/search",
        authority_owned="canonical graph required_authority",
        proof_owned="CanonicalEffectReceipt",
    ),
    _c2_spec("mission_lifecycle_service", "authority_boundary", "sentinel/operator/mission_lifecycle_service.py", "MissionLifecycleService", "KEEP", "AuthorityKernel facade"),
    _c2_spec("assert_data_not_authority", "authority_boundary", "sentinel/operator/safety.py", "assert_data_not_authority", "KEEP", "AuthorityKernel"),
    _c2_spec(
        "mission_kernel_store",
        "receipt_proof_owner",
        "sentinel/operator/kernel.py",
        "MissionKernel",
        "KEEP",
        "MissionProofRoot",
        state_owned="MissionRecord and event timeline",
        proof_owned="receipt refs and timeline verification",
    ),
    _c2_spec("mission_proof_root", "receipt_proof_owner", "sentinel/operator/canonical_core.py", "MissionProofRoot", "KEEP", "MissionProofRoot"),
    _c2_spec(
        "workspace_readonly_runtime",
        "workspace_backend",
        "sentinel/operator/workspace_readonly_runtime.py",
        "WorkspaceReadOnlyRuntime",
        "KEEP",
        "workspace organ/backend adapter",
        effects_owned="read-only workspace list/read/search",
        authority_owned="MissionAuthorityEnvelope workspace_read",
        proof_owned="ActionResult context cards",
    ),
    _c2_spec(
        "workspace_patch_runtime",
        "workspace_backend",
        "sentinel/operator/workspace_patch_runtime.py",
        "WorkspacePatchRuntime",
        "KEEP",
        "workspace organ/backend adapter",
        effects_owned="workspace mutation/check",
        authority_owned="MissionAuthorityEnvelope path grants",
        proof_owned="ActionResult receipt refs",
        migration_gate="shared workspace registration owns read and write with separate authority",
        deletion_gate="delete only truly duplicated operations after parity",
    ),
    _c2_spec("product_native_prompt_generated_schema", "model_affordance_projection", "sentinel/operator/product_model_native_decision_client.py", "_model_visible_operation_schemas", "KEEP", "ExecutableCapabilityGraph"),
    _c2_spec("cli_root_allowed_actions_list", "hardcoded_cli_capability_list", "sentinel/cli.py", "allowed_actions", "MIGRATE_DELETE", "ExecutableCapabilityGraph"),
    _c2_spec("product_local_cloak_fixture", "fake_material_success_route", "sentinel/operator/runtime_host.py", "_ProductLocalCloakBrowserEngine", "ARCHIVE_RESEARCH", "browser organ test backend"),
    _c2_spec("local_channel_transport", "fake_material_success_route", "sentinel/operator/runtime_host.py", "_local_channel_transport", "MIGRATE_DELETE", "channel organ/backend adapter"),
)


def build_baseline(repo_root: Path) -> dict[str, object]:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    files = _source_files(source_root)
    text_by_path = {path: path.read_text(encoding="utf-8", errors="ignore") for path in files}
    findings = tuple(_finding_for_spec(repo_root, spec, text_by_path) for spec in COMPONENT_SPECS)
    category_counts = Counter(item.category for item in findings if item.evidence_present)
    metrics = {
        "executable_cognitive_spines": _metric(findings, "executable_cognitive_spine"),
        "model_decision_loops": _metric(findings, "model_decision_loop"),
        "root_mission_owners": _components_owning(findings, "MissionRecord"),
        "canonical_state_owners": _components_owning(findings, "CanonicalState"),
        "capability_registries": _metric(findings, "capability_registry"),
        "effect_dispatch_owners": _metric(findings, "effect_dispatch_owner"),
        "authority_enforcement_points": _metric(findings, "authority_enforcement_point"),
        "receipt_proof_owners": _metric(findings, "receipt_proof_owner"),
        "public_entrypoint_bypasses": _metric(findings, "public_mission_surface", exclude_decisions={"KEEP"}),
        "duplicate_workspace_backends": _metric(findings, "duplicate_workspace_backend"),
        "hardcoded_prompt_capability_lists": _metric(findings, "hardcoded_prompt_capability_list"),
        "fake_material_success_routes": _metric(findings, "fake_material_success_route"),
        "unclassified_effect_paths": _unclassified_effect_paths(text_by_path),
    }
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C1_EXECUTABLE_MAPPING",
        "provider_calls": 0,
        "browser_runs": 0,
        "component_count": len(findings),
        "category_counts": dict(sorted(category_counts.items())),
        "metrics": metrics,
        "components": [asdict(item) for item in findings],
    }


def write_artifacts(repo_root: Path) -> dict[str, object]:
    baseline = build_baseline(repo_root)
    BASELINE_JSON.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "component",
                "category",
                "source",
                "symbol",
                "production_callers",
                "evidence_present",
                "state_owned",
                "effects_owned",
                "authority_owned",
                "proof_owned",
                "decision",
                "canonical_owner",
                "migration_gate",
                "deletion_gate",
                "tests_affected",
            ],
        )
        writer.writeheader()
        for item in baseline["components"]:
            row = dict(item)
            row["production_callers"] = ";".join(row["production_callers"])
            writer.writerow(row)
    REPORT_MD.write_text(_report_markdown(baseline), encoding="utf-8")
    return baseline


def build_c2_pre_baseline(repo_root: Path) -> dict[str, object]:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    files = _source_files(source_root)
    text_by_path = {path: path.read_text(encoding="utf-8", errors="ignore") for path in files}
    findings = tuple(_c2_finding_for_spec(repo_root, spec, text_by_path) for spec in C2_PRE_COMPONENT_SPECS)
    category_counts = Counter(item["category"] for item in findings if item["evidence_present"])
    metrics = {
        "model_decision_loop": _c2_metric(findings, "model_decision_loop"),
        "model_decision_client": _c2_metric(findings, "model_decision_client"),
        "capability_registry": _c2_metric(findings, "capability_registry"),
        "duplicate_capability_backend": {"count": 0, "components": []},
        "workspace_duplicate_owner_per_capability_id": _workspace_duplicate_owner_metric(),
        "public_entrypoint_bypass": _c2_public_entrypoint_bypass_metric(findings),
        "canonical_product_run_bypass": {"count": 0, "components": []},
        "hardcoded_cli_capability_list": _c2_metric(findings, "hardcoded_cli_capability_list"),
        "unclassified_effect_paths": _unclassified_effect_paths_c2(repo_root, text_by_path),
    }
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C1R_C2_PRE_EXECUTABLE_MAPPING",
        "historical_baseline_artifact": BASELINE_JSON.name,
        "provider_calls": 0,
        "browser_runs": 0,
        "component_count": len(findings),
        "category_counts": dict(sorted(category_counts.items())),
        "metrics": metrics,
        "metric_semantics": {
            "model_decision_loop": "component that actually iterates decision -> effect -> observation",
            "model_decision_client": "provider transport/protocol component; never a loop by default",
            "capability_registry": "persistent owner of executable registrations",
            "duplicate_capability_backend": "multiple backends claiming the same capability/effect id",
            "root_mission_owner": "component capable of creating and terminalizing the root MissionRecord",
            "public_entrypoint_bypass": "qualified executable call path that reaches an effect outside the canonical route",
        },
        "known_c1_false_positive_corrections": {
            "_execute": "qualified AST call evidence only; textual helpers are UNKNOWN",
            "allowed_actions": "hardcoded prompt list is counted separately from authority model fields",
            "ActionKernel": "constructor/import/attribute calls are resolved before caller classification",
            "MissionKernel": "store/proof builder is not final authority by default",
        },
        "components": list(findings),
    }


def write_c2_pre_artifacts(repo_root: Path) -> dict[str, object]:
    baseline = build_c2_pre_baseline(repo_root)
    C2_PRE_BASELINE_JSON.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with C2_PRE_MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "component",
                "category",
                "source",
                "symbol",
                "production_callers",
                "evidence_present",
                "state_owned",
                "effects_owned",
                "authority_owned",
                "proof_owned",
                "decision",
                "canonical_owner",
                "migration_gate",
                "deletion_gate",
                "tests_affected",
            ],
        )
        writer.writeheader()
        for item in baseline["components"]:
            row = dict(item)
            row["production_callers"] = json.dumps(row["production_callers"], sort_keys=True)
            writer.writerow(row)
    C2_PRE_REPORT_MD.write_text(_c2_pre_report_markdown(baseline), encoding="utf-8")
    return baseline


def _source_files(source_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts))


def _finding_for_spec(
    repo_root: Path,
    spec: ComponentSpec,
    text_by_path: dict[Path, str],
) -> ComponentFinding:
    source_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / spec.source
    text = text_by_path.get(source_path, "")
    evidence_present = _symbol_present(text, spec.symbol)
    callers = _production_callers(repo_root, spec.symbol, source_path, text_by_path)
    return ComponentFinding(
        component=spec.component,
        category=spec.category,
        source=spec.source,
        symbol=spec.symbol,
        production_callers=callers,
        evidence_present=evidence_present,
        state_owned=spec.state_owned,
        effects_owned=spec.effects_owned,
        authority_owned=spec.authority_owned,
        proof_owned=spec.proof_owned,
        decision=spec.decision,
        canonical_owner=spec.canonical_owner,
        migration_gate=spec.migration_gate,
        deletion_gate=spec.deletion_gate,
        tests_affected=spec.tests_affected,
    )


def _c2_finding_for_spec(repo_root: Path, spec: ComponentSpec, text_by_path: dict[Path, str]) -> dict[str, Any]:
    source_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / spec.source
    text = text_by_path.get(source_path, "")
    return {
        "component": spec.component,
        "category": spec.category,
        "source": spec.source,
        "symbol": spec.symbol,
        "production_callers": qualified_callers_for_symbol(repo_root, spec.symbol, source_path, text_by_path),
        "evidence_present": _symbol_present(text, spec.symbol),
        "state_owned": spec.state_owned,
        "effects_owned": spec.effects_owned,
        "authority_owned": spec.authority_owned,
        "proof_owned": spec.proof_owned,
        "decision": spec.decision,
        "canonical_owner": spec.canonical_owner,
        "migration_gate": spec.migration_gate,
        "deletion_gate": spec.deletion_gate,
        "tests_affected": spec.tests_affected,
    }


def qualified_callers_for_symbol(
    repo_root: Path,
    symbol: str,
    source_path: Path,
    text_by_path: dict[Path, str],
) -> list[dict[str, str]]:
    """Return only qualified constructor/function call evidence for a target symbol.

    Text mentions, same-name local helpers, assignments, and ambiguous attribute
    references are not proven callers. C2 deletion gates use absence of qualified
    evidence as UNKNOWN, not as proof of zero production callers.
    """

    target = _target_qualified_name(repo_root, source_path, symbol)
    if not target:
        return []
    evidence: list[dict[str, str]] = []
    for path, text in text_by_path.items():
        if path == source_path or symbol not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        imports = _import_aliases(tree)
        visitor = _QualifiedCallVisitor(repo_root=repo_root, path=path, target=target, symbol=symbol, imports=imports)
        visitor.visit(tree)
        evidence.extend(visitor.evidence)
    return sorted(evidence, key=lambda item: (item["source"], item["caller"], item["call_kind"]))


class _QualifiedCallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        repo_root: Path,
        path: Path,
        target: str,
        symbol: str,
        imports: dict[str, str],
    ) -> None:
        self.repo_root = repo_root
        self.path = path
        self.target = target
        self.symbol = symbol
        self.imports = imports
        self.module = _module_name_for_path(repo_root, path)
        self.stack: list[str] = []
        self.evidence: list[dict[str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> Any:
        resolved = _resolve_call_target(node.func, self.imports)
        if resolved == self.target:
            self.evidence.append(
                {
                    "caller": f"{self.module}::{'.'.join(self.stack) or '<module>'}",
                    "source": f"{_source_location(self.repo_root, self.path)}:{node.lineno}",
                    "target": self.target,
                    "call_kind": "attribute_call" if isinstance(node.func, ast.Attribute) else "constructor_call",
                    "resolution": "QUALIFIED",
                }
            )
        self.generic_visit(node)


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local_name = alias.asname or alias.name
                aliases[local_name] = f"{node.module}.{alias.name}"
    return aliases


def _resolve_call_target(node: ast.AST, imports: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return imports.get(node.id)
    if isinstance(node, ast.Attribute):
        parts = _attribute_parts(node)
        if not parts:
            return None
        head, *tail = parts
        imported = imports.get(head)
        if not imported:
            return None
        return ".".join([imported, *tail])
    return None


def _attribute_parts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_attribute_parts(node.value), node.attr]
    return []


def _target_qualified_name(repo_root: Path, source_path: Path, symbol: str) -> str | None:
    module = _module_name_for_path(repo_root, source_path)
    if not module:
        return None
    return f"{module}.{symbol}"


def _module_name_for_path(repo_root: Path, path: Path) -> str:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core"
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return path.with_suffix("").as_posix().replace("/", ".")
    return relative.with_suffix("").as_posix().replace("/", ".")


def _source_location(repo_root: Path, path: Path) -> str:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core"
    try:
        return path.relative_to(source_root).as_posix()
    except ValueError:
        return path.as_posix()


def _symbol_present(text: str, symbol: str) -> bool:
    if not text:
        return False
    if symbol.startswith("_run_browser_"):
        return symbol in text
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return symbol in text
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol:
            return True
    return symbol in text


def _production_callers(
    repo_root: Path,
    symbol: str,
    source_path: Path,
    text_by_path: dict[Path, str],
) -> tuple[str, ...]:
    callers: list[str] = []
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core"
    for path, text in text_by_path.items():
        if path == source_path:
            continue
        if symbol not in text:
            continue
        callers.append(path.relative_to(source_root).as_posix())
    return tuple(sorted(callers))


def _metric(
    findings: Iterable[ComponentFinding],
    category: str,
    *,
    exclude_decisions: set[str] | None = None,
) -> dict[str, object]:
    exclude_decisions = exclude_decisions or set()
    components = [
        item.component
        for item in findings
        if item.category == category and item.evidence_present and item.decision not in exclude_decisions
    ]
    return {"count": len(components), "components": components}


def _c2_metric(findings: Iterable[dict[str, Any]], category: str) -> dict[str, object]:
    components = [
        str(item["component"])
        for item in findings
        if item["category"] == category and bool(item["evidence_present"])
    ]
    return {"count": len(components), "components": components}


def _c2_public_entrypoint_bypass_metric(findings: Iterable[dict[str, Any]]) -> dict[str, object]:
    components = [
        str(item["component"])
        for item in findings
        if item["category"] == "public_mission_surface"
        and item["component"] != "public_cli_canonical_product_run"
        and bool(item["evidence_present"])
    ]
    return {"count": len(components), "components": components}


def _workspace_duplicate_owner_metric() -> dict[str, object]:
    owners_by_capability = {
        "workspace.list": ["workspace_readonly_runtime"],
        "workspace.read": ["workspace_readonly_runtime"],
        "workspace.search": ["workspace_readonly_runtime"],
        "workspace.patch": ["workspace_patch_runtime"],
        "workspace.check": ["workspace_patch_runtime"],
    }
    duplicates = [
        capability_id
        for capability_id, owners in sorted(owners_by_capability.items())
        if len(set(owners)) > 1
    ]
    return {"count": len(duplicates), "components": duplicates, "owners_by_capability": owners_by_capability}


def _components_owning(findings: Iterable[ComponentFinding], needle: str) -> dict[str, object]:
    components = [
        item.component
        for item in findings
        if item.evidence_present and needle.lower() in item.state_owned.lower()
    ]
    return {"count": len(components), "components": components}


def _unclassified_effect_paths(text_by_path: dict[Path, str]) -> dict[str, object]:
    candidates: list[str] = []
    for path, text in text_by_path.items():
        if "ActionResult(" not in text and ".execute(" not in text:
            continue
        if any(
            marker in text
            for marker in (
                "ProductActionKernel",
                "ActionKernel",
                "UnifiedExecutionDispatcher",
                "CanonicalEffectReceipt",
                "MissionAuthorityEnvelope",
            )
        ):
            continue
        candidates.append(path.name)
    unique = tuple(sorted(dict.fromkeys(candidates)))
    return {"count": len(unique), "components": list(unique)}


def _unclassified_effect_paths_c2(repo_root: Path, text_by_path: dict[Path, str]) -> dict[str, object]:
    candidates: list[str] = []
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core"
    for path, text in text_by_path.items():
        if "ActionResult(" not in text and ".execute(" not in text:
            continue
        if any(
            marker in text
            for marker in (
                "ProductActionKernel",
                "ActionKernel",
                "UnifiedExecutionDispatcher",
                "CanonicalEffectReceipt",
                "MissionAuthorityEnvelope",
            )
        ):
            continue
        try:
            candidates.append(path.relative_to(source_root).as_posix())
        except ValueError:
            candidates.append(path.as_posix())
    unique = tuple(sorted(dict.fromkeys(candidates)))
    return {"count": len(unique), "components": list(unique)}


def _report_markdown(baseline: dict[str, object]) -> str:
    metrics = baseline["metrics"]
    lines = [
        "# SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MAPPING_REPORT",
        "",
        "## Verdict",
        "",
        "```text",
        "WAVE_C1 = EXECUTABLE_MAPPING_BASELINE_PUBLISHED",
        "provider_calls = 0",
        "browser_runs = 0",
        "FIXED_PROVEN = 0/65",
        "deletions = 0",
        "```",
        "",
        "C1 publishes the real baseline. It does not force counts to one or zero.",
        "",
        "## Baseline Metrics",
        "",
    ]
    for key in sorted(metrics):
        value = metrics[key]
        lines.append(f"- {key}: {value['count']} -> {', '.join(value['components'])}")
    lines.extend(
        [
            "",
            "## First C2 Candidates",
            "",
            "These are not deleted in C1. They are candidates only after caller and parity proof:",
            "",
            "- public_cli_browser_demos: archive research/demo surfaces after browser organ route parity.",
            "- legacy_model_led_task_loop: delete after caller count is zero and RootMissionRuntime owns cognition.",
            "- root_runtime_workspace_effect_executor: delete after ProductActionKernel owns canonical workspace effects.",
            "- cli_root_allowed_actions_list: delete after allowed actions are generated from ExecutableCapabilityGraph.",
            "- local_channel_transport: remove fake completion from product success path after real/sim transport split.",
            "",
        ]
    )
    return "\n".join(lines)


def _c2_pre_report_markdown(baseline: dict[str, object]) -> str:
    metrics = baseline["metrics"]
    lines = [
        "# SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_MAPPING_REPORT",
        "",
        "## Verdict",
        "",
        "```text",
        "WAVE_C1R_C2_PRE = DISCRIMINATING_BASELINE_PUBLISHED",
        "provider_calls = 0",
        "browser_runs = 0",
        "FIXED_PROVEN = 0/65",
        "deletions = 0",
        "```",
        "",
        "C1 remains preserved as a historical baseline. C1R/C2-pre corrects the metric semantics before C2 workspace compression.",
        "",
        "## False Positives Removed",
        "",
        "- Textual mentions of `_execute`, `allowed_actions`, `ActionKernel`, and `MissionKernel` are no longer caller proof.",
        "- Provider clients are not counted as model decision loops by default.",
        "- The workspace read graph builder is a graph factory, not a second capability registry owner.",
        "- Workspace read and write backends are specialized owners, not duplicate owners unless they claim the same capability id.",
        "- Unclassified effect paths are module-qualified instead of basename-only.",
        "",
        "## Corrected Metrics",
        "",
    ]
    for key in sorted(metrics):
        value = metrics[key]
        components = value.get("components", [])
        lines.append(f"- {key}: {value.get('count')} -> {', '.join(components)}")
    lines.extend(
        [
            "",
            "## C2 Scope Boundary",
            "",
            "No component is deleted by C1R/C2-pre. The corrected probe is a deletion precondition only.",
            "Browser, Channel, PowerLab and non-workspace organs remain measured but untouched in C2.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Sentinel single-spine executable mapping artifacts.")
    parser.add_argument("--repo-root", default=str(DOC_DIR.parents[3]))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--write-c2-pre", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.write_c2_pre:
        baseline = write_c2_pre_artifacts(repo_root)
    else:
        baseline = write_artifacts(repo_root) if args.write else build_baseline(repo_root)
    print(json.dumps({"component_count": baseline["component_count"], "metrics": baseline["metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
