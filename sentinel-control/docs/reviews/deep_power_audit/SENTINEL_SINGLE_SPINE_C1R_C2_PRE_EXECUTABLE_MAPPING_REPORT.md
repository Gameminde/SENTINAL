# SENTINEL_SINGLE_SPINE_C1R_C2_PRE_EXECUTABLE_MAPPING_REPORT

## Verdict

```text
WAVE_C1R_C2_PRE = DISCRIMINATING_BASELINE_PUBLISHED
provider_calls = 0
browser_runs = 0
FIXED_PROVEN = 0/65
deletions = 0
```

C1 remains preserved as a historical baseline. C1R/C2-pre corrects the metric semantics before C2 workspace compression.

## False Positives Removed

- Textual mentions of `_execute`, `allowed_actions`, `ActionKernel`, and `MissionKernel` are no longer caller proof.
- Provider clients are not counted as model decision loops by default.
- The workspace read graph builder is a graph factory, not a second capability registry owner.
- Workspace read and write backends are specialized owners, not duplicate owners unless they claim the same capability id.
- Unclassified effect paths are module-qualified instead of basename-only.

## Corrected Metrics

- canonical_product_run_bypass: 0 -> 
- capability_registry: 2 -> executable_capability_graph, runtime_connection_registry
- duplicate_capability_backend: 0 -> 
- hardcoded_cli_capability_list: 1 -> cli_root_allowed_actions_list
- model_decision_client: 2 -> canonical_provider_request_builder, cli_private_real_provider_canonical_decision_client
- model_decision_loop: 4 -> root_mission_runtime, runtime_host_product_task_loop_method, model_led_product_action_kernel_task_loop, legacy_model_led_task_loop
- public_entrypoint_bypass: 4 -> public_cli_canonical_dev_run, public_cli_cockpit_chat, public_cli_power_lab_run, public_cli_browser_demos
- unclassified_effect_paths: 15 -> sentinel/agent/model_execution/coordinator.py, sentinel/agent/organs/channel_draft_send_organ_v1.py, sentinel/agent/organs/external_api_read_write_organ_v1.py, sentinel/agent/organs/local_artifact_executor.py, sentinel/agent/organs/sandbox_shell_code_organ_v1.py, sentinel/memory/store.py, sentinel/operator/connection_live_channel_action_models.py, sentinel/operator/desktop_sidecar_models.py, sentinel/operator/model_client.py, sentinel/organs/capability_frontier.py, sentinel/organs/real_world_gauntlet.py, sentinel/organs/reality_activation.py, sentinel/perf/hot_cold/cold_receipt_store.py, sentinel/perf/hot_cold/receipt_index.py, sentinel/shared/db.py
- workspace_duplicate_owner_per_capability_id: 0 -> 

## C2 Scope Boundary

No component is deleted by C1R/C2-pre. The corrected probe is a deletion precondition only.
Browser, Channel, PowerLab and non-workspace organs remain measured but untouched in C2.
