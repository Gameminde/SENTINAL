# P6B Agent Lab Organ Harvest Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6B_AGENT_LAB_ORGAN_HARVEST
status = FULL_LOCK_CANDIDATE
previous_phase = P6A_FULL_LOCKED
next_phase = P6C_BROWSER_ORGAN_CONTRACT_REVIEW
promotion = L0/L1 forensic observation -> L2 Sentinel contract candidates
```

## Purpose

P6B turns Agent Lab forensic evidence into machine-readable organ harvest
candidates. It does not import vendor runtime, copy vendor code, register live
organs, or add external execution powers.

## Source Coverage

```text
OpenClaw = harvested as SentinelActionKernel candidate
Hermes = harvested as SentinelMemorySkillSpec candidate
OpenJarvis = harvested as SentinelCostRouter candidate
JARVIS = harvested as PermissionedSidecarManifest candidate
financial-services = harvested as FinancialProcedureGraph candidate
CloakBrowser = harvested as BrowserPowerGovernor candidate
```

## Machine-Readable Models

```text
AgentLabHarvestSource = present
OrganHarvestCandidate = present
AgentLabOrganHarvestMatrix = present
AgentLabOrganHarvestClassifier = present
HarvestSourceKind = present
HarvestPowerFamily = present
HarvestCandidateStatus = present
```

## Locked Harvest Rules

```text
source evidence refs required = pass
candidate evidence must come from declared source = pass
target promotion fixed to L2 Sentinel contract candidate = pass
vendor code copy rejected = pass
vendor runtime bridge rejected = pass
authority expansion rejected = pass
runtime powers added = 0
candidate IDs deterministic = pass
matrix ID deterministic = pass
VendorHarvestReference projection remains rewrite knowledge only = pass
high-risk runtime surfaces preserved as blocked findings = pass
evented harvest matrix records trace without execution = pass
```

## Blocked Runtime Surfaces Preserved As Findings

```text
shell_execution
browser_submit
channel_send
dynamic_plugin_install
memory_as_policy
autonomous_skill_execution
oauth_skill_setup
fail_open_hooks
host_shell_execution
runtime_skill_sync
open_by_default_capability_policy
learned_config_autowrite
raw_shell
clipboard_read
screenshot_capture
desktop_keystrokes
arbitrary_cdp_evaluate
payment_execution
trade_execution
investment_advice_without_review
credential_access
fake_identity
kyc_bypass
credential_theft
unauthorized_scraping
access_control_evasion
```

## Tests

```text
python -m pytest tests/test_p6_agent_lab_organ_harvest.py -v --tb=short
result = 9 passed

python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
result = 20 passed

python -m pytest tests/test_agent_event_bus.py tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
result = 30 passed

python -m pytest tests -v --tb=short
result = 647 passed
```

## No-Power Confirmation

```text
browser execution added = no
payment/spend runtime added = no
trading runtime added = no
account creation runtime added = no
credential access added = no
external API execution added = no
channel send added = no
sidecar execution added = no
vendor runtime bridge added = no
vendor code copied = no
silent authority expansion = no
```
