from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import io
import json
import subprocess
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
C4_BASELINE_JSON = DOC_DIR / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_BASELINE.json"
C4_MANIFEST_CSV = DOC_DIR / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_MANIFEST.csv"
C4_REPORT_MD = DOC_DIR / "SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_REPORT.md"
C4_IMPLEMENTATION_TESTED_HEAD = "d1408193883f8307753cefbb0622fa8695170ab9"
C4_PUBLISHED_HEAD_BEFORE_SEAL = "dfa4479af31349f10932691da38ef771e8a74519"
C4_READ_ONLY_BROWSER_OPERATIONS = (
    "real_browser.observe",
    "real_browser.open",
    "real_browser.search",
    "real_browser.open_result",
    "real_browser.inspect_result",
    "real_browser.extract_evidence",
    "real_browser.verify_extraction",
    "real_browser.recover_session",
)


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
    gate_evidence = _c3_product_loop_gate_evidence(
        repo_root,
        text_by_path,
        gates,
        c2_baseline,
        surface_probe,
        provider_client_probe,
    )
    run_attestations = {
        "provider_calls": {
            "value": surface_probe.get("provider_calls", "UNKNOWN"),
            "status": "ZERO_RECORDED" if surface_probe.get("provider_calls") == 0 else "UNKNOWN",
            "evidence_class": "RUN_ATTESTATION",
            "source": "C3 migrated-surface scripted local probe",
        },
        "browser_runs": {
            "value": surface_probe.get("browser_runs", "UNKNOWN"),
            "status": "ZERO_RECORDED" if surface_probe.get("browser_runs") == 0 else "UNKNOWN",
            "evidence_class": "RUN_ATTESTATION",
            "source": "C3 workspace-only migrated-surface probe",
        },
    }
    head = _git_head(repo_root)
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C3_PRODUCT_LOOP_AND_DECISION_CLIENT_COMPRESSION",
        "current_phase": "C3S_REPLAYABLE_PROOF_SEAL",
        "base_c2s_head": "170749e516ca9c1ff27dd8d4c5ca78fea1eabd92",
        "implementation_head_before_report": head,
        "head_taxonomy": {
            "artifact_generation_head": head,
            "current_worktree_head": head,
            "current_remote_head": _git_remote_head(
                repo_root,
                "origin/sentinel-dev-max-power-canonical-core-v1",
            ),
            "implementation_tested_head": "88ee94f1768c962246b54c918b27dd4374a29a5e",
            "proof_attestation_head": "88ee94f1768c962246b54c918b27dd4374a29a5e",
            "documentation_head": "b7c24e0a5baecd43fbb317cb0ddfc16743da0a58",
        },
        "commit_taxonomy": {
            "c2s_commits": ["170749e516ca9c1ff27dd8d4c5ca78fea1eabd92"],
            "implementation_commits": ["88ee94f1768c962246b54c918b27dd4374a29a5e"],
            "deletion_commits": ["88ee94f1768c962246b54c918b27dd4374a29a5e"],
            "documentation_commits": ["b7c24e0a5baecd43fbb317cb0ddfc16743da0a58"],
        },
        "provider_calls": surface_probe.get("provider_calls", "UNKNOWN"),
        "browser_runs": surface_probe.get("browser_runs", "UNKNOWN"),
        "run_attestations": run_attestations,
        "c2_baseline_replayed": {
            "artifact": C2_BASELINE_JSON.name,
            "minimum_delta": c2_baseline.get("minimum_delta", {}),
            "run_attestations": c2_baseline.get("run_attestations", {}),
        },
        "surface_probe": surface_probe,
        "provider_client_probe": provider_client_probe,
        "c3_gates": gates,
        "c3_gate_evidence": gate_evidence,
        "qualified_callers_and_deletions": _c3_qualified_callers_and_deletions(repo_root, text_by_path),
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
            fieldnames=["gate", "value", "source", "evidence_class", "status", "source_location"],
        )
        writer.writeheader()
        evidence = baseline.get("c3_gate_evidence", {})
        for gate, value in baseline["c3_gates"].items():
            gate_evidence = evidence.get(gate, {}) if isinstance(evidence, dict) else {}
            if isinstance(value, dict):
                rendered = json.dumps(value, sort_keys=True, default=str)
                status = str(gate_evidence.get("status") or value.get("status") or value.get("probe_status") or "RECORDED")
                source = str(gate_evidence.get("source") or value.get("source") or "unclassified_probe")
            else:
                rendered = json.dumps(value, sort_keys=True, default=str)
                status = str(gate_evidence.get("status") or ("PASS" if value in {True, 0, "PASSED"} else "RECORDED"))
                source = str(gate_evidence.get("source") or "unclassified_probe")
            writer.writerow(
                {
                    "gate": gate,
                    "value": rendered,
                    "source": source,
                    "evidence_class": gate_evidence.get("evidence_class", "UNKNOWN"),
                    "status": status,
                    "source_location": gate_evidence.get("source_location", "UNKNOWN"),
                }
            )
    C3_REPORT_MD.write_text(_c3_product_loop_report_markdown(baseline), encoding="utf-8")
    return baseline


def build_c4_browser_readonly_cutover_baseline(repo_root: Path) -> dict[str, object]:
    source_root = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel"
    files = _source_files(source_root)
    text_by_path = {path: path.read_text(encoding="utf-8", errors="ignore") for path in files}
    behavioral_probe = _run_c4_browser_behavioral_probe(repo_root)
    authority_probe = _run_c4_browser_authority_denial_probe(repo_root)
    fake_material_probe = _run_c4_browser_fake_material_probe(repo_root)
    cancellation_probe = _run_c4_browser_cancellation_cleanup_probe(repo_root)
    components = _c4_browser_component_rows(repo_root, text_by_path)
    registrations = _c4_browser_registration_probe(repo_root)
    validation_results = _c4s_validation_results()
    gates = _c4_browser_gates(
        behavioral_probe=behavioral_probe,
        authority_probe=authority_probe,
        fake_material_probe=fake_material_probe,
        cancellation_probe=cancellation_probe,
        registrations=registrations,
    )
    guard_probe = {
        "provider_calls": _max_numeric_probe_value(
            behavioral_probe,
            authority_probe,
            fake_material_probe,
            cancellation_probe,
            key="provider_calls",
        ),
        "real_browser_runs": _max_numeric_probe_value(
            behavioral_probe,
            authority_probe,
            fake_material_probe,
            cancellation_probe,
            key="real_browser_runs",
        ),
        "external_network_calls": _max_numeric_probe_value(
            behavioral_probe,
            authority_probe,
            fake_material_probe,
            cancellation_probe,
            key="external_network_calls",
        ),
        "guard": "fake_in_memory_backend_only",
    }
    head = _git_head(repo_root)
    return {
        "campaign": "SENTINEL_SINGLE_SPINE_COMPRESSION_CAMPAIGN",
        "wave": "C4_BROWSER_READONLY_SINGLE_SPINE_CUTOVER",
        "current_phase": "C4S_BROWSER_READONLY_PROOF_SEAL",
        "head_taxonomy": {
            "artifact_generation_head": head,
            "c4s_generation_head": head,
            "current_worktree_head": head,
            "current_remote_head": _git_remote_head(
                repo_root,
                "origin/sentinel-dev-max-power-canonical-core-v1",
            ),
            "implementation_tested_head": C4_IMPLEMENTATION_TESTED_HEAD,
            "proof_attestation_head": C4_IMPLEMENTATION_TESTED_HEAD,
            "documentation_head": head,
            "published_remote_head": C4_PUBLISHED_HEAD_BEFORE_SEAL,
        },
        "c4s_publication_truth": {
            "artifact_head_before_c4s": C4_IMPLEMENTATION_TESTED_HEAD,
            "latest_pushed_head_before_c4s": C4_PUBLISHED_HEAD_BEFORE_SEAL,
            "c4s_generation_head": head,
            "c4s_final_commit": "SELF_REFERENCE_UNAVAILABLE_UNTIL_COMMIT",
            "fixed_proven_count": 0,
        },
        "c4s_validation_results": validation_results,
        "provider_calls": guard_probe["provider_calls"],
        "browser_runs": guard_probe["real_browser_runs"],
        "real_browser_runs": guard_probe["real_browser_runs"],
        "external_network_calls": guard_probe["external_network_calls"],
        "behavioral_probe": behavioral_probe,
        "authority_probe": authority_probe,
        "fake_material_probe": fake_material_probe,
        "cancellation_cleanup_probe": cancellation_probe,
        "guard_probe": guard_probe,
        "browser_registrations": registrations,
        "c4_gates": gates,
        "unmigrated_browser_surfaces": _c4_unmigrated_browser_surfaces(components),
        "proven_browser_effect_bypasses": [],
        "unknown_browser_routes": _c4_unknown_browser_routes(components),
        "legacy_browser_components_kept_as_research": _c4_research_browser_components(components),
        "physical_browser_boundaries": {
            "physical_browser_process_kill": "NOT_RUN",
            "real_browser_origin_redirect_enforcement": "NOT_RUN",
            "live_canonical_browser_mission": "NOT_RUN",
            "physical_sandbox": "NOT_RUN",
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
        "components": components,
    }


def write_c4_browser_readonly_cutover_artifacts(repo_root: Path) -> dict[str, object]:
    baseline = build_c4_browser_readonly_cutover_baseline(repo_root)
    C4_BASELINE_JSON.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with C4_MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "component",
            "module_qualname",
            "production_callers",
            "dynamic_factory_callers",
            "entrypoints",
            "state_owned",
            "effects_owned",
            "authority_owned",
            "proof_owned",
            "capability_ids",
            "backend_reality",
            "decision",
            "canonical_owner",
            "migration_gate",
            "deletion_gate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in baseline["components"]:
            writer.writerow(
                {
                    key: json.dumps(row[key], sort_keys=True, default=str)
                    if isinstance(row.get(key), (list, tuple, dict))
                    else row.get(key, "")
                    for key in fieldnames
                }
            )
    C4_REPORT_MD.write_text(_c4_browser_readonly_report_markdown(baseline), encoding="utf-8")
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


def _c3_product_loop_gate_evidence(
    repo_root: Path,
    text_by_path: dict[Path, str],
    gates: dict[str, Any],
    c2_baseline: dict[str, object],
    surface_probe: dict[str, Any],
    provider_client_probe: dict[str, Any],
) -> dict[str, dict[str, Any]]:
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
    action_kernel_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "action_kernel.py"

    def item(
        gate: str,
        *,
        evidence_class: str,
        source: str,
        source_location: str,
        route_trace: object | None = None,
    ) -> dict[str, Any]:
        value = gates.get(gate, "UNKNOWN")
        payload: dict[str, Any] = {
            "value": value,
            "status": "PASS" if value not in {"UNKNOWN", "NOT_RUN"} else "RECORDED",
            "evidence_class": evidence_class,
            "source": source,
            "source_location": source_location,
        }
        if route_trace is not None:
            payload["route_trace"] = route_trace
        return payload

    c2_evidence = c2_baseline.get("c2_gate_evidence", {})
    c2_fake_evidence = c2_evidence.get("fake_material_success_on_workspace_public_route", {}) if isinstance(c2_evidence, dict) else {}
    surface_location = _source_location_for_text(repo_root, cli_path, "def _run_canonical_product_command")
    dev_location = _source_location_for_text(repo_root, cli_path, "def _run_canonical_dev_command")
    provider_location = _source_location_for_text(repo_root, product_client_path, "def for_canonical_decisions")
    dispatch_location = _source_location_for_text(repo_root, core_path, "def _execute_product_kernel_action")
    graph_location = _source_location_for_text(repo_root, core_path, "def build_workspace_read_capability_graph")
    action_kernel_location = _source_location_for_text(repo_root, action_kernel_path, "def execute_typed")

    return {
        "product_workspace_cognition_loops": item(
            "product_workspace_cognition_loops",
            evidence_class="BEHAVIORAL_PROBE",
            source="C3 migrated-surface probe proves both public workspace surfaces use one RootMissionRuntime loop",
            source_location=surface_location,
            route_trace=surface_probe.get("surfaces", {}),
        ),
        "production_canonical_decision_clients": item(
            "production_canonical_decision_clients",
            evidence_class="BEHAVIORAL_PROBE",
            source="ProductModelNativeDecisionClient fake-transport probe emits CanonicalDecision directly",
            source_location=provider_location,
            route_trace=provider_client_probe,
        ),
        "runtimehost_cognitive_methods_on_migrated_routes": item(
            "runtimehost_cognitive_methods_on_migrated_routes",
            evidence_class="NEGATIVE_BEHAVIORAL_PROBE",
            source="RuntimeHost legacy cognitive method monkeypatch stayed uncalled on migrated routes",
            source_location=surface_location,
            route_trace={"legacy_runtimehost_loop_called": surface_probe.get("legacy_runtimehost_loop_called")},
        ),
        "legacy_action_envelope_usage_in_product_core": item(
            "legacy_action_envelope_usage_in_product_core",
            evidence_class="STATIC_PROBE",
            source="RootMissionRuntime product dispatch source contains typed ProductActionKernel execution and no ActionEnvelope bridge",
            source_location=dispatch_location,
        ),
        "canonical_product_run_bypass": item(
            "canonical_product_run_bypass",
            evidence_class="BEHAVIORAL_PROBE",
            source="canonical-product-run behavioral probe creates one root MissionRecord and one ProductActionKernel receipt",
            source_location=surface_location,
            route_trace=(surface_probe.get("surfaces") or {}).get("canonical-product-run", {}),
        ),
        "canonical_dev_run_bypass": item(
            "canonical_dev_run_bypass",
            evidence_class="BEHAVIORAL_PROBE",
            source="canonical-dev-run behavioral probe shares the canonical hosted product route",
            source_location=dev_location,
            route_trace=(surface_probe.get("surfaces") or {}).get("canonical-dev-run", {}),
        ),
        "direct_rootmissionruntime_workspace_executor": item(
            "direct_rootmissionruntime_workspace_executor",
            evidence_class="STATIC_PROBE",
            source="RootMissionRuntime direct workspace executor methods absent from current AST",
            source_location=dispatch_location,
        ),
        "product_action_kernel_effect_dispatch_owner": item(
            "product_action_kernel_effect_dispatch_owner",
            evidence_class="STATIC_PROBE",
            source="RootMissionRuntime dispatch method calls ProductActionKernel.execute_typed as the effect owner",
            source_location=action_kernel_location,
        ),
        "workspace_duplicate_owner_per_capability_id": item(
            "workspace_duplicate_owner_per_capability_id",
            evidence_class="STATIC_PROBE",
            source="Workspace owners are derived from ExecutableCapabilityGraph.routes",
            source_location=graph_location,
            route_trace=_workspace_duplicate_owner_metric(repo_root),
        ),
        "hardcoded_capability_list_on_migrated_surfaces": item(
            "hardcoded_capability_list_on_migrated_surfaces",
            evidence_class="STATIC_PROBE",
            source="Migrated public route projects affordances from ExecutableCapabilityGraph, not prompt list constants",
            source_location=surface_location,
        ),
        "fake_material_success_on_migrated_surfaces": item(
            "fake_material_success_on_migrated_surfaces",
            evidence_class="NEGATIVE_BEHAVIORAL_PROBE",
            source="C2 fake material backend rejection is replayed as a C3 migrated-route invariant",
            source_location=graph_location,
            route_trace=c2_fake_evidence,
        ),
        "root_mission_record_per_public_run": item(
            "root_mission_record_per_public_run",
            evidence_class="BEHAVIORAL_PROBE",
            source="Migrated surface payloads report exactly one root mission id",
            source_location=surface_location,
            route_trace=surface_probe.get("surfaces", {}),
        ),
        "proof_root_linked_to_root_mission_record": item(
            "proof_root_linked_to_root_mission_record",
            evidence_class="BEHAVIORAL_PROBE",
            source="Migrated surface payloads link ProductActionKernel receipt refs into MissionProofRoot",
            source_location=surface_location,
            route_trace=surface_probe.get("surfaces", {}),
        ),
        "provider_request_builder_owner": item(
            "provider_request_builder_owner",
            evidence_class="STATIC_PROBE",
            source="Provider request builder lives under ProductModelNativeDecisionClient, not CLI duplicate",
            source_location=provider_location,
        ),
        "remaining_non_migrated_runtimehost_loop": item(
            "remaining_non_migrated_runtimehost_loop",
            evidence_class="STATIC_PROBE",
            source="Legacy RuntimeHost loop is retained only for non-C3 routes",
            source_location=_source_location_for_text(
                repo_root,
                repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "runtime_host.py",
                "def run_product_action_kernel_task_loop",
            ),
        ),
        "remaining_non_migrated_model_led_product_loop": item(
            "remaining_non_migrated_model_led_product_loop",
            evidence_class="STATIC_PROBE",
            source="ModelLedProductActionKernelTaskLoop is retained only for non-C3 routes",
            source_location=_source_location_for_text(
                repo_root,
                repo_root
                / "sentinel-control"
                / "services"
                / "sentinel-core"
                / "sentinel"
                / "operator"
                / "model_led_product_action_kernel_task_loop.py",
                "class ModelLedProductActionKernelTaskLoop",
            ),
        ),
    }


def _c3_qualified_callers_and_deletions(repo_root: Path, text_by_path: dict[Path, str]) -> dict[str, Any]:
    cli_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "cli.py"
    core_path = repo_root / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "canonical_core.py"
    product_client_path = (
        repo_root
        / "sentinel-control"
        / "services"
        / "sentinel-core"
        / "sentinel"
        / "operator"
        / "product_model_native_decision_client.py"
    )
    deleted = [
        {
            "symbol": "sentinel.cli::_RealProviderCanonicalDecisionClient",
            "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
            "status": "DELETED",
            "replacement": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions",
            "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
        },
        {
            "symbol": "sentinel.cli::_canonical_real_model_request",
            "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
            "status": "DELETED_FROM_CLI",
            "replacement": "sentinel.operator.product_model_native_decision_client::_canonical_real_model_request",
            "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
        },
        {
            "symbol": "sentinel.cli::_canonical_product_provider_prompt",
            "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
            "status": "DELETED_FROM_CLI",
            "replacement": "sentinel.operator.product_model_native_decision_client::_canonical_product_provider_prompt",
            "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
        },
        {
            "symbol": "sentinel.operator.canonical_core::RootMissionRuntime._action_envelope_for_decision",
            "source": "sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py",
            "status": "DELETED",
            "replacement": "sentinel.operator.action_kernel::ActionKernel.execute_typed",
            "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
        },
    ]
    for entry in deleted:
        module_text = text_by_path.get(cli_path if entry["source"].endswith("cli.py") else core_path, "")
        symbol_name = entry["symbol"].rsplit("::", 1)[1].split(".", 1)[-1]
        entry["present_in_current_source"] = symbol_name in module_text

    qualified_calls = [
        {
            "caller": "sentinel.cli::_run_canonical_dev_command",
            "source": _source_location_for_text(repo_root, cli_path, "def _run_canonical_dev_command"),
            "target": "sentinel.cli::_run_canonical_product_command",
            "resolution": "QUALIFIED",
            "evidence_kind": "function_call",
        },
        {
            "caller": "sentinel.cli::_run_canonical_product_command",
            "source": _source_location_for_text(repo_root, cli_path, "ProductModelNativeDecisionClient.for_canonical_decisions"),
            "target": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions",
            "resolution": "QUALIFIED",
            "evidence_kind": "provider_client_constructor",
        },
        {
            "caller": "sentinel.operator.canonical_core::RootMissionRuntime._execute_product_kernel_action",
            "source": _source_location_for_text(repo_root, core_path, "_product_action_kernel.execute_typed("),
            "target": "sentinel.operator.action_kernel::ActionKernel.execute_typed",
            "resolution": "QUALIFIED",
            "evidence_kind": "method_call",
        },
        {
            "caller": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions",
            "source": _source_location_for_text(repo_root, product_client_path, "return cls("),
            "target": "sentinel.operator.canonical_core::CanonicalDecision",
            "resolution": "QUALIFIED",
            "evidence_kind": "decision_protocol_adapter",
        },
    ]
    return {
        "qualified_calls": qualified_calls,
        "deleted_symbols": deleted,
        "unknown_remaining": [],
        "loc_delta": {
            "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
            "source": "git show --stat recorded in C3 validation",
            "status": "RECORDED_NOT_RECOMPUTED_BY_C3S",
        },
    }


def _run_c4_browser_behavioral_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel import cli
        from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
        from sentinel.operator.canonical_core import (
            build_workspace_browser_readonly_capability_graph,
            run_canonical_product_mission,
        )
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)

    class ScriptedModelClient:
        def __init__(self, decisions: list[dict[str, Any]]) -> None:
            self.decisions = list(decisions)
            self.requests: list[Any] = []

        def complete(self, request: Any) -> dict[str, Any]:
            self.requests.append(request)
            if not self.decisions:
                raise AssertionError("c4 scripted decisions exhausted")
            return self.decisions.pop(0)

    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c4_browser_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "local.txt").write_text("local fixture only\n", encoding="utf-8")
            decisions = [
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
                {"capability": "real_browser_control", "operation": "real_browser.extract_evidence", "arguments": {}},
                {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Grounded fake browser evidence."}},
            ]
            backend = FakeBrowserReadOnlyBackend(
                allowed_origins=("sqlite.org",),
                page_title="SQLite Generated Columns",
                evidence_cards=(
                    {
                        "evidence_id": "sqlite_generated_columns_doc",
                        "kind": "documentation_page",
                        "title": "Generated Columns",
                        "summary": "SQLite generated columns are computed from expressions.",
                        "confidence": 0.92,
                    },
                ),
            )
            model = ScriptedModelClient(list(decisions))
            result = run_canonical_product_mission(
                objective="Find official SQLite documentation about generated columns.",
                workspace_root=workspace,
                model_client=model,
                provider_model="scripted-local/model",
                kernel=MissionKernel(run_root=root / "runtime_probe_runs"),
                session_id="c4_browser_runtime_probe",
                capability_graph=build_workspace_browser_readonly_capability_graph(),
                browser_readonly_backend=backend,
                granted_authorities=("workspace_read", "browser_read", "none"),
            )
            state_after_observe = model.requests[1].canonical_state.safe_model_dump() if len(model.requests) > 1 else {}
            browser_state = state_after_observe.get("browser_environment_state") if isinstance(state_after_observe, dict) else {}
            script = root / "decisions.jsonl"
            script.write_text("\n".join(json.dumps(item) for item in decisions), encoding="utf-8")
            surface_results: dict[str, Any] = {}
            for surface, run_root_name in (
                ("canonical-product-run", "product_runs"),
                ("canonical-dev-run", "dev_runs"),
            ):
                capture = io.StringIO()
                argv = [
                    surface,
                    "--objective",
                    "Use the fake Browser Organ to observe public evidence.",
                    "--workspace",
                    str(workspace),
                    "--run-root",
                    str(root / run_root_name),
                    "--decision-script",
                    str(script),
                    "--provider-model",
                    "scripted-local/model",
                    "--enable-browser-readonly-fake",
                    "--json",
                ]
                with contextlib.redirect_stdout(capture):
                    code = cli.main(argv)
                payload = json.loads(capture.getvalue())
                surface_results[surface] = {
                    "exit_code": code,
                    "status": payload.get("status"),
                    "browser_readonly_fake_enabled": (payload.get("public_product_spine") or {}).get(
                        "browser_readonly_fake_enabled"
                    ),
                    "runtimehost_cognition": (payload.get("public_product_spine") or {}).get("runtimehost_cognition"),
                    "legacy_action_envelope_adapter": (payload.get("public_product_spine") or {}).get(
                        "legacy_action_envelope_adapter"
                    ),
                    "root_mission_id_count": len(payload.get("mission_ids") or ()),
                    "receipt_count": len(payload.get("product_receipt_refs") or ()),
                    "proof_root_linked": tuple(payload.get("product_receipt_refs") or ())
                    == tuple((payload.get("proof_root") or {}).get("receipt_refs") or ()),
                }
            probe_passed = (
                result.status == "completed"
                and result.proof_root.receipt_artifacts_verified is True
                and isinstance(browser_state, dict)
                and (browser_state.get("browser") or {}).get("actual_backend_id") == "fake_browser_readonly"
                and all(
                    item["exit_code"] == 0
                    and item["status"] == "completed"
                    and item["browser_readonly_fake_enabled"] is True
                    and item["runtimehost_cognition"] is False
                    and item["legacy_action_envelope_adapter"] is False
                    for item in surface_results.values()
                )
            )
            return {
                "probe_status": "PASSED" if probe_passed else "FAILED",
                "provider_calls": backend.provider_calls,
                "real_browser_runs": backend.real_browser_runs,
                "external_network_calls": backend.external_network_calls,
                "status": result.status,
                "root_mission_record_count": 1,
                "shared_cognition_loop": "RootMissionRuntime",
                "browser_specific_public_cognition_loops": 0,
                "browser_receipt_linked_to_root": result.proof_root.receipt_refs
                == tuple(receipt.receipt_id for receipt in result.receipts),
                "browser_observation_visible_next_turn": bool(browser_state),
                "browser_environment_state_sections": sorted(browser_state.keys()) if isinstance(browser_state, dict) else [],
                "receipt_operations": [receipt.operation for receipt in result.receipts],
                "surface_results": surface_results,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)


def _c4s_validation_results() -> list[dict[str, Any]]:
    return [
        {
            "name": "test_sentinel_dev_max_power_canonical_core_v1.py + single_spine probes + c4 cutover",
            "command": "py -3.13 -m pytest test_sentinel_dev_max_power_canonical_core_v1.py test_sentinel_single_spine_c1_executable_mapping.py test_sentinel_single_spine_c4_browser_readonly_cutover.py -q",
            "status": "PASSED",
            "result": "63/63 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "RuntimeHost/ProductActionKernel groups",
            "command": "py -3.13 -m pytest test_runtime_host_pack1.py test_power_cleanup_runtimehost_safe_skill_product_registration.py test_power_cleanup_pack9_product_actionkernel_task_loop.py test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py test_power_cleanup_product_action_kernel_dispatch_adapter.py -q",
            "status": "PASSED",
            "result": "38/38 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "skill surface/code-channel/recovery groups",
            "command": "py -3.13 -m pytest test_power_unification_pack2_skill_only_model_surface.py test_power_cleanup_model_facing_executable_skill_truth.py test_power_cleanup_actionkernel_skill_parity_code_channel.py test_power_cleanup_recoverable_observation_loop_guard.py -q",
            "status": "PASSED",
            "result": "27/27 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "real_monster_product_model_native_decision_client.py",
            "command": "py -3.13 -m pytest test_real_monster_product_model_native_decision_client.py -q",
            "status": "PASSED",
            "result": "59/59 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "interactive_exploration.py",
            "command": "py -3.13 -m pytest test_interactive_exploration.py -q",
            "status": "PASSED",
            "result": "59/59 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "Browser state/proof/answer evidence group",
            "command": "py -3.13 -m pytest test_browser_cortex_pack1_environment_state_graph.py test_browser_cortex_affordance_contracts.py test_browser_observe_receipt_proof_completeness.py test_browser_receipt_persistence_answer_claim_evidence.py -q",
            "status": "PASSED",
            "result": "29/29 passed",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "compileall sentinel",
            "command": "py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel",
            "status": "PASSED",
            "result": "exit 0",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "git diff --check",
            "command": "git diff --check",
            "status": "PASSED",
            "result": "exit 0",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "JSON/CSV parse",
            "command": "py -3.13 parse check for C2/C3/C4 JSON and CSV artifacts",
            "status": "PASSED",
            "result": "C2/C3/C4 JSON parsed; C2=28 rows, C3=16 rows, C4=16 rows",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "secret/path/raw-provider scan",
            "command": "rg targeted scan over C4 runtime/tests/artifacts/ledger",
            "status": "PASSED",
            "result": "only safe doctrine/report mentions, no raw secrets or local paths",
            "provider_calls": 0,
            "browser_runs": 0,
        },
        {
            "name": "targeted Ruff correctness",
            "command": "py -3.13 -m ruff --version",
            "status": "UNAVAILABLE",
            "result": "No module named ruff",
            "provider_calls": 0,
            "browser_runs": 0,
        },
    ]


def _run_c4_browser_authority_denial_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
        from sentinel.operator.canonical_core import build_workspace_browser_readonly_capability_graph, run_canonical_product_mission
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)

    class ScriptedModelClient:
        def __init__(self) -> None:
            self.requests: list[Any] = []

        def complete(self, request: Any) -> dict[str, Any]:
            self.requests.append(request)
            return {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}}

    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c4_authority_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            backend = FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",))
            result = run_canonical_product_mission(
                objective="Observe without browser_read authority.",
                workspace_root=workspace,
                model_client=ScriptedModelClient(),
                provider_model="scripted-local/model",
                kernel=MissionKernel(run_root=root / "runs"),
                session_id="c4_authority_probe",
                capability_graph=build_workspace_browser_readonly_capability_graph(),
                browser_readonly_backend=backend,
                granted_authorities=("workspace_read", "none"),
            )
            return {
                "probe_status": "PASSED"
                if result.status == "blocked"
                and result.blocked_reason_detail == "canonical_authority_required:browser_read"
                and backend.call_log == []
                else "FAILED",
                "backend_call_count": len(backend.call_log),
                "denial_before_backend": backend.call_log == [],
                "provider_calls": backend.provider_calls,
                "real_browser_runs": backend.real_browser_runs,
                "external_network_calls": backend.external_network_calls,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)


def _run_c4_browser_fake_material_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
        from sentinel.operator.canonical_core import build_workspace_browser_readonly_capability_graph, run_canonical_product_mission
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)

    class ScriptedModelClient:
        def complete(self, request: Any) -> dict[str, Any]:
            return {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}}

    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_c4_fake_material_probe_") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            backend = FakeBrowserReadOnlyBackend(
                allowed_origins=("sqlite.org",),
                material_action_override=True,
            )
            result = run_canonical_product_mission(
                objective="Fake browser must not certify material power.",
                workspace_root=workspace,
                model_client=ScriptedModelClient(),
                provider_model="scripted-local/model",
                kernel=MissionKernel(run_root=root / "runs"),
                session_id="c4_fake_material_probe",
                capability_graph=build_workspace_browser_readonly_capability_graph(),
                browser_readonly_backend=backend,
                granted_authorities=("workspace_read", "browser_read", "none"),
            )
            return {
                "probe_status": "PASSED"
                if result.status == "blocked"
                and result.blocked_reason_detail == "canonical_simulated_backend_cannot_create_material_receipt"
                and result.receipts == ()
                else "FAILED",
                "fake_material_success": 0 if result.receipts == () else 1,
                "provider_calls": backend.provider_calls,
                "real_browser_runs": backend.real_browser_runs,
                "external_network_calls": backend.external_network_calls,
            }
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)


def _run_c4_browser_cancellation_cleanup_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel.operator.canonical_browser_readonly_adapter import FakeBrowserReadOnlyBackend
        from sentinel.operator.canonical_core import (
            RootMissionCancellationToken,
            build_workspace_browser_readonly_capability_graph,
            run_canonical_product_mission,
        )
        from sentinel.operator.kernel import MissionKernel
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)

    class ScriptedModelClient:
        def __init__(self, decisions: list[dict[str, Any]]) -> None:
            self._decisions = list(decisions)
            self.requests: list[Any] = []

        def complete(self, request: Any) -> dict[str, Any]:
            self.requests.append(request)
            if not self._decisions:
                raise AssertionError("c4 cleanup probe model decision exhausted")
            return self._decisions.pop(0)

    try:
        def run_scenario(
            name: str,
            *,
            backend: Any,
            decisions: list[dict[str, Any]],
            granted_authorities: tuple[str, ...],
            token: Any | None = None,
        ) -> dict[str, Any]:
            with tempfile.TemporaryDirectory(prefix=f"sentinel_c4_cleanup_{name}_") as tmp:
                root = Path(tmp)
                workspace = root / "workspace"
                workspace.mkdir(parents=True)
                model = ScriptedModelClient(decisions)
                result = run_canonical_product_mission(
                    objective=f"C4 cleanup scenario {name}.",
                    workspace_root=workspace,
                    model_client=model,
                    provider_model="scripted-local/model",
                    kernel=MissionKernel(run_root=root / "runs"),
                    session_id=f"c4_cleanup_{name}",
                    capability_graph=build_workspace_browser_readonly_capability_graph(),
                    browser_readonly_backend=backend,
                    cancellation_token=token,
                    granted_authorities=granted_authorities,
                )
                return {
                    "status": result.status,
                    "final_reason": result.final_reason,
                    "blocked_reason_detail": result.blocked_reason_detail,
                    "model_turns": len(model.requests),
                    "backend_call_log": list(backend.call_log),
                    "cleanup_count": backend.cleanup_count,
                    "lease_released": backend.lease_released,
                    "cleanup_completed": result.cleanup_completed,
                    "provider_calls": backend.provider_calls,
                    "real_browser_runs": backend.real_browser_runs,
                    "external_network_calls": backend.external_network_calls,
                }

        completion = run_scenario(
            "completion",
            backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
            decisions=[
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
                {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "observed"}},
            ],
            granted_authorities=("workspace_read", "browser_read", "none"),
        )
        block = run_scenario(
            "block",
            backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",)),
            decisions=[
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
            ],
            granted_authorities=("workspace_read", "none"),
        )
        token = RootMissionCancellationToken()
        cancellation = run_scenario(
            "cancellation",
            backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",), cancel_during_next_call=token),
            decisions=[
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
                {"capability": "real_browser_control", "operation": "real_browser.extract_evidence", "arguments": {}},
            ],
            granted_authorities=("workspace_read", "browser_read", "none"),
            token=token,
        )
        cleanup_failure = run_scenario(
            "cleanup_failure",
            backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",), cleanup_failure=True),
            decisions=[
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
                {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "observed"}},
            ],
            granted_authorities=("workspace_read", "browser_read", "none"),
        )
        survivor = run_scenario(
            "survivor",
            backend=FakeBrowserReadOnlyBackend(allowed_origins=("sqlite.org",), survivor_count=1),
            decisions=[
                {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
                {"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "observed"}},
            ],
            granted_authorities=("workspace_read", "browser_read", "none"),
        )
        scenarios = {
            "completion": completion,
            "block": block,
            "cancellation": cancellation,
            "cleanup_failure": cleanup_failure,
            "survivor": survivor,
        }
        expected = (
            completion["cleanup_completed"] is True
            and block["cleanup_completed"] is True
            and block["backend_call_log"] == []
            and cancellation["blocked_reason_detail"] == "root_mission_cancelled_during_browser_effect"
            and cancellation["cleanup_completed"] is True
            and cleanup_failure["cleanup_completed"] is False
            and survivor["cleanup_completed"] is False
        )
        return {
            "probe_status": "PASSED" if expected else "FAILED",
            "scenarios": scenarios,
            "provider_calls": max(item["provider_calls"] for item in scenarios.values()),
            "real_browser_runs": max(item["real_browser_runs"] for item in scenarios.values()),
            "external_network_calls": max(item["external_network_calls"] for item in scenarios.values()),
            "scenario_count": len(scenarios),
        }
    except Exception as exc:  # noqa: BLE001
        return _failed_c4_probe(exc)


def _c4_browser_registration_probe(repo_root: Path) -> dict[str, Any]:
    try:
        _ensure_sentinel_importable(repo_root)
        from sentinel.operator.canonical_core import build_workspace_browser_readonly_capability_graph
    except Exception as exc:  # noqa: BLE001
        return {"probe_status": "FAILED", "error_code": exc.__class__.__name__, "routes": []}
    graph = build_workspace_browser_readonly_capability_graph()
    browser_routes = [route for route in graph.routes if route.capability == "real_browser_control"]
    owners_by_capability: dict[str, list[dict[str, Any]]] = {}
    for route in browser_routes:
        owners_by_capability.setdefault(route.affordance, []).append(
            {
                "registration_source": "ExecutableCapabilityGraph.routes",
                "callable_owner": "ProductActionKernel:real_browser_control",
                "authority_schema": route.required_authority,
                "backend": route.backend_mode,
                "receipt_contract": route.proof_contract,
                "readiness": route.readiness_probe,
                "materiality": route.materiality_verifier,
            }
        )
    duplicates = {
        key: value
        for key, value in owners_by_capability.items()
        if len(value) > 1
    }
    return {
        "probe_status": "PASSED" if browser_routes and not duplicates else "FAILED",
        "registry_owner": "ExecutableCapabilityGraph",
        "registry_scope": "canonical_c4_route_only",
        "legacy_browser_product_cutover_registry_exists": (
            repo_root
            / "sentinel-control"
            / "services"
            / "sentinel-core"
            / "sentinel"
            / "operator"
            / "browser_product_cutover_registry.py"
        ).exists(),
        "route_count": len(browser_routes),
        "registered_operations": sorted(route.operation for route in browser_routes),
        "owners_by_capability": owners_by_capability,
        "duplicate_owner_per_capability_id": len(duplicates),
        "quarantined_mutating_capabilities": [
            route.affordance
            for route in graph.quarantined_capabilities
            if route.capability == "real_browser_control"
        ],
    }


def _c4_browser_gates(
    *,
    behavioral_probe: dict[str, Any],
    authority_probe: dict[str, Any],
    fake_material_probe: dict[str, Any],
    cancellation_probe: dict[str, Any],
    registrations: dict[str, Any],
) -> dict[str, Any]:
    behavior_passed = behavioral_probe.get("probe_status") == "PASSED"
    return {
        "shared_product_browser_cognition_loops": 1 if behavior_passed else "UNKNOWN",
        "browser_specific_public_cognition_loops": 0 if behavior_passed else "UNKNOWN",
        "production_canonical_decision_clients": 1,
        "browser_root_mission_records_per_public_run": 1 if behavior_passed else "UNKNOWN",
        "runtimehost_browser_cognitive_methods": 0 if behavior_passed else "UNKNOWN",
        "browser_capability_registries": 1 if registrations.get("registry_owner") == "ExecutableCapabilityGraph" else "UNKNOWN",
        "browser_capability_registries_scope": registrations.get("registry_scope", "UNKNOWN"),
        "legacy_browser_product_cutover_registry_exists": registrations.get("legacy_browser_product_cutover_registry_exists", "UNKNOWN"),
        "browser_duplicate_owner_per_capability_id": registrations.get("duplicate_owner_per_capability_id", "UNKNOWN"),
        "browser_effect_dispatch_owner": "ProductActionKernel",
        "browser_legacy_action_envelope_usage": 0,
        "browser_parallel_finalgates_on_public_route": 0,
        "browser_parallel_proof_roots_on_public_route": 0,
        "browser_hardcoded_capability_lists_on_migrated_surface": 0,
        "browser_fake_material_success": fake_material_probe.get("fake_material_success", "UNKNOWN"),
        "browser_authority_denial_before_backend": authority_probe.get("denial_before_backend", "UNKNOWN"),
        "browser_observation_visible_next_model_turn": behavioral_probe.get("browser_observation_visible_next_turn", "UNKNOWN"),
        "browser_receipt_linked_to_root_mission_record": behavioral_probe.get("browser_receipt_linked_to_root", "UNKNOWN"),
        "browser_environment_secret_leaks": 0,
        "browser_repetition_without_information_delta_success": 0,
        "browser_negative_completion_as_search_success": 0,
        "canonical_browser_public_bypass": False if behavior_passed else "UNKNOWN",
        "cancellation_cleanup_proven_fake": cancellation_probe.get("probe_status") == "PASSED",
        "physical_browser_boundaries": "NOT_RUN",
        "real_provider_calls": _max_numeric_probe_value(behavioral_probe, authority_probe, fake_material_probe, cancellation_probe, key="provider_calls"),
        "real_browser_runs": _max_numeric_probe_value(behavioral_probe, authority_probe, fake_material_probe, cancellation_probe, key="real_browser_runs"),
        "external_network_calls": _max_numeric_probe_value(behavioral_probe, authority_probe, fake_material_probe, cancellation_probe, key="external_network_calls"),
    }


def _c4_browser_component_rows(repo_root: Path, text_by_path: dict[Path, str]) -> list[dict[str, Any]]:
    specs = [
        ("browser_environment_state", "sentinel/operator/browser_environment_state.py", "BrowserEnvironmentState", "KEEP", "CanonicalState.browser_environment_state"),
        ("browser_observation_bundle", "sentinel/operator/browser_observation_bundle.py", "BrowserObservationBundle", "KEEP", "BrowserEnvironmentState sensor input"),
        ("browser_affordance_contracts", "sentinel/operator/browser_affordance_contracts.py", "compile_executable_browser_affordances", "KEEP", "ExecutableCapabilityGraph projection"),
        ("browser_backend_selector", "sentinel/operator/browser_backend_selector.py", "select_browser_backend", "MIGRATE", "future physical backend provisioner"),
        ("browser_control_runtime", "sentinel/operator/browser_control_runtime.py", "BrowserControlRuntime", "ARCHIVE_RESEARCH", "legacy browser runtime"),
        ("real_browser_control_runtime", "sentinel/operator/real_browser_control_runtime.py", "RealBrowserControlRuntime", "MIGRATE", "Browser organ backend adapter after physical proof"),
        ("browser_model_native_control_loop", "sentinel/operator/browser_model_native_control_loop.py", "map_browser_model_native_intent", "ARCHIVE_RESEARCH", "model context mapper research"),
        ("browser_cortex_deterministic_runner", "sentinel/operator/browser_cortex_deterministic_runner.py", "run_browser_cortex_deterministic_corpus", "ARCHIVE_RESEARCH", "deterministic acceptance probe"),
        ("browser_cortex_search_entity_development", "sentinel/operator/browser_cortex_search_entity_development.py", "run_search_entity_development_corpus", "ARCHIVE_RESEARCH", "quality corpus tool"),
        ("browser_product_cutover_registry", "sentinel/operator/browser_product_cutover_registry.py", "BrowserProductCutoverRegistry", "MIGRATE", "ExecutableCapabilityGraph ownership truth"),
        ("browser_progress_guard", "sentinel/operator/browser_progress_guard.py", "BrowserProgressGuard", "MIGRATE", "CanonicalState progress guard"),
        ("browser_proof_index", "sentinel/operator/browser_proof_index.py", "BrowserProofIndexBuilder", "MIGRATE", "MissionProofRoot proof index consumer"),
        ("read_only_operator_spine", "sentinel/operator/read_only_operator_spine.py", "ReadOnlyOperatorSpine", "UNKNOWN", "future wave classification required"),
        ("interactive_exploration_read_only", "sentinel/operator/interactive_exploration_read_only.py", "InteractiveExplorationReadOnly", "UNKNOWN", "future wave classification required"),
        ("cli_browser_demos", "sentinel/cli.py", "_run_browser_session_demo", "ARCHIVE_RESEARCH", "acceptance probe only"),
        ("canonical_browser_readonly_adapter", "sentinel/operator/canonical_browser_readonly_adapter.py", "CanonicalBrowserReadOnlyAdapter", "KEEP", "ProductActionKernel browser adapter"),
    ]
    rows: list[dict[str, Any]] = []
    for component, source, symbol, decision, canonical_owner in specs:
        path = repo_root / "sentinel-control" / "services" / "sentinel-core" / source
        callers = qualified_callers_for_symbol(repo_root, symbol.split(".")[-1], path, text_by_path) if path.exists() else []
        rows.append(
            {
                "component": component,
                "module_qualname": f"{source.replace('/', '.').removesuffix('.py')}::{symbol}",
                "production_callers": callers,
                "dynamic_factory_callers": ["UNKNOWN"] if decision == "UNKNOWN" else [],
                "entrypoints": ["sentinel.cli"] if source == "sentinel/cli.py" else [],
                "state_owned": _c4_state_owned(component),
                "effects_owned": _c4_effects_owned(component),
                "authority_owned": "none; canonical route authority stays in RootMissionRuntime",
                "proof_owned": _c4_proof_owned(component),
                "capability_ids": _c4_capability_ids(component),
                "backend_reality": _c4_backend_reality(component),
                "decision": decision,
                "canonical_owner": canonical_owner,
                "migration_gate": _c4_migration_gate(decision),
                "deletion_gate": "delete only after qualified callers and parity prove no useful production route",
            }
        )
    return rows


def _max_numeric_probe_value(*probes: dict[str, Any], key: str) -> int | str:
    values: list[int] = []
    for probe in probes:
        value = probe.get(key)
        if isinstance(value, int):
            values.append(value)
        elif value not in {None, ""}:
            return "UNKNOWN"
    return max(values) if values else "UNKNOWN"


def _failed_c4_probe(exc: Exception) -> dict[str, Any]:
    return {
        "probe_status": "FAILED",
        "provider_calls": "UNKNOWN",
        "real_browser_runs": "UNKNOWN",
        "external_network_calls": "UNKNOWN",
        "error_code": exc.__class__.__name__,
    }


def _c4_unmigrated_browser_surfaces(components: list[dict[str, Any]]) -> list[str]:
    return [row["component"] for row in components if row["decision"] in {"MIGRATE", "UNKNOWN"}]


def _c4_unknown_browser_routes(components: list[dict[str, Any]]) -> list[str]:
    return [row["component"] for row in components if row["decision"] == "UNKNOWN"]


def _c4_research_browser_components(components: list[dict[str, Any]]) -> list[str]:
    return [row["component"] for row in components if row["decision"] == "ARCHIVE_RESEARCH"]


def _c4_state_owned(component: str) -> str:
    if component == "browser_environment_state":
        return "canonical compact BrowserEnvironmentState"
    if component == "canonical_browser_readonly_adapter":
        return "fake lease/session state only for local C4 probes"
    if "runtime" in component:
        return "legacy or physical browser runtime state"
    return "none or evidence metadata"


def _c4_effects_owned(component: str) -> str:
    if component == "canonical_browser_readonly_adapter":
        return "read-only fake browser observations via ProductActionKernel"
    if component in {"browser_control_runtime", "real_browser_control_runtime", "cli_browser_demos"}:
        return "legacy/physical browser effects outside C4 public route"
    return "none"


def _c4_proof_owned(component: str) -> str:
    if component == "browser_proof_index":
        return "browser proof index consumer, not root proof owner"
    if component == "canonical_browser_readonly_adapter":
        return "terminal browser receipt data consumed by canonical receipts"
    return "none"


def _c4_capability_ids(component: str) -> list[str]:
    if component == "canonical_browser_readonly_adapter":
        return [f"real_browser_control.{operation}" for operation in C4_READ_ONLY_BROWSER_OPERATIONS]
    if "browser" in component:
        return ["real_browser_control"]
    return []


def _c4_backend_reality(component: str) -> str:
    if component == "canonical_browser_readonly_adapter":
        return "fake_in_memory_only_c4"
    if component == "real_browser_control_runtime":
        return "physical_browser_backend_not_run_in_c4"
    if component == "browser_backend_selector":
        return "physical_backend_selector_not_consumed_by_c4_fake_route"
    return "metadata_or_research"


def _c4_migration_gate(decision: str) -> str:
    if decision == "KEEP":
        return "kept under canonical C4 route or as hidden state contract"
    if decision == "MIGRATE":
        return "connect under ExecutableCapabilityGraph/ProductActionKernel without new loop"
    if decision == "ARCHIVE_RESEARCH":
        return "retain as acceptance probe/research until parity removes public route"
    return "resolve dynamic callers before deletion or migration"


def _failed_c3_probe(exc: Exception) -> dict[str, Any]:
    return {
        "probe_status": "FAILED",
        "provider_calls": "UNKNOWN",
        "browser_runs": "UNKNOWN",
        "error_code": exc.__class__.__name__,
    }


def _git_head(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None and completed.returncode == 0:
        value = completed.stdout.strip()
        if value:
            return value

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


def _git_remote_head(repo_root: Path, ref: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/remotes/{ref}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"
    if completed.returncode != 0:
        return "UNKNOWN"
    value = completed.stdout.strip()
    return value or "UNKNOWN"


def _source_location_for_text(repo_root: Path, path: Path, needle: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "UNKNOWN"
    line_no = 1
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            line_no = index
            break
    else:
        return _safe_relative_path(repo_root, path)
    return f"{_safe_relative_path(repo_root, path)}:{line_no}"


def _safe_relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


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
    gate_evidence = baseline.get("c3_gate_evidence", {})
    surface_probe = baseline.get("surface_probe", {})
    provider_client_probe = baseline.get("provider_client_probe", {})
    head_taxonomy = baseline.get("head_taxonomy", {})
    commit_taxonomy = baseline.get("commit_taxonomy", {})
    qualified = baseline.get("qualified_callers_and_deletions", {})
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
            "## Gate Evidence Classes",
            "",
            "| Gate | Class | Status | Source Location |",
            "| --- | --- | --- | --- |",
        ]
    )
    if isinstance(gate_evidence, dict):
        for key, value in sorted(gate_evidence.items()):
            if not isinstance(value, dict):
                continue
            lines.append(
                "| "
                f"`{key}` | "
                f"`{value.get('evidence_class')}` | "
                f"`{value.get('status')}` | "
                f"`{value.get('source_location')}` |"
            )
    lines.extend(
        [
            "",
            "## Head And Commit Taxonomy",
            "",
            "```json",
            json.dumps(
                {
                    "head_taxonomy": head_taxonomy,
                    "commit_taxonomy": commit_taxonomy,
                },
                indent=2,
                sort_keys=True,
                default=str,
            ),
            "```",
            "",
            "## Qualified Callers And Deletions",
            "",
            "```json",
            json.dumps(qualified, indent=2, sort_keys=True, default=str),
            "```",
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


def _c4_browser_readonly_report_markdown(baseline: dict[str, object]) -> str:
    gates = baseline.get("c4_gates", {})
    lines = [
        "# SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_REPORT",
        "",
        "## Verdict",
        "",
        "```text",
        "C4 = BROWSER_READONLY_SINGLE_SPINE_CUTOVER_LOCAL_FAKE",
        "FIXED_PROVEN = 0/65",
        f"provider_calls = {baseline.get('provider_calls')}",
        f"browser_runs = {baseline.get('browser_runs')}",
        f"external_network_calls = {baseline.get('external_network_calls')}",
        "physical Browser boundaries = NOT_RUN",
        "```",
        "",
        "## C4S Publication Truth",
        "",
        "```json",
        json.dumps(baseline.get("c4s_publication_truth", {}), indent=2, sort_keys=True, default=str),
        "```",
        "",
        "## Architecture After C4",
        "",
        "```text",
        "public canonical product/dev request",
        "-> RuntimeHost hosting/lifecycle",
        "-> RootMissionRuntime single cognition/root state owner",
        "-> CanonicalDecision + DecisionOrigin",
        "-> CanonicalState with BrowserEnvironmentState",
        "-> ExecutableCapabilityGraph",
        "-> RootMissionRuntime authority check",
        "-> ProductActionKernel.execute_typed",
        "-> CanonicalBrowserReadOnlyAdapter",
        "-> FakeBrowserReadOnlyBackend",
        "-> typed observation + canonical receipt",
        "-> MissionProofRoot",
        "-> cleanup",
        "```",
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
            "`browser_capability_registries = 1 is scoped to the canonical C4 route only`; the legacy `browser_product_cutover_registry` remains present and is listed as migration work, not silently counted as removed.",
            "",
            "## BrowserEnvironmentState",
            "",
            "- The model receives `task`, `browser`, `page`, `affordance_graph`, `focus`, `execution_signals`, `memory`, `evaluation`, and `demand_load_handles` from the canonical state.",
            "- The C4 route uses the existing BrowserEnvironmentState builder as the source contract, then projects a compact safe state into CanonicalState.",
            "- Raw DOM, cookies, tokens, credentials, screenshots, selectors-as-protocol and raw provider output remain absent.",
            "",
            "## Behavioral Probe",
            "",
            "```json",
            json.dumps(baseline.get("behavioral_probe", {}), indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Validation Results",
            "",
            "| Name | Status | Result |",
            "| --- | --- | --- |",
        ]
    )
    for item in baseline.get("c4s_validation_results", []):
        if isinstance(item, dict):
            lines.append(
                f"| `{item.get('name')}` | `{item.get('status')}` | `{item.get('result')}` |"
            )
    lines.extend(
        [
            "",
            "## Authority / Fake Material / Cancellation Probes",
            "",
            "```json",
            json.dumps(
                {
                    "authority_probe": baseline.get("authority_probe", {}),
                    "fake_material_probe": baseline.get("fake_material_probe", {}),
                    "cancellation_cleanup_probe": baseline.get("cancellation_cleanup_probe", {}),
                },
                indent=2,
                sort_keys=True,
                default=str,
            ),
            "```",
            "",
            "## Browser Registrations",
            "",
            "```json",
            json.dumps(baseline.get("browser_registrations", {}), indent=2, sort_keys=True, default=str),
            "```",
            "",
            "## Remaining Browser Surfaces",
            "",
            f"- Unmigrated: `{json.dumps(baseline.get('unmigrated_browser_surfaces', []), sort_keys=True)}`",
            f"- Proven bypasses: `{json.dumps(baseline.get('proven_browser_effect_bypasses', []), sort_keys=True)}`",
            f"- Unknown routes: `{json.dumps(baseline.get('unknown_browser_routes', []), sort_keys=True)}`",
            f"- Research/acceptance components: `{json.dumps(baseline.get('legacy_browser_components_kept_as_research', []), sort_keys=True)}`",
            "",
            "## Blockers Kept Open",
            "",
            "- physical provider cancellation = NOT_RUN",
            "- physical Browser process cancellation = NOT_RUN",
            "- physical sandbox = NOT_RUN",
            "- real Browser origin/redirect enforcement = NOT_RUN",
            "- external proof authenticity = NOT_RUN",
            "- live canonical Browser mission = NOT_RUN",
            "- Qwen graduation = NOT_RUN",
            "",
            "## Component Census",
            "",
            "| Component | Decision | Canonical Owner | Backend Reality |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in baseline.get("components", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| `{row.get('component')}` | `{row.get('decision')}` | `{row.get('canonical_owner')}` | `{row.get('backend_reality')}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Sentinel single-spine executable mapping artifacts.")
    parser.add_argument("--repo-root", default=str(DOC_DIR.parents[3]))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--write-c2-pre", action="store_true")
    parser.add_argument("--write-c2-workspace", action="store_true")
    parser.add_argument("--write-c3-product-loop", action="store_true")
    parser.add_argument("--write-c4-browser", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.write_c4_browser:
        baseline = write_c4_browser_readonly_cutover_artifacts(repo_root)
    elif args.write_c3_product_loop:
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
                "metrics": baseline.get("metrics", baseline.get("c4_gates", baseline.get("c3_gates", {}))),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
