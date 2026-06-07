from __future__ import annotations

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.memory.models import (
    MemoryUtilityEvaluation,
    MemoryUtilityMetrics,
)


class MemoryUtilityEvaluator:
    """Measures explicit outcome deltas without mutating memory or runtime."""

    def evaluate(
        self,
        *,
        baseline: MemoryUtilityMetrics,
        with_memory: MemoryUtilityMetrics,
        memory_record_ids: list[str],
    ) -> MemoryUtilityEvaluation:
        baseline_score = _score(baseline)
        memory_score = _score(with_memory)
        delta = round(memory_score - baseline_score, 6)
        payload = {
            "baseline": baseline.model_dump(mode="json"),
            "with_memory": with_memory.model_dump(mode="json"),
            "memory_record_ids": list(dict.fromkeys(memory_record_ids)),
            "utility_delta": delta,
        }
        return MemoryUtilityEvaluation(
            evaluation_id=f"memory_utility_{stable_hash(payload)[:16]}",
            baseline=baseline,
            with_memory=with_memory,
            utility_delta=delta,
            useful=delta > 0,
            memory_record_ids=payload["memory_record_ids"],
        )


def _score(metrics: MemoryUtilityMetrics) -> float:
    intervention_penalty = min(1.0, metrics.operator_interventions / 10.0)
    failure_penalty = min(1.0, metrics.blocked_or_failed_steps / 10.0)
    return round(
        metrics.completion_score * 0.45
        + metrics.evidence_coverage * 0.35
        + (1.0 - intervention_penalty) * 0.1
        + (1.0 - failure_penalty) * 0.1,
        6,
    )
