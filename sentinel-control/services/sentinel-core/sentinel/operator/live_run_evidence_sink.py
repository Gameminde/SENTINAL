from __future__ import annotations

import json
import os
import re
import threading
from builtins import open as builtin_open
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import utc_now
from sentinel.operator.redaction import redact_operator_text
from sentinel.shared.safety_scanner import SHARED_SECRET_LIKE_PATTERN


_RUN_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.:-]+")
_MAX_SAFE_STRING_CHARS = 1200
_MAX_EVENT_BYTES = 32_768
_MAX_EVENTS = 512

_RAW_MATERIAL_KEY_MARKERS = (
    "raw_provider",
    "provider_output",
    "provider_response",
    "raw_response",
    "raw_prompt",
    "raw_dom",
    "dom_dump",
    "screenshot",
    "selector",
    "binary_path",
    "chain_of_thought",
    "reasoning",
    "private_thought",
    "private_chain",
)

_HASH_ONLY_KEY_MARKERS = (
    "query",
    "url",
    "uri",
    "target",
    "selector",
)

_SECRET_KEY_MARKERS = (
    "api_key",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "refresh_token",
    "secret",
    "session_cookie",
    "session_token",
    "token",
    "x_api_key",
)

_SESSION_MATERIAL_KEY_MARKERS = (
    "browser_profile",
    "profile_material",
    "session_material",
    "storage_state",
)

_ASSESSMENT_FIELDS = (
    "perceived_blocker",
    "failure_interpretation",
    "proposed_next_strategy",
    "required_evidence",
    "missing_capability",
    "objective_satisfied",
    "confidence",
)


class CrashSafeBoundedLiveRunEvidenceSink:
    """Crash-safe bounded safe-evidence journal for live product runs.

    The sink is intentionally not a receipt or authority source. It mirrors
    safe transition facts so stdout truncation, report rendering errors and
    cleanup cannot erase the run's minimum observable truth.
    """

    def __init__(
        self,
        *,
        evidence_root: Path | str,
        run_id: str,
        max_events: int = _MAX_EVENTS,
        max_event_bytes: int = _MAX_EVENT_BYTES,
    ) -> None:
        self.evidence_root = Path(evidence_root).resolve()
        safe_run_id = _safe_run_id(run_id)
        self.run_id = safe_run_id
        self.run_dir = self.evidence_root / safe_run_id
        os.makedirs(_fs_path(self.run_dir), exist_ok=True)
        self.event_log_path = self.run_dir / "safe_evidence_events.jsonl"
        self.snapshot_path = self.run_dir / "safe_evidence_snapshot.json"
        self.max_events = max_events
        self.max_event_bytes = max_event_bytes
        self._lock = threading.RLock()
        self._events: list[dict[str, Any]] = []
        self._previous_hash: str | None = None
        self._summary = {
            "run_id": self.run_id,
            "provider_decision_count": 0,
            "action_sequence": [],
            "material_receipt_count": 0,
            "finalgate_result_count": 0,
            "cleanup_recorded": False,
            "terminal_verdict": None,
            "raw_material_persisted": False,
            "data_not_authority": True,
            "can_execute": False,
            "can_grant_authority": False,
        }
        self._write_snapshot()

    def record_transition(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if len(self._events) >= self.max_events:
                payload = {
                    "dropped_event_type": str(event_type),
                    "reason": "max_events_exceeded",
                    "data_not_authority": True,
                    "can_execute": False,
                }
                event_type = "evidence_event_dropped"
            event_payload = _sanitize_payload(payload or {})
            event_payload = _bound_event_payload(event_payload, self.max_event_bytes)
            event = {
                "run_id": self.run_id,
                "sequence": len(self._events),
                "event_type": _safe_event_type(event_type),
                "created_at": utc_now().isoformat(),
                "payload": event_payload,
                "previous_hash": self._previous_hash,
                "event_hash": "",
                "data_not_authority": True,
                "can_execute": False,
                "can_grant_authority": False,
            }
            event["event_hash"] = stable_hash({**event, "event_hash": ""})
            self._events.append(event)
            self._previous_hash = str(event["event_hash"])
            self._update_summary(event)
            self._append_event(event)
            self._write_snapshot()
            return event

    def load_snapshot(self) -> dict[str, Any]:
        with builtin_open(_fs_path(self.snapshot_path), encoding="utf-8") as handle:
            return json.load(handle)

    def _append_event(self, event: dict[str, Any]) -> None:
        with builtin_open(_fs_path(self.event_log_path), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _write_snapshot(self) -> None:
        payload = {
            "schema_version": "crash-safe-live-run-evidence/v1",
            "run_id": self.run_id,
            "event_count": len(self._events),
            "event_log_ref": f"safe_evidence_events:{text_hash(str(self.event_log_path.name))[:16]}",
            "summary": dict(self._summary),
            "events": list(self._events),
            "latest_event_hash": self._previous_hash,
            "local_integrity_hash": "",
            "data_not_authority": True,
            "can_execute": False,
            "can_grant_authority": False,
        }
        payload["local_integrity_hash"] = stable_hash({**payload, "local_integrity_hash": ""})
        _atomic_write_json(self.snapshot_path, payload)

    def _update_summary(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type == "provider_decision_received":
            self._summary["provider_decision_count"] = int(self._summary["provider_decision_count"]) + 1
        if event_type == "action_envelope_accepted":
            capability = str(payload.get("capability_id") or "")
            operation = str(payload.get("operation") or "")
            if capability and operation:
                sequence = list(self._summary["action_sequence"])
                sequence.append(f"{capability}.{operation}")
                self._summary["action_sequence"] = sequence
        if event_type == "material_receipt_created":
            self._summary["material_receipt_count"] = int(self._summary["material_receipt_count"]) + 1
        if event_type == "FinalGate_result":
            self._summary["finalgate_result_count"] = int(self._summary["finalgate_result_count"]) + 1
        if event_type == "cleanup_result":
            self._summary["cleanup_recorded"] = True
        if event_type == "terminal_verdict":
            verdict = str(payload.get("verdict") or payload.get("status") or "")
            self._summary["terminal_verdict"] = verdict.lower() if verdict else None


def safe_model_operational_assessment(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("model_blocker_assessment")
    if not isinstance(candidate, dict):
        candidate = {
            key: payload[key]
            for key in _ASSESSMENT_FIELDS
            if key in payload
        }
    if not isinstance(candidate, dict) or not candidate:
        return None
    assessment: dict[str, Any] = {}
    for key in _ASSESSMENT_FIELDS:
        value = candidate.get(key)
        if value is None:
            assessment[key] = None
        elif key in {"objective_satisfied"}:
            assessment[key] = bool(value)
        elif key in {"confidence"}:
            try:
                assessment[key] = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                assessment[key] = None
        else:
            text = redact_operator_text(str(value))
            assessment[key] = text[:_MAX_SAFE_STRING_CHARS]
    assessment["advisory"] = True
    assessment["data_not_authority"] = True
    return assessment


def _safe_run_id(run_id: str) -> str:
    safe = _RUN_ID_PATTERN.sub("_", str(run_id).strip())[:120].strip("._-")
    return safe or "live_run"


def _safe_event_type(event_type: str) -> str:
    return _RUN_ID_PATTERN.sub("_", str(event_type).strip())[:120] or "transition"


def _sanitize_payload(value: Any, *, key: str = "") -> Any:
    if hasattr(value, "safe_model_dump") and callable(value.safe_model_dump):
        value = value.safe_model_dump()
    elif hasattr(value, "model_dump") and callable(value.model_dump):
        value = value.model_dump(mode="json")
    normalized_key = key.lower()
    if _key_contains(normalized_key, _RAW_MATERIAL_KEY_MARKERS):
        return _redacted_hash(value, reason=key or "raw_material")
    if _key_contains(normalized_key, _SESSION_MATERIAL_KEY_MARKERS):
        return _redacted_hash(value, reason="session_or_profile_material")
    if _key_contains(normalized_key, _SECRET_KEY_MARKERS):
        return _redacted_hash(value, reason="session_or_cookie_material" if "cookie" in normalized_key or "session" in normalized_key else "secret_value")
    if _key_contains(normalized_key, _HASH_ONLY_KEY_MARKERS) and isinstance(value, str):
        return _redacted_hash(value, reason=key or "sensitive_locator_or_target")
    if isinstance(value, dict):
        sanitized = {str(item_key): _sanitize_payload(item_value, key=str(item_key)) for item_key, item_value in value.items()}
        if key == "runtime_failure_fact":
            sanitized["authoritative"] = True
            sanitized["data_not_authority"] = True
        if key == "model_blocker_assessment":
            assessment = safe_model_operational_assessment({"model_blocker_assessment": sanitized})
            return assessment if assessment is not None else {"advisory": True, "data_not_authority": True}
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_payload(item, key=key) for item in list(value)[:64]]
    if isinstance(value, str):
        redacted = redact_operator_text(value)
        if redacted != value or SHARED_SECRET_LIKE_PATTERN.search(value):
            return _redacted_hash(value, reason="secret_value")
        if len(value) > _MAX_SAFE_STRING_CHARS:
            return {
                "truncated": True,
                "char_count": len(value),
                "sha256": text_hash(value),
                "safe_prefix": value[:160],
                "data_not_authority": True,
            }
        return value
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(type(value).__name__)


def _bound_event_payload(payload: dict[str, Any], max_event_bytes: int) -> dict[str, Any]:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    if len(rendered.encode("utf-8")) <= max_event_bytes:
        return payload
    return {
        "payload_truncated": True,
        "payload_hash": stable_hash(payload),
        "payload_bytes": len(rendered.encode("utf-8")),
        "data_not_authority": True,
        "can_execute": False,
    }


def _redacted_hash(value: Any, *, reason: str) -> dict[str, Any]:
    rendered = json.dumps(value, sort_keys=True, default=str) if not isinstance(value, str) else value
    return {
        "redacted": reason,
        "sha256": text_hash(rendered),
        "data_not_authority": True,
    }


def _key_contains(key: str, markers: tuple[str, ...]) -> bool:
    return any(marker in key for marker in markers)


def _atomic_write_json(path: Path, payload: Any) -> None:
    os.makedirs(_fs_path(path.parent), exist_ok=True)
    rendered = json.dumps(payload, sort_keys=True, indent=2, default=str)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=_fs_path(path.parent),
        prefix=".tmp.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = handle.name
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(_fs_path(temp_path), _fs_path(path))


def _fs_path(path: Path | str) -> str:
    rendered = str(path)
    if os.name != "nt":
        return rendered
    if rendered.startswith("\\\\?\\"):
        return rendered
    absolute = str(Path(rendered).resolve())
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute


__all__ = [
    "CrashSafeBoundedLiveRunEvidenceSink",
    "safe_model_operational_assessment",
]
