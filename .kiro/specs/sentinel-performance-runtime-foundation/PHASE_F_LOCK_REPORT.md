# Phase F Lock Report - Benchmark / Regression Gates

Date: 2026-05-16

Spec: `sentinel-performance-runtime-foundation`

## Final Verdict

Phase F = LOCKED

Phase F implements benchmark/regression gates with deterministic local golden
mission runners, completed gate evaluation, pytest hot-path coverage gate, and
CoreFinalGate PerformanceReceipt mission-close invariant verification. The
full-lock benchmark run completed all four golden mission classes with
`min_iterations=30` and passed p95/p99 gates.

## Phase F Task Status

| Task | Status | Notes |
| --- | --- | --- |
| 11.1 Define GoldenMission classes and budgets | ACCEPTABLE | Defines `startup`, `single_tool`, `multi_tool`, `browser_heavy` with exact budget constants and `min_iterations >= 30`. |
| 11.2 Implement `BenchmarkHarness.run` | ACCEPTABLE | Runs each golden mission through deterministic local default runners or injected runners for tests; computes p50/p95/p99 and marks `passed=True` only after gates pass. |
| 11.3 Implement `BenchmarkHarness.evaluate_gates` | ACCEPTABLE | Evaluates completed reports only; returns in-progress verdict for incomplete runs; no benchmark execution inside gate evaluation. |
| 11.4 Property test for benchmark-gate semantics | ACCEPTABLE | Hypothesis covers completed and in-progress reports, exact p95/p99 tolerance boundaries, and regression entry shape. |
| 11.5 Unit tests for golden-mission enumeration and budgets | ACCEPTABLE | Confirms names, min iteration floor, exact budget constants, and hot-path coverage relationship. |
| 11.6 Hot-path module registry and CI gate | ACCEPTABLE | Defines hot-path module registry and a pytest merge-gate test that fails when a hot-path module lacks golden mission coverage. |
| 11.7 CoreFinalGate PerformanceReceipt invariants only | ACCEPTABLE | Adds minimal `CoreFinalGate.verify_performance_receipts(...)` and mission-close evaluation for supplied `AgentRunResult.performance_receipts`; checks authority, secret-leakage marker, and hash invariants only. |

## Files Changed

Phase F files:

- `sentinel-control/services/sentinel-core/sentinel/perf/bench/golden_missions.py`
- `sentinel-control/services/sentinel-core/sentinel/perf/bench/golden_runners.py`
- `sentinel-control/services/sentinel-core/sentinel/perf/bench/harness.py`
- `sentinel-control/services/sentinel-core/sentinel/perf/bench/hot_path_registry.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/__init__.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_benchmark_harness_run.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_benchmark_harness_gates.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_benchmark_harness_gate_property.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_core_final_gate_performance_receipts.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_golden_missions.py`
- `sentinel-control/services/sentinel-core/tests/perf/bench/test_hot_path_registry.py`
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_F_LOCK_REPORT.md`

Cross-cutting dependency touched in Phase F:

- `sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/models.py`

Phase F uses `AgentRunResult.performance_receipts` as the mission-close boundary
for supplied `PerformanceReceipt` objects. No latency budget evaluation was
added to `CoreFinalGate`.

## Tests Run

Required commands:

```bash
python -m pytest tests/perf/bench -q
```

Result: passed. Latest targeted run confirmed:

```text
30 passed
```

```bash
python -m pytest tests/perf/ -m "not slow" -q
```

Result: passed. Latest required run confirmed:

```text
177 selected tests passed; 6 slow tests remained deselected by marker.
```

```bash
python -m pytest tests/test_agent_runtime.py -q
```

Result: passed. Latest required run confirmed:

```text
14 tests passed.
```

Diff hygiene:

```bash
git diff --check -- sentinel-control/services/sentinel-core/sentinel/perf/bench sentinel-control/services/sentinel-core/tests/perf/bench
```

Result: passed, no output.

```bash
git diff --check -- sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
```

Result: passed. Git emitted only the existing line-ending warning:

```text
warning: in the working copy of 'sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py', LF will be replaced by CRLF the next time Git touches it
```

Staging check:

```bash
git diff --cached --name-only
```

Result: no staged files.

## Benchmark / Gate Behavior Summary

- Golden mission classes exist for `startup`, `single_tool`, `multi_tool`, and `browser_heavy`.
- Budgets are deterministic constants:
  - `startup`: p50 150 ms, p95 400 ms, p99 800 ms
  - `single_tool`: p50 200 ms, p95 500 ms, p99 1000 ms
  - `multi_tool`: p50 400 ms, p95 1000 ms, p99 2000 ms
  - `browser_heavy`: p50 800 ms, p95 2000 ms, p99 4000 ms
- `BenchmarkHarness.run` uses deterministic local default runners for the four golden mission classes and still allows injected runners for tests.
- `BenchmarkHarness.run` sets `passed=True` only after `evaluate_gates(...)` passes.
- `BenchmarkHarness.evaluate_gates` does not run benchmarks.
- Incomplete reports return an in-progress verdict and do not falsely fail.
- Completed reports fail p95 only when measured p95 is more than 10 percent over budget.
- Completed reports fail p99 only when measured p99 is more than 15 percent over budget.
- Regression entries include metric, mission class, measured value, budget value, and overage percent.
- `CoreFinalGate` does not evaluate latency budgets, benchmark regressions, golden mission budgets, or model cost optimization.

## Safety / Runtime Impact

Production behavior changed: no existing production path changed. Phase F adds
new benchmark modules and an additive `CoreFinalGate.verify_performance_receipts`
helper for callers that explicitly supply `PerformanceReceipt` objects.

Authority expansion: no.

Raw secret leakage observed: no.

Benchmark correctness risk: no for the implemented structural gate semantics.
Production benchmark proof remains unclaimed until real golden mission runners
are added.

No platform multiplier was introduced.

No silent budget relaxation was introduced.

No old backlog item was closed.

## Open Backlog Items Still Open

- `P-B-PERF-01` - ColdReceiptStore.persist Linux/macOS canonical p95 proof.
- `P-B-PERF-02` - ArtifactRefStore.get Linux/macOS proof or honest budget revision.
- `P-C-RUNTIME-01` - Wire LLMDecisionFrameCache, PromptFrameCache, and TokenBudgetGovernor into real decision-core call sites.
- `P-C-KEY-01` - Replace envelope.id stand-in with the true four-component composite key.
- `P-D-RUNTIME-01` - Mission kill-switch table sourcing.
- `P-D-BATCH-01` - Shared event loop / batch dispatch performance.
- `P-D-BROWSER-01` - Route browser organ paths through scheduler.

## New Phase F Backlog

No new Phase F backlog remains after the full-lock pass.

Closed in this full-lock pass:

- `P-F-RUNNER-01` - closed by deterministic local golden mission runners for
  `startup`, `single_tool`, `multi_tool`, and `browser_heavy`.
- `P-F-CI-01` - closed by the pytest hot-path coverage gate under
  `tests/perf/bench/test_hot_path_registry.py`; no external workflow change was
  needed for this repo state.

## Lock Notes

This phase is fully locked for the current spec. It provides deterministic
local golden mission runners, gate evaluation semantics, property coverage,
hot-path coverage gate tests, and minimal PerformanceReceipt FinalGate
mission-close validation. It does not close Phase B/C/D backlog items.

## Full-Lock Benchmark Evidence

Recorded: 2026-05-16 21:56:36 UTC / 2026-05-16 23:56:36 +02:00.

Gate result: pass.

Total iterations: 120.

| Golden mission | Iterations | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| `startup` | 30 | 12 | 17 | 27 |
| `single_tool` | 30 | 3 | 4 | 4 |
| `multi_tool` | 30 | 1 | 1 | 2 |
| `browser_heavy` | 30 | 35 | 51 | 57 |
