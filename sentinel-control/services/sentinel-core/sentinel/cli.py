from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
    BrowserOperatorAgentL4L5Live,
    BrowserOperatorLiveActionKind,
    BrowserOperatorLiveContract,
    BrowserOperatorLiveRequest,
)
from sentinel.agent.organs.browser_session_manager_l5_live import (
    BrowserSessionActionKind,
    BrowserSessionContract,
    BrowserSessionManagerL5Live,
    BrowserSessionRequest,
)
from sentinel.agent.organs.browser_trajectory_planner_l5 import (
    BrowserTrajectoryActionKind,
    BrowserTrajectoryContract,
    BrowserTrajectoryPlannerL5,
    BrowserTrajectoryRequest,
)
from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
    BrowserFormSubmitContract,
    BrowserFormSubmitRequest,
    BrowserFormSubmitSpecialAuthorityL6,
)
from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
    BrowserLoginCredentialSessionBrokerL6,
    BrowserLoginCredentialSessionContract,
    BrowserLoginCredentialSessionRequest,
    EphemeralBrowserCredentialProvider,
)
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope
from sentinel.operator.canonical_core import (
    CanonicalCoreError,
    CanonicalDecisionRequest,
    run_canonical_dev_mission,
    run_canonical_product_mission,
)
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.legacy_classification import InternalAccessClassification
from sentinel.operator.mission_lifecycle_service import (
    PROVIDER_DECISION_TIMEOUT_SECONDS_MAX,
    PROVIDER_DECISION_TIMEOUT_SECONDS_MIN,
)
from sentinel.operator.model_client import OperatorCatalogModelClient
from sentinel.operator.models import (
    OperatorConversationState,
    OperatorMode,
    OperatorTurnResult,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.product_execution_binding import (
    ProductExecutionBindingError,
    build_product_execution_binding,
)
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.operator.read_only_model_clients import ReadOnlyProviderDecisionClient, ReadOnlyProviderReportClient
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.structured_output import READ_ONLY_RESEARCH_CAPABILITY
from sentinel.organs.browser.playwright_interaction_backend import PlaywrightLimitedInteractionBackend
from sentinel.organs.browser.playwright_renderer import PlaywrightReadOnlyRenderer
from sentinel.power_lab import PowerLabMissionRejected, load_power_lab_mission_file, run_power_lab_mission
from sentinel.shared.models import SentinelModel


class CanonicalProductPublicRunResult(SentinelModel):
    root_mission_id: str
    status: str
    final_reason: str
    blocked_reason: str | None = None
    provider_decision_count: int
    material_action_count: int
    mission_record_created_before_provider: bool
    root_created_before_first_provider_call: bool
    mission_ids: tuple[str, ...] = ()
    dispatch_mission_ids: tuple[str, ...] = ()
    product_receipt_refs: tuple[str, ...] = ()
    product_finalgate_refs: tuple[str, ...] = ()
    certificate_refs: tuple[str, ...] = ()
    proof_root: dict[str, Any]
    replay: dict[str, Any]
    public_product_spine: dict[str, Any]
    cleanup_completed: bool


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

    for cockpit_command in ("cockpit", "chat"):
        cockpit_parser = subparsers.add_parser(
            cockpit_command,
            help="Start the LLM live operator cockpit. Alias: chat.",
        )
        cockpit_parser.add_argument("--run-root", required=True, help="Directory where local cockpit mission state is written.")
        cockpit_parser.add_argument(
            "--model-contract",
            default=None,
            help="Explicit UserModelContract JSON for product LLM mode. Required unless deterministic test mode is set.",
        )
        cockpit_parser.add_argument(
            "--deterministic-test-mode",
            action="store_true",
            help="Use deterministic offline test mode; not a product LLM mode.",
        )
        cockpit_parser.add_argument("--once", default=None, help="Process one user message and exit.")
        cockpit_parser.add_argument("--script", default=None, help="Read newline-delimited user messages from a text file.")
        cockpit_parser.add_argument(
            "--workspace",
            default=None,
            help="Explicit governed local workspace directory for product read-only research missions.",
        )
        cockpit_parser.add_argument(
            "--authority-scope",
            default=None,
            help="Explicit MissionAuthorityApprovalScope JSON file for governed product mission starts.",
        )
        cockpit_parser.add_argument(
            "--legacy-internal-direct",
            action="store_true",
            help="Use the old direct-kernel cockpit path. Classified LEGACY_INTERNAL and not a product route.",
        )
        cockpit_parser.add_argument(
            "--explicit-mission-bootstrap",
            action="store_true",
            help=(
                "Create a governed product-script mission draft from explicit local inputs. "
                "Requires --script, --workspace, --authority-scope, --model-contract and --json."
            ),
        )
        cockpit_parser.add_argument(
            "--stop-after-first-material-receipt",
            action="store_true",
            help="Explicit product run mode: terminalize after the first governed material read-only receipt.",
        )
        cockpit_parser.add_argument(
            "--low-friction-read-only-power-mode",
            action="store_true",
            help=(
                "Explicit product run mode: allow autonomous in-scope read-only exploration after upfront "
                "workspace authority. Requires --explicit-mission-bootstrap and first-receipt or model-led autopilot mode."
            ),
        )
        cockpit_parser.add_argument(
            "--model-led-read-only-autopilot",
            action="store_true",
            help="Explicit Pack 4A product run mode: continue governed read-only actions until finish or budget.",
        )
        cockpit_parser.add_argument(
            "--max-material-receipts",
            type=int,
            default=None,
            help="Pack 4A model-led autopilot material receipt budget.",
        )
        cockpit_parser.add_argument(
            "--max-provider-decision-calls",
            type=int,
            default=None,
            help="Pack 4A model-led autopilot provider decision-call budget.",
        )
        cockpit_parser.add_argument(
            "--provider-decision-timeout-seconds",
            type=int,
            default=None,
            help=(
                "Pack 4B.1 model-led autopilot read-only provider decision timeout "
                f"({PROVIDER_DECISION_TIMEOUT_SECONDS_MIN}-{PROVIDER_DECISION_TIMEOUT_SECONDS_MAX} seconds)."
            ),
        )
        cockpit_parser.add_argument(
            "--generate-read-only-mission-summary",
            action="store_true",
            help="Pack 4B model-led autopilot option: persist a safe non-authority read-only mission summary artifact.",
        )
        cockpit_parser.add_argument(
            "--write-operator-memory-candidate",
            action="store_true",
            help="Pack 4B model-led autopilot option: persist a revocable non-authority operator memory candidate artifact.",
        )
        cockpit_parser.add_argument("--json", action="store_true", help="Print machine-readable turn summaries.")

    canonical_parser = subparsers.add_parser(
        "canonical-dev-run",
        help="Run the Sentinel canonical core development vertical slice with a local decision script.",
    )
    canonical_parser.add_argument("--objective", required=True, help="Mission objective presented to the model client.")
    canonical_parser.add_argument("--workspace", required=True, help="Governed workspace root for read-only workspace skills.")
    canonical_parser.add_argument("--decision-script", required=True, help="JSONL local decision script for deterministic dev proof.")
    canonical_parser.add_argument("--provider-model", required=True, help="Provider/model identity label for the decision stream.")
    canonical_parser.add_argument("--max-provider-decisions", type=int, default=40)
    canonical_parser.add_argument("--max-material-actions", type=int, default=120)
    canonical_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")

    canonical_product_parser = subparsers.add_parser(
        "canonical-product-run",
        help="Run the Sentinel canonical core through a kernel-backed product mission.",
    )
    canonical_product_parser.add_argument("--objective", required=True, help="Mission objective presented to the model client.")
    canonical_product_parser.add_argument("--workspace", required=True, help="Governed workspace root for read-only workspace skills.")
    canonical_product_parser.add_argument("--run-root", required=True, help="Directory where MissionKernel artifacts are written.")
    canonical_product_parser.add_argument(
        "--decision-script",
        default=None,
        help="JSONL local decision script for deterministic product-path validation. Omit for real provider mode.",
    )
    canonical_product_parser.add_argument(
        "--provider-model",
        default=None,
        help="Legacy provider/model identity label for scripted mode. In real provider mode defaults to provider/model.",
    )
    canonical_product_parser.add_argument("--provider-id", default=None, help="Catalog provider id for real provider mode.")
    canonical_product_parser.add_argument("--backend-id", default=None, help="Catalog backend id for real provider mode.")
    canonical_product_parser.add_argument("--model-id", default=None, help="Catalog model id for real provider mode.")
    canonical_product_parser.add_argument("--max-provider-decisions", type=int, default=40)
    canonical_product_parser.add_argument("--max-material-actions", type=int, default=120)
    canonical_product_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")

    observe_parser = subparsers.add_parser("browser-observe", help="Perform a live governed public browser observation.")
    _add_browser_arguments(observe_parser, action=False)

    act_parser = subparsers.add_parser("browser-act", help="Perform one governed limited browser interaction.")
    _add_browser_arguments(act_parser, action=True)

    session_parser = subparsers.add_parser(
        "browser-session-demo",
        help="Run a governed persistent browser session workflow through CloakBrowser or the compatibility engine.",
    )
    session_parser.add_argument("--mission", required=True, help="Path to a structured mission authority file.")
    session_parser.add_argument("--url", required=True, help="HTTPS URL covered by the mission domain allowlist.")
    session_parser.add_argument("--run-root", required=True, help="Directory where session evidence artifacts are written.")
    session_parser.add_argument(
        "--engine",
        default="cloak",
        choices=["cloak", "playwright"],
        help="Browser engine. CloakBrowser is primary; Playwright is a compatibility/test engine.",
    )
    session_parser.add_argument(
        "--fixture-html",
        default=None,
        help="Development-only HTML fixture served through the selected browser engine.",
    )
    session_parser.add_argument("--target-role", required=True)
    session_parser.add_argument("--target-name", required=True)
    session_parser.add_argument("--text", required=True)
    session_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")

    trajectory_parser = subparsers.add_parser(
        "browser-trajectory-demo",
        help="Run a governed browser trajectory with ranked target recovery in a persistent session.",
    )
    trajectory_parser.add_argument("--mission", required=True, help="Path to a structured mission authority file.")
    trajectory_parser.add_argument("--url", required=True, help="HTTPS URL covered by the mission domain allowlist.")
    trajectory_parser.add_argument("--run-root", required=True, help="Directory where trajectory evidence artifacts are written.")
    trajectory_parser.add_argument("--engine", default="cloak", choices=["cloak", "playwright"])
    trajectory_parser.add_argument("--fixture-html", default=None)
    trajectory_parser.add_argument("--target-role", required=True)
    trajectory_parser.add_argument("--target-hint", required=True)
    trajectory_parser.add_argument("--text", required=True)
    trajectory_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")

    submit_parser = subparsers.add_parser(
        "browser-submit-demo",
        help="Run one governed special-authority browser form submit in a persistent session.",
    )
    submit_parser.add_argument("--mission", required=True, help="Path to a structured mission authority file.")
    submit_parser.add_argument("--url", required=True, help="HTTPS URL covered by the mission domain allowlist.")
    submit_parser.add_argument("--run-root", required=True, help="Directory where submit evidence artifacts are written.")
    submit_parser.add_argument("--engine", default="cloak", choices=["cloak", "playwright"])
    submit_parser.add_argument("--fixture-html", default=None)
    submit_parser.add_argument("--input-role", default="textbox")
    submit_parser.add_argument("--input-name", required=True)
    submit_parser.add_argument("--text", required=True)
    submit_parser.add_argument("--submit-role", default="button")
    submit_parser.add_argument("--submit-name", required=True)
    submit_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")

    login_parser = subparsers.add_parser(
        "browser-login-demo",
        help="Run one governed credential-backed browser login using env-sourced ephemeral credential values.",
    )
    login_parser.add_argument("--mission", required=True, help="Path to a structured mission authority file.")
    login_parser.add_argument("--url", required=True, help="HTTPS URL covered by the mission domain allowlist.")
    login_parser.add_argument("--run-root", required=True, help="Directory where login evidence artifacts are written.")
    login_parser.add_argument("--engine", default="cloak", choices=["cloak", "playwright"])
    login_parser.add_argument("--fixture-html", default=None)
    login_parser.add_argument("--username-ref", required=True)
    login_parser.add_argument("--password-ref", required=True)
    login_parser.add_argument("--username-env", required=True)
    login_parser.add_argument("--password-env", required=True)
    login_parser.add_argument("--username-name", required=True)
    login_parser.add_argument("--password-name", required=True)
    login_parser.add_argument("--submit-name", required=True)
    login_parser.add_argument("--json", action="store_true", help="Print machine-readable result summary.")
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

    if args.command in {"cockpit", "chat"}:
        return _run_cockpit_command(args)

    if args.command == "canonical-dev-run":
        try:
            result = _run_canonical_dev_command(args)
        except (CanonicalCoreError, OSError, json.JSONDecodeError) as exc:
            print(f"sentinel canonical-dev-run: rejected:{exc.__class__.__name__}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), sort_keys=True, default=str))
        else:
            print(
                "sentinel canonical_dev_run "
                f"root_mission_id={result.root_mission_id} "
                f"status={result.status} "
                f"provider_decisions={result.provider_decision_count} "
                f"material_actions={result.material_action_count}"
            )
        return 0 if result.status == "completed" else 2

    if args.command == "canonical-product-run":
        try:
            result = _run_canonical_product_command(args)
        except (CanonicalCoreError, OSError, json.JSONDecodeError) as exc:
            print(f"sentinel canonical-product-run: rejected:{exc.__class__.__name__}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), sort_keys=True, default=str))
        else:
            print(
                "sentinel canonical_product_run "
                f"root_mission_id={result.root_mission_id} "
                f"status={result.status} "
                f"provider_decisions={result.provider_decision_count} "
                f"material_actions={result.material_action_count}"
            )
        return 0 if result.status == "completed" else 2

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

    if args.command == "browser-session-demo":
        try:
            result, run_dir = _run_browser_session_demo(args)
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result, sort_keys=True, default=str))
        else:
            print(
                "sentinel browser_session_workflow "
                f"mission_id={result['mission_id']} "
                f"status={result['status']} "
                f"engine={args.engine} "
                f"run_dir={run_dir}"
            )
        return 0 if result["accepted"] else 2

    if args.command == "browser-trajectory-demo":
        try:
            result, run_dir = _run_browser_trajectory_demo(args)
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result, sort_keys=True, default=str))
        else:
            print(
                "sentinel browser_trajectory_workflow "
                f"mission_id={result['mission_id']} "
                f"status={result['status']} "
                f"engine={args.engine} "
                f"run_dir={run_dir}"
            )
        return 0 if result["accepted"] else 2

    if args.command == "browser-submit-demo":
        try:
            result, run_dir = _run_browser_submit_demo(args)
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result, sort_keys=True, default=str))
        else:
            print(
                "sentinel browser_submit_workflow "
                f"mission_id={result['mission_id']} "
                f"status={result['status']} "
                f"engine={args.engine} "
                f"run_dir={run_dir}"
            )
        return 0 if result["accepted"] else 2

    if args.command == "browser-login-demo":
        try:
            result, run_dir = _run_browser_login_demo(args)
        except PowerLabMissionRejected as exc:
            print(f"sentinel: rejected: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result, sort_keys=True, default=str))
        else:
            print(
                "sentinel browser_login_workflow "
                f"mission_id={result['mission_id']} "
                f"status={result['status']} "
                f"engine={args.engine} "
                f"run_dir={run_dir}"
            )
        return 0 if result["accepted"] else 2

    parser.print_help()
    return 2


def _run_canonical_dev_command(args: argparse.Namespace):
    model_client = _JsonlCanonicalDecisionScriptClient(Path(args.decision_script))
    return run_canonical_dev_mission(
        objective=str(args.objective),
        workspace_root=Path(args.workspace),
        model_client=model_client,
        provider_model=str(args.provider_model),
        max_provider_decisions=int(args.max_provider_decisions),
        max_material_actions=int(args.max_material_actions),
    )


def _run_canonical_product_command(args: argparse.Namespace):
    run_root = Path(args.run_root)
    workspace = Path(args.workspace)
    provider_model = str(args.provider_model or "scripted-local/model")
    if args.decision_script:
        decision_client = _JsonlCanonicalDecisionScriptClient(Path(args.decision_script))
        decision_client_label = "_JsonlCanonicalDecisionScriptClient"
    else:
        provider_id = str(args.provider_id or os.environ.get("SENTINEL_CANONICAL_MODEL_PROVIDER_ID") or "aliyun_dashscope")
        backend_id = str(
            args.backend_id
            or os.environ.get("SENTINEL_CANONICAL_MODEL_BACKEND_ID")
            or "aliyun_openai_compatible_chat"
        )
        model_id = str(args.model_id or args.provider_model or os.environ.get("SENTINEL_CANONICAL_MODEL_ID") or "deepseek-v4-pro")
        decision_client = _RealProviderCanonicalDecisionClient(
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
        )
        decision_client_label = "_RealProviderCanonicalDecisionClient"
        provider_model = f"{provider_id}/{model_id}"
    host = SentinelRuntimeHost(run_root=run_root)
    cleanup_completed = False
    host.start()
    mission_result = None
    try:
        mission_result = run_canonical_product_mission(
            objective=str(args.objective),
            workspace_root=workspace,
            model_client=decision_client,
            provider_model=provider_model,
            kernel=host.kernel,
            session_id="canonical_product_public_root",
            max_provider_decisions=int(args.max_provider_decisions),
            max_material_actions=int(args.max_material_actions),
        )
    finally:
        cleanup_completed = host.shutdown().status.value == "stopped"
    assert mission_result is not None
    return CanonicalProductPublicRunResult(
        root_mission_id=mission_result.root_mission_id,
        status=mission_result.status,
        final_reason=mission_result.final_reason,
        blocked_reason=mission_result.blocked_reason_detail or None,
        provider_decision_count=mission_result.provider_decision_count,
        material_action_count=mission_result.material_action_count,
        mission_record_created_before_provider=mission_result.mission_record_created_before_provider,
        root_created_before_first_provider_call=mission_result.root_created_before_first_provider_call,
        mission_ids=(mission_result.root_mission_id,),
        dispatch_mission_ids=(mission_result.root_mission_id,),
        product_receipt_refs=tuple(receipt.receipt_id for receipt in mission_result.receipts),
        product_finalgate_refs=(),
        certificate_refs=(),
        proof_root=mission_result.proof_root.safe_model_dump(),
        replay={
            "replay_mode": "mission_kernel_timeline_reconstruction",
            "mission_ids": [mission_result.root_mission_id],
            "receipt_refs": [receipt.receipt_id for receipt in mission_result.receipts],
            "side_effects_reexecuted": False,
            "timeline_verified": host.kernel.store.verify_timeline(mission_result.root_mission_id),
        },
        public_product_spine={
            "strategy": "RUNTIMEHOST_HOSTS_ROOTMISSIONRUNTIME_CANONICAL_WORKSPACE",
            "decision_client": decision_client_label,
            "runtime_entrypoint": "RootMissionRuntime.run",
            "model_decision_protocol": "CanonicalDecision",
            "capability_dispatch": "ProductActionKernel",
            "authority_gate": "RootMissionRuntime authority check plus MissionAuthorityEnvelope backend gate",
            "receipt_owner": "MissionProofRoot/canonical_effect_receipts",
            "proof_root_owner": "MissionProofRoot",
            "legacy_action_envelope_adapter": False,
            "runtimehost_cognition": False,
            "parallel_rootmission_effect_executor_used": False,
        },
        cleanup_completed=cleanup_completed and mission_result.cleanup_completed,
    )


class _RealProviderCanonicalDecisionClient:
    def __init__(self, *, provider_id: str, backend_id: str, model_id: str) -> None:
        self.provider_id = provider_id
        self.backend_id = backend_id
        self.model_id = model_id
        self._contract = _canonical_user_model_contract(
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
        )
        self._client = OperatorCatalogModelClient(user_model_contract=self._contract)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: CanonicalDecisionRequest) -> dict[str, Any]:
        prompt = _canonical_product_provider_prompt(request)
        real_request = _canonical_real_model_request(
            canonical_request=request,
            prompt=prompt,
            provider_id=self.provider_id,
            backend_id=self.backend_id,
            model_id=self.model_id,
            user_model_contract_id=self._contract.id,
        )
        self.requests.append(real_request)
        raw = self._client.complete(real_request)
        return _extract_canonical_json_decision(raw)


class _JsonlCanonicalDecisionScriptClient:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._decisions = self._load(path)
        self.requests: list[CanonicalDecisionRequest] = []

    def complete(self, request: CanonicalDecisionRequest) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise CanonicalCoreError("canonical_dev_decision_script_exhausted")
        return self._decisions.pop(0)

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise CanonicalCoreError("canonical_dev_decision_script_line_must_be_object")
            decisions.append(payload)
        if not decisions:
            raise CanonicalCoreError("canonical_dev_decision_script_empty")
        return decisions


def _canonical_user_model_contract(*, provider_id: str, backend_id: str, model_id: str) -> UserModelContract:
    return UserModelContract(
        selected_provider_id=provider_id,
        selected_backend_id=backend_id,
        selected_model=model_id,
        cost_profile=ModelCostProfile(
            model_name=model_id,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model_id,
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=700,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="canonical_core_workspace_vertical_slice",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _canonical_real_model_request(
    *,
    canonical_request: CanonicalDecisionRequest,
    prompt: str,
    provider_id: str,
    backend_id: str,
    model_id: str,
    user_model_contract_id: str,
) -> RealModelRequest:
    metadata = {
        "raw_text_transport": "product_model_native_intent_v1",
        "canonical_core_product_route": True,
        "mission_id": canonical_request.root_mission_id,
        "canonical_state_hash": canonical_request.canonical_state.state_hash,
        "model_visible_affordances": list(canonical_request.canonical_state.model_visible_affordances),
        "fallback_auto_enabled": False,
        "provider_native_tools_enabled": False,
    }
    prompt_hash = text_hash(prompt)
    hash_payload = {
        "provider_id": provider_id,
        "backend_id": backend_id,
        "model_id": model_id,
        "runtime": "product_model_native_decision",
        "prompt_hash": prompt_hash,
        "frame_hash": canonical_request.canonical_state.state_hash,
        "user_model_contract_id": user_model_contract_id,
        "request_metadata": metadata,
    }
    return RealModelRequest(
        provider_id=provider_id,
        model_id=model_id,
        backend_id=backend_id,
        backend=backend_id,
        runtime="product_model_native_decision",
        prompt_hash=prompt_hash,
        frame_hash=canonical_request.canonical_state.state_hash,
        user_model_contract_id=user_model_contract_id,
        estimated_input_tokens=max(1, (len(prompt) + 3) // 4),
        estimated_output_tokens=700,
        prompt_text_in_memory_only=prompt,
        request_metadata=metadata,
        timeout_policy_id="canonical_product_default_timeout",
        retry_policy_id="canonical_product_no_retry",
        budget_policy_id="canonical_product_bounded_budget",
        request_hash=stable_hash(hash_payload),
    )


def _canonical_product_provider_prompt(request: CanonicalDecisionRequest) -> str:
    state = request.canonical_state.safe_model_dump()
    operation_schemas = state.get("model_visible_operation_schemas", [])
    return (
        "You are the model brain. Sentinel is the body, state, effects, proof, and laws.\n"
        "Choose exactly one safe next operation for this read-only workspace mission.\n"
        "Return exactly one JSON object and no markdown.\n"
        "Allowed operations are generated from Sentinel's executable capability graph:\n"
        f"{json.dumps(operation_schemas, sort_keys=True, default=str)}\n"
        "Do not request code execution, network, credentials, browser, shell, provider-native tools, fallback, or authority changes.\n"
        "Finish only after a prior receipt/evidence ref supports the answer.\n"
        f"Mission objective: {request.canonical_state.objective}\n"
        f"Mission objective hash: {text_hash(request.canonical_state.objective)}\n"
        f"Canonical state: {json.dumps(state, sort_keys=True, default=str)}\n"
    )


def _extract_canonical_json_decision(raw: Any) -> dict[str, Any]:
    text = ""
    if isinstance(raw, dict):
        if raw.get("provider_failure") is True:
            category = str(raw.get("provider_failure_category") or raw.get("provider_error_class") or "UNKNOWN")
            diagnosis = _canonical_provider_failure_diagnosis(raw)
            raise CanonicalCoreError(f"canonical_provider_failure_{category}_{diagnosis}")
        metadata = raw.get("metadata")
        if isinstance(metadata, dict) and metadata.get("blocked_reason"):
            raise CanonicalCoreError(f"canonical_provider_blocked_{metadata.get('blocked_reason')}")
        for key in ("content", "reply", "text", "message"):
            value = raw.get(key)
            if isinstance(value, str):
                text = value
                break
        if not text and isinstance(metadata, dict):
            for key in ("content", "reply", "text", "message"):
                value = metadata.get(key)
                if isinstance(value, str):
                    text = value
                    break
        if not text and {"capability", "operation"} <= set(raw):
            return raw
    elif isinstance(raw, str):
        text = raw
    if not text.strip():
        raise CanonicalCoreError("canonical_provider_decision_empty")
    candidate = _first_json_object(text)
    if candidate is None:
        raise CanonicalCoreError("canonical_provider_decision_json_missing")
    return candidate


def _canonical_provider_failure_diagnosis(payload: dict[str, Any]) -> str:
    category = str(payload.get("provider_failure_category") or payload.get("provider_error_class") or "UNKNOWN")
    status = payload.get("http_status") or payload.get("status_code")
    try:
        http_status = int(status)
    except (TypeError, ValueError):
        http_status = None
    if category == "PROVIDER_AUTH_ERROR":
        if http_status == 401:
            return "credential_rejected_http_401"
        if http_status == 403:
            return "model_or_workspace_unauthorized_http_403"
        if http_status in {400, 404}:
            return f"endpoint_or_model_http_{http_status}"
        if http_status is not None:
            return f"auth_rejected_http_{http_status}"
        return "auth_rejected_status_unknown"
    if http_status is not None:
        return f"http_{http_status}"
    return "cause_unknown"


def _first_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            loaded = json.loads(stripped)
            return loaded if isinstance(loaded, dict) else None
        except json.JSONDecodeError:
            return None
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        loaded = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _run_cockpit_command(args: argparse.Namespace) -> int:
    explicit_bootstrap_turns: list[str] | None = None
    if args.model_led_read_only_autopilot and not args.explicit_mission_bootstrap:
        return _emit_cockpit_product_block(
            args,
            reason="model_led_autopilot_requires_explicit_bootstrap",
            outcome="mission_not_created",
        )
    if args.model_led_read_only_autopilot and args.stop_after_first_material_receipt:
        return _emit_cockpit_product_block(
            args,
            reason="model_led_autopilot_conflicts_with_first_receipt_mode",
            outcome="mission_not_created",
        )
    if args.model_led_read_only_autopilot and not args.low_friction_read_only_power_mode:
        return _emit_cockpit_product_block(
            args,
            reason="model_led_autopilot_requires_low_friction_read_only_power_mode",
            outcome="mission_not_created",
        )
    if args.provider_decision_timeout_seconds is not None and not args.model_led_read_only_autopilot:
        return _emit_cockpit_product_block(
            args,
            reason="provider_decision_timeout_requires_model_led_read_only_autopilot",
            outcome="mission_not_created",
        )
    if args.low_friction_read_only_power_mode and not (
        args.explicit_mission_bootstrap
        and (args.stop_after_first_material_receipt or args.model_led_read_only_autopilot)
    ):
        return _emit_cockpit_product_block(
            args,
            reason="low_friction_mode_requires_explicit_first_receipt_bootstrap",
            outcome="mission_not_created",
        )
    if (args.max_material_receipts is not None or args.max_provider_decision_calls is not None) and not args.model_led_read_only_autopilot:
        return _emit_cockpit_product_block(
            args,
            reason="autopilot_budgets_require_model_led_read_only_autopilot",
            outcome="mission_not_created",
        )
    if (
        args.generate_read_only_mission_summary or args.write_operator_memory_candidate
    ) and not args.model_led_read_only_autopilot:
        return _emit_cockpit_product_block(
            args,
            reason="read_only_summary_artifacts_require_model_led_read_only_autopilot",
            outcome="mission_not_created",
        )
    if args.write_operator_memory_candidate and not args.generate_read_only_mission_summary:
        return _emit_cockpit_product_block(
            args,
            reason="operator_memory_candidate_requires_read_only_mission_summary",
            outcome="mission_not_created",
        )
    if args.max_material_receipts is not None and args.max_material_receipts < 1:
        return _emit_cockpit_product_block(
            args,
            reason="max_material_receipts_must_be_positive",
            outcome="mission_not_created",
        )
    if args.max_provider_decision_calls is not None and args.max_provider_decision_calls < 1:
        return _emit_cockpit_product_block(
            args,
            reason="max_provider_decision_calls_must_be_positive",
            outcome="mission_not_created",
        )
    if args.provider_decision_timeout_seconds is not None and not (
        PROVIDER_DECISION_TIMEOUT_SECONDS_MIN
        <= args.provider_decision_timeout_seconds
        <= PROVIDER_DECISION_TIMEOUT_SECONDS_MAX
    ):
        return _emit_cockpit_product_block(
            args,
            reason="provider_decision_timeout_seconds_out_of_bounds",
            outcome="mission_not_created",
        )
    if args.stop_after_first_material_receipt and not args.explicit_mission_bootstrap:
        return _emit_cockpit_product_block(
            args,
            reason="first_receipt_mode_requires_explicit_bootstrap",
            outcome="mission_not_created",
        )
    if args.explicit_mission_bootstrap:
        reason = _explicit_bootstrap_preflight_reason(args)
        if reason is not None:
            return _emit_cockpit_product_block(
                args,
                reason=reason,
                outcome=_conversation_outcome_for_block_reason(reason),
            )
        explicit_bootstrap_turns = _explicit_bootstrap_script_turns(Path(args.script))
    if not args.deterministic_test_mode and args.model_contract is None:
        print("sentinel cockpit: --model-contract is required for llm_operator_mode", file=sys.stderr)
        return 2
    if args.legacy_internal_direct and args.workspace is not None:
        print("sentinel cockpit: workspace_binding_not_allowed_for_legacy_internal_direct", file=sys.stderr)
        return 2

    mode = OperatorMode.DETERMINISTIC_TEST if args.deterministic_test_mode else OperatorMode.LLM_OPERATOR
    user_model_contract = _load_user_model_contract(Path(args.model_contract)) if args.model_contract else None

    if args.legacy_internal_direct:
        model_client = (
            OperatorCatalogModelClient(user_model_contract=user_model_contract)
            if user_model_contract is not None and mode is OperatorMode.LLM_OPERATOR
            else None
        )
        return _run_legacy_internal_cockpit_command(
            args,
            mode=mode,
            user_model_contract=user_model_contract,
            model_client=model_client,
        )

    try:
        approval_scope = _load_authority_approval_scope(Path(args.authority_scope)) if args.authority_scope else None
    except ValueError as exc:
        print(f"sentinel cockpit: authority_scope_invalid:{exc}", file=sys.stderr)
        return 2

    product_execution_binding = None
    if approval_scope is not None and args.workspace is not None:
        try:
            product_execution_binding = build_product_execution_binding(
                workspace=Path(args.workspace),
                run_root=Path(args.run_root),
                approval_scope=approval_scope,
                user_model_contract=user_model_contract,
                capability_id=READ_ONLY_RESEARCH_CAPABILITY,
                operation="inspect_repository",
            )
        except ProductExecutionBindingError as exc:
            return _emit_cockpit_product_block(
                args,
                reason=exc.reason,
                outcome=_conversation_outcome_for_block_reason(exc.reason),
            )
    model_client = (
        OperatorCatalogModelClient(user_model_contract=user_model_contract)
        if user_model_contract is not None and mode is OperatorMode.LLM_OPERATOR
        else None
    )

    host = None
    read_only_decision_factory = None
    read_only_report_factory = None
    require_read_only_model_clients = mode is OperatorMode.LLM_OPERATOR
    if mode is OperatorMode.LLM_OPERATOR:
        if user_model_contract is None or model_client is None:
            print("sentinel cockpit: read_only_provider_execution_factories_required", file=sys.stderr)
            return 2
        read_only_decision_factory = lambda _request, _authority: ReadOnlyProviderDecisionClient(
            user_model_contract=user_model_contract,
            model_client=model_client,
            telemetry_sink=host.kernel.telemetry_sink if host is not None else None,
            timeout_seconds=_provider_decision_timeout_seconds(_request),
        )
        read_only_report_factory = lambda _request, _authority: ReadOnlyProviderReportClient(
            user_model_contract=user_model_contract,
            model_client=model_client,
            telemetry_sink=host.kernel.telemetry_sink if host is not None else None,
        )
    try:
        host = SentinelRuntimeHost(
            run_root=Path(args.run_root),
            read_only_decision_client_factory=read_only_decision_factory,
            read_only_report_client_factory=read_only_report_factory,
            require_read_only_model_clients=require_read_only_model_clients,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"sentinel cockpit: runtime_host_construction_failed:{exc.__class__.__name__}", file=sys.stderr)
        return 2

    try:
        try:
            host.start()
        except Exception as exc:  # noqa: BLE001
            print(f"sentinel cockpit: runtime_host_start_failed:{exc.__class__.__name__}", file=sys.stderr)
            return 2

        cockpit = LLMLiveOperatorCockpit(
            run_root=Path(args.run_root),
            mode=mode,
            user_model_contract=user_model_contract,
            model_client=model_client,
            lifecycle_service=host.lifecycle,
            authority_approval_scope=approval_scope,
            product_execution_binding=product_execution_binding,
            mission_execution_options=_mission_execution_options_from_args(args),
            require_mission_understanding_v2=mode is OperatorMode.LLM_OPERATOR,
        )
        return _run_cockpit_turn_loop(
            args,
            cockpit,
            classification=InternalAccessClassification.PRODUCTION_ROUTE,
            host=host,
            explicit_bootstrap_turns=explicit_bootstrap_turns,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"sentinel cockpit: cockpit_product_route_failed:{exc.__class__.__name__}", file=sys.stderr)
        return 2
    finally:
        try:
            host.shutdown()
        except Exception as exc:  # noqa: BLE001
            print(f"sentinel cockpit: runtime_host_shutdown_failed:{exc.__class__.__name__}", file=sys.stderr)


def _run_legacy_internal_cockpit_command(
    args: argparse.Namespace,
    *,
    mode: OperatorMode,
    user_model_contract: UserModelContract | None,
    model_client: OperatorCatalogModelClient | None,
) -> int:
    cockpit = LLMLiveOperatorCockpit(
        run_root=Path(args.run_root),
        mode=mode,
        user_model_contract=user_model_contract,
        model_client=model_client,
    )
    return _run_cockpit_turn_loop(
        args,
        cockpit,
        classification=InternalAccessClassification.LEGACY_INTERNAL,
        host=None,
    )


def _run_cockpit_turn_loop(
    args: argparse.Namespace,
    cockpit: LLMLiveOperatorCockpit,
    *,
    classification: InternalAccessClassification,
    host: SentinelRuntimeHost | None,
    explicit_bootstrap_turns: list[str] | None = None,
) -> int:
    turns: list[dict[str, object]] = []
    pumped_mission_ids: set[str] = set()

    if args.once is None and args.script is None and not args.json:
        print("Sentinel: Bonjour, je suis la. Qu'est-ce que tu veux faire ?")

    input_lines = explicit_bootstrap_turns if explicit_bootstrap_turns is not None else _cockpit_input_lines(args)
    for turn_index, line in enumerate(input_lines):
        normalized = line.strip().lower()
        if not normalized:
            continue
        if explicit_bootstrap_turns is not None and turn_index == 0:
            turn = cockpit.bootstrap_explicit_product_mission(line)
        elif explicit_bootstrap_turns is not None:
            if _is_explicit_bootstrap_approval(normalized):
                turn = cockpit.handle(line)
            else:
                turn = _explicit_bootstrap_approval_missing_turn(cockpit)
        elif normalized in {"/exit", "exit", "quit"}:
            break
        elif normalized in {"/help", "help"}:
            turn = _cockpit_help_turn(cockpit)
        elif normalized in {"/missions", "missions"}:
            turn = _cockpit_missions_turn(cockpit)
        elif normalized in {"/timeline", "timeline", "show timeline", "montre la timeline"}:
            turn = _cockpit_timeline_turn(cockpit)
        elif normalized in {"/replay", "replay", "what happened?", "qu'est-ce qui s'est passe ?"}:
            turn = _cockpit_replay_turn(cockpit)
        else:
            turn = cockpit.handle(line)
        turn = _with_cockpit_route_metadata(turn, classification=classification, host=host)
        if (
            host is not None
            and turn.state is OperatorConversationState.MISSION_QUEUED
            and turn.mission_record is not None
            and getattr(turn.mission_record, "mission_id", None)
            and turn.mission_record.mission_id not in pumped_mission_ids
            and not turn.metadata.get("legacy_deterministic_scope_compatibility")
        ):
            try:
                pickup = host.pump_daemon_once(turn.mission_record.mission_id)
            except Exception as exc:  # noqa: BLE001
                print(f"sentinel cockpit: daemon_pickup_failed:{exc.__class__.__name__}", file=sys.stderr)
                return 2
            pumped_mission_ids.add(turn.mission_record.mission_id)
            turn = _with_cockpit_route_metadata(
                turn,
                classification=classification,
                host=host,
                daemon_pickup={
                    "mission_id": pickup.mission_id,
                    "execution_request_ref": pickup.execution_request_ref,
                    "claimed": pickup.claimed,
                    "tick_executed": bool(getattr(pickup.tick_result, "executed", False)),
                    "tick_status": getattr(getattr(pickup.tick_result, "status", None), "value", None),
                    "dispatch_status": getattr(getattr(pickup.dispatch_result, "status", None), "value", None),
                    "dispatch_adapter_id": getattr(pickup.dispatch_result, "adapter_id", None),
                },
            )
        safe_turn = turn.safe_model_dump()
        turns.append(safe_turn)
        if not args.json:
            print(f"Sentinel: {safe_turn['reply']}")

    if args.json:
        if turns:
            metadata = dict(turns[-1].get("metadata", {}))
            metadata["conversation_outcome"] = _classify_cockpit_conversation(turns)
            turns[-1]["metadata"] = metadata
        print(json.dumps(turns, sort_keys=True, default=str))
    return 0


def _classify_cockpit_conversation(turns: list[dict[str, object]]) -> str:
    if not turns:
        return "conversation_completed"
    final = turns[-1]
    metadata = final.get("metadata")
    if isinstance(metadata, dict):
        blocked_outcome = _conversation_outcome_for_block_reason(str(metadata.get("blocked_reason", "")))
        if blocked_outcome != "mission_not_created":
            return blocked_outcome
        explicit_outcome = str(metadata.get("conversation_outcome", ""))
        if explicit_outcome == "explicit_bootstrap_draft_created":
            return explicit_outcome
    mission_record = final.get("mission_record")
    if isinstance(mission_record, dict):
        status = mission_record.get("status")
        if status in {"completed", "failed", "blocked", "killed", "revoked"}:
            return "mission_terminal"
        if status in {"queued", "running", "paused"}:
            return "mission_dispatched" if _has_daemon_pickup(turns) else "mission_queued"
    if _has_daemon_pickup(turns):
        return "mission_dispatched"
    if any(isinstance(turn.get("mission_record"), dict) for turn in turns):
        return "mission_queued"
    return "mission_not_created"


def _conversation_outcome_for_block_reason(reason: str) -> str:
    if reason in {"workspace_binding_required", "workspace_not_found", "workspace_not_directory"}:
        return "mission_not_created_workspace_missing"
    if reason == "workspace_outside_approved_scope":
        return "mission_not_created_workspace_outside_scope"
    if reason in {
        "explicit_bootstrap_requires_two_script_turns",
        "explicit_bootstrap_approval_missing_or_ambiguous",
    }:
        return "mission_not_created_approval_missing"
    return "mission_not_created"


def _has_daemon_pickup(turns: list[dict[str, object]]) -> bool:
    for turn in turns:
        metadata = turn.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("daemon_pickup"), dict):
            return True
    return False


def _emit_cockpit_product_block(args: argparse.Namespace, *, reason: str, outcome: str) -> int:
    payload = [
        {
            "state": OperatorConversationState.ASKING_CLARIFICATIONS.value,
            "reply": "Sentinel cannot start this governed product mission without a valid explicit workspace binding.",
            "metadata": {
                "blocked_reason": reason,
                "conversation_outcome": outcome,
                "internal_access_classification": InternalAccessClassification.PRODUCTION_ROUTE.value,
                "production_runtime_host_used": False,
            },
            "mission_record": None,
        }
    ]
    if args.json:
        print(json.dumps(payload, sort_keys=True, default=str))
    else:
        print(f"sentinel cockpit: {reason}", file=sys.stderr)
    return 2


def _explicit_bootstrap_preflight_reason(args: argparse.Namespace) -> str | None:
    if args.stop_after_first_material_receipt and not args.explicit_mission_bootstrap:
        return "first_receipt_mode_requires_explicit_bootstrap"
    if args.legacy_internal_direct:
        return "explicit_bootstrap_not_allowed_for_legacy_internal_direct"
    if args.deterministic_test_mode:
        return "explicit_bootstrap_requires_llm_product_mode"
    if not args.json:
        return "explicit_bootstrap_requires_json_output"
    if args.script is None:
        return "explicit_bootstrap_requires_script"
    if args.workspace is None:
        return "explicit_bootstrap_requires_workspace"
    if args.authority_scope is None:
        return "explicit_bootstrap_requires_authority_scope"
    if args.model_contract is None:
        return "explicit_bootstrap_requires_model_contract"
    try:
        turns = _explicit_bootstrap_script_turns(Path(args.script))
    except OSError:
        return "explicit_bootstrap_script_read_failed"
    if len(turns) != 2:
        return "explicit_bootstrap_requires_two_script_turns"
    return None


def _mission_execution_options_from_args(args: argparse.Namespace) -> dict[str, object]:
    options: dict[str, object] = {}
    if getattr(args, "stop_after_first_material_receipt", False):
        options["stop_after_first_material_receipt"] = True
    if getattr(args, "low_friction_read_only_power_mode", False):
        options["low_friction_read_only_power_mode"] = True
    if getattr(args, "model_led_read_only_autopilot", False):
        options["model_led_read_only_autopilot"] = True
    if getattr(args, "max_material_receipts", None) is not None:
        options["max_material_receipts"] = int(args.max_material_receipts)
    if getattr(args, "max_provider_decision_calls", None) is not None:
        options["max_provider_decision_calls"] = int(args.max_provider_decision_calls)
    if getattr(args, "provider_decision_timeout_seconds", None) is not None:
        options["provider_decision_timeout_seconds"] = int(args.provider_decision_timeout_seconds)
    if getattr(args, "generate_read_only_mission_summary", False):
        options["generate_read_only_mission_summary"] = True
    if getattr(args, "write_operator_memory_candidate", False):
        options["write_operator_memory_candidate"] = True
    return options


def _provider_decision_timeout_seconds(request: object) -> float:
    execution_options = getattr(request, "execution_options", {}) or {}
    value = execution_options.get("provider_decision_timeout_seconds")
    return float(value) if value is not None else 20.0


def _explicit_bootstrap_script_turns(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _is_explicit_bootstrap_approval(normalized: str) -> bool:
    return normalized == "start"


def _explicit_bootstrap_approval_missing_turn(cockpit: LLMLiveOperatorCockpit) -> OperatorTurnResult:
    return OperatorTurnResult(
        session_id=cockpit.session.session_id,
        state=OperatorConversationState.ASKING_CLARIFICATIONS,
        reply="Explicit product mission bootstrap requires ASCII approval: start.",
        metadata={
            "blocked_reason": "explicit_bootstrap_approval_missing_or_ambiguous",
            "conversation_outcome": "mission_not_created_approval_missing",
            "bootstrap_protocol": "explicit_product_mission_bootstrap_v1",
            "provider_call_boundary": "cockpit_provider_not_called",
        },
    )


_REQUIRED_APPROVAL_SCOPE_FIELDS = frozenset(
    {
        "user_id",
        "allowed_systems",
        "allowed_tools",
        "allowed_actions",
        "forbidden_actions",
        "allowed_paths",
        "allowed_domains",
        "allowed_accounts",
        "allowed_data_types",
        "browser_v3_authority_grants",
        "credential_grants",
        "max_duration_minutes",
        "max_actions",
        "max_cost_usd",
    }
)


def _load_authority_approval_scope(path: Path) -> MissionAuthorityApprovalScope:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"read_failed:{exc.__class__.__name__}") from exc
    if not isinstance(payload, dict):
        raise ValueError("approval_scope_must_be_json_object")
    missing = sorted(_REQUIRED_APPROVAL_SCOPE_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"approval_scope_missing_required_fields:{','.join(missing)}")
    try:
        return MissionAuthorityApprovalScope.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"approval_scope_validation_failed:{exc.__class__.__name__}") from exc


def _with_cockpit_route_metadata(
    turn: OperatorTurnResult,
    *,
    classification: InternalAccessClassification,
    host: SentinelRuntimeHost | None,
    daemon_pickup: dict[str, object] | None = None,
) -> OperatorTurnResult:
    metadata = dict(turn.metadata)
    metadata["internal_access_classification"] = classification.value
    metadata["production_runtime_host_used"] = classification is InternalAccessClassification.PRODUCTION_ROUTE
    if host is not None:
        metadata["runtime_host_status"] = host.status().status.value
        metadata["runtime_host_lifecycle_ref"] = f"lifecycle:{id(host.lifecycle)}"
    if daemon_pickup is not None:
        metadata["daemon_pickup"] = daemon_pickup
    return turn.model_copy(update={"metadata": metadata})


def _cockpit_help_turn(cockpit: LLMLiveOperatorCockpit) -> OperatorTurnResult:
    return OperatorTurnResult(
        session_id=cockpit.session.session_id,
        state=cockpit.session.state,
        reply=(
            "Commands: /status, /timeline, /replay, /pause, /resume, "
            "/kill, /missions, /exit. Natural language mission requests are "
            "converted into drafts before Sentinel can start governed work."
        ),
    )


def _cockpit_missions_turn(cockpit: LLMLiveOperatorCockpit) -> OperatorTurnResult:
    records = cockpit.kernel.list_missions()
    if not records:
        reply = "Missions: none."
    else:
        lines = [f"{record.mission_id}: {record.status.value}: {record.draft.title}" for record in records]
        reply = "Missions\n" + "\n".join(lines)
    return OperatorTurnResult(
        session_id=cockpit.session.session_id,
        state=cockpit.session.state,
        reply=reply,
        metadata={"mission_count": len(records)},
    )


def _cockpit_input_lines(args: argparse.Namespace):
    if args.once is not None:
        yield args.once
        return
    if args.script is not None:
        yield from Path(args.script).read_text(encoding="utf-8").splitlines()
        return
    while True:  # pragma: no cover - interactive loop is covered through --once/--script.
        try:
            yield input("> ")
        except EOFError:
            return


def _cockpit_timeline_turn(cockpit: LLMLiveOperatorCockpit) -> OperatorTurnResult:
    mission_id = cockpit.active_mission_id
    if mission_id is None:
        return OperatorTurnResult(
            session_id=cockpit.session.session_id,
            state=cockpit.session.state,
            reply="Aucune mission active pour la timeline.",
        )
    events = cockpit.kernel.store.load_events(mission_id)
    tampered = not cockpit.kernel.store.verify_timeline(mission_id)
    lines = [f"{event.sequence}:{event.event_type}:{event.safe_summary}" for event in events]
    reply = "\n".join(lines) if lines else "Timeline vide."
    if tampered:
        reply = "Timeline integrity warning: event stream tampered.\n" + reply
    return OperatorTurnResult(
        session_id=cockpit.session.session_id,
        state=cockpit.session.state,
        reply=reply,
        mission_record=cockpit.kernel.store.load_record(mission_id),
        metadata={
            "timeline_summary": {"tampered": tampered},
            "timeline": [event.model_dump(mode="json") for event in events],
        },
    )


def _cockpit_replay_turn(cockpit: LLMLiveOperatorCockpit) -> OperatorTurnResult:
    mission_id = cockpit.active_mission_id
    if mission_id is None:
        return OperatorTurnResult(
            session_id=cockpit.session.session_id,
            state=cockpit.session.state,
            reply="Aucune mission active a rejouer.",
        )
    replay = MissionReplayBuilder(cockpit.kernel.store).build(mission_id)
    summary = replay.safe_summary_text()
    return OperatorTurnResult(
        session_id=cockpit.session.session_id,
        state=OperatorConversationState.MISSION_RUNNING,
        reply=f"Replay\n{summary}\n{replay.terminal_explanation}",
        mission_record=cockpit.kernel.store.load_record(mission_id),
        metadata={
            "replay_summary": {
                "tampered": replay.tampered,
                "evidence_only": True,
                "receipt_ref_count": len(replay.receipt_refs),
                "finalgate_ref_count": len(replay.finalgate_certificate_refs),
                "memory_ref_count": len(replay.memory_feedback_refs),
            }
        },
    )


def _load_user_model_contract(path: Path) -> UserModelContract:
    return UserModelContract.model_validate(json.loads(path.read_text(encoding="utf-8")))


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
        resolver=_fixture_public_dns_resolver(args.url) if args.fixture_html is not None else None,
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


def _run_browser_session_demo(args: argparse.Namespace) -> tuple[dict[str, object], Path]:
    mission_file = load_power_lab_mission_file(Path(args.mission))
    run_dir = _create_browser_run_dir(Path(args.run_root), mission_file.mission.id)
    fixtures = {args.url: args.fixture_html} if args.fixture_html is not None else None
    manager = BrowserSessionManagerL5Live(
        capture_root=run_dir,
        engine=args.engine,
        document_fixtures=fixtures,
    )
    contract = BrowserSessionContract(
        mission_id=mission_file.mission.id,
        allowed_domains=mission_file.mission.allowed_domains,
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
        max_steps=5,
    )
    opened = manager.open_session(
        BrowserSessionRequest(
            mission=mission_file.mission,
            url=args.url,
            contract=contract,
            action_kind=BrowserSessionActionKind.OPEN,
        )
    )
    typed = None
    observed = None
    closed = None
    if opened.accepted:
        typed = manager.interact(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role=args.target_role,
                target_name=args.target_name,
                text=args.text,
            )
        )
    if typed is not None and typed.accepted:
        observed = manager.observe(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=contract,
                session_id=opened.session_id,
            )
        )
    if opened.accepted:
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            )
        )
    manager.close_all()
    steps = [step for step in (opened, typed, observed, closed) if step is not None]
    accepted = bool(steps) and all(step.accepted for step in steps)
    result: dict[str, object] = {
        "type": "browser_session_workflow",
        "mission_id": mission_file.mission.id,
        "accepted": accepted,
        "status": "completed" if accepted else "blocked",
        "session_id": opened.session_id,
        "receipt_ids": [step.receipt.receipt_id for step in steps],
        "blocked_reasons": [step.reason for step in steps if not step.accepted],
        "data_not_instruction": True,
        "authority_effect": "none",
    }
    (run_dir / "browser.session.result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return result, run_dir


def _fixture_public_dns_resolver(url: str):
    """Return a deterministic public resolver for development-only HTML fixtures.

    Fixture mode fulfills the document from memory and does not contact the
    origin. The resolver keeps URL guard behavior deterministic without making
    a real DNS call.
    """

    fixture_host = (urlsplit(url).hostname or "").lower()

    def resolve(host: str) -> list[str]:
        if host.lower() != fixture_host:
            return []
        return ["93.184.216.34"]

    return resolve


def _run_browser_trajectory_demo(args: argparse.Namespace) -> tuple[dict[str, object], Path]:
    mission_file = load_power_lab_mission_file(Path(args.mission))
    run_dir = _create_browser_run_dir(Path(args.run_root), mission_file.mission.id)
    fixtures = {args.url: args.fixture_html} if args.fixture_html is not None else None
    manager = BrowserSessionManagerL5Live(
        capture_root=run_dir,
        engine=args.engine,
        document_fixtures=fixtures,
    )
    session_contract = BrowserSessionContract(
        mission_id=mission_file.mission.id,
        allowed_domains=mission_file.mission.allowed_domains,
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
        max_steps=5,
    )
    opened = manager.open_session(
        BrowserSessionRequest(
            mission=mission_file.mission,
            url=args.url,
            contract=session_contract,
            action_kind=BrowserSessionActionKind.OPEN,
        )
    )
    trajectory_result = None
    closed = None
    if opened.accepted and opened.session_id:
        snapshot = manager.snapshot_for_session(mission_id=mission_file.mission.id, session_id=opened.session_id)
        if snapshot is None:
            raise PowerLabMissionRejected("browser trajectory snapshot unavailable")
        trajectory_contract = BrowserTrajectoryContract(
            mission_id=mission_file.mission.id,
            allowed_domains=mission_file.mission.allowed_domains,
            allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE],
            max_recovery_attempts=3,
        )
        trajectory_result = BrowserTrajectoryPlannerL5().execute_with_recovery(
            manager,
            BrowserTrajectoryRequest(
                mission=mission_file.mission,
                url=args.url,
                session_id=opened.session_id,
                contract=trajectory_contract,
                source_snapshot=snapshot,
                source_receipt_id=opened.receipt.receipt_id,
                objective_summary=f"type value into {args.target_hint}",
                desired_action_kind=BrowserTrajectoryActionKind.TYPE,
                target_role_hint=args.target_role,
                target_name_hint=args.target_hint,
                text=args.text,
            ),
        )
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=session_contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            )
        )
    manager.close_all()
    accepted = bool(opened.accepted and trajectory_result and trajectory_result.accepted and (closed is None or closed.accepted))
    result: dict[str, object] = {
        "type": "browser_trajectory_workflow",
        "mission_id": mission_file.mission.id,
        "accepted": accepted,
        "status": "completed" if accepted else "blocked",
        "session_id": opened.session_id,
        "plan_hash": trajectory_result.plan.plan_hash if trajectory_result and trajectory_result.plan else None,
        "trajectory_receipt_id": trajectory_result.receipt.receipt_id if trajectory_result else None,
        "execution_receipt_id": trajectory_result.execution_receipt_id if trajectory_result else None,
        "blocked_reasons": [item for item in [opened.reason if not opened.accepted else None, trajectory_result.reason if trajectory_result and not trajectory_result.accepted else None] if item],
        "data_not_instruction": True,
        "authority_effect": "none",
    }
    (run_dir / "browser.trajectory.result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return result, run_dir


def _run_browser_submit_demo(args: argparse.Namespace) -> tuple[dict[str, object], Path]:
    mission_file = load_power_lab_mission_file(Path(args.mission))
    run_dir = _create_browser_run_dir(Path(args.run_root), mission_file.mission.id)
    fixtures = {args.url: args.fixture_html} if args.fixture_html is not None else None
    manager = BrowserSessionManagerL5Live(
        capture_root=run_dir,
        engine=args.engine,
        document_fixtures=fixtures,
    )
    session_contract = BrowserSessionContract(
        mission_id=mission_file.mission.id,
        allowed_domains=mission_file.mission.allowed_domains,
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
        max_steps=5,
    )
    opened = manager.open_session(
        BrowserSessionRequest(
            mission=mission_file.mission,
            url=args.url,
            contract=session_contract,
            action_kind=BrowserSessionActionKind.OPEN,
        )
    )
    typed = None
    submitted = None
    closed = None
    if opened.accepted and opened.session_id:
        typed = manager.interact(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=session_contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role=args.input_role,
                target_name=args.input_name,
                text=args.text,
            )
        )
    if typed is not None and typed.accepted and opened.session_id:
        snapshot = manager.snapshot_for_session(mission_id=mission_file.mission.id, session_id=opened.session_id)
        submit_contract = BrowserFormSubmitContract(
            mission_id=mission_file.mission.id,
            allowed_domains=mission_file.mission.allowed_domains,
            allow_form_submit=True,
        )
        submitted = BrowserFormSubmitSpecialAuthorityL6().execute(
            BrowserFormSubmitRequest(
                mission=mission_file.mission,
                url=args.url,
                session_id=opened.session_id,
                contract=submit_contract,
                target_role=args.submit_role,
                target_name=args.submit_name,
                source_snapshot_hash=snapshot.snapshot_sha256 if snapshot else None,
            ),
            session_manager=manager,
        )
    if opened.accepted and opened.session_id:
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=session_contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            )
        )
    manager.close_all()
    accepted = bool(opened.accepted and typed and typed.accepted and submitted and submitted.accepted and (closed is None or closed.accepted))
    result: dict[str, object] = {
        "type": "browser_submit_workflow",
        "mission_id": mission_file.mission.id,
        "accepted": accepted,
        "status": "completed" if accepted else "blocked",
        "session_id": opened.session_id,
        "open_receipt_id": opened.receipt.receipt_id,
        "type_receipt_id": typed.receipt.receipt_id if typed else None,
        "submit_receipt_id": submitted.receipt.receipt_id if submitted else None,
        "submit_certificate_id": submitted.finalgate_certificate.certificate_id if submitted and submitted.finalgate_certificate else None,
        "blocked_reasons": [
            item
            for item in [
                opened.reason if not opened.accepted else None,
                typed.reason if typed and not typed.accepted else None,
                submitted.reason if submitted and not submitted.accepted else None,
            ]
            if item
        ],
        "data_not_instruction": True,
        "authority_effect": "none",
    }
    (run_dir / "browser.submit.result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return result, run_dir


def _run_browser_login_demo(args: argparse.Namespace) -> tuple[dict[str, object], Path]:
    username_value = os.environ.get(args.username_env)
    password_value = os.environ.get(args.password_env)
    if username_value is None or password_value is None:
        raise PowerLabMissionRejected("browser login demo requires username/password env vars")
    mission_file = load_power_lab_mission_file(Path(args.mission))
    run_dir = _create_browser_run_dir(Path(args.run_root), mission_file.mission.id)
    fixtures = {args.url: args.fixture_html} if args.fixture_html is not None else None
    manager = BrowserSessionManagerL5Live(
        capture_root=run_dir,
        engine=args.engine,
        document_fixtures=fixtures,
    )
    session_contract = BrowserSessionContract(
        mission_id=mission_file.mission.id,
        allowed_domains=mission_file.mission.allowed_domains,
        max_steps=5,
    )
    opened = manager.open_session(
        BrowserSessionRequest(
            mission=mission_file.mission,
            url=args.url,
            contract=session_contract,
            action_kind=BrowserSessionActionKind.OPEN,
        )
    )
    logged_in = None
    closed = None
    if opened.accepted and opened.session_id:
        login_contract = BrowserLoginCredentialSessionContract(
            mission_id=mission_file.mission.id,
            allowed_domains=mission_file.mission.allowed_domains,
            username_credential_ref_id=args.username_ref,
            password_credential_ref_id=args.password_ref,
            allow_login=True,
        )
        logged_in = BrowserLoginCredentialSessionBrokerL6().execute(
            BrowserLoginCredentialSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                session_id=opened.session_id,
                contract=login_contract,
                username_target_role="textbox",
                username_target_name=args.username_name,
                password_target_role="textbox",
                password_target_name=args.password_name,
                submit_target_role="button",
                submit_target_name=args.submit_name,
            ),
            session_manager=manager,
            credential_provider=EphemeralBrowserCredentialProvider(
                {
                    args.username_ref: username_value,
                    args.password_ref: password_value,
                }
            ),
        )
    if opened.accepted and opened.session_id:
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=mission_file.mission,
                url=args.url,
                contract=session_contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            )
        )
    manager.close_all()
    accepted = bool(opened.accepted and logged_in and logged_in.accepted and (closed is None or closed.accepted))
    result: dict[str, object] = {
        "type": "browser_login_workflow",
        "mission_id": mission_file.mission.id,
        "accepted": accepted,
        "status": "completed" if accepted else "blocked",
        "session_id": opened.session_id,
        "open_receipt_id": opened.receipt.receipt_id,
        "login_receipt_id": logged_in.receipt.receipt_id if logged_in else None,
        "login_certificate_id": logged_in.finalgate_certificate.certificate_id if logged_in and logged_in.finalgate_certificate else None,
        "credential_proof_ids": [proof.proof_id for proof in logged_in.credential_proofs] if logged_in else [],
        "blocked_reasons": [
            item
            for item in [
                opened.reason if not opened.accepted else None,
                logged_in.reason if logged_in and not logged_in.accepted else None,
            ]
            if item
        ],
        "data_not_instruction": True,
        "authority_effect": "none",
    }
    (run_dir / "browser.login.result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
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
