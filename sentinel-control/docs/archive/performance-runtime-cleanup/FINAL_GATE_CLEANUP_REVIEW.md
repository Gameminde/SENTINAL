# FinalGate Cleanup Review

Date: 2026-05-16
Status: review only. No staging, no commit, no new phase.

## Scope

This review covers Step 2 only: whether the remaining `final_gate.py` hunks,
`final_gate_registry.py`, and direct FinalGate tests form a safe standalone
cleanup commit.

## Repository State Commands

Commands run:

```bash
git status --short
git log --oneline -8
git diff --stat
git diff --cached --name-only
```

Observed state:

```text
HEAD = 8db5336 refactor: move browser runtime into organ layer
staged files = none
dirty tracked files = 22
untracked files = 25 before this report
```

Recent commits:

```text
8db5336 refactor: move browser runtime into organ layer
3b8b911 docs: close performance runtime foundation A-F
eddaecb perf: add benchmark regression gates foundation
daa4625 docs: update project readme status
7aaecb1 baseline: lock performance runtime foundation phases A-E
4af1672 Lock P6T-B browser controlled navigation L6
332147d Lock P6T-A browser AgentLab power binding
fc9be71 Lock P6S desktop workspace L6
```

`git diff --stat` showed 22 tracked files changed with 1370 insertions and
490 deletions. `git diff --cached --name-only` was empty.

## Files Inspected

Required files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_browser_organ_final_gate.py
sentinel-control/services/sentinel-core/tests/perf/bench/test_core_final_gate_performance_receipts.py
```

Important Git detail:

- `final_gate_registry.py`, `test_final_gate_registry.py`,
  `test_final_gate_determinism.py`, and `test_final_gate_terminality.py` are
  untracked.
- `git diff -- final_gate_registry.py` produces no patch because the file is
  untracked; content was inspected directly with `Get-Content`.
- `test_browser_organ_final_gate.py` and
  `tests/perf/bench/test_core_final_gate_performance_receipts.py` are already
  committed from prior cleanup/Phase F work.

## final_gate.py Hunk Classification

`final_gate.py` has mixed hunks. It must not be staged as a whole file.

### Registry/decomposition hunks

These belong to a possible FinalGate registry/decomposition commit:

```text
1. Add import:
   from sentinel.agent.final_gate_registry import FinalGateRegistry

2. Expand CoreFinalGate docstring to describe registry decomposition.

3. Add CoreFinalGate.__init__(registry: FinalGateRegistry | None = None).

4. Add CoreFinalGate.registry property.

5. Replace monolithic evaluate() check-list construction with:
   self._registry.evaluate_all(...)
```

Reason:

- These hunks introduce the registry extension surface.
- They preserve `CoreFinalGate.evaluate(...)` as the caller-facing API.
- They match `test_final_gate_registry.py` expectations for module ordering,
  duplicate-module rejection, and default-registry behavior.

### Non-registry hunks

These do not belong to a pure registry/decomposition commit:

```text
1. Relax _mission_result_consistency:
   old: mission_result.success != result.success fails
   new: result.success and not mission_result.success fails

2. Add AgentRunResult.model_rebuild(
       _types_namespace={"CoreFinalGateResult": CoreFinalGateResult}
   )
```

Reason:

- The mission-success relaxation changes FinalGate semantics beyond registry
  decomposition. It likely belongs with AgentRuntime terminality/runtime wiring.
- `AgentRunResult.model_rebuild(...)` is explicitly labelled Task 1.3 /
  Requirement 1 FinalGate runtime integration, not Task 11 registry
  decomposition.
- Including these in the registry commit would blur cleanup boundaries.

## final_gate_registry.py Review

Observed components:

```text
FinalGateCheckModule protocol
FinalGateRegistry
CoreChecksModule
BrowserChecksModule
default_registry()
_ProjectScopeTailModule
```

Positive findings:

- Registry preserves deterministic module order.
- Duplicate module names raise `ValueError`.
- `CoreChecksModule` delegates to existing `CoreFinalGate` static/instance
  checks rather than copying check logic.
- `BrowserChecksModule` remains available as a reference module.
- `default_registry()` uses `sentinel.organs.browser.final_gate.BrowserOrganChecksModule`,
  which aligns with the browser-organ migration already committed in `8db5336`.
- Project-scope is split into a tail module to preserve old end-of-list
  ordering.

Risk:

- `CoreChecksModule.checks(...)` instantiates `CoreFinalGate()`, which itself
  constructs a default registry. Current tests pass, but this recursion-shaped
  design depends on no evaluate call happening inside that constructor path.
- The file contains comments with some mojibake in console output due terminal
  encoding, but content itself did not block tests.

## Tests Run

From `sentinel-control/services/sentinel-core`:

```bash
python -m pytest tests/test_final_gate_registry.py tests/test_final_gate_determinism.py tests/test_final_gate_terminality.py -q
```

Result:

```text
19 passed
```

```bash
python -m pytest tests/test_browser_organ_final_gate.py -q
```

Result:

```text
14 passed
```

```bash
python -m pytest tests/perf/bench/test_core_final_gate_performance_receipts.py -q
```

Result:

```text
6 passed
```

```bash
python -m pytest tests/test_agent_runtime.py -q
```

Result:

```text
14 passed
```

## Can This Be Committed Standalone?

Not as the whole current dirty set.

A narrow FinalGate registry/decomposition commit is plausible, but only after
hunk-level staging because `final_gate.py` contains registry hunks mixed with
runtime/semantic hunks.

## Exact Files That Belong In A Narrow Registry Commit

Candidate files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
```

Candidate hunk-level staging from:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
```

Approved registry-only hunks:

```text
import FinalGateRegistry
CoreFinalGate registry docstring
CoreFinalGate.__init__
CoreFinalGate.registry property
CoreFinalGate.evaluate delegation to registry.evaluate_all
```

Optional but not required for the narrow registry commit:

```text
sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py
```

Reason:

- It tests `CoreFinalGate.evaluate` determinism and can support the registry
  refactor, but the file labels itself as FinalGate Runtime Integration
  rather than registry decomposition. Include only if the next commit scope is
  "FinalGate evaluate determinism plus registry", not pure registry.

## Exact Files That Must Stay Out

Must stay out of the registry/decomposition commit:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
sentinel-control/services/sentinel-core/sentinel/mission/cancellation.py
sentinel-control/services/sentinel-core/sentinel/mission/exceptions.py
sentinel-control/services/sentinel-core/sentinel/mission/gate_sequence.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_kill_switch_reactive_property.py
sentinel-control/services/sentinel-core/tests/test_mission_runner_browser_operator_route_rejected.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py
sentinel-control/docs/BASELINE_PLAN.md
sentinel-control/docs/BASELINE_STAGE_PASS1_REPORT.md
sentinel-control/docs/BASELINE_STAGE_PASS2_REPORT.md
sentinel-control/docs/BASELINE_STAGING_AUDIT.md
sentinel-control/docs/DIRTY_TREE_TRIAGE_PLAN.md
```

Must also stay out of the registry/decomposition commit:

```text
final_gate.py hunk: mission_result.success relaxation
final_gate.py hunk: AgentRunResult.model_rebuild(...)
```

Reason:

- `test_final_gate_terminality.py` depends on AgentRuntime `_apply_final_gate`
  behavior from the `runtime.py` dirty set, so it belongs in Step 4/5, not in
  Step 2/3.
- Mission runner and gate-sequence files are separate cleanup blocks.
- Baseline and triage docs are parked docs, not runtime code.

## Risk Assessment

Main risks:

```text
1. Hunk contamination:
   Staging final_gate.py whole-file would include runtime/semantic changes
   unrelated to registry decomposition.

2. Clean-checkout test risk:
   test_final_gate_terminality.py may pass in the current dirty tree because
   runtime.py has uncommitted _apply_final_gate wiring. It should not be
   committed before runtime.py is reviewed.

3. Check-order regression:
   Registry refactor must preserve the exact 38/39 check sequence. Current
   tests verify this.

4. Browser module coupling:
   default_registry() now uses the organ-side browser module. This is
   acceptable only because browser-organ migration is already committed in
   8db5336 and its direct tests pass.
```

Authority expansion risk:

```text
No authority expansion observed in the registry/decomposition hunks.
```

Production behavior risk:

```text
Low to medium for registry-only hunks because they refactor the evaluation
surface. Tests prove check names/order/count, but this still touches
CoreFinalGate.evaluate.
```

## Hunk-Level Staging Required

Yes.

`final_gate.py` requires hunk-level staging or a deliberate patch file. Whole
file staging is not acceptable.

Recommended staging boundary:

```text
Stage:
- import FinalGateRegistry
- CoreFinalGate docstring update
- __init__
- registry property
- evaluate delegation

Do not stage:
- mission_result.success relaxation
- AgentRunResult.model_rebuild(...)
```

## Recommended Commit Message

If the narrow registry/decomposition subset is approved after this review:

```text
refactor: decompose final gate registry
```

## Verdict

```text
NEEDS_TRIAGE
```

Reason:

The registry/decomposition work is coherent and the targeted tests pass, but
the required `final_gate.py` file has mixed unrelated hunks. Per cleanup rules,
mixed files require explicit hunk-level approval before commit. The current
whole dirty set is not safe as a standalone commit.

## Step 2 Follow-up — Hunk Triage

Status: follow-up review only. No staging, no commit, no Step 3 execution.

Commands run:

```bash
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
git diff -- sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
git diff -- sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
```

Observed diff behavior:

```text
final_gate.py produced a tracked-file patch.
final_gate_registry.py produced no patch because it is untracked.
test_final_gate_registry.py produced no patch because it is untracked.
```

Tests were not rerun in this follow-up because no code was changed and the
same targeted suite already passed during Step 2.

### 1. Registry/Decomposition Hunks To Include

Include only these `final_gate.py` hunks in a future minimal registry commit:

```text
1. Import hunk:
   from sentinel.agent.final_gate_registry import FinalGateRegistry

2. CoreFinalGate class docstring hunk:
   Expand the docstring to describe Task 11 / Requirement 11
   CoreFinalGate decomposition into FinalGateCheckModule instances held
   by FinalGateRegistry.

3. Constructor / registry initialization hunk:
   Add CoreFinalGate.__init__(registry: "FinalGateRegistry | None" = None)
   and lazily import default_registry inside the constructor.

4. Registry property hunk:
   Add CoreFinalGate.registry returning self._registry.

5. evaluate(...) decomposition hunk:
   Replace the monolithic local check-list construction in evaluate(...)
   with self._registry.evaluate_all(...), preserving allowed_project_root
   normalization.
```

Include this direct new file in the future commit:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
```

Direct compatibility glue required for `FinalGateRegistry`:

```text
FinalGateCheckModule protocol
FinalGateRegistry.register/evaluate_all
CoreChecksModule
BrowserChecksModule reference module
default_registry()
_ProjectScopeTailModule
```

Rationale:

- These hunks and the new registry file are the minimum surface that turns
  `CoreFinalGate.evaluate(...)` from a monolithic check-list into a registry
  backed evaluation path.
- They preserve the public `CoreFinalGate.evaluate(...)` API.
- They are covered by `test_final_gate_registry.py`.

### 2. Hunks To Keep Out

Keep these hunks out of the future minimal registry commit:

```text
1. mission_result.success relaxation:
   old: mission_result.success != result.success
   new: result.success and not mission_result.success

2. AgentRunResult.model_rebuild(...):
   AgentRunResult.model_rebuild(
       _types_namespace={"CoreFinalGateResult": CoreFinalGateResult}
   )
```

Also keep out:

```text
any runtime certification / downgrade behavior
any AgentRuntime._apply_final_gate behavior
any performance receipt helper already committed in Phase F
any browser route rejection change
any gate sequence change
any mission cancellation or revocation change
any runtime.py or runner.py related change
```

Reason:

- The mission-result success relaxation is a semantic FinalGate behavior
  change and belongs with the AgentRuntime terminality / downgrade cleanup.
- `AgentRunResult.model_rebuild(...)` is labelled Task 1.3 / Requirement 1
  FinalGate Runtime Integration and belongs with runtime wiring, not with
  registry decomposition.
- Phase F's `verify_performance_receipts(...)` helper is already committed
  and must not be restaged or reworked here.

### 3. Files Allowed In A Future Commit

Allowed files for the future minimal registry commit:

```text
sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
```

Constraint:

```text
final_gate.py may include registry/decomposition hunks only.
```

### 4. Files Not Allowed In That Future Commit

Do not include:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/mission/runner.py
sentinel-control/services/sentinel-core/sentinel/mission/gate_sequence.py
sentinel-control/services/sentinel-core/sentinel/mission/cancellation.py
sentinel-control/services/sentinel-core/sentinel/mission/exceptions.py
sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py
sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py
sentinel-control/services/sentinel-core/tests/test_mission_runner_browser_operator_route_rejected.py
```

Also do not include:

```text
sentinel-control/docs/BASELINE_PLAN.md
sentinel-control/docs/BASELINE_STAGE_PASS1_REPORT.md
sentinel-control/docs/BASELINE_STAGE_PASS2_REPORT.md
sentinel-control/docs/BASELINE_STAGING_AUDIT.md
sentinel-control/docs/DIRTY_TREE_TRIAGE_PLAN.md
```

### 5. Proposed Hunk-Staging Strategy

Use:

```bash
git add -p sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py
git add -- sentinel-control/services/sentinel-core/sentinel/agent/final_gate_registry.py
git add -- sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py
```

Rules:

```text
Do not stage final_gate.py whole-file.
Accept only the import/docstring/constructor/property/evaluate-delegation hunks.
Reject the mission_result.success relaxation hunk.
Reject the AgentRunResult.model_rebuild(...) hunk.
If git add -p presents a hunk that mixes registry and unrelated semantic
changes, mark it as NEEDS_MANUAL_SPLIT and do not stage that hunk.
```

Expected split quality:

```text
The import hunk is clean.
The CoreFinalGate docstring + constructor + registry property + evaluate
delegation are adjacent but registry-only, so they are acceptable as one
staged hunk if presented together.
The mission_result.success relaxation hunk is separate and must be rejected.
The AgentRunResult.model_rebuild(...) hunk is separate and must be rejected.
```

### 6. Proposed Commit Message

```text
refactor: decompose final gate registry
```

### 7. Follow-up Verdict

```text
READY_FOR_HUNK_COMMIT
```

Reason:

The required registry/decomposition subset is now isolated clearly enough for
hunk-level staging. The future commit remains safe only if `final_gate.py` is
staged with `git add -p` and the unrelated semantic/runtime hunks stay out.
