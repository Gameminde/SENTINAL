# SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE2_CODE_SANDBOX_QUARANTINE_REPORT

## Verdict

```text
P0-02_CODE_SANDBOX_PHYSICAL_BOUNDARY = REPRODUCED_UNSAFE_T1_LOCAL
CANONICAL_CORE_CODE_EXEC_EXPOSURE = QUARANTINED
PHYSICAL_SANDBOX_FIX = NOT_IMPLEMENTED
PROVIDER_CALLS = 0
BROWSER_RUNS = 0
```

This tranche protects the new canonical core from exposing a capability that is
not yet physically confined.

## Executable Probe

A deterministic local probe created:

```text
outside temporary canary file
workspace-local pytest file
code_execution_sandbox pytest_file profile
```

The workspace-local pytest file read the outside canary successfully through
the current host subprocess runtime.

Observed truth:

```text
CodeExecutionSandboxRuntime = argument-filtered subprocess sandbox
OS-level read confinement = not proven
outside workspace read = reproduced
```

No user files, secrets, network endpoints or real project files were touched.
The canary lived only inside pytest temporary directories.

## Core Quarantine

The canonical capability graph now records:

```text
capability = code_execution_sandbox
operation = code_exec.run_profile
reason = physical_sandbox_not_proven
proof_tier = P0_REPRODUCED_LOCAL
model_visible = false
```

If the model selects the quarantined capability anyway, the canonical core
returns:

```text
status = blocked
final_reason = CAPABILITY_QUARANTINED
blocked_capability = code_execution_sandbox.code_exec.run_profile
blocked_reason_detail = physical_sandbox_not_proven
material_action_count = 0
cleanup_completed = true
```

This keeps power honest: the capability still exists in Sentinel, but the new
core will not advertise or execute it as safe product power until the physical
sandbox is real.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/canonical_core.py
sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_STAGE2_CODE_SANDBOX_QUARANTINE_REPORT.md
```

## Validation

Passed:

```text
py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_stage2_probe_confirms_current_code_exec_is_not_physical_sandbox_and_core_quarantines_it -q
1 passed

py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_model_selected_quarantined_code_capability_returns_typed_blocker -q
1 passed

py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -q
14 passed
```

## Required Future Fix

To unblock code execution under the core:

```text
real process/container sandbox
read-only root
explicit writable workspace mount
network denied by default
ambient credentials absent
child-process kill
post-run residue scan
receipt-backed confinement proof
```

Only after that proof should `code_exec.run_profile` become model-visible under
the canonical core.
