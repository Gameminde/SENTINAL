# L3 Reversible Workspace Action Contract

Status: docs/spec lock

Date: 2026-05-19

## Purpose

L3 is Sentinel's first future reversible local workspace mutation surface. It
may modify local workspace content only when the action is bounded,
reversible, receipted, and contained inside an approved workspace root.

L3 is still local-only. It does not include shell, process, desktop host
control, browser, network, API, send, spend, or trading behavior.

## Allowed L3 Actions

L3 may later allow:

- reversible local workspace file update;
- reversible local workspace metadata update;
- bounded edit under an approved workspace root;
- tombstoned local cleanup where deletion-like behavior is explicitly allowed;
- rollback from a safe before snapshot or before hash.

Every action must have before/after proof.

## Forbidden L3 Actions

L3 must never perform:

- mutation outside the approved workspace root;
- destructive deletion without tombstone and audit;
- shell, terminal, or process execution;
- desktop host control;
- network call;
- browser submit, login, upload, or download;
- email or channel send;
- API mutation;
- credential use;
- payment, spend, or trading;
- provider/backend/model override;
- hidden tool or organ execution;
- restore or rollback execution without a contract.

## Execution Preconditions

Future L3 execution requires:

- Root Authority present;
- allowed `DelegatedActionLane`;
- `execution_enabled` explicitly transitioned by a future executor contract;
- matching `mission_id`;
- matching organ kind;
- approved workspace root;
- path containment proof;
- before hash;
- after hash;
- rollback posture;
- rollback receipt plan;
- action budget;
- receipt contract;
- FinalGate posture;
- no raw prompt, provider response, reasoning, key, secret, or hidden payload
  persistence.

If any precondition is missing, L3 must block before mutation.

## Workspace Safety

The future L3 executor must enforce:

- resolved-path containment under the allowed root;
- no symlink escape;
- no parent traversal;
- no absolute sensitive path;
- no hidden executable payload;
- no binary mutation in v0 unless a later explicit contract allows it;
- no overwrite without before hash;
- no delete without tombstone;
- no file mutation if rollback is unavailable.

Path checks must use filesystem-aware resolution and containment, equivalent in
spirit to `Path.relative_to` after resolving the intended root and target.

## Before / After Proof

Before mutation:

- capture safe file metadata;
- capture before hash;
- capture allowed root id;
- capture lane id;
- verify rollback posture.

After mutation:

- capture after hash;
- capture changed path metadata;
- verify target stayed under allowed root;
- write execution receipt;
- link receipt to gate result and lane.

## Rollback

Rollback must be tested before L3 mutation is allowed.

Allowed rollback forms:

- restore previous content from safe before snapshot;
- restore previous content verified by before hash;
- revert metadata change when metadata rollback is defined;
- mark tombstoned deletion-like action as reversible only if restoration is
  proven.

If rollback is unavailable, unsafe, untested, or outside scope, the executor
must block before mutation.

## FinalGate Posture

FinalGate later certifies:

- action remained local and reversible;
- before/after hash exists;
- rollback receipt exists or rollback was not needed;
- no forbidden surface occurred;
- authority lane and budget were respected;
- workspace containment held through the whole action.
