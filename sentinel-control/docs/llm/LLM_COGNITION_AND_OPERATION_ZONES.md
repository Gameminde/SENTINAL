# LLM Cognition And Operation Zones

Status: docs/spec lock candidate

## Zone Map

Sentinel separates thought, proposal, delegated operation, execution, and
learning. This separation lets the LLM think at maximum power while keeping
world mutation mediated.

```text
Free Cognition
-> Evidence Reasoning
-> Proposal
-> Authority / Budget / Risk Gate
-> Delegated Operational
-> Organ Execution
-> Receipt / Feedback / Learning
```

## 1. Free Cognition Zone

Purpose: maximum imagination and reasoning.

Allowed:

- brainstorming;
- strategy generation;
- self-debate;
- criticism;
- research planning;
- code planning;
- hypothesis generation;
- wild scenario exploration;
- opportunity discovery.

Forbidden:

- world mutation;
- durable raw prompt storage;
- durable raw response storage;
- durable raw reasoning storage;
- secret access;
- organ calls;
- authority expansion.

Clarification:

```text
Unlimited imagination does not mean unlimited durable logging, secret access,
or direct mutation.
```

## 2. Evidence Reasoning Zone

Purpose: bind cognition to truth.

Every claim should carry:

- evidence refs when available;
- receipt refs when available;
- observation refs when available;
- uncertainty level;
- missing evidence;
- contradiction notes.

The LLM can interpret evidence. It cannot rewrite evidence, mark unsupported
claims as verified, or convert memory into authority.

## 3. Proposal Zone

Purpose: transform cognition into structured non-executing artifacts.

Proposal artifacts may include:

- mission plans;
- action candidates;
- API request candidates;
- browser step candidates;
- desktop workflow candidates;
- channel/email drafts;
- code patch plans;
- research plans;
- risk mitigations;
- self-improvement proposals.

Every proposal must include:

- authority class;
- risk class;
- budget estimate;
- evidence refs;
- expected outcome;
- rollback posture;
- user review requirement if applicable.

## 4. Authority / Budget / Risk Gate

Purpose: decide whether a proposal can become a delegated operational lane.

The gate validates:

- mission envelope;
- scope;
- action budget;
- token/cost budget;
- risk class;
- credential policy;
- organ promotion level;
- user approval requirement;
- receipt requirement.

Gate decisions:

- `allowed`;
- `blocked`;
- `needs_user_review`;
- `needs_more_evidence`;
- `budget_exhausted`;
- `authority_extension_required`.

## 5. Delegated Operational Zone

Purpose: let the LLM operate inside an approved lane.

The LLM may choose substeps only inside the lane. It may operate an organ
through the runtime gate and organ contract. It may not arbitrarily execute or
change the lane boundaries.

Examples:

- choose next click inside approved browser navigation;
- choose which allowed file to edit inside an approved workspace path;
- choose retry strategy inside retry budget;
- choose draft text before user-approved send.

## 6. Organ Execution Zone

Purpose: real world or workspace action through a Sentinel organ.

Organs execute only approved bounded actions. High-power classes require
stronger authority:

- browser submit;
- email/channel send;
- credential use;
- desktop host control;
- shell/process;
- upload/download;
- spend/payment/trading;
- production mutation.

Every execution produces receipts.

## 7. Receipt / Feedback / Learning Zone

Purpose: make outcomes improve future cognition.

Receipts record safe truth about:

- action attempted;
- gate decision;
- organ result;
- rejection reason;
- budget use;
- evidence produced;
- rollback status;
- FinalGate result.

Receipts can feed the next loop. They cannot grant authority or rewrite history.
