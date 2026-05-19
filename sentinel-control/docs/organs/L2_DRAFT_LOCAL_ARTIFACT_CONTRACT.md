# L2 Draft Local Artifact Contract

Status: docs/spec lock

Date: 2026-05-19

## Purpose

L2 is Sentinel's first future low-risk execution surface. It covers creating
drafts and generated local artifacts inside an approved generated workspace.

L2 is local-only. It is not external mutation.

## Allowed L2 Actions

L2 may later allow:

- create a local draft file;
- create a generated local artifact;
- write a generated report under an approved generated workspace;
- create a non-executable metadata artifact;
- create receipt-only summaries containing artifact path and hash.

L2 output must stay inside a path lane granted by Root Authority and the
delegated gate.

## Forbidden L2 Actions

L2 must never perform:

- email or channel send;
- browser submit;
- login;
- upload or download;
- API calls or network calls;
- credential use;
- shell, terminal, or process execution;
- desktop host control;
- payment, spend, or trading;
- production mutation;
- provider/backend/model override;
- hidden tool or organ execution.

## Authority Requirements

Future L2 execution requires:

- Root Authority present;
- matching `mission_id`;
- allowed `DelegatedActionLane`;
- matching organ kind;
- workspace root allowlist;
- action budget;
- receipt contract;
- rollback posture;
- no raw prompt, provider response, reasoning, key, secret, or hidden payload
  persistence.

The LLM cannot create, expand, or rewrite Root Authority. It may only operate
inside a future lane after an executor contract explicitly enables L2.

## Workspace Rules

L2 writes must satisfy:

- path is under an approved generated workspace root;
- path containment is verified with resolved paths, not string prefix checks;
- parent traversal is rejected;
- symlink escape is rejected;
- absolute sensitive paths are rejected;
- executable payloads are rejected;
- binary artifacts are rejected in v0 unless explicitly allowed later;
- overwrite is rejected unless the contract explicitly allows replacing a
  generated artifact with before-hash proof.

## Receipt Requirements

Every L2 attempt must record:

- execution attempt id;
- `mission_id`;
- authority lane id;
- gate result id;
- artifact path metadata;
- artifact hash;
- action budget used;
- rejection reason when blocked;
- rollback path or tombstone posture;
- future FinalGate result ref when available.

Receipts must not contain:

- raw prompt;
- raw provider response;
- raw reasoning or thinking;
- key, credential, token, or secret;
- hidden action payload;
- raw executable params.

## Rollback

L2 rollback may delete the generated draft or artifact only when deletion is
allowed by the lane. Even then, rollback must preserve tombstone and audit
metadata:

- original artifact hash;
- deletion or cleanup reason;
- rollback receipt id;
- timestamp;
- actor/executor id;
- lane id.

If tombstone/audit metadata cannot be written safely, rollback must be marked
unavailable and future execution must block before creating the artifact.

## FinalGate Posture

FinalGate later certifies:

- artifact stayed inside the L2 lane;
- no external mutation happened;
- no forbidden action class occurred;
- receipt contains path/hash metadata only;
- rollback posture exists;
- authority and budget were respected.
