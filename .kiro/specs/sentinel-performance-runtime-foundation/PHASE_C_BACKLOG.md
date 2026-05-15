# Phase C — Post-Lock Backlog

Items deferred from Phase C that do not block Phase D start, but **must** be closed before Phase C can be re-graded as full LOCKED.

---

## P-C-RUNTIME-01 — Wire `LLMDecisionFrameCache`, `PromptFrameCache`, and `TokenBudgetGovernor` into real decision-core call sites

**Status:** Open
**Priority:** Medium (correctness foundation already proven by property tests; adoption gap)
**Owner:** Sentinel runtime team
**Created:** Phase C closure

### Context

Task 6.11 wired `ContextBuildCache` at the real `ContextBuilder.build` call site in `AgentRuntime`. The other three cache injections — `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor` — are stored on `AgentRuntime` and exposed via private helper methods (`_build_decision_frame_cached`, `_render_prompt_text_cached`, `_enforce_frame_budget`), but no production call site invokes those helpers today.

The cognitive cycle in this codebase does not currently invoke `LLMDecisionFrame.build` or `LLMDecisionFrame.render_prompt_text` from `AgentRuntime`. Until that pattern lands (or the decision-core is otherwise refactored to call through these helpers), three of the four Phase C caches remain inert in production.

### Acceptance criteria (all required)

1. **`LLMDecisionFrameCache` wired at the real `LLMDecisionFrame.build` call site.**
   - Production path: `AgentRuntime` (or a downstream subagent it owns) computes the four-component composite hash, calls `cache.get(composite, mission_id=...)`, falls through to a real `LLMDecisionFrame.build(...)` invocation on miss, then `cache.put(composite, frame, mission_id=...)`.
   - Gated by `if self._decision_frame_cache is not None:` — default-off path remains bit-identical.
   - Regression test proves the cache is actually exercised: miss-then-hit observed across two runs against the same mission slice.
2. **`PromptFrameCache` wired at the real prompt render call site.**
   - Production path: `cache.get_or_render(frame, lambda f: f.render_prompt_text(), mission_id=...)`.
   - Gated by `if self._prompt_frame_cache is not None:` — default-off bit-identical.
   - Regression test proves miss-then-hit on identical frames.
3. **`TokenBudgetGovernor` wired at the real frame/model-call budget boundary.**
   - Production path: `governor.enforce_frame(mission_id, builder, self.context_compressor, frame_budget)`; result handled per the documented `BudgetDecision` contract (over-budget rejection short-circuits the model call).
   - `frame_budget` sourced from a real budget surface (e.g. `PromptBudgetAllocator` if available; otherwise documented as a deterministic constant tied to `MissionAuthorityEnvelope.max_cost_usd` or model-card limits, with rationale).
   - Gated by `if self._token_budget_governor is not None:` — default-off bit-identical.
   - Regression test proves a frame that exceeds the budget is rejected pre-execution and emits `BUDGET_EXCEEDED scope=frame`.
4. **Mini-review discipline preserved.** Each of the three wirings receives its own Mini Subtask Review (ACCEPTABLE / NEEDS FIX) before Phase C can be re-graded.

### Forbidden resolutions

- ❌ Move call sites into a test fixture and claim that as production wiring.
- ❌ Bypass the cache module's `verify=True` / safety re-check / TTL semantics on the integration path.
- ❌ Hide the integration behind a flag that defaults to "on" for tests but "off" everywhere else without documenting the asymmetry.

---

## P-C-KEY-01 — Replace `envelope.id` stand-in with the canonical four-component composite key

**Status:** Open
**Priority:** Medium (cross-mission leakage is structurally impossible today; correctness gap is on cross-snapshot/cross-organ-state cache hit shape)
**Owner:** Sentinel runtime team
**Created:** Phase C closure

### Context

The `AgentRuntime` integration of `ContextBuildCache` (Task 6.11) computes the composite key with all four slots bound to `envelope.id`:

```python
self._context_build_cache.composite_key(
    mission_hot_hash=envelope.id,
    workspace_snapshot_id="v1",
    organ_state_hash="v1",
    authority_hash=envelope.id,
)
```

This stand-in is correct on the cross-mission axis (different missions have different envelope ids → different composite keys → cache hits cannot leak across missions) but is incorrect on the other three axes:

- **`mission_hot_hash`** should hash the mutable mission state (constraints, blockers, organ_states, recent_action_summaries) so a context built early in the mission does not get reused after the hot state has materially changed.
- **`workspace_snapshot_id`** should be the `snapshot_id` of the current `WorkspaceSnapshotCache` so a context built before a workspace delta is not reused after the delta lands.
- **`organ_state_hash`** should hash the relevant organ surface state.
- **`authority_hash`** should hash the live `MissionAuthorityEnvelope` slice (allowed_actions, allowed_paths, etc.) so a context built before an authority change is not reused after the change.

Today all four bind to `envelope.id`, so any context built within the same mission for the same envelope id is treated as cache-equivalent — even after the hot state, workspace, organ state, or authority have changed mid-mission.

### Acceptance criteria (all required)

1. **`mission_hot_hash`** sourced from the `HotMissionCache` view's canonical-form hash (or an equivalent deterministic hash of the bounded mission state). When `HotMissionCache` is not injected, the runtime falls back to a documented surrogate (e.g. envelope id) **only if** the cache is also bypassed entirely — no silent partial-key.
2. **`workspace_snapshot_id`** sourced from `WorkspaceSnapshotCache.snapshot_id` (Phase E module). Until Phase E is implemented, this slot may bind to a constant **only if** the runtime documents and emits a `CACHE_INVALIDATION_BULK_WARNING`-equivalent on workspace delta arrival, OR the `ContextBuildCache` is left uninjected. No half-correct path.
3. **`organ_state_hash`** sourced from a deterministic hash of the organ surface relevant to the context (allowed organ kinds + organ promotion levels + organ kill-switch states).
4. **`authority_hash`** sourced from a deterministic hash of the canonical `MissionAuthorityEnvelope` slice (sorted `allowed_actions`, `allowed_systems`, `allowed_tools`, `allowed_paths`, `allowed_domains`, `forbidden_actions`, `mode`, `max_actions`, `max_duration_minutes`).
5. **Property test** in `tests/perf/caches/test_runtime_cache_wiring.py` proves: changing any one of the four components causes a cache miss; not changing any of them causes a cache hit.

### Forbidden resolutions

- ❌ Bind any slot to `envelope.id` as a long-term answer.
- ❌ Drop `verify=True` diagnostic mode to mask key-divergence issues during the migration.
- ❌ Silently permit a cache hit across mid-mission state changes that the canonical key would have invalidated.

### Dependencies

- P-C-KEY-01 partially depends on P-B-PERF-01 (Phase B persist canonical proof) only insofar as the `ContextBuildCache` benefit is measurable; not on the correctness side.
- P-C-KEY-01 depends on Phase E `WorkspaceSnapshotCache` for the `workspace_snapshot_id` slot. Until Phase E lands, this slot may use a documented surrogate per acceptance criterion (2).

---

## Closure protocol

Both backlog items must be closed under the same mini-review discipline as the original Phase C tasks (ACCEPTABLE / NEEDS FIX after each, no silent claims of full LOCKED). When both are closed, an amended Phase C lock report should be produced with the verdict re-graded from **STRUCTURAL LOCK / PARTIAL RUNTIME ADOPTION** to **LOCKED**.

Until both are closed, the verdict remains **STRUCTURAL LOCK / PARTIAL RUNTIME ADOPTION** and Phase D may proceed only with explicit user acknowledgement of the deferral (already given for the Phase C → Phase D transition).
