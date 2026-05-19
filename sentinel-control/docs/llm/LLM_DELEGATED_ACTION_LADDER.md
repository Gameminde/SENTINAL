# LLM Delegated Action Ladder

Status: docs/spec lock candidate

## Purpose

The delegated action ladder defines how LLM agency grows without confusing
agency with root authority.

```text
Cognition is free.
Execution is delegated.
Authority is sovereign.
```

## Ladder

| Level | Name | Meaning |
| --- | --- | --- |
| L0 | Thought only | Internal cognition, no proposal required. |
| L1 | Proposal only | Structured non-executing proposal. |
| L2 | Draft/local artifact | Create draft or local artifact in allowed area. |
| L3 | Reversible local action | Execute reversible local workspace action. |
| L4 | External low-risk action | Execute bounded external low-risk action. |
| L5 | User-confirmed high-risk action | Execute high-risk action after explicit approval. |
| L6 | Live powerful action with strict contracts | Execute strong live organ action under strict authority. |
| L7 | Exceptional strategic action | Execute only under explicit special authority. |

## L0 - Thought Only

- LLM can decide: ideas, hypotheses, critiques, strategies.
- Sentinel verifies: no durable raw reasoning, no action payload.
- User approves: nothing.
- Receipt required: role-loop metadata if persisted.
- Rollback/revocation: discard thought artifact.
- FinalGate certifies: no execution occurred.

## L1 - Proposal Only

- LLM can decide: proposed plan, action candidate, draft intent.
- Sentinel verifies: proposal schema, authority class, risk class, evidence refs,
  budget estimate.
- User approves: only if policy requires reviewing the proposal.
- Receipt required: proposal artifact hash and validation status.
- Rollback/revocation: proposal can be rejected.
- FinalGate certifies: proposal did not execute.

## L2 - Draft / Local Artifact

- LLM can decide: draft content, local artifact structure, allowed file candidate.
- Sentinel verifies: workspace path, allowed file class, budget, no secret leak.
- User approves: not required for low-risk local drafts if envelope allows.
- Receipt required: artifact path/hash, inputs used, rollback path.
- Rollback/revocation: delete or restore local artifact.
- FinalGate certifies: local artifact stayed within lane.

## L3 - Reversible Local Action

- LLM can decide: bounded local action substeps.
- Sentinel verifies: reversibility, path containment, tool/organ contract, budget.
- User approves: optional by policy.
- Receipt required: before/after hash, rollback receipt, action ledger.
- Rollback/revocation: revert local action.
- FinalGate certifies: action was reversible and within envelope.

## L4 - External Low-Risk Action

- LLM can decide: bounded external substeps such as read-only API query,
  low-risk browser navigation, or non-submitting form preparation.
- Sentinel verifies: domain/account/scope, credential policy, rate/budget,
  no submit/send/spend.
- User approves: required if policy marks the external action user-visible.
- Receipt required: request metadata hash, response metadata hash, redaction.
- Rollback/revocation: stop future calls, revoke lane; external read cannot be
  undone but has no mutation.
- FinalGate certifies: external action stayed low-risk and bounded.

## L5 - User-Confirmed High-Risk Action

- LLM can decide: exact proposed high-risk action after user approval has
  authorized that exact lane.
- Sentinel verifies: approval matches dry-run preview, budget, risk,
  credential scope, receipt plan.
- User approves: explicit approval required.
- Receipt required: approval receipt, execution receipt, result receipt.
- Rollback/revocation: defined per organ; must be explicit before execution.
- FinalGate certifies: approved action matched the approved preview.

## L6 - Live Powerful Action With Strict Contracts

- LLM can decide: operational substeps inside a live powerful lane.
- Sentinel verifies: strict authority contract, kill switch, budget, credentials,
  rollback/disable plan, evidence, and FinalGate hooks.
- User approves: explicit contract or policy-defined live authority required.
- Receipt required: high-fidelity action ledger, budget ledger, risk ledger,
  organ receipts, FinalGate receipt.
- Rollback/revocation: live disable, credential revoke, kill switch, rollback
  where possible.
- FinalGate certifies: live power stayed inside contract.

## L7 - Exceptional Strategic Action

- LLM can decide: recommendation and operational plan only after special
  authority exists.
- Sentinel verifies: special authority, human approval, risk escalation,
  budget cap, credential scope, rollback plan, legal/policy constraints.
- User approves: explicit special approval required.
- Receipt required: full special authority packet and execution trail.
- Rollback/revocation: special contract defines emergency stop and recovery.
- FinalGate certifies: exceptional action had explicit special authority.

## Prohibited Across All Levels

- Root Authority expansion by model output.
- Provider/backend/model override by model output.
- Credential access beyond envelope.
- Raw prompt, response, reasoning, or key durability.
- Hidden action payloads.
- Provider-native tool execution without Sentinel organ contract.
