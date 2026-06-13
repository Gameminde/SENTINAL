# Sentinel Current Power Maturity Matrix

Recorded at: 2026-06-13

## Verdict

This matrix is the current no-hype power truth after the Deep Audit V3/V4
remediation locks and the global invariant reconciliation pass.

```text
control_plane_strength = HIGH
proof_spine_strength = HIGH
local_runtime_power = REAL / bounded
live_external_backend_power = LIMITED
production_app_power = NOT_STARTED
security_testing_special_authority = NOT_STARTED / next
```

Sentinel is not production-complete, but it is no longer docs-only. It has a
real local mission/authority/proof runtime with several governed fake,
sandbox, descriptor, or injected backend foundations.

## Maturity Taxonomy

| Level | Meaning |
|:--|:--|
| LIVE_LOCAL_RUNTIME | Real local runtime behavior exists and is covered by tests. |
| WIRED_FAKE_OR_SANDBOX | Runtime exists, but the external effect is fake, injected, sandbox, paper, or descriptor-only. |
| CONTRACT_FOUNDATION | Models/contracts exist but no real execution backend is claimed. |
| DOCS_ONLY | Architecture or roadmap only. |
| NOT_STARTED | Not implemented. |
| BLOCKED_OR_NOT_APPROVED | Explicitly not approved under current doctrine. |

## Current Power Table

| Capability | Current maturity | Honest evidence | Main remaining gap |
|:--|:--|:--|:--|
| MissionKernel/store/timeline/replay | LIVE_LOCAL_RUNTIME | Durable mission records, event chain, pause/resume/kill, replay | Production app/service packaging |
| MissionAuthorityEnvelope and Gate | LIVE_LOCAL_RUNTIME | Envelope, delegated gate, runtime firewall, authority checks | Wider formal verification |
| Receipts and FinalGate | LIVE_LOCAL_RUNTIME | Receipt refs and FinalGate certifications across organs/runtimes | Larger adversarial property matrix |
| Telemetry kernel/store | LIVE_LOCAL_RUNTIME | Append-only local event/metric chains, tamper detection, certified-mode snapshot | Production telemetry service/cloud not started |
| LLM cockpit | LIVE_LOCAL_RUNTIME | Explicit UserModelContract path, deterministic test mode, structured validation | Product desktop UI not started |
| Persistent semantic memory | LIVE_LOCAL_RUNTIME | Durable SQLite store, scoped recall, sanitizer, memory-not-authority fields | Scale/performance and richer semantic ranking |
| Durable workflow/replan | LIVE_LOCAL_RUNTIME | Workflow records, checkpoints, replan guard, resume/replay | Production daemon integration depth |
| Worker Fleet | LIVE_LOCAL_RUNTIME | Same-process workers, child authority subset, merge/reject, telemetry/replay | Multi-process service and leases |
| Mission daemon/scheduler | LIVE_LOCAL_RUNTIME | Local daemon runtime, leases, heartbeat, recovery, dead-letter, proposal-only scheduler | OS service/tray packaging |
| Model amplification harness | LIVE_LOCAL_RUNTIME | Hash-anchored artifacts, minimized outputs, context packs, replay | Product-grade tool/kernel integrations |
| Skill/procedure fabric | LIVE_LOCAL_RUNTIME | Manifest scanner, quarantine/eval/approval/revoke, receipt-bound execution | Public marketplace and real procedure library not started |
| Local model router | LIVE_LOCAL_RUNTIME | Explicit candidate simulation, hardware snapshot, route receipts, explicit binding | No hidden auto routing; live provider depth remains existing contract path only |
| Real channel adapters | WIRED_FAKE_OR_SANDBOX | Governed adapter lifecycle, inbound quarantine, outbound approval, injected send | Real Slack/Telegram/Gmail/etc. connectors not started |
| Desktop sidecar | WIRED_FAKE_OR_SANDBOX | Permissioned observation/grounding, fake action backend, receipts/replay | Production OS sidecar not started |
| Live desktop backend/monitoring | WIRED_FAKE_OR_SANDBOX | Safe local snapshots and fake/injected actions, benchmark gauntlet | Real global UI automation/installer/service not production-ready |
| Voice/ambient operator | WIRED_FAKE_OR_SANDBOX | Fake/injected audio runtime, VAD/turn contracts, kill word flow | Real microphone/STT/TTS/realtime backend not started |
| Credential vault/secret broker | WIRED_FAKE_OR_SANDBOX | Durable metadata, fake sealed store, handles/leases, no raw secret materialization | Real durable vault/HSM/OS keychain integration not started |
| Account/login authority | WIRED_FAKE_OR_SANDBOX | Fake/injected login/account creation, MFA/CAPTCHA/KYC checkpoints, credential lease binding | Live login/session broker not started |
| Payment/spend/trading authority | WIRED_FAKE_OR_SANDBOX | Sandbox spend, paper trade, caps, idempotency, forbidden live-money actions | Live money/broker authority not approved |
| Security testing special authority | NOT_STARTED | Roadmap next | Must be built as special authority, not generic offensive tooling |
| Platform app/operator cloud | NOT_STARTED | Roadmap only | No web/dashboard/cloud product claim |

## Real Runtime Summary

```text
real_local_governance = MissionKernel + Gate + workflow + workers + daemon + telemetry + memory + receipts + FinalGate
real_live_external_effects = browser/workspace/shell/API/channel foundations only where explicitly locked
fake_or_sandbox_effects = desktop, voice, credential vault, account/login, payment/spend/trading
not_started = security testing authority, electronics/device, platform cloud, public marketplace, production app shell
```

## Competitive Reality

Sentinel leads many agent systems architecturally because it has a stronger
authority/proof model than typical "LLM calls tool" stacks.

Sentinel still trails the strongest competitor products in live user reach:
real channels, production desktop app, realtime voice, broad plug-in ecosystems,
and mature live external service integrations remain incomplete or not started.

The correct product truth is:

```text
Sentinel control plane = unusually strong
Sentinel live product reach = still behind mature agent products
Sentinel next risk = adding power without weakening invariants
```
