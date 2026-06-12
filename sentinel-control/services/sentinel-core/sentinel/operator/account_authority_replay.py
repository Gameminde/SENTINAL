from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.account_authority_models import (
    AccountAuthorityConfig,
    AccountAuthorityFinalGateCertificate,
    AccountAuthorityReplayView,
    AccountCreationPlan,
    AccountCreationReceipt,
    AccountLoginPlan,
    AccountLoginReceipt,
    AccountSessionBinding,
    HumanCheckpoint,
)
from sentinel.operator.store import MissionRunStore


class AccountAuthorityReplayBuilder:
    def __init__(self, store: Any) -> None:
        self._store = getattr(store, "_mission_store", store)
        if not isinstance(self._store, MissionRunStore):
            self._store = store

    def build(self, mission_id: str) -> AccountAuthorityReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", AccountAuthorityConfig)
        login_plans = _load_many(root / "login_plans", AccountLoginPlan)
        creation_plans = _load_many(root / "account_creation_plans", AccountCreationPlan)
        login_receipts = _load_many(root / "login_receipts", AccountLoginReceipt)
        creation_receipts = _load_many(root / "account_creation_receipts", AccountCreationReceipt)
        bindings = _load_many(root / "session_bindings", AccountSessionBinding)
        checkpoints = _load_many(root / "checkpoints", HumanCheckpoint)
        finalgate = _load_many(root / "finalgate", AccountAuthorityFinalGateCertificate)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (configs, login_plans, creation_plans):
            for item in collection:
                verifier = getattr(item, "verify_hash", None)
                if callable(verifier) and not verifier():
                    tampered = True
        events = [event for event in self._store.load_events(mission_id) if event.event_type.startswith("account_")]
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        for receipt in [*login_receipts, *creation_receipts]:
            receipt_refs.append(receipt.receipt_id)
        for certificate in finalgate:
            finalgate_refs.append(certificate.certificate_id)
        for event in events:
            receipt_refs.extend(event.receipt_refs)
            finalgate_refs.extend(event.finalgate_certificate_refs)
        return AccountAuthorityReplayView(
            mission_id=mission_id,
            configs=configs,
            login_plans=login_plans,
            account_creation_plans=creation_plans,
            login_receipts=login_receipts,
            account_creation_receipts=creation_receipts,
            session_bindings=bindings,
            checkpoints=checkpoints,
            finalgate_certificates=finalgate,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            tampered=tampered,
            replayed_login=False,
            created_live_account=False,
            materialized_credential=False,
            called_provider_api=False,
            executed_browser_action=False,
            solved_captcha=False,
            bypassed_mfa=False,
            bypassed_kyc=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id, create=True) / "account_authority"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


__all__ = ["AccountAuthorityReplayBuilder"]
