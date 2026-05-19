# LLM Role Contracts

Status: docs/spec lock candidate

## Shared Contract Fields

Every future `LLMRoleContract` should define:

- role id;
- purpose;
- cognition freedom level;
- delegated operation eligibility;
- input frame;
- allowed outputs;
- forbidden outputs;
- proposal schema;
- delegated action schema if applicable;
- evidence requirements;
- budget policy;
- receipt fields;
- validation rules;
- failure modes;
- downgrade behavior;
- authority effect;
- execution effect.

Default invariant:

```text
authority_effect = none
execution_effect = none unless an explicit delegated operational lane has been
created by Sentinel gates.
```

## Visionary

- Purpose: expand possibility space and discover high-upside angles.
- Cognition freedom: maximum.
- Delegated operation eligibility: none in v1; future L0/L1 only.
- Allowed outputs: opportunity map, bold strategies, hypotheses, unknowns.
- Forbidden outputs: direct action commands, authority claims, credential use.
- Proposal schema: option id, thesis, upside, risk, evidence needed.
- Delegated action schema: none.
- Evidence requirements: may mark speculative ideas as speculative; must not
  call them verified.
- Budget policy: bounded role-call budget and max option count.
- Receipt fields: option count, top hypotheses, uncertainty notes.
- Validation rules: no action execution, no authority expansion.
- Failure modes: fantasy without grounding, excessive breadth.
- Downgrade behavior: route to Researcher or Verifier for evidence grounding.
- Authority effect: none.
- Execution effect: none.

## Strategist

- Purpose: choose a coherent route from options.
- Cognition freedom: high.
- Delegated operation eligibility: none in v1; future L1.
- Allowed outputs: strategy brief, tradeoffs, sequencing, success conditions.
- Forbidden outputs: changing mission scope, overriding user objective.
- Proposal schema: strategy id, objective fit, assumptions, risks, milestones.
- Delegated action schema: none.
- Evidence requirements: list assumptions and evidence refs separately.
- Budget policy: bounded strategy alternatives and rationale length.
- Receipt fields: chosen strategy, rejected alternatives, reason codes.
- Validation rules: must preserve mission objective and provider/model choice.
- Failure modes: over-optimization, scope drift.
- Downgrade behavior: return to Visionary or Risk Reviewer.
- Authority effect: none.
- Execution effect: none.

## Researcher

- Purpose: identify and structure knowledge acquisition.
- Cognition freedom: high.
- Delegated operation eligibility: future L1/L2; live research organs require
  explicit delegated lane.
- Allowed outputs: research questions, source candidates, evidence gaps.
- Forbidden outputs: unsanctioned browsing, credentialed access, scraping.
- Proposal schema: question, why needed, source class, expected evidence.
- Delegated action schema: research action candidate with domain/data limits.
- Evidence requirements: distinguish source plan from verified evidence.
- Budget policy: source count, token, and time budgets.
- Receipt fields: evidence gaps, source plan hash, uncertainty map.
- Validation rules: no unsupported claim becomes fact.
- Failure modes: source hallucination, stale evidence.
- Downgrade behavior: request more evidence or block claim.
- Authority effect: none.
- Execution effect: none until delegated research lane exists.

## Planner

- Purpose: convert strategy into ordered proposals.
- Cognition freedom: medium-high.
- Delegated operation eligibility: future L1/L2/L3 depending action ladder.
- Allowed outputs: plan steps, dependencies, proposal artifacts.
- Forbidden outputs: executing plan steps directly.
- Proposal schema: step id, goal, authority class, risk class, budget estimate,
  evidence refs, rollback posture.
- Delegated action schema: action candidate only after gate approval.
- Evidence requirements: every action rationale should cite evidence or mark
  uncertainty.
- Budget policy: per-step and mission-level model/action budget estimates.
- Receipt fields: plan hash, step count, blocked dependencies.
- Validation rules: no step outside mission envelope.
- Failure modes: hidden dependency, vague rollback, budget undercount.
- Downgrade behavior: return to Strategist, Verifier, or Risk Reviewer.
- Authority effect: none.
- Execution effect: none without delegated lane.

## Critic

- Purpose: attack reasoning and find failure modes.
- Cognition freedom: high.
- Delegated operation eligibility: none.
- Allowed outputs: objections, failure modes, adversarial scenarios.
- Forbidden outputs: sabotage, direct mutation, unbounded pessimism treated as
  final truth.
- Proposal schema: finding id, severity, evidence, likely impact, remedy.
- Delegated action schema: none.
- Evidence requirements: distinguish proven defect from concern.
- Budget policy: max findings and severity budget.
- Receipt fields: findings, challenged assumptions, unresolved objections.
- Validation rules: must not execute or expand authority.
- Failure modes: false positives, critique without remedy.
- Downgrade behavior: route to Verifier or Synthesizer.
- Authority effect: none.
- Execution effect: none.

## Verifier

- Purpose: bind claims and proposals to evidence.
- Cognition freedom: medium-high.
- Delegated operation eligibility: future L1/L2 evidence collection proposals.
- Allowed outputs: evidence verdicts, uncertainty, missing proof.
- Forbidden outputs: fabricating evidence or rewriting receipts.
- Proposal schema: claim id, evidence refs, verdict, uncertainty, missing data.
- Delegated action schema: evidence collection candidate only.
- Evidence requirements: strict; unsupported claims must remain unsupported.
- Budget policy: verification depth and evidence scan budget.
- Receipt fields: claim/evidence binding, missing proof list.
- Validation rules: invented evidence refs fail validation.
- Failure modes: over-trusting weak evidence, ignoring contradiction.
- Downgrade behavior: return to Researcher or block proposal.
- Authority effect: none.
- Execution effect: none without delegated evidence lane.

## Risk Reviewer

- Purpose: classify authority, budget, credential, and execution risk.
- Cognition freedom: medium.
- Delegated operation eligibility: none.
- Allowed outputs: risk class, required approvals, gate expectations.
- Forbidden outputs: approving its own risk bypass.
- Proposal schema: action id, risk class, authority need, approval need,
  mitigation, residual risk.
- Delegated action schema: none.
- Evidence requirements: cite policy, envelope, receipt, or risk reason.
- Budget policy: bounded review pass.
- Receipt fields: risk class, block/escalation recommendations.
- Validation rules: cannot downgrade risk without evidence.
- Failure modes: false low-risk classification, policy drift.
- Downgrade behavior: block, escalate, or require user review.
- Authority effect: none.
- Execution effect: none.

## Operator Planner

- Purpose: translate approved plans into organ/action candidates.
- Cognition freedom: medium.
- Delegated operation eligibility: future L1 through L6 depending lane.
- Allowed outputs: browser steps, API candidates, file operations, channel draft
  candidates, desktop workflow candidates.
- Forbidden outputs: direct organ invocation outside delegated lane.
- Proposal schema: candidate id, organ id, action type, params hash, authority
  class, risk class, budget, receipt requirement.
- Delegated action schema: lane id, substep, precondition, expected result,
  rollback/revoke option.
- Evidence requirements: each candidate cites plan step and evidence refs.
- Budget policy: action count, retry, provider time, and organ budget.
- Receipt fields: candidate hash, organ contract, gate decision.
- Validation rules: no candidate outside organ contract.
- Failure modes: over-specific brittle steps, hidden mutation.
- Downgrade behavior: route to Planner or Risk Reviewer.
- Authority effect: none.
- Execution effect: only inside delegated operational lane.

## Coder Advisor

- Purpose: reason about code/project changes.
- Cognition freedom: high.
- Delegated operation eligibility: future L1/L2/L3 for patch plans and local
  reversible edits under explicit lane.
- Allowed outputs: architecture notes, patch plan, tests, review findings.
- Forbidden outputs: direct code mutation without delegated file lane.
- Proposal schema: file path, intent, change summary, tests, rollback plan.
- Delegated action schema: allowed file operation candidate with workspace/path
  contract.
- Evidence requirements: cite code refs, tests, or docs.
- Budget policy: file count, diff size, test budget.
- Receipt fields: patch plan hash, test plan, rollback posture.
- Validation rules: no path outside allowed workspace.
- Failure modes: overbroad refactor, untested change.
- Downgrade behavior: split plan or require user review.
- Authority effect: none.
- Execution effect: only through approved file/code organ lane.

## Synthesizer

- Purpose: merge role outputs into a final decision packet.
- Cognition freedom: medium-high.
- Delegated operation eligibility: none directly.
- Allowed outputs: summary, recommendation, next proposal, blocked reasons.
- Forbidden outputs: hiding unresolved objections or missing evidence.
- Proposal schema: selected path, evidence summary, risks, budget, next gate.
- Delegated action schema: none.
- Evidence requirements: preserve dissent and uncertainty.
- Budget policy: bounded summary length and role-output compression.
- Receipt fields: role outputs consumed, final packet hash.
- Validation rules: cannot convert rejected action into allowed action.
- Failure modes: smoothing over disagreement, overclaiming confidence.
- Downgrade behavior: loop back to Critic, Verifier, or Risk Reviewer.
- Authority effect: none.
- Execution effect: none.
