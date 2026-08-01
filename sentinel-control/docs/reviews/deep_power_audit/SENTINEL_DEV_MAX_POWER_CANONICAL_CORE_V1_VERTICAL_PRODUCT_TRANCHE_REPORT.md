# SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE_REPORT

## Verdict

```text
SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE
= T3_REAL_MODEL_CANONICAL_SLICE_PROVEN_BUT_P0_01_NOT_CLOSED

accepted_t3_attestation_commit = fe28a144445168aa75bc3f9c02e1e4626466e5db
tested_runtime_head = b721ce62343316bcdbe9c792af8a0967c8ae1680
FIXED_PROVEN_COUNT = 0
P0-01 = IMPLEMENTING
```

V13 remains preserved as the first real-model canonical slice proof. It proved a
useful Qwen workspace mission through the new canonical core path, with real
provider authentication, model-native decisions, one material workspace action,
model-selected finish, receipt integrity, proof root, and cleanup.

It does not close `P0-01`. The accepted V13 path used:

```text
_RealProviderCanonicalDecisionClient
-> run_canonical_product_mission
-> RootMissionRuntime
```

The P0-01 acceptance probe still requires the public product route:

```text
public product request
-> ProductModelNativeDecisionClient
-> RuntimeHost.run_product_action_kernel_task_loop
-> ProductActionKernel
-> receipt
```

## Current Correction

This tranche now chooses the adapter/convergence strategy:

```text
RootMissionRuntime remains the canonical root record/proof direction.
Public product execution routes through RuntimeHost.run_product_action_kernel_task_loop.
ProductModelNativeDecisionClient maps model-native skills to legacy ActionEnvelope internally.
ProductActionKernel remains the material effect dispatcher.
```

The local discriminant probe is:

```text
test_public_product_cli_entrypoint_reaches_runtimehost_product_action_kernel_spine
```

It invokes the real public CLI surface in script-backed product-native mode and
fails if execution bypasses into the parallel `run_canonical_product_mission`
effect loop.

## Implemented Product Path

```text
public CLI request
-> root MissionRecord created before provider/model decision
-> ProductModelNativeDecisionClient
-> simple model skill surface: read/search/finish
-> internal DecisionProtocol to legacy ActionEnvelope adapter
-> RuntimeHost.run_product_action_kernel_task_loop
-> MissionExecutionCoordinator
-> RuntimeConnectionRegistry(connection_id=workspace)
-> ProductActionKernelDispatchAdapter
-> ProductActionKernel
-> WorkspaceReadOnlyRuntime backend
-> ProductActionKernelReceipt
-> ProductActionKernel task-loop proof root
-> terminal root MissionRecord
-> cleanup
```

The model sees simple skills. Internal runtime actions such as
`workspace.search` remain machine-readable schema details, not the primary
model language.

## Files Changed

```text
sentinel/cli.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/model_skill_surface.py
sentinel/operator/product_model_native_decision_client.py
sentinel/operator/runtime_connections.py
sentinel/operator/runtime_host.py
sentinel/operator/workspace_readonly_runtime.py
tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_METHODOLOGY_RECONCILIATION_REPORT.md
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE_REPORT.md
```

## Local Probe Evidence

```text
public product route local discriminant = PASS
MissionRecord before provider/model = PASS
decision client marker = ProductModelNativeDecisionClient
runtime entrypoint marker = RuntimeHost.run_product_action_kernel_task_loop
capability dispatch marker = ProductActionKernel
legacy ActionEnvelope adapter = true
parallel RootMissionRuntime effect executor used = false
ProductActionKernel receipt persisted = true
dispatch closeout persisted = true
cleanup completed = true
```

Proof root for this public product path:

```text
integrity_model = product_action_kernel_task_loop_finalgate_v1
receipt_artifacts_verified = true
authentic_external_ledger = false
proof_gaps = external_append_only_signer_missing
```

Therefore `P0-07` remains `IMPLEMENTING`: local receipt integrity exists, but
external/non-recomputable authenticity is not proven.

## Ledger Truth

```text
ledger_current_head = fe28a144445168aa75bc3f9c02e1e4626466e5db
tested_runtime_head = b721ce62343316bcdbe9c792af8a0967c8ae1680
attestation_head = fe28a144445168aa75bc3f9c02e1e4626466e5db
fixed_proven_count = 0
P0 fixed / 15 = 0/15
P1 fixed / 44 = 0/44
P2 fixed / 6 = 0/6
total FIXED_PROVEN / 65 = 0/65
status_counts = CONFIRMED_CURRENT:9, IMPLEMENTING:8, OPEN:48
P0-01 = IMPLEMENTING
C-P0-01 = IMPLEMENTING
C-P0-06 = IMPLEMENTING
P0-07 = IMPLEMENTING
```

V13 remains an accepted proof artifact. It is not deleted or degraded; it is
only narrowed to the proof it actually supplied.

## Gates

```text
T3 real-model canonical slice = PRESERVED
public product path local discriminant = PASS
P0-01 fixed proven = NO
legacy/public ProductActionKernel route real-provider graduation = PENDING
C-P0-01 several spines fully fused = NO
C-P0-06 full organ capability graph = NO
P0-07 external proof authenticity = NO
```

## Next

Before provider cancellation and physical sandbox, the convergence proof must
graduate the public product route with a real provider mission:

```text
provider authenticated
-> ProductModelNativeDecisionClient
-> RuntimeHost.run_product_action_kernel_task_loop
-> model-native workspace operation selected
-> ProductActionKernel receipt persisted
-> observation returned to next model turn
-> model-selected finish
-> terminal MissionRecord
-> proof root
-> cleanup
```

Do not return to Browser Organ in this tranche.
