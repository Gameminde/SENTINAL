# Durable Mission Workflow And Automatic Replan V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`
> to implement this plan task-by-task. Use TDD for every runtime behavior.

**Goal:** Extend the existing MissionKernel, PowerRuntime, and AgentRuntime
spine into restartable, checkpointed workflows with automatic replan inside
the original MissionAuthorityEnvelope.

**Architecture:** MissionKernel remains the canonical mission lifecycle owner.
The durable workflow layer stores versioned plans, branches, checkpoints, and
resume cursors inside the existing mission run directory. It executes only
through existing operator bridges into PowerRuntime or AgentRuntime.

**Doctrine:** Replan is autonomy inside authority. Replan is not new authority.

---

## Reuse Map

Reuse without replacement:

- `sentinel/operator/kernel.py` for mission lifecycle;
- `sentinel/operator/store.py` for the mission run root and canonical event
  stream;
- `sentinel/operator/replay.py` for evidence-only mission replay;
- `sentinel/operator/power_bridge.py` and `agent_bridge.py` for runtime calls;
- `sentinel/power/runtime.py` and `sentinel/agent/runtime.py` as the only
  execution engines;
- `MissionAuthorityEnvelope`, cancellation, receipts, FinalGate, EventBus,
  replan-ready packets, and persistent semantic memory refs.

Harvested mechanisms, rewritten Sentinel-native:

- Microsoft Agent Framework: replayable durable orchestration state;
- JARVIS: strict resume state validation and versioned workflow runs;
- Hermes: durable task state, idempotent continuation, visible lifecycle;
- gptme / Agent Zero: background continuation ergonomics;
- oh-my-pi: hash-anchored state and minimized typed results.

No vendor runtime, code, dependency, account, or service is integrated.

## Task 1 - Durable Workflow Contracts

Create:

- `sentinel/operator/workflow_models.py`
- `tests/test_durable_mission_workflow_and_automatic_replan_v1.py`

Test first:

- durable records, branches, checkpoints, step states, and resume cursors are
  typed, authority-neutral, and hash-bound;
- completed durable step state requires a branch/plan/step-bound local proof
  record with receipt and FinalGate refs;
- workflow models reject raw secrets, provider overrides, authority expansion,
  and direct organ execution payloads;
- a replan candidate cannot claim memory, receipts, or FinalGate as authority.

Implement:

- `DurableWorkflowRecord`
- `WorkflowAuthoritySnapshot`
- `WorkflowStepState`
- `WorkflowBranch`
- `WorkflowCheckpoint`
- `ResumeCursor`
- `ReplanCandidate`
- `ReplanDecision`
- `WorkflowReplayView`

## Task 2 - Atomic Workflow Store In Existing Mission Run Root

Create:

- `sentinel/operator/workflow_store.py`

Modify:

- `sentinel/operator/store.py`

Test first:

- workflow records and plans live under the existing mission directory;
- writes are atomic and guarded against stale record versions;
- plan/checkpoint hashes detect tamper;
- branch transition writes its checkpoint before publishing the new active
  branch, so a partial write fails closed;
- restart reloads the latest checkpoint and resume cursor;
- no parallel workflow event stream is created;
- no raw secrets, credentials, prompts, provider responses, or reasoning are
  persisted.

## Task 3 - Replan Execution Guard

Create:

- `sentinel/operator/replan_guard.py`

Test first:

- automatic execution passes only for the same envelope, objective, actions,
  risk lane or lower, budgets, credential scope, provider/model contract,
  organs/executor contract, and target scope;
- revocation, expiry, authority drift, budget expansion, risk increase,
  provider/model change, credential expansion, special-authority boundary,
  irreversible action, and target expansion escalate;
- memory, receipts, FinalGate, and old checkpoints never approve execution;
- product default is automatic inside authority;
- optional `require_confirmation_for_every_replan` escalates.

## Task 4 - Checkpointed PowerRuntime Continuation

Create:

- `sentinel/operator/workflow_runtime.py`

Modify:

- `sentinel/operator/power_bridge.py`

Test first:

- a workflow executes PowerRuntime steps through the existing bridge only;
- PowerRuntime bridge requires the current authority envelope and a bound
  executor contract;
- action attempts and typed estimated cost are reserved before execution and
  reconciled at the durable checkpoint;
- every successful step produces a durable checkpoint;
- resume skips only proof-backed completed steps;
- pause, kill, revocation, expiry, and malformed/tampered checkpoint fail
  closed before the next step;
- crash after a checkpoint can resume without duplicate execution;
- missing executor remains fail closed.

## Task 5 - AgentRuntime Replan Boundary

Modify:

- `sentinel/operator/agent_bridge.py`
- `sentinel/operator/workflow_runtime.py`

Test first:

- AgentRuntime remains reachable only through its public bridge;
- the same MissionAuthorityEnvelope is revalidated before continuation;
- provider/model overrides and direct execution instructions are rejected;
- AgentRuntime receipt, FinalGate, memory, and replan refs are recorded as
  evidence only;
- opaque AgentRuntime automatic replan escalates until a typed action plan can
  prove exact action, organ, target, risk, and budget scope;
- no direct Brain private call or organ dispatch is introduced.

## Task 6 - Automatic Replan Branching And Escalation

Test first:

- an approved candidate creates a versioned branch and executes automatically;
- a failed guard creates a user checkpoint/escalation and does not execute;
- retry, equivalent branch, authorized reorder, timeout continuation, and
  same-scope read fallback can auto-execute;
- payment, spend, trading, account, KYC, CAPTCHA, security, sensitive desktop,
  new recipient, new endpoint, API mutation expansion, and higher-risk lane
  escalate;
- automatic replan count is bounded.

## Task 7 - Workflow Replay And Product Gauntlet

Create:

- `sentinel/operator/workflow_replay.py`
- `tests/test_durable_mission_workflow_replan_gauntlet_v1.py`

Test first:

- replay reconstructs branches, checkpoints, decisions, receipts, FinalGate,
  and memory refs without re-execution;
- workflow and mission timeline tamper are visible;
- full crash/resume/replan/finish flow preserves proof;
- all execution remains behind MissionKernel and runtime bridges.

## Task 8 - Regressions And Self-Audit

Run focused regressions for:

- MissionKernel/store/replay;
- PowerRuntime and operator bridge;
- AgentRuntime bridge and replan packet;
- persistent semantic memory;
- mission authority, cancellation, Gate, receipts, and FinalGate.

Audit:

- authority expansion and drift;
- direct organ/runtime bypass;
- memory/receipt/FinalGate-as-permission;
- resume duplication and stale checkpoint races;
- provider/model/credential/target expansion;
- raw secret and provider payload persistence;
- docs overclaim and parallel workflow universes.

Fix all P0/P1 and serious P2 findings before lock.

## Task 9 - Truth Docs, Lock Report, Commit, Push

Create:

- `sentinel-control/docs/reviews/DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1_LOCK_REPORT.md`

Update after approval:

- `README.md`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md`
- relevant subordinate roadmap.

The lock report must prove:

- automatic replan cannot expand authority;
- automatic replan cannot bypass MissionKernel, PowerRuntime, or AgentRuntime;
- automatic replan cannot call organs directly;
- memory, receipts, FinalGate, and checkpoints cannot become permission;
- existing Sentinel components were reused;
- AgentLab mechanisms were harvested as source-only specimens;
- no vendor code/runtime/dependency was copied or integrated;
- no parallel workflow system was created.

Expected final truth:

```text
current_phase = DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1_LOCKED
previous_phase = PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED
next_phase = MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

Stage only intended files, commit, push `origin/main`, verify local HEAD equals
remote HEAD, and stop without starting the next phase.
