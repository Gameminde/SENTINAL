# Real-World Power Convergence Wave 1 - Coding, Workspace, And Browser Live Power Lock Report

Date: 2026-06-14

## Verdict

```text
status = PARTIALLY_CLOSED
current_phase = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER_PARTIALLY_CLOSED
previous_phase = REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCKED
next_phase = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_COMPLETION
Wave 2 = NOT_STARTED / blocked until Wave 1 completion gates pass
```

The wave delivered real backend convergence and repeated vertical task proof,
but it is not called locked because real-model coding-agent certification,
process-restart browser continuity, fully vertical durable coding resume, and
long-duration soak evidence remain open.

## Sentinel Components Reused

```text
MissionAuthorityEnvelope
DelegatedActionLane and Gate-bound workspace contracts
L3ReversibleWorkspaceExecutor
ShellCodeSandboxOrganV1
BrowserSessionManagerL5Live
BrowserFormSubmitSpecialAuthorityL6
BrowserFileQuarantineOrganL6
MissionKernel / MissionRunStore
TelemetryKernel certified mode
DurableMissionWorkflowRuntime regression proof
receipts
FinalGate certificates
MissionReplayBuilder
```

No parallel coding runtime, browser runtime, telemetry store, replay store,
authority source, or actuator family was created.

## AgentLab Mechanisms Harvested

| Reference | Mechanism harvested | Sentinel-native rewrite |
| --- | --- | --- |
| oh-my-pi | Hash-anchored reliable edits and compact task loops | Atomic scoped workspace replacement inside the existing L3 executor |
| gptme / Agent Zero | Usable edit-test continuation and visible failure | Repeated local fixture repair with shell receipts and honest failure status |
| Microsoft Agent Framework | Checkpoint/resume and no duplicate certified step | Existing durable workflow regression plus stale mutation rejection evidence |
| UI-TARS / Agent TARS | Changed-state recovery and GUI target continuity | Controlled live DOM target invalidation and recovery |
| OpenClaw / Hermes / DeerFlow | Persistent supervised multi-step browser work | Bounded live tabs in the existing mission-owned browser session |

No vendor code, runtime, dependency, bridge, account, or service was used.

## Runtime Changes

### Coding / Workspace

```text
approved text mutation = atomic same-directory temp write + fsync + os.replace
rollback = atomic replacement
safe restore after failed verification = atomic replacement
existing root/path/hash/race/rollback/receipt boundaries = preserved
```

### Browser

```text
live bounded multi-tab open/switch/close = implemented in existing persistent session
tab ids and counts = receipt-bound
max_tabs = enforced
max_steps = enforced
session contract hash = bound at open and cannot be silently expanded
revocation/expiry = rechecked before every non-close action
safe close = still allowed after revocation/expiry
controlled new-page fixture routing = installed at browser-context level
```

## Benchmark Result

```text
coding vertical repetitions = 5 / 5 passed
coding median = 6.743 seconds
coding p95 = 8.083 seconds
browser vertical repetitions = 10 / 10 passed
browser median = 11.606 seconds
browser p95 = 37.127 seconds
silent success = 0
duplicate material side effects = 0
cross-mission contamination = 0
```

Detailed evidence:

```text
sentinel-control/docs/reviews/REAL_WORLD_POWER_CONVERGENCE_WAVE_1_BENCHMARK_REPORT.md
```

## Authority And Proof Review

```text
new authority source = none
new special authority = none
new actuator family = none
direct organ bypass introduced = none
provider fallback/AUTO = none
vendor runtime = none
memory/telemetry/receipt/FinalGate as authority = blocked
replay re-execution = false
workspace path traversal = existing fail-closed policy preserved
browser cross-mission contract/state expansion = blocked
```

## Audit Findings

| Severity | Finding | Surface | Decision | Fix or rationale | Remaining limit |
| --- | --- | --- | --- | --- | --- |
| P1 | Browser action path did not recheck mission revocation/expiry at each step | live browser session | accepted_and_fixed | Added lifecycle recheck; safe close remains available | Special L6 actions still rely on their existing governed runtime admission path |
| P1 | Browser session limits could be replaced by a different later request contract | live browser session | accepted_and_fixed | Bound a safe contract hash at open and reject mismatch | No process-restart session restoration |
| P2 | `max_steps` existed but was not enforced | live browser session | accepted_and_fixed | Enforced before every interaction with certified blocked receipt | Special-authority organ budgets remain enforced by their existing paths |
| P2 | Workspace mutation/rollback exposed direct-write partial-state risk | L3 workspace executor | accepted_and_fixed | Added same-directory atomic replace for mutation, rollback, restore | Text workspace only |
| P2 | Live browser session had no real multi-tab operations | live browser session | accepted_and_fixed | Added bounded tab operations inside existing context | No process-restart continuity |
| P2 | Exact contract-hash matching blocked compatible narrower trajectory contracts | live browser session | accepted_and_fixed | Retained the opening contract as the ceiling and accept only strict compatible subsets | No authority or limit expansion allowed |
| P2 | Multi-tab initialization eagerly accessed the page and broke close-failure resilience | live browser session | accepted_and_fixed | Restored lazy first-page access while retaining tab identity/count state | No process-restart continuity |
| P2 | Coding C5 is not one fully vertical process-restart resume around actual L3 edits | benchmark | accepted_deferred_with_reason | Existing durable workflow resume plus vertical stale-write rejection prove components, but not the combined process-restart task | Blocks full Wave 1 lock |
| P2 | No explicit real `UserModelContract` was available for coding-agent certification | environment | accepted_deferred_with_reason | Backend certification recorded honestly | Blocks Coding 8/10 |
| P2 | No multi-hour soak or browser process-restart corpus | reliability/browser | accepted_deferred_with_reason | Controlled repeatability recorded; no overclaim | Blocks Browser/Reliability 8/10 |

Open P0/P1: `0`.

## CodeRabbit Advisory Review

```text
CodeRabbit used = no
reason = CodeRabbit CLI unavailable in this environment
manual exhaustive audit = performed
CodeRabbit authority effect = none
```

## Contract / Export Growth

```text
new authority model families = 0
new actuator families = 0
new runtime modules = 0
new public broad operator exports = 0
existing BrowserSessionActionKind additions = 3 bounded tab actions
existing request/contract/receipt fields = tab id/count and max tabs
private workspace helper = 1
new vertical benchmark test module = 1
new end-to-end task families = 2
```

The ratio favors runtime/task proof over contract growth.

## Score Decision

```text
Coding / Workspace = 7.5 / 10
Browser = 7.5 / 10
Reliability = 7.5 / 10
Overall real-world product power = 5.7 / 10
Governance / Proof = 9.0 / 10
```

No score reaches 8 because the exact certification gates are not all met.

## Tests And Checks

Completed before the final canonical suite:

```text
Wave 1 vertical gauntlet = 2 passed
workspace + shell targeted slice = 53 passed
browser session/form/file slice = 23 passed
impacted browser + Wave 1 slice after final remediation = 27 passed
complete browser corpus = 326 passed
workflow/replan/telemetry/memory slice = 132 passed
worker/daemon/harness/skill slice = 38 passed
cockpit/runtime/Gate/FinalGate/evidence/replay slice = 178 passed
workspace performance benchmark isolated verification = 3 / 3 passed, p95 4.142-4.586 ms under 50 ms budget
complete canonical core suite final run = 2698 collected / 2695 passed / 0 failed / 3 skipped
compileall = clean
git diff --check = clean
```

The first complete-suite run had one transient workspace performance benchmark
failure under suite-wide contention (`p95 = 85.084 ms`). The unchanged
benchmark then passed three isolated reproductions and the second complete
suite passed. No performance threshold or unrelated benchmark code was changed.

## Remaining Completion Gates

```text
run an explicit real UserModelContract coding mission
resume the actual coding edit mission from a new runtime/process checkpoint
restore a governed browser session after process restart or define and certify an honest checkpoint/reopen contract
run a longer-duration reliability/soak corpus
```

Wave 2 remains blocked. Security Testing remains deferred and not started.
