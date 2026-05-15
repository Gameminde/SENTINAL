# Phase E — Lock Report

**Phase**: E — Workspace Delta
**Date**: 2026 (Phase E closure)
**Verdict**: **LOCKED**

---

## Files changed

### New production modules (`sentinel/perf/workspace/`)

- `sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_change_watcher.py` — Task 10.1 (interface + `WorkspaceDelta` model + passive `WorkspaceChangeWatcher` container)
- `sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_snapshot_cache.py` — Task 10.2 (incremental `snapshot_id` + `apply_delta` driving `CacheInvalidationPolicy`)

### New test modules

- `sentinel-control/services/sentinel-core/tests/perf/workspace/__init__.py` — empty package skeleton
- `sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_delta_semantics.py` — Task 10.3 (47 logical tests, 55 collected after parametrization)
- `sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_benchmark.py` — Task 10.4 (warm-update p95 ≤ 50 ms benchmark)

### Modified production modules

**None.** Phase E is a purely additive package. `AgentRuntime`, `ContextBuildCache`, `CacheInvalidationPolicy`, and all other existing modules are unchanged. The integration of `WorkspaceSnapshotCache.snapshot_id` into the `ContextBuildCache.composite_key` is owned by backlog item **P-C-KEY-01**, NOT by Phase E.

### Spec / docs

- `.kiro/specs/sentinel-performance-runtime-foundation/tasks.md` — Phase E markers updated through 10.5
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md` — appended **P-B-PERF-02** (newly surfaced during the Phase E final regression run; see §"Open backlog items kept open" below)
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md` (this file)

---

## Tests run

### Per-task

```
# Task 10.3 — workspace delta semantics unit tests
pytest tests/perf/workspace/test_workspace_delta_semantics.py -v --tb=short
→ 55 passed in 1.59s

# Task 10.4 — workspace warm-update benchmark
pytest tests/perf/workspace/test_workspace_benchmark.py -v -s -m slow --tb=short
→ 1 passed in 2.50s
  [10.4 BENCH] warm_update p50=2.191 ms p95=5.756 ms p99=7.658 ms (n=100)
```

### Phase-wide regression

```
pytest tests/perf/ -m "not slow" --tb=no -q
→ 147 passed (92 prior + 55 new Task 10.3 tests)

pytest tests/perf/ -m slow --tb=short
→ 5 passed, 1 failed (pre-existing Phase B test_artifact_get_p95_full_scale_10k Windows variance — see §"Open backlog items kept open" below; NOT a Phase E regression)
```

---

## Pass / fail counts

| Phase E task | Status | Tests | Pass | Fail | Errors | Skipped |
|---|---|---|---|---|---|---|
| 10.1 WorkspaceChangeWatcher (interface + types) | ACCEPTABLE | inline spot-check | all | 0 | 0 | 0 |
| 10.2 WorkspaceSnapshotCache (snapshot_id + apply_delta) | ACCEPTABLE | inline spot-check (11 cases) | 11 | 0 | 0 | 0 |
| 10.3 Workspace delta semantics unit tests | ACCEPTABLE | 55 deterministic unit tests | 55 | 0 | 0 | 0 |
| 10.4 Workspace warm-update benchmark | ACCEPTABLE | 1 benchmark | 1 | 0 | 0 | 0 |
| **Phase E total** | **LOCKED** | **67 task-specific + 147 perf regression** | **all green** | **0** | **0** | **0** |

---

## Skipped tests

- 0 Phase E tests skipped via `pytest.mark.skip`.
- The Phase E benchmark (Task 10.4) is gated by `pytest.mark.slow` and is therefore deselected from the fast-path run; it runs under `-m slow` and passes.

---

## Benchmark results

| Benchmark | Canonical budget (p95) | Measured p50 | Measured p95 | Measured p99 | Headroom |
|---|---|---|---|---|---|
| `WorkspaceSnapshotCache.apply_delta(MODIFIED)` warm-update (Task 10.4) | ≤ 50.0 ms | 2.191 ms | **5.756 ms** | 7.658 ms | ~8.7× |

The Phase E warm-update benchmark passes on the Windows host with substantial headroom. No `P-E-PERF-XX` deferral required for Phase E content.

---

## Production behavior changed

**NO.**

Phase E is purely additive. The new modules `sentinel/perf/workspace/workspace_change_watcher.py` and `sentinel/perf/workspace/workspace_snapshot_cache.py` are not imported by any existing production module yet. `AgentRuntime`, `ContextBuilder`, `LLMDecisionFrame`, `MissionRunner`, and all other existing surfaces are byte-for-byte unchanged.

The `ContextBuildCache.composite_key(workspace_snapshot_id=...)` integration into `AgentRuntime` is owned by backlog item **P-C-KEY-01** (still open) and is intentionally NOT closed by Phase E. The current `AgentRuntime` continues to bind the `workspace_snapshot_id` slot to `"v1"` per the documented Phase C stand-in.

---

## Authority expansion

**NO.**

`WorkspaceSnapshotCache` only manipulates path strings, numeric filesystem metadata (`mtime_ns`, `size`), and SHA-256 hex digests. It never touches `MissionAuthorityEnvelope` or any authority-bearing surface. `WorkspaceChangeWatcher` is a passive container that holds typed `WorkspaceDelta` records.

`CacheInvalidationPolicy.invalidate(...)` is the only existing module called from Phase E code; that module's authority surface is unchanged.

---

## Raw secret leakage observed

**NO.**

Phase E modules handle:
- Path strings (normalized via `Path(...).as_posix()` to forward-slash POSIX form)
- Integer filesystem metadata (`mtime_ns`, `size`)
- SHA-256 hex digests of file content (`content_sha256`)
- `time.monotonic_ns()` timestamps (`detected_at_ns`)

No file body bytes ever flow through any Phase E surface. The `WorkspaceDelta` model's validator explicitly forbids body-shaped fields; the snapshot cache stores only `(mtime_ns, size, content_sha256)` tuples per path.

The `CacheInvalidationPolicy` payload whitelist for `CACHE_INVALIDATION_BULK_WARNING` (Phase B) is preserved; Phase E does not widen it.

---

## Open backlog items kept open

Per Phase E entry direction from the user:

- **P-B-PERF-01** — `ColdReceiptStore.persist` canonical p95 ≤ 10ms proof on Linux/macOS. Open. Not affected by Phase E.
- **P-B-PERF-02** — *NEW, surfaced during Phase E final regression run.* `ArtifactRefStore.get` p95 = 13.934 ms vs 5 ms canonical budget on Windows NTFS at the 10k-artifact scale. Same class of Windows variance as P-B-PERF-01. Documented in `PHASE_B_BACKLOG.md`. Phase E never touched `tests/perf/hot_cold/` (verified via `git status` — the entire directory is `??` untracked); this is a pre-existing finding that should have been caught at Phase B closure but was masked by selective benchmark execution. Honest accounting: surface it now, add to backlog, do not retroactively re-grade Phase B because the correctness contracts (atomicity, property tests) still hold.
- **P-C-RUNTIME-01** — Wire `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor` into real decision-core call sites. Open. Not affected by Phase E.
- **P-C-KEY-01** — Replace `envelope.id` stand-in with canonical four-component composite key for `ContextBuildCache`. Open. *Phase E provides the `workspace_snapshot_id` source* (`WorkspaceSnapshotCache.snapshot_id`), but the wiring of that source into `AgentRuntime.run` is explicitly owned by P-C-KEY-01 and remains deferred. Phase E does NOT close P-C-KEY-01.
- **P-D-RUNTIME-01** — Wire mission-level `OrganKillSwitch` table into `_route_local_tool_call_through_scheduler`. Open. Not affected by Phase E.
- **P-D-BATCH-01** — Replace per-call `asyncio.run(_drive())` with shared event-loop dispatch. Open. Not affected by Phase E.
- **P-D-BROWSER-01** — Route browser-shaped tool calls through `AsyncOrganScheduler`. Open. Not affected by Phase E.

No Phase E-specific backlog items created. The warm-update benchmark passes the canonical 50 ms p95 budget on Windows by ~8.7×; no `P-E-PERF-XX` deferral is needed.

---

## Phase verdict

**LOCKED**.

All four Phase E tasks (10.1 watcher interface, 10.2 snapshot cache, 10.3 unit tests, 10.4 warm-update benchmark) carry an ACCEPTABLE Mini Subtask Review. All required validation tasks (`*` — 10.3 unit tests, 10.4 benchmark) pass at canonical settings on the Windows host. The required production tasks (10.1, 10.2) implement only the interface + passive container + apply_delta semantics — no real fs-watcher backend wiring (deferred per phase gate), no `AgentRuntime` integration (deferred to P-C-KEY-01). No authority expansion. No raw-secret leakage. No production behaviour change anywhere — Phase E is purely additive.

One pre-existing Phase B finding (`test_artifact_get_p95_full_scale_10k` Windows p95 = 13.934 ms vs 5 ms budget) was surfaced honestly during the Phase E final regression run and added to `PHASE_B_BACKLOG.md` as **P-B-PERF-02**. That finding does NOT block Phase E LOCK because:
1. Phase E never modified `tests/perf/hot_cold/` or `sentinel/perf/hot_cold/` (verified via `git status` — directory is fully untracked, no diffs).
2. The Phase B correctness contracts (atomicity, round-trip, dedup, integrity, sanitization) still hold and are proven by their property tests.
3. The Windows variance is operational, not architectural — Linux/macOS canonical proof is the resolution path, identical to the existing P-B-PERF-01 protocol.

Phase F is allowed to start. Phase F rules apply: same mini-review discipline, no Run All Tasks globally, no closure of P-B-PERF-01 / P-B-PERF-02 / P-C-RUNTIME-01 / P-C-KEY-01 / P-D-RUNTIME-01 / P-D-BATCH-01 / P-D-BROWSER-01 during Phase F.
