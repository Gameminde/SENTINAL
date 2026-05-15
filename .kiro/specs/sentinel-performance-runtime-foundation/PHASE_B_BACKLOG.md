# Phase B — Post-Lock Backlog

Items deferred from Phase B that do not block Phase C.

---

## P-B-PERF-01 — `ColdReceiptStore.persist` canonical p95 proof on Linux/macOS

**Status:** Open
**Priority:** Medium (performance proof, not a correctness blocker)
**Owner:** Sentinel runtime team
**Created:** Phase B closure

### Context

Phase B Task 4.11 set a canonical performance budget of `ColdReceiptStore.persist` p95 ≤ 10 ms. The Windows measurement under SQLite `synchronous=FULL` on NTFS produced p95 ≈ 16.4 ms. Windows NTFS `fsync` overhead is the primary driver (15–40 ms per fsync is typical). The Linux/macOS canonical proof was deferred at user direction to unblock Phase C.

This caveat does **not** affect correctness, authority, safety, receipt integrity, or the atomicity coupling between `ColdReceiptStore` and `ReceiptIndex`. Those are all proven by property tests under Option A.

### Acceptance criteria (any one of)

1. **Original budget confirmed.** Run the Phase B benchmark suite on a Linux host (ext4 / xfs / btrfs) or macOS host (apfs). Measured `ColdReceiptStore.persist` p95 < 10 ms. Update `PHASE_B_LOCK_REPORT.md` with the result, mark P-B-PERF-01 closed.
2. **Budget revised honestly with measured evidence.** If Linux/macOS also exceeds 10 ms, revise the canonical budget in `tasks.md` Task 4.11 and `design.md` Phase B targets to a number that matches the measured cost of fsync-on-every-commit durability. Justification must include the measured p50/p95/p99 across ≥3 platforms (e.g. Linux ext4, macOS apfs, Windows NTFS) and a rationale paragraph. Requires user approval.
3. **Safe tuning or batching closes the gap.**
   - **Tuning examples that preserve durability:** raise `PRAGMA mmap_size`, raise `PRAGMA cache_size`, pre-allocate WAL via `PRAGMA wal_autocheckpoint`. Must keep `PRAGMA synchronous=FULL` semantics or be explicitly justified as still durable across application crash and OS crash.
   - **Batching:** expose an opt-in `persist_batch(receipts)` API that wraps a logical batch of receipts in a single SQLite transaction. The single-receipt `persist` contract is unchanged; batching is caller-driven only.
   - Re-measure on Linux/macOS after the tuning/batching change. Apply rule 1 or rule 2 to the new measurements.

### Forbidden resolutions (explicit)

- ❌ Hide the failure under a platform multiplier and call it a canonical pass.
- ❌ Drop `synchronous=FULL` to `synchronous=NORMAL` silently.
- ❌ Skip the Linux/macOS measurement.
- ❌ Declare "canonical pass" using only the Windows measurement.

### Repro instructions

See `PHASE_B_LINUX_RUNBOOK.md` for the exact command, environment-context capture, and report format.

### Notes

The `pytest.mark.slow` marker is registered in `sentinel-control/services/sentinel-core/pyproject.toml`; the Phase B benchmark suite is gated behind that marker so it stays out of fast-path test runs.


---

## P-B-PERF-02 — `ArtifactRefStore.get` canonical p95 proof on Linux/macOS

**Status:** Open
**Priority:** Medium (performance proof, not a correctness blocker)
**Owner:** Sentinel runtime team
**Created:** Phase E closure (surfaced while running the full `slow` benchmark suite)

### Context

Phase B Task 4.11 set a canonical performance budget of `ArtifactRefStore.get` p95 ≤ 5 ms at the 10k-artifact scale. The Windows measurement on this host (NTFS, default SQLite/filesystem stack) produces:

```
[Benchmark] ArtifactRefStore.get @ 10,000 artifacts / 100 gets:
  p50: 11.190 ms
  p95: 13.934 ms  (>= 5 ms budget; FAIL)
  p99: 20.783 ms
```

This caveat is the same class of Windows wall-clock / fsync variance as `P-B-PERF-01` covers for `ColdReceiptStore.persist`. The `ArtifactRefStore.get` benchmark was not surfaced at original Phase B closure because the failing run was masked by selective benchmark execution. It surfaced honestly during the Phase E final regression run (`pytest tests/perf/ -m slow`).

This caveat does **not** affect correctness, authority, safety, receipt integrity, or atomicity. The Phase B property tests for artifact round-trip / dedup / integrity / sanitization all pass. The remaining issue is a performance-budget proof, not a correctness blocker.

### Acceptance criteria (any one of)

1. **Original budget confirmed.** Run the Phase B benchmark suite on a Linux host (ext4 / xfs / btrfs) or macOS host (apfs). Measured `ArtifactRefStore.get` p95 < 5 ms. Update `PHASE_B_LOCK_REPORT.md` with the result, mark P-B-PERF-02 closed.
2. **Budget revised honestly with measured evidence.** If Linux/macOS also exceeds 5 ms at the 10k-artifact scale, revise the canonical budget in `tasks.md` Task 4.11 and `design.md` Phase B targets to match measured cost. Justification must include p50/p95/p99 across ≥3 platforms and a rationale paragraph. Requires user approval.
3. **Safe tuning closes the gap.** Tuning options that preserve correctness/integrity:
   - Cache the on-disk artifact handle/inode so repeated reads avoid re-traversing the directory layer.
   - Switch the per-read SHA-256 verification to a streaming-hash-against-stored-digest path that early-exits on mismatch.
   - Add an opt-in `get_unverified(content_hash)` API for callers that have already verified the artifact in this process; the verifying `get` remains the canonical safe API. Both APIs ship; integrity property tests cover both.
   - Re-measure on Linux/macOS after the tuning. Apply rule 1 or rule 2 to the new measurements.

### Forbidden resolutions (explicit)

- ❌ Hide the failure under a platform multiplier and call it a canonical pass.
- ❌ Drop SHA-256 integrity verification on the read path silently.
- ❌ Skip the Linux/macOS measurement.
- ❌ Declare "canonical pass" using only the Windows measurement.

### Repro instructions

```
cd sentinel-control/services/sentinel-core
python -m pytest tests/perf/hot_cold/test_phase_b_benchmarks.py::test_artifact_get_p95_full_scale_10k -v -s -m slow
```

### Notes

This finding does NOT block Phase E lock. Phase E's own 4 tasks (10.1 watcher, 10.2 snapshot cache, 10.3 unit tests, 10.4 warm-update benchmark) all pass on this Windows host with the warm-update p95 measured at 5.756 ms (~9× headroom under the 50 ms budget). Phase E and Phase B are independently graded.

P-B-PERF-01 and P-B-PERF-02 should be closed together when the Linux/macOS Phase B benchmark suite is run.
