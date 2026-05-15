# Feature: sentinel-performance-runtime-foundation, Property 7: ReceiptIndex query semantics and atomicity (Option A — true atomic lock)
"""Property-based test for ``ReceiptIndex`` query semantics and persist+index atomicity.

**Validates: Requirements 5.1, 5.2, 5.3 (cap — 5 ms p95 benchmark in BenchmarkHarness),
5.4 (indexed compound shapes), 5.5, 5.6, 5.7, 5.8 (under Option A — true atomic lock).**

Phase B Refactor — Option A. The :class:`ReceiptIndex` shares the
:class:`ColdReceiptStore` SQLite connection. The new constructor signature is
``ReceiptIndex(*, event_bus, cold_store)`` (no ``db_path``, all keyword-only).

What this test covers
---------------------
1. ``test_query_semantics_single_dim`` — corpus of 1–30 receipts persisted via
   ``index.persist_and_index``; for each supported single-dimension shape
   (``mission_id``, ``organ_id``, ``action_type``, ``entity_path``,
   ``content_hash``) results match in-memory filtered ground truth, sorted by
   ``ts_ns DESC``, truncated to limit, zero-match returns ``[]``.
2. ``test_query_semantics_compound_shapes`` — covers ALL supported indexed
   compound shapes: ``mission_id + timestamp_range``, ``organ_id +
   action_type``, ``entity_path + mission_id``. Closes Blocker 2 of the prior
   review (compound shapes were untested).
3. ``test_atomicity_under_index_insert_failure`` — Option A coupling proof.
   Inject ``sqlite3.OperationalError`` on the ``INSERT INTO receipt_index``
   step (NOT on the receipts insert). After the failure: ref is ``None``,
   ``COLD_STORE_PERSISTENCE_FAILED`` with ``stage="atomic_persist_and_index"``
   is emitted, and BOTH the ``receipts`` row and the ``receipt_index`` row are
   absent — the receipt INSERT was unwound by the same transaction's
   ``ROLLBACK``.
4. ``test_atomicity_under_commit_failure`` — same coupling proof, failing on
   the literal ``"COMMIT"`` SQL execution. Same post-conditions.
5. ``test_health_check_returns_zero_under_atomic_lock`` — after N successful
   ``persist_and_index`` calls, ``health_check()`` returns 0. A deliberately
   bypass-inserted index row (no matching ``receipts`` row) is detected and
   ``RECEIPT_INDEX_INCONSISTENCY`` with tag ``"health_check"`` is emitted.
6. ``test_unsupported_shape_raises`` — ``query(mission_id="x", organ_id="y")``
   raises ``ValueError``; a Hypothesis-driven variant draws random unsupported
   non-empty dimension subsets and asserts the same.

Failure injection (tests 3 and 4)
---------------------------------
SQLite's ``Connection.execute`` is read-only and cannot be monkey-patched
directly. We wrap the live connection in a proxy that intercepts ``execute``
based on a SQL predicate and passes every other attribute through via
``__getattr__``. We swap ``index._conn`` (and therefore the connection that
``cold_store.persist_in_transaction`` receives via ``conn=self._conn``) to
the proxy for one ``persist_and_index`` call, restore it afterwards, and
inspect the underlying real connection via ``cold_store.connection``.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.hot_cold.cold_receipt_store import ColdReceiptStore
from sentinel.perf.hot_cold.receipt_index import ReceiptIndex
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import (
    PerformanceSeverity,
    PerformanceTrace,
)
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import new_id


# ---------------------------------------------------------------------------
# Receipt factory
# ---------------------------------------------------------------------------


def _make_receipt(
    *,
    mission_id: str = "m",
    organ_id: str | None = None,
    action_type: str = "a",
    ts: datetime | None = None,
) -> PerformanceReceipt:
    """Build a valid :class:`PerformanceReceipt` with metadata overrides."""
    trace = PerformanceTrace(
        action_id=new_id("act"),
        mission_id=mission_id,
        organ_id=organ_id,
        action_type=action_type,
        queue_wait_ms=0,
        wall_ms=10,
        cpu_ms=5,
        bytes_in=100,
        bytes_out=50,
        tokens_in=20,
        tokens_out=10,
        cache_hit=0,
        cache_miss=1,
        organ_latency_ms=0,
        model_prefill_decode_ms=0,
        error=False,
        error_category=None,
        severity=PerformanceSeverity.INFO,
    )
    return PerformanceReceipt(
        mission_id=mission_id,
        action_id=trace.action_id,
        organ_id=organ_id,
        action=action_type,
        trace=trace,
        estimated_cost_usd=Decimal("0.001000"),
        model_id="test-model",
        budget_remaining=900,
        budget_limit=1000,
        cache_type=None,
        backpressure_reason=None,
        queue_depth_at_receipt=None,
        deadline_ms=None,
        elapsed_ms=None,
        authority_expansion=False,
        raw_secret_leakage=False,
        created_at=ts or datetime.now(UTC),
    )


def _datetime_from_us(microseconds: int) -> datetime:
    """Create a UTC datetime from microseconds since epoch (preserves precision)."""
    return datetime.fromtimestamp(microseconds / 1_000_000, tz=UTC)


def _ts_ns_from_datetime(dt: datetime) -> int:
    """Convert datetime to nanoseconds the same way ``_extract_ts_ns`` does.

    Matches ``int(created_at.timestamp() * 1_000_000_000)`` exactly so the
    in-memory ground-truth ``ts_ns`` aligns with what
    :meth:`ReceiptIndex.persist_and_index` writes to the index row.
    """
    return int(dt.timestamp() * 1_000_000_000)


# ---------------------------------------------------------------------------
# Connection proxy for failure injection
# ---------------------------------------------------------------------------


class _ConnExecuteProxy:
    """Proxy a :class:`sqlite3.Connection` and intercept ``execute`` calls.

    All other attributes are passed through via ``__getattr__`` so callers
    that touch e.g. ``.commit()`` or ``.cursor()`` see the real connection.
    The proxy is swapped into ``index._conn`` for the duration of one
    ``persist_and_index`` call and restored afterwards so the underlying
    connection is unaffected for inspection.
    """

    def __init__(
        self,
        real: sqlite3.Connection,
        *,
        fail_predicate: Callable[[str], bool],
        error: Exception,
    ) -> None:
        self._real = real
        self._fail_predicate = fail_predicate
        self._error = error

    def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
        if self._fail_predicate(sql):
            raise self._error
        return self._real.execute(sql, parameters)

    def __getattr__(self, name: str) -> Any:
        # Called only for attributes not found on the proxy itself.
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_MISSION_POOL = ("mission_a", "mission_b", "mission_c")
_ORGAN_POOL: tuple[str | None, ...] = ("organ_x", "organ_y", "organ_z", None)
_ACTION_POOL = ("read", "write", "execute", "query")
_ENTITY_POOL: tuple[str | None, ...] = ("/path/a", "/path/b", "/path/c", None)
_HASH_POOL: tuple[str | None, ...] = ("hash_aaa", "hash_bbb", "hash_ccc", None)


@st.composite
def _receipt_corpus_st(draw: st.DrawFn) -> list[dict[str, Any]]:
    """Generate a corpus of 1–30 receipt-spec dicts with unique microsecond timestamps."""
    n = draw(st.integers(min_value=1, max_value=30))
    base_us = 1_577_836_800_000_000  # 2020-01-01 UTC
    span_us = 315_360_000_000_000  # ~10 years
    ts_values = sorted(
        draw(
            st.lists(
                st.integers(min_value=base_us, max_value=base_us + span_us),
                min_size=n,
                max_size=n,
                unique=True,
            )
        )
    )
    corpus: list[dict[str, Any]] = []
    for i in range(n):
        corpus.append(
            {
                "mission_id": draw(st.sampled_from(_MISSION_POOL)),
                "organ_id": draw(st.sampled_from(_ORGAN_POOL)),
                "action_type": draw(st.sampled_from(_ACTION_POOL)),
                "entity_path": draw(st.sampled_from(_ENTITY_POOL)),
                "content_hash": draw(st.sampled_from(_HASH_POOL)),
                "ts_us": ts_values[i],
            }
        )
    return corpus


# ---------------------------------------------------------------------------
# Helpers used by every test
# ---------------------------------------------------------------------------


def _persist_corpus(
    index: ReceiptIndex, corpus: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Persist every entry in ``corpus`` and return the in-memory ground truth."""
    ground_truth: list[dict[str, Any]] = []
    for entry in corpus:
        ts_dt = _datetime_from_us(entry["ts_us"])
        actual_ts_ns = _ts_ns_from_datetime(ts_dt)
        receipt = _make_receipt(
            mission_id=entry["mission_id"],
            organ_id=entry["organ_id"],
            action_type=entry["action_type"],
            ts=ts_dt,
        )
        ref = index.persist_and_index(
            receipt,
            entity_path=entry["entity_path"],
            content_hash=entry["content_hash"],
        )
        assert ref is not None, "persist_and_index should succeed for fresh ids"
        ground_truth.append(
            {
                "receipt_id": receipt.id,
                "mission_id": entry["mission_id"],
                "organ_id": entry["organ_id"],
                "action_type": entry["action_type"],
                "entity_path": entry["entity_path"],
                "content_hash": entry["content_hash"],
                "ts_ns": actual_ts_ns,
            }
        )
    return ground_truth


def _expected_ids(filtered: list[dict[str, Any]], limit: int = 1000) -> list[str]:
    """Sort filtered entries by ``ts_ns DESC`` and truncate to ``limit``."""
    return [
        e["receipt_id"]
        for e in sorted(filtered, key=lambda e: e["ts_ns"], reverse=True)[:limit]
    ]


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(corpus=_receipt_corpus_st())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_query_semantics_single_dim(corpus: list[dict[str, Any]]) -> None:
    """Single-dimension query results match in-memory filtered ground truth.

    **Validates: Requirements 5.1, 5.5, 5.6**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_query_single")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)

        try:
            ground_truth = _persist_corpus(index, corpus)

            # mission_id alone
            for mid in {e["mission_id"] for e in ground_truth}:
                expected = _expected_ids(
                    [e for e in ground_truth if e["mission_id"] == mid]
                )
                assert index.query(mission_id=mid) == expected

            # organ_id alone (only non-None values are queryable as a dimension)
            for oid in {
                e["organ_id"] for e in ground_truth if e["organ_id"] is not None
            }:
                expected = _expected_ids(
                    [e for e in ground_truth if e["organ_id"] == oid]
                )
                assert index.query(organ_id=oid) == expected

            # action_type alone
            for at in {e["action_type"] for e in ground_truth}:
                expected = _expected_ids(
                    [e for e in ground_truth if e["action_type"] == at]
                )
                assert index.query(action_type=at) == expected

            # entity_path alone
            for ep in {
                e["entity_path"] for e in ground_truth if e["entity_path"] is not None
            }:
                expected = _expected_ids(
                    [e for e in ground_truth if e["entity_path"] == ep]
                )
                assert index.query(entity_path=ep) == expected

            # content_hash alone
            for ch in {
                e["content_hash"]
                for e in ground_truth
                if e["content_hash"] is not None
            }:
                expected = _expected_ids(
                    [e for e in ground_truth if e["content_hash"] == ch]
                )
                assert index.query(content_hash=ch) == expected

            # Zero-match returns []
            assert index.query(mission_id="__never_persisted__") == []

            # Truncation to limit (5.6 / 5.3-cap-shape)
            if ground_truth:
                first_mid = ground_truth[0]["mission_id"]
                full = _expected_ids(
                    [e for e in ground_truth if e["mission_id"] == first_mid]
                )
                if len(full) > 1:
                    one = index.query(mission_id=first_mid, limit=1)
                    assert one == full[:1]
        finally:
            cold_store.close()


@given(corpus=_receipt_corpus_st())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_query_semantics_compound_shapes(corpus: list[dict[str, Any]]) -> None:
    """All supported indexed compound shapes match AND-filtered ground truth.

    **Validates: Requirement 5.4 (indexed compound shapes)**

    Covers every compound shape declared by ``ReceiptIndex._SUPPORTED_SHAPES``:

    * ``mission_id + timestamp_range``
    * ``organ_id + action_type``
    * ``entity_path + mission_id``
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_query_compound")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)

        try:
            ground_truth = _persist_corpus(index, corpus)

            # ---- mission_id + timestamp_range -------------------------------
            ts_values = sorted({e["ts_ns"] for e in ground_truth})
            # Probe several ranges: full span, lower half, upper half, empty,
            # single-point exact.
            spans: list[tuple[int, int]] = []
            if ts_values:
                lo, hi = ts_values[0], ts_values[-1]
                spans.append((lo, hi + 1))  # inclusive of all
                mid_idx = len(ts_values) // 2
                spans.append((lo, ts_values[mid_idx] + 1))  # lower half
                spans.append((ts_values[mid_idx], hi + 1))  # upper half
                spans.append((hi + 1_000_000, hi + 2_000_000))  # empty future
                spans.append((ts_values[0], ts_values[0] + 1))  # single-point

            for mid in {e["mission_id"] for e in ground_truth}:
                for ts_start, ts_end in spans:
                    filtered = [
                        e
                        for e in ground_truth
                        if e["mission_id"] == mid
                        and ts_start <= e["ts_ns"] < ts_end
                    ]
                    expected = _expected_ids(filtered)
                    actual = index.query(
                        mission_id=mid, timestamp_range=(ts_start, ts_end)
                    )
                    assert actual == expected, (
                        f"mission_id+timestamp_range mismatch: mid={mid} "
                        f"range=({ts_start},{ts_end}) "
                        f"expected={expected} got={actual}"
                    )

            # ---- organ_id + action_type -------------------------------------
            organ_action_pairs = {
                (e["organ_id"], e["action_type"])
                for e in ground_truth
                if e["organ_id"] is not None
            }
            for oid, at in organ_action_pairs:
                filtered = [
                    e
                    for e in ground_truth
                    if e["organ_id"] == oid and e["action_type"] == at
                ]
                expected = _expected_ids(filtered)
                actual = index.query(organ_id=oid, action_type=at)
                assert actual == expected, (
                    f"organ_id+action_type mismatch: oid={oid} at={at} "
                    f"expected={expected} got={actual}"
                )

            # ---- entity_path + mission_id -----------------------------------
            entity_mission_pairs = {
                (e["entity_path"], e["mission_id"])
                for e in ground_truth
                if e["entity_path"] is not None
            }
            for ep, mid in entity_mission_pairs:
                filtered = [
                    e
                    for e in ground_truth
                    if e["entity_path"] == ep and e["mission_id"] == mid
                ]
                expected = _expected_ids(filtered)
                actual = index.query(entity_path=ep, mission_id=mid)
                assert actual == expected, (
                    f"entity_path+mission_id mismatch: ep={ep} mid={mid} "
                    f"expected={expected} got={actual}"
                )
        finally:
            cold_store.close()


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_atomicity_under_index_insert_failure(seed: int) -> None:
    """Failure on ``INSERT INTO receipt_index`` rolls back the receipt row too.

    **Validates: Requirement 5.2 (single-transaction commit-or-rollback),
    Requirement 5.5 (no orphan index entries), Requirement 5.7 (diagnostic
    event emission).**

    This is the Option A coupling proof: the receipt INSERT happens FIRST in
    the transaction; injecting a failure on the *subsequent* index INSERT
    must roll the receipt row back as well.
    """
    del seed  # only used to drive Hypothesis shrink/diversification
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_atom_index")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)

        try:
            receipt = _make_receipt(
                mission_id="mission_failtest",
                organ_id="organ_x",
                action_type="write",
            )

            real_conn = index._conn
            proxy = _ConnExecuteProxy(
                real_conn,
                fail_predicate=lambda sql: sql.lstrip().startswith(
                    "INSERT INTO receipt_index"
                ),
                error=sqlite3.OperationalError(
                    "injected index insert failure"
                ),
            )

            # Swap connection for one call.
            index._conn = proxy  # type: ignore[assignment]
            try:
                ref = index.persist_and_index(
                    receipt, entity_path="/p", content_hash="h"
                )
            finally:
                index._conn = real_conn

            # 1. ref is None
            assert ref is None, (
                "persist_and_index must return None when the atomic transaction"
                " is rolled back"
            )

            # 2. Diagnostic event emitted with the right stage tag.
            failures = [
                ev
                for ev in event_bus.events()
                if ev.event_type
                == AgentEventType.COLD_STORE_PERSISTENCE_FAILED
            ]
            assert failures, (
                "COLD_STORE_PERSISTENCE_FAILED must be emitted on rollback"
            )
            last = failures[-1]
            assert last.payload["stage"] == "atomic_persist_and_index", (
                f"stage mismatch: {last.payload!r}"
            )
            assert last.payload["receipt_id"] == receipt.id

            # 3. NO row in receipts table for that id.
            row = real_conn.execute(
                "SELECT 1 FROM receipts WHERE receipt_id = ?", (receipt.id,)
            ).fetchone()
            assert row is None, (
                "receipts row must be rolled back together with the index row"
            )

            # 4. NO row in receipt_index table for that id.
            row = real_conn.execute(
                "SELECT 1 FROM receipt_index WHERE receipt_id = ?",
                (receipt.id,),
            ).fetchone()
            assert row is None, (
                "receipt_index row must not survive a rolled-back transaction"
            )

            # 5. Connection still usable after the rollback (no leaked txn).
            follow_up = _make_receipt(mission_id="mission_followup")
            ref2 = index.persist_and_index(follow_up)
            assert ref2 is not None, (
                "post-rollback connection must accept new persists"
            )
        finally:
            cold_store.close()


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_atomicity_under_commit_failure(seed: int) -> None:
    """Failure on ``COMMIT`` rolls back both inserts.

    **Validates: Requirement 5.2, 5.5, 5.7**
    """
    del seed
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_atom_commit")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)

        try:
            receipt = _make_receipt(
                mission_id="mission_commitfail",
                organ_id="organ_y",
                action_type="execute",
            )

            real_conn = index._conn
            proxy = _ConnExecuteProxy(
                real_conn,
                fail_predicate=lambda sql: sql.strip().upper() == "COMMIT",
                error=sqlite3.OperationalError("injected commit failure"),
            )

            index._conn = proxy  # type: ignore[assignment]
            try:
                ref = index.persist_and_index(
                    receipt, entity_path="/q", content_hash="hh"
                )
            finally:
                index._conn = real_conn

            assert ref is None
            failures = [
                ev
                for ev in event_bus.events()
                if ev.event_type
                == AgentEventType.COLD_STORE_PERSISTENCE_FAILED
            ]
            assert failures
            last = failures[-1]
            assert last.payload["stage"] == "atomic_persist_and_index"
            assert last.payload["receipt_id"] == receipt.id

            row = real_conn.execute(
                "SELECT 1 FROM receipts WHERE receipt_id = ?", (receipt.id,)
            ).fetchone()
            assert row is None
            row = real_conn.execute(
                "SELECT 1 FROM receipt_index WHERE receipt_id = ?",
                (receipt.id,),
            ).fetchone()
            assert row is None

            # Connection recovers.
            follow_up = _make_receipt(mission_id="mission_postcommit")
            assert index.persist_and_index(follow_up) is not None
        finally:
            cold_store.close()


@given(corpus=_receipt_corpus_st())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_health_check_returns_zero_under_atomic_lock(
    corpus: list[dict[str, Any]],
) -> None:
    """``health_check()`` returns 0 under Option A; orphans are still detected.

    **Validates: Requirement 5.5 (consistency invariant), Requirement 5.7 / 5.8
    (diagnostic event with ``health_check`` tag).**

    Under Option A every successful ``persist_and_index`` writes the receipt
    row and the index row in a single transaction, so no orphan can arise
    through normal use; ``health_check()`` is a defensive backstop. We confirm
    the zero-orphan claim and then deliberately inject an orphan via a direct
    ``INSERT INTO receipt_index`` to verify the backstop still fires when a
    bug bypasses the atomic path.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_health_check")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)

        try:
            _persist_corpus(index, corpus)

            # 1. After N atomic persists, health_check sees zero orphans.
            assert index.health_check() == 0

            # 2. Inject a deliberate orphan via direct insert (bypassing
            #    persist_and_index) and verify the backstop fires.
            orphan_id = "orphan_receipt_id_xyz"
            cold_store.connection.execute(
                "INSERT INTO receipt_index "
                "(receipt_id, mission_id, organ_id, action_type, "
                " entity_path, content_hash, ts_ns) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (orphan_id, "mission_orphan", None, "x", None, None, 0),
            )
            assert index.health_check() == 1

            inconsistencies = [
                ev
                for ev in event_bus.events()
                if ev.event_type
                == AgentEventType.RECEIPT_INDEX_INCONSISTENCY
            ]
            assert inconsistencies, (
                "RECEIPT_INDEX_INCONSISTENCY must be emitted for an orphan"
            )
            last = inconsistencies[-1]
            assert last.payload["tag"] == "health_check", (
                f"tag mismatch: {last.payload!r}"
            )
            assert last.payload["receipt_id"] == orphan_id
        finally:
            cold_store.close()


# ---------------------------------------------------------------------------
# Unsupported shape — concrete + Hypothesis-driven
# ---------------------------------------------------------------------------


_ALL_DIMS = (
    "mission_id",
    "organ_id",
    "timestamp_range",
    "action_type",
    "entity_path",
    "content_hash",
)
_SUPPORTED_SHAPES = {
    frozenset({"mission_id"}),
    frozenset({"mission_id", "timestamp_range"}),
    frozenset({"organ_id"}),
    frozenset({"organ_id", "action_type"}),
    frozenset({"entity_path"}),
    frozenset({"entity_path", "mission_id"}),
    frozenset({"content_hash"}),
    frozenset({"action_type"}),
    frozenset({"timestamp_range"}),
}


def _kwargs_for_dims(dims: frozenset[str]) -> dict[str, Any]:
    """Build a ``query()`` kwargs dict whose non-None keys equal ``dims``."""
    kwargs: dict[str, Any] = {}
    if "mission_id" in dims:
        kwargs["mission_id"] = "x"
    if "organ_id" in dims:
        kwargs["organ_id"] = "y"
    if "timestamp_range" in dims:
        kwargs["timestamp_range"] = (0, 1_000_000_000)
    if "action_type" in dims:
        kwargs["action_type"] = "z"
    if "entity_path" in dims:
        kwargs["entity_path"] = "/p"
    if "content_hash" in dims:
        kwargs["content_hash"] = "h"
    return kwargs


def test_unsupported_shape_raises() -> None:
    """``query(mission_id="x", organ_id="y")`` raises ``ValueError``.

    **Validates: Requirement 5.4 (only listed indexed compound shapes are
    accepted).**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_unsupported")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)
        try:
            try:
                index.query(mission_id="x", organ_id="y")
            except ValueError as exc:
                assert "Unsupported query shape" in str(exc)
            else:
                raise AssertionError(
                    "query(mission_id='x', organ_id='y') must raise"
                )
        finally:
            cold_store.close()


_unsupported_shape_st = (
    st.sets(st.sampled_from(_ALL_DIMS), min_size=1, max_size=len(_ALL_DIMS))
    .map(frozenset)
    .filter(lambda s: s not in _SUPPORTED_SHAPES)
)


@given(dims=_unsupported_shape_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_unsupported_shape_raises_hypothesis(dims: frozenset[str]) -> None:
    """Random unsupported non-empty dimension subsets all raise ``ValueError``.

    **Validates: Requirement 5.4**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="test_unsupported_h")
        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)
        try:
            kwargs = _kwargs_for_dims(dims)
            try:
                index.query(**kwargs)
            except ValueError as exc:
                assert "Unsupported query shape" in str(exc)
            else:
                raise AssertionError(
                    f"query(**{kwargs}) with shape {set(dims)} must raise"
                )
        finally:
            cold_store.close()
