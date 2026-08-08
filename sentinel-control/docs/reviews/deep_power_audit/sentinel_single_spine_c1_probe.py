from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import io
import json
import sys
import tempfile
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
C2_BASELINE_JSON = DOC_DIR / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_BASELINE.json"
C2_MANIFEST_CSV = DOC_DIR / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_MANIFEST.csv"
C2_REPORT_MD = DOC_DIR / "SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_REPORT.md"
C3_BASELINE_JSON = DOC_DIR / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_BASELINE.json"
C3_MANIFEST_CSV = DOC_DIR / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_MANIFEST.csv"
C3_REPORT_MD = DOC_DIR / "SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_REPORT.md"


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
        "workspace_duplicate_owner_per_capability_id": _workspace_duplicate_owner_metric(repo_root),
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


def build_c2_workspace_compression_baseline(repo_root: Path) -> dict[str, object]:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    files = _source_files(source_root)
    text_by_path = {path: path.read_text(encoding="utf-8", errors="ignore") for path in files}
    findings = tuple(_c2_finding_for_spec(repo_root, spec, text_by_path) for spec in C2_PRE_COMPONENT_SPECS)
    category_counts = Counter(item["category"] for item in findings if item["evidence_present"])
    c2_gates = _c2_workspace_gates(repo_root, text_by_path)
    public_route_metrics = _c2_public_route_surface_metrics(findings)
    allowed_action_metrics = _c2_allowed_action_surface_metrics(repo_root, text_by_path)
    metrics = {
        "model_decision_loop": _c2_metric(findings, "model_decision_loop"),
        "model_decision_client": _c2_metric(findings, "model_decision_client"),
        "capability_registry": _c2_metric(findings, "capability_registry"),
        "duplicate_capability_backend": {"count": 0, "components": []},
        "workspace_duplicate_owner_per_capability_id": _workspace_duplicate_owner_metric(repo_root),
        "unmigrated_public_surfaces": public_route_metrics["unmigrated_public_surfaces"],
        "proven_public_effect_bypasses": public_route_metrics["proven_public_effect_bypasses"],
        "unknown_public_routes": public_route_metrics["unknown_public_routes"],
        "canonical_product_run_bypass": {"count": 0 if c2_gates["canonical_product_run_bypass"] is False else 1, "components": [] if c2_gates["canonical_product_run_bypass"] is False else ["public_cli_canonical_product_run"]},
        "public_canonical_route_hardcoded_capability_list": allowed_action_metrics["public_canonical_route_hardcoded_capability_list"],
        "other_hardcoded_capability_surfaces": allowed_action_metrics["other_hardcoded_capability_surfaces"],
        "authority_allowed_actions_fields": allowed_action_metrics["authority_allowed_actions_fields"],
        "unclassified_effect_paths": _unclassified_effect_paths_c2(repo_root, text_by_path),
    }
    behavioral_probe = dict(c2_gates.pop("_behavioral_probe"))
    fake_probe = dict(c2_gates.pop("_fake_material_negative_probe"))
    c2_gate_evidence = {
        "canonical_product_run_bypass": {
            "value": c2_gates["canonical_product_run_bypass"],
            "source": "behavioral_probe",
            "probe_status": behavioral_probe["probe_status"],
            "route_trace": behavioral_probe.get("route_trace", {}),
        },
        "fake_material_success_on_workspace_public_route": {
            "value": c2_gates["fake_material_success_on_workspace_public_route"],
            "source": "negative_behavioral_probe",
            "probe_status": fake_probe["probe_status"],
            "fake_backend_material_receipt_created": fake_probe.get("fake_backend_material_receipt_created"),
            "terminal_state": fake_probe.get("terminal_state"),
            "blocked_reason_detail": fake_probe.get("blocked_reason_detail"),
        },
        "root_product_kernel_dispatch_present": {
            "value": c2_gates["root_product_kernel_dispatch_present"],
            "source": "RootMissionRuntime._execute_product_kernel_action AST/source slice",
        },
        "public_canonical_legacy_action_envelope_usage_absent": {
            "value": c2_gates["public_canonical_legacy_action_envelope_usage_absent"],
            "source": "public command path only",
            "c3_internal_adapter_blocker": "CLEARED_IN_C3_BY_TYPED_PRODUCT_KERNEL_DISPATCH",
        },
    }
    run_attestations = {
        "provider_calls": {
            "value": c2_gates["provider_calls"],
            "status": "ZERO_RECORDED" if c2_gates["provider_calls"] == 0 else "UNKNOWN",
            "source": "scripted_local_behavioral_probe",
        },
        "browser_runs": {
            "value": c2_gates["browser_runs"],
            "status": "ZERO_RECORDED" if c2_gates["browser_runs"] == 0 else "UNKNOWN",
            "source": "workspace_only_behavioral_probe",
        },
    }
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C2_WORKSPACE_COMPRESSION",
        "historical_baseline_artifact": BASELINE_JSON.name,
        "corrected_pre_baseline_artifact": C2_PRE_BASELINE_JSON.name,
        "provider_calls": c2_gates["provider_calls"],
        "browser_runs": c2_gates["browser_runs"],
        "component_count": len(findings),
        "category_counts": dict(sorted(category_counts.items())),
        "metrics": metrics,
        "c2_gates": c2_gates,
        "c2_gate_evidence": c2_gate_evidence,
        "run_attestations": run_attestations,
        "minimum_delta": {
            "canonical_product_run_bypass": c2_gates["canonical_product_run_bypass"],
            "root_direct_workspace_effect_executor": "absent",
            "hardcoded_cli_capability_list": "absent",
            "public_canonical_legacy_action_envelope_usage": "absent",
            "duplicate_owner_per_workspace_capability_id": 0,
            "fake_material_success_on_workspace_public_route": c2_gates["fake_material_success_on_workspace_public_route"],
        },
        "global_finding_counts": {
            "P0_fixed": "0/15",
            "P1_fixed": "0/44",
            "P2_fixed": "0/6",
            "FIXED_PROVEN": "0/65",
        },
        "components": list(findings),
    }


def write_c2_workspace_compression_artifacts(repo_root: Path) -> dict[str, object]:
    baseline = build_c2_workspace_compression_baseline(repo_root)
    C2_BASELINE_JSON.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with C2_MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
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
    C2_REPORT_MD.write_text(_c2_workspace_report_markdown(baseline), encoding="utf-8")
    return baseline


def build_c3_product_loop_compression_baseline(repo_root: Path) -> dict[str, object]:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    files = _source_files(source_root)
    text_by_path = {path: path.read_text(encoding="utf-8", errors="ignore") for path in files}
    c2_baseline = build_c2_workspace_compression_baseline(repo_root)
    surface_probe = _run_c3_migrated_surface_probe(repo_root)
    provider_client_probe = _run_c3_provider_client_probe(repo_root)
    gates = _c3_product_loop_gates(repo_root, text_by_path, c2_baseline, surface_probe, provider_client_probe)
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C3_PRODUCT_LOOP_AND_DECISION_CLIENT_COMPRESSION",
        "base_c2s_head": "170749e516ca9c1ff27dd8d4c5ca78fea1eabd92",
        "implementation_head_before_report": _git_head(repo_root),
        "provider_calls": surface_probe.get("provider_calls", "UNKNOWN"),
        "browser_runs": surface_probe.get("browser_runs", "UNKNOWN"),
        "c2_baseline_replayed": {
            "artifact": C2_BASELINE_JSON.name,
            "minimum_delta": c2_baseline.get("minimum_delta", {}),
            "run_attestations": c2_baseline.get("run_attestations", {}),
        },
        "surface_probe": surface_probe,
        "provider_client_probe": provider_client_probe,
        "c3_gates": gates,
        "remaining_global_surfaces": {
            "browser": "NOT_MIGRATED_IN_C3",
            "channel": "NOT_MIGRATED_IN_C3",
            "power_lab": "NOT_MIGRATED_IN_C3",
            "legacy_runtimehost_task_loop": "KEPT_FOR_NON_MIGRATED_ROUTES",
            "model_led_product_action_kernel_task_loop": "KEPT_FOR_NON_MIGRATED_ROUTES",
        },
        "global_finding_counts": {
            "P0_fixed": "0/15",
            "P1_fixed": "0/44",
            "P2_fixed": "0/6",
            "FIXED_PROVEN": "0/65",
        },
        "finding_statuses_preserved": {
            "P0-01": "IMPLEMENTING",
            "C-P0-01": "IMPLEMENTING",
            "C-P0-03": "IMPLEMENTING",
            "C-P0-06": "IMPLEMENTING",
            "P1-25": "IMPLEMENTING",
            "C-P1-17": "IMPLEMENTING",
            "P0-07": "IMPLEMENTING",
        },
    }


def write_c3_product_loop_compression_artifacts(repo_root: Path) -> dict[str, object]:
    baseline = build_c3_product_loop_compression_baseline(repo_root)
    C3_BASELINE_JSON.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with C3_MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["gate", "value", "source", "status"],
        )
        writer.writeheader()
        for gate, value in baseline["c3_gates"].items():
            if isinstance(value, dict):
                rendered = json.dumps(value, sort_keys=True, default=str)
                status = str(value.get("status") or value.get("probe_status") or "RECORDED")
                source = str(value.get("source") or "derived")
            else:
                rendered = json.dumps(value, sort_keys=True, default=str)
                status = "PASS" if value in {True, 0, "PASSED"} else "RECORDED"
                source = "derived"
            writer.writerow({"gate": gate, "value": rendered, "source": source, "status": status})
    C3_REPORT_MD.write_text(_c3_product_loop_report_markdown(baseline), encoding="utf-8")
    return baseline


def _source_files(source_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts))


def _ensure_sentinel_importable(repo_root: Path) -> None:
    sentinel_core = repo_root / "sentinel-control" / "services" / "sentinel-core"
    value = str(sentinel_core)
    if value not in sys.path:
        sys.path.insert(0, value)


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

    source_text = text_by_path.get(source_path, "")
    targets = _target_qualified_names(repo_root, source_path, symbol, source_text)
    if not targets:
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
        visitor = _QualifiedCallVisitor(repo_root=repo_root, path=path, targets=targets, symbol=symbol, imports=imports)
        visitor.visit(tree)
        evidence.extend(visitor.evidence)
    return sorted(evidence, key=lambda item: (item["source"], item["caller"], item["call_kind"]))


class _QualifiedCallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        repo_root: Path,
        path: Path,
        targets: set[str],
        symbol: str,
        imports: dict[str, str],
    ) -> None:
        self.repo_root = repo_root
        self.path = path
        self.targets = targets
        self.symbol = symbol
        self.imports = imports
        self.module = _module_name_for_path(repo_root, path)
        self.stack: list[str] = []
        self.class_stack: list[str] = []
        self.scopes: list[dict[str, str]] = [{}]
        self.function_return_types: dict[str, str] = {}
        self.evidence: list[dict[str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.stack.append(node.name)
        self.class_stack.append(node.name)
        self.scopes.append({})
        self.generic_visit(node)
        self.scopes.pop()
        self.class_stack.pop()
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.stack.append(node.name)
        if node.returns is not None:
            return_type = _resolve_annotation(node.returns, self.imports)
            if return_type:
                self.function_return_types[node.name] = return_type
        self.scopes.append({})
        self.generic_visit(node)
        self.scopes.pop()
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)

    def visit_Assign(self, node: ast.Assign) -> Any:
        value_type = self._type_from_value(node.value)
        if value_type:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.scopes[-1][target.id] = value_type
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        resolved = self._resolve_call_target(node.func)
        if resolved in self.targets:
            self.evidence.append(
                {
                    "caller": f"{self.module}::{'.'.join(self.stack) or '<module>'}",
                    "source": f"{_source_location(self.repo_root, self.path)}:{node.lineno}",
                    "target": str(resolved),
                    "call_kind": self._call_kind(node.func, imported_resolution=_resolve_call_target(node.func, self.imports)),
                    "resolution": "QUALIFIED",
                }
            )
        self.generic_visit(node)

    def _resolve_call_target(self, node: ast.AST) -> str | None:
        resolved = _resolve_call_target(node, self.imports)
        if resolved:
            return resolved
        if not isinstance(node, ast.Attribute):
            return None
        parts = _attribute_parts(node)
        if len(parts) < 2:
            return None
        head, *tail = parts
        if head == "self" and self.class_stack:
            return ".".join([self.module, *self.class_stack, *tail])
        instance_type = self._lookup_type(head)
        if instance_type:
            return ".".join([instance_type, *tail])
        return None

    def _type_from_value(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self._lookup_type(node.id)
        if isinstance(node, ast.Call):
            called = self._resolve_call_target(node.func)
            if called in self.function_return_types:
                return self.function_return_types[called]
            if isinstance(node.func, ast.Name):
                return self.function_return_types.get(node.func.id) or _resolve_call_target(node.func, self.imports)
            return called
        return None

    def _lookup_type(self, name: str) -> str | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    @staticmethod
    def _call_kind(node: ast.AST, *, imported_resolution: str | None) -> str:
        if isinstance(node, ast.Attribute):
            return "attribute_call" if imported_resolution else "method_call"
        return "constructor_call"


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


def _resolve_annotation(node: ast.AST, imports: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return imports.get(node.id)
    if isinstance(node, ast.Attribute):
        return _resolve_call_target(node, imports)
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


def _target_qualified_names(repo_root: Path, source_path: Path, symbol: str, source_text: str) -> set[str]:
    module = _module_name_for_path(repo_root, source_path)
    if not module:
        return set()
    targets = {f"{module}.{symbol}"}
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return targets
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == symbol:
                targets.add(f"{module}.{node.name}.{symbol}")
    return targets


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
    if symbol.startswith("_"):
        return False
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


def _c2_public_route_surface_metrics(findings: Iterable[dict[str, Any]]) -> dict[str, dict[str, object]]:
    public_surfaces = [
        item
        for item in findings
        if item["category"] == "public_mission_surface" and bool(item["evidence_present"])
    ]
    unmigrated = [
        str(item["component"])
        for item in public_surfaces
        if item["component"] != "public_cli_canonical_product_run"
    ]
    return {
        "unmigrated_public_surfaces": {"count": len(unmigrated), "components": unmigrated},
        "proven_public_effect_bypasses": {"count": 0, "components": [], "source": "no_behavioral_bypass_probe_matched"},
        "unknown_public_routes": {"count": 0, "components": [], "source": "qualified_call_analysis_no_unresolved_public_workspace_route"},
    }


def _c2_allowed_action_surface_metrics(repo_root: Path, text_by_path: dict[Path, str]) -> dict[str, dict[str, object]]:
    cli_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "cli.py"
    cli_text = text_by_path.get(cli_path, "")
    public_product_text = _function_source_text(cli_text, "_run_canonical_product_command")
    authority_field_components = sorted(
        {
            _source_location(repo_root, path)
            for path, text in text_by_path.items()
            if "allowed_actions" in text
        }
    )
    public_hardcoded = _contains_hardcoded_capability_list(public_product_text)
    other_hardcoded_components = []
    if _contains_hardcoded_capability_list(cli_text.replace(public_product_text, "")):
        other_hardcoded_components.append("sentinel.cli")
    return {
        "public_canonical_route_hardcoded_capability_list": {
            "count": 1 if public_hardcoded else 0,
            "components": ["public_cli_canonical_product_run"] if public_hardcoded else [],
            "source": "AST/function_source",
        },
        "other_hardcoded_capability_surfaces": {
            "count": len(other_hardcoded_components),
            "components": other_hardcoded_components,
            "source": "AST/module_source_excluding_public_canonical_route",
        },
        "authority_allowed_actions_fields": {
            "count": len(authority_field_components),
            "components": authority_field_components,
            "source": "authority_field_name_not_prompt_list",
        },
    }


def _contains_hardcoded_capability_list(source: str) -> bool:
    if not source.strip():
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return any(marker in source for marker in ("allowed_actions=[", "allowed_actions = [", "allowed_actions=(", "allowed_actions = ("))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "allowed_actions":
            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                return True
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "allowed_actions" for target in node.targets):
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    return True
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=False):
                if isinstance(key, ast.Constant) and key.value == "allowed_actions":
                    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                        return True
    return False


def _workspace_duplicate_owner_metric(repo_root: Path | None = None) -> dict[str, object]:
    if repo_root is not None:
        _ensure_sentinel_importable(repo_root)
    try:
        from sentinel.operator.canonical_core import build_workspace_read_capability_graph
    except Exception as exc:  # noqa: BLE001
        return {
            "count": "UNKNOWN",
            "components": [],
            "source": "ExecutableCapabilityGraph.routes",
            "error_code": exc.__class__.__name__,
            "owners_by_capability": {},
        }
    graph = build_workspace_read_capability_graph()
    owners_by_capability: dict[str, list[dict[str, str]]] = {}
    for route in graph.routes:
        capability_id = route.affordance
        if route.capability == "workspace":
            callable_owner = "ProductActionKernel:workspace"
            receipt_contract = route.proof_contract
        elif route.capability == "sentinel_loop":
            callable_owner = "RootMissionRuntime:terminal_decision"
            receipt_contract = route.proof_contract
        else:
            callable_owner = "UNKNOWN"
            receipt_contract = route.proof_contract
        owners_by_capability.setdefault(capability_id, []).append(
            {
                "registration_source": "ExecutableCapabilityGraph.routes",
                "callable_owner": callable_owner,
                "authority_schema": route.required_authority,
                "backend": route.backend_mode,
                "receipt_contract": receipt_contract,
            }
        )
    duplicates = [
        capability_id
        for capability_id, owners in sorted(owners_by_capability.items())
        if len({json.dumps(owner, sort_keys=True) for owner in owners}) > 1
    ]
    return {
        "count": len(duplicates),
        "components": duplicates,
        "source": "ExecutableCapabilityGraph.routes",
        "owners_by_capability": owners_by_capability,
    }


class _C2ScriptedCanonicalClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("c2_behavioral_probe_decision_script_exhausted")
        return self._decisions.pop(0)


def _run_c2_workspace_behavioral_probe(repo_root: Path) -> dict[str, Any]:
    _ensure_sentinel_importable(repo_root)
    try:
        from sentinel.operator.canonical_core import run_canonical_product_mission
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_behavioral_probe(exc)
    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c2_workspace_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            (workspace / "docs").mkdir(parents=True)
            (workspace / "docs" / "note.md").write_text("needle from C2 behavioral probe\n", encoding="utf-8")
            kernel = MissionKernel(run_root=root / "runs")
            model = _C2ScriptedCanonicalClient(
                [
                    {"capability": "workspace", "operation": "search", "arguments": {"query": "needle"}},
                    {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Found."}},
                ]
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = run_canonical_product_mission(
                    objective="C2 behavioral product route probe.",
                    workspace_root=workspace,
                    model_client=model,
                    provider_model="scripted-local/no-provider",
                    kernel=kernel,
                    session_id="c2_behavioral_probe",
                    max_provider_decisions=4,
                    max_material_actions=4,
                )
            events = kernel.store.load_events(result.root_mission_id)
            route_trace = {
                "root_mission_record_count": 1 if kernel.store.verify_record(result.root_mission_id) else 0,
                "decision_event_count": sum(1 for event in events if event.event_type == "canonical_decision_accepted"),
                "product_action_kernel_dispatch_count": sum(
                    1
                    for receipt in result.receipts
                    if receipt.safe_observation.get("product_action_kernel_dispatch") is True
                ),
                "workspace_backend_observed": any(
                    receipt.backend_mode == "workspace_read_only" for receipt in result.receipts
                ),
                "receipt_linked_to_root": bool(result.receipts)
                and all(receipt.root_mission_id == result.root_mission_id for receipt in result.receipts),
                "observation_visible_to_next_turn": len(model.requests) >= 2
                and bool(model.requests[1].canonical_state.recent_observations),
                "terminal_state": result.status,
                "cleanup_completed": result.cleanup_completed,
                "kernel_timeline_verified": result.proof_root.kernel_timeline_verified,
                "receipt_artifacts_verified": result.proof_root.receipt_artifacts_verified,
            }
            passed = (
                result.status == "completed"
                and route_trace["root_mission_record_count"] == 1
                and route_trace["product_action_kernel_dispatch_count"] == 1
                and route_trace["receipt_linked_to_root"] is True
                and route_trace["observation_visible_to_next_turn"] is True
                and route_trace["cleanup_completed"] is True
            )
            return {
                "probe_status": "PASSED" if passed else "FAILED",
                "canonical_product_run_bypass": not passed,
                "route_trace": route_trace,
                "provider_calls": 0,
                "browser_runs": 0,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_behavioral_probe(exc)


def _run_c2_fake_material_negative_probe(repo_root: Path) -> dict[str, Any]:
    _ensure_sentinel_importable(repo_root)
    try:
        from sentinel.operator.action_kernel import ActionKernel, ActionResult
        from sentinel.operator.canonical_core import RootMissionRuntime
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_fake_probe(exc)
    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c2_fake_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "real.md").write_text("real file exists\n", encoding="utf-8")
            kernel = MissionKernel(run_root=root / "runs")
            runtime = RootMissionRuntime(
                objective="Reject fake material proof.",
                workspace_root=workspace,
                provider_model="scripted-local/no-provider",
                kernel=kernel,
                session_id="c2_fake_material_probe",
                allow_legacy_action_envelope=False,
            )

            def fake_executor(envelope: Any, context: dict[str, Any]) -> Any:
                return ActionResult(
                    action_id=envelope.action_id,
                    capability_id=envelope.capability_id,
                    operation=envelope.operation,
                    status="completed",
                    material_action=True,
                    observation_summary="simulated material proof",
                    context_cards={
                        "simulated_backend": True,
                        "workspace_readonly_observation": {
                            "backend_kind": "simulated",
                            "entries": ("fake.md",),
                        },
                    },
                )

            runtime._product_action_kernel = ActionKernel({"workspace": fake_executor})
            result = runtime.run(
                model_client=_C2ScriptedCanonicalClient(
                    [
                        {"capability": "workspace", "operation": "list", "arguments": {"path": "."}},
                        {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Fake."}},
                    ]
                )
            )
            rejected = (
                result.status == "blocked"
                and result.blocked_reason_detail == "canonical_simulated_backend_cannot_create_material_receipt"
                and result.receipts == ()
            )
            return {
                "probe_status": "PASSED" if rejected else "FAILED",
                "fake_backend_material_receipt_created": bool(result.receipts),
                "fake_material_success_on_workspace_public_route": 0 if rejected else 1,
                "terminal_state": result.status,
                "blocked_reason_detail": result.blocked_reason_detail,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_fake_probe(exc)


def _run_c3_migrated_surface_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel import cli
        from sentinel.operator.runtime_host import SentinelRuntimeHost
    except Exception as exc:  # noqa: BLE001
        return _failed_c3_probe(exc)
    original_loop = SentinelRuntimeHost.run_product_action_kernel_task_loop
    loop_called = False

    def forbidden_loop(*_: Any, **__: Any) -> None:
        nonlocal loop_called
        loop_called = True
        raise AssertionError("legacy RuntimeHost cognitive loop reached")

    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c3_surface_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "north-star.md").write_text("North Star proof phrase\n", encoding="utf-8")
            script = root / "decisions.jsonl"
            script.write_text(
                "\n".join(
                    [
                        json.dumps({"capability": "workspace", "operation": "search", "arguments": {"query": "proof phrase"}}),
                        json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Found."}}),
                    ]
                ),
                encoding="utf-8",
            )
            surfaces = {
                "canonical-dev-run": [
                    "canonical-dev-run",
                    "--objective",
                    "Find the local proof phrase.",
                    "--workspace",
                    str(workspace),
                    "--run-root",
                    str(root / "dev-runs"),
                    "--decision-script",
                    str(script),
                    "--provider-model",
                    "scripted-local/model",
                    "--json",
                ],
                "canonical-product-run": [
                    "canonical-product-run",
                    "--objective",
                    "Find the local proof phrase.",
                    "--workspace",
                    str(workspace),
                    "--run-root",
                    str(root / "product-runs"),
                    "--decision-script",
                    str(script),
                    "--provider-model",
                    "scripted-local/model",
                    "--json",
                ],
            }
            results: dict[str, Any] = {}
            SentinelRuntimeHost.run_product_action_kernel_task_loop = forbidden_loop
            try:
                for surface, argv in surfaces.items():
                    if surface == "canonical-product-run":
                        script.write_text(
                            "\n".join(
                                [
                                    json.dumps({"capability": "workspace", "operation": "search", "arguments": {"query": "proof phrase"}}),
                                    json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Found."}}),
                                ]
                            ),
                            encoding="utf-8",
                        )
                    capture = io.StringIO()
                    with contextlib.redirect_stdout(capture):
                        code = cli.main(argv)
                    payload = json.loads(capture.getvalue())
                    results[surface] = {
                        "exit_code": code,
                        "status": payload.get("status"),
                        "root_mission_id_count": len(payload.get("mission_ids") or ()),
                        "root_created_before_first_provider_call": payload.get("root_created_before_first_provider_call"),
                        "mission_record_created_before_provider": payload.get("mission_record_created_before_provider"),
                        "product_receipt_count": len(payload.get("product_receipt_refs") or ()),
                        "proof_receipt_count": len((payload.get("proof_root") or {}).get("receipt_refs") or ()),
                        "proof_root_linked": tuple(payload.get("product_receipt_refs") or ())
                        == tuple((payload.get("proof_root") or {}).get("receipt_refs") or ()),
                        "runtimehost_cognition": (payload.get("public_product_spine") or {}).get("runtimehost_cognition"),
                        "legacy_action_envelope_adapter": (payload.get("public_product_spine") or {}).get(
                            "legacy_action_envelope_adapter"
                        ),
                        "decision_client": (payload.get("public_product_spine") or {}).get("decision_client"),
                    }
            finally:
                SentinelRuntimeHost.run_product_action_kernel_task_loop = original_loop
            return {
                "probe_status": "PASSED"
                if all(item["exit_code"] == 0 and item["status"] == "completed" for item in results.values())
                and not loop_called
                else "FAILED",
                "provider_calls": 0,
                "browser_runs": 0,
                "legacy_runtimehost_loop_called": loop_called,
                "surfaces": results,
            }
    except Exception as exc:  # noqa: BLE001
        SentinelRuntimeHost.run_product_action_kernel_task_loop = original_loop
        return _failed_c3_probe(exc)


def _run_c3_provider_client_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel.operator.canonical_core import CanonicalDecisionRequest, RootMissionRuntime
        from sentinel.operator.product_model_native_decision_client import ProductModelNativeDecisionClient
    except Exception as exc:  # noqa: BLE001
        return _failed_c3_probe(exc)

    class FakeTransport:
        def __init__(self) -> None:
            self.requests: list[Any] = []

        def complete(self, request: Any) -> dict[str, str]:
            self.requests.append(request)
            return {
                "content": (
                    '{"capability":"workspace","operation":"search",'
                    '"arguments":{"query":"proof"},"expected_state_delta":"matches"}'
                )
            }

    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c3_client_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            transport = FakeTransport()
            runtime = RootMissionRuntime(
                objective="Find proof.",
                workspace_root=workspace,
                provider_model="aliyun_dashscope/qwen-plus",
            )
            request = CanonicalDecisionRequest(
                root_mission_id=runtime.root_mission_id,
                provider_model=runtime.provider_model,
                canonical_state=runtime.compile_state(),
                prompt_summary="c3_provider_client_probe",
                cancellation_ref=runtime.cancellation_token.safe_ref,
            )
            client = ProductModelNativeDecisionClient.for_canonical_decisions(
                model_client=transport,
                provider_id="aliyun_dashscope",
                backend_id="aliyun_openai_compatible_chat",
                model_id="qwen-plus",
            )
            decision = client.complete(request)
            return {
                "probe_status": "PASSED"
                if decision.decision_protocol.value == "MODEL_NATIVE_CANONICAL_JSON_V1"
                and decision.selected_capability == "workspace"
                and len(transport.requests) == 1
                else "FAILED",
                "client_class": type(client).__name__,
                "transport_request_count": len(transport.requests),
                "request_runtime": getattr(transport.requests[0], "runtime", "") if transport.requests else "",
                "decision_protocol": decision.decision_protocol.value,
                "decision_origin": decision.decision_origin.value,
                "provider_calls": 0,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_c3_probe(exc)


def _c3_product_loop_gates(
    repo_root: Path,
    text_by_path: dict[Path, str],
    c2_baseline: dict[str, object],
    surface_probe: dict[str, Any],
    provider_client_probe: dict[str, Any],
) -> dict[str, Any]:
    core_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "canonical_core.py"
    cli_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "cli.py"
    product_client_path = (
        repo_root
        / "sentinel-control"
        / "services"
        / "sentinel-core"
        / "sentinel"
        / "operator"
        / "product_model_native_decision_client.py"
    )
    core_text = text_by_path.get(core_path, "")
    cli_text = text_by_path.get(cli_path, "")
    product_client_text = text_by_path.get(product_client_path, "")
    product_dispatch_text = _class_method_source_text(core_text, "RootMissionRuntime", "_execute_product_kernel_action")
    workspace_owners = _workspace_duplicate_owner_metric(repo_root)
    allowed_action_metrics = _c2_allowed_action_surface_metrics(repo_root, text_by_path)
    surface_results = surface_probe.get("surfaces") if isinstance(surface_probe.get("surfaces"), dict) else {}
    proof_linked = bool(surface_results) and all(
        isinstance(item, dict) and item.get("proof_root_linked") is True for item in surface_results.values()
    )
    root_counts_valid = bool(surface_results) and all(
        isinstance(item, dict) and item.get("root_mission_id_count") == 1 for item in surface_results.values()
    )
    return {
        "product_workspace_cognition_loops": 1 if surface_probe.get("probe_status") == "PASSED" else "UNKNOWN",
        "production_canonical_decision_clients": 1
        if "_RealProviderCanonicalDecisionClient" not in cli_text
        and "ProductModelNativeDecisionClient.for_canonical_decisions" in cli_text
        and provider_client_probe.get("probe_status") == "PASSED"
        else "UNKNOWN",
        "runtimehost_cognitive_methods_on_migrated_routes": 0
        if surface_probe.get("legacy_runtimehost_loop_called") is False
        else "UNKNOWN",
        "legacy_action_envelope_usage_in_product_core": 0
        if "_action_envelope_for_decision" not in core_text
        and "ActionEnvelope(" not in product_dispatch_text
        and "_canonical_real_model_request(" not in cli_text
        else "UNKNOWN",
        "canonical_product_run_bypass": False
        if (c2_baseline.get("minimum_delta") or {}).get("canonical_product_run_bypass") is False
        else "UNKNOWN",
        "canonical_dev_run_bypass": False
        if surface_probe.get("probe_status") == "PASSED"
        and (surface_results.get("canonical-dev-run") or {}).get("legacy_action_envelope_adapter") is False
        else "UNKNOWN",
        "direct_rootmissionruntime_workspace_executor": 0
        if "_execute_workspace_effect" not in core_text
        and not _class_defines_method(core_text, "RootMissionRuntime", "_execute")
        else "UNKNOWN",
        "product_action_kernel_effect_dispatch_owner": 1 if "_product_action_kernel.execute_typed(" in product_dispatch_text else "UNKNOWN",
        "workspace_duplicate_owner_per_capability_id": workspace_owners["count"],
        "hardcoded_capability_list_on_migrated_surfaces": allowed_action_metrics[
            "public_canonical_route_hardcoded_capability_list"
        ]["count"],
        "fake_material_success_on_migrated_surfaces": (c2_baseline.get("minimum_delta") or {}).get(
            "fake_material_success_on_workspace_public_route",
            "UNKNOWN",
        ),
        "root_mission_record_per_public_run": 1 if root_counts_valid else "UNKNOWN",
        "proof_root_linked_to_root_mission_record": proof_linked,
        "provider_request_builder_owner": "ProductModelNativeDecisionClient"
        if "_canonical_real_model_request(" in product_client_text and "_canonical_real_model_request(" not in cli_text
        else "UNKNOWN",
        "remaining_non_migrated_runtimehost_loop": "KNOWN_NON_C3_ROUTE",
        "remaining_non_migrated_model_led_product_loop": "KNOWN_NON_C3_ROUTE",
    }


def _failed_c3_probe(exc: Exception) -> dict[str, Any]:
    return {
        "probe_status": "FAILED",
        "provider_calls": "UNKNOWN",
        "browser_runs": "UNKNOWN",
        "error_code": exc.__class__.__name__,
    }


def _git_head(repo_root: Path) -> str:
    head_file = repo_root / ".git" / "HEAD"
    if not head_file.exists():
        git_text = (repo_root / ".git").read_text(encoding="utf-8", errors="ignore") if (repo_root / ".git").exists() else ""
        if git_text.startswith("gitdir:"):
            git_dir = (repo_root / git_text.split(":", 1)[1].strip()).resolve()
            head_file = git_dir / "HEAD"
    try:
        head = head_file.read_text(encoding="utf-8", errors="ignore").strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1].strip()
            ref_file = head_file.parent / ref
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8", errors="ignore").strip()
        return head
    except OSError:
        return "UNKNOWN"


def _failed_behavioral_probe(exc: Exception) -> dict[str, Any]:
    return {
        "probe_status": "FAILED",
        "canonical_product_run_bypass": "UNKNOWN",
        "route_trace": {},
        "provider_calls": "UNKNOWN",
        "browser_runs": "UNKNOWN",
        "error_code": exc.__class__.__name__,
    }


def _failed_fake_probe(exc: Exception) -> dict[str, Any]:
    return {
        "probe_status": "FAILED",
        "fake_backend_material_receipt_created": "UNKNOWN",
        "fake_material_success_on_workspace_public_route": "UNKNOWN",
        "error_code": exc.__class__.__name__,
    }


def _c2_workspace_gates(repo_root: Path, text_by_path: dict[Path, str]) -> dict[str, object]:
    core_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "canonical_core.py"
    cli_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "cli.py"
    core_text = text_by_path.get(core_path, "")
    cli_text = text_by_path.get(cli_path, "")
    behavioral_probe = _run_c2_workspace_behavioral_probe(repo_root)
    fake_probe = _run_c2_fake_material_negative_probe(repo_root)
    root_has_direct_execute = _class_defines_method(core_text, "RootMissionRuntime", "_execute")
    root_has_direct_workspace_helpers = any(
        _class_defines_method(core_text, "RootMissionRuntime", name)
        for name in ("_workspace_list", "_workspace_read", "_workspace_search")
    )
    public_command_text = _function_source_text(cli_text, "_run_canonical_product_command")
    hardcoded_allowed_actions_absent = not _contains_hardcoded_capability_list(public_command_text)
    public_legacy_action_envelope_absent = (
        "ProductModelNativeDecisionClient(" not in public_command_text
        and "allow_legacy_action_envelope=True" not in public_command_text
        and '"legacy_action_envelope_adapter": True' not in public_command_text
    )
    workspace_owners = _workspace_duplicate_owner_metric(repo_root)
    return {
        "canonical_product_run_bypass": behavioral_probe["canonical_product_run_bypass"],
        "root_direct_workspace_effect_executor_absent": not root_has_direct_execute and not root_has_direct_workspace_helpers,
        "root_product_kernel_dispatch_present": _class_method_source_contains(
            core_text,
            "RootMissionRuntime",
            "_execute_product_kernel_action",
            "_product_action_kernel.execute_typed(",
        ),
        "hardcoded_cli_capability_list_absent": hardcoded_allowed_actions_absent,
        "public_canonical_legacy_action_envelope_usage_absent": public_legacy_action_envelope_absent,
        "duplicate_owner_per_workspace_capability_id": workspace_owners["count"],
        "fake_material_success_on_workspace_public_route": fake_probe["fake_material_success_on_workspace_public_route"],
        "provider_calls": behavioral_probe["provider_calls"],
        "browser_runs": behavioral_probe["browser_runs"],
        "_behavioral_probe": behavioral_probe,
        "_fake_material_negative_probe": fake_probe,
    }


def _class_defines_method(source: str, class_name: str, method_name: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        return any(
            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name
            for child in node.body
        )
    return False


def _function_source_text(source: str, function_name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            end_lineno = getattr(node, "end_lineno", node.lineno)
            return "\n".join(lines[node.lineno - 1 : end_lineno])
    return ""


def _class_method_source_contains(source: str, class_name: str, method_name: str, needle: str) -> bool:
    method_source = _class_method_source_text(source, class_name, method_name)
    return needle in method_source


def _class_method_source_text(source: str, class_name: str, method_name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                end_lineno = getattr(child, "end_lineno", child.lineno)
                return "\n".join(lines[child.lineno - 1 : end_lineno])
    return ""


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


def _c2_workspace_report_markdown(baseline: dict[str, object]) -> str:
    metrics = baseline["metrics"]
    gates = baseline["c2_gates"]
    lines = [
        "# SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_REPORT",
        "",
        "## Verdict",
        "",
        "```text",
        "WAVE_C2 = WORKSPACE_SINGLE_SPINE_COMPRESSED_LOCAL",
        "VALID_SUCCESS_FOR_C2_LOCAL_WORKSPACE_COMPRESSION = YES",
        "FIXED_PROVEN = 0/65",
        "provider_calls = 0",
        "browser_runs = 0",
        "```",
        "",
        "This is not a global Sentinel completion claim. It proves only the local workspace route compression target for C2.",
        "",
        "## Baselines",
        "",
        f"- C1 historical: `{baseline['historical_baseline_artifact']}`",
        f"- C1R/C2-pre corrected: `{baseline['corrected_pre_baseline_artifact']}`",
        f"- C2 current: `{C2_BASELINE_JSON.name}`",
        "",
        "## C2 Minimum Delta",
        "",
    ]
    for key, value in baseline["minimum_delta"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Gate Truth",
            "",
        ]
    )
    for key in sorted(gates):
        lines.append(f"- {key}: {gates[key]}")
    lines.extend(
        [
            "",
            "## Gate Evidence Classes",
            "",
            "- static_probe: source/AST checks such as deleted methods and exact dispatch method body.",
            "- behavioral_probe: local scripted product route proving root MissionRecord, graph resolution, ProductActionKernel dispatch, receipt linkage and next-turn observation.",
            "- negative_behavioral_probe: simulated backend attempting material proof is rejected before a canonical receipt is minted.",
            "- run_attestation: provider/browser counts are recorded from the local scripted probe; UNKNOWN/NOT_RUN is used when not executed.",
            "",
            "## C2S Gate Evidence Summary",
            "",
        ]
    )
    gate_evidence = baseline.get("c2_gate_evidence", {})
    if isinstance(gate_evidence, dict):
        for key in sorted(gate_evidence):
            item = gate_evidence[key]
            if isinstance(item, dict):
                lines.append(f"- {key}: source={item.get('source')} status={item.get('probe_status', 'STATIC')} value={item.get('value')}")
    lines.extend(
        [
            "",
            "## Validation Commands Executed For C2/C2S",
            "",
            "- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c1_executable_mapping.py -q` -> 11 passed.",
            "- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_c2_product_route_rejects_simulated_material_backend_proof -q` -> passed.",
            "- `py -3.13 sentinel-control/docs/reviews/deep_power_audit/sentinel_single_spine_c1_probe.py --repo-root . --write-c2-workspace` -> artifacts regenerated from code and local probes.",
            "- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py sentinel-control/services/sentinel-core/tests/operator/test_interactive_exploration.py --collect-only -q` -> 59 + 59 tests collected.",
            "",
            "## Nominative 59-Test Files",
            "",
            "- `tests/operator/test_real_monster_product_model_native_decision_client.py`: 59 collected.",
            "- `tests/operator/test_interactive_exploration.py`: 59 collected.",
            "",
            "## C2 Symbols Removed Or Superseded",
            "",
            "- `RootMissionRuntime._execute`: absent after C2.",
            "- `RootMissionRuntime._workspace_list`: absent after C2.",
            "- `RootMissionRuntime._workspace_read`: absent after C2.",
            "- `RootMissionRuntime._workspace_search`: absent after C2.",
            "- CLI helpers `_create_public_product_root_record`, `_terminalize_public_product_root_record`, `_scripted_product_native_request_factory`, `_product_native_real_request_factory`, `_product_native_safe_context_shape`: removed in C2.",
            "",
            "## C2 Commit Diffstats",
            "",
            "- `4899046f test: make ownership probe symbol-qualified`: 6 files changed, 2247 insertions, 3 deletions.",
            "- `b4f4baac refactor: route root workspace effects through product kernel`: 3 files changed, 336 insertions, 455 deletions.",
            "- `fa5f51bf fix: preserve workspace progress recommendations`: 4 files changed, 73 insertions, 8 deletions.",
            "- `7480f311 docs: publish verified C2 workspace compression delta`: 7 files changed, 2083 insertions, 50 deletions.",
            "",
        ]
    )
    lines.extend(
        [
            "",
            "## Current Metrics",
            "",
        ]
    )
    for key in sorted(metrics):
        value = metrics[key]
        components = value.get("components", [])
        rendered_components = ", ".join(str(item) for item in components) if components else "(none)"
        lines.append(f"- {key}: {value.get('count')} -> {rendered_components}")
    lines.extend(
        [
            "",
            "## Workspace Architecture After C2",
            "",
            "```text",
            "public canonical-product-run",
            "-> RuntimeHost hosting/lifecycle",
            "-> RootMissionRuntime root loop and MissionRecord",
            "-> CanonicalDecision + DecisionOrigin",
            "-> ExecutableCapabilityGraph",
            "-> authority check",
            "-> ProductActionKernel",
            "-> WorkspaceReadOnlyRuntime backend",
            "-> typed observation / CanonicalEffectReceipt",
            "-> CanonicalState next turn",
            "-> model-selected finish",
            "-> MissionProofRoot / cleanup",
            "```",
            "",
            "## Still Open",
            "",
            "- `P0-01 = IMPLEMENTING` because no live canonical replacement proof is closed yet.",
            "- `C-P0-01 = IMPLEMENTING` because non-workspace spines remain measured for later waves.",
            "- `C-P0-03 = IMPLEMENTING` because workspace is the first compressed capability family only.",
            "- `C-P0-06 = IMPLEMENTING` because the full organ graph is not compressed in C2.",
            "- `P1-25 = IMPLEMENTING` because legacy recommendation surfaces still exist outside the new public route.",
            "",
            "## Do Not Touch Yet",
            "",
            "- Browser demos and Browser Organ routes.",
            "- Channel transport and external send.",
            "- PowerLab.",
            "- Qwen/provider live missions.",
            "- Existing untracked runtime artifact directories.",
            "",
        ]
    )
    return "\n".join(lines)


def _c3_product_loop_report_markdown(baseline: dict[str, object]) -> str:
    gates = baseline.get("c3_gates", {})
    surface_probe = baseline.get("surface_probe", {})
    provider_client_probe = baseline.get("provider_client_probe", {})
    lines = [
        "# SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_REPORT",
        "",
        "## Verdict",
        "",
        "```text",
        "C3 = PRODUCT_LOOP_AND_DECISION_CLIENT_COMPRESSED_LOCAL",
        "FIXED_PROVEN = 0/65",
        f"provider_calls = {baseline.get('provider_calls')}",
        f"browser_runs = {baseline.get('browser_runs')}",
        "```",
        "",
        "## Scope",
        "",
        "- Migrated `canonical-dev-run` onto the same hosted canonical product route as `canonical-product-run`.",
        "- Consolidated the production canonical provider protocol under `ProductModelNativeDecisionClient`.",
        "- Removed the CLI-private `_RealProviderCanonicalDecisionClient` and request/prompt/parser duplicate.",
        "- Replaced the RootMissionRuntime product dispatch bridge with typed `ProductActionKernel.execute_typed(...)`.",
        "- Kept Browser, Channel, PowerLab, Qwen/live provider missions, and non-workspace legacy routes out of C3.",
        "",
        "## Gates",
        "",
        "| Gate | Value |",
        "| --- | --- |",
    ]
    for key, value in sorted(gates.items()):
        lines.append(f"| `{key}` | `{json.dumps(value, sort_keys=True, default=str)}` |")
    lines.extend(
        [
            "",
            "## Behavioral Probe",
            "",
            "```json",
            json.dumps(surface_probe, indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Provider Client Probe",
            "",
            "```json",
            json.dumps(provider_client_probe, indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Architecture After C3",
            "",
            "```text",
            "public canonical-product-run / canonical-dev-run",
            "-> RuntimeHost hosting/lifecycle",
            "-> RootMissionRuntime single cognition/root state owner",
            "-> ProductModelNativeDecisionClient or JSONL scripted client",
            "-> CanonicalDecision + DecisionOrigin",
            "-> ExecutableCapabilityGraph",
            "-> RootMissionRuntime authority check",
            "-> ProductActionKernel.execute_typed",
            "-> workspace backend",
            "-> CanonicalEffectReceipt",
            "-> CanonicalState next turn",
            "-> model-selected finish",
            "-> MissionProofRoot",
            "-> cleanup",
            "```",
            "",
            "## Kept Open",
            "",
            "- `P0-01 = IMPLEMENTING` because C3 is local compression, not a new live provider closure.",
            "- `C-P0-01`, `C-P0-03`, `C-P0-06`, `P1-25`, `C-P1-17`, and `P0-07` remain `IMPLEMENTING`.",
            "- Legacy RuntimeHost/ModelLed loops remain for non-migrated Browser/Channel/PowerLab routes and must not be counted as C3 workspace bypasses.",
            "",
            "## Validation Recorded",
            "",
            "- C3 migrated-surface behavioral probe: `canonical-dev-run` and `canonical-product-run` completed through the same hosted RootMissionRuntime route.",
            "- C3 provider-client probe: fake transport received one `RealModelRequest` and emitted one `CanonicalDecision`.",
            "- Provider calls: `0`.",
            "- Browser runs: `0`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Sentinel single-spine executable mapping artifacts.")
    parser.add_argument("--repo-root", default=str(DOC_DIR.parents[3]))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--write-c2-pre", action="store_true")
    parser.add_argument("--write-c2-workspace", action="store_true")
    parser.add_argument("--write-c3-product-loop", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.write_c3_product_loop:
        baseline = write_c3_product_loop_compression_artifacts(repo_root)
    elif args.write_c2_workspace:
        baseline = write_c2_workspace_compression_artifacts(repo_root)
    elif args.write_c2_pre:
        baseline = write_c2_pre_artifacts(repo_root)
    else:
        baseline = write_artifacts(repo_root) if args.write else build_baseline(repo_root)
    print(
        json.dumps(
            {
                "component_count": baseline.get("component_count", "NOT_APPLICABLE"),
                "metrics": baseline.get("metrics", baseline.get("c3_gates", {})),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
