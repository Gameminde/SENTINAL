# Phase F Lock Report - Benchmark / Regression Gates

Date: 2026-05-16

Spec: `sentinel-performance-runtime-foundation`

## Final Verdict

Phase F = STRUCTURAL LOCK

Phase F implemented the benchmark/regression gate foundation and all targeted
verification commands passed. This is not claimed as production benchmark proof:
`BenchmarkHarness` uses injected iteration runners and no real golden mission
runner suite has been wired yet.

## Phase F Task Status

| Task | Status | Notes |
| --- | --- | --- |
| 11.1 Define GoldenMission classes and budgets | ACCEPTABLE | Defines `startup`, `single_tool`, `multi_tool`, `browser_heavy` with exact budget constants and `min_iterations >= 30`. |
| 11.2 Implement `BenchmarkHarness.run` | ACCEPTABLE | Runs each golden mission through an injected runner for required iterations and computes p50/p95/p99. No fake default runner. |
| 11.3 Implement `BenchmarkHarness.evaluate_gates` | ACCEPTABLE | Evaluates completed reports only; returns in-progress verdict for incomplete runs; no benchmark execution inside gate evaluation. |
| 11.4 Property test for benchmark-gate semantics | ACCEPTABLE | Hypothesis covers completed and in-progress reports, exact p95/p99 tolerance boundaries, and regression entry shape. |
| 11.5 Unit tests for golden-mission enumeration and budgets | ACCEPTABLE | Confirms names, min iteration floor, exact budget constants, and hot-path coverage relationship. |
| 11.6 Hot-path module registry and CI gate | ACCEPTABLE | Defines hot-path module registry and a gate helper that fails when a hot-path module lacks golden mission coverage. |
| 11.7 CoreFinalGate PerformanceReceipt invariants only | ACCEPTABLE | Adds minimal `CoreFinalGate.verify_performance_receipts(...)` for authority, secret-leakage marker, and hash invariants only. |

## Files Changed

Phase F files:

- `sentinel-control/services/sentinel-core/sentinel/perf/bench/golden_missions.py`
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

Note: `final_gate.py` already had unrelated/pre-existing dirty changes in the
working tree. Phase F added only the minimal PerformanceReceipt verifier surface.

## Tests Run

Required commands:

```bash
python -m pytest tests/perf/bench -q
```

Result: passed. Expanded counter run confirmed:

```text
26 passed in 11.39s
```

```bash
python -m pytest tests/perf/ -m "not slow" -q
```

Result: passed. Expanded counter run confirmed:

```text
173 passed, 6 deselected in 162.58s (0:02:42)
```

```bash
python -m pytest tests/test_agent_runtime.py -q
```

Result: passed. Expanded counter run confirmed:

```text
14 passed in 13.54s
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
- `BenchmarkHarness.run` requires an injected iteration runner and computes percentiles after all required iterations finish.
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

- `P-F-RUNNER-01` - Add real golden mission runners before claiming production
  benchmark proof. Current `BenchmarkHarness` intentionally requires injected
  iteration runners and should be described as benchmark/regression gate
  foundation.
- `P-F-CI-01` - Wire the hot-path coverage assertion and benchmark gate into
  the repository's actual CI workflow once the CI entrypoint is selected.

## Lock Notes

This phase is structurally complete for benchmark configuration, gate
evaluation semantics, property coverage, and minimal PerformanceReceipt
FinalGate invariant validation. It is not a full production benchmark lock
because golden mission execution is not yet backed by real mission runners.
