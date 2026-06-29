from __future__ import annotations

from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.action_power_contract import ActionAliasNormalizer, ActionFailureClass
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoopStatus

from test_power_pack6_real_browser_bounded_web_control import _HardSearchBrowserEngine, _RealBrowserFixture


def test_pack6c_action_alias_normalizer_canonicalizes_power_surface_aliases() -> None:
    normalizer = ActionAliasNormalizer()

    cases = [
        (
            ActionEnvelope(capability_id="finish", operation="finish"),
            ("sentinel_loop", "finish"),
        ),
        (
            ActionEnvelope(capability_id="read_only", operation="read_file_segment"),
            ("read_only_research", "read_file_segment"),
        ),
        (
            ActionEnvelope(capability_id="real_browser", operation="type_text"),
            ("real_browser_control", "real_browser.type_text"),
        ),
        (
            ActionEnvelope(capability_id="browser", operation="click"),
            ("browser_control", "browser.click"),
        ),
        (
            ActionEnvelope(capability_id="channel_transport", operation="send_message"),
            ("bounded_channel", "send_message"),
        ),
    ]

    for envelope, expected in cases:
        normalized = normalizer.normalize(envelope)
        assert (normalized.capability_id, normalized.operation) == expected


def test_pack6c_browser_open_context_exposes_actionability_registry_and_search_box_alias(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())

    opened = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser", operation="open"),
        authority=fixture.authority,
        context={},
    )

    registry = opened.context_cards["browser_actionability_registry"]
    actionability_frame = opened.context_cards["actionability_frame"]

    assert registry["generated_at_turn"] == 0
    assert registry["expires_on_navigation"] is True
    assert registry["canonical_refs"][0]["canonical_ref"] == "input:search"
    assert "search_box" in registry["canonical_refs"][0]["accepted_aliases"]
    assert registry["candidate_actions"][0]["canonical_action_id"].startswith("real_browser_control.real_browser.")
    assert actionability_frame["source_runtime"] == "real_browser_control"
    assert "search_box" in actionability_frame["executable_refs"]
    assert "real_browser_control.real_browser.type_text" in actionability_frame["accepted_aliases"]
    assert "real_browser_control.real_browser.observe" in actionability_frame["recovery_actions"]


def test_pack6c_unknown_browser_ref_is_recoverable_and_next_turn_gets_refreshed_candidates(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "search_box_missing", "text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "search_box", "text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.press_key",
                params={"ref": "search_box", "key": "Enter"},
            ),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_text"),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "browser recovered"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.capability_sequence[1] == "real_browser_control:real_browser.type_text"
    assert result.failure_diagnostics == {}
    recoverable_context = decisions.contexts[2]
    assert recoverable_context["last_recoverable_failure"]["failure_class"] == ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE
    assert recoverable_context["last_recoverable_failure"]["failure_code"] == "real_browser_element_ref_unknown"
    assert "search_box" in recoverable_context["actionability_frame"]["executable_refs"]
    assert fixture.engine.type_count == 1
    assert fixture.engine.press_count == 1
    assert result.material_action_count == 2


def test_pack6c_recovery_budget_exhaustion_blocks_without_fake_receipt(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "missing:one", "text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "missing:two", "text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "missing:three", "text": "glasses under 5 euro"},
            ),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "RECOVERY_BUDGET_EXHAUSTED"
    assert fixture.engine.type_count == 0
    assert all(not ref.startswith("real_browser_action_receipt") for ref in result.receipt_refs)


def test_pack6c_hard_boundary_failures_remain_terminal(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.open",
                params={"url": "https://example.com/outside"},
            ),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "real_browser_unbounded_url_blocked"
    assert fixture.engine.open_count == 1
