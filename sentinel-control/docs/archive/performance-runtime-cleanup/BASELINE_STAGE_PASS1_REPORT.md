# Phase A-E Baseline Stage Pass 1 Report

Status: dry-run staging audit plus safe staging pass.

No commit was made. Phase F was not started. `git add .` was not used. `runtime.py`, `runner.py`, and `shared/events.py` were not staged.

## Pass 1 Safe Staging Performed

Staged only:

- Group 1 `.kiro/specs/sentinel-performance-runtime-foundation/*` spec/report files, using `git add -f`.
- Group 2 exact `sentinel/perf/*` module files.
- Group 3 exact `tests/perf/*` test files.
- `sentinel-control/services/sentinel-core/pyproject.toml`.

No broad-directory staging command was used.

## Cached Diff Summary After Pass 1

Command:

```bash
git diff --cached --stat
```

Summary:

```text
66 files changed, 22393 insertions(+)
```

The cached diff contains:

- 10 spec / lock / backlog files.
- 28 `sentinel/perf` files.
- 27 `tests/perf` files.
- 1 `pyproject.toml` marker change.

## Cached File List After Pass 1

Command:

```bash
git diff --cached --name-only
```

Cached files:

```text
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/design.md
.kiro/specs/sentinel-performance-runtime-foundation/requirements.md
.kiro/specs/sentinel-performance-runtime-foundation/tasks.md
sentinel-control/services/sentinel-core/pyproject.toml
sentinel-control/services/sentinel-core/sentinel/perf/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/bench/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/context_build_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/llm_decision_frame_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/prompt_frame_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/token_budget_governor.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/artifact_ref_store.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cache_invalidation_policy.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cold_receipt_store.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/delta_state_engine.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/hot_mission_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/receipt_index.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/cost_profiler.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/latency_profiler.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_receipt.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_trace.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/async_organ_scheduler.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/backpressure_controller.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/batch_execution_planner.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/tool_call_queue.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_change_watcher.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_snapshot_cache.py
sentinel-control/services/sentinel-core/tests/perf/__init__.py
sentinel-control/services/sentinel-core/tests/perf/caches/__init__.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_canonical_equivalence_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_invalidation_dependency_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_decision_frame_cache_lifecycle_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_runtime_cache_wiring.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_safety_invariants_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_token_budget_enforcement_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/__init__.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_artifact_ref_store_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_cold_receipt_store_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_hot_cold_bounds_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_phase_b_benchmarks.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_receipt_index_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/__init__.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_latency_profiler_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_receipt_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_trace_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_profiler_eventbus_wireup.py
sentinel-control/services/sentinel-core/tests/perf/sched/__init__.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_backpressure_lifecycle_property.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_runtime_scheduler_wiring.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_non_blocking_property.py
sentinel-control/services/sentinel-core/tests/perf/workspace/__init__.py
sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_delta_semantics.py
```

## Explicitly Not Staged

These required-review files remain unstaged:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

These baseline audit docs remain unstaged:

```text
sentinel-control/docs/BASELINE_PLAN.md
sentinel-control/docs/BASELINE_STAGING_AUDIT.md
sentinel-control/docs/BASELINE_STAGE_PASS1_REPORT.md
```

All browser/organ/full-system-audit dirty files remain excluded.

## Pass 2 Content Review: `shared/events.py`

File:

```text
sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

Decision:

```text
Do not stage as part of Pass 1.
Do not propose whole-file staging as a pure Phase A-D performance-runtime file.
```

Why:

- The file is required by the staged performance modules and tests because they import `sentinel.shared.events`, `AgentEventType`, and `EventBus`.
- The file includes the additive performance event family needed by `sentinel-performance-runtime-foundation`.
- But it is not fully a Phase A-D performance-runtime file. Its docstring identifies `Task 13 / Requirement 13 — Event Bus Primitives Layer Extraction (F-A2.2)`, and it contains the complete shared `AgentPhase`, large existing `AgentEventType` surface, `TraceIntegrityError`, `AgentEvent`, and `EventBus`.
- It also includes many browser, organ, capital, trading, and Brain L4 event names that are broader than the performance-runtime baseline.

Conclusion:

```text
shared/events.py is a required dependency for the staged performance baseline, but not a clean whole-file Phase A-D performance-runtime artifact.
```

Recommended resolution:

1. Either create a separate accepted baseline for the shared event extraction before committing the performance baseline.
2. Or explicitly approve staging `shared/events.py` as a cross-phase dependency even though it is not fully Phase A-D performance-runtime.

Without one of those decisions, the current cached performance baseline is incomplete for a clean checkout because staged perf modules depend on `sentinel.shared.events`.

## Pass 2 Hunk Review: `runtime.py`

File:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
```

Current status:

```text
unstaged
not safe for whole-file staging
```

### Required Performance-Runtime Hunks

Stage only with `git add -p` / split-hunk edit:

```text
Lines around 60-67:
TYPE_CHECKING imports for ContextBuildCache, LLMDecisionFrameCache, PromptFrameCache, TokenBudgetGovernor, CostProfiler, LatencyProfiler, AsyncOrganScheduler, BackpressureController.

Lines around 73-89:
_ToolCallSchedulerAction model for Phase D scheduler routing.

Lines around 107-157:
AgentRuntime constructor optional default-off injections for latency_profiler, cost_profiler, context_build_cache, prompt_frame_cache, decision_frame_cache, token_budget_governor, async_organ_scheduler, backpressure_controller.

Lines around 162-181:
Storage of profiler/cache/scheduler/backpressure injected fields.

Lines around 286-363:
ContextBuildCache integration and LatencyProfiler instrumentation around ContextBuilder.build.

Lines around 369-384:
LatencyProfiler instrumentation around ContextCompressor.compress.

Lines around 1239-1280:
Scheduler path eligibility for local controlled-capability tool calls.

Lines around 1356-1596:
_route_local_tool_call_through_scheduler and related scheduler submission/rejection mapping.

Lines around 1688-1808:
_build_decision_frame_cached, _render_prompt_text_cached, _enforce_frame_budget helper methods.
```

### Excluded Full-System-Audit / Unrelated Hunks

Do not stage into this baseline:

```text
Line around 36:
from sentinel.agent.final_gate import CoreFinalGate

Line around 42:
AgentContext import if used only by memory-not-authority helper.

Lines around 205-210:
CoreFinalGate construction.

Lines around 216-242:
_assert_memory_not_authority_boundary helper.

Lines around 257-273:
Hoisted variables and original_allowed_actions for FinalGate / Memory-not-Authority fallback behavior.

Lines around 387, 411, 428, 447, 535, 624, 660, 805, 932:
Memory-not-authority boundary checks.

Lines around 509, 594, 765, 884, 1030, 1142:
Return-site wrapping with _apply_final_gate.

Lines around 1116-1142:
BLOCKED fallback preservation tied to CoreFinalGate.

Lines around 1811-1889:
_apply_final_gate.
```

### Hunk-Staging Risk

Some imports and nearby line blocks are mixed. This file should not be staged until a manual patch or precise interactive hunk split is performed.

## Pass 2 Hunk Review: `runner.py`

File:

```text
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
```

Current status:

```text
unstaged
not safe for whole-file staging
```

### Required Performance-Runtime Hunks

Stage only with `git add -p` / split-hunk edit:

```text
Lines around 20-24:
TYPE_CHECKING imports for ColdReceiptStore, HotMissionCache, ReceiptIndex, LatencyProfiler.

Lines around 44-48:
MissionRunner constructor optional default-off injections for latency_profiler, hot_cache, cold_store, receipt_index.

Lines around 58-61:
Storage of _latency_profiler, _hot_cache, _cold_store, _receipt_index.

Lines around 89-126:
Profiler start/stop, hot cache set on mission start, hot cache eviction on terminal state.
```

### Excluded Full-System-Audit / Browser Hunks

Do not stage into this baseline:

```text
Line around 9:
CancellationToken import.

Lines around 11-12:
MissionRevokedException and BrowserOperatorRouteRejected imports.

Lines around 70, 87, 136:
cancellation_token parameter propagation.

Lines around 160-177 and 218-232:
reactive revocation polling and MISSION_REVOKED timeline events.

Lines around 261-296:
REVOKED terminal state and success calculation changes.

Lines around 303-330:
_check_revocation helper.

Lines around 333-388:
BrowserOperatorRouteRejected route wrapping and browser route exception structuring.
```

### Hunk-Staging Risk

The `run_mission` wrapper hunk is mixed: profiler/hot-cache logic sits near cancellation-token propagation. This file should not be staged until a manual patch or precise interactive hunk split is performed.

## Recommended Next Commands

Do not run these until the user approves the next pass.

If `shared/events.py` is approved as a cross-phase dependency:

```bash
git add -- sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

For `runtime.py` and `runner.py`, do not whole-file stage:

```bash
git add -p -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git add -p -- sentinel-control/services/sentinel-core/sentinel/mission/runner.py
```

If interactive hunk splitting is too coarse, use a manual patch branch or temporary copy workflow to stage only the performance-runtime hunks.

## Safety Checks Before Any Commit

Run after any approved Pass 2 staging:

```bash
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
git status --short
```

Current check result after Pass 1:

```text
git diff --cached --check
  exit code: 1
  finding: .kiro/specs/sentinel-performance-runtime-foundation/design.md:1153: new blank line at EOF.
```

This should be fixed before any baseline commit, but it was not changed during this pass because this task was staging preparation plus reporting, not spec-file cleanup.

Then from `sentinel-control/services/sentinel-core`:

```bash
python -m pytest tests/perf/ -m "not slow" -q
python -m pytest tests/test_agent_runtime.py -q
```

## Final Verdict

```text
NEEDS_MANUAL_PATCH
```

Reason:

- Pass 1 safe staging is complete.
- `shared/events.py` is required by the staged performance files but is not purely a Phase A-D performance-runtime file.
- `runtime.py` and `runner.py` both require fine-grained hunk staging or a manual patch workflow.
- Committing the current index without resolving `shared/events.py` and the runtime/runner performance hunks would produce an incomplete baseline.
