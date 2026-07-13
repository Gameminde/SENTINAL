from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.browser_cortex_quality_gate import BrowserCortexCorpusCase
from sentinel.operator.real_browser_control_runtime import (
    RealBrowserControlRuntimeError,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
)


@dataclass(frozen=True)
class BrowserCortexDeterministicFixtureSpec:
    case_id: str
    fixture_hash: str
    category_tags: tuple[str, ...]
    expected_search_control_ref: str
    expected_search_material_success: bool
    expected_result_region: bool
    relevant: bool


class BrowserCortexDeterministicFixtureEngine:
    browser_backend_id = "cloak_browser"
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"

    def __init__(self, spec: BrowserCortexDeterministicFixtureSpec) -> None:
        self.spec = spec
        self.opened = False
        self.query = ""
        self.submitted = False
        self.results_visible = False
        self.network_event_count = 0
        self.recovery_attempts = 0
        self._stale_failed_once = False

    @classmethod
    def from_case(cls, case: BrowserCortexCorpusCase) -> "BrowserCortexDeterministicFixtureEngine":
        return cls(
            BrowserCortexDeterministicFixtureSpec(
                case_id=case.task_id,
                fixture_hash=stable_hash(
                    {
                        "task_id": case.task_id,
                        "tags": case.category_tags,
                        "expected_search_control_ref": case.expected_search_control_ref,
                        "expected_search_material_success": case.expected_search_material_success,
                        "expected_result_region": case.expected_result_region,
                    }
                ),
                category_tags=case.category_tags,
                expected_search_control_ref=case.expected_search_control_ref,
                expected_search_material_success=case.expected_search_material_success,
                expected_result_region=case.expected_result_region,
                relevant=bool(case.expected_semantic_facts.get("relevant") is True),
            )
        )

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash(f"browser-cortex-deterministic://{self.spec.case_id}")

    def open(self) -> RealBrowserEngineSnapshot:
        self.opened = True
        return self._snapshot()

    def observe(self) -> RealBrowserEngineSnapshot:
        self.opened = True
        return self._snapshot()

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self.opened = True
        if "stale_controls" in self.spec.category_tags and not self._stale_failed_once:
            self._stale_failed_once = True
            self.recovery_attempts += 1
            raise RealBrowserControlRuntimeError("real_browser_stale_control")
        if ref != self.spec.expected_search_control_ref:
            self.recovery_attempts += 1
            raise RealBrowserControlRuntimeError("real_browser_type_ref_not_textbox")
        self.query = text
        return self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        if ref != self.spec.expected_search_control_ref:
            raise RealBrowserControlRuntimeError("real_browser_type_ref_not_textbox")
        if key == "Enter":
            self._submit()
        return self._snapshot()

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        if ref in {"button:search", "button:localized_search", "button:autocomplete_submit"}:
            self._submit()
        return self._snapshot()

    def select_option(self, ref: str, option: str) -> RealBrowserEngineSnapshot:
        del ref, option
        if "client_side_filter" in self.spec.category_tags:
            self._submit()
        return self._snapshot()

    def wait_for_load(self) -> RealBrowserEngineSnapshot:
        if "dynamic_loading" in self.spec.category_tags and self.submitted:
            self.results_visible = self.spec.expected_result_region
        return self._snapshot()

    def wait_for_text(self, text: str, timeout_ms: int = 1000) -> tuple[bool, RealBrowserEngineSnapshot]:
        del timeout_ms
        return text.lower() in self._page_text().lower(), self._snapshot()

    def scroll(self, delta_y: int = 600) -> RealBrowserEngineSnapshot:
        del delta_y
        if "infinite_scroll" in self.spec.category_tags and self.submitted:
            self.results_visible = self.spec.expected_result_region
        return self._snapshot()

    def assert_text(self, text: str) -> tuple[bool, RealBrowserEngineSnapshot]:
        return text.lower() in self._page_text().lower(), self._snapshot()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        return self._page_text(), self._snapshot()

    def safe_devtools_context(self) -> dict[str, Any]:
        return {
            "source": "browser_cortex_deterministic_fixture",
            "available": True,
            "backend_kind": "cloakbrowser",
            "page_target_count": 1,
            "snapshot_hash": stable_hash({"case_id": self.spec.case_id, "submitted": self.submitted}),
            "network_ledger_hash": stable_hash({"network_event_count": self.network_event_count}),
            "safe_metadata": {
                "source_backend_kind": "cloakbrowser",
                "session_ref": stable_hash(self.spec.case_id),
                "url_hash": self.safe_url_origin_hash,
                "title_hash": text_hash(f"Fixture {self.spec.case_id}"),
                "step_index": 1,
                "network_event_count": self.network_event_count,
                "network_failure_count": 1 if "network_failure" in self.spec.category_tags else 0,
                "console_message_count": 0,
                "console_error_count": 0,
            },
        }

    def _submit(self) -> None:
        self.submitted = True
        if self.spec.expected_search_material_success:
            self.network_event_count = 1
            self.results_visible = self.spec.expected_result_region
        elif "fill_only_false_success_trap" in self.spec.category_tags:
            self.network_event_count = 0
            self.results_visible = False
        elif "url_query_no_result" in self.spec.category_tags:
            self.network_event_count = 1
            self.results_visible = False
        elif "network_failure" in self.spec.category_tags:
            self.network_event_count = 0
            self.results_visible = False

    def _snapshot(self) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title=f"Browser Cortex Fixture {self.spec.case_id}",
            state_hash=stable_hash(
                {
                    "case_id": self.spec.case_id,
                    "query_hash": text_hash(self.query),
                    "submitted": self.submitted,
                    "results_visible": self.results_visible,
                    "network_event_count": self.network_event_count,
                }
            ),
            elements=self._elements(),
        )

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        elements = [
            RealBrowserEngineElement(
                self.spec.expected_search_control_ref,
                "searchbox" if "client_side_filter" not in self.spec.category_tags else "combobox",
                self._search_name(),
                value_preview=self.query[:80],
            ),
            RealBrowserEngineElement("button:search", "button", "Search", text_preview="Search"),
        ]
        if "multiple_search_fields" in self.spec.category_tags:
            elements.insert(0, RealBrowserEngineElement("input:footer_search", "textbox", "Newsletter search"))
        if "modal_overlay" in self.spec.category_tags and not self.submitted:
            elements.append(RealBrowserEngineElement("button:close_modal", "button", "Close modal", text_preview="Close"))
        if self.submitted and not self.spec.expected_result_region and "url_query_no_result" in self.spec.category_tags:
            elements.append(
                RealBrowserEngineElement(
                    "region:no_results",
                    "generic",
                    "No matching results",
                    text_preview="Search completed but no matching result region is visible.",
                )
            )
        if self.results_visible:
            elements.extend(self._result_elements())
        return tuple(elements)

    def _result_elements(self) -> list[RealBrowserEngineElement]:
        if not self.spec.expected_result_region:
            return []
        if "non_commerce" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:article_result",
                    "link",
                    "Reference article result",
                    text_preview="Reference article result with no product price or supplier.",
                )
            ]
        if "pack1_mixed_cards" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_relevant_under",
                    "link",
                    "Polarized sunglasses sample",
                    text_preview=(
                        "Polarized sunglasses sample 4.80 EUR per piece MOQ 10 pieces "
                        "Supplier VisionCraft Store shipping not included."
                    ),
                ),
                RealBrowserEngineElement(
                    "link:pack1_irrelevant",
                    "link",
                    "Safety helmets sample",
                    text_preview=(
                        "Industrial safety helmets 3.90 EUR per piece MOQ 50 pieces "
                        "Supplier HelmetWorks Store."
                    ),
                ),
            ]
        if "pack1_relevant_under_price" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_relevant_under",
                    "link",
                    "Polarized sunglasses sample",
                    text_preview=(
                        "Polarized sunglasses sample 4.80 EUR per piece MOQ 10 pieces "
                        "Supplier VisionCraft Store shipping not included available."
                    ),
                )
            ]
        if "pack1_above_price" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_above_price",
                    "link",
                    "Prescription eyeglasses premium sample",
                    text_preview=(
                        "Prescription eyeglasses premium sample 18.00 EUR per piece MOQ 100 pieces "
                        "Supplier VisionCraft Store."
                    ),
                )
            ]
        if "pack1_unknown_price" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_unknown_price",
                    "link",
                    "Rimless eyeglasses catalog sample",
                    text_preview=(
                        "Rimless eyeglasses catalog sample price unavailable MOQ 10 pieces "
                        "Supplier VisionCraft Store."
                    ),
                )
            ]
        if "pack1_irrelevant_product" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_irrelevant",
                    "link",
                    "Industrial safety helmet sample",
                    text_preview=(
                        "Industrial safety helmet sample 4.80 EUR per piece MOQ 20 pieces "
                        "Supplier HelmetWorks Store."
                    ),
                )
            ]
        relevance_text = "relevant" if self.spec.relevant else "not relevant to objective"
        price_text = "4.80 EUR MOQ 10" if self.spec.relevant else "18.00 EUR MOQ 100"
        if "contradictory_price_currency" in self.spec.category_tags:
            return [
                RealBrowserEngineElement(
                    "link:pack1_currency_conflict",
                    "link",
                    "Fashion sunglasses currency conflict sample",
                    text_preview=(
                        "Fashion sunglasses currency conflict sample 4.80 EUR visible text, "
                        "structured data USD 9.50 MOQ 10 pieces Supplier VisionCraft Store."
                    ),
                )
            ]
        return [
            RealBrowserEngineElement(
                "link:result_1",
                "link",
                f"Deterministic product {self.spec.case_id}",
                text_preview=(
                    f"Deterministic product card {price_text} Supplier Cortex Fixture Store {relevance_text}."
                ),
            )
        ]

    def _page_text(self) -> str:
        if not self.results_visible:
            if self.submitted and not self.spec.expected_result_region:
                return "Search completed but no matching result region is visible."
            return "Search products with a bounded deterministic fixture."
        return " ".join(element.text_preview for element in self._result_elements())

    def _search_name(self) -> str:
        if "localized_ui" in self.spec.category_tags:
            return "Rechercher"
        if "autocomplete" in self.spec.category_tags:
            return "Autocomplete product search"
        if "client_side_filter" in self.spec.category_tags:
            return "Filter products"
        return "Search products"


def deterministic_fixture_bundle_hash(cases: tuple[BrowserCortexCorpusCase, ...]) -> str:
    return stable_hash(
        [
            BrowserCortexDeterministicFixtureEngine.from_case(case).spec.__dict__
            for case in cases
        ]
    )


_FIXTURE_ENGINE_CACHE: dict[str, BrowserCortexDeterministicFixtureEngine] = {}


def clear_browser_cortex_deterministic_fixture_cache() -> None:
    _FIXTURE_ENGINE_CACHE.clear()


def browser_cortex_deterministic_fixture_engine_for_case(
    case: BrowserCortexCorpusCase,
) -> BrowserCortexDeterministicFixtureEngine:
    engine = _FIXTURE_ENGINE_CACHE.get(case.task_id)
    if engine is None:
        engine = BrowserCortexDeterministicFixtureEngine.from_case(case)
        _FIXTURE_ENGINE_CACHE[case.task_id] = engine
    return engine


__all__ = [
    "browser_cortex_deterministic_fixture_engine_for_case",
    "BrowserCortexDeterministicFixtureEngine",
    "BrowserCortexDeterministicFixtureSpec",
    "clear_browser_cortex_deterministic_fixture_cache",
    "deterministic_fixture_bundle_hash",
]
