"""CoreFinalGate checks only minimal PerformanceReceipt invariants.

Validates: Requirements 12.1, 12.2, 12.3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sentinel.agent.final_gate import CoreFinalGate
from sentinel.perf.bench.golden_missions import GoldenMission
from sentinel.perf.bench.harness import BenchmarkHarness, BenchmarkReport
from sentinel.perf.measure.latency_profiler import MissionPerformanceAggregate
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace


def _trace(*, wall_ms: int = 5) -> PerformanceTrace:
    return PerformanceTrace(
        action_id="action_perf_receipt_gate",
        mission_id="mission_perf_receipt_gate",
        organ_id="organ_perf_receipt_gate",
        action_type="test_action",
        queue_wait_ms=0,
        wall_ms=wall_ms,
        cpu_ms=0,
        bytes_in=0,
        bytes_out=0,
        tokens_in=0,
        tokens_out=0,
        cache_hit=0,
        cache_miss=0,
        organ_latency_ms=0,
        model_prefill_decode_ms=0,
        error=False,
        error_category=None,
        severity=PerformanceSeverity.INFO,
    )


def _receipt(*, wall_ms: int = 5) -> PerformanceReceipt:
    return PerformanceReceipt(
        mission_id="mission_perf_receipt_gate",
        action_id="action_perf_receipt_gate",
        organ_id="organ_perf_receipt_gate",
        action="test_action",
        trace=_trace(wall_ms=wall_ms),
        estimated_cost_usd=Decimal("0.000000"),
        model_id="test-model",
        budget_remaining=0,
        budget_limit=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _unsafe_receipt(base: PerformanceReceipt, **updates: object) -> PerformanceReceipt:
    data = {
        field_name: getattr(base, field_name)
        for field_name in type(base).model_fields
    }
    data.update(updates)
    return PerformanceReceipt.model_construct(**data)


def _isolated_invalid_flag(
    base: PerformanceReceipt,
    **updates: object,
) -> PerformanceReceipt:
    receipt = _unsafe_receipt(base, **updates)
    return _unsafe_receipt(
        receipt,
        receipt_hash=receipt._compute_receipt_hash(),
    )


def _error_codes(result) -> list[str]:
    return result.checks[0].details["errors"]


def test_core_final_gate_accepts_clean_performance_receipt() -> None:
    result = CoreFinalGate().verify_performance_receipts([_receipt()])

    assert result.accepted is True
    assert result.errors == []


def test_core_final_gate_rejects_authority_expansion_receipt() -> None:
    bad = _isolated_invalid_flag(_receipt(), authority_expansion=True)

    result = CoreFinalGate().verify_performance_receipts([bad])

    assert result.accepted is False
    assert "performance_receipt_authority_expansion" in _error_codes(result)


def test_core_final_gate_rejects_raw_secret_leakage_receipt() -> None:
    bad = _isolated_invalid_flag(_receipt(), raw_secret_leakage=True)

    result = CoreFinalGate().verify_performance_receipts([bad])

    assert result.accepted is False
    assert "performance_receipt_raw_secret_leakage" in _error_codes(result)


def test_core_final_gate_rejects_bad_performance_receipt_hash() -> None:
    bad = _unsafe_receipt(_receipt(), receipt_hash="0" * 64)

    result = CoreFinalGate().verify_performance_receipts([bad])

    assert result.accepted is False
    assert "performance_receipt_hash_mismatch" in _error_codes(result)


def test_core_final_gate_does_not_reject_latency_over_budget() -> None:
    result = CoreFinalGate().verify_performance_receipts([_receipt(wall_ms=999_999)])

    assert result.accepted is True


def test_core_final_gate_does_not_evaluate_benchmark_regressions() -> None:
    mission = GoldenMission(
        name="gate_scope_test",
        min_iterations=30,
        p50_budget_ms=10,
        p95_budget_ms=100,
        p99_budget_ms=200,
        benchmarked_modules=("sentinel.agent.runtime",),
    )
    report = BenchmarkReport(
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        iteration_count=30,
        per_mission={
            "gate_scope_test": MissionPerformanceAggregate(
                mission_id="gate_scope_test",
                action_count=30,
                p50_wall_ms=10,
                p95_wall_ms=10_000,
                p99_wall_ms=20_000,
            )
        },
        passed=True,
    )
    benchmark_verdict = BenchmarkHarness(
        golden_missions=(mission,),
        iteration_runner=lambda *_: 0,
    ).evaluate_gates(report)

    assert benchmark_verdict.passed is False
    assert CoreFinalGate().verify_performance_receipts([_receipt()]).accepted is True
