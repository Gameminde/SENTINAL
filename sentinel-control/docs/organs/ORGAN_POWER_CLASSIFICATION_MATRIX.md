# Organ Power Classification Matrix

Status: audit lock

Date: 2026-05-19

## Classification Scale

| Level | Meaning | Baseline control |
| --- | --- | --- |
| L2 | Local draft or local artifact generation | generated workspace root, path containment, receipt |
| L3 | Reversible local workspace mutation | approved root, before/after hash, rollback proof |
| L4 | Read-only external perception or preparation | domain/endpoint allowlist, untrusted context, no mutation |
| L5 | Controlled external action | approval, preview, external receipt, rollback/disable posture |
| L6 | Sensitive delegated execution | special authority, credential refs, kill switch, FinalGate |
| L7 | Critical/high-risk execution | exceptional authority, budget/loss caps, compliance, human review |

Power level is a maximum capability classification. It does not imply current
default runtime availability.

## Matrix

| Organ/system | Paths | Level | Why | Real-world power | Attack surface | Missing controls before expansion |
| --- | --- | --- | --- | --- | --- | --- |
| Local Artifact Executor | `sentinel/agent/organs/local_artifact_executor.py` | L2 | Creates local drafts/reports only under contract | First controlled body movement; artifact creation | path traversal, secret persistence, hidden payloads | integrate with broader replay and long-term artifact retention policy |
| Reversible Workspace Executor | `sentinel/agent/organs/reversible_workspace_executor.py` | L3 | Mutates local text/json files with before/after proof | Can modify workspace content | symlink escape, overwrite, rollback failure, hidden executable payloads | broaden patch support only after test-run and code-review gates |
| Safe Mission Executors | `sentinel/mission/safe_executors.py` | L2-L3 | Writes generated project artifacts and GTM packs | Produces user-visible local project outputs | older path outside new DelegatedActionGate | wrap or migrate into L2 local artifact executor |
| Local Controlled Capability Runner | `sentinel/agent/controlled_capability.py` | L2 | Creates markdown/json artifacts through manifest policy | Direct local tool-call artifact creation | model-provided tool calls, artifact path tricks | bind to new organ candidate/gate chain or keep strictly limited |
| Artifact Capture Sandbox | `sentinel/agent/artifact_capture.py` | L2-L3 | Captures text/json/binary artifacts in mission capture root | Stores browser/tool outputs | binary capture, existing-file collision, raw content persistence | add uniform raw secret/prompt scanner for all capture kinds |
| Brain Cognition Loop | `sentinel/agent/brain/cognition_loop.py` | L2 planning only | Orchestrates cognition and memory, cannot execute | Produces next-step recommendations | recommendation treated as instruction | keep as proposal-only; never grant authority |
| Role/Proposal/Evidence loop | `sentinel/agent/llm/*.py` | L2 planning only | Generates and validates plans, evidence, memory summaries | High cognitive leverage | hallucinated evidence, prompt injection, authority pressure | maintain evidence-bound verifier and no-authority firewall |
| Memory bridge/slots/retrieval/replay | `sentinel/agent/llm/memory_*.py` | L2-L4 data | Stores/retrieves/replays scoped memory as data | Improves attention and continuity | memory poisoning, stale evidence, replay poisoning | never inject as instruction; TTL and contradiction survival tests |
| Organ Proposal Bridge | `sentinel/agent/organs/proposal_bridge.py` | L2-L5 candidate | Converts proposals into organ-specific candidates | Maps cognition to body plans | candidate mistaken for permission | keep candidate-only and data-not-instruction |
| Delegated Action Gate | `sentinel/agent/organs/delegated_action_gate.py` | L2-L5 gate | Classifies authority, risk, evidence, budget, organ contract | Creates metadata-only lanes | lane metadata treated as execution grant | keep `execution_enabled=false`; require explicit executor contracts |
| Low-Risk FinalGate | `sentinel/agent/organs/low_risk_finalgate.py` | L2-L3 certification | Certifies receipts, never executes | Creates auditable certification | certificate treated as future permission | keep certificate non-authoritative |
| AgentRuntime L2/L3 opt-in | `sentinel/agent/organs/runtime_execution.py`, `agent/runtime.py` | L2-L3 | Explicit local-only runtime path | Makes L2/L3 usable through runtime | config misuse, authority envelope bypass | keep disabled by default; never support L4+ here |
| Browser read/render/extract | `sentinel/organs/browser/live_fetch.py`, `rendered_snapshot.py`, `extraction.py`, `dom_snapshot.py`, `accessibility_snapshot.py`, `pdf.py` | L4 | Reads and renders public web evidence | Gives Sentinel web perception | prompt injection, privacy leakage, network SSRF-like misuse | domain policy, untrusted rendering, DLP, no raw body durability |
| Browser limited interaction | `sentinel/organs/browser/interaction_execution.py` | L5 | Executes bounded click/type/fill/select/hover/wait plan | Can mutate web UI state without submit | UI spoofing, stale snapshot, hidden submit, cross-origin drift | bind to modern DelegatedActionGate and browser FinalGate |
| Browser form submit | `sentinel/organs/browser/form_submit.py` | L6 | Submits forms after V3 authority | External user-visible web mutation | account creation, posting, purchase, irreversible submit | special authority, exact preview, user review, external-effect receipt |
| Browser upload/download | `sentinel/organs/browser/upload_authorized.py`, `download_quarantine.py` | L5-L6 | Uploads certified artifacts or downloads into quarantine | Data movement between local and web | exfiltration, malware, oversharing, download risk | DLP, artifact certification, quarantine, upload recipient proof |
| Browser private session/login/cookie/HAR/JS | `sentinel/organs/browser/v3_advanced_authorities.py` | L6-L7 | Private sessions, vault-indirected login, storage, script, HAR | Account/session power | credential exposure, account mutation, arbitrary JS, raw body capture | credential broker, redaction, script hash allowlist, session destroy proof |
| Browser operator route | `sentinel/agent/browser/operator_runtime.py`, runtime injection | L4-L6 | Routes browser actions through alternate operator path | Browser execution abstraction | hidden action path if route is injected loosely | require same organ contract and FinalGate as browser runner |
| External API plan/dry run | `sentinel/organs/external_api/*` | L4-L5 | Plans GET/HEAD read-only requests, rejects live execute | API perception and future mutation planning | raw auth headers, endpoint drift, paid/account-affecting calls | authenticated read adapter and API FinalGate |
| Channel draft/send gate | `sentinel/organs/channels/*` | L3-L6 | Drafts messages, send gate always dry-run in current code | External communication potential | unauthorized send, spam, recipient poisoning | provider draft adapter, provenance, compliance, exact send approval |
| Credential reference/vault policy | `sentinel/organs/credentials/*` | L6-L7 | Scoped refs, grants, redaction, policy | Unlocks private APIs/accounts later | raw secret exposure, grant replay, scope confusion | real vault adapter, revocation ledger, no raw secret durability |
| Desktop workspace L6 | `sentinel/organs/desktop/workspace_l6.py` | L6 | Workspace list/read/write/create under desktop authority | Sensitive host/workspace control | host file mutation, sensitive file access | migrate down into L3 where possible or keep special authority for desktop scope |
| Desktop sidecar observe/action pieces | `sentinel/organs/desktop/*` | L6-L7 | Sidecar manifest, screen sanitizer, action lifecycle, fake sidecar | Host observation/action | screenshots, clipboard, click/type, app control | enrollment, signed sidecar, sanitizer, kill switch, user review |
| Reality activation | `sentinel/organs/reality_activation.py` | L4-L7 | Real read-only browser/API, local draft write, env ref resolve, desktop write, paper trade, spend test mode | Cross-organ prototype of real-world actions | direct network, env secret in memory, local write, fake capital actions | wrap every capability in modern organ contracts before promotion |
| Spend test-mode provider | `sentinel/organs/spend/runtime.py` | L7 | Fake/test-mode spend only; real provider disabled | Capital movement architecture | accidental real provider, subscription abuse | L7 special authority, refund/cancel proof, kill switch |
| Trading paper provider | `sentinel/organs/trading/special_authority.py` | L7 | Paper trades with special authority; real trading disabled | Trading decision architecture | broker credentials, real order risk, market hallucination | live only under L7 exceptional authority, max loss, broker FinalGate |
| Capital sandbox | `sentinel/organs/capital/sandbox.py` | L5-L7 planning | Converts signals into spend/opportunity proposals | Business/capital planning | false profit signal, budget pressure | evidence-bound inputs and no auto-spend |
| Async organ scheduler | `sentinel/perf/sched/*` | L2-L6 scheduler | Routes organ-shaped work when injected | Throughput and backpressure | scheduled hidden execution, queue replay | keep injection-gated, preserve authority/dry-run/kill-switch preflight |
| Capability registry/tool-call protocol | `sentinel/capabilities/*`, `sentinel/agent/tool_call_protocol.py` | L2-L6 tool gateway | Parses and policy-checks tool calls | Main tool surface inside `AgentRuntime.run()` | prompt-injected tool calls, manifest overpermission | do not add powerful manifests without organ interface compliance |
| Skill/plugin scanner lab | `agent-lab/tools/openclaw_static_scanner` | L4-L6 lab | Scans OpenClaw-like skills/plugins | Future plugin ecosystem defense | supply-chain, shell/install/secret plugins | keep no-runtime until scanner plus sandbox gates exist |
| Vendor harvest models | `sentinel/organs/vendor_harvest.py`, `desktop/harvest.py`, `trading/tradingagents_harvest.py` | L2-L4 planning | Converts vendor lessons into matrices | Capability mining | vendor pattern becoming authority | keep source-only, proposal-only |
| Shell/host command fixture | `sentinel/capabilities/fixtures/static_catalog.py` | L7 blocked | Explicitly blocked shell execution manifest | Host command power | total host compromise | shell sandbox spec only; never host shell by default |
| Email send candidate | `sentinel/capabilities/fixtures/static_catalog.py` | L6-L7 candidate | Candidate-only outbound email send | External message send | spam, legal/compliance, account mutation | draft-first, send gate, exact approval |
| RedditPulse report route | `RedditPulse/app/src/app/api/scan/[id]/report/route.ts` | L7 adjacent surface | Starts a Python report command through Node `exec(...)` | Web-triggered host process execution with provider/service env | shell injection, credential exposure, stdout/stderr leakage | do not reuse; rewrite as sandbox shell/test organ with env isolation |
| RedditPulse Python worker routes | `RedditPulse/app/src/app/api/scan/route.ts`, `api/enrich/route.ts`, `api/discover/route.ts`, `app/src/lib/queue.ts` | L6-L7 adjacent surface | Spawn Python workers with argument arrays | Web-triggered provider-backed jobs | privileged env in child process, worker output leakage | isolate env, route through job organ, no shell, explicit receipts |
| RedditPulse admin scraper | `RedditPulse/app/src/lib/admin-data.ts`, `api/admin/jobs/run-scraper/route.ts` | L7 adjacent surface | Executes env-configured admin command | Admin-controlled host process power | admin/env compromise becomes arbitrary command execution | quarantine; never import as Sentinel organ |
| Sentinel web mission-status route | `sentinel-control/apps/web/app/api/missions/[missionId]/status/route.ts` | L4-L5 web control | Mutates mission status | Can pause/stop/revoke mission state | unauthenticated/local-mode authority mutation if exposed | require route auth/authority checks before production exposure |

## Highest-Power Current Surfaces

The most powerful existing surfaces are:

1. Browser V3 form submit, upload, login, private session, cookie/storage, JS,
   and HAR body capture.
2. Desktop workspace L6 and sidecar models.
3. Reality activation env credential resolver, network readers, desktop writer,
   spend test-mode, and paper trading.
4. Capability registry plus direct tool-call parsing inside `AgentRuntime.run`.
5. Future skill/plugin/MCP surfaces represented by Agent Lab scanner fixtures.
6. Adjacent `RedditPulse` web-triggered process execution and privileged env
   propagation, which are outside Sentinel organ law.

## Classification Verdict

Sentinel already contains L6/L7-shaped organs, but most are gated, fake,
direct-test-only, or dormant. The current production-quality execution chain is
L2/L3 local only. The safest expansion path is not adding more raw capability;
it is binding existing high-power surfaces to the same modern law proven by
L2/L3:

```text
explicit authority -> gate -> executor contract -> receipt -> FinalGate -> replay
```
