# Sentinel Real Power Attempt Browser Cortex Alibaba V1 Report

Date: 2026-07-12

## Verdict

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V1 = VALID_FAILED
primary_failure_classification = PRODUCT_PROOF_LONG_PATH_IO_GAP
secondary_failure_classification = PRODUCT_BROWSER_BACKEND_STILL_LOCAL_FIXTURE_PATH
```

This run did not prove the final bounded Alibaba browser objective. It did,
however, expose the next two product-spine blockers without retrying or hiding
the result.

## Safe Preflight

```text
Cloak readiness before mission = passed
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
raw endpoint values persisted = no
raw credential values persisted = no
raw browser binary path persisted = no
```

The bounded browser target was referenced only through safe origin/hash metadata
in persisted artifacts.

## Execution Summary

```text
mission_id = mission_042795e3c3cc43e78774e7afd1bfc52b
dispatch_id = dispatch_8c123426a55a4e1584019d0a0f863814
mission_status = blocked
task_loop_finalgate = blocked
task_loop_finalgate_reason = proof_receipt_missing
action_sequence = real_browser_control.real_browser.search
browser_action_status = completed
browser_selected_backend_id = cloak_browser
browser_actual_backend_id = cloak_browser
browser_session_backend_kind = cloakbrowser
browser_backend_mismatch = false
```

Provider decision calls were not mechanically countable from the persisted
attempt summary because the runner did not finish writing that summary after the
blocked mission. No raw provider output or reasoning was persisted.

## What Worked

```text
Cloak/session readiness passed before mission execution.
ProductActionKernel routed the browser search action.
RealBrowserControlRuntime produced a browser action receipt.
Browser FinalGate accepted the browser search receipt.
ProductActionKernel produced a product receipt.
ProductActionKernel FinalGate accepted the product receipt.
Backend truth matched: selected Cloak == actual Cloak.
Raw provider/reasoning/DOM/screenshot/cookie/session persistence scan = clean.
```

## What Failed

```text
ProductActionKernel task loop blocked with proof_receipt_missing.
Root cause: proof verifier used normal Path.exists/read_text on long Windows paths.
The proof files existed, but long-path reads failed in the verification lane.
```

A second product truth issue was also exposed:

```text
RuntimeHost product browser executor still forced _ProductLocalCloakBrowserEngine.
The world model safe title was Sentinel Product Browser Fixture.
Therefore this run was not real Alibaba page proof.
```

## Product Evidence

```text
browser_receipt = real_browser_action_afd85bebb55e4d948e03b02be5408328
browser_finalgate = real_browser_finalgate_089ce8bdee764c3eadb39a59be32b08f
product_receipt = product_action_kernel_receipt_2c6977ad980343c88aa1c172e1179546
product_finalgate = product_action_kernel_finalgate_b80a958230e643c3822ae81b4a64648f
product/search candidate cards = 3
safe origin hash present = yes
raw target URL persisted = no
```

The candidate cards came from the local product browser fixture and must not be
reported as real Alibaba product extraction.

## Replay

```text
replay_no_react = not mechanically verified
reason = mission blocked before completed task-loop proof
```

## Safety Scan

```text
scan_scope = attempt artifact tree
scan_method = long-path-aware file read
high_risk_hit_count = 0
raw provider/reasoning hit count = 0
credential/session/cookie hit count = 0
raw browser binary path hit count = 0
```

## Follow-Up Fixes

```text
6087d81 fix: make product proof reads long-path aware
8fa9e86 fix: route product browser executor through env cloak backend
```

## Recommended Next Proof

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V2_AFTER_PROOF_IO_AND_ENV_CLOAK_FIX
```

The next attempt must prove both:

```text
ProductActionKernel proof no longer blocks on long Windows paths.
RuntimeHost uses the env-configured Cloak-first real browser engine, not the local fixture engine.
```

