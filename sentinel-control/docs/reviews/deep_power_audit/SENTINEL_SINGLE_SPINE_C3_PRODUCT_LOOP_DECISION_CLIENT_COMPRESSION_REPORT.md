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

## Gate Evidence Classes

| Gate | Class | Status | Source Location |
| --- | --- | --- | --- |
| `canonical_dev_run_bypass` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:503` |
| `canonical_product_run_bypass` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `direct_rootmissionruntime_workspace_executor` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py:901` |
| `fake_material_success_on_migrated_surfaces` | `NEGATIVE_BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py:456` |
| `hardcoded_capability_list_on_migrated_surfaces` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `legacy_action_envelope_usage_in_product_core` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py:901` |
| `product_action_kernel_effect_dispatch_owner` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/action_kernel.py:237` |
| `product_workspace_cognition_loops` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `production_canonical_decision_clients` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py:83` |
| `proof_root_linked_to_root_mission_record` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `provider_request_builder_owner` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py:83` |
| `remaining_non_migrated_model_led_product_loop` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py:116` |
| `remaining_non_migrated_runtimehost_loop` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py:792` |
| `root_mission_record_per_public_run` | `BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `runtimehost_cognitive_methods_on_migrated_routes` | `NEGATIVE_BEHAVIORAL_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/cli.py:507` |
| `workspace_duplicate_owner_per_capability_id` | `STATIC_PROBE` | `PASS` | `sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py:456` |

## Head And Commit Taxonomy

```json
{
  "commit_taxonomy": {
    "c2s_commits": [
      "170749e516ca9c1ff27dd8d4c5ca78fea1eabd92"
    ],
    "deletion_commits": [
      "88ee94f1768c962246b54c918b27dd4374a29a5e"
    ],
    "documentation_commits": [
      "b7c24e0a5baecd43fbb317cb0ddfc16743da0a58"
    ],
    "implementation_commits": [
      "88ee94f1768c962246b54c918b27dd4374a29a5e"
    ]
  },
  "head_taxonomy": {
    "artifact_generation_head": "ref: refs/heads/sentinel-dev-max-power-canonical-core-v1",
    "current_remote_head": "b7c24e0a5baecd43fbb317cb0ddfc16743da0a58",
    "current_worktree_head": "ref: refs/heads/sentinel-dev-max-power-canonical-core-v1",
    "documentation_head": "b7c24e0a5baecd43fbb317cb0ddfc16743da0a58",
    "implementation_tested_head": "88ee94f1768c962246b54c918b27dd4374a29a5e",
    "proof_attestation_head": "88ee94f1768c962246b54c918b27dd4374a29a5e"
  }
}
```

## Qualified Callers And Deletions

```json
{
  "deleted_symbols": [
    {
      "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
      "present_in_current_source": false,
      "replacement": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions",
      "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
      "status": "DELETED",
      "symbol": "sentinel.cli::_RealProviderCanonicalDecisionClient"
    },
    {
      "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
      "present_in_current_source": false,
      "replacement": "sentinel.operator.product_model_native_decision_client::_canonical_real_model_request",
      "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
      "status": "DELETED_FROM_CLI",
      "symbol": "sentinel.cli::_canonical_real_model_request"
    },
    {
      "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
      "present_in_current_source": false,
      "replacement": "sentinel.operator.product_model_native_decision_client::_canonical_product_provider_prompt",
      "source": "sentinel-control/services/sentinel-core/sentinel/cli.py",
      "status": "DELETED_FROM_CLI",
      "symbol": "sentinel.cli::_canonical_product_provider_prompt"
    },
    {
      "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
      "present_in_current_source": false,
      "replacement": "sentinel.operator.action_kernel::ActionKernel.execute_typed",
      "source": "sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py",
      "status": "DELETED",
      "symbol": "sentinel.operator.canonical_core::RootMissionRuntime._action_envelope_for_decision"
    }
  ],
  "loc_delta": {
    "deletion_commit": "88ee94f1768c962246b54c918b27dd4374a29a5e",
    "source": "git show --stat recorded in C3 validation",
    "status": "RECORDED_NOT_RECOMPUTED_BY_C3S"
  },
  "qualified_calls": [
    {
      "caller": "sentinel.cli::_run_canonical_dev_command",
      "evidence_kind": "function_call",
      "resolution": "QUALIFIED",
      "source": "sentinel-control/services/sentinel-core/sentinel/cli.py:503",
      "target": "sentinel.cli::_run_canonical_product_command"
    },
    {
      "caller": "sentinel.cli::_run_canonical_product_command",
      "evidence_kind": "provider_client_constructor",
      "resolution": "QUALIFIED",
      "source": "sentinel-control/services/sentinel-core/sentinel/cli.py:527",
      "target": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions"
    },
    {
      "caller": "sentinel.operator.canonical_core::RootMissionRuntime._execute_product_kernel_action",
      "evidence_kind": "method_call",
      "resolution": "QUALIFIED",
      "source": "sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py:918",
      "target": "sentinel.operator.action_kernel::ActionKernel.execute_typed"
    },
    {
      "caller": "sentinel.operator.product_model_native_decision_client::ProductModelNativeDecisionClient.for_canonical_decisions",
      "evidence_kind": "decision_protocol_adapter",
      "resolution": "QUALIFIED",
      "source": "sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py:108",
      "target": "sentinel.operator.canonical_core::CanonicalDecision"
    }
  ],
  "unknown_remaining": []
}
```

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
