# LLM Power Unleash Implementation Roadmap

Status: docs/spec lock candidate

## Current Truth

```text
current_phase = SENTINEL_MODEL_EXECUTION_BUDGETS_LOCKED
real_runtime_model_execution = WIRED_AND_VALIDATED
provider_backend_model_contract = EXPLICIT
credential_binding = ENFORCED
catalog_constrains_execution = TRUE
model_budgets = ENFORCED
production_provider_routing = OPEN
fallback_routing = NOT_STARTED / NOT_APPROVED
AUTO_model_routing = NOT_STARTED / NOT_APPROVED
```

## Next Implementation Sequence

### 1. STRICT_SINGLE_MODEL_ROLE_LOOP

Implement a multi-role cognition loop using the existing user-selected
provider/backend/model for every role.

No organ execution. No provider expansion. No fallback.

### 2. LLM Delegated Action Ladder Data Model

Introduce explicit action levels L0-L7 as data contracts. Do not execute new
levels broadly yet.

### 3. Proposal Artifact Schemas

Define structured proposal artifacts for plans, browser steps, API candidates,
email drafts, file/code plans, research plans, and self-improvement proposals.

### 4. Evidence-Bound Verifier

Require claims and proposals to bind to evidence refs, receipts, observations,
or explicit uncertainty.

### 5. Role-Loop Receipts

Record safe role-loop metadata:

- role id;
- model id;
- input hashes;
- output hashes;
- evidence refs;
- budget use;
- decision summary;
- validation result.

No raw prompt, response, reasoning, or key durability.

### 6. Feedback Into Workspace / Belief / Receipts

Feed blocked actions, failures, evidence gaps, budget waste, and successful
strategies back into safe mission memory.

### 7. Organ Proposal Bridge

Map role-loop proposals to organ-specific candidates without execution. This is
the bridge from cognition to delegated operation.

### 8. Delegated Low-Risk Action Execution

Allow first bounded low-risk delegated lanes, likely L2/L3 first:

- draft/local artifacts;
- reversible local workspace actions;
- non-submitting browser preparation only if already authorized by a future
  organ contract.

### 9. Strict Multi-Model By User

Allow role-specific models only when explicitly selected by the user.

### 10. FLEX Later

Allow model recommendations through explicit policy. Recommendations cannot
execute as routing.

### 11. AUTO Much Later

AUTO routing requires its own contract, evidence base, and FinalGate checks.

## Must Not Start Yet

- broad organ execution;
- provider expansion;
- fallback routing;
- AUTO routing;
- P6U implementation;
- Brain/Science live society;
- real spend/trading live execution;
- provider-native tool execution;
- model-controlled credential access.

## Success Criteria For This Spec Pack

- Doctrine locked.
- Delegated authority model defined.
- Cognition and operation zones defined.
- Role hierarchy and contracts defined.
- Delegated action ladder defined.
- Proposal-to-execution gate defined.
- Receipt and feedback model defined.
- Self-improvement proposal loop defined.
- Multi-model roadmap defined without implementing FLEX/AUTO.
