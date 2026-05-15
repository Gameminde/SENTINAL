# Phase D — Lock Report

**Phase**: D — Async Organ Scheduling
**Date**: 2025 (Phase D closure)
**Verdict**: **LOCKED**

---

## Files changed

### New production modules (`sentinel/perf/sched/`)

- `sentinel-control/services/sentinel-core/sentinel/perf/sched/__init__.py`
- `sentinel-control/services/sentinel-core/sentinel/perf/sched/tool_call_queue.py` — Task 8.1
- `sentinel-control/services/sentinel-core/sentinel/perf/sched/backpressure_controller.py` — Task 8.2
- `sentinel-control/services/sentinel-core/sentinel/perf/sched/batch_execution_planner.py` — Task 8.3
- `sentinel-control/services/sentinel-core/sentinel/perf/sched/async_organ_scheduler.py` — Task 8.4

### New test modules

- `sentinel-control/services/sentinel-core/tests/perf/sched/__init__.py`
- `sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_non_blocking_property.py` — Task 8.5 (Property 9)
- `sentinel-control/services/sentinel-core/tests/perf/sched/test_backpressure_lifecycle_property.py` — Task 8.6 (Property 10)
- `sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_benchmark.py` — Task 8.7 (benchmarks)
- `sentinel-control/services/sentinel-core/tests/perf/sched/test_runtime_scheduler_wiring.py` — Task 8.8 regression

### Modified production modules

- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py` — Task 8.8 wiring:
  - Added optional kwargs `async_organ_scheduler: AsyncOrganScheduler | None = None` and `backpressure_controller: BackpressureController | None = None` to `AgentRuntime.__init__`
  - Added `_ToolCallSchedulerAction` frozen pydantic stub (structural `_OrganActionLike` protocol implementation)
  - Added `_route_local_tool_call_through_scheduler(...)` helper
  - Inserted injection-gated branch in `_execute_controlled_tool_calls` that runs only when BOTH injections are present AND the tool call is non-browser-shaped

### Spec / docs

- `.kiro/specs/sentinel-performance-runtime-foundation/tasks.md` — Phase D markers updated through 8.8
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md` (new)
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md` (this file)

---

## Tests run

### Per-task

```
# Task 8.5 — Property 9 (scheduler non-blocking + outcome events)
pytest tests/perf/sched/test_scheduler_non_blocking_property.py -v --tb=short
→ 6 passed in 19.24s

# Task 8.6 — Property 10 (backpressure lifecycle never expands authority)
pytest tests/perf/sched/test_backpressure_lifecycle_property.py -v --tb=short
→ 5 passed in 3.11s

# Task 8.7 — scheduler benchmarks
pytest tests/perf/sched/test_scheduler_benchmark.py -v -s -m slow --no-header
→ 2 passed in 5.74s
  [8.7 BENCH] submit       p50=0.055 ms p95=0.078 ms p99=0.103 ms (n=100)
  [8.7 BENCH] event_resp   p50=0.089 ms p95=0.119 ms p99=0.212 ms (n=100)

# Task 8.8 — runtime scheduler wiring regression
pytest tests/perf/sched/test_runtime_scheduler_wiring.py -x -v
→ 3 passed
```

### Phase-wide smoke

```
pytest tests/ -m "not slow" -q
→ 1167 passed, 5 deselected
```

The 5 deselected items are the `slow`-marked Phase B and Phase D benchmarks, which run under `-m slow` separately.

---

## Pass / fail counts

| Phase D task | Status | Tests | Pass | Fail | Errors | Skipped |
|---|---|---|---|---|---|---|
| 8.1 ToolCallQueue | ACCEPTABLE | 6 spot-checks | 6 | 0 | 0 | 0 |
| 8.2 BackpressureController | ACCEPTABLE | 7 spot-checks | 7 | 0 | 0 | 0 |
| 8.3 BatchExecutionPlanner | ACCEPTABLE | 7 spot-checks | 7 | 0 | 0 | 0 |
| 8.4 AsyncOrganScheduler | ACCEPTABLE | 6 inline asyncio spot-checks | 6 | 0 | 0 | 0 |
| 8.5 Property 9 (non-blocking + outcome events) | ACCEPTABLE | 6 property tests | 6 | 0 | 0 | 0 |
| 8.6 Property 10 (backpressure lifecycle) | ACCEPTABLE | 5 property tests | 5 | 0 | 0 | 0 |
| 8.7 scheduler benchmarks | ACCEPTABLE | 2 benchmarks | 2 | 0 | 0 | 0 |
| 8.8 runtime scheduler wiring | ACCEPTABLE | 3 regression tests | 3 | 0 | 0 | 0 |
| **Phase D total** | **LOCKED** | **38 task-specific + 1167 smoke** | **all green** | **0** | **0** | **5 deselected (slow benchmarks)** |

---

## Skipped tests

- 5 `pytest.mark.slow`-tagged benchmark tests are deselected from the fast-path run (`-m "not slow"`). They were run separately under `-m slow` and all passed (Task 8.7 benchmarks plus pre-existing Phase B benchmarks).
- No `pytest.mark.skip` is applied to any Phase D test.

---

## Benchmark results

| Benchmark | Canonical budget (p95) | Measured p50 | Measured p95 | Measured p99 | Headroom |
|---|---|---|---|---|---|
| `AsyncOrganScheduler.submit` (Req 7.1, Task 8.7) | ≤ 1.0 ms | 0.055 ms | **0.078 ms** | 0.103 ms | ~12.8× |
| Decision-core event responsiveness with in-flight organ (Req 7.2, Task 8.7) | ≤ 5.0 ms | 0.089 ms | **0.119 ms** | 0.212 ms | ~42× |

Both Phase D performance budgets are met with substantial headroom on the Windows host (`n=100` per benchmark). No `P-D-PERF-XX` deferral required.

---

## Production behavior changed

**YES, but only on the injection-gated path.**

- When BOTH `async_organ_scheduler` and `backpressure_controller` are injected into `AgentRuntime.__init__`, organ-shaped (non-browser) controlled-capability tool calls route through `scheduler.submit(...)`. The scheduler emits ADDITIONAL observability events (`ORGAN_EXECUTION_RECEIPT_RECORDED`, `PERFORMANCE_RECEIPT_RECORDED`, `QUEUE_BACKPRESSURE_APPLIED` on rejection, `KILL_SWITCH_BLOCKED` if the kill-switch is triggered) on top of the existing receipt stream.
- When NEITHER is injected (the default), `AgentRuntime` is **bit-identical** to the pre-Task-8.8 path. Verified by `test_runtime_default_path_executes_controlled_capabilities` and `test_runtime_injected_path_matches_default_receipt_stream` (the latter normalises volatile id-shaped fields and asserts the `ControlledCapabilityResult.model_dump` payloads + the underlying `CONTROLLED_CAPABILITY_*` event sequence match exactly across the two runs).

The default-off contract is structural: absence of injection IS the default-off behaviour. No flag defaults on for tests but off for prod.

---

## Authority expansion

**NO.**

- `BackpressureController.check_submission` clamps every emitted bound to `min(configured_bound, envelope.max_actions)` for every key (Property 10 Test 1, 200 examples).
- The scheduler's synthetic `OrganAuthorityEnvelope` (built inside `_route_local_tool_call_through_scheduler`) is sourced **exclusively** from the mission envelope's `allowed_actions` / `allowed_tools` / `allowed_paths` / `max_actions` / `max_cost_usd`. Never widened.
- Property 10 enforces `bounds_used[k] <= envelope.max_actions` on every decision in 200 examples × 4 tests.

---

## Raw secret leakage observed

**NO.**

- `_ToolCallSchedulerAction` carries only short identifier strings (`action_id`, `mission_id`, `organ_id`, `action_type`). Frozen pydantic with `extra="forbid"`. No tool-call arguments, no payload bytes, no credentials.
- `OrganDryRunReceipt.preview` (built in the helper) carries only `{tool_id, action}` strings.
- `BackpressureController` enforces a strict payload whitelist on every event:
  - `QUEUE_BACKPRESSURE_APPLIED` payload keys = `{organ_type, queue_depth, estimated_wait_ms, reason}`
  - `QUEUE_BACKPRESSURE_CLEARED` payload keys = `{organ_type, queue_depth}`
  - Property 10 Test 4 asserts strict equality (not subset) on 200 examples. Any future widening of these payloads will fail the property test.
- `PerformanceReceipt` construction (Phase A) re-runs the canonical `sanitize_context_text` on every string field; rejects `raw_secret_leakage=True` writes.

---

## Open backlog items kept open

Per Phase D entry direction from the user:

- **P-B-PERF-01** — `ColdReceiptStore.persist` canonical p95 ≤ 10ms proof on Linux/macOS (Phase B caveat). Open. Not affected by Phase D.
- **P-C-RUNTIME-01** — Wire `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor` into real decision-core call sites. Open. Not affected by Phase D.
- **P-C-KEY-01** — Replace `envelope.id` stand-in with canonical four-component composite key for `ContextBuildCache`. Open. Not affected by Phase D.

New Phase D backlog items (see `PHASE_D_BACKLOG.md`):

- **P-D-RUNTIME-01** — Wire mission-level `OrganKillSwitch` table into `_route_local_tool_call_through_scheduler` so a triggered kill-switch can propagate to routed calls without monkey-patching. Currently the helper builds a non-triggered switch from the mission envelope; the regression test in Task 8.8 monkey-patches the helper to verify the scheduler's enforcement. The runtime cannot **source** a triggered switch from production code today.
- **P-D-BATCH-01** — Replace per-call `asyncio.run(_drive())` with a shared event loop or `submit_batch` API. Performance optimisation; correctness already correct.
- **P-D-BROWSER-01** — Route browser-shaped tool calls through `AsyncOrganScheduler`. Currently excluded by `scheduler_path_eligible` guard. Scope expansion, not correctness.

None of these block Phase E start. Phase D's correctness contracts (non-blocking submit, outcome-event correctness, kill-switch / authority enforcement, backpressure-never-expands-authority, payload whitelists, default-off bit-identical wiring) are all proven by property + regression tests.

---

## Phase verdict

**LOCKED**.

All eight Phase D tasks (8.1–8.8) carry an ACCEPTABLE Mini Subtask Review. All required validation tasks (`*` — 8.5 Property 9, 8.6 Property 10, 8.7 benchmarks) pass at canonical settings on the Windows host. The required runtime wiring (Task 8.8) is implemented under a default-off / injection-gated contract with bit-identical observable behaviour in the default path, verified by a 1167-test smoke suite plus a dedicated three-test regression file. No authority expansion. No raw-secret leakage. No production behaviour change in the default path. Three backlog items (P-D-RUNTIME-01, P-D-BATCH-01, P-D-BROWSER-01) are documented as scope-expansion / production-sourcing improvements that do not invalidate Phase D's correctness guarantees.

Phase E is allowed to start. Phase E rules apply: same mini-review discipline, no Run All Tasks globally, no closure of P-B-PERF-01 / P-C-RUNTIME-01 / P-C-KEY-01 / P-D-RUNTIME-01 / P-D-BATCH-01 / P-D-BROWSER-01 during Phase E.
