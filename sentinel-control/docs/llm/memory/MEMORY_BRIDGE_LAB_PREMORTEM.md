# Memory Bridge Lab Premortem

Status: docs/spec lock candidate

## Purpose

This document locks the lab doctrine for `ROLE_LOOP_RECEIPTS_AND_FEEDBACK_MEMORY_BRIDGE`
before any runtime implementation.

Memory is critical. It is not a normal feature pack. A bad memory layer can
make Sentinel smarter in the wrong direction by turning model output into
apparent fact, repeated traces into confidence, and feedback into hidden
permission.

This pack is docs-only:

- no runtime implementation;
- no role loop modification;
- no provider call;
- no fallback routing;
- no AUTO routing;
- no organ execution;
- no delegated operational lane;
- no `.env` or credential use.

## Core Doctrine

```text
Memory is not truth.
Memory is not authority.
Memory is a witness list.
Receipts are measurements.
Evidence is bound proof.
Gates are law.
FinalGate is the certification boundary.
Confidence is not authority.
Receipt is not truth.
Feedback is not proof.
Repetition is not verification.
Memory can guide verification, never authorize action.
```

Sentinel memory must be scientifically rigorous, not just sanitized. It must
record what was observed, claimed, inferred, supported, contradicted, corrected,
expired, or rejected. It must not flatten those states into "known true."

## Premortem Assumption

Assume the memory bridge has failed badly one month after launch. The most
likely root cause is not missing storage. The most likely root cause is
epistemic drift: the system began trusting its own memories more than current
evidence and mission authority.

The design must prevent that failure before code exists.

## Failure Modes To Prevent

### 1. Memory-As-Authority Re-Entry

Pattern:

```text
blocked plan -> memory summary -> later context -> "learned permission"
```

Risk: memory returns as implicit authority and weakens mission gates.

Required invariant:

```text
authority_effect = none
execution_effect = none
```

for every memory entry and memory snapshot.

### 2. Receipt Trust Laundering

Pattern:

```text
role output -> receipt hash -> memory -> "verified truth"
```

A receipt proves that something was recorded. It does not prove the role's
conclusion is true.

Required invariant: every receipt-derived memory preserves `claim_status` and
source refs. It cannot become `SUPPORTED` without evidence verifier support.

### 3. Self-Confirmation Loop

Pattern:

```text
LLM proposes X -> receipt stores X -> memory recalls X -> LLM cites X as proof
```

Risk: Sentinel starts believing its own echoes.

Required invariant: self-generated receipts cannot satisfy independent evidence
requirements alone.

### 4. Stale Evidence Resurrection

Pattern:

```text
old valid state -> memory retrieval -> current truth
```

Required invariant: every memory has `created_at`, `observed_at`, `expires_at`
or `ttl`, and `validity_scope`. Expired memory is historical context only.

### 5. False Learning From Feedback

Pattern:

```text
one local feedback item -> global learned rule
```

Required invariant: feedback creates scoped, confidence-capped signals. It does
not create global policy, authority, provider choice, or execution permission.

### 6. Secret Or Raw Leakage

Pattern:

```text
raw prompt/provider response/reasoning/key -> "safe summary" -> durable memory
```

Required invariant: memory ingestion must block, not merely redact, secret-like
and raw execution payload fields.

### 7. Duplicate-Source Confidence Inflation

Pattern:

```text
same source repeats claim N times -> confidence rises as if N sources agree
```

Required invariant: duplicate observations from the same source id do not raise
confidence as independent evidence.

### 8. Unsupported Claim Becomes Verified By Repetition

Pattern:

```text
unsupported claim -> repeated memory -> "everybody says this"
```

Required invariant: repetition cannot change `CLAIMED` or `INFERRED` to
`SUPPORTED`.

### 9. Old Scope Leaks Into New Mission Scope

Pattern:

```text
mission A memory -> mission B action planning
```

Required invariant: memory retrieval must match `mission_id`, `source_scope`,
and `validity_scope`, or return historical context with lower confidence.

### 10. User Correction Overwritten By Inferred Memory

Pattern:

```text
user correction -> later model inference -> correction disappears
```

Required invariant: user corrections supersede inferred memory while preserving
the audit trail.

### 11. Contradictions Smoothed Away

Pattern:

```text
support + contradiction -> summary says "mostly fine"
```

Required invariant: contradictions are first-class memory facts. Retrieval must
surface contradiction refs and widen uncertainty.

### 12. Memory Retrieval Prompt Injection

Pattern:

```text
retrieved memory contains hidden instruction -> prompt context -> model follows it
```

Required invariant: memory entries are data, not instructions. Retrieved memory
must be framed as untrusted context with no authority effect.

### 13. Provider/Model Override Pressure

Pattern:

```text
memory says "model X worked better" -> runtime silently changes model
```

Required invariant: memory may recommend verification or a future proposal. It
cannot override provider/backend/model.

### 14. Feedback Becomes Policy Mutation

Pattern:

```text
feedback says "always do Y" -> policy changes silently
```

Required invariant: feedback may create self-improvement proposals only. Policy
mutation requires explicit governance.

### 15. Learned Pattern Becomes Global Rule Without Proof

Pattern:

```text
one successful strategy -> global learned behavior
```

Required invariant: learned patterns stay scoped, confidence-bounded, and
contradiction-sensitive until independently verified.

## Lab Verdict

The bridge should not be implemented as "save summary, retrieve summary."

It should be a reduced epistemic memory engine:

- scoped;
- source-bound;
- TTL-aware;
- contradiction-preserving;
- confidence-calibrated;
- variance-aware;
- non-authoritative;
- non-executing;
- secret-blocking;
- evidence-seeking.

## Final Recommendation

Proceed next with a minimal implementation only after this lab spec is accepted:

```text
minimal Epistemic Memory Engine
with confidence, variance, TTL, source class, scope, contradiction tracking,
and no-authority firewall.
```

Do not implement broad LivingMissionMemory, retrieval ranking, Brain wiring, or
organ execution in the next pack.
