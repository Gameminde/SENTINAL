# Requirements Document

## Introduction

This specification establishes the performance and runtime foundation for Sentinel before any new organs are built. The system must transition from a context-rebuilding orchestrator into a local incremental runtime that operates on references (not blobs), deltas (not rescans), hot state (not cold rebuilds), async organs (not blocking tools), cached decision frames (not rebuilt prompts), and measured latency (not guessed optimization). The first implementation step is measurement, not optimization.

## Explicit Non-Goals

The following are explicitly out of scope for this specification:

- No new external organ creation
- No P6U API implementation
- No LangChain or LangGraph integration or harvest
- No Rust rewrite (measurement comes before language-level optimization)
- No low-level kernel implementation before measurement proves the need
- No browser runtime receipt adoption implementation
- No new real-world powers
- No authority expansion beyond current mission authority boundaries

## Glossary

- **LatencyProfiler**: Module that instruments wall time, CPU time, queue wait, bytes read/written, round trips, and token costs for every action in the system.
- **CostProfiler**: Module that tracks token consumption, dollar cost, and resource utilization per action, organ call, and mission.
- **PerformanceReceipt**: Machine-readable receipt emitted per action that records timing, cost, cache behavior, and correctness metadata.
- **DeltaStateEngine**: Module that applies only validated changes since the last known state, replacing full-world rescans with incremental updates.
- **HotMissionCache**: Compact in-memory mutable state for active missions: objectives, constraints, blockers, organ states, last useful results.
- **ColdReceiptStore**: Append-only durable journal of tool calls, decisions, validations, traces, and mutations stored outside the hot path.
- **ReceiptIndex**: Secondary index over ColdReceiptStore enabling fast retrieval by mission_id, organ, timestamp, action_type, entity path, and content hash.
- **ArtifactRefStore**: Content-addressed store for files, patches, DOM summaries, API response summaries, and other large artifacts, keyed by SHA-256 hash.
- **ContextBuildCache**: Cache of evidence selections already assembled for a composite key of (mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash).
- **PromptFrameCache**: Cache of fully-rendered prompt text for a given model when only small zones have changed since the last frame.
- **LLMDecisionFrameCache**: Cache of the final compact decision frame keyed by semantic hash of its dependencies.
- **TokenBudgetGovernor**: Module that enforces hard token limits per frame, per action, and per mission, rejecting or compressing frames that exceed budget.
- **ModelCallOptimizer**: Module that selects runtime, model, and backend and decides when to reuse a prefix, chunk, or switch device.
- **AsyncOrganScheduler**: Event-loop-based submission and completion scheduler for slow organs, decoupled from the decision core.
- **ToolCallQueue**: Central observable queue with priority, deadline, estimated cost, and cancellation support for all organ work.
- **BatchExecutionPlanner**: Module that fuses safe read-only operations (file reads, HEAD requests, metadata fetches) into batched executions.
- **BackpressureController**: Module that enforces concurrency limits, token budgets, byte budgets, timeouts, and bounded queue depths.
- **WorkspaceChangeWatcher**: Native filesystem watcher (with fallback scan) that produces delta events instead of full-tree rescans.
- **WorkspaceSnapshotCache**: Incremental view of workspace state maintained via deltas rather than full file-tree dumps.
- **CacheInvalidationPolicy**: Explicit per-asset-type invalidation rules that detect and evict stale cached entries.
- **Decision_Core**: The reasoning and planning subsystem of Sentinel (CognitiveCycle, DecisionFrame, ContextBuilder) that must never be blocked by organ I/O.
- **MissionRunner**: Existing module (sentinel/mission/runner.py) that orchestrates mission lifecycle.
- **EventBus**: Existing module (sentinel/agent/event_bus.py) that distributes typed events across the agent.
- **Performance_Trace**: Structured record containing queue_wait_ms, wall_ms, cpu_ms, bytes_in, bytes_out, tokens_in, tokens_out, cache_hit, cache_miss, organ_latency_ms, and model_prefill_decode_ms fields.

## Requirements

### Requirement 1: Performance Measurement Foundation

**User Story:** As a Sentinel developer, I want every action, tool call, and model invocation to produce structured timing and cost data, so that I can identify bottlenecks with evidence rather than guessing.

#### Acceptance Criteria

1. WHEN an action completes successfully, THE LatencyProfiler SHALL emit a Performance_Trace containing queue_wait_ms, wall_ms, cpu_ms, bytes_in, bytes_out, tokens_in, tokens_out, cache_hit, cache_miss, organ_latency_ms, and model_prefill_decode_ms fields, where each numeric field is a non-negative integer and fields not applicable to the action type are recorded as 0.
2. WHEN a model call completes, THE CostProfiler SHALL record tokens_in, tokens_out, estimated_cost_usd (as a decimal with up to 6 fractional digits), and model_id in the PerformanceReceipt for that action.
3. THE PerformanceReceipt SHALL be append-only and immutable after creation; IF any code attempts to modify a field on an existing PerformanceReceipt, THEN THE system SHALL raise an error and leave the receipt unchanged.
4. WHEN a mission completes, THE LatencyProfiler SHALL produce an aggregate summary with p50, p95, and p99 latencies (in milliseconds) across all actions in that mission; IF the mission contains fewer than 2 actions, THEN THE aggregate summary SHALL report identical values for p50, p95, and p99.
5. THE LatencyProfiler SHALL add less than 1 ms of wall-clock overhead per instrumented action, measured as the difference between instrumented and uninstrumented execution of the same action under single-action sequential load.
6. WHEN the LatencyProfiler instruments an action, THE LatencyProfiler SHALL attach the Performance_Trace to the existing EventBus event stream without requiring changes to organ call signatures.
7. IF an action fails due to an exception or timeout before completion, THEN THE LatencyProfiler SHALL still emit a Performance_Trace with all timing fields populated up to the point of failure and a boolean error field set to true.

### Requirement 2: Cache Correctness

**User Story:** As a Sentinel developer, I want cached computation results to be provably equivalent to fresh computation, so that caching never introduces silent correctness regressions.

#### Acceptance Criteria

1. WHEN the ContextBuildCache returns a cached evidence selection, THE ContextBuildCache SHALL produce output byte-identical to a fresh computation given the same composite key (mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash); WHILE verify_cache_equivalence diagnostic mode is active, THE ContextBuildCache SHALL enforce this invariant by recomputing the fresh result and comparing, and WHILE diagnostic mode is inactive, THE ContextBuildCache SHALL trust the cached result without per-read byte-identity verification.
2. WHEN the PromptFrameCache returns a cached frame, THE PromptFrameCache SHALL produce a frame whose frame_hash matches the hash that a fresh build would produce.
3. WHEN the LLMDecisionFrameCache returns a cached decision frame, THE LLMDecisionFrameCache SHALL produce a frame that passes DecisionFrameVerifier verification identically to a freshly-built frame.
4. WHEN verify_cache_equivalence diagnostic mode is activated, THE system SHALL compute fresh results for all cached entries and compare them against cached results, reporting each entry as equivalent or divergent (round-trip property).
5. IF verify_cache_equivalence detects a divergence between a cached result and its fresh recomputation, THEN THE system SHALL evict the divergent cache entry, emit a cache_correctness_violation event to the EventBus containing the cache type, composite key, and mismatch description, and return the fresh result produced by the diagnostic recomputation without requiring a second recomputation.
6. IF any cache (ContextBuildCache, PromptFrameCache, or LLMDecisionFrameCache) serves a result at runtime that fails its correctness check (byte-identity, frame_hash match, or DecisionFrameVerifier verification respectively), THEN THE system SHALL discard the cached result, evict the entry, and fall back to fresh computation before proceeding.

### Requirement 3: Cache Invalidation Correctness

**User Story:** As a Sentinel developer, I want stale caches to be detected and evicted promptly, so that the system never acts on outdated state.

#### Acceptance Criteria

1. WHEN any component of a ContextBuildCache composite key (mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash) changes, THE CacheInvalidationPolicy SHALL evict all entries dependent on that key within the same event-loop tick, including downstream PromptFrameCache and LLMDecisionFrameCache entries whose inputs depend on the evicted entry.
2. WHEN a workspace file is created, content-modified, renamed, or deleted, THE CacheInvalidationPolicy SHALL invalidate all ContextBuildCache and WorkspaceSnapshotCache entries that reference that file path or its previous path in the case of a rename.
3. WHEN mission authority constraints change (authority_hash differs from the value recorded in cached entries), THE CacheInvalidationPolicy SHALL invalidate all PromptFrameCache and LLMDecisionFrameCache entries for that mission.
4. THE CacheInvalidationPolicy SHALL use dependency-graph-based invalidation as the primary mechanism for all asset types, with a maximum TTL upper bound of 300 seconds for workspace snapshots, 600 seconds for evidence selections, 600 seconds for prompt frames, and 600 seconds for decision frames, after which entries are evicted regardless of dependency state.
5. IF a cache entry is accessed after its invalidation condition is met but before eviction completes, THEN THE CacheInvalidationPolicy SHALL return a cache miss rather than stale data.
6. WHEN an invalidation event triggers eviction of dependent entries, THE CacheInvalidationPolicy SHALL complete the full dependency-graph traversal and eviction within a single event-loop tick, and SHALL log a warning to the EventBus if the number of evicted entries exceeds 1000 in a single invalidation pass; THE warning SHALL be emitted only for evictions triggered by invalidation events, and SHALL NOT be emitted for evictions caused by TTL expiration or other non-invalidation causes.

### Requirement 4: Hot/Cold State Separation

**User Story:** As a Sentinel developer, I want mutable mission state kept compact and in-memory while receipts and artifacts are stored cold by reference, so that the decision core operates on minimal working sets.

#### Acceptance Criteria

1. THE HotMissionCache SHALL store only active objectives, current constraints, active blockers, organ states, and up to 10 last-action summaries in memory per active mission.
2. THE HotMissionCache SHALL reference receipts and artifacts by ID only, storing zero receipt or artifact payloads in the hot path.
3. WHEN a receipt is created, THE ColdReceiptStore SHALL persist the receipt to durable append-only storage and return only the receipt ID to the hot path within 10ms.
4. IF the ColdReceiptStore fails to persist a receipt, THEN THE ColdReceiptStore SHALL retain the receipt in a durable write-ahead buffer, emit a persistence-failure event to the EventBus, and retry until persistence succeeds before discarding the buffered receipt.
5. THE HotMissionCache SHALL maintain a memory footprint below 64 KB per active mission for missions with fewer than 100 completed actions, below 128 KB per active mission for missions with up to 1,000 completed actions, and below 256 KB per active mission for missions with more than 1,000 completed actions.
6. WHEN the Decision_Core requires evidence from a past action, THE Decision_Core SHALL retrieve evidence via ReceiptIndex lookup by reference, not by scanning the hot cache.
7. WHEN a mission reaches a terminal state (completed, failed, or cancelled), THE HotMissionCache SHALL evict all entries for that mission synchronously within the same event-loop tick, blocking other HotMissionCache operations until the eviction completes.
8. WHEN a mission is active, THE HotMissionCache SHALL evict action summaries beyond the 10 most recent, replacing them with their receipt IDs in the cold store.

### Requirement 5: Receipt Indexing

**User Story:** As a Sentinel developer, I want receipts retrievable in milliseconds by mission, organ, timestamp, path, or hash, so that evidence retrieval never becomes a bottleneck.

#### Acceptance Criteria

1. THE ReceiptIndex SHALL support queries by mission_id, organ_id, timestamp range, action_type, entity_path, and content_hash, returning an ordered list of matching receipt IDs sorted by timestamp descending.
2. WHEN a receipt is persisted to ColdReceiptStore, THE ReceiptIndex SHALL update its indexes within the same write transaction such that either both the receipt and all index entries are committed, or neither is committed.
3. WHEN a query is issued against the ReceiptIndex, THE ReceiptIndex SHALL return results within 5ms for indexes containing up to 100,000 receipts, with a maximum result set of 1,000 receipt IDs per query.
4. THE ReceiptIndex SHALL support compound queries combining at least two index dimensions (mission_id + timestamp range, organ_id + action_type, entity_path + mission_id) using logical AND semantics, and compound queries SHALL return results within the same 5ms latency bound defined in criterion 3 without exemption for index intersection complexity.
5. THE ReceiptIndex SHALL maintain index consistency with ColdReceiptStore such that every persisted receipt is queryable and no index entry references a missing receipt.
6. IF a query matches zero receipts, THEN THE ReceiptIndex SHALL return an empty list within the same latency bound as a non-empty result.
7. IF the ReceiptIndex detects an inconsistency between an index entry and ColdReceiptStore during a query, THEN THE ReceiptIndex SHALL exclude the inconsistent entry from results and emit a diagnostic event to the EventBus.
8. THE ReceiptIndex MAY emit diagnostic events to the EventBus for broader index-health scenarios beyond query-time inconsistencies, including scheduled preventive health checks and index rebuild operations, with each diagnostic event tagged with its source scenario (query_inconsistency, health_check, or index_rebuild).

### Requirement 6: Artifact Reference Store

**User Story:** As a Sentinel developer, I want large artifacts stored once by content hash and referenced everywhere by ID, so that no blob is duplicated in memory or storage.

#### Acceptance Criteria

1. THE ArtifactRefStore SHALL store artifacts keyed by their SHA-256 content hash, accepting artifacts up to 10 MB in size.
2. WHEN an artifact with an existing hash is submitted, THE ArtifactRefStore SHALL return the existing content hash reference without writing duplicate data.
3. THE ArtifactRefStore SHALL support retrieval by content hash in under 5 ms for stores containing up to 10,000 artifacts.
4. WHEN an artifact is referenced in a receipt or decision frame, THE system SHALL use the content hash reference only, never embedding the artifact payload inline.
5. THE ArtifactRefStore SHALL verify content integrity on read by recomputing the SHA-256 hash and comparing it to the stored key.
6. IF the recomputed hash does not match the stored key on read, THEN THE ArtifactRefStore SHALL reject the read, return an integrity error indicating hash mismatch, and leave the corrupted entry unmodified.
7. IF a submitted artifact exceeds 10 MB, THEN THE ArtifactRefStore SHALL reject the submission and return an error indicating the size limit was exceeded.
8. IF the ArtifactRefStore is unable to persist an artifact due to resource exhaustion, THEN THE ArtifactRefStore SHALL reject the submission explicitly by both returning an error indicating storage unavailability AND preventing any further processing of the submission, and SHALL NOT create a partial or corrupt entry.

### Requirement 7: Async Organ Scheduling

**User Story:** As a Sentinel developer, I want slow organs (browser, network, filesystem) to execute asynchronously without blocking the decision core, so that reasoning continues while I/O completes.

#### Acceptance Criteria

1. WHEN an organ action is submitted, THE AsyncOrganScheduler SHALL enqueue the action and return control to the Decision_Core within 1ms.
2. WHILE an organ action is executing, THE Decision_Core SHALL remain able to process new EventBus events within 5ms and to cancel any pending organ action without waiting for the executing action to complete.
3. WHEN an organ action completes successfully, THE AsyncOrganScheduler SHALL deliver the result to the Decision_Core via the EventBus as a completion event within 2ms of the organ returning its output; THE AsyncOrganScheduler SHALL NOT deliver a success completion event for an organ action that did not actually complete successfully (timeouts, failures, and cancellations SHALL be delivered via the paths defined in criteria 4, 5, and 8 instead).
4. WHEN an organ action exceeds the deadline specified at submission time, THE AsyncOrganScheduler SHALL cancel the action, release its queue slot, and emit a timeout PerformanceReceipt containing the organ_id, action, deadline_ms, and elapsed_ms fields.
5. IF an organ action fails with an error before its deadline, THEN THE AsyncOrganScheduler SHALL emit a failure PerformanceReceipt containing the organ_id, action, and error category, and SHALL deliver a failure completion event to the Decision_Core via the EventBus.
6. THE AsyncOrganScheduler SHALL support at least 3 discrete priority levels (critical, normal, low) such that actions at a higher priority level execute before actions at a lower priority level in the same queue.
7. THE ToolCallQueue SHALL expose current queue depth, estimated wait time, and per-organ concurrency counts as metrics queryable via programmatic API, updated on every enqueue and dequeue operation.
8. WHEN a mission is aborted, THE AsyncOrganScheduler SHALL cancel all queued and in-flight organ actions for that mission and emit a cancellation PerformanceReceipt for each cancelled action.

### Requirement 8: Backpressure Control

**User Story:** As a Sentinel developer, I want concurrency limits, token budgets, and queue bounds enforced at the scheduling layer, so that the system degrades gracefully under load rather than thrashing.

#### Acceptance Criteria

1. THE BackpressureController SHALL enforce a configurable maximum concurrency limit per organ type such that submissions exceeding the limit are held in the ToolCallQueue until a slot becomes available.
2. WHEN the ToolCallQueue depth exceeds a configurable bound, THE BackpressureController SHALL reject new submissions and return a backpressure signal containing the organ type, current queue depth, and estimated wait time to the caller.
3. THE BackpressureController SHALL enforce a configurable token budget per mission such that total tokens consumed across all actions do not exceed the budget.
4. WHEN a token budget is exhausted, THE BackpressureController SHALL reject new model calls for that mission, emit a budget-exhausted event to the EventBus, and allow in-flight model calls to complete without cancellation.
5. THE BackpressureController SHALL enforce per-organ byte-rate limits measured over a 1-second sliding window to prevent a single organ from consuming more than its configured byte-rate allocation.
6. WHEN backpressure is applied, THE BackpressureController SHALL record the backpressure event in a PerformanceReceipt with reason, queue_depth, and budget_remaining fields.
7. WHEN the ToolCallQueue depth drops below the configured bound after a backpressure rejection, THE BackpressureController SHALL resume accepting new submissions and emit a backpressure-cleared event to the EventBus; THE backpressure-cleared event SHALL be emitted only when both the queue depth is actually below the configured bound AND backpressure has been cleared, and SHALL NOT be emitted based on determination alone without the queue depth condition being satisfied.

### Requirement 9: Decision-Frame Caching

**User Story:** As a Sentinel developer, I want stable prompt prefixes and decision frames reused across consecutive actions, so that redundant LLM prefill computation is eliminated.

#### Acceptance Criteria

1. WHEN a decision frame is built and its composite hash matches a cached entry that has not exceeded its time-to-live, THE LLMDecisionFrameCache SHALL return the cached frame without recomputation.
2. THE LLMDecisionFrameCache SHALL key entries by a composite hash of (mission_hot_hash, authority_hash, evidence_set_hash, tool_surface_hash) and SHALL store at most 128 entries per mission, evicting the least-recently-used entry when the limit is reached.
3. WHEN only the evidence delta changes between consecutive frames while mission_hot_hash, authority_hash, and tool_surface_hash remain identical, THE PromptFrameCache SHALL reuse the stable prefix and append only the changed evidence sections.
4. THE LLMDecisionFrameCache SHALL track cache hit count, miss count, and eviction count per mission and report them in the mission-level PerformanceReceipt aggregate; THE hit count SHALL be incremented only on actual cache hits, THE miss count SHALL be incremented only on actual cache misses, and THE eviction count SHALL be incremented only on actual eviction events, with no counter incremented on operation outcomes that do not match its corresponding event type.
5. WHEN a cached decision frame is reused, THE LLMDecisionFrameCache SHALL skip the full ContextBuilder pipeline and proceed directly to model invocation.
6. IF the composite hash does not match any cached entry, THEN THE LLMDecisionFrameCache SHALL fall through to the ContextBuilder pipeline to build the frame from scratch and store the result in the cache.
7. IF a cached entry's time-to-live has expired or the underlying authority_hash changes, THEN THE LLMDecisionFrameCache SHALL invalidate the stale entry and trigger a full frame rebuild via the ContextBuilder pipeline.

### Requirement 10: Token Budget Enforcement

**User Story:** As a Sentinel developer, I want hard token limits enforced per frame, per action, and per mission, so that context windows are never exceeded and costs remain predictable.

#### Acceptance Criteria

1. THE TokenBudgetGovernor SHALL enforce a configurable maximum token count per decision frame, with the configured value constrained to be greater than 0 and no greater than the model's context_window_tokens.
2. WHEN a built decision frame exceeds the per-frame token budget, THE TokenBudgetGovernor SHALL trigger evidence compression until the frame fits within budget.
3. IF evidence compression cannot reduce the decision frame to within the per-frame token budget after a maximum of 3 compression passes, THEN THE TokenBudgetGovernor SHALL reject the frame and emit a budget-exceeded event to the EventBus indicating the frame could not be compressed.
4. THE TokenBudgetGovernor SHALL enforce a configurable maximum token count per individual action (input + output), with the configured value constrained to be greater than 0.
5. IF an individual action's token count (input + output) exceeds the per-action budget, THEN THE TokenBudgetGovernor SHALL reject the action before execution and emit a budget-exceeded event to the EventBus.
6. THE TokenBudgetGovernor SHALL enforce a configurable maximum cumulative token count per mission, with the configured value constrained to be greater than 0.
7. WHEN a mission's cumulative token consumption reaches or exceeds its per-mission token budget, THE TokenBudgetGovernor SHALL block new model calls for that mission and emit a budget-exhausted event to the EventBus.
8. WHEN a mission approaches 90% of its token budget, THE TokenBudgetGovernor SHALL emit a budget-warning event to the EventBus.
9. THE TokenBudgetGovernor SHALL record actual vs. budgeted token counts (tokens_in, tokens_out, budget_remaining, budget_limit) in every PerformanceReceipt.

### Requirement 11: Benchmark Regression Gates

**User Story:** As a Sentinel developer, I want p50/p95/p99 latencies tracked against budgets with automated gates, so that future changes cannot silently regress performance.

#### Acceptance Criteria

1. THE performance benchmark harness SHALL define golden mission classes (startup, single-tool, multi-tool, browser-heavy) with target latency budgets for p50, p95, and p99 percentiles for each class.
2. WHEN a benchmark run completes, THE harness SHALL compute p50, p95, and p99 latencies for each golden mission class from a minimum of 30 iterations per class.
3. WHEN a p95 latency exceeds its budget by more than 10% AND the benchmark run has completed, THE benchmark gate SHALL fail and report the regression including the metric name, golden mission class, measured value, budget value, and percentage overage; IF a benchmark run has not yet completed, THEN THE benchmark gate SHALL wait for completion rather than failing on in-progress measurements.
4. WHEN a p99 latency exceeds its budget by more than 15% AND the benchmark run has completed successfully, THE benchmark gate SHALL fail and report the regression including the metric name, golden mission class, measured value, budget value, and percentage overage; IF a benchmark run has not completed successfully, THEN THE benchmark gate SHALL wait for successful completion rather than failing on in-progress or incomplete measurements.
5. THE benchmark harness SHALL track mission startup latency with a budget of 400ms (p95) and an ideal target of 150ms (p50).
6. THE benchmark harness SHALL track decision-frame build latency with a budget of 100ms (p95) and an ideal target of 30ms (p50) for hot-cache scenarios.
7. THE benchmark harness SHALL track receipt retrieval latency with a budget of 10ms (p95) and an ideal target of 5ms (p50).
8. WHEN a new module is added to the hot path (any module invoked during Decision_Core processing, context building, prompt frame assembly, or receipt retrieval), THE benchmark harness SHALL require a benchmark entry for that module before the change is merged.
9. WHEN a benchmark run completes with all gates passing, THE harness SHALL emit a structured pass report containing the run timestamp, iteration count, and measured p50/p95/p99 values for each golden mission class.

### Requirement 12: Safety Invariants

**User Story:** As a Sentinel developer, I want the performance foundation to preserve all existing safety guarantees, so that optimization never compromises authority boundaries, secret protection, or data integrity.

#### Acceptance Criteria

1. THE PerformanceReceipt SHALL contain zero raw secrets, credentials, tokens, or API keys in any field, verified by applying the same sanitize_context_text check used by LLMDecisionFrame.build before persisting.
2. THE LLMDecisionFrameCache SHALL preserve the existing authority_expansion=False invariant on all cached frames and SHALL reject any cache write where authority_expansion=True.
3. WHEN a cached decision frame is returned, THE LLMDecisionFrameCache SHALL verify that raw_secret_leakage=False before serving the cached entry, and IF raw_secret_leakage=True is detected, THEN THE LLMDecisionFrameCache SHALL evict the entry and return a cache miss.
4. THE ArtifactRefStore SHALL refuse to store artifacts that contain detected secret patterns (strings matching known API key prefixes, bearer/token header patterns, PEM private key markers, or high-entropy strings flagged by the sanitize_context_text scanner) and SHALL return a rejection indicating the artifact requires sanitization before storage.
5. THE AsyncOrganScheduler SHALL enforce the existing OrganAuthorityEnvelope and OrganKillSwitch checks before submitting any organ action to execution, and IF the OrganKillSwitch is triggered or execution_allowed=False, THEN THE AsyncOrganScheduler SHALL reject the submission and emit a kill-switch-blocked event.
6. THE BackpressureController SHALL not expand mission authority boundaries when applying backpressure, meaning it SHALL NOT increase token budgets, byte budgets, concurrency limits, or permission scopes beyond the values defined in the MissionAuthorityEnvelope.
7. IF a state transition would set any authority field to a value exceeding the mission's original MissionAuthorityEnvelope bounds established at mission creation, THEN THE DeltaStateEngine SHALL reject the transition, preserve the prior state unchanged, and emit an authority-violation event to the EventBus.
8. WHEN any safety invariant check in criteria 1-7 detects a violation, THE violating component SHALL log the violation type and component name as a Performance_Trace event with severity=critical, without exposing the secret content in the log payload.

## Performance Targets

| Metric | Ideal (p50) | Acceptable (p95) | Budget Gate (p95 fail) |
|--------|-------------|-------------------|------------------------|
| Mission startup latency | 150ms | 400ms | >440ms |
| Decision-frame build (hot) | 30ms | 100ms | >110ms |
| Decision-frame build (warm) | 50ms | 150ms | >165ms |
| Workspace snapshot warm-update | 20ms | 50ms | >55ms |
| Receipt retrieval | 5ms | 10ms | >11ms |
| Tool routing latency | 10ms | 25ms | >27ms |
| Tokens per action (median) | 1,500 | 3,000 | >3,300 |
| Over-budget frame rate | <1% | <3% | >3.3% |

## Phase Structure

### Phase A — Measurement Foundation
Modules: LatencyProfiler, CostProfiler, PerformanceReceipt, Performance_Trace schema.
Covers: Requirements 1, 11 (harness definition), 12 (safety in receipts).

### Phase B — Delta and Hot/Cold State Foundation
Modules: DeltaStateEngine, HotMissionCache, ColdReceiptStore, ReceiptIndex, ArtifactRefStore, CacheInvalidationPolicy.
Covers: Requirements 3, 4, 5, 6, 12 (delta safety).

### Phase C — Context and Prompt Cache Foundation
Modules: ContextBuildCache, PromptFrameCache, LLMDecisionFrameCache, TokenBudgetGovernor, ModelCallOptimizer.
Covers: Requirements 2, 9, 10, 12 (frame safety).

### Phase D — Async Organ Scheduling Foundation
Modules: AsyncOrganScheduler, ToolCallQueue, BatchExecutionPlanner, BackpressureController.
Covers: Requirements 7, 8, 12 (authority in scheduling).

### Phase E — Workspace Delta Performance Plan
Modules: WorkspaceChangeWatcher, WorkspaceSnapshotCache, file cards, rollback metadata, atomic write pattern.
Covers: Requirements 3 (workspace invalidation), 4 (hot/cold for workspace).

### Phase F — Benchmark and Regression Gates
Modules: Performance benchmark harness, golden mission classes, p50/p95/p99 tracking, perf budget gates.
Covers: Requirement 11.

## Integration with Existing Modules

| Existing Module | Integration Point |
|----------------|-------------------|
| MissionRunner (sentinel/mission/runner.py) | Emits Performance_Trace on mission start/end; uses HotMissionCache for state |
| AgentRuntime (sentinel/agent/runtime.py) | Hosts AsyncOrganScheduler; routes through ToolCallQueue |
| DecisionFrame (sentinel/agent/decision_frame.py) | Cached by LLMDecisionFrameCache; governed by TokenBudgetGovernor |
| Receipts (sentinel/organs/receipts.py) | Persisted to ColdReceiptStore; indexed by ReceiptIndex |
| EventBus (sentinel/agent/event_bus.py) | Carries Performance_Trace events, backpressure signals, budget warnings |
| FinalGate (sentinel/agent/final_gate.py) | Validates PerformanceReceipt safety invariants before mission close |
| CognitiveCycle (sentinel/agent/cognitive_cycle.py) | Reads from HotMissionCache; never blocked by organ I/O |
| ContextBuilder (sentinel/agent/context_builder.py) | Results cached by ContextBuildCache; skipped on cache hit |
| ContextCompressor (sentinel/agent/context_compressor.py) | Triggered by TokenBudgetGovernor when frame exceeds budget |
| TokenLedger (sentinel/agent/token_ledger.py) | Feeds data to TokenBudgetGovernor and CostProfiler |
| PromptBudget (sentinel/agent/prompt_budget.py) | Enforced by TokenBudgetGovernor at frame build time |
| Organs (sentinel/organs/) | Scheduled via AsyncOrganScheduler; subject to BackpressureController limits |
