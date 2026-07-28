from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.real_browser_control_runtime import (
    CLOAK_BROWSER_BACKEND_ID,
    InMemoryRealBrowserEngine,
    RealBrowserControlRuntime,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
)


def test_search_action_context_includes_browser_environment_state(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    fixture.runtime.execute(_envelope("real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        _envelope("real_browser.search", query="glasses under 5 euro"),
        authority=fixture.authority,
        context={},
    )

    state = result.context_cards["browser_environment_state"]

    assert result.status == "completed"
    assert state["backend_truth"]["selected_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert state["backend_truth"]["actual_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert state["backend_truth"]["product_backend_proven"] is True
    assert "input:search" in state["action_graph"]["search_like_refs"]
    assert state["extraction_graph"]["product_or_result_candidate_count"] >= 1
    assert "search" in state["recommended_model_skills"]
    assert "extract_evidence" in state["recommended_model_skills"]
    assert state["raw_material_persisted"] is False
    assert state["can_execute"] is False


def test_search_action_receipt_links_environment_state_hash(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    fixture.runtime.execute(_envelope("real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        _envelope("real_browser.search", query="glasses under 5 euro"),
        authority=fixture.authority,
        context={},
    )

    state = result.context_cards["browser_environment_state"]
    receipt = fixture.load_receipt(result.receipt_refs[0])

    assert receipt["browser_environment_state_hash"] == stable_hash(state)
    assert receipt["selected_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert receipt["actual_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert receipt["session_backend_kind"] == "cloakbrowser"


def test_recoverable_search_failure_carries_environment_state_for_next_turn(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, engine=_NoSearchControlEngine())

    fixture.runtime.execute(_envelope("real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        _envelope("real_browser.search", query="glasses under 5 euro"),
        authority=fixture.authority,
        context={},
    )

    state = result.context_cards["browser_environment_state"]

    assert result.status == "recoverable_failed"
    assert result.recoverable is True
    assert result.failure_code == "real_browser_search_control_not_found"
    assert state["page_state"]["stable_ref_count"] >= 1
    assert state["backend_truth"]["actual_backend_id"] == CLOAK_BROWSER_BACKEND_ID
    assert state["can_execute"] is False


def test_environment_state_context_does_not_expose_raw_cookie_storage_or_dom(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, engine=_ProductSearchEngine())

    fixture.runtime.execute(_envelope("real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        _envelope("real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )

    serialized = json.dumps(result.context_cards["browser_environment_state"], sort_keys=True)

    assert "raw-cookie-value" not in serialized
    assert "raw-storage-value" not in serialized
    assert "<html" not in serialized.lower()
    assert "raw_dom" not in serialized.lower()


def _fixture(tmp_path: Path, *, engine: object | None = None) -> "_Fixture":
    kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
    record = kernel.create_mission(
        session_id="session_browser_cortex_pack2",
        draft=MissionDraft(
            title="Browser Cortex Pack 2",
            objective="Search a bounded product page for glasses under 5 EUR and extract relevant product cards.",
            constraints=["bounded browser URL", "no login/contact/payment"],
            expected_artifacts=["browser environment state receipts"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="browser_cortex_pack2",
            allowed_actions=[
                "real_browser.open",
                "real_browser.observe",
                "real_browser.search",
                "real_browser.extract_product_cards",
                "real_browser.verify_extraction",
            ],
            forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
            summary="Browser Cortex Pack 2 bounded browser authority.",
        ),
    )
    kernel.enqueue(record.mission_id)
    authority = MissionAuthorityEnvelope(
        id=record.mission_id,
        user_id="user_youcef",
        mission_title="Browser Cortex Pack 2",
        mission_objective="Search a bounded product page for glasses under 5 EUR and extract relevant product cards.",
        allowed_tools=["real_browser_control"],
        allowed_actions=[
            "real_browser.open",
            "real_browser.observe",
            "real_browser.search",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
        ],
        forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
        allowed_domains=["real_browser:bounded_test_url"],
        max_actions=8,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    runtime = RealBrowserControlRuntime(
        kernel=kernel,
        mission_id=record.mission_id,
        engine=engine or _ProductSearchEngine(),
        bounded_url_ref="env:SENTINEL_BROWSER_TEST_URL",
        selected_backend_id=CLOAK_BROWSER_BACKEND_ID,
    )
    return _Fixture(kernel=kernel, mission_id=record.mission_id, authority=authority, runtime=runtime)


def _envelope(operation: str, **params: str) -> ActionEnvelope:
    return ActionEnvelope(capability_id="real_browser_control", operation=operation, params=params)


class _Fixture:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        authority: MissionAuthorityEnvelope,
        runtime: RealBrowserControlRuntime,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.authority = authority
        self.runtime = runtime

    def load_receipt(self, receipt_ref: str) -> dict[str, object]:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        return json.loads(path.read_text(encoding="utf-8"))


class _ProductSearchEngine(InMemoryRealBrowserEngine):
    browser_backend_id = CLOAK_BROWSER_BACKEND_ID
    session_backend_kind = "cloakbrowser"
    session_manager_backend_kind = "cloakbrowser"

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash("cloak://browser-cortex-pack2")

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:search", "searchbox", "Search products", value_preview=self.status_value),
            RealBrowserEngineElement("button:search", "button", "Search", text_preview="Search"),
            RealBrowserEngineElement(
                "link:glasses",
                "link",
                "Blue light glasses 4.80 EUR MOQ 10",
                text_preview="Blue light glasses visible price 4.80 EUR per unit MOQ 10 Supplier VisionCraft",
            ),
        )

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self.extract_count += 1
        return (
            "<html>raw_dom_should_not_leak</html> Blue light glasses visible price 4.80 EUR per unit MOQ 10 "
            "Supplier VisionCraft raw-cookie-value raw-storage-value",
            self._snapshot(),
        )


class _NoSearchControlEngine(_ProductSearchEngine):
    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement(
                "link:glasses",
                "link",
                "Blue light glasses 4.80 EUR MOQ 10",
                text_preview="Blue light glasses visible price 4.80 EUR per unit MOQ 10 Supplier VisionCraft",
            ),
        )


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
