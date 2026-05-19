# LLM Self-Improvement Proposal Loop

Status: docs/spec lock candidate

## Purpose

The LLM should learn from Sentinel's receipts, failures, blocked actions,
budget waste, and weak evidence. This is a powerful capability, but it must
remain proposal-only until governed.

## Allowed Analysis

The LLM may analyze:

- role-loop receipts;
- rejected plans;
- blocked delegated action candidates;
- failed organ results;
- budget overruns;
- weak evidence;
- bad outputs;
- test failures;
- review findings;
- user corrections;
- FinalGate failures.

## Allowed Proposals

The LLM may propose improvements to:

- prompts;
- role contracts;
- strategy patterns;
- evidence gathering;
- budget estimates;
- tests;
- docs;
- code plans;
- organ proposal schemas;
- risk classifications.

## Forbidden Automatic Mutation

The LLM may not automatically mutate:

- runtime code;
- policy;
- authority envelopes;
- provider registry;
- provider/backend/model choice;
- prompt contracts;
- tools;
- organs;
- credentials;
- `.env`;
- tests;
- production state.

Self-improvement remains:

```text
observe -> diagnose -> propose -> gate -> user/Sentinel governance -> execute if allowed
```

## Proposal Schema

Every self-improvement proposal should include:

- proposal id;
- problem observed;
- receipt/evidence refs;
- proposed change;
- expected benefit;
- risk class;
- budget estimate;
- affected surface;
- approval requirement;
- rollback plan;
- validation plan.

## Downgrade Behavior

If a self-improvement proposal touches code, policy, prompts, providers,
authority, credentials, organs, or runtime behavior, it must downgrade to
explicit review. It cannot auto-apply.

## FinalGate Relationship

FinalGate certifies that self-improvement remained proposal-only unless a later
delegated execution lane explicitly authorized a bounded change.
