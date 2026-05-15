# Phase C — Final Lock Report (Amended)

**Verdict:** Phase C = **STRUCTURAL LOCK / PARTIAL RUNTIME ADOPTION**.
**Phase D:** allowed to start under the same mini-review discipline, **with the explicit caveat** that the Phase C runtime adoption is not full. Backlog items P-C-RUNTIME-01 and P-C-KEY-01 remain open and must be closed before Phase C can be re-graded as full LOCKED.

The previous "Phase C = LOCKED" verdict was wrong on its own terms. The 6.11 mini-review noted that three of the four cache injections (`LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor`) have helper methods on `AgentRuntime` but no real call sites, and that the `ContextBuildCache` composite key uses `envelope.id` as a stand-in for the real four-component key. That admission is incompatible with the LOCKED claim that Phase C — the **Context and Prompt Cache Foundation** — is fully wired into the decision core.

This amended report records the partial state honestly, not under a "structural multiplier" or any soft-claim wording.

## Status by sub-task

| Task | Status | Notes |
|------|--------|-------|
| 6.1 ContextBuildCache | ACCEPTABLE | LRU + canonical-form equivalence + verify-mode + payload-whitelisted events |
| 6.2 PromptFrameCache | ACCEPTABLE | Frame-table + prefix-table LRU; `get_or_render` + `reuse_prefix` |
| 6.3 LLMDecisionFrameCache | ACCEPTABLE | Per-mission LRU 128 + TTL 600s + safety re-check + per-event-type counters |
| 6.4 TokenBudgetGovernor | ACCEPTABLE | Per-frame ≤3 passes / per-action / per-mission single-fire warning + exhaustion |
| 6.5 ModelCallOptimizer | ACCEPTABLE | Deterministic structural planner |
| 6.6 Cache canonical-form equivalence (Property 3) | ACCEPTABLE | 6/6 passed |
| 6.7 Cache invalidation dependency closure (Property 4) | ACCEPTABLE | 7/7 passed (synthetic WorkspaceDelta per patched task graph) |
| 6.8 Decision-frame cache lifecycle (Property 11) | ACCEPTABLE | 11/11 passed |
| 6.9 Token-budget enforcement (Property 12) | ACCEPTABLE | 5/5 passed |
| 6.10 Safety invariants (Property 13) | ACCEPTABLE | 7/7 passed (`max_examples=200` for safety axes) |
| 6.11 Wire caches into the decision core | **PARTIAL** | See below |

### 6.11 partial-wiring breakdown

| Component | Wiring status |
|-----------|---------------|
| `ContextBuildCache` → `ContextBuilder.build` call site in `AgentRuntime.run` | **WIRED** ✅ — guarded by `if self._context_build_cache is not None`; default-off path is bit-identical to baseline (verified by zero-cache-event regression test) |
| `LLMDecisionFrameCache` → `LLMDecisionFrame.build` call site | **HELPER ONLY** ⚠️ — `_build_decision_frame_cached` exists on `AgentRuntime` but the cognitive cycle does not invoke `LLMDecisionFrame.build` from `AgentRuntime` today; cache is reachable only by future call sites |
| `PromptFrameCache` → render call site | **HELPER ONLY** ⚠️ — `_render_prompt_text_cached` exists; no production caller invokes it |
| `TokenBudgetGovernor` → frame/model-call budget boundary | **HELPER ONLY** ⚠️ — `_enforce_frame_budget` exists; no production caller invokes it |
| `ContextBuildCache` composite key components | **STAND-IN** ⚠️ — uses `envelope.id` for `mission_hot_hash`, `workspace_snapshot_id`, `organ_state_hash`, `authority_hash`. Discriminates by mission (so cross-mission leakage is structurally impossible) but is not the canonical four-component key the design specifies |

### What this means concretely
- A mission run today benefits from **at most one** of the four Phase C caches (`ContextBuildCache`), and even that one keys off a stand-in.
- The other three caches and the governor are inert until the cognitive cycle is refactored to invoke `LLMDecisionFrame.build` / `render_prompt_text` / a frame budget through `AgentRuntime`.
- All five property tests run against the cache modules in isolation, so the **structural correctness** (canonical-form equivalence, invalidation closure, lifecycle, budget enforcement, safety invariants) is genuinely proven for those modules. The gap is **adoption**, not module correctness.

## Tests run

| Suite | Result |
|-------|--------|
| `pytest tests/perf/caches/test_cache_canonical_equivalence_property.py -v` | **6 passed** |
| `pytest tests/perf/caches/test_cache_invalidation_dependency_property.py -v` | **7 passed** |
| `pytest tests/perf/caches/test_decision_frame_cache_lifecycle_property.py -v` | **11 passed** |
| `pytest tests/perf/caches/test_token_budget_enforcement_property.py -v` | **5 passed** |
| `pytest tests/perf/caches/test_safety_invariants_property.py -v` | **7 passed** |
| `pytest tests/perf/caches/test_runtime_cache_wiring.py -v` | **4 passed** |
| `pytest tests/perf/caches/ -v (full Phase C)` | **40 passed** |
| `pytest tests/ -k "runtime or cache or perf"` | **192 passed** |
| `pytest tests/test_agent_runtime.py -v (baseline unchanged)` | **14 passed** |

### Pass / fail counts
- **Total Phase C new tests**: 40
- **Passed**: 40
- **Failed**: 0
- **Errors**: 0
- **Existing tests under runtime/cache/perf scope**: 192/192

### Skipped tests
- None

### Benchmark results
- N/A — Phase C has no benchmark sub-tasks. Hot-path latency benchmarks for the cache layer are owned by Phase F's `BenchmarkHarness`.

## Production behavior changed
**No.** All four cache injections are gated behind `if self._<cache> is not None:`. Default constructor values are `None`. The default-off mission run emits zero cache-family events (verified by structural witness test). Behavior is bit-identical to pre-Phase-C.

## Authority expansion
**No.** The `ContextBuildCache` composite key includes the `authority_hash` slot (currently `envelope.id` stand-in — but `envelope.id` is per-mission-unique, so a different authority envelope still hashes to a different cache key by construction). `LLMDecisionFrameCache.put` rejects `authority_expansion=True` writes; `LLMDecisionFrameCache.get` re-evicts on post-store mutation to `authority_expansion=True`. Both invariants validated in property tests 13 and 11.

## Raw secret leakage observed
**No.** Every cache module enforces a payload whitelist on the `EventBus`. Property 3 (test 6) asserts user-supplied substrings never appear in any cache event payload across all three caches. `LLMDecisionFrameCache.get` evicts entries with `raw_secret_leakage=True` (validated by Property 13).

## Cache correctness violations observed
**No.** `verify=True` divergence path emits `CACHE_CORRECTNESS_VIOLATION`, evicts, returns fresh, with builder/renderer invoked exactly once (validated by Property 3). No silent stale-data serve.

## P-B-PERF-01 status
**Open** — not silently closed during Phase C. Linux/macOS canonical persist p95 proof remains the open backlog item from Phase B.

## What is NOT claimed
- ❌ Phase C full LOCKED.
- ❌ Full runtime adoption of all four Phase C caches.
- ❌ Production code paths exercise `LLMDecisionFrameCache`, `PromptFrameCache`, or `TokenBudgetGovernor` today.
- ❌ The canonical four-component composite key for `ContextBuildCache` is in production.

## What IS claimed
- ✅ Five Phase C cache modules implemented under mini-review discipline.
- ✅ Five Phase C property tests pass with the documented invariants enforced (canonical-form equivalence, dependency closure, lifecycle, budget enforcement, safety invariants).
- ✅ `ContextBuildCache` is wired at the real `ContextBuilder.build` call site in `AgentRuntime`, default-off and bit-identical when not injected, with miss-then-hit observed end-to-end via regression test.
- ✅ Default-off contract preserved across all four cache injections.
- ✅ Cache events never include raw bodies, secrets, credentials, or artifact blobs.
- ✅ Cache hits never expand authority.

## Phase C verdict

**STRUCTURAL LOCK / PARTIAL RUNTIME ADOPTION.**

Phase D is allowed to start under the same mini-review discipline. The two backlog items below remain open and must be closed before Phase C can be re-graded as full LOCKED.

---

See `PHASE_C_BACKLOG.md` for the open backlog items P-C-RUNTIME-01 and P-C-KEY-01.
