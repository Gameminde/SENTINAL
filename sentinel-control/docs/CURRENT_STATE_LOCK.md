# Current State Lock

Date: 2026-05-09

## Phase

```text
current_phase = P6N_FULL_LOCKED
previous_phase = P6M_FULL_LOCKED
next_phase = P6O_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN
```

P6N Existing Organs Capability Frontier is accepted as full locked. It pushes
the P6M-activated organs to their practical limits before adding any new organ
family.

P6N measures:

```text
what each organ can do now
what each organ can only simulate/test-mode
what each organ cannot do yet
what fails or is too weak
what needs runtime/provider work
what requires LLM runtime integration
what should be promoted next
```

P6N does not add a new organ family, start Code/Shell harvest, add real
payment, real trading, live channel send, account creation, credential secret
logging, browser power expansion, host desktop control, shell/process
execution, or authority expansion.

## P6N Verification

```text
P6N targeted tests = 8 passed
P6M neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_existing_organs_capability_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

P6N required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/capability_frontier.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_existing_organs_capability_frontier.py
sentinel-control/docs/organs/P6N_EXISTING_ORGANS_CAPABILITY_FRONTIER_SCORECARD.md
sentinel-control/docs/organs/P6N_ORGAN_LIMITS_MAP.md
sentinel-control/docs/organs/P6N_LOCK_VERDICT.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6N findings:

```text
Sentinel can do public reads, read-only API calls, local drafts, env credential
refs, workspace file ops, capital signal ingestion, market-data paper trading,
and test-mode spend.
Sentinel can only simulate/test-mode live spend, real trading, channel send,
and desktop host control.
Sentinel cannot yet do authenticated live provider workflows, account creation,
browser mutation, or shell execution.
Weakest organ = credentials.
Closest organ to production-scoped execution = desktop.
Organs needing LLM runtime first = channel, capital, trading.
No authority expansion is allowed.
```

## Prior P6M Phase

P6M Reality Activation for Existing Organs remains accepted as full locked. It
changes the direction from adding another organ family to making the already
created organs do scoped real work.

## Prior P6L Phase

P6L Desktop Sidecar Organ Implementation remains accepted as full locked. It
implements the Sentinel-native Desktop Sidecar Organ from the P6K JARVIS-first
harvest and blueprint.

## Prior P6K Phase

P6K Desktop AgentLab Harvest and Blueprint remains accepted as full locked. It
prevents Sentinel from building the Desktop Sidecar Organ from a generic
specification by harvesting JARVIS first, then OpenClaw and OpenJarvis, and
rewriting their desktop/sidecar mechanisms into Sentinel-native blueprint
models.

## Prior P6J1 Phase

P6J1 Power Surface Doctrine Reframe remains accepted as full locked. It corrects
the P6J vocabulary so Sentinel treats advanced browser, live API, channel,
credential, spend, trading, and sidecar surfaces as high-power operator
capabilities with promotion paths, not as capabilities to delete.

## Prior P6J Phase

P6J AgentLab Implementation Alignment remains accepted as full locked. It
verifies that every implemented P6C-P6I.6 organ maps to source-backed
AgentLab/vendor patterns and has a Sentinel-native rewrite, capability
classification, and promotion path.

## Prior P6I.6 Phase

P6I.6 TradingAgents Harvest remains accepted as full locked. It clones
TauricResearch/TradingAgents into AgentLab for static audit only, extracts its
multi-agent trading-desk patterns, and integrates them into Sentinel as
Sentinel-native internal trading cognition.

## Prior P6I.5 Phase

P6I.5 Capital Stack Hardening remains accepted as full locked. It hardens the
locked P6G/P6H/P6I capital stack after logic review by binding spend proposals
to real signal refs, capping sandbox budget reallocation, binding spend
kill-switches to the authority mission, blocking credential-ref overrides,
enforcing trading authority asset scope, enforcing max leverage, and broadening
profit-guarantee detection.

## Prior P6I Phase

P6I Trading Special Authority remains accepted as full locked. It defines
paper-first trading special authority, broker contracts, asset policy, position
sizing, max-loss policy, stop-loss policy, trade journal, paper trade provider,
and deterministic trading receipts.

## Prior P6H Phase

P6H Spend Runtime Limited remains accepted as full locked. It defines explicit
spend authority, spend requests, provider adapter interface, fake/sandbox
provider, spend receipts, subscription guard, refund/cancel path, and spend kill
switch.

P6H does not execute real payment providers, grant authority, add browser
execution, implement real trading runtime, account creation, credential access,
external API execution, channel send, sidecar execution, vendor runtime bridges,
vendor code copies, or silent authority expansion.

## P6H Verification

```text
targeted P6H tests = 10 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_spend_runtime_limited.py -v --tb=short
```

P6H required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/spend/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/spend/runtime.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_spend_runtime_limited.py
sentinel-control/docs/organs/P6H_SPEND_RUNTIME_LIMITED_SCORECARD.md
sentinel-control/docs/organs/P6H_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6H rules:

```text
Spend authority requires explicit budget, vendor, category, expiry, receipt, and
kill switch.
FakeSpendProvider creates sandbox receipts only.
Real provider interface exists but is disabled by default.
Budget overrun and single-transaction overrun are blocked.
Hidden subscriptions are blocked.
Explicit subscriptions require explicit authority and refund/cancel path.
Credential use is reference-only; raw credential material is blocked.
SpendReceipt cannot start real payment, access secrets, or expand authority.
```

## Prior P6G Phase

P6G Capital Operator Sandbox remains accepted as full locked. It defines
opportunity modeling, signal ledgers, adaptive operating envelopes, sandbox
budget reallocation, dynamic spend proposals, capital risk review, and
deterministic capital sandbox receipts without live spend.

P6G does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6G Verification

```text
targeted P6G tests = 9 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_capital_operator_sandbox.py -v --tb=short
```

P6G required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/capital/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/capital/sandbox.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_capital_operator_sandbox.py
sentinel-control/docs/organs/P6G_CAPITAL_OPERATOR_SANDBOX_SCORECARD.md
sentinel-control/docs/organs/P6G_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6G rules:

```text
Capital opportunities and planned Browser/API/Channel/Credential inputs are
modeled as sandbox references only.
SignalLedger records market, API, outreach, ROI, and risk signals.
Dynamic budget reallocation requires signal refs.
CapitalRiskReview flags profit guarantee claims.
DynamicSpendPolicy produces spend proposals only.
CapitalSandboxReceipt cannot start spend, execution, or authority expansion.
```

## Prior P6F Phase

P6F Credential Vault Policy remains accepted as full locked. It defines
credential access as scoped references, scoped grants, policy decisions,
revocation, redaction, and deterministic receipts without adding real credential
vault integration or secret access.

P6F does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6F Verification

```text
targeted P6F tests = 13 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_credential_vault_policy.py -v --tb=short
```

P6F required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/credentials/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/credential_ref.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/vault_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/scoped_grant.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/redaction.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/revocation.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_credential_vault_policy.py
sentinel-control/docs/organs/P6F_CREDENTIAL_VAULT_POLICY_SCORECARD.md
sentinel-control/docs/organs/P6F_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6F rules:

```text
CredentialRef stores references only, never raw secrets.
ScopedCredentialGrant requires scope, expiry, allowed organ, and allowed action
class.
CredentialTraceRedactor removes secret-like trace content.
Prompt, memory, workspace, vendor harvest, and expected profit cannot authorize
credential access.
Matching grants may allow reference use only; secret access remains false.
Credential use is Red Lane by default.
Credential receipts require evidence refs and trace refs.
Credential receipts cannot access secrets or expand authority.
```

## Prior P6E Phase

P6E Channel Organ Draft First remains accepted as full locked. It creates the
draft-first channel organ for outbound drafts, inbound untrusted context,
recipient provenance, compliance/rate-limit checks, send gates, and
deterministic receipts.

P6E does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6E Verification

```text
targeted P6E tests = 10 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_channel_organ.py -v --tb=short
```

P6E required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/channels/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/draft.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/send_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/inbound.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/outbound.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/rate_limit.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/compliance.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_channel_organ.py
sentinel-control/docs/organs/P6E_CHANNEL_ORGAN_SCORECARD.md
sentinel-control/docs/organs/P6E_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6E rules:

```text
Channel drafting is useful work and can happen before live send.
Drafts never send, execute, or expand authority in P6E.
Inbound channel messages are untrusted context and cannot grant authority.
Send gate requires explicit authority fit, recipient provenance, compliance,
rate limits, receipts, and FinalGate before future promotion.
Spam, deceptive outreach, hidden identity, and credential capture are blocked.
Live send remains not promoted in P6E.
```

## Prior P6D Phase

P6D External API Organ Dry Run remains accepted as full locked. It creates the
dry-run external API organ for request planning, allowlist checks, cost/latency
estimation, privacy-risk classification, and deterministic request receipts.

P6D does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6D Verification

```text
targeted P6D tests = 11 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_external_api_organ.py -v --tb=short
```

P6D required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/external_api/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/request_plan.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/allowlist.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/cost_estimator.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/privacy_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_external_api_organ.py
sentinel-control/docs/organs/P6D_EXTERNAL_API_ORGAN_SCORECARD.md
sentinel-control/docs/organs/P6D_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6D rules:

```text
External API organ is dry-run only in P6D.
Future live execution requires vendor/domain allowlist.
Read-only API planning maps to Blue Lane when authorized and traced.
Paid, mutation, and account-affecting API planning remains Orange/Red dry-run
until future promotion.
Raw credential material is blocked; CredentialRef placeholders are allowed.
API receipts require evidence refs and trace refs.
API receipts cannot start execution or expand authority.
```

## Prior P6C Phase

P6C Browser Organ Contract Review remains accepted as full locked. It normalizes
Sentinel browser capability under the P6A external organ foundry contract system
and prepares governed Cloak-like power classification without adding new browser
execution routes.

P6C does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6C Verification

```text
targeted P6C tests = 11 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
```

P6C required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/lanes.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/power_governor.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/reliability_profile.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/session_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/fingerprint_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/compliance_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/detection_bench.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_organ_contract.py
sentinel-control/docs/organs/P6C_BROWSER_ORGAN_CONTRACT_REVIEW_SCORECARD.md
sentinel-control/docs/organs/P6C_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6C rules:

```text
Cloak-like browser powers are classified and governed, not discarded.
P5 is misuse-objective rejection, not capability deletion.
BrowserPowerGovernor may downgrade stronger power to the lowest needed safe
power.
Read-only public browsing maps to Blue Lane when authorized and traced.
Sensitive submit/form/click/login/upload actions remain dry-run/proposal unless
future promotion explicitly authorizes them.
P4 stealth-class browser power requires special authority.
Browser receipts require evidence refs and trace refs.
Browser receipts cannot start execution or expand authority.
```

## Prior P6B Phase

P6B Agent Lab Organ Harvest remains accepted as full locked. It turns forensic
evidence from Agent Lab and external source ledgers into deterministic,
machine-readable Sentinel organ harvest candidates.

P6B does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6B Verification

```text
targeted P6B tests = 9 passed
P6A neighbor tests = 20 passed
event bus + P5L neighbor tests = 30 passed
full sentinel-core regression = 647 passed
```

Commands verified:

```bash
python -m pytest tests/test_p6_agent_lab_organ_harvest.py -v --tb=short
python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
python -m pytest tests/test_agent_event_bus.py tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
```

P6B required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/vendor_harvest.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_agent_lab_organ_harvest.py
sentinel-control/docs/organs/P6B_AGENT_LAB_ORGAN_HARVEST_SCORECARD.md
sentinel-control/docs/organs/P6B_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6B harvest candidates:

```text
OpenClaw -> SentinelActionKernel
Hermes -> SentinelMemorySkillSpec
OpenJarvis -> SentinelCostRouter
JARVIS -> PermissionedSidecarManifest
financial-services -> FinancialProcedureGraph
CloakBrowser -> BrowserPowerGovernor
```

Locked P6B rules:

```text
Agent Lab harvests mechanisms, not vendor runtime.
P6B candidates are L2 Sentinel contract candidates only.
P6B does not register executable organs.
P6B does not grant authority.
P6B does not copy vendor code.
P6B does not bridge vendor runtime.
P6B preserves dangerous runtime surfaces as blocked findings.
VendorHarvestReference remains rewrite knowledge only.
```

## Autonomy/Risk Lane Doctrine

This doctrine corrects the interpretation of P6A safety. Sentinel must become
more autonomous inside explicit authority, not less autonomous.

```text
Green Lane:
local, reversible, low-risk actions; auto-execute when authorized.

Blue Lane:
external read-only or low-risk actions; auto-execute with trace when
authorized.

Orange Lane:
cost/account/message/API actions; execute inside explicit RootAuthorityEnvelope
and risk budget, without micro-approval for every small authorized action.

Red Lane:
trading, spend runtime, credentials, desktop/sidecar, stealth browser; require
special authority, caps, receipts, kill switch, and FinalGate.

Black Lane:
fraud, fake identity, KYC bypass, credential theft, illegal spam, unlawful
evasion, profit guarantees; always blocked as misuse objectives.
```

```text
blocked-by-default = not executable until promoted
blocked-by-default != forbidden forever
powerful-by-authority > safe-by-refusal
```

Risk is allowed only when user authority is explicit, risk budget exists, the
action class is promoted, receipts/replay exist, kill switch exists, and
FinalGate passes.

Risk is not allowed when it crosses root authority, hides cost or identity,
creates unapproved obligation, violates legal/compliance boundaries, or bypasses
policy.

## Prior P6A Phase

P6A External Organ Foundry remains accepted as full locked. It creates the
Sentinel-native contract layer for future external organs without adding real
external execution powers.

## P6A Verification

```text
targeted P6A tests = 20 passed
P5L integrated review tests = 23 passed
full sentinel-core regression = 638 passed
```

Commands verified:

```bash
python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
```

P6A required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/authority.py
sentinel-control/services/sentinel-core/sentinel/organs/contracts.py
sentinel-control/services/sentinel-core/sentinel/organs/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/organs/promotion_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/registry.py
sentinel-control/services/sentinel-core/sentinel/organs/replay.py
sentinel-control/services/sentinel-core/sentinel/organs/risk.py
sentinel-control/services/sentinel-core/tests/test_p6_external_organ_foundry.py
sentinel-control/docs/organs/P6A_EXTERNAL_ORGAN_FOUNDRY_SCORECARD.md
sentinel-control/docs/organs/P6A_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6A rules:

```text
ExternalOrganContract requires authority mapping, risk profile schema,
dry-run receipt schema, execution receipt schema, trace/event compatibility,
kill-switch compatibility, source refs, and FinalGate compatibility.
VendorHarvestReference records rewrite knowledge only and cannot grant
authority.
Signals, workspace, memory, and expected profit cannot expand authority.
Payment/trading/account/credential action classes are blocked by default.
Dry-run-only organ authority cannot execute.
Execution-shaped receipts require explicit executable authority and untriggered
kill switch.
Receipts use deterministic hashes and replay rejects forged/mismatched records.
Promotion toward execution requires eval dataset, risk map, failure modes,
rollback/disable plan, receipt schema, kill switch, and FinalGate adapter.
```

## Prior Architecture Lock

The Sentinel A to Z architecture lock remains the project compass before P6
external organs. It records where Sentinel's powers are harvested from, why they
matter, how they are rewritten under Sentinel authority, which product workflows
use them, and which promotion levels must be passed before execution.

## Architecture A To Z Verification

```text
docs-only architecture lock = created
external source ledger = financial-services and CloakBrowser recorded
CloakBrowser powers = classified, not discarded
misuse objectives = blocked by Brain power governance
product workflow map = created
repo governance and dirty-tree policy = created
promotion ladder L0-L8 = created
runtime powers added = 0
vendor code copied = 0
```

Required files:

```text
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/00_README_PROJECT_COMPASS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/01_ORIGIN_AND_NORTH_STAR.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/02_AGENT_LAB_FORENSIC_EVIDENCE_INDEX.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/03_POWER_HARVEST_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/04_COMPARATIVE_ARCHITECTURE_ANALYSIS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/05_TRADEOFF_DECISION_LEDGER.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/06_SENTINEL_SYSTEM_ARCHITECTURE_A_TO_Z.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/07_DIRECTORY_AND_FILE_BLUEPRINT.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/08_ADVISORY_TO_EXECUTABLE_PROMOTION_LADDER.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/09_SIMULATION_AND_PREMORTEM_SCENARIOS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/10_PRESERVATION_CONSTRAINTS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/12_P6A_EXTERNAL_ORGAN_FOUNDRY_SPEC.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/13_ARCHITECTURE_LOCK_VERDICT.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/14_PRODUCT_WORKFLOW_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/15_REPO_GOVERNANCE_AND_DIRTY_TREE_POLICY.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/18_SOURCE_RESEARCH_LEDGER.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## Prior P5L Phase

P5L remains accepted as full locked. It integrates and hardens the Brain L4 stack
before P6 external organs. It does not execute external systems, grant authority,
add external powers, implement payment/spend runtime, trading runtime, account
creation, credential access, browser power expansion, or authority expansion.

## Verification

```text
targeted P5L tests = 23 passed
targeted full P5 suite with P5L = 102 passed
full sentinel-core regression = 618 passed
targeted P5K tests = 9 passed
targeted full P5 suite = 79 passed
full sentinel-core regression = 595 passed
targeted P5J tests = 6 passed
targeted P5I tests = 10 passed
targeted P5H tests = 7 passed
targeted P5G tests = 7 passed
targeted P5F tests = 6 passed
targeted P5E tests = 11 passed
targeted P5B/P5C/P5D neighbor tests = 23 passed
P5D.5 docs verification = diff check passed
targeted P5D tests = 11 passed
targeted P5B/P5C tests = 12 passed
```

Commands verified:

```bash
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py tests/test_agent_global_workspace.py tests/test_agent_bayesian_belief_state.py tests/test_agent_adaptive_debate.py tests/test_agent_epistemic_action.py tests/test_agent_resourcefulness_engine.py tests/test_agent_skill_procedure_graph.py tests/test_agent_brainbench.py tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
python -m pytest tests/test_agent_brainbench.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py tests/test_agent_global_workspace.py tests/test_agent_bayesian_belief_state.py tests/test_agent_adaptive_debate.py tests/test_agent_epistemic_action.py tests/test_agent_resourcefulness_engine.py tests/test_agent_skill_procedure_graph.py tests/test_agent_brainbench.py -v --tb=short
python -m pytest tests -v --tb=short
python -m pytest tests/test_agent_skill_procedure_graph.py -v --tb=short
python -m pytest tests/test_agent_resourcefulness_engine.py -v --tb=short
python -m pytest tests/test_agent_epistemic_action.py -v --tb=short
python -m pytest tests/test_agent_adaptive_debate.py -v --tb=short
python -m pytest tests/test_agent_bayesian_belief_state.py -v --tb=short
python -m pytest tests/test_agent_global_workspace.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py -v --tb=short
git diff --check -- sentinel-control/docs/CURRENT_STATE_LOCK.md sentinel-control/docs/brain
python -m pytest tests/test_agent_society_manager.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py -v --tb=short
```

Full sentinel-core was rerun after P5L and passed.

## P5L Required Files

These files are required to preserve the P5L full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/workspace.py
sentinel-control/services/sentinel-core/sentinel/agent/resourcefulness.py
sentinel-control/services/sentinel-core/sentinel/agent/brainbench.py
sentinel-control/services/sentinel-core/tests/test_agent_brain_l4_integrated_review.py
sentinel-control/services/sentinel-core/tests/test_agent_brain_l4_premortem_fixtures.py
sentinel-control/docs/brain/P5L_BRAIN_L4_INTEGRATED_REVIEW.md
sentinel-control/docs/brain/P5L_PREMORTEM_HARDENING_SCORECARD.md
sentinel-control/docs/brain/P5L_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5L Locked Doctrine

P5L certifies the Brain L4 stack as an integrated internal cognitive system.

It hardens these pre-mortem classes:

```text
over/under agent allocation
workspace fact pollution
belief confidence inflation
debate false positive/false negative routing
unsafe high-information action ranking
resourcefulness authority bypass
silent authority extension activation
partial success mislabeled as full success
skill procedure missing-authority execution recommendation
capital profit guarantee claims
dynamic spend changes without signal refs
dirty broadcast context leakage
role creation without first-principles purpose
missing or forged P5 trace events
```

P5L remains internal. It does not attach real-world execution organs.

## P5K Required Files

These files are required to preserve the P5K full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/brainbench.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_brainbench.py
sentinel-control/docs/brain/P5K_BRAINBENCH_SCORECARD.md
sentinel-control/docs/brain/P5K_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5K Locked Doctrine

`BrainBench` is evaluation only.

It produces:

```text
BrainBenchCase
BrainBenchReport
allocation_accuracy
belief_update_quality
debate_trigger_precision
information_gain_score
cost_efficiency
trace_integrity
negative authority-expansion cases
```

It may emit:

```text
BRAINBENCH_CASE_RUN
BRAINBENCH_REPORT_CREATED
```

BrainBench rejects forged L4 traces and authority-expansion attempts.

## P5J Required Files

These files are required to preserve the P5J full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/skill_procedure.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_skill_procedure_graph.py
sentinel-control/docs/brain/P5J_SKILL_PROCEDURE_GRAPH_SCORECARD.md
sentinel-control/docs/brain/P5J_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5J Locked Doctrine

`SkillProcedureGraph` is advisory only.

It produces:

```text
SkillProcedure
SkillProcedureMatch
ProcedurePrecondition
RequiredAuthority
CanonicalStep
SuccessProof
KnownFailureMode
```

It may emit:

```text
SKILL_PROCEDURE_MATCHED
```

Skill memory recommends procedures, but never grants authority or starts
execution.

## P5I Required Files

These files are required to preserve the P5I full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/resourcefulness.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_resourcefulness_engine.py
sentinel-control/docs/brain/P5I_RESOURCEFULNESS_ENGINE_SCORECARD.md
sentinel-control/docs/brain/P5I_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5I Locked Doctrine

`ResourcefulnessEngine` is advisory only.

It produces:

```text
ResourcefulnessDecision
DebrouilleLevel D0-D5
FallbackPlanSet
ToolSubstitutionDecision
PartialSuccessReport
AuthorityExtensionProposal
```

It may emit:

```text
RESOURCEFULNESS_ROUTED
FALLBACK_PLAN_CREATED
TOOL_SUBSTITUTION_PROPOSED
PARTIAL_SUCCESS_DECLARED
AUTHORITY_EXTENSION_PROPOSED
```

AuthorityExtensionProposal is proposal-only and cannot activate new authority.

## P5H Required Files

These files are required to preserve the P5H full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/epistemic_action.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_epistemic_action.py
sentinel-control/docs/brain/P5H_EPISTEMIC_ACTION_EVALUATOR_SCORECARD.md
sentinel-control/docs/brain/P5H_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5H Locked Doctrine

`EpistemicActionEvaluator` is advisory only.

It produces:

```text
EpistemicActionScore
expected_progress
expected_information_gain
risk_penalty
cost_penalty
authority_impact
total_action_value
```

It may emit:

```text
EPISTEMIC_ACTION_SCORED
```

Action value never authorizes execution. Unsafe high-information actions remain
blocked or proposal-only outside this evaluator.

## P5G Required Files

These files are required to preserve the P5G full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/adaptive_debate.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_adaptive_debate.py
sentinel-control/docs/brain/P5G_ADAPTIVE_DEBATE_SPARSE_MOA_SCORECARD.md
sentinel-control/docs/brain/P5G_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5G Locked Doctrine

`AdaptiveDebateRouter` is advisory only.

It produces:

```text
DebateRoute
DebateRolePlan
SparseMoAPlan
DebateAggregationPlan
unresolved_disputes
fan_in_limit
max_layers
max_debate_rounds
```

It may emit:

```text
DEBATE_ROUTED
MOA_LAYER_COMPLETED
DEBATE_AGGREGATED
```

Debate planning never executes agents, calls tools, or expands authority.

## P5F Required Files

These files are required to preserve the P5F full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/belief_state.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_bayesian_belief_state.py
sentinel-control/docs/brain/P5F_BAYESIAN_BELIEF_STATE_SCORECARD.md
sentinel-control/docs/brain/P5F_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5F Locked Doctrine

`BayesianBeliefState` is advisory only.

It produces:

```text
Belief
BeliefUpdate
EvidenceSupport
ContradictionSupport
belief_probability
belief_variance
posterior_update_reason
```

It may emit:

```text
BELIEF_STATE_UPDATED
```

Belief confidence informs cognition only. It never grants tools, actions, paths,
browser powers, payment powers, credentials, or authority.

## P5E Required Files

These files are required to preserve the P5E full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/workspace.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_global_workspace.py
sentinel-control/docs/brain/P5E_MISSION_GLOBAL_WORKSPACE_SCORECARD.md
sentinel-control/docs/brain/P5E_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5E Locked Doctrine

`MissionGlobalWorkspace` is the versioned shared cognition layer.

It produces:

```text
WorkspaceSnapshot
WorkspaceDelta
BroadcastSlice
WorkspaceFact
WorkspaceClaim
WorkspaceSignal
WorkspaceAgentOutput
WorkspaceOpenQuestion
WorkspaceRejectedClaim
```

It may emit:

```text
WORKSPACE_SNAPSHOT_CREATED
WORKSPACE_BROADCAST_PREPARED
WORKSPACE_DELTA_APPLIED
```

It stores facts, claims, questions, rejected claims, signal observations, and
agent outputs. It never grants tools, actions, paths, browser powers, payment
powers, credentials, or authority.

Rejected claims cannot be reintroduced as accepted facts.

Broadcast slices must be role-specific and minimized rather than dumping the
whole workspace.

## P5D.5 Required Files

These files are required to preserve the P5D.5 full lock:

```text
sentinel-control/docs/brain/P5D5_CAPITAL_OPERATOR_DOCTRINE.md
sentinel-control/docs/brain/P5D5_ADAPTIVE_OPERATING_ENVELOPE.md
sentinel-control/docs/brain/P5D5_SIGNAL_RESPONSIVE_SPEND_POLICY.md
sentinel-control/docs/brain/P5D5_LOCK_VERDICT.md
sentinel-control/docs/brain/P5A_BRAIN_L4_ROADMAP.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5D.5 Locked Doctrine

P5D.5 locks:

```text
RootAuthorityEnvelope = fixed user mandate boundaries
AdaptiveOperatingEnvelope = dynamic operating parameters inside root boundaries
SignalLedger = evidence for operating changes
BudgetReallocator = moves spend toward stronger signals without crossing authority
DynamicSpendPolicy = spend/hold/scale/cut/propose-extension doctrine
SpendDecisionTrace = reason, signal, risk, budget, receipt, and stop-condition proof
```

Core rule:

```text
Authority boundaries do not silently expand.
Operational allocation must adapt continuously inside those boundaries.
```

Current core still treats payment/spend/credential actions as blocked black-zone
actions. P5D.5 does not change runtime behavior.

If explicit spend authority is granted in a future runtime, Sentinel should be
able to act inside that authority rather than remain passive. Any action outside
root authority requires an `AuthorityExtensionProposal`.

## P5D Required Files

These files are required to preserve the P5D full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/agent_society.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_society_manager.py
sentinel-control/docs/brain/P5D_AGENT_SOCIETY_SCORECARD.md
sentinel-control/docs/brain/P5D_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5D Locked Doctrine

`AgentSocietyManager` is advisory only.

It consumes:

```text
AgentCountRoute
MissionEntropyEstimate
MissionAuthorityEnvelope
```

It produces deterministic outputs:

```text
AgentSocietyPlan
AgentRoleAssignment
AgentOutputContract
AgentRolePurpose
AgentSocietyPlanStatus
```

It may emit:

```text
AGENT_SOCIETY_PLANNED
AGENT_ROLE_ASSIGNED
```

Each role must map to at least one P5C.5 first-principles purpose:

```text
exploration
verification
aggregation
contradiction
cost control
context compression
authority-bound fallback
```

It must not grant:

```text
tools
actions
paths
browser powers
external systems
credentials
payments
channel sending
desktop control
```

It must not spawn agents and must not implement runtime multi-agent execution.

## P5C.5 Required Files

These files remain required to preserve the P5C.5 full lock:

```text
sentinel-control/docs/brain/P5C5_FIRST_PRINCIPLES_BRAIN_STACK.md
sentinel-control/docs/brain/P5C5_INFORMATION_THERMODYNAMICS_CONTRACT.md
sentinel-control/docs/brain/P5C5_ENTROPY_BUDGET_MODEL.md
sentinel-control/docs/brain/P5C5_MATH_TO_ALGORITHM_TRANSLATION.md
sentinel-control/docs/brain/P5C5_LOCK_VERDICT.md
```

## P5C Required Files

These files remain required to preserve the P5C full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/agent_count.py
sentinel-control/services/sentinel-core/tests/test_agent_count_controller.py
sentinel-control/docs/brain/P5C_AGENT_COUNT_SCORECARD.md
sentinel-control/docs/brain/P5C_LOCK_VERDICT.md
```

## P5B Required Files

These files remain required to preserve the P5B full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/mission_entropy.py
sentinel-control/services/sentinel-core/tests/test_agent_mission_entropy.py
sentinel-control/docs/brain/P5B_MISSION_ENTROPY_SCORECARD.md
sentinel-control/docs/brain/P5B_LOCK_VERDICT.md
```

## Boundary

Do not stop the P5 sprint unless a hard blocker appears.

Do not start the next organ.

Do not add new browser powers.

Do not implement runtime multi-agent execution.

Do not implement payment/spend runtime.

Do not implement trading runtime.

Do not implement account creation.

Do not silently expand authority.
