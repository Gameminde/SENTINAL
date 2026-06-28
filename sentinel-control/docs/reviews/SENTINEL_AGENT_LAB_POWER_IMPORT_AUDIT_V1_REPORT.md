# SENTINEL_AGENT_LAB_POWER_IMPORT_AUDIT_V1_REPORT

Status: audit-only, power-import review.

Provider calls: 0.
Live external credentials used: 0.
Runtime behavior changes: 0.
Push: not performed.

## Executive Verdict

`agent-lab` is present and useful as a power reference. It is not one runtime;
it is a research workspace containing vendor specimens, forensic audits,
benchmarks, harvested browser power files, and Sentinel integration notes.

The strongest lesson is simple:

```text
model calls should drive a general task loop
tools should execute inside already-granted authority
receipts and replay should happen in the background
human friction should appear only at real boundary violations
```

Sentinel already has better proof machinery than the studied systems:
MissionAuthorityEnvelope, receipts, FinalGate, replay, credential boundaries,
manifest visibility, and product-proven read-only execution. Sentinel's main
power gap is not another registry. The gap is a generic model-led action loop
that can reuse multiple already-approved capability adapters the way agent-lab
specimens reuse tools, skills, browser, shell, workers, and channels.

Recommended next implementation pack:

```text
POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1
```

This is the fastest path to 70 percent power parity because it turns Sentinel's
existing powers into a general continuation engine before adding new high-risk
surfaces. Workspace write/patch, shell sandbox, browser computer control, and
real channel transports should plug into that loop next.

## Agent-Lab Location And Files Inspected

Agent-lab location:

```text
C:\Users\youcefcheriet\sentinal\agent-lab
```

Top-level files and directories inspected:

```text
agent-lab/README.md
agent-lab/AGENT_LAB_PLAN.md
agent-lab/adapters/README.md
agent-lab/audits/AGENT_COMPARISON_MATRIX.md
agent-lab/audits/SUPERPOWER_EXTRACTION_TABLE.md
agent-lab/audits/final/2026-06-06_sentinel_competitive_power_delta_and_roadmap.md
agent-lab/audits/final/openclaw_final_forensic_report.md
agent-lab/audits/final/hermes_final_forensic_report.md
agent-lab/audits/final/openjarvis_final_forensic_report.md
agent-lab/audits/final/jarvis_final_forensic_report.md
agent-lab/benchmarks/browser_tasks/README.md
agent-lab/benchmarks/openclaw_fake_runtime/benchmark_runner.py
agent-lab/module-harvest/browser/openclaw/README.md
agent-lab/module-harvest/browser/openclaw/P3N_BROWSER_FINAL_SUPREMACY_REVIEW.md
agent-lab/module-harvest/browser/openclaw/power-files/src/browser/pw-tools-core.interactions.ts
agent-lab/module-harvest/browser/openclaw/power-files/src/browser/pw-role-snapshot.ts
agent-lab/sentinel_integration_notes/SENTINEL_RUNTIME_BLUEPRINT.md
```

Current Sentinel files inspected for adaptation mapping:

```text
sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py
sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py
sentinel-control/services/sentinel-core/sentinel/operator/connection_live_channel_action_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter.py
sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter_replay.py
sentinel-control/services/sentinel-core/sentinel/operator/worker_fleet.py
sentinel-control/services/sentinel-core/sentinel/operator/harness_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/power_bridge.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/
sentinel-control/services/sentinel-core/sentinel/organs/browser/
sentinel-control/services/sentinel-core/sentinel/memory/
sentinel-control/services/sentinel-core/sentinel/agent/llm/memory_bridge.py
```

No agent-lab vendor runtime was executed or copied.

## Agent-Lab Architecture Map

Agent-lab is organized as a specimen and benchmark lab:

```text
agent-lab/
  vendors/                 third-party agent runtimes as reference specimens
  audits/                  static power audits and synthesis documents
  module-harvest/          selected portable ideas, especially browser power
  benchmarks/              fake/local benchmark harnesses and browser missions
  adapters/                experimental adapter concepts, not production code
  sentinel_integration_notes/
                           notes for adapting vendor ideas to Sentinel
```

The major vendor patterns are:

| Specimen | Power Pattern | How The Agent Invokes It | Persisted State | Human Friction |
| --- | --- | --- | --- | --- |
| OpenClaw | Gateway, sessions, channels, plugins, browser, shell, memory, subagents | Tools exposed through gateway/session prompt and plugin registry | Workspace/session/plugin/channel traces | Low once configured; high power surface |
| Hermes | Long agent loop with persistent memory, skills, hooks, delegation, compression | Model selects tools; tool hook chain can transform/block results | Memory files, skill prompt cache, conversation state | Low; model continues until budget/final |
| OpenJarvis | Agent tool loop, hardware-aware routing, parallel tool execution, loop guards | LLM tool calls become ToolCall objects, executor runs sequential/parallel | Trace groups, routing telemetry, memory | Low; budget/loop guard stops runaway |
| JARVIS | Daemon plus sidecar for desktop/browser/filesystem/shell/clipboard | Orchestrator dispatches named tools through registry and authority engine | Audit logs, workflows, sidecar state | Medium; powerful sidecar with approvals |
| UI-TARS/Desktop agents | GUI/browser/remote computer operation | Multimodal observation to action loop | Screenshots, trajectories | Low during task, high setup risk |
| Webwright | Browser workflows compiled to rerunnable programs/logs | Browser actions become reusable code/workflow | Program logs, run traces | Low after capture |
| Microsoft Agent Framework | Durable workflow, checkpointing, restartable multi-agent execution | Workflow graph and agents run with state checkpoints | Durable checkpoints and run state | Low for long workflows |
| Agent Zero | Full local desktop agent with browser, host connector, projects, plugins, scheduler | Agent loop invokes host/project/plugin tools | Project memory, schedules, logs | Low once host is granted |
| oh-my-pi | Execution harness, persistent kernels, LSP/debugger, hash-anchored edits, parallel worktrees | Model drives command/edit/test subloops | Kernel state, edit hashes, worker outputs | Low for developer tasks |

## Strongest Power Mechanisms

### 1. Generic Agent-To-Tool Loop

Power given:

```text
model chooses action
runtime executes action
observation returns to model
model continues without another user turn
```

Agent-lab evidence:

- Hermes has a conversation loop with iteration budget, tools, memory, skills,
  subagents, compression, and final/budget exits.
- OpenJarvis converts model tool calls into `ToolCall` objects, executes tools
  sequentially or with a thread pool, appends observations, and continues.
- JARVIS dispatches named tools through a registry and sidecar.

Sentinel adaptation:

Build a general `ModelLedTaskLoop` over existing governed capability adapters.
It should begin with read-only research and bounded channel send because both
already have receipts. It should not require a new human approval per step once
mission-level authority is granted.

Suggested Sentinel receiver:

```text
sentinel/operator/model_led_task_loop.py
sentinel/operator/action_kernel.py
sentinel/operator/decision_context.py
```

Current blocker:

Read-only autopilot has a loop, but it is capability-specific. Channel send has
a live bounded runtime, but it is not yet part of a general multi-action loop.

### 2. Safe Observation Context Instead Of Raw Dumps

Power given:

The model can adapt from previous action results without the runtime exposing
raw provider wrappers, secrets, or uncontrolled full file dumps.

Agent-lab evidence:

- Hermes uses memory and compressed context.
- OpenJarvis uses tool observations and context trimming.
- Sentinel already stores evidence, receipt refs, and safe summaries.

Sentinel adaptation:

Create a context compiler that feeds the next decision with:

```text
mission objective
available actions
authority summary
receipt refs
bounded observation summaries
evidence hashes/counts
last action status
budget remaining
```

Suggested Sentinel receiver:

```text
sentinel/operator/decision_context.py
sentinel/operator/read_only_operator_spine.py
sentinel/operator/connection_live_channel_action_runtime.py
```

Current blocker:

Each surface builds context in its own local way. There is no common observation
language for model-led continuation across capabilities.

### 3. Loop Guard And Budget Instead Of Approval Spam

Power given:

The agent can run fast, while runaway loops are stopped by deterministic loop
guards and budgets.

Agent-lab evidence:

OpenJarvis has loop guard concepts: repeated call hashing, ping-pong detection,
polling budgets, max context messages, and compression.

Sentinel adaptation:

Add a runtime loop guard with:

```text
max_model_calls
max_material_actions
max_same_action_hash
max_repeated_target
max_no_progress_turns
deadline_seconds
kill/revocation check
```

Suggested Sentinel receiver:

```text
sentinel/operator/model_led_task_loop.py
sentinel/operator/loop_guard.py
sentinel/operator/daemon_runtime.py
```

Current blocker:

Read-only autopilot has provider/material budgets, but Sentinel lacks a general
cross-capability loop guard.

### 4. Tool Hook Chain

Power given:

Tools stay ergonomic for models while the runtime can normalize arguments,
redact outputs, and record telemetry.

Agent-lab evidence:

Hermes has pre-tool, post-tool, and transform hooks plus argument coercion and
error sanitization.

Sentinel adaptation:

Use hooks as invisible runtime plumbing:

```text
pre_execute: authority/scope/idempotency
normalize: model dialect to canonical action
execute: adapter call
post_execute: evidence/receipt/finalgate event
transform: safe observation context
```

Suggested Sentinel receiver:

```text
sentinel/operator/action_kernel.py
sentinel/operator/model_decision_extractor.py
sentinel/operator/redaction.py
```

Current blocker:

Sentinel has strong validation but too much logic is surface-specific. The hook
shape would reduce repeated schema micro-fixes without lowering boundaries.

### 5. Gateway/Session Surface For Channels And Tools

Power given:

The agent sees one command surface even when execution fans out to browser,
channels, shell, memory, workers, and plugins.

Agent-lab evidence:

OpenClaw organizes power behind gateway/session/channel/plugin primitives.

Sentinel adaptation:

Do not copy the plugin loader. Copy the unified route shape:

```text
mission session
available action cards
typed action result
receipt refs
replay handle
```

Suggested Sentinel receiver:

```text
sentinel/operator/runtime_host.py
sentinel/operator/unified_execution_dispatcher.py
sentinel/operator/connection_live_channel_action_runtime.py
sentinel/operator/runtime_connections.py
```

Current blocker:

`UnifiedExecutionDispatcher` routes mission requests, but model-led action
selection is not yet a generic gateway over multiple adapters.

### 6. Browser Stable-Ref Acting

Power given:

The model can inspect a page, refer to stable element refs, and act through
click/type/select/fill/hover/drag primitives.

Agent-lab evidence:

The OpenClaw browser harvest includes Playwright interaction functions and role
snapshot references. The browser benchmark catalog covers lifecycle,
navigation, forms, files, network diagnostics, repair, visual perception, and
long-horizon operator flows.

Sentinel adaptation:

Sentinel already has broad browser modules and organs. The import target is not
another browser audit. It is product-route connection:

```text
model-led task loop
-> browser observation action
-> stable refs
-> bounded interaction action
-> receipt
-> verification
-> continue
```

Suggested Sentinel receiver:

```text
sentinel/agent/browser/
sentinel/organs/browser/
sentinel/operator/model_led_task_loop.py
```

Current blocker:

Browser power exists in modules, but current canonical product-dispatchable
power is still read-only research plus local/fake bounded channel send.

### 7. Hash-Anchored File And Code Editing

Power given:

The model can mutate files while the runtime verifies that the edit applies to
the intended base content.

Agent-lab evidence:

oh-my-pi emphasizes hash-anchored edits, persistent execution kernels, LSP,
debugger, and parallel worktree subagents. Sentinel's own harness runtime
already contains hash-anchored artifact/edit verification patterns.

Sentinel adaptation:

Build workspace patch power after the generic task loop:

```text
read file hash
model proposes patch with base hash
runtime applies only if base hash matches
tests run as bounded action
receipt persists patch/test result
replay does not reapply
```

Suggested Sentinel receiver:

```text
sentinel/operator/harness_runtime.py
sentinel/agent/organs/reversible_workspace_executor.py
sentinel/operator/model_led_task_loop.py
```

Current blocker:

There is harness proof logic, but not a product route where the model can
autonomously choose and execute a bounded workspace mutation.

### 8. Sidecar And Computer Control

Power given:

The agent can operate the machine, not just text APIs.

Agent-lab evidence:

JARVIS and UI-TARS style systems expose desktop/screen/browser/filesystem/shell
through sidecars.

Sentinel adaptation:

Use a sidecar later, after the generic task loop and after browser/workspace
write have receipts. Sidecar should expose narrow action families, not all host
capabilities by default.

Suggested Sentinel receiver:

```text
sentinel/organs/desktop/
sentinel/agent/organs/browser_operator_agent_l4_l5_live.py
sentinel/operator/model_led_task_loop.py
```

Current blocker:

Desktop/browser power is represented in organs, but not yet connected as a
model-led product route with low friction and receipts.

### 9. Worker Fleet And Parallel Execution

Power given:

The system can split work into sub-tasks and run them concurrently.

Agent-lab evidence:

Hermes delegates subagents; OpenJarvis can parallelize tool calls; Microsoft
Agent Framework and Agent Zero use durable workflows/background work.

Sentinel adaptation:

Sentinel already has `WorkerFleetRuntime`. Power import should let the model
request bounded worker spawn inside one mission, with child authority, receipts,
and merge results.

Suggested Sentinel receiver:

```text
sentinel/operator/worker_fleet.py
sentinel/operator/workflow_runtime.py
sentinel/operator/model_led_task_loop.py
```

Current blocker:

Worker fleet exists but is not a first-class action in the product model-led
loop.

### 10. Persistent Memory And Skill Index

Power given:

The agent stops forgetting how to operate, and can load procedure knowledge
without asking the user again.

Agent-lab evidence:

Hermes and Letta show durable memory value. Hermes skills show a lightweight
skill index/prompt assembly pattern.

Sentinel adaptation:

Use memory as context, not authority:

```text
retrieve safe memories
compile skill/procedure cards
feed them to model
actions still require mission authority
receipts verify execution
```

Suggested Sentinel receiver:

```text
sentinel/memory/
sentinel/agent/llm/memory_bridge.py
sentinel/operator/harness_runtime.py
sentinel/operator/model_led_task_loop.py
```

Current blocker:

Memory exists and Pack 4B created operator memory candidates, but memory is not
yet a friction-reducing procedure layer for product operations.

## Sentinel Vs Agent-Lab Gap Table

| Capability | Agent-Lab Power Pattern | Current Sentinel State | Gap |
| --- | --- | --- | --- |
| Agent autonomy | Long model loops continue until final/budget | Read-only autopilot exists; channel send path exists | No generic cross-capability task loop |
| Tool/action breadth | Browser, shell, file, memory, channels, workers, sidecars | Product-dispatchable: read-only research; local/fake channel send | Need action kernel over adapters |
| Write/code execution | Hash-anchored edits, kernels, debugger, worktrees | Harness and reversible executor concepts exist | Not product-dispatchable model-led write |
| Browser/computer action | Stable refs, Playwright, desktop sidecars | Browser modules/organs exist; browser harvest complete | Not current product route power |
| Shell execution | Host/sandbox shell in several specimens | Sandbox shell organ exists | Not connected as bounded product action |
| Memory | Persistent memory, skill context, profiles | Memory services and candidates exist | Not yet a power multiplier in loop |
| Task loop | Tool call, execute, observe, continue | Read-only loop only | Need generic loop |
| Parallelism | Subagents, worker pools, durable workflows | WorkerFleetRuntime exists | Not model-led product action |
| External connectors | Channels, gateway, plugins | Pack 5 fake/local send path | Need real transport after generic loop |
| User friction | Low after grant, budgets/guards stop loops | Low-friction read-only and channel grant started | Too many powers still unconnected |
| Speed to useful output | Broad tools immediately available | Proof-heavy but now receipt-proven | Need model-led breadth with receipts invisible |

## Top 10 Power Features To Import

1. Generic model-led task loop.
2. Unified typed action interface across adapters.
3. Safe observation/context compiler from receipts and evidence.
4. Loop guard and budget governor replacing per-step approval.
5. Tool hook chain for normalization, execution, evidence, and context.
6. Workspace write/patch with hash-anchored apply and test receipts.
7. Browser stable-ref observe/act/verify continuation.
8. Shell/code execution sandbox with bounded command set and receipts.
9. Real channel transport send after mission-level destination grant.
10. Worker fleet as a model-led action for parallel research/build subtasks.

## Sentinel Module Assignment

| Feature | Primary Receiver | Supporting Modules |
| --- | --- | --- |
| Generic task loop | `sentinel/operator/model_led_task_loop.py` | `runtime_host.py`, `mission_lifecycle_service.py`, `unified_execution_dispatcher.py` |
| Unified action interface | `sentinel/operator/action_kernel.py` | read-only spine, channel runtime, browser organs, harness runtime |
| Observation context | `sentinel/operator/decision_context.py` | `read_only_operator_spine.py`, `channel_adapter.py`, `memory_bridge.py` |
| Loop guard | `sentinel/operator/loop_guard.py` | `daemon_runtime.py`, `worker_fleet.py` |
| Tool hooks | `sentinel/operator/action_hooks.py` | model decision extractor, redaction, safety scanner |
| Workspace patch | `sentinel/operator/harness_runtime.py` | `agent/organs/reversible_workspace_executor.py` |
| Browser action | `sentinel/agent/browser/` and `sentinel/organs/browser/` | model-led task loop |
| Shell sandbox | `sentinel/agent/organs/sandbox_shell_code_organ_v1.py` | model-led task loop, harness runtime |
| Channel send | `sentinel/operator/connection_live_channel_action_runtime.py` | `channel_adapter.py`, `channel_adapter_replay.py` |
| Worker fleet | `sentinel/operator/worker_fleet.py` | `workflow_runtime.py`, model-led task loop |

## Fastest Path To 70 Percent Power Parity

### Step 1: Generic Loop Over Existing Power

Implement:

```text
POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1
```

Minimum behavior:

```text
mission-level grant
-> model decision
-> canonical action envelope
-> adapter execute
-> evidence + receipt
-> safe observation context
-> continue until finish/budget/kill
-> replay no re-execute
```

Initial adapters:

```text
read_only_research
local/fake bounded channel send
```

Why first:

This imports the highest-leverage agent-lab pattern without adding a new
dangerous external surface. It turns already-proven Pack 4A/4B and Pack 5 power
into one product operating loop.

### Step 2: Workspace Write/Patch

Implement:

```text
POWER_PACK_2_MODEL_LED_WORKSPACE_WRITE_AND_PATCH_V1
```

This should use hash-anchored edits, bounded test commands, receipts, and
replay no-reapply. This gives Sentinel visible developer productivity power.

### Step 3: Shell And Code Execution Sandbox

Implement:

```text
POWER_PACK_3_SHELL_AND_CODE_EXECUTION_SANDBOX_V1
```

Start with a local bounded sandbox command set, not ambient host shell.

### Step 4: Browser Computer Control

Implement:

```text
POWER_PACK_4_BROWSER_COMPUTER_CONTROL_V1
```

Use stable refs, observe/act/verify loops, and browser receipts. Sentinel has
many browser modules already; this pack should connect them to the product loop.

### Step 5: Real Channel Transport Send

Implement:

```text
POWER_PACK_5_REAL_CHANNEL_TRANSPORT_SEND_V1
```

Promote Pack 5's local/fake channel transport into one real bounded channel
after the generic loop exists.

## What Not To Copy

Do not copy:

```text
unscanned marketplace plugins
dynamic plugin execution as authority
memory as authority
unknown tools defaulting to safe/read
ambient shell as a general tool
arbitrary browser/CDP eval as normal power
desktop sidecar with all capabilities by default
raw cookie/profile/password access
provider fallback/AUTO hidden behind convenience
per-action approval spam
config mutation by model
learned routing policies auto-applied without explicit promotion
```

Also do not copy old agent-lab promotion language that turns every pack into a
new audit gate. Use the useful runtime ideas, then let Sentinel's receipts and
replay run quietly in the background.

## Recommended Next Implementation Pack

Recommended:

```text
POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1
```

Objective:

```text
Create a generic model-led task loop over already-authorized capability
adapters, starting with read_only_research and local/fake bounded channel send.
```

Definition of done:

```text
user grants once
model chooses multiple actions
runtime executes in-scope actions without per-action approval
each material action gets evidence + receipt
safe observations feed the next decision
loop stops on finish/budget/kill/revocation
replay does not re-call model, re-run tools, or resend
no raw provider/reasoning/credential persistence
```

First fake-provider proof path:

```text
read_only.list_directory
-> channel.send_message through local/fake bounded transport
-> read_only.search_text
-> finish
-> receipts verified
-> replay zero material deltas
```

Why not another manifest/security/approval pack:

Connection Packs 2-5 already established maps, identity boundaries, inbound
read-only evidence, and bounded send. The next bottleneck is product power
breadth, not visibility. More registry work will not make Sentinel feel alive.

## Remaining Risks

1. The generic loop can become another read-only-specific loop if the action
   envelope is not capability-agnostic.
2. Context compilation can become too lossy if it hides useful observation
   summaries from the model.
3. Browser, shell, and workspace-write packs should not start before the loop
   has replay no-reexecute proof.
4. Real channel transports should wait until local/fake send works through the
   generic loop.
5. Existing browser modules may be powerful but disconnected; product route
   wiring must be proven, not inferred from module presence.

## Final Decision

```text
AGENT_LAB_FOUND
POWER_IMPORT_AUDIT_COMPLETE
recommended_next_pack = POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1
provider_calls = 0
live_external_credentials_used = 0
runtime_behavior_changes = 0
push = not_performed
```

