# JARVIS Desktop Static Audit

Date: 2026-05-09

## Scope

This audit inspects JARVIS as the primary source for Sentinel's Desktop
Sidecar Organ design. It is static analysis only:

```text
no vendor runtime executed
no vendor code copied into Sentinel
no vendor runtime bridge created
no live desktop control enabled
```

Primary source:

```text
agent-lab/vendors/jarvis/source
```

Supporting AgentLab evidence:

```text
agent-lab/audits/jarvis_sidecar_map.md
agent-lab/audits/jarvis_permission_map.md
agent-lab/audits/jarvis_desktop_awareness_map.md
agent-lab/audits/final/jarvis_final_forensic_report.md
agent-lab/audits/final/openclaw_final_forensic_report.md
agent-lab/audits/final/openjarvis_final_forensic_report.md
agent-lab/audits/final/g9_cross_agent_synthesis.md
```

## Source Findings

### Sidecar Capability Manifest

JARVIS exposes a host sidecar capability surface covering:

```text
terminal
filesystem
desktop
browser
clipboard
screenshot
system_info
awareness
```

Source evidence:

```text
agent-lab/vendors/jarvis/source/src/sidecar/types.ts
agent-lab/vendors/jarvis/source/sidecar/types.go
```

Sentinel rewrite:

```text
PermissionedSidecarManifest
DesktopCapabilityMap
DesktopPermissionSurface
```

The important power is not the exact code. The important mechanism is a
machine-level capability declaration that can be mapped into explicit
authority, promotion level, receipts, and trace requirements.

### Enrollment And Revocation

JARVIS uses sidecar enrollment, signing, sidecar identity, and token validation
before accepting remote sidecar connections.

Source evidence:

```text
agent-lab/vendors/jarvis/source/src/sidecar/manager.ts
```

Sentinel rewrite:

```text
SidecarEnrollmentGrant
signed_enrollment
sidecar_identity
policy_hash
revocation
stale_token_rejection
```

P6K preserves this as a blueprint only. P6L must implement the Sentinel-native
contract before any host control exists.

### RPC Registry

JARVIS sidecar handlers expose host action RPCs including:

```text
run_command
read_file
write_file
list_directory
get_clipboard
set_clipboard
capture_screen
get_window_tree
click_element
type_text
press_keys
launch_app
focus_window
find_element
get_config
update_config
```

Source evidence:

```text
agent-lab/vendors/jarvis/source/sidecar/handlers.go
```

Sentinel rewrite:

```text
SidecarRPCDryRun
DesktopActionLifecycle
DesktopActionPreview
SidecarKillSwitch
```

P6K records the full power surface, but does not enable live RPC execution.

### Desktop Awareness And Action Tools

JARVIS desktop tools provide window listing, UI snapshots, screenshots, element
search, click, type, keypress, launch, and focus operations.

Source evidence:

```text
agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts
agent-lab/audits/jarvis_desktop_awareness_map.md
```

Sentinel rewrite:

```text
ScreenContextSanitizer
DesktopActionPreview
DesktopActionLifecycle
target_window_binding
wrong_target_fixture
```

Observation and mutation are intentionally separated. Window metadata can later
be promoted earlier than screenshot, clipboard, click, type, launch, or admin
configuration surfaces.

## Cross-Agent Patterns

OpenClaw contributes action preview and approval lifecycle patterns for
high-power execution surfaces.

OpenJarvis contributes cost, sandbox, timeout, and local execution policy
patterns.

The Sentinel rewrite combines these with JARVIS desktop mechanics:

```text
JARVIS sidecar power
+ OpenClaw approval/action-kernel discipline
+ OpenJarvis local execution budget/sandbox discipline
= Sentinel Desktop Sidecar Blueprint
```

## Failure Modes Harvested

P6K records the following desktop/sidecar failure modes as fixtures for P6L:

```text
path_traversal_or_blocklist_bypass
shell_string_execution_bypass
screenshot_or_clipboard_secret_leak
sidecar_admin_config_escalation
stale_or_revoked_sidecar_token
desktop_keystroke_wrong_target
```

## Verdict

JARVIS is the correct primary source for Desktop. Sentinel should harvest its
sidecar, desktop awareness, and host-control topology, then rewrite it through
Sentinel authority, trace, receipts, kill-switch, and FinalGate.

P6K adds no live desktop execution. It creates the source-backed map and
blueprint required before P6L implementation.
