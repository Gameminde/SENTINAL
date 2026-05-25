# Brain Native Candidate Source And Memory Feedback Lock Report

Status vocabulary is limited to `CLOSED`, `PARTIAL`, `PREPARED`, and `NOT_STARTED`.
No global "closed loop complete" claim is made here.

## 1. Files Read Evidence

Read before implementation:

- `sentinel-control/docs/reviews/BRAIN_TO_ORGAN_RUNTIME_CLOSED_LOOP_LOCK_REPORT.md`
  - Confirmed the previous truth table: Brain candidate source `PARTIAL`, memory feedback `PREPARED`, replan-ready output `PREPARED`.
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - Confirmed the existing `ORGAN_DISPATCHING` phase, temporary structured candidate bridge, `AgentRuntime.run()` return construction, and default-off organ dispatch config usage.
- `sentinel-control/services/sentinel-core/sentinel/agent/brain/cognition_loop.py`
  - Confirmed the stable API is `BrainCognitionLoop.run(BrainCognitionInput | dict)` and that `BrainCognitionResult.proposal_artifacts` is the native proposal source.
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py`
  - Confirmed the dispatcher already routes candidates through proposal bridge, delegated gate, executor request construction, receipt, and FinalGate.
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py`
  - Confirmed low-risk and browser perception organ execution remains explicit opt-in and default disabled.
- `sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_bridge.py`
  - Confirmed `RoleLoopMemoryBridge.build(...) -> MemoryBridgeResult` is the real typed memory feedback mechanism available in this pack.
- `sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_slots.py`
  - Confirmed slots remain data-not-instruction and are not used here as authority.
- `sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_retrieval.py`
  - Confirmed retrieval output remains scoped data only and is not used to authorize execution.
- `sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_replay.py`
  - Confirmed replay/checkpoint data remains historical metadata only.
- `sentinel-control/services/sentinel-core/sentinel/agent/models.py`
  - Confirmed `AgentRunResult` already carried dispatch/replan placeholders and was the right place to expose Brain and memory feedback results.
- `sentinel-control/services/sentinel-core/sentinel/shared/events.py`
  - Confirmed `ORGAN_DISPATCHING`, `ORGAN_DISPATCH_COMPLETED`, and `ORGAN_DISPATCH_SKIPPED` are the existing event/phase surface.
- `sentinel-control/services/sentinel-core/sentinel/agent/phases.py`
  - Confirmed the valid phase order already allows `EXECUTING -> ORGAN_DISPATCHING -> ARTIFACT_REVIEWING`.

## 2. Worktree Preflight Summary

Preflight before this pack showed:

- `git status --short --untracked-files=all`: clean.
- `git diff --stat`: no output.
- `git diff -- sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`: no output.
- `git diff -- sentinel-control/services/sentinel-core/sentinel/agent/brain/cognition_loop.py`: no output.
- `git diff -- sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_bridge.py`: no output.

The pack started from commit `634d709ef9d9`.
There were no inherited uncommitted Opus/Codex edits to preserve in this turn.
The main architectural risk was breaking the previous temporary `user_input` bridge; it was preserved behind explicit `temporary_candidate_bridge_enabled=True` and its regression tests were updated to declare that transition fallback intentionally.

## 3. Implementation Summary

- Added explicit config switches to `OrganRuntimeExecutionConfig`:
  - `brain_native_candidate_source_enabled = false`
  - `temporary_candidate_bridge_enabled = false`
  - `memory_feedback_enabled = false`
- Added optional, default-off `AgentRuntime` injections:
  - `brain_cognition_loop`
  - `memory_bridge`
- `AgentRuntime.run()` now calls `BrainCognitionLoop.run(...)` only when organ dispatch is enabled and `brain_native_candidate_source_enabled=true`.
- Native Brain proposals become the primary organ candidate source when present and safe.
- The temporary structured `user_input` bridge is disabled by default and used only when explicitly enabled.
- `AgentRuntime.run()` now calls `RoleLoopMemoryBridge.build(...)` when `memory_feedback_enabled=true`, producing a typed `MemoryBridgeResult`.
- `AgentRunResult` now exposes:
  - `brain_cognition_result`
  - `brain_candidate_source_status`
  - `memory_feedback_result`
  - `memory_snapshot_ref`
  - `durable_memory_persistence`
- `replan_packet` is now populated with Brain refs, proposal refs, dispatch refs, receipt refs, FinalGate certificate refs, memory feedback refs, unresolved objections, missing evidence, and recommended next loop input.
- `automatic_replan_executed` remains `false`.
- Durable memory persistence is not implemented or claimed; `durable_memory_persistence = NOT_STARTED`.

## 4. Closed Loop Truth Table

| Segment | Previous status | New status | Evidence test | Limitation |
| --- | --- | --- | --- | --- |
| Brain candidate source | PARTIAL | CLOSED | `test_brain_native_enabled_uses_proposals_as_primary_source_without_fallback`; `test_brain_native_source_runs_before_organ_dispatching_and_is_skipped_disabled` | Closed for explicit opt-in `BrainCognitionInput` passed to `AgentRuntime.run()`. No free-text candidate parsing. |
| OrganDispatcher | CLOSED | CLOSED | `test_brain_native_l2_path_writes_real_memory_feedback_and_replan_packet`; `test_brain_native_l3_path_produces_receipt_finalgate_feedback_and_replan`; previous closed-loop tests | Still requires explicit runtime opt-in and candidate-compatible organ contracts. |
| DelegatedActionGate | CLOSED | CLOSED | `test_brain_native_dangerous_surfaces_never_dispatch_execution`; delegated gate suite | Gate remains classification/allowance only. It does not execute. |
| L2 execution | CLOSED | CLOSED | `test_brain_native_l2_path_writes_real_memory_feedback_and_replan_packet`; L2 executor suite | Local artifact only. |
| L3 execution | CLOSED | CLOSED | `test_brain_native_l3_path_produces_receipt_finalgate_feedback_and_replan`; L3 executor suite | Reversible local workspace mutation only. |
| Browser ReadOnly / Preparation / Semantic | CLOSED | CLOSED | `test_brain_native_browser_perception_trio_is_non_mutating_data_only` | Browser L4 remains read-only/preparation/semantic extraction only. No submit/login/upload/download/credential/JS. |
| Receipt | CLOSED | CLOSED | L2/L3/browser native tests assert receipt presence; FinalGate receipt suite | Receipts are measurements, not authority. |
| FinalGate | CLOSED | CLOSED | L2/L3/browser native tests assert FinalGate certificate presence; FinalGate receipt suite | FinalGate certifies the recorded result; it does not approve future execution. |
| Memory feedback | PREPARED | CLOSED | `test_memory_feedback_is_closed_only_after_real_bridge_result`; `test_brain_native_l2_path_writes_real_memory_feedback_and_replan_packet` | Closed for typed in-memory `MemoryBridgeResult`; no durable persistence. |
| Durable memory persistence | NOT_STARTED | NOT_STARTED | `test_durable_memory_persistence_is_not_claimed` | No database/file persistence layer was added. |
| Replan-ready output | PREPARED | CLOSED | `test_replan_ready_packet_is_closed_without_automatic_replan` | Closed as a packet only. It prepares the next loop input but does not run it. |
| Automatic replan execution | NOT_STARTED | NOT_STARTED | `test_replan_ready_packet_is_closed_without_automatic_replan` | `automatic_replan_executed=false`; no automatic replan is executed in this pack. |
| AgentRuntime default-off | CLOSED | CLOSED | `test_default_off_exact_regression_skips_brain_memory_and_replan`; runtime regression tests | Brain, memory feedback, dispatch, and temporary bridge remain disabled unless explicitly configured. |

## 5. Anti-Overclaim Statement

- No fake lock.
- `CLOSED` is used only where tests prove the segment.
- `PREPARED` is used only where a packet/ref exists without execution.
- `NOT_STARTED` is used for durable memory persistence and automatic replan execution.
- `automatic_replan_executed=false` because no automatic replan loop is implemented or tested.
- Durable memory persistence is not claimed.
- Memory feedback is `CLOSED` only because `AgentRuntime.run()` calls `RoleLoopMemoryBridge.build(...)` and stores a typed `MemoryBridgeResult`.

## 6. Verification Summary

Targeted commands run after implementation:

- `python -m pytest tests/test_brain_native_candidate_source_and_memory_feedback_lock.py -q` -> 12 passed
- `python -m pytest tests/test_brain_to_organ_runtime_closed_loop.py -q` -> 10 passed
- `python -m pytest tests/test_organ_execution_agentruntime_opt_in.py -q` -> 29 passed
- `python -m pytest tests/test_low_risk_execution_finalgate_receipts.py -q` -> 27 passed
- `python -m pytest tests/test_reversible_workspace_action_executor_l3.py -q` -> 42 passed
- `python -m pytest tests/test_low_risk_local_artifact_executor_l2.py -q` -> 30 passed
- `python -m pytest tests/test_delegated_action_gate_model_v0.py -q` -> 25 passed
- `python -m pytest tests/test_organ_proposal_bridge.py -q` -> 26 passed
- `python -m pytest tests/test_brain_cognition_loop_wiring.py -q` -> 21 passed
- `python -m pytest tests/test_runtime_model_execution_wiring.py -q -rs` -> 9 passed
- `python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q` -> 21 passed

Total targeted tests represented by these commands: 252 passed.
