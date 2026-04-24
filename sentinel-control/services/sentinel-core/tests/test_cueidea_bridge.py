import pytest

from sentinel.cueidea_bridge import CueIdeaBridge, normalize_validation_response
from sentinel.shared.enums import EvidenceType


SAMPLE_VALIDATION = {
    "validation_id": "val_123",
    "report": {
        "verdict": "RISKY",
        "confidence": 72,
        "executive_summary": "Freelancers show invoice chasing pain, but WTP needs more proof.",
        "market_analysis": {
            "evidence": [
                {
                    "id": "direct_1",
                    "source": "reddit",
                    "url": "https://example.com/direct",
                    "title": "I hate chasing unpaid invoices",
                    "summary": "Freelancers complain about manual invoice follow-ups.",
                    "directness_tier": "direct",
                    "confidence": "high",
                },
                {
                    "id": "adjacent_1",
                    "source": "hn",
                    "title": "Client billing ops are messy",
                    "summary": "Adjacent operator discussion about billing workflows.",
                    "directness_tier": "adjacent",
                    "confidence": "medium",
                },
            ]
        },
        "wtp_evidence": [
            {
                "id": "wtp_1",
                "source": "reddit",
                "summary": "A freelancer says they would pay for automated payment reminders.",
                "directness_tier": "direct",
            }
        ],
        "competition_landscape": {
            "direct_competitors": [
                {"name": "InvoiceTool", "gap": "Tracks invoices but does not handle relationship-aware reminders."}
            ]
        },
        "trends_data": {
            "keyword": "invoice automation",
            "overall_trend": "growing",
            "confidence": 0.6,
        },
    },
}


class FakeTransport:
    async def get_json(self, path, params=None):
        assert path == "/api/trend-signals"
        return SAMPLE_VALIDATION

    async def post_json(self, path, payload):
        assert "idea" in payload
        return SAMPLE_VALIDATION


def test_normalize_validation_response_maps_direct_adjacent_and_wtp():
    result = normalize_validation_response(SAMPLE_VALIDATION, idea="AI invoice chasing")

    assert result.validation_id == "val_123"
    assert result.confidence == 0.72
    assert result.direct_evidence_count == 2
    assert result.adjacent_evidence_count == 1
    assert result.wtp_signal_count == 1
    assert any(item.evidence_type == EvidenceType.WTP for item in result.evidence)
    assert result.competitors[0].name == "InvoiceTool"
    assert result.trends[0].keyword == "invoice automation"


@pytest.mark.asyncio
async def test_bridge_uses_transport_and_returns_normalized_result():
    bridge = CueIdeaBridge(FakeTransport())
    result = await bridge.validate_idea("AI invoice chasing")
    competitors = await bridge.get_competitors("AI invoice chasing")
    trends = await bridge.get_trends("AI invoice chasing")

    assert result.evidence[0].metadata["proof_tier"] == "direct"
    assert competitors[0].gap.startswith("Tracks invoices")
    assert trends[0].direction == "growing"

