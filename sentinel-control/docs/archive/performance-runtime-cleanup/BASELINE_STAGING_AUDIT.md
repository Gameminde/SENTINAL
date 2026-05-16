# Phase A-E Baseline Staging Audit

Status: dry-run staging audit only.

Do not commit yet. Do not start Phase F yet. Do not use `git add .`. Do not stage broad directories.

## Commands Used

Dry-run / inspection commands used:

```bash
git diff --stat
git diff --name-only
git diff --unified=0 -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git diff --unified=0 -- sentinel-control/services/sentinel-core/sentinel/mission/runner.py
git diff -- sentinel-control/services/sentinel-core/pyproject.toml
git diff -- sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

Additional non-staging file-list checks were used to enumerate exact candidate files under `.kiro`, `sentinel/perf`, and `tests/perf`.

No staging command was run.

## Candidate Staging File List

### Group 1: Spec Files and Lock / Backlog Reports

All files exist.

```text
.kiro/specs/sentinel-performance-runtime-foundation/tasks.md
.kiro/specs/sentinel-performance-runtime-foundation/design.md
.kiro/specs/sentinel-performance-runtime-foundation/requirements.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
```

Important:

```text
.kiro is ignored by .gitignore.
```

These files require explicit forced staging if they are approved for the baseline.

### Group 2: `sentinel/perf/*` Modules

Exact candidate files:

```text
sentinel-control/services/sentinel-core/sentinel/perf/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/bench/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/context_build_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/llm_decision_frame_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/prompt_frame_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/caches/token_budget_governor.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/artifact_ref_store.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cache_invalidation_policy.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cold_receipt_store.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/delta_state_engine.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/hot_mission_cache.py
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/receipt_index.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/cost_profiler.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/latency_profiler.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_receipt.py
sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_trace.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/async_organ_scheduler.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/backpressure_controller.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/batch_execution_planner.py
sentinel-control/services/sentinel-core/sentinel/perf/sched/tool_call_queue.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/__init__.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_change_watcher.py
sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_snapshot_cache.py
```

Do not stage generated cache files:

```text
sentinel-control/services/sentinel-core/sentinel/perf/**/__pycache__/
sentinel-control/services/sentinel-core/sentinel/perf/**/*.pyc
```

### Group 3: `tests/perf/*` Tests

Exact candidate files:

```text
sentinel-control/services/sentinel-core/tests/perf/__init__.py
sentinel-control/services/sentinel-core/tests/perf/caches/__init__.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_canonical_equivalence_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_invalidation_dependency_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_decision_frame_cache_lifecycle_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_runtime_cache_wiring.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_safety_invariants_property.py
sentinel-control/services/sentinel-core/tests/perf/caches/test_token_budget_enforcement_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/__init__.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_artifact_ref_store_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_cold_receipt_store_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_hot_cold_bounds_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_phase_b_benchmarks.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_receipt_index_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/__init__.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_latency_profiler_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_receipt_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_trace_property.py
sentinel-control/services/sentinel-core/tests/perf/measure/test_profiler_eventbus_wireup.py
sentinel-control/services/sentinel-core/tests/perf/sched/__init__.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_backpressure_lifecycle_property.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_runtime_scheduler_wiring.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_non_blocking_property.py
sentinel-control/services/sentinel-core/tests/perf/workspace/__init__.py
sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_benchmark.py
sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_delta_semantics.py
```

Do not stage generated cache files:

```text
sentinel-control/services/sentinel-core/tests/perf/**/__pycache__/
sentinel-control/services/sentinel-core/tests/perf/**/*.pyc
```

### Group 4: Runtime Integration Candidates

Exact candidate files:

```text
sentinel-control/services/sentinel-core/pyproject.toml
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

`pyproject.toml` is safe as a whole-file stage:

```text
performance-runtime hunk:
- adds pytest marker: slow: long-running benchmark or property test
```

`sentinel/shared/events.py` is untracked, so `git diff -- sentinel/shared/events.py` does not show content. It is required as a baseline candidate because:

- Phase D lock report names `sentinel/shared/events.py` as the shared EventBus / AgentEventType layer.
- Perf modules and tests reference `sentinel.shared.events`, `AgentEventType`, and `EventBus`.
- `AgentRuntime` imports performance event types through the shared/agent event bridge.

Recommendation: include `sentinel/shared/events.py` only if the baseline owner accepts that Phase A-D event-layer relocation is part of this baseline. It should be staged as a whole new file only after a content review.

## Group 4 Hunk-Level Summary

### `sentinel/agent/runtime.py`

Classification by observed diff areas:

| Area | Classification | Stage? |
|---|---|---|
| Imports adding `asyncio`, `uuid`, `TYPE_CHECKING`, `Callable`, `ConfigDict`, `SentinelModel` | mixed performance-runtime and support imports | stage only performance-related lines; requires hunk edit |
| Import `CoreFinalGate` and `AgentContext` | prior full-system-audit dependency | exclude from Phase A-E baseline unless broader prior-audit baseline is approved |
| `TYPE_CHECKING` imports for `ContextBuildCache`, `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor`, `CostProfiler`, `LatencyProfiler`, `AsyncOrganScheduler`, `BackpressureController` | performance-runtime hunk | stage |
| `TYPE_CHECKING` imports for `OrganAuthorityEnvelope`, `OrganDryRunReceipt`, `OrganKillSwitch` | performance-runtime scheduler support | stage if scheduler wiring is included |
| `_ToolCallSchedulerAction` model | performance-runtime Phase D scheduler wiring | stage |
| Constructor optional injections for latency/cost profilers, caches, scheduler, backpressure | performance-runtime hunk | stage |
| Stored `_latency_profiler`, `_cost_profiler`, cache fields, scheduler fields | performance-runtime hunk | stage |
| `_final_gate = CoreFinalGate()` | prior full-system-audit dependency | exclude |
| `_assert_memory_not_authority_boundary(...)` helper | prior full-system-audit dependency | exclude |
| Hoisted `plan`, `mission_result`, original allowed actions for final-gate/memory-not-authority failure paths | prior full-system-audit dependency | exclude |
| ContextBuildCache integration around `context_builder.build` and latency profiler instrumentation | performance-runtime hunk | stage |
| Latency profiler instrumentation around `context_compressor.compress` and `cognitive_cycle.orient` | performance-runtime hunk | stage |
| Memory-not-authority boundary checks between phases | prior full-system-audit dependency | exclude |
| Return-site wrapping via `_apply_final_gate(...)` | prior full-system-audit dependency | exclude |
| Scheduler eligibility and `_route_local_tool_call_through_scheduler(...)` | performance-runtime Phase D scheduler wiring | stage |
| `_build_decision_frame_cached`, `_render_prompt_text_cached`, `_enforce_frame_budget` | performance-runtime Phase C helper-only adoption | stage |
| `_apply_final_gate(...)` | prior full-system-audit dependency | exclude |

Audit note:

```text
runtime.py is not safe for whole-file staging.
It requires `git add -p` with hunk splitting/manual edit.
Some hunks mix performance-runtime lines with prior full-system-audit lines.
```

### `sentinel/mission/runner.py`

Classification by observed diff areas:

| Area | Classification | Stage? |
|---|---|---|
| `TYPE_CHECKING` import | performance-runtime support | stage only if paired with perf imports |
| `ColdReceiptStore`, `HotMissionCache`, `ReceiptIndex`, `LatencyProfiler` type imports | performance-runtime hunk | stage |
| `CancellationToken`, `MissionRevokedException` imports | prior full-system-audit dependency | exclude |
| `BrowserOperatorRouteRejected` import | unrelated/browser/full-system-audit hunk | exclude |
| Constructor optional injections for profiler, hot cache, cold store, receipt index | performance-runtime hunk | stage |
| Stored `_latency_profiler`, `_hot_cache`, `_cold_store`, `_receipt_index` | performance-runtime hunk | stage |
| `run_mission` wrapper with profiler start/stop and hot cache set/evict | performance-runtime hunk | stage |
| `cancellation_token` parameter propagation | prior full-system-audit dependency | exclude |
| Revocation polling before/after plan steps | prior full-system-audit dependency | exclude |
| REVOKED terminal status branch | prior full-system-audit dependency | exclude |
| `_check_revocation(...)` helper | prior full-system-audit dependency | exclude |
| `BrowserOperatorRouteRejected` wrapping in browser route | unrelated/browser/full-system-audit hunk | exclude |

Audit note:

```text
runner.py is not safe for whole-file staging.
It requires `git add -p` with hunk splitting/manual edit.
The wrapper around `run_mission` is especially mixed because profiler/hot-cache wiring and cancellation-token propagation are adjacent.
```

## Exact Files Excluded

Excluded from the Phase A-E baseline unless explicitly reclassified:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/BASELINE_PLAN.md
sentinel-control/docs/BASELINE_STAGING_AUDIT.md
sentinel-control/services/sentinel-core/_junit.xml
sentinel-control/services/sentinel-core/_tmp_cold_store_smoke.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/accessibility_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/advanced_pool.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/cdp_ax.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/controlled_runner.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/dom_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/download_quarantine.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/evidence_adapter.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/extraction.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/form_submit.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/interaction_dry_run.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/interaction_execution.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/live_fetch.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/models.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/multitab_operator.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/observability.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/operator_runtime.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/pdf.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/playwright_interaction_backend.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/playwright_renderer.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/public_lifecycle.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/rendered_snapshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/screenshot.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/supervisor.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/ui_observation.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/upload_authorized.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/url_guard.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/v3_advanced_authorities.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/v3_authority.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/verifier.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/visual_observation.py
sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py
sentinel-control/services/sentinel-core/sentinel/agent/event_bus.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/evidence_ranker.py
sentinel-control/services/sentinel-core/sentinel/agent/exceptions.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/sentinel/agent/invariants.py
sentinel-control/services/sentinel-core/sentinel/agent/models.py
sentinel-control/services/sentinel-core/sentinel/agent/phases.py
sentinel-control/services/sentinel-core/sentinel/agent/state.py
sentinel-control/services/sentinel-core/sentinel/agent/supervisor.py
sentinel-control/services/sentinel-core/sentinel/learning/self_improvement.py
sentinel-control/services/sentinel-core/sentinel/mission/autonomy.py
sentinel-control/services/sentinel-core/sentinel/mission/cancellation.py
sentinel-control/services/sentinel-core/sentinel/mission/exceptions.py
sentinel-control/services/sentinel-core/sentinel/mission/gate_sequence.py
sentinel-control/services/sentinel-core/sentinel/mission/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/mission/risk.py
sentinel-control/services/sentinel-core/sentinel/organs/authority.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/accessibility_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/advanced_pool.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/cdp_ax.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/controlled_runner.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/dom_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/download_quarantine.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/evidence_adapter.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/extraction.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/final_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/form_submit.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/interaction_dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/interaction_execution.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/live_fetch.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/models.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/multitab_operator.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/observability.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/operator_runtime.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/pdf.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/playwright_interaction_backend.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/playwright_renderer.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/public_lifecycle.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/receipt_wrapper.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/rendered_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/screenshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/supervisor.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/ui_observation.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/upload_authorized.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/url_guard.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/v3_advanced_authorities.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/v3_authority.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/verifier.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/visual_observation.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/contracts.py
sentinel-control/services/sentinel-core/sentinel/organs/desktop/harvest.py
sentinel-control/services/sentinel-core/sentinel/organs/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/exceptions.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/implementation_alignment.py
sentinel-control/services/sentinel-core/sentinel/organs/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/organs/promotion_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/registry.py
sentinel-control/services/sentinel-core/sentinel/organs/replay.py
sentinel-control/services/sentinel-core/sentinel/organs/risk.py
sentinel-control/services/sentinel-core/sentinel/organs/vendor_harvest.py
sentinel-control/services/sentinel-core/tests/test_agent_invariants.py
sentinel-control/services/sentinel-core/tests/test_agent_phases.py
sentinel-control/services/sentinel-core/tests/test_browser_organ_final_gate.py
sentinel-control/services/sentinel-core/tests/test_browser_receipt_wrapper.py
sentinel-control/services/sentinel-core/tests/test_decision_frame_mandatory_params.py
sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py
sentinel-control/services/sentinel-core/tests/test_kill_switch_reactive_property.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_bias.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_property.py
sentinel-control/services/sentinel-core/tests/test_mission_runner_browser_operator_route_rejected.py
sentinel-control/services/sentinel-core/tests/test_p6_external_organ_foundry.py
sentinel-control/services/sentinel-core/tests/test_p6_subquadratic_agent_context_engine.py
sentinel-control/services/sentinel-core/tests/test_sanitization_property.py
sentinel-control/services/sentinel-core/tests/test_self_improvement.py
sentinel-control/services/sentinel-core/tests/test_shared_events_layering.py
sentinel-control/services/sentinel-core/tests/test_toctou_binding_property.py
sentinel-control/services/sentinel-core/tests/test_trace_hash_property.py
```

## Recommended Staging Commands

Group 1, forced because `.kiro` is ignored:

```bash
git add -f -- .kiro/specs/sentinel-performance-runtime-foundation/tasks.md .kiro/specs/sentinel-performance-runtime-foundation/design.md .kiro/specs/sentinel-performance-runtime-foundation/requirements.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md .kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
```

Group 2, exact files only:

```bash
git add -- sentinel-control/services/sentinel-core/sentinel/perf/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/bench/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/caches/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/caches/context_build_cache.py sentinel-control/services/sentinel-core/sentinel/perf/caches/llm_decision_frame_cache.py sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py sentinel-control/services/sentinel-core/sentinel/perf/caches/prompt_frame_cache.py sentinel-control/services/sentinel-core/sentinel/perf/caches/token_budget_governor.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/artifact_ref_store.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cache_invalidation_policy.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/cold_receipt_store.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/delta_state_engine.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/hot_mission_cache.py sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/receipt_index.py sentinel-control/services/sentinel-core/sentinel/perf/measure/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/measure/cost_profiler.py sentinel-control/services/sentinel-core/sentinel/perf/measure/latency_profiler.py sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_receipt.py sentinel-control/services/sentinel-core/sentinel/perf/measure/performance_trace.py sentinel-control/services/sentinel-core/sentinel/perf/sched/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/sched/async_organ_scheduler.py sentinel-control/services/sentinel-core/sentinel/perf/sched/backpressure_controller.py sentinel-control/services/sentinel-core/sentinel/perf/sched/batch_execution_planner.py sentinel-control/services/sentinel-core/sentinel/perf/sched/tool_call_queue.py sentinel-control/services/sentinel-core/sentinel/perf/workspace/__init__.py sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_change_watcher.py sentinel-control/services/sentinel-core/sentinel/perf/workspace/workspace_snapshot_cache.py
```

Group 3, exact files only:

```bash
git add -- sentinel-control/services/sentinel-core/tests/perf/__init__.py sentinel-control/services/sentinel-core/tests/perf/caches/__init__.py sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_canonical_equivalence_property.py sentinel-control/services/sentinel-core/tests/perf/caches/test_cache_invalidation_dependency_property.py sentinel-control/services/sentinel-core/tests/perf/caches/test_decision_frame_cache_lifecycle_property.py sentinel-control/services/sentinel-core/tests/perf/caches/test_runtime_cache_wiring.py sentinel-control/services/sentinel-core/tests/perf/caches/test_safety_invariants_property.py sentinel-control/services/sentinel-core/tests/perf/caches/test_token_budget_enforcement_property.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/__init__.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_artifact_ref_store_property.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_cold_receipt_store_property.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_hot_cold_bounds_property.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_phase_b_benchmarks.py sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_receipt_index_property.py sentinel-control/services/sentinel-core/tests/perf/measure/__init__.py sentinel-control/services/sentinel-core/tests/perf/measure/test_latency_profiler_benchmark.py sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_receipt_property.py sentinel-control/services/sentinel-core/tests/perf/measure/test_performance_trace_property.py sentinel-control/services/sentinel-core/tests/perf/measure/test_profiler_eventbus_wireup.py sentinel-control/services/sentinel-core/tests/perf/sched/__init__.py sentinel-control/services/sentinel-core/tests/perf/sched/test_backpressure_lifecycle_property.py sentinel-control/services/sentinel-core/tests/perf/sched/test_runtime_scheduler_wiring.py sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_benchmark.py sentinel-control/services/sentinel-core/tests/perf/sched/test_scheduler_non_blocking_property.py sentinel-control/services/sentinel-core/tests/perf/workspace/__init__.py sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_benchmark.py sentinel-control/services/sentinel-core/tests/perf/workspace/test_workspace_delta_semantics.py
```

Group 4, safe whole-file subset:

```bash
git add -- sentinel-control/services/sentinel-core/pyproject.toml
git add -- sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

Group 4, mixed files requiring interactive hunk staging:

```bash
git add -p -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git add -p -- sentinel-control/services/sentinel-core/sentinel/mission/runner.py
```

During `git add -p`, stage only the performance-runtime hunks listed above. Use split/edit mode for mixed import and wrapper hunks. Do not accept whole-file staging for either file.

## Safety Checks After Staging

From repository root:

```bash
git diff --cached --stat
git diff --cached --name-only
git status --short
```

From `sentinel-control/services/sentinel-core`:

```bash
python -m pytest tests/perf/ -m "not slow" -q
python -m pytest tests/test_agent_runtime.py -q
```

Required cached diff shape:

```text
Includes Groups 1-3.
Includes pyproject.toml.
Includes shared/events.py only if content review confirms the shared event layer belongs to Phase A-D.
Includes only performance-runtime hunks from runtime.py and runner.py.
Excludes all browser/organ/full-system-audit files listed above.
```

## Final Verdict

```text
NEEDS_MORE_TRIAGE
```

Reason:

- Groups 1-3 are exact and ready for file-specific staging.
- `pyproject.toml` is ready for whole-file staging.
- `sentinel/shared/events.py` is required by Phase A-D but is untracked and needs content review before whole-file staging.
- `runtime.py` and `runner.py` are mixed files. They cannot safely be staged as whole files, and multiple hunks require split/edit staging to avoid pulling full-system-audit and browser-route changes into the Phase A-E baseline.
