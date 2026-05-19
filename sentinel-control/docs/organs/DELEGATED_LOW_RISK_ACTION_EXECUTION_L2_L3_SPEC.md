# Delegated Low Risk Action Execution L2 L3 Spec

Status: docs/spec lock

Date: 2026-05-19

Pack: `DELEGATED_LOW_RISK_ACTION_EXECUTION_L2_L3_SPEC`

## Purpose

This spec locks the first real delegated low-risk execution surfaces for
Sentinel before implementation:

- L2 draft and local artifact creation;
- L3 reversible local workspace actions.

This is a spec-first pack. It defines the future execution contract only. It
does not implement execution code, executor wiring, AgentRuntime default
behavior changes, external actions, provider routing, or organ execution.

## Current Truth

- `BrainCognitionLoop` is implemented.
- `OrganProposalBridge` is implemented.
- `DelegatedActionGateModelV0` is implemented.
- `DelegatedActionLane` remains metadata-only with `execution_enabled=false`.
- No organ execution exists yet.
- No executor wiring exists yet.
- No AgentRuntime default behavior change exists yet.

## Core Doctrine

```text
The LLM may operate the body only inside delegated authority.
Root Authority comes from user mission, MissionAuthorityEnvelope, explicit approvals, policy, or special authority contracts.
The LLM cannot create or expand Root Authority.
Gate creates lane metadata.
Execution comes only after explicit L2/L3 execution contract.
Draft/local artifact is not external mutation.
Reversible local action must have before/after proof and rollback posture.
```

## Scope

### L2 Draft / Local Artifact

L2 may later allow:

- create a local draft;
- create a local artifact;
- write a generated report or artifact under an allowed generated workspace;
- produce path/hash receipts;
- rollback by deleting the generated artifact when allowed and preserving
  tombstone/audit metadata.

L2 must not allow:

- external mutation;
- send;
- network;
- credential use;
- browser submit;
- API mutation;
- shell or process execution.

### L3 Reversible Local Workspace Action

L3 may later allow:

- a reversible local workspace action;
- mutation only under an approved workspace root;
- before hash capture;
- after hash capture;
- rollback receipt capture;
- tombstone/audit metadata for deletion-like operations.

L3 must not allow:

- mutation outside the allowed path;
- destructive deletion without tombstone and audit;
- shell execution unless a later explicit shell contract exists;
- binary mutation in v0 unless a later explicit binary contract exists;
- external network or credential use.

## Forbidden Surfaces

L2/L3 low-risk execution v0 explicitly forbids:

- email or channel send;
- browser submit;
- login;
- upload or download;
- API mutation;
- external network calls;
- shell, terminal, or process execution;
- desktop host control;
- credential use;
- payment, spend, or trading;
- production mutation;
- restore or rollback execution without a rollback contract;
- hidden tool or organ payloads;
- provider-native tool execution;
- provider/backend/model override.

## Execution Preconditions

Before any L2/L3 executor may exist in a future pack, every execution attempt
must prove:

- Root Authority is present.
- A `DelegatedActionLane` was allowed by the gate.
- `execution_enabled` is explicitly transitioned only by the future executor
  contract, never by model output or lane metadata alone.
- `mission_id` matches.
- organ kind matches.
- workspace root is allowlisted.
- action budget is available.
- rollback posture exists.
- receipt contract exists.
- FinalGate posture is defined.
- no raw prompt, provider response, reasoning, key, secret, or hidden action
  payload is persisted.

## Safety Model

The future L2/L3 executor must enforce:

- path containment;
- no symlink escape;
- no absolute sensitive path;
- no parent traversal;
- no hidden executable payload;
- no binary mutation in v0 unless explicitly allowed later;
- no overwrite without before hash;
- no delete without tombstone;
- no mutation outside the allowed workspace root;
- no shell/process escalation.

The executor must treat model, memory, proposal, and replay data as untrusted
data. None of them can grant authority or widen an existing lane.

## Receipt Model

The low-risk execution receipt model is locked in:

- `LOW_RISK_EXECUTION_RECEIPT_MODEL.md`

Every future execution attempt must produce a safe receipt, including blocked
or rejected attempts.

## Rollback Model

The low-risk rollback model is locked in:

- `LOW_RISK_EXECUTION_ROLLBACK_MODEL.md`

Rollback must be possible and tested before L3 mutation is allowed. If rollback
is unavailable, L3 mutation must be blocked before any write.

## Contract Documents

This pack creates the following contract documents:

- `L2_DRAFT_LOCAL_ARTIFACT_CONTRACT.md`
- `L3_REVERSIBLE_WORKSPACE_ACTION_CONTRACT.md`
- `LOW_RISK_EXECUTION_RECEIPT_MODEL.md`
- `LOW_RISK_EXECUTION_ROLLBACK_MODEL.md`
- `LOW_RISK_EXECUTION_TEST_PLAN.md`

## Implementation Sequence After This Spec

1. `LOW_RISK_LOCAL_ARTIFACT_EXECUTOR_L2`
2. `REVERSIBLE_WORKSPACE_ACTION_EXECUTOR_L3`
3. `LOW_RISK_EXECUTION_FINALGATE_RECEIPTS`
4. `ORGAN_EXECUTION_AGENTRUNTIME_OPT_IN`
5. `BROWSER_READONLY_OR_PREPARATION_SPEC` later
6. `CHANNEL_DRAFT_SPEC` later
7. `API_READONLY_SPEC` later

## Non-Goals

This pack does not start:

- runtime execution code;
- executor wiring;
- AgentRuntime default behavior changes;
- browser, API, channel, desktop, shell, payment, spend, or trading execution;
- L4, L5, L6, or L7 execution;
- provider expansion;
- fallback routing;
- AUTO routing;
- `.env` access or credential use.
