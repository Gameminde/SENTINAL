# JARVIS Desktop Capability Map

Date: 2026-05-09

## Capability Families

| Capability family | JARVIS source mechanism | Sentinel rewrite | P6K status |
| --- | --- | --- | --- |
| Sidecar capability manifest | Sidecar advertises terminal, filesystem, desktop, browser, clipboard, screenshot, system info, and awareness | `PermissionedSidecarManifest`, `DesktopCapabilityMap` | Harvested, not executable |
| Sidecar enrollment | Signed sidecar identity and token validation | `SidecarEnrollmentGrant`, revocation ledger | Blueprinted |
| RPC registry | Host RPC methods for files, clipboard, screenshot, desktop, browser, config, and terminal | `SidecarRPCDryRun`, `DesktopActionLifecycle` | Classified, no live RPC |
| Desktop observation | Window list, UI tree, screenshot, element search | `ScreenContextSanitizer`, context minimization | Planned promotion path |
| Desktop mutation | Click, type, keys, launch, focus | `DesktopActionPreview`, approval, kill-switch, FinalGate | Special-authority blueprint |
| Clipboard | Get/set clipboard | `ClipboardSanitizer`, preview, trace | Special-authority blueprint |
| Sidecar admin | Get/update config | Signed manifest update with revocation | Special-authority blueprint |
| Local execution | Terminal/filesystem patterns | Future typed executor and sandbox policy | Desktop shell disabled in P6K |

## Power Classification

P6K treats desktop powers as high-power operator surfaces, not as capabilities to
delete. The difference is:

```text
capability exists -> classify -> bind to authority -> promote through evals
misuse objective -> block
```

Examples:

```text
window metadata observation -> Blue Lane candidate after fake eval
screenshot/clipboard -> Red Lane candidate with sanitizer and approval
click/type/keys/launch -> Red Lane special authority
sidecar admin mutation -> Red Lane special authority
fake identity, credential theft, hidden keystrokes -> Black Lane misuse objective
```

## Source-Backed Vendor Patterns

| Pattern | Source | Power harvested | Sentinel-native rewrite |
| --- | --- | --- | --- |
| `permissioned_sidecar_capability_manifest` | JARVIS | Multi-machine host-control routing | `PermissionedSidecarManifest` |
| `desktop_awareness_and_action_tools` | JARVIS | Structural and visual desktop operation | `DesktopActionLifecycle` |
| `action_kernel_and_exec_approval_pattern` | OpenClaw | Preview and approval loop | `DesktopActionPreview` |
| `cost_and_sandbox_policy_for_local_execution` | OpenJarvis | Budgeted local execution discipline | `DesktopCostAndSandboxPolicy` |

## Required Promotion Evals

P6L/P6M must cover:

```text
fake_sidecar_capability_escalation
path_traversal_and_symlink_escape
shell_blocklist_bypass
screen_secret_redaction
clipboard_secret_redaction
stale_token_rejection
wrong_target_desktop_action
```

## Non-Goals In P6K

```text
no vendor runtime bridge
no vendor code copy
no live desktop execution
no host control
no credential access
no authority expansion
```
