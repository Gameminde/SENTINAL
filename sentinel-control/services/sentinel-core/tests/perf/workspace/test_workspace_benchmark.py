# Feature: sentinel-performance-runtime-foundation, Phase E Task 10.4: workspace warm-update benchmark
"""Phase E Task 10.4 benchmark — ``WorkspaceSnapshotCache`` warm-update p95.

**Validates: performance targets table — Workspace snapshot warm-update**
(p50 20 ms / p95 50 ms / fail >55 ms).

This module measures the latency of
``WorkspaceSnapshotCache.apply_delta`` against a *warm* (already
populated) snapshot. It is the standalone latency floor for the warm
realistic-workspace path; the production-grade
``BenchmarkHarness`` integration (LatencyProfiler + chain-integrity
sweep + CI gate) lands in Phase F and is not the responsibility of
this task.

Methodology
-----------
1. Build a single ``EventBus`` + ``CacheInvalidationPolicy`` +
   ``WorkspaceSnapshotCache`` trio. The policy receives the cache's
   ``put``/``invalidate`` calls so the warm-update path exercises the
   *full* realistic chain (snapshot mutation → policy invalidation
   → policy ``put`` of the new snapshot generation).
2. Pre-populate the cache with ``N=1000`` files via 1000 ``CREATED``
   deltas. Paths are deterministic
   (``f"src/module_{i // _FILES_PER_MODULE:04d}/file_{i %
   _FILES_PER_MODULE:03d}.py"``) so the benchmark is byte-reproducible
   across runs and platforms. Pre-population is **NOT** measured.
3. Run 100 measured iterations, each issuing one ``MODIFIED`` delta
   against a randomly-selected pre-existing path. The selector uses a
   fixed ``random.Random(42)`` so the path choice sequence is
   reproducible. Each iteration changes ``mtime_ns``, ``size``, and
   ``content_sha256`` so the snapshot composition genuinely moves and
   both the per-path invalidate AND the snapshot-generation
   invalidate+put fire — i.e. the full realistic warm-update path.
4. Time each iteration with ``time.perf_counter_ns()`` immediately
   before and after ``cache.apply_delta(delta)``.
5. Compute p50, p95, p99 from the 100 nanosecond samples; print
   ``[10.4 BENCH] warm_update p50=X ms p95=Y ms p99=Z ms (n=100)``.
6. Assert ``p95 <= 50.0`` ms (canonical budget from the Performance
   Targets table).

Strict rules honoured
---------------------
* Module-level ``pytestmark = pytest.mark.slow`` mirrors the Phase B
  (``test_phase_b_benchmarks.py``) and Phase D
  (``test_scheduler_benchmark.py``) precedents. The ``slow`` marker is
  registered in ``pyproject.toml``.
* No ``LatencyProfiler`` instrumentation — Phase F's
  ``BenchmarkHarness`` will own that integration. This bench measures
  wall-clock only.
* No ``time.time``, no ``time.sleep`` — only ``time.perf_counter_ns``.
* No real filesystem I/O. The benchmark exercises the in-memory
  ``WorkspaceSnapshotCache`` only; ``WorkspaceChangeWatcher`` and the
  deferred fs-watcher backend are not on the measured path.
* No production module is modified.
* No new dependencies. No Hypothesis (the Phase D benchmark precedent
  uses a deterministic seed; this bench follows that contract).
* Synthetic ``mtime_ns``/``size``/``content_sha256`` values per
  iteration so the snapshot mutates non-trivially and the invalidate
  chain is exercised faithfully.
* A single warmup iteration primes any first-call asyncio/JIT
  overhead and is discarded from the latency series.

How to run
----------
::

    pytest tests/perf/workspace/test_workspace_benchmark.py \\
        -v -s -m slow --tb=short

If the ``slow`` filter is omitted the benchmark still runs (the
marker is purely declarative).
"""

from __future__ import annotations

import hashlib
import random
import time

import pytest

from sentinel.perf.hot_cold.cache_invalidation_policy import (
    CacheInvalidationPolicy,
)
from sentinel.perf.workspace.workspace_change_watcher import WorkspaceDelta
from sentinel.perf.workspace.workspace_snapshot_cache import (
    WorkspaceSnapshotCache,
)
from sentinel.shared.events import EventBus

# Mark all tests in this module as "slow" so they can be filtered via -m slow.
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p10_bench_10_4"

# Realistic warm workspace size — 1000 files spread across 20 modules of 50
# files each. Both factors are kept stable so the path strings are
# byte-reproducible across runs and platforms.
_WARM_FILE_COUNT = 1000
_FILES_PER_MODULE = 50
assert _WARM_FILE_COUNT % _FILES_PER_MODULE == 0, (
    "warm file count must divide evenly into modules so the path "
    "generator produces exactly _WARM_FILE_COUNT unique paths."
)
_MODULE_COUNT = _WARM_FILE_COUNT // _FILES_PER_MODULE  # 20

# Iteration count. Phase D precedent (``test_scheduler_benchmark.py``) uses
# 100; we follow that for percentile resolution under a sub-100 ms budget.
_MEASURED_ITERATIONS = 100

# Canonical budget from the Performance Targets table —
# Workspace snapshot warm-update p95.
_WARM_UPDATE_P95_BUDGET_MS = 50.0

# Fixed RNG seed so path selection during the measured loop is
# reproducible across runs.
_RNG_SEED = 42

# Synthetic-content prefix for content_sha256 derivation. The prefix
# guarantees a content hash that does not collide with any pre-population
# hash and varies per iteration so the snapshot composition genuinely
# moves on each MODIFIED.
_ITER_HASH_PREFIX = "iter_"

# Sentinel index used for the warmup MODIFIED. Negative-namespaced so it
# can never collide with a measured-iteration's hash domain.
_WARMUP_HASH_TAG = "warmup"


# ---------------------------------------------------------------------------
# Path + delta builders
# ---------------------------------------------------------------------------


def _path_for_index(i: int) -> str:
    """Deterministic path for the ``i``-th file in the warm workspace.

    With ``_WARM_FILE_COUNT=1000`` and ``_FILES_PER_MODULE=50`` this
    yields 20 modules × 50 files = 1000 unique POSIX paths of the form
    ``src/module_0000/file_000.py`` … ``src/module_0019/file_049.py``.
    The forward-slash form matches ``WorkspaceSnapshotCache``'s
    canonical key normalization (``Path(...).as_posix()``).
    """
    if i < 0 or i >= _WARM_FILE_COUNT:
        raise ValueError(
            f"path index {i} out of range [0, {_WARM_FILE_COUNT})"
        )
    module = i // _FILES_PER_MODULE
    file = i % _FILES_PER_MODULE
    return f"src/module_{module:04d}/file_{file:03d}.py"


def _content_sha256_for_iter(tag: str) -> str:
    """SHA-256 hex digest of ``f"iter_{tag}".encode()``.

    Used to give every measured iteration a unique content hash so the
    snapshot mutation is non-trivial and the cached ``snapshot_id``
    actually moves — which in turn forces the policy's
    invalidate-prior + put-new chain to fire (the realistic warm-update
    path being benchmarked).
    """
    return hashlib.sha256(f"{_ITER_HASH_PREFIX}{tag}".encode()).hexdigest()


def _build_created_delta(index: int) -> WorkspaceDelta:
    """Construct a CREATED delta for the ``index``-th pre-populated file.

    The metadata triple is derived from ``index`` so pre-population is
    deterministic, and so the *initial* content_sha256 set is disjoint
    from the per-iteration measured hashes (different prefix domain).
    """
    path = _path_for_index(index)
    # Use a "init_" prefix so pre-population hashes never collide with the
    # measured-iteration hashes (which use the "iter_" prefix). This makes
    # every MODIFIED in the measured loop a true content change.
    initial_hash = hashlib.sha256(f"init_{index}".encode()).hexdigest()
    return WorkspaceDelta(
        type="CREATED",
        path=path,
        previous_path=None,
        mtime_ns=index + 1,  # > 0, monotonically increasing
        size=(index + 1) * 100,
        content_sha256=initial_hash,
        detected_at_ns=index + 1,
    )


def _build_modified_delta(
    *,
    path: str,
    iteration_tag: str,
    iteration_counter: int,
) -> WorkspaceDelta:
    """Construct a MODIFIED delta with synthetic per-iteration metadata.

    ``iteration_counter`` drives ``mtime_ns`` and ``size`` so each
    measured iteration produces a unique metadata triple — guaranteeing
    the snapshot composition moves and the policy's
    invalidate-prior + put-new chain fires. ``iteration_tag`` is the
    domain-string fed into the content hash; it is the loop counter for
    measured iterations and ``_WARMUP_HASH_TAG`` for the single warmup.
    """
    # The CacheInvalidationPolicy treats `mtime_ns` as a non-negative int;
    # offset by `_WARM_FILE_COUNT` so measured-iteration mtimes never
    # accidentally coincide with the pre-population mtimes (1..1000).
    mtime_ns = _WARM_FILE_COUNT + iteration_counter + 1
    size = (iteration_counter + 1) * 100
    return WorkspaceDelta(
        type="MODIFIED",
        path=path,
        previous_path=None,
        mtime_ns=mtime_ns,
        size=size,
        content_sha256=_content_sha256_for_iter(iteration_tag),
        detected_at_ns=mtime_ns,
    )


# ---------------------------------------------------------------------------
# Percentile + summary helpers (mirrors Phase D pattern)
# ---------------------------------------------------------------------------


def _percentile_ns(sorted_values: list[int], pct: float) -> int:
    """p-th percentile from a pre-sorted ascending list of nanosecond values."""
    if not sorted_values:
        return 0
    idx = int(len(sorted_values) * pct / 100.0)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


def _summarise_warm_update(
    latencies_ns: list[int],
    *,
    canonical_budget_ms: float,
) -> tuple[float, float, float]:
    """Sort, compute p50/p95/p99 (ms), and print the ``[10.4 BENCH]`` line.

    Returns ``(p50_ms, p95_ms, p99_ms)`` for assertion use.
    """
    latencies_ns = sorted(latencies_ns)
    p50_ms = _percentile_ns(latencies_ns, 50) / 1_000_000.0
    p95_ms = _percentile_ns(latencies_ns, 95) / 1_000_000.0
    p99_ms = _percentile_ns(latencies_ns, 99) / 1_000_000.0
    n = len(latencies_ns)
    print(
        f"\n[10.4 BENCH] warm_update "
        f"p50={p50_ms:.3f} ms p95={p95_ms:.3f} ms p99={p99_ms:.3f} ms (n={n})"
    )
    print(f"  Canonical budget: {canonical_budget_ms:.1f} ms (p95)")
    return p50_ms, p95_ms, p99_ms


# ---------------------------------------------------------------------------
# Benchmark: workspace snapshot warm-update p95 ≤ 50 ms
# ---------------------------------------------------------------------------


def test_workspace_snapshot_warm_update_p95_under_50ms() -> None:
    """``WorkspaceSnapshotCache.apply_delta(MODIFIED)`` warm-update p95 ≤ 50 ms.

    Validates the Performance Targets table line "Workspace snapshot
    warm-update — p50 20 ms / p95 50 ms / fail >55 ms" for the
    in-memory snapshot path. See the module docstring for the full
    methodology.
    """
    # ------------------------------------------------------------------
    # Setup — single trio for the whole benchmark.
    # ------------------------------------------------------------------
    bus = EventBus(mission_id=_MISSION_ID)
    policy = CacheInvalidationPolicy(event_bus=bus)
    cache = WorkspaceSnapshotCache(invalidation_policy=policy)

    # ------------------------------------------------------------------
    # Pre-population — N CREATED deltas. NOT measured.
    # ------------------------------------------------------------------
    for i in range(_WARM_FILE_COUNT):
        cache.apply_delta(_build_created_delta(i))

    # Sanity: the cache is populated to the expected size.
    populated_files = cache.files()
    assert len(populated_files) == _WARM_FILE_COUNT, (
        f"benchmark setup error: expected {_WARM_FILE_COUNT} populated "
        f"files, got {len(populated_files)}"
    )

    # ------------------------------------------------------------------
    # Warmup — one MODIFIED on a path that is then re-MODIFIED in the
    # measured loop without trouble (each iteration uses a fresh
    # content hash, so no idempotent-no-op risk). Discarded from the
    # latency series. Primes:
    #   * any first-call hashlib / pydantic-validator JIT overhead,
    #   * the policy's TTL bookkeeping for the workspace_snapshot
    #     category (the first put on that category warms the
    #     timestamp/dep maps).
    # ------------------------------------------------------------------
    rng = random.Random(_RNG_SEED)
    warmup_index = rng.randrange(_WARM_FILE_COUNT)
    cache.apply_delta(
        _build_modified_delta(
            path=_path_for_index(warmup_index),
            iteration_tag=_WARMUP_HASH_TAG,
            # Use a counter outside the measured-iteration domain so
            # mtime_ns/size do not collide with any measured value.
            iteration_counter=-1,
        )
    )

    # ------------------------------------------------------------------
    # Measured loop — 100 iterations of MODIFIED on random paths.
    # ------------------------------------------------------------------
    warm_update_latencies_ns: list[int] = []

    for iteration in range(_MEASURED_ITERATIONS):
        path_index = rng.randrange(_WARM_FILE_COUNT)
        path = _path_for_index(path_index)
        delta = _build_modified_delta(
            path=path,
            iteration_tag=str(iteration),
            iteration_counter=iteration,
        )

        start_ns = time.perf_counter_ns()
        cache.apply_delta(delta)
        elapsed_ns = time.perf_counter_ns() - start_ns

        warm_update_latencies_ns.append(elapsed_ns)

    # ------------------------------------------------------------------
    # Sanity + summary + assertion.
    # ------------------------------------------------------------------
    assert len(warm_update_latencies_ns) == _MEASURED_ITERATIONS, (
        f"expected {_MEASURED_ITERATIONS} samples, got "
        f"{len(warm_update_latencies_ns)}"
    )

    # The cache must still be at the original size — MODIFIED never adds
    # or removes paths, so the warm-workspace invariant must hold.
    assert len(cache.files()) == _WARM_FILE_COUNT, (
        f"warm-update should preserve file count; cache has "
        f"{len(cache.files())} files, expected {_WARM_FILE_COUNT}"
    )

    _, p95_ms, _ = _summarise_warm_update(
        warm_update_latencies_ns,
        canonical_budget_ms=_WARM_UPDATE_P95_BUDGET_MS,
    )

    assert p95_ms <= _WARM_UPDATE_P95_BUDGET_MS, (
        f"WorkspaceSnapshotCache.apply_delta(MODIFIED) warm-update p95 = "
        f"{p95_ms:.3f} ms exceeds the {_WARM_UPDATE_P95_BUDGET_MS:.1f} ms "
        f"canonical budget (Performance Targets table — Workspace "
        f"snapshot warm-update)."
    )
