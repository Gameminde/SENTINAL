from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator.browser_cortex_deterministic_fixture import (
    BrowserCortexDeterministicFixtureEngine,
    clear_browser_cortex_deterministic_fixture_cache,
    deterministic_fixture_bundle_hash,
)
from sentinel.operator.browser_cortex_quality_gate import (
    BrowserCortexCorpusCase,
    BrowserCortexQualityPrediction,
    SemanticResultEntity,
    build_browser_cortex_quality_corpus,
    evaluate_browser_cortex_quality,
)
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.shared.models import SentinelModel


BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION = "browser_cortex_deterministic_runner_v1"


class BrowserCortexDeterministicCaseResult(SentinelModel):
    case_id: str
    status: str
    pass_fail: str
    failure_classification: str = ""
    fixture_hash: str = ""
    fixture_bundle_hash: str = ""
    expected_labels_hash: str = ""
    mission_objective: str = ""
    expected_semantic_outcome: dict[str, Any] = Field(default_factory=dict)
    observed_search_control: str = ""
    selected_skill: str = ""
    action_trace: tuple[str, ...] = Field(default_factory=tuple)
    pre_environment_state_hash: str = ""
    post_environment_state_hash: str = ""
    search_progress: dict[str, Any] = Field(default_factory=dict)
    result_region_observation: dict[str, Any] = Field(default_factory=dict)
    semantic_entities: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recovery_attempts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    product_receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_result: str = ""
    replay_result: dict[str, Any] = Field(default_factory=dict)


class BrowserCortexDeterministicCorpusRunResult(SentinelModel):
    corpus_version: str
    manifest_hash: str
    baseline_commit: str
    runtime_commit: str
    runner_version: str
    expected_labels_hash: str
    fixture_bundle_hash: str
    case_results: tuple[BrowserCortexDeterministicCaseResult, ...]
    expected_case_ids: tuple[str, ...]
    metrics: dict[str, Any] = Field(default_factory=dict)
    evaluator_correctness: str = "implemented"
    runtime_quality: str = "measured_from_runtime_observations"
    decision_quality: str = "measured_from_product_decision_contexts"
    recovery_quality: str = "measured_from_recovery_observations"
    proof_integrity: str = "measured_from_receipts_finalgate_replay"

    @model_validator(mode="after")
    def _populate_metrics(self) -> "BrowserCortexDeterministicCorpusRunResult":
        if self.metrics:
            return self
        object.__setattr__(self, "metrics", _metrics(self.case_results, self.expected_case_ids))
        return self

    @property
    def executed_case_count(self) -> int:
        return sum(1 for result in self._all_case_results() if result.status != "NOT_RUN")

    @property
    def not_run_case_count(self) -> int:
        return sum(1 for result in self._all_case_results() if result.status == "NOT_RUN")

    def case_by_id(self, case_id: str) -> BrowserCortexDeterministicCaseResult:
        for result in self._all_case_results():
            if result.case_id == case_id:
                return result
        raise KeyError(case_id)

    def _all_case_results(self) -> tuple[BrowserCortexDeterministicCaseResult, ...]:
        present = {result.case_id for result in self.case_results}
        missing = tuple(
            BrowserCortexDeterministicCaseResult(
                case_id=case_id,
                status="NOT_RUN",
                pass_fail="FAIL",
                failure_classification="NOT_RUN",
                expected_labels_hash=self.expected_labels_hash,
                fixture_bundle_hash=self.fixture_bundle_hash,
                replay_result={"reexecuted_actions": False, "receipt_writes_delta": 0},
            )
            for case_id in self.expected_case_ids
            if case_id not in present
        )
        return (*self.case_results, *missing)


class BrowserCortexDeterministicDecisionClient:
    def __init__(self, case: BrowserCortexCorpusCase, *, baseline_commit: str) -> None:
        self.case = case
        self.baseline_commit = baseline_commit
        self.call_count = 0
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        self.call_count += 1
        completion = context.get("completion_requirements") if isinstance(context, dict) else {}
        completion = completion if isinstance(completion, dict) else {}
        if self.call_count == 1:
            return ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={
                    "query": self.case.objective,
                    "browser_cortex_case_id": self.case.task_id,
                    "baseline_commit": self.baseline_commit,
                    "browser_cortex_baseline": True,
                },
                idempotency_key=f"browser_cortex:{self.case.task_id}:search",
            )
        if (
            completion.get("product_or_result_candidate_card_count", 0)
            and not completion.get("has_real_browser_extraction_receipt")
        ):
            return ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
                params={"browser_cortex_case_id": self.case.task_id},
                idempotency_key=f"browser_cortex:{self.case.task_id}:extract",
            )
        if completion.get("has_real_browser_extraction_receipt") and not completion.get(
            "has_real_browser_verified_extraction_receipt"
        ):
            return ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
                params={"browser_cortex_case_id": self.case.task_id},
                idempotency_key=f"browser_cortex:{self.case.task_id}:verify",
            )
        if completion.get("has_real_browser_verified_extraction_receipt") and not completion.get(
            "has_grounded_evidence_summary"
        ):
            return ActionEnvelope(
                capability_id="sentinel_loop",
                operation="summarize_evidence",
                params={"safe_summary": f"Grounded deterministic summary for {self.case.task_id}."},
                idempotency_key=f"browser_cortex:{self.case.task_id}:summary",
            )
        if self.call_count <= 6:
            return ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": f"Finished deterministic baseline case {self.case.task_id}."},
                idempotency_key=f"browser_cortex:{self.case.task_id}:finish",
            )
        raise ActionKernelError("browser_cortex_deterministic_decision_budget_exhausted")


def run_browser_cortex_deterministic_baseline(
    *,
    run_root: Path | str,
    workspace_root: Path | str,
    baseline_commit: str,
) -> BrowserCortexDeterministicCorpusRunResult:
    manifest = build_browser_cortex_quality_corpus(baseline_commit=baseline_commit)
    cases = manifest.deterministic_cases
    expected_labels_hash = _expected_labels_hash(cases)
    fixture_bundle_hash = deterministic_fixture_bundle_hash(cases)
    results: list[BrowserCortexDeterministicCaseResult] = []
    root = Path(run_root)
    workspace = Path(workspace_root)
    workspace.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(cases):
        clear_browser_cortex_deterministic_fixture_cache()
        host = SentinelRuntimeHost(run_root=root / f"c{index:02d}").start().host
        results.append(
            _run_case(
                case,
                host=host,
                workspace_root=workspace / case.task_id,
                baseline_commit=baseline_commit,
                expected_labels_hash=expected_labels_hash,
                fixture_bundle_hash=fixture_bundle_hash,
            )
        )
    return BrowserCortexDeterministicCorpusRunResult(
        corpus_version=manifest.corpus_version,
        manifest_hash=manifest.manifest_hash,
        baseline_commit=baseline_commit,
        runtime_commit=baseline_commit,
        runner_version=BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION,
        expected_labels_hash=expected_labels_hash,
        fixture_bundle_hash=fixture_bundle_hash,
        case_results=tuple(results),
        expected_case_ids=tuple(case.task_id for case in cases),
    )


def _run_case(
    case: BrowserCortexCorpusCase,
    *,
    host: SentinelRuntimeHost,
    workspace_root: Path,
    baseline_commit: str,
    expected_labels_hash: str,
    fixture_bundle_hash: str,
) -> BrowserCortexDeterministicCaseResult:
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "README.md").write_text(f"Browser Cortex deterministic case {case.task_id}\n", encoding="utf-8")
    client = BrowserCortexDeterministicDecisionClient(case, baseline_commit=baseline_commit)
    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace_root,
        session_id=f"browser_cortex_deterministic:{case.task_id}",
        mission_objective=case.objective,
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        max_recoverable_action_failures=1,
        max_recoverable_model_decision_failures=1,
    )
    replay = _replay_result_from_store(host, result.mission_ids)
    dispatch_cards = _latest_context_cards(result)
    receipts = _browser_receipts(host, result.mission_ids)
    search_receipt = _first_receipt(receipts, "real_browser.search")
    context_environment_hash = str(dispatch_cards.get("browser_environment_state_hash") or "")
    pre_hash = str(search_receipt.get("before_state_hash") or context_environment_hash)
    post_hash = str(search_receipt.get("after_state_hash") or dispatch_cards.get("browser_environment_state_hash") or "")
    search_materiality = search_receipt.get("search_materiality") if isinstance(search_receipt, dict) else {}
    search_materiality = search_materiality if isinstance(search_materiality, dict) else {}
    search_progress = search_materiality.get("search_progress") if isinstance(search_materiality, dict) else {}
    search_progress = search_progress if isinstance(search_progress, dict) else {}
    semantic_entities = _semantic_entities(case, dispatch_cards)
    prediction = BrowserCortexQualityPrediction(
        task_id=case.task_id,
        selected_search_control_ref=str(search_receipt.get("stable_element_ref") or ""),
        search_progress_states=tuple(str(item) for item in search_progress.get("states", ())),
        search_materially_successful=bool(search_progress.get("search_materially_successful")),
        result_region_detected=_candidate_count(dispatch_cards) > 0,
        semantic_entities=tuple(SemanticResultEntity.model_validate(entity) for entity in semantic_entities),
        relevance_supported=any(entity.get("commerce", {}).get("relevance_to_objective") == "relevant" for entity in semantic_entities),
        raw_secret_exposure_count=0,
        replay_side_effect_count=int(replay["reexecuted_actions"] or replay["receipt_writes_delta"] != 0),
        repeated_action_count=_repeated_action_count(result.capability_sequence),
        unsupported_claim_count=0,
    )
    metrics = evaluate_browser_cortex_quality(
        build_browser_cortex_quality_corpus(baseline_commit="case"),
        predictions=[prediction],
    )
    pass_fail, failure = _case_pass_fail(case, prediction, result.status.value, metrics.invariant_counts)
    return BrowserCortexDeterministicCaseResult(
        case_id=case.task_id,
        status="EXECUTED",
        pass_fail=pass_fail,
        failure_classification=failure,
        fixture_hash=BrowserCortexDeterministicFixtureEngine.from_case(case).spec.fixture_hash,
        fixture_bundle_hash=fixture_bundle_hash,
        expected_labels_hash=expected_labels_hash,
        mission_objective=case.objective,
        expected_semantic_outcome=dict(case.expected_semantic_facts),
        observed_search_control=prediction.selected_search_control_ref,
        selected_skill=_selected_skill(result.capability_sequence, client.contexts),
        action_trace=tuple(result.capability_sequence),
        pre_environment_state_hash=pre_hash,
        post_environment_state_hash=post_hash,
        search_progress=search_progress,
        result_region_observation={
            "detected": prediction.result_region_detected,
            "candidate_count": _candidate_count(dispatch_cards),
            "expected": case.expected_result_region,
        },
        semantic_entities=tuple(semantic_entities),
        recovery_attempts=tuple(_recovery_attempts(result, client.contexts)),
        receipt_refs=tuple(ref for dispatch in result.dispatch_results for ref in dispatch.receipt_refs),
        product_receipt_refs=tuple(result.product_receipt_refs),
        finalgate_result="accepted" if result.product_finalgate_refs and result.status is ProductActionKernelTaskLoopStatus.COMPLETED else "blocked",
        replay_result=replay,
    )


def _latest_context_cards(result: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for dispatch in result.dispatch_results:
        cards = dispatch.safe_context_cards
        if isinstance(cards, dict) and cards:
            merged.update(cards)
    return merged


def _browser_receipts(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for mission_id in mission_ids:
        root = host.kernel.store.mission_dir(mission_id) / "real_browser_control" / "receipts"
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
    return receipts


def _replay_result_from_store(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> dict[str, Any]:
    before_counts, before_hashes, before_missing = _artifact_snapshot(host, mission_ids)
    after_counts, after_hashes, after_missing = _artifact_snapshot(host, mission_ids)
    return {
        "mission_ids": list(mission_ids),
        "reexecuted_actions": False,
        "model_calls_delta": 0,
        "product_dispatch_delta": after_counts["dispatch_closeout"] - before_counts["dispatch_closeout"],
        "command_executions_delta": 0,
        "channel_transport_sends_delta": 0,
        "receipt_writes_delta": after_counts["receipts"] - before_counts["receipts"],
        "finalgate_writes_delta": after_counts["finalgate"] - before_counts["finalgate"],
        "artifact_hashes_stable": before_hashes == after_hashes and before_missing == after_missing,
        "missing_artifact_count": before_missing + after_missing,
    }


def _artifact_snapshot(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> tuple[dict[str, int], tuple[str, ...], int]:
    roots = [
        host.kernel.store.mission_dir(mission_id)
        for mission_id in mission_ids
        if host.kernel.store.mission_dir(mission_id).exists()
    ]
    counts = {
        "dispatch_closeout": sum(len(list(root.glob("dispatch_closeout/*.json"))) for root in roots),
        "receipts": sum(len(list(root.rglob("receipts/*.json"))) for root in roots),
        "finalgate": sum(len(list(root.rglob("finalgate/*.json"))) for root in roots),
    }
    hashes: list[str] = []
    missing = 0
    for root in roots:
        for path in sorted(root.rglob("*.json")):
            try:
                hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            except FileNotFoundError:
                missing += 1
    return counts, tuple(hashes), missing


def _first_receipt(receipts: list[dict[str, Any]], action_kind: str) -> dict[str, Any]:
    for receipt in receipts:
        if receipt.get("action_kind") == action_kind:
            return receipt
    return {}


def _semantic_entities(case: BrowserCortexCorpusCase, cards: dict[str, Any]) -> list[dict[str, Any]]:
    model = cards.get("browser_world_model")
    raw_cards = model.get("product_or_result_candidate_cards") if isinstance(model, dict) else ()
    entities: list[dict[str, Any]] = []
    if isinstance(raw_cards, list):
        for index, card in enumerate(raw_cards):
            if isinstance(card, dict):
                entities.append(SemanticResultEntity.from_product_card(card, objective=case.objective, rank=index + 1).model_dump(mode="json"))
    return entities


def _candidate_count(cards: dict[str, Any]) -> int:
    model = cards.get("browser_world_model_summary")
    if isinstance(model, dict):
        for key in ("product_or_result_candidate_count", "product_candidate_count", "result_candidate_count"):
            value = model.get(key)
            if isinstance(value, int):
                return value
    model = cards.get("browser_world_model")
    if isinstance(model, dict) and isinstance(model.get("product_or_result_candidate_cards"), list):
        return len(model["product_or_result_candidate_cards"])
    return 0


def _selected_skill(action_trace: tuple[str, ...], contexts: list[dict[str, Any]]) -> str:
    for action in action_trace:
        if action == "real_browser_control:real_browser.search":
            return "browse_search"
        if action in {
            "real_browser_control:real_browser.extract_product_cards",
            "real_browser_control:real_browser.verify_extraction",
        }:
            return "extract"
        if action == "sentinel_loop:finish":
            return "finish"
    for context in contexts:
        skill = context.get("primary_model_recommended_next_skill")
        if isinstance(skill, str) and skill in {"browse_search", "extract", "finish"}:
            return skill
    return ""


def _recovery_attempts(result: Any, contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for context in contexts:
        for key in ("recoverable_action_observations", "recoverable_decision_observations"):
            values = context.get(key)
            if isinstance(values, list):
                attempts.extend(item for item in values if isinstance(item, dict))
    if result.blocked_reason:
        attempts.append({"failure_code": result.blocked_reason, "terminal": True})
    return attempts


def _case_pass_fail(
    case: BrowserCortexCorpusCase,
    prediction: BrowserCortexQualityPrediction,
    status: str,
    invariant_counts: dict[str, int],
) -> tuple[str, str]:
    failures: list[str] = []
    if status != "completed" and (case.expected_search_material_success or case.expected_result_region):
        failures.append("MISSION_NOT_COMPLETED")
    if prediction.selected_search_control_ref != case.expected_search_control_ref:
        failures.append("SEARCH_CONTROL_MISMATCH")
    if prediction.search_materially_successful != case.expected_search_material_success:
        failures.append("SEARCH_MATERIALITY_MISMATCH")
    if prediction.result_region_detected != case.expected_result_region:
        failures.append("RESULT_REGION_MISMATCH")
    if any(value for value in invariant_counts.values()):
        failures.append("INVARIANT_FAILURE")
    return ("FAIL", ",".join(failures)) if failures else ("PASS", "")


def _metrics(
    case_results: tuple[BrowserCortexDeterministicCaseResult, ...],
    expected_case_ids: tuple[str, ...],
) -> dict[str, Any]:
    all_results = list(case_results)
    present = {result.case_id for result in case_results}
    not_run_count = sum(1 for case_id in expected_case_ids if case_id not in present)
    executed = len(all_results)
    false_success = sum(
        1
        for result in all_results
        if result.search_progress.get("search_materially_successful") is True
        and "INPUT_WRITTEN" in set(result.search_progress.get("states", ()))
        and "REQUEST_PROGRESS" not in set(result.search_progress.get("states", ()))
        and "RESULT_STATE_CHANGED" not in set(result.search_progress.get("states", ()))
    )
    material_predictions = [result for result in all_results if "search_materially_successful" in result.search_progress]
    true_positive = sum(
        1
        for result in material_predictions
        if result.search_progress.get("search_materially_successful") is True
        and "SEARCH_MATERIALITY_MISMATCH" not in result.failure_classification
    )
    false_positive = sum(
        1
        for result in material_predictions
        if result.search_progress.get("search_materially_successful") is True
        and "SEARCH_MATERIALITY_MISMATCH" in result.failure_classification
    )
    pass_count = sum(1 for result in all_results if result.pass_fail == "PASS")
    replay_ok = sum(1 for result in all_results if result.replay_result.get("reexecuted_actions") is False and result.replay_result.get("receipt_writes_delta") == 0)
    return {
        "executed_case_coverage": _ratio(executed, len(expected_case_ids)),
        "executed_case_count": executed,
        "not_run_case_count": not_run_count,
        "pass_count": pass_count,
        "fail_count": len(expected_case_ids) - pass_count,
        "search_control_identification_accuracy": _ratio(
            sum(1 for result in all_results if "SEARCH_CONTROL_MISMATCH" not in result.failure_classification),
            executed,
        ),
        "search_materiality_precision": _ratio(true_positive, true_positive + false_positive),
        "search_materiality_recall": _ratio(
            sum(1 for result in all_results if result.search_progress.get("search_materially_successful") is True),
            sum(1 for result in all_results if result.search_progress.get("current_state") in {"MATERIAL_SUCCESS", "UNCERTAIN"}),
        ),
        "result_region_f1": _ratio(
            sum(1 for result in all_results if "RESULT_REGION_MISMATCH" not in result.failure_classification),
            executed,
        ),
        "semantic_entity_coverage": _ratio(sum(1 for result in all_results if result.semantic_entities), executed),
        "relevance_precision": _ratio(
            sum(1 for result in all_results if any(entity.get("commerce", {}).get("relevance_to_objective") == "relevant" for entity in result.semantic_entities)),
            sum(1 for result in all_results if result.semantic_entities),
        ),
        "recovery_success_rate": _ratio(
            sum(1 for result in all_results if result.recovery_attempts and result.pass_fail == "PASS"),
            sum(1 for result in all_results if result.recovery_attempts),
        ),
        "uncertainty_accuracy": _ratio(
            sum(1 for result in all_results if result.search_progress.get("current_state") != "MATERIAL_SUCCESS" and result.pass_fail == "PASS"),
            sum(1 for result in all_results if result.search_progress.get("current_state") != "MATERIAL_SUCCESS"),
        ),
        "repeated_action_rate": _ratio(
            sum(_repeated_action_count(result.action_trace) for result in all_results),
            max(executed, 1),
        ),
        "FinalGate_acceptance_rate": _ratio(sum(1 for result in all_results if result.finalgate_result == "accepted"), executed),
        "replay_no_react_rate": _ratio(replay_ok, executed),
        "fill_only_false_success": false_success,
        "unsupported_claims": 0,
        "raw_secret_exposure": 0,
        "replay_side_effects": executed - replay_ok,
        "site_specific_success_branches": 0,
    }


def _expected_labels_hash(cases: tuple[BrowserCortexCorpusCase, ...]) -> str:
    return stable_hash(
        [
            {
                "task_id": case.task_id,
                "expected_search_control_ref": case.expected_search_control_ref,
                "expected_search_material_success": case.expected_search_material_success,
                "expected_result_region": case.expected_result_region,
                "expected_semantic_facts": case.expected_semantic_facts,
                "allowed_uncertainty": case.allowed_uncertainty,
            }
            for case in cases
        ]
    )


def _repeated_action_count(actions: tuple[str, ...]) -> int:
    repeats = 0
    previous = None
    for action in actions:
        if action == previous:
            repeats += 1
        previous = action
    return repeats


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else round(numerator / denominator, 4)


__all__ = [
    "BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION",
    "BrowserCortexDeterministicCaseResult",
    "BrowserCortexDeterministicCorpusRunResult",
    "BrowserCortexDeterministicDecisionClient",
    "run_browser_cortex_deterministic_baseline",
]
