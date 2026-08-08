# SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_REPORT

## Verdict

```text
WAVE_C2 = WORKSPACE_SINGLE_SPINE_COMPRESSED_LOCAL
VALID_SUCCESS_FOR_C2_LOCAL_WORKSPACE_COMPRESSION = YES
FIXED_PROVEN = 0/65
provider_calls = 0
browser_runs = 0
```

This is not a global Sentinel completion claim. It proves only the local workspace route compression target for C2.

## Baselines

- C1 historical: `SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_BASELINE.json`
- C1R/C2-pre corrected: `SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_BASELINE.json`
- C2 current: `SENTINEL_SINGLE_SPINE_C2_WORKSPACE_COMPRESSION_BASELINE.json`

## C2 Minimum Delta

- canonical_product_run_bypass: False
- root_direct_workspace_effect_executor: absent
- hardcoded_cli_capability_list: absent
- public_canonical_legacy_action_envelope_usage: absent
- duplicate_owner_per_workspace_capability_id: 0
- fake_material_success_on_workspace_public_route: 0

## Gate Truth

- browser_runs: 0
- canonical_product_run_bypass: False
- duplicate_owner_per_workspace_capability_id: 0
- fake_material_success_on_workspace_public_route: 0
- hardcoded_cli_capability_list_absent: True
- provider_calls: 0
- public_canonical_legacy_action_envelope_usage_absent: True
- root_direct_workspace_effect_executor_absent: True
- root_product_kernel_dispatch_present: True

## Gate Evidence Classes

- static_probe: source/AST checks such as deleted methods and exact dispatch method body.
- behavioral_probe: local scripted product route proving root MissionRecord, graph resolution, ProductActionKernel dispatch, receipt linkage and next-turn observation.
- negative_behavioral_probe: simulated backend attempting material proof is rejected before a canonical receipt is minted.
- run_attestation: provider/browser counts are recorded from the local scripted probe; UNKNOWN/NOT_RUN is used when not executed.

## C2S Gate Evidence Summary

- canonical_product_run_bypass: source=behavioral_probe status=PASSED value=False
- fake_material_success_on_workspace_public_route: source=negative_behavioral_probe status=PASSED value=0
- public_canonical_legacy_action_envelope_usage_absent: source=public command path only status=STATIC value=True
- root_product_kernel_dispatch_present: source=RootMissionRuntime._execute_product_kernel_action AST/source slice status=STATIC value=True

## Validation Commands Executed For C2/C2S

- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c1_executable_mapping.py -q` -> 11 passed.
- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_c2_product_route_rejects_simulated_material_backend_proof -q` -> passed.
- `py -3.13 sentinel-control/docs/reviews/deep_power_audit/sentinel_single_spine_c1_probe.py --repo-root . --write-c2-workspace` -> artifacts regenerated from code and local probes.
- `py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py sentinel-control/services/sentinel-core/tests/operator/test_interactive_exploration.py --collect-only -q` -> 59 + 59 tests collected.

## Nominative 59-Test Files

- `tests/operator/test_real_monster_product_model_native_decision_client.py`: 59 collected.
- `tests/operator/test_interactive_exploration.py`: 59 collected.

## C2 Symbols Removed Or Superseded

- `RootMissionRuntime._execute`: absent after C2.
- `RootMissionRuntime._workspace_list`: absent after C2.
- `RootMissionRuntime._workspace_read`: absent after C2.
- `RootMissionRuntime._workspace_search`: absent after C2.
- CLI helpers `_create_public_product_root_record`, `_terminalize_public_product_root_record`, `_scripted_product_native_request_factory`, `_product_native_real_request_factory`, `_product_native_safe_context_shape`: removed in C2.

## C2 Commit Diffstats

- `4899046f test: make ownership probe symbol-qualified`: 6 files changed, 2247 insertions, 3 deletions.
- `b4f4baac refactor: route root workspace effects through product kernel`: 3 files changed, 336 insertions, 455 deletions.
- `fa5f51bf fix: preserve workspace progress recommendations`: 4 files changed, 73 insertions, 8 deletions.
- `7480f311 docs: publish verified C2 workspace compression delta`: 7 files changed, 2083 insertions, 50 deletions.


## Current Metrics

- authority_allowed_actions_fields: 81 -> sentinel/agent/action_engine.py, sentinel/agent/agent_society.py, sentinel/agent/browser/self_hosted_benchmark.py, sentinel/agent/browser/v3_measured_supremacy.py, sentinel/agent/capability_selector.py, sentinel/agent/context_builder.py, sentinel/agent/epistemic_action.py, sentinel/agent/invariants.py, sentinel/agent/llm/context_pack.py, sentinel/agent/llm/tool_intent_compiler.py, sentinel/agent/mission_entropy.py, sentinel/agent/models.py, sentinel/agent/organs/browser_download_upload_quarantine_l6.py, sentinel/agent/organs/browser_form_submit_special_authority_l6.py, sentinel/agent/organs/browser_js_sandbox_special_authority_l6.py, sentinel/agent/organs/browser_login_credential_session_broker_l6.py, sentinel/agent/organs/browser_operator_agent_l4_l5_live.py, sentinel/agent/organs/browser_session_manager_l5_live.py, sentinel/agent/organs/browser_trajectory_planner_l5.py, sentinel/agent/resourcefulness.py, sentinel/agent/runtime.py, sentinel/agent/skill_procedure.py, sentinel/agent/supervisor.py, sentinel/agent/tool_selector.py, sentinel/agent/worker_coordinator.py, sentinel/agent/workspace.py, sentinel/capabilities/fixtures/static_catalog.py, sentinel/capabilities/models.py, sentinel/capabilities/policy.py, sentinel/cli.py, sentinel/mission/escalation.py, sentinel/mission/gate_sequence.py, sentinel/mission/models.py, sentinel/mission/scope_checker.py, sentinel/operator/account_authority.py, sentinel/operator/authority_issuer.py, sentinel/operator/browser_action_candidates.py, sentinel/operator/browser_control_runtime.py, sentinel/operator/browser_decision_frame.py, sentinel/operator/browser_search_parameter_boundary.py, sentinel/operator/canonical_core.py, sentinel/operator/channel_adapter.py, sentinel/operator/cockpit.py, sentinel/operator/code_execution_sandbox_runtime.py, sentinel/operator/credential_vault.py, sentinel/operator/decision_context.py, sentinel/operator/desktop_sidecar.py, sentinel/operator/deterministic.py, sentinel/operator/financial_authority.py, sentinel/operator/live_desktop_backend.py, sentinel/operator/llm_frame.py, sentinel/operator/model_led_product_action_kernel_task_loop.py, sentinel/operator/model_led_task_loop.py, sentinel/operator/models.py, sentinel/operator/power_bridge.py, sentinel/operator/read_only_model_clients.py, sentinel/operator/read_only_operator_spine.py, sentinel/operator/real_browser_control_runtime.py, sentinel/operator/real_model_certification.py, sentinel/operator/replan_guard.py, sentinel/operator/runtime_host.py, sentinel/operator/skill_fabric.py, sentinel/operator/structured_output.py, sentinel/operator/unified_execution_dispatcher.py, sentinel/operator/voice_runtime.py, sentinel/operator/worker_fleet.py, sentinel/operator/worker_models.py, sentinel/operator/worker_orchestration_runtime.py, sentinel/operator/workflow_models.py, sentinel/operator/workspace_patch_runtime.py, sentinel/operator/workspace_readonly_runtime.py, sentinel/organs/authority.py, sentinel/organs/browser/contract.py, sentinel/organs/browser/navigation_l6.py, sentinel/organs/browser/power_governor.py, sentinel/organs/channels/contract.py, sentinel/organs/desktop/contract.py, sentinel/organs/external_api/contract.py, sentinel/perf/bench/golden_runners.py, sentinel/perf/caches/context_cache_key.py, sentinel/power_lab.py
- canonical_product_run_bypass: 0 -> (none)
- capability_registry: 2 -> executable_capability_graph, runtime_connection_registry
- duplicate_capability_backend: 0 -> (none)
- model_decision_client: 0 -> (none)
- model_decision_loop: 4 -> root_mission_runtime, runtime_host_product_task_loop_method, model_led_product_action_kernel_task_loop, legacy_model_led_task_loop
- other_hardcoded_capability_surfaces: 0 -> (none)
- proven_public_effect_bypasses: 0 -> (none)
- public_canonical_route_hardcoded_capability_list: 0 -> (none)
- unclassified_effect_paths: 15 -> sentinel/agent/model_execution/coordinator.py, sentinel/agent/organs/channel_draft_send_organ_v1.py, sentinel/agent/organs/external_api_read_write_organ_v1.py, sentinel/agent/organs/local_artifact_executor.py, sentinel/agent/organs/sandbox_shell_code_organ_v1.py, sentinel/memory/store.py, sentinel/operator/connection_live_channel_action_models.py, sentinel/operator/desktop_sidecar_models.py, sentinel/operator/model_client.py, sentinel/organs/capability_frontier.py, sentinel/organs/real_world_gauntlet.py, sentinel/organs/reality_activation.py, sentinel/perf/hot_cold/cold_receipt_store.py, sentinel/perf/hot_cold/receipt_index.py, sentinel/shared/db.py
- unknown_public_routes: 0 -> (none)
- unmigrated_public_surfaces: 4 -> public_cli_canonical_dev_run, public_cli_cockpit_chat, public_cli_power_lab_run, public_cli_browser_demos
- workspace_duplicate_owner_per_capability_id: 0 -> (none)

## Workspace Architecture After C2

```text
public canonical-product-run
-> RuntimeHost hosting/lifecycle
-> RootMissionRuntime root loop and MissionRecord
-> CanonicalDecision + DecisionOrigin
-> ExecutableCapabilityGraph
-> authority check
-> ProductActionKernel
-> WorkspaceReadOnlyRuntime backend
-> typed observation / CanonicalEffectReceipt
-> CanonicalState next turn
-> model-selected finish
-> MissionProofRoot / cleanup
```

## Still Open

- `P0-01 = IMPLEMENTING` because no live canonical replacement proof is closed yet.
- `C-P0-01 = IMPLEMENTING` because non-workspace spines remain measured for later waves.
- `C-P0-03 = IMPLEMENTING` because workspace is the first compressed capability family only.
- `C-P0-06 = IMPLEMENTING` because the full organ graph is not compressed in C2.
- `P1-25 = IMPLEMENTING` because legacy recommendation surfaces still exist outside the new public route.

## Do Not Touch Yet

- Browser demos and Browser Organ routes.
- Channel transport and external send.
- PowerLab.
- Qwen/provider live missions.
- Existing untracked runtime artifact directories.
