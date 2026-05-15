# Phase B — Final Lock Report (Amended)

**Verdict:** Phase B = **STRUCTURAL LOCK / PERFORMANCE CAVEAT ACCEPTED**.
**Phase C:** allowed to start.

The architectural and correctness blockers from the previous review (no-fake-atomicity, property-test gaps, full-scale benchmark scope) are all closed. One performance proof remains deferred and is tracked as backlog item P-B-PERF-01.

## Status by sub-task

| Task | Status | Notes |
|------|--------|-------|
| 4.1 HotMissionCache | LOCKED | bounds + same-tick eviction + overflow→receipt-id |
| 4.2 ColdReceiptStore (SQLite-backed, Option A) | LOCKED | SQLite WAL is the durable WAL; `persist_in_transaction` exposes the coupling point |
| 4.3 Cold-store durability property test | LOCKED | 5/5 passed (round-trip, persist failure → None + event + no orphan, transaction atomicity, no partial state after rollback, KeyError on unknown id) |
| 4.4 ReceiptIndex true atomic coupling | LOCKED | shares the `ColdReceiptStore` connection; receipt INSERT + index INSERT in a single `BEGIN IMMEDIATE`/`COMMIT` |
| 4.5 ReceiptIndex query + atomicity property test | LOCKED | 7/7 passed (single-dim, all compound shapes, INSERT failure rollback, COMMIT failure rollback, health_check, unsupported shape concrete + Hypothesis) |
| 4.6 ArtifactRefStore | LOCKED | SHA-256 keying, dedup, integrity check on read, sanitization gate for text+llm_exposable only |
| 4.7 Artifact property test | LOCKED | 6/6 passed (round-trip, dedup, oversize rejection, secret-pattern rejection, binary bypass, integrity error) |
| 4.8 DeltaStateEngine | LOCKED | bounds-check before mutation; `AUTHORITY_VIOLATION` on rejection; prior state preserved |
| 4.9 CacheInvalidationPolicy | LOCKED | dependency-graph BFS invalidation, TTL bounds, bulk warning |
| 4.10 Hot/cold size bounds property test | LOCKED | 3/3 passed |
| 4.11 Phase B benchmarks (full scale) | **PARTIAL — PERF CAVEAT** | see below |
| 4.12 MissionRunner + organs/receipts wiring | LOCKED | additive optional params, default-off, bit-identical when not injected |

## Benchmark results

| Benchmark | Canonical budget | Result | Status |
|-----------|------------------|--------|--------|
| `ReceiptIndex.query` p95 @ 100k rows | ≤ 5 ms | **3.5 ms** (Windows) | CANONICAL PASS ✅ |
| `ArtifactRefStore.get` p95 @ 10k artifacts | ≤ 5 ms | **1.75 ms** (Windows) | CANONICAL PASS ✅ |
| `ColdReceiptStore.persist` p95 | ≤ 10 ms | **16.4 ms** (Windows, NTFS, SQLite `synchronous=FULL`) | DEFERRED / NOT CANONICALLY PROVEN ⚠️ |

### Performance caveat — explicit

- The Windows measurement (16.4 ms p95) is recorded honestly. It is **not** a canonical pass.
- The 5x platform multiplier exists in the test file for CI stability **only**; it does **not** count as a canonical lock pass and is documented as a platform note in the test output.
- The remaining gap is a performance-budget proof, **not** a correctness blocker. Atomicity, authority enforcement, receipt integrity, sanitization, and rollback semantics are all proven by property tests under Option A.
- The user has explicitly accepted this caveat to unblock Phase C. Linux/macOS canonical proof is deferred to backlog item P-B-PERF-01.

### What is NOT claimed

- ❌ Phase B full performance lock.
- ❌ Canonical `persist` p95 ≤ 10 ms.
- ❌ Platform multiplier as a canonical pass.

### What IS claimed

- ✅ Atomicity architecture (Option A — true ACID coupling) is locked.
- ✅ All property tests for hot/cold storage pass.
- ✅ Two of three Phase B benchmarks pass canonically.
- ✅ Operational latency on the user's measured Windows host is sufficient for the current Sentinel runtime; correctness, authority, safety, receipt integrity, and atomicity are unaffected.

## Files added / modified during Phase B

**New files:**
- `sentinel/perf/hot_cold/hot_mission_cache.py`
- `sentinel/perf/hot_cold/cold_receipt_store.py` (SQLite-backed, Option A)
- `sentinel/perf/hot_cold/receipt_index.py` (shares cold-store SQLite connection)
- `sentinel/perf/hot_cold/artifact_ref_store.py`
- `sentinel/perf/hot_cold/delta_state_engine.py`
- `sentinel/perf/hot_cold/cache_invalidation_policy.py`
- `tests/perf/hot_cold/test_cold_receipt_store_property.py`
- `tests/perf/hot_cold/test_receipt_index_property.py`
- `tests/perf/hot_cold/test_artifact_ref_store_property.py`
- `tests/perf/hot_cold/test_hot_cold_bounds_property.py`
- `tests/perf/hot_cold/test_phase_b_benchmarks.py`
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LINUX_RUNBOOK.md`
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md`
- `.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md` (this file)

**Modified files:**
- `sentinel/mission/runner.py` — additive optional `hot_cache`, `cold_store`, `receipt_index` params; default-off bit-identical behavior when not injected
- `sentinel/organs/receipts.py` — additive optional `cold_store`, `receipt_index` params on `planned_only` / `started`; `_persist_receipt_to_cold` helper
- `sentinel/shared/events.py` — 22 additive event-type members (Phase A)
- `sentinel-control/services/sentinel-core/pyproject.toml` — registered `pytest.mark.slow`

## Production behavior changed
**No.** All Phase B integration is gated behind `if self._hot_cache is not None:` / `if ... is not None:` guards. Default constructor values are `None`. When not injected, code paths are bit-identical to pre-Phase-B behavior.

## Authority expansion
**No.** `DeltaStateEngine` explicitly *prevents* authority expansion by rejecting deltas that exceed envelope bounds and emitting `AUTHORITY_VIOLATION`.

## Raw secret leakage observed
**No.** `ArtifactRefStore` applies `sanitize_context_text` only for text+llm_exposable artifacts. Receipt classes enforce sanitization at construction. Error strings in events truncated to 200 chars.

## Final verdict

**Phase B = STRUCTURAL LOCK / PERFORMANCE CAVEAT ACCEPTED.**
**Phase C = ALLOWED TO START.**

The atomicity contract is genuine; no fake atomicity remains. The performance caveat is documented openly, recorded as backlog P-B-PERF-01, and not masked under any platform multiplier or budget revision.
