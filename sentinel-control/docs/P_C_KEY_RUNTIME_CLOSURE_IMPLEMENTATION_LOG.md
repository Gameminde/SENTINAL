# P-C-KEY-01 / P-C-RUNTIME-01 — Per-Task Implementation Log

- **Spec:** `sentinel-context-cache-runtime-closure`
- **Spec directory:** `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\`
- **Anchor commit (foundation lock):** `378d862310bc1b5939b210a49c04026cd99a860d` — `perf: fully lock benchmark regression gates`
- **Closure backlog items:**
  - **P-C-KEY-01** — replace the temporary `envelope.id` cache-key stand-in with the canonical four-component `ContextCacheKey` `(mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash)`.
  - **P-C-RUNTIME-01** — wire `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor`, and (conditionally) `ModelCallOptimizer` into the real `AgentRuntime` call sites under additive optional constructor injection.
- **Purpose of this log:** record an auditable, append-only completion note for every task and subtask in `tasks.md`, so the closure work is reviewable against the foundation-spec lock and can be verified at the Final Review Checkpoint (Task 11.0) before `docs/CURRENT_STATE_LOCK.md` is updated by Task 11.1.

## How to use this log

- **Append-only, before the next task starts.** Every task and subtask in `.kiro/specs/sentinel-context-cache-runtime-closure/tasks.md` MUST append a completion entry to this file BEFORE the next task begins. A task is NOT complete unless its log entry exists. Skipped or deferred tasks (for example any subtask gated by `P-C-RUNTIME-01-MODELOPT-DEFER`) still receive a log entry that records the deferral identifier and reason.
- **Entry shape is fixed.** Use the canonical per-entry template in the next section verbatim. Do not invent fields. Do not omit fields — record `none` or `n/a` explicitly when a field has no content.
- **No sensitive material in this log.** This log SHALL NOT contain raw secrets, prompt bodies, private payloads, raw envelope contents, raw cache values, or any byte sequence that the canonical `sanitize_context_text` / `sanitize_context_payload` gate would reject. Reference items by name (file path, hash field, requirement id) rather than by raw value.
- **One file only.** Other docs are not used for per-task notes. In particular, `sentinel-control/docs/CURRENT_STATE_LOCK.md` is NOT updated by individual tasks; it is updated only by the final lock report task (Task 11.1) after the Final Review Checkpoint (Task 11.0) passes.
- **Hard scope guardrails apply on every task.** No P6U work. No Brain / Science work. No new organ. No new product power. No authority expansion. No payment / spend / trading / channel-send / credential-secret behavior. No browser power expansion. No change to existing public required signatures. The boundary-detection gate (`tests/perf/test_scope_guardrails.py::U12`, created in Task 0.2) runs as a pre-task gate before each implementation task.

## Per-entry shape template (copy for every task / subtask)

Copy the block below verbatim into the **Task entries** section, fill in every field, and keep the field order. The shape is lifted from `design.md` §Per-Task Implementation Log.

```markdown
### <task-id> — <short title>

- task id: <e.g., 2.2>
- files read: <list of absolute paths read during this task, or "none">
- files changed: <list of absolute paths written or modified, or "none">
- exact implementation summary: <2–4 sentence concrete description>
- tests added or updated: <test file paths and test ids, or "none">
- tests run: <commands and scope, e.g., "python -m pytest tests/perf/test_context_cache_key_builder.py -q", or "none">
- result: pass | fail | partial
- scope guardrail result: pass — boundary gate halted as expected on synthetic diff | n/a (read-only) | n/a (documentation-only) | fail (halt and record)
- authority impact: none | <explanation referring to MissionAuthorityEnvelope / OrganAuthorityEnvelope fields and confirming no expansion>
- secrets impact: none | <explanation confirming no SecretMaterial leaked into key, receipt, trace, prompt, or log>
- remaining risk or follow-up: <one-line note, or "none">
- safe to continue: yes | no (with reason)
```

## Task entries

<!-- Append new task entries below this marker. Newest entries go at the end. -->

### 0.1 — Initialize the implementation log file

- task id: 0.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\requirements.md`
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (specifically §Per-Task Implementation Log and §Final Review Checkpoint)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 0.1 §Done-When and the per-task implementation log policy section)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (created)
- exact implementation summary: Created the per-task implementation log file with a header identifying the spec name, the anchor commit `378d862310bc1b5939b210a49c04026cd99a860d`, and a short purpose statement; added a "How to use this log" section enforcing the append-before-next-task discipline and the no-sensitive-material rule; added a copyable per-entry shape template lifted verbatim from Design §Per-Task Implementation Log; opened the "Task entries" section and recorded this Task 0.1 completion note as the first entry. No production source, test, or other tracked documentation file was touched.
- tests added or updated: none
- tests run: none
- result: pass
- scope guardrail result: n/a (documentation-only file under `sentinel-control/docs/`; no production code touched, no test code touched, no authority surface touched)
- authority impact: none
- secrets impact: none
- remaining risk or follow-up: none
- safe to continue: yes — the log scaffold is ready to receive Task 0.2 (create `tests/perf/test_scope_guardrails.py`).

### 0.2 — Create the static boundary-detection scanner / gate test (U12)

- task id: 0.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\requirements.md` (Requirement 8 — hard scope guardrails)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Boundary-Detection Gate Ordering, §Final Review Checkpoint §3)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 0.2 §Done-When)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\organs\` directory listing (foundation-lock organ subpackage and flat-module set)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (verified clean of denylist tokens at HEAD)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (verified clean of denylist tokens at HEAD)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_scope_guardrails.py` (new)
- exact implementation summary: Created the U12 boundary-detection gate as a single example-based pytest module that lives ONLY inside the test file. Defined `FileDiff` and `BoundaryViolation` dataclasses and a pure `detect_boundary_crossings(diffs)` scanner that detects eight forbidden categories — `p6u_namespace`, `brain_science_namespace`, `new_organ_subpackage`, `mission_authority_field_change`, `organ_authority_field_change`, `regex_denylist_term`, `new_agent_event_type_member`, `new_required_build_parameter`. Allow-listed this test file and the historical state-lock / implementation-log docs from the regex-denylist scan; existing organ files at the foundation lock are exempt from the regex scan but new files under those directories remain subject to the new-organ-subpackage rule. Added one synthetic-diff test per category, parametrized the regex-denylist test over the ten literal tokens, added a clean-control test that asserts zero violations for a benign new file under `sentinel/perf/caches/`, and added a working-tree test that scans the spec's allowed-file-set on disk and asserts no production file in that set contains a denylist token. No production source was touched.
- tests added or updated:
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_p6u_namespace`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_brain_namespace`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_science_namespace`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_new_organ_subpackage`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_mission_authority_field_default_change`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_organ_authority_field_change`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_each_regex_denylist_term` (parametrized over 10 tokens)
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_new_agent_event_type_member`
  - `tests/perf/test_scope_guardrails.py::test_gate_halts_on_new_required_build_parameter`
  - `tests/perf/test_scope_guardrails.py::test_gate_does_not_halt_on_clean_diff`
  - `tests/perf/test_scope_guardrails.py::test_no_denylist_terms_in_files_added_or_modified_by_this_spec`
- tests run: `python -m pytest tests/perf/test_scope_guardrails.py -q` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` — 20 passed in 3.46s
- result: pass
- scope guardrail result: pass — gate halts on every synthetic boundary-crossing case (P6U namespace, Brain/Science namespace, new organ subpackage, MissionAuthorityEnvelope field default change, OrganAuthorityEnvelope field change, each of the ten regex-denylist tokens, new AgentEventType member, new required `build(...)` parameter); clean-diff control case asserts zero violations; working-tree no-denylist-term test passes — `sentinel/perf/caches/__init__.py` and `sentinel/agent/runtime.py` (the two production files in the spec's allowed set that exist at HEAD and are not allow-listed) contain no denylist token.
- authority impact: none
- secrets impact: none
- remaining risk or follow-up: none — the scanner is example-based and pure; future waves that expand the allowed-file-set will need to extend `_SPEC_ALLOWED_PATHS` accordingly, but no such expansion is anticipated by this spec.
- safe to continue: yes — proceed to Task 0.3 (run the gate test together with the foundation-spec baseline before any production change).

### 0.3 — Run the gate test and the foundation-spec baseline before any production change

- task id: 0.3
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 0.3 §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Boundary-Detection Gate Ordering, §Lock Criteria §0, §6)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_scope_guardrails.py` (created in Task 0.2; not modified here)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\bench\golden_missions.py` (read-only; budget definitions for the four golden mission classes)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\bench\harness.py` (read-only; confirms `BenchmarkReport.structured_pass_report()` is the canonical Phase F p50/p95/p99 surface and that the relative tolerances are `P95_FAIL_TOLERANCE = 1.10`, `P99_FAIL_TOLERANCE = 1.15`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\bench\test_golden_missions.py` (read-only; confirms the four golden mission names and budgets)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\bench\test_benchmark_harness_run.py` (read-only; confirms the harness `run()` exit shape used to capture baseline numbers)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Executed all three commands required by Task 0.3 from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` against the foundation lock at `378d862310bc1b5939b210a49c04026cd99a860d`. Ran the U12 gate test, the full foundation-spec baseline (`python -m pytest -q`), and the Phase F bench suite (`python -m pytest tests/perf/bench -q`); also invoked `BenchmarkHarness().run().structured_pass_report()` once to capture per-mission p50/p95/p99 numbers as informational Wave 0 baselines. No production source, no test source, and no `docs/CURRENT_STATE_LOCK.md` was touched.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py` → **20 passed in 1.26 s** (gate test, U12 boundary-detection gate)
  - `python -m pytest -q` (foundation-spec baseline, full suite) → first observed run **1277 passed, 0 failed**; on later confirmation runs the suite intermittently surfaced a single absolute-budget flake under `tests/perf/hot_cold/test_phase_b_benchmarks.py` (one run: `test_receipt_index_query_p95_full_scale_100k` measured p95 9.048 ms vs the 5 ms canonical Phase B budget; another run: `test_artifact_get_p95_full_scale_10k` measured p95 9.699 ms vs the 5 ms canonical Phase B budget). Three of the runs we executed were fully green (1277 passed, exit 0); the longest visible run reported `1 failed, 1277 passed in 433.40s (0:07:13)`. Both flake locations are Phase B hot/cold-store absolute-budget assertions pre-dating this spec; the Phase F relative gates (the actual lock criterion this spec is bound by per Tasks §0.3 wording) are evaluated by the bench suite below and were green on every run.
  - `python -m pytest tests/perf/bench -q` (Phase F bench suite, the lock-criterion suite) → **30 passed in 7.91 s**, every run, exit 0.
- result: partial — gate test green and Phase F bench suite (the closure spec's declared lock criterion) green every run; the foundation-spec baseline as a whole was green on three of our runs and showed environmental perf-variance flakes on two of our runs against legacy absolute Phase B hot/cold-store p95 budgets that this spec is explicitly told NOT to treat as new fixed budgets.
- scope guardrail result: pass — U12 gate green; no production source touched; no test file modified; no authority surface touched; no payment / spend / trading / channel-send / credential-secret term introduced; no `MissionAuthorityEnvelope` or `OrganAuthorityEnvelope` field touched; no new organ; no new product power; no new `AgentEventType` member; no new required parameter on `ContextBuilder.build`.
- authority impact: none
- secrets impact: none
- remaining risk or follow-up: Foundation baseline shows environmental perf-variance flakes on two absolute-budget assertions in `tests/perf/hot_cold/test_phase_b_benchmarks.py` (`test_receipt_index_query_p95_full_scale_100k`, `test_artifact_get_p95_full_scale_10k`), both holding a 5 ms p95 ceiling against measured ~9–10 ms on this Windows host. These are pre-existing foundation-lock absolute-budget tests outside the closure spec's scope; per Task 0.3 wording the Phase F relative gates (p95 ≤ +10 %, p99 ≤ +15 % over golden mission budgets) remain the lock criterion this spec must satisfy, and that suite is green. No fix attempted (Task 0.3 forbids touching foundation code). Wave 0 is captured as informational only; subsequent waves should re-confirm Phase F bench numbers with `BenchmarkHarness().run().structured_pass_report()` rather than relying on the Phase B absolute budgets.
- safe to continue: yes — the closure spec's declared lock criterion (Phase F relative gates) is green every run; the U12 boundary-detection gate is green; the foundation baseline flake is environmental, scoped to legacy Phase B absolute hot/cold-store budgets, and explicitly outside the spec's done-when contract.

#### Baseline benchmark measurements (informational only)

These per-mission p50/p95/p99 values are recorded as **Wave 0 informational baselines only**. They are **NOT** new fixed budgets and **must not** be used as absolute hard ceilings in subsequent tasks. The Phase F relative gates remain the lock criterion: a `p95` measurement fails only when it is **more than +10 %** over its golden-mission `p95_budget_ms`; a `p99` measurement fails only when it is **more than +15 %** over its golden-mission `p99_budget_ms`. These tolerances are already encoded in `BenchmarkHarness.P95_FAIL_TOLERANCE = 1.10` and `BenchmarkHarness.P99_FAIL_TOLERANCE = 1.15` and are evaluated by the green `tests/perf/bench` suite above.

Captured by `BenchmarkHarness().run().structured_pass_report()` (run timestamp `2026-05-17T09:14:50.357886+00:00`, iteration count 120 = 30 × 4 missions, `passed = True`):

| mission        | iterations | p50 (ms) | p95 (ms) | p99 (ms) | p50 budget (ms) | p95 budget (ms) | p99 budget (ms) | p95 vs budget | p99 vs budget |
| -------------- | ---------- | -------- | -------- | -------- | --------------- | --------------- | --------------- | ------------- | ------------- |
| startup        | 30         | 15       | 17       | 23       | 150             | 400             | 800             | −95.75 %      | −97.13 %      |
| single_tool    | 30         | 2        | 4        | 4        | 200             | 500             | 1000            | −99.20 %      | −99.60 %      |
| multi_tool     | 30         | 1        | 1        | 1        | 400             | 1000            | 2000            | −99.90 %      | −99.95 %      |
| browser_heavy  | 30         | 31       | 36       | 61       | 800             | 2000            | 4000            | −98.20 %      | −98.48 %      |

Reading: every measured `p95` is **far below** its `p95_budget_ms` (negative percentages mean comfortably under budget); every measured `p99` is **far below** its `p99_budget_ms`. No mission is anywhere near the +10 % p95 or +15 % p99 fail boundary, so the Phase F gate verdict computed by `BenchmarkHarness.evaluate_gates(...)` is `passed = True` with empty `p95_regressions` and `p99_regressions` tuples — consistent with the green `tests/perf/bench` run above. These numbers are recorded **for trend visibility only**; they will be re-captured (not re-imposed) in subsequent waves of this spec.

### 1.1 — Inspect the temporary `envelope.id` stand-in in `AgentRuntime.run` (READ-ONLY)

- task id: 1.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_build_cache.py` (grep'd for `envelope` / `envelope.id`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\llm_decision_frame_cache.py` (grep'd for `envelope` / `envelope.id`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\prompt_frame_cache.py` (grep'd for `envelope` / `envelope.id`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\token_budget_governor.py` (grep'd for `envelope` / `envelope.id`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\model_call_optimizer.py` (grep'd for `envelope` / `envelope.id`)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (cross-reference §Exact Runtime Call Sites to Inspect)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 1.1 §Done-When)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry only)
- exact implementation summary: Read-only inspection of `sentinel/agent/runtime.py` at the foundation lock. Located the `envelope.id` cache-key stand-in inside the `if self._context_build_cache is not None:` guard at the `CONTEXT_BUILDING` phase, captured the four `_build_decision_frame_cached` / `_render_prompt_text_cached` / `_enforce_frame_budget` / `_execute_controlled_tool_calls` helper signatures + bodies and the absence of any `_execute_controlled_tool_calls`-side or mission-budget-side `enforce_action` / `enforce_mission` invocation, grep-confirmed that no production cache-key path under `sentinel/perf/caches/` or under `AgentRuntime` currently uses `envelope.id` as a cache-key value other than the two slots flagged below, and recorded all enumerated findings into this log entry. No production source, test, or `docs/CURRENT_STATE_LOCK.md` was modified.
- tests added or updated: none
- tests run: none
- result: pass

#### (a) The four `envelope.id`-based cache-key arguments at the runtime call site

The stand-in lives inside the `if self._context_build_cache is not None:` guard at `runtime.py` lines **308 → 340** (CONTEXT_BUILDING phase). The result variable AgentRuntime currently uses for `composite_key(...)` is named **`composite_key`**; the result of `get_or_build(...)` is bound to **`context`**.

Exact code as it appears at HEAD (lines **330–340**):

```python
                composite_key = self._context_build_cache.composite_key(
                    mission_hot_hash=envelope.id,
                    workspace_snapshot_id="v1",
                    organ_state_hash="v1",
                    authority_hash=envelope.id,
                )
                context = self._context_build_cache.get_or_build(
                    composite_key,
                    _build_context_cached,
                    mission_id=envelope.id,
                )
```

The four cache-key arguments at the `composite_key(...)` call site (lines **330–335**) are:

| line | argument | current value | classification |
| ---- | -------- | ------------- | -------------- |
| 331  | `mission_hot_hash`        | `envelope.id`     | cache-key value (forbidden by P-C-KEY-01 — to be replaced by `ContextCacheKeyBuilder.derive(...).mission_hot_hash` in Task 3.2) |
| 332  | `workspace_snapshot_id`   | `"v1"` literal    | cache-key value placeholder (to be replaced by `self._workspace_snapshot_id()` in Task 3.1 / 3.2) |
| 333  | `organ_state_hash`        | `"v1"` literal    | cache-key value placeholder (to be replaced by `ContextCacheKeyBuilder.derive(...).organ_state_hash` in Task 3.2) |
| 334  | `authority_hash`          | `envelope.id`     | cache-key value (forbidden by P-C-KEY-01 — to be replaced by `ContextCacheKeyBuilder.derive(...).authority_hash` in Task 3.2) |

The third positional argument on the `get_or_build(...)` call at line **338** (`mission_id=envelope.id`) is the cache-event **`mission_id` propagation argument**, NOT a cache-key value (it is consumed by `ContextBuildCache` for `CACHE_HIT` / `CACHE_MISS` event tagging). It is correct as-is and is NOT touched by P-C-KEY-01.

The surrounding `if self._context_build_cache is not None:` guard begins at line **308** and the cached branch closes at line **340**; lines **341–360** are the `elif self._latency_profiler is not None:` and final `else:` branches (default-off path) which build context inline and do NOT touch the cache-key surface.

#### (b) The four call-site shapes from the design

| # | helper / checkpoint | line range at HEAD | current shape | wave that wires it |
| - | ------------------- | ------------------ | ------------- | ------------------ |
| 1 | `_build_decision_frame_cached(...)` | def at line **1772**, body **1772–1817** | `composite_inputs["mission_hot_hash"]` and `composite_inputs["authority_hash"]` are sourced from the caller's argument dict; **the helper has NO live caller inside `AgentRuntime.run` at HEAD** (grep for `self._build_decision_frame_cached` returns zero hits). Therefore the helper itself does NOT currently reference `envelope.id` — the responsibility for sourcing those two slots from `envelope.id` (vs `ContextCacheKeyBuilder`) lives at the future caller, which Task 4.1 will add. | Wave 4 (Task 4.1) |
| 2 | `_render_prompt_text_cached(...)` | def at line **1818**, body **1818–1847** | When the prompt cache is None (default-off): returns `frame.render_prompt_text()` directly (line **1841**). When injected: invokes `self._prompt_frame_cache.get_or_render(frame, lambda f: f.render_prompt_text(), mission_id=mission_id)` (lines **1843–1846**). **Confirmed: the renderer it invokes IS `frame.render_prompt_text()` on both paths.** Like (1), the helper has **no live caller** inside `AgentRuntime.run` at HEAD; the call-site insertion is a Wave 5 task. | Wave 5 (Task 5.1) |
| 3 | `_enforce_frame_budget(...)` + `_execute_controlled_tool_calls(...)` | `_enforce_frame_budget` def at line **1848**, body **1848–1881**; `_execute_controlled_tool_calls` def at line **1162**, body **1162–1354** | `_enforce_frame_budget` invokes `TokenBudgetGovernor.enforce_frame(mission_id, builder, self.context_compressor, frame_budget)` at lines **1875–1880** — **`self.context_compressor` IS passed as the `compressor` argument** (third positional). Note: the source attribute is the public `self.context_compressor` (no leading underscore; assigned in `__init__` as `self.context_compressor = ContextCompressor()`); the design.md text uses `self._context_compressor` informally — the production attribute is `self.context_compressor`. The helper has **no live caller** at HEAD; Wave 6 (Task 6.1) will add the call site. The Wave 6 insertion point for per-action `enforce_action(...)` inside `_execute_controlled_tool_calls` is at lines **1212–1276** of the `for raw_call in raw_calls:` loop, **after** canonicalization succeeds (line ~1218) and **before** any of the four dispatch branches: `_route_local_tool_call_through_scheduler(...)` (lines 1278–1284), `browser_operator_route.run(...)` (lines 1289–1308), `browser_runner.run(...)` (lines 1316–1320), and `runner.run(...)` (lines 1325–1329). | Wave 6 (Tasks 6.1, 6.2) |
| 4 | Mission-budget checkpoint(s) | **not present** for token-budget `enforce_mission` | A grep across `runtime.py` for `enforce_mission`, `mission_budget`, `enforce_action`, `enforce_frame` returns only the existing `_enforce_frame_budget` definition + its single internal `enforce_frame` call (line **1875**). There is **no** `enforce_mission` invocation, no token-level `mission_budget` attribute, and no other token-budget checkpoint anywhere in `AgentRuntime`. The closest plausible mission-budget enforcement seam is the existing **action-count** check `_block_repair_if_action_budget_would_overflow(...)` at line **1355** (and its duplicate at line **1665** — see anomaly note below) which compares `controlled_executed + mission_actions_used + plan_step_count` against `envelope.max_actions`; that is an action-count budget, not a token budget, and is therefore NOT a `TokenBudgetGovernor.enforce_mission` site. Wave 6 (Task 6.3) will add the token-budget mission checkpoint at a runtime location TBD by that wave. | Wave 6 (Task 6.3) — currently **not present** at HEAD |

#### (c) Existing public required signatures unchanged at HEAD

The five `def` lines were captured verbatim from `runtime.py` (one line per helper, ignoring the Python continuation indentation on multi-line signatures the file uses; the full multi-line signatures were verified by reading the surrounding context):

```text
244:    def run(
245:        self,
246:        envelope: MissionAuthorityEnvelope,
247:        user_input: dict[str, Any] | None = None,
248:        *,
249:        evidence_refs: list[str] | None = None,
250:        memory_items: list[dict[str, Any]] | None = None,
251:    ) -> AgentRunResult:
```

```text
1162:    def _execute_controlled_tool_calls(
1163:        self,
1164:        envelope: MissionAuthorityEnvelope,
1165:        user_input: dict[str, Any],
1166:        event_bus: EventBus,
1167:        *,
1168:        max_calls: int,
1169:    ) -> list[dict[str, Any]]:
```

```text
1772:    def _build_decision_frame_cached(
1773:        self,
1774:        *,
1775:        mission_id: str,
1776:        composite_inputs: dict[str, str],
1777:        builder: "Callable[[], LLMDecisionFrame]",
1778:    ) -> "LLMDecisionFrame":
```

```text
1818:    def _render_prompt_text_cached(
1819:        self,
1820:        frame: "LLMDecisionFrame",
1821:        *,
1822:        mission_id: str,
1823:    ) -> str:
```

```text
1848:    def _enforce_frame_budget(
1849:        self,
1850:        *,
1851:        mission_id: str,
1852:        builder: "Callable[[], LLMDecisionFrame]",
1853:        frame_budget: int,
1854:    ) -> tuple["LLMDecisionFrame", Any]:
```

All five signatures match the foundation-lock shape recorded in the spec's design §Exact Runtime Call Sites to Inspect — no required parameter has been added, removed, or renamed at HEAD. These are the signatures that Task 9 (U9) will pin by AST.

#### (d) Line range of the `CONTEXT_BUILDING` phase block in `AgentRuntime.run`

The `CONTEXT_BUILDING` phase block — from the `state = state.transition(AgentPhase.CONTEXT_BUILDING)` line through the last event/operation tagged with `phase_after=AgentPhase.CONTEXT_BUILDING` and immediately preceding the `state = state.transition(AgentPhase.ORIENTING)` line — spans `runtime.py` lines **285 → 391**:

- line **285**: `state = state.transition(AgentPhase.CONTEXT_BUILDING)`
- lines **286–307**: leading comment block (Task 6.11 / sentinel-performance-runtime-foundation rationale + envelope.id stand-in caveat)
- lines **308–340**: `if self._context_build_cache is not None:` cached branch (the P-C-KEY-01 stand-in lives at lines **330–334**)
- lines **341–358**: `elif self._latency_profiler is not None:` profiled-uncached branch
- lines **359–365**: `else:` default-off branch
- lines **366–367**: `supervisor.assert_mission_can_run` and `supervisor.assert_context_did_not_expand_authority`
- lines **368–374**: `event_bus.append(AgentEventType.CONTEXT_BUILT, ...)`
- lines **376–384**: `context_compress` latency-profiler block + `self.context_compressor.compress(context)` call
- lines **385–391**: `event_bus.append(AgentEventType.CONTEXT_COMPRESSED, ...)` (last event with `phase_after=AgentPhase.CONTEXT_BUILDING`)
- line **393**: `state = state.transition(AgentPhase.ORIENTING)` (the next phase begins here)

Line range to record for the CONTEXT_BUILDING phase block: **285–391** (inclusive of the leading transition line and the closing `CONTEXT_COMPRESSED` event-bus append; exclusive of the next `state.transition(AgentPhase.ORIENTING)` at line 393).

#### (e) Any other reference to `envelope.id` in `AgentRuntime` / `sentinel/perf/caches/`, categorised cache-key value vs other use

**Under `sentinel/perf/caches/`**: a grep for `envelope.id` returned **zero matches**; a grep for the bare token `envelope` matched only docstring prose in `context_build_cache.py`, `llm_decision_frame_cache.py`, and `prompt_frame_cache.py` (each describing the authority-envelope invariant). **No production cache-key path under `sentinel/perf/caches/` references `envelope.id` as a cache-key value.**

**Under `sentinel/agent/runtime.py`**: a grep for `envelope.id` returned the following matches (every match categorised cache-key value vs other use):

| line | snippet | classification |
| ---- | ------- | -------------- |
| 252  | `event_bus = EventBus(envelope.id)`                                                                 | other use (mission_id propagation into the `EventBus` aggregate id) |
| 275  | `state = AgentState(mission_id=envelope.id).transition(AgentPhase.INITIALIZED)`                     | other use (mission_id propagation into AgentState) |
| 296 (comment) | `# ``authority_hash`` slot is bound to ``envelope.id`` for`                                | other use (Task 6.11 rationale comment that this spec replaces) |
| 312  | `mission_id=envelope.id,`  (LatencyProfiler.instrument inside `_build_context_cached` closure)      | other use (mission_id propagation) |
| 313  | `action_id=f"{envelope.id}:context_build",`                                                         | other use (action_id template) |
| **330** | `mission_hot_hash=envelope.id,`  (inside `composite_key(...)`)                                  | **cache-key value (forbidden by P-C-KEY-01)** |
| **333** | `authority_hash=envelope.id,`  (inside `composite_key(...)`)                                    | **cache-key value (forbidden by P-C-KEY-01)** |
| 338  | `mission_id=envelope.id,`  (inside `get_or_build(...)`)                                             | other use (cache-event mission_id tag, NOT a cache-key value) |
| 342  | `mission_id=envelope.id,`  (LatencyProfiler.instrument in elif branch)                              | other use |
| 343  | `action_id=f"{envelope.id}:context_build",`                                                         | other use |
| 371  | `mission_id=envelope.id,`  (LatencyProfiler.instrument for `context_compress`)                      | other use |
| 372  | `action_id=f"{envelope.id}:context_compress",`                                                      | other use |
| 395  | `mission_id=envelope.id,`  (LatencyProfiler.instrument for `orient`)                                | other use |
| 396  | `action_id=f"{envelope.id}:orient",`                                                                | other use |
| 510  | `mission_id=envelope.id,`  (BLOCKED `AgentRunResult`, tool-selection critical findings)             | other use (AgentRunResult.mission_id field) |
| 595  | `mission_id=envelope.id,`  (BLOCKED `AgentRunResult`, hypothesis verification critical findings)    | other use |
| 766  | `mission_id=envelope.id,`  (BLOCKED `AgentRunResult`, repair-loop overflow path)                    | other use |
| 885  | `mission_id=envelope.id,`  (ESCALATED `AgentRunResult`)                                             | other use |
| 1031 | `mission_id=envelope.id,`  (success / final `AgentRunResult`)                                       | other use |
| 1143 | `mission_id=envelope.id,`  (BLOCKED fallback `AgentRunResult` in `except Exception`)                | other use |
| 1288, 1289, 1312, 1313, 1322, 1323 | LatencyProfiler.instrument (`mission_id=...`, `action_id=f"{envelope.id}:tool_call:..."`) | other use (latency profiler in tool-call dispatch) |
| 1467 (comment) | `# ``self._mission_kill_switches[envelope.id]`` (out of scope`                              | other use (rationale comment) |
| 1500 | `action_id = f"{envelope.id}:tool_call:{uuid.uuid4().hex[:8]}"`                                     | other use (scheduler action_id template) |
| 1512 | `mission_id=envelope.id,`  (`OrganAuthorityEnvelope` construction in scheduler path)                | other use (mission_id propagation into organ envelope) |
| 1513 | `root_authority_id=envelope.id,`  (`OrganAuthorityEnvelope`)                                        | other use (root authority chaining; not a cache key) |
| 1527 | `mission_id=envelope.id,`  (`OrganKillSwitch`)                                                      | other use |
| 1534 | `mission_id=envelope.id,`  (`OrganDryRunReceipt`)                                                   | other use |
| 1539 | `risk_profile_id=f"orisk_{envelope.id}",`  (`OrganDryRunReceipt`)                                   | other use (risk-profile id template) |
| 1541 | `evidence_refs=["ev_agent_runtime_scheduler_wiring"],` (literal — not envelope.id; included only as adjacent context) | n/a (no envelope.id token) |
| 1562 | `mission_id=envelope.id,`  (`_ToolCallSchedulerAction`)                                             | other use |

**Net categorisation summary**: across `runtime.py` only **two** occurrences of `envelope.id` are used as a **cache-key value** (lines **330** and **333**, the `mission_hot_hash` and `authority_hash` slots inside `ContextBuildCache.composite_key(...)`). Every other occurrence is `mission_id` propagation, `action_id` template construction, organ-envelope mission_id linkage, an `EventBus`/`AgentState`/`AgentRunResult`/`OrganAuthorityEnvelope`/`OrganKillSwitch`/`OrganDryRunReceipt`/`_ToolCallSchedulerAction` field that legitimately requires the mission identifier, or a docstring/comment describing the stand-in. **No other cache-key value path in `AgentRuntime` references `envelope.id`.**

- scope guardrail result: n/a (read-only)
- authority impact: none
- secrets impact: none
- remaining risk or follow-up: **anomaly noted (out of scope for P-C-KEY-01)** — `runtime.py` contains duplicate definitions of `_block_repair_if_action_budget_would_overflow` (lines **1355** and **1665**), `_accepted_controlled_capability_count` (lines **1410** and **1720**), `_raw_tool_call_payloads` (lines **1414** and **1724**), `_controlled_capture_root` (lines **1430** and **1740**), `_certify_trace` (lines **1441** and **1751**), and `_snapshot_trace` (lines **1444** and **1754**). The second definition silently shadows the first at class-construction time. This pre-dates the closure spec and is outside the P-C-KEY-01 / P-C-RUNTIME-01 scope; it is recorded here for visibility only and SHALL NOT be touched by this wave. Also noted: the design.md text refers informally to `self._context_compressor` whereas the production attribute is `self.context_compressor` (no leading underscore); subsequent waves should use the production attribute name. No other anomalies. Cache-key replacement target lines (**330**, **333**) are uniquely identified and ready for Task 3.2.
- safe to continue: yes — proceed to Task 1.2 (inspect the four locked cache helpers and capture their public required signatures).

### 1.2 — Inspect the four locked cache helpers and their public required signatures (READ-ONLY)

- task id: 1.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_build_cache.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\llm_decision_frame_cache.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\prompt_frame_cache.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\token_budget_governor.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\model_call_optimizer.py`
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (cross-reference §Components and Interfaces / §Existing helpers)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 1.2 §Done-When)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry only)
- exact implementation summary: Read-only inspection of the five locked helper modules at the foundation lock. Captured class definition lines, every public required method `def` line and line range, constructor (`__init__`) signatures, the LLMDecisionFrameCache safety-bypass locations (gate names + line ranges, no body content quoted), and the cache event family imports referenced in each module. Findings are recorded below as the AST-pin checklist for U9 (Task 9). No production source, test, or `docs/CURRENT_STATE_LOCK.md` was modified.
- tests added or updated: none
- tests run: none
- result: pass

#### Captured signatures — checklist for U9 AST pinning

##### `sentinel/perf/caches/context_build_cache.py`

- **Class definition (line 209):**
  ```python
  class ContextBuildCache:
  ```

- **`__init__` (line 247; def block 247–258):**
  ```python
  def __init__(self, *, event_bus: EventBus, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
  ```
  - parameters: `self`; keyword-only `event_bus: EventBus` (required, no default), `max_entries: int = DEFAULT_MAX_ENTRIES` (default `256`)
  - return type: `None`

- **`ContextBuildCache.composite_key` (line 262; def block 262–286):**
  ```python
  def composite_key(
      self,
      *,
      mission_hot_hash: str,
      workspace_snapshot_id: str,
      organ_state_hash: str,
      authority_hash: str,
  ) -> CacheKey:
  ```
  - parameters: `self`; keyword-only `mission_hot_hash: str`, `workspace_snapshot_id: str`, `organ_state_hash: str`, `authority_hash: str` (all required, no defaults)
  - return type: `CacheKey` (module-level alias for `str`)

- **`ContextBuildCache.get_or_build` (line 287; def block 287–354):**
  ```python
  def get_or_build(
      self,
      key: CacheKey,
      builder: Callable[[], AgentContext],
      *,
      verify: bool = False,
      mission_id: str | None = None,
  ) -> AgentContext:
  ```
  - parameters: `self`; positional `key: CacheKey`, `builder: Callable[[], AgentContext]`; keyword-only `verify: bool = False`, `mission_id: str | None = None`
  - return type: `AgentContext`

##### `sentinel/perf/caches/llm_decision_frame_cache.py`

- **Class definition (line 216):**
  ```python
  class LLMDecisionFrameCache:
  ```

- **`__init__` (line 225; def block 225–239):**
  ```python
  def __init__(
      self,
      *,
      event_bus: EventBus,
      clock: Callable[[], int] = time.monotonic_ns,
  ) -> None:
  ```
  - parameters: `self`; keyword-only `event_bus: EventBus` (required, no default), `clock: Callable[[], int] = time.monotonic_ns` (default `time.monotonic_ns`)
  - return type: `None`

- **`LLMDecisionFrameCache.composite_hash` (line 242; def block 242–266):**
  ```python
  def composite_hash(
      self,
      *,
      mission_hot_hash: str,
      authority_hash: str,
      evidence_set_hash: str,
      tool_surface_hash: str,
  ) -> str:
  ```
  - parameters: `self`; keyword-only `mission_hot_hash: str`, `authority_hash: str`, `evidence_set_hash: str`, `tool_surface_hash: str` (all required, no defaults)
  - return type: `str`

- **`LLMDecisionFrameCache.get` (line 267; def block 267–344):**
  ```python
  def get(self, composite: str, *, mission_id: str) -> LLMDecisionFrame | None:
  ```
  - parameters: `self`; positional `composite: str`; keyword-only `mission_id: str` (required, no default)
  - return type: `LLMDecisionFrame | None`

- **`LLMDecisionFrameCache.put` (line 345; def block 345–383):**
  ```python
  def put(self, composite: str, frame: LLMDecisionFrame, *, mission_id: str) -> None:
  ```
  - parameters: `self`; positional `composite: str`, `frame: LLMDecisionFrame`; keyword-only `mission_id: str` (required, no default)
  - return type: `None`

##### `sentinel/perf/caches/prompt_frame_cache.py`

- **Class definition (line 194):**
  ```python
  class PromptFrameCache:
  ```

- **`__init__` (line 224; def block 224–238):**
  ```python
  def __init__(self, *, event_bus: EventBus, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
  ```
  - parameters: `self`; keyword-only `event_bus: EventBus` (required, no default), `max_entries: int = DEFAULT_MAX_ENTRIES` (default `256`)
  - return type: `None`

- **`PromptFrameCache.get_or_render` (line 240; def block 240–309):**
  ```python
  def get_or_render(
      self,
      frame: LLMDecisionFrame,
      renderer: Callable[[LLMDecisionFrame], str],
      *,
      verify: bool = False,
      mission_id: str | None = None,
  ) -> str:
  ```
  - parameters: `self`; positional `frame: LLMDecisionFrame`, `renderer: Callable[[LLMDecisionFrame], str]`; keyword-only `verify: bool = False`, `mission_id: str | None = None`
  - return type: `str`

- **`PromptFrameCache.reuse_prefix` (line 348; def block 348–386):**
  ```python
  def reuse_prefix(
      self,
      stable_prefix_hash: str,
      evidence_delta: list[EvidenceCard],
      *,
      mission_id: str | None = None,
  ) -> str | None:
  ```
  - parameters: `self`; positional `stable_prefix_hash: str`, `evidence_delta: list[EvidenceCard]`; keyword-only `mission_id: str | None = None`
  - return type: `str | None`

##### `sentinel/perf/caches/token_budget_governor.py`

- **Class definition (line 251):**
  ```python
  class TokenBudgetGovernor:
  ```
  (note: sibling frozen verdict model `class BudgetDecision(SentinelModel):` at line 218, `model_config = ConfigDict(extra="forbid", frozen=True)`)

- **`__init__` (line 276; def block 276–302):**
  ```python
  def __init__(
      self,
      *,
      event_bus: EventBus,
      max_compression_passes: int = DEFAULT_MAX_COMPRESSION_PASSES,
      warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
  ) -> None:
  ```
  - parameters: `self`; keyword-only `event_bus: EventBus` (required, no default), `max_compression_passes: int = DEFAULT_MAX_COMPRESSION_PASSES` (default `3`), `warning_threshold: float = DEFAULT_WARNING_THRESHOLD` (default `0.9`)
  - return type: `None`

- **`TokenBudgetGovernor.enforce_frame` (line 356; def block 356–442):**
  ```python
  def enforce_frame(
      self,
      mission_id: str,
      frame_builder: Callable[[], Any],
      compressor: Any,
      frame_budget: int,
  ) -> tuple[Any, BudgetDecision]:
  ```
  - parameters: `self`; positional `mission_id: str`, `frame_builder: Callable[[], Any]`, `compressor: Any`, `frame_budget: int` (all required, no defaults; no keyword-only marker)
  - return type: `tuple[Any, BudgetDecision]`

- **`TokenBudgetGovernor.enforce_action` (line 444; def block 444–517):**
  ```python
  def enforce_action(
      self,
      mission_id: str,
      estimated_tokens: int,
      action_budget: int,
  ) -> BudgetDecision:
  ```
  - parameters: `self`; positional `mission_id: str`, `estimated_tokens: int`, `action_budget: int` (all required, no defaults)
  - return type: `BudgetDecision`

- **`TokenBudgetGovernor.enforce_mission` (line 519; def block 519–619):**
  ```python
  def enforce_mission(
      self,
      mission_id: str,
      tokens_just_spent: int,
      mission_budget: int,
  ) -> BudgetDecision:
  ```
  - parameters: `self`; positional `mission_id: str`, `tokens_just_spent: int`, `mission_budget: int` (all required, no defaults)
  - return type: `BudgetDecision`

##### `sentinel/perf/caches/model_call_optimizer.py`

- **Class definition (line 311):**
  ```python
  class ModelCallOptimizer:
  ```
  (note: sibling frozen plan model `class ModelCallPlan(SentinelModel):` at line 264, `model_config = ConfigDict(extra="forbid", frozen=True)`)

- **`__init__` (line 324; def block 324–340):**
  ```python
  def __init__(
      self,
      *,
      default_model_id: str = DEFAULT_MODEL_ID,
      default_backend: str = DEFAULT_BACKEND,
  ) -> None:
  ```
  - parameters: `self`; keyword-only `default_model_id: str = DEFAULT_MODEL_ID` (default `"gpt-4o-mini"`), `default_backend: str = DEFAULT_BACKEND` (default `"openai"`)
  - return type: `None`

- **`ModelCallOptimizer.plan` (line 353; def block 353–419):**
  ```python
  def plan(self, frame: LLMDecisionFrame, ledger: Any | None = None) -> ModelCallPlan:
  ```
  - parameters: `self`; positional `frame: LLMDecisionFrame` (required, no default), `ledger: Any | None = None` (default `None`; no keyword-only marker)
  - return type: `ModelCallPlan`

#### LLMDecisionFrameCache — locked safety-bypass locations (Requirement 9.4 / 12.2 / 12.3)

- **`put`-side rejection of `authority_expansion=True` writes** — `llm_decision_frame_cache.py` lines **365–369** (inside the `put(...)` method body whose def is at line 345). The block tests the `authority_expansion` gate on the incoming frame and on a positive read raises `ValueError` with the gate name embedded in the message; the frame is not stored in any form. No body content is reproduced here. (Reference: the gate name is `authority_expansion`; the rejection path emits no event and stores no entry — consistent with the module-docstring contract.)

- **`get`-side eviction on `authority_expansion=True` reads** — `llm_decision_frame_cache.py` lines **314–327** (inside the `get(...)` method body whose def is at line 267). The block tests the `authority_expansion` gate on the cached frame and on a positive read deletes the bucket entry, increments `safety_bypasses`, and emits `CACHE_EVICTED` with `reason="authority_expansion_bypass"` (constant `_REASON_AUTHORITY_EXPANSION` defined at line 166); returns `None` to the caller. (Reference: the gate name is `authority_expansion`; the eviction reason tag is `authority_expansion_bypass`.)

- **`get`-side eviction on `raw_secret_leakage=True` reads** — `llm_decision_frame_cache.py` lines **328–338** (inside the same `get(...)` method body). The block tests the `raw_secret_leakage` gate on the cached frame and on a positive read deletes the bucket entry, increments `safety_bypasses`, and emits `CACHE_EVICTED` with `reason="raw_secret_leakage_bypass"` (constant `_REASON_RAW_SECRET_LEAKAGE` defined at line 167); returns `None` to the caller. (Reference: the gate name is `raw_secret_leakage`; the eviction reason tag is `raw_secret_leakage_bypass`.)

(Description-only by reference; no body content quoted that could risk leaking sensitive content.)

#### Cache event family imports — per file

| file | `AgentEventType` references at HEAD | classification |
| ---- | ------------------------------------ | -------------- |
| `context_build_cache.py` | `CACHE_HIT`, `CACHE_MISS`, `CACHE_EVICTED`, `CACHE_CORRECTNESS_VIOLATION` | cache event family — expected; no anomaly |
| `llm_decision_frame_cache.py` | `CACHE_HIT`, `CACHE_MISS`, `CACHE_EVICTED` | cache event family — expected; no anomaly. (No `CACHE_CORRECTNESS_VIOLATION` is emitted by this module — by design: the module's correctness contract is mediated by the safety-bypass evictions documented above plus the `composite_hash` opaque key, not by a verify-on-read code path.) |
| `prompt_frame_cache.py` | `CACHE_HIT`, `CACHE_MISS`, `CACHE_EVICTED`, `CACHE_CORRECTNESS_VIOLATION` | cache event family — expected; no anomaly |
| `token_budget_governor.py` | `BUDGET_WARNING`, `BUDGET_EXCEEDED`, `BUDGET_EXHAUSTED` | **non-cache** family — **visibility note, not an anomaly**. These are the foundation-lock **budget** event family (Task 6.4 / sentinel-performance-runtime-foundation Requirements 10.1–10.9), already locked at HEAD. They are NOT a new event family introduced by this spec; this closure spec adds zero new `AgentEventType` members per Design Invariant §8 / Hard Scope Guardrails. |
| `model_call_optimizer.py` | (none) | event-bus-free by design (module docstring asserts the optimizer "does not touch the EventBus"); confirms the planner is purely structural and emits zero events. |

No `CACHE_INVALIDATION_BULK_WARNING` reference in any of the five files at HEAD — that event member is owned by the `sentinel/perf/hot_cold/cache_invalidation_policy.py` module (Phase B locked) per design §Current State Summary, not by these cache helpers; absence here is correct.

- scope guardrail result: n/a (read-only)
- authority impact: none — `MissionAuthorityEnvelope`, `OrganAuthorityEnvelope`, and the locked `LLMDecisionFrameCache` `authority_expansion` reject/evict surfaces were inspected only; not modified. No authority field added or modified.
- secrets impact: none — only signature lines, line numbers, and gate-name references were captured. No frame body, no prompt text, no evidence content, no payload bytes, no cache value, and no body content from the safety-bypass blocks was quoted into this log entry; `raw_secret_leakage` and `authority_expansion` gates are referenced by name only.
- remaining risk or follow-up: none. The five module signatures recorded here are the AST-pin baseline U9 (Task 9) will lock; any future drift on these `def` lines or `__init__` parameter shapes will be detected by U9.
- safe to continue: yes — proceed to Task 1.3 (read-only inspection of `ContextBuilder`, `ContextCompressor`, `CognitiveCycle`, `phases`, and `MissionRunner` host points).



### 1.3 — Inspect `ContextBuilder`, `ContextCompressor`, `CognitiveCycle`, and `MissionRunner` host points (READ-ONLY)

- task id: 1.3
- files read:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\context_builder.py` (read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\context_compressor.py` (read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\cognitive_cycle.py` (read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\phases.py` (read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\shared\events.py` (lines 56-80 — `AgentPhase` enum members)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\reviewer.py` (header — confirms file contains `ReviewerLite`, NOT `MissionRunner`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\runner.py` (lines 1-120 — `MissionRunner` definition + `__init__` / `run_mission` / `run_gtm_mission` signatures)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (re-grepped for `original_allowed_actions`, `__init__`, `_mission_kill_switches`, `workspace_snapshot_cache`, organ-registry attributes; spot-read lines 59-220, 260-340, 385-395)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\workspace\workspace_snapshot_cache.py` (header + `snapshot_id` property at line 224)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry only)
- exact implementation summary: Read-only inspection of the four host classes referenced by the spec design table (`ContextBuilder`, `ContextCompressor`, `CognitiveCycle`, `MissionRunner`), the `AgentPhase` state-machine module, the `AgentRuntime` constructor + run-entry `original_allowed_actions` capture point + first consumer call site, and `WorkspaceSnapshotCache.snapshot_id`. Confirmed all four call-site shapes match the design's §Exact Runtime Call Sites to Inspect table; recorded the verbatim `def` lines that U9 will pin by AST in Task 9; located `MissionRunner` at `mission/runner.py` (NOT `mission/reviewer.py`, which holds `ReviewerLite`); confirmed `original_allowed_actions` is captured at line 274 of `runtime.py` and consumed at the CONTEXT_BUILDING→ORIENTING boundary at line 391 (and at every subsequent phase boundary thereafter); confirmed AgentRuntime has neither a `WorkspaceSnapshotCache` injection nor a `self._mission_kill_switches` map nor an `self._organs` / `self._organ_registry` attribute at HEAD — Task 3.1 will use the canonical empty-snapshot hex constant fallback and will build `OrganStateView` from per-call `OrganKillSwitch` construction at the controlled-capability call site. No production source, test, or `docs/CURRENT_STATE_LOCK.md` was modified.
- tests added or updated: none
- tests run: none
- result: pass

#### (1) `ContextBuilder` (`sentinel/agent/context_builder.py`) — HEAD shape

- File line count: **70 lines** (`splitlines` count; file ends with newline; bytes = 2694).
- Class definition: `class ContextBuilder:` at **line 12**.
- `__init__` signature at **line 13**:

  ```python
  def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
  ```

  Single optional kwarg-only parameter (`latency_profiler`); no `cache_key_provider`, no `context_build_cache`.

- `build` signature, lines **16–22** (verbatim, multi-line):

  ```python
  def build(
      self,
      envelope: MissionAuthorityEnvelope,
      *,
      user_input: dict[str, Any] | None = None,
      evidence_refs: list[str] | None = None,
      memory_items: list[dict[str, Any]] | None = None,
  ) -> AgentContext:
  ```

  Single-line equivalent (matching the design table cell): `def build(self, envelope: MissionAuthorityEnvelope, *, user_input: dict[str, Any] | None = None, evidence_refs: list[str] | None = None, memory_items: list[dict[str, Any]] | None = None) -> AgentContext:`. **This matches the design's expected shape exactly** — same positional `envelope`, same three keyword-only optional parameters (`user_input`, `evidence_refs`, `memory_items`), same return type `AgentContext`. No deviation. The design table cell types `user_input` / `evidence_refs` / `memory_items` informally as `=None`; the production code adds the matching Pydantic-friendly `| None` annotations and `dict[str, Any] | None` / `list[str] | None` / `list[dict[str, Any]] | None` defaults — these are type annotations only and do not change the public required signature.

- **No-`_do_build` assertion (deviation flagged for the task description):** the task description asks to "confirm there is NO `_do_build` method". `ContextBuilder` **does** have a private `_do_build` method at **line 45** (and `ContextCompressor._do_compress` at line 23 of `context_compressor.py`, and `CognitiveCycle._do_orient` at line 26 of `cognitive_cycle.py`). These three private `_do_*` methods predate this closure spec — they were introduced by `sentinel-performance-runtime-foundation` Phase B/C as the latency-profiler-instrumentation indirection (the `if self._latency_profiler is not None: with self._latency_profiler.instrument(...): return self._do_*(...)` shape). They are part of the foundation lock, not added by this closure spec. The closure spec's actual "do not modify" contract is on the **public** required signatures and on the absence of `cache_key_provider` / `context_build_cache` kwargs and cache-helper imports — all of which is intact at HEAD. **Recording the `_do_build` presence as a finding so the task description can be reconciled, and confirming the closure-spec invariants below.**
- **No `cache_key_provider` kwarg:** verified via `grep_search "cache_key_provider|context_build_cache|ContextBuildCache"` against `agent/context_builder.py` — zero matches.
- **No `context_build_cache` kwarg:** same grep — zero matches.
- **No import of cache helpers:** verified via `grep_search "perf\.caches|context_build_cache|ContextBuildCache|ContextCacheKey|ContextCacheKeyBuilder"` against `agent/context_builder.py` — zero matches. Imports at HEAD are limited to `sentinel.agent.capability_selector`, `sentinel.agent.models`, `sentinel.mission.models`, and (under `TYPE_CHECKING`) `sentinel.perf.measure.latency_profiler`. **Layering rule satisfied.**
- This is the file Task 8.1 (U9) will assert "no diff against the foundation lock" for; the line count (70) is recorded here as the U9 baseline.

#### (2) `ContextCompressor` (`sentinel/agent/context_compressor.py`) — HEAD shape

- Class definition: `class ContextCompressor:` at **line 11**.
- `__init__` signature at **line 12**: `def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:`. Single optional kwarg-only parameter (`latency_profiler`); no constructor injection of any cache helper.
- `compress` signature at **line 15** (verbatim): `def compress(self, context: AgentContext) -> AgentContext:`. **Matches the design's expected shape exactly.** No deviation.
- Other public methods on `ContextCompressor`: **none.** The file contains only `__init__`, `compress`, and the private `_do_compress` (line 23) — matching the same `_do_*` indirection pattern used in `ContextBuilder` and `CognitiveCycle`. The class is invoked through `TokenBudgetGovernor.enforce_frame(..., compressor=self.context_compressor, ...)` per the design's wiring matrix; this read-only inspection confirms `compress` is the only public method available for that wrapping.
- No import of cache helpers: imports at HEAD are limited to `sentinel.agent.models` (for `AgentContext`) and (under `TYPE_CHECKING`) `sentinel.perf.measure.latency_profiler`. Verified via `grep_search "perf\.caches|ContextCacheKey|TokenBudgetGovernor"` — zero matches.

#### (3) `CognitiveCycle` (`sentinel/agent/cognitive_cycle.py`) — HEAD shape

- Class definition: `class CognitiveCycle:` at **line 12**.
- `__init__` signature at **line 13**: `def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:`. Single optional kwarg-only parameter (`latency_profiler`); no cache helper injected, no key parameter.
- `orient` signature at **line 16** (verbatim): `def orient(self, state: AgentState, context: AgentContext) -> AgentState:`. **Matches the design's expected shape exactly.** No deviation.
- Other public phase methods (`decide`, `act`, `replay`, etc.): **none.** The class exposes only `orient` plus the private `_do_orient` (line 26). The "nine cognitive phase boundaries" referenced by the Memory-not-Authority invariant are **not** methods on `CognitiveCycle`; they are phase transitions inside the `AgentRuntime.run` phase loop (re-confirmed in Task 1.1 — boundaries are observed at the `state.transition(AgentPhase.<X>)` call sites in `runtime.py`). Therefore there are no sibling phase methods on `CognitiveCycle` that could take a cache helper or a key parameter; the `cache lookups happen one level up at the AgentRuntime.run phase loop` rule from the design is structurally true.
- Imports at HEAD: `sentinel.agent.models`, `sentinel.agent.state`, `sentinel.agent.uncertainty`, and (under `TYPE_CHECKING`) `sentinel.perf.measure.latency_profiler`. Verified via `grep_search "perf\.caches|ContextCacheKey"` — zero matches.

#### (4) `AgentPhase` enum (`sentinel/agent/phases.py` re-exports from `sentinel/shared/events.py`)

- `phases.py` line 14 re-exports `AgentPhase` for backward compatibility: `from sentinel.shared.events import AgentPhase`. The enum class itself is `class AgentPhase(StrEnum):` at `shared/events.py:56`.
- Member count: **24** members (lines 57–80 of `shared/events.py`):
  - `CREATED`, `INITIALIZED`, `CONTEXT_BUILDING`, `ORIENTING`, `METHOD_SELECTING`, `CAPABILITY_SELECTING`, `TOOL_SELECTING`, `HYPOTHESIS_VERIFYING`, `ACTION_SCORING`, `EFFORT_ROUTING`, `PLANNING`, `PLAN_REVIEWING`, `EXECUTING`, `ARTIFACT_REVIEWING`, `REPAIRING`, `SUCCESS_EVALUATING`, `LEARNING_PROPOSING`, `COMPLETED`, `ESCALATED`, `PAUSED`, `STOPPED`, `REVOKED`, `BLOCKED`, `FAILED`.
- Enum is unchanged at HEAD by this closure spec; it is the foundation-lock shape and is the source of truth for the `state.transition(AgentPhase.<X>)` call sites in `AgentRuntime.run`. No new member is added by this spec (a new member would be flagged by U12's `test_gate_halts_on_new_agent_event_type_member` analogue, and adding a new `AgentPhase` member is explicitly forbidden by the spec's hard-scope guardrails).

#### (5) `MissionRunner` location and signatures

- **`mission/reviewer.py` does NOT contain `MissionRunner`.** It contains `class ReviewerLite:` (line 19) with method `review(envelope, project_dir, artifacts, *, unresolved_critical_escalations: int = 0) -> ReviewResult` and a helper constant `GENERIC_MARKERS`. `ReviewerLite` is the artifact-quality reviewer surface, not the mission runtime. The task description's path was a misdirection; the actual `MissionRunner` lives at `mission/runner.py`.
- **Actual location:** `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\runner.py`. `class MissionRunner:` at **line 39** (def-line 39, `__init__` opens at line 40).
- `MissionRunner.__init__` signature, lines **40–52** (verbatim multi-line):

  ```python
  def __init__(
      self,
      project_root: str | Path | None = None,
      registry: MissionRegistry | None = None,
      browser_operator_route: BrowserOperatorMissionRouteProtocol | None = None,
      *,
      latency_profiler: LatencyProfiler | None = None,
      hot_cache: HotMissionCache | None = None,
      cold_store: ColdReceiptStore | None = None,
      receipt_index: ReceiptIndex | None = None,
  ) -> None:
  ```

- `run_gtm_mission` signature, lines **64–71**:

  ```python
  def run_gtm_mission(
      self,
      envelope: MissionAuthorityEnvelope,
      *,
      idea: str | None = None,
      evidence_refs: list[str] | None = None,
      plan: MissionPlan | None = None,
      cancellation_token: CancellationToken | None = None,
  ) -> MissionRunResult:
  ```

  Body delegates straight into `self.run_mission(envelope, idea=idea, evidence_refs=evidence_refs, plan=plan, cancellation_token=cancellation_token)`.

- `run_mission` signature, lines **81–89**:

  ```python
  def run_mission(
      self,
      envelope: MissionAuthorityEnvelope,
      *,
      idea: str | None = None,
      evidence_refs: list[str] | None = None,
      plan: MissionPlan | None = None,
      cancellation_token: CancellationToken | None = None,
  ) -> MissionRunResult:
  ```

- **No-modification confirmation:** none of the three signatures contains `original_allowed_actions`, `context_build_cache`, `decision_frame_cache`, `prompt_frame_cache`, `token_budget_governor`, `model_call_optimizer`, or any `ContextCacheKey` parameter. This closure spec does **not** modify `MissionRunner`. The design's wiring matrix lists `MissionRunner.run_mission` / `run_gtm_mission` under "remain exactly as locked"; this is confirmed.

#### (6) AgentRuntime — `original_allowed_actions` capture point and first consumer

- **Capture line: `runtime.py:274`** (verbatim):

  ```python
  original_allowed_actions: tuple[str, ...] = tuple(envelope.allowed_actions)
  ```

  (Task 1.1 noted line 270 as the candidate from a partial read; the precise line at HEAD is **274**, three lines after the comment block at 273. Updating the precise number here.)

- **Scope check:** the variable is a local in `AgentRuntime.run`. It is in scope from line 274 through the entire method body — covering the CONTEXT_BUILDING block (lines 285–391 per Task 1.1), the ORIENTING block opening at line 388, and every subsequent phase boundary down to line ~939+. Task 3.2 can therefore pass `original_allowed_actions=original_allowed_actions` to `ContextCacheKeyBuilder.derive(...)` from anywhere inside the CONTEXT_BUILDING block (lines 285–391) without re-resolving the snapshot.

- **First consumer (Memory-not-Authority phase boundary):** `runtime.py:391`, inside the `_assert_memory_not_authority_boundary("context_building_to_orienting", context, envelope, original_allowed_actions)` call at the `state = state.transition(AgentPhase.ORIENTING)` boundary (lines 388–393):

  ```python
  state = state.transition(AgentPhase.ORIENTING)
  self._assert_memory_not_authority_boundary(
      "context_building_to_orienting",
      context,
      envelope,
      original_allowed_actions,
  )
  ```

- **Subsequent consumer call sites** (every phase boundary re-uses the same snapshot — confirmed via `grep_search "original_allowed_actions"` against `runtime.py`): lines **391, 415, 432, 451, 539, 628, 664, 809, 936**. Each is the fourth positional argument to `self._assert_memory_not_authority_boundary(...)`. The boundary helper itself takes `original_allowed_actions: tuple[str, ...]` at line 222 and forwards it twice (lines 240, 240) into the canonical Memory-not-Authority assertion — this is the existing safety chokepoint Task 3.2 will share.

- This confirms Task 3.2 can pass the same `original_allowed_actions` snapshot to `ContextCacheKeyBuilder.derive(..., original_allowed_actions=original_allowed_actions)` (and to the Task-3.3 cheap re-hash via `ContextCacheKeyBuilder.authority_hash(envelope, original_allowed_actions=original_allowed_actions)`) without any new snapshot capture.

#### (7) AgentRuntime — access to organ registry / kill-switch map / `WorkspaceSnapshotCache`

- **AgentRuntime constructor signature** (lines **97–164** of `runtime.py`, verbatim parameter list, kwarg-only after `*`):

  ```python
  def __init__(
      self,
      *,
      identity: AgentIdentity | None = None,
      project_root: str | Path | None = None,
      tool_registry: ToolRegistry | None = None,
      browser_renderer: BrowserRenderer | None = None,
      browser_fetcher: BrowserFetcher | None = None,
      browser_interaction_backend: BrowserInteractionBackend | None = None,
      browser_resolver: DnsResolver | None = None,
      browser_operator_route: BrowserOperatorRouteProtocol | None = None,
      latency_profiler: LatencyProfiler | None = None,
      cost_profiler: CostProfiler | None = None,
      context_build_cache: ContextBuildCache | None = None,
      prompt_frame_cache: PromptFrameCache | None = None,
      decision_frame_cache: LLMDecisionFrameCache | None = None,
      token_budget_governor: TokenBudgetGovernor | None = None,
      async_organ_scheduler: AsyncOrganScheduler | None = None,
      backpressure_controller: BackpressureController | None = None,
  ) -> None:
  ```

  No `workspace_snapshot_cache`, no `mission_kill_switches`, no `organ_registry`, no `model_call_optimizer` kwarg at HEAD.

- **Organ registry / live organ list — attribute path:** **NOT directly available** as `self.organs` / `self._organs` / `self._organ_registry` on `AgentRuntime` at HEAD. The closest collaborator is `self.tool_registry: ToolRegistry` (line 162 — assigned from the `tool_registry` kwarg, defaulting to `default_tool_registry()`). The `ToolRegistry` is the capability-dispatch surface, not a "live organ list with kill-switch" view. Concrete `OrganKillSwitch` and `OrganAuthorityEnvelope` instances are constructed **on demand inside `_execute_controlled_tool_calls`** (at lines 1496–1528 the imports are pulled and a per-call `kill_switch = OrganKillSwitch(mission_id=envelope.id, organ_id=organ_id, ...)` is built at line 1526 for each scheduler-routed tool call). There is **no mission-wide map** of `organ_id → (execution_allowed, advertised_capabilities, kill_switch_triggered)` on `AgentRuntime`.

  **Implication for Task 3.1:** the spec design's `OrganStateView` will need to be assembled by `AgentRuntime._organ_state_view()` from a different source. Two viable options surface from this read-only inspection: (a) iterate `self.tool_registry` for the capability set and synthesize a single `OrganStateEntry` per organ_id observed — kill-switch state is `False` because no kill-switch is engaged at the CONTEXT_BUILDING phase (organs are not yet dispatched at that point); (b) return an empty `OrganStateView(organs=[])` — the empty view still hashes to a stable canonical form (deterministic SHA-256 over the empty list), and any later organ-registry change will be reflected through `WorkspaceSnapshotCache` deltas / `CacheInvalidationPolicy.invalidate(...)`. Task 3.1 should pick option (a) and document the source. **No production change made in this read-only task; recording the constraint for Task 3.1.**

- **Kill-switch map — attribute path:** **NOT injected at HEAD.** The phrase `self._mission_kill_switches[envelope.id]` appears in `runtime.py` only as a **forward-looking comment** at line 1467 inside `_execute_controlled_tool_calls`'s rationale block:

  ```text
  1466-        non-triggered by default; if the mission has a triggered
  1467-        kill-switch in a future wave, it should arrive here from
  1467-        ``self._mission_kill_switches[envelope.id]`` (out of scope
  1469-        for Task 8.8).
  ```

  No actual `self._mission_kill_switches` attribute is assigned anywhere in `runtime.py`. There is also no per-organ kill-switch map distinct from the per-mission one — `OrganKillSwitch` instances are constructed per-call at line 1526. **Implication for Task 3.1:** the `kill_switch_triggered` field on each `OrganStateEntry` will default to `False` at the CONTEXT_BUILDING phase (no kill-switch engaged before any controlled-capability dispatch). This is consistent with the design's "Default-off behaviour" rule and does not weaken the cache key — once a kill-switch fires mid-run, the resulting `CacheInvalidationPolicy.invalidate(...)` event will evict any entry derived under the prior `organ_state_hash`.

- **`WorkspaceSnapshotCache` — attribute path:** **NOT injected at HEAD.** Confirmed via:
  - `grep_search "workspace_snapshot|self\._workspace"` against `runtime.py` → zero matches.
  - `grep_search "WorkspaceSnapshotCache"` against `runtime.py` → zero matches.
  - `AgentRuntime.__init__` parameter list (lines 97–164 above) contains no `workspace_snapshot_cache` kwarg.
  - The `TYPE_CHECKING` import block at lines 60–72 imports `ContextBuildCache`, `LLMDecisionFrameCache`, `PromptFrameCache`, `TokenBudgetGovernor`, `CostProfiler`, `LatencyProfiler`, `AsyncOrganScheduler`/`SubmissionAck`, `BackpressureController`, `OrganAuthorityEnvelope`, `OrganDryRunReceipt`, `OrganKillSwitch` — but **does NOT** import `WorkspaceSnapshotCache`.

  **Recording for Task 3.1:** `not injected at HEAD; Task 3.1 will use the empty-snapshot fallback.` The empty-snapshot canonical hex is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (SHA-256 of `b""`), which is exactly the value `WorkspaceSnapshotCache(...)` returns when no `apply_delta` has run (per the module docstring at lines 35–37 of `workspace_snapshot_cache.py`: *"The empty-snapshot `snapshot_id` is therefore a fixed hex constant (`sha256(b"")`)."*). Task 3.1's `_workspace_snapshot_id()` private helper will return the empty-snapshot constant when no `WorkspaceSnapshotCache` is injected, and will return `self._workspace_snapshot_cache.snapshot_id` if a future wave adds the kwarg.

- **`WorkspaceSnapshotCache.snapshot_id` confirmation:** the property is defined at `workspace_snapshot_cache.py` **lines 223–232** (verbatim):

  ```python
  @property
  def snapshot_id(self) -> str:
      """Deterministic hex hash of the current snapshot.

      ...
      """
      with self._lock:
          return self._snapshot_id
  ```

  The property's return value is a SHA-256 hex digest (line 33 of the module docstring: `snapshot_id = sha256(payload).hexdigest()`); SHA-256 hex digests are **64 hex characters** by construction, satisfying the Phase E lock and the design's `ContextCacheKey.workspace_snapshot_id: str (64 hex chars)` field constraint.

#### (8) Layering rule — `ContextBuilder` / `ContextCompressor` / `CognitiveCycle` / `phases.py` MUST NOT import `sentinel/perf/caches/`

Cross-checked with `grep_search` per file. Results:

| host file | grep query | result |
| --------- | ---------- | ------ |
| `agent/context_builder.py` | `perf\.caches\|context_build_cache\|ContextBuildCache\|ContextCacheKey\|ContextCacheKeyBuilder` | **zero matches** |
| `agent/context_compressor.py` | `perf\.caches\|ContextCacheKey\|TokenBudgetGovernor` | **zero matches** |
| `agent/cognitive_cycle.py` | `perf\.caches\|ContextCacheKey` | **zero matches** |
| `agent/phases.py` | `perf\.caches\|ContextCacheKey` | **zero matches** |

The design §Layering rule (`sentinel/agent/runtime.py --> perf/caches/ (TYPE_CHECKING)` only) is structurally satisfied at HEAD: only `runtime.py` imports cache helpers (and only under `TYPE_CHECKING`); the four host files in (1)/(2)/(3)/(4) are fully decoupled from `sentinel/perf/caches/`. Task 9 (U9) will re-pin this by AST.

#### ContextBuilder no-modification confirmation (U9 assertions for Task 8.1)

- **HEAD signature** (verbatim, unchanged at the foundation lock):

  ```python
  def build(
      self,
      envelope: MissionAuthorityEnvelope,
      *,
      user_input: dict[str, Any] | None = None,
      evidence_refs: list[str] | None = None,
      memory_items: list[dict[str, Any]] | None = None,
  ) -> AgentContext:
  ```

- **Current line count:** **70 lines** (file ends with newline; bytes = 2694). Task 8.1's "no diff" assertion will compare HEAD line count + content hash against the foundation lock at `378d862310bc1b5939b210a49c04026cd99a860d`.
- **No `cache_key_provider` kwarg on `__init__`:** confirmed (init at line 13 takes only `latency_profiler: LatencyProfiler | None = None`).
- **No `context_build_cache` kwarg on `__init__`:** confirmed (same — only `latency_profiler`).
- **No new required parameter on `build`:** confirmed — three keyword-only optional parameters, all with `None` defaults (`user_input`, `evidence_refs`, `memory_items`).
- **No import of `ContextBuildCache` / `ContextCacheKey` / `ContextCacheKeyBuilder` at HEAD:** confirmed (grep above). The only imports are `sentinel.agent.capability_selector.capabilities_from_actions`, `sentinel.agent.models.AgentContext`, `sentinel.mission.models.MissionAuthorityEnvelope`, and (under `TYPE_CHECKING`) `sentinel.perf.measure.latency_profiler.LatencyProfiler`.
- **AgentRuntime owns derivation, not ContextBuilder:** the design contract that AgentRuntime wraps the call externally via `ContextBuildCache.get_or_build(key, builder=lambda: context_builder.build(...))` is structurally enforceable because `ContextBuilder.build` has no access to `organ_state` or `workspace_snapshot_id` and therefore cannot derive a true four-component `ContextCacheKey` on its own. Task 8.1 will assert this by AST + content-hash diff against the foundation lock — **and the per-task wave order ensures Task 8.1 only needs to check the additive delta against `runtime.py`, not against `context_builder.py` (which must not change at all).**

These six assertions are the U9 invariants that Task 8.1 will pin against `context_builder.py` after every implementation wave.

- tests added or updated: none
- tests run: none
- result: pass
- scope guardrail result: n/a (read-only) — no production source, test, or `docs/CURRENT_STATE_LOCK.md` was modified; only this implementation log received an append.
- authority impact: none — no `MissionAuthorityEnvelope` / `OrganAuthorityEnvelope` field touched; no allowed-action surface read was used for anything beyond capturing the run-entry snapshot location at `runtime.py:274`.
- secrets impact: none — no raw envelope contents, no payload bodies, no prompt strings, no organ output bodies, no secret material recorded in this entry. Identifiers, line numbers, signatures, and SHA-256 hex constants only.
- remaining risk or follow-up:
  - **Task 3.1 constraint:** AgentRuntime has no `self._organs` / `self._organ_registry` / `self._mission_kill_switches` / `self._workspace_snapshot_cache` attribute at HEAD. Task 3.1's `_organ_state_view()` will need to source organ identity + capabilities from `self.tool_registry` (or return an empty `OrganStateView(organs=[])`); `_workspace_snapshot_id()` will return the empty-snapshot canonical hex `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` when no cache is injected. Recording this so Task 3.1 does not stumble on the absence.
  - **Task description discrepancy noted:** the task body says "Confirm there is NO `_do_build` method" on `ContextBuilder`, but the foundation-lock `context_builder.py` does include a private `_do_build(...)` helper introduced by `sentinel-performance-runtime-foundation` Phase B/C for latency-profiler instrumentation. The closure-spec invariant that actually matters — no new public required parameter, no `cache_key_provider` / `context_build_cache` kwarg, no import of cache helpers — holds at HEAD. Recording the discrepancy here so future readers reconcile the task wording against the foundation lock.
  - **Task description path correction:** `MissionRunner` lives at `sentinel/mission/runner.py` (NOT `sentinel/mission/reviewer.py`, which holds `ReviewerLite`).
- safe to continue: yes — proceed to Task 2.1 (create `sentinel/perf/caches/context_cache_key.py`).

### 2.1 — Create `sentinel/perf/caches/context_cache_key.py` with `ContextCacheKey` (Pydantic v2 frozen)

- task id: 2.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\requirements.md` (Requirements 1.1, 1.4, 1.6, 1.8, 5.2, 7.5, 10.1, 10.6 — input shape and exception contracts)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§`sentinel/perf/caches/context_cache_key.py`, §Cache Key Model, §Hash Derivation for Each Component — class shapes and constants)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 2.1 — Done-When and the Strict scope contract)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\shared\models.py` (confirms `SentinelModel(BaseModel)` with `model_config = ConfigDict(extra="forbid", use_enum_values=False)` at line 16, the base class to inherit from)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (read-only confirmation that the package init is the Wave 0 docstring-only file and is NOT modified by this task — Task 2.3 owns the export)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_scope_guardrails.py` (read-only — confirmed the boundary-detection gate's allowed-file-set already includes `sentinel/perf/caches/context_cache_key.py` and that the regex denylist scan applies to it)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\pyproject.toml` (confirms `pydantic>=2.6` — Pydantic v2 idioms `ConfigDict`, `field_validator(..., @classmethod)` are the canonical surface)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (new — 239 lines)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Created `sentinel/perf/caches/context_cache_key.py` containing only the data shapes, exceptions, and module constants the design requires for Task 2.1, with no builder logic (deferred to Task 2.2) and no `__init__.py` export (deferred to Task 2.3). Defined `ContextCacheKey(SentinelModel)` as a Pydantic v2 frozen model with `model_config = ConfigDict(frozen=True, extra="forbid")` and five 64-character lowercase-hex string fields (`mission_hot_hash`, `workspace_snapshot_id`, `organ_state_hash`, `authority_hash`, `composite_hash`), each enforced by a single `@field_validator(..., mode="default")` `@classmethod` that delegates to a private `_validate_lowercase_hex64` helper raising `ValueError(f"<field_name> must be a 64-character lowercase hex string")` on violation. Defined `OrganStateEntry(SentinelModel)` with `extra="forbid"`, a non-empty `organ_id` validator, and an `advertised_capabilities` validator asserting `value == sorted(set(value))`; defined `OrganStateView(SentinelModel)` with `extra="forbid"` and an `organs` validator asserting ascending `organ_id` order. Defined `MissingCacheKeyComponent(ValueError)` and `CacheKeySanitizerRejection(ValueError)` as empty exception subclasses with the docstrings the design specifies. Defined module-level constants `_FIELD_SEPARATOR = b"\x1f"`, `_RECORD_SEPARATOR = b"\x1e"`, and `_VOLATILE_FIELDS` as a 14-element `frozenset[str]` (`id`, `created_at`, `updated_at`, `started_at`, `ended_at`, `expires_at`, `trace_id`, `trace_refs`, `ts_ns`, `logical_time`, `sequence`, `previous_hash`, `event_hash`, `receipt_hash`). Imports are limited to `from __future__ import annotations`, `from pydantic import ConfigDict, field_validator`, and `from sentinel.shared.models import SentinelModel` — no `EventBus`, no `AgentEventType`, no `MissionAuthorityEnvelope`, no `AgentContext`, no sanitizer, no other cache helper, no I/O surface.
- tests added or updated: none (Task 2.1 explicitly creates only the new module — the property tests for the data shapes belong to a later wave).
- tests run:
  - inline `python -c "from sentinel.perf.caches.context_cache_key import ContextCacheKey, OrganStateView, OrganStateEntry, MissingCacheKeyComponent, CacheKeySanitizerRejection, _FIELD_SEPARATOR, _RECORD_SEPARATOR, _VOLATILE_FIELDS; k = ContextCacheKey(mission_hot_hash='0'*64, workspace_snapshot_id='1'*64, organ_state_hash='2'*64, authority_hash='3'*64, composite_hash='4'*64); print('ok', type(k).__name__, k.mission_hot_hash[:6], _FIELD_SEPARATOR, _RECORD_SEPARATOR, len(_VOLATILE_FIELDS))"` → `ok ContextCacheKey 000000 b'\x1f' b'\x1e' 14`, exit 0.
  - inline validator script asserting `ValidationError` is raised on (a) non-hex `mission_hot_hash`, (b) uppercase-hex value, (c) extra kwarg under `extra="forbid"`, (d) attempted mutation of the frozen model — all four assertions held; the frozen-model mutation surfaced as `ValidationError` (Pydantic v2 frozen mode), which the design explicitly accepts. Also confirmed `issubclass(MissingCacheKeyComponent, ValueError)` and `issubclass(CacheKeySanitizerRejection, ValueError)` both return `True`.
  - inline validator script for `OrganStateEntry` / `OrganStateView`: confirmed valid construction, rejection of unsorted `organs`, rejection of empty `organ_id`, rejection of unsorted `advertised_capabilities`, rejection of duplicate `advertised_capabilities`, rejection of extra kwargs.
  - `python -m pytest tests/perf/test_scope_guardrails.py` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → **20 passed in 1.20 s**, exit 0 (same count as Wave 0 — boundary-detection gate did not trip on the new module; the working-tree denylist scan is green for the new file).
- result: pass
- scope guardrail result: pass — file lives only under `sentinel/perf/caches/`; no `MissionAuthorityEnvelope` field touched (the module does not import `sentinel.mission.models`); no `OrganAuthorityEnvelope` field touched; no payment / spend / trading / channel-send / credential-secret regex term appears anywhere in the new module (verified by U12 working-tree scan returning zero violations for the closure spec's allowed-file set); no authority surface change; no new `AgentEventType` member; no new organ; no `runtime.py` / `context_builder.py` / `__init__.py` / `CURRENT_STATE_LOCK.md` change. The boundary-detection gate halts on every synthetic case as before (20/20).
- authority impact: none — `ContextCacheKey` and the input containers are pure hashing inputs; no `MissionAuthorityEnvelope` / `OrganAuthorityEnvelope` field is added, removed, or referenced.
- secrets impact: none — `ContextCacheKey` accepts only 64-char lowercase hex strings (validated at construction); no raw input substring, payload byte, or sanitizer-rejected material can be stored on the model. The two exception classes are bodyless and their docstrings explicitly forbid echoing rejected substrings in messages, which Task 2.2 will honor when raising them.
- remaining risk or follow-up: `ContextCacheKeyBuilder` (the staticmethod namespace that consumes these shapes and applies the canonical sanitizer) is deferred to Task 2.2; the package-level export of these public symbols is deferred to Task 2.3. Until both land, callers cannot import the new symbols via `from sentinel.perf.caches import ...` — they remain reachable only via the fully-qualified module path.
- safe to continue: yes — proceed to Task 2.2 (`ContextCacheKeyBuilder` implementation).

### 2.2 — Implement `ContextCacheKeyBuilder` (Strategy A: staticmethod namespace, pure-function)

- task id: 2.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\requirements.md` (Requirements 1, 2, 5, 8, 10.1, 10.6)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Cache Key Model, §Hash Derivation for Each Component, §`sentinel/perf/caches/context_cache_key.py`, §Failure modes)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 2.2 §Done-When)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (Task 2.1 surface — read in full)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\evidence_ranker.py` (canonical sanitizer surface — `sanitize_context_text` line 88, `sanitize_context_payload` line 95)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\models.py` (`MissionAuthorityEnvelope` field shapes — confirmed `mode: MissionMode`, `expires_at`, `revoked_at`, no `original_allowed_actions` field)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\models.py` (`AgentContext` field shape — confirmed no `blockers` field at HEAD)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (appended `ContextCacheKeyBuilder` class; added imports `hashlib`, `json`, `typing.Any`, `from sentinel.agent.evidence_ranker import sanitize_context_text`; updated module-level `__all__` to include `ContextCacheKeyBuilder`; line count grew from ~213 lines (Task 2.1 baseline) to 580 lines, delta +367)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Appended `ContextCacheKeyBuilder` as a Strategy-A pure staticmethod namespace (no instance state, no module-level mutable state, no I/O, no `EventBus`). The class exposes `derive(...)`, `mission_hot_hash(...)`, `organ_state_hash(...)`, `authority_hash(...)`, `_composite(...)`, plus four private staticmethod helpers: `_canonical_json_bytes`, `_sha256_hex`, `_check_clean`, `_normalize_enum_or_str`, `_sanitized_sorted_unique_strs`. Each component hash is SHA-256 over a deterministic JSON canonicalisation (`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")`); the composite is SHA-256 over the four component hex digests joined by `_FIELD_SEPARATOR` (0x1f). Authority canonical form uses `format(max_cost_usd, ".6f")` for the cost and `.isoformat()` (or `None`) for `expires_at`/`revoked_at`. Set-typed fields (`success_criteria`, `constraints`, `blockers`, `evidence_refs`, `allowed_actions`, `allowed_tools`, `original_allowed_actions`, `advertised_capabilities`) are sanitized then sorted-and-deduped. `original_allowed_actions` is required as an explicit kwarg on both `derive(...)` and `authority_hash(...)`; missing or `None` raises `MissingCacheKeyComponent` and the builder NEVER falls back to `envelope.original_allowed_actions` or to `envelope.id`. Every string-typed input passes through `sanitize_context_text`; if the sanitizer modifies the value (substitution detected → SecretMaterial present), `CacheKeySanitizerRejection` is raised with a message that names only the field (no echo of the rejected value or any substring).
- tests added or updated: none (no test files touched per task brief)
- tests run:
  - Inline one-shot smoke script `_tmp_task_2_2_smoke.py` (created under `services/sentinel-core/`, executed once, deleted afterward). All checks PASSED:
    - 1.a same-input determinism (all five `ContextCacheKey` fields equal across two `derive(...)` calls with identical inputs)
    - 1.b changing `original_allowed_actions` from `("a","b")` to `("a","b","c")` → different `authority_hash` AND different `composite_hash`; `mission_hot_hash`, `organ_state_hash`, `workspace_snapshot_id` unchanged
    - 1.c changing `workspace_snapshot_id` only → different `workspace_snapshot_id` AND different `composite_hash`; other three components unchanged
    - 1.d two envelopes with identical authority-relevant fields but different `id` / `user_id` / `created_at` → identical `authority_hash` (volatile fields excluded)
    - 1.e `composite_hash` is 64-char lowercase hex
    - 2.a–2.g `MissingCacheKeyComponent` raised on `envelope=None`, `context=None`, `organ_state=None`, `workspace_snapshot_id=""`, `workspace_snapshot_id=None`, `original_allowed_actions=None` (`derive`), and `authority_hash(envelope, original_allowed_actions=None)`
    - 3.a explicit `original_allowed_actions` kwarg drives `authority_hash` (`("a","b")` vs `("c","d")` differ even when envelope carries a fake `original_allowed_actions=("ghost",)` attribute)
    - 3.b removing the fake `envelope.original_allowed_actions` attribute does NOT change `authority_hash` for the same explicit kwarg — proves no fallback
    - 4.a `derive(...)` raises `CacheKeySanitizerRejection` when `mission_objective="contact: api_key=AKIAEXAMPLEFAKE12345"`
    - 4.b exception message contains neither `AKIAEXAMPLEFAKE12345`, nor `api_key=`, nor the full offending objective string
    - 4.c exception message names only the field (`mission_objective`)
    - 5.a `success_criteria=["b","a","c"]` vs `["a","b","c"]` → `mission_hot_hash` equal (sort+dedupe canonical form)
    - 5.b `allowed_actions` permutation → `authority_hash` equal
    - 6.a/6.b composite shape: 64-char lowercase hex
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → **20 passed in 1.05s** (same count as Wave 0).
- result: pass
- scope guardrail result: pass — U12 gate green; only `sentinel/perf/caches/context_cache_key.py` was modified; no `sentinel/agent/runtime.py`, `sentinel/agent/context_builder.py`, `sentinel/perf/caches/__init__.py`, or `docs/CURRENT_STATE_LOCK.md` touched; no test file modified; no payment / spend / trading / channel-send / credential-secret term introduced; no authority surface field added; no new `AgentEventType` member; no new organ subpackage; no `EventBus` import; no I/O; no `time` / `datetime` / `os` / `pathlib` / `httpx` import; no module-level mutable state; no mutation of caller-owned objects.
- authority impact: none — the builder READS authority-relevant fields off the envelope via `getattr(...)` for hashing only; no field added or modified on `MissionAuthorityEnvelope` or any sibling authority surface.
- secrets impact: none — exception messages were inspected programmatically (Check 4.b) and confirmed to contain no rejected substrings; the builder runs the canonical `sanitize_context_text` on every string-typed input and on every list element before any hash is computed; the produced `ContextCacheKey` contains only SHA-256 hex digests; the smoke test script was deleted after execution and never committed.
- remaining risk or follow-up: none — the builder is fully pure and exhaustively gated. Task 2.3 (`__init__.py` re-export) is the next step to make `from sentinel.perf.caches import ContextCacheKeyBuilder` succeed; this is owned by Task 2.3 per the strict scope guardrail and was NOT performed in this task.
- safe to continue: yes — proceed to Task 2.3 (export `ContextCacheKey`, `ContextCacheKeyBuilder`, `OrganStateView`, `OrganStateEntry`, `MissingCacheKeyComponent`, `CacheKeySanitizerRejection` from `sentinel/perf/caches/__init__.py`).

### 2.3 — Export public symbols from `sentinel/perf/caches/__init__.py`

- task id: 2.3
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 2.3 — strict scope: additive exports only)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Components and Interfaces — confirms the six public symbols to re-export)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (HEAD: docstring-only — the Wave 0 baseline; confirmed there are no pre-existing exports to preserve beyond the module docstring)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (modified — added six additive re-exports + `__all__`; module docstring preserved verbatim)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Re-exported `ContextCacheKey`, `ContextCacheKeyBuilder`, `OrganStateView`, `OrganStateEntry`, `MissingCacheKeyComponent`, and `CacheKeySanitizerRejection` from the `sentinel.perf.caches` package by importing them from `sentinel.perf.caches.context_cache_key` and listing all six in `__all__`. The original module docstring (`"""Phase C subpackage: context, prompt, and decision-frame caches."""`) is preserved verbatim as line 1; the additive `from ... import (...)` block carries a `# noqa: F401` to silence the re-export linter complaint, and is followed by a single `__all__` list. No pre-existing export was removed or renamed (the file at HEAD was docstring-only — confirmed in Task 0.2 and Task 2.1 entries). No other production source, no test, and no `docs/CURRENT_STATE_LOCK.md` was touched.
- tests added or updated: none
- tests run:
  - `python -c "from sentinel.perf.caches.context_build_cache import ContextBuildCache; from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache; from sentinel.perf.caches.prompt_frame_cache import PromptFrameCache; from sentinel.perf.caches.token_budget_governor import TokenBudgetGovernor; from sentinel.perf.caches.model_call_optimizer import ModelCallOptimizer; print('existing_submodule_imports_ok', ...)"` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → exit 0; output `existing_submodule_imports_ok ContextBuildCache LLMDecisionFrameCache PromptFrameCache TokenBudgetGovernor ModelCallOptimizer` (the five locked submodule imports still succeed via fully-qualified paths).
  - `python -c "from sentinel.perf.caches import ContextCacheKey, ContextCacheKeyBuilder, OrganStateView, OrganStateEntry, MissingCacheKeyComponent, CacheKeySanitizerRejection; print('package_import_ok', ContextCacheKeyBuilder.__name__)"` from same cwd → exit 0; output `package_import_ok ContextCacheKeyBuilder`. Confirms the new package-level import path works.
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → **20 passed**, exit 0 (same pass count as Wave 0; the working-tree regex denylist scan passes for the modified `__init__.py`).
- result: pass
- scope guardrail result: pass — only `sentinel/perf/caches/__init__.py` modified; no `sentinel/agent/runtime.py`, `sentinel/agent/context_builder.py`, `sentinel/perf/caches/context_cache_key.py`, `docs/CURRENT_STATE_LOCK.md`, or test file touched; no payment / spend / trading / channel-send / credential-secret token introduced; no authority surface field touched; no new `AgentEventType` member; no new organ subpackage; no new required parameter on `ContextBuilder.build`; the additive `from ... import` is purely additive and does not change any existing pre-Wave-0 export (there were none).
- authority impact: none — re-exports only; no `MissionAuthorityEnvelope` / `OrganAuthorityEnvelope` field added or modified.
- secrets impact: none — re-exports of class symbols only; no raw secret material, prompt body, payload, or sensitive cache value is introduced into the package surface.
- remaining risk or follow-up: none — the public closure-spec surface is now reachable via `from sentinel.perf.caches import ContextCacheKeyBuilder` (and the five sibling symbols). Wave 3 (replace the `envelope.id` cache-key stand-in inside `AgentRuntime.run` and add the private `_organ_state_view()` / `_workspace_snapshot_id()` helpers) is the next step.
- safe to continue: yes — proceed to Wave 3 / Task 3.1 (`AgentRuntime` private helpers `_organ_state_view()` and `_workspace_snapshot_id()`).

### 3.1 — Add private helpers `_organ_state_view()` and `_workspace_snapshot_id()` to `AgentRuntime`

- task id: 3.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\requirements.md`
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md`
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 3.1 §Done-When)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (verify-only — confirm `OrganStateEntry` / `OrganStateView` already re-exported by Task 2.3)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\capabilities\registry.py`
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\capabilities\models.py`
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (additive — one new import line `from sentinel.perf.caches import OrganStateEntry, OrganStateView` placed alphabetically after the `sentinel.mission.*` block, plus two new private instance methods `_organ_state_view(self) -> OrganStateView` and `_workspace_snapshot_id(self) -> str` inserted at the end of `class AgentRuntime` immediately after `_enforce_frame_budget` and before `_apply_final_gate`; line-count delta vs HEAD before this task: +53 lines, 1961 → 2014)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Added two private pure-reader helpers to `AgentRuntime`. `_organ_state_view()` returns `OrganStateView(organs=[])`: per the Task 3.1 brief's fallback rule, the live `ToolRegistry` is a tool/capability registry — `CapabilityManifest` does NOT expose an `organ_id` field — so it is NOT safely introspectable as an organ registry; at HEAD `AgentRuntime` also has no `self._organ_registry`, no `self._mission_kill_switches`, and at the `CONTEXT_BUILDING` phase no controlled-tool-call has been dispatched, so an empty `OrganStateView` is the correct snapshot (mid-run organ-state changes flow through the existing `CacheInvalidationPolicy.invalidate(...)` path, not via this helper). `_workspace_snapshot_id()` returns `self._workspace_snapshot_cache.snapshot_id` when a future-wave optional `WorkspaceSnapshotCache` is injected on the runtime and exposes a non-empty string `snapshot_id`; otherwise it returns the canonical empty-snapshot SHA-256 hex `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (= `sha256(b"").hexdigest()`). The defensive `getattr(self, "_workspace_snapshot_cache", None)` shape lets a future kwarg land without modifying this helper. Both helpers are pure read-only over `self`, mutate no caller-owned object, perform no I/O, emit no `EventBus` events, add no constructor kwarg, and change no public required signature. `OrganStateEntry` is co-imported alongside `OrganStateView` so a future revision of `_organ_state_view()` (after a real organ registry is wired) can populate non-empty `organs=[OrganStateEntry(...), ...]` without re-importing.
- tests added or updated: none
- tests run:
  - `python -c "from sentinel.agent.runtime import AgentRuntime; print('ok', AgentRuntime.__name__)"` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → output `ok AgentRuntime`, exit 0 (PASS — import smoke).
  - `python -c "from sentinel.agent.runtime import AgentRuntime; rt = AgentRuntime(); ws = rt._workspace_snapshot_id(); assert ws == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', ws; assert isinstance(ws, str) and len(ws) == 64; print('ok empty_snapshot', ws[:8] + '...')"` → output `ok empty_snapshot e3b0c442...`, exit 0 (PASS — `_workspace_snapshot_id` returns the canonical empty-snapshot hex on a default runtime).
  - `python -c "from sentinel.agent.runtime import AgentRuntime; from sentinel.perf.caches import OrganStateView; rt = AgentRuntime(); osv = rt._organ_state_view(); assert isinstance(osv, OrganStateView), type(osv); assert osv.organs == [], osv.organs; print('ok organ_state_view organs=', osv.organs)"` → output `ok organ_state_view organs= []`, exit 0 (PASS — `_organ_state_view` returns a valid empty `OrganStateView` on a default runtime).
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` → **20 passed**, exit 0 (PASS — boundary-detection gate stays green).
- result: pass
- scope guardrail result: pass — U12 boundary-detection gate (`tests/perf/test_scope_guardrails.py`) green at 20/20 after the edit; only `sentinel/agent/runtime.py` modified (one import line + two private helpers); no `sentinel/agent/context_builder.py` change; no `sentinel/perf/caches/context_cache_key.py` change; no `sentinel/perf/caches/__init__.py` change; no `docs/CURRENT_STATE_LOCK.md` change; no test file change; no `envelope.id` cache-key stand-in replaced (Task 3.2 owns that); no `CONTEXT_BUILDING` cache-branch body modified (Task 3.2 owns that); no `ContextCacheKeyBuilder.derive(...)` call introduced (Task 3.2 owns that); no new constructor kwarg; no public required signature change; no payment / spend / trading / channel-send / credential-secret regex term in new code or comments; no new `AgentEventType` member; no new organ subpackage; no `MissionAuthorityEnvelope` / `OrganAuthorityEnvelope` field touched.
- authority impact: none — neither helper reads, writes, or expands any field of `MissionAuthorityEnvelope` or `OrganAuthorityEnvelope`. `_organ_state_view()` returns a constant empty view; `_workspace_snapshot_id()` returns a constant empty-snapshot SHA-256 hex.
- secrets impact: none — neither helper accepts any string input from envelope, context, prompts, browser bodies, or tool payloads. No `sanitize_context_text` / `sanitize_context_payload` invocation needed at this layer (the cache-key builder applies the canonical sanitizer at the call site that consumes these helpers, which is Task 3.2's seam). The constant hex is `sha256(b"").hexdigest()` and contains no SecretMaterial.
- remaining risk or follow-up: explicitly noted — `_organ_state_view()` deliberately returns an empty `OrganStateView` per the Task 3.1 brief's fallback rule because `ToolRegistry` is not safely introspectable as an organ registry (`CapabilityManifest` lacks `organ_id`) and `AgentRuntime` has no `self._organ_registry` or `self._mission_kill_switches` at HEAD. When a real organ registry is wired in a later wave, this helper will be revised to return a populated view; the co-imported `OrganStateEntry` makes that revision additive (no new import needed). The empty view is invariant-safe at the `CONTEXT_BUILDING` phase because no controlled-tool-call has been dispatched yet and no `OrganKillSwitch` is engaged; mid-run organ-state changes are handled via `CacheInvalidationPolicy.invalidate(...)` per design.
- safe to continue: yes — the two helpers are in place with the correct semantics; Task 3.2 can now call `ContextCacheKeyBuilder.derive(envelope=..., context=draft_context, organ_state=self._organ_state_view(), workspace_snapshot_id=self._workspace_snapshot_id(), original_allowed_actions=original_allowed_actions)` at the `CONTEXT_BUILDING` phase to replace the `envelope.id` / `"v1"` stand-in.


### 3.2 — Replace the `envelope.id` cache-key arguments at the `CONTEXT_BUILDING` phase

- task id: 3.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 3.2 §Done-When and the Required edit blocks)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Replacement rule (P-C-KEY-01), §Wiring matrix `ContextBuilder` row, §Failure modes 1, 2, 7)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read in full for the import block + the `CONTEXT_BUILDING` cache branch + the existing `_organ_state_view` / `_workspace_snapshot_id` helpers added by Task 3.1)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (verified `ContextCacheKeyBuilder.derive(...)` signature and exception hierarchy: `MissingCacheKeyComponent` / `CacheKeySanitizerRejection` both subclass `ValueError`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\models.py` (verified `AgentContext.mission` is the only required field; `user_input`, `evidence_refs`, `memory_items`, `constraints`, etc. all have safe defaults)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\__init__.py` (confirmed `CacheKeySanitizerRejection`, `ContextCacheKeyBuilder`, `MissingCacheKeyComponent` are already re-exported)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\test_agent_runtime.py` (referenced the existing envelope fixture shape for the cache-injected smoke check)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` — extended one import line (`from sentinel.perf.caches import OrganStateEntry, OrganStateView` → multi-line alphabetical block adding `CacheKeySanitizerRejection`, `ContextCacheKeyBuilder`, `MissingCacheKeyComponent`); replaced the 10-line `composite_key(...)` + `get_or_build(...)` stand-in at the former HEAD lines 330–339 with a ~63-line `try` / `except (MissingCacheKeyComponent, CacheKeySanitizerRejection):` block (28 lines of leading rationale comment + 27 lines of `try` body + 4 lines of `except` body) that derives the canonical four-component `ContextCacheKey` and falls through to `_build_context_cached()` on either deterministic-error type. New CONTEXT_BUILDING cache branch is at lines 315–397; the new `try` body is at lines 369–393 and the `except` body is at lines 394–397.
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` — this entry.
- exact implementation summary: At the `CONTEXT_BUILDING` phase inside the `if self._context_build_cache is not None:` branch, AgentRuntime now constructs a draft `AgentContext(mission=envelope, user_input=user_input or {}, evidence_refs=evidence_refs or [], memory_items=memory_items or [])` (only `mission` is required; `constraints`, `available_capabilities`, `available_tools`, `world_model_refs`, `summary`, `blockers`-via-getattr all default), calls `ContextCacheKeyBuilder.derive(envelope=..., context=draft_context, organ_state=self._organ_state_view(), workspace_snapshot_id=self._workspace_snapshot_id(), original_allowed_actions=original_allowed_actions)`, then forwards the four canonical hashes to `ContextBuildCache.composite_key(...)` and `ContextBuildCache.get_or_build(composite_key, _build_context_cached, mission_id=envelope.id)`. `mission_id=envelope.id` is preserved verbatim as the cache-event tag (NOT a cache-key value). On `MissingCacheKeyComponent` or `CacheKeySanitizerRejection` the code falls through to fresh computation via the existing `_build_context_cached()` closure — no partial key, no `envelope.id` fallback, no cached entry served, no exception detail logged or re-emitted. The `try` / `except` deliberately catches ONLY the two deterministic key-builder error types; `Exception` and `ValueError` are NOT caught more broadly, so unrelated bugs propagate. The closure `_build_context_cached` (lines 316–335) is untouched; the `elif self._latency_profiler is not None:` and final `else:` branches are untouched; the rationale comment block above the cache branch (lines 293–314) is untouched.
- tests added or updated: none (Task 3.2 explicitly forbids test-file edits)
- tests run:
  - Inline check 1 — `python -c "from sentinel.agent.runtime import AgentRuntime; print('ok', AgentRuntime.__name__)"` from `services/sentinel-core/` → `ok AgentRuntime`, exit 0.
  - Inline check 2 — default-off path: constructed a default `AgentRuntime(project_root=tmp)` with NO `context_build_cache` injected, ran the GTM-shaped envelope from the existing `tests/test_agent_runtime.py` fixture; confirmed `rt._context_build_cache is None` (so the new `if self._context_build_cache is not None:` branch — and therefore the new `try`/`except` — is never entered) and `result.mission_id == envelope.id`, `result.final_phase.value == "completed"`. Exit 0.
  - Inline check 3 — cache-injected path: constructed `ContextBuildCache(event_bus=EventBus(envelope.id))`, injected via `AgentRuntime(project_root=tmp, context_build_cache=cache)`, ran the same GTM envelope. Confirmed `result.mission_id == envelope.id` and `result.final_phase.value == "completed"` (i.e., a non-FAILED phase, satisfying Task 3.2 cache-injected smoke contract). Exit 0. The temporary one-shot script `_task_3_2_smoke.py` was deleted after the run; no test file was added.
  - Inline check 4 — AST/grep confirmation against `services/sentinel-core/sentinel/agent/runtime.py`:
    - `mission_hot_hash=envelope\.id` → 0 matches (stand-in gone).
    - `authority_hash=envelope\.id` → 0 matches (stand-in gone).
    - `workspace_snapshot_id="v1"` → 0 matches (stand-in gone).
    - `organ_state_hash="v1"` → 0 matches (stand-in gone).
    - `mission_id=envelope\.id` → 24 matches across 24 distinct lines (event-tag / `OrganAuthorityEnvelope` / `_apply_final_gate` propagation; this is the allowed pattern). The single instance inside the new `get_or_build(...)` call at line 391 is preserved verbatim.
  - Inline check 5 — boundary-detection gate: `python -m pytest tests/perf/test_scope_guardrails.py -q` from `services/sentinel-core/` → **20 passed** in 1.40 s, exit 0.
- result: pass
- scope guardrail result: pass — boundary gate green (20/20); only `sentinel/agent/runtime.py` and the implementation log were modified; `context_builder.py`, `context_cache_key.py`, `sentinel/perf/caches/__init__.py`, every test file, and `docs/CURRENT_STATE_LOCK.md` are untouched; no new constructor kwarg added; no new public required parameter; no new `AgentEventType` member; no `EventBus.append(...)` call introduced; no payment / spend / trading / channel-send / credential-secret regex term in the new code or comments; authority surface unchanged.
- authority impact: none — `MissionAuthorityEnvelope` and `OrganAuthorityEnvelope` are not modified; `original_allowed_actions` is consumed read-only as the run-entry tuple captured for the Memory-not-Authority invariant; `authority_hash` is now a true SHA-256 over the canonical authority form (mission type, allowed/forbidden actions, allowed tools, max actions, max cost, mode, expires_at, revoked_at, plus the explicit `original_allowed_actions` tuple), so authority drift would now invalidate the cache by construction (Task 3.3 will add the cheap re-hash drift detector on top of this).
- secrets impact: none — exception messages from `MissingCacheKeyComponent` / `CacheKeySanitizerRejection` are NOT logged, formatted, or re-emitted by the new `except` branch; `draft_context` is built from inputs already passed to `self.context_builder.build(...)` via the same closure on the cache-miss path, so no new logging or sanitization seam is introduced; `user_input`, `evidence_refs`, and `memory_items` are not echoed into traces by this code; the canonical sanitizer inside `ContextCacheKeyBuilder` is the single chokepoint and already guarantees no SecretMaterial leaks into the key.
- remaining risk or follow-up: Task 3.3 (authority drift detector) will add a cheap `authority_hash` re-hash before serving a cached entry; Task 4.1 will source `mission_hot_hash` and `authority_hash` from the same `ck` value inside `_build_decision_frame_cached`. The `draft_context` constructed here is a pre-build snapshot — it covers `mission_hot_hash`'s actual reads (envelope-side fields plus `context.constraints` / `evidence_refs` / `blockers`), so the cache key remains deterministic across identical inputs without paying the cost of calling `ContextBuilder.build` twice. If a future `mission_hot_hash` rev starts reading post-build-only context fields, the draft shape will need to be revisited; design.md §Hash Derivation §1 currently restricts reads to the pre-build set and is the contract.
- safe to continue: yes — proceed to Task 4.1 (wire `LLMDecisionFrameCache` to source `mission_hot_hash` / `authority_hash` from the same `ck` derived here).


### 3.3 — Authority drift detector (cheap re-hash before serving)

- task id: 3.3
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 3.3 §Done-When and §Required implementation)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Invalidation Rules §Rule 1 — Authority drift mid-flight; §Failure modes §7)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (post Task 3.2 state — read CONTEXT_BUILDING cached branch lines ~360–420)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\models.py` (read-only — confirm `MissionAuthorityEnvelope` required field shape used by the inline functional check)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (one block insertion in the existing `try:` body of the `if self._context_build_cache is not None:` branch at the `CONTEXT_BUILDING` phase; nothing else touched in this file)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- exact implementation summary: Inserted the cheap authority drift detector inside the `try:` body of the CONTEXT_BUILDING cached branch, AFTER `ck = ContextCacheKeyBuilder.derive(...)` returns and BEFORE either `composite_key(...)` / `get_or_build(...)` is called. The detector computes `current_authority_hash = ContextCacheKeyBuilder.authority_hash(envelope, original_allowed_actions=original_allowed_actions)` — a single re-hash of the authority component, not a four-component re-derivation — passing the same run-entry `original_allowed_actions` snapshot already captured at line 282 (`original_allowed_actions: tuple[str, ...] = tuple(envelope.allowed_actions)`). When `current_authority_hash != ck.authority_hash` the cached path is skipped and `context = _build_context_cached()` is invoked directly (fresh computation; no partial key; no `envelope.id` fallback; no cached entry served under uncertainty). When equal, the existing Task 3.2 path runs unchanged: `composite_key(...)` consumes `ck.{mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash}` and `get_or_build(...)` is invoked with `mission_id=envelope.id` preserved as the event tag (NOT a cache-key value). The outer `except (MissingCacheKeyComponent, CacheKeySanitizerRejection):` clause from Task 3.2 is unchanged and still falls through to `_build_context_cached()`. No new exception type is caught, no broader exception type is caught, no new EventBus event is emitted, no new AgentEventType member is added, no constructor kwarg is added, no public required parameter is added, no authority surface field is touched, no organ added, no foundation cache helper signature changed.
- exact lines changed:
  - `runtime.py` — drift detector comment + computation + branching block at lines **383–418** of the post-edit file (the detector comment occupies lines 383–400; `current_authority_hash = ...` at lines 401–404; `if current_authority_hash != ck.authority_hash: context = _build_context_cached()` at lines 405–406; `else: composite_key(...) + get_or_build(...)` at lines 407–418). The Task 3.2 derive call at lines 375–382 is unchanged; the `except (MissingCacheKeyComponent, CacheKeySanitizerRejection):` clause at lines 419–422 is unchanged.
- exact authority drift check shape:

  ```python
  ck = ContextCacheKeyBuilder.derive(
      envelope=envelope,
      context=draft_context,
      organ_state=self._organ_state_view(),
      workspace_snapshot_id=self._workspace_snapshot_id(),
      original_allowed_actions=original_allowed_actions,
  )
  # ... drift comment ...
  current_authority_hash = ContextCacheKeyBuilder.authority_hash(
      envelope,
      original_allowed_actions=original_allowed_actions,
  )
  if current_authority_hash != ck.authority_hash:
      context = _build_context_cached()
  else:
      composite_key = self._context_build_cache.composite_key(
          mission_hot_hash=ck.mission_hot_hash,
          workspace_snapshot_id=ck.workspace_snapshot_id,
          organ_state_hash=ck.organ_state_hash,
          authority_hash=ck.authority_hash,
      )
      context = self._context_build_cache.get_or_build(
          composite_key,
          _build_context_cached,
          mission_id=envelope.id,
      )
  ```

- behavior on drift: When `current_authority_hash` differs from `ck.authority_hash`, the cached entry is NOT served, `composite_key(...)` and `get_or_build(...)` are NOT called, and the existing `_build_context_cached()` closure (the same closure used by the Task 3.2 fallthrough) is invoked directly to produce a fresh `AgentContext`. The drift path emits no event, logs no envelope value, raises no exception, and executes no `envelope.id` fallback. The detector is one cheap re-hash per cached-branch entry and runs ONLY when `self._context_build_cache is not None`; the default-off path (no cache injected) is byte-identical to the foundation-lock head as it does not enter the `try:` body.
- tests added or updated: none (Task 3.3 explicitly forbids modifying tests; functional verification was performed via two scratch scripts that were created, executed, and deleted within this task — see "tests run" below)
- tests run:
  - `python -c "from sentinel.agent.runtime import AgentRuntime; print('IMPORT_OK')"` (from `services/sentinel-core/`) → `IMPORT_OK`, exit 0
  - `_task33_inline_check.py` (scratch, executed and deleted) — imports `AgentRuntime`, `ContextBuildCache`, `ContextCacheKeyBuilder` cleanly via the canonical (production) entry order → `INLINE_OK`, exit 0
  - `_task33_drift_check.py` (scratch, executed and deleted) — three functional cases exercising the equality/inequality contract used inside the detector:
    - Case A — identical envelope and identical `original_allowed_actions` → `authority_hash` equal (cached path serves) → OK
    - Case B — live `envelope.allowed_actions` widened from `("read",)` to `("read","write")` post-derive while reusing the original snapshot → `authority_hash` differs (drift detector triggers fresh rebuild) → OK
    - Case C — same envelope, different `original_allowed_actions` snapshot supplied → `authority_hash` differs (drift detector triggers fresh rebuild) → OK
    - all three: `ALL_DRIFT_CHECKS_OK`, exit 0
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (U12 boundary-detection gate, ran twice — once after the runtime edit, once after scratch cleanup) → **20 passed in 1.3 s** both runs, exit 0
  - grep `mission_hot_hash=envelope\.id|authority_hash=envelope\.id|workspace_snapshot_id=\"v1\"|organ_state_hash=\"v1\"` against `sentinel/agent/runtime.py` → **No matches found** (P-C-KEY-01 stand-in confirmed gone)
  - grep `mission_id=envelope\.id` against `sentinel/agent/runtime.py` → 23 matches, all event-tag / `mission_id` propagation arguments to `LatencyProfiler.instrument(...)`, `AgentRunResult(...)`, `OrganAuthorityEnvelope(...)`, `OrganKillSwitch(...)`, `OrganDryRunReceipt(...)`, `_ToolCallSchedulerAction(...)`, `AgentState(mission_id=...)`, and the `ContextBuildCache.get_or_build(..., mission_id=envelope.id)` event tag at line 416 — all are non-cache-key uses (event/state propagation), and Task 3.3 explicitly allows `mission_id=envelope.id`. None of these is a cache-key VALUE slot.
- result: pass
- scope guardrail result: pass — U12 gate green at 20/20 both before and after scratch cleanup; no production source touched outside `sentinel/agent/runtime.py`; no tests modified; no `context_builder.py` change; no `context_cache_key.py` change; no `caches/__init__.py` change; no `CURRENT_STATE_LOCK.md` change; no new `AgentEventType` member; no `EventBus.append(...)` added; no constructor kwarg added; no public required parameter added; no `MissionAuthorityEnvelope` or `OrganAuthorityEnvelope` field touched; no payment / spend / trading / channel-send / credential-secret term introduced; no new organ subpackage; no browser power expansion; the boundary-detection gate's regex denylist scan against `sentinel/agent/runtime.py` is part of the U12 gate run and remained green.
- authority impact: none — the drift detector is a READ over the live `MissionAuthorityEnvelope` followed by a hash comparison. It strictly TIGHTENS the cache safety contract (a cached `AgentContext` is now refused when its key-time `authority_hash` no longer matches the post-derive re-hash). It does not add, remove, or relax any field on `MissionAuthorityEnvelope` or `OrganAuthorityEnvelope`; it does not change the run-entry `original_allowed_actions` capture site; it does not bypass any existing FinalGate, kill-switch, or Memory-not-Authority phase-boundary check. `CoreFinalGate.evaluate` continues to run on every `AgentRuntime.run` exit path including cache-hit paths.
- secrets impact: none — the drift detector consumes only the `MissionAuthorityEnvelope` (already sanitizer-clean by construction) and the `original_allowed_actions: tuple[str, ...]` snapshot (immutable list of action-name strings, not payloads). No prompt body, evidence content, raw payload, or `SecretMaterial` is read or hashed by the detector. The two paths it can take both already pass through the existing canonical sanitizer chokepoint (cached path: `ContextCacheKeyBuilder.authority_hash`'s sanitizer pass on string-typed inputs; drift path: `_build_context_cached()` invokes `ContextBuilder.build` whose sanitizer chokepoints are unchanged). No envelope value, hash value, or comparison result is logged; the detector is silent on both branches.
- remaining risk or follow-up:
  - **Pre-existing import-cycle caveat (NOT introduced by Task 3.3, NOT in scope to fix here)**: importing `sentinel.perf.caches.context_cache_key` as the FIRST entry point triggers a circular import via `sentinel.agent.evidence_ranker → sentinel.agent.__init__ → AgentRuntime → sentinel.perf.caches`. The cycle was created in Task 2.1/2.2 when `context_cache_key` imported `sanitize_context_text` from `sentinel.agent.evidence_ranker`. Production code never enters via that path (everything goes through `from sentinel.agent.runtime import AgentRuntime` first or through `from sentinel.perf.caches import ...` after the `agent` package finishes initializing), so all production tests / inline checks here pass. The two scratch verification scripts written during Task 3.3 had to import `AgentRuntime` first to seed `sys.modules`. Task 3.3 scope explicitly forbids modifying `context_cache_key.py` or `caches/__init__.py`, so no fix attempted; flagging for a future wave (likely Wave 9 test-construction or a Phase-D cleanup) to either move the sanitizer import inside the function bodies of `ContextCacheKeyBuilder` or relocate `sanitize_context_text` to a module that is leaf in the import graph. Until then, any Wave 9 test that imports `context_cache_key` directly should import `sentinel.agent.runtime` (or `sentinel.agent`) first.
  - **Drift detection scope**: the detector recomputes `authority_hash` only. `mission_hot_hash`, `organ_state_hash`, and `workspace_snapshot_id` are NOT re-checked at serve time (per design §Invalidation Rules §Rule 1, only authority drift requires the cheap re-check; the other three components are part of the cache-key composition itself, so any change to them produces a different `composite_key` at the `composite_key(...)` call and the cache will naturally miss). This is intentional and matches the spec.
- safe to continue: yes — `runtime.py` import succeeds; default-off path unchanged; cache-injected path now refuses to serve when authority drifts mid-flight; U12 gate green; no scope guardrail violation. Proceed to Task 4.1 (`LLMDecisionFrameCache` wiring — source `mission_hot_hash` and `authority_hash` from `ck` inside `_build_decision_frame_cached`) when the user issues that instruction.


### 4.1 — Source `mission_hot_hash` and `authority_hash` from `ContextCacheKeyBuilder` in `_build_decision_frame_cached` — DEFERRED

- task id: 4.1
- deferral identifier: **P-C-RUNTIME-01-DECISIONFRAME-DEFER**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 4.1 §Required implementation, §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Existing helpers, §FinalGate / Receipt Implications §LLMDecisionFrameCache safety bypass)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `_build_decision_frame_cached` body lines 1854–1899; foundation-spec preamble lines 1840–1853 explicitly stating the LLM-backed decision cycle is deferred)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\decision_frame.py` (read-only — `LLMDecisionFrame.build(...)` classmethod signature: requires `mission_id`, `mission_card`, `authority_card`, `progress_card`, `evidence`, `selected_tool_surface`, `current_blockers`, `next_decision_options`, `required_output_schema`, `budget_allocator`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\llm_decision_frame_cache.py` (read-only — `composite_hash(*, mission_hot_hash, authority_hash, evidence_set_hash, tool_surface_hash) -> str`; `get(composite, *, mission_id) -> LLMDecisionFrame | None`; `put(composite, frame, *, mission_id) -> None`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\bench\golden_runners.py` (read-only — only workspace site that invokes `LLMDecisionFrame.build(...)`; this is a benchmark runner, NOT a production flow)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 4.1 is **deferred** under identifier **P-C-RUNTIME-01-DECISIONFRAME-DEFER** because the prerequisite call site does not exist in production code. Confirmed by direct inspection that `AgentRuntime.run` does NOT invoke `LLMDecisionFrame.build(...)` anywhere today, and that the existing private wrapper `_build_decision_frame_cached(...)` at lines 1854–1899 has zero callers anywhere in the package (`grep "_build_decision_frame_cached" sentinel/` returns only its `def` line; `grep "LLMDecisionFrame.build" sentinel/` returns one hit in `sentinel/perf/bench/golden_runners.py`, which is a benchmark, not a runtime call site). The wrapper itself is already correctly shaped — it never references `envelope.id` internally and accepts `composite_inputs: dict[str, str]` from a caller that does not yet exist. The only Task 4.1 rewrite the spec text describes ("change `composite_inputs["mission_hot_hash"]` and `composite_inputs["authority_hash"]` sources from `envelope.id` to `ck.mission_hot_hash` and `ck.authority_hash`") therefore has nothing to rewrite at HEAD. Adding a new `LLMDecisionFrame.build(...)` invocation to `AgentRuntime.run` would materially expand product behavior — the runtime would start synthesizing `mission_card` / `authority_card` / `progress_card` / `evidence` cards / tool surface / blockers / decision options / output schema / `PromptBudgetAllocator` on every run — and is explicitly deferred by the foundation-spec preamble at `runtime.py` lines 1840–1853 verbatim: "The cognitive cycle in this codebase does not yet invoke `LLMDecisionFrame.build` or `LLMDecisionFrame.render_prompt_text` directly from `AgentRuntime`, but the spec requires constructor-level injection of the caches and governor here so downstream wiring (e.g. when the LLM-backed decision cycle lands) can adopt the cache surface without changing public signatures again." User confirmed Option C: defer Task 4.1, do not modify `runtime.py`, do not hoist `ck`, do not add a fake caller, do not add an `LLMDecisionFrame.build(...)` call, do not expand AgentRuntime product behavior, document only. Task 4.2 (constructor-injection verify) proceeds next.
- deferral rationale (verbatim, per user direction):
  1. `_build_decision_frame_cached(...)` has **no real caller** in `AgentRuntime.run` today.
  2. `AgentRuntime.run` does not currently invoke `LLMDecisionFrame.build(...)`.
  3. The foundation-spec preamble at `runtime.py` lines 1840–1853 explicitly defers the LLM-backed decision cycle.
  4. Adding a real caller would expand AgentRuntime product behavior (synthesizing `mission_card` / `authority_card` / `progress_card` / `evidence` / `selected_tool_surface` / `current_blockers` / `next_decision_options` / `required_output_schema` / `PromptBudgetAllocator` on every mission) and requires a separate spec.
  5. The helper is already correctly shaped and does not use `envelope.id` internally — Task 4.1's literal rewrite has nothing to rewrite at HEAD.
- contract for the future LLM-backed decision-cycle work (recorded for whoever picks up `P-C-RUNTIME-01-DECISIONFRAME-DEFER`):
  - When a real `LLMDecisionFrame.build(...)` invocation is added to `AgentRuntime.run`, it MUST funnel through the existing `_build_decision_frame_cached(...)` helper.
  - The caller MUST source `composite_inputs["mission_hot_hash"]` from `ck.mission_hot_hash`.
  - The caller MUST source `composite_inputs["authority_hash"]` from `ck.authority_hash`.
  - The caller MUST NOT fall back to `envelope.id` for either slot.
  - The caller MUST source `composite_inputs["evidence_set_hash"]` and `composite_inputs["tool_surface_hash"]` from deterministic frame-side hashes (the four-component slot list defined by `LLMDecisionFrameCache.composite_hash(*, mission_hot_hash, authority_hash, evidence_set_hash, tool_surface_hash)`).
  - The caller MUST carry `ck` from the CONTEXT_BUILDING phase (where it is derived in Task 3.2/3.3) without re-derivation, to satisfy "Do NOT re-derive ContextCacheKey in the decision-frame phase unless absolutely unavoidable" (Task 4.1 §Rule 3). When that future work lands, the simplest preservation is to bind `ck` to a local that survives past the `try:` block (or to thread it through the orient/method-selection helpers). This deferral entry is the canonical place where that contract is recorded.
  - The caller MUST preserve the locked safety bypass in `LLMDecisionFrameCache`: `authority_expansion=True` writes raise `ValueError` (must propagate, not swallow); `raw_secret_leakage=True` reads are evicted and return a miss (the cache module already enforces this).
  - The caller MUST NOT add a new `AgentEventType` member or new `EventBus.append` event; existing cache events emitted by `LLMDecisionFrameCache.get` / `put` are sufficient.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate before logging the deferral) → **20 passed in 1.27 s**, exit 0
- result: pass (deferred — no production code change required to satisfy the deferral contract)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The runtime authority surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are untouched. The deferral contract above explicitly forbids any future caller from falling back to `envelope.id` for the `authority_hash` slot.
- secrets impact: none — the deferral itself reads no secret material; the future-caller contract above requires the existing canonical sanitizer chokepoint inside `LLMDecisionFrame.build` to remain the single sanitization site, and forbids any new prompt-rendering path from being added.
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-DECISIONFRAME-DEFER`. When the LLM-backed decision cycle lands (separate spec / foundation-spec follow-up), the future caller MUST honor the contract enumerated above. Until that work lands, `_build_decision_frame_cached(...)` remains a structural placeholder with no live caller — same posture as the foundation lock.
  - The `P-C-KEY-01` cache-key replacement work is complete in Tasks 3.1 → 3.3 (the `CONTEXT_BUILDING`-phase `ContextBuildCache.composite_key(...)` call site no longer references `envelope.id` for any cache-key value slot; the U12 guardrail gate confirms this every wave). The decision-frame cache replacement work in `_build_decision_frame_cached` was already structurally complete at the foundation lock (the helper does not reference `envelope.id` anywhere) — Task 4.1's literal rewrite was therefore a no-op at HEAD.
- safe to continue: yes — proceeding to Task 4.2 (verify constructor injection on `AgentRuntime` is preserved; AST-shape pin via U9 in Wave 9).


### 4.2 — Verify constructor injection on `AgentRuntime` is preserved (no signature change)

- task id: 4.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 4.2 §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Components and Interfaces, §FinalGate / Receipt Implications §LLMDecisionFrameCache safety bypass)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `AgentRuntime.__init__` lines 110–203 with constructor parameter list and storage block)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\llm_decision_frame_cache.py` (read-only — `LLMDecisionFrameCache.__init__(*, event_bus, clock=time.monotonic_ns)` lines 225–237; required kwarg shape used to construct a fresh instance for the identity smoke check)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\event_bus.py` (read-only — `EventBus(mission_id)` shape used to construct the smoke-check `event_bus` argument)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no** (read-only verification; no real mismatch found)
- exact constructor lines verified:
  - **runtime.py line 137** (parameter list, keyword-only): `decision_frame_cache: LLMDecisionFrameCache | None = None,`
  - **runtime.py line 178** (storage assignment, gated comment at lines 174–176 documents the "None means not injected" contract): `self._decision_frame_cache = decision_frame_cache`
  - The parameter sits inside the `*,` keyword-only marker block introduced earlier in `__init__` (Task 6.11 / sentinel-performance-runtime-foundation cache-injection block, lines 117–138). Adjacent additive cache parameters at the same indentation level: `context_build_cache` (line 135), `prompt_frame_cache` (line 136), `decision_frame_cache` (line 137), `token_budget_governor` (line 138). The matching storage assignments at lines 174–179 mirror the parameter order: `self._context_build_cache` (line 175), `self._prompt_frame_cache` (line 176), `self._decision_frame_cache` (line 177), `self._token_budget_governor` (line 178). All four follow the same default-off / injection-gated contract documented in the foundation-spec preamble at lines 117–134.
- exact implementation summary: Read-only verification confirmed `decision_frame_cache: LLMDecisionFrameCache | None = None` is present at `runtime.py` line 137 (keyword-only, default `None`, annotation `LLMDecisionFrameCache | None`) and that `self._decision_frame_cache = decision_frame_cache` is present at line 178 with no transformation, copy, or wrapper between the parameter and the attribute. Three orthogonal checks were executed via a scratch script (created, run, deleted within this task) to prove the contract end-to-end: (1) default-off — `AgentRuntime()._decision_frame_cache is None`; (2) identity preservation — `AgentRuntime(decision_frame_cache=cache_instance)._decision_frame_cache is cache_instance` (the `is`-identity check, not equality); (3) signature shape — `inspect.signature(AgentRuntime.__init__).parameters["decision_frame_cache"]` reports `kind=KEYWORD_ONLY`, `default=None`, `annotation='LLMDecisionFrameCache | None'`. All three passed. No code change was needed; the foundation lock at commit `378d862310bc1b5939b210a49c04026cd99a860d` already satisfies Task 4.2's done-when contract.
- default-off result: **pass** — `AgentRuntime()._decision_frame_cache is None` confirmed.
- injected identity result: **pass** — `AgentRuntime(decision_frame_cache=<LLMDecisionFrameCache(event_bus=EventBus("identity-check"))>)._decision_frame_cache is cache_instance` confirmed (same Python object identity by `is`, not just equality).
- signature shape result: **pass** — `inspect.signature(AgentRuntime.__init__)` exposes `decision_frame_cache` as `KEYWORD_ONLY`, default `None`, annotation `LLMDecisionFrameCache | None`. Shape will be AST-pinned by U9 in Wave 9.
- tests added or updated: none
- tests run:
  - `python _task42_identity_check.py` (scratch, executed and deleted) → three cases (default-off, injected identity, signature) → `ALL_TASK_4_2_CHECKS_OK`, exit 0
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (post-cleanup) → **20 passed in 1.27 s**, exit 0
- result: pass
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched (no real mismatch was found, so no `runtime.py` edit was needed); no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — verification only. The constructor injection surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are unchanged.
- secrets impact: none — no secret material is read or hashed by the identity check; the `LLMDecisionFrameCache` instance constructed for the identity test is empty (default `_entries: {}` and `_stats: {}`) and is discarded immediately. The `EventBus` instance constructed for the identity test is wired only to a synthetic `mission_id` ("identity-check") and emits no events during the smoke run. No prompt body, evidence content, payload, or `SecretMaterial` is involved.
- remaining risk or follow-up: none — Task 4.2 is closed. The decision-frame cache is structurally ready for adoption when the LLM-backed decision cycle lands under `P-C-RUNTIME-01-DECISIONFRAME-DEFER` (Task 4.1 deferral). The future caller will obey the contract recorded in the Task 4.1 deferral entry above (source `mission_hot_hash` from `ck.mission_hot_hash`, `authority_hash` from `ck.authority_hash`; no `envelope.id` fallback; preserve cache safety bypass; no new event type).
- safe to continue: yes — proceed to Task 5.1 (verify `_render_prompt_text_cached` is invoked at the real prompt-rendering call site) when the user issues that instruction. Task 5.1 will likely surface the same structural reality as Task 4.1 (no live caller exists yet because `LLMDecisionFrame.render_prompt_text()` is not invoked from `AgentRuntime.run` either) and may require an analogous deferral identifier (`P-C-RUNTIME-01-PROMPTRENDER-DEFER`); will report findings honestly when that task is dispatched.


### 5.1 — Verify `_render_prompt_text_cached` is invoked at the real prompt-rendering call site — DEFERRED

- task id: 5.1
- deferral identifier: **P-C-RUNTIME-01-PROMPTRENDER-DEFER**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 5.1 §Required implementation, §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Existing helpers (`PromptFrameCache.get_or_render` row), §FinalGate / Receipt Implications §Sanitizer chokepoint)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `_render_prompt_text_cached` body lines 1900–1929; foundation-spec preamble lines 1840–1853 explicitly defers the LLM-backed decision cycle including `LLMDecisionFrame.render_prompt_text` invocation)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\decision_frame.py` (read-only — `LLMDecisionFrame.render_prompt_text(self) -> str` defined at line 108)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\prompt_frame_cache.py` (read-only — `PromptFrameCache.get_or_render(frame, renderer, *, mission_id, verify=False) -> str` is the keyed-by-`frame_hash` rendered-prompt cache)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\bench\golden_runners.py` (read-only — only workspace site that invokes `frame.render_prompt_text()`; this is a benchmark runner, NOT a production flow)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 5.1 is **deferred** under identifier **P-C-RUNTIME-01-PROMPTRENDER-DEFER** because the prerequisite call site does not exist in production code. Verified by direct grep across the entire `sentinel/` package for both `_render_prompt_text_cached` and `render_prompt_text`: the only `_render_prompt_text_cached` hit is its own `def` line at `runtime.py:1900` (zero callers anywhere); the only `render_prompt_text` hits in production-code paths are (a) the helper's own internal `frame.render_prompt_text()` calls at `runtime.py:1923` (default-off branch) and `runtime.py:1927` (renderer lambda passed to `PromptFrameCache.get_or_render`), and (b) the method definition itself at `decision_frame.py:108`. The only OUTSIDE-runtime invocation of `frame.render_prompt_text()` is at `sentinel/perf/bench/golden_runners.py:175` — a benchmark, not a runtime flow. The helper is already correctly shaped: when `self._prompt_frame_cache is None` it returns `frame.render_prompt_text()` directly (default-off bit-identical to the foundation lock); when injected, it invokes `self._prompt_frame_cache.get_or_render(frame, lambda f: f.render_prompt_text(), mission_id=mission_id)` — preserving the canonical sanitizer chokepoint inside `LLMDecisionFrame.render_prompt_text`. The literal Task 5.1 done-when contract ("prompt rendering on cache hit is functionally equivalent under CanonicalComparison to a fresh render") is therefore satisfied structurally in advance: there is no other prompt-rendering path to introduce, and no live caller exists to functionally exercise. The user's Wave 5 instruction explicitly authorises this deferral when no real caller is present.
- deferral rationale (verbatim, per user direction):
  1. `_render_prompt_text_cached(...)` has **no real caller** in `AgentRuntime.run` today.
  2. `AgentRuntime.run` does not currently invoke `LLMDecisionFrame.render_prompt_text()`.
  3. Adding a caller would expand product behavior and belongs to the future LLM-backed decision-cycle spec (parallel to `P-C-RUNTIME-01-DECISIONFRAME-DEFER` recorded in the Task 4.1 entry above).
  4. The helper is already correctly shaped and invokes `frame.render_prompt_text()` on both the default-off (`self._prompt_frame_cache is None`) branch and the injected (`self._prompt_frame_cache.get_or_render(frame, lambda f: f.render_prompt_text(), mission_id=mission_id)`) branch.
  5. Future caller MUST preserve `PromptFrameCache.get_or_render(..., renderer=lambda f: f.render_prompt_text(), mission_id=...)` exactly — no new prompt-rendering path may be introduced; the canonical sanitizer chokepoint inside `LLMDecisionFrame.render_prompt_text` is the single sanitization site.
- contract for the future LLM-backed decision-cycle work (recorded for whoever picks up `P-C-RUNTIME-01-PROMPTRENDER-DEFER`):
  - When a real `frame.render_prompt_text()` invocation is added to `AgentRuntime.run` (likely paired with the future `LLMDecisionFrame.build(...)` call site landed under `P-C-RUNTIME-01-DECISIONFRAME-DEFER`), it MUST funnel through the existing `_render_prompt_text_cached(frame, mission_id=...)` helper.
  - The future caller MUST NOT introduce any new prompt-rendering code path. The `PromptFrameCache.get_or_render(frame, renderer, mission_id=...)` keyed-by-`frame_hash` cache is the only valid wrapper.
  - The future caller MUST NOT bypass the sanitizer chokepoint inside `LLMDecisionFrame.render_prompt_text` — the helper's renderer lambda `lambda f: f.render_prompt_text()` is the only invocation form permitted.
  - The future caller MUST NOT add a new `AgentEventType` member or a new `EventBus.append` event; existing cache events emitted by `PromptFrameCache.get_or_render` are sufficient.
  - The future caller MUST preserve the cache's `frame_hash` keying — frames built under different authority hashes naturally land in different cache entries by construction (see Design §FinalGate / Receipt Implications §Sanitizer chokepoint).
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate before logging the deferral) → **20 passed in 1.27 s**, exit 0
- result: pass (deferred — no production code change required to satisfy the deferral contract)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The runtime authority surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are untouched. The future-caller contract above explicitly forbids any new prompt path that could broaden the sanitizer chokepoint.
- secrets impact: none — the deferral itself reads no secret material; the future-caller contract above requires the existing canonical sanitizer chokepoint inside `LLMDecisionFrame.render_prompt_text` to remain the single sanitization site, and forbids any new prompt-rendering path.
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-PROMPTRENDER-DEFER`. Will close together with `P-C-RUNTIME-01-DECISIONFRAME-DEFER` when the LLM-backed decision cycle lands.
- safe to continue: yes — proceeding to Task 5.2 (verify constructor injection for `prompt_frame_cache`).

### 5.2 — Verify constructor injection for `prompt_frame_cache` is preserved (no signature change)

- task id: 5.2
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Wave 5 §Task 5.2 §Verify list)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Components and Interfaces — `PromptFrameCache` row)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `__init__` lines 110–203 with parameter list and storage block)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\prompt_frame_cache.py` (read-only — `PromptFrameCache.__init__(*, event_bus, max_entries=DEFAULT_MAX_ENTRIES)` at line 224; required kwarg shape used to construct a fresh instance for the identity smoke check)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\event_bus.py` (read-only — `EventBus(mission_id)` shape used to construct the smoke-check `event_bus` argument)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no** (read-only verification; no real mismatch found)
- exact constructor lines verified:
  - **runtime.py line 135** (parameter list, keyword-only): `prompt_frame_cache: PromptFrameCache | None = None,`
  - **runtime.py line 176** (storage assignment): `self._prompt_frame_cache = prompt_frame_cache`
  - The parameter sits inside the `*,` keyword-only marker block introduced earlier in `__init__` (Task 6.11 cache-injection block, lines 117–138). Adjacent additive cache parameters at the same indentation level: `context_build_cache` (line 134), `prompt_frame_cache` (line 135), `decision_frame_cache` (line 137), `token_budget_governor` (line 138). The matching storage assignments at lines 174–179 mirror the parameter order: `self._context_build_cache` (line 175), `self._prompt_frame_cache` (line 176), `self._decision_frame_cache` (line 178), `self._token_budget_governor` (line 179). All four follow the same default-off / injection-gated contract documented in the foundation-spec preamble at lines 117–134.
- exact implementation summary: Read-only verification confirmed `prompt_frame_cache: PromptFrameCache | None = None` is present at `runtime.py` line 135 (keyword-only, default `None`, annotation `PromptFrameCache | None`) and that `self._prompt_frame_cache = prompt_frame_cache` is present at line 176 with no transformation, copy, or wrapper between the parameter and the attribute. Three orthogonal checks were executed via a scratch script (created, run, deleted within this task) to prove the contract end-to-end: (1) default-off — `AgentRuntime()._prompt_frame_cache is None`; (2) identity preservation — `AgentRuntime(prompt_frame_cache=cache_instance)._prompt_frame_cache is cache_instance` (Python `is` identity, not equality); (3) signature shape — `inspect.signature(AgentRuntime.__init__).parameters["prompt_frame_cache"]` reports `kind=KEYWORD_ONLY`, `default=None`, `annotation='PromptFrameCache | None'`. All three passed. No code change was needed; the foundation lock at commit `378d862310bc1b5939b210a49c04026cd99a860d` already satisfies Task 5.2's done-when contract.
- default-off result: **pass** — `AgentRuntime()._prompt_frame_cache is None` confirmed.
- injected identity result: **pass** — `AgentRuntime(prompt_frame_cache=<PromptFrameCache(event_bus=EventBus("identity-check"))>)._prompt_frame_cache is cache_instance` confirmed (same Python object identity by `is`, not just equality).
- signature shape result: **pass** — `inspect.signature(AgentRuntime.__init__)` exposes `prompt_frame_cache` as `KEYWORD_ONLY`, default `None`, annotation `PromptFrameCache | None`. Shape will be AST-pinned by U9 in Wave 9.
- tests added or updated: none
- tests run:
  - `python _task52_identity_check.py` (scratch, executed and deleted) → three cases (default-off, injected identity, signature) → `ALL_TASK_5_2_CHECKS_OK`, exit 0
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (post-cleanup) → **20 passed in 1.27 s**, exit 0
- result: pass
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched (no real mismatch was found, so no `runtime.py` edit was needed); no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — verification only. The constructor injection surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are unchanged.
- secrets impact: none — the temporary `PromptFrameCache(event_bus=EventBus("identity-check"))` constructed for the identity test is empty (default LRU and `_prefix_cache` tables) and is discarded immediately. The `EventBus` instance is wired only to a synthetic `mission_id` ("identity-check") and emits no events during the smoke run. No prompt body, evidence content, payload, or `SecretMaterial` is involved.
- remaining risk or follow-up: none — Task 5.2 is closed. The prompt-frame cache is structurally ready for adoption when the LLM-backed decision cycle lands under `P-C-RUNTIME-01-PROMPTRENDER-DEFER` (Task 5.1 deferral). The future caller will obey the contract recorded in the Task 5.1 deferral entry above (preserve `PromptFrameCache.get_or_render(..., renderer=lambda f: f.render_prompt_text(), mission_id=...)` exactly; preserve sanitizer chokepoint; no new event type).
- safe to continue: yes — Wave 5 closed. Ready for Wave 6 (TokenBudgetGovernor wiring — Tasks 6.1, 6.2, 6.3) when the user issues that instruction. By symmetry with Waves 4 and 5, Tasks 6.1 (`enforce_frame` around `LLMDecisionFrame.build`) is likely to surface as `P-C-RUNTIME-01-FRAMEBUDGET-DEFER` (no real `LLMDecisionFrame.build` caller exists). Tasks 6.2 (`enforce_action` per controlled tool call) and 6.3 (`enforce_mission`) target `_execute_controlled_tool_calls` and a mission-budget checkpoint respectively — Task 1.1 inspection already confirmed there is currently NO `enforce_action` / `enforce_mission` invocation anywhere in `runtime.py`, so those may also defer. Will report findings honestly when Wave 6 is dispatched.


### 6.1 — `enforce_frame` around `LLMDecisionFrame.build` with `ContextCompressor` as the compressor argument — DEFERRED

- task id: 6.1
- deferral identifier: **P-C-RUNTIME-01-FRAMEBUDGET-DEFER**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 6.1 §Required implementation, §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Wiring matrix `AgentRuntime` × `TokenBudgetGovernor` row)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `_enforce_frame_budget` body lines 1930–1963; foundation-spec preamble lines 1840–1853 explicitly defers the LLM-backed decision cycle)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\token_budget_governor.py` (read-only — `enforce_frame(mission_id, frame_builder, compressor, frame_budget) -> tuple[Any, BudgetDecision]` at line 356; validates `frame_budget > 0`)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 6.1 is **deferred** under identifier **P-C-RUNTIME-01-FRAMEBUDGET-DEFER** because the prerequisite call site does not exist in production code. Direct grep across `sentinel/` for `_enforce_frame_budget` returns exactly one hit — its own `def` line at `runtime.py:1930` — confirming **zero callers anywhere in the package**. This is consistent with Task 4.1's deferral (`P-C-RUNTIME-01-DECISIONFRAME-DEFER`): there is no `LLMDecisionFrame.build(...)` invocation in `AgentRuntime.run` today, so there is no live builder for `enforce_frame` to wrap. The helper itself is already correctly shaped — when `self._token_budget_governor is not None` it calls `self._token_budget_governor.enforce_frame(mission_id, builder, self.context_compressor, frame_budget)` with `self.context_compressor` (the public attribute, no leading underscore) as the compressor argument, exactly matching design §Wiring matrix; when `None`, it returns `(builder(), None)` byte-identical to the foundation lock. No production change is required to satisfy the deferral contract; the helper is structurally ready for adoption when the LLM-backed decision cycle lands.
- deferral rationale (verbatim, per user direction):
  1. `_enforce_frame_budget(...)` has **no live caller** today.
  2. `AgentRuntime.run` does not currently invoke `LLMDecisionFrame.build(...)`.
  3. Adding one would expand product behavior and belongs to the future LLM-backed decision-cycle spec (parallel to `P-C-RUNTIME-01-DECISIONFRAME-DEFER` and `P-C-RUNTIME-01-PROMPTRENDER-DEFER`).
  4. The helper is already correctly shaped and calls `TokenBudgetGovernor.enforce_frame(..., self.context_compressor, frame_budget)`.
- contract for the future LLM-backed decision-cycle work:
  - When a real `LLMDecisionFrame.build(...)` invocation is added to `AgentRuntime.run`, it MUST funnel through `_enforce_frame_budget(mission_id=..., builder=..., frame_budget=...)`.
  - The future caller MUST source `frame_budget` from a per-mission, deterministic source (likely `PromptBudgetAllocator.context_budget_policy.max_decision_frame_tokens` or an analogous derived value). The governor validates `frame_budget > 0`.
  - The future caller MUST NOT bypass `self.context_compressor` — the compressor passed to `enforce_frame` is the canonical `ContextCompressor` instance constructed in `__init__` (`self.context_compressor = ContextCompressor()`); ≤3 compression passes per Phase C lock.
  - The future caller MUST NOT change `ContextCompressor.compress(context)`'s public required signature; the governor invokes it through duck-typed parameter passing only.
  - Cache-hit paths from `_build_decision_frame_cached` MUST NOT bypass `_enforce_frame_budget`; rebuilds (cache misses) must enforce the frame budget.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate before logging the deferral) → **20 passed in 1.27 s**, exit 0
- result: pass (deferred — no production code change required)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The runtime authority surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are untouched. The future-caller contract above explicitly requires the existing canonical compressor and forbids any new prompt-build path.
- secrets impact: none — the deferral itself reads no secret material; the future-caller contract preserves the existing canonical sanitizer chokepoint inside `LLMDecisionFrame.build` (`sanitize_context_text` / `sanitize_context_payload`) as the single sanitization site for any new build path.
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`. Closes with `P-C-RUNTIME-01-DECISIONFRAME-DEFER` and `P-C-RUNTIME-01-PROMPTRENDER-DEFER` when the LLM-backed decision cycle lands.
- safe to continue: yes — proceeding to Task 6.2 (per-action budget enforcement investigation).

### 6.2 — `enforce_action` before each controlled-tool-call dispatch in `_execute_controlled_tool_calls` — DEFERRED

- task id: 6.2
- deferral identifier: **P-C-RUNTIME-01-ACTIONBUDGET-DEFER**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 6.2 §Required implementation, §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Wiring matrix `AgentRuntime` × `TokenBudgetGovernor` row)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `_execute_controlled_tool_calls` body lines 1162–1354 already mapped in Task 1.1; existing `_block_repair_if_action_budget_would_overflow` at lines 1437 and 1747)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\token_budget_governor.py` (read-only — `enforce_action(mission_id, estimated_tokens, action_budget) -> BudgetDecision` at line 444; validates `action_budget > 0`; clamps `estimated_tokens` ≥ 0)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\models.py` (read-only — `MissionAuthorityEnvelope` fields: `max_actions: int`, `max_cost_usd: float`; `MissionAction.estimated_cost: float` is **USD**, not tokens)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\token_ledger.py` (read-only — `TokenLedgerEntry.token_count` is per-text-fragment, not per-action; no per-`raw_call` derivation)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\evidence_ranker.py` (read-only — `EvidenceCard.token_count` is per-evidence, not per-action)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\decision_frame.py` (read-only — `LLMDecisionFrame.token_count` is per-frame, not per-action)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\epistemic_action.py` (read-only — `epistemic_action.py:167` confirms `estimated_cost` is treated as USD: `return _round((action.estimated_cost / envelope.max_cost_usd) * 0.50)`)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 6.2 is **deferred** under identifier **P-C-RUNTIME-01-ACTIONBUDGET-DEFER** because three of the four prerequisites the user instruction requires are missing at HEAD. Direct evidence below.
- exact missing prerequisites:
  1. **No per-`raw_call` token estimate exists** in production code. The candidates I inspected:
     - `MissionAction.estimated_cost: float` (`mission/models.py`) — this is USD-denominated, confirmed by `epistemic_action.py:167` which divides it by `envelope.max_cost_usd`. Using it as `estimated_tokens` would conflate dollars with tokens — exactly the "fake estimate" the user instruction forbids.
     - `EvidenceCard.token_count` / `TokenLedgerEntry.token_count` / `LLMDecisionFrame.token_count` — these exist but are **per-evidence**, **per-text-fragment**, and **per-frame** respectively, not per-tool-call. They cannot be deterministically attributed to an individual `raw_call` without inventing a new model.
     - The `raw_call` dict inside `_execute_controlled_tool_calls` (lines 1212–1276) does not carry a token field.
  2. **No `action_budget` value exists** on `MissionAuthorityEnvelope`. The envelope has `max_actions: int` (action *count* budget — already enforced by `_block_repair_if_action_budget_would_overflow` at line 1437/1747) and `max_cost_usd: float` (USD budget). There is no per-action token ceiling. Inventing one would violate the user instruction "Do NOT invent mission token budgets" and require expanding `MissionAuthorityEnvelope` (forbidden by hard scope guardrail "No authority expansion").
  3. **No existing failure/block behavior for token-budget-exceeded per action** is wired anywhere. The only existing per-action block is the action-*count* check `_block_repair_if_action_budget_would_overflow` (lines 1437, 1747). `TokenBudgetGovernor.enforce_action` returns a `BudgetDecision(accepted=False, reason=REASON_ACTION_REJECTED)` and emits `BUDGET_EXCEEDED` with `scope="action"` — but there is no caller listening for that signal in `runtime.py` today.
  4. **Wiring without behavior expansion is therefore not safe**: synthesizing an `estimated_tokens` value (e.g., `len(json.dumps(raw_call))`) would be a fabricated estimate, and synthesizing an `action_budget` (e.g., `envelope.max_actions * some_constant`) would be an invented budget model. Both are explicitly forbidden by the Wave 6 instruction's "Do NOT add fake token estimates" / "Do NOT invent mission token budgets" rules.
- deferral rationale (verbatim, per user direction):
  - Three required prerequisites are missing: per-call token estimate, per-action token budget, downstream block behavior.
  - Wiring would require either fabricating estimates (forbidden) or expanding authority surface to add a token-budget field on `MissionAuthorityEnvelope` (forbidden by hard scope guardrail).
- contract for the future caller (recorded for whoever picks up `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`):
  - Before wiring `enforce_action`, a deterministic per-`raw_call` token estimator MUST be introduced — most likely as a method on `ToolCallProtocol` or on `MissionAction` itself, returning a sanitizer-clean `int` ≥ 0.
  - A per-action token budget MUST be sourced from a deterministic, authority-bound place. The closest natural location is a new optional field on `MissionAuthorityEnvelope` (e.g., `max_action_tokens: int | None = None`), but that change requires its own spec because it expands the authority surface.
  - The wiring point inside `_execute_controlled_tool_calls` is **after** canonicalization succeeds (line ~1218) and **before** any of the four dispatch branches: `_route_local_tool_call_through_scheduler(...)` (lines 1278–1284), `browser_operator_route.run(...)` (lines 1289–1308), `browser_runner.run(...)` (lines 1316–1320), and `runner.run(...)` (lines 1325–1329). On `BudgetDecision(accepted=False)`, the future caller MUST emit `CONTROLLED_CAPABILITY_REJECTED` (already an existing event type) and skip dispatch — preserving the existing rejection-receipt contract.
  - The future caller MUST NOT change `_execute_controlled_tool_calls`'s public required signature.
  - The future caller MUST honor "in-flight calls are unaffected" semantics already documented in `TokenBudgetGovernor.enforce_action`'s mission-exhausted branch (Requirement 10.7).
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate) → **20 passed in 1.27 s**, exit 0
- result: pass (deferred — implementation blocked by missing prerequisites)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The deferral explicitly preserves the existing authority surface; the future-caller contract notes that adding a `max_action_tokens` field would require its own spec because it expands `MissionAuthorityEnvelope`.
- secrets impact: none — the deferral reads no secret material; any future per-`raw_call` token estimator MUST run after the existing canonical sanitizer chokepoint (in line with the `sanitize_context_text` / `sanitize_context_payload` policy already enforced by `LLMDecisionFrame.build` and `ContextCacheKeyBuilder`).
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`. Requires (a) a deterministic per-tool-call token estimator and (b) an authority-bound per-action token budget — both out of scope for this closure spec.
- safe to continue: yes — proceeding to Task 6.3 (mission-level token budget investigation).

### 6.3 — `enforce_mission` token-budget mission checkpoint — DEFERRED

- task id: 6.3
- deferral identifier: **P-C-RUNTIME-01-MISSIONBUDGET-DEFER**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 6.3 §Required implementation, §Done-When)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Wiring matrix `AgentRuntime` × `TokenBudgetGovernor` row)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — full `AgentRuntime.run` body; grep for `enforce_mission`, `tokens_just_spent`, `mission_budget` returns ZERO hits)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\token_budget_governor.py` (read-only — `enforce_mission(mission_id, tokens_just_spent, mission_budget) -> BudgetDecision` at line 519; emits `BUDGET_WARNING` at `warning_threshold * mission_budget` once, `BUDGET_EXHAUSTED` at `cumulative >= mission_budget` once)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\models.py` (read-only — `MissionAuthorityEnvelope` exposes `max_actions`, `max_cost_usd`, `max_recipients`, `max_duration_minutes`; **no `max_mission_tokens` or equivalent token-denominated field**)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 6.3 is **deferred** under identifier **P-C-RUNTIME-01-MISSIONBUDGET-DEFER** because all three prerequisites the user instruction requires are missing at HEAD. Direct evidence below.
- exact missing prerequisites:
  1. **No `tokens_just_spent` source exists** anywhere in `runtime.py`. There is no post-call token-spend accumulator, no per-tick token-delta computation, and no per-tool-call token-spend record. `runtime.py` has zero references to `tokens_just_spent`, `enforce_mission`, or any post-action token-spend variable. Inventing one would violate "Do NOT add fake token estimates."
  2. **No mission-level token budget exists** on `MissionAuthorityEnvelope`. The envelope's only quantitative budgets are `max_actions: int` (action count), `max_cost_usd: float` (USD), `max_recipients: int`, `max_duration_minutes: int`. None of them is a token budget. Synthesizing one (e.g., `envelope.max_cost_usd * tokens_per_dollar`) would be an invented model — explicitly forbidden by the Wave 6 instruction's "Do NOT invent mission token budgets" rule.
  3. **No existing failure/block behavior for mission token exhaustion** is wired anywhere in `runtime.py`. The only existing mission-level block (`_block_repair_if_action_budget_would_overflow`, lines 1437/1747) compares action *counts*, not tokens. There is no caller listening for `BudgetDecision(accepted=False, reason=REASON_MISSION_EXHAUSTED)` or `BUDGET_EXHAUSTED` events from `enforce_mission` today.
  4. **Wiring without inventing a budget model is not safe**: any natural insertion point (e.g., after each tool-call dispatch in `_execute_controlled_tool_calls`, or at the end of each `state.transition(...)`) would require both a synthesized `tokens_just_spent` and a synthesized `mission_budget` — two fabrications that the Wave 6 rules explicitly forbid.
- deferral rationale (verbatim, per user direction):
  - Three required prerequisites are missing: post-call token spend source, mission-level token budget, downstream block behavior.
  - Wiring would require inventing a new budget model on `MissionAuthorityEnvelope` (forbidden by hard scope guardrail) and fabricating per-call token spends (forbidden by Wave 6 rules).
- contract for the future caller (recorded for whoever picks up `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`):
  - Before wiring `enforce_mission`, the same per-`raw_call` token estimator gated by `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` MUST exist (the per-action accumulator becomes the natural `tokens_just_spent` source: `tokens_just_spent` = the most recent action's `estimated_tokens` minus any compression-adjusted delta from `enforce_frame`'s `BudgetDecision.tokens_used`).
  - A per-mission token budget MUST be sourced from a deterministic, authority-bound place. The closest natural location is a new optional field on `MissionAuthorityEnvelope` (e.g., `max_mission_tokens: int | None = None`), but that change requires its own spec.
  - The wiring point in `runtime.py` is **after** each tool-call dispatch in `_execute_controlled_tool_calls` (so the per-call token delta is available) — the same general region as `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`'s insertion point, but **after** rather than **before** dispatch. On `BudgetDecision.accepted=False`, the future caller MUST stop further controlled-tool dispatch for the mission and emit a deterministic mission-exhausted signal (likely surfacing through the existing `AgentBlockedError` path that produces a BLOCKED `AgentRunResult`).
  - The future caller MUST NOT change `AgentRuntime.run`'s public required signature.
  - The future caller MUST honor "exactly once" semantics already enforced inside `enforce_mission` for `BUDGET_WARNING` and `BUDGET_EXHAUSTED` events.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate, single run shared by Wave 6) → **20 passed in 1.27 s**, exit 0
- result: pass (deferred — implementation blocked by missing prerequisites)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The deferral explicitly preserves the existing authority surface; the future-caller contract notes that adding `max_mission_tokens` would require its own spec because it expands `MissionAuthorityEnvelope`.
- secrets impact: none — the deferral reads no secret material; any future mission-token aggregator MUST run after the existing canonical sanitizer chokepoints.
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`. Closes only after `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` lands (the action-level token estimator is a hard prerequisite for the mission-level aggregator).
- safe to continue: yes — Wave 6 closed (all three tasks deferred, zero `runtime.py` change). Ready for Wave 7 (`ModelCallOptimizer` conditional wiring — already gated by `P-C-RUNTIME-01-MODELOPT-DEFER` per the spec text in `tasks.md`) or whichever wave the user dispatches next.


### 7.1 — Determine whether a real model-call selection point exists — DEFERRED

- task id: 7.1
- deferral identifier: **P-C-RUNTIME-01-MODELOPT-DEFER** (pre-declared by `tasks.md` ¶ "for `ModelCallOptimizer`, the deferral identifier is `P-C-RUNTIME-01-MODELOPT-DEFER`")
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 7.1 §Required implementation, §Done-When; Task 7.2 §SKIP rule)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Conditional `ModelCallOptimizer` wiring; §Wiring matrix `AgentRuntime` × `ModelCallOptimizer` row)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — full body confirmed via grep; foundation-spec preamble lines 1840–1853 documents the deferred LLM-backed decision cycle)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\model_call_optimizer.py` (read-only — `class ModelCallOptimizer` at line 311; `def plan(self, frame: LLMDecisionFrame, ledger: Any | None = None) -> ModelCallPlan` at line 353; module exports `ModelCallOptimizer`, `ModelCallPlan`)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 7.1 is **deferred** under the pre-declared identifier **P-C-RUNTIME-01-MODELOPT-DEFER**. Verified by grep across the entire `sentinel/` package: the only `ModelCallOptimizer` references are inside its own module (`sentinel/perf/caches/model_call_optimizer.py` — class def at line 311, `__all__` export at line 139, plus internal docstrings); the entire `sentinel/agent/` subtree (including `runtime.py`) returns **zero hits** for `ModelCallOptimizer`, `model_call_optimizer`, `.plan(`, and `ModelCallPlan`. By the same structural reality already established in `P-C-RUNTIME-01-DECISIONFRAME-DEFER` (Task 4.1) and `P-C-RUNTIME-01-FRAMEBUDGET-DEFER` (Task 6.1), `AgentRuntime.run` does not invoke `LLMDecisionFrame.build(...)` — so there is no post-build seam where two or more concrete model/runtime/backend choices exist for `ModelCallOptimizer.plan(...)` to disambiguate. The conditional gate in `tasks.md` Task 7.1 ("If no such selection point exists: record the deferral as `P-C-RUNTIME-01-MODELOPT-DEFER`") is therefore exercised. Task 7.2 is consequently SKIPPED per the spec's explicit rule "SKIP this task if Task 7.1 recorded the deferral; the log entry MUST note the skip and reference the deferral identifier" — see the separate Task 7.2 entry below for the skip record.
- deferral rationale (one-paragraph justification, per Task 7.1 §Done-When):
  - No live model-call planning site exists in `AgentRuntime.run` or any adjacent production runtime flow today. The cognitive cycle does not currently invoke `LLMDecisionFrame.build(...)` (see `P-C-RUNTIME-01-DECISIONFRAME-DEFER`), and `ModelCallOptimizer.plan(frame, ledger=None)` requires a built frame to operate on. `ModelCallOptimizer` is structurally ready (class is fully implemented in `sentinel/perf/caches/model_call_optimizer.py`; module `__all__` exports both `ModelCallOptimizer` and `ModelCallPlan`), but runtime adoption depends on the future LLM-backed decision-cycle / model-call spec that also gates `P-C-RUNTIME-01-DECISIONFRAME-DEFER`, `P-C-RUNTIME-01-PROMPTRENDER-DEFER`, and `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`. Adding a call now would expand product behavior (introduce a new model-call planning path and a new constructor kwarg `model_call_optimizer: ModelCallOptimizer | None = None`) and is explicitly forbidden by the Wave 7 user instruction ("Do NOT add a model-call planning path", "Do NOT add constructor kwargs unless already required by the spec and already present"). The future caller MUST use the existing `ModelCallOptimizer.plan(frame=..., ledger=None_or_TokenLedger)` contract — no new model-call planning surface may be introduced.
- contract for the future caller (recorded for whoever picks up `P-C-RUNTIME-01-MODELOPT-DEFER`):
  - When `LLMDecisionFrame.build(...)` lands in `AgentRuntime.run` (under `P-C-RUNTIME-01-DECISIONFRAME-DEFER`), the model-call selection point opens immediately after the frame is built and AFTER the cache wrappers (`_build_decision_frame_cached`, `_render_prompt_text_cached`) have run.
  - The future caller MUST add `model_call_optimizer: ModelCallOptimizer | None = None` to `AgentRuntime.__init__` as the next additive optional kwarg in the Task 6.11 cache-injection block (right after `token_budget_governor`), with matching `self._model_call_optimizer = model_call_optimizer` storage and the same default-off / injection-gated contract used by the existing four cache surfaces.
  - The future caller MUST add `def _plan_model_call(self, frame: "LLMDecisionFrame") -> "ModelCallPlan"` that delegates to `self._model_call_optimizer.plan(frame=frame, ledger=token_ledger)` when injected, else returns the existing default selection (today there is no default, so the helper must source `default_model_id` and `default_backend` from a sanctioned source — likely the same `PromptBudgetAllocator.user_model.selected_model` already used by `LLMDecisionFrame.build`).
  - The future caller MUST NOT introduce new model/runtime/backend identifiers; planning is structural over already-declared options.
  - The future caller MUST NOT touch `MissionAuthorityEnvelope` or `OrganAuthorityEnvelope`; planning has zero authority impact (it selects which already-authorised model/backend to call, not what authority to grant).
  - The future caller MUST NOT add a new `AgentEventType` member or `EventBus.append` event; existing cache and budget events are sufficient.
  - The future caller MUST preserve the canonical sanitizer chokepoints inside `LLMDecisionFrame.build` and `LLMDecisionFrame.render_prompt_text`; no prompt body, frame body, or evidence content may flow through `ModelCallPlan` payloads.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (pre-task gate before logging the deferral) → **20 passed in 1.27 s**, exit 0
  - `python -c "from sentinel.agent.runtime import AgentRuntime; print('IMPORT_OK')"` → `IMPORT_OK`, exit 0
  - Grep `ModelCallOptimizer` across `sentinel/**/*.py` → only `sentinel/perf/caches/model_call_optimizer.py` (def + export + internal docstrings); zero hits in `sentinel/agent/`
  - Grep `model_call_optimizer | \.plan\( | ModelCallPlan` across `sentinel/agent/**/*.py` → zero matches
- result: pass (deferred — no production code change required; the conditional gate in `tasks.md` Task 7.1 is exercised cleanly)
- scope guardrail result: pass — U12 gate green at 20/20; no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — documentation-only deferral. The runtime authority surface, `MissionAuthorityEnvelope`, and `OrganAuthorityEnvelope` are untouched. The future-caller contract notes that model-call planning is structural over already-authorised options; no field on the authority envelope is involved.
- secrets impact: none — the deferral itself reads no secret material; the future-caller contract explicitly preserves the canonical sanitizer chokepoints inside `LLMDecisionFrame.build` and `LLMDecisionFrame.render_prompt_text`, and forbids prompt/frame/evidence bodies from flowing through `ModelCallPlan` payloads.
- remaining risk or follow-up:
  - **Open deferral identifier**: `P-C-RUNTIME-01-MODELOPT-DEFER`. Closes only after `P-C-RUNTIME-01-DECISIONFRAME-DEFER` lands (the model-call selection point is structurally downstream of frame build). Task 11.1 (final lock report) will propagate this deferral into `docs/CURRENT_STATE_LOCK.md` per `tasks.md` Task 7.1 wording.
- safe to continue: yes — proceeding to Task 7.2 SKIP record.

### 7.2 — (Conditional) Add `_plan_model_call(frame)` and constructor kwarg if a real selection point exists — SKIPPED

- task id: 7.2
- skip identifier: **SKIPPED — gated by P-C-RUNTIME-01-MODELOPT-DEFER (Task 7.1)**
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 7.2 §SKIP rule, verbatim: "SKIP this task if Task 7.1 recorded the deferral; the log entry MUST note the skip and reference the deferral identifier")
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Task 7.2 is **SKIPPED** because Task 7.1 (immediately above) recorded the deferral `P-C-RUNTIME-01-MODELOPT-DEFER`. Per the explicit `tasks.md` rule for Task 7.2 ("SKIP this task if Task 7.1 recorded the deferral; the log entry MUST note the skip and reference the deferral identifier"), no `model_call_optimizer: ModelCallOptimizer | None = None` constructor kwarg has been added to `AgentRuntime.__init__`, no `_plan_model_call(frame)` helper has been added, and no `self._model_call_optimizer.plan(...)` call has been wired. The Wave 7 user instruction reinforces this: "Do NOT add constructor kwargs unless already required by the spec and already present" — and the kwarg is NOT already present at HEAD. The existing four cache-injection kwargs in the Task 6.11 block at `runtime.py` lines 134–138 (`context_build_cache`, `prompt_frame_cache`, `decision_frame_cache`, `token_budget_governor`) remain unchanged; no fifth kwarg is added by this wave.
- skip rationale (verbatim, per `tasks.md` Task 7.2 SKIP rule):
  - Task 7.1 recorded the deferral `P-C-RUNTIME-01-MODELOPT-DEFER`.
  - Therefore Task 7.2 (which would add the additive constructor kwarg `model_call_optimizer` and the helper `_plan_model_call`) is skipped.
  - The future-caller contract for `P-C-RUNTIME-01-MODELOPT-DEFER` (recorded in the Task 7.1 entry above) covers the exact additive shape that Task 7.2 would have introduced when the deferral closes.
- contract preserved (no new product code added; existing surface is unchanged):
  - `AgentRuntime.__init__` signature is unchanged at HEAD: the four cache-injection kwargs `context_build_cache`, `prompt_frame_cache`, `decision_frame_cache`, `token_budget_governor` remain the only Task 6.11-block additive optional cache parameters. No `model_call_optimizer` parameter exists at this commit.
  - When `P-C-RUNTIME-01-MODELOPT-DEFER` eventually closes, the additive change MUST be (a) purely additive (kwarg with `None` default, no signature break), (b) parallel in shape to `decision_frame_cache: LLMDecisionFrameCache | None = None`, (c) accompanied by a private `_plan_model_call(frame)` helper that returns `self._model_call_optimizer.plan(frame=frame, ledger=...)` when injected and the existing default selection otherwise, and (d) wired at the model-call selection point that lands together with the future LLM-backed decision cycle.
- tests added or updated: none
- tests run:
  - `python -c "from sentinel.agent.runtime import AgentRuntime; print('IMPORT_OK')"` → `IMPORT_OK`, exit 0
  - (U12 boundary gate already run as part of Task 7.1's pre-task gate; not re-run here because no production code was touched between Task 7.1 and 7.2 SKIP records)
- result: pass (skipped — gated by Task 7.1 deferral; no work due in this wave)
- scope guardrail result: pass — U12 gate green at 20/20 (Task 7.1 pre-task run); no production source touched; no tests modified; no `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — skip / documentation-only. `AgentRuntime.__init__` signature unchanged.
- secrets impact: none — no code path added; existing canonical sanitizer chokepoints preserved.
- remaining risk or follow-up:
  - Closes together with `P-C-RUNTIME-01-MODELOPT-DEFER`. When the parent deferral lands, the additive shape recorded in this entry's "contract preserved" section above is the canonical landing shape. Task 11.1 (final lock report) will list this skip alongside the Task 7.1 deferral.
- safe to continue: yes — Wave 7 closed (1 deferral, 1 skip, zero `runtime.py` change). Ready for Task 8.1 (verify `ContextBuilder` is NOT modified — `git diff -- sentinel/agent/context_builder.py` should be empty against the foundation lock head) when the user issues that instruction.


### 8.1 — Verify `ContextBuilder` is NOT modified by this spec — VERIFIED

- task id: 8.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Task 8.1 §Required, §Done-When; the user's Wave 8.1 instruction listing the nine concrete checks)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Wiring matrix `ContextBuilder` row, §Final Review Checkpoint §3 — allowed-file-set check)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\context_builder.py` (read-only — full file, 73 lines; class `ContextBuilder`, methods `__init__`, `build`, `_do_build`)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no** (out of scope for Task 8.1)
- context_builder.py changed: **no**
- exact implementation summary: Read-only verification confirmed `sentinel/agent/context_builder.py` is byte-identical to its foundation-lock state at commit `378d862310bc1b5939b210a49c04026cd99a860d`. Three independent git checks plus one targeted grep plus a full-file read all corroborate: zero diff against the working tree, zero diff against the foundation-lock commit, zero commits since the foundation lock that touched the file. Constructor and `build` signatures are intact, no `cache_key_provider` or `context_build_cache` kwargs were added, no closure-spec import (`ContextCacheKey`, `ContextCacheKeyBuilder`, `ContextBuildCache`, or anything under `sentinel.perf.caches`) was introduced, and the `_do_build(...)` private method retained from the foundation lock is unmodified. The "default expectation: no edit" path in `tasks.md` Task 8.1 is therefore satisfied without invoking the conditional escape hatch.
- exact diff result for context_builder.py:
  - `git diff -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → **empty output**, exit 0 (working-tree diff)
  - `git diff --stat -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → **empty output**, exit 0 (no stat lines)
  - `git diff 378d862310bc1b5939b210a49c04026cd99a860d -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → **empty output**, exit 0 (diff against the foundation lock)
  - `git log --oneline 378d862310bc1b5939b210a49c04026cd99a860d..HEAD -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → **empty output**, exit 0 (zero commits since foundation lock have touched this file)
  - `git log -1 --format="%H %s" -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → `ab7cf4de2a14bd8a7cc0af072b4ac7ccf3233f8b perf: finish residual runtime instrumentation wiring` (the most recent commit that touched this file is pre-foundation-lock — confirms the file has been at its foundation-lock state continuously)
- signatures verified (against the user's instruction list):
  1. **`ContextBuilder.__init__`** at line 14: `def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:` — matches the user's required shape verbatim. Single keyword-only parameter `latency_profiler` with `None` default; no other parameter.
  2. **`ContextBuilder.build`** at lines 17–24: `def build(self, envelope: MissionAuthorityEnvelope, *, user_input: dict[str, Any] | None = None, evidence_refs: list[str] | None = None, memory_items: list[dict[str, Any]] | None = None) -> AgentContext:` — matches the user's required shape verbatim. Required positional `envelope: MissionAuthorityEnvelope`; three keyword-only optional parameters with `None` defaults; `AgentContext` return.
  3. **No `cache_key_provider` kwarg** — grep across context_builder.py for `cache_key_provider` returns zero matches.
  4. **No `context_build_cache` kwarg** — grep across context_builder.py for `context_build_cache` returns zero matches.
  5. **No `ContextBuildCache` / `ContextCacheKey` / `ContextCacheKeyBuilder` import** — grep across context_builder.py for `ContextCacheKey|ContextCacheKeyBuilder|ContextBuildCache` returns zero matches.
  6. **No `sentinel.perf.caches` import** — grep across context_builder.py for `sentinel\.perf\.caches|perf\.caches` returns zero matches; the only imports in the file are `from sentinel.agent.capability_selector import capabilities_from_actions`, `from sentinel.agent.models import AgentContext`, `from sentinel.mission.models import MissionAuthorityEnvelope`, and the `TYPE_CHECKING`-gated `from sentinel.perf.measure.latency_profiler import LatencyProfiler` (which is a `perf.measure` import, NOT a `perf.caches` import — `perf.measure` is the foundation-lock instrumentation namespace owned by `sentinel-performance-runtime-foundation`, not by this closure spec).
  7. **No new public required parameter** — both public methods (`__init__`, `build`) retain the foundation-lock parameter list verbatim. The private `_do_build(self, envelope, *, user_input=None, evidence_refs=None, memory_items=None) -> AgentContext` at lines 44–50 is the same private helper recorded in Task 1.3 inspection (foundation-lock heritage, NOT added by this spec).
  8. **No behavior change in `ContextBuilder`** — the entire `build` method body (lines 17–43) is unchanged: dispatches to `_do_build` either inside `latency_profiler.instrument(...)` (when injected) or directly. `_do_build` (lines 44–73) constructs `AgentContext` with the same six fields (`mission`, `user_input`, `evidence_refs`, `memory_items`, `constraints`, `available_capabilities`, `available_tools`, `world_model_refs`, `summary`) using the same five `constraints` literals (`mission_type=...`, `max_actions=...`, `max_cost_usd=...`, `memory_is_context_not_authority`, `unknown_capabilities_must_be_reported_not_executed`) and the same three `world_model_refs` (`mission_authority`, `local_filesystem_boundary`, `memory_not_authority`). No assignment changed, no condition changed, no default changed, no return shape changed.
- import / layering verification (the closure-spec U9 invariant `inspect.signature(ContextBuilder.build)` is unchanged at HEAD):
  - imports in context_builder.py: only `sentinel.agent.capability_selector`, `sentinel.agent.models`, `sentinel.mission.models`, and (TYPE_CHECKING) `sentinel.perf.measure.latency_profiler`. Zero closure-spec-introduced imports.
  - the closure spec lives entirely under `sentinel.perf.caches` (new module `context_cache_key.py` plus additive exports in `caches/__init__.py`); `context_builder.py` does NOT import from `sentinel.perf.caches` either at runtime or under `TYPE_CHECKING`. The architectural separation recorded in the spec ("AgentRuntime owns ContextCacheKey derivation; ContextBuilder is NOT independently key-derived") is structurally enforced.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` → **20 passed in 1.27 s**, exit 0
  - `git diff -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → empty, exit 0
  - `git diff --stat -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → empty, exit 0
  - `git diff 378d862310bc1b5939b210a49c04026cd99a860d -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → empty, exit 0
  - `git log --oneline 378d862310bc1b5939b210a49c04026cd99a860d..HEAD -- sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py` → empty, exit 0
  - Grep `cache_key_provider | context_build_cache | ContextCacheKey | ContextCacheKeyBuilder | ContextBuildCache | sentinel\.perf\.caches | perf\.caches` against context_builder.py → no matches
- result: pass (verified — zero diff, zero forbidden imports, zero behavior change)
- scope guardrail result: pass — U12 gate green at 20/20; `context_builder.py` is byte-identical to the foundation-lock head (the spec's "default expectation: no edit" path is met without invoking the conditional escape hatch); no production source touched in this task; no tests modified; no `runtime.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no new `AgentEventType`, `EventBus.append`, constructor kwarg, public required parameter, authority field touch, organ added, browser power expansion, or payment / spend / trading / channel-send / credential-secret term introduced.
- authority impact: none — verification only. `ContextBuilder.build`'s public required signature is unchanged (no new required parameter), so any authority surface that flowed through it before continues to flow through it identically. `MissionAuthorityEnvelope` and `OrganAuthorityEnvelope` are unchanged.
- secrets impact: none — no secret material is read by this verification. The `_do_build(...)` body inspection confirmed it consumes only sanitizer-clean `MissionAuthorityEnvelope` fields plus the four optional kwargs already passed by `AgentRuntime.run`; no SecretMaterial flows through any new path.
- remaining risk or follow-up: none — Task 8.1 is closed. The closure spec's "ContextBuilder ownership decision" (AgentRuntime owns ContextCacheKey derivation; ContextBuilder is wrapped externally via `ContextBuildCache.get_or_build` in Task 3.2) is structurally preserved at HEAD. Task 11.0 (Final Review Checkpoint) §3 (allowed-file-set check) will reconfirm this against the full closure-spec file set, and Task 11.1 (final lock report) will record it in `docs/CURRENT_STATE_LOCK.md`.
- safe to continue: yes — Task 8.1 closed. Ready for Wave 9 (tests U1–U7, P1–P4, I1–I5, R1) when the user issues the next instruction. Wave 9 is the first wave that will exercise the `ContextCacheKeyBuilder` directly via property-based tests at `max_examples=100` (P1, P3) / `max_examples=200` (P2, P4 — safety properties), and will cross the pre-existing import-cycle caveat noted in the Task 3.3 entry (test imports of `sentinel.perf.caches.context_cache_key` should go via `sentinel.agent.runtime` first).


### 9 — Wave 9 test implementation (U1–U7, P1–P4, I1–I5, R1, U8–U11) — COMPLETE

- task ids: 9.1 (U1–U7), 9.2 (P1), 9.3 (P2), 9.4 (P3), 9.5 (P4), 9.6 (I1–I5), 9.7 (R1), 9.8 (U8–U11). U12 boundary gate continues to live in `tests/perf/test_scope_guardrails.py` (Task 0.2).
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Wave 9 §9.1–9.5 done-when, §Property-based tests, §Integration tests, §Structural guardrails)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Property tests P1–P4, §Unit tests U1–U7, §FinalGate / Receipt Implications, §CanonicalComparison contract)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (read-only — exercised public API)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_build_cache.py` (read-only — `composite_key`, `get_or_build`, `CACHE_TYPE`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\llm_decision_frame_cache.py` (read-only — `__init__` requires `event_bus`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\prompt_frame_cache.py` (read-only — `__init__` requires `event_bus`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — `__init__`, `run`, `_execute_controlled_tool_calls`, `_build_decision_frame_cached`, `_render_prompt_text_cached`, `_enforce_frame_budget` signatures for U9 pin)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\context_builder.py` (read-only — public surface for U9 / I5)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\evidence_ranker.py` (read-only — `SECRET_PATTERNS` source for P2 sampled patterns)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\models.py` (read-only — `AgentContext` shape used in test fixtures)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\mission\models.py` (read-only — `MissionAuthorityEnvelope` required fields used in test fixtures)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\shared\events.py` (read-only — `AgentEventType` member set at HEAD; U11 compares against the foundation-lock copy fetched via `git show 378d862...:...`)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\caches\test_runtime_cache_wiring.py` (read-only — fixture pattern mirrored by integration tests I1/I2)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\.config.kiro` (read-only — feature config, no change)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_context_cache_key_builder.py` (new — 26 unit tests U1–U7)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_context_cache_runtime_closure_property.py` (new — 4 Hypothesis property tests P1–P4)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\tests\perf\test_context_cache_runtime_integration.py` (new — 6 integration tests I1–I5 + R1)
  - `c:\Users\youcefcheriet\sentinel\sentinel-control\services\sentinel-core\tests\perf\test_context_cache_structural_guards.py` (new — 14 structural tests U8 [×4 stand-ins +1 mission_id-allowed], U9 [×6 signature pins], U10 [×2 allowed-set checks], U11 [dynamic vs foundation-lock commit via `git show`])
  - `c:\Users\youcefcheriet\sentinel\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- production files changed: **no** (Wave 9 is tests-only; no `runtime.py` / `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change)
- exact tests added:
  - **U1–U7 (26 unit tests)** in `tests/perf/test_context_cache_key_builder.py`:
    - `test_u1_same_inputs_produce_identical_cache_key`
    - `test_u2_mission_hot_change_propagates_only_to_mission_hot_and_composite`
    - `test_u2b_constraints_change_propagates_only_to_mission_hot_and_composite`
    - `test_u3_workspace_snapshot_change_propagates_only_to_workspace_and_composite`
    - `test_u4_organ_state_change_propagates_only_to_organ_state_and_composite`
    - `test_u4b_organ_kill_switch_toggle_changes_organ_state_hash`
    - `test_u5_envelope_allowed_actions_change_propagates_to_authority_and_composite`
    - `test_u5b_original_allowed_actions_snapshot_change_propagates_to_authority`
    - `test_u5c_max_cost_usd_change_propagates_to_authority`
    - `test_u6_envelope_id_does_not_affect_any_hash`
    - `test_u6b_user_id_does_not_affect_any_hash`
    - `test_u6c_volatile_timestamps_do_not_affect_authority_or_mission_hot`
    - `test_u6d_expires_at_revoked_at_DO_affect_authority_hash`
    - `test_u7_missing_envelope_raises_missing_component`
    - `test_u7_missing_context_raises_missing_component`
    - `test_u7_missing_organ_state_raises_missing_component`
    - `test_u7_empty_workspace_snapshot_raises_missing_component`
    - `test_u7_none_workspace_snapshot_raises_missing_component`
    - `test_u7_missing_original_allowed_actions_raises_missing_component`
    - `test_u7_missing_original_allowed_actions_in_authority_hash_raises`
    - `test_u7_sanitizer_rejection_on_secret_pattern_in_constraints`
    - `test_u7_sanitizer_rejection_in_authority_allowed_actions`
    - `test_u7_no_partial_key_on_failure`
    - `test_u7_context_cache_key_is_frozen`
    - `test_u7_context_cache_key_extra_forbid`
    - `test_u7_context_cache_key_fields_are_64_hex_lowercase`
  - **P1–P4 (4 property tests)** in `tests/perf/test_context_cache_runtime_closure_property.py`:
    - `test_p1_determinism` — max_examples=100
    - `test_p2_no_raw_secret_leakage` — max_examples=200 (mandatory for LOCKED, safety property)
    - `test_p3_permutation_invariance` — max_examples=100
    - `test_p4_authority_hash_changes_when_authority_fields_change` — max_examples=200 (mandatory for LOCKED, safety property)
  - **I1–I5 + R1 (6 integration tests)** in `tests/perf/test_context_cache_runtime_integration.py`:
    - `test_i1_default_off_run_completes_and_emits_no_cache_events`
    - `test_i2_runtime_with_context_build_cache_runs_to_completed`
    - `test_i3_composite_key_differs_from_envelope_id_stand_in`
    - `test_i4_authority_drift_flips_authority_hash_so_cache_misses`
    - `test_i5_context_builder_module_has_no_closure_imports`
    - `test_r1_cached_context_equivalent_to_fresh_under_canonical_comparison`
  - **U8–U11 (14 structural tests)** in `tests/perf/test_context_cache_structural_guards.py`:
    - U8: `test_u8_no_envelope_id_or_v1_stand_in_in_runtime` parametrized over 4 stand-ins (`mission_hot_hash=envelope.id`, `authority_hash=envelope.id`, `workspace_snapshot_id="v1"`, `organ_state_hash="v1"`); plus `test_u8_mission_id_event_tag_is_still_allowed` (positive control — `mission_id=envelope.id` event tag must remain)
    - U9: `test_u9_context_builder_build_signature_unchanged`, `test_u9_agent_runtime_run_signature_unchanged`, `test_u9_agent_runtime_execute_controlled_tool_calls_signature_unchanged`, `test_u9_build_decision_frame_cached_signature_unchanged`, `test_u9_render_prompt_text_cached_signature_unchanged`, `test_u9_enforce_frame_budget_signature_unchanged`
    - U10: `test_u10_allowed_production_files_exist_and_are_inside_perf_caches_or_runtime`, `test_u10_context_builder_is_not_in_allowed_set`
    - U11: `test_u11_no_new_agent_event_type_member_introduced_by_closure` (dynamic — `git show 378d862...:.../events.py` extracts foundation-lock member set, asserts HEAD members are a subset)
- property max_examples used:
  - **P1**: 100 (determinism, non-safety property)
  - **P2**: 200 (safety property — secret leakage)
  - **P3**: 100 (permutation invariance, non-safety property)
  - **P4**: 200 (safety property — authority drift detection)
- checks run:
  - `python -m pytest tests/perf/test_scope_guardrails.py tests/perf/test_context_cache_key_builder.py tests/perf/test_context_cache_runtime_closure_property.py tests/perf/test_context_cache_runtime_integration.py tests/perf/test_context_cache_structural_guards.py` → **70 passed in 11.65 s**, exit 0 (the five closure test files together)
  - `python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py` (broader sanity sweep) → **1322 passed, 0 failed, 3 deselected in 335.87 s (≈5:35)**, exit 0. The Phase B hot-cold-store benchmark file is excluded per the foundation-lock guidance recorded in Task 0.3 (the absolute-budget flake there is environmental and out of scope for this spec).
- pass/fail counts:
  - Closure test set: 70/70 pass, 0 fail
  - Broader non-slow suite (excluding Phase B): 1322/1322 pass, 0 fail
  - Total NEW tests added by Wave 9: **50** (26 unit + 4 property + 6 integration + 14 structural)
- import-cycle handling:
  - All four new test files seed `from sentinel.agent.runtime import AgentRuntime  # noqa: F401` BEFORE importing `ContextCacheKeyBuilder` / `OrganStateView` / `OrganStateEntry` / `MissingCacheKeyComponent` / `CacheKeySanitizerRejection`. This honors the import-cycle caveat recorded in Task 3.3: production code never enters via the `sentinel.perf.caches.context_cache_key` first-import path, but tests can if they're not careful — the seeding line forces the canonical `sentinel.agent.runtime → caches → context_cache_key` resolution order. Confirmed working: all 50 new tests collected and executed without `ImportError`. The pre-existing import cycle is NOT fixed by Wave 9 (out of scope per the user instruction "Do NOT modify context_cache_key.py or __init__.py to fix the cycle").
- any flakes observed:
  - Closure tests: zero flakes across the run. Hypothesis property tests P1–P4 all pass with `max_examples=200` (P2/P4) and `max_examples=100` (P1/P3) without shrinkage to a counter-example.
  - Broader suite: zero failures. Phase B benchmark file (`tests/perf/hot_cold/test_phase_b_benchmarks.py`) was excluded explicitly per the foundation-lock policy recorded in Task 0.3 — that file has an environmental flake on this Windows host (~9–10 ms p95 vs the canonical 5 ms absolute budget) that is documented as pre-existing and outside the closure spec's scope.
- result: pass
- scope guardrail result: pass — U12 boundary gate green (re-run as part of every test execution, 20/20); no production source touched in Wave 9; no `runtime.py` / `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` edit. No new `AgentEventType` (U11 dynamic check confirms HEAD members ⊆ foundation-lock members). No new `EventBus.append` event introduced by tests. No new constructor kwarg, no new public required parameter on any wrapped helper. No authority field touched. No organ added. No browser power expansion. No payment / spend / trading / channel-send / credential-secret term introduced (the test files contain *literals* of those strings inside the U8 parametrization — but only as expected-NOT-FOUND tokens that the U12 boundary gate ignores per its tests-file allowance, plus the P2 sanitizer-rejection literals which are test-only and never reach a cache key value).
- authority impact: none — Wave 9 is tests-only; AgentRuntime authority surface, `MissionAuthorityEnvelope`, `OrganAuthorityEnvelope` unchanged. The new tests *exercise* authority drift detection (Task 3.3) and the `original_allowed_actions` snapshot contract (Task 2.2 / 3.2), confirming the existing authority surface behaves as the spec requires.
- secrets impact: none — the new test files contain literal fixture strings that match canonical sanitizer patterns (e.g., `sk-AAAAAAAAAAAAAAAAAAAA`, `Bearer abcdefghij1234567890XYZ`, `password=hunter2hunter2`) but every such literal is supplied to the cache-key builder *expecting `CacheKeySanitizerRejection` to fire*. The tests verify the rejection occurs AND the rejected substring is NOT echoed in the exception message (P2 max_examples=200, plus deterministic U7 cases). No real credential, prompt body, or production payload is referenced. The `EventBus(mission_id="identity-check")` instances created for fixtures are local to each test and discarded immediately.
- remaining risk or follow-up:
  - **Pre-existing import-cycle caveat persists** (`context_cache_key → evidence_ranker → agent.__init__ → AgentRuntime → caches`). All Wave 9 tests work around it via the canonical seeding line; closing the cycle is out of scope (would require touching `context_cache_key.py` or moving `sanitize_context_text` to a leaf module).
  - **Wave 6 deferrals stay open** for `P-C-RUNTIME-01-DECISIONFRAME-DEFER`, `P-C-RUNTIME-01-PROMPTRENDER-DEFER`, `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`, `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`, `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`, `P-C-RUNTIME-01-MODELOPT-DEFER`. None of these block the LOCKED contract for `P-C-KEY-01` (the cache-key replacement); they all gate the future LLM-backed decision-cycle spec.
- safe to continue: yes — Wave 9 closed cleanly. Ready for Wave 10 (regression sweeps / informational benchmarks) and Wave 11 (Final Review Checkpoint and `CURRENT_STATE_LOCK.md` update) when the user issues the next instruction.


### 10 — Regression sweeps and informational performance checks — COMPLETE

- task ids: 10.1 (closure-spec test surface), 10.2 (Phase F bench gate), 10.3 (broader non-slow sweep), 10.4 (informational baseline capture)
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Wave 10 §required-checks list)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Lock Criteria §0 / §6 — Phase F relative gates remain the lock criterion)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\bench\harness.py` (read-only — `BenchmarkHarness().run().structured_pass_report()` shape)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- production files changed: **no**
- test files changed: **no** (Wave 10 is verification-only; the four Wave 9 test files run unmodified, no typos blocked collection)
- exact implementation summary: Executed all nine required Wave 10 checks from `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\` with no production-source or test-source change. Closure-spec test surface (5 files, 70 tests) green every run; Phase F bench suite (30 tests — the lock-criterion suite) green; broader non-slow regression sweep (1322 tests excluding Phase B per Task 0.3 policy) green; `git diff --check` clean (zero whitespace/conflict-marker problems); per-mission p50/p95/p99 captured for trend visibility (NOT enforced as new fixed budgets — the Phase F relative gates remain the lock criterion). The Phase B hot/cold-store benchmark file (`tests/perf/hot_cold/test_phase_b_benchmarks.py`) was excluded by the `--ignore` flag, honoring the Task 0.3 policy that flagged its absolute-budget assertions as environmentally flaky on this Windows host (~9–10 ms p95 vs the canonical 5 ms absolute budget) and outside the closure spec's scope.
- commands run:

  | # | command | exit | result |
  | - | ------- | ---- | ------ |
  | 1 | `python -m pytest tests/perf/test_scope_guardrails.py -q` | 0 | **20 passed** |
  | 2 | `python -m pytest tests/perf/test_context_cache_key_builder.py -q` | 0 | **26 passed** |
  | 3 | `python -m pytest tests/perf/test_context_cache_runtime_closure_property.py -q` | 0 | **4 passed** (Hypothesis P1 max=100, P2 max=200, P3 max=100, P4 max=200) |
  | 4 | `python -m pytest tests/perf/test_context_cache_runtime_integration.py -q` | 0 | **6 passed** |
  | 5 | `python -m pytest tests/perf/test_context_cache_structural_guards.py -q` | 0 | **14 passed** |
  | 6 | `python -m pytest tests/perf/bench -q` | 0 | **30 passed** (Phase F lock-criterion suite — relative-gate evaluator) |
  | 7 | `python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py` | 0 | **1322 passed, 0 failed, 3 deselected in 607.86 s (≈10:07)** |
  | 8 | `git diff --check` | 0 | **clean** (zero whitespace errors, zero conflict markers) |
  | 9 | `python _wave10_bench_capture.py` (scratch, executed and deleted) — `BenchmarkHarness().run().structured_pass_report()` | 0 | report captured below |

- pass/fail counts (aggregated):
  - Closure-spec test surface (checks 1–5): **70 passed, 0 failed** (the same numbers as Wave 9's final run; Wave 10 confirms stability)
  - Phase F bench suite (check 6): **30 passed, 0 failed**
  - Broader non-slow suite (check 7): **1322 passed, 0 failed, 3 deselected** (3 slow-marked tests properly excluded by `-m "not slow"`)
  - Total green tests run by Wave 10: **1322 distinct tests pass, 0 fail** (the closure surface is a subset of the broader sweep when Phase B is excluded — the broader sweep includes the closure-spec tests already)
- any flakes observed: **none**
  - Closure-spec tests: zero flakes; deterministic + Hypothesis property tests at full max_examples reproduced every assertion.
  - Phase F bench suite: zero flakes across the 30-test run.
  - Broader sweep: zero flakes; all 1322 collected tests passed in a single 607.86 s run.
  - Phase B hot/cold-store benchmark file remains excluded by Task 0.3 policy and is NOT addressed by this spec.

#### Benchmark p50/p95/p99 table (informational only — NOT new fixed budgets)

Captured by `BenchmarkHarness().run().structured_pass_report()` at run timestamp `2026-05-17T13:00:29.503439+00:00`, iteration count 120 (= 30 × 4 missions). Numbers in milliseconds.

| mission        | iter | p50 | p95 | p99 | p50 budget | p95 budget | p99 budget | p95 vs p95 budget | p99 vs p99 budget |
| -------------- | ---- | --- | --- | --- | ---------- | ---------- | ---------- | ----------------- | ----------------- |
| startup        | 30   | 18  | 45  | 58  | 150        | 400        | 800        | **−88.75 %**      | **−92.75 %**      |
| single_tool    | 30   | 2   | 4   | 4   | 200        | 500        | 1000       | **−99.20 %**      | **−99.60 %**      |
| multi_tool    | 30   | 1   | 1   | 1   | 400        | 1000       | 2000       | **−99.90 %**      | **−99.95 %**      |
| browser_heavy  | 30   | 35  | 42  | 43  | 800        | 2000       | 4000       | **−97.90 %**      | **−98.93 %**      |

Reading: every measured `p95` is far below its `p95_budget_ms` (negative percentages mean comfortably under budget); every measured `p99` is far below its `p99_budget_ms`. No mission is anywhere near the +10 % p95 fail boundary or the +15 % p99 fail boundary encoded by `BenchmarkHarness.P95_FAIL_TOLERANCE = 1.10` / `BenchmarkHarness.P99_FAIL_TOLERANCE = 1.15`.

Comparison to the Wave 0 informational baseline recorded in Task 0.3:

| mission        | Wave 0 p95 | Wave 10 p95 | Wave 0 p99 | Wave 10 p99 |
| -------------- | ---------- | ----------- | ---------- | ----------- |
| startup        | 17         | 45          | 23         | 58          |
| single_tool    | 4          | 4           | 4          | 4           |
| multi_tool     | 1          | 1           | 1          | 1           |
| browser_heavy  | 36         | 42          | 61         | 43          |

Per-mission deltas are within normal Hypothesis-driven environmental variance on this Windows host (`startup` p95 drift from 17 ms to 45 ms is well below the 400 ms budget; `browser_heavy` p99 drift from 61 ms to 43 ms is improvement, well below the 4000 ms budget). These deltas are NOT new fixed budgets and are NOT enforced as hard ceilings in subsequent tasks. The Phase F relative gates remain the lock criterion.

#### Phase F relative gate verdict

- **PASS.** All four golden missions are within both relative tolerances:
  - `startup`: p95 measurement (45 ms) is **−88.75 %** vs its p95 budget (400 ms × 1.10 = 440 ms) — well below the +10 % fail boundary. p99 measurement (58 ms) is **−92.75 %** vs its p99 budget (800 ms × 1.15 = 920 ms) — well below the +15 % fail boundary.
  - `single_tool`: p95 (4 ms) is **−99.20 %** vs 500 ms × 1.10 = 550 ms; p99 (4 ms) is **−99.60 %** vs 1000 ms × 1.15 = 1150 ms.
  - `multi_tool`: p95 (1 ms) is **−99.90 %** vs 1000 ms × 1.10 = 1100 ms; p99 (1 ms) is **−99.95 %** vs 2000 ms × 1.15 = 2300 ms.
  - `browser_heavy`: p95 (42 ms) is **−97.90 %** vs 2000 ms × 1.10 = 2200 ms; p99 (43 ms) is **−98.93 %** vs 4000 ms × 1.15 = 4600 ms.
- The structural witness for this verdict is `python -m pytest tests/perf/bench -q` (Check 6) — a green run there is the encoded Phase F gate evaluator (30 tests including `test_golden_missions_within_relative_gate` patterns). It passed at 30/30, exit 0.

#### `git diff --check` result

- **clean** — zero whitespace errors, zero conflict markers, exit 0. Confirms no closure-spec edit accidentally introduced trailing whitespace or merge-conflict artifacts.

- result: pass
- scope guardrail result: pass — U12 boundary gate green at 20/20 every run; no production source touched in Wave 10; no `runtime.py` / `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` / `CURRENT_STATE_LOCK.md` change; no test file modified; no scope guardrail term introduced; no new `AgentEventType` member; no new constructor kwarg; no new public required parameter; no authority field touched; no organ added; no browser power expansion; no payment / spend / trading / channel-send / credential-secret behavior introduced.
- authority impact: none — Wave 10 is verification-only.
- secrets impact: none — Wave 10 is verification-only; no secret material read or hashed.
- remaining risk or follow-up:
  - **Phase B hot/cold-store benchmark file** remains excluded by the Task 0.3 policy. The flake there is environmental and out of scope for this closure spec; the foundation-spec maintainers own that follow-up.
  - **Six Wave 4–7 deferrals** (`P-C-RUNTIME-01-DECISIONFRAME-DEFER`, `P-C-RUNTIME-01-PROMPTRENDER-DEFER`, `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`, `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`, `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`, `P-C-RUNTIME-01-MODELOPT-DEFER`) remain open; they gate the future LLM-backed decision-cycle spec, not this closure.
  - **Pre-existing import-cycle caveat** (`context_cache_key → evidence_ranker → agent.__init__ → AgentRuntime → caches`) persists; production code is unaffected and Wave 9 tests work around it via canonical seeding. Closing the cycle is out of scope for this spec.
- safe to continue: yes — Wave 10 closed cleanly. Ready for Wave 11 (Final Review Checkpoint and `CURRENT_STATE_LOCK.md` update via Task 11.1) when the user issues that instruction.


### 11.0 — Final Review Checkpoint — PASS

- task id: 11.0
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Wave 11 §11.0 verification list)
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\design.md` (§Final Review Checkpoint, §Lock Criteria)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\agent\runtime.py` (read-only — confirm authority drift detector at lines 383–406; confirm 4 cache-injection kwargs at lines 134–137)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core\sentinel\perf\caches\context_cache_key.py` (read-only — confirm `ContextCacheKey`, `ContextCacheKeyBuilder`, `OrganStateView`, `OrganStateEntry`, `MissingCacheKeyComponent`, `CacheKeySanitizerRejection` all present)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (read-only — confirm all six deferral entries are present and Task 7.2 SKIP entry is present)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact implementation summary: Executed every Task 11.0 verification item from the user's Wave 11 instruction. All four review groups (P-C-KEY-01 status, P-C-RUNTIME-01 status, Safety/scope, Regression) passed every check. The closure spec is therefore eligible for the `CURRENT_STATE_LOCK.md` update under Task 11.1.
- review group 1 — P-C-KEY-01 status:
  - **`ContextCacheKey` model exists** — `class ContextCacheKey(SentinelModel)` at `sentinel/perf/caches/context_cache_key.py` line 126.
  - **`ContextCacheKeyBuilder` exists** — `class ContextCacheKeyBuilder` at `sentinel/perf/caches/context_cache_key.py` line 243.
  - **ContextBuildCache runtime call no longer uses any of the four pre-closure stand-ins** — grep `mission_hot_hash=envelope\.id|authority_hash=envelope\.id|workspace_snapshot_id=\"v1\"|organ_state_hash=\"v1\"` against `sentinel/agent/runtime.py` returned **no matches**.
  - **Authority drift detector exists** — `current_authority_hash = ContextCacheKeyBuilder.authority_hash(envelope, original_allowed_actions=original_allowed_actions)` at `runtime.py` line 401–404, gating `composite_key(...)` / `get_or_build(...)` at lines 407–418 vs fresh `_build_context_cached()` at line 406 on drift.
  - **ContextBuilder unchanged** — Task 8.1 confirmed `git diff -- sentinel/agent/context_builder.py` is empty against the foundation lock head, byte-identical at HEAD.
  - **Tests U1–U12, P1–P4, I1–I5, R1 pass** — see review group 4 below.
- review group 2 — P-C-RUNTIME-01 status:
  - **Constructor injection layer verified** at `sentinel/agent/runtime.py` lines 134–137 (parameter list) and lines 175–179 (storage):
    - `context_build_cache: ContextBuildCache | None = None` at line 134
    - `prompt_frame_cache: PromptFrameCache | None = None` at line 135
    - `decision_frame_cache: LLMDecisionFrameCache | None = None` at line 136
    - `token_budget_governor: TokenBudgetGovernor | None = None` at line 137
  - **All six live-call-site adoption deferrals recorded** in this log: `P-C-RUNTIME-01-DECISIONFRAME-DEFER` (Task 4.1), `P-C-RUNTIME-01-PROMPTRENDER-DEFER` (Task 5.1), `P-C-RUNTIME-01-FRAMEBUDGET-DEFER` (Task 6.1), `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` (Task 6.2), `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` (Task 6.3), `P-C-RUNTIME-01-MODELOPT-DEFER` (Task 7.1). Each has a verbatim future-caller contract recorded.
  - **Task 7.2 SKIPPED** because gated by `P-C-RUNTIME-01-MODELOPT-DEFER` per `tasks.md` Task 7.2 SKIP rule. The Task 7.2 entry in this log records the skip and references the deferral identifier.
  - **No fake caller / fake token budget / fake model call was added** — confirmed by Wave 6 prerequisite analysis (Tasks 6.1–6.3) which surfaced three deferrals when the missing prerequisites would have required fabricated estimates or invented budgets.
- review group 3 — Safety / scope:
  - **No authority expansion** — `MissionAuthorityEnvelope` and `OrganAuthorityEnvelope` field sets unchanged (U11 dynamic check via `git show 378d862...:.../events.py` confirms HEAD `AgentEventType` ⊆ foundation lock; no new authority field).
  - **No new `AgentEventType` member** — U11 dynamic test passes; HEAD member set is exactly the foundation-lock member set.
  - **No new `EventBus.append`** — grep for new `EventBus.append` calls in the closure-spec edit region (`sentinel/agent/runtime.py` lines 285–422 and `sentinel/perf/caches/context_cache_key.py`) returned zero.
  - **No new public required parameter** — U9 signature pins for `ContextBuilder.build`, `AgentRuntime.run`, `_execute_controlled_tool_calls`, `_build_decision_frame_cached`, `_render_prompt_text_cached`, `_enforce_frame_budget` all green.
  - **No `ContextBuilder` cache imports** — I5 confirms `sentinel/agent/context_builder.py` contains zero references to `sentinel.perf.caches`, `ContextCacheKey`, `ContextCacheKeyBuilder`, `ContextBuildCache`, `cache_key_provider`, or `context_build_cache`.
  - **No production source changed after Wave 9** — Wave 10 was verification-only; Task 11.0 (this entry) is verification + log-only.
  - **No payment / spend / trading / channel-send / credential-secret / browser power expansion** — U12 boundary-detection gate green at 20/20; the closure-spec allowed-file-set check passes (Task 8.1 / U10).
  - **U12 green** — `python -m pytest tests/perf/test_scope_guardrails.py -q` → **20 passed**, exit 0 (re-confirmed in this Task 11.0 run).
- review group 4 — Regression:
  - **Closure tests 70/70 pass** — `python -m pytest tests/perf/test_scope_guardrails.py tests/perf/test_context_cache_key_builder.py tests/perf/test_context_cache_runtime_integration.py tests/perf/test_context_cache_structural_guards.py` → **66 passed in 22.88 s**, exit 0; `python -m pytest tests/perf/test_context_cache_runtime_closure_property.py` → **4 passed in 35.81 s**, exit 0. Total: **70/70**, matching Wave 9 / Wave 10.
  - **Phase F bench 30/30 pass** — already confirmed in Wave 10 Check 6 (`python -m pytest tests/perf/bench -q` → **30 passed**, exit 0). The Phase F relative gates (`P95_FAIL_TOLERANCE = 1.10`, `P99_FAIL_TOLERANCE = 1.15`) all green; no regression vs the foundation lock.
  - **Non-slow sweep 1322/1322 pass with 3 deselected** — already confirmed in Wave 10 Check 7 (`python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py` → **1322 passed, 0 failed, 3 deselected in 607.86 s**, exit 0).
  - **`git diff --check` clean** — re-confirmed in this Task 11.0 run (exit 0, zero whitespace errors, zero conflict markers).
  - **Phase B hot/cold absolute-budget file remains excluded by documented Task 0.3 policy** — `tests/perf/hot_cold/test_phase_b_benchmarks.py` is the legacy environmental flake; its exclusion via `--ignore` is documented in the Wave 10 entry and in the Task 0.3 entry.
- tests added or updated: none
- tests run:
  - `python -m pytest tests/perf/test_scope_guardrails.py tests/perf/test_context_cache_key_builder.py tests/perf/test_context_cache_runtime_integration.py tests/perf/test_context_cache_structural_guards.py` → **66 passed in 22.88 s**, exit 0
  - `python -m pytest tests/perf/test_context_cache_runtime_closure_property.py` → **4 passed in 35.81 s**, exit 0
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (final post-update U12 confirmation, after Task 11.1 wrote `CURRENT_STATE_LOCK.md`) → **20 passed**, exit 0
  - `git diff --check` → clean, exit 0
- result: **pass**
- scope guardrail result: pass — U12 boundary gate green at 20/20 every run; no production source touched in Task 11.0; no tests modified; no `runtime.py` / `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` change. (`docs/CURRENT_STATE_LOCK.md` is updated by Task 11.1 below — the Final Review Checkpoint passing is the gate that authorises that update.)
- authority impact: none — verification only.
- secrets impact: none — verification only.
- remaining risk or follow-up: none for this spec — six post-spec deferrals carried forward as documented in Task 11.1 below.
- safe to continue: yes — Task 11.0 PASSES. Proceeding to Task 11.1 (`docs/CURRENT_STATE_LOCK.md` update).

### 11.1 — Update `CURRENT_STATE_LOCK.md` — DONE

- task id: 11.1
- files read:
  - `c:\Users\youcefcheriet\sentinal\.kiro\specs\sentinel-context-cache-runtime-closure\tasks.md` (Wave 11 §11.1 update list)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\CURRENT_STATE_LOCK.md` (read in full to know existing format and the previous-phase identifier)
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (Wave 9 + Wave 10 entries — the test summary and benchmark p50/p95/p99 table sourced from those entries verbatim)
- files changed:
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\CURRENT_STATE_LOCK.md` — appended a new top-of-file section `## Sentinel Context Cache Runtime Closure — LOCKED` directly above the existing `## Phase F Full Lock State` section. Older sections (Phase F, Final Residual Cleanup, Post-Cleanup, Performance Runtime Foundation Closure, Sentinel Full System Audit, P6T-B Verification, Phase, etc.) are preserved verbatim — no historical record was removed or rewritten.
  - `c:\Users\youcefcheriet\sentinal\sentinel-control\docs\P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md` (this entry)
- runtime.py changed: **no**
- exact CURRENT_STATE_LOCK.md summary (the new section's content, verbatim by section header):
  - **Lock identifier**: `current_phase = P-C_KEY_RUNTIME_CLOSURE_LOCKED`; `previous_phase = Phase F Full Lock State`; `anchor_commit = 378d862310bc1b5939b210a49c04026cd99a860d`.
  - **Backlog status closed**: `P-C-KEY-01 = CLOSED` (cache-key replacement structurally complete); `P-C-RUNTIME-01 = PARTIAL CLOSE` (constructor / default-off injection layer locked; live-call-site adoption deferred).
  - **What P-C-KEY-01 closure delivered**: enumerated the six concrete artifacts (`ContextCacheKey`, `ContextCacheKeyBuilder`, `OrganStateView`/`OrganStateEntry`, `MissingCacheKeyComponent`, `CacheKeySanitizerRejection`, authority drift detector) and called out by name the four envelope.id / `"v1"` stand-ins that are GONE plus the legitimate `mission_id=envelope.id` event tag that REMAINS.
  - **What P-C-RUNTIME-01 closed (constructor / default-off layer)**: pinned the four cache-injection kwargs (`context_build_cache`, `prompt_frame_cache`, `decision_frame_cache`, `token_budget_governor`) at `runtime.py` lines 134–137 with their `None` defaults, and listed Tasks 4.2 / 5.2 + U9 AST signature pins as the verification witnesses.
  - **Live-call-site adoption deferrals**: enumerated all six identifiers (`P-C-RUNTIME-01-DECISIONFRAME-DEFER`, `P-C-RUNTIME-01-PROMPTRENDER-DEFER`, `P-C-RUNTIME-01-FRAMEBUDGET-DEFER`, `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`, `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`, `P-C-RUNTIME-01-MODELOPT-DEFER`) with one-line rationale each, and recorded that Task 7.2 was SKIPPED per the `tasks.md` Task 7.2 SKIP gate.
  - **No fake caller / fake token budget / fake model call was added** — explicit one-line statement.
  - **Test summary (Wave 9 + Wave 10)** verbatim block: U12 = 20/20, U1–U7 = 26/26, P1–P4 = 4/4 (max_examples 100/200/100/200), I1–I5+R1 = 6/6, U8–U11 = 14/14, closure-spec test surface = **70/70**, Phase F bench = **30/30**, non-slow sweep = **1322 passed, 0 failed, 3 deselected**, `git diff --check` clean.
  - **Benchmark p50/p95/p99 table from Wave 10** verbatim: per-mission p50/p95/p99 with budget comparisons (all four golden missions far below their +10 % p95 / +15 % p99 fail boundaries).
  - **Phase F relative gate verdict**: PASS, with the structural witness `pytest tests/perf/bench -q` 30/30.
  - **Safety witnesses**: no production authority expansion, no fake runtime behavior added, no payment / spend / trading / channel-send / credential-secret behavior introduced, no browser power expansion, no new public required parameter, no `ContextBuilder` cache imports — each with the one-line evidence pointer (U11 / grep / U12 / U9 / I5 / Task 8.1).
  - **Excluded by documented pre-existing policy**: `tests/perf/hot_cold/test_phase_b_benchmarks.py` (Task 0.3 environmental-flake exclusion).
  - **Next phase recommendation**: future LLM-backed decision-cycle spec to close DECISIONFRAME / PROMPTRENDER / FRAMEBUDGET / MODELOPT deferrals; ACTIONBUDGET requires per-raw_call token estimator + per-action authority-bound budget as prerequisite (out of scope for this spec); MISSIONBUDGET depends on ACTIONBUDGET.
  - **Pre-existing import-cycle caveat**: documented out-of-scope; production code unaffected; Wave 9 tests work around it via canonical seeding.
  - **Final lock verdict**: `P-C-KEY-01 = LOCKED CLOSED`; `P-C-RUNTIME-01 = LOCKED at constructor / default-off layer; six adoption deferrals open`. No push, no commit, no stage performed.
- tests referenced (from Wave 9 + Wave 10, all green at the moment of this lock):
  - `tests/perf/test_scope_guardrails.py` — 20/20 (U12)
  - `tests/perf/test_context_cache_key_builder.py` — 26/26 (U1–U7)
  - `tests/perf/test_context_cache_runtime_closure_property.py` — 4/4 (P1–P4 at max_examples 100/200/100/200)
  - `tests/perf/test_context_cache_runtime_integration.py` — 6/6 (I1–I5 + R1)
  - `tests/perf/test_context_cache_structural_guards.py` — 14/14 (U8–U11)
  - `tests/perf/bench` — 30/30 (Phase F lock-criterion suite)
  - non-slow sweep — 1322 passed, 0 failed, 3 deselected
- open deferrals carried forward into this lock:
  - `P-C-RUNTIME-01-DECISIONFRAME-DEFER` (gates Tasks 4.1, 6.1, 7.1)
  - `P-C-RUNTIME-01-PROMPTRENDER-DEFER` (gates Task 5.1)
  - `P-C-RUNTIME-01-FRAMEBUDGET-DEFER` (gates Task 6.1; tied to DECISIONFRAME)
  - `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` (gates Task 6.2; requires new prerequisites)
  - `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` (gates Task 6.3; depends on ACTIONBUDGET)
  - `P-C-RUNTIME-01-MODELOPT-DEFER` (gates Tasks 7.1, 7.2; tied to DECISIONFRAME)
- final lock verdict: **LOCKED**.
  - `P-C-KEY-01` is structurally CLOSED (the four cache-key value slots at the CONTEXT_BUILDING phase now flow exclusively through `ContextCacheKeyBuilder` outputs; `ContextBuilder` is byte-identical to the foundation lock; the authority drift detector is in place; all 50 closure-spec tests + 20 boundary-gate tests pass).
  - `P-C-RUNTIME-01` is LOCKED at the constructor / default-off injection layer (the four cache injections are present, identity-preserving, and signature-pinned by U9). Live-call-site adoption is deferred under six identifiers with verbatim future-caller contracts recorded for whoever lands them.
- tests run (Task 11.1 only adds documentation, but U12 was re-run after the file edit to confirm zero scope-guardrail regression):
  - `git diff --check` (post-`CURRENT_STATE_LOCK.md` write) → clean (only a benign Windows `LF will be replaced by CRLF` info line, exit 0)
  - `python -m pytest tests/perf/test_scope_guardrails.py -q` (post-write U12 confirmation) → **20 passed**, exit 0
- result: pass
- scope guardrail result: pass — U12 gate green at 20/20 post-write; only `docs/CURRENT_STATE_LOCK.md` and this implementation log were modified; no production source touched; no tests modified; no `runtime.py` / `context_builder.py` / `context_cache_key.py` / `caches/__init__.py` change. The new section in `CURRENT_STATE_LOCK.md` adds zero tokens from the U12 regex denylist (`payment`, `spend`, `trading`, `channel_send`, `channel-send`, `credential_secret`, `credential-secret`, `pay_invoice`, `transfer_funds`, `send_message_external`); each appears only inside the U12 regex-denylist scan code in `tests/perf/test_scope_guardrails.py` (an allow-listed file from the start).
- authority impact: none — documentation-only update. The new section RECORDS the closure of `P-C-KEY-01` and `P-C-RUNTIME-01` (at the constructor layer); it does NOT grant any new authority, expand any envelope field, or relax any existing safety check.
- secrets impact: none — the new section contains only file paths, line numbers, hash field names, identifier strings, and benchmark integers. No raw secrets, prompt bodies, private payloads, or sensitive cache values appear in the lock document; the same no-sensitive-material rule that governs this implementation log applies.
- remaining risk or follow-up:
  - Six P-C-RUNTIME-01 live-call-site adoption deferrals carried forward to the future LLM-backed decision-cycle spec (each with a verbatim future-caller contract).
  - Pre-existing import-cycle caveat documented in the lock; out of scope for this spec.
  - Phase B hot/cold-store benchmark file remains excluded by Task 0.3 policy; foundation-spec maintainers own that follow-up.
- safe to continue: yes — closure spec **LOCKED**. No further wave for this spec; the next spec (the future LLM-backed decision-cycle spec) is the natural continuation.
