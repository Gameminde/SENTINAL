# P6L Desktop Sidecar Organ Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6L_DESKTOP_SIDECAR_ORGAN_IMPLEMENTATION
previous_phase = P6K_FULL_LOCKED
next_phase = P6M_CODE_SHELL_AGENTLAB_HARVEST
```

## Goal

Implement the Sentinel-native Desktop Sidecar Organ from the P6K JARVIS-first
harvest and blueprint. P6L creates contracts, fake sidecar previews,
sanitizers, receipts, and kill-switch behavior without enabling live host
control.

## Source Pattern

```text
JARVIS sidecar power
+ OpenClaw action preview / approval lifecycle
+ OpenJarvis cost / sandbox / timeout discipline
= Sentinel Desktop Sidecar Organ
```

## Implemented Code

```text
sentinel/organs/desktop/contract.py
sentinel/organs/desktop/sidecar_manifest.py
sentinel/organs/desktop/enrollment.py
sentinel/organs/desktop/action_lifecycle.py
sentinel/organs/desktop/action_preview.py
sentinel/organs/desktop/fake_sidecar.py
sentinel/organs/desktop/screen_sanitizer.py
sentinel/organs/desktop/clipboard_sanitizer.py
sentinel/organs/desktop/receipts.py
sentinel/organs/desktop/kill_switch.py
sentinel/organs/desktop/finalgate_adapter.py
sentinel/organs/desktop/misuse_classifier.py
```

## Implemented Models

```text
PermissionedSidecarManifest
SidecarEnrollmentGrant
SidecarRPCDryRun
DesktopActionPreview
DesktopHighPowerSurface
FakeSidecarProvider
FakeSidecarDryRunResult
ScreenContextSanitizer
ClipboardSanitizer
DesktopActionReceipt
SidecarKillSwitch
DesktopFinalGateAdapter
DesktopMisuseClassifier
```

## Behavior Locked

```text
Desktop organ contract registers through ExternalOrganRegistry.
Manifest declares JARVIS-backed capability families.
Enrollment requires identity, signed enrollment, policy hash, expiry, and evidence.
Stale or revoked sidecars cannot plan fake sidecar previews.
FakeSidecarProvider creates dry-run previews only.
Screen and clipboard context is sanitized before receipts.
Wrong-target mutation is rejected.
Path traversal and symlink escape are rejected for file previews.
Sidecar admin config mutation requires special authority and remains preview-only.
DesktopActionReceipt is deterministic and redacted.
SidecarKillSwitch blocks fake sidecar execution-shaped preview.
DesktopFinalGateAdapter shape exists for future promotion.
High-power surfaces have promotion paths.
Black Lane host misuse objectives remain blocked.
```

## Capability Lane Mapping

| Surface | Lane | Status |
| --- | --- | --- |
| window metadata / system info / awareness | Blue | fake eval candidate |
| screenshot / clipboard / filesystem preview | Red | sanitizer required |
| click / type / keys / launch / focus | Red | special authority candidate |
| sidecar admin config | Red | special authority candidate |
| hidden keystrokes / credential theft / secret capture / authority bypass | Black | blocked misuse objective |

## Boundaries

```text
no vendor runtime bridge
no vendor code copy
no live desktop execution
no host control
no real shell/process execution
no credential secret access
no authority expansion
```

## Verification

```text
P6L targeted tests = 14 passed
P6K neighbor tests = 8 passed
full sentinel-core tests = not run for this small block by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_desktop_sidecar_organ.py -v --tb=short
python -m pytest tests/test_p6_desktop_agentlab_harvest.py -v --tb=short
```
