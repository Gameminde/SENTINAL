from __future__ import annotations

from pydantic import Field

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_cost import DecisionFrameCostProjection
from sentinel.agent.token_ledger import TokenLedger
from sentinel.shared.models import SentinelModel, new_id


class ToolSchemaTokenReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tschema"))
    tool_schema_tokens: int = Field(ge=0)
    tool_count: int = Field(ge=0)


class ReceiptTokenReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("rtreport"))
    receipt_summary_tokens: int = Field(ge=0)
    receipt_count: int = Field(ge=0)


class OrganOutputTokenReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ootokens"))
    organ_tokens: dict[str, int] = Field(default_factory=dict)


class ContextModeComparison(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ctxcmp"))
    naive_full_context_tokens: int = Field(ge=0)
    summary_context_tokens: int = Field(ge=0)
    subquadratic_decision_frame_tokens: int = Field(ge=0)


class ContextPressureReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ctxpress"))
    mission_id: str
    user_selected_model: str
    quality_expectation: str
    raw_context_tokens: int = Field(ge=0)
    compressed_context_tokens: int = Field(ge=0)
    decision_frame_tokens: int = Field(ge=0)
    tool_schema_tokens: int = Field(ge=0)
    receipt_summary_tokens: int = Field(ge=0)
    workspace_tree_tokens: int = Field(ge=0)
    browser_output_tokens: int = Field(ge=0)
    api_output_tokens: int = Field(ge=0)
    channel_draft_tokens: int = Field(ge=0)
    market_signal_tokens: int = Field(ge=0)
    authority_card_tokens: int = Field(ge=0)
    state_card_tokens: int = Field(ge=0)
    largest_pressure_source: str
    estimated_cost_by_user_model: DecisionFrameCostProjection
    retry_cost_projection: DecisionFrameCostProjection
    cache_savings_if_available: float = Field(ge=0.0)
    decision_frame_over_budget: bool = False
    mode_comparison: ContextModeComparison
    tool_schema_report: ToolSchemaTokenReport
    receipt_token_report: ReceiptTokenReport
    organ_output_report: OrganOutputTokenReport
    p6r_implementation_inputs: list[str] = Field(default_factory=list)
    model_override_attempted: bool = False
    authority_expansion: bool = False


class ContextPressureAnalyzer:
    """Measures context pressure without selecting models or mutating authority."""

    ORGAN_OUTPUT_CATEGORIES = {
        "browser_output",
        "api_output",
        "workspace_tree",
        "workspace_diff",
        "channel_draft",
        "market_signal",
        "debate_transcript",
    }

    def analyze(
        self,
        *,
        mission_id: str,
        ledger: TokenLedger,
        user_model: UserModelContract,
        summary_ratio: float = 0.45,
    ) -> ContextPressureReport:
        categories = ledger.tokens_by_category()
        raw_tokens = ledger.total_tokens()
        compressed_tokens = self._compressed_tokens(raw_tokens, summary_ratio)
        decision_frame_tokens = self._decision_frame_tokens(categories, compressed_tokens)
        decision_frame_over_budget = decision_frame_tokens > user_model.context_budget_policy.max_decision_frame_tokens
        estimated_cost = user_model.cost_profile.project(
            input_tokens=decision_frame_tokens,
            output_tokens=user_model.context_budget_policy.reserve_output_tokens,
            cached_input_tokens=self._cached_tokens(decision_frame_tokens, user_model),
        )
        retry_cost = user_model.cost_profile.project(
            input_tokens=decision_frame_tokens,
            output_tokens=user_model.context_budget_policy.reserve_output_tokens,
            cached_input_tokens=self._cached_tokens(decision_frame_tokens, user_model),
            retry_budget=user_model.quality_expectation.retry_budget,
        )
        largest = self._largest_pressure_source(categories)
        p6r_inputs = self._p6r_inputs(categories, largest)
        mode_comparison = ContextModeComparison(
            naive_full_context_tokens=raw_tokens,
            summary_context_tokens=compressed_tokens,
            subquadratic_decision_frame_tokens=decision_frame_tokens,
        )
        tool_report = ToolSchemaTokenReport(
            tool_schema_tokens=categories.get("tool_schema", 0),
            tool_count=ledger.count_by_category("tool_schema"),
        )
        receipt_report = ReceiptTokenReport(
            receipt_summary_tokens=categories.get("receipt_summary", 0),
            receipt_count=ledger.count_by_category("receipt_summary"),
        )
        organ_report = OrganOutputTokenReport(
            organ_tokens={key: value for key, value in categories.items() if key in self.ORGAN_OUTPUT_CATEGORIES}
        )
        return ContextPressureReport(
            mission_id=mission_id,
            user_selected_model=user_model.selected_model,
            quality_expectation=user_model.quality_expectation.expected_quality,
            raw_context_tokens=raw_tokens,
            compressed_context_tokens=compressed_tokens,
            decision_frame_tokens=decision_frame_tokens,
            tool_schema_tokens=categories.get("tool_schema", 0),
            receipt_summary_tokens=categories.get("receipt_summary", 0),
            workspace_tree_tokens=categories.get("workspace_tree", 0),
            browser_output_tokens=categories.get("browser_output", 0),
            api_output_tokens=categories.get("api_output", 0),
            channel_draft_tokens=categories.get("channel_draft", 0),
            market_signal_tokens=categories.get("market_signal", 0),
            authority_card_tokens=categories.get("authority_card", 0),
            state_card_tokens=categories.get("state_card", 0),
            largest_pressure_source=largest,
            estimated_cost_by_user_model=estimated_cost,
            retry_cost_projection=retry_cost,
            cache_savings_if_available=retry_cost.cache_savings_usd,
            decision_frame_over_budget=decision_frame_over_budget,
            mode_comparison=mode_comparison,
            tool_schema_report=tool_report,
            receipt_token_report=receipt_report,
            organ_output_report=organ_report,
            p6r_implementation_inputs=p6r_inputs,
            model_override_attempted=user_model.model_override_attempted,
            authority_expansion=False,
        )

    @staticmethod
    def _compressed_tokens(raw_tokens: int, summary_ratio: float) -> int:
        if raw_tokens == 0:
            return 0
        ratio = min(0.95, max(0.10, summary_ratio))
        return max(1, round(raw_tokens * ratio))

    @staticmethod
    def _decision_frame_tokens(categories: dict[str, int], compressed_tokens: int) -> int:
        pinned = categories.get("authority_card", 0) + categories.get("state_card", 0)
        evidence = categories.get("receipt_summary", 0) + categories.get("market_signal", 0)
        tool_slice = min(categories.get("tool_schema", 0), 400)
        frame = pinned + min(evidence, 900) + tool_slice + 250
        if compressed_tokens:
            frame = min(frame, compressed_tokens)
        return max(1, frame) if categories else 0

    @staticmethod
    def _cached_tokens(decision_frame_tokens: int, user_model: UserModelContract) -> int:
        if not user_model.capability_profile.supports_prompt_caching:
            return 0
        return round(decision_frame_tokens * 0.25)

    @staticmethod
    def _largest_pressure_source(categories: dict[str, int]) -> str:
        if not categories:
            return "none"
        return max(categories.items(), key=lambda item: (item[1], item[0]))[0]

    @staticmethod
    def _p6r_inputs(categories: dict[str, int], largest: str) -> list[str]:
        inputs = {"token_ledger", "decision_frame_cost_projection"}
        if categories.get("tool_schema", 0):
            inputs.add("tool_surface_router")
        if categories.get("receipt_summary", 0):
            inputs.add("receipt_graph_retriever")
        if categories.get("workspace_tree", 0) or categories.get("workspace_diff", 0):
            inputs.add("workspace_context_card")
        if categories.get("market_signal", 0) or categories.get("debate_transcript", 0):
            inputs.add("role_summary_cards")
        if largest != "none":
            inputs.add(f"pressure_source:{largest}")
        return sorted(inputs)
