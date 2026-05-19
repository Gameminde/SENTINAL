# Memory Control-System Model

Status: docs/spec lock candidate

## Purpose

This document models Sentinel memory as a closed-loop control system. The goal
is stable learning: feedback improves cognition without causing authority drift,
self-confirmation, or runaway confidence.

## Variables

```text
x_t = memory state at time t
y_t = receipts / measurements
e_t = feedback error
G   = gates / constraints
K   = feedback gain
```

Sentinel translation:

```text
memory = latent operating state
receipts = observations / measurements
feedback = correction signal
gates = admissible-state/action constraints
FinalGate = certification boundary
```

## Safe Update Equation

The future memory bridge should approximate:

```text
x_{t+1} = Project_G((1 - lambda) x_t + alpha * receipt + beta * feedback)
```

Where:

- `lambda` is forgetting / damping;
- `alpha` is measurement weight;
- `beta` is feedback gain;
- `Project_G` applies no-authority and no-execution constraints.

## Stability Rules

### Feedback Must Not Outweigh Evidence

```text
beta <= alpha
```

Feedback can suggest a correction. Evidence must dominate durable belief.

### Hard Constraints Must Remain Hard

Gates are constraints, not penalties.

Forbidden:

```text
score = reward - gate_penalty
```

for high-power surfaces such as credentials, browser submit, channel send,
spend, trade, desktop host control, file mutation, provider override, or policy
mutation.

Required:

```text
valid_action = G(candidate) == true
```

Memory cannot soften `G`.

### Confidence Cannot Become Authority

Unsafe loop:

```text
success -> confidence increase -> more authority -> more action -> more success
```

Safe loop:

```text
success -> scoped memory -> verification targets -> proposals -> gates
```

Authority expansion requires explicit root authority, not confidence.

## Measurement Weights

Future implementations should classify measurement strength:

| Measurement Class | Example Weight |
| --- | --- |
| simulated/internal role output | 0.2 |
| proposal artifact receipt | 0.3 |
| local deterministic test | 0.5 |
| integration test | 0.7 |
| external observed result | 0.9 |
| independently verifiable external result | 1.0 |
| explicit user correction | scope-specific priority source |

Weights are not authority. They affect confidence only.

## Damping And TTL

Non-lock memories require damping.

```text
memory_score_t = confidence * recency_decay * scope_match * receipt_quality
recency_decay = exp(-lambda * age)
```

Volatile domains require short TTL. Locked specs, tests, and policy can have
longer TTL, but they remain contradiction-sensitive.

Expired memory becomes historical context only.

## Entropy And Narrative Collapse

Memory should not collapse too early into one story. Track uncertainty across
competing hypotheses:

```text
H = -sum(p_i * log(p_i))
```

Low entropy is healthy only when evidence quality and diversity are high. Low
entropy from repeated same-source memory is brittle and should raise a warning.

## Risk Counters

Future memory bridge snapshots should track:

- memory entries created;
- memory entries expired;
- memory entries contradicted;
- duplicate source suppressions;
- self-generated evidence quarantines;
- contradiction count;
- missing evidence count;
- confidence before/after delta;
- variance before/after delta;
- source concentration;
- stale memory retrieval count;
- user correction supersession count;
- gate override attempt count;
- authority effect violations blocked;
- execution effect violations blocked.

## Promotion Formula

If future packs use memory to recommend promotion, the promotion score must
remain a recommendation only:

```text
promotion_score =
  calibrated_confidence
  * receipt_diversity
  * gate_margin
  * rollback_readiness
  * freshness
```

Block promotion recommendation if:

```text
contradiction_rate > threshold
OR source_concentration > threshold
OR gate_override_attempts > 0
OR rollback_plan_missing
OR independent_evidence_count == 0
```

Even a high promotion score cannot authorize action.

## Control-System Verdict

Sentinel memory must be evidence-seeking, not self-believing. It may update
attention and confidence. It may not update authority.
