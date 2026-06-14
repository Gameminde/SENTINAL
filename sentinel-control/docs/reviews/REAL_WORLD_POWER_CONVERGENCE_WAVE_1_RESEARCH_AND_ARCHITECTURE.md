# Real-World Power Convergence Wave 1 - Research And Architecture

Date: 2026-06-14

Baseline:

```text
HEAD = 995bc035e63e40ff37c1aaf9862f3dbccbd0f36f
current_phase = REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCKED
next_phase = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER
measurement_doctrine = product power under provable authority
```

## Executive Decision

Wave 1 will converge existing Sentinel mechanisms into repeated vertical task
proof. It will not create a parallel coding agent, browser runtime, authority
path, telemetry store, or replay system.

The minimum implementation gaps found before coding are:

1. promote approved text workspace mutations from verified direct writes to
   verified atomic replacement while preserving existing hash, scope, rollback,
   receipt, and Gate bindings;
2. promote multi-tab operation into the existing governed persistent live
   browser session manager rather than relying only on the stateless lifecycle
   ledger;
3. add focused vertical benchmark tests that compose existing workspace,
   shell, workflow/recovery, browser, receipt, FinalGate, and replay surfaces.

Persistent shell/kernel, live LSP, and debugger integration are not required to
pass the deterministic V1 fixture task. They remain honest gaps and will not be
claimed.

## Current Mechanism Inventory

| Mechanism | Current Sentinel Surface | Classification | Truth |
| --- | --- | --- | --- |
| workspace inspection | local filesystem, harness artifacts, shell tree manifests | LIVE_BOUNDED | Repository files can be inspected inside an explicit root; there is no dedicated semantic project index. |
| filesystem access | `L3ReversibleWorkspaceExecutor`, workspace organs | LIVE_BOUNDED | Scoped local reads/writes exist with traversal and sensitive-path blocks. |
| file editing | `L3ReversibleWorkspaceExecutor` | LIVE_BOUNDED | Real text replacement, append, JSON metadata update, and rollback exist. |
| patching | model amplification hash-anchored edit verification | WIRED | Hash-anchored proposals and verification exist; no general patch application engine is promoted. |
| hash anchoring | workspace executor and amplification harness | LIVE | Before/after hashes, stale-write rejection, content-addressed artifacts, and receipt hashes exist. |
| atomic file write | mission store JSON only | ABSENT for workspace mutation | Mission records use temp file plus `os.replace`; workspace mutations currently use direct `write_text`. |
| shell execution | `ShellCodeSandboxOrganV1` | LIVE_BOUNDED | Real tokenized `subprocess.run`, allowlisted prefixes, bounded output/time, scrubbed env, receipt, and FinalGate. |
| persistent shell/kernel sessions | none promoted for coding | ABSENT | Process-per-command only. Not required by the deterministic Wave 1 coding fixture. |
| test execution | sandbox shell allowlisted pytest/compileall commands | LIVE_BOUNDED | Targeted and regression tests can run inside a scoped project root. |
| process lifecycle | sandbox timeout and kill-before-start; daemon/workflow lifecycle | LIVE_BOUNDED | Bounded subprocess lifecycle exists; no unrestricted terminal daemon. |
| coding workers | Worker Fleet plus typed result contracts | WIRED | Governed workers exist, but Wave 1 does not claim real-model coding-worker certification. |
| model harness | Model Amplification Harness | LIVE_BOUNDED | Hash-anchored artifacts, minimized tool output, context packs, conflicts, replay; not execution authority. |
| LSP / semantic navigation | no promoted live LSP path | ABSENT | Do not claim LSP. Repository inspection remains evidence-backed textual inspection. |
| debugger support | no promoted live debugger path | ABSENT | Do not claim debugger integration. |
| rollback | `L3ReversibleWorkspaceExecutor.rollback` | LIVE | Real bounded restoration with restored-hash verification and rollback receipt. |
| workspace receipts | workspace executor and shell sandbox | LIVE | Mutation and command receipts carry hashes, scope, result, and safe evidence. |
| browser live backend | `BrowserSessionManagerL5Live` with CloakBrowser primary and explicit Playwright compatibility engine | LIVE_BOUNDED | Persistent live session, click/fill/select/hover/wait, screenshots, snapshots, receipts, FinalGate. No hidden fallback. |
| browser session continuity | `BrowserSessionManagerL5Live`, runtime cache | LIVE_BOUNDED | Session state persists across governed steps and is isolated by mission/config/profile. |
| multi-tab operation | public lifecycle/multitab ledger | WIRED | Multi-tab lifecycle is proved in a stateless ledger, not yet promoted into the live persistent session. |
| upload/download | live session special-authority methods | LIVE_BOUNDED | Controlled local fixture upload/download and quarantine paths exist. |
| form submit | live session special-authority method and Browser V3 contracts | LIVE_BOUNDED | Governed submit exists; ordinary interaction does not silently promote submit. |
| login checkpoint | credential session broker and login special-authority path | LIVE_BOUNDED | Governed login shape exists; MFA/CAPTCHA/KYC remain checkpoints. |
| visual grounding | browser visual grounding and live session source methods | LIVE_BOUNDED | Evidence-linked grounding exists; ambiguity and sensitive boundaries block. |
| network/console/performance intelligence | live session hash-only metadata and browser intelligence organs | LIVE_BOUNDED | Metadata is available without raw body/secret promotion. |
| failure recovery | browser orchestrator recovery, neural recovery, durable workflow/replan | LIVE_BOUNDED | Recovery paths exist; Wave 1 must prove them through repeated vertical tasks. |
| workflow checkpoint/resume | `DurableMissionWorkflowRuntime` / `DurableWorkflowStore` | LIVE | Checkpointed resume and unchanged-authority replan exist with tamper detection. |
| telemetry | `TelemetryKernel` and MissionRunStore bridge | LIVE | Local append-only, hash-bound certified telemetry exists and is required for material benchmark evidence. |
| replay | mission/workflow/browser replay surfaces | LIVE_BOUNDED | Replay reconstructs stored evidence and must not re-execute. |

## Existing Spine Reused

```text
MissionAuthorityEnvelope
-> Gate / delegated lane
-> L3ReversibleWorkspaceExecutor or BrowserSessionManagerL5Live
-> ShellCodeSandboxOrganV1 where tests are required
-> receipts
-> FinalGate
-> MissionRunStore timeline
-> TelemetryKernel
-> replay / no re-execution checks
```

Durable workflow and recovery proof reuse:

```text
MissionKernel
-> DurableWorkflowStore
-> DurableMissionWorkflowRuntime
-> checkpoint
-> resume/replan inside unchanged authority
```

## AgentLab Mechanism Harvest

| Competitor/reference | Task advantage | Mechanism | Sentinel current equivalent | Gap | Sentinel-native action | Must not copy | Benchmark impact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oh-my-pi | reliable fast coding edits | content/hash-anchored edits and workspace snapshots | L3 before/after hashes and harness artifacts | workspace replacement is not atomic | use MissionRunStore-style temp write plus `os.replace` inside L3 executor | vendor code, unrestricted native tools, ambient shell | C2, C5, C6 |
| oh-my-pi | compact coding loops | typed/minimized results | harness minimized tool outputs and typed workers | not assembled into one coding task proof | retain existing result contracts and prove vertical task | vendor worker/runtime | C1-C4 |
| gptme / Agent Zero | usable local coding flow | visible command results and simple continuation | shell receipts, workflow checkpoints, daemon status | fragmented proof | compose existing receipts/checkpoints in benchmark evidence | ambient host authority | C3-C5 |
| Microsoft Agent Framework | restartable work | durable checkpoints and cancellation semantics | durable workflow/replan and daemon | task-level repeated evidence missing | prove interrupted resume/no duplicate mutation | vendor runtime/dependency | C5, B7 |
| UI-TARS / Agent TARS | robust GUI/browser operation | target verification and changed-state recovery | visual grounding and browser recovery engines | live multi-tab continuity gap | add bounded live tab selection to existing session manager | uncontrolled computer use | B1-B7 |
| OpenClaw | broad browser/session usability | stable sessions and operator-visible progress | persistent live browser manager and cockpit | end-to-end live fixture gauntlet missing | repeated controlled local browser task proof | plugin/runtime authority | B1-B8 |
| Hermes | persistent supervised browser work | persistent browser lease/session and guarded continuity | live session manager plus daemon/workflow | benchmark does not prove full chain | exercise session continuity and cleanup repeatedly | vendor browser/runtime | B1-B8 |
| DeerFlow | multi-step plan continuation | long-running task graph and recovery | durable workflow/replan | vertical task proof missing | reuse existing workflow checkpoints; no new graph | vendor orchestration | C5, B7 |

No vendor code, runtime, bridge, dependency, account, or service is admitted.

## Minimum Implementation Plan

### Coding / Workspace

1. Add a private atomic text replacement helper to the existing L3 workspace
   executor.
2. Use it for normal mutations, rollback, and safe restore.
3. Preserve all current root containment, hash checks, rollback posture,
   receipts, and FinalGate behavior.
4. Add a deterministic multi-file fixture task proving:
   - repository inspection evidence;
   - two related edits with unrelated user change preserved;
   - failing targeted test, diagnosis, repair, targeted rerun;
   - regression run;
   - interrupted resume without duplicate mutation;
   - verified rollback.

Persistent shell/kernel, live LSP, and debugger are explicitly deferred because
the fixture does not require them and adding them would expand the execution
surface.

### Browser

1. Extend `BrowserSessionManagerL5Live` with bounded live-tab operations inside
   its existing browser context and mission-owned session.
2. Require the existing mission authority, domain allowlist, action allowlist,
   step budget, receipts, FinalGate, and mission/session isolation.
3. Do not add fallback, automatic engine switching, credential access, or open
   web mutation.
4. Add a controlled local-fixture gauntlet proving:
   - multi-step navigation;
   - live multi-tab open/switch/close;
   - controlled form submit;
   - controlled upload/download quarantine paths;
   - login checkpoint behavior;
   - changed-page and induced failure recovery;
   - kill/close then new mission without state leakage.

### Evidence / Scoring

Deterministic coding tasks run at least five times. Timing-sensitive browser
tasks run ten times where the local Playwright engine is available. All
material tasks require certified local telemetry and preserve receipt,
FinalGate, and replay evidence.

The model certification status for Wave 1 is:

```text
BACKEND_CERTIFIED / AGENT_LEVEL_NOT_RUN
```

Therefore Coding / Workspace cannot be scored 8/10 in this wave even if the
backend gauntlet passes. Browser and Reliability scores may reach 8/10 only if
their full evidence gates pass.

## Architecture Boundaries

Wave 1 adds no authority source. Benchmark inputs, model outputs, memory,
telemetry, receipts, FinalGate certificates, and replay remain data only.

Blocked:

```text
new actuator family
parallel browser runtime
parallel coding runtime
parallel telemetry/replay
unrestricted persistent terminal
hidden provider/model switch
provider fallback/AUTO
vendor runtime/dependency
open-web mutation
replay mutation or browser re-action
```

## Contract Inflation Budget

Expected public export/model growth:

```text
0 new broad operator exports
0 new authority model families
0 new actuator families
bounded additions to existing BrowserSessionActionKind/request/receipt only
private workspace atomic-write helper only
focused convergence benchmark tests and reports
```

## Lock Decision Rule

The wave is `LOCKED` only if the repeated backend task gates, recovery gates,
evidence gates, targeted/regression/full suite, audit, and truth updates pass.
Otherwise it is reported as `PARTIALLY_CLOSED` with scores left below their
unmet gates.
