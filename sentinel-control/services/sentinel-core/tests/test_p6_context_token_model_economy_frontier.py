from __future__ import annotations

import pytest

from sentinel.agent import (
    ContextBudgetPolicy,
    ContextModeComparison,
    ContextPressureAnalyzer,
    ModelCapabilityProfile,
    ModelCostProfile,
    QualityExpectationContract,
    TokenLedger,
    UserModelContract,
)


def selected_model(
    *,
    model_name: str = "deepseek-v4-pro",
    input_price: float = 0.14,
    output_price: float = 0.28,
    max_frame_tokens: int = 2_000,
    ) -> UserModelContract:
    return UserModelContract(
        selected_provider_id="deepseek",
        selected_backend_id="deepseek_chat_completions",
        selected_model=model_name,
        cost_profile=ModelCostProfile(
            model_name=model_name,
            input_usd_per_1m=input_price,
            output_usd_per_1m=output_price,
            cached_input_usd_per_1m=input_price / 2,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model_name,
            context_window_tokens=128_000,
            supports_tool_calling=True,
            supports_vision=False,
            supports_prompt_caching=True,
            strengths=["cost_efficiency", "batch_exploration"],
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=max_frame_tokens,
            max_tool_schema_tokens=400,
            max_evidence_tokens=900,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="broad_exploration",
            minimum_evidence_refs=3,
            retry_budget=2,
        ),
    )


def seeded_ledger() -> TokenLedger:
    ledger = TokenLedger(mission_id="mission_p6q")
    ledger.add_text("browser_output", "browser_receipt_1", "browser page evidence " * 900)
    ledger.add_text("api_output", "api_receipt_1", "api json field " * 280)
    ledger.add_text("workspace_tree", "desktop_tree_1", "src/file.py\n" * 750)
    ledger.add_text("channel_draft", "draft_1", "prospect draft paragraph " * 160)
    ledger.add_text("receipt_summary", "receipt_summary_1", "receipt ref summary " * 240)
    ledger.add_text("tool_schema", "openclaw_surface", "tool schema with parameters " * 500)
    ledger.add_text("market_signal", "trading_role_report", "market analyst debate signal " * 360)
    ledger.add_text("authority_card", "authority", "allowed local workspace read write; forbidden send spend shell")
    ledger.add_text("state_card", "state", "current blocker: choose next evidence source")
    return ledger


def test_browser_api_desktop_channel_receipts_produce_token_pressure_report():
    report = ContextPressureAnalyzer().analyze(
        mission_id="mission_p6q",
        ledger=seeded_ledger(),
        user_model=selected_model(),
    )

    assert report.raw_context_tokens > report.decision_frame_tokens
    assert report.browser_output_tokens > 0
    assert report.api_output_tokens > 0
    assert report.workspace_tree_tokens > 0
    assert report.channel_draft_tokens > 0
    assert report.receipt_summary_tokens > 0
    assert report.estimated_cost_by_user_model.total_estimated_usd > 0
    assert report.largest_pressure_source in {
        "browser_output",
        "workspace_tree",
        "tool_schema",
        "market_signal",
        "api_output",
        "channel_draft",
        "receipt_summary",
    }


def test_workspace_tree_and_file_diffs_surface_desktop_pressure():
    ledger = TokenLedger(mission_id="desktop_pressure")
    ledger.add_text("workspace_tree", "tree", "nested/path/file.py\n" * 1_200)
    ledger.add_text("workspace_diff", "diff", "-old\n+new\n" * 700)

    report = ContextPressureAnalyzer().analyze(
        mission_id="desktop_pressure",
        ledger=ledger,
        user_model=selected_model(),
    )

    assert report.workspace_tree_tokens > 0
    assert report.organ_output_report.organ_tokens["workspace_diff"] > 0
    assert report.largest_pressure_source in {"workspace_tree", "workspace_diff"}
    assert "workspace_context_card" in report.p6r_implementation_inputs


def test_tradingagents_role_outputs_measure_debate_report_pressure():
    ledger = TokenLedger(mission_id="trading_pressure")
    ledger.add_text("market_signal", "market_analyst", "market analyst report " * 500)
    ledger.add_text("debate_transcript", "bull_bear_debate", "bull says buy. bear says wait. " * 600)

    report = ContextPressureAnalyzer().analyze(
        mission_id="trading_pressure",
        ledger=ledger,
        user_model=selected_model(),
    )

    assert report.market_signal_tokens > 0
    assert report.organ_output_report.organ_tokens["debate_transcript"] > 0
    assert "role_summary_cards" in report.p6r_implementation_inputs


def test_openclaw_broad_tool_surface_measures_schema_pressure():
    ledger = TokenLedger(mission_id="tool_pressure")
    for index in range(40):
        ledger.add_text("tool_schema", f"tool_{index}", f"tool_{index}(path, url, payload, account, browser_target)")

    report = ContextPressureAnalyzer().analyze(
        mission_id="tool_pressure",
        ledger=ledger,
        user_model=selected_model(max_frame_tokens=1_200),
    )

    assert report.tool_schema_tokens > report.authority_card_tokens
    assert report.tool_schema_report.tool_count == 40
    assert "tool_surface_router" in report.p6r_implementation_inputs


def test_hermes_style_compression_compares_three_context_modes():
    report = ContextPressureAnalyzer().analyze(
        mission_id="mode_comparison",
        ledger=seeded_ledger(),
        user_model=selected_model(),
        summary_ratio=0.35,
    )

    comparison = report.mode_comparison
    assert isinstance(comparison, ContextModeComparison)
    assert comparison.naive_full_context_tokens == report.raw_context_tokens
    assert comparison.naive_full_context_tokens > comparison.summary_context_tokens
    assert comparison.summary_context_tokens > comparison.subquadratic_decision_frame_tokens
    assert comparison.subquadratic_decision_frame_tokens == report.decision_frame_tokens


def test_user_selected_cheap_model_projects_broad_exploration_cost_without_override():
    model = selected_model(model_name="deepseek-v4-pro", input_price=0.14, output_price=0.28)
    report = ContextPressureAnalyzer().analyze(
        mission_id="cheap_model",
        ledger=seeded_ledger(),
        user_model=model,
    )

    assert report.user_selected_model == "deepseek-v4-pro"
    assert report.model_override_attempted is False
    assert report.estimated_cost_by_user_model.model_name == "deepseek-v4-pro"
    assert report.retry_cost_projection.retry_budget == 2
    assert "broad_exploration" in report.quality_expectation


def test_user_selected_expensive_model_projects_narrow_quality_cost_without_override():
    model = selected_model(model_name="o3-pro", input_price=15.0, output_price=60.0, max_frame_tokens=1_000)
    model = model.model_copy(
        update={
            "quality_expectation": QualityExpectationContract(
                expected_quality="critical_reasoning",
                minimum_evidence_refs=6,
                retry_budget=1,
            )
        }
    )
    report = ContextPressureAnalyzer().analyze(
        mission_id="expensive_model",
        ledger=seeded_ledger(),
        user_model=model,
    )

    assert report.user_selected_model == "o3-pro"
    assert report.model_override_attempted is False
    assert report.decision_frame_tokens > 1_000
    assert report.decision_frame_over_budget is True
    assert report.estimated_cost_by_user_model.input_cost_usd > 0
    assert "critical_reasoning" in report.quality_expectation


def test_context_pressure_reports_over_budget_without_capping_projection():
    ledger = seeded_ledger()
    model = selected_model(max_frame_tokens=500)

    report = ContextPressureAnalyzer().analyze(
        mission_id="over_budget_context",
        ledger=ledger,
        user_model=model,
    )

    assert report.decision_frame_tokens > 500
    assert report.decision_frame_over_budget is True
    assert report.estimated_cost_by_user_model.input_tokens == report.decision_frame_tokens


def test_user_model_contract_allows_recommendation_but_rejects_silent_override():
    contract = selected_model(model_name="user-selected-model")

    recommended = contract.recommend_alternative("other-model", reason="cheaper")

    assert recommended.selected_model == "user-selected-model"
    assert recommended.alternative_model_recommendations[0]["model"] == "other-model"

    with pytest.raises(ValueError, match="must not override"):
        contract.with_selected_model_override("other-model")
