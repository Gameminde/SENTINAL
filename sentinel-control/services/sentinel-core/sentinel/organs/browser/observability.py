from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from sentinel.organs.browser.models import (
    BrowserConsoleRecord,
    BrowserHealthMetadata,
    BrowserNetworkLedger,
    BrowserPageErrorRecord,
    BrowserRequestFailureRecord,
    BrowserRequestRecord,
    BrowserResponseRecord,
)


def build_browser_network_ledger(
    *,
    requests: Sequence[BrowserRequestRecord] | None = None,
    responses: Sequence[BrowserResponseRecord] | None = None,
    failures: Sequence[BrowserRequestFailureRecord] | None = None,
    console: Sequence[BrowserConsoleRecord] | None = None,
    page_errors: Sequence[BrowserPageErrorRecord] | None = None,
    health: BrowserHealthMetadata | None = None,
    max_records: int = 200,
) -> BrowserNetworkLedger:
    max_count = max(1, int(max_records))
    raw = {
        "requests": list(requests or []),
        "responses": list(responses or []),
        "failures": list(failures or []),
        "console": list(console or []),
        "page_errors": list(page_errors or []),
    }
    original_counts = {key: len(value) for key, value in raw.items()}
    bounded = {key: value[-max_count:] for key, value in raw.items()}
    truncated = any(original_counts[key] > len(bounded[key]) for key in raw)
    ledger_payload = {
        "requests": [item.model_dump(mode="json") for item in bounded["requests"]],
        "responses": [item.model_dump(mode="json") for item in bounded["responses"]],
        "failures": [item.model_dump(mode="json") for item in bounded["failures"]],
        "console": [item.model_dump(mode="json") for item in bounded["console"]],
        "page_errors": [item.model_dump(mode="json") for item in bounded["page_errors"]],
        "health": (health or BrowserHealthMetadata()).model_dump(mode="json"),
        "max_records": max_count,
        "truncated": truncated,
        "original_counts": original_counts,
    }
    return BrowserNetworkLedger(
        **ledger_payload,
        ledger_sha256=hash_browser_network_ledger_payload(ledger_payload),
    )


def minimal_browser_network_ledger(
    *,
    final_url: str,
    status_code: int,
    content_type: str,
    renderer: str = "injected_renderer",
    max_records: int = 200,
) -> BrowserNetworkLedger:
    request = BrowserRequestRecord(id="r1", method="GET", url=final_url, resource_type="document")
    response = BrowserResponseRecord(
        request_id="r1",
        url=final_url,
        status=status_code if 100 <= status_code <= 599 else None,
        ok=200 <= status_code <= 299,
        content_type=content_type,
    )
    return build_browser_network_ledger(
        requests=[request],
        responses=[response],
        health=BrowserHealthMetadata(renderer=renderer, status="captured", page_url=final_url),
        max_records=max_records,
    )


def _jsonable(value):
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    return value


def hash_browser_network_ledger_payload(payload: Mapping) -> str:
    canonical = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_browser_network_ledger_hash(ledger: Mapping, expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {key: value for key, value in ledger.items() if key != "ledger_sha256"}
    return hash_browser_network_ledger_payload(payload) == expected_hash
