# C5B CONTROLLED LIVE BROWSER PRODUCT MISSION

## Verdict

```text
C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION
= VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR

C5B preflight = PASSED
provider_calls = 1
product_browser_mission_attempts = 1
physical_browser_backend_actions = 0
model_native_decision_accepted = false
ProductActionKernel reached = false
Cloak reached during product mission = false
cleanup = PASSED
FIXED_PROVEN = 0/65
```

The controlled C5B run did not prove a cognitive Browser mission. It reached
the real provider phase after creating a durable root MissionRecord, but the
provider returned a credential rejection before any canonical model decision
could be accepted.

## Frozen Mission

```text
mission_id = C5B_SQLITE_OFFICIAL_GENERATED_COLUMNS_READONLY_V1
target_origin = sqlite.org
authority = public_web_read_only_browser_read_workspace_read
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = qwen-plus
max_provider_decisions = 10
max_material_actions = 16
fixture_backend = false
Playwright_fallback = false
holdout = false
```

The raw target URL, provider output, local binary path, profile/session
material, raw DOM, cookies and tokens were not persisted in the safe bundle.

## Preflight

The provider-free C5B preflight passed before the live provider mission:

```text
origin_redirect_enforcement = true
readiness_context_page_observe = true
timeout_worker_terminated = true
post_timeout_reopen_ready = true
provider_calls = 0
```

The preflight artifact is:

```text
sentinel-control/docs/reviews/deep_power_audit/C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_PREFLIGHT/c5b_preflight.safe.json
```

## Live Run Truth

```text
root MissionRecord created before provider = true
provider phase reached = true
provider call count = 1
failure = canonical_provider_failure_PROVIDER_AUTH_ERROR_credential_rejected_http_401
canonical decisions accepted = 0
material actions = 0
canonical receipts = 0
browser receipts = 0
Final mission status = blocked
mission cleanup = true
timeline reconstruction = true
proof root persisted = true
external authentic ledger = false
```

The first causal blocker is provider credential rejection. This is not a
SQLite content failure, not a Cloak failure, not a Browser routing failure and
not a model reasoning failure.

## Attempt 0

Before the real mission started, a premission runner provenance bug looked for
`path` / `executable_path` while the installed Cloak package exposes
`binary_path`. No provider call was consumed, no mission was started and no
Browser action was executed.

That premission attempt is preserved as:

```text
sentinel-control/docs/reviews/deep_power_audit/C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION/c5b_attempt0_provenance_block.safe.json
```

## Safe Evidence

The main safe bundle is:

```text
sentinel-control/docs/reviews/deep_power_audit/C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION/c5b_live_mission.safe.json
```

It records:

```text
mission freeze
provider/model metadata
safe Cloak provenance metadata
provider decision count
root MissionRecord status
safe failure classification
proof root hash
timeline verification
cleanup result
raw material persistence flags
```

No raw provider response or private reasoning was persisted.

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
= 4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py -q
= 26 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_stage0_finding_ledger_contains_all_65_findings -q
= 1 passed

JSON parse for ledger, C5B preflight and C5B live safe bundles
= passed
```

A prior combined validation command exceeded its 240 second bound, so the
validation was rerun in smaller named groups instead of being reported as
passed.

## Next Action

C5B should not be rerun silently. The next smallest useful step is credential
configuration repair or provider entitlement diagnosis without exposing the
secret, followed by one new explicitly versioned Browser product mission.
