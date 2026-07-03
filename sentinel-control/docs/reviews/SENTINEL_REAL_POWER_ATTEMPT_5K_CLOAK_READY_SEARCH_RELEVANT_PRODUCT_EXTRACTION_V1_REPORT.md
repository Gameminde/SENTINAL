# SENTINEL_REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1_REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1 = VALID_FAILED
primary_failure_classification = RELEVANT_CARDS_NOT_FOUND
secondary = UNDER_5_EUR_SUPPORT_NOT_VISIBLE, FINISH_POLICY_GAP_SEARCH_CHURN
```

5K did not prove the full Alibaba product-research path. It did prove the important backend truth correction:

```text
Cloak readiness passed before provider call.
Provider call was allowed only after readiness.
Selected browser backend = cloak_browser.
Actual browser backend = cloak_browser.
Cloak/session receipts were produced for material browser actions.
No silent Playwright fallback occurred.
```

The product blocker moved from backend selection/readiness to relevance-quality and completion routing after non-relevant or price-unknown cards.

## Run Identity

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\attempt5k-20260703-173350
mission_id = mission_1fdc181559de4071bfc166d927ff344f
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
bounded_origin_hash = 952b92400b51c20b115f14e357fca0d066d761e3d64c9304fac6578a62122b9c
```

Raw endpoint, credential values, and raw binary path are not recorded in this report.

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

The readiness gate executed before any provider call. This means 5K did not spend provider budget discovering Cloak bootstrap/download readiness.

## Provider And Model-Native Loop

```text
provider_decision_calls = 8
model_native_intent_accepted_count = 5
metadata.reply_native_count = 5
provider_failure = false
```

Provider turns were retained only as safe diagnostics: top-level key names, hashes, visible-content counts, normalization strategy, and reasoning-presence flags. Raw provider output and reasoning were not persisted.

Two turns had empty or invalid visible content and were handled through existing model-native recovery/context routing. The run was not retried.

## Backend Truth

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
browser_devtools_context = present
browser_devtools_context_source = browser_session_manager_l5
browser_devtools_context_available = true
page_target_count = 1
```

Action receipts for `extract_product_cards`, `verify_extraction`, and both completed `search` actions all recorded:

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
```

The automatic summary initially marked `receipt_backend_match = false` because the open receipt type does not carry `selected_backend_id` / `actual_backend_id` fields. That is a reporting/evaluation mismatch, not a Playwright fallback or Cloak mismatch. Material browser action receipts matched Cloak.

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

## Browser Evidence Metrics

```text
browser_receipt_count = 5
search_attempt_count = 3
search_material_receipt_count = 2
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

The extracted cards were grounded, but did not satisfy the objective-relevance proof. The final card set contained several unrelated Alibaba navigation/search cards and one eyewear-like French card whose visible price/currency/MOQ remained unknown and whose relevance classifier did not credit it as relevant. Because relevance proof was not satisfied, finish remained unavailable.

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

Replay did not reopen, reclick, retype, resubmit, reextract, or rewrite receipts.

## Safety And Persistence Scan

Initial artifact scan found two raw-material marker hits inside the temporary Cloak browser profile/cache directory under the attempt capture root. This was not in Sentinel receipts, world-model JSON, FinalGate certificates, or reports.

The temporary browser profile directory was removed after the run:

```text
profile_dirs_removed = 1
post_cleanup_raw_material_hits = 0
secret_value_hits = 0
binary_path_hits = 0
raw_binary_path_persistence_scan_result = 0
process_env_cleanup = confirmed
```

The process-scoped variables set for the run were removed after the command:

```text
CLOAKBROWSER_BINARY_PATH = absent
SENTINEL_BROWSER_TEST_URL = absent
SENTINEL_BROWSER_HEADLESS = absent
SENTINEL_5K_RUN_ROOT = absent
```

Important follow-up: temporary browser profile cleanup must become automatic for Cloak live missions, not a manual report-step cleanup.

## Failure Interpretation

5K should not be treated as a backend failure. Cloak-first execution is now live enough to expose the next product blocker:

```text
search/extraction produced visible cards
but relevance assessment did not find a supported under-5-EUR product
then the loop re-entered search repeatedly
and loop_guard_repeated_action blocked before finish
```

The correct next blocker is:

```text
RELEVANCE_AND_SEARCH_RESULT_QUALITY_LOOP_GAP
```

Sub-problems:

```text
1. Search actuation can produce receipts but still land on weak/general Alibaba content.
2. Product extraction includes irrelevant navigation cards.
3. Multilingual product relevance is too weak.
4. Under-5-EUR support is correctly not claimed when price/currency evidence is unknown.
5. After summary says evidence is insufficient, the loop repeats search until guard block instead of escalating to a stronger inspect/open/refine-search skill lane.
6. Open receipts do not carry backend truth fields, causing evaluation false negatives.
7. Cloak live profile material cleanup needs to be automatic.
```

## Recommended Next Action

```text
FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1
```

Focus:

```text
- make Cloak profile cleanup automatic after live missions
- fix backend-match evaluation for open receipts vs action receipts
- improve search query/refinement when generic Alibaba landing content remains visible
- filter navigation/help cards out of product extraction
- support multilingual eyewear relevance terms such as glasses/sunglasses/lunettes
- route repeated insufficient-evidence search into inspect/open/refine-search, not repeated same search until loop guard
```

Follow-up implementation status:

```text
FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1 = LOCALLY_COMMITTED_IMPLEMENTED_CANDIDATE
implementation_commit = 380bbb7f13c4f68f4ffc0b17d3154571f428bf22
product_proven = no
next_prepared_real_attempt = REAL_POWER_ATTEMPT_5L_CLOAK_RELEVANCE_QUALITY_AND_PROFILE_CLEANUP_V1
```

## Confirmation

```text
one provider mission = yes
provider retry = no
fallback/AUTO = no
provider-native tools = no
push = no
merge = no
fake success = no
raw endpoint/credential/binary path persisted in report = no
```
