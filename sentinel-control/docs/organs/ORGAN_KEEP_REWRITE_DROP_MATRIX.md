# Organ Keep Rewrite Drop Matrix

Status: audit lock

Date: 2026-05-19

## Decision Vocabulary

- `KEEP`: keep as current foundation with normal hardening.
- `UPGRADE`: keep the concept and code, but wrap or extend it before broader
  promotion.
- `REWRITE`: preserve the capability idea, but replace the execution path with
  Sentinel-native organ contracts.
- `DROP`: do not integrate; only keep as lab evidence or blocked fixture.

## Matrix

| Organ/system | Decision | Justification | Interface compliance | Gate/receipt/rollback/replay state | Main risk | Required action |
| --- | --- | --- | --- | --- | --- | --- |
| BrainCognitionLoop | KEEP | Safe cognition orchestrator, non-executing | partial; not an organ executor | produces safe result only | recommendation-as-authority | keep proposal-only |
| Role loop / proposal artifacts / evidence verifier | KEEP | Core cognition and evidence chain is safe and structured | not organ interface; upstream cognition | receipts/evidence validation exist | hallucinated evidence | keep evidence-bound verifier mandatory |
| Memory bridge / slots / retrieval / replay | KEEP | No-authority witness memory foundation | not organ executor; data layer | snapshots, signals, replay timeline exist | memory/retrieval as instruction | keep data-not-instruction and TTL/contradiction tests |
| OrganProposalBridge | KEEP | Correct candidate-only boundary | close to prepare/draft organ standard | candidates are proposal-only | candidate mistaken for lane | keep non-executing |
| DelegatedActionGate | KEEP | Correct first gate model | gate standard aligned | lanes metadata-only, receipt contract present | lane metadata treated as executable | keep lane execution disabled |
| L2 Local Artifact Executor | KEEP | Clean first body movement | supports standard methods | receipt, rollback/tombstone, FinalGate-ready | content scanner gaps over time | harden with broader DLP and retention |
| L3 Reversible Workspace Executor | KEEP | Clean reversible mutation model | supports standard methods | before/after hash, rollback receipt, tombstone | patch complexity and rollback drift | expand only after test-run/code-review gates |
| Low-Risk FinalGate | KEEP | Certifies receipt truth without authority | certification standard aligned | certificate hash and safety scanner | certificate as future permission | keep non-authoritative |
| AgentRuntime L2/L3 opt-in | KEEP | Explicit method, disabled by default | runtime adapter, not universal organ | returns receipt and certificate | accidental config enablement | keep low-risk-only; no L4+ in this path |
| LocalControlledCapabilityRunner | UPGRADE | Useful legacy local artifact path | partial; older than Organ Interface V1 | receipt exists, no FinalGate low-risk certificate | direct tool-call path in `AgentRuntime.run` | migrate or bridge to L2 executor |
| SafeMissionExecutors | UPGRADE | Practical GTM/research artifact generation | older than Organ Interface V1 | artifact index, generated-root checks | no new gate/FinalGate chain | wrap as L2 local artifact organ |
| ArtifactCaptureSandbox | UPGRADE | Strong capture root and hash model | utility, not organ | capture events and hashes exist | binary/raw capture can persist unsafe data | add scanner/redaction policy and retention |
| Browser read/render/extract | UPGRADE | Powerful perception; already structured | partial browser organ interface | receipts/artifacts exist | web prompt injection and raw body leakage | bind to Browser Read-Only organ gate |
| Browser limited interaction | UPGRADE | Valuable bounded browser action | partial; older V2/V3 contracts | receipts and plan hash checks exist | UI mutation without unified gate | bridge to DelegatedActionGate and browser FinalGate |
| Browser form submit/upload/login/JS/HAR | REWRITE | Capability is desired but critical | strong local contracts, not current unified organ chain | authority receipts exist; rollback limited | external irreversible effects, credentials, script misuse | reintroduce only through L6/L7 browser action contracts |
| Browser operator route injection | UPGRADE | Useful route abstraction | runtime protocol only | depends on route implementation | hidden alternate execution path | require same browser organ contract as runner |
| External API request plan/dry-run | UPGRADE | Good API planning and allowlist foundation | partial organ contract | dry-run receipt exists, execute rejects | authenticated read/mutation future drift | build API Read-Only organ first |
| Channel draft/send gate | UPGRADE | Draft-first and send-blocked model is aligned | partial organ contract | draft and send-gate receipts exist | future provider send bypass | build provider draft before send |
| Credential refs/vault policy | UPGRADE | Strong no-raw-secret policy foundation | partial credential organ | grants, receipts, redaction | raw secret in process memory or grant replay | real vault adapter plus revocation ledger |
| Desktop workspace L6 | UPGRADE | Strong path containment and authority model | partial/older L6 organ | receipts, path proofs, rollback refs | overlaps with new L3 workspace executor | converge with L3 or keep as special desktop scope |
| Desktop sidecar pieces | REWRITE | Sidecar power is desired but host-critical | contracts/fake pieces only | manifest, sanitizer, action lifecycle | screenshot/clipboard/click/type host control | implement observe-only before action sidecar |
| Reality activation | REWRITE | Useful lab proof but too broad for default | not Organ Interface V1 unified | receipts exist but cross-surface direct calls | network/env/file/capital in one module | split into per-organ adapters |
| Spend test-mode provider | UPGRADE | Test-mode spend model is useful | partial L7 organ | authority, kill switch, receipts | real payment promotion | keep fake until L7 special authority |
| Trading paper provider | UPGRADE | Paper/risk structure useful | partial L7 organ | special authority and receipts | real broker/trading risk | keep paper-only; live trading needs exceptional authority |
| Capital sandbox | UPGRADE | Business/capital reasoning valuable | planning organ only | signals/traces exist | false ROI becoming spend pressure | feed only proposals and risk review |
| Async organ scheduler | UPGRADE | Backpressure and queue model valuable | scheduler, not organ | evented route exists | hidden queued execution | only submit after same preflight as synchronous path |
| Capability registry/tool protocol | UPGRADE | Necessary gateway and policy catalog | tool interface, not organ standard | decisions/events exist | manifest permission drift | every powerful manifest must map to an organ |
| Agent Lab scanner/benchmarks | KEEP | Critical no-runtime lab defense | lab tooling | fake eval reports exist | accidentally treating vendor fixture as capability | keep lab-only |
| Vendor runtime code | DROP | Capability mining only | not Sentinel-native | no Sentinel gates | hidden authority, supply-chain, default-open tools | never import or run directly |
| Shell host execution | DROP for default; REWRITE later as sandbox | Host shell is critical | blocked fixture only | no safe executor | host compromise | future containerized shell sandbox spec |
| Plugin marketplace/runtime | DROP for now; REWRITE later | Power multiplier and supply-chain risk | scanner only | no install/runtime gate | untrusted code, secrets, network, shell | skill scanner and sandbox before install |
| MCP memory/tool surface | DROP for now; REWRITE later | Broad tool surface could bypass gates | not implemented | none | memory/tool as authority | build Sentinel-native MCP broker only after organ law |
| RedditPulse `exec(...)` report route | DROP as integration source; REWRITE capability if needed | Host shell through web route is not Sentinel-controlled | not compatible | no Sentinel gate/receipt/rollback/FinalGate | shell injection and key-bearing child env | quarantine; future report generation must be sandbox job organ |
| RedditPulse spawned Python workers | REWRITE if reused | Useful job-worker pattern but outside organ law | not compatible | app-specific logs, no Sentinel receipts | privileged env propagation and provider calls | isolate into scheduler/job organ with safe env and receipts |
| RedditPulse admin scraper command | DROP | Env-configured arbitrary command is too broad | not compatible | no Sentinel rollback/FinalGate | admin/env compromise to arbitrary command | do not harvest execution path |
| Sentinel web mission-status mutation route | UPGRADE | Useful control route but needs explicit route authority if exposed | web API, not organ interface | no organ receipt | availability/authority mutation | require `getRequestUser`/owner/authority envelope checks for production |

## Compatibility Findings

### Organ Interface Standard V1

The newest L2/L3 executors are closest to full compliance because they expose
`observe`, `prepare`, `draft`, `execute`, `rollback`, `replay`,
`render_untrusted_context`, `validate_request`, and `produce_receipt`
equivalents.

Older `sentinel.organs.*` modules often have excellent validators and receipts
but do not all expose the universal method set. They should be upgraded through
adapter packs before promotion.

### DelegatedActionGate Compatibility

The newest chain is compatible. Older browser/desktop/API/channel/capital
organs must be bridged through `OrganProposalBridge` and
`DelegatedActionGate` before broad runtime exposure.

### Receipt Compatibility

Receipts exist across many systems, but schema shape differs:

- `L2LocalArtifactReceipt`, `L3WorkspaceReceipt`, and
  `LowRiskFinalGateCertificate` are current best practice.
- `OrganExecutionReceipt`, browser receipts, desktop receipts, channel
  receipts, API receipts, spend receipts, and trading receipts are valuable but
  should gain adapter hashes and FinalGate mappings.

### Rollback Compatibility

Rollback is strongest in L3. External actions mostly need disable/compensate
posture rather than true rollback. Browser submit, channel send, spend,
trading, and desktop action must never claim full reversibility unless proven.

### Replay Compatibility

Memory replay and older organ replay can be unified by adding stable event
adapters for every receipt family. Replay must remain historical data only.

### Provider Contract Preservation

New model-execution work preserves provider/backend/model contracts. Organ
systems must continue to treat provider/model suggestions as historical or
recommendation data only.

## Final Compatibility Verdict

Keep the current L2/L3 execution chain as the gold standard.

Upgrade older Sentinel-native organs by wrapping them, not by deleting their
power.

Rewrite vendor-inspired and broad high-power surfaces into Sentinel-native
contracts.

Drop vendor runtime import, direct marketplace runtime, default shell, and any
tool surface that bypasses authority, budget, receipts, rollback/disable, and
FinalGate.

Also drop direct reuse of adjacent app process execution. The existence of a
useful worker pattern does not make the worker an organ; it becomes an organ
only after Sentinel rewrites it behind scoped authority, env isolation, receipts,
rollback/disable posture, and FinalGate.
