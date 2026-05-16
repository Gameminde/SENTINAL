# Performance Runtime Foundation A-F Handoff

Recorded at: 2026-05-16 16:45:28 +02:00

Branch: `main`

HEAD: `eddaecb` (`eddaecbb36a202fff18db12f40e41186d097eec3`)

Remote status: local `main` is ahead of `origin/main` by 1 commit.

## Scope

This handoff closes preparation for the
`sentinel-performance-runtime-foundation` work through Phase F. It does not
start a new phase and does not implement any backlog item.

## What Phase A-F Delivered

Phase A - Measurement Foundation:

- `PerformanceTrace`
- `PerformanceReceipt`
- `LatencyProfiler`
- `CostProfiler`
- performance EventBus events
- runtime/mission instrumentation

Phase B - Hot/Cold State Foundation:

- `HotMissionCache`
- SQLite-backed `ColdReceiptStore`
- `ReceiptIndex`
- atomic receipt/index transaction design
- `ArtifactRefStore`
- `DeltaStateEngine`
- `CacheInvalidationPolicy`
- MissionRunner hot/cold/receipt wiring

Phase C - Cache / Context / Prompt Foundation:

- `ContextBuildCache`
- `PromptFrameCache`
- `LLMDecisionFrameCache`
- `TokenBudgetGovernor`
- `ModelCallOptimizer`
- partial runtime adoption with known open runtime/key backlog

Phase D - Async Organ Scheduling:

- `ToolCallQueue`
- `BackpressureController`
- `BatchExecutionPlanner`
- `AsyncOrganScheduler`
- default-off AgentRuntime scheduler/backpressure wiring

Phase E - Workspace Delta / Snapshot Foundation:

- `WorkspaceChangeWatcher`
- `WorkspaceDelta`
- `WorkspaceSnapshotCache`
- deterministic snapshot IDs
- delta application semantics
- cache invalidation propagation

Phase F - Benchmark / Regression Gates:

- `GoldenMission` classes and budgets
- `BenchmarkHarness.run`
- `BenchmarkHarness.evaluate_gates`
- Property 14 benchmark-gate tests
- golden mission enumeration/budget tests
- hot-path module registry and coverage gate
- minimal `CoreFinalGate.verify_performance_receipts(...)`
- `PHASE_F_LOCK_REPORT.md`

## What Was Committed

Baseline A-E:

```text
7aaecb1 - baseline: lock performance runtime foundation phases A-E
```

README status update:

```text
daa4625 - docs: update project readme status
```

Phase F:

```text
eddaecb - perf: add benchmark regression gates foundation
```

## What Remains Dirty In The Worktree

The worktree is not clean. Remaining dirty files include:

- `sentinel-control/docs/CURRENT_STATE_LOCK.md` updated for closure prep in the current uncommitted step.
- `sentinel-control/docs/PERFORMANCE_RUNTIME_A_F_HANDOFF.md` created in the current uncommitted step.
- `sentinel-control/docs/POST_PHASE_F_DIRTY_TREE_REPORT.md` created in the current uncommitted step.
- pre-existing browser/organ/full-system-audit tracked modifications under `sentinel-control/services/sentinel-core/sentinel/agent/`, `sentinel-control/services/sentinel-core/sentinel/organs/`, and related tests.
- untracked browser organ migration files under `sentinel-control/services/sentinel-core/sentinel/organs/browser/`.
- baseline planning report docs under `sentinel-control/docs/BASELINE_*`.
- temporary/generated files: `sentinel-control/services/sentinel-core/_junit.xml` and `sentinel-control/services/sentinel-core/_tmp_cold_store_smoke.py`.

See `sentinel-control/docs/POST_PHASE_F_DIRTY_TREE_REPORT.md` for the detailed classification.

## Open Backlog

The following items remain open and must not be silently closed:

```text
P-B-PERF-01
P-B-PERF-02
P-C-RUNTIME-01
P-C-KEY-01
P-D-RUNTIME-01
P-D-BATCH-01
P-D-BROWSER-01
P-F-RUNNER-01
P-F-CI-01
```

## What Must NOT Be Claimed

Do not claim:

- Phase B full performance lock.
- Phase C full runtime adoption.
- Phase F production benchmark proof.
- Real golden mission runners exist.
- CI gate is wired into repository CI.
- P-C-KEY-01 is closed because Phase E exists.
- P-B-PERF-01 or P-B-PERF-02 are closed without Linux/macOS proof or accepted budget revision.
- Browser/organ/full-system-audit dirty tree is resolved.
- Brain/Science research has started.
- Consensus.ai research has started.

## Recommended Next Options

A. Close technical backlog:

- Address P-B, P-C, P-D, and P-F backlog intentionally.
- Keep each closure scoped and separately reviewed.

B. Clean browser/organ/full-system-audit dirty tree:

- Classify whether remaining modifications belong to the full-system audit,
  browser organ migration, or should be reverted/parked.
- Do not mix this with performance-runtime commits.

C. Plan Brain/Science research:

- Create a separate planning phase only after the dirty tree/backlog strategy is accepted.

D. Plan Consensus.ai research:

- Treat as a separate research workstream, not a continuation of Phase F.

## Closure Warning

Do not start new architecture work until dirty tree and backlog strategy are accepted.

No new phase started.

Brain/Science research not started.

Consensus.ai research not started.
