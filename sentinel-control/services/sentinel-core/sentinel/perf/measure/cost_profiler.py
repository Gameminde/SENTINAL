"""``CostProfiler`` — per-model-call token cost tracking and receipt emission.

This module provides the ``CostProfiler`` class which ingests token usage
from model calls, computes estimated USD cost, tracks cumulative budget
consumption per mission, and emits a ``PerformanceReceipt`` via the
``EventBus`` for every recorded model call.

Requirements covered: 1.2, 10.9.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceTrace
from sentinel.shared.events import AgentEventType, EventBus


class CostProfiler:
    """Tracks tokens_in, tokens_out, estimated_cost_usd, model_id per model call.

    Requirements: 1.2, 10.9
    """

    def __init__(
        self,
        event_bus: EventBus,
        budget_limit: int = 1_000_000,
        cost_per_token_usd: Decimal = Decimal("0.000001"),
    ) -> None:
        self._event_bus = event_bus
        self._budget_limit = budget_limit
        self._cost_per_token_usd = cost_per_token_usd
        self._budget_spent: dict[str, int] = {}

    def record_model_call(
        self,
        *,
        action_id: str,
        mission_id: str,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
    ) -> PerformanceReceipt:
        """Record a model call and emit a PerformanceReceipt.

        Computes total token usage, estimated cost in USD, updates the
        cumulative budget for the mission, builds a PerformanceTrace and
        PerformanceReceipt, emits the receipt on the EventBus, and returns it.
        """
        total_tokens = tokens_in + tokens_out
        estimated_cost_usd = Decimal(total_tokens) * self._cost_per_token_usd

        # Update cumulative budget spent for this mission
        self._budget_spent[mission_id] = self._budget_spent.get(mission_id, 0) + total_tokens

        budget_remaining = max(0, self._budget_limit - self._budget_spent[mission_id])

        trace = PerformanceTrace(
            action_id=action_id,
            mission_id=mission_id,
            action_type="model_call",
            queue_wait_ms=0,
            wall_ms=0,
            cpu_ms=0,
            bytes_in=0,
            bytes_out=0,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cache_hit=0,
            cache_miss=0,
            organ_latency_ms=0,
            model_prefill_decode_ms=0,
            error=False,
            error_category=None,
        )

        receipt = PerformanceReceipt(
            mission_id=mission_id,
            action_id=action_id,
            action="model_call",
            trace=trace,
            estimated_cost_usd=estimated_cost_usd,
            model_id=model_id,
            budget_remaining=budget_remaining,
            budget_limit=self._budget_limit,
            created_at=datetime.now(UTC),
        )

        self._event_bus.append(
            event_type=AgentEventType.PERFORMANCE_RECEIPT_RECORDED,
            summary=f"CostProfiler: model_call receipt for model={model_id}, "
            f"tokens_in={tokens_in}, tokens_out={tokens_out}, "
            f"cost_usd={estimated_cost_usd}",
            payload={"receipt_id": receipt.id, "model_id": model_id},
        )

        return receipt


__all__ = ["CostProfiler"]
