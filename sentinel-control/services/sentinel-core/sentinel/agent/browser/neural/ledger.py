from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.browser.neural.models import stable_neural_hash
from sentinel.agent.organs.safety_scanner import scan_secret_like_text
from sentinel.shared.models import SentinelModel, new_id


class BrowserNeuralLedgerIntegrityError(RuntimeError):
    pass


_LEDGER_LOCKS_GUARD = threading.Lock()
_LEDGER_LOCKS: dict[str, threading.RLock] = {}


def _ledger_lock(path: Path) -> threading.RLock:
    key = str(path.resolve(strict=False))
    with _LEDGER_LOCKS_GUARD:
        lock = _LEDGER_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LEDGER_LOCKS[key] = lock
        return lock


class BrowserNeuralLedgerEvent(SentinelModel):
    event_id: str = Field(default_factory=lambda: new_id("bnledger"))
    workflow_id: str
    run_id: str
    call_id: str | None = None
    event_type: str
    actor_or_neuron_id: str
    refs: dict[str, str] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    previous_hash: str | None = None
    event_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False

    @model_validator(mode="after")
    def _ledger_event_is_data_only(self) -> "BrowserNeuralLedgerEvent":
        if not self.data_not_instruction:
            raise ValueError("browser_neural_ledger_event_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("browser_neural_ledger_event_cannot_enable_authority_or_execution")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("browser_neural_ledger_event_cannot_enable_authority_or_execution")
        return self


class BrowserNeuralReceiptLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve(strict=False)
        self._lock = _ledger_lock(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        workflow_id: str,
        run_id: str,
        event_type: str,
        actor_or_neuron_id: str,
        refs: dict[str, Any],
        state: dict[str, Any],
        call_id: str | None = None,
    ) -> BrowserNeuralLedgerEvent:
        with self._lock:
            previous_hash = self._last_hash()
            risk_flags: set[str] = set()
            safe_state = _sanitize_for_ledger(state, risk_flags=risk_flags)
            safe_refs = {
                str(key): str(_sanitize_for_ledger(value, key=str(key), risk_flags=risk_flags))
                for key, value in sorted(refs.items(), key=lambda item: str(item[0]))
            }
            created_at = datetime.now(UTC)
            base = {
                "event_id": new_id("bnledger"),
                "workflow_id": workflow_id,
                "run_id": run_id,
                "call_id": call_id,
                "event_type": event_type,
                "actor_or_neuron_id": actor_or_neuron_id,
                "refs": safe_refs,
                "state": safe_state,
                "risk_flags": sorted(risk_flags),
                "previous_hash": previous_hash,
                "created_at": created_at,
                "data_not_instruction": True,
                "authority_effect": "none",
                "execution_effect": "none",
                "can_grant_authority": False,
                "can_approve_future_execution": False,
            }
            event = BrowserNeuralLedgerEvent(**base, event_hash="")
            payload = event.model_dump(mode="json")
            payload.pop("event_hash", None)
            event = event.model_copy(update={"event_hash": stable_neural_hash(payload)})
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
                handle.write("\n")
            return event

    def replay(self) -> list[BrowserNeuralLedgerEvent]:
        with self._lock:
            self.verify_integrity()
            return self._read_events()

    def verify_integrity(self) -> bool:
        with self._lock:
            previous_hash: str | None = None
            for event in self._read_events():
                if event.previous_hash != previous_hash:
                    raise BrowserNeuralLedgerIntegrityError("browser_neural_ledger_previous_hash_mismatch")
                payload = event.model_dump(mode="json")
                stored_hash = payload.pop("event_hash")
                if stable_neural_hash(payload) != stored_hash:
                    raise BrowserNeuralLedgerIntegrityError("browser_neural_ledger_event_hash_mismatch")
                previous_hash = stored_hash
            return True

    def _last_hash(self) -> str | None:
        with self._lock:
            events = self._read_events()
            if not events:
                return None
            self.verify_integrity()
            return events[-1].event_hash

    def _read_events(self) -> list[BrowserNeuralLedgerEvent]:
        if not self.path.exists():
            return []
        events: list[BrowserNeuralLedgerEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(BrowserNeuralLedgerEvent.model_validate(json.loads(line)))
        return events


_SECRETISH_KEYS = {
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "session",
    "token",
    "api_key",
    "bearer",
}


def _sanitize_for_ledger(value: Any, *, risk_flags: set[str], key: str = "$") -> Any:
    key_l = key.lower()
    if any(marker in key_l for marker in _SECRETISH_KEYS):
        risk_flags.add("secret_like_payload_suppressed")
        return "[REDACTED]"
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, str):
        if scan_secret_like_text(value, path=key):
            risk_flags.add("secret_like_payload_suppressed")
            return "[REDACTED]"
        return value
    if isinstance(value, dict):
        return {str(k): _sanitize_for_ledger(v, key=str(k), risk_flags=risk_flags) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_for_ledger(item, key=key, risk_flags=risk_flags) for item in value]
    return value
