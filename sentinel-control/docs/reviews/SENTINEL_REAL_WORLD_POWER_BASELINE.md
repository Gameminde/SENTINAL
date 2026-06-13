# Sentinel Real-World Power Baseline

Recorded at: 2026-06-14

## Verdict

Sentinel has a strong governed local runtime and a limited set of real bounded
effects. It does not yet have broad production user reach.

```text
control_plane = strong
local_governed_runtime = real
live_external_backend_reach = limited
production_operator_product = not started
overall_real_world_product_power = 5.4 / 10
```

The baseline rule is strict:

```text
contract != power
fake or injected backend != live power
sandbox or paper result != live external effect
test success != normal-user product readiness
```

## Post-Baseline Green Gate Remediation

The baseline findings below remain historical evidence of the state measured
at the baseline lock. They were closed by
`REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION` without changing the
baseline score or backend maturity:

```text
full canonical core suite after remediation = 2686 passed, 0 failed, 3 skipped
stale historical truth test = CLOSED
mixed unsafe/safe browser-neural continuity defect = CLOSED
new capability = none
Wave 1 = not started
```

## Maturity Labels

| Label | Meaning |
|:--|:--|
| `LIVE_PROVEN` | A real backend effect was exercised in this baseline with evidence. |
| `LIVE_BOUNDED` | A real effect exists but is constrained to a narrow local or fixture-backed scope. |
| `LOCAL_ONLY` | Real local runtime behavior exists without a production external backend. |
| `INJECTED` | Runtime behavior uses an injected transport/backend. |
| `SANDBOX` | Side effect is intentionally simulated or isolated. |
| `PAPER` | Financial behavior is paper-only. |
| `DESCRIPTOR` | Capability metadata exists without execution. |
| `CONTRACT_ONLY` | Contracts exist without a demonstrated runtime backend. |
| `NOT_STARTED` | No implementation is claimed. |
| `BLOCKED` | Explicitly unavailable under current policy. |

## Complete Task-Level Power Inventory

| Surface | Contract maturity | Runtime wiring | Backend type | Real side effect possible | Setup required | Default mode | Task success evidence | Recovery behavior | Operator intervention | Product readiness | Main blocker |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| Browser | Closed across governed L4/L5 and scoped L6 paths | Mission/Power/Agent runtime paths | Playwright fixture/local renderer plus fake orchestration backends | Yes, bounded browser actions | Explicit authority and local browser dependencies | Bounded/explicit | Live observe/type/click tests; 5 live-browser tests were among the slowest baseline tasks | Multi-step recovery proven on fake action backend | Authority/checkpoints for sensitive boundaries | `LIVE_BOUNDED` | Real SaaS/session/upload/download/login gauntlet |
| Workspace | Closed L3 reversible executor | Explicit runtime opt-in | Real scoped filesystem | Yes, inside approved workspace | Approved root, hashes, rollback posture | Explicit opt-in | Real file replacement and rollback tests | Hash drift and rollback checks | Boundary escalation only | `LIVE_BOUNDED` | End-to-end coding mission UX and larger project benchmarks |
| Coding | Harness, shell/code organ, workspace, workers exist | Fragmented across existing spine | Local bounded tools | Partly | Explicit mission plus scoped workspace | Explicit opt-in | Hash-anchored edit, workspace mutation, compile/test subprocess proofs | Workflow/replan can recover bounded steps | Needed for scope/authority expansion | `LOCAL_ONLY` | No measured full repository inspect-edit-test-debug mission |
| Shell | Closed allowlisted sandbox organ | PowerRuntime adapter | Real local subprocess, allowlisted | Yes, bounded | Scoped cwd, command allowlist, timeout | Explicit opt-in | Python version and compileall receipt/FinalGate tests | Timeout and kill paths tested | Required outside allowlist | `LIVE_BOUNDED` | No broad build/dev command profiles or container-grade isolation |
| External API | Closed scoped read/write organ | PowerRuntime adapter | Injected transport in current tests | Transport contract can mutate when authorized | Domain/method authority and injected transport | Read/scoped; mutation requires authority | GET, mutation gate, rate limit, response quarantine tests | Fail closed on scope/rate mismatch | Required for new domains/mutations | `INJECTED` | No production connector/task benchmark |
| Filesystem | Closed reversible workspace path | Explicit executor | Real local scoped filesystem | Yes, bounded | Approved workspace root | Explicit opt-in | Path traversal/symlink/race/rollback tests | Rollback/tombstone available for supported operations | Boundary escalation | `LIVE_BOUNDED` | No user-facing project workspace flow |
| Channels | Closed governed adapter foundation | Mission/telemetry/receipt/FinalGate path | Draft local; send injected | Draft yes; external send not proven | Adapter descriptor, authority, approval | Draft-only | Draft and injected send tests | Replay does not resend; revoked/killed sends block | Approval required for send | `INJECTED` | One production-quality real connector |
| Desktop | Closed sidecar and monitoring foundations | Mission/telemetry/receipt/FinalGate path | Fake/injected action backend | No production desktop control claimed | Explicit policy, authority, allowlists | Observe/monitor or fake action | Snapshot, fake action, kill, replay gauntlet | Kill/revocation and replay-no-reaction tested | Approval for action | `INJECTED` | Production live opt-in OS adapter and app packaging |
| Voice | Closed local runtime foundation | Cockpit/MissionKernel proposal path | Fake/injected audio | No live microphone/STT/TTS proven | Explicit voice policy | Fake/injected | VAD, transcript lifecycle, barge-in, kill word tests | Kill word and replay-no-playback tested | Checkpoint for dangerous command | `INJECTED` | Live realtime audio/provider backend |
| Credentials | Closed secret-broker foundation | Existing authority/receipt/replay spine | Fake sealed store | No production secret backend | Explicit unlock/lease policy | Local fake sealed | Lease/ref and no-raw-secret tests | Revocation/expiry/kill tested | Unlock approval | `INJECTED` | OS keychain or production encrypted backend |
| Account/Login | Closed special-authority foundation | Vault + mission + browser/desktop paths | Fake/injected | No universal live login | Explicit authority, credential lease, checkpoints | Fake/injected | Login/account planning and checkpoint tests | Safe checkpoint/handoff | Required at MFA/CAPTCHA/KYC/passkey/terms | `INJECTED` | Real provider/site adapter |
| Finance | Closed sandbox/paper special-authority foundation | Vault + mission + telemetry + proof spine | Sandbox spend and paper trade | No live money | Explicit authority, caps, approval | Sandbox/paper only | Sandbox spend and paper trade test | Idempotency, kill, revocation tested | Approval/checkpoints | `SANDBOX` / `PAPER` | Live provider/bank/broker connectors remain deferred |
| Memory | Closed persistent semantic memory | Brain/cockpit/mission integrations | Real local SQLite | Yes, local durable context | Explicit scope; optional recall | Default-off where sensitive | Restart persistence and scoped recall tests | Corrupt records quarantined; expiry/tombstone | None for safe recall; never authority | `LOCAL_ONLY` | Measured mission-completion uplift and scale |
| Workflow/Replan | Closed durable workflow and automatic replan | MissionKernel + PowerRuntime | Real local same-process | Yes, existing authorized steps | Existing mission authority | Automatic only inside unchanged authority | Resume, retry, replan, kill, tamper tests | Strong local recovery | Checkpoint on authority change | `LOCAL_ONLY` | Multi-process durability and live mission evidence |
| Workers | Closed governed Worker Fleet | Workflow/telemetry/memory/runtime spine | Same-process worker runtime | Yes, bounded local/runtime work | Parent mission and strict child authority | Explicit governed fleet | Merge/reject/conflict and durable checkpoint tests | Cancellation/conflict/reject paths | Checkpoint for authority expansion | `LOCAL_ONLY` | Multi-process worker service and real productivity benchmarks |
| Daemon | Closed local daemon/scheduler foundation | Existing mission/workflow/worker spine | Same-process local daemon | Yes, local background ticks | Certified telemetry and lease | Proposal-only scheduler | Lease, heartbeat, recovery, dead-letter tests | Crash-state inspection and stale takeover | Handoff/dead-letter | `LOCAL_ONLY` | OS service/tray and long-duration live runs |
| Skills | Closed governed procedure fabric | Existing runtime/proof spine | Local governed manifests/procedures | Only through existing executors | Scan, eval, approval/promotion | Unapproved blocked | Lifecycle, scanner, revoke, replay tests | Revoke/rollback posture | Promotion/approval | `LOCAL_ONLY` | Useful procedure library and live task uplift |
| Model routing | Closed explicit router | Existing UserModelContract path | Simulation/descriptors plus existing contracts | Binding only; no hidden execution | Explicit candidates/policy/approval | No fallback/AUTO | Simulation, receipt, explicit binding tests | New proposal required on failure | Approval where policy requires | `LOCAL_ONLY` | Measured quality/cost improvement on real missions |
| Operator app | Cockpit CLI closed; product app not started | CLI over local core | CLI/local process | Mission control yes | Python environment and explicit model contract for LLM mode | CLI | Cockpit product gauntlet | Timeline/replay/pause/kill | Natural confirmation/checkpoints | `LOCAL_ONLY` | Installable tray/compact/full desktop app |

## Safe Baseline Gauntlet

The focused task gauntlet used only existing safe repository capabilities.
It ran 18 representative tests and passed in 15.46 seconds. The broader
adjacent slice ran 270 tests successfully.

The full canonical core suite was also run from
`sentinel-control/services/sentinel-core`:

```text
collected = 2687
passed = 2681
failed = 2
skipped = 4
duration = 662.4 seconds
```

The two failures are baseline findings, not hidden:

1. `test_browser_final_capability_lock_docs_mark_roadmap_complete` is stale
   truth-test drift. It still requires the README current phase to equal
   `PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED`, which conflicts with the canonical
   current-phase model.
2. `test_unsafe_browser_neural_signal_refs_are_hashed_before_memory_or_replan`
   proves tested secrets remain absent, but an unsafe mixed-reference motor
   proposal is rejected as a whole and loses the co-located safe
   `nsig_planner` reference before replan. This is fail-closed but reduces
   useful recovery continuity.

| Task | Result | Duration evidence | Interventions | Replans/recovery | Receipt/proof | Backend maturity | Honest conclusion |
|:--|:--|--:|:--|:--|:--|:--|:--|
| Inspect/hash a repository artifact | PASS | 0.16s | 0 | Drift rejection | Hash-anchored artifact refs | `LOCAL_ONLY` | Artifact-level inspection proven, not a complete repo mission |
| Modify a small file | PASS | 0.03s | 0 | Hash/rollback checks | Workspace receipt | `LIVE_BOUNDED` | Real scoped filesystem mutation |
| Run a command/test-shaped subprocess | PASS | 0.02s | 0 | Timeout/kill covered elsewhere | Receipt + FinalGate | `LIVE_BOUNDED` | Real allowlisted subprocess, not broad shell |
| Recover from an induced task failure | PASS | 0.01s | 0 | Fake browser action fails once then recovers | Orchestrator result | `INJECTED` | Recovery algorithm proven on fake action backend |
| Execute a controlled browser observation | PASS | 3.12s | 0 | N/A | Browser evidence | `LIVE_BOUNDED` | Real Playwright path on local document fixture |
| Perform a multi-step browser task | PASS | 0.01s | 0 | One recovery | Structured result | `INJECTED` | Multi-step logic proven, live web task not proven |
| Resume durable workflow | PASS | 0.80s | 0 | Resume without duplicate certified step | Checkpoint/proof refs | `LOCAL_ONLY` | Strong local durability proof |
| Run governed worker | PASS | 0.13s | 0 | Merge path | Telemetry/evidence | `LOCAL_ONLY` | Same-process governed worker proof |
| Use memory after restart | PASS | 0.04s | 0 | Durable restart recall | Provenance/scoped record | `LOCAL_ONLY` | Durable local memory, uplift not measured |
| Draft a channel message | PASS | 0.05s | 0 | Replay-no-send covered | Draft record | `LOCAL_ONLY` | Draft capability only |
| Run injected channel send | PASS | 0.26s | Approval in test | Scope/rate/revocation gates | Receipt + FinalGate | `INJECTED` | Not a real provider connector |
| Capture desktop monitoring snapshot | PASS | 0.15s | 0 | Unknown metrics represented honestly | Snapshot refs | `INJECTED` | No production OS monitoring backend claimed |
| Run injected desktop action | PASS | 0.20s | Approval in test | Allowlist/kill gates | Receipt + FinalGate | `INJECTED` | No real global desktop action |
| Run injected voice session | PASS | 0.25s | 0 | Barge/kill covered | Transcript refs/telemetry | `INJECTED` | No live audio/provider call |
| Run sandbox spend and paper trade | PASS | 0.60s | Approval refs | Kill/revocation/idempotency covered | Receipts + FinalGate | `SANDBOX` / `PAPER` | No live money |
| Kill a running mission before next step | PASS | 0.33s | 1 kill command | Stops before next step | Timeline/proof | `LOCAL_ONLY` | Kill semantics proven locally |
| Replay without re-execution | PASS | 0.06s | 0 | No action replay | Timeline/replay hash | `LOCAL_ONLY` | Replay safety proven |
| Run cockpit mission flow | PASS | 0.10s | Confirmation flow | Timeline/replay | PowerRuntime refs | `LOCAL_ONLY` | Product flow proven in test cockpit, not installable app |

## What Was Not Demonstrated

```text
normal-user end-to-end repository inspect/edit/test/debug mission
live multi-step public SaaS browser task
real Slack/Telegram/Gmail send
real global desktop click/type
live microphone/STT/TTS conversation
production credential backend
live public-site login
live money or broker action
installable desktop app or OS service
```

## Baseline Risks Found

```text
stale historical truth test = OPEN / docs-test drift
mixed unsafe/safe browser neural refs lose safe recovery ref = OPEN / fail-closed continuity defect
full core suite = NOT GREEN / 2681 passed, 2 failed, 4 skipped
```

Neither open item creates new authority, leaks the tested secret values, or
changes backend maturity. Both should be repaired in the hardening work
attached to the first convergence wave.

Post-baseline truth: both items are now closed by the dedicated zero-growth
green-gate remediation before Wave 1.

## Baseline Commands

```text
18-task evidence gauntlet = 18 passed in 15.46s
adjacent real-world-power slice = 270 passed
full canonical core suite = 2681 passed, 2 failed, 4 skipped / 2687 collected / 662.4s
```

No vendor runtime was run, no external account was connected, and no fake,
injected, sandbox, or paper result is labeled as live external power.
