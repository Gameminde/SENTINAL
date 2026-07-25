from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.presence_observer import (
    PresenceJsonlJournal,
    PresenceSidecarRelay,
    PresenceSnapshotSidecar,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-presence-observer",
        description="Project persisted safe Sentinel mission artifacts into a read-only Presence Protocol journal.",
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--proof-index", required=True, type=Path)
    parser.add_argument("--mission-ledger", type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.poll_seconds < 0.2:
        raise SystemExit("--poll-seconds must be at least 0.2")
    journal = PresenceJsonlJournal(args.journal)
    relay = PresenceSidecarRelay(journal.append)
    sidecar = PresenceSnapshotSidecar(relay)
    total_emitted = 0

    try:
        while True:
            snapshot = _load_json(args.snapshot, required=True)
            proof_index = _load_json(args.proof_index, required=False)
            mission_ledger = _load_json(args.mission_ledger, required=False) if args.mission_ledger else {}
            emitted = sidecar.observe(
                safe_evidence_snapshot=snapshot,
                proof_index=proof_index,
                mission_ledger=mission_ledger,
            )
            total_emitted += emitted
            if args.once:
                break
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "status": "observer_blocked",
                    "exception_class": exc.__class__.__name__,
                    "failure_hash": stable_hash(
                        {
                            "exception_class": exc.__class__.__name__,
                            "total_emitted": total_emitted,
                        }
                    ),
                    "raw_exception_persisted": False,
                    "data_not_authority": True,
                    "can_execute": False,
                },
                sort_keys=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": "observer_stopped" if not args.once else "observer_once_completed",
                "events_emitted": total_emitted,
                "relay_failure_count": relay.failure_count,
                "relay_last_failure_hash": relay.last_failure_hash,
                "data_not_authority": True,
                "can_execute": False,
            },
            sort_keys=True,
        )
    )
    return 0


def _load_json(path: Path, *, required: bool) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if not required:
            return {}
        raise
    if not isinstance(value, dict):
        raise ValueError("presence observer input must be a JSON object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
