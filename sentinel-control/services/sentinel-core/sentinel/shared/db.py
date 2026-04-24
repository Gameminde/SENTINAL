from __future__ import annotations

import copy
import os
from typing import Any, Protocol

from pydantic import BaseModel


def to_row(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return copy.deepcopy(value)


class TraceRepository(Protocol):
    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        ...

    def list(self, table: str) -> list[dict[str, Any]]:
        ...


class InMemoryTraceRepository:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(row)
        self.tables.setdefault(table, []).append(stored)
        return copy.deepcopy(stored)

    def list(self, table: str) -> list[dict[str, Any]]:
        return copy.deepcopy(self.tables.get(table, []))

    def first(self, table: str, **filters: Any) -> dict[str, Any] | None:
        for row in self.tables.get(table, []):
            if all(row.get(key) == value for key, value in filters.items()):
                return copy.deepcopy(row)
        return None


class SupabaseTraceRepository:
    def __init__(self, url: str | None = None, service_role_key: str | None = None, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
            return

        resolved_url = url or os.getenv("SUPABASE_URL")
        resolved_key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not resolved_url or not resolved_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

        try:
            from supabase import create_client
        except ImportError as exc:
            raise RuntimeError("The supabase package is required for SupabaseTraceRepository.") from exc

        self.client = create_client(resolved_url, resolved_key)

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table(table).insert(row).execute()
        data = getattr(response, "data", None) or []
        return data[0] if data else row

    def list(self, table: str) -> list[dict[str, Any]]:
        response = self.client.table(table).select("*").execute()
        return list(getattr(response, "data", None) or [])

