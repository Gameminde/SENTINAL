from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.credential_vault_models import (
    CredentialVaultConfig,
    SecretAccessGrant,
    SecretAccessLease,
    SecretCheckoutResult,
    SecretLeakScanResult,
    SecretMetadata,
    SecretReplayView,
    SecretRevocationRecord,
    SecretUseReceipt,
    VaultUnlockSession,
)
from sentinel.operator.store import MissionRunStore


class CredentialVaultReplayBuilder:
    def __init__(self, store: Any) -> None:
        self._store = getattr(store, "_mission_store", store)
        if not isinstance(self._store, MissionRunStore):
            self._store = store

    def build(self, mission_id: str) -> SecretReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", CredentialVaultConfig)
        secrets = _load_many(root / "secrets", SecretMetadata)
        sessions = _load_many(root / "unlock_sessions", VaultUnlockSession)
        grants = _load_many(root / "grants", SecretAccessGrant)
        leases = _load_many(root / "leases", SecretAccessLease)
        checkouts = _load_many(root / "checkouts", SecretCheckoutResult)
        receipts = _load_many(root / "receipts", SecretUseReceipt)
        revocations = _load_many(root / "revocations", SecretRevocationRecord)
        leak_scans = _load_many(root / "leak_scans", SecretLeakScanResult)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (configs, secrets, sessions, grants, leases):
            for item in collection:
                verifier = getattr(item, "verify_hash", None)
                if callable(verifier) and not verifier():
                    tampered = True
        events = [event for event in self._store.load_events(mission_id) if event.event_type.startswith(("credential_vault_", "secret_"))]
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        for receipt in receipts:
            receipt_refs.append(receipt.receipt_id)
            if receipt.finalgate_certificate is not None:
                finalgate_refs.append(receipt.finalgate_certificate.certificate_id)
        for event in events:
            receipt_refs.extend(event.receipt_refs)
            finalgate_refs.extend(event.finalgate_certificate_refs)
        return SecretReplayView(
            mission_id=mission_id,
            configs=configs,
            secret_metadata=secrets,
            unlock_sessions=sessions,
            grants=grants,
            leases=leases,
            checkout_results=checkouts,
            use_receipts=receipts,
            revocations=revocations,
            leak_scans=leak_scans,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            tampered=tampered,
            materialized_secret=False,
            unlocked_vault=False,
            called_os_keychain=False,
            called_provider_api=False,
            replayed_login=False,
            sent_channel_message=False,
            filled_desktop_field=False,
            invoked_model_provider=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id, create=True) / "credential_vault"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
