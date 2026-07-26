# SENTINEL SQLITE OFFICIAL GENERATED COLUMNS DOCS V1 LIVE XRAY REPORT

## Verdict

```text
SQLITE_LIVE_RUN_V2 = VALID_FAILED_INFRASTRUCTURE
SQLITE_LIVE_RUN_V2_AUTHORIZATION_CONSUMED = YES
SQLITE_RERUN_AUTHORIZED = NO
provider_calls_consumed = 1
material_actions_consumed = 0
fixture_backend = false
playwright_fallback = false
frozen_holdout_used = false
```

This report covers the second, separately authorized SQLite live run after Cloak lifecycle readiness repair. The mission reached the real provider/model phase and consumed one provider decision. It did not reach a material browser dispatch receipt.

## Frozen Mission

```text
mission_id = SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1
target_origin = sqlite.org public read-only
max_provider_decisions = 10
max_material_actions = 16
one_run_only = true
backend = cloak_browser
```

## Backend And Preflight Truth

- body-only preflight: `PASSED`
- cloak readiness: `ready = true`
- selected_backend_id: `cloak_browser`
- actual_backend_id: `cloak_browser`
- session_backend_kind: `cloakbrowser`
- preflight receipt_backend_match: `true`
- provider_call_allowed_before_provider: `true`
- ensure_binary_called: `false`
- profile_material_persisted: `false`
- owned_process_count_after_mission: `0`
- live_context_count_after_mission: `0`
- profile_material_count_after_mission: `0`

Safe artifact refs:

```text
safe_artifacts/body_only_preflight.json
safe_artifacts/terminal_summary.json
safe_artifacts/proof_integrity_gate.json
safe_artifacts/presence_mirror_status.json
```

Safe hashes:

```text
body_only_preflight_sha256 = 6E52AAC11F9B01CD69E854D0508CAF478781EE31E77F2814826084E077E80835
terminal_summary_sha256 = 52BFC834394670E22B96519A59CD9511D934FCF42E82D55181777534F053BA4B
```

## Mission Trace

```text
run_id = sqlite_v2_20260726T122128Z
provider/model = aliyun_dashscope / deepseek-v4-pro
provider_decisions = 1
model-selected action = real_browser_control.real_browser.search
action_envelope_accepted = true
browser_action_started = true
ProductActionKernel dispatch = NOT_REACHED
terminal browser receipt = NOT_REACHED
BrowserProofIndex = empty / NOT_REACHED
FinalGate = NOT_REACHED
replay reconstruction = NOT_REACHED
final answer = NOT_AVAILABLE
```

Crash-safe evidence events:

```text
sqlite_live_v2_manifest_frozen
run_started
provider_decision_received
action_envelope_accepted
browser_action_started
cleanup_result
sqlite_live_v2_safe_bundle_written
```

## First Causal Blocker

```text
first_causal_blocker = mission_workspace_root_not_found
failure_stage = mission workspace preparation before ProductActionKernel browser dispatch
exception_class = ValueError
exception_hash = a6db61ff8b35de2da692f6b9bc627e4fa5c2baa437c914a83d5a0afe501c7fe0
```

Provider/model succeeded in selecting a safe browser search. The run failed because the RuntimeHost passed a runtime-owned workspace root into MissionWorkspaceRuntime before creating that directory. The browser action was therefore recorded as started, but no material Cloak browser receipt could be produced.

This is a Sentinel local lifecycle/infrastructure defect. It is not a SQLite content failure, not a model reasoning failure, and not evidence of Playwright fallback.

## Corrections Applied After The Consumed Run

The SQLite mission was not rerun.

Local corrections prepared for the next authorized run:

- `RuntimeHost.run_product_action_kernel_task_loop` now creates the runtime-owned workspace root before creating the resource scope and task loop.
- `CrashSafeBoundedLiveRunEvidenceSink` now uses Windows long-path-safe filesystem operations for event logs and atomic snapshots.
- `/api/presence/events` now selects the latest valid mission by append order, not by cross-mission numeric sequence.
- `/presence` no longer renders the historical MDN replay as the initial primary state. Before live connection it shows a transparent connecting/unavailable observer state; once live is reachable it renders the live SQLite mission.

## Presence / X-Ray Truth

```text
presence_stream = CONNECTED
presence_mission_id = sqlite_v2_20260726T122128Z
presence_event_count = 7
historical_mdn_as_primary_state = false
mock_runtime_actions = false
can_execute = false
can_grant_authority = false
```

Visible UI verification after the correction showed:

```text
LIVE SAFE STREAM / SQLITE_V2_20260726T122128Z
state = OBSERVING
safe_summary = Telemetry event persisted.
Observed event 7 of 7
MDN visible as primary mission = false
```

## Gate Results

```text
PROOF_INFRASTRUCTURE_GATE = FAILED
BROWSER_TASK_GATE = FAILED_INFRASTRUCTURE
SESSION_CONTINUITY_GATE = NOT_REACHED_FOR_MISSION_ACTION
SESSION_RECOVERY_GATE = NOT_TRIGGERED
REPETITION_BOUND_GATE = NOT_REACHED
HUMAN_EVIDENCE_GATE = FAILED_NO_EVIDENCE
FINAL_ANSWER_GATE = FAILED_NO_ANSWER
```

The proof gate failed correctly because the run ended with a runner exception before ProductActionKernel browser dispatch. It did not silently certify an empty BrowserProofIndex.

## Safety

No raw provider output, private reasoning, raw DOM, raw URL, raw query, selectors, screenshots, cookies, session/profile material, secrets, or raw Cloak binary path are included in this report.

## Validation

Executed after the run, without rerunning SQLite:

```text
py -3.13 -m pytest sentinel-control\services\sentinel-core\tests\operator\test_crash_safe_bounded_live_run_evidence_sink.py -q
5 passed

py -3.13 -m pytest sentinel-control\services\sentinel-core\tests\operator\test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
13 passed

node scripts\presence-shell-real-state.test.mjs
presence_shell_real_state_contract=PASS

npx tsc --noEmit
passed

npm run build
passed

py -3.13 -m compileall -q sentinel-control\services\sentinel-core\sentinel
passed
```

## Next

Do not rerun SQLite without a new explicit authorization. The next run should start from the local workspace-root fix and use the same no-fallback, real-provider, real-Cloak contract.
