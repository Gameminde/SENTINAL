# JARVIS Desktop To Sentinel Integration Notes

Date: 2026-05-09

## Integration Principle

Sentinel does not implement Desktop from a generic spec. Desktop comes from
AgentLab harvest:

```text
JARVIS source and audits
+ OpenClaw approval/action-kernel patterns
+ OpenJarvis cost/sandbox patterns
-> Sentinel-native Desktop Sidecar Organ
```

P6K is the harvest and blueprint phase. P6L is the implementation phase.

## What Sentinel Takes

```text
sidecar capability declaration
sidecar enrollment and revocation pattern
desktop awareness model
window and UI tree observation
screenshot and clipboard surfaces
desktop action RPC taxonomy
config/admin mutation awareness
approval lifecycle concepts
event/log/trace discipline
failure modes from real desktop-agent code
```

## What Sentinel Rewrites

```text
PermissionedSidecarManifest
DesktopCapabilityMap
DesktopPermissionSurface
DesktopActionLifecycle
ScreenContextSanitizer
ClipboardSanitizer
DesktopActionPreview
SidecarEnrollmentGrant
SidecarRPCDryRun
SidecarKillSwitch
```

## What Sentinel Does Not Take

```text
vendor runtime bridge
vendor code copy
raw shell execution
blocklist-only path security
raw screenshot ingestion
raw clipboard ingestion
sidecar admin mutation without signed authority
click/type/keys without target preview
desktop execution without receipts and FinalGate
```

## P6L Build Notes

P6L should implement the Desktop Sidecar Organ from the P6K blueprint with:

```text
contract registration through P6A organ foundry
capability manifest parser
fake sidecar provider
RPC dry-run request model
sanitized observation receipts
action preview receipts
revocation and kill-switch fixtures
wrong-target desktop action fixtures
FinalGate compatibility hooks
```

Live host control remains locked until later promotion.
