# Organ Execution Expansion Roadmap

Status: audit lock

Date: 2026-05-19

## Objective

Expand Sentinel toward maximum capability without losing control.

The roadmap optimizes for:

```text
more power,
more evidence,
more receipts,
more rollback/disable posture,
more FinalGate certification,
zero authority drift.
```

## Current Baseline

Implemented and current:

- Brain cognition loop;
- proposal artifacts;
- evidence verifier;
- memory bridge, slots, retrieval, replay/checkpoints;
- OrganProposalBridge;
- DelegatedActionGate;
- L2 Local Artifact Executor;
- L3 Reversible Workspace Action Executor;
- LowRisk FinalGate receipts;
- explicit AgentRuntime L2/L3 opt-in.

Not approved as broad default:

- browser/API/channel/desktop/shell/network/credential execution;
- L4/L5/L6/L7 runtime expansion;
- provider fallback;
- AUTO routing;
- vendor runtime import;
- plugin/MCP runtime.

## Wave 0: Organ Audit Lock

Pack:

- `ORGAN_STATE_OF_THE_SYSTEM_AUDIT`

Capability gain:

- unified map of current and latent organs;
- clear KEEP/UPGRADE/REWRITE/DROP decisions;
- high-power expansion order.

Risk increase:

- none; docs-only.

Rollback strategy:

- no runtime change.

## Wave 1: Harden Current L2/L3 Runtime Opt-In

Packs:

1. `LOW_RISK_LOCAL_ARTIFACT_EXECUTOR_L2_HARDENING`
2. `REVERSIBLE_WORKSPACE_ACTION_EXECUTOR_L3_HARDENING`
3. `LOW_RISK_EXECUTION_REPLAY_ADAPTERS`

Prerequisites:

- current L2/L3 tests pass;
- no `.env` or raw prompt/provider/reasoning durability;
- default runtime remains unchanged.

Capability gain:

- reliable local body movement;
- stronger artifact retention and replay.

Risk increase:

- low; local-only.

Rollback strategy:

- L2 tombstone/delete generated artifacts;
- L3 restore before snapshot/hash.

## Wave 2: Browser Read-Only And Preparation

Status:

- `BROWSER_READONLY_OR_PREPARATION_SPEC` started and locked as the Wave 2
  entry contract.
- Runtime implementation remains not started.
- Browser V3 action surfaces remain out of scope for this wave entry spec.

Packs:

1. `BROWSER_READONLY_OR_PREPARATION_SPEC` - started/locked, docs-only
2. `BROWSER_READONLY_ORGAN_V1`
3. `BROWSER_SEMANTIC_EXTRACTION_ORGAN_V1`
4. `BROWSER_PREPARATION_ORGAN_V1`

Prerequisites:

- data-not-instruction browser renderer;
- domain/redirect policy;
- injection scanner;
- source confidence model;
- no submit/login/upload/download.

Capability gain:

- external web perception;
- safer research autonomy;
- preparation plans for later browser actions.

Risk increase:

- medium because web content is adversarial.

Rollback strategy:

- no external mutation;
- discard/quarantine artifacts;
- revoke browser lane.

Tests:

- prompt injection denied;
- browser submit blocked;
- stale redirect flagged;
- raw body/secrets not durable.

## Wave 3: Research, OCR, PDF, Vision

Packs:

1. `RESEARCH_WEB_EVIDENCE_ORGAN_V1`
2. `VISION_OCR_SCREENSHOT_ORGAN_V1`
3. `PDF_IMAGE_EXTRACTION_ORGAN_V1`

Prerequisites:

- extraction as observation, not instruction;
- DLP/redaction;
- source hashes;
- evidence verifier integration.

Capability gain:

- multimodal perception;
- better evidence gathering;
- stronger browser and desktop grounding.

Risk increase:

- medium-high due to OCR prompt injection and private data.

Rollback strategy:

- delete/quarantine derived artifacts;
- mark extraction as unsafe/historical only.

Tests:

- screenshot secret redacted;
- PDF injection cannot create instruction;
- unsupported claims remain unverified.

## Wave 4: Code Patch, Test Runner, Sandbox Shell

Packs:

1. `CODE_PATCH_PLAN_SAFE_APPLY_SPEC`
2. `TEST_RUNNER_ALLOWLIST_SPEC`
3. `LOW_RISK_CODE_PATCH_EXECUTOR`
4. `TEST_RUNNER_ORGAN_V1`
5. `SHELL_SANDBOX_SPEC`
6. `SHELL_SANDBOX_ORGAN_V1`
7. `JOB_WORKER_ORGAN_SPEC`

Prerequisites:

- L3 rollback hardened;
- allowlisted commands;
- no host shell;
- sandbox/container or disposable workspace;
- stdout/stderr redaction.

Capability gain:

- real code repair and verification;
- controlled diagnostics.
- safe replacement for adjacent ad hoc web-triggered worker/process patterns.

Risk increase:

- high because tests and shell can execute arbitrary project code.

Rollback strategy:

- patch reverse or restore before hashes;
- destroy sandbox;
- no host state changes.

Tests:

- non-allowlisted command blocked;
- dependency install blocked unless separately authorized;
- no credentials/network by default;
- FinalGate sees command/output hashes.
- child env contains only allowlisted keys;
- stdout/stderr are redacted before durable receipts.

## Wave 5: API Read-Only, Then API Mutation

Packs:

1. `API_READONLY_SPEC`
2. `API_READONLY_ORGAN_V1`
3. `API_MUTATION_SPEC`
4. `API_MUTATION_ORGAN_V1`

Prerequisites:

- credential broker refs;
- endpoint allowlist;
- rate/cost budget;
- response redaction;
- exact mutation preview.

Capability gain:

- official data access;
- controlled external system actions later.

Risk increase:

- read-only medium-high, mutation critical.

Rollback strategy:

- read-only none needed;
- mutation compensation or provider-specific rollback.

Tests:

- raw auth header rejected;
- POST/PATCH/DELETE blocked in read-only;
- idempotency/rollback required for mutation.

## Wave 6: Channel And Email Draft, Then Send

Packs:

1. `CHANNEL_DRAFT_SPEC`
2. `EMAIL_DRAFT_ORGAN_V1`
3. `CHANNEL_DRAFT_ORGAN_V1`
4. `EMAIL_SEND_SPECIAL_AUTHORITY_SPEC`
5. `CHANNEL_SEND_SPECIAL_AUTHORITY_SPEC`

Prerequisites:

- recipient provenance;
- compliance/opt-out classifier;
- exact preview;
- user approval;
- provider draft rollback.

Capability gain:

- operational communication power.

Risk increase:

- draft medium, send critical.

Rollback strategy:

- delete draft when possible;
- edit/delete sent message if platform supports;
- compensation follow-up when not reversible.

Tests:

- no send without exact approval;
- recipient provenance missing blocks;
- spam/compliance flags require review.

## Wave 7: Desktop Observe, Then Desktop Action

Packs:

1. `DESKTOP_SIDECAR_OBSERVE_SPEC`
2. `DESKTOP_SIDECAR_OBSERVE_ORGAN_V1`
3. `DESKTOP_SIDECAR_ACTION_SPEC`
4. `DESKTOP_SIDECAR_ACTION_ORGAN_V1`

Prerequisites:

- signed sidecar enrollment;
- sanitizer/redaction;
- user-visible kill switch;
- action preview;
- per-app/window authority.

Capability gain:

- host awareness and eventually local app operation.

Risk increase:

- observe high, action critical.

Rollback strategy:

- revoke sidecar;
- stop session;
- action compensation if possible;
- honest rollback-unavailable receipts.

Tests:

- screenshot secret redacted;
- clipboard raw secret not durable;
- destructive click requires review;
- token replay blocked.

## Wave 8: Skill, Plugin, MCP Ecosystem

Packs:

1. `SKILL_SCANNER_ORGAN_SPEC`
2. `SKILL_SCANNER_ORGAN_V1`
3. `SKILL_SANDBOX_ORGAN_SPEC`
4. `PLUGIN_RUNTIME_SPECIAL_AUTHORITY_SPEC`
5. `MCP_BROKER_ORGAN_SPEC`

Prerequisites:

- source hash and ruleset version;
- no-runtime scanner;
- fake malicious fixtures;
- offline sandbox;
- permission manifest.

Capability gain:

- scalable tool/skill expansion.

Risk increase:

- critical supply-chain risk.

Rollback strategy:

- disable/remove plugin;
- tombstone install metadata;
- destroy sandbox;
- revoke connector grants.

Tests:

- shell plugin blocked;
- secret plugin blocked;
- channel send plugin blocked;
- postinstall disabled;
- MCP tool cannot bypass organ gate.

## Wave 9: Scheduler And Automation

Packs:

1. `SCHEDULER_AUTOMATION_SPEC`
2. `SCHEDULER_METADATA_ORGAN_V1`
3. `SCHEDULER_EXECUTION_REVALIDATION_V1`

Prerequisites:

- replay/checkpoints stable;
- authority expiry;
- cancellation receipts;
- every run revalidates gate and FinalGate.

Capability gain:

- persistent missions and timed operations.

Risk increase:

- high because stale authority can become hidden execution.

Rollback strategy:

- cancel schedule;
- revoke lane;
- mark stale checkpoints historical only.

Tests:

- expired authority blocks scheduled run;
- schedule cannot create new authority;
- recurrence requires new validation.

## Wave 10: Credential Broker, Cloud, DevOps

Packs:

1. `CREDENTIAL_REFERENCE_ORGAN_SPEC`
2. `VAULT_BACKED_CREDENTIAL_BROKER_V1`
3. `DEVOPS_CLOUD_READONLY_SPEC`
4. `DEVOPS_CLOUD_MUTATION_SPECIAL_AUTHORITY_SPEC`

Prerequisites:

- credential refs only;
- short-lived grants;
- revocation ledger;
- cloud account/environment binding;
- plan/apply separation.

Capability gain:

- authenticated operations and infrastructure power.

Risk increase:

- critical.

Rollback strategy:

- revoke credential;
- disable grant;
- cloud rollback/disable plan;
- production freeze gate.

Tests:

- raw secret never reaches memory or prompt;
- wrong organ/action scope blocked;
- production mutation requires special authority.

## Wave 11: Spend And Trading L7

Packs:

1. `SPEND_TEST_MODE_PROVIDER_FINALGATE`
2. `TRADING_LIVE_PAPER_FEED_L6`
3. `SPEND_TRADING_L7_SPECIAL_AUTHORITY_SPEC`
4. `SPEND_TRADING_L7_EXECUTOR_V1`

Prerequisites:

- L7 special authority;
- budget/max-loss;
- kill switch;
- broker/payment contracts;
- compliance review;
- exact approval semantics.

Capability gain:

- capital operations.

Risk increase:

- exceptional.

Rollback strategy:

- cancel/refund if possible;
- hedge/close paper/live positions if explicitly supported;
- kill switch stops future actions;
- honest irreversible receipt if no rollback.

Tests:

- real provider disabled until explicit contract;
- max loss enforced;
- subscription hidden path blocked;
- broker credential scope enforced.

## Anti-Drift Rules

Do not skip from this audit to:

- browser submit;
- browser login;
- channel/email send;
- API mutation;
- desktop action;
- host shell;
- plugin runtime;
- credential access;
- spend/trading;
- provider expansion;
- fallback routing;
- AUTO routing.

Every expansion must produce:

- spec;
- fake eval;
- tests;
- gate;
- executor contract;
- receipt;
- rollback or disable model;
- FinalGate;
- replay adapter.

## Final Nexus Verdict

Current Sentinel organ maturity:

- medium-high overall;
- high for cognition, memory, proposal, gate, L2/L3 local execution;
- medium for browser because power exists but needs unified current-chain
  promotion;
- medium-low for desktop/API/channel/credential/spend/trading runtime promotion.

Current capability level:

- L2/L3 local execution is real and runtime opt-in;
- L4-L7 surfaces exist as contracts, older modules, candidates, fakes, or
  direct-test modules;
- broad autonomous external execution is not enabled by default.

Current safety level:

- strong in the newest L2/L3 chain;
- strong in many validators;
- uneven because older organ families use separate control planes.

Biggest weakness:

- control-plane fragmentation between `sentinel.agent.organs.*`,
  `sentinel.organs.*`, browser controlled tools, mission safe executors, and
  capability manifests, plus adjacent app process execution that is outside
  Sentinel organ law.

Biggest opportunity:

- bind the already-rich browser organ family into the modern delegated action
  gate and FinalGate chain.

Most dangerous future organ:

- plugin/MCP runtime combined with shell/browser/session/credential access. It
  can become a hidden universal executor if not sandboxed and gated.

Highest-value next implementation:

- `BROWSER_READONLY_OR_PREPARATION_SPEC`, followed by a browser read-only organ
  that treats all web output as untrusted evidence data.

Recommended next pack:

```text
BROWSER_READONLY_OR_PREPARATION_SPEC
```

Parallel hardening recommendation:

```text
WEB_AND_JOB_EXECUTION_SURFACE_QUARANTINE_AUDIT
```

This parallel audit should quarantine or rewrite adjacent `RedditPulse` and web
route process/state-mutation surfaces before any worker-like functionality is
harvested into Sentinel.
