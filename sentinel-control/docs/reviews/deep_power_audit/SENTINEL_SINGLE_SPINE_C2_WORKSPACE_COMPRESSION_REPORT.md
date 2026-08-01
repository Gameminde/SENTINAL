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

## Current Metrics

- canonical_product_run_bypass: 0 -> 
- capability_registry: 2 -> executable_capability_graph, runtime_connection_registry
- duplicate_capability_backend: 0 -> 
- hardcoded_cli_capability_list: 0 -> 
- model_decision_client: 2 -> canonical_provider_request_builder, cli_private_real_provider_canonical_decision_client
- model_decision_loop: 4 -> root_mission_runtime, runtime_host_product_task_loop_method, model_led_product_action_kernel_task_loop, legacy_model_led_task_loop
- public_entrypoint_bypass: 4 -> public_cli_canonical_dev_run, public_cli_cockpit_chat, public_cli_power_lab_run, public_cli_browser_demos
- unclassified_effect_paths: 15 -> sentinel/agent/model_execution/coordinator.py, sentinel/agent/organs/channel_draft_send_organ_v1.py, sentinel/agent/organs/external_api_read_write_organ_v1.py, sentinel/agent/organs/local_artifact_executor.py, sentinel/agent/organs/sandbox_shell_code_organ_v1.py, sentinel/memory/store.py, sentinel/operator/connection_live_channel_action_models.py, sentinel/operator/desktop_sidecar_models.py, sentinel/operator/model_client.py, sentinel/organs/capability_frontier.py, sentinel/organs/real_world_gauntlet.py, sentinel/organs/reality_activation.py, sentinel/perf/hot_cold/cold_receipt_store.py, sentinel/perf/hot_cold/receipt_index.py, sentinel/shared/db.py
- workspace_duplicate_owner_per_capability_id: 0 -> 

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
