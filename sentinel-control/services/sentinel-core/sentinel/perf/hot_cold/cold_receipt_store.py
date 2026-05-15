"""``ColdReceiptStore`` — SQLite-backed durable receipt journal (Phase B, Option A).

This module implements the *cold side* of the hot/cold state separation
(Requirements 4.3, 4.4) as a SQLite-backed store. Under **Option A** the
SQLite WAL is the durable WAL: there is no separate filesystem WAL/store
split, no retry buffer, no ``wal_failure_volatile``, no ``pending_retries``.
Every successful ``persist`` returns a ``ReceiptRef`` whose status is
``PERSISTED`` — the row is durably committed to the database before the
ref is returned. Persistence either succeeds atomically or rolls back
atomically; there is no intermediate "WAL_DURABLE" state to expose.

Atomicity contract (Option A — true atomic lock)
-------------------------------------------------
``persist_in_transaction`` is the coupling point that allows a caller
(typically :class:`sentinel.perf.hot_cold.receipt_index.ReceiptIndex`) to
drive a single ``BEGIN IMMEDIATE`` ... ``COMMIT`` block that covers BOTH
the ``receipts`` row and any sibling tables (e.g. ``receipt_index``) in
the same database file. When that helper is used, persist-and-index is
truly atomic — either both rows commit or both roll back.

When ``persist`` is called directly (no caller-driven transaction) the
store opens its own ``BEGIN IMMEDIATE`` ... ``COMMIT`` around a single
INSERT.

Schema
------

.. code-block:: sql

    CREATE TABLE IF NOT EXISTS receipts (
        receipt_id TEXT PRIMARY KEY,
        receipt_type TEXT NOT NULL,
        payload TEXT NOT NULL,          -- canonical JSON
        created_at_ns INTEGER NOT NULL
    );

The ``receipts`` table lives in the SAME SQLite database file as the
``receipt_index`` table — Task 4.4 will share this connection through the
``connection`` constructor argument. The DB file is ``<root>/cold_store.db``.

PRAGMAs (set on connection open)
--------------------------------
* ``PRAGMA journal_mode=WAL`` — SQLite's WAL is the durable WAL.
* ``PRAGMA synchronous=FULL`` — durability over throughput. This is the
  canonical 10 ms p95 target's tuning point: dropping to NORMAL would
  trade durability for latency. Phase D will revisit if benchmark
  pressure proves it necessary.
* ``PRAGMA foreign_keys=ON`` — for future FK constraints.

Canonical encoding
------------------
Receipts are serialized as a single canonical JSON line stored in the
``payload`` TEXT column. ``receipt_type`` lives in its own column rather
than in a header line — the previous two-line "header + payload" format
was a Phase-B-pre-refactor artifact appropriate for an opaque file
journal but unnecessary for a typed SQL schema.

Round-trip property: re-encoding the loaded receipt with
``_canonical_encode`` produces a string identical to the stored payload.

Thread-safety
-------------
SQLite connections are not thread-safe by default. A single
``ColdReceiptStore`` instance is intended for a single thread or for a
single asyncio event loop. Phase D will revisit locking if needed.

Layering
--------
This module sits in ``sentinel.perf.hot_cold`` and may import from
``sentinel.shared.events`` (EventBus + AgentEventType), ``sentinel.organs.*``
(receipt model classes), and ``sentinel.perf.measure`` (PerformanceReceipt).
It MUST NOT import from ``sentinel.agent.*`` or ``sentinel.mission.*``.

Requirements covered: 4.3, 4.4.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias

from pydantic import ConfigDict, Field

from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.receipts import OrganExecutionReceipt
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


BaseReceipt: TypeAlias = (
    PerformanceReceipt | OrganExecutionReceipt | OrganDryRunReceipt
)
"""Receipt union accepted by :class:`ColdReceiptStore`.

No new superclass is introduced. The cold store accepts exactly the three
receipt families defined elsewhere in the platform; any other type is
rejected at ``persist`` with ``TypeError``.
"""


_RECEIPT_CLASS_BY_NAME: dict[str, type[SentinelModel]] = {
    "PerformanceReceipt": PerformanceReceipt,
    "OrganExecutionReceipt": OrganExecutionReceipt,
    "OrganDryRunReceipt": OrganDryRunReceipt,
}


class ReceiptRefStatus(StrEnum):
    """Lifecycle status of a :class:`ReceiptRef`.

    Under Option A only ``PERSISTED`` is meaningful: every returned ref
    refers to a row that is durably committed to SQLite. The prior
    ``WAL_DURABLE`` state (where the canonical bytes were durable in a
    filesystem WAL but not yet in their final placement) was a
    Phase-B-pre-refactor artifact of the two-stage filesystem journal and
    no longer exists. The enum is preserved (rather than removed) so
    downstream code that reads ``ref.status`` keeps working without
    needing branch updates.
    """

    PERSISTED = "persisted"


class ReceiptRef(SentinelModel):
    """Frozen handle returned by :meth:`ColdReceiptStore.persist`.

    Under Option A a ``ReceiptRef`` is only ever returned for receipts
    whose SQLite row was durably committed. Persistence failure returns
    ``None``. There is no ``wal_path`` field — the canonical bytes live
    inside the SQLite database, not on a separate filesystem path.
    """

    receipt_id: str
    status: ReceiptRefStatus = ReceiptRefStatus.PERSISTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


# ---------------------------------------------------------------------------
# Canonical encoder
# ---------------------------------------------------------------------------


def _canonical_encode(receipt: BaseReceipt) -> str:
    """Encode ``receipt`` to its canonical on-disk JSON string.

    Returns a deterministic JSON string suitable for storage in a SQLite
    TEXT column. ``sort_keys=True`` + fixed separators + ``ensure_ascii=True``
    guarantee a stable, byte-identical round trip: re-encoding the result
    of ``load(receipt_id)`` with this function produces a string identical
    to the originally stored payload.

    The receipt type is NOT embedded in the payload — it is stored in a
    separate ``receipt_type`` column (the prior "header line" format from
    the filesystem-WAL era is no longer needed).
    """
    payload_dict = receipt.model_dump(mode="json")
    return json.dumps(
        payload_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------


_RECEIPTS_DDL = """\
CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY,
    receipt_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at_ns INTEGER NOT NULL
);
"""


# ---------------------------------------------------------------------------
# ColdReceiptStore
# ---------------------------------------------------------------------------


class ColdReceiptStore:
    """SQLite-backed append-only durable receipt journal.

    Under Option A the SQLite WAL is the durable WAL. ``persist`` returns
    a ``ReceiptRef`` (with ``status=PERSISTED``) only after the row is
    durably committed; on any persistence failure it returns ``None`` and
    emits ``COLD_STORE_PERSISTENCE_FAILED``.

    The store exposes ``persist_in_transaction`` so callers (notably
    :class:`ReceiptIndex`) can wrap the receipt INSERT and a sibling-table
    INSERT in a single ``BEGIN IMMEDIATE`` ... ``COMMIT`` block — that is
    the coupling point that makes Option A a *true* atomic lock.

    Requirements: 4.3, 4.4.
    """

    _ERROR_TRUNCATE: int = 200

    def __init__(
        self,
        root: Path | str,
        *,
        event_bus: EventBus,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self._root: Path = Path(root)
        self._event_bus: EventBus = event_bus

        if connection is not None:
            # Caller-supplied connection (used by ReceiptIndex to share
            # the DB file). The caller is responsible for the connection's
            # PRAGMAs and lifetime; we still ensure the receipts table
            # exists on this connection.
            self._conn = connection
            self._owns_connection = False
        else:
            # Open our own connection on ``<root>/cold_store.db``.
            self._root.mkdir(parents=True, exist_ok=True)
            db_path = self._root / "cold_store.db"
            self._conn = sqlite3.connect(
                str(db_path),
                # Manual transaction control via BEGIN IMMEDIATE / COMMIT
                # / ROLLBACK; isolation_level=None disables sqlite3's
                # implicit-transaction behaviour.
                isolation_level=None,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._owns_connection = True

        # Always ensure the receipts table exists on whichever connection
        # we end up using. ``executescript`` would issue an implicit
        # COMMIT that conflicts with our manual transaction model, so use
        # plain ``execute`` on the single statement.
        self._conn.execute(_RECEIPTS_DDL)

    # ------------------------------------------------------------------
    # connection — exposed so ReceiptIndex can share the same DB handle.
    # ------------------------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying SQLite connection.

        Exposed so :class:`ReceiptIndex` can share the same connection in
        Task 4.4 — that is what allows the receipt INSERT and the
        receipt_index INSERT to commit in a single transaction.
        """
        return self._conn

    # ---------------------------------------------------------------- persist

    def persist(self, receipt: BaseReceipt) -> ReceiptRef | None:
        """Persist ``receipt`` to the SQLite ``receipts`` table.

        Wraps the INSERT in a ``BEGIN IMMEDIATE`` ... ``COMMIT`` block.
        Returns a ``ReceiptRef`` with ``status=PERSISTED`` on success.
        On any ``sqlite3.Error`` (or other exception) issues a best-effort
        ``ROLLBACK``, emits ``COLD_STORE_PERSISTENCE_FAILED`` with
        ``stage="sqlite_persist"`` and the truncated error string, and
        returns ``None``.

        Raises :class:`TypeError` if ``receipt`` is not one of
        ``PerformanceReceipt``, ``OrganExecutionReceipt``,
        ``OrganDryRunReceipt`` — the cold store does not accept arbitrary
        ``BaseModel`` subclasses; broadening the surface would weaken the
        round-trip guarantee.
        """
        receipt_type = type(receipt).__name__
        if receipt_type not in _RECEIPT_CLASS_BY_NAME:
            raise TypeError(
                f"ColdReceiptStore.persist refused type {receipt_type!r}; "
                f"accepted: {sorted(_RECEIPT_CLASS_BY_NAME)}"
            )

        receipt_id = receipt.id
        payload_json = _canonical_encode(receipt)
        created_at_ns = _extract_created_at_ns(receipt)

        try:
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO receipts "
                "(receipt_id, receipt_type, payload, created_at_ns) "
                "VALUES (?, ?, ?, ?)",
                (receipt_id, receipt_type, payload_json, created_at_ns),
            )
            self._conn.execute("COMMIT")
        except Exception as exc:  # pragma: no cover — covers sqlite3.Error and any other failure
            try:
                self._conn.execute("ROLLBACK")
            except Exception:
                # Best-effort: the connection may be closed or already
                # rolled back; do not mask the original error.
                pass
            self._emit_persistence_failed(receipt_id, "sqlite_persist", exc)
            return None

        return ReceiptRef(
            receipt_id=receipt_id,
            status=ReceiptRefStatus.PERSISTED,
            created_at=datetime.now(UTC),
        )

    # ----------------------------------------------- persist_in_transaction

    def persist_in_transaction(
        self,
        receipt: BaseReceipt,
        *,
        conn: sqlite3.Connection,
    ) -> None:
        """Insert ``receipt`` into the ``receipts`` table without managing the transaction.

        The caller (typically :class:`ReceiptIndex`) is expected to have
        already opened a ``BEGIN IMMEDIATE`` block on ``conn`` and is
        responsible for ``COMMIT``/``ROLLBACK``. This is THE coupling point
        that makes Option A a true atomic lock: the receipt row and the
        index row commit (or roll back) together.

        Raises :class:`TypeError` for unaccepted receipt types and lets
        ``sqlite3.Error`` propagate so the caller's outer ``except`` block
        can roll back the whole transaction.
        """
        receipt_type = type(receipt).__name__
        if receipt_type not in _RECEIPT_CLASS_BY_NAME:
            raise TypeError(
                f"ColdReceiptStore.persist_in_transaction refused type "
                f"{receipt_type!r}; accepted: {sorted(_RECEIPT_CLASS_BY_NAME)}"
            )

        receipt_id = receipt.id
        payload_json = _canonical_encode(receipt)
        created_at_ns = _extract_created_at_ns(receipt)

        # No BEGIN/COMMIT here — the caller drives the transaction.
        conn.execute(
            "INSERT INTO receipts "
            "(receipt_id, receipt_type, payload, created_at_ns) "
            "VALUES (?, ?, ?, ?)",
            (receipt_id, receipt_type, payload_json, created_at_ns),
        )

    # ---------------------------------------------------------------- load

    def load(self, receipt_id: str) -> BaseReceipt:
        """Round-trip a previously persisted receipt by id.

        Reads ``(receipt_type, payload)`` from the ``receipts`` table and
        validates the payload against the appropriate Pydantic class.

        Raises :class:`KeyError` if no row exists for ``receipt_id``.
        Raises :class:`ValueError` if the stored ``receipt_type`` is
        unknown to the platform.

        Round-trip integrity (Requirement 4.3): re-encoding the returned
        receipt with :func:`_canonical_encode` yields a string
        byte-for-byte identical to the stored ``payload`` column.
        """
        cursor = self._conn.execute(
            "SELECT receipt_type, payload FROM receipts "
            "WHERE receipt_id = ?",
            (receipt_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError(f"receipt {receipt_id} not found")

        receipt_type, payload = row
        receipt_cls = _RECEIPT_CLASS_BY_NAME.get(receipt_type)
        if receipt_cls is None:
            raise ValueError(
                f"receipt {receipt_id} has unknown receipt_type {receipt_type!r}"
            )
        return receipt_cls.model_validate_json(payload)  # type: ignore[return-value]

    # ---------------------------------------------------------------- close

    def close(self) -> None:
        """Close the underlying SQLite connection (only if owned)."""
        if self._owns_connection:
            self._conn.close()

    # --------------------------------------------------------------- internal

    def _emit_persistence_failed(
        self,
        receipt_id: str,
        stage: str,
        exc: BaseException,
    ) -> None:
        """Emit ``COLD_STORE_PERSISTENCE_FAILED`` with a truncated error string.

        Truncation keeps incidental large messages out of the event ledger
        and reduces the chance of inadvertently propagating sensitive
        substrings the underlying SQLite layer may have included in the
        error.
        """
        self._event_bus.append(
            AgentEventType.COLD_STORE_PERSISTENCE_FAILED,
            f"Cold-store persistence failed at stage={stage}.",
            payload={
                "receipt_id": receipt_id,
                "stage": stage,
                "error": str(exc)[: self._ERROR_TRUNCATE],
            },
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_created_at_ns(receipt: BaseReceipt) -> int:
    """Extract a nanosecond creation timestamp from ``receipt``.

    ``PerformanceReceipt`` has a ``created_at`` ``datetime`` field; the
    organ receipts do not (they are append-only-via-event-bus and rely on
    the event ledger for ordering). For receipts without a ``created_at``
    we fall back to ``time.time_ns()`` at persist time — good enough for
    indexing and ordering, while still deterministic w.r.t. wall clock.
    """
    created_at = getattr(receipt, "created_at", None)
    if isinstance(created_at, datetime):
        return int(created_at.timestamp() * 1_000_000_000)
    return time.time_ns()


__all__ = [
    "BaseReceipt",
    "ColdReceiptStore",
    "ReceiptRef",
    "ReceiptRefStatus",
]
