# SENTINEL_SQLITE_LIVE_RUN_V4_GLM_5_2_ACTUAL_RUN_REPORT

## Verdict

```text
SQLITE_LIVE_RUN_V4_GLM_5_2 = VALID_FAILED_TRUTHFUL_BLOCKER
mission_status = blocked
blocked_reason = BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS
model_id = glm-5.2
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
```

This was a single real-provider, real-Cloak mission after correcting
`SENTINEL_CERT_MODEL_API_KEY`. No retry mission was run.

## Mission

```text
mission_id = SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1
target = sqlite.org
authority = public_web_read_only
max_provider_decisions = 10
max_material_actions = 16
run_id = sqlite_v4_glm_5_2_20260728T145552Z
HEAD = 55b56c00c4dc2ea69a76a14acd458011b39ebe32
```

Safe artifact refs:

```text
.armed_sqlite_xray/sqlite_live_runs/sqlite_v4_glm_5_2_20260728T145552Z/safe_artifacts/terminal_summary.json
.armed_sqlite_xray/sqlite_live_runs/sqlite_v4_glm_5_2_20260728T145552Z/safe_evidence/sqlite_v4_glm_5_2_20260728T145552Z/browser_proof_index.json
.armed_sqlite_xray/sqlite_live_runs/sqlite_v4_glm_5_2_20260728T145552Z/safe_artifacts/replay_reconstruction.json
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

## Search Actuation Truth

The first material browser blocker is generic and matches the DeepSeek V3 run:

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

This is not a SQLite content failure and not a GLM reasoning failure. The model
selected a valid high-level browser skill, then the browser body failed before
input-write proof.

## Proof And Cleanup

```text
proof_integrity_gate = FAILED
failure_reasons =
  - evaluator_not_called
  - proof_index_missing
  - runtime_provenance_missing_or_unsealed

completion_ledger_consistency = PASS
material_browser_receipts = PASS
replay_reconstruction = PASS
cleanup = PASS
safe_bundle = PASS
```

Replay:

```text
history_reconstructed = true
effect_reexecution_attempted = false
reexecuted_actions = false
model_calls_delta = 0
product_dispatch_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
```

Cleanup:

```text
live_context_count_after_mission = 0
owned_process_count_after_mission = 0
profile_material_count_after_mission = 0
profile_material_persisted = false
raw_paths_persisted = false
```

## DeepSeek V3 Versus GLM V4

| Metric | DeepSeek V3 | GLM 5.2 V4 |
| --- | --- | --- |
| Run ID | sqlite_v3_20260728T072411Z | sqlite_v4_glm_5_2_20260728T145552Z |
| Provider decisions | 8 | 8 |
| Material actions | 3 | 3 |
| Browser body reached | yes | yes |
| Cloak reached | yes | yes |
| Capability sequence | search -> extract -> verify -> summarize -> observe -> observe | search -> extract -> verify -> summarize -> observe -> observe |
| Search status | recoverable_failed | recoverable_failed |
| Search failure code | real_browser_search_write_failed | real_browser_search_write_failed |
| Input written | false | false |
| Submission attempted | false | false |
| Browser receipts | 5 readable / 0 missing | 5 readable / 0 missing |
| Final answer | none | none |
| Terminal blocker | BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS | BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS |
| Replay | no-react passed | no-react passed |
| Cleanup | passed | passed |
| Proof gate | failed | failed |

## Interpretation

GLM 5.2 did not outperform DeepSeek here because both models ran into the same
body-level blocker before the browser could write into the search control.

The comparative result is useful because it removes provider/model access as the
current blocker:

```text
GLM provider access = fixed
GLM product loop = reached
model strategy = sufficient to select browser search
first causal blocker = Cloak/browser search write actuation
```

The next correction should focus on the existing generic class:

```text
FIX_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMIT_MATERIALITY_V1
```

Do not tune prompts or switch models to hide this failure. The Browser Organ must
prove input write/readback/submission materiality before either model can fairly
complete this SQLite task through search.

