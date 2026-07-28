# SENTINEL_SQLITE_LIVE_RUN_V4_GLM_5_2_PROVIDER_PREFLIGHT_AND_COMPARATIVE_REPORT

## Verdict

```text
SQLITE_LIVE_RUN_V4_GLM_5_2 = NOT_RUN
reason = GLM_5_2_PROVIDER_PREFLIGHT_AUTH_FAILED
sqlite_provider_mission_calls = 0
browser_actions = 0
sqlite_rerun_authorized = NO
```

Supersession note:

```text
SUPERSEDED_BY = SENTINEL_SQLITE_LIVE_RUN_V4_GLM_5_2_ACTUAL_RUN_REPORT.md
reason = SENTINEL_CERT_MODEL_API_KEY was corrected after this preflight report
```

This report remains useful as the historical provider-auth diagnosis before the
environment variable was corrected. It is no longer the final V4 run truth.

The SQLite mission was not launched with GLM 5.2 because the required pre-mission
model response test did not pass.

## Contract Added

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = glm-5.2
request_mode = OpenAI-compatible chat
reasoning transport = non-thinking provider mode
provider-native tools = disabled
fallback/AUTO = disabled
```

Alibaba's current Model Studio documentation identifies `glm-5.2` as callable via
OpenAI-compatible APIs and documents GLM thinking/non-thinking mode. For this
Sentinel product comparison, the provider profile now sets:

```text
enable_thinking = false
reasoning_effort = none
```

This keeps the comparison on visible answer/decision content and avoids relying
on raw private reasoning transport.

## Preflight Evidence

### Ping 1

```text
run_id = glm_5_2_ping_20260728T074802Z
provider_call_consumed = true
credential_present = true
provider_contract_block = no
reply_present = false
result = inconclusive transport/provider response
```

### Ping 2 After Non-Thinking Contract

```text
run_id = glm_5_2_ping_non_thinking_20260728T075654Z
provider_call_consumed = true
credential_present = true
provider_contract_block = no
provider_failure = true
provider_failure_category = PROVIDER_AUTH_ERROR
provider_error_class = PROVIDER_ERROR
reply_present = false
```

Safe artifact refs:

```text
.armed_sqlite_xray/sqlite_live_runs/glm_5_2_ping_non_thinking_20260728T075654Z/safe_artifacts/glm_5_2_ping_result.json
```

No raw provider output, raw reasoning, cookies, session material, profile
material, selectors, DOM, or binary path is persisted in the ping artifact.

## Why The SQLite Mission Was Not Started

The user requested a GLM response test before the mission. The model contract is
now accepted locally, but the real provider returned an authorization-class
failure for `glm-5.2`. Launching the browser mission after that would spend a
mission authorization on a known provider access blocker rather than evaluating
GLM strategy or browser power.

```text
provider/model reached = yes
model usable for mission = no
first blocker = GLM_5_2_PROVIDER_AUTH_ERROR
SQLite mission = NOT_RUN
```

## DeepSeek V3 Baseline

Safe source:

```text
.armed_sqlite_xray/sqlite_live_runs/sqlite_v3_20260728T072411Z/safe_artifacts/terminal_summary.json
.armed_sqlite_xray/sqlite_live_runs/sqlite_v3_20260728T072411Z/safe_evidence/sqlite_v3_20260728T072411Z/browser_proof_index.json
```

Summary:

```text
model_id = deepseek-v4-pro
provider_decisions = 8
material_actions_consumed = 3
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
mission_status = blocked
mission_verdict = VALID_FAILED_TRUTHFUL_BLOCKER
blocked_reason = BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS
final_answer_present = false
browser_body_reached = true
browser_receipt_missing_count = 0
browser_receipt_readable_count = 5
material_browser_receipt_count = 5
replay_reconstruction = passed
cleanup = passed
proof_integrity_gate = failed
```

Observed DeepSeek V3 capability sequence:

```text
real_browser.search
real_browser.extract_evidence
real_browser.verify_extraction
sentinel_loop.summarize_evidence
real_browser.observe
real_browser.observe
```

Important mechanical truth from DeepSeek V3:

```text
search input_written = false
submit_attempted = false
search_materially_successful = false
first browser body blocker = real_browser_search_write_failed
terminal blocker = repeated action without progress
```

## GLM V4 Comparative Truth

```text
model_id = glm-5.2
provider_ping_calls = 2
sqlite_mission_provider_decisions = 0
material_actions_consumed = 0
selected_backend_id = NOT_REACHED
actual_backend_id = NOT_REACHED
browser_body_reached = false
FinalGate = NOT_REACHED
replay = NOT_REACHED
cleanup = NOT_REACHED_BY_MISSION
mission_verdict = NOT_RUN_PROVIDER_PREFLIGHT_FAILED
```

## Comparison

| Dimension | DeepSeek V3 | GLM 5.2 V4 |
| --- | --- | --- |
| Provider/model usable | Yes | No, provider auth failure |
| Browser body reached | Yes | Not reached |
| Cloak backend reached | Yes | Not reached |
| Provider decisions in mission | 8 | 0 |
| Material browser receipts | 5 readable, 0 missing | Not reached |
| Search materiality | Failed before input write proof | Not reached |
| Final answer | None | Not reached |
| Replay | Reconstruction passed | Not reached |
| Cleanup | Passed | Not reached |
| Comparative model behavior | Observable | Not observable |

## Implementation Notes

Files changed:

```text
sentinel/agent/model_execution/provider_profiles.py
sentinel/agent/model_execution/openai_compatible.py
tests/test_model_provider_catalog.py
tests/test_openai_compatible_provider_base.py
```

The change is provider-contract support only:

```text
known model id = glm-5.2
top-level provider request controls = supported
browser cognition = unchanged
browser runtime = unchanged
SQLite mission prompt/budget = unchanged
```

## Next Decision

Before a GLM browser mission can be evaluated, the Alibaba workspace/API key
must be authorized for `glm-5.2` on the selected DashScope/Model Studio endpoint,
or an explicitly approved GLM-capable provider/backend must be added through the
same product model contract.

Do not compare GLM browser intelligence from this tranche; the model never got
to the mission loop.
