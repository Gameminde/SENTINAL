# Brain To Organ Runtime Closed Loop Lock Report

Status vocabulary is limited to `CLOSED`, `PARTIAL`, `PREPARED`, and `NOT_STARTED`.
No global "closed loop complete" claim is made here.

## 1. Files Read Evidence

Read before implementation:

- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `AgentRuntime.__init__`, organ runtime config ownership, `run()` phase flow, existing `execute_organ_runtime_request()` helper.
  - Important implementation zones after this pack: `_organ_dispatch_should_run()`, `_dispatch_organs_from_runtime()`, `_extract_temporary_organ_candidates_from_user_input()`, and the `ORGAN_DISPATCHING` phase between `EXECUTING` and `ARTIFACT_REVIEWING`.
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py`
  - Existing Bridge -> Gate -> runtime execution pipeline.
  - Added typed browser preparation and semantic extraction request construction while preserving existing L2, L3, and browser read-only behavior.
- `sentinel-control/services/sentinel-core/sentinel/agent/brain/cognition_loop.py`
  - Confirmed `BrainCognitionResult.proposal_artifacts` as the preferred future source.
  - Runtime currently supports this as a structured source when provided, but direct BrainCognitionLoop invocation inside `AgentRuntime.run()` is not implemented in this pack.
- `sentinel-control/services/sentinel-core/sentinel/agent/models.py`
  - `AgentRunResult` now carries `organ_dispatch_result`, memory feedback status refs, and replan-ready metadata.
- `sentinel-control/services/sentinel-core/sentinel/shared/events.py`
  - Confirmed event type extension pattern and `ORGAN_DISPATCH_COMPLETED` / `ORGAN_DISPATCH_SKIPPED` availability.
- `sentinel-control/services/sentinel-core/sentinel/agent/phases.py`
  - Confirmed `ORGAN_DISPATCHING` exists as a serializable phase and transitions after `EXECUTING`.
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py`
  - Confirmed L2, L3, browser read-only, browser preparation, and browser semantic extraction execution entrypoints are explicit opt-in and default disabled.

## 2. Worktree Preflight Summary

Preflight before modification showed:

- Modified existing files:
  - `sentinel-control/services/sentinel-core/sentinel/agent/organs/__init__.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/phases.py`
  - `sentinel-control/services/sentinel-core/sentinel/shared/events.py`
- Untracked existing file:
  - `sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py`
- No preflight diff in:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`

Interpretation:

- The phase/event/runtime execution work appeared inherited from prior Opus/Codex work and was preserved.
- `organ_dispatch.py` already contained the core dispatch pipeline but was not tracked yet.
- This pack modified `runtime.py`, `models.py`, `final_gate.py`, `delegated_action_gate.py`, and completed the untracked dispatcher rather than replacing it.
- The existing default-off organ execution config was preserved.

## 3. Closed Loop Truth Table

| Segment | Status | Evidence test | Limitation |
| --- | --- | --- | --- |
| Brain candidate source | PARTIAL | `test_enabled_l2_success_dispatches_executes_receipts_and_finalgate`, `test_enabled_l3_success_dispatches_reversible_receipt_and_finalgate`, browser success test use structured runtime candidate input; `runtime.py` also accepts `BrainCognitionResult.proposal_artifacts` when supplied. | `AgentRuntime.run()` still does not invoke `BrainCognitionLoop` directly. The structured user-input bridge is explicitly marked temporary. |
| OrganDispatcher | CLOSED | `test_enabled_l2_success_dispatches_executes_receipts_and_finalgate`, `test_enabled_l3_success_dispatches_reversible_receipt_and_finalgate`, `test_enabled_browser_readonly_preparation_and_semantic_extraction`. | Closed for explicit candidates/proposals only, not for automatic Brain loop invocation. |
| DelegatedActionGate | CLOSED | `test_enabled_gate_rejection_blocks_before_executor`, `test_no_l4_l5_l6_l7_or_forbidden_surface_execution`, `tests/test_delegated_action_gate_model_v0.py`. | L4 browser perception can pass only with explicit authority/user review/special authority and supported browser perception contracts. |
| L2 execution | CLOSED | `test_enabled_l2_success_dispatches_executes_receipts_and_finalgate`; L2 regression suite passed. | Only local artifact execution, no external action. |
| L3 execution | CLOSED | `test_enabled_l3_success_dispatches_reversible_receipt_and_finalgate`; L3 regression suite passed. | Only reversible local workspace mutation. No shell, browser action, API, desktop, or channel execution. |
| Browser ReadOnly / Preparation / Semantic | CLOSED | `test_enabled_browser_readonly_preparation_and_semantic_extraction`. | Closed for read-only observation, preparation, and semantic extraction semantics only. No submit/login/upload/download/JS/credentials. |
| Receipt | CLOSED | L2, L3, and browser dispatch success tests assert execution results include receipts; low-risk FinalGate receipt suite passed. | Receipt is measurement only and does not authorize future execution. |
| FinalGate | CLOSED | L2, L3, and browser success tests assert certificates; `tests/test_low_risk_execution_finalgate_receipts.py` passed. | FinalGate certifies received metadata; it does not execute, rollback, or approve future actions. |
| Memory feedback | PREPARED | `test_memory_feedback_honesty_is_prepared_not_fake_closed`. | No real memory object is written by `AgentRuntime.run()` in this pack. Only dispatch event/ref + input hash are prepared as feedback refs. |
| Replan-ready output | PREPARED | `test_replan_ready_packet_is_prepared_without_automatic_replan`. | `replan_ready=true`; `automatic_replan_executed=false`. No automatic replan is executed. |
| AgentRuntime default-off | CLOSED | `test_default_off_exact_regression_preserves_existing_behavior`, `test_phase_order_enabled_and_disabled`. Existing runtime tests also passed. | Dispatch is absent unless `organ_dispatch_enabled` and organ execution config are explicitly enabled. |

## 4. Default-Off Proof

`test_default_off_exact_regression_preserves_existing_behavior` proves:

- `organ_dispatch_result is None`
- `memory_feedback_path == "NOT_STARTED"`
- `replan_ready is False`
- `automatic_replan_executed is False`
- no organ dispatch completed/skipped event is emitted
- no generated artifact path is created

Existing runtime regression commands also passed:

- `python -m pytest tests/test_organ_execution_agentruntime_opt_in.py -q`
- `python -m pytest tests/test_runtime_model_execution_wiring.py -q -rs`
- `python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q`

## 5. Anti-Overclaim Statement

- Closed where proven by tests.
- Partial where the Brain source is accepted structurally but the real BrainCognitionLoop is not invoked by `AgentRuntime.run()`.
- Prepared where feedback/replan metadata is available but not acted on.
- No fake closed loop.
- `automatic_replan_executed=false` because no automatic replan is executed by this pack.

## 6. Verification Summary

Targeted tests run after implementation:

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

Total targeted/regression tests represented by these commands: 240 passed.
