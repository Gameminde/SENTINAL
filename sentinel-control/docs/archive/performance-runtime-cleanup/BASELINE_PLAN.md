# Phase A-E Baseline Plan

Status: proposal only. Do not commit yet. Do not start Phase F yet.

## 1. Current Dirty Tree Classification

Fresh audit source:

```bash
git status --short
git status --short -- .kiro sentinel-control/services/sentinel-core/sentinel/perf sentinel-control/services/sentinel-core/tests/perf sentinel-control/services/sentinel-core/sentinel/agent/runtime.py sentinel-control/services/sentinel-core/sentinel/mission/runner.py
git diff -- sentinel-control/services/sentinel-core/pyproject.toml
```

### Phase A-E Performance-Runtime Files

These appear to be the core Phase A-E performance-runtime baseline surface:

```text
sentinel-control/services/sentinel-core/sentinel/perf/
sentinel-control/services/sentinel-core/tests/perf/
sentinel-control/services/sentinel-core/sentinel/shared/events.py
sentinel-control/services/sentinel-core/pyproject.toml
```

Observed details:

- `sentinel/perf/` is untracked and contains `measure`, `hot_cold`, `caches`, `sched`, `workspace`, and `bench/__init__.py`.
- `tests/perf/` is untracked and contains Phase A-E tests for measurement, hot/cold storage, caches, scheduler, and workspace.
- `sentinel/shared/events.py` is untracked and is likely Phase A/D support because the performance runtime and scheduler reports reference shared EventBus / AgentEventType additions.
- `pyproject.toml` is modified only to add the `slow` pytest marker for benchmark/property-test selection.

### Lock Reports / Backlog Docs

These files exist under the spec folder:

```text
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
```

Important git fact:

```text
.kiro is ignored by .gitignore via the top-level "*" rule.
```

If these reports must enter the baseline commit, they require explicit forced staging:

```bash
git add -f .kiro/specs/sentinel-performance-runtime-foundation/tasks.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/design.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/requirements.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
```

### Spec Files

Spec files exist and were read during the audit:

```text
.kiro/specs/sentinel-performance-runtime-foundation/tasks.md
.kiro/specs/sentinel-performance-runtime-foundation/design.md
.kiro/specs/sentinel-performance-runtime-foundation/requirements.md
```

Phase F task order confirmed:

```text
11.1, 11.6, 11.2, 11.3, 11.5, 11.4, 11.7, 12
```

These files are also ignored by default because `.kiro` is ignored.

### AgentRuntime / MissionRunner Dirty Files

Potential Phase A-E baseline candidates:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
```

Observed Phase A-E relevant changes:

- `AgentRuntime` has optional default-off injections for profilers, caches, scheduler, and backpressure controller.
- `AgentRuntime` includes scheduler-routing helper logic for local controlled-capability tool calls.
- `MissionRunner` has optional default-off injections for latency profiler, hot cache, cold store, and receipt index.

Manual triage required:

- `AgentRuntime` also contains full-system-audit changes such as `CoreFinalGate`, memory-not-authority boundary checks, and final-gate runtime wiring.
- `MissionRunner` also contains full-system-audit changes such as cancellation/revocation and browser route exception wiring.
- These may be valid prior-phase dependencies, but they are not exclusively Phase A-E performance-runtime changes.

### Unrelated Browser / Organ / Runtime Dirty Files

These must not enter the Phase A-E baseline unless separately proven as Phase A-E dependencies:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/services/sentinel-core/sentinel/agent/browser/*
sentinel-control/services/sentinel-core/sentinel/organs/browser/*
sentinel-control/services/sentinel-core/sentinel/organs/*
sentinel-control/services/sentinel-core/sentinel/agent/cognitive_cycle.py
sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py
sentinel-control/services/sentinel-core/sentinel/agent/context_compressor.py
sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py
sentinel-control/services/sentinel-core/sentinel/agent/event_bus.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/evidence_ranker.py
sentinel-control/services/sentinel-core/sentinel/agent/exceptions.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
sentinel-control/services/sentinel-core/sentinel/agent/invariants.py
sentinel-control/services/sentinel-core/sentinel/agent/models.py
sentinel-control/services/sentinel-core/sentinel/agent/phases.py
sentinel-control/services/sentinel-core/sentinel/agent/state.py
sentinel-control/services/sentinel-core/sentinel/agent/supervisor.py
sentinel-control/services/sentinel-core/sentinel/learning/self_improvement.py
sentinel-control/services/sentinel-core/sentinel/mission/autonomy.py
sentinel-control/services/sentinel-core/sentinel/mission/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/mission/risk.py
sentinel-control/services/sentinel-core/tests/test_agent_invariants.py
sentinel-control/services/sentinel-core/tests/test_p6_external_organ_foundry.py
sentinel-control/services/sentinel-core/tests/test_p6_subquadratic_agent_context_engine.py
```

`CURRENT_STATE_LOCK.md` is modified with a large full-system-audit decision record and browser structural lock notes. It is not a clean Phase A-E performance-runtime baseline file.

### Unknown / Unclassified Files

These require manual triage before any baseline commit:

```text
sentinel-control/services/sentinel-core/_junit.xml
sentinel-control/services/sentinel-core/_tmp_cold_store_smoke.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/sentinel/mission/cancellation.py
sentinel-control/services/sentinel-core/sentinel/mission/exceptions.py
sentinel-control/services/sentinel-core/sentinel/mission/gate_sequence.py
sentinel-control/services/sentinel-core/sentinel/organs/exceptions.py
sentinel-control/services/sentinel-core/tests/test_agent_phases.py
sentinel-control/services/sentinel-core/tests/test_browser_organ_final_gate.py
sentinel-control/services/sentinel-core/tests/test_browser_receipt_wrapper.py
sentinel-control/services/sentinel-core/tests/test_decision_frame_mandatory_params.py
sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py
sentinel-control/services/sentinel-core/tests/test_kill_switch_reactive_property.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_bias.py
sentinel-control/services/sentinel-core/tests/test_memory_not_authority_property.py
sentinel-control/services/sentinel-core/tests/test_mission_runner_browser_operator_route_rejected.py
sentinel-control/services/sentinel-core/tests/test_sanitization_property.py
sentinel-control/services/sentinel-core/tests/test_self_improvement.py
sentinel-control/services/sentinel-core/tests/test_shared_events_layering.py
sentinel-control/services/sentinel-core/tests/test_toctou_binding_property.py
sentinel-control/services/sentinel-core/tests/test_trace_hash_property.py
```

## 2. Proposed Staging Groups

### Group 1: Spec Files and Lock / Backlog Reports

Stage only if the user accepts that `.kiro` spec artifacts should be committed despite being ignored:

```bash
git add -f .kiro/specs/sentinel-performance-runtime-foundation/tasks.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/design.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/requirements.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_B_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_C_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_LOCK_REPORT.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_D_BACKLOG.md
git add -f .kiro/specs/sentinel-performance-runtime-foundation/PHASE_E_LOCK_REPORT.md
```

Do not stage:

```text
.kiro/specs/sentinel-performance-runtime-foundation/PHASE_F_LOCK_REPORT.md
```

It does not exist and Phase F has not started.

### Group 2: `sentinel/perf/*` Modules

Stage the performance runtime package as one unit:

```bash
git add sentinel-control/services/sentinel-core/sentinel/perf
```

Expected contents:

```text
sentinel/perf/measure/*
sentinel/perf/hot_cold/*
sentinel/perf/caches/*
sentinel/perf/sched/*
sentinel/perf/workspace/*
sentinel/perf/bench/__init__.py
```

Do not stage ignored cache artifacts:

```text
__pycache__/
*.pyc
```

### Group 3: `tests/perf/*` Tests

Stage the performance test package as one unit:

```bash
git add sentinel-control/services/sentinel-core/tests/perf
```

Expected contents:

```text
tests/perf/measure/*
tests/perf/hot_cold/*
tests/perf/caches/*
tests/perf/sched/*
tests/perf/workspace/*
```

Do not stage ignored cache artifacts:

```text
__pycache__/
*.pyc
```

### Group 4: AgentRuntime / MissionRunner Changes That Belong to Phases A-E

Stage only after a diff review confirms the staged hunks are the default-off performance-runtime wiring:

```bash
git add -p sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
git add -p sentinel-control/services/sentinel-core/sentinel/mission/runner.py
git add sentinel-control/services/sentinel-core/pyproject.toml
```

Expected allowed hunks:

- profiler injection
- cache injection
- scheduler/backpressure injection
- hot/cold receipt wiring
- `slow` pytest marker
- comments documenting default-off behavior and no raw secret leakage

Potential support file requiring explicit proof:

```bash
git add sentinel-control/services/sentinel-core/sentinel/shared/events.py
```

Only stage `sentinel/shared/events.py` if it is proven to be the shared EventBus / AgentEventType layer required by Phase A-D performance-runtime tests.

Do not stage full-system-audit-only hunks into the Phase A-E baseline unless the user explicitly approves a broader baseline.

### Group 5: Unrelated Dirty Files That Must NOT Enter the Baseline Commit

Do not stage broad paths such as:

```bash
git add sentinel-control
git add sentinel-control/services/sentinel-core/sentinel
git add sentinel-control/services/sentinel-core/tests
```

Do not stage browser/organ/full-system-audit files unless a file-specific diff proves it is required by Phase A-E:

```text
sentinel/agent/browser/*
sentinel/organs/browser/*
sentinel/organs/*
sentinel/agent/final_gate.py
sentinel/agent/invariants.py
sentinel/mission/cancellation.py
sentinel/mission/gate_sequence.py
CURRENT_STATE_LOCK.md
browser/final-gate/unit test files
memory-not-authority/full-system-audit test files
```

## 3. Proposed Commit Message

```text
baseline: lock performance runtime foundation phases A-E
```

## 4. Safety Checks Before Commit

Run from repository root:

```bash
git diff --stat
git status --short
```

Run from `sentinel-control/services/sentinel-core`:

```bash
python -m pytest tests/perf/ -m "not slow" -q
python -m pytest tests/test_agent_runtime.py -q
```

Known latest audit results before this plan:

```text
python -m pytest tests/perf/ --collect-only -q
  exit 0

python -m pytest tests/perf/ -m "not slow" -q
  exit 0

python -m pytest tests/test_agent_runtime.py -q
  14 passed
```

After staging and before commit, run:

```bash
git diff --cached --stat
git diff --cached --name-only
```

The cached file list must contain only Groups 1-4 approved files.

## 5. Explicit Warning

Do not stage unrelated browser/organ files unless they are proven Phase D/E dependencies.

Do not use broad staging commands.

Do not close these backlog items in the baseline:

```text
P-B-PERF-01
P-B-PERF-02
P-C-RUNTIME-01
P-C-KEY-01
P-D-RUNTIME-01
P-D-BATCH-01
P-D-BROWSER-01
```

Do not claim:

```text
Phase B full performance lock
Phase C full runtime adoption
Phase F started
Phase F locked
```

## 6. Final Recommendation

```text
NEEDS_MANUAL_TRIAGE
```

Reason:

- The Phase A-E performance-runtime files are present and targeted tests pass.
- The intended baseline groups are separable.
- However, `.kiro` spec/lock files are ignored and require explicit forced staging.
- `AgentRuntime` and `MissionRunner` contain mixed performance-runtime and full-system-audit hunks.
- The worktree includes many unrelated browser/organ/runtime changes that must not enter the baseline commit.

Recommended next action after user approval:

1. Stage Group 1 with `git add -f` only if committing `.kiro` artifacts is accepted.
2. Stage Groups 2 and 3 normally.
3. Stage Group 4 with hunk-level review.
4. Exclude Group 5 entirely.
5. Run safety checks.
6. Commit with:

```bash
git commit -m "baseline: lock performance runtime foundation phases A-E"
```
