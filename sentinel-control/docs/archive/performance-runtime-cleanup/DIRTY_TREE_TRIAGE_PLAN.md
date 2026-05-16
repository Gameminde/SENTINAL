# Dirty Tree Triage Plan

Status: proposal only. Do not stage, commit, revert, delete, or start a new phase from this document.

Repository snapshot:

```text
Branch: main
HEAD before this plan: 3b8b911 docs: close performance runtime foundation A-F
Observed dirty tree before this plan: 69 modified tracked files, 61 untracked files
Observed dirty tree after creating this plan: 69 modified tracked files, 62 untracked files
Staged files: none
```

## Rules

- Do not touch browser, organ, or full-system-audit files except inspection/reporting until a cleanup route is accepted.
- Do not close performance-runtime backlog items during dirty-tree cleanup.
- Do not use `git add .`.
- Do not delete files until the delete bucket is approved.
- Mixed-hunk files must be handled with hunk-level staging or a deliberate manual patch.

## Required Commands Run

```bash
git status --short
git diff --stat
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git diff -- sentinel-control/services/sentinel-core/sentinel/mission/runner.py
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
```

Summary:

- `git status --short` shows no staged files. Before this plan it had 69 modified tracked files and 61 untracked files. After this plan it has 69 modified tracked files and 62 untracked files.
- `git diff --stat` shows 69 tracked files changed with 2039 insertions and 11086 deletions.
- The large deletion count is mainly from `sentinel/agent/browser/*` becoming compatibility shims while implementation appears in untracked `sentinel/organs/browser/*`.
- `runtime.py`, `runner.py`, and `final_gate.py` are mixed/high-risk files and are not safe to stage as whole files.

## Bucket 1: Commit Candidate

These files appear to belong to already-completed browser/organ migration work or related full-system-audit/browser tests. Recommended action is not immediate commit; first create a focused cleanup branch or commit group, run targeted tests, and stage exact files only.

### 1A. Browser Agent Compatibility Shims

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/accessibility_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/advanced_pool.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/cdp_ax.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/controlled_runner.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/dom_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/download_quarantine.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/evidence_adapter.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/extraction.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/form_submit.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/interaction_dry_run.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/interaction_execution.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/live_fetch.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/models.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/multitab_operator.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/observability.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/operator_runtime.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/pdf.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/playwright_interaction_backend.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/playwright_renderer.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/public_lifecycle.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/rendered_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/screenshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/supervisor.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/ui_observation.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/upload_authorized.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/url_guard.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/v3_advanced_authorities.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/v3_authority.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/verifier.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/visual_observation.py
```

Why it belongs here:

- Inspection of `sentinel/agent/browser/accessibility_snapshot.py` shows a backward-compatibility shim importing from `sentinel.organs.browser.accessibility_snapshot`.
- The diff stat shows large deletions in this family, consistent with moving implementation out of `agent/browser` into `organs/browser`.

Recommended action:

- Commit as part of a browser-organ migration cleanup only after verifying every shim imports the matching organ module.
- Use exact file staging, not directory staging, because this family is large.

Risk if wrong:

- Import breakage across legacy `sentinel.agent.browser.*` call sites.
- Silent loss of browser FinalGate coverage if an organ-side module is missing.

Required tests before committing:

```bash
python -m pytest tests/test_browser_organ_final_gate.py tests/test_browser_receipt_wrapper.py -q
python -m pytest tests/test_p6_external_organ_foundry.py -q
python -m pytest tests/test_agent_runtime.py -q
```

### 1B. Browser Organ Implementations

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/browser/accessibility_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/advanced_pool.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/cdp_ax.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/controlled_runner.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/dom_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/download_quarantine.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/evidence_adapter.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/extraction.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/final_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/form_submit.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/interaction_dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/interaction_execution.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/live_fetch.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/models.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/multitab_operator.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/observability.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/operator_runtime.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/pdf.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/playwright_interaction_backend.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/playwright_renderer.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/public_lifecycle.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/receipt_wrapper.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/rendered_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/screenshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/supervisor.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/ui_observation.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/upload_authorized.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/url_guard.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/v3_advanced_authorities.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/v3_authority.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/verifier.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/visual_observation.py
```

Why it belongs here:

- These are the apparent destination modules for the browser migration.
- The inspected implementation file contains real browser evidence code rather than generated artifacts.

Recommended action:

- Pair this bucket with Bucket 1A in the same browser-organ migration commit.
- Confirm `sentinel.organs.browser.__init__` exports are correct before staging.

Risk if wrong:

- Committing destination modules without matching shims may create duplicate browser surfaces.
- Missing one file can break imports that were converted to organ paths.

Required tests before committing:

```bash
python -m pytest tests/test_browser_organ_final_gate.py tests/test_browser_receipt_wrapper.py -q
python -m pytest tests/test_p6_external_organ_foundry.py -q
```

### 1C. Organ Contract Compatibility Changes

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/authority.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/contracts.py
sentinel-control/services/sentinel-core/sentinel/organs/desktop/harvest.py
sentinel-control/services/sentinel-core/sentinel/organs/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/implementation_alignment.py
sentinel-control/services/sentinel-core/sentinel/organs/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/organs/promotion_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/registry.py
sentinel-control/services/sentinel-core/sentinel/organs/replay.py
sentinel-control/services/sentinel-core/sentinel/organs/risk.py
sentinel-control/services/sentinel-core/sentinel/organs/vendor_harvest.py
sentinel-control/services/sentinel-core/sentinel/organs/exceptions.py
```

Why it belongs here:

- These files are organ-layer compatibility or migration supports.
- Some changes are small enum/import additions likely needed by browser-organ relocation and organ registration.

Recommended action:

- Commit with the browser-organ migration only if tests prove no P6 contract regression.
- If any hunk touches authority semantics, stage it separately and review by hunk.

Risk if wrong:

- Authority expansion or broken organ registration.
- P6A/P6C contract regression.

Required tests before committing:

```bash
python -m pytest tests/test_p6_external_organ_foundry.py -q
python -m pytest tests/test_p6_browser_organ_contract.py -q
python -m pytest tests/test_browser_organ_final_gate.py -q
```

### 1D. Browser/Organ Direct Tests

Exact files:

```text
sentinel-control/services/sentinel-core/tests/test_browser_organ_final_gate.py
sentinel-control/services/sentinel-core/tests/test_browser_receipt_wrapper.py
sentinel-control/services/sentinel-core/tests/test_mission_runner_browser_operator_route_rejected.py
sentinel-control/services/sentinel-core/tests/test_p6_external_organ_foundry.py
```

Why it belongs here:

- These tests directly support the browser organ migration and route rejection surfaces.

Recommended action:

- Commit only with the related implementation files they test.

Risk if wrong:

- Tests may encode future behavior not implemented in the same commit.

Required tests before committing:

```bash
python -m pytest tests/test_browser_organ_final_gate.py tests/test_browser_receipt_wrapper.py tests/test_mission_runner_browser_operator_route_rejected.py tests/test_p6_external_organ_foundry.py -q
```

## Bucket 2: Revert Candidate

No file is safe to mark as a direct revert candidate from this inspection alone.

Why:

- The dirty tree appears intentional and clustered around browser/organ migration plus full-system-audit support.
- The high-risk files are mixed, but that makes them manual-review candidates, not automatic revert candidates.

Recommended action:

- Do not run `git checkout --` or `git restore` on any file yet.
- If a later review proves a hunk is obsolete, revert by exact hunk or restore a copied file into a scratch area first.

Risk if wrong:

- Reverting apparently "unrelated" files could break the browser-organ shims or full-system-audit tests.

Required tests before reverting any future file:

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/test_p6_external_organ_foundry.py -q
```

## Bucket 3: Park Candidate

These are valuable process artifacts or future-spec work, but they should not enter the next cleanup commit without a deliberate strategy.

### 3A. Baseline Process Docs

Exact files:

```text
sentinel-control/docs/BASELINE_PLAN.md
sentinel-control/docs/BASELINE_STAGE_PASS1_REPORT.md
sentinel-control/docs/BASELINE_STAGE_PASS2_REPORT.md
sentinel-control/docs/BASELINE_STAGING_AUDIT.md
```

Why it belongs here:

- These were useful during Phase A-F baseline staging, but they are not canonical lock reports.
- They may be worth preserving in an archive, but should not pollute feature or runtime commits.

Recommended action:

- Either move to an accepted archive path in a docs-only commit, or delete after explicit approval.

Risk if wrong:

- Committing them as top-level docs may confuse future phase state.
- Deleting them too early loses staging evidence.

Required tests before committing:

```bash
git diff --check -- sentinel-control/docs
```

### 3B. Full-System-Audit Support Package

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/sentinel/mission/cancellation.py
sentinel-control/services/sentinel-core/sentinel/mission/exceptions.py
sentinel-control/services/sentinel-core/sentinel/mission/gate_sequence.py
sentinel-control/services/sentinel-core/tests/test_agent_phases.py
sentinel-control/services/sentinel-core/tests/test_decision_frame_mandatory_params.py
sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py
sentinel-control/services/sentinel-core/tests/test_kill_switch_reactive_property.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_bias.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_property.py
sentinel-control/services/sentinel-core/tests/test_sanitization_property.py
sentinel-control/services/sentinel-core/tests/test_self_improvement.py
sentinel-control/services/sentinel-core/tests/test_shared_events_layering.py
sentinel-control/services/sentinel-core/tests/test_toctou_binding_property.py
sentinel-control/services/sentinel-core/tests/test_trace_hash_property.py
```

Why it belongs here:

- Inspection shows `final_gate_registry.py` is a Task 11/CoreFinalGate decomposition module.
- Inspection shows `gate_sequence.py` is a Task 6/F-A3.8 gate-ordering module.
- These are not temporary, but they are also not part of the just-closed performance runtime foundation.

Recommended action:

- Park as a separate "full-system-audit consolidation" cleanup plan.
- Commit only after mixed files in Bucket 5 are reviewed, because these modules likely require `final_gate.py`, `runtime.py`, and `runner.py` hunks.

Risk if wrong:

- Parking too long keeps tests untracked and hides architecture progress.
- Committing without mixed-hunk dependencies may leave imports unresolved.

Required tests before committing:

```bash
python -m pytest tests/test_final_gate_registry.py tests/test_final_gate_determinism.py tests/test_final_gate_terminality.py -q
python -m pytest tests/test_gate_sequence_integration.py tests/test_gate_sequence_runtime_wiring.py -q
python -m pytest tests/test_memory_not_authority_property.py tests/test_sanitization_property.py tests/test_trace_hash_property.py -q
```

## Bucket 4: Delete Candidate

These appear temporary/generated only. Do not delete until approved.

Exact files:

```text
sentinel-control/services/sentinel-core/_junit.xml
sentinel-control/services/sentinel-core/_tmp_cold_store_smoke.py
```

Why it belongs here:

- `_junit.xml` is a test report artifact.
- `_tmp_cold_store_smoke.py` is a temporary smoke script.

Recommended action:

- Delete after approval with exact paths only.
- Consider adding or confirming ignore rules for `_junit.xml` if this recurs.

Risk if wrong:

- Low for `_junit.xml`.
- Medium for `_tmp_cold_store_smoke.py` if it contains unique benchmark diagnostics not captured elsewhere.

Required tests before deleting:

```bash
python -m pytest tests/perf/ -m "not slow" -q
```

## Bucket 5: Needs Manual Review

These files are not safe to commit, revert, or park automatically because they contain mixed phase concerns, core runtime changes, authority/final-gate logic, or broad agent behavior.

### 5A. Mixed-Hunk Core Runtime Files

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
```

Observed `runtime.py` hunk summary:

- Adds `CoreFinalGate` import and constructs `self._final_gate`.
- Adds `_assert_memory_not_authority_boundary`.
- Captures `original_allowed_actions`.
- Wraps multiple return paths through `_apply_final_gate`.
- Preserves mission result/archive on blocked fallback.
- Removes older helper blocks around repair/action budget and raw tool-call payload parsing.
- Contains scheduler-routing helper comments and helper body from prior performance/scheduler work.
- Adds `_apply_final_gate` with downgrade-and-recertify behavior.

Classification:

- Needs manual review.

Recommended action:

- Split into at least two commits if accepted:
  1. full-system-audit FinalGate runtime wiring
  2. any remaining performance/scheduler helper remnants that were not captured in A-F

Risk if wrong:

- Returning uncertified or over-blocked `AgentRunResult`.
- Closing backlog by accident.
- Breaking tool-call scheduling or controlled capability behavior.

Required tests before committing:

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/test_memory_not_authority_property.py tests/test_final_gate_terminality.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

Observed `runner.py` hunk summary:

- Adds `CancellationToken`, `MissionRevokedException`, and `BrowserOperatorRouteRejected`.
- Adds optional perf-runtime constructor dependencies and hot-cache/profiler use that still appear in the unstaged diff.
- Adds cancellation token threading into `run` and `run_mission`.
- Adds revocation polling before and after plan steps.
- Adds `MissionStatus.REVOKED` terminal behavior.
- Wraps browser operator route failures in structured `BrowserOperatorRouteRejected`.

Classification:

- Needs manual review.

Recommended action:

- Split performance-runtime remnants from full-system-audit revocation/browser-route changes.
- Do not stage whole file.

Risk if wrong:

- Incorrect mission terminal state.
- Browser route rejection behavior can change production mission semantics.
- Performance Phase B/C/D claims could be accidentally altered.

Required tests before committing:

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/test_gate_sequence_runtime_wiring.py tests/test_mission_runner_browser_operator_route_rejected.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

Observed `final_gate.py` hunk summary:

- Imports `FinalGateRegistry`.
- Replaces monolithic `evaluate` body with registry evaluation.
- Adds registry constructor/property.
- Relaxes mission result success consistency to reject only overall success with inner mission failure.
- Adds `AgentRunResult.model_rebuild(...)`.
- The Phase F `verify_performance_receipts` helper was already committed and is not the primary remaining diff here.

Classification:

- Needs manual review.

Recommended action:

- Commit only with `final_gate_registry.py` and its direct tests if the registry preserves exact check order/count.
- Do not mix with browser migration unless a test proves the browser module adapter dependency.

Risk if wrong:

- FinalGate check order/count changes.
- Missing browser checks.
- Authority/receipt validation regression.

Required tests before committing:

```bash
python -m pytest tests/test_final_gate_registry.py tests/test_final_gate_determinism.py tests/test_final_gate_terminality.py -q
python -m pytest tests/perf/bench/test_core_final_gate_performance_receipts.py -q
```

### 5B. Broad Agent/Brain Runtime Changes

Exact files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py
sentinel-control/services/sentinel-core/sentinel/agent/event_bus.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/evidence_ranker.py
sentinel-control/services/sentinel-core/sentinel/agent/exceptions.py
sentinel-control/services/sentinel-core/sentinel/agent/invariants.py
sentinel-control/services/sentinel-core/sentinel/agent/models.py
sentinel-control/services/sentinel-core/sentinel/agent/phases.py
sentinel-control/services/sentinel-core/sentinel/agent/state.py
sentinel-control/services/sentinel-core/sentinel/agent/supervisor.py
sentinel-control/services/sentinel-core/sentinel/learning/self_improvement.py
sentinel-control/services/sentinel-core/sentinel/mission/autonomy.py
sentinel-control/services/sentinel-core/sentinel/mission/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/mission/risk.py
sentinel-control/services/sentinel-core/tests/test_agent_invariants.py
sentinel-control/services/sentinel-core/tests/test_p6_subquadratic_agent_context_engine.py
```

Why it belongs here:

- These files affect core cognitive/runtime behavior, not only browser migration.
- They likely support full-system-audit tests, memory-not-authority checks, sanitization, phase sequencing, or decision-frame mandatory params.

Recommended action:

- Review with `git diff` per file and map each hunk to a named full-system-audit task before staging.

Risk if wrong:

- Silent authority expansion/regression.
- Context engine behavior drift.
- Test expectations may move ahead of implementation.

Required tests before committing:

```bash
python -m pytest tests/test_agent_invariants.py tests/test_memory_not_authority_property.py tests/test_sanitization_property.py -q
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py -q
```

## Exact Unclassified Items Check

Every item from the observed dirty tree is assigned above:

- Browser shim files: Bucket 1A.
- Browser organ destination files: Bucket 1B.
- Organ contract/common files: Bucket 1C.
- Browser/organ direct tests: Bucket 1D.
- Baseline docs: Bucket 3A.
- Full-system-audit support package: Bucket 3B.
- Generated/temp files: Bucket 4.
- `runtime.py`, `runner.py`, `final_gate.py`: Bucket 5A.
- Broad agent/brain runtime files and adjacent tests: Bucket 5B.
- This plan file itself, `sentinel-control/docs/DIRTY_TREE_TRIAGE_PLAN.md`, is intentionally new and should remain uncommitted until accepted.

Bucket counts, excluding this plan file itself:

```text
Bucket 1 Commit candidate: 83 files
Bucket 2 Revert candidate: 0 files
Bucket 3 Park candidate: 23 files
Bucket 4 Delete candidate: 2 files
Bucket 5 Needs manual review: 22 files
Total classified pre-plan dirty items: 130 files
Current additional untracked plan file: 1 file
```

## Recommended Cleanup Order

1. Delete candidate cleanup after approval:
   - Remove `_junit.xml` and `_tmp_cold_store_smoke.py`.
   - This can be done without a commit if both are untracked.

2. Browser-organ migration commit:
   - Stage Bucket 1A, 1B, 1C, and 1D only after targeted browser/organ tests pass.
   - Recommended message: `refactor: move browser runtime into organ layer`.

3. Full-system-audit park/commit decision:
   - Decide whether Bucket 3B is ready to commit or should move to a later spec.
   - Do not commit until Bucket 5A and 5B hunk dependencies are resolved.

4. Mixed core runtime hunk review:
   - Review `runtime.py`, `runner.py`, and `final_gate.py` manually.
   - Use hunk-level staging only.

5. Baseline docs decision:
   - Archive or delete Bucket 3A after the cleanup direction is accepted.

## Recommended First Cleanup Commit

The first real cleanup commit should be the browser-organ migration bundle only if targeted tests pass:

```text
refactor: move browser runtime into organ layer
```

Include:

- Bucket 1A browser compatibility shims.
- Bucket 1B browser organ implementations.
- Bucket 1C organ contract/common files only if tests prove they are required.
- Bucket 1D direct browser/organ tests.

Do not include:

- `runtime.py`
- `runner.py`
- `final_gate.py`
- full-system-audit registry/gate-sequence files
- baseline docs
- temp/generated files

Reason:

- The browser/organ migration is the most coherent visible cluster.
- It has a clear source/destination shape.
- It can be tested independently before touching core runtime mixed hunks.
