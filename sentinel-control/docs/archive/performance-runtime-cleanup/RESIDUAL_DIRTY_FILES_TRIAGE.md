# Residual Dirty Files Triage

Recorded at: 2026-05-16

Scope: final inspection only. No staging, no commit, no push, no P6U, and no new phase started.

## Commands Run

```bash
git status --short
git diff --stat
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git diff -- sentinel-control/services/sentinel-core/sentinel/mission/runner.py
rg "_block_repair_if_action_budget_would_overflow|_accepted_controlled_capability_count|_raw_tool_call_payloads|_controlled_capture_root|_certify_trace|_snapshot_trace" sentinel-control/services/sentinel-core/sentinel/agent/runtime.py sentinel-control/services/sentinel-core/tests -n
rg "CognitiveCycle\(|ContextBuilder\(|ContextCompressor\(" sentinel-control/services/sentinel-core/sentinel/agent/runtime.py sentinel-control/services/sentinel-core/sentinel -n
```

## Current Dirty Tree

```text
 M sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
 M sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
 M sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
 M sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
 M sentinel-control/services/sentinel-core/sentinel/mission/runner.py
```

Diff stat:

```text
sentinel/agent/cognitive_cycle.py      |  18 ++++
sentinel/agent/context_builder.py      |  35 +++++-
sentinel/agent/context_compressor.py   |  18 ++++
sentinel/agent/runtime.py              | 119 +++++----------------
sentinel/mission/runner.py             |  83 ++++++++++----
5 files changed, 155 insertions(+), 118 deletions(-)
```

## Executive Classification

| File | Classification | Recommended action |
|------|----------------|--------------------|
| `sentinel/agent/cognitive_cycle.py` | Commit candidate | Commit as default-off performance instrumentation residual. |
| `sentinel/agent/context_builder.py` | Commit candidate | Commit as default-off performance instrumentation residual. |
| `sentinel/agent/context_compressor.py` | Commit candidate | Commit as default-off performance instrumentation residual. |
| `sentinel/agent/runtime.py` | Revert candidate | Revert residual comment/whitespace hunk; do not commit. |
| `sentinel/mission/runner.py` | Mixed: commit + revert | Commit perf constructor/profiler/cache hunks; revert import-order/comment-only cleanup hunks. |

Verdict: `READY_FOR_FINAL_CLEANUP`

The repo can become clean now with one small perf-residual commit plus a targeted revert of obsolete comment/whitespace leftovers.

## File: `sentinel/agent/cognitive_cycle.py`

### Remaining Hunks

```diff
+from typing import TYPE_CHECKING
+
+if TYPE_CHECKING:
+    from sentinel.perf.measure.latency_profiler import LatencyProfiler
+
+    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
+        self._latency_profiler = latency_profiler
+
     def orient(self, state: AgentState, context: AgentContext) -> AgentState:
+        if self._latency_profiler is not None:
+            with self._latency_profiler.instrument(...):
+                return self._do_orient(state, context)
+        return self._do_orient(state, context)
+
+    def _do_orient(self, state: AgentState, context: AgentContext) -> AgentState:
```

### Classification

`commit as performance instrumentation residual`

### Why

This is a default-off optional `LatencyProfiler` injection. With `latency_profiler=None`, behavior is intended to stay bit-identical except for the extracted `_do_orient` helper. It does not add authority, external execution, or new product power.

### Risk If Wrong

If the wrapper changes exception timing or profiler context behavior, cognition orientation could fail only when profiler is injected.

### Required Tests Before Commit

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

Recommended optional follow-up test: add or locate a small unit test proving `CognitiveCycle(latency_profiler=None).orient(...)` matches the old path and injected profiler records exactly one span.

## File: `sentinel/agent/context_builder.py`

### Remaining Hunks

```diff
-from typing import Any
+from typing import TYPE_CHECKING, Any
+
+if TYPE_CHECKING:
+    from sentinel.perf.measure.latency_profiler import LatencyProfiler
+
+    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
+        self._latency_profiler = latency_profiler
+
     def build(...):
+        if self._latency_profiler is not None:
+            with self._latency_profiler.instrument(...):
+                return self._do_build(...)
+        return self._do_build(...)
+
+    def _do_build(...):
```

### Classification

`commit as performance instrumentation residual`

### Why

This matches the Phase A/F performance-runtime shape: default-off latency instrumentation around a hot context-build path. It is not wired into a new runtime power and does not change authority semantics.

### Risk If Wrong

The extracted `_do_build` path must preserve exact context fields and memory/evidence handling. A subtle parameter-forwarding bug would affect prompt/context construction.

### Required Tests Before Commit

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

Recommended optional follow-up test: assert `ContextBuilder().build(...)` and `ContextBuilder(latency_profiler=fake).build(...)` produce identical `AgentContext` values except profiler side effects.

## File: `sentinel/agent/context_compressor.py`

### Remaining Hunks

```diff
+from typing import TYPE_CHECKING
+
+if TYPE_CHECKING:
+    from sentinel.perf.measure.latency_profiler import LatencyProfiler
+
+    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
+        self._latency_profiler = latency_profiler
+
     def compress(self, context: AgentContext) -> AgentContext:
+        if self._latency_profiler is not None:
+            with self._latency_profiler.instrument(...):
+                return self._do_compress(context)
+        return self._do_compress(context)
+
+    def _do_compress(self, context: AgentContext) -> AgentContext:
```

### Classification

`commit as performance instrumentation residual`

### Why

This is the same default-off profiler wrapper pattern as context builder and cognitive cycle. It is a plausible final residual from the performance-runtime foundation.

### Risk If Wrong

If `_do_compress` extraction changes return identity or summary truncation behavior, context compression behavior could drift.

### Required Tests Before Commit

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

Recommended optional follow-up test: assert summary truncation and evidence/capability preservation stay identical with and without injected profiler.

## File: `sentinel/agent/runtime.py`

### Remaining Hunks

```diff
- blank line after imports
+ blank line after `state.transition(AgentPhase.CONTEXT_BUILDING)`

- large diff hunk around `_block_repair_if_action_budget_would_overflow`,
  `_accepted_controlled_capability_count`, `_raw_tool_call_payloads`,
  `_controlled_capture_root`, `_certify_trace`, `_snapshot_trace`
+ replacement appears as a long scheduler helper comment in `git diff`

- comment: `(consumed by RuntimeCertificationGate, downstream verifiers and the trace replayer ...`
+ comment: `(consumed by RuntimeCertificationGate, CoreFinalGate, and the trace replayer) ...`

- blank line before decision-frame cache wrapper comment
```

Important inspection note:

`rg` confirms the helper methods still exist in the working file:

```text
_block_repair_if_action_budget_would_overflow
_accepted_controlled_capability_count
_raw_tool_call_payloads
_controlled_capture_root
_certify_trace
_snapshot_trace
```

The large diff hunk appears to be a misleading block-level diff around comment placement, not an actual safe semantic cleanup to commit. The only clear intended changes are comments/blank lines.

### Classification

`revert as obsolete leftover`

### Why

This file has no necessary executable residual for the final cleanup. The meaningful FinalGate runtime certification work was already committed in:

```text
e6565a1 - runtime: certify agent run results through final gate
```

The remaining hunks are comment/whitespace leftovers and should not create another runtime commit.

### Risk If Wrong

If staged accidentally, this could appear to delete or rewrite helper methods due to the large diff hunk, even though the working file currently still contains them. That makes it a bad hunk to commit casually.

### Required Tests After Revert

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

## File: `sentinel/mission/runner.py`

### Remaining Hunks

#### Hunk A - import order / whitespace

```diff
-from sentinel.mission.exceptions import BrowserOperatorRouteRejected
 from sentinel.mission.exceptions import MissionRevokedException
+from sentinel.mission.exceptions import BrowserOperatorRouteRejected

- blank line before TYPE_CHECKING
```

Classification: `revert as obsolete leftover`

#### Hunk B - constructor performance injection

```diff
     def __init__(..., browser_operator_route: BrowserOperatorMissionRouteProtocol | None = None,
+        *,
+        latency_profiler: LatencyProfiler | None = None,
+        hot_cache: HotMissionCache | None = None,
+        cold_store: ColdReceiptStore | None = None,
+        receipt_index: ReceiptIndex | None = None,
     ) -> None:
```

Classification: `commit as performance instrumentation residual`

Critical note:

The committed HEAD already assigns:

```text
self._latency_profiler = latency_profiler
self._hot_cache = hot_cache
self._cold_store = cold_store
self._receipt_index = receipt_index
```

without the constructor parameters. Therefore reverting this constructor hunk would leave `MissionRunner.__init__` with undefined local variables when instantiated. This hunk is not optional cosmetics; it repairs an incomplete previously committed performance-runtime wiring surface.

#### Hunk C - mission run profiler/hot-cache lifecycle

```diff
- trace_id = None
- self._latency_profiler.start_trace(... metadata={"phase": "mission_runner"})
+ _profiler_handle: str | None = None
+ self._latency_profiler.start(...)

+ self._hot_cache.set_objective(...)
+ self._hot_cache.set_constraints(...)
+ _error_occurred = False

- self._hot_cache.set(envelope.id, result)
+ except BaseException:
+     _error_occurred = True
+     self._latency_profiler.stop(... error=True ...)

- self._hot_cache.evict(envelope.id)
- self._latency_profiler.stop_trace(trace_id)
+ self._hot_cache.evict_mission(envelope.id)
+ self._latency_profiler.stop(_profiler_handle)
```

Classification: `commit as performance instrumentation residual`

Why:

This is the real MissionRunner Phase A-E performance-runtime wiring style. It aligns with the injected `LatencyProfiler` and `HotMissionCache` fields already present in HEAD and gives them usable lifecycle semantics.

#### Hunk D - revocation comments / formatting

```diff
- Task 4 / Requirement 4 (F-A3.10) - reactive revocation check.
+ Task 4 / Requirement 4 (F-A3.10) — reactive revocation check.

- steps; they must not execute.
+ steps — they MUST NOT execute.

comment expansion around post-step revocation and `_check_revocation`
```

Classification: `revert as obsolete leftover`

Why:

The reactive kill-switch behavior itself was already committed in:

```text
f8d8cda - mission: add revocation and browser route rejection safeguards
```

The remaining hunk only changes comments/formatting. It should not be mixed into the performance residual cleanup.

#### Hunk E - browser route rejection comments

```diff
+ comments under `except BrowserOperatorRouteRejected`
+ comments under `except Exception as original_exc`
```

Classification: `revert as obsolete leftover`

Why:

Structured browser route rejection behavior was already committed in `f8d8cda`. Remaining comments are not needed for a final cleanup commit.

### Recommended Action

Hunk-level split:

1. Commit only Hunks B and C as performance instrumentation residual.
2. Revert Hunks A, D, and E as obsolete comment/formatting leftovers.

### Risk If Wrong

Reverting Hunks B/C would leave the current committed `MissionRunner.__init__` with undefined constructor variables. Committing all of `runner.py` would mix perf wiring with unrelated comment/format churn.

### Required Tests Before Commit

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
python -m pytest tests/test_kill_switch_reactive_property.py -q
python -m pytest tests/test_mission_runner_browser_operator_route_rejected.py -q
```

## Recommended Final Cleanup Plan

### Commit 1 - performance residual wiring

Commit message:

```text
perf: finish residual runtime instrumentation wiring
```

Stage:

```text
sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py hunks B/C only
```

Do not stage:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
runner.py Hunks A/D/E
```

Required tests:

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
python -m pytest tests/test_kill_switch_reactive_property.py -q
python -m pytest tests/test_mission_runner_browser_operator_route_rejected.py -q
```

### Cleanup 2 - revert obsolete leftovers

After Commit 1, revert:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
runner.py remaining comment/import/whitespace hunks
```

Required tests:

```bash
python -m pytest tests/test_agent_runtime.py -q
python -m pytest tests/perf/ -m "not slow" -q
```

### Final Docs

Update `CURRENT_STATE_LOCK.md` and `POST_CLEANUP_HANDOFF.md` after the working tree is clean, then commit a final docs lock if needed.

## Can The Repo Become Clean Now?

Yes.

The repo can become clean now without starting a new phase:

1. Commit default-off perf residual wiring.
2. Revert runtime and runner comment/whitespace leftovers.
3. Run targeted tests.
4. Update final lock/handoff docs if needed.

## Risks

1. `MissionRunner` is the only true risk. Its constructor performance parameters are needed because committed HEAD already references the corresponding local variables.
2. `runtime.py` should not be staged. The diff presents a large confusing block around helper methods, even though the helpers still exist in the working file.
3. The three agent helper files are low-risk but should still be tested because they split public methods into profiler wrappers and private `_do_*` helpers.
4. No backlog item should be marked closed by this cleanup. This is residual hygiene, not performance backlog completion.

## Final Verdict

```text
READY_FOR_FINAL_CLEANUP
```

Recommended next action:

```text
Commit perf residual wiring, then revert obsolete runtime/comment leftovers.
```
