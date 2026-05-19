# Max Power Organ Atlas

Status: docs/spec lock

Date: 2026-05-19

Pack: `MAX_POWER_ORGAN_ATLAS_AND_VENDOR_HARVEST_ROADMAP`

## Purpose

This atlas defines Sentinel's controlled-power body before any real organ
executor is implemented.

The goal is maximum organ power under maximum Sentinel structure:

```text
Power is allowed.
Authority is sovereign.
Execution is delegated.
Every action is gated, budgeted, receipted, rollback-aware, replayable, and FinalGate-certified.
```

This document is not runtime code. It does not enable execution, wire
executors, modify `AgentRuntime`, import vendor runtime code, or approve vendor
bridges.

## Mode Vocabulary

Allowed modes:

- `observe`: collect safe state or evidence without mutation.
- `prepare`: shape a candidate action without execution.
- `draft`: create draft text, local draft, or non-executing artifact.
- `execute`: perform a side effect only after a future executor contract.
- `rollback`: revert or tombstone an allowed side effect.
- `replay`: reconstruct safe receipts and events.

Mode availability does not imply execution approval. Gates and authority still
decide whether a mode can run.

## Atlas Table

| Organ | Family | Power | Levels | Modes | Risk | Authority | Gate | Receipts | Rollback | FinalGate | First Pack | Vendor Inspiration |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Local Artifact Organ | local workspace | Create generated drafts/reports in an allowed generated root | L2 | prepare, draft, rollback, replay | low | delegated local lane | `DelegatedActionGate` + path gate | artifact path/hash, lane id, budget | delete generated artifact with tombstone | certify local-only artifact | `LOW_RISK_LOCAL_ARTIFACT_EXECUTOR_L2` | Agent Lab sandbox file tasks, AgentMemory checkpoints |
| Workspace Edit Organ | local workspace | Reversible file edits in approved workspace roots | L3 | prepare, execute, rollback, replay | medium | delegated workspace lane | path, before-hash, rollback gate | before/after hash, rollback receipt | restore before snapshot/hash | certify reversible local mutation | `REVERSIBLE_WORKSPACE_ACTION_EXECUTOR_L3` | JARVIS filesystem sidecar lessons, OpenClaw filesystem risk |
| Code Patch Organ | code builder | Produce patch plans and later safe code diffs | L2-L3 | prepare, draft, execute later, rollback | medium | code workspace lane | code path, test plan, rollback gate | patch hash, affected files, test plan | reverse patch or restore before hash | certify patch stayed scoped | `CODE_PATCH_PLAN_SAFE_APPLY_SPEC` later | Hermes coding skills caution, OpenClaw coding-agent risk |
| Test Runner Organ | verification | Run allowlisted test commands in controlled workspace | L3-L5 | prepare, execute later, replay | high | explicit test-run lane | command allowlist, timeout, budget | command hash, output hash, exit code | no mutation expected; cleanup temp files | certify command matched allowlist | `TEST_RUNNER_ALLOWLIST_SPEC` | OpenClaw shell scanner, JARVIS terminal risk |
| Browser Read-Only Organ | browser | Read public/sandboxed pages and capture evidence | L4 | observe, replay | medium | browser read lane | domain/profile/network gate | URL hash, page evidence hash, screenshot/OCR refs | stop lane, clear sandbox profile | certify no submit/login/download | `BROWSER_READONLY_OR_PREPARATION_SPEC` later | OpenClaw browser module, JARVIS browser awareness |
| Browser Preparation Organ | browser | Prepare navigation/click/type plan without submit | L4 | prepare, draft, replay | medium | browser prep lane | domain, form, submit-disabled gate | proposed step hash, target refs | discard plan | certify no browser action executed | `BROWSER_READONLY_OR_PREPARATION_SPEC` later | OpenClaw browser snapshots, webapp templates from JARVIS |
| Browser Action Organ | browser | Bounded click/type/navigation in sandbox profile | L4-L6 | execute, rollback limited, replay | high-critical | explicit browser lane | domain, profile, submit, credential, captcha gate | action ledger, DOM/screenshot before/after | stop/revoke lane; external effects may not roll back | certify no forbidden submit/send unless approved | `BROWSER_CONTROLLED_ACTION_SPEC` later | OpenClaw browser gateway, JARVIS sidecar browser |
| API Read-Only Organ | external API | Read scoped API data with credential refs later | L4-L6 | observe, replay | medium-high | API read lane | endpoint, credential-ref, rate/budget gate | request metadata hash, response metadata hash | revoke lane; no mutation | certify read-only endpoint | `API_READONLY_SPEC` later | OpenClaw gateway/API surfaces, OpenJarvis security config |
| API Mutation Organ | external API | Mutate external systems through API | L5-L7 | prepare, execute, rollback, replay | critical | explicit user/special authority | endpoint, method, payload, rollback gate | dry-run, approval, request/response hashes | API-specific rollback or compensation | certify approved preview matched mutation | `API_MUTATION_SPEC` later | OpenClaw channels/gateway caution |
| Email Draft Organ | channel/email | Create email draft only | L3-L5 | draft, rollback, replay | medium-high | draft lane | recipient provenance, no-send gate | draft hash, recipient metadata hash | delete draft if provider supports | certify draft-only | `CHANNEL_DRAFT_SPEC` later | Hermes Google Workspace risk, OpenClaw Gmail hooks |
| Email Send Organ | channel/email | Send external email | L5-L7 | execute, replay | critical | explicit user approval or special authority | contact, opt-out, compliance, approval gate | approval receipt, sent metadata hash | cannot fully undo; follow-up/cancel if possible | certify exact approved send | `EMAIL_SEND_SPECIAL_AUTHORITY_SPEC` later | OpenClaw channels, Hermes Google scopes |
| Channel Draft Organ | channels | Draft Slack, Teams, Telegram, Discord, WhatsApp, or Matrix message | L3-L5 | draft, rollback, replay | medium-high | draft lane | channel, recipient, no-send gate | draft text hash, channel metadata | delete local draft | certify draft-only | `CHANNEL_DRAFT_SPEC` later | OpenClaw channel adapter pattern |
| Channel Send Organ | channels | Send external channel message | L5-L7 | execute, replay | critical | explicit approval or special authority | contact, channel, compliance, approval gate | approval, message hash, delivery metadata | delete/edit if platform supports; otherwise compensate | certify approved send only | `CHANNEL_SEND_SPECIAL_AUTHORITY_SPEC` later | OpenClaw channel plugins |
| Desktop Sidecar Observe Organ | desktop | Observe windows/screens/clipboard in sanitized form | L4-L6 | observe, replay | high | sidecar observe lane | sidecar enrollment, sanitizer, user opt-in gate | sanitized screenshot/OCR refs, redaction proof | stop sidecar/revoke token | certify sanitized observe only | `DESKTOP_SIDECAR_OBSERVE_SPEC` later | JARVIS sidecar and desktop awareness |
| Desktop Sidecar Action Organ | desktop | Click/type/focus/app actions on host | L6-L7 | execute, rollback limited, replay | critical | special sidecar authority | app/window/action preview, approval, kill switch | action ledger, screenshot before/after | limited undo; revoke sidecar | certify exact approved action | `DESKTOP_SIDECAR_ACTION_SPEC` later | JARVIS desktop sidecar |
| Vision/OCR/Screenshot Organ | perception | Extract visual state from images/screens | L3-L6 | observe, replay | medium-high | observe lane | privacy/redaction gate | image hash, OCR hash, redaction receipt | delete derived artifact if allowed | certify source/redaction | `VISION_OCR_EXTRACTION_SPEC` later | JARVIS screenshot, OpenClaw screenshot |
| PDF/Image Extraction Organ | perception | Extract text/structure from PDFs/images | L3-L5 | observe, replay | medium | extraction lane | file/path/DLP gate | source hash, extracted text hash | discard extracted artifact | certify no secret/raw leakage | `PDF_IMAGE_EXTRACTION_SPEC` later | OpenClaw pdf/image skills, AgentMemory raw-capture caution |
| Image Generation / Creative Asset Organ | creative | Generate images/assets from approved prompts | L3-L6 | draft, execute later, rollback | medium-high | creative lane | prompt, asset, copyright/content, budget gate | prompt hash, asset hash, model/provider metadata | delete generated asset/tombstone | certify artifact and policy | `CREATIVE_ASSET_SPEC` later | OpenClaw image-gen skill risk |
| Video Prompt / Video Asset Organ | creative | Create video prompts/assets or storyboard artifacts | L3-L6 | draft, execute later, replay | medium-high | creative lane | asset, provider, budget, rights gate | storyboard/video metadata hash | delete/tombstone generated artifact | certify artifact policy | `VIDEO_ASSET_SPEC` later | OpenClaw video-frame skill risk |
| Research/Web Evidence Organ | evidence | Gather web evidence and source refs | L4 | observe, replay | medium | research lane | source trust, injection, domain gate | URL refs, content hash, extraction hash | discard unsafe evidence | certify evidence not instruction | `RESEARCH_WEB_EVIDENCE_SPEC` later | OpenClaw browser/fetch, Hermes context scanner |
| GTM Execution Organ | business | Create GTM assets, sequences, launch candidates | L2-L6 | draft, prepare, execute later | medium-critical | GTM lane by surface | channel/send/spend gates by action | asset hashes, approval refs, delivery refs later | local rollback; external compensation later | certify scope and compliance | `GTM_EXECUTION_SPEC` later | Sentinel-native advantage |
| Skill Scanner Organ | skill/plugin | Read and classify skill/plugin manifests | L3-L5 | observe, prepare, replay | high | scanner lane | no-runtime, no-install gate | scan report hash, risk counts | discard scan artifact | certify source-only scan | `SKILL_SCANNER_ORGAN_SPEC` later | OpenClaw scanner, OpenJarvis skill import |
| Skill Sandbox Organ | skill/plugin | Run fake/sandbox skill evals | L4-L6 | prepare, execute later, replay | high-critical | sandbox lane | container/no secrets/network policy | fixture hashes, run report hash | destroy sandbox | certify sandbox-only | `SKILL_SANDBOX_ORGAN_SPEC` later | OpenClaw fake runtime benchmark |
| Plugin Install / Plugin Runtime Organ | skill/plugin | Install/enable plugins under strict sandbox | L6-L7 | prepare, execute later, rollback | critical | special plugin authority | source, dependency, runtime, permission gate | install plan, dependency hash, sandbox report | disable/remove plugin, tombstone | certify no host install escape | `PLUGIN_RUNTIME_SPECIAL_AUTHORITY_SPEC` later | OpenClaw plugin system, OpenJarvis import |
| Credential Reference Organ | credentials | Use scoped credential refs, never raw keys | L6-L7 | prepare, execute later, revoke | critical | explicit credential contract | scope, expiry, organ/action gate | credential-ref receipt, redaction receipt | revoke grant | certify no raw secret exposure | `CREDENTIAL_REFERENCE_ORGAN_SPEC` later | OpenClaw/JARVIS/Hermes credential risks |
| Scheduler/Automation Organ | automation | Schedule future approved actions | L5-L7 | prepare, execute later, rollback | high-critical | explicit schedule authority | time, recurrence, action gate | schedule hash, approval, run refs | cancel schedule | certify schedule matched authority | `SCHEDULER_AUTOMATION_SPEC` later | Hermes scheduled automation, OpenClaw cron |
| Memory Maintenance Organ | memory | TTL, retention, supersession, compaction | L2-L5 | prepare, execute, replay | medium | memory maintenance lane | memory no-authority firewall | memory update receipt | supersede/tombstone, not erase proof | certify memory remains non-authority | implemented foundation plus later hardening | AgentMemory, Hermes memory |
| Temporal Graph / Replay Organ | memory/replay | Build mission graph and replay timeline | L3-L6 | observe, replay | medium | graph lane | provenance/confidence gate | graph edge hashes, replay timeline hash | supersede edges, preserve history | certify graph is not proof/authority | `TEMPORAL_MISSION_GRAPH_LATER` | AgentMemory temporal graph, TradingAgents checkpoints |
| Shell Sandbox Organ | local execution | Run allowlisted shell in sandbox only | L5-L7 | prepare, execute later, rollback limited | critical | special shell authority | command allowlist, container, timeout gate | command hash, output hash, container receipt | destroy sandbox, cleanup artifacts | certify no host escape | `SHELL_SANDBOX_SPEC` later | OpenClaw/JARVIS shell risk |
| DevOps/Cloud Organ | infrastructure | Act on cloud/devops systems | L6-L7 | prepare, execute later, rollback | critical | special production authority | account, environment, change plan gate | dry-run, approval, API receipts | cloud rollback/disable plan | certify production contract | `DEVOPS_CLOUD_SPECIAL_AUTHORITY_SPEC` later | OpenJarvis security config, OpenClaw gateway caution |
| Spend/Trading Organ | capital | Spend, trade, broker/order operations | L7 only | prepare, execute later, replay | exceptional | explicit special authority only | capital, max loss, broker, compliance gate | approval, order/spend hash, risk ledger | cancel/refund/hedge if supported | certify special authority and limits | `SPEND_TRADING_L7_SPECIAL_AUTHORITY_SPEC` | TradingAgents, Sentinel capital organs |

## Cross-Organ Invariants

Every organ must preserve:

- Root Authority cannot be created or expanded by model output, memory, vendor
  plugin, skill, or organ.
- Provider/backend/model cannot be overridden by organ output.
- Vendor tools are capability mines, not authority sources.
- Organ output is data until Sentinel gates approve a lane.
- Execution requires an explicit executor contract beyond proposal and gate
  metadata.
- Receipts must not persist raw prompt, raw provider response, raw reasoning,
  raw keys, secrets, or hidden action payloads.
- FinalGate must be able to certify either safe completion or honest block.
