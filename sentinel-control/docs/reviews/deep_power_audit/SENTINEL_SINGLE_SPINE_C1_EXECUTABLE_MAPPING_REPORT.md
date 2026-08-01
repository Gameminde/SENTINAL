# SENTINEL_SINGLE_SPINE_C1_EXECUTABLE_MAPPING_REPORT

## Verdict

```text
WAVE_C1 = EXECUTABLE_MAPPING_BASELINE_PUBLISHED
provider_calls = 0
browser_runs = 0
FIXED_PROVEN = 0/65
deletions = 0
```

C1 publishes the real baseline. It does not force counts to one or zero.

## Baseline Metrics

- authority_enforcement_points: 3 -> mission_lifecycle_service, product_kernel_dispatch_adapter, assert_data_not_authority
- canonical_state_owners: 2 -> root_mission_runtime, root_runtime_workspace_effect_executor
- capability_registries: 3 -> executable_capability_graph, workspace_read_capability_graph_builder, runtime_connection_registry
- duplicate_workspace_backends: 2 -> workspace_readonly_runtime, workspace_patch_runtime
- effect_dispatch_owners: 3 -> product_action_kernel, unified_execution_dispatcher, root_runtime_workspace_effect_executor
- executable_cognitive_spines: 2 -> root_mission_runtime, runtime_host_product_task_loop
- fake_material_success_routes: 2 -> product_local_cloak_fixture, local_channel_transport
- hardcoded_prompt_capability_lists: 1 -> cli_root_allowed_actions_list
- model_decision_loops: 4 -> model_led_product_action_kernel_task_loop, legacy_model_led_task_loop, product_model_native_decision_client, real_provider_canonical_decision_client
- public_entrypoint_bypasses: 5 -> public_cli_canonical_product_run, public_cli_canonical_dev_run, public_cli_cockpit_chat, public_cli_power_lab_run, public_cli_browser_demos
- receipt_proof_owners: 3 -> mission_kernel_store, mission_proof_root, product_task_loop_finalgate
- root_mission_owners: 6 -> public_cli_canonical_product_run, public_cli_canonical_dev_run, root_mission_runtime, mission_lifecycle_service, mission_kernel_store, cli_root_allowed_actions_list
- unclassified_effect_paths: 15 -> capability_frontier.py, channel_draft_send_organ_v1.py, cold_receipt_store.py, connection_live_channel_action_models.py, coordinator.py, db.py, desktop_sidecar_models.py, external_api_read_write_organ_v1.py, local_artifact_executor.py, model_client.py, real_world_gauntlet.py, reality_activation.py, receipt_index.py, sandbox_shell_code_organ_v1.py, store.py

## First C2 Candidates

These are not deleted in C1. They are candidates only after caller and parity proof:

- public_cli_browser_demos: archive research/demo surfaces after browser organ route parity.
- legacy_model_led_task_loop: delete after caller count is zero and RootMissionRuntime owns cognition.
- root_runtime_workspace_effect_executor: delete after ProductActionKernel owns canonical workspace effects.
- cli_root_allowed_actions_list: delete after allowed actions are generated from ExecutableCapabilityGraph.
- local_channel_transport: remove fake completion from product success path after real/sim transport split.
