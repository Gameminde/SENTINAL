# SENTINEL_REAL_BROWSER_BODY_SESSION_LIFECYCLE_AND_ACTUATION_STABILITY_V1_REPORT

## Verdict

```text
REAL_BROWSER_BODY_SESSION_LIFECYCLE_AND_ACTUATION_STABILITY_V1
= VALID_BODY_STABLE_CANARY_NOT_RUN

implementation_commit = 22f8caf9d54eb6dc7a69dff98a649195a2780034
provider_calls = 0
real_provider_used = no
real_browser_live_canary_run = no
frozen_holdout_used = no
playwright_fallback = no
implicit_fixture_as_cloak = no
trusted_runtime_context_override_from_model = blocked
browser_authority_expansion = blocked in runtime helpers
push_performed = no
```

This tranche implements the root-task browser body ownership fix exposed by
Stage 0. It proves the corrected lifecycle locally on the RuntimeHost product
path and keeps the real provider/browser canary blocked until live Cloak
readiness is available in the current process.

Current process preflight:

```text
CLOAKBROWSER_BINARY_PATH_present = false
provider_env_present = true
provider_call_allowed_for_this_tranche = false
reason = live Cloak readiness cannot be proven in this process
```

No real-provider call was made.

After the additional critical review, this tranche also folds in the P0 truth
guards that are prerequisites for a trustworthy browser body:

```text
local deterministic fixture is labeled local_fixture_browser_engine
missing live browser config blocks before browser execution
selected_backend_id derives from actual engine identity
loop_context/model evidence cannot override mission_id/workspace_ref/adapter/backend/kernel
browser runtime authority helpers do not add domains/actions behind the root grant
```

## Accepted Stage 0 Evidence

Stage 0 accepted state:

```text
REAL_BROWSER_BODY_SESSION_LIFECYCLE_AND_ACTUATION_STABILITY_V1_STAGE0
= VALID_REVIEW_AND_BODY_REPRODUCTION

provider_calls = 0
playwright_fallback = no
```

Accepted reproduced evidence:

```text
45 missions
12 top-level tasks
40 real_browser_search_session_open_failed
top-level FileNotFoundError preserved
one partially operational task
46 provider decisions in calibration
```

Stage 0 body-only reproduction showed:

```text
sequential close/open = passed
overlapping unclosed Cloak contexts = failed with cloakbrowser_open_failed:Error
product-loop body-only second search = real_browser_search_session_open_failed
```

## Measured Cloak Concurrency Capability

Pre-implementation characterization tested:

```text
same backend + same profile overlap = failed
same backend + different profile overlap = failed
different backend owner + same profile overlap = failed
different backend owner + different profile overlap = failed
failure class = BrowserSessionEngineError / cloakbrowser_open_failed:Error
provider_calls = 0
playwright_fallback = false
```

Implementation exposes this as:

```text
backend_concurrency_capability = one_active_cloak_context_global_measured
```

This is not a global unowned singleton. It is a host-owned, root-task-scoped
resource lease that serializes live browser ownership by keeping one active
browser body per root product task and closing it at the root ownership boundary.

## Root Lease Architecture

New runtime ownership path:

```text
RuntimeHost.run_product_action_kernel_task_loop
-> ProductTaskResourceScope
-> ProductTaskBrowserRuntimeLease
-> one root-owned browser engine/session manager
-> child MissionRecord wraps the same engine in per-action RealBrowserControlRuntime
-> child receipts stay per MissionRecord
-> root finally closes browser lease
```

Child missions receive only safe data refs and context cards:

```text
root_browser_runtime_lease.safe_ref
root_browser_runtime_lease.lease_hash
root_scope_id_hash
root_session_id_hash
selected_backend_id
actual_backend_id
backend_concurrency_capability
lifecycle_state
```

They do not own or close:

```text
Cloak process
persistent context
page
profile directory
session manager
root lease
```

## P0 Truth Guard Additions

The implementation includes the first critical review fixes needed before any
new provider calibration:

```text
P0.2 authority monotonicity:
  _real_browser_authority now preserves the child/root grant instead of adding browser actions/domains.
  BrowserSessionManagerRealBrowserEngine no longer adds target_host or browser_session_* actions to authority.
  Product loop no longer injects real_browser:bounded_test_url into child authority.
  Browser tests now declare the bounded browser ref explicitly.

P0.3 fixture/backend identity truth:
  explicit local fixture backend = local_fixture_browser_engine
  explicit local fixture session kind = local_fixture
  selected_backend_id is the actual engine backend id, not hardcoded cloak_browser.
  no-env live browser search blocks as real_browser_live_backend_config_missing before browser receipts.

P0.4 trusted runtime context protection:
  ActionKernel strips trusted runtime keys from loop_context before merging model evidence.
  RuntimeHost browser/sentinel executors allowlist model evidence context separately.
  model-supplied mission_id/workspace_ref/adapter_id/backend_id cannot override product runtime identity.

P0 browser fluidity preservation:
  visible product cards still prioritize extract_product_cards in the browser decision frame.
  extract/verify may consume an existing root browser lease without requiring a new live backend config.
```

Not fully closed in this tranche:

```text
P0.1 root lease architecture = implemented locally; live Cloak canary still required.
P0.5 workspace file snippet redaction = not expanded in this tranche; existing scans remain targeted.
P1 close-state/quarantine/thread cleanup refinements = deferred after live canary evidence.
```

## Before / After Resource Graph

Before:

```text
root product loop
-> child MissionRecord per browser action
-> new RealBrowserControlRuntime
-> new BrowserSessionManagerRealBrowserEngine
-> new BrowserSessionManagerL5Live
-> new Cloak persistent context
-> no product-loop finally close
```

After:

```text
root product loop
-> root ProductTaskResourceScope
-> lazy ProductTaskBrowserRuntimeLease
-> one browser engine/session body reused across child actions
-> child MissionRecord creates per-action receipt runtime around same engine
-> root finally closes lease
-> RuntimeHost.shutdown closes leaked scopes
```

## Cleanup Paths

Implemented cleanup ownership:

```text
successful completion = root finally closes lease
grounded negative completion = root finally closes lease
model/material budget exhaustion = root finally closes lease
body failure = circuit breaker result, root finally closes lease
exception = root finally closes lease
RuntimeHost.shutdown = close_all_product_task_resource_scopes()
replay = no live browser creation or close
```

Properties proven locally:

```text
close is idempotent at ProductTaskResourceScope
child mission does not close root lease
shutdown closes leaked root scope
partial-open/body failure closes failed and recovered engines
replay does not create another engine/session/context
```

## Operational Readiness

Readiness result model now exposes separate fields:

```text
backend_selected
backend_identity_matched
process_operational
devtools_operational
context_operational
page_operational
multi_action_reuse_operational
cleanup_operational
reopen_operational
provider_call_allowed
```

The readiness probe now performs:

```text
open
-> observe
-> second observe
-> close/cleanup
-> reopen
-> close/cleanup in finally
```

Local fake Cloak readiness proof:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
backend_identity_matched = true
multi_action_reuse_operational = true
cleanup_operational = true
reopen_operational = true
open_calls = 2
observe_calls >= 2
```

Live Cloak readiness in this process:

```text
not_run
reason = CLOAKBROWSER_BINARY_PATH not present in process environment
```

## Body Circuit Breaker Proof

Implemented behavior:

```text
browser body failure
-> compute safe failure fingerprint
-> close degraded root engine
-> create one replacement engine inside same root lease
-> retry already selected action once
-> if body still fails, return BODY_SESSION_UNAVAILABLE
-> no model/provider recall
```

Regression proof:

```text
test_unchanged_browser_body_failure_circuit_breaker_blocks_without_model_recall = passed
blocked_reason = BODY_SESSION_UNAVAILABLE
capability_sequence = real_browser_control:real_browser.search
model_call_count = 1
provider_calls = 0
engines_created = 2
failed/recovered engines closed >= 2
```

## Body Stress Proof

Local/fake body stress proof:

```text
root cycles = 3
actions per root = search -> open_result -> extract_product_cards -> verify_extraction -> summarize_evidence -> finish
root engine factory calls = 3 total / 1 per root
close_count = 1 per root
type_count = 1 per root
extract_count >= 2 per root
replay creates no live body = passed
RuntimeHost shutdown closes leaked scope = passed
```

Required metric disposition:

```text
session open success = 1.0 local/fake
navigation/observation success = covered locally by search/open/extract/verify path
multi-action root reuse = 1.0 local/fake
FileNotFoundError = 0 in local/fake product path tests
unsupported overlap attempts = 0 on new root-scoped path
stale child handles = 0 observed in local/fake tests
profile cleanup failures = 0 observed in local/fake tests
provider calls during body stress = 0
silent fallback = 0
implicit local fixture as Cloak = 0
trusted runtime context overrides from model loop_context = 0 in regression
raw profile/session persistence = 0 observed in targeted scan of changed paths
```

Not claimed:

```text
6 public-origin live Cloak stress = not run in this process
12 live sequential public-origin cycles = not run in this process
provider canary = not run
```

## FileNotFoundError Disposition

Stage 0 preserved the calibration top-level `FileNotFoundError` as an open
truth. This implementation did not reproduce it in local/fake product path tests.

Disposition:

```text
top-level FileNotFoundError boundary = still open for next live Cloak canary
local/fake lifecycle correction = no FileNotFoundError observed
claim_not_made = not proven fixed
```

If the next live Cloak canary no longer produces the top-level
`FileNotFoundError`, that should be recorded as correlated evidence only until
the exact file boundary is identified.

## Provider Canary

Provider canary was not run.

Reason:

```text
live Cloak readiness gate not satisfied in current process
CLOAKBROWSER_BINARY_PATH_present = false
```

This prevents a provider call from being consumed to discover a body bootstrap
or lifecycle failure. That is the intended behavior.

## Files Changed

```text
sentinel/operator/runtime_host.py
sentinel/operator/action_kernel.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/unified_execution_dispatcher.py
sentinel/operator/real_browser_control_runtime.py
tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
tests/operator/test_power_pack6d_browser_skill_spine.py
tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 25 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
result = 11 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 95 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack3_agent_workspace_runtime.py -q
result = 5 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
result = 15 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result = passed

git diff --check
result = passed with CRLF conversion warnings only

targeted scan for secrets/raw-provider/provider-native/fallback/AUTO/raw DOM/cookies/session/profile material
result = benign hits only:
  - forbidden marker constants and hard-boundary lists
  - redaction/assertion test strings
  - screenshot/cookie/session wording in negative-persistence tests
```

## Hard Boundaries Preserved

No change was made to:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier / external send outside grant
cookies / session persistence
upload/download outside authority
arbitrary browser JavaScript outside grant
workspace escape
destructive writes outside authority
provider-native tools
fallback/AUTO
replay side effects
fake proof / proof tampering
```

## Remaining Gaps

```text
1. Run live Cloak operational canary after CLOAKBROWSER_BINARY_PATH is restored.
2. If live canary passes, run exactly one real-provider non-holdout canary.
3. Trace top-level FileNotFoundError only if it remains after lifecycle fix.
4. Consider a separate proof-policy cleanup for non-material inspect_result receipts.
5. Do not resume broad calibration until live body canary passes.
```

## Next Prepared Action

```text
REAL_BROWSER_BODY_LIVE_CLOAK_OPERATIONAL_CANARY_V1
```

Only run it after:

```text
CLOAKBROWSER_BINARY_PATH present in process env
SENTINEL_BROWSER_TEST_URL bounded non-holdout target set
Cloak readiness fields all operational enough for provider_call_allowed = true
```

Then, and only then, prepare the single provider canary required by the tranche.
