# P6S-B Desktop Workspace L6 Scorecard

Date: 2026-05-10

## Phase

```text
phase = P6S_B_DESKTOP_WORKSPACE_L6_IMPLEMENTATION
previous_phase = P6S_A_FULL_LOCKED
next_phase = P6T_BROWSER_CONTROLLED_NAVIGATION_L6
```

## Goal

Promote the existing desktop workspace capability to L6 real scoped workspace
execution without creating a new organ family or adding broad host control.

P6S-B implements Desktop Workspace L6 as:

```text
P6S-A AgentLab power binding
+ P6R decision-frame discipline
+ scoped workspace authority
+ path containment proofs
+ rollback refs
+ deterministic receipts
+ kill switch
+ FinalGate
```

## Implemented Code

```text
sentinel-control/services/sentinel-core/sentinel/organs/desktop/workspace_l6.py
sentinel-control/services/sentinel-core/sentinel/organs/desktop/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_desktop_workspace_l6.py
```

## Models And Components

```text
DesktopWorkspaceAuthority
WorkspaceOperationAdapter
WorkspaceOperationBudget
WorkspaceTimeoutPolicy
WorkspaceMutationScope
PathContainmentProofRef
WorkspaceRollbackRef
DesktopWorkspaceKillSwitch
WorkspaceCostTrace
DesktopWorkspaceL6Receipt
DesktopWorkspaceL6Result
WorkspaceFailureReceipt
WorkspaceDiffSummary
WorkspaceContextCard
DesktopDecisionFrameSlice
WorkspaceActionKernel
WorkspaceCapabilityScanner
DesktopWorkspaceL6FinalGate
WorkspaceReceiptAdapter
```

## Capability Surface

| Surface | P6S-B status | Boundary |
| --- | --- | --- |
| `list_dir` | real scoped workspace action | inside declared workspace root |
| `read_file` | real scoped workspace action | byte budget, no raw content in receipt summary |
| `write_file` | real scoped workspace mutation | rollback ref, path proof, kill switch |
| `create_folder` | real scoped workspace mutation | rollback ref, path proof, kill switch |
| `rollback_workspace_change` | decision-frame tool surface only | no automatic rollback executor yet |
| shell/process | blocked | not Desktop Workspace L6 |
| screenshot/clipboard | blocked live surface | future sidecar promotion only |
| click/type/key/launch/focus | blocked live host control | future sidecar promotion only |

## AgentLab Binding

P6S-B requires the Desktop Workspace L6 authority and action kernel to carry the
source-binding refs locked by P6S-A:

```text
jarvis_sidecar_rpc_registry
openjarvis_budget_timeout_discipline
openclaw_action_kernel_preview
hermes_context_compression
sentinel_p6r_decision_frame
```

These refs do not grant authority. They prove that the L6 implementation is a
Sentinel-native rewrite of audited source mechanisms rather than a generic file
helper.

## Context Economy

Workspace reads may return raw content to the caller, but receipts and decision
frames keep raw workspace material out of the prompt-facing context.

P6S-B produces:

```text
WorkspaceContextCard
DesktopDecisionFrameSlice
receipt refs
rollback refs
path containment proof refs
content hashes
compact diff summaries
```

It does not dump:

```text
raw file contents
raw workspace tree
all receipts
shell surfaces
host-control surfaces
```

## Verification

```text
P6S-B targeted tests = 9 passed
P6L desktop sidecar neighbor tests = 14 passed
P6M reality activation neighbor tests = 8 passed
```

Command:

```bash
python -m pytest tests/test_p6_desktop_workspace_l6.py -v --tb=short
python -m pytest tests/test_p6_desktop_sidecar_organ.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

## Boundaries

```text
new organ family = no
vendor runtime bridge = no
vendor code copy = no
full host control = no
shell/process execution = no
live screenshot/clipboard = no
desktop click/type/key/launch/focus = no
sidecar admin mutation = no
browser power expansion = no
payment/spend runtime = no
trading runtime = no
credential secret access = no
authority expansion = no
```
