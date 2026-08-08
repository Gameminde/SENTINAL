# SENTINEL_SINGLE_SPINE_C3_PRODUCT_LOOP_DECISION_CLIENT_COMPRESSION_REPORT

## Verdict

```text
C3 = PRODUCT_LOOP_AND_DECISION_CLIENT_COMPRESSED_LOCAL
FIXED_PROVEN = 0/65
provider_calls = 0
browser_runs = 0
```

## Scope

- Migrated `canonical-dev-run` onto the same hosted canonical product route as `canonical-product-run`.
- Consolidated the production canonical provider protocol under `ProductModelNativeDecisionClient`.
- Removed the CLI-private `_RealProviderCanonicalDecisionClient` and request/prompt/parser duplicate.
- Replaced the RootMissionRuntime product dispatch bridge with typed `ProductActionKernel.execute_typed(...)`.
- Kept Browser, Channel, PowerLab, Qwen/live provider missions, and non-workspace legacy routes out of C3.

## Gates

| Gate | Value |
| --- | --- |
| `canonical_dev_run_bypass` | `false` |
| `canonical_product_run_bypass` | `false` |
| `direct_rootmissionruntime_workspace_executor` | `0` |
| `fake_material_success_on_migrated_surfaces` | `0` |
| `hardcoded_capability_list_on_migrated_surfaces` | `0` |
| `legacy_action_envelope_usage_in_product_core` | `0` |
| `product_action_kernel_effect_dispatch_owner` | `1` |
| `product_workspace_cognition_loops` | `1` |
| `production_canonical_decision_clients` | `1` |
| `proof_root_linked_to_root_mission_record` | `true` |
| `provider_request_builder_owner` | `"ProductModelNativeDecisionClient"` |
| `remaining_non_migrated_model_led_product_loop` | `"KNOWN_NON_C3_ROUTE"` |
| `remaining_non_migrated_runtimehost_loop` | `"KNOWN_NON_C3_ROUTE"` |
| `root_mission_record_per_public_run` | `1` |
| `runtimehost_cognitive_methods_on_migrated_routes` | `0` |
| `workspace_duplicate_owner_per_capability_id` | `0` |

## Behavioral Probe

```json
{
  "browser_runs": 0,
  "legacy_runtimehost_loop_called": false,
  "probe_status": "PASSED",
  "provider_calls": 0,
  "surfaces": {
    "canonical-dev-run": {
      "decision_client": "_JsonlCanonicalDecisionScriptClient",
      "exit_code": 0,
      "legacy_action_envelope_adapter": false,
      "mission_record_created_before_provider": true,
      "product_receipt_count": 1,
      "proof_receipt_count": 1,
      "proof_root_linked": true,
      "root_created_before_first_provider_call": true,
      "root_mission_id_count": 1,
      "runtimehost_cognition": false,
      "status": "completed"
    },
    "canonical-product-run": {
      "decision_client": "_JsonlCanonicalDecisionScriptClient",
      "exit_code": 0,
      "legacy_action_envelope_adapter": false,
      "mission_record_created_before_provider": true,
      "product_receipt_count": 1,
      "proof_receipt_count": 1,
      "proof_root_linked": true,
      "root_created_before_first_provider_call": true,
      "root_mission_id_count": 1,
      "runtimehost_cognition": false,
      "status": "completed"
    }
  }
}
```

## Provider Client Probe

```json
{
  "client_class": "ProductModelNativeDecisionClient",
  "decision_origin": "MODEL_SELECTED",
  "decision_protocol": "MODEL_NATIVE_CANONICAL_JSON_V1",
  "probe_status": "PASSED",
  "provider_calls": 0,
  "request_runtime": "product_model_native_decision",
  "transport_request_count": 1
}
```

## Architecture After C3

```text
public canonical-product-run / canonical-dev-run
-> RuntimeHost hosting/lifecycle
-> RootMissionRuntime single cognition/root state owner
-> ProductModelNativeDecisionClient or JSONL scripted client
-> CanonicalDecision + DecisionOrigin
-> ExecutableCapabilityGraph
-> RootMissionRuntime authority check
-> ProductActionKernel.execute_typed
-> workspace backend
-> CanonicalEffectReceipt
-> CanonicalState next turn
-> model-selected finish
-> MissionProofRoot
-> cleanup
```

## Kept Open

- `P0-01 = IMPLEMENTING` because C3 is local compression, not a new live provider closure.
- `C-P0-01`, `C-P0-03`, `C-P0-06`, `P1-25`, `C-P1-17`, and `P0-07` remain `IMPLEMENTING`.
- Legacy RuntimeHost/ModelLed loops remain for non-migrated Browser/Channel/PowerLab routes and must not be counted as C3 workspace bypasses.

## Validation Recorded

- C3 migrated-surface behavioral probe: `canonical-dev-run` and `canonical-product-run` completed through the same hosted RootMissionRuntime route.
- C3 provider-client probe: fake transport received one `RealModelRequest` and emitted one `CanonicalDecision`.
- Provider calls: `0`.
- Browser runs: `0`.
