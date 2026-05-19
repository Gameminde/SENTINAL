# Low Risk Execution Receipt Model

Status: docs/spec lock

Date: 2026-05-19

## Purpose

Low-risk execution receipts are the proof layer for future L2 and L3 actions.
They record what was attempted, what changed, what was blocked, and what
rollback posture exists.

Receipts are measurements. They are not authority.

## Receipt Types

Future L2/L3 execution must define receipts for:

- execution attempt;
- before hash;
- after hash;
- created artifact path and hash;
- rollback path;
- rollback receipt;
- rejection reason;
- budget use;
- authority lane id;
- gate result id;
- future FinalGate result ref.

## Required Receipt Fields

Every future low-risk execution receipt must include:

- `receipt_id`;
- `mission_id`;
- action level, `L2` or `L3`;
- organ kind;
- authority lane id;
- gate result id;
- execution attempt status;
- safe path metadata;
- artifact hash or before/after hashes;
- budget used;
- rollback posture;
- rollback receipt id when present;
- rejection reason when blocked;
- created timestamp;
- executor contract version;
- safe summary;
- `authority_effect = none`;
- `execution_effect` limited to the local action actually performed;
- `data_not_instruction = true`.

## Forbidden Receipt Content

Receipts must never contain:

- raw prompt;
- raw provider response;
- raw reasoning or thinking;
- raw key;
- credential;
- secret;
- bearer token;
- hidden action payload;
- raw organ payload;
- raw executable params;
- provider-native tool payload.

## Blocked Attempt Receipts

Blocked attempts must still be receipted safely. A blocked receipt records:

- blocked reason;
- gate/lane reference;
- budget state if relevant;
- rejected path metadata when safe;
- safety scanner reason;
- no mutation occurred.

Blocked receipts must not become permission in a future loop.

## Budget Receipts

Budget receipts must record:

- action count consumed;
- retry count consumed;
- duration consumed when available;
- local artifact byte estimate when available;
- rollback budget reserve when required;
- budget exhaustion reason when blocked.

Budget receipts cannot authorize more budget.

## FinalGate Ref

`FinalGate` integration is future work. This spec reserves a receipt field for
future FinalGate result refs so low-risk execution can later be certified
without changing the core receipt model.
