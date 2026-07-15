from __future__ import annotations

from pathlib import Path

from sentinel.operator import runtime_host as runtime_host_module
from sentinel.operator.action_kernel import ActionEnvelope, _grounded_evidence_summary
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
)
from sentinel.operator.real_browser_control_runtime import (
    RealBrowserControlRuntimeError,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost, stable_hash, text_hash


class PythonOrgLikeSearchActuationFailEngine(runtime_host_module._ProductLocalCloakBrowserEngine):
    browser_backend_id = "cloak_browser"
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"

    def __init__(self) -> None:
        super().__init__()
        self.search_attempt_count = 0

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash({"scheme": "https", "netloc": "www.python.org"})

    def type_text(self, ref: str, text: str):  # type: ignore[no-untyped-def]
        del ref, text
        self.search_attempt_count += 1
        raise RealBrowserControlRuntimeError("locator_timeout")

    def _snapshot(self) -> RealBrowserEngineSnapshot:
        text = self._page_text()
        return RealBrowserEngineSnapshot(
            page_title="Welcome to Python.org",
            state_hash=stable_hash(
                {
                    "text_hash": text_hash(text),
                    "search_attempt_count": self.search_attempt_count,
                }
            ),
            elements=self._elements(),
        )

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("e15", "searchbox", "Search"),
            RealBrowserEngineElement("e16", "button", "Submit this Search GO", text_preview="GO"),
            RealBrowserEngineElement("e46", "link", "Docs", text_preview="Python Documentation Docs"),
            RealBrowserEngineElement(
                "e91",
                "link",
                "More about pathlib glob in Python 3",
                text_preview="Pathlib Path.glob documentation and examples",
            ),
            RealBrowserEngineElement(
                "e95",
                "link",
                "More control flow tools in Python 3",
                text_preview="More control flow tools in Python 3",
            ),
        )

    def _page_text(self) -> str:
        return "\n".join(
            [
                "Search Python.org documentation",
                "Python Documentation Docs",
                "Pathlib Path.glob documentation and examples",
                "More control flow tools in Python 3",
            ]
        )


def test_recoverable_search_failure_exposes_model_visible_body_failure_packet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engines: list[PythonOrgLikeSearchActuationFailEngine] = []

    def fake_factory() -> PythonOrgLikeSearchActuationFailEngine:
        engine = PythonOrgLikeSearchActuationFailEngine()
        engines.append(engine)
        return engine

    monkeypatch.setenv("SENTINEL_BROWSER_TEST_URL", "https://www.python.org/")
    monkeypatch.setenv("SENTINEL_BROWSER_HEADLESS", "true")
    monkeypatch.setattr(runtime_host_module, "build_cloak_first_real_browser_engine_from_env", fake_factory)

    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "pathlib glob documentation"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="test_python_org_body_failure_feedback",
        mission_objective="Search Python.org documentation for pathlib glob and summarize grounded docs evidence.",
        decision_client=client,
        allowed_domains=("www.python.org", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=2,
        max_recoverable_action_failures=1,
    )

    assert engines and engines[0].search_attempt_count >= 1
    assert result.dispatch_results[0].blocked_reason == "real_browser_search_actuation_failed"
    next_context = client.contexts[1]

    packet = next_context["model_visible_body_failure_packet"]
    fact = next_context["runtime_failure_fact"]
    schema = next_context["model_blocker_assessment_schema"]

    assert fact["failure_code"] == "real_browser_search_actuation_failed"
    assert fact["attempted_operation"] == "real_browser.search"
    assert fact["authority_effect"] == "none"
    assert fact["can_grant_authority"] is False
    assert packet["attempted_operation"] == "real_browser.search"
    assert packet["typed_outcome"]["failure_code"] == "real_browser_search_actuation_failed"
    assert packet["material_effect_observed"] is False
    assert packet["session_continuity"]["root_lease_present"] is True
    assert packet["safe_current_page_state_summary"]["page_kind_guess"] in {
        "documentation_search_or_index",
        "catalog_search",
        "search_results_uncertain",
    }
    assert packet["available_affordances"]["search_like_refs"]
    assert packet["retry_material_action_budget_remaining"] >= 0
    assert packet["evidence_refs"]
    assert set(schema["required_model_response_fields"]) == {
        "perceived_blocker",
        "concise_failure_interpretation",
        "proposed_next_strategy",
        "required_evidence",
        "missing_capability",
        "objective_satisfied",
        "confidence",
    }


def test_python_documentation_links_are_open_world_entities_not_product_candidates() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Welcome to Python.org",
        state_hash="state_docs",
        elements=(
            RealBrowserEngineElement("e15", "searchbox", "Search"),
            RealBrowserEngineElement("e46", "link", "Docs", text_preview="Python Documentation Docs"),
            RealBrowserEngineElement(
                "e91",
                "link",
                "Pathlib Path.glob documentation",
                text_preview="Pathlib Path.glob official documentation and examples",
            ),
            RealBrowserEngineElement(
                "e95",
                "link",
                "More control flow tools in Python 3",
                text_preview="More control flow tools in Python 3",
            ),
        ),
    )

    world = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find Python pathlib Path.glob documentation.",
        origin_hash="origin:python",
    )

    kinds = {card.kind for card in world.product_or_result_candidate_cards}
    assert world.product_or_result_candidate_cards
    assert "product_candidate" not in kinds
    assert {"documentation_result", "api_symbol_result"} & kinds
    first = world.product_or_result_candidate_cards[0]
    assert first.objective_relevance_assessed is True
    assert first.extra_attributes["entity_family"] in {"documentation", "api_symbol"}
    assert first.evidence_refs


def test_grounded_summary_for_documentation_entities_is_not_product_summary() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Welcome to Python.org",
        state_hash="state_docs_summary",
        elements=(
            RealBrowserEngineElement("e15", "searchbox", "Search"),
            RealBrowserEngineElement(
                "e91",
                "link",
                "Pathlib Path.glob documentation",
                text_preview="Pathlib Path.glob official documentation and examples",
            ),
        ),
    )
    world = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find Python pathlib Path.glob documentation.",
        origin_hash="origin:python",
    )

    summary = _grounded_evidence_summary({"browser_world_model": world.model_dump(mode="json")})

    assert summary["summary_kind"] == "grounded_browser_open_world_evidence_summary"
    assert summary["objective_relevance_assessed"] is True
    assert summary["objective_satisfaction_status"] in {"supported", "partial", "uncertain"}
    assert summary["has_relevant_product_evidence"] is False
    assert summary["unsupported_claims"] == 0
