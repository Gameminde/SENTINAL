# Implementation Plan: Sentinel Performance Runtime Foundation

## Overview

Convert the feature design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Make sure that each prompt builds on the previous prompts, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.

Implementation language: **Python** (matches the design's concrete pydantic / asyncio / Hypothesis artefacts).

All new code lives under `sentinel-control/services/sentinel-core/sentinel/perf/` as a clean, additive subpackage. Integration into existing modules (`sentinel/agent/runtime.py`, `sentinel/agent/cognitive_cycle.py`, `sentinel/agent/context_builder.py`, `sentinel/agent/context_compressor.py`, `sentinel/agent/decision_frame.py`, `sentinel/agent/token_ledger.py`, `sentinel/agent/prompt_budget.py`, `sentinel/agent/final_gate.py`, `sentinel/mission/runner.py`, `sentinel/organs/receipts.py`, `sentinel/shared/events.py`) is by constructor injection or call-site wrapping. **Existing public behavior is preserved. Constructor changes are additive optional parameters with defaults. No existing required parameter, return type, or call contract is changed.** Adding a new optional keyword argument to an `__init__` is permitted; changing any existing required parameter, return type, or method signature is not. Phase order (A → B → C → D → E → F) is mandatory: measurement lands before any optimization it would measure.

Property-based tests use **Hypothesis** with `max_examples=100` (200 for safety/authority properties) and the tag comment:
`# Feature: sentinel-performance-runtime-foundation, Property {n}: {property_title}`.
Latency SLAs (p95 / p99 targets) are enforced by `BenchmarkHarness` (Phase F), not by property tests.

## Tasks

- [x] 1. Scaffold `sentinel/perf/` package and EventBus event families
  - [x] 1.1 Create `sentinel/perf/` package skeleton
    - Create `sentinel/perf/__init__.py` plus empty `measure/`, `hot_cold/`, `caches/`, `sched/`, `workspace/`, `bench/` subpackages, each with `__init__.py`
    - Record the layering rule (`measure → hot_cold → caches/sched/workspace → bench` fan-in only) in the package docstring
    - _Requirements: foundational for Phases A–F_

  - [x] 1.2 Extend `AgentEventType` in `sentinel/shared/events.py` additively
    - Add members grouped by family: Performance (`PERFORMANCE_TRACE_EMITTED`, `PERFORMANCE_RECEIPT_RECORDED`); Cache (`CACHE_HIT`, `CACHE_MISS`, `CACHE_EVICTED`, `CACHE_CORRECTNESS_VIOLATION`, `CACHE_INVALIDATION_BULK_WARNING`); Cold-Store (`COLD_STORE_PERSISTENCE_FAILED`, `RECEIPT_INDEX_INCONSISTENCY`, `RECEIPT_INDEX_HEALTH_CHECK`); Artifact (`ARTIFACT_INTEGRITY_ERROR`, `ARTIFACT_REJECTED`); Queue/Backpressure (`QUEUE_BACKPRESSURE_APPLIED`, `QUEUE_BACKPRESSURE_CLEARED`); Budget (`BUDGET_WARNING`, `BUDGET_EXCEEDED`, `BUDGET_EXHAUSTED`); Organ-Action (`ORGAN_ACTION_TIMEOUT`, `ORGAN_ACTION_FAILED`, `ORGAN_ACTION_CANCELLED`); Authority/KillSwitch (`AUTHORITY_VIOLATION`, `KILL_SWITCH_BLOCKED`)
    - Preserve additivity: neither rename nor renumber existing members
    - _Requirements: 1.6, 2.5, 3.6, 4.4, 5.7, 5.8, 6.6, 6.7, 6.8, 7.4, 7.5, 7.8, 8.2, 8.4, 8.6, 8.7, 10.3, 10.5, 10.7, 10.8, 12.4, 12.5, 12.7_

- [x] 2. Phase A — Measurement Foundation
  - [x] 2.1 Implement `PerformanceTrace` frozen pydantic model
    - File: `sentinel/perf/measure/performance_trace.py`
    - Eleven non-negative integer fields (`queue_wait_ms`, `wall_ms`, `cpu_ms`, `bytes_in`, `bytes_out`, `tokens_in`, `tokens_out`, `cache_hit`, `cache_miss`, `organ_latency_ms`, `model_prefill_decode_ms`); `error: bool`, `error_category: str | None`, `severity` ∈ {info, warning, critical}; `model_config = ConfigDict(frozen=True)`
    - _Requirements: 1.1, 1.7, 10.9, 12.8_

  - [x]* 2.2 Write property test — PerformanceTrace shape is total and non-negative
    - **Property 1: PerformanceTrace shape is total and non-negative**
    - **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    - Hypothesis `max_examples=200` (safety property); exercises sync `instrument`, async `instrument_async`, and explicit `start`/`stop` emission paths; verifies all 11 numeric fields are non-negative integers, failing actions set `error=True` + `error_category`, critical violations set `severity='critical'` and carry no raw secret substrings

  - [x] 2.3 Implement `PerformanceReceipt` frozen pydantic model
    - File: `sentinel/perf/measure/performance_receipt.py`
    - Embed `PerformanceTrace`; fields `estimated_cost_usd` (Decimal up to 6 fractional digits), `model_id`, `budget_remaining`, `budget_limit`, `cache_type`, `backpressure_reason`, `queue_depth_at_receipt`, `deadline_ms`, `elapsed_ms`, `authority_expansion`, `raw_secret_leakage`, `receipt_hash`, `created_at`
    - `model_validator` reuses canonical `sanitize_context_text` on every string field; rejects `authority_expansion=True`; computes and freezes `receipt_hash`
    - _Requirements: 1.2, 1.3, 8.6, 9.4, 10.9, 12.1, 12.8_

  - [x]* 2.4 Write property test — PerformanceReceipt immutability and aggregate ordering
    - **Property 2: PerformanceReceipt is append-only and immutable**
    - **Validates: Requirements 1.3, 1.4**
    - Hypothesis generator for valid receipts; any field mutation raises and leaves the receipt unchanged; `aggregate_mission` yields `p50 == p95 == p99` when `action_count < 2`, and `p50 <= p95 <= p99` otherwise

  - [x] 2.5 Implement `LatencyProfiler` (sync + async + `aggregate_mission`)
    - File: `sentinel/perf/measure/latency_profiler.py`
    - Sync `instrument(...)` contextmanager; async `instrument_async(...)` contextmanager; explicit `start(...)` / `stop(handle, error=..., error_category=...)`; `aggregate_mission(mission_id)` computes `MissionPerformanceAggregate`
    - Emits `PerformanceTrace` via `PERFORMANCE_TRACE_EMITTED` on the existing `EventBus`; no organ signature changes
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 1.7_

  - [x] 2.6 Implement `CostProfiler.record_model_call`
    - File: `sentinel/perf/measure/cost_profiler.py`
    - Ingests `TokenLedger` results; emits a `PerformanceReceipt` containing `tokens_in`, `tokens_out`, `estimated_cost_usd`, `model_id`
    - _Requirements: 1.2, 10.9_

  - [x]* 2.7 Write unit tests — profiler EventBus wire-up
    - Assert `LatencyProfiler.instrument` emits `PERFORMANCE_TRACE_EMITTED` through `sentinel/shared/events.py` EventBus
    - Assert failure paths emit `severity='critical'` without raw secrets in payload
    - Assert the async surface produces the same trace shape as the sync surface
    - _Requirements: 1.6, 12.8_

  - [x]* 2.8 Write benchmark — LatencyProfiler overhead < 1 ms per instrumented action
    - Benchmark in `sentinel/perf/bench/` harness stubs (populated in Phase F); measure instrumented vs uninstrumented wall-time on a single-action sequential workload
    - _Requirements: 1.5_

  - [x] 2.9 Inject profilers into existing decision core and mission runner
    - `AgentRuntime.__init__` accepts optional `latency_profiler`, `cost_profiler` (defaults preserve current behaviour); `AgentRuntime.run` wraps each phase transition in `instrument(...)`; `AgentRuntime._execute_controlled_tool_calls` wraps each tool call in `instrument_async(...)`
    - `CognitiveCycle.orient`, `ContextBuilder.build`, `ContextCompressor.compress`, `LLMDecisionFrame.build` instrumented at call boundaries (injection, not signature change)
    - `MissionRunner.run_mission` / `MissionRunner.run_gtm_mission` emit mission-start and mission-end `PerformanceTrace`; `_check_revocation` instrumentation is NOT used as the mission lifecycle hook
    - _Requirements: 1.1, 1.6, 1.7_

- [x] 3. Checkpoint — Measurement Foundation
  - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
    - **Files changed**: full list of added / modified files
    - **Tests run**: test command(s) invoked
    - **Pass / fail counts**: total, passed, failed, errors
    - **Skipped tests**: list of skipped tests with reasons
    - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
    - **Production behavior changed**: yes / no, with justification
    - **Authority expansion**: yes / no (must be no; any yes halts the phase)
    - **Raw secret leakage observed**: yes / no (must be no)
    - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
  - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.

- [x] 4. Phase B — Hot/Cold State Foundation
  - [x] 4.1 Implement `HotMissionCache` with `HotMissionView` caps and synchronous eviction
    - File: `sentinel/perf/hot_cold/hot_mission_cache.py`
    - Bounded fields (constraints ≤32, blockers ≤16, organ_states ≤32, `recent_action_summaries` ≤10); references-only (no receipt/artifact payload bytes); `memory_footprint_bytes` estimator calibrated to the per-tier thresholds (<64 KB / <128 KB / <256 KB); `evict_mission` same-tick blocking; overflow replaces oldest summary with receipt id
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 4.7, 4.8_

  - [x] 4.2 Implement `ColdReceiptStore` with WAL-durable staging + retry loop
    - File: `sentinel/perf/hot_cold/cold_receipt_store.py`
    - `persist(receipt) -> ReceiptRef` returns only after WAL write succeeds; on any persistence failure emits `COLD_STORE_PERSISTENCE_FAILED`; retries apply only to entries whose WAL write succeeded and continue until success before discarding the buffered entry; WAL-write failure returns no ref (persisted nor pending)
    - `load(receipt_id) -> BaseReceipt` round-trips canonical-encoded payload byte-for-byte
    - _Requirements: 4.3, 4.4_

  - [x]* 4.3 Write property test — Cold-store durability under injected failures
    - **Property 5: Cold-store durability — no-loss round-trip under failure**
    - **Validates: Requirements 4.3 (durability contract — 10 ms p95 lives in BenchmarkHarness), 4.4**
    - Hypothesis-sampled failure schedule toggling WAL vs downstream persistence failures; every returned `ReceiptRef` is load-recoverable, every failure emits the event, WAL failure returns no ref

  - [x] 4.4 Implement `ReceiptIndex` backed by SQLite, transactional with `ColdReceiptStore`
    - File: `sentinel/perf/hot_cold/receipt_index.py`
    - Schema and indexes (`ix_receipt_mission_ts`, `ix_receipt_organ_action`, `ix_receipt_entity_mission`, `ix_receipt_content`) per design; `query(...)` accepts single-dimension and the four supported indexed compound shapes only; `LIMIT 1000` enforced in SQL; results sorted by `ts_ns DESC`; zero-match returns `[]`; inconsistency exclusion emits `RECEIPT_INDEX_INCONSISTENCY` tagged `query_inconsistency | health_check | index_rebuild`
    - Receipt persistence and index updates are committed in the same transaction
    - **No-fake-atomicity contract**: if the same-transaction coupling between `ColdReceiptStore.persist` and `ReceiptIndex` updates cannot be implemented safely in this task (for example because the WAL stage and the SQLite index do not share a single commit scope), the task must report `NOT LOCKED` in its Phase B checkpoint and explicitly document the missing atomicity. Do not claim transactional coupling that is not actually enforced. The property test in Task 4.5 exists to catch exactly this gap — it must not be relaxed to accommodate a partial implementation.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x]* 4.5 Write property test — ReceiptIndex query semantics and persist+index atomicity
    - **Property 7: ReceiptIndex query semantics and atomicity**
    - **Validates: Requirements 5.1, 5.2, 5.3 (cap — 5 ms p95 benchmark in BenchmarkHarness), 5.4 (indexed compound shapes), 5.5, 5.6, 5.7, 5.8**
    - Hypothesis generators for receipt corpora and query shapes; result list equals in-memory AND-filtered ground truth truncated to 1000 and desc-sorted; atomicity under injected mid-transaction failures

  - [x] 4.6 Implement `ArtifactRefStore` with SHA-256 keying, dedup, integrity, sanitization gate
    - File: `sentinel/perf/hot_cold/artifact_ref_store.py`
    - `put(payload, content_type='binary'|'text', llm_exposable=False)` / `get(content_hash)`; 10 MB cap; size-overflow and storage-exhaustion reject with `ARTIFACT_REJECTED` and NO partial entry; on-disk path `<root>/<sha256[0:2]>/<sha256>`
    - Canonical `sanitize_context_text` applied only when `content_type='text'` AND `llm_exposable=True`; binary payloads never regex-scanned; `get` recomputes SHA-256, raises `ArtifactIntegrityError` + `ARTIFACT_INTEGRITY_ERROR` on mismatch
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 12.4_

  - [x]* 4.7 Write property test — Artifact round-trip, dedup, integrity, and sanitization
    - **Property 8: ArtifactRefStore SHA-256 round-trip, dedup, and integrity**
    - **Validates: Requirements 6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 6.8, 12.4**
    - `max_examples=200` for the sanitizer-rejection axis; Hypothesis strategies for bytes, text with embedded secret patterns, oversize payloads, and corrupted on-disk blobs

  - [x] 4.8 Implement `DeltaStateEngine.apply` with authority-envelope bounds check
    - File: `sentinel/perf/hot_cold/delta_state_engine.py`
    - Rejects deltas that would exceed `MissionAuthorityEnvelope` bounds; prior state preserved; emits `AUTHORITY_VIOLATION`
    - _Requirements: 12.7_

  - [x] 4.9 Implement `CacheInvalidationPolicy` with dependency graph + TTL bounds + bulk warning
    - File: `sentinel/perf/hot_cold/cache_invalidation_policy.py`
    - `register_dependency(parent, child)`; `invalidate(key, cause)` same-tick dependency-graph traversal; TTL upper bounds 300 s / 600 s / 600 s / 600 s; `CACHE_INVALIDATION_BULK_WARNING` iff `cause == INVALIDATION_EVENT` and evicted count > 1000; access to invalidated-but-not-yet-evicted entries returns a miss
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x]* 4.10 Write property test — Hot/cold size bounds and overflow round-trip
    - **Property 6: Hot/cold size bounds and overflow round-trip**
    - **Validates: Requirements 4.1, 4.2, 4.5, 4.7, 4.8**
    - Hypothesis state-machine over action-summary pushes; footprint stays under the tier threshold; overflow replaced by receipt-id refs and recoverable via `ReceiptIndex.query` / `ColdReceiptStore.load`; terminal eviction is same-tick

  - [x]* 4.11 Write benchmark — cold-store persist ≤10 ms p95, receipt-index query ≤5 ms p95 @100k rows, artifact get ≤5 ms p95 @10k artifacts
    - Benchmarks registered in `sentinel/perf/bench/` harness stubs (populated in Phase F)
    - _Requirements: 4.3, 5.3, 6.3_

  - [x] 4.12 Wire `MissionRunner` + `sentinel/organs/receipts.py` through hot/cold layer
    - `MissionRunner` creates `HotMissionView` on mission start; terminal state evicts synchronously via `HotMissionCache.evict_mission`
    - `OrganExecutionReceipt` persisted to `ColdReceiptStore` and indexed by `ReceiptIndex`; `Decision_Core` evidence retrieval goes through `ReceiptIndex.query`, not hot-cache scans
    - _Requirements: 4.6, 4.7, 5.2, 5.5_

- [x] 5. Checkpoint — Hot/Cold State Foundation
  - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
    - **Files changed**: full list of added / modified files
    - **Tests run**: test command(s) invoked
    - **Pass / fail counts**: total, passed, failed, errors
    - **Skipped tests**: list of skipped tests with reasons
    - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
    - **Production behavior changed**: yes / no, with justification
    - **Authority expansion**: yes / no (must be no; any yes halts the phase)
    - **Raw secret leakage observed**: yes / no (must be no)
    - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
  - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.

- [x] 6. Phase C — Context and Prompt Cache Foundation
  - [x] 6.1 Implement `ContextBuildCache` with composite-key lookup + `verify_cache_equivalence`
    - File: `sentinel/perf/caches/context_build_cache.py`
    - `composite_key(mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash)` via canonical `_stable_hash`; `get_or_build(key, builder, verify=False)` returns a defensive deep copy of mutable `AgentContext` (or frozen canonical snapshot); diagnostic mode compares canonical deterministic forms
    - _Requirements: 2.1, 2.4, 2.5, 2.6, 3.1_

  - [x] 6.2 Implement `PromptFrameCache` with `get_or_render` + `reuse_prefix`
    - File: `sentinel/perf/caches/prompt_frame_cache.py`
    - Keyed by `LLMDecisionFrame.frame_hash`; `reuse_prefix(stable_prefix_hash, evidence_delta)` returns rendered prompt string equal to a full rebuild; canonical-form equivalence under `verify=True`
    - _Requirements: 2.2, 2.6, 9.3_

  - [x] 6.3 Implement `LLMDecisionFrameCache` with LRU cap 128, TTL, safety bypass, per-mission stats
    - File: `sentinel/perf/caches/llm_decision_frame_cache.py`
    - `composite_hash(mission_hot_hash, authority_hash, evidence_set_hash, tool_surface_hash)`; `get` returns None on miss / TTL expired / `authority_expansion=True` / `raw_secret_leakage=True` and evicts on safety bypass; `put` rejects `authority_expansion=True` writes; `stats(mission_id)` reports per-event-type ground-truth counters
    - _Requirements: 2.3, 2.6, 9.1, 9.2, 9.4, 9.5, 9.6, 9.7, 12.2, 12.3_

  - [x] 6.4 Implement `TokenBudgetGovernor` (per-frame / per-action / per-mission)
    - File: `sentinel/perf/caches/token_budget_governor.py`
    - `enforce_frame(frame_builder, compressor, frame_budget)` invokes `ContextCompressor.compress` at most 3 times; `enforce_action(action, action_budget)` pre-execution reject with `BUDGET_EXCEEDED`; `enforce_mission(mission_id, mission_budget)` blocks new calls and emits `BUDGET_EXHAUSTED` while in-flight calls finish; crosses 90 % emits `BUDGET_WARNING` exactly once
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

  - [x] 6.5 Implement `ModelCallOptimizer.plan`
    - File: `sentinel/perf/caches/model_call_optimizer.py`
    - Selects runtime/model/backend and prefix-reuse strategy from `LLMDecisionFrame` + `TokenLedger`
    - _Requirements: 9.3, 11.6_

  - [x]* 6.6 Write property test — Cache canonical-form equivalence and runtime fallback
    - **Property 3: Cache canonical-form equivalence and correctness fallback**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
    - Hypothesis composite-key-equivalent pairs; under `verify=True` every divergence evicts, emits `CACHE_CORRECTNESS_VIOLATION` carrying `(cache_type, composite_key, mismatch_description)`, and returns the fresh recomputation without a second recompute

  - [x]* 6.7 Write property test — Cache invalidation dependency closure
    - **Property 4: Cache invalidation dependency closure**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    - Hypothesis FSM over `(create, modify, rename, delete)` workspace events × composite-key component changes; every transitively dependent entry across `ContextBuildCache`, `WorkspaceSnapshotCache`, `PromptFrameCache`, `LLMDecisionFrameCache` is evicted within one tick; TTL expiry evicts regardless of deps; bulk warning fires iff cause is invalidation event and count > 1000

  - [x]* 6.8 Write property test — Decision-frame cache lifecycle and prefix reuse
    - **Property 11: Decision-frame cache lifecycle and prefix reuse**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7**
    - TTL/LRU/authority-change invariants; counters equal ground-truth event counts; `reuse_prefix` output equals a full rebuild

  - [x]* 6.9 Write property test — Token-budget enforcement at frame/action/mission
    - **Property 12: Token-budget enforcement at frame, action, and mission scope**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8**
    - Hypothesis budgets/frames/actions; ≤3 compression passes; crossing 90 % emits `BUDGET_WARNING` exactly at the crossing; cumulative budget exhaustion blocks new calls but not in-flight

  - [x]* 6.10 Write property test — Safety invariants across receipts, caches, and deltas
    - **Property 13: Safety invariants are preserved across receipts, caches, and deltas**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.7**
    - `max_examples=200`; receipt construction rejects raw secrets; `LLMDecisionFrameCache` rejects `authority_expansion=True` writes and evicts served entries with `raw_secret_leakage=True`; `DeltaStateEngine` rejects out-of-envelope transitions and emits `AUTHORITY_VIOLATION`

  - [x] 6.11 Wire caches into the decision core
    - `AgentRuntime` wraps `ContextBuilder.build` with `ContextBuildCache.get_or_build`
    - `LLMDecisionFrame.build` call sites wrap `LLMDecisionFrameCache.get` → fall through → `put`
    - `PromptFrameCache.get_or_render` applied at rendering; `TokenBudgetGovernor.enforce_frame` bound to `PromptBudget` + `ContextCompressor` + `TokenLedger`; `CostProfiler` reads `TokenLedger`
    - _Requirements: 2.1, 2.2, 2.3, 9.1, 9.5, 10.2_

- [x] 7. Checkpoint — Cache Layer
  - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
    - **Files changed**: full list of added / modified files
    - **Tests run**: test command(s) invoked
    - **Pass / fail counts**: total, passed, failed, errors
    - **Skipped tests**: list of skipped tests with reasons
    - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
    - **Production behavior changed**: yes / no, with justification
    - **Authority expansion**: yes / no (must be no; any yes halts the phase)
    - **Raw secret leakage observed**: yes / no (must be no)
    - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
  - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.

- [x] 8. Phase D — Async Organ Scheduling
  - [x] 8.1 Implement `ToolCallQueue` priority queue + metrics
    - File: `sentinel/perf/sched/tool_call_queue.py`
    - Three priority levels (`CRITICAL=0`, `NORMAL=1`, `LOW=2`); `depth`, `estimated_wait_ms`, `per_organ_concurrency` update on every enqueue/dequeue
    - _Requirements: 7.6, 7.7, 8.1, 8.2_

  - [x] 8.2 Implement `BackpressureController` envelope-bounded decisions + sliding-byte-rate
    - File: `sentinel/perf/sched/backpressure_controller.py`
    - `check_submission` never returns bounds exceeding the envelope (Requirement 12.6); `sliding_byte_rate` measured over 1 s window; queue-depth overflow rejects with `(organ_type, queue_depth, estimated_wait_ms)` and emits `QUEUE_BACKPRESSURE_APPLIED`; `QUEUE_BACKPRESSURE_CLEARED` emitted iff backpressure has actually cleared AND queue depth is below the configured bound
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.6_

  - [x] 8.3 Implement `BatchExecutionPlanner.plan` for safe read-only fusion
    - File: `sentinel/perf/sched/batch_execution_planner.py`
    - Fuses file reads, HEAD requests, and metadata fetches into `OrganActionBatch`es
    - _Requirements: scheduling efficiency (implicit)_

  - [x] 8.4 Implement `AsyncOrganScheduler` submit / completion / cancel with authority + kill-switch gates
    - File: `sentinel/perf/sched/async_organ_scheduler.py`
    - `submit(action, authority, kill_switch, dry_run, deadline_ms, priority)`: non-blocking w.r.t. organ execution; rejects with `KILL_SWITCH_BLOCKED` when `kill_switch.triggered` or `execution_allowed=False`; rejects with `AUTHORITY_DENIED` when `execution_authorized=False`; on success emits a success completion event only when the organ actually succeeded; deadline → timeout `PerformanceReceipt` (`organ_id`, `action`, `deadline_ms`, `elapsed_ms`) + slot release; failure → failure `PerformanceReceipt` + failure completion event; `cancel_mission` cancels queued + in-flight and emits a cancellation `PerformanceReceipt` per action
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 12.5_

  - [x]* 8.5 Write property test — Scheduler non-blocking + outcome events + kill-switch/authority
    - **Property 9: Scheduler non-blocking + outcome-event correctness + kill-switch/authority enforcement**
    - **Validates: Requirements 7.1 (non-blocking contract — 1 ms p95 in BenchmarkHarness), 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 12.5**
    - `max_examples=200`; Hypothesis FSM over submissions × outcomes × (kill-switch/authority) states; asserts outcome-event correctness and higher-priority precedence

  - [x]* 8.6 Write property test — Backpressure lifecycle never expands authority
    - **Property 10: Backpressure lifecycle never expands authority**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.6**
    - `max_examples=200`; every `BackpressureDecision` ≤ envelope in all fields; `CLEARED` emitted iff both conditions hold

  - [x]* 8.7 Write benchmark — scheduler submit ≤1 ms p95 and decision-core event responsiveness ≤5 ms with in-flight organ
    - _Requirements: 7.1 (latency), 7.2 (latency)_

  - [x] 8.8 Route `AgentRuntime` organ calls through `AsyncOrganScheduler` + `BackpressureController`
    - Preserve existing `OrganAuthorityEnvelope`, `OrganKillSwitch`, `OrganDryRunReceipt` checks; existing public method signatures unchanged
    - **Default-off contract**: `AsyncOrganScheduler` and `BackpressureController` are engaged only when explicitly injected into `AgentRuntime.__init__` (additive optional parameters per Patch 2). When neither is injected, `AgentRuntime` executes organs via the existing synchronous path with **bit-identical observable behavior**, verified by a regression test that runs a representative mission with and without injection and compares the produced receipt stream.
    - _Risk note_: scheduler migration is a large surface change; gating it behind explicit injection prevents the performance spec from destabilizing the default runtime.
    - _Requirements: 7.1, 12.5, 12.6_

- [x] 9. Checkpoint — Async Organ Scheduling
  - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
    - **Files changed**: full list of added / modified files
    - **Tests run**: test command(s) invoked
    - **Pass / fail counts**: total, passed, failed, errors
    - **Skipped tests**: list of skipped tests with reasons
    - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
    - **Production behavior changed**: yes / no, with justification
    - **Authority expansion**: yes / no (must be no; any yes halts the phase)
    - **Raw secret leakage observed**: yes / no (must be no)
    - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
  - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.

- [x] 10. Phase E — Workspace Delta
  - [x] 10.1 Implement `WorkspaceChangeWatcher` (native fs watcher + poll fallback)
    - File: `sentinel/perf/workspace/workspace_change_watcher.py`
    - Emits `WorkspaceDelta` of type `CREATED | MODIFIED | RENAMED | DELETED`; on rename carries both old and new paths
    - **Phase gate**: This task produces the `WorkspaceDelta` / `WorkspaceChangeWatcher` interface and types only. No subscription to the real filesystem watcher is wired before Phase E completes. No integration with `CacheInvalidationPolicy` or `WorkspaceSnapshotCache.apply_delta` happens here.
    - _Requirements: 3.2_

  - [x] 10.2 Implement `WorkspaceSnapshotCache` incremental `snapshot_id` + `apply_delta`
    - File: `sentinel/perf/workspace/workspace_snapshot_cache.py`
    - `snapshot_id` is hash of sorted `(path, mtime_ns, size, content_sha256)` tuples, changes only on delta apply; `apply_delta` propagates invalidation to `CacheInvalidationPolicy` for both the new path and (on rename) the previous path
    - _Requirements: 3.2, 3.4_

  - [x]* 10.3 Write unit tests — workspace delta semantics
    - CREATED / MODIFIED / RENAMED (old path invalidated) / DELETED; TTL 300 s eviction; event-type correctness
    - _Requirements: 3.2, 3.4_

  - [x]* 10.4 Write benchmark — workspace warm-update p95 ≤ 50 ms
    - _Requirements: performance targets table (workspace snapshot warm-update)_

  - [x] 10.5 Checkpoint — Workspace Delta
    - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
      - **Files changed**: full list of added / modified files
      - **Tests run**: test command(s) invoked
      - **Pass / fail counts**: total, passed, failed, errors
      - **Skipped tests**: list of skipped tests with reasons
      - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
      - **Production behavior changed**: yes / no, with justification
      - **Authority expansion**: yes / no (must be no; any yes halts the phase)
      - **Raw secret leakage observed**: yes / no (must be no)
      - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
    - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.

- [x] 11. Phase F — Benchmark Regression Gates
  - [x] 11.1 Define `GoldenMission` classes and budgets
    - File: `sentinel/perf/bench/golden_missions.py`
    - Classes `startup` / `single_tool` / `multi_tool` / `browser_heavy` with their p50 / p95 / p99 budgets and `min_iterations=30`
    - _Requirements: 11.1, 11.5, 11.6, 11.7_

  - [x] 11.2 Implement `BenchmarkHarness.run`
    - File: `sentinel/perf/bench/harness.py`
    - Blocks until every golden-mission class completes ≥30 iterations; computes p50 / p95 / p99 per class; sets `BenchmarkReport.completed_at` on successful completion; emits a structured pass report `(run_timestamp, iteration_count, p50, p95, p99 per class)` when all gates pass
    - _Requirements: 11.2, 11.9_

  - [x] 11.3 Implement `BenchmarkHarness.evaluate_gates`
    - Same file as 11.2 (append-only); 10 % p95 / 15 % p99 tolerance; on `completed_at is None` waits rather than failing; returns `GateVerdict` with `(metric, class, measured, budget, overage%)` entries
    - _Requirements: 11.3, 11.4_

  - [x]* 11.4 Write property test — Benchmark-gate semantics under completed runs
    - **Property 14: Benchmark-gate semantics under completed runs**
    - **Validates: Requirements 11.2, 11.3, 11.4, 11.9**
    - Hypothesis over synthetic `BenchmarkReport`s (completed + in-progress); verdict fails exactly on the >10 % p95 / >15 % p99 classes, waits on in-progress, passes otherwise

  - [x]* 11.5 Write unit tests — golden-mission enumeration and budget constants
    - Assert each class exists with the documented budgets and `min_iterations ≥ 30`
    - _Requirements: 11.1, 11.5, 11.6, 11.7_

  - [x] 11.6 Implement hot-path module registry + CI gate (Requirement 11.8)
    - File: `sentinel/perf/bench/hot_path_registry.py`
    - Enumerates hot-path modules (invoked during Decision_Core processing, context building, prompt frame assembly, or receipt retrieval); CI check fails the merge when a new hot-path module is added without a benchmark entry in `GOLDEN_MISSION_CLASSES`
    - _Requirements: 11.8_

  - [x] 11.7 Wire `CoreFinalGate` to verify cross-cutting `PerformanceReceipt` invariants only
    - Verify `authority_expansion=False`, `raw_secret_leakage=False`, `receipt_hash` validity before mission close; explicitly do NOT re-run performance budgets (owned by `BenchmarkHarness`)
    - _Requirements: 12.1, 12.2, 12.3_

- [x] 12. Final checkpoint — Full run
  - Produce a **Phase Lock Report** and do not proceed until it is reviewed. The report must include:
    - **Files changed**: full list of added / modified files
    - **Tests run**: test command(s) invoked
    - **Pass / fail counts**: total, passed, failed, errors
    - **Skipped tests**: list of skipped tests with reasons
    - **Benchmark results**: p50 / p95 / p99 for any `*` benchmark tasks in this phase (or "N/A — no benchmarks in this phase")
    - **Production behavior changed**: yes / no, with justification
    - **Authority expansion**: yes / no (must be no; any yes halts the phase)
    - **Raw secret leakage observed**: yes / no (must be no)
    - **Phase verdict**: `LOCKED` or `NOT LOCKED` with a one-line reason
  - A phase is **LOCKED** only when all non-optional tasks pass AND every associated `*` validation task has either passed or has a documented deferral approved by the user. Otherwise the verdict is `NOT LOCKED` and the next phase does not start.
  - The feature is release-ready only when every phase's verdict is LOCKED.

## Notes

- Tasks marked with `*` are validation tasks. They are **NOT optional for phase lock**. They may be skipped only for local draft spikes, but no phase may be accepted or locked without its associated tests and benchmarks. Skipping a `*` task means the phase it belongs to cannot be declared LOCKED at the phase checkpoint.
- Each task references the specific acceptance-criterion clauses it covers for traceability.
- Every correctness property from the design document is realised as exactly one property-based test sub-task, tagged with its property number and the requirement clauses it validates.
- Checkpoints after each phase exist to validate the phase boundary before the next phase imports from it.
- Integration into existing modules is additive (constructor injection or call-site wrapping). No existing **required** public signature or behavior is changed; new optional keyword parameters with defaults are permitted.
- Phase ordering is load-bearing: measurement before caching before scheduling before benchmark gates. Do not reorder.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "2.6"] },
    { "id": 4, "tasks": ["2.7", "2.8"] },
    { "id": 5, "tasks": ["2.9"] },
    { "id": 6, "tasks": ["4.1", "4.2", "4.4", "4.6", "4.8", "4.9"] },
    { "id": 7, "tasks": ["4.3", "4.5", "4.7", "4.10", "4.11"] },
    { "id": 8, "tasks": ["4.12"] },
    { "id": 9, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5"] },
    { "id": 10, "tasks": ["6.6", "6.7", "6.8", "6.9", "6.10"] },
    { "id": 11, "tasks": ["6.11"] },
    { "id": 12, "tasks": ["8.1", "8.2", "8.3"] },
    { "id": 13, "tasks": ["8.4"] },
    { "id": 14, "tasks": ["8.5", "8.6", "8.7"] },
    { "id": 15, "tasks": ["8.8"] },
    { "id": 16, "tasks": ["10.1", "10.2"] },
    { "id": 17, "tasks": ["10.3", "10.4"] },
    { "id": 18, "tasks": ["11.1", "11.6"] },
    { "id": 19, "tasks": ["11.2"] },
    { "id": 20, "tasks": ["11.3", "11.5"] },
    { "id": 21, "tasks": ["11.4", "11.7"] }
  ]
}
```
