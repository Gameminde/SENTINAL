# Sentinel Product Power Scorecard

Recorded at: 2026-06-14

## Scoring Law

Every score is tied to repository evidence and current backend maturity.
Foundations, contracts, fake backends, sandbox results, and paper results do
not receive live-product credit.

| Domain | Score / 10 | Evidence | Current blocker | Competitor reference | Required work to reach 8/10 |
|:--|--:|:--|:--|:--|:--|
| Coding/workspace | 7.5 | Five repeated controlled inspect-edit-test-repair-regression-rollback missions; atomic scoped mutation and proof invariants | Real explicit-model agent run, process-restart coding continuity, and product LSP/debugger path remain open | oh-my-pi, gptme, Agent Zero | Real-model repository corpus with durable process restart, LSP/debugger depth, and bounded interventions |
| Browser | 7.5 | Ten repeated controlled live Playwright missions with multi-tab, submit, upload/download quarantine, login checkpoint, changed-target recovery, revocation, and replay | Public-SaaS corpus and browser-session continuity across process restart remain open | Hermes, Webwright, UI-TARS | Public live-task corpus with restart continuity, changed-state recovery, and bounded interventions |
| Desktop | 3.5 | Injected monitoring and fake actions with strong policy/proof | No production live opt-in OS adapter | UI-TARS, JARVIS, Agent Zero | Real scoped OS action backend plus benchmark success/recovery/kill proof |
| Voice | 3.0 | Fake/injected VAD, transcript, barge-in, kill word | No live microphone/STT/TTS/realtime backend | JARVIS, Hermes | Live local/realtime conversation with latency, interruption, kill, and no authority bypass |
| Channels | 3.0 | Local drafts and injected send lifecycle | No real provider connector | OpenClaw, Hermes, DeerFlow | One production-quality connector with inbound/outbound, auth, replay, recovery, rate limits |
| Memory usefulness | 6.5 | Durable local scoped recall, restart proof, integrations | No measured mission-completion delta | Letta, Hermes | Multi-session utility benchmark showing statistically useful completion/recovery lift |
| Long-task autonomy | 5.5 | Workflow, worker, daemon, leases, heartbeat, recovery foundations | Same-process/local foundation; no OS service or long-duration live missions | gptme, Hermes, Microsoft Agent Framework | Multi-hour restart-safe missions with bounded intervention and complete proof |
| Recovery/replan | 7.0 | Strong resume/retry/replan/tamper/kill local gauntlet | Live external task recovery not measured | Microsoft Agent Framework, JARVIS | Representative live failure corpus and recovery success target |
| Worker parallelism | 5.5 | Governed same-process workers, strict child authority, merge/reject | No multi-process service or measured time improvement | Hermes, DeerFlow, OpenJarvis | Task decomposition benchmark showing lower completion time without cost/error explosion |
| Local model/cost routing | 5.0 | Explicit route simulation, hardware snapshot, receipts | No measured quality/cost delta on real missions | OpenJarvis, gptme | Real task routing benchmark with quality floor, cost/latency delta, explicit approval |
| Credential usability | 3.0 | Fake sealed store, scoped handles/leases, no raw secret persistence | No OS keychain/production vault backend | JARVIS, OpenClaw | Real OS credential backend with user-visible lease/use/revoke UX |
| Operator UX | 4.5 | LLM cockpit CLI, mission status, timeline, replay | No installable tray/compact/full app | Agent Zero, OpenClaw, JARVIS | Lightweight app with fast onboarding, approvals, progress, kill, replay |
| Installation/deployment | 1.5 | Repository and Python CLI only | No installer, OS service, tray, upgrade flow | OpenClaw, Agent Zero, JARVIS | One-command install and reliable local service/app lifecycle |
| Reliability | 7.5 | Repeated Wave 1 vertical gauntlets with zero silent success, duplicate material side effects, and cross-mission contamination; strong local invariant coverage | Long-duration soak and full process-restart convergence remain open | Microsoft Agent Framework, Hermes | Long-duration real-task corpus, process restart recovery, and soak targets |
| Governance/proof | 9.0 | Authority envelope, Gate, receipts, FinalGate, telemetry, replay, kill/revocation | Larger adversarial FinalGate matrix still recommended | Sentinel | Expand cross-surface property tests while preserving current invariants |

## Current Aggregate

```text
unweighted_average = 5.7 / 10
control_and_proof = strongest area
live_product_reach = primary limiter
installation_and_operator_product = weakest area
```

The post-baseline full canonical core suite is green:

```text
2698 collected
2695 passed
0 failed
3 skipped
```

The dedicated green-gate remediation closed the stale historical truth
assertion and the fail-closed browser-neural continuity defect. Wave 1 then
raised only evidence-backed scores: controlled coding/workspace passed five
repetitions and controlled live Playwright browser passed ten repetitions.
Both reported zero silent success, duplicate material side effects, and
cross-mission contamination. The backend is certified; agent-level real-model,
process-restart, public-SaaS, and soak gates remain open.

## Exact 8/10 Certification Gates

### Coding/Workspace 8/10

```text
representative repository missions >= 85% success
inspect -> edit -> test -> debug -> verify flow proven
at least one induced failure recovered automatically
median operator interventions <= 1
workspace escape = 0
receipts/replay completeness >= 98%
```

### Browser 8/10

```text
representative live multi-step task success >= 80%
session continuity across restart proven
changed-selector/state recovery >= 75%
upload/download and login checkpoint flows proven
sensitive/irreversible boundaries pause correctly
median operator interventions <= 1
complete receipts/replay >= 98%
```

### Desktop 8/10

```text
real opt-in OS backend on one supported platform
open/focus/find/click/type/switch/monitor tasks >= 80% success
changed-state recovery >= 70%
sensitive region pause and resume proven
kill latency within defined target
no hidden capture and complete before/after proof
```

### Voice 8/10

```text
real microphone/STT/TTS or local realtime backend
time to first transcript and response within product target
barge-in and kill word reliability >= 99% in test corpus
dangerous requests always become checkpoints
conversation can create/status/pause/resume mission
no raw audio/prompt/provider persistence
```

### Channels 8/10

```text
one production-quality provider connector
inbound identity/scope and untrusted-content handling proven
outbound draft/approval/send lifecycle >= 95% success
recipient/rate/idempotency enforcement proven
restart/retry without duplicate send
complete receipt/FinalGate/replay
```

### Memory 8/10

```text
cross-session benchmark shows meaningful completion or time improvement
stale/contradictory recall detection target met
cross-user/cross-mission leakage = 0
memory-generated authority/model/tool switch = 0
recall latency and storage growth within target
```

### Daemon/Autonomy 8/10

```text
OS service or equivalent durable local supervisor
multi-hour missions with restart/crash recovery
lease/double-run violations = 0
operator handoff and kill proven
autonomous useful minutes and intervention count reported
```

### Operator App 8/10

```text
installable lightweight desktop app
tray, compact, and full cockpit modes
first useful mission within onboarding target
authority/approval/kill/proof understandable without internal JSON
UI close does not stop core; kill does revoke powers
offline/local-first mode proven
```

## Certification Rule

No domain may be called 8/10 from contracts or subsystem tests alone. It must
pass representative end-to-end tasks using the backend maturity being claimed.
