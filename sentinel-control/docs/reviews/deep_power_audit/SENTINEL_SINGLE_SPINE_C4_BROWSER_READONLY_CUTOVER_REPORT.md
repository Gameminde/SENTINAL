# SENTINEL_SINGLE_SPINE_C4_BROWSER_READONLY_CUTOVER_REPORT

## Verdict

```text
C4 = BROWSER_READONLY_SINGLE_SPINE_CUTOVER_LOCAL_FAKE
FIXED_PROVEN = 0/65
provider_calls = 0
browser_runs = 0
external_network_calls = 0
physical Browser boundaries = NOT_RUN
```

## C4S Publication Truth

```json
{
  "artifact_head_before_c4s": "d1408193883f8307753cefbb0622fa8695170ab9",
  "c4s_final_commit": "SELF_REFERENCE_UNAVAILABLE_UNTIL_COMMIT",
  "c4s_generation_head": "dfa4479af31349f10932691da38ef771e8a74519",
  "fixed_proven_count": 0,
  "latest_pushed_head_before_c4s": "dfa4479af31349f10932691da38ef771e8a74519"
}
```

## Architecture After C4

```text
public canonical product/dev request
-> RuntimeHost hosting/lifecycle
-> RootMissionRuntime single cognition/root state owner
-> CanonicalDecision + DecisionOrigin
-> CanonicalState with BrowserEnvironmentState
-> ExecutableCapabilityGraph
-> RootMissionRuntime authority check
-> ProductActionKernel.execute_typed
-> CanonicalBrowserReadOnlyAdapter
-> FakeBrowserReadOnlyBackend
-> typed observation + canonical receipt
-> MissionProofRoot
-> cleanup
```

## Gates

| Gate | Value |
| --- | --- |
| `browser_authority_denial_before_backend` | `true` |
| `browser_capability_registries` | `1` |
| `browser_capability_registries_scope` | `"canonical_c4_route_only"` |
| `browser_duplicate_owner_per_capability_id` | `0` |
| `browser_effect_dispatch_owner` | `"ProductActionKernel"` |
| `browser_environment_secret_leaks` | `0` |
| `browser_fake_material_success` | `0` |
| `browser_hardcoded_capability_lists_on_migrated_surface` | `0` |
| `browser_legacy_action_envelope_usage` | `0` |
| `browser_negative_completion_as_search_success` | `0` |
| `browser_observation_visible_next_model_turn` | `true` |
| `browser_parallel_finalgates_on_public_route` | `0` |
| `browser_parallel_proof_roots_on_public_route` | `0` |
| `browser_receipt_linked_to_root_mission_record` | `true` |
| `browser_repetition_without_information_delta_success` | `0` |
| `browser_root_mission_records_per_public_run` | `1` |
| `browser_specific_public_cognition_loops` | `0` |
| `cancellation_cleanup_proven_fake` | `true` |
| `canonical_browser_public_bypass` | `false` |
| `external_network_calls` | `0` |
| `legacy_browser_product_cutover_registry_exists` | `true` |
| `physical_browser_boundaries` | `"NOT_RUN"` |
| `production_canonical_decision_clients` | `1` |
| `real_browser_runs` | `0` |
| `real_provider_calls` | `0` |
| `runtimehost_browser_cognitive_methods` | `0` |
| `shared_product_browser_cognition_loops` | `1` |

`browser_capability_registries = 1 is scoped to the canonical C4 route only`; the legacy `browser_product_cutover_registry` remains present and is listed as migration work, not silently counted as removed.

## BrowserEnvironmentState

- The model receives `task`, `browser`, `page`, `affordance_graph`, `focus`, `execution_signals`, `memory`, `evaluation`, and `demand_load_handles` from the canonical state.
- The C4 route uses the existing BrowserEnvironmentState builder as the source contract, then projects a compact safe state into CanonicalState.
- Raw DOM, cookies, tokens, credentials, screenshots, selectors-as-protocol and raw provider output remain absent.

## Behavioral Probe

```json
{
  "browser_environment_state_sections": [
    "affordance_graph",
    "authority_effect",
    "browser",
    "can_execute",
    "can_grant_authority",
    "data_not_authority",
    "demand_load_handles",
    "evaluation",
    "execution_signals",
    "focus",
    "limits",
    "memory",
    "page",
    "schema_version",
    "source_contract",
    "task"
  ],
  "browser_observation_visible_next_turn": true,
  "browser_receipt_linked_to_root": true,
  "browser_specific_public_cognition_loops": 0,
  "external_network_calls": 0,
  "probe_status": "PASSED",
  "provider_calls": 0,
  "real_browser_runs": 0,
  "receipt_operations": [
    "real_browser.observe",
    "real_browser.extract_evidence"
  ],
  "root_mission_record_count": 1,
  "shared_cognition_loop": "RootMissionRuntime",
  "status": "completed",
  "surface_results": {
    "canonical-dev-run": {
      "browser_readonly_fake_enabled": true,
      "exit_code": 0,
      "legacy_action_envelope_adapter": false,
      "proof_root_linked": true,
      "receipt_count": 2,
      "root_mission_id_count": 1,
      "runtimehost_cognition": false,
      "status": "completed"
    },
    "canonical-product-run": {
      "browser_readonly_fake_enabled": true,
      "exit_code": 0,
      "legacy_action_envelope_adapter": false,
      "proof_root_linked": true,
      "receipt_count": 2,
      "root_mission_id_count": 1,
      "runtimehost_cognition": false,
      "status": "completed"
    }
  }
}
```

## Validation Results

| Name | Status | Result |
| --- | --- | --- |
| `test_sentinel_dev_max_power_canonical_core_v1.py + single_spine probes + c4 cutover` | `PASSED` | `63/63 passed` |
| `RuntimeHost/ProductActionKernel groups` | `PASSED` | `38/38 passed` |
| `skill surface/code-channel/recovery groups` | `PASSED` | `27/27 passed` |
| `real_monster_product_model_native_decision_client.py` | `PASSED` | `59/59 passed` |
| `interactive_exploration.py` | `PASSED` | `59/59 passed` |
| `Browser state/proof/answer evidence group` | `PASSED` | `29/29 passed` |
| `compileall sentinel` | `PASSED` | `exit 0` |
| `git diff --check` | `PASSED` | `exit 0` |
| `JSON/CSV parse` | `PASSED` | `C2/C3/C4 JSON parsed; C2=28 rows, C3=16 rows, C4=16 rows` |
| `secret/path/raw-provider scan` | `PASSED` | `only safe doctrine/report mentions, no raw secrets or local paths` |
| `targeted Ruff correctness` | `UNAVAILABLE` | `No module named ruff` |

## Authority / Fake Material / Cancellation Probes

```json
{
  "authority_probe": {
    "backend_call_count": 0,
    "denial_before_backend": true,
    "external_network_calls": 0,
    "probe_status": "PASSED",
    "provider_calls": 0,
    "real_browser_runs": 0
  },
  "cancellation_cleanup_probe": {
    "external_network_calls": 0,
    "probe_status": "PASSED",
    "provider_calls": 0,
    "real_browser_runs": 0,
    "scenario_count": 5,
    "scenarios": {
      "block": {
        "backend_call_log": [],
        "blocked_reason_detail": "canonical_authority_required:browser_read",
        "cleanup_completed": true,
        "cleanup_count": 1,
        "external_network_calls": 0,
        "final_reason": "EFFECT_DISPATCH_FAILED",
        "lease_released": true,
        "model_turns": 1,
        "provider_calls": 0,
        "real_browser_runs": 0,
        "status": "blocked"
      },
      "cancellation": {
        "backend_call_log": [
          "real_browser.observe"
        ],
        "blocked_reason_detail": "root_mission_cancelled_during_browser_effect",
        "cleanup_completed": true,
        "cleanup_count": 1,
        "external_network_calls": 0,
        "final_reason": "EFFECT_DISPATCH_FAILED",
        "lease_released": true,
        "model_turns": 1,
        "provider_calls": 0,
        "real_browser_runs": 0,
        "status": "blocked"
      },
      "cleanup_failure": {
        "backend_call_log": [
          "real_browser.observe"
        ],
        "blocked_reason_detail": "",
        "cleanup_completed": false,
        "cleanup_count": 1,
        "external_network_calls": 0,
        "final_reason": "model_selected_finish",
        "lease_released": false,
        "model_turns": 2,
        "provider_calls": 0,
        "real_browser_runs": 0,
        "status": "completed"
      },
      "completion": {
        "backend_call_log": [
          "real_browser.observe"
        ],
        "blocked_reason_detail": "",
        "cleanup_completed": true,
        "cleanup_count": 1,
        "external_network_calls": 0,
        "final_reason": "model_selected_finish",
        "lease_released": true,
        "model_turns": 2,
        "provider_calls": 0,
        "real_browser_runs": 0,
        "status": "completed"
      },
      "survivor": {
        "backend_call_log": [
          "real_browser.observe"
        ],
        "blocked_reason_detail": "",
        "cleanup_completed": false,
        "cleanup_count": 1,
        "external_network_calls": 0,
        "final_reason": "model_selected_finish",
        "lease_released": false,
        "model_turns": 2,
        "provider_calls": 0,
        "real_browser_runs": 0,
        "status": "completed"
      }
    }
  },
  "fake_material_probe": {
    "external_network_calls": 0,
    "fake_material_success": 0,
    "probe_status": "PASSED",
    "provider_calls": 0,
    "real_browser_runs": 0
  }
}
```

## Browser Registrations

```json
{
  "duplicate_owner_per_capability_id": 0,
  "legacy_browser_product_cutover_registry_exists": true,
  "owners_by_capability": {
    "real_browser_control.real_browser.extract_evidence": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "public_evidence_delta_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.inspect_result": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "typed_inspection_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.observe": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "browser_state_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.open": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "bounded_origin_state_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.open_result": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "typed_link_follow_delta_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.recover_session": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "lease_state_transition_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.search": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "typed_search_outcome_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ],
    "real_browser_control.real_browser.verify_extraction": [
      {
        "authority_schema": "browser_read",
        "backend": "fake_in_memory_browser_read_only",
        "callable_owner": "ProductActionKernel:real_browser_control",
        "materiality": "verification_state_observed",
        "readiness": "fake_browser_readonly_session_ready",
        "receipt_contract": "canonical_core_browser_readonly_receipt_v1",
        "registration_source": "ExecutableCapabilityGraph.routes"
      }
    ]
  },
  "probe_status": "PASSED",
  "quarantined_mutating_capabilities": [
    "real_browser_control.real_browser.click",
    "real_browser_control.real_browser.download",
    "real_browser_control.real_browser.execute_script",
    "real_browser_control.real_browser.login",
    "real_browser_control.real_browser.payment",
    "real_browser_control.real_browser.select_option",
    "real_browser_control.real_browser.submit_form",
    "real_browser_control.real_browser.type_text",
    "real_browser_control.real_browser.upload"
  ],
  "registered_operations": [
    "real_browser.extract_evidence",
    "real_browser.inspect_result",
    "real_browser.observe",
    "real_browser.open",
    "real_browser.open_result",
    "real_browser.recover_session",
    "real_browser.search",
    "real_browser.verify_extraction"
  ],
  "registry_owner": "ExecutableCapabilityGraph",
  "registry_scope": "canonical_c4_route_only",
  "route_count": 8
}
```

## Remaining Browser Surfaces

- Unmigrated: `["browser_backend_selector", "real_browser_control_runtime", "browser_product_cutover_registry", "browser_progress_guard", "browser_proof_index", "read_only_operator_spine", "interactive_exploration_read_only"]`
- Proven bypasses: `[]`
- Unknown routes: `["read_only_operator_spine", "interactive_exploration_read_only"]`
- Research/acceptance components: `["browser_control_runtime", "browser_model_native_control_loop", "browser_cortex_deterministic_runner", "browser_cortex_search_entity_development", "cli_browser_demos"]`

## Blockers Kept Open

- physical provider cancellation = NOT_RUN
- physical Browser process cancellation = NOT_RUN
- physical sandbox = NOT_RUN
- real Browser origin/redirect enforcement = NOT_RUN
- external proof authenticity = NOT_RUN
- live canonical Browser mission = NOT_RUN
- Qwen graduation = NOT_RUN

## Component Census

| Component | Decision | Canonical Owner | Backend Reality |
| --- | --- | --- | --- |
| `browser_environment_state` | `KEEP` | `CanonicalState.browser_environment_state` | `metadata_or_research` |
| `browser_observation_bundle` | `KEEP` | `BrowserEnvironmentState sensor input` | `metadata_or_research` |
| `browser_affordance_contracts` | `KEEP` | `ExecutableCapabilityGraph projection` | `metadata_or_research` |
| `browser_backend_selector` | `MIGRATE` | `future physical backend provisioner` | `physical_backend_selector_not_consumed_by_c4_fake_route` |
| `browser_control_runtime` | `ARCHIVE_RESEARCH` | `legacy browser runtime` | `metadata_or_research` |
| `real_browser_control_runtime` | `MIGRATE` | `Browser organ backend adapter after physical proof` | `physical_browser_backend_not_run_in_c4` |
| `browser_model_native_control_loop` | `ARCHIVE_RESEARCH` | `model context mapper research` | `metadata_or_research` |
| `browser_cortex_deterministic_runner` | `ARCHIVE_RESEARCH` | `deterministic acceptance probe` | `metadata_or_research` |
| `browser_cortex_search_entity_development` | `ARCHIVE_RESEARCH` | `quality corpus tool` | `metadata_or_research` |
| `browser_product_cutover_registry` | `MIGRATE` | `ExecutableCapabilityGraph ownership truth` | `metadata_or_research` |
| `browser_progress_guard` | `MIGRATE` | `CanonicalState progress guard` | `metadata_or_research` |
| `browser_proof_index` | `MIGRATE` | `MissionProofRoot proof index consumer` | `metadata_or_research` |
| `read_only_operator_spine` | `UNKNOWN` | `future wave classification required` | `metadata_or_research` |
| `interactive_exploration_read_only` | `UNKNOWN` | `future wave classification required` | `metadata_or_research` |
| `cli_browser_demos` | `ARCHIVE_RESEARCH` | `acceptance probe only` | `metadata_or_research` |
| `canonical_browser_readonly_adapter` | `KEEP` | `ProductActionKernel browser adapter` | `fake_in_memory_only_c4` |
