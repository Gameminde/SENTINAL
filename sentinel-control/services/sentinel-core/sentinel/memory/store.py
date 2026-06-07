from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.memory.indexes import tokenize
from sentinel.agent.llm.memory_bridge import MemoryClaimStatus
from sentinel.memory.models import MemoryRecord, MemoryTombstone


class MemoryIntegrityError(ValueError):
    """Raised when durable memory content does not match its stored hash."""


class DuplicateMemoryError(ValueError):
    """Raised when a durable lineage or content record already exists."""


class SupersessionTargetError(ValueError):
    """Raised when durable supersession cannot be applied in the same scope."""


class DurableMemoryStore:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._fts_available = True
        self._initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def save(self, record: MemoryRecord) -> None:
        with self._lock, self._connection:
            try:
                self._insert_record(record)
            except sqlite3.IntegrityError as exc:
                raise DuplicateMemoryError("duplicate durable memory lineage or content") from exc

    def save_with_supersession(
        self,
        record: MemoryRecord,
    ) -> None:
        """Persist a record and its scoped supersession updates atomically."""

        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._save_with_supersession_in_transaction(record)
            except Exception:
                self._connection.rollback()
                raise
            self._connection.commit()

    def _save_with_supersession_in_transaction(self, record: MemoryRecord) -> None:
        superseded_records: list[MemoryRecord] = []
        for target_id in record.supersedes_refs:
            row = self._connection.execute(
                "SELECT payload_json, record_hash FROM memory_records WHERE record_id = ?",
                (target_id,),
            ).fetchone()
            if row is None:
                raise SupersessionTargetError("supersession_target_missing")
            target = self._parse_verified(row["payload_json"], row["record_hash"])
            if target.namespace != record.namespace or target.validity_scope != record.validity_scope:
                raise SupersessionTargetError("supersession_scope_mismatch")
            updated = target.model_copy(
                update={
                    "claim_status": MemoryClaimStatus.SUPERSEDED,
                    "historical_only": True,
                    "superseded_by_refs": list(
                        dict.fromkeys([*target.superseded_by_refs, record.record_id])
                    ),
                    "record_hash": "",
                }
            )
            updated_payload = updated.model_dump(mode="json")
            updated_payload["record_hash"] = record_hash_payload(updated_payload)
            superseded_records.append(MemoryRecord.model_validate(updated_payload))
        try:
            self._insert_record(record)
            for superseded in superseded_records:
                self._update_record(superseded)
        except sqlite3.IntegrityError as exc:
            raise DuplicateMemoryError("duplicate durable memory lineage or content") from exc

    def update(self, record: MemoryRecord) -> None:
        with self._lock, self._connection:
            self._update_record(record)

    def get(self, record_id: str) -> MemoryRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json, record_hash FROM memory_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        return self._parse_verified(row["payload_json"], row["record_hash"])

    def all_records(self) -> tuple[list[MemoryRecord], list[str]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT record_id, payload_json, record_hash FROM memory_records ORDER BY record_id ASC"
            ).fetchall()
        records: list[MemoryRecord] = []
        quarantined: list[str] = []
        for row in rows:
            try:
                records.append(self._parse_verified(row["payload_json"], row["record_hash"]))
            except MemoryIntegrityError:
                quarantined.append(str(row["record_id"]))
        return records, quarantined

    def records_for_user(self, owner_user_id: str) -> tuple[list[MemoryRecord], list[str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT record_id, payload_json, record_hash
                FROM memory_records
                WHERE owner_user_id = ?
                ORDER BY record_id ASC
                """,
                (owner_user_id,),
            ).fetchall()
        records: list[MemoryRecord] = []
        quarantined: list[str] = []
        for row in rows:
            try:
                records.append(self._parse_verified(row["payload_json"], row["record_hash"]))
            except MemoryIntegrityError:
                quarantined.append(str(row["record_id"]))
        return records, quarantined

    def fts_scores(self, *, owner_user_id: str, query_text: str, limit: int) -> dict[str, float]:
        if not self._fts_available:
            return {}
        terms = list(dict.fromkeys(tokenize(query_text)))
        if not terms:
            return {}
        match_query = " OR ".join(f'"{term}"' for term in terms)
        try:
            with self._lock:
                rows = self._connection.execute(
                    """
                    SELECT memory_fts.record_id AS record_id, bm25(memory_fts) AS rank
                    FROM memory_fts
                    JOIN memory_records ON memory_records.record_id = memory_fts.record_id
                    WHERE memory_records.owner_user_id = ? AND memory_fts MATCH ?
                    ORDER BY rank ASC, memory_fts.record_id ASC
                    LIMIT ?
                    """,
                    (owner_user_id, match_query, limit),
                ).fetchall()
        except sqlite3.OperationalError:
            return {}
        return {
            str(row["record_id"]): round(1.0 / index, 6)
            for index, row in enumerate(rows, start=1)
        }

    def entity_record_ids(self, entity_ids: list[str]) -> list[str]:
        return self._secondary_values("memory_entities", "entity_id", entity_ids)

    def procedure_record_ids(self, procedure_ids: list[str]) -> list[str]:
        return self._secondary_values("memory_procedures", "procedure_id", procedure_ids)

    def contradiction_refs(self, record_id: str) -> list[str]:
        return self._record_secondary_values("memory_contradictions", "contradiction_ref", record_id)

    def supersedes_refs(self, record_id: str) -> list[str]:
        return self._record_secondary_values("memory_supersession", "supersedes_id", record_id)

    def find_duplicate(self, *, owner_user_id: str, source_lineage_id: str, content_hash: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT record_id FROM memory_records
                WHERE owner_user_id = ? AND (source_lineage_id = ? OR content_hash = ?)
                ORDER BY record_id ASC LIMIT 1
                """,
                (owner_user_id, source_lineage_id, content_hash),
            ).fetchone()
        return str(row["record_id"]) if row is not None else None

    def write_tombstone_and_delete(self, tombstone: MemoryTombstone) -> None:
        payload = json.dumps(tombstone.model_dump(mode="json"), sort_keys=True, ensure_ascii=True)
        with self._lock:
            with self._connection:
                self._connection.execute(
                    "INSERT INTO memory_tombstones (record_id, payload_json) VALUES (?, ?)",
                    (tombstone.record_id, payload),
                )
                self._connection.execute("DELETE FROM memory_records WHERE record_id = ?", (tombstone.record_id,))
                self._connection.execute("DELETE FROM memory_entities WHERE record_id = ?", (tombstone.record_id,))
                self._connection.execute("DELETE FROM memory_procedures WHERE record_id = ?", (tombstone.record_id,))
                self._connection.execute("DELETE FROM memory_contradictions WHERE record_id = ?", (tombstone.record_id,))
                self._connection.execute("DELETE FROM memory_supersession WHERE record_id = ?", (tombstone.record_id,))
                if self._fts_available:
                    self._connection.execute("DELETE FROM memory_fts WHERE record_id = ?", (tombstone.record_id,))
            self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def get_tombstone(self, record_id: str) -> MemoryTombstone | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM memory_tombstones WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return MemoryTombstone.model_validate(json.loads(row["payload_json"])) if row is not None else None

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA busy_timeout=5000")
            self._connection.execute("PRAGMA secure_delete=ON")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    record_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    namespace_kind TEXT NOT NULL,
                    mission_id TEXT,
                    entity_id TEXT,
                    procedure_id TEXT,
                    source_lineage_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    vector_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS memory_records_owner_idx ON memory_records(owner_user_id)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS memory_records_scope_idx ON memory_records(owner_user_id, namespace_kind, mission_id)"
            )
            self._connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS memory_records_lineage_unique ON memory_records(owner_user_id, source_lineage_id)"
            )
            self._connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS memory_records_content_unique ON memory_records(owner_user_id, content_hash)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_tombstones (
                    record_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS memory_entities (record_id TEXT NOT NULL, entity_id TEXT NOT NULL, PRIMARY KEY(record_id, entity_id))"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS memory_entities_entity_idx ON memory_entities(entity_id)"
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS memory_procedures (record_id TEXT NOT NULL, procedure_id TEXT NOT NULL, PRIMARY KEY(record_id, procedure_id))"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS memory_procedures_procedure_idx ON memory_procedures(procedure_id)"
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS memory_contradictions (record_id TEXT NOT NULL, contradiction_ref TEXT NOT NULL, PRIMARY KEY(record_id, contradiction_ref))"
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS memory_supersession (record_id TEXT NOT NULL, supersedes_id TEXT NOT NULL, PRIMARY KEY(record_id, supersedes_id))"
            )
            try:
                self._connection.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(record_id UNINDEXED, safe_summary)"
                )
            except sqlite3.OperationalError:
                self._fts_available = False

    def _upsert_fts(self, record: MemoryRecord) -> None:
        if not self._fts_available:
            return
        self._connection.execute("DELETE FROM memory_fts WHERE record_id = ?", (record.record_id,))
        if record.historical_only or record.claim_status.value in {"EXPIRED", "SUPERSEDED"}:
            return
        self._connection.execute(
            "INSERT INTO memory_fts (record_id, safe_summary) VALUES (?, ?)",
            (record.record_id, record.safe_summary),
        )

    def _replace_secondary_indexes(self, record: MemoryRecord) -> None:
        self._connection.execute("DELETE FROM memory_entities WHERE record_id = ?", (record.record_id,))
        self._connection.execute("DELETE FROM memory_procedures WHERE record_id = ?", (record.record_id,))
        self._connection.execute("DELETE FROM memory_contradictions WHERE record_id = ?", (record.record_id,))
        self._connection.execute("DELETE FROM memory_supersession WHERE record_id = ?", (record.record_id,))
        self._connection.executemany(
            "INSERT INTO memory_entities (record_id, entity_id) VALUES (?, ?)",
            [(record.record_id, value) for value in record.entity_refs],
        )
        self._connection.executemany(
            "INSERT INTO memory_procedures (record_id, procedure_id) VALUES (?, ?)",
            [(record.record_id, value) for value in record.procedure_refs],
        )
        self._connection.executemany(
            "INSERT INTO memory_contradictions (record_id, contradiction_ref) VALUES (?, ?)",
            [(record.record_id, value) for value in record.contradiction_refs],
        )
        self._connection.executemany(
            "INSERT INTO memory_supersession (record_id, supersedes_id) VALUES (?, ?)",
            [(record.record_id, value) for value in record.supersedes_refs],
        )

    def _insert_record(self, record: MemoryRecord) -> None:
        payload = record.model_dump(mode="json")
        self._connection.execute(
            """
            INSERT INTO memory_records (
                record_id, owner_user_id, namespace_kind, mission_id,
                entity_id, procedure_id, source_lineage_id, content_hash,
                record_hash, payload_json, vector_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.record_id,
                record.namespace.owner_user_id,
                record.namespace.kind.value,
                record.namespace.mission_id,
                record.namespace.entity_id,
                record.namespace.procedure_id,
                record.provenance.source_lineage_id,
                record.content_hash,
                record.record_hash,
                json.dumps(payload, sort_keys=True, ensure_ascii=True),
                "[]",
            ),
        )
        self._upsert_fts(record)
        self._replace_secondary_indexes(record)

    def _update_record(self, record: MemoryRecord) -> None:
        payload = record.model_dump(mode="json")
        self._connection.execute(
            "UPDATE memory_records SET record_hash = ?, payload_json = ? WHERE record_id = ?",
            (
                record.record_hash,
                json.dumps(payload, sort_keys=True, ensure_ascii=True),
                record.record_id,
            ),
        )
        self._upsert_fts(record)
        self._replace_secondary_indexes(record)

    def _secondary_values(self, table: str, column: str, values: list[str]) -> list[str]:
        if not values:
            return []
        placeholders = ",".join("?" for _ in values)
        with self._lock:
            rows = self._connection.execute(
                f"SELECT DISTINCT record_id FROM {table} WHERE {column} IN ({placeholders}) ORDER BY record_id",
                tuple(values),
            ).fetchall()
        return [str(row["record_id"]) for row in rows]

    def _record_secondary_values(self, table: str, column: str, record_id: str) -> list[str]:
        with self._lock:
            rows = self._connection.execute(
                f"SELECT {column} FROM {table} WHERE record_id = ? ORDER BY {column}",
                (record_id,),
            ).fetchall()
        return [str(row[column]) for row in rows]

    @staticmethod
    def _parse_verified(payload_json: str, stored_hash: str) -> MemoryRecord:
        payload = json.loads(payload_json)
        payload_hash = _record_hash(payload)
        if payload_hash != stored_hash:
            raise MemoryIntegrityError("memory record hash mismatch")
        return MemoryRecord.model_validate(payload)


def record_hash_payload(payload: dict) -> str:
    canonical = MemoryRecord.model_validate(payload).model_dump(mode="json")
    return _record_hash(canonical)


def _record_hash(payload: dict) -> str:
    material = dict(payload)
    material["record_hash"] = ""
    return stable_hash(material)
