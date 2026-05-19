# Low Risk Execution Test Plan

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This test plan locks the required future tests for L2/L3 low-risk execution.
The tests must be implemented before or with any future executor code.

This document does not add tests in this pack.

## L2 Draft / Local Artifact Tests

Future required tests:

- L2 creates artifact only in allowed workspace.
- L2 cannot write outside workspace.
- L2 cannot write through parent traversal.
- L2 cannot write through symlink escape.
- L2 cannot write absolute sensitive paths.
- L2 cannot send, network, or call API.
- L2 cannot use credentials.
- L2 cannot run shell, terminal, or process execution.
- L2 receipt contains path/hash metadata only.
- L2 rollback deletes only generated artifact when allowed.
- L2 rollback preserves tombstone/audit metadata.
- L2 cannot persist raw prompt, provider response, reasoning, key, or secret.

## L3 Reversible Workspace Action Tests

Future required tests:

- L3 requires before hash.
- L3 requires after hash.
- L3 requires rollback posture.
- L3 cannot mutate outside workspace.
- L3 blocks symlink escape.
- L3 blocks parent traversal.
- L3 blocks absolute sensitive path.
- L3 blocks binary mutation in v0 unless a later contract allows it.
- L3 blocks overwrite without before hash.
- L3 blocks delete without tombstone.
- L3 rollback restores previous state.
- L3 blocked if rollback unavailable.
- L3 receipt links before/after hashes and rollback receipt.

## Authority And Gate Tests

Future required tests:

- executor cannot expand authority.
- executor cannot override provider/backend/model.
- executor cannot execute if gate denied.
- executor cannot execute if lane expired.
- executor cannot execute if `execution_enabled=false`.
- executor cannot execute if `mission_id` mismatches.
- executor cannot execute if organ kind mismatches.
- executor cannot create delegated lane.
- executor cannot bypass user review.
- executor cannot bypass FinalGate posture.

## Forbidden Surface Tests

Future required tests:

- executor cannot run shell.
- executor cannot use credentials.
- executor cannot send email or channel message.
- executor cannot submit browser forms.
- executor cannot login.
- executor cannot upload or download.
- executor cannot call external network.
- executor cannot call API.
- executor cannot perform API mutation.
- executor cannot perform desktop host control.
- executor cannot perform payment, spend, or trading.
- executor rejects hidden tool or organ payloads.
- executor rejects restore/rollback execution without rollback contract.

## Receipt And FinalGate Tests

Future required tests:

- execution attempt receipt is created for allowed action.
- rejection receipt is created for blocked action.
- before hash receipt is created for L3 before mutation.
- after hash receipt is created for L3 after mutation.
- rollback receipt is created after rollback.
- receipt contains path/hash metadata only.
- receipt excludes raw prompt, provider response, reasoning, key, secret, and
  hidden action payload.
- FinalGate sees execution receipt.
- FinalGate sees rollback receipt when rollback occurs.
- FinalGate rejects missing receipt contract.

## Regression Boundaries

Future executor implementation must keep existing tests green for:

- `DelegatedActionGateModelV0`;
- `OrganProposalBridge`;
- `BrainCognitionLoop`;
- memory bridge, slots, retrieval, replay, and checkpoints;
- runtime model execution wiring;
- provider catalog and provider base contract tests.
