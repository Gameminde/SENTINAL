# Feature: sentinel-performance-runtime-foundation, Property 5: Cold-store durability — no-loss round-trip under failure (Option A — SQLite)
"""Property-based test for the SQLite-backed ``ColdReceiptStore`` (Phase B Refactor).

**Validates: Requirements 4.3, 4.4 (under Option A — true atomic SQLite WAL).**

Phase B Refactor — Option A. Under Option A the SQLite WAL is the durable WAL.
There is exactly one transaction boundary inside ``ColdReceiptStore.persist`` and
exactly two outcomes:

* **success** — the receipt row is durably committed; ``persist`` returns a
  ``ReceiptRef`` with ``status=PERSISTED``; ``load(id)`` returns an equal
  receipt; re-encoding via ``_canonical_encode`` is byte-equal to the original
  encoding (string equality).
* **failure** — the SQLite transaction rolls back; ``persist`` returns
  ``None``; a ``COLD_STORE_PERSISTENCE_FAILED`` event with
  ``stage="sqlite_persist"`` is emitted; ``load(id)`` raises ``KeyError``; no
  orphan row is left behind by the failed persist.

There is no ``WAL_DURABLE`` intermediate state, no retry buffer, no
``wal_failure_pending``, no ``pending_retries``, no ``retry_pending()``, no
two-stage filesystem failure schedule — those were artifacts of the
pre-refactor filesystem journal and have been removed under Option A.

Failure injection is now SQLite-driven, not filesystem-driven:

* ``integrity_error`` — persist two receipts that share the same
  ``receipt.id`` (built via ``model_copy(update={"id": fixed_id})``). The
  second insert hits the PRIMARY KEY constraint and raises
  ``sqlite3.IntegrityError``.
* ``closed_conn`` — close the underlying ``sqlite3.Connection`` and call
  ``persist``; the next ``execute`` raises ``sqlite3.ProgrammingError``
  (a subclass of ``sqlite3.Error``). A fresh inspection connection
  re-opened against the on-disk DB file confirms no row survived.

The Option A coupling helper (``persist_in_transaction``) is exercised
directly by ``test_persist_in_transaction_atomic`` and
``test_no_partial_state_after_rollback``: the test opens its own
``BEGIN IMMEDIATE`` block on ``store.connection`` and chooses whether to
``COMMIT`` or ``ROLLBACK``. Under ``ROLLBACK`` neither receipt row
survives — the property that guarantees Option A's "no inconsistent
partial state" claim.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.hot_cold.cold_receipt_store import (
    ColdReceiptStore,
    ReceiptRef,
    ReceiptRefStatus,
    _canonical_encode,
)
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import new_id


# ---------------------------------------------------------------------------
# Receipt factory
# ---------------------------------------------------------------------------


def _make_receipt(
    *,
    wall_ms: int = 10,
    cpu_ms: int = 5,
    bytes_in: int = 100,
    bytes_out: int = 50,
    tokens_in: int = 20,
    tokens_out: int = 10,
    cache_miss: int = 1,
    budget_remaining: int = 900,
    budget_limit: int = 1000,
    cost_micro_usd: int = 1000,
) -> PerformanceReceipt:
    """Build a fresh valid ``PerformanceReceipt`` with a unique id.

    Hypothesis-driven counters are accepted as keyword arguments so the
    round-trip property is exercised across a range of valid receipt
    shapes rather than a single hard-coded one.
    """
    trace = PerformanceTrace(
        action_id=new_id("act"),
        mission_id="mission_cold_test",
        organ_id=None,
        action_type="test_action",
        queue_wait_ms=0,
        wall_ms=wall_ms,
        cpu_ms=cpu_ms,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cache_hit=0,
        cache_miss=cache_miss,
        organ_latency_ms=0,
        model_prefill_decode_ms=0,
        error=False,
        error_category=None,
        severity=PerformanceSeverity.INFO,
    )
    return PerformanceReceipt(
        id=new_id("pr"),
        mission_id="mission_cold_test",
        action_id=trace.action_id,
        organ_id=None,
        action="test_persist",
        trace=trace,
        # Decimal with 6 fractional digits matches the ``max_digits=20,
        # decimal_places=6`` constraint on the receipt model.
        estimated_cost_usd=(Decimal(cost_micro_usd) / Decimal("1000000")).quantize(
            Decimal("0.000001")
        ),
        model_id="test-model",
        budget_remaining=budget_remaining,
        budget_limit=budget_limit,
        cache_type=None,
        backpressure_reason=None,
        queue_depth_at_receipt=None,
        deadline_ms=None,
        elapsed_ms=None,
        authority_expansion=False,
        raw_secret_leakage=False,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------


# Small bounded counters — large enough to exercise the canonical JSON
# encoder (multi-digit integers, nontrivial Decimal arithmetic) but small
# enough to keep runs fast.
_counter_st = st.integers(min_value=0, max_value=10_000)
_budget_st = st.integers(min_value=0, max_value=100_000)
_cost_micro_st = st.integers(min_value=0, max_value=10_000_000)

# Two sub-cases for the persist-failure property, drawn by Hypothesis.
_failure_mode_st = st.sampled_from(["integrity_error", "closed_conn"])

# Random unknown ids for the load-not-found property. ``min_size=1`` keeps
# us out of the empty-string corner (which is a separately interesting
# input but not what this property targets) and ``max_size=64`` keeps the
# generator fast.
_unknown_id_st = st.text(min_size=1, max_size=64)

# Number of receipts to insert in the multi-row rollback property.
_rollback_count_st = st.integers(min_value=2, max_value=4)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(
    wall_ms=_counter_st,
    cpu_ms=_counter_st,
    bytes_in=_counter_st,
    bytes_out=_counter_st,
    tokens_in=_counter_st,
    tokens_out=_counter_st,
    cache_miss=_counter_st,
    budget_remaining=_budget_st,
    budget_limit=_budget_st,
    cost_micro_usd=_cost_micro_st,
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_round_trip_on_success(
    wall_ms: int,
    cpu_ms: int,
    bytes_in: int,
    bytes_out: int,
    tokens_in: int,
    tokens_out: int,
    cache_miss: int,
    budget_remaining: int,
    budget_limit: int,
    cost_micro_usd: int,
) -> None:
    """Successful persist → loadable receipt → byte-equal canonical encoding.

    Validates: Requirements 4.3, 4.4 (success path).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="mission_cold_test")
        store = ColdReceiptStore(root, event_bus=event_bus)
        try:
            original = _make_receipt(
                wall_ms=wall_ms,
                cpu_ms=cpu_ms,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cache_miss=cache_miss,
                budget_remaining=budget_remaining,
                budget_limit=budget_limit,
                cost_micro_usd=cost_micro_usd,
            )

            ref = store.persist(original)

            # 1. Ref shape.
            assert isinstance(ref, ReceiptRef), f"expected ReceiptRef, got {ref!r}"
            assert ref.status == ReceiptRefStatus.PERSISTED
            assert ref.receipt_id == original.id

            # 2. load(id) returns an equal receipt.
            loaded = store.load(original.id)
            assert isinstance(loaded, PerformanceReceipt)
            assert loaded == original, (
                "loaded receipt is not equal to the original under "
                "PerformanceReceipt.__eq__"
            )

            # 3. Canonical encoding round-trip is string-equal.
            assert _canonical_encode(loaded) == _canonical_encode(original), (
                "canonical encoding of the loaded receipt differs from the "
                "original — round-trip is not byte-stable"
            )
        finally:
            store.close()


@given(failure_mode=_failure_mode_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_persist_failure_returns_none(failure_mode: str) -> None:
    """Injected SQLite failure → ``None``, event emitted, no orphan row.

    Two sub-cases drawn by Hypothesis:

    * ``integrity_error`` — collide on PRIMARY KEY ``receipt_id``.
    * ``closed_conn``     — close the connection and persist.

    Validates: Requirements 4.3, 4.4 (failure path).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="mission_cold_test")
        store = ColdReceiptStore(root, event_bus=event_bus)
        db_path = root / "cold_store.db"

        try:
            if failure_mode == "integrity_error":
                # Persist a baseline receipt successfully.
                baseline = _make_receipt()
                baseline_ref = store.persist(baseline)
                assert baseline_ref is not None, "baseline persist must succeed"

                # Build a colliding receipt: a fresh receipt whose id is
                # rewritten to match the baseline. ``model_copy`` bypasses
                # validation (default), so the receipt_hash field is stale
                # — that is fine here because we never call ``load`` on the
                # colliding receipt; only the INSERT is observed.
                fixed_id = baseline.id
                colliding = _make_receipt().model_copy(update={"id": fixed_id})

                event_count_before = len(event_bus.events())
                ref = store.persist(colliding)

                # 1. persist returned None.
                assert ref is None, (
                    f"integrity_error: expected persist to return None, got {ref!r}"
                )

                # 2. event emitted with stage='sqlite_persist' for this id.
                step_events = event_bus.events()[event_count_before:]
                matching = [
                    ev
                    for ev in step_events
                    if ev.event_type == AgentEventType.COLD_STORE_PERSISTENCE_FAILED
                    and ev.payload.get("stage") == "sqlite_persist"
                    and ev.payload.get("receipt_id") == fixed_id
                ]
                assert matching, (
                    "integrity_error: expected a COLD_STORE_PERSISTENCE_FAILED "
                    f"event with stage='sqlite_persist' for receipt_id={fixed_id}; "
                    f"events seen this step: "
                    f"{[(ev.event_type, ev.payload) for ev in step_events]}"
                )

                # 3. No orphan row added by the failed persist — exactly one
                #    row exists for that id (the baseline).
                cursor = store.connection.execute(
                    "SELECT COUNT(*) FROM receipts WHERE receipt_id = ?",
                    (fixed_id,),
                )
                (count,) = cursor.fetchone()
                assert count == 1, (
                    "integrity_error: expected exactly one row for "
                    f"receipt_id={fixed_id} (the baseline); got {count}"
                )

                # 4. The baseline receipt is still loadable.
                loaded = store.load(fixed_id)
                assert loaded.id == fixed_id

            else:  # failure_mode == "closed_conn"
                receipt = _make_receipt()

                # Close the underlying connection. Any subsequent execute
                # on the store's connection will raise
                # ``sqlite3.ProgrammingError`` (a subclass of
                # ``sqlite3.Error``). The store's persist() catches it,
                # attempts ROLLBACK (also fails — best-effort, swallowed),
                # emits the event, and returns None.
                store.connection.close()

                event_count_before = len(event_bus.events())
                ref = store.persist(receipt)

                # 1. persist returned None.
                assert ref is None, (
                    f"closed_conn: expected persist to return None, got {ref!r}"
                )

                # 2. event emitted with stage='sqlite_persist'.
                step_events = event_bus.events()[event_count_before:]
                matching = [
                    ev
                    for ev in step_events
                    if ev.event_type == AgentEventType.COLD_STORE_PERSISTENCE_FAILED
                    and ev.payload.get("stage") == "sqlite_persist"
                    and ev.payload.get("receipt_id") == receipt.id
                ]
                assert matching, (
                    "closed_conn: expected a COLD_STORE_PERSISTENCE_FAILED "
                    f"event with stage='sqlite_persist' for receipt_id={receipt.id}; "
                    f"events seen this step: "
                    f"{[(ev.event_type, ev.payload) for ev in step_events]}"
                )

                # 3. No row exists in the DB for that id. Inspect via a
                #    fresh connection — the store's own connection is
                #    closed.
                inspect = sqlite3.connect(str(db_path))
                try:
                    row = inspect.execute(
                        "SELECT 1 FROM receipts WHERE receipt_id = ?",
                        (receipt.id,),
                    ).fetchone()
                    assert row is None, (
                        "closed_conn: expected no row for "
                        f"receipt_id={receipt.id} after failed persist"
                    )
                finally:
                    inspect.close()
        finally:
            # Best-effort close — for the closed_conn branch the connection
            # is already closed; ColdReceiptStore.close() guards on
            # _owns_connection but a double-close is harmless.
            try:
                store.close()
            except sqlite3.ProgrammingError:
                pass


@given(commit=st.booleans())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_persist_in_transaction_atomic(commit: bool) -> None:
    """Caller-driven transaction: COMMIT → loadable; ROLLBACK → not loadable.

    Exercises the Option A coupling helper directly. The test opens its
    own ``BEGIN IMMEDIATE`` block on the cold store's connection, calls
    ``persist_in_transaction``, then either ``COMMIT`` or ``ROLLBACK``.
    The resulting state proves the receipt row's atomicity is genuinely
    under the caller's control — which is the property that makes the
    cold store composable with sibling tables (notably ``receipt_index``)
    in a single atomic transaction.

    Validates: Requirements 4.3, 4.4 (Option A coupling).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="mission_cold_test")
        store = ColdReceiptStore(root, event_bus=event_bus)
        try:
            receipt = _make_receipt()

            store.connection.execute("BEGIN IMMEDIATE")
            store.persist_in_transaction(receipt, conn=store.connection)

            if commit:
                store.connection.execute("COMMIT")
                loaded = store.load(receipt.id)
                assert loaded.id == receipt.id, (
                    "commit: receipt should be loadable after COMMIT"
                )
                assert loaded == receipt, (
                    "commit: loaded receipt should equal the original"
                )
            else:
                store.connection.execute("ROLLBACK")
                try:
                    store.load(receipt.id)
                except KeyError:
                    pass
                else:
                    raise AssertionError(
                        "rollback: receipt should NOT be loadable after ROLLBACK"
                    )
        finally:
            store.close()


@given(num_receipts=_rollback_count_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_no_partial_state_after_rollback(num_receipts: int) -> None:
    """Multiple inserts in one transaction → ROLLBACK → none survive.

    Stronger version of :func:`test_persist_in_transaction_atomic`: insert
    ``num_receipts`` receipts inside the same ``BEGIN IMMEDIATE`` block,
    then ``ROLLBACK`` before ``COMMIT``. Assert that NONE of the receipts
    are loadable afterward. This is the property that guarantees Option
    A's atomicity claim — an inconsistent partial state (some inserted
    rows survive a rollback, others do not) cannot occur.

    Validates: Requirements 4.3, 4.4 (Option A no-partial-state).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="mission_cold_test")
        store = ColdReceiptStore(root, event_bus=event_bus)
        try:
            receipts = [_make_receipt() for _ in range(num_receipts)]

            store.connection.execute("BEGIN IMMEDIATE")
            for r in receipts:
                store.persist_in_transaction(r, conn=store.connection)
            store.connection.execute("ROLLBACK")

            for r in receipts:
                try:
                    store.load(r.id)
                except KeyError:
                    pass
                else:
                    raise AssertionError(
                        "no_partial_state: receipt "
                        f"{r.id} survived ROLLBACK — partial state observed"
                    )

            # Defensive cross-check directly against the table — confirms
            # the property at the SQL layer rather than only via the
            # ``load`` API.
            ids = tuple(r.id for r in receipts)
            placeholders = ",".join("?" for _ in ids)
            cursor = store.connection.execute(
                f"SELECT COUNT(*) FROM receipts WHERE receipt_id IN ({placeholders})",
                ids,
            )
            (count,) = cursor.fetchone()
            assert count == 0, (
                "no_partial_state: expected zero receipts surviving ROLLBACK, "
                f"found {count}"
            )
        finally:
            store.close()


@given(unknown_id=_unknown_id_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_load_unknown_id_raises_keyerror(unknown_id: str) -> None:
    """``load`` raises ``KeyError`` for any id not present in the store.

    Validates: Requirements 4.3 (well-defined miss behaviour).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        event_bus = EventBus(mission_id="mission_cold_test")
        store = ColdReceiptStore(root, event_bus=event_bus)
        try:
            try:
                store.load(unknown_id)
            except KeyError:
                pass
            else:
                raise AssertionError(
                    f"expected KeyError for unknown id {unknown_id!r}"
                )
        finally:
            store.close()
