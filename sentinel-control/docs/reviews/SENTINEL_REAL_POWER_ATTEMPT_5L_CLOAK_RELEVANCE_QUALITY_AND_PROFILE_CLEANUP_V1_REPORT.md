# SENTINEL_REAL_POWER_ATTEMPT_5L_CLOAK_RELEVANCE_QUALITY_AND_PROFILE_CLEANUP_V1_REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5L_CLOAK_RELEVANCE_QUALITY_AND_PROFILE_CLEANUP_V1 = VALID_FAILED
primary_failure_classification = SEARCH_MATERIAL_RECEIPT_MISSING
secondary = RELEVANT_CARDS_NOT_FOUND, FINISH_POLICY_GAP_SEARCH_CHURN, CLOAK_PROFILE_MATERIAL_CLEANUP_GAP
```

5L did not prove relevant Alibaba product search. It did prove that the 5K backend-truth false negative was fixed:

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
browser_devtools_context = present
silent Playwright fallback = no
```

## Run Identity

```text
source_commit = d7e20a35fb2028bf8d6b8ddf82f347b784a4bbca
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\attempt5l-20260704-014734
mission_id = mission_34df42fadd89428aa4398a9e39346a49
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
bounded_origin_hash = 952b92400b51c20b115f14e357fca0d066d761e3d64c9304fac6578a62122b9c
```

Raw endpoint URL, API key, provider output, reasoning, DOM, screenshots, cookies, session data, and raw Cloak binary path are not included in this report.

## Pre-Provider Readiness

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
failure_code = null
```

The readiness gate passed before provider consumption, so this was a real consumed provider mission.

## Provider And Model-Native Loop

```text
provider_decision_calls = 8
model_native_intent_accepted_count = 6
provider_failure = false
```

Provider retained diagnostics are structure-only: top-level key names, hashes, visible-content counts, normalization strategy, and reasoning-presence flags. Raw provider output and raw reasoning were not persisted.

## Action Sequence

```text
real_browser_control:real_browser.open
real_browser_control:real_browser.extract_product_cards
real_browser_control:real_browser.verify_extraction
sentinel_loop:summarize_evidence
real_browser_control:real_browser.search
real_browser_control:real_browser.search
real_browser_control:real_browser.search
```

The loop again reached extraction and verification, then produced a summary. It did not reach finish because relevance proof stayed unsatisfied and later turns churned into repeated search failures.

## Browser Metrics

```text
browser_receipt_count = 3
search_attempt_count = 3
search_material_receipt_count = 0
product_or_result_candidate_card_count = 6
relevant_product_card_count = 0
under_5_eur_supported_count = 0
extract_product_cards_count = 1
verify_extraction_count = 1
summarize_evidence_count = 1
summary_present = true
finish_present = false
mission_status = blocked
blocked_reason = loop_guard_repeated_action
final_context_progress_state = real_browser_verified_extraction_needs_relevant_products
finish_available = false
```

The material browser receipts were:

```text
real_browser.extract_product_cards = completed, cloak backend matched
real_browser.verify_extraction = passed, cloak backend matched
real_browser.open = present, legacy open receipt without backend fields
```

The fixed backend evaluator correctly ignores the legacy open receipt for backend-truth matching and validates the material Cloak action receipts.

## Failure Interpretation

5L moved the truth from "backend mismatch" to "search/relevance power still too weak":

```text
1. Cloak backend selection and actual runtime match.
2. Product/result candidate cards were visible and extracted.
3. Verification passed.
4. Summary lane ran.
5. No relevant under-5-EUR product evidence was established.
6. Search attempts after summary produced recoverable failures, not material search receipts.
7. Loop guard blocked repeated search before finish.
```

The actionable blocker is not provider, not schema, not backend selection, and not replay. It is:

```text
CLOAK_SEARCH_ACTUATION_AND_RELEVANCE_ROUTING_GAP
```

The browser skill needs a stronger search/inspect/open lane after relevance proof fails: repeated search should not be the dominant route when cards exist but relevance is not satisfied.

## Replay Proof

```text
replay_no_react = true
model_calls_delta = 0
real_browser_open_delta = 0
real_browser_click_delta = 0
real_browser_type_delta = 0
real_browser_extract_delta = 0
real_browser_press_delta = 0
real_browser_wait_delta = 0
real_browser_scroll_delta = 0
receipt_writes_delta = 0
evidence_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
```

Replay did not reopen, reclick, retype, resubmit, reextract, rewrite receipts, or call the provider.

## Safety And Cleanup

Initial run scan:

```text
secret_value_hits = 0
binary_path_hits = 0
raw_material_name_hits = 21
safety_scan_high_risk_hit_count = 21
```

The hits came from a generated live Cloak profile directory under the attempt capture root. That means the intended automatic profile cleanup did not fully hold for this run.

Post-run cleanup removed only the generated profile directory inside the 5L run root:

```text
profile_dirs_removed = 1
post_cleanup_secret_value_hits = 0
post_cleanup_binary_path_hits = 0
post_cleanup_high_risk_marker_hits = 0
post_cleanup_benign_boundary_marker_hits = 1
```

The remaining benign marker is `record.json` listing forbidden boundary categories such as cookies/session persistence. No raw credential, raw endpoint, raw binary path, raw provider output, raw reasoning, raw DOM, screenshot bytes, cookies, or session-token material remained after cleanup.

Browser attempt-scoped environment variables were absent after the command:

```text
CLOAKBROWSER_BINARY_PATH = absent
SENTINEL_BROWSER_TEST_URL = absent
SENTINEL_BROWSER_HEADLESS = absent
SENTINEL_5L_RUN_ROOT = absent
```

Provider env values were not printed or persisted.

## Git Status

Pre-run git status already contained unrelated dirty docs:

```text
 M sentinel-control/docs/reviews/SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
?? sentinel-control/docs/reviews/SENTINEL_REAL_POWER_ATTEMPT_5C_MODEL_LED_ALIBABA_ACTIONABILITY_RECOVERY_V1_REPORT.md
?? sentinel-control/docs/reviews/SENTINEL_ROOT_POWER_SIMPLIFICATION_CUT_PLAN_V1.md
```

This report is the only new report artifact created for 5L.

## Recommended Next Action

```text
FIX_CLOAK_SEARCH_ACTUATION_AND_RELEVANCE_ROUTING_V1
```

Focus:

```text
- make real_browser.search produce a material receipt when it actuates through Cloak
- if search fails after verified extraction, route to inspect_result/open_result/refine_query rather than repeated same search
- require relevance assessment but avoid repeated-search churn
- make Cloak profile cleanup automatic at runtime close, not manual post-run cleanup
- keep raw primitives internal and preserve hard boundaries
```

## Confirmation

```text
one provider mission = yes
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
push = no
merge = no
fake success = no
safe evidence only = yes after post-run profile cleanup
```
