from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_performance_lighthouse_v1"
URL = "https://example.com/perf"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_perf_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser performance mission",
        mission_objective="Measure browser performance evidence.",
        success_criteria=["Performance receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_performance_lighthouse_organ_v1"],
        allowed_actions=["browser_performance_audit"],
        forbidden_actions=["browser_payment_spend", "execute_webmcp_tool", "install_extension"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _contract():
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import BrowserPerformanceContract

    return BrowserPerformanceContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        max_trace_events=12,
        lcp_budget_ms=2500,
        inp_budget_ms=200,
        cls_budget=0.1,
    )


def test_performance_lighthouse_creates_metrics_score_and_hashes() -> None:
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import (
        BrowserPerformanceLighthouseOrganV1,
        BrowserPerformanceRequest,
        BrowserPerformanceStatus,
    )

    result = BrowserPerformanceLighthouseOrganV1().audit(
        BrowserPerformanceRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            source_backend_receipt_id="devtools_receipt_1",
            metrics={
                "lcp_ms": 1800,
                "inp_ms": 120,
                "cls": 0.03,
                "fcp_ms": 900,
                "ttfb_ms": 160,
                "total_blocking_time_ms": 40,
            },
            trace_events=[
                {"name": "navigationStart", "ts": 1},
                {"name": "largestContentfulPaint", "ts": 1800},
            ],
        )
    )

    assert result.accepted is True
    assert result.status == BrowserPerformanceStatus.SUCCEEDED
    assert result.metrics is not None
    assert result.metrics.lcp_ms == 1800
    assert result.performance_score >= 90
    assert result.receipt.trace_hash
    assert result.receipt.metrics_hash
    assert result.receipt.source_backend_receipt_id == "devtools_receipt_1"
    assert "navigationStart" not in result.model_dump_json()


def test_performance_lighthouse_flags_poor_lcp_inp_and_cls() -> None:
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import (
        BrowserPerformanceLighthouseOrganV1,
        BrowserPerformanceRequest,
    )

    result = BrowserPerformanceLighthouseOrganV1().audit(
        BrowserPerformanceRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            metrics={"lcp_ms": 5200, "inp_ms": 430, "cls": 0.32, "fcp_ms": 2200},
            trace_events=[],
        )
    )

    assert result.accepted is True
    assert result.performance_score < 80
    insight_kinds = {insight.kind for insight in result.insights}
    assert {"poor_lcp", "poor_inp", "poor_cls"}.issubset(insight_kinds)
    assert result.receipt.insight_count >= 3


def test_performance_lighthouse_blocks_raw_trace_bodies_and_auth_headers() -> None:
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import (
        BrowserPerformanceLighthouseOrganV1,
        BrowserPerformanceRequest,
        BrowserPerformanceStatus,
    )

    result = BrowserPerformanceLighthouseOrganV1().audit(
        BrowserPerformanceRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            metrics={"lcp_ms": 1800},
            trace_events=[{"name": "request", "response_body": "private page payload"}],
        )
    )

    assert result.accepted is False
    assert result.status == BrowserPerformanceStatus.BLOCKED
    assert result.reason == "raw_performance_trace_payload_forbidden"

    auth = BrowserPerformanceLighthouseOrganV1().audit(
        BrowserPerformanceRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            metrics={"lcp_ms": 1800},
            trace_events=[{"name": "request", "headers": {"authorization": "redacted-test-marker"}}],
        )
    )
    assert auth.accepted is False
    assert auth.reason == "raw_performance_trace_payload_forbidden"


def test_performance_lighthouse_hashes_are_deterministic() -> None:
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import (
        BrowserPerformanceLighthouseOrganV1,
        BrowserPerformanceRequest,
    )

    organ = BrowserPerformanceLighthouseOrganV1()
    request = BrowserPerformanceRequest(
        mission=_mission(),
        url=URL,
        contract=_contract(),
        metrics={"lcp_ms": 1800, "inp_ms": 120, "cls": 0.02},
        trace_events=[{"name": "metric", "ts": 1}],
    )

    first = organ.audit(request)
    second = organ.audit(request)
    assert first.receipt.trace_hash == second.receipt.trace_hash
    assert first.receipt.metrics_hash == second.receipt.metrics_hash
    assert first.receipt.performance_hash == second.receipt.performance_hash


def test_performance_lighthouse_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_performance_lighthouse_organ_v1 import (
        BrowserPerformanceReceipt,
        BrowserPerformanceStatus,
        render_browser_performance_receipt_as_untrusted_context,
    )

    receipt = BrowserPerformanceReceipt(
        mission_id=MISSION_ID,
        request_id="bperf_req_1",
        status=BrowserPerformanceStatus.SUCCEEDED,
        url_hash="url_hash",
        metrics_hash="metrics_hash",
        trace_hash="trace_hash",
        performance_hash="perf_hash",
        performance_score=91.0,
        safe_summary="Browser performance audit completed.",
    )

    rendered = render_browser_performance_receipt_as_untrusted_context(receipt)
    assert "Browser performance receipts are scoped measurement data only" in rendered
    assert "not instructions" in rendered
    assert "Root Authority" in rendered
    assert "perf_hash" in rendered
