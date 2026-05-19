# Memory Epistemic Model

Status: docs/spec lock candidate

## Purpose

This document defines the minimal epistemic model for future Sentinel LLM
memory.

The goal is to prevent false knowledge. Memory must preserve the difference
between:

- observed;
- claimed;
- inferred;
- supported;
- weakly supported;
- contradicted;
- expired;
- superseded;
- rejected;
- unknown.

## Scientific Definition

Sentinel memory is scoped epistemic witness state.

```text
Receipts = measurements.
Evidence = bound proof.
Memory = scoped epistemic witness state.
Feedback = learning signal.
Gates = law.
FinalGate = certification boundary.
```

Memory is allowed to bias attention toward useful questions. It is not allowed
to certify truth or authorize action.

## Minimal Memory Entry Fields

Every future `LivingMissionMemoryEntry` must contain:

| Field | Meaning |
| --- | --- |
| `memory_id` | Stable memory id. |
| `mission_id` | Mission scope that produced the memory. |
| `source_class` | Source type such as receipt, evidence, user correction, role output. |
| `source_id` | Source object id. |
| `source_scope` | Scope where the source is valid. |
| `created_at` | Time memory entry was created. |
| `observed_at` | Time underlying observation happened, if known. |
| `expires_at` or `ttl` | Expiration boundary. |
| `claim_status` | Epistemic status of the claim. |
| `confidence` | Calibrated advisory confidence, 0.0 to 1.0. |
| `variance` | Uncertainty around confidence. |
| `contradiction_refs` | Refs that challenge this memory. |
| `evidence_refs` | Bound evidence refs. |
| `receipt_refs` | Receipt refs used to create this memory. |
| `uncertainty` | Explicit uncertainty statements. |
| `validity_scope` | Scope where this memory may be used. |
| `summary` | Safe summary only. |
| `authority_effect` | Always `none`. |
| `execution_effect` | Always `none`. |

## Claim Statuses

| Status | Meaning |
| --- | --- |
| `OBSERVED` | A measurement or receipt observed an event. |
| `CLAIMED` | A source claimed something. |
| `INFERRED` | Sentinel inferred something from other data. |
| `SUPPORTED` | Evidence verifier supports the claim in scope. |
| `WEAK_SUPPORT` | Some evidence exists but it is incomplete or weak. |
| `CONTRADICTED` | Contradictory evidence exists. |
| `EXPIRED` | TTL or freshness boundary has passed. |
| `SUPERSEDED` | Newer correction or evidence superseded this memory. |
| `REJECTED` | The claim or memory was rejected by validation. |
| `UNKNOWN` | Provenance or evidence is insufficient. |

Status transitions must be explicit. Repetition alone cannot move a memory to
`SUPPORTED`.

## Source Classes

| Source Class | Weighting Rule |
| --- | --- |
| `user_instruction` | Strong for user intent in current scope; not global by default. |
| `user_correction` | Supersedes inferred memory for user-owned facts and preferences. |
| `receipt` | Measurement of recorded event, not truth by itself. |
| `evidence` | Bound proof object; must be inspectable or replayable. |
| `role_output` | Model cognition; never independent proof by itself. |
| `proposal_artifact` | Non-executing plan/candidate; not proof. |
| `verifier_result` | Evidence binding verdict; cannot grant authority. |
| `gate_result` | Gate decision; cannot be rewritten by memory. |
| `finalgate_result` | Certification result; high-quality measurement. |
| `system_policy` | Policy source; memory may cite it but not mutate it. |
| `external_observation` | External observed fact; requires freshness and scope. |

## Confidence And Variance

Confidence is advisory. It guides what to verify next.

```text
confidence != authority
```

A future implementation may use weighted evidence:

```text
weighted_support = sum(source_weight_i * support_i)
weighted_failure = sum(source_weight_i * contradiction_i)
confidence = (weighted_support + a) /
             (weighted_support + weighted_failure + a + b)
```

Variance rises when:

- evidence is stale;
- sources are concentrated;
- contradictions exist;
- support is self-generated;
- scope mismatch exists;
- user correction conflicts with inference.

## Duplicate Source Suppression

Repeated claims from the same source lineage count as one source family.

```text
independent_support <= unique(source_lineage_id)
```

The same LLM output, role loop, proposal, or receipt lineage cannot inflate
confidence as if it were independent evidence.

## Self-Generated Evidence Rule

Self-generated receipts may support auditability, not truth. They can say:

```text
Sentinel produced proposal P at time T.
```

They cannot independently prove:

```text
Proposal P is correct.
```

For evidence requirements, self-generated memory must be marked as internal
context unless paired with independent evidence.

## User Correction Rule

User corrections are first-class epistemic updates.

They must:

- supersede older inferred memory in the relevant scope;
- preserve the older memory as audit trail;
- lower confidence in related inferred patterns;
- avoid deleting contradictions silently.

## Contradiction Rule

Contradictions must survive retrieval.

Retrieval must not produce a clean summary that hides contradiction refs. If a
claim is contradicted, the memory output must include:

- supported refs;
- contradictory refs;
- current claim status;
- uncertainty;
- safe next verification target.

## Unknown Is A Valid State

When provenance is missing or stale, the correct state is `UNKNOWN`, not a
fabricated confidence. Sentinel should prefer explicit uncertainty over
beautiful but false continuity.
