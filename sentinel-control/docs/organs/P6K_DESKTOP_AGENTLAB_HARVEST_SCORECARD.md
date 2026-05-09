# P6K Desktop AgentLab Harvest Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6K_DESKTOP_AGENTLAB_HARVEST_AND_BLUEPRINT
previous_phase = P6J1_FULL_LOCKED
next_phase = P6L_DESKTOP_SIDECAR_ORGAN_IMPLEMENTATION
```

## Goal

Build Desktop from real AgentLab/vendor mechanisms, not from a generic desktop
spec. P6K harvests JARVIS first, then OpenClaw and OpenJarvis, and rewrites the
power surface into Sentinel-native contracts and blueprints.

## Required Models

```text
DesktopCapabilityMap
DesktopVendorPattern
DesktopSidecarBlueprint
DesktopPermissionSurface
DesktopActionLifecycle
DesktopFailureMode
DesktopHarvestIntegrator
```

Status: implemented.

## Source Coverage

| Source | Coverage |
| --- | --- |
| JARVIS | sidecar manifest, enrollment, desktop awareness, RPC registry, clipboard/screenshot, admin config |
| OpenClaw | action preview and approval lifecycle patterns |
| OpenJarvis | cost, sandbox, timeout, local execution policy patterns |

## Sentinel Rewrites

```text
PermissionedSidecarManifest
DesktopCapabilityMap
DesktopPermissionSurface
DesktopActionLifecycle
ScreenContextSanitizer
ClipboardSanitizer
SidecarEnrollmentGrant
SidecarRPCDryRun
DesktopActionPreview
SidecarKillSwitch
DesktopCostAndSandboxPolicy
```

## High-Power Surface Handling

Desktop powers are classified as high-power operator capabilities with promotion
paths. P6K does not delete them and does not activate them.

```text
window metadata observation -> Blue Lane candidate
screenshot/clipboard -> Red Lane candidate with sanitizer and approval
click/type/keys/launch/focus -> Red Lane special authority candidate
sidecar admin mutation -> Red Lane special authority candidate
```

Black Lane misuse objectives remain blocked:

```text
fake identity
credential theft
hidden keystrokes
wrong-target mutation
secret capture
authority bypass
vendor runtime bridge
```

## Boundaries

```text
no vendor code copy
no vendor runtime bridge
no live desktop execution
no host control
no credential access
no shell/process execution
no authority expansion
```

## Verification

```text
P6K targeted tests = 8 passed
P6J neighbor tests = 10 passed
P6C-P6I.6 organ tests = 89 passed
P5L Brain neighbor tests = 23 passed
full sentinel-core tests = 754 passed
```

Commands:

```bash
python -m pytest tests/test_p6_desktop_agentlab_harvest.py -v --tb=short
python -m pytest tests/test_p6_agentlab_implementation_alignment.py -v --tb=short
python -m pytest tests/test_p6_browser_organ_contract.py tests/test_p6_external_api_organ.py tests/test_p6_channel_organ.py tests/test_p6_credential_vault_policy.py tests/test_p6_capital_operator_sandbox.py tests/test_p6_spend_runtime_limited.py tests/test_p6_trading_special_authority.py tests/test_p6_capital_stack_hardening.py tests/test_p6_tradingagents_harvest.py -v --tb=short
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
```
