"""Deterministic local golden-mission runners for Phase F full lock.

The runners in this module exercise existing Sentinel runtime surfaces without
adding product powers or external execution. They are intentionally local and
deterministic: filesystem work is isolated in disposable temporary
directories, network/browser automation is not invoked, and every operation is
measured as wall-clock latency in milliseconds.
"""

from __future__ import annotations

import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sentinel.agent.context_builder import ContextBuilder
from sentinel.agent.context_compressor import ContextCompressor
from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.agent.evidence_ranker import EvidenceCard
from sentinel.agent.runtime import AgentRuntime
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.prompt_budget import PromptBudgetAllocator
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.mission.runner import MissionRunner
from sentinel.perf.bench.golden_missions import GoldenMission
from sentinel.perf.caches.context_build_cache import ContextBuildCache
from sentinel.perf.hot_cold.artifact_ref_store import ArtifactRefStore
from sentinel.perf.hot_cold.cache_invalidation_policy import CacheInvalidationPolicy
from sentinel.perf.hot_cold.cold_receipt_store import ColdReceiptStore
from sentinel.perf.hot_cold.hot_mission_cache import HotMissionCache
from sentinel.perf.hot_cold.receipt_index import ReceiptIndex
from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.perf.sched.backpressure_controller import BackpressureController
from sentinel.perf.sched.batch_execution_planner import BatchExecutionPlanner
from sentinel.perf.sched.tool_call_queue import Priority, QueuedAction, ToolCallQueue
from sentinel.perf.workspace.workspace_change_watcher import WorkspaceDelta
from sentinel.perf.workspace.workspace_snapshot_cache import WorkspaceSnapshotCache
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.shared.events import EventBus

__all__ = ["run_golden_mission_iteration"]


def run_golden_mission_iteration(mission: GoldenMission, iteration: int) -> int:
    """Run one deterministic local iteration for a golden mission class."""

    start_ns = time.perf_counter_ns()
    if mission.name == "startup":
        _run_startup(iteration)
    elif mission.name == "single_tool":
        _run_single_tool(iteration)
    elif mission.name == "multi_tool":
        _run_multi_tool(iteration)
    elif mission.name == "browser_heavy":
        _run_browser_heavy(iteration)
    else:
        raise ValueError(f"Unknown golden mission class: {mission.name}")
    elapsed_ns = time.perf_counter_ns() - start_ns
    return max(0, (elapsed_ns + 999_999) // 1_000_000)


def _envelope(name: str, iteration: int) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="phase_f_benchmark",
        mission_type=MissionType.GTM,
        mission_title=f"Phase F {name} golden mission",
        mission_objective=f"Run deterministic local benchmark iteration {iteration}.",
        success_criteria=["Trace exists", "Local benchmark completes"],
        mode=MissionMode.POWER,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_file_writer"],
        allowed_actions=[
            "create_project_folder",
            "create_markdown_file",
            "export_json",
            "generate_gtm_pack",
            "generate_landing_copy",
            "generate_outreach_drafts_without_sending",
            "create_watchlist",
            "generate_research_questions",
            "write_trace",
        ],
        forbidden_actions=[
            "send_email",
            "run_shell_command",
            "browser_submit_form",
            "credential_access",
        ],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=30,
        max_actions=20,
        max_cost_usd=1.0,
    )


def _run_startup(iteration: int) -> None:
    with tempfile.TemporaryDirectory(prefix="sentinel-phase-f-startup-") as tmp:
        root = Path(tmp)
        envelope = _envelope("startup", iteration)
        event_bus = EventBus(mission_id=envelope.id)
        profiler = LatencyProfiler(event_bus)
        hot_cache = HotMissionCache()
        with profiler.instrument(
            mission_id=envelope.id,
            action_id=f"{envelope.id}:startup",
            action_type="golden_startup",
        ):
            AgentRuntime(project_root=root, latency_profiler=profiler)
            MissionRunner(
                project_root=root,
                latency_profiler=profiler,
                hot_cache=hot_cache,
            )
            hot_cache.set_objective(envelope.id, envelope.mission_objective)
            hot_cache.set_constraints(envelope.id, envelope.success_criteria)
            hot_cache.evict_mission(envelope.id)
        profiler.aggregate_mission(envelope.id)


def _run_single_tool(iteration: int) -> None:
    envelope = _envelope("single_tool", iteration)
    event_bus = EventBus(mission_id=envelope.id)
    builder = ContextBuilder()
    compressor = ContextCompressor()
    cache = ContextBuildCache(event_bus=event_bus)
    key = cache.composite_key(
        mission_hot_hash=f"mission-{iteration}",
        workspace_snapshot_id="workspace-snapshot-phase-f",
        organ_state_hash="organ-state-phase-f",
        authority_hash=f"authority-{envelope.id}",
    )
    context = cache.get_or_build(
        key,
        lambda: builder.build(
            envelope,
            user_input={"idea": "Phase F single tool"},
            evidence_refs=["ev_phase_f_single_tool"],
        ),
        mission_id=envelope.id,
    )
    compressed = compressor.compress(context)
    evidence = [
        EvidenceCard(
            receipt_id="receipt_phase_f_single_tool",
            source_type="local",
            summary=compressed.summary,
            evidence_refs=["ev_phase_f_single_tool"],
            relevance_score=1.0,
            token_count=10,
            critical=True,
        )
    ]
    frame = LLMDecisionFrame.build(
        mission_id=envelope.id,
        mission_card={"objective": envelope.mission_objective},
        authority_card={"allowed_actions": envelope.allowed_actions},
        progress_card={"iteration": iteration},
        evidence=evidence,
        selected_tool_surface=["safe_file_writer"],
        current_blockers=[],
        next_decision_options=["continue"],
        required_output_schema={"type": "object"},
        budget_allocator=PromptBudgetAllocator(_user_model()),
    )
    frame.render_prompt_text()


def _run_multi_tool(iteration: int) -> None:
    envelope = _envelope("multi_tool", iteration)
    event_bus = EventBus(mission_id=envelope.id)
    queue = ToolCallQueue(max_depth=16)
    backpressure = BackpressureController(
        event_bus=event_bus,
        queue=queue,
        max_queue_depth=16,
        max_organ_concurrency=4,
    )
    actions = [
        QueuedAction(
            action_id=f"phase-f-{iteration}-{idx}",
            mission_id=envelope.id,
            organ_id="filesystem",
            action_type="file_read" if idx < 2 else "metadata_fetch",
            priority=Priority.NORMAL,
            deadline_ms=1000,
            enqueued_at_ns=time.monotonic_ns(),
            estimated_cost_ms=5,
        )
        for idx in range(3)
    ]
    for action in actions:
        decision = backpressure.check_submission(action, envelope=envelope)
        if decision.accepted:
            queue.enqueue(action)
            backpressure.note_enqueue(action, byte_estimate=128)
    BatchExecutionPlanner().plan(actions)
    while queue.dequeue() is not None:
        queue.note_completion("filesystem")


def _run_browser_heavy(iteration: int) -> None:
    with tempfile.TemporaryDirectory(prefix="sentinel-phase-f-browser-heavy-") as tmp:
        root = Path(tmp)
        event_bus = EventBus(mission_id=f"mission_phase_f_browser_heavy_{iteration}")
        payload = f"<html><title>Phase F {iteration}</title></html>".encode("utf-8")
        artifact_store = ArtifactRefStore(root, event_bus=event_bus)
        artifact_ref = artifact_store.put(payload, content_type="text")
        artifact_store.get(artifact_ref.content_hash)

        cold_store = ColdReceiptStore(root, event_bus=event_bus)
        index = ReceiptIndex(event_bus=event_bus, cold_store=cold_store)
        receipt = _receipt(mission_id=f"mission_phase_f_browser_heavy_{iteration}")
        ref = index.persist_and_index(
            receipt,
            entity_path="bench/page.html",
            content_hash=artifact_ref.content_hash,
        )
        if ref is not None:
            cold_store.load(ref.receipt_id)
        index.query(
            mission_id=receipt.mission_id,
            timestamp_range=(0, time.time_ns()),
        )

        policy = CacheInvalidationPolicy(event_bus=event_bus)
        snapshot = WorkspaceSnapshotCache(invalidation_policy=policy)
        snapshot.apply_delta(
            WorkspaceDelta(
                type="CREATED",
                path="bench/page.html",
                previous_path=None,
                mtime_ns=time.time_ns(),
                size=len(payload),
                content_sha256=artifact_ref.content_hash,
                detected_at_ns=time.monotonic_ns(),
            )
        )
        snapshot.snapshot_id
        index.close()
        cold_store.close()


def _receipt(*, mission_id: str) -> PerformanceReceipt:
    trace = PerformanceTrace(
        action_id="phase_f_browser_heavy_read",
        mission_id=mission_id,
        organ_id="browser_heavy",
        action_type="receipt_retrieval",
        queue_wait_ms=0,
        wall_ms=1,
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
    return PerformanceReceipt(
        mission_id=mission_id,
        action_id="phase_f_browser_heavy_read",
        organ_id="browser_heavy",
        action="receipt_retrieval",
        trace=trace,
        estimated_cost_usd=Decimal("0.000000"),
        model_id="phase-f-local",
        budget_remaining=0,
        budget_limit=0,
        created_at=datetime.now(UTC),
    )


def _user_model() -> UserModelContract:
    model_name = "phase-f-local-model"
    return UserModelContract(
        selected_model=model_name,
        cost_profile=ModelCostProfile(
            model_name=model_name,
            input_usd_per_1m=0,
            output_usd_per_1m=0,
            context_window_tokens=8_192,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model_name,
            context_window_tokens=8_192,
            supports_tool_calling=True,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=1_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="deterministic local benchmark",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )
