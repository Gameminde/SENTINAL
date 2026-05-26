from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
    BrowserOperatorAgentL4L5Live,
    BrowserOperatorLiveActionKind,
    BrowserOperatorLiveContract,
    BrowserOperatorLiveRequest,
)
from sentinel.organs.browser.playwright_interaction_backend import PlaywrightLimitedInteractionBackend
from sentinel.organs.browser.playwright_renderer import PlaywrightReadOnlyRenderer
from sentinel.power_lab import PowerLabMissionRejected, load_power_lab_mission_file, run_power_lab_mission


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

    observe_parser = subparsers.add_parser("browser-observe", help="Perform a live governed public browser observation.")
    _add_browser_arguments(observe_parser, action=False)

    act_parser = subparsers.add_parser("browser-act", help="Perform one governed limited browser interaction.")
    _add_browser_arguments(act_parser, action=True)
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

    if args.command in {"browser-observe", "browser-act"}:
        try:
            result, run_dir = _run_browser_command(args)
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), sort_keys=True, default=str))
        else:
            print(
                "sentinel browser "
                f"mission_id={result.mission_id} "
                f"status={result.status.value} "
                f"effect={result.execution_effect} "
                f"run_dir={run_dir}"
            )
        return 0 if result.accepted else 2

    parser.print_help()
    return 2


def _add_browser_arguments(parser: argparse.ArgumentParser, *, action: bool) -> None:
    parser.add_argument("--mission", required=True, help="Path to a structured mission authority file.")
    parser.add_argument("--url", required=True, help="HTTPS URL covered by the mission domain allowlist.")
    parser.add_argument("--run-root", required=True, help="Directory where browser evidence artifacts are written.")
    parser.add_argument(
        "--fixture-html",
        default=None,
        help="Development-only HTML fixture served through the real Playwright renderer.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")
    if action:
        parser.add_argument(
            "--action",
            required=True,
            choices=[
                BrowserOperatorLiveActionKind.CLICK.value,
                BrowserOperatorLiveActionKind.TYPE.value,
                BrowserOperatorLiveActionKind.FILL.value,
                BrowserOperatorLiveActionKind.SELECT.value,
                BrowserOperatorLiveActionKind.HOVER.value,
                BrowserOperatorLiveActionKind.WAIT_FOR_TEXT.value,
            ],
            help="Limited interaction action; submit/login/upload/download/JS are not promoted.",
        )
        parser.add_argument("--target-role", default=None)
        parser.add_argument("--target-name", default=None)
        parser.add_argument("--target-nth", type=int, default=0)
        parser.add_argument("--text", default=None)
        parser.add_argument("--value", dest="values", action="append", default=[])


def _run_browser_command(args: argparse.Namespace) -> tuple[object, Path]:
    mission_file = load_power_lab_mission_file(Path(args.mission))
    run_dir = _create_browser_run_dir(Path(args.run_root), mission_file.mission.id)
    fixtures = {args.url: args.fixture_html} if args.fixture_html is not None else None
    operator = BrowserOperatorAgentL4L5Live(
        capture_root=run_dir,
        renderer=PlaywrightReadOnlyRenderer(document_fixtures=fixtures),
        interaction_backend=PlaywrightLimitedInteractionBackend(document_fixtures=fixtures),
    )
    if args.command == "browser-observe":
        contract = BrowserOperatorLiveContract(
            mission_id=mission_file.mission.id,
            allowed_domains=mission_file.mission.allowed_domains,
        )
        result = operator.observe(
            BrowserOperatorLiveRequest(
                mission=mission_file.mission,
                action_kind=BrowserOperatorLiveActionKind.OBSERVE,
                url=args.url,
                contract=contract,
            )
        )
    else:
        action_kind = BrowserOperatorLiveActionKind(args.action)
        contract = BrowserOperatorLiveContract(
            mission_id=mission_file.mission.id,
            allowed_domains=mission_file.mission.allowed_domains,
            allow_l5_interaction=True,
            allowed_action_kinds=[action_kind],
        )
        result = operator.execute(
            BrowserOperatorLiveRequest(
                mission=mission_file.mission,
                action_kind=action_kind,
                url=args.url,
                contract=contract,
                target_role=args.target_role,
                target_name=args.target_name,
                target_nth=args.target_nth,
                text=args.text,
                values=args.values,
            )
        )
    (run_dir / "browser.operator.result.json").write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return result, run_dir


def _create_browser_run_dir(run_root: Path, mission_id: str) -> Path:
    run_root.mkdir(parents=True, exist_ok=True)
    safe_mission_id = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in mission_id)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = run_root / f"{stamp}_{safe_mission_id}_browser"
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
