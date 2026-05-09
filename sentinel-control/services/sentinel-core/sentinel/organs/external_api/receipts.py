from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ExternalAPIRequestReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("apircpt"))
    mission_id: str
    organ_id: str
    action: str
    vendor: str
    domain: str
    method: str
    path: str
    lane: str
    preview: dict[str, Any]
    evidence_refs: list[str]
    trace_refs: list[str]
    request_hash: str = ""
    future_live_allowed: bool = False
    execution_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ExternalAPIRequestReceipt:
        if not self.evidence_refs:
            raise ValueError("ExternalAPIRequestReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("ExternalAPIRequestReceipt requires trace refs.")
        if self.execution_started:
            raise ValueError("ExternalAPIRequestReceipt cannot start execution.")
        if self.authority_expansion:
            raise ValueError("ExternalAPIRequestReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.request_hash and self.request_hash != expected:
            raise ValueError("ExternalAPIRequestReceipt hash mismatch.")
        if not self.request_hash:
            self.request_hash = expected
        return self

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "organ_id": self.organ_id,
                "action": self.action,
                "vendor": self.vendor,
                "domain": self.domain,
                "method": self.method,
                "path": self.path,
                "lane": self.lane,
                "preview": self.preview,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "future_live_allowed": self.future_live_allowed,
            }
        )
