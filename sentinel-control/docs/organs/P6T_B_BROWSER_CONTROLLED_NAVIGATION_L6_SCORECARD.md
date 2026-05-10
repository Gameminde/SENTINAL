# P6T-B Browser Controlled Navigation L6 Scorecard

Date: 2026-05-10

## Phase

```text
phase = P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_IMPLEMENTATION
previous_phase = P6T_A_FULL_LOCKED
next_phase = P6U_API_AUTHENTICATED_READ_L6
```

## Goal

Promote the existing Sentinel browser capability to controlled navigation L6.

This is a promotion of the existing browser organ, not a new browser family,
browser takeover, login/session automation, form submission, upload/download
automation, stealth/captcha bypass, arbitrary JavaScript execution, or vendor
runtime bridge.

## Implemented Code

```text
sentinel-control/services/sentinel-core/sentinel/organs/browser/navigation_l6.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_controlled_navigation_l6.py
```

## Models And Components

```text
BrowserNavigationAuthority
BrowserNavigationAdapter
BrowserNavigationBudget
BrowserNavigationTimeoutPolicy
BrowserNavigationReceipt
BrowserNavigationResult
BrowserFailureReceipt
BrowserPageEvidenceCard
BrowserNavigationDiffSummary
BrowserLinkCandidateRef
BrowserActionCandidateRef
BrowserNavigationDecisionFrameSlice
BrowserNavigationFinalGate
BrowserNavigationKillSwitch
BrowserNavigationCapabilityScanner
BrowserNavigationReceiptAdapter
BrowserNavigationActionKernel
BrowserNavigationPreview
BrowserRiskRouter
BrowserSchemeClassifier
BrowserQuarantineSandboxPolicy
BrowserSandboxAuthority
BrowserSandboxInspectionReceipt
BrowserSandboxNetworkPolicy
BrowserSandboxArtifactStore
BrowserSandboxEscapeGuard
SuspiciousUrlEvidenceCard
BrowserSandboxDecisionFrameSlice
```

## Source Binding

P6T-B requires these P6T-A source-binding refs:

```text
openclaw_browser_action_kernel
cloakbrowser_power_classification
jarvis_permission_lifecycle
browser_use_action_registry_crosscheck
cua_browser_tool_boundary_crosscheck
chrome_devtools_mcp_cdp_shape_crosscheck
hermes_browser_output_pruning
sentinel_p6r_decision_frame
```

These refs do not grant authority. They prove the implementation is a
Sentinel-native rewrite of audited mechanisms.

## Route Model

| Route | Purpose | P6T-B status |
| --- | --- | --- |
| `NORMAL_NAVIGATION` | `http/https`, allowlisted public domains, read-only navigation | implemented |
| `QUARANTINE_SANDBOX_INSPECTION` | `file:`, `javascript:`, `data:`, localhost/private IP, suspicious redirect | classified and modeled |
| `PROPOSAL_ONLY` | `chrome:`, `devtools:`, profile surfaces, login/session/form/upload/download/account-affecting actions | modeled, not executed |
| `BLACK_LANE_BLOCK` | credential theft, fake identity, KYC bypass, captcha bypass, stealth abuse, malware, fraud/payment abuse | blocked |

## Normal Navigation Capability

P6T-B can:

```text
navigate/read public page on allowlisted domains
fetch/read through the existing public read path shape
extract compact title/text/link evidence
emit deterministic navigation receipts
emit compact page evidence cards
emit link/action candidates as refs
produce BrowserNavigationDecisionFrameSlice compatible with P6R
```

## Context Discipline

P6T-B emits compact page evidence:

```text
title
text summary
text summary hash
page content hash
link candidate refs
navigation receipt refs
risk flags
```

P6T-B does not put these into the LLM-facing frame:

```text
raw page dump
full DOM dump
all links dump
all tool schemas
untrusted page instructions
secret-like content
```

## Sandbox Doctrine

Suspicious URL schemes are not permanently rejected capabilities.

```text
They are denied from NORMAL_NAVIGATION.
They are classified by BrowserSchemeClassifier.
They are routed by BrowserRiskRouter to sandbox/proposal/block according to
authority, objective, and route risk.
```

Sandbox policy is modeled with:

```text
disposable profile
no personal/default profile
no saved cookies/passwords
no credential store
no clipboard/camera/microphone
no host filesystem mount
downloads only to quarantine artifact store
```

## Verification

```text
P6T-B targeted tests = 35 passed
P6C browser organ neighbor tests = 11 passed
P6R/P6Q context economy neighbor tests = 26 passed
P6M reality activation neighbor tests = 8 passed
```

Command:

```bash
python -m pytest tests/test_p6_browser_controlled_navigation_l6.py -v --tb=short
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

## Boundaries

```text
new browser organ family = no
login/session mutation = no
form submit = no
file upload = no
file download automation = no
payment/checkout = no
publishing/posting/sending = no
arbitrary JS execution = no
stealth/captcha/bypass = no
browser profile takeover = no
personal/default browser profile connection = no
credential secret access = no
browser power expansion beyond controlled navigation = no
vendor runtime bridge = no
vendor code copy = no
authority expansion = no
```
