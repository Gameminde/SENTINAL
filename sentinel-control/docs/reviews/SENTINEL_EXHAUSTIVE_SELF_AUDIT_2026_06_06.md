# Sentinel Exhaustive Self-Audit

Audit executed: 2026-06-07
Requested baseline label retained in filename: 2026-06-06
Inspected baseline HEAD: `987e2ee7f8f930fa38f10c0da66056a6db275141`

## Executive Verdict

Sentinel is a real controlled agentic operating system kernel, not a design
mockup. Its strongest connected path is:

```text
LLM/operator or Brain proposal
-> mission/runtime validation
-> DelegatedActionGate
-> governed organ/executor
-> receipt
-> FinalGate
-> memory feedback and replan-ready context
-> operator/event timeline
```

The system already has live browser, workspace, constrained shell/code,
scoped external API, and injected channel-send paths. It also has a real
LLM-backed cockpit, local mission kernel, replay, and explicit model contract.

The main gap is no longer basic execution. The main gap is durable useful
execution across time and parallel work:

```text
persistent semantic memory
checkpointed workflow and automatic replan
real authority-inheriting worker fleet
production daemon and scheduler
product-grade skills, routing, channels, desktop, and voice
```

The audit also found a recurring truth problem: `CLOSED` is used for several
different maturity levels. A contract with tests, a direct opt-in backend, and
a broadly promoted product path must not share one unqualified status.

## Audit Scope And Method

Inspected:

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/
sentinel-control/docs/organs/
sentinel-control/docs/reviews/
sentinel-control/services/sentinel-core/sentinel/
sentinel-control/services/sentinel-core/tests/
sentinel-control/examples/
```

Source inventory:

```text
Sentinel Python source files inspected/inventoried = 423
test files = 239
test functions discovered = 2229
review documents = 70
organ documents = 70
```

This is a source and documentation audit. No runtime implementation was added
and no runtime test suite was required for this docs-only lock.

## Classification Vocabulary

| Status | Meaning |
| --- | --- |
| `CLOSED` | The scoped lock's acceptance criteria are satisfied. Must be paired with a runtime maturity status where ambiguity is possible. |
| `PARTIALLY_CLOSED` | Important parts are implemented, but the named capability is not complete. |
| `LIVE_RUNTIME` | Current source can execute the capability through a real Sentinel runtime path. |
| `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | A governed path exists, but connector, transport, persistence, or generalization remains narrow. |
| `CONTRACT_TEST_LOCKED` | Models, firewalls, receipts, and tests exist, but broad live runtime power does not. |
| `DOCS_ONLY` | Design or roadmap exists without meaningful current implementation. |
| `NOT_STARTED` | No meaningful implementation exists for the named product capability. |
| `DEFERRED` | Intentionally postponed by an explicit boundary. |
| `STALE_DOC` | Text conflicts with newer source/current truth or presents historical state as current. |
| `ARCHITECTURE_DEBT` | The feature works, but structure or coupling raises maintenance and regression risk. |

## Component Truth Table

| Component | Current Classification | Source Truth | Principal Gap |
| --- | --- | --- | --- |
| Brain / `BrainCognitionLoop` | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Produces opt-in proposals, memory context, evidence-linked cognitive results, and no authority. | It does not itself run a durable worker society or automatic replan loop. |
| `AgentRuntime` | `LIVE_RUNTIME`, `ARCHITECTURE_DEBT` | Real multi-phase runtime, controlled tool calls, organ dispatch, FinalGate, memory feedback, and replan-ready packet. | 3,073-line orchestration monolith; automatic replan remains false. |
| `MissionAuthorityEnvelope` | `LIVE_RUNTIME`, `CLOSED` | Canonical mission scope, allow/deny surfaces, budgets, revocation, and credential-grant metadata. | Future child-worker inheritance and durable resumed-work validation need explicit contracts. |
| Mission runner and seven-gate sequence | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Real mission step execution, cancellation/revocation checks, budgets, traces, and short-circuit gates. | Unknown-tool gate becomes a no-op when the known-tools registry is not supplied. |
| `DelegatedActionGate` | `LIVE_RUNTIME`, `CLOSED` | Mandatory dispatcher gate with canonical scanner, budget, authority, and credential-proof checks. | Large shared policy surface increases regression cost when new organs are added. |
| `OrganDispatcher` | `LIVE_RUNTIME`, `CLOSED`, `ARCHITECTURE_DEBT` | Enforces Gate -> executor -> receipt -> FinalGate for registered organ routes. | 1,645-line routing hub and growing per-organ coupling. |
| `CoreFinalGate` | `LIVE_RUNTIME`, `CLOSED`, `ARCHITECTURE_DEBT` | Terminal invariant aggregation across runtime exits and organ receipts. | 2,854-line god-class; per-surface logic is difficult to evolve safely. |
| `EventBus` | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Hash-chained in-memory event ledger with O(1) append posture and integrity verification. | No production durable WAL/recovery service. |
| `PowerRuntime V0` | `LIVE_RUNTIME`, `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Default-off injected executor, serial governed plan, hash timeline, receipt/FinalGate/memory refs. | No restartable durable workflow, leases, checkpoints, or automatic replan. |
| LLM live operator cockpit | `LIVE_RUNTIME`, `CLOSED` | Real explicit-contract LLM path, structured output validation, safe prompt frame, natural mission intake, and local cockpit CLI. | Local product surface only; no web/voice surface or production daemon. |
| MissionKernel / store / queue | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Local JSON records, JSONL hash-chain events, queue/state transitions, pause/resume/kill, tamper detection. | Local filesystem durability only; no worker leases, transactional recovery, or production service. |
| Operator model client / LLM adapter | `LIVE_RUNTIME`, `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Explicit `UserModelContract`, pinned provider/backend/model, no fallback/AUTO, loopback-only local backend safety. | OpenAI-compatible family path only; no hardware-aware routing or broad provider strategy layer. |
| Browser L4 readonly/prep/semantic | `LIVE_RUNTIME`, `CLOSED` | Real public observation and governed evidence transforms. | Browser output remains untrusted and advanced intelligence is not universally promoted. |
| Browser L5 session manager | `LIVE_RUNTIME`, `CLOSED` | Persistent governed session manager with real backend paths and runtime/dispatcher promotion. | Generic private session/account use remains outside current authority. |
| Browser L6 form/login/file/JS paths | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Special-authority submit, ephemeral credential login broker, upload/download quarantine, and JS sandbox are runtime-wired. | Login is credential-thin; no generic session, durable vault, arbitrary JS, or generic file transfer. |
| Browser neural cortex / signal graph | `CONTRACT_TEST_LOCKED`, `PARTIALLY_CLOSED` | Signal graph, perception/planning/risk/recovery/motor contracts and gauntlets exist. Some motor refs enter runtime/memory. | Not a general neural fabric or autonomous live worker system. |
| Browser DevTools/visual/replay/recovery | `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Direct live backend helpers collect hash-only metadata, screenshot sources, replay events, and recovery requests. | New paths are not broadly AgentRuntime-promoted; OCR engine, live MCP, raw CDP firehose, and response bodies are not started. |
| Browser multi-agent operator squad | `CONTRACT_TEST_LOCKED` | Cognitive role views and ledger tests exist. | No independently executing browser worker fleet. |
| Shell/code sandbox organ | `LIVE_RUNTIME`, `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Real allowlisted subprocess execution with cwd containment, timeout, output cap, receipts, and FinalGate. | No strong OS/container isolation and no unrestricted shell. |
| External API organ | `LIVE_RUNTIME`, `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Real scoped transport; GET/HEAD path and explicit-authority mutation path exist. | No durable credential/OAuth integration and no unbounded mutation. |
| Channel draft/send organ | `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Draft path is real; send path requires authority and injected sender. | No real Telegram/Slack/Gmail/SMTP connector. |
| L2 local artifact executor | `LIVE_RUNTIME`, `CLOSED` | Real scoped writes, post-write readback/hash proof, safe receipts, no rollback overclaim. | Narrow artifact surface by design. |
| L3 reversible workspace executor | `LIVE_RUNTIME`, `CLOSED` | Real scoped mutation, rollback attempt/success separation, readback/hash proof. | Not a broad desktop or code-host control surface. |
| Desktop workspace L6 | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Real scoped list/read/write/create filesystem operations with containment and receipts. | Live host control, screenshot, clipboard, app/window actions remain blocked. |
| Desktop sidecar | `CONTRACT_TEST_LOCKED` | Manifests, fake sidecar, enrollment, sanitizers, receipts, and kill-switch contracts exist. | No live host sidecar or visual computer-use path. |
| Credential foundation | `CONTRACT_TEST_LOCKED`, `RUNTIME_GOVERNED_BUT_BACKEND_THIN` | Credential refs, grants, proofs, revocation/expiry/scope/use checks, and metadata-only access decisions exist. | No durable secret vault or generic real credential resolution. |
| `RoleLoopMemoryBridge` | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Builds evidence-linked feedback memory, contradictions, safe entries, and runtime feedback refs. | Memory is not a durable semantic product store. |
| Safe memory retrieval / replay / slots | `CONTRACT_TEST_LOCKED`, `PARTIALLY_CLOSED` | Safe retrieval contracts, replay builder, and hot-slot selection exist. | No durable FTS/vector/entity store, cross-session ranking, expiry service, or memory utility evaluation. |
| Replan-ready packet | `LIVE_RUNTIME`, `CLOSED` as packet | Runtime emits replan-ready context and reasons. | Automatic governed replan execution is `NOT_STARTED`. |
| Mission timeline / replay | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Operator timeline and replay verify hash chain and do not re-execute actions. | Multiple ledgers are not unified into a durable operational black box. |
| Receipts and receipt ledgers | `LIVE_RUNTIME`, `PARTIALLY_CLOSED` | Organ receipts, FinalGate refs, PowerRuntime timeline, browser neural JSONL ledger, and operator events exist. | Ledger implementations are fragmented; no single durable receipt service. |
| Agent society / worker plans | `CONTRACT_TEST_LOCKED` | Advisory roles, budgets, scopes, evidence/output contracts, and authority subsets are modeled. | `agent_spawning=false` and `runtime_multi_agent_execution=false`; no real worker fleet. |
| Skill/procedure graph | `CONTRACT_TEST_LOCKED` | Advisory matching, authority requirements, canonical steps, proofs, and failure modes exist. | No admitted executable skill fabric, import quarantine, promotion, or revocation runtime. |
| Model cost profiles | `CONTRACT_TEST_LOCKED` | Token/cost projection and explicit model contracts exist. | No hardware discovery, route competition, quality/cost/latency receipts, or product router. |
| Production mission daemon / scheduler | `NOT_STARTED` | Local MissionKernel exists, but no production background service, restart leases, or proactive proposal scheduler. | Entire production operating layer remains. |
| Voice / ambient operator | `DOCS_ONLY`, `NOT_STARTED` | Voice-ready product direction appears in docs. | No microphone, speech, realtime interruption, or voice runtime tests. |
| Spend | `CONTRACT_TEST_LOCKED` | Fake spend provider, authority/policy models, and kill-switch concepts exist. | No real payment rail or provider. |
| Trading | `CONTRACT_TEST_LOCKED` | Paper-only provider and special-authority contracts exist. | No real broker integration. |
| Account creation/login special authority | `CONTRACT_TEST_LOCKED` | Browser boundary and special-authority models/reports exist. | No real account provider, generic login, or durable identity/credential broker. |
| Security testing | `DOCS_ONLY`, `NOT_STARTED` | Future roadmap concept only. | No authorized scope engine, target proof, testing organ, or live execution. |
| Electronics/device/IoT control | `DOCS_ONLY`, `NOT_STARTED` | Future roadmap concept only. | No device enrollment, protocol adapters, safety interlocks, or live organ. |

## Runtime Connection Map

```text
User
  -> LLM Live Operator Cockpit
      -> explicit UserModelContract
      -> structured Operator artifacts
      -> Sentinel validation
      -> MissionKernel record / queue / timeline
          -> OperatorAgentRuntimeBridge (default-off injected runtime)
              -> AgentRuntime
                  -> BrainCognitionLoop proposals
                  -> controlled tool calls
                  -> OrganDispatcher
                      -> DelegatedActionGate
                      -> runtime_execution / organ executor
                      -> receipt
                      -> organ FinalGate
                  -> CoreFinalGate
                  -> RoleLoopMemoryBridge
                  -> replan-ready packet
          -> OperatorPowerRuntimeBridge
              -> PowerRuntime V0
                  -> injected governed actuator executor
                  -> receipts / FinalGate refs / memory refs
          -> operator event stream and replay
```

The operator bridges do not call organs directly. The Brain proposes; it does
not grant authority or execute. PowerRuntime does not discover ambient
executors; missing executors fail closed.

## Authority Flow Map

```text
MissionAuthorityEnvelope
  -> mission scope / allowed actions / tools / paths / domains / budget
  -> MissionRunner gates and revocation checks
  -> DelegatedActionGate exact organ/action decision
  -> organ-local validator/firewall
  -> executor side effect
  -> receipt records what happened
  -> FinalGate certifies terminal result
```

Authority invariants:

```text
LLM output != authority
conversation text != authority
memory != authority
receipt != authority
FinalGate certificate != future permission
credential proof != authority
provider/backend/model selection != authority expansion
```

Risk:

- `sentinel/agent/invariants.py` retains an intentional authority-check stub.
- Gate 6 is a no-op if the known-tools registry is not supplied.
- Child-worker authority inheritance is modeled conceptually but not yet a
  durable runtime mechanism.

## Data Flow Map

```text
user/context/evidence
-> scanner and redaction boundaries
-> cognitive/operator structured data
-> mission plan or power plan
-> governed execution request
-> side-effect result
-> safe receipt / evidence refs / hashes
-> FinalGate result
-> memory feedback and timeline summary
-> future context
```

Raw secrets, raw provider responses, raw reasoning, raw prompts, raw browser
auth surfaces, and unrestricted response bodies are intentionally excluded
from durable operator/runtime records.

## Memory Flow Map

```text
runtime result / role-loop feedback / evidence refs
-> RoleLoopMemoryBridge
-> safe LivingMissionMemoryEntry and contradiction handling
-> hot slots / safe retrieval contracts / replay context
-> Brain or operator context pack
```

Current memory is mostly in-process or supplied to contracts. The local
MissionKernel persists mission state and timelines, but it is not semantic
memory. `PERSISTENT_SEMANTIC_MEMORY_V1` must add durable retrieval without
turning recalled text into authority or instructions.

## Execution Surface Map

| Surface | Real Side Effect | Governing Boundary | Current Limit |
| --- | --- | --- | --- |
| Browser public observation | Yes | Browser authority, session manager, receipts, FinalGate | Public/scoped observation |
| Browser L5 interaction | Yes | Session/action scope, target evidence, receipts, FinalGate | Governed interaction only |
| Browser L6 submit/login/file/JS | Yes, scoped | Special authority, quarantine/sandbox, receipts, FinalGate | No generic private/browser power |
| Workspace L2/L3/L6 | Yes | Path scope, containment, readback/hash, rollback posture | Scoped filesystem only |
| Shell/code sandbox | Yes | Allowlist, cwd, timeout, output cap, receipts, FinalGate | No unrestricted host shell |
| External API | Yes, scoped | Domain/method scope, mutation authority, receipts | No generic credentials/unbounded mutation |
| Channel send | Only with injected sender | Explicit authority, sender injection, receipt | No real connector |
| Desktop host control | No | Contracts/fake sidecar only | Not started |
| Payment/spend | No real provider | Fake provider/contracts | Not started |
| Trading | Paper only | Special-authority contracts | Not started |
| Credential resolution | Ephemeral narrow paths only | Grants/proofs/scopes | No durable vault |

## Documentation Drift

| Drift | Classification | Required Treatment |
| --- | --- | --- |
| `CURRENT_STATE_LOCK.md` contains many historical `current_phase` and `next_phase` blocks. | `STALE_DOC` risk when copied out of context | Keep append-only history, but make the first section explicitly canonical and point to the master roadmap. |
| `SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md` still names `COMPETITIVE_GAP_DELTA_LOCKED` as current phase. | `STALE_DOC` | Update its current execution truth and defer to the new master roadmap. |
| README uses unqualified `CLOSED` for some contract/test-only browser capabilities. | `STALE_DOC` / maturity ambiguity | Add truth taxonomy and master-roadmap link; do not rewrite historical lists in this lock. |
| Historical browser reports list later-implemented work as `NOT_STARTED`. | Historical, not current | Treat as immutable evidence; never use historical report status as current truth. |
| Updated company audit says operator shell/mission daemon is missing. | `STALE_DOC` after cockpit | Superseded by cockpit/external-audit locks and this audit. |
| Agent Lab historical “do not enable browser submit/shell” language predates governed paths. | Historical lab guardrail | Keep as research safety history, not Sentinel current capability truth. |
| Root README has older historical current-state sections far below the current snapshot. | `STALE_DOC` risk | Canonical top section and master roadmap must supersede lower historical sections. |

## Architecture Debt

### High Priority

1. **Runtime and FinalGate god-classes**
   - `agent/runtime.py`: 3,073 lines.
   - `agent/final_gate.py`: 2,854 lines.
   - `agent/organs/runtime_execution.py`: 2,235 lines.
   - `agent/organs/organ_dispatch.py`: 1,645 lines.
   - `organs/browser/final_gate.py`: 1,783 lines.

2. **Fragmented orchestration**
   - MissionRunner, AgentRuntime, PowerRuntime, Browser orchestrator, and
     MissionKernel each manage overlapping lifecycle concepts.
   - A durable workflow layer must unify checkpoints and state transitions
     without creating a bypass runtime.

3. **Fragmented ledgers**
   - EventBus, operator JSONL timeline, browser neural ledger, PowerRuntime
     timeline, and per-organ receipts are related but not one durable service.

4. **Authority invariant gap**
   - An intentional authority-check stub remains in `agent/invariants.py`.
   - Gate 6 can become a no-op without the known-tools registry.

5. **Browser namespace/migration debt**
   - Browser behavior spans `sentinel/agent/browser`,
     `sentinel/agent/organs`, and `sentinel/organs/browser`.
   - Compatibility shims and multiple FinalGate layers complicate ownership.

### Medium Priority

6. **Status vocabulary ambiguity**
   - `CLOSED` frequently means contract closed, direct backend closed, or
     product path closed. New locks must always pair scope status with runtime
     maturity.

7. **Local durability without transactional recovery**
   - MissionKernel JSON/JSONL state is useful but not a production daemon
     store with leases, atomic checkpoint transitions, and crash recovery.

8. **Test concentration**
   - Browser and operator/control boundaries are heavily tested.
   - Voice has zero test files; model-cost routing has no dedicated filename
     group; future power surfaces are mainly contract tests.

9. **Large browser/session executors**
   - Several browser and workspace files exceed 900 lines, increasing the
     regression surface for backend promotion.

## Test Coverage Map

Heuristic classification by test filename:

| Area | Test Files |
| --- | ---: |
| Browser | 73 |
| Operator/cockpit | 14 |
| Runtime other | 12 |
| Control/gate/authority/final/scanner | 11 |
| Actuators/channel/API/shell/desktop/spend/trading | 10 |
| Memory | 8 |
| Power | 3 |
| Credential | 2 |
| Other domain/performance/mission/model tests | 106 |
| **Total** | **239** |

Test functions discovered: `2229`.

Coverage strengths:

- authority boundaries, scanner behavior, browser surface restrictions;
- runtime/dispatcher/Gate/receipt/FinalGate connection tests;
- cockpit structured output, tamper detection, model contract, and lifecycle;
- failure and negative-control tests.

Coverage gaps:

- limited broad real-world/live connector gauntlets;
- no production daemon crash/restart/lease tests;
- no durable semantic memory quality/poisoning benchmark;
- no real worker-fleet concurrency and merge-conflict gauntlet;
- no voice tests;
- future desktop/payment/security/electronics surfaces remain non-live.

## Current Product-Power Score

This is an audit-derived maturity score, not an external benchmark result.

| Axis | Score / 10 | Truth |
| --- | ---: | --- |
| Authority and proof plane | 9.0 | Sentinel leads internally. |
| Cognitive/runtime connection | 7.5 | Real but structurally concentrated. |
| Browser operating subsystem | 8.0 | Broad governed live paths; some advanced promotion remains thin. |
| Operator cockpit | 6.5 | Real LLM cockpit and local kernel; no production surface/daemon. |
| Mission durability and recovery | 4.5 | Local state/replay exists; restartable workflow/replan does not. |
| Persistent semantic memory | 3.5 | Strong contracts/feedback; durable retrieval not started. |
| Worker fleet | 2.0 | Advisory plans only. |
| Channels and external reach | 3.5 | Controlled organ foundation, no real channel connector. |
| Local/hardware/cost routing | 3.5 | Explicit contracts and profiles, no product router. |
| Desktop/voice/ambient reach | 2.5 | Workspace live; sidecar/voice not live. |

```text
overall_product_power = 6.8 / 10
overall_product_readiness = 5.8 / 10
control_plane = 9.0 / 10
```

Sentinel is stronger than a library and weaker than a complete daily operating
system. Its fastest path to a step-change is durable continuity, not another
isolated organ contract.

## What Should Be Next

```text
GO -> PERSISTENT_SEMANTIC_MEMORY_V1
```

The next three compound-power phases must remain:

```text
PERSISTENT_SEMANTIC_MEMORY_V1
-> DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
-> MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

Reason:

- memory gives missions useful cross-session continuity;
- durable workflow turns replan packets into restartable governed progress;
- workers then multiply a workflow that can recover, merge, explain, and stop.

Adding broad channels, desktop, credentials, or payment before those three
layers would increase reach faster than completion reliability.

## Audit Decision

```text
SENTINEL_EXHAUSTIVE_SELF_AUDIT = COMPLETE
recommendation = GO
next_phase = PERSISTENT_SEMANTIC_MEMORY_V1
runtime_changes = none
new_execution_surfaces = none
```
