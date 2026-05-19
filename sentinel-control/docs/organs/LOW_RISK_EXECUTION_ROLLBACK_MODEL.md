# Low Risk Execution Rollback Model

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This model defines rollback expectations for future L2 and L3 execution.
Rollback is not optional for L3. If rollback cannot be proven before mutation,
L3 must block.

Rollback receipts are measurements. They are not authority and cannot approve
future execution.

## L2 Rollback

L2 rollback may:

- delete a generated draft or artifact when the lane allows cleanup;
- move a generated artifact to a tombstone area when defined;
- mark artifact cleanup as unavailable and preserve the artifact if deletion is
  not allowed.

L2 rollback must preserve tombstone/audit metadata:

- artifact path metadata;
- artifact hash;
- lane id;
- gate result id;
- cleanup reason;
- timestamp;
- rollback receipt id.

L2 must not delete non-generated files.

## L3 Rollback

L3 rollback may:

- restore previous content from a safe before snapshot;
- restore content verified by before hash;
- revert a bounded metadata change;
- restore a tombstoned local item when deletion-like action was explicitly
  allowed.

L3 rollback must be tested before allowing mutation. The executor must block
before write if:

- before hash is missing;
- before snapshot is missing when needed;
- rollback receipt cannot be produced;
- target path is outside allowed workspace;
- symlink escape is detected;
- binary mutation is requested in v0;
- rollback would require shell/process execution;
- rollback would require credentials or network.

## Rollback Safety Rules

Future rollback logic must enforce:

- path containment;
- no symlink escape;
- no parent traversal;
- no absolute sensitive path;
- no hidden executable payload;
- no restore outside the approved root;
- no destructive delete without tombstone;
- no rollback execution without explicit rollback contract.

## Rollback Receipt

Rollback receipts must include:

- rollback receipt id;
- original execution receipt id;
- lane id;
- gate result id;
- before hash;
- restored hash or final state hash;
- affected path metadata;
- rollback status;
- rollback failure reason when blocked;
- safe summary.

Rollback receipts must not contain raw prompt, provider response, reasoning,
keys, secrets, hidden payloads, raw executable params, or raw organ payloads.

## Rollback And FinalGate

Future FinalGate checks must be able to verify:

- rollback was possible before L3 mutation;
- rollback was executed when required;
- rollback stayed inside the same lane and workspace root;
- rollback did not expand authority or execute forbidden actions.
