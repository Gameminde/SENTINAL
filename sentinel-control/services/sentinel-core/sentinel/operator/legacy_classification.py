from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sentinel.shared.models import SentinelModel


class InternalAccessClassification(StrEnum):
    PRODUCTION_ROUTE = "production_route"
    LEGACY_INTERNAL = "legacy_internal"
    TEST_ONLY = "test_only"
    DISABLED = "disabled"


class InternalAccessRecord(SentinelModel):
    surface: str
    classification: InternalAccessClassification
    owner: str
    rationale: str
    migrated: bool = False
    notes: list[str] = Field(default_factory=list)


__all__ = ["InternalAccessClassification", "InternalAccessRecord"]
