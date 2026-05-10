# P6S Desktop AgentLab Power Binding

Date: 2026-05-10

## Purpose

P6S must not implement Desktop Workspace L6 from internal Sentinel classes
alone. Desktop L6 is a promotion of existing Sentinel capability, but it must
be bound to the strongest desktop-relevant mechanisms harvested from AgentLab.

The goal is not to imitate JARVIS, OpenClaw, OpenJarvis, or Hermes. The goal is:

```text
extract their strongest mechanisms
rewrite them Sentinel-native
combine them with Brain L4 + P6R context discipline
surpass the source agents through receipts, replay, rollback, authority,
FinalGate, and compact decision frames
```

## Sources Used

```text
agent-lab/audits/jarvis_desktop_static_audit.md
agent-lab/audits/jarvis_desktop_capability_map.md
agent-lab/audits/jarvis_sidecar_map.md
agent-lab/audits/jarvis_permission_map.md
agent-lab/audits/openjarvis_cost_router_map.md
agent-lab/audits/openjarvis_algorithm_map.md
agent-lab/audits/openclaw_capability_map.md
agent-lab/audits/hermes_algorithm_map.md
agent-lab/audits/hermes_prompt_map.md
agent-lab/audits/final/g9_cross_agent_synthesis.md
agent-lab/audits/SUPERPOWER_EXTRACTION_TABLE.md
sentinel-control/docs/organs/P6L_DESKTOP_SIDECAR_ORGAN_SCORECARD.md
sentinel-control/docs/organs/P6M_REALITY_ACTIVATION_SCORECARD.md
sentinel-control/docs/organs/P6P_RUNTIME_PROMOTION_PLAN.md
sentinel-control/docs/research/P6R_DECISION_FRAME_SPEC.md
```

No vendor runtime was executed. No vendor code is copied or bridged.

## Binding Formula

```text
JARVIS sidecar / desktop awareness / approval / audit
+ OpenJarvis budget, timeout, local execution discipline
+ OpenClaw action kernel, manifest, preview, approval surface
+ Hermes context quarantine, compression, prompt discipline
+ Sentinel P6R decision frames
+ Sentinel authority, receipts, rollback, FinalGate
= Desktop Workspace L6
```

## JARVIS Binding

### Exact Mechanism

JARVIS exposes a sidecar with capability families:

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

It also provides:

```text
sidecar enrollment
ES256/JWT identity
JWKS validation
RPC registry
window metadata and UI tree observation
filesystem read/write/list
screenshot and clipboard surfaces
desktop click/type/key/launch/focus
approval lifecycle
audit trail
revocation
```

### Why Powerful

JARVIS turns an agent into a machine operator. The source power is the topology:
a daemon can see machine state, register host capabilities, route actions
through sidecars, and record approvals/audits.

### Where It Beats Sentinel Today

```text
real sidecar lifecycle exists in vendor source
real RPC registry exists in vendor source
real desktop/window/screenshot/clipboard primitives exist in vendor source
approval and audit are connected to a live daemon concept
```

### Where Sentinel Is Stronger

```text
P6R prevents raw workspace/context dumps into the selected LLM
P6Q exposes token pressure and model cost before decisions
P5/P6 authority model separates memory, evidence, and permission
receipts are deterministic and replay-oriented
promotion ladder forces proof before wider power
```

### What P6S Must Harvest

```text
sidecar identity model
capability manifest discipline
RPC method taxonomy
workspace filesystem capability
approval lifecycle states
audit trail shape
revocation/stale sidecar rejection
desktop awareness as state, not just screenshot pixels
```

### What P6S Must Not Copy

```text
raw host bridge
full sidecar control by default
terminal/shell execution
browser app submit/send
screenshot/clipboard live ingestion in P6S
config mutation over ordinary RPC
path blocklist security
all-capability sidecar enrollment
```

### Sentinel-Native Rewrite

```text
DesktopWorkspaceAuthority
WorkspaceOperationAdapter
WorkspaceReceiptAdapter
WorkspaceContextCard
WorkspaceDiffSummary
WorkspaceRollbackRef
PathContainmentProofRef
DesktopWorkspaceL6Receipt
DesktopWorkspaceL6FinalGate
DesktopWorkspaceKillSwitch
```

### Context / Token Pressure

JARVIS-like desktop power can generate:

```text
directory trees
file contents
diffs
screenshots
clipboard text
window/UI trees
action logs
approval records
```

P6S must not pass those raw objects to the LLM. It must produce compact
workspace cards and refs.

### P6R Decision-Frame Implication

```text
LLM sees:
  objective
  authority card
  workspace context card
  top changed paths
  compact diff summaries
  rollback refs
  receipt refs
  next allowed operation options

LLM does not see by default:
  full tree
  full file contents
  raw receipt bodies
  raw diffs
  clipboard/screenshot content
  shell/process surface
```

## OpenJarvis Binding

### Exact Mechanism

OpenJarvis contributes:

```text
hardware-aware engine recommendation
available memory estimate
model tiering
cost/pricing metadata
reward weights for accuracy/latency/cost/efficiency
timeout and loop discipline
skill import quarantine ideas
failure telemetry and fallback direction
```

### Why Powerful

OpenJarvis treats execution cost, latency, hardware fit, and model routing as
control signals instead of afterthoughts.

### Where It Beats Sentinel Today

```text
more mature local/cloud routing concepts
explicit hardware-fit heuristics
trace-driven evolution concepts
```

### Where Sentinel Is Stronger

```text
user-selected model remains authoritative
model routing cannot silently override user choice
learning produces proposals, not self-mutating config
authority and evidence are first-class constraints
```

### What P6S Must Harvest

```text
workspace operation budget
timeout policy
file-size and output-size caps
retry budget
failure receipt taxonomy
cost trace per operation
fallback from write to preview when budget or authority is insufficient
```

### What P6S Must Not Copy

```text
auto model switching
silent learned configuration mutation
unbounded local execution
host command execution
runtime skill sync
```

### Sentinel-Native Rewrite

```text
WorkspaceOperationBudget
WorkspaceTimeoutPolicy
WorkspaceMutationScope
WorkspaceCostTrace
WorkspaceFailureReceipt
WorkspaceBudgetExceededDecision
```

### Context / Token Pressure

Desktop file reads and diffs can inflate prompts. OpenJarvis cost discipline
maps to P6Q/P6R by making file read size, diff size, retry count, and output
tokens measurable before LLM exposure.

### P6R Decision-Frame Implication

```text
DesktopDecisionFrameSlice must include budget_used, budget_remaining,
operation_count, changed_file_count, and largest_context_pressure_source.
```

## OpenClaw Binding

### Exact Mechanism

OpenClaw contributes:

```text
plugin/tool manifest pattern
gateway/control-plane pattern
action kernel
exec approval machinery
tool policy
browser/channel/shell capability separation
scanner reports
UI approval overlay concept
```

### Why Powerful

OpenClaw demonstrates how many surfaces can be orchestrated through one action
kernel without making each organ invent its own lifecycle.

### Where It Beats Sentinel Today

```text
broader runtime surface
more mature plugin/tool manifest topology
approval UI concept exists as a product surface
```

### Where Sentinel Is Stronger

```text
organ promotion ladder prevents broad power from arriving all at once
P6R minimizes tool surface in the LLM decision frame
authority cannot come from plugins, memory, workspace, or expected profit
receipts and FinalGate are phase requirements
```

### What P6S Must Harvest

```text
WorkspaceActionKernel
action preview lifecycle
tool/operation manifest pattern
capability scanner
approval request shape
separation between browser/channel/shell/desktop powers
```

### What P6S Must Not Copy

```text
broad shell access
unscanned plugin loading
marketplace power without promotion
always-allow approval semantics
vendor runtime bridge
```

### Sentinel-Native Rewrite

```text
WorkspaceActionKernel
WorkspaceActionPreview
WorkspaceCapabilityScanner
WorkspaceToolSurfaceRoute
WorkspaceApprovalRequest
WorkspaceActionReceipt
```

### Context / Token Pressure

OpenClaw-style broad tool surfaces are dangerous for context economy because
LLMs get too many schemas. P6S must expose only the workspace operations
needed for the next step.

### P6R Decision-Frame Implication

```text
ToolSurfaceRouter exposes:
  list_dir
  read_file
  write_file
  create_folder
  rollback_write

It does not expose:
  shell
  process execution
  browser mutation
  screenshot/clipboard
  sidecar admin
```

## Hermes Binding

### Exact Mechanism

Hermes contributes:

```text
context scanner
prompt block trust labeling
memory threat checks
skill prompt cache
tool hook pipeline
trajectory compression
provider context discipline
```

### Why Powerful

Hermes shows that long-horizon agents need durable context, compression, and
procedural memory. It also shows why context must be treated as a threat
surface.

### Where It Beats Sentinel Today

```text
more mature memory/provider context patterns
more mature skill prompt surface
tool hook lifecycle exists as runtime pattern
```

### Where Sentinel Is Stronger

```text
memory is non-authoritative
P6R keeps exact receipts outside the prompt
critical evidence refs are checked explicitly
secret-like keys and values are sanitized before frame persistence
```

### What P6S Must Harvest

```text
workspace context quarantine
trajectory compression into operation cards
tool-output pruning
trust labels for file content
prompt trace record
raw-vs-summary separation
```

### What P6S Must Not Copy

```text
memory as authority
skill prompt injection
raw trajectory dumps
project files as policy
tool-result transforms that hide raw output
```

### Sentinel-Native Rewrite

```text
WorkspaceContextCard
WorkspaceDiffSummary
WorkspaceEvidenceCard
DesktopDecisionFrameSlice
WorkspacePromptTraceRecord
WorkspaceTrustLabel
```

### Context / Token Pressure

Hermes confirms the reason P6R must precede P6S: desktop operations generate
too much raw context, and long missions will collapse if every file/tree/diff
goes into the model.

### P6R Decision-Frame Implication

```text
P6S must create context cards first and model prompts second.
If a Desktop operation cannot produce a compact card and receipt refs, it is
not ready for L6.
```

## Surpass-Not-Imitate Requirements

P6S must exceed the source agents in these concrete ways:

| Source weakness | Sentinel improvement |
| --- | --- |
| JARVIS sidecar has broad host-level capability topology | Sentinel scopes Desktop L6 to workspace operations only |
| JARVIS approval/audit lacks full P6R decision-frame economy | Sentinel links every action to compact context cards and receipt refs |
| JARVIS path protection relies on weaker blocked-path patterns in audited areas | Sentinel requires allow-root containment and path proof refs |
| OpenClaw broad tool surface can overload prompt/tool context | Sentinel exposes only selected workspace tools through ToolSurfaceRouter |
| OpenJarvis routing can become silent model/config mutation | Sentinel preserves user-selected model and uses improvement proposals |
| Hermes memory/context can become behavior-shaping prompt policy | Sentinel marks memory/file context as data, not authority |
| Vendor logs are useful but not necessarily replay-complete | Sentinel requires deterministic receipts, rollback refs, and FinalGate |

## P6S-A Output Contract

Before P6S-B implementation, the Desktop promotion must define:

```text
DesktopWorkspaceAuthority
WorkspaceOperationAdapter
WorkspaceReceiptAdapter
WorkspaceContextCard
WorkspaceDiffSummary
WorkspaceRollbackRef
PathContainmentProofRef
DesktopDecisionFrameSlice
DesktopWorkspaceL6Receipt
DesktopWorkspaceL6FinalGate
DesktopWorkspaceKillSwitch
WorkspaceOperationBudget
WorkspaceTimeoutPolicy
WorkspaceActionKernel
WorkspaceCapabilityScanner
```

## P6S-B Implementation Boundary

Allowed in P6S-B:

```text
real workspace list/read/write/create under authorized root
path containment proofs
write receipts
rollback refs for writes/creates
compact workspace cards
P6R decision-frame slice
FinalGate adapter for workspace operations
kill switch for workspace mutation
budget/timeout policy
```

Not allowed in P6S-B:

```text
full host control
raw sidecar bridge
vendor runtime bridge
vendor code copy
shell/process execution
live screenshot
live clipboard
desktop click/type/key/launch/focus
sidecar admin mutation
browser mutation
credential secret access
authority expansion
```

## Final Verdict

```text
P6S should proceed only as:
P6S-A Desktop AgentLab Power Binding
-> P6S-B Desktop Workspace L6 Implementation
```

Sentinel can surpass the audited agents if Desktop L6 is not just a file
operator. It must become a controlled workspace actuator with compact cognition,
deterministic receipts, rollback, policy versioning, and replayable proof.
