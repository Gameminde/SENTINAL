# Memory Failure Modes

Status: docs/spec lock candidate

## Purpose

This document lists the failure modes the future memory bridge must test
against. Each failure mode includes predicted pattern, impact, and required
guard.

## 1. Memory-As-Authority Re-Entry

Pattern:

```text
blocked action -> memory summary -> future planner treats it as allowed
```

Impact: root authority erodes through memory.

Guard:

- memory entries always have `authority_effect = none`;
- retrieval cannot add allowed actions;
- tests reject memory fields that look like approval or authority grants.

## 2. Receipt Trust Laundering

Pattern:

```text
receipt hash -> memory summary -> verified fact
```

Impact: auditability is mistaken for truth.

Guard:

- receipt-derived memory must preserve `claim_status`;
- `SUPPORTED` requires evidence verifier support;
- receipt refs alone cannot satisfy evidence requirements.

## 3. Self-Confirmation Loop

Pattern:

```text
model output -> receipt -> memory -> model cites memory as evidence
```

Impact: the model verifies itself.

Guard:

- self-generated receipts are internal context;
- independent evidence count must be tracked;
- self-generated source lineage cannot increase independent support.

## 4. Stale Evidence Resurrection

Pattern:

```text
old repo/provider/runtime state -> current decision
```

Impact: historical truth becomes current falsehood.

Guard:

- TTL and freshness class required;
- expired memories returned as historical context only;
- current-state claims require fresh verification.

## 5. False Learning From Feedback

Pattern:

```text
one feedback event -> global preference or policy
```

Impact: accidental feedback becomes durable behavior.

Guard:

- feedback memory is scoped;
- confidence cap on single feedback;
- user correction source class distinct from general feedback;
- policy mutation is proposal-only.

## 6. Secret Or Raw Leakage

Pattern:

```text
raw prompt/response/reasoning/key -> durable memory field
```

Impact: secret leakage and irreversible contamination.

Guard:

- recursive scanner blocks raw prompt, raw response, reasoning fields, keys,
  Bearer tokens, credential-like strings, hidden action payloads;
- blocked input creates a rejection signal, not memory.

## 7. Duplicate-Source Confidence Inflation

Pattern:

```text
same source repeats claim -> confidence treated as independent agreement
```

Impact: false certainty.

Guard:

- source lineage id required;
- duplicate source suppression counter;
- confidence updates require independent source diversity.

## 8. Unsupported Claim Verified By Repetition

Pattern:

```text
CLAIMED -> repeated -> SUPPORTED
```

Impact: repetition becomes truth.

Guard:

- repetition cannot change claim status;
- only evidence verifier can move a claim toward support.

## 9. Scope Leakage

Pattern:

```text
mission A memory -> mission B plan
```

Impact: wrong context controls current reasoning.

Guard:

- `mission_id`, `source_scope`, and `validity_scope` required;
- scope mismatch lowers confidence and marks historical context.

## 10. User Correction Overwritten

Pattern:

```text
user correction -> later inferred memory -> correction lost
```

Impact: user intent becomes unstable.

Guard:

- user correction supersedes inferred memory in scope;
- audit trail preserved;
- later inference cannot overwrite correction without explicit user update.

## 11. Contradiction Smoothing

Pattern:

```text
supported evidence + contradictory evidence -> smooth summary hides conflict
```

Impact: uncertainty disappears.

Guard:

- contradiction refs required;
- retrieval returns contradictions;
- variance increases when contradiction exists.

## 12. Retrieval Prompt Injection

Pattern:

```text
memory summary contains instruction -> role prompt follows it
```

Impact: memory becomes hidden prompt channel.

Guard:

- retrieved memory is data, not instruction;
- scanner rejects instruction-shaped hidden action payloads;
- prompt renderer frames memory as untrusted context.

## 13. Provider/Model Override Pressure

Pattern:

```text
memory says "use model B" -> plan silently changes user-selected model
```

Impact: user-selected model doctrine breaks.

Guard:

- memory cannot mutate `UserModelContract`;
- model/provider observations remain recommendation metadata only.

## 14. Feedback As Policy Mutation

Pattern:

```text
feedback -> learned policy -> automatic runtime behavior change
```

Impact: governance bypass.

Guard:

- feedback creates self-improvement proposal only;
- code, prompt, policy, provider, organ, and runtime changes need explicit gate.

## 15. Learned Pattern As Global Rule

Pattern:

```text
one successful strategy -> always use this strategy
```

Impact: overfitting and brittle reasoning.

Guard:

- learned pattern has scope and variance;
- contradiction-sensitive;
- global promotion requires independent evidence, user review, and future gate.

## Failure Mode Verdict

Every implementation task must include tests for these classes. If a test suite
only checks storage and retrieval, it is not sufficient.
