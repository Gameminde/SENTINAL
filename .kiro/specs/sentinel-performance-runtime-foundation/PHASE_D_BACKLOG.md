# Phase D — Post-Lock Backlog

Items deferred from Phase D that do not block Phase E start, but **must** be closed before Phase D can be re-graded.

---

## P-D-RUNTIME-01 — Wire mission-level `OrganKillSwitch` table into `_route_local_tool_call_through_scheduler`

**Status:** Open
**Priority:** Medium (correctness foundation already proven by property + regression tests; runtime kill-switch sourcing gap)
**Owner:** Sentinel runtime team
**Created:** Phase D closure

### Context

Task 8.8 wired `AsyncOrganScheduler` + `BackpressureController` into `AgentRuntime._execute_controlled_tool_calls` under a default-off / injection-gated contract. The injected path now routes every non-browser controlled-capability tool call through `scheduler.submit(...)`, with all four safety surfaces (`OrganAuthorityEnvelope`, `OrganKillSwitch`, `OrganDryRunReceipt`, `BackpressureController`) consulted before the synchronous runner ever runs.

The current implementation, however, builds a **fresh non-triggered `OrganKillSwitch`** inside `_route_local_tool_call_through_scheduler` for every routed call:

```python
kill_switch = OrganKillSwitch(
    mission_id=envelope.id,
    organ_id=organ_id,
    enabled=True,
    triggered=False,           # <-- always False
    execution_allowed=True,    # <-- always True
)
```

This is correct on the *enforcement* axis — Test 3 of `test_runtime_scheduler_wiring.py` proves the scheduler **does** reject submissions when a kill-switch is triggered. But the runtime cannot **source** a triggered kill-switch from anywhere today: no mission-level kill-switch table exists in `AgentRuntime`, and the test had to monkey-patch the helper to inject a triggered switch.

In production, an operator-initiated kill-switch event (e.g. `kill_switch.trigger(reason=...)`) must propagate to the next routed tool call within the same mission. Today that propagation has no plumbing.

### Acceptance criteria (all required)

1. **Mission-level kill-switch registry exposed on `AgentRuntime`.** Either an additive optional `kill_switch_registry` constructor kwarg (typed `Mapping[str, OrganKillSwitch]` keyed by mission-id, default `None`), or an existing registry already on the runtime that the helper consults. When `None`, behaviour matches the current default-non-triggered behaviour.
2. **`_route_local_tool_call_through_scheduler` consults the registry**, falling back to a non-triggered switch only when the registry has no entry for the current `(mission_id, organ_id)` pair. The fallback path remains bit-identical to today's behaviour for unmodified callers.
3. **Trigger semantics are explicit.** When the registry returns a triggered switch, the helper passes it through to `scheduler.submit` and the scheduler emits `KILL_SWITCH_BLOCKED` and the helper mirrors `CONTROLLED_CAPABILITY_REJECTED` with `reason="kill_switch_blocked"` — the same shape Test 3 already verifies under the monkey-patched helper.
4. **Regression test** added to `test_runtime_scheduler_wiring.py` (or a new sibling test) that constructs `AgentRuntime` with a real registry containing a triggered switch, and asserts the routed call is rejected without monkey-patching the helper.
5. **Default-path bit-identical contract preserved.** When no registry is injected and no scheduler is injected, AgentRuntime behaves exactly as today.

### Forbidden resolutions

- ❌ Build the registry into the synchronous path as a side-effect of Phase D — that changes default behaviour without an injection guard.
- ❌ Move the kill-switch construction out of `_route_local_tool_call_through_scheduler` into `_execute_controlled_tool_calls` such that the kill-switch is consulted only on the scheduler-routed path; the synchronous path must continue to use the runner's internal black-zone gate as it does today.

---

## P-D-BATCH-01 — Replace per-call `asyncio.run` with shared event-loop dispatch

**Status:** Open
**Priority:** Low (performance, not correctness)
**Owner:** Sentinel runtime team
**Created:** Phase D closure

### Context

`_route_local_tool_call_through_scheduler` currently invokes `asyncio.run(_drive())` once per tool call. Each call constructs a fresh event loop, runs `submit` plus the wrapper-task drain to completion, then closes the loop. For high tool-call-count missions this serialises submissions through repeated loop construction overhead.

The scheduler's documented Requirement 7.1 budget (`submit` p95 ≤ 1 ms) is satisfied per submission — Task 8.7 measured 0.078 ms. The aggregate cost across N tool calls is bounded by N × (submit + loop construction). Loop construction on Windows is roughly 0.5 ms; on Linux/macOS roughly 0.2 ms. For N ≤ 20 this is negligible; for large N it could amount to ~10–20 ms of per-mission overhead.

### Acceptance criteria (any one of)

1. **Shared event loop per `_execute_controlled_tool_calls` invocation.** The synchronous helper drives a single `asyncio.new_event_loop()` for the entire batch of routed calls, runs them sequentially or concurrently inside that loop, and closes the loop once at the end. Submit p95 still satisfied; aggregate cost reduced.
2. **Batch submit API.** `AsyncOrganScheduler.submit_batch(...)` takes a list of (action, authority, kill_switch, dry_run) tuples and returns a list of `SubmissionAck` in the same order. The runtime helper delegates to it. Receipt-stream parity preserved.
3. **Honest deferral.** Phase D regression tests show ≤ 30ms aggregate overhead per mission with N=10 routed calls is acceptable for current Sentinel mission shapes; document the measurement and close P-D-BATCH-01 with no implementation change. Requires user approval.

### Forbidden resolutions

- ❌ Convert `_execute_controlled_tool_calls` to async without explicit user permission (strict Phase D rule — public sync surface preserved).
- ❌ Use `asyncio.get_event_loop()` (deprecated for non-coroutine callers) — must construct a fresh loop or use `asyncio.run` semantics.

---

## P-D-BROWSER-01 — Route browser-shaped tool calls through `AsyncOrganScheduler`

**Status:** Open
**Priority:** Low (scope expansion, not correctness)
**Owner:** Sentinel runtime team
**Created:** Phase D closure

### Context

Task 8.8 explicitly excludes browser-shaped tool calls from the scheduler-routed path:

```python
scheduler_path_eligible = (
    self._async_organ_scheduler is not None
    and self._backpressure_controller is not None
    and canonicalization.call.action
    not in BrowserControlledCapabilityRunner.SUPPORTED_ACTIONS
)
```

Reason: browser routes (`browser_operator_route.run(...)`) and the `BrowserControlledCapabilityRunner` run a separate organ chain whose receipt-stream contract is owned by the browser organ tests. Routing them through the scheduler in the same wave as Task 8.8 would change observable behaviour beyond the task's authorised scope.

### Acceptance criteria (all required)

1. Browser-shaped tool calls route through `scheduler.submit(...)` in the injected path with the same default-off / bit-identical contract.
2. Browser organ regression tests pass without modification on the default path.
3. Receipt-stream parity test extended to include a representative browser tool call (or a sibling test for browser routes specifically).
4. The browser operator route's existing `OrganAuthorityEnvelope` / `OrganKillSwitch` / `OrganDryRunReceipt` are preserved end-to-end (no synthetic substitution).

### Forbidden resolutions

- ❌ Change browser organ test contracts to accommodate scheduler events without a separate task and explicit user authorisation.

---

## Closure protocol

All three backlog items must be closed under the same mini-review discipline as the original Phase D tasks (ACCEPTABLE / NEEDS FIX after each, no silent claims of full LOCKED). When all three are closed, an amended Phase D lock report should be produced if the verdict requires re-grading.

For now the verdict is **LOCKED** (default-off / injection-gated wiring is correct, all property tests + regression tests + smoke pass). The backlog items above are scope-expansion / production-sourcing improvements that do not retroactively invalidate Phase D's correctness guarantees.
