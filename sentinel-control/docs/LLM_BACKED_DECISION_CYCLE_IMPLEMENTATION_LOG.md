# Sentinel LLM-Backed Decision Cycle - Implementation Log

Spec: `.kiro/specs/sentinel-llm-backed-decision-cycle/`

Anchor commit: `1f2a245` - `perf: lock context cache runtime closure`

Goal for this spec:

```text
AgentRuntime context
-> LLMDecisionFrame
-> prompt render
-> ModelCallPlan
-> stop unless a sanctioned model backend already exists
```

No API key is required by this spec. Real model execution is reserved for the future `sentinel-real-model-execution-backend` spec, which may use environment variables only and must include budget, timeout, trace, redaction, FinalGate, and skip-safe tests.

## Entry Template

Each task entry records:

- task id
- files read
- files changed
- implementation summary
- tests added or updated
- tests run
- result
- authority impact
- secrets impact
- deferrals opened or closed
- safe to continue

No entry may include raw prompt bodies, raw receipt bodies, browser/file/API bodies, credentials, or secrets.

## Entries

### 0.1 - Inspect AgentRuntime.run

- task id: 0.1
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/requirements.md`
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/design.md`
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/tasks.md`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Inspected `AgentRuntime.run` without production edits. The run signature starts at `runtime.py:251`. The best insertion point is after tool selection finishes and before hypothesis verification begins: `AgentPhase.TOOL_SELECTING` starts at `runtime.py:528`, and `AgentPhase.HYPOTHESIS_VERIFYING` starts at `runtime.py:616`. This point has compressed context, selected capabilities, selected/candidate/blocked tools, missing capabilities, and tool-selection findings, while still preceding execution-sensitive tool dispatch.
- tests added or updated: none
- tests run:
  - `rg -n "AgentPhase\\.TOOL_SELECTING|AgentPhase\\.HYPOTHESIS_VERIFYING|def run\\(" sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- result: pass
- authority impact: none; inspection only.
- secrets impact: none; inspection output contains only filenames, signatures, and line references.
- deferrals opened or closed: none
- safe to continue: yes

### 0.2 - Inspect LLM decision-frame contracts

- task id: 0.2
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Verified that `LLMDecisionFrame` exists at `decision_frame.py:23`, `LLMDecisionFrame.build(...)` starts at `decision_frame.py:45`, and `render_prompt_text(...)` starts at `decision_frame.py:108`. The build contract requires mission, authority, progress, evidence cards, selected tool surface, blockers, next decision options, required output schema, and a `PromptBudgetAllocator`. The builder already sanitizes mission/authority/progress/blocker/option/schema payloads and evidence summaries.
- tests added or updated: none
- tests run:
  - `rg -n "class LLMDecisionFrame|def build\\(|def render_prompt_text|class PromptBudgetAllocator|def estimate_frame_tokens" sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py`
- result: pass
- authority impact: none; inspection only.
- secrets impact: none; no raw prompt or runtime payload inspected.
- deferrals opened or closed: none
- safe to continue: yes

### 0.3 - Inspect cache, budget, and optimizer wrappers

- task id: 0.3
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/token_budget_governor.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Verified the existing runtime wrappers: `_build_decision_frame_cached(...)` at `runtime.py:1854`, `_render_prompt_text_cached(...)` at `runtime.py:1900`, and `_enforce_frame_budget(...)` at `runtime.py:1930`. Verified `TokenBudgetGovernor.enforce_frame(...)` starts at `token_budget_governor.py:356` and `ModelCallOptimizer.plan(frame, ledger=None)` starts at `model_call_optimizer.py:353`. The wrappers are already default-off and are the only acceptable wrappers for this spec.
- tests added or updated: none
- tests run:
  - `rg -n "def _build_decision_frame_cached|def _render_prompt_text_cached|def _enforce_frame_budget|class ModelCallOptimizer|def plan\\(|class TokenBudgetGovernor|def enforce_frame\\(" ...`
- result: pass
- authority impact: none; inspection only.
- secrets impact: none.
- deferrals opened or closed: none
- safe to continue: yes

### 0.4 - Verify model execution backend status

- task id: 0.4
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/llm/interface.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/llm/context_pack.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - repository grep results under `sentinel-control/services/sentinel-core/sentinel`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Verified that the repo contains bounded LLM-facing contracts (`ContextPackAssembler`, `BrowserPlannerRole`, `BrowserVerifierRole`) but no sanctioned model execution backend wired into `AgentRuntime.run`. `BrowserPlannerRole.draft(...)` and `BrowserVerifierRole.verify(...)` are deterministic helpers operating on caller-supplied inputs; they are not model backends. This spec therefore stops at frame, prompt, and `ModelCallPlan`.
- tests added or updated: none
- tests run:
  - `rg -n "class BrowserPlannerRole|class BrowserVerifierRole|def draft\\(|def verify\\(|ContextPackAssembler|LLM_REASONING_DRAFTED|LLM_VERIFICATION_DRAFTED" sentinel-control/services/sentinel-core/sentinel/agent/llm`
  - repository search for provider SDK calls, model execution entrypoints, and provider credential environment names under `sentinel-control/services/sentinel-core/sentinel`
- result: pass
- authority impact: none; inspection only.
- secrets impact: none; no API keys were requested or read.
- deferrals opened or closed:
  - opened / confirmed: `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`
  - rationale: no sanctioned model execution backend exists in `AgentRuntime.run`; future work belongs to `sentinel-real-model-execution-backend`.
- safe to continue: yes

### 1.1 - Create implementation log

- task id: 1.1
- files read:
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/tasks.md`
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/design.md`
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/requirements.md`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Created this implementation log and recorded Wave 0 evidence in a sanitized, append-only format. The log explicitly states that this spec requires no provider API key and that real model execution is deferred to the future `sentinel-real-model-execution-backend` spec unless a sanctioned backend is found later.
- tests added or updated: none
- tests run: none
- result: pass
- authority impact: none; documentation only.
- secrets impact: none.
- deferrals opened or closed:
  - confirmed: `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`
- safe to continue: yes

### 1.2 - Lock data mapping table

- task id: 1.2
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/mission/models.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/models.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/state.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py`
- files changed:
  - `sentinel-control/docs/LLM_BACKED_DECISION_CYCLE_IMPLEMENTATION_LOG.md`
- implementation summary: Locked the field mapping for the runtime seam. `mission_card` comes from `MissionAuthorityEnvelope` plus `AgentContext.summary/constraints`; `authority_card` comes from authority envelope fields plus `original_allowed_actions`; `progress_card` comes from `AgentState`, selected methods, capabilities, and tool-selection state; `evidence` is built only from compact refs/summaries already present; `selected_tool_surface` is the authority-bounded intersection of selected tools and allowed tools; blockers come from missing/unavailable capabilities, blocked tools, critical findings, and blocking questions; output schema is static and sanitized; budget allocator requires a user-selected model contract.
- tests added or updated: none
- tests run: none
- result: pass
- authority impact: none; data mapping does not add authority and explicitly intersects tools with `envelope.allowed_tools`.
- secrets impact: none; mapping forbids raw prompt, raw receipt, raw browser/file/API body, artifact blobs, credentials, and secrets.
- deferrals opened or closed:
  - `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` remains open.
  - `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` remains out of scope.
  - `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` remains out of scope.
- safe to continue: yes

### 2.1 - Carry ContextCacheKey safely

- task id: 2.1
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- implementation summary: Added a local `context_cache_key` carry-forward variable inside `AgentRuntime.run`. It is assigned only after `ContextCacheKeyBuilder.derive(...)` succeeds and the authority-drift check confirms that the live authority hash still matches the derived key. If derivation fails or authority drift is detected, the key remains unavailable and the decision-frame seam re-derives through `ContextCacheKeyBuilder` or bypasses the decision-frame cache; it never falls back to `envelope.id` or partial keys.
- tests added or updated:
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
- result: pass (`7/7`)
- authority impact: none; the key carries authority hash only and does not change envelope powers.
- secrets impact: none; no raw authority payload or rejected sanitizer substring is logged.
- deferrals opened or closed: none
- safe to continue: yes

### 3.1-3.3 - Build LLMDecisionFrame default-off

- task id: 3.1, 3.2, 3.3
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/evidence_ranker.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/model_contract.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/models.py`
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: Added an injection-gated LLM decision seam after `TOOL_SELECTING` and before `HYPOTHESIS_VERIFYING`. The seam is enabled only when `user_model_contract` is injected. It builds `LLMDecisionFrame` only through `LLMDecisionFrame.build(...)`, sourcing all cards from existing runtime objects and compact refs. It records only safe metadata on `AgentRunResult.llm_decision_cycle`; no raw prompt body is stored.
- tests added or updated:
  - default-off compatibility test
  - real frame/prompt/model-plan metadata test
  - authority-bounded tool-surface test
  - raw prompt/secret metadata exclusion test
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
  - `python -m pytest tests/test_agent_runtime.py -q`
- result: pass (`7/7`; `14/14`)
- authority impact: no expansion. Selected LLM tool surface is intersected with `MissionAuthorityEnvelope.allowed_tools`, and memory-not-authority checks run before and after frame build.
- secrets impact: no prompt body or secret material is placed in result metadata or trace payloads by this seam.
- deferrals opened or closed:
  - `P-C-RUNTIME-01-DECISIONFRAME-DEFER` is now eligible for closure after Wave 4 because a real runtime caller exists.
- safe to continue: yes

### 4.1-4.2 - Wire decision-frame cache

- task id: 4.1, 4.2
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/llm_decision_frame_cache.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: Added deterministic evidence-set and tool-surface hashes over sanitized compact inputs. The runtime now calls `_build_decision_frame_cached(...)` when a locked `ContextCacheKey` is available or can be safely derived. The composite inputs use `mission_hot_hash`, `authority_hash`, `evidence_set_hash`, and `tool_surface_hash`; no slot uses `envelope.id`, `"v1"`, or partial keys.
- tests added or updated:
  - decision-frame cache wrapper recording test
  - no `envelope.id` / `"v1"` decision-frame cache-key test
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
  - `python -m pytest tests/perf/test_context_cache_key_builder.py tests/perf/test_context_cache_runtime_closure_property.py -q`
  - `python -m pytest tests/perf/test_context_cache_runtime_integration.py tests/perf/test_context_cache_structural_guards.py -q`
- result: pass (`7/7`; `30/30`; `20/20`)
- authority impact: no expansion; authority hash is part of the frame-cache composite.
- secrets impact: evidence and tool hashes use compact sanitized refs only.
- deferrals opened or closed:
  - closed by implementation evidence: `P-C-RUNTIME-01-DECISIONFRAME-DEFER`
- safe to continue: yes

### 5.1-5.2 - Wire frame budget

- task id: 5.1, 5.2
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/model_contract.py`
  - `sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/token_budget_governor.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: Frame-budget enforcement now uses `_enforce_frame_budget(...)` around the real cached frame builder when the seam is enabled. The concrete budget source is the injected `UserModelContract.context_budget_policy.max_decision_frame_tokens`. This spec does not call action or mission token-budget enforcement.
- tests added or updated:
  - recording token-budget governor wrapper test
  - real `TokenBudgetGovernor` oversized-frame rejection test
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
- result: pass (`7/7`)
- authority impact: none.
- secrets impact: budget metadata contains counts and reason tags only.
- correction note: Added `_DecisionFrameBudgetCompressor` so the real governor can reject oversized `LLMDecisionFrame` objects without accidentally invoking `ContextCompressor` on the wrong object type. This does not hide compression; it leaves the frame unchanged and lets the governor return a rejected budget decision.
- deferrals opened or closed:
  - closed by implementation evidence: `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`
  - remains open and out of scope: `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`
  - remains open and out of scope: `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`
- safe to continue: yes

### 6.1-6.2 - Wire prompt render cache

- task id: 6.1, 6.2
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/prompt_frame_cache.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: The prompt is rendered only through `_render_prompt_text_cached(frame, mission_id=...)`. The runtime stores `prompt_sha256` and `prompt_token_count`; it does not store prompt text in result metadata, events, receipts, or docs.
- tests added or updated:
  - prompt wrapper recording test
  - raw prompt metadata exclusion test
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
- result: pass (`7/7`)
- authority impact: none.
- secrets impact: prompt body not stored; metadata is hash and token count only.
- deferrals opened or closed:
  - closed by implementation evidence: `P-C-RUNTIME-01-PROMPTRENDER-DEFER`
- safe to continue: yes

### 7.1-7.3 - Wire ModelCallOptimizer planning

- task id: 7.1, 7.2, 7.3
- files read:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/perf/caches/model_call_optimizer.py`
- files changed:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: Added optional `model_call_optimizer` injection. The optimizer is called only after a real `LLMDecisionFrame` exists. The plan is recorded as executable-plan metadata only when the planned model matches the user-selected model; otherwise it is recorded as a recommendation and not as an execution plan. No model execution backend is called.
- tests added or updated:
  - model-plan metadata test
  - optimizer alternative/no-silent-override test
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
- result: pass (`7/7`)
- authority impact: none; model planning grants no tool/action authority.
- secrets impact: model-plan metadata contains IDs, counts, hashes, and rationale tags only.
- deferrals opened or closed:
  - closed by implementation evidence: `P-C-RUNTIME-01-MODELOPT-DEFER`
  - remains open for future backend spec: `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`
- safe to continue: yes

### 8.1-8.3 - Targeted tests

- task id: 8.1, 8.2, 8.3
- files read:
  - `.kiro/specs/sentinel-llm-backed-decision-cycle/tasks.md`
  - `sentinel-control/services/sentinel-core/tests/test_agent_runtime.py`
- files changed:
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- implementation summary: Added targeted unit/integration/structural tests for default-off behavior, frame build metadata, decision-frame cache-key slots, frame-budget wrapper, prompt wrapper, optimizer plan/no-override behavior, no model execution, no raw prompt metadata, no raw secret in the new metadata or trace, and FinalGate continuity.
- tests added or updated:
  - `sentinel-control/services/sentinel-core/tests/test_llm_backed_decision_cycle.py`
- tests run:
  - `python -m pytest tests/test_llm_backed_decision_cycle.py -q`
  - `python -m pytest tests/test_agent_runtime.py -q`
  - `python -m pytest tests/perf/test_scope_guardrails.py -q`
  - `python -m pytest tests/perf/test_context_cache_key_builder.py tests/perf/test_context_cache_runtime_closure_property.py -q`
  - `python -m pytest tests/perf/test_context_cache_runtime_integration.py tests/perf/test_context_cache_structural_guards.py -q`
  - `python -m pytest tests/perf/bench -q`
  - `python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py -q`
- result: pass (`7/7`; `14/14`; `20/20`; `30/30`; `20/20`; `30/30`; not-slow sweep exit 0)
- authority impact: no expansion detected in targeted tests.
- secrets impact: no raw prompt or test secret appears in the new decision-cycle metadata or trace.
- deferrals opened or closed:
  - closed: `P-C-RUNTIME-01-DECISIONFRAME-DEFER`
  - closed: `P-C-RUNTIME-01-PROMPTRENDER-DEFER`
  - closed: `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`
  - closed: `P-C-RUNTIME-01-MODELOPT-DEFER`
  - remains open: `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`
  - remains open: `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`
  - remains open: `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`
- safe to continue: yes
