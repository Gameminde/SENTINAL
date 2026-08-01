# SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE0_AND_VERTICAL_SLICE_REPORT

## Verdict

```text
SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE0_LEDGER = CREATED
FIRST_CANONICAL_CORE_VERTICAL_SLICE = VALID_SUCCESS_T1_LOCAL_DETERMINISTIC
WHOLE_SENTINEL_COMPLETION = NOT_CLAIMED
REAL_PROVIDER_PROOF = NOT_RUN
REAL_BROWSER_PROOF = NOT_RUN
```

This tranche starts the whole-Sentinel canonical core. It does not make the
Browser Organ the center of Sentinel, and it does not claim that the full
Cognitive OS is unified yet.

## Baseline

```text
baseline_commit = efdbd558abddbc38cea7e506ff8cb8dfe8ef93fa
working_branch = sentinel-dev-max-power-canonical-core-v1
base_tree = isolated worktree from efdbd558
provider_calls = 0
browser_runs = 0
```

The existing `.armed_sqlite_xray` runtime artifacts were left unmodified and
uncommitted.

## Ledger

Created:

```text
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json
```

Ledger counts:

```text
total_findings = 65
P0 = 15
P1 = 44
P2 = 6
status = OPEN for all entries at ledger creation
```

The ledger is intentionally not a success claim. It is the executable work
queue for the 65 verified findings from the whole-system audits.

## Core Slice

Added:

```text
sentinel/operator/canonical_core.py
```

Implemented first vertical contracts:

```text
RootMissionRuntime
CanonicalState
CanonicalDecisionRequest
CanonicalDecision
ExecutableCapabilityGraph
CanonicalEffectReceipt
MissionProofRoot
```

The local slice proves:

```text
root mission exists before first model decision
model client is mandatory before first cognitive turn
model receives canonical state and visible affordances
workspace.list / workspace.read / workspace.search execute generically
ActionEnvelope can be consumed without creating a parallel model protocol
workspace escape is blocked
model payload self-grant is blocked
cleanup completes before terminal result is returned
```

The initial `MissionProofRoot` is deliberately labeled:

```text
integrity_model = non_authentic_placeholder
authentic_external_ledger = false
proof_gaps = external_append_only_signer_missing
```

That preserves the truth from the audits: proof authenticity is not solved yet.

## Public Dev Entrypoint

Added an explicit development CLI route:

```text
sentinel canonical-dev-run
```

This route runs the canonical core with a local JSONL decision script. It is a
public deterministic dev entrypoint, not a real provider proof.

The route exercises:

```text
CLI
-> scripted model-client boundary
-> RootMissionRuntime
-> CanonicalState
-> workspace read-only capabilities
-> receipts
-> non-authentic proof placeholder
-> cleanup
```

## P0 Truth

No P0 is globally closed by this tranche.

Partially advanced:

```text
C-P0-01 no single root core:
  first root mission skeleton exists, but all organs are not yet migrated.

P0-01 ProductModelNativeDecisionClient not public product route:
  V13 proves a T3 real-model canonical slice, but P0-01 remains IMPLEMENTING
  until the public product surface graduates ProductModelNativeDecisionClient
  -> RuntimeHost.run_product_action_kernel_task_loop -> ProductActionKernel
  -> receipt without a parallel RootMissionRuntime effect loop.

P0-03 no root MissionRecord/cancellation:
  root mission identity exists locally, but durable MissionRecord cancellation is
  not yet implemented.

C-P0-06 descriptive registries:
  first ExecutableCapabilityGraph exists for workspace read-only skills only.
```

Still open:

```text
physical code sandbox
kill/revocation propagation
browser open_result/cross-origin typed effects
channel negation/effect inversion
authentic proof ledger and tamper rejection
trust-kernel write protection
memory/global workspace product ownership
fake worker/channel/desktop/voice success paths
full executable capability graph for all organs
```

## Files Changed

```text
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE0_AND_VERTICAL_SLICE_REPORT.md
sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py
sentinel-control/services/sentinel-core/sentinel/cli.py
sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py
```

## Validation

Passed:

```text
py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -q
10 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py::test_cli_product_route_uses_single_runtime_host_lifecycle_and_pumps_daemon -q
1 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
14 passed

py -3.13 -m compileall -q sentinel
passed
```

Observed adjacent pre-existing/stale expectation:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
8 passed / 1 failed

failure:
test_off_scope_skill_selection_recovers_without_granting_authority expected
"browse_search" in model_visible_skills, but the current skill-only browser
surface exposes separate affordances such as observe, navigate, search, follow,
inspect and extract_evidence.
```

This was not introduced by the canonical core slice and should be classified
before rewriting the test: stale expectation versus product regression.

## Next Correct Tranche

Proceed to the next vertical Foundation step, not a browser micro-fix:

```text
SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE1_ROOT_MISSION_CANCELLATION_AND_CAPABILITY_GRAPH
```

Minimum next target:

```text
RootMissionRuntime becomes durable MissionRecord-owned
root cancellation/revocation token exists before provider call
workspace list/read/search remain under the core
capability graph starts being generated from executable routes, not docs
proof placeholder remains honest until authentic proof ledger is implemented
```

Do not claim Sentinel is done until the 65-finding ledger is worked down with
real tests and graduated proof tiers.
