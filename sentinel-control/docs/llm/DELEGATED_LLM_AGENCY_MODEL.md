# Delegated LLM Agency Model

Status: docs/spec lock candidate

## Purpose

This document defines the authority model that lets Sentinel unleash LLM agency
without allowing the model to rewrite the law of the system.

The LLM may operate inside delegated lanes. It may not create the lane, widen
the lane, or ignore the lane.

## Root Authority

`RootAuthority` is the sovereign permission layer. It defines what the mission
is allowed to do.

Sources:

- user mission intent;
- `MissionAuthorityEnvelope`;
- explicit user approvals;
- policy;
- special authority contracts.

The LLM can never create, expand, or rewrite Root Authority.

Root Authority controls:

- allowed systems;
- allowed tools and actions;
- allowed paths, domains, accounts, and data classes;
- cost, token, action, duration, and recipient budgets;
- risk posture;
- credential access;
- provider/backend/model contract;
- send, spend, trade, browser submit, upload, download, shell, desktop, and
  other high-power classes.

## Delegated Operational Authority

`DelegatedOperationalAuthority` is a bounded lane created by Sentinel after
checking Root Authority and current mission state.

Sources:

- Sentinel authority gate;
- mission envelope;
- budget gate;
- risk gate;
- organ contract;
- receipt requirements;
- FinalGate requirements.

Inside delegated authority, the LLM may choose operational substeps, such as:

- click;
- navigate;
- type;
- send;
- call API;
- modify allowed files;
- use browser, desktop, API, channel, file, OCR, vision, image/video/design,
  code/project, and future spend/trading organs;
- coordinate a campaign;
- retry or repair within a bounded allowance.

These operations are legal only while the action remains inside the lane.

## Lane Rules

Every delegated lane must be:

- bounded;
- observable;
- revocable;
- budgeted;
- risk-classified;
- receipted;
- certifiable;
- blocked if it leaves the lane.

The LLM can approve or choose operational substeps inside an existing lane. It
cannot:

- expand lane boundaries;
- approve spend/send/trade/credential use beyond the envelope;
- change provider/backend/model;
- convert a rejected proposal into execution;
- bypass user review when the lane requires it;
- bypass FinalGate.

## Permission Model

```text
Root Authority decides what may exist.
Delegated Operational Authority decides what may run now.
The LLM can operate within the second.
The LLM can never author the first.
```

## Examples

Allowed future delegated lane:

```text
Mission allows browser navigation on example.com.
Gate allows click/type on non-submit elements.
LLM chooses click and type substeps.
Browser organ executes bounded actions.
Receipts capture each result.
FinalGate certifies the run.
```

Blocked boundary crossing:

```text
Mission allows drafting an email.
LLM proposes send.
Gate sees no send authority.
Action is blocked or escalated for user approval.
No channel organ send occurs.
```

Special authority future lane:

```text
Mission explicitly grants low-risk spend test authority.
Budget, risk, credential, and rollback contracts pass.
LLM may choose bounded spend operation substeps.
Spend organ executes only the approved lane.
Receipts and FinalGate remain mandatory.
```
