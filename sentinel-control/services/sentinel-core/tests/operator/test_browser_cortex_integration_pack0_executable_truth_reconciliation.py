from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.browser_cortex_deterministic_fixture import BrowserCortexDeterministicFixtureEngine
from sentinel.operator.browser_cortex_deterministic_runner import BrowserCortexDeterministicDecisionClient
from sentinel.operator.browser_cortex_quality_gate import build_browser_cortex_quality_corpus
from sentinel.operator.browser_product_cutover_registry import build_default_browser_product_cutover_registry
from sentinel.operator.browser_search_outcomes import BrowserSearchOutcomeKind, derive_browser_search_outcome
from sentinel.operator.browser_semantic_control_classifier import classify_search_controls
from sentinel.operator.model_led_product_action_kernel_task_loop import ProductActionKernelTaskLoopStatus
from sentinel.operator.real_browser_control_runtime import (
    CLOAK_BROWSER_BACKEND_ID,
    RealBrowserControlRuntime,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.kernel import MissionKernel


class _CapturingBrowserDecisionClient:
    def __init__(self, action: ActionEnvelope) -> None:
        self.action = action
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        if len(self.contexts) == 1:
            return self.action
        return ActionEnvelope(
            capability_id="sentinel_loop",
            operation="finish",
            params={"safe_summary": "Stop after product context capture."},
            idempotency_key="pack0:capture:finish",
        )


def test_actual_product_loop_context_consumes_browser_environment_state(tmp_path: Path) -> None:
    client = _CapturingBrowserDecisionClient(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro", "engine_profile": "fake_product_search"},
            idempotency_key="pack0:capture:search",
        )
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="session_pack0_product_context",
        mission_objective="Search a bounded browser catalog and extract visible product cards.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=2,
        max_material_actions=3,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    product_context = client.contexts[1]
    cognitive_frame = product_context["browser_cognitive_decision_frame"]

    assert cognitive_frame["canonical_state_source"] == "BrowserEnvironmentState"
    assert cognitive_frame["state_hash"] == product_context["browser_environment_state_hash"]
    assert cognitive_frame["result_regions"]["candidate_count"] >= 1
    assert cognitive_frame["candidate_entities"]
    assert cognitive_frame["primary_recommended_skill"] == "extract"
    assert product_context["primary_model_recommended_next_skill"] == "extract"
    assert "browser_environment_state" in product_context["skill_decision_frame"]


def test_shared_multilingual_control_classifier_feeds_world_model_and_actuation() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Catalogue",
        state_hash="state_localized",
        elements=(
            RealBrowserEngineElement(
                ref="input:recherche",
                role="searchbox",
                name="Rechercher",
                text_preview="Rechercher dans le catalogue",
            ),
            RealBrowserEngineElement(ref="button:localized_search", role="button", name="Lancer"),
        ),
    )

    candidates = classify_search_controls(
        snapshot.elements,
        mission_objective="Trouver des lunettes autour de 5 EUR.",
        frame_id="main",
        tab_id="tab_1",
    )

    assert candidates
    assert candidates[0].control_ref == "input:recherche"
    assert candidates[0].semantic_role == "search_control"
    assert candidates[0].confidence >= 0.75
    assert candidates[0].submission_mechanisms
    assert "accessibility_role:searchbox" in candidates[0].evidence_refs


def test_no_results_confirmed_requires_material_empty_state_not_zero_cards() -> None:
    uncertain = derive_browser_search_outcome(
        input_written=True,
        submission_attempted=True,
        request_observed=True,
        query_reflected=True,
        result_region_changed=False,
        before_result_region_count=0,
        after_result_region_count=0,
        query_hash="query_hash",
        pre_state_hash="pre",
        post_state_hash="post",
        empty_result_evidence=False,
        evidence_refs=("request:query",),
    )
    confirmed = derive_browser_search_outcome(
        input_written=True,
        submission_attempted=True,
        request_observed=True,
        query_reflected=True,
        result_region_changed=False,
        before_result_region_count=2,
        after_result_region_count=0,
        query_hash="query_hash",
        pre_state_hash="pre",
        post_state_hash="post",
        empty_result_evidence=True,
        evidence_refs=("request:query", "empty_result_region:stable"),
    )

    assert uncertain.outcome_kind is BrowserSearchOutcomeKind.MATERIAL_UNCERTAIN
    assert confirmed.outcome_kind is BrowserSearchOutcomeKind.NO_RESULTS_CONFIRMED
    assert confirmed.search_materially_successful is True


def test_devtools_safe_sensor_evidence_reaches_environment_state(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, _DevToolsSearchEngine())

    result = runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
            idempotency_key="pack0:devtools:search",
        ),
        authority=_authority(),
        context={},
    )

    state = result.context_cards["browser_environment_state"]
    bundle = result.context_cards["browser_observation_bundle"]

    assert state["protocol_graph"]["network_event_count"] >= 1
    assert bundle["devtools_sensor_consumed"] is True
    assert bundle["raw_material_persisted"] is False
    assert "raw_body" not in str(result.context_cards)
    assert "secret-cookie" not in str(result.context_cards)


def test_recovery_engine_plan_is_hidden_evidence_for_stale_control(tmp_path: Path) -> None:
    case = next(
        case
        for case in build_browser_cortex_quality_corpus(baseline_commit="pack0").deterministic_cases
        if case.task_id == "det_stale_controls"
    )
    runtime = _runtime(tmp_path, BrowserCortexDeterministicFixtureEngine.from_case(case))

    result = runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": case.objective},
            idempotency_key="pack0:stale:search",
        ),
        authority=_authority(),
        context={},
    )

    assert result.status == "completed"
    assert result.context_cards["browser_recovery_evidence"]["consumed_by_product_runtime"] is True
    assert "REFRESH_SNAPSHOT" in result.context_cards["browser_recovery_evidence"]["planned_actions"]
    assert result.context_cards["browser_recovery_evidence"]["can_execute"] is False
    assert result.context_cards["browser_recovery_evidence"]["parallel_finalgate_used"] is False


def test_browser_cutover_consumed_flags_match_executable_truth() -> None:
    registry = build_default_browser_product_cutover_registry()
    frame = registry.compile_frame().safe_model_dump()

    assert frame["registry_truth_mismatch_count"] == 0
    by_id = {item["path_id"]: item for item in frame["paths"]}
    assert by_id["browser_devtools_machine_intelligence"]["consumed_by_browser_cortex"] is True
    assert by_id["browser_devtools_machine_intelligence"]["executable_trace_proof"] == "browser_observation_bundle"
    assert by_id["browser_failure_recovery_engine"]["consumed_by_browser_cortex"] is True
    assert by_id["browser_failure_recovery_engine"]["executable_trace_proof"] == "browser_recovery_evidence"


def test_confirmed_no_results_search_completes_through_negative_summary(tmp_path: Path) -> None:
    case = next(
        case
        for case in build_browser_cortex_quality_corpus(baseline_commit="pack0").deterministic_cases
        if case.task_id == "det_url_query_no_result"
    )
    BrowserCortexDeterministicFixtureEngine.from_case(case)
    client = BrowserCortexDeterministicDecisionClient(case, baseline_commit="pack0")
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="session_pack0_no_results_completion",
        mission_objective=case.objective,
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        max_recoverable_action_failures=1,
        max_recoverable_model_decision_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert "real_browser_control:real_browser.search" in result.capability_sequence
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence
    assert result.capability_sequence[-1] == "sentinel_loop:finish"
    assert any(
        context.get("completion_requirements", {}).get("has_confirmed_no_results_search_receipt") is True
        for context in client.contexts
    )
    assert all(
        context.get("completion_requirements", {}).get("product_or_result_candidate_card_count") == 0
        for context in client.contexts
        if context.get("completion_requirements", {}).get("has_confirmed_no_results_search_receipt") is True
    )


def _runtime(tmp_path: Path, engine: Any) -> RealBrowserControlRuntime:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    mission_id = "mission_pack0_browser_cortex"
    kernel.store.mission_dir(mission_id, create=True)
    return RealBrowserControlRuntime(
        kernel=kernel,
        mission_id=mission_id,
        engine=engine,
        selected_backend_id=CLOAK_BROWSER_BACKEND_ID,
    )


def _authority() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="user_pack0",
        mission_title="Browser Cortex Pack 0",
        mission_objective="Search bounded browser page and extract relevant cards.",
        allowed_tools=["real_browser_control"],
        allowed_actions=[
            "real_browser.open",
            "real_browser.observe",
            "real_browser.search",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
        ],
        forbidden_actions=["login", "payment", "checkout", "contact_supplier", "credential_access"],
        allowed_domains=["real_browser:bounded_test_url"],
        max_actions=6,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text("browser cortex pack 0 workspace", encoding="utf-8")
    return workspace


class _DevToolsSearchEngine:
    browser_backend_id = CLOAK_BROWSER_BACKEND_ID
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"

    @property
    def safe_url_origin_hash(self) -> str:
        return "origin_hash"

    def observe(self) -> RealBrowserEngineSnapshot:
        return self._snapshot(query="")

    def open(self) -> RealBrowserEngineSnapshot:
        return self._snapshot(query="")

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        assert ref == "input:search"
        return self._snapshot(query=text)

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        assert ref == "input:search"
        assert key == "Enter"
        return self._snapshot(query="glasses under 5 euro", results=True)

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        return self._snapshot(query="glasses under 5 euro", results=True)

    def safe_devtools_context(self) -> dict[str, Any]:
        return {
            "source": "pack0_fake_devtools",
            "available": True,
            "safe_metadata": {
                "network_event_count": 1,
                "console_error_count": 0,
                "request_classes": {"document": 1},
                "response_status_classes": {"2xx": 1},
                "query_linked_request_evidence": True,
                "raw_body": "must-not-leak",
                "cookie": "secret-cookie",
            },
        }

    def _snapshot(self, *, query: str, results: bool = False) -> RealBrowserEngineSnapshot:
        elements: list[RealBrowserEngineElement] = [
            RealBrowserEngineElement(ref="input:search", role="searchbox", name="Search products", value_preview=query),
            RealBrowserEngineElement(ref="button:search", role="button", name="Search"),
        ]
        if results:
            elements.append(
                RealBrowserEngineElement(
                    ref="link:result_1",
                    role="link",
                    name="Blue light glasses 4.80 EUR MOQ 10",
                    text_preview="Blue light glasses visible price 4.80 EUR MOQ 10 Supplier Pack0.",
                )
            )
        return RealBrowserEngineSnapshot(
            page_title="Pack0 Fixture",
            state_hash=f"state:{query}:{results}",
            elements=tuple(elements),
        )
