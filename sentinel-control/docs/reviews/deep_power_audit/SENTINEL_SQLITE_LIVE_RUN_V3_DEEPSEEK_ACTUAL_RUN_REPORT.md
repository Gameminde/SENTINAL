# SENTINEL_SQLITE_LIVE_RUN_V3_DEEPSEEK_ACTUAL_RUN_REPORT

## Verdict

```text
SQLITE_LIVE_RUN_V3_DEEPSEEK = VALID_FAILED_TRUTHFUL_BLOCKER
mission_status = blocked
blocked_reason = BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS
model_id = deepseek-v4-pro
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
```

This was a real-provider, real-Cloak SQLite mission. It did not complete the
objective, but it preserved truthful failure instead of inventing a final answer.

## Mission

```text
mission_id = SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1
target = sqlite.org
authority = public_web_read_only
run_id = sqlite_v3_20260728T072411Z
model = deepseek-v4-pro
```

Safe artifact refs:

```text
.armed_sqlite_xray/sqlite_live_runs/sqlite_v3_20260728T072411Z/safe_artifacts/terminal_summary.json
.armed_sqlite_xray/sqlite_live_runs/sqlite_v3_20260728T072411Z/safe_evidence/sqlite_v3_20260728T072411Z/browser_proof_index.json
.armed_sqlite_xray/sqlite_live_runs/sqlite_v3_20260728T072411Z/safe_artifacts/replay_reconstruction.json
```

No raw provider output, private reasoning, raw DOM, cookies, session/profile
material, selectors, screenshots, or raw local binary path are included in this
report.

## Provider And Browser Path

```text
provider_decisions_consumed = 8
material_actions_consumed = 3
browser_body_reached = true
Cloak backend reached = true
browser_receipt_missing_count = 0
browser_receipt_readable_count = 5
material_browser_receipt_count = 5
```

Capability sequence:

```text
real_browser.search
real_browser.extract_evidence
real_browser.verify_extraction
sentinel_loop.summarize_evidence
real_browser.observe
real_browser.observe
```

## Browser Search Actuation Truth

The first material browser failure happened at search write actuation:

```text
operation = real_browser.search
status = recoverable_failed
typed_search_outcome = FAILED_RECOVERABLE
safe_failure_code = real_browser_search_write_failed
candidate_selected = true
ref_resolved = true
element_attached = true
element_visible = true
element_enabled = true
focus_attempted = true
focus_succeeded = false
clear_attempted = true
clear_succeeded = true
write_attempted = true
write_method = fill
write_succeeded = false
write_readback_status = not_attempted
input_written = false
submission_attempted = false
request_observed = false
navigation_or_state_changed = false
result_region_changed = false
```

DeepSeek selected an in-scope high-level browser path. Sentinel then failed
mechanically before proving input write or submission materiality.

## Evidence And Answer Quality

```text
final_answer_present = false
mission_objective_satisfied = false
human_readable_public_evidence_count = 0
supported_factual_claim_count = 0
unsupported_factual_claim_count = 0
```

No useful SQLite answer was produced. This is correct: the proof lane did not
have human-readable official evidence sufficient for a grounded final answer.

## Proof Gate

```text
proof_integrity_gate = FAILED
failure_reasons =
  - evaluator_not_called
  - proof_index_missing
  - runtime_provenance_missing_or_unsealed
```

Subresults:

```text
safe_bundle = PASS
material_browser_receipts = PASS
completion_ledger_consistency = PASS
replay_reconstruction = PASS
cleanup = PASS
proof_index = FAIL
runtime_provenance = FAIL
blind_evaluator_consistency = FAIL
```

Important nuance: the safe evidence copy contains a readable
`browser_proof_index.json`, but the terminal summary still records an empty
proof-index reference and therefore the official proof gate remains failed.

## Replay

```text
history_reconstructed = true
effect_reexecution_attempted = false
reexecuted_actions = false
model_calls_delta = 0
product_dispatch_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
replay_mode = artifact_history_reconstruction
```

Replay no-react held for the recorded artifact history.

## Cleanup

```text
live_context_count_after_mission = 0
owned_process_count_after_mission = 0
profile_material_count_after_mission = 0
profile_material_persisted = false
raw_paths_persisted = false
raw_dom_cookies_session_profile_persisted = false
raw_provider_output_persisted = false
```

## Interpretation

DeepSeek V3 proved that the model/provider/product path reached the Browser
Organ and Cloak backend, but it did not prove SQLite task completion or browser
search materiality.

The first causal product blocker is:

```text
CLOAK_SEARCH_WRITE_ACTUATION_FAILURE
```

The correct next fix class is:

```text
FIX_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMIT_MATERIALITY_V1
```

