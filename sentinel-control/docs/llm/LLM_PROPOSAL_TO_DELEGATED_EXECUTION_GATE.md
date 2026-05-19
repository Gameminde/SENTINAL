# LLM Proposal To Delegated Execution Gate

Status: docs/spec lock candidate

## Pipeline

```text
LLM thought
-> structured proposal or delegated action candidate
-> authority check
-> budget check
-> risk check
-> organ contract check
-> receipt requirement
-> execution if allowed
-> FinalGate certification
```

No raw thought becomes direct action.

## Gate Inputs

The future gate consumes:

- `ProposalArtifact` or `DelegatedActionCandidate`;
- `MissionAuthorityEnvelope`;
- current mission state;
- provider/backend/model contract;
- budget ledger;
- risk policy;
- credential policy;
- organ contract;
- evidence refs;
- receipt requirements;
- user approval state when needed.

## Gate Decisions

| Decision | Meaning |
| --- | --- |
| `allowed` | Candidate becomes a delegated operational lane. |
| `blocked` | Candidate violates authority, risk, budget, or organ contract. |
| `needs_user_review` | Candidate may run only after explicit user approval. |
| `needs_more_evidence` | Candidate lacks proof or has unresolved uncertainty. |
| `budget_exhausted` | Token/cost/action/provider-time budget is exhausted. |
| `authority_extension_required` | Candidate requires a new root authority decision. |

## Required Checks

Authority:

- mission identity matches;
- action class is allowed;
- forbidden action is absent;
- requested system/path/domain/account is allowed;
- provider/backend/model is not overridden.

Budget:

- model token budget;
- action budget;
- mission budget;
- retry budget;
- provider time budget;
- organ-specific budget.

Risk:

- risk class;
- user-visible effect;
- reversibility;
- sensitive data;
- external mutation;
- spend/trade/payment;
- credential use.

Organ contract:

- organ exists and is promoted to required level;
- action shape matches organ schema;
- no provider-native tool bypass;
- receipt fields are available;
- rollback/revoke path is defined when required.

## Delegated Operational Lane

If the gate returns `allowed`, Sentinel creates a bounded lane:

```text
lane_id
action_level
organ_id
allowed_substeps
budget
risk_class
credential_scope
receipt_contract
revocation_rule
FinalGate_checks
```

The LLM can operate inside this lane. The LLM cannot expand it.

## Block And Escalation Feedback

Blocked, review, evidence, budget, and authority-extension decisions feed the
next cognition loop as safe feedback. The LLM may learn why a lane failed and
propose better plans. It may not treat rejection feedback as permission.
