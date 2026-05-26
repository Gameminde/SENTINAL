from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from sentinel.power_lab import PowerLabMissionRejected, run_power_lab_mission


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel", description="Sentinel Control operator shell.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a structured Sentinel mission file.")
    run_parser.add_argument("--mission", required=True, help="Path to a JSON mission file.")
    run_parser.add_argument("--run-root", required=True, help="Directory where run artifacts are written.")
    run_parser.add_argument("--preset", default=None, help="Override mission preset.")
    run_parser.add_argument(
        "--enable-organ-dispatch",
        action="store_true",
        help="Explicitly enable existing opt-in organ dispatch for supported presets.",
    )
    run_parser.add_argument(
        "--enable-brain-native",
        action="store_true",
        help="Explicitly enable BrainCognitionLoop as native proposal source.",
    )
    run_parser.add_argument(
        "--enable-memory-feedback",
        action="store_true",
        help="Explicitly enable memory feedback when organ dispatch is enabled.",
    )
    run_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        try:
            result = run_power_lab_mission(
                Path(args.mission),
                run_root=Path(args.run_root),
                preset=args.preset,
                enable_organ_dispatch=bool(args.enable_organ_dispatch),
                enable_brain_native=bool(args.enable_brain_native),
                enable_memory_feedback=bool(args.enable_memory_feedback),
            )
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), sort_keys=True, default=str))
        else:
            print(
                "sentinel run "
                f"mission_id={result.mission_id} "
                f"status={result.status.value} "
                f"run_dir={result.run_dir}"
            )
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
