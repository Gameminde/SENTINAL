"""``ReceiptIndex`` — SQLite-backed secondary index over ``ColdReceiptStore``.

This module implements the receipt index (Requirements 5.1–5.8) as a SQLite
secondary index that lives in the **same** SQLite database as
:class:`sentinel.perf.hot_cold.cold_receipt_store.ColdReceiptStore`. The
index shares the cold store's ``sqlite3.Connection`` (exposed via
``ColdReceiptStore.connection``) and drives a single ``BEGIN IMMEDIATE`` /
``COMMIT`` block that covers BOTH the ``receipts`` row and the
``receipt_index`` row at once.

Atomicity contract (Option A — true atomic lock)
-------------------------------------------------
- Receipt INSERT and index INSERT are wrapped in a single SQLite
  ``BEGIN IMMEDIATE`` / ``COMMIT`` block on the SAME connection (shared
  from :class:`ColdReceiptStore`). Either both rows commit, or both roll
  back.
- On any ``sqlite3.Error`` (or other exception) we issue a best-effort
  ``ROLLBACK``, emit ``COLD_STORE_PERSISTENCE_FAILED`` with
  ``stage='atomic_persist_and_index'`` and the truncated error string,
  and return ``None``. There is no inconsistent state on this path: the
  receipt row and the index row are both absent — failure means nothing
  was written, so ``RECEIPT_INDEX_INCONSISTENCY`` is NOT emitted here.
- On success: BOTH rows are committed atomically and a ``ReceiptRef``
  with ``status=PERSISTED`` is returned.

The previous "documented inconsistency" path (cold-store persist
succeeded, SQLite commit failed → orphan receipt) is gone — under
Option A there is no atomicity gap to document, because the receipt
INSERT and the index INSERT now share a single transaction on a single
connection.

Supported indexed compound query shapes
----------------------------------------
- ``mission_id`` alone
- ``mission_id + timestamp_range``
- ``organ_id`` alone
- ``organ_id + action_type``
- ``entity_path`` alone
- ``entity_path + mission_id``
- ``content_hash`` alone
- ``action_type`` alone
- ``timestamp_range`` alone

Any other combination raises ``ValueError("Unsupported query shape")``.

``health_check`` (defensive backstop)
--------------------------------------
Under Option A the ``receipts`` and ``receipt_index`` tables are always
in sync — every successful ``persist_and_index`` writes both rows in
the same transaction, every failure rolls both back. ``health_check``
is therefore a defensive sanity check that catches developer error
(e.g. a code path that bypasses ``persist_and_index`` to insert into
``receipt_index`` directly). It should always return 0 in production;
any non-zero result indicates a bug somewhere upstream.

Requirements covered: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.perf.hot_cold.cold_receipt_store import (
        BaseReceipt,
        ColdReceiptStore,
        ReceiptRef,
    )

from sentinel.shared.events import AgentEventType, EventBus


# ---------------------------------------------------------------------------
# Supported query shapes — frozensets of the non-None keyword arg names.
# ---------------------------------------------------------------------------

_SUPPORTED_SHAPES: set[frozenset[str]] = {
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


# ---------------------------------------------------------------------------
# Schema DDL — issued via plain ``execute`` (NOT ``executescript``) so we do
# not trigger SQLite's implicit COMMIT, which would break our manual
# transaction control. Each statement is a single ``execute`` call.
# ---------------------------------------------------------------------------

_RECEIPT_INDEX_TABLE_DDL = """\
CREATE TABLE IF NOT EXISTS receipt_index (
    receipt_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    organ_id TEXT,
    action_type TEXT NOT NULL,
    entity_path TEXT,
    content_hash TEXT,
    ts_ns INTEGER NOT NULL
)
"""

_RECEIPT_INDEX_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS ix_receipt_mission_ts "
    "ON receipt_index(mission_id, ts_ns)",
    "CREATE INDEX IF NOT EXISTS ix_receipt_organ_action "
    "ON receipt_index(organ_id, action_type)",
    "CREATE INDEX IF NOT EXISTS ix_receipt_entity_mission "
    "ON receipt_index(entity_path, mission_id)",
    "CREATE INDEX IF NOT EXISTS ix_receipt_content "
    "ON receipt_index(content_hash)",
)


# ---------------------------------------------------------------------------
# ReceiptIndex
# ---------------------------------------------------------------------------


class ReceiptIndex:
    """Secondary index over :class:`ColdReceiptStore`. Truly atomic with the store.

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8

    Constructor parameters
    ----------------------
    event_bus : EventBus
        Event bus for emitting ``COLD_STORE_PERSISTENCE_FAILED`` (on the
        atomic-persist failure path) and ``RECEIPT_INDEX_INCONSISTENCY``
        (on the defensive health-check path only).
    cold_store : ColdReceiptStore
        Cold store whose connection we share. ``cold_store.connection`` is
        the ``sqlite3.Connection`` against which both the ``receipts`` row
        and the ``receipt_index`` row commit in a single transaction.
    """

    _ERROR_TRUNCATE: int = 200

    def __init__(
        self,
        *,
        event_bus: EventBus,
        cold_store: "ColdReceiptStore",
    ) -> None:
        self._event_bus = event_bus
        self._cold_store = cold_store
        # Share the cold store's connection — that is the whole point of
        # Option A. The cold store has already configured journal_mode,
        # synchronous, and isolation_level on this connection.
        self._conn = cold_store.connection

        # Ensure the receipt_index table and its compound indexes exist.
        # Use plain ``execute`` (not ``executescript``) so we do NOT issue
        # an implicit COMMIT — the connection is in autocommit-off mode
        # (isolation_level=None with manual BEGIN/COMMIT), and an implicit
        # commit at construction time would interfere with any future
        # in-flight transaction. Outside any explicit transaction these
        # ``execute`` calls auto-commit, which is what we want at startup.
        self._conn.execute(_RECEIPT_INDEX_TABLE_DDL)
        for ddl in _RECEIPT_INDEX_INDEXES:
            self._conn.execute(ddl)

    # ------------------------------------------------------------------
    # persist_and_index — the true atomic entry point.
    # ------------------------------------------------------------------

    def persist_and_index(
        self,
        receipt: "BaseReceipt",
        *,
        entity_path: str | None = None,
        content_hash: str | None = None,
    ) -> "ReceiptRef | None":
        """Persist ``receipt`` and write its index row in a single transaction.

        Atomicity contract (Option A — true atomic lock):

        * Both INSERTs run inside a single ``BEGIN IMMEDIATE`` / ``COMMIT``
          block on the connection shared with :class:`ColdReceiptStore`.
        * On success: both rows committed; returns a ``ReceiptRef`` with
          ``status=PERSISTED``.
        * On any exception (``sqlite3.Error``, ``TypeError`` from
          ``persist_in_transaction``, etc.): best-effort ``ROLLBACK``,
          emit ``COLD_STORE_PERSISTENCE_FAILED`` with
          ``stage='atomic_persist_and_index'``, return ``None``. Neither
          the receipt row nor the index row is left behind.

        Parameters
        ----------
        receipt : BaseReceipt
            The receipt to persist and index.
        entity_path : str | None
            Optional entity path for indexing (e.g., file path).
        content_hash : str | None
            Optional content hash for indexing.

        Returns
        -------
        ReceiptRef | None
            A ``ReceiptRef`` with ``status=PERSISTED`` on full success, or
            ``None`` if the atomic transaction was rolled back.
        """
        # Lazy import to avoid a top-level cycle with cold_receipt_store.
        from sentinel.perf.hot_cold.cold_receipt_store import (
            ReceiptRef,
            ReceiptRefStatus,
        )

        # Extract metadata for the index row up front. These values are
        # not mutated inside the transaction; computing them outside the
        # ``BEGIN IMMEDIATE`` keeps the transaction window as small as
        # possible.
        receipt_id = receipt.id
        mission_id = getattr(receipt, "mission_id", "") or ""
        organ_id = getattr(receipt, "organ_id", None)
        action_type = (
            getattr(receipt, "action", None)
            or getattr(receipt, "action_type", "")
            or ""
        )
        ts_ns = _extract_ts_ns(receipt)

        try:
            self._conn.execute("BEGIN IMMEDIATE")
            # 1. Receipt row — insert via the cold store helper that does
            #    NOT manage the transaction (the caller drives it).
            self._cold_store.persist_in_transaction(receipt, conn=self._conn)
            # 2. Index row — same connection, same transaction.
            self._conn.execute(
                "INSERT INTO receipt_index "
                "(receipt_id, mission_id, organ_id, action_type, "
                " entity_path, content_hash, ts_ns) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt_id,
                    mission_id,
                    organ_id,
                    action_type,
                    entity_path,
                    content_hash,
                    ts_ns,
                ),
            )
            self._conn.execute("COMMIT")
        except Exception as exc:
            # Best-effort rollback — the connection may already have
            # rolled back implicitly (e.g. on integrity errors). Either
            # way, neither the receipt row nor the index row survives.
            try:
                self._conn.execute("ROLLBACK")
            except Exception:
                pass
            self._event_bus.append(
                AgentEventType.COLD_STORE_PERSISTENCE_FAILED,
                "Atomic persist_and_index transaction rolled back.",
                payload={
                    "receipt_id": receipt_id,
                    "stage": "atomic_persist_and_index",
                    "error": str(exc)[: self._ERROR_TRUNCATE],
                },
            )
            return None

        return ReceiptRef(
            receipt_id=receipt_id,
            status=ReceiptRefStatus.PERSISTED,
            created_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # query — UNCHANGED. Same supported shapes, same WHERE-clause builder,
    # same LIMIT 1000 cap, same ORDER BY ts_ns DESC.
    # ------------------------------------------------------------------

    def query(
        self,
        *,
        mission_id: str | None = None,
        organ_id: str | None = None,
        timestamp_range: tuple[int, int] | None = None,
        action_type: str | None = None,
        entity_path: str | None = None,
        content_hash: str | None = None,
        limit: int = 1000,
    ) -> list[str]:
        """Query the receipt index for matching receipt IDs.

        Returns receipt_ids sorted by ts_ns DESC, capped at ``limit``
        (max 1000). Zero-match returns ``[]``.

        Only the supported indexed compound query shapes are accepted.
        Unsupported combinations raise ``ValueError("Unsupported query
        shape")``.

        Parameters
        ----------
        mission_id : str | None
            Filter by mission ID.
        organ_id : str | None
            Filter by organ ID.
        timestamp_range : tuple[int, int] | None
            Filter by timestamp range (inclusive start, exclusive end) in
            nanoseconds.
        action_type : str | None
            Filter by action type.
        entity_path : str | None
            Filter by entity path.
        content_hash : str | None
            Filter by content hash.
        limit : int
            Maximum number of results (default and max: 1000).

        Returns
        -------
        list[str]
            List of receipt IDs sorted by timestamp descending.

        Raises
        ------
        ValueError
            If the query shape is not one of the supported indexed compounds.
        """
        shape = _query_shape(
            mission_id=mission_id,
            organ_id=organ_id,
            timestamp_range=timestamp_range,
            action_type=action_type,
            entity_path=entity_path,
            content_hash=content_hash,
        )
        if shape not in _SUPPORTED_SHAPES:
            raise ValueError("Unsupported query shape")

        # Enforce LIMIT cap.
        limit = min(limit, 1000)
        if limit < 1:
            limit = 1

        # Build WHERE clause from the non-None dimensions.
        conditions: list[str] = []
        params: list[object] = []

        if mission_id is not None:
            conditions.append("mission_id = ?")
            params.append(mission_id)
        if organ_id is not None:
            conditions.append("organ_id = ?")
            params.append(organ_id)
        if action_type is not None:
            conditions.append("action_type = ?")
            params.append(action_type)
        if entity_path is not None:
            conditions.append("entity_path = ?")
            params.append(entity_path)
        if content_hash is not None:
            conditions.append("content_hash = ?")
            params.append(content_hash)
        if timestamp_range is not None:
            ts_start, ts_end = timestamp_range
            conditions.append("ts_ns >= ? AND ts_ns < ?")
            params.append(ts_start)
            params.append(ts_end)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = (
            f"SELECT receipt_id FROM receipt_index "
            f"WHERE {where_clause} "
            f"ORDER BY ts_ns DESC LIMIT ?"
        )
        params.append(limit)

        cursor = self._conn.execute(sql, params)
        return [row[0] for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # health_check — defensive sanity check (always 0 in production).
    # ------------------------------------------------------------------

    def health_check(self) -> int:
        """Verify every index row has a matching receipts row.

        Under Option A the ``receipts`` and ``receipt_index`` tables are
        always in sync, so this method is a defensive backstop against
        developer error (e.g. someone bypassing
        :meth:`persist_and_index` to insert into ``receipt_index``
        directly without writing to ``receipts``).

        For each ``receipt_index.receipt_id`` we issue a single SELECT
        against the ``receipts`` table on the same connection. Any
        row with no matching ``receipts.receipt_id`` is an orphan. We do
        NOT delete the orphan automatically (deleting silently could mask
        the upstream bug); we only emit
        ``RECEIPT_INDEX_INCONSISTENCY`` with tag ``health_check`` so the
        bug surfaces in the event ledger.

        Returns
        -------
        int
            Count of orphan index rows found. Should always be 0 under
            Option A; any non-zero result indicates a bug somewhere
            upstream.
        """
        cursor = self._conn.execute("SELECT receipt_id FROM receipt_index")
        all_ids = [row[0] for row in cursor.fetchall()]

        inconsistencies = 0
        for receipt_id in all_ids:
            row = self._conn.execute(
                "SELECT 1 FROM receipts WHERE receipt_id = ? LIMIT 1",
                (receipt_id,),
            ).fetchone()
            if row is None:
                self._event_bus.append(
                    AgentEventType.RECEIPT_INDEX_INCONSISTENCY,
                    f"Orphaned index entry for receipt {receipt_id}.",
                    payload={
                        "receipt_id": receipt_id,
                        "tag": "health_check",
                    },
                )
                inconsistencies += 1

        return inconsistencies

    # ------------------------------------------------------------------
    # close — does NOT close the underlying connection.
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release any per-instance resources.

        The underlying ``sqlite3.Connection`` is owned by the
        :class:`ColdReceiptStore` we share it with, so we do NOT close
        it here. Closing it from the index would yank the connection
        out from under the cold store and break subsequent ``persist`` /
        ``load`` calls. Lifecycle:

        * ``ColdReceiptStore.close()`` — closes the connection.
        * ``ReceiptIndex.close()`` — no-op (kept for API symmetry).
        """
        # Intentionally no-op. The cold store owns the connection.
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _query_shape(
    *,
    mission_id: str | None,
    organ_id: str | None,
    timestamp_range: tuple[int, int] | None,
    action_type: str | None,
    entity_path: str | None,
    content_hash: str | None,
) -> frozenset[str]:
    """Compute the frozenset of non-None query dimensions."""
    dims: list[str] = []
    if mission_id is not None:
        dims.append("mission_id")
    if organ_id is not None:
        dims.append("organ_id")
    if timestamp_range is not None:
        dims.append("timestamp_range")
    if action_type is not None:
        dims.append("action_type")
    if entity_path is not None:
        dims.append("entity_path")
    if content_hash is not None:
        dims.append("content_hash")
    return frozenset(dims)


def _extract_ts_ns(receipt: "BaseReceipt") -> int:
    """Extract a nanosecond timestamp from a receipt.

    Tries ``created_at`` (datetime) first, falling back to the current
    time. Converts to integer nanoseconds since epoch — matching the
    convention used by :func:`sentinel.perf.hot_cold.cold_receipt_store._extract_created_at_ns`.
    """
    created_at = getattr(receipt, "created_at", None)
    if isinstance(created_at, datetime):
        return int(created_at.timestamp() * 1_000_000_000)
    return time.time_ns()


__all__ = [
    "ReceiptIndex",
]
