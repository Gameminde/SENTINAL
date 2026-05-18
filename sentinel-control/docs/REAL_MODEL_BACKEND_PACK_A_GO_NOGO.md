# Real Model Backend Pack A Go / No-Go

Date: 2026-05-18
Status: Pre-implementation go/no-go

## Final Verdict

```text
PACK_A = GO_WITH_GUARDRAILS
lock_claim_allowed = NO
model_execution_deferral_closure = NO
provider_adapter = NO
runtime_wiring = NO
```

Pack A may start only as the model execution foundation.

The correct label after Pack A should be:

```text
real_model_execution_backend_foundation = STRUCTURAL_READY
```

not:

```text
real_model_execution_backend = FULL_LOCKED
```

## Allowed Pack A Scope

Allowed waves:

```text
Wave 0 inventory and backend proof
Wave 1 data models
Wave 2 provider interface and registry
Wave 3 credential handling
Wave 4 request builder
Wave 5 response validation
Wave 6 receipt shape
Wave 7.1 default-off coordinator
Wave 7.3 no-execution boundaries
```

Wave 7.2 rule:

```text
Wave 7.2 real provider execution = structure only in Pack A
successful provider execution path = deferred
```

## Not Allowed In Pack A

```text
Wave 8 real provider adapter
Wave 9 AgentRuntime wiring
real provider call
API key use or request
env file modification
fake provider backend
fake model response
runtime.py modification
CURRENT_STATE_LOCK.md modification
P6U start
Brain/Science expansion
new organ
tool/organ execution from model output
authority expansion
closing LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
closing P-C-RUNTIME-01-ACTIONBUDGET-DEFER
closing P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

## Required Pack A Proofs

Pack A must prove:

```text
provider registry rejects unknown providers
provider registry rejects disabled providers
provider registry rejects fake provider markers
missing credential does not call provider
missing credential does not fake a response
request metadata excludes raw prompt
credential handle excludes raw credential
receipt excludes raw prompt and raw credential
receipt hash is deterministic
validator rejects invalid schema
validator maps provider refusal to refusal outcome
validator rejects authority-expanding fields
coordinator default-off returns disabled/deferred outcome
model output never executes tools or organs
```

## Required Files If Implemented Later

Implementation files allowed for Pack A:

```text
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/models.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/provider.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/registry.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/credentials.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/policy.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/coordinator.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/validator.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/receipts.py
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/redaction.py
```

Test file allowed:

```text
sentinel-control/services/sentinel-core/tests/test_real_model_execution_backend.py
```

Doc file allowed:

```text
sentinel-control/docs/REAL_MODEL_EXECUTION_BACKEND_IMPLEMENTATION_LOG.md
```

## Required Verification If Pack A Is Implemented

Run from:

```text
sentinel-control/services/sentinel-core
```

Commands:

```bash
python -m pytest tests/test_real_model_execution_backend.py -q
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
git diff --check
git status --short --untracked-files=all
```

No provider integration test is required in Pack A because Wave 8 is not
implemented. If a skip-safe provider test is added early, it must skip when
configuration is absent and must fail if any fake response path is substituted.

## Stop Conditions

Stop immediately if any implementation attempt requires:

```text
real provider SDK import
real provider API call
API key value
writing env files
provider success without real provider adapter
fake backend or fake response
AgentRuntime.run wiring
tool execution from model output
authority mutation from response content
P6U/API organ changes
CURRENT_STATE_LOCK.md update
```

## Open Deferrals After Pack A

These must remain open:

```text
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

Reason:

```text
Pack A has no real provider adapter and no AgentRuntime wiring.
Action and mission token budgets require future authority-surface work.
```

## Go Condition For Wave 8 Later

Wave 8 may start only after Pack A proves:

```text
registry and fake-provider rejection are solid
credential redaction is solid
request/receipt hashing is deterministic
response validation blocks authority expansion
coordinator cannot fake success
```

Wave 8 must choose one sanctioned real provider, default-off, with API keys
from environment variables or scoped credential refs only.

## Go Condition For Wave 9 Later

Wave 9 may start only after Wave 8 has:

```text
one real provider adapter
skip-safe real-provider integration tests
timeout/redaction behavior
no raw credential leakage proof
no raw prompt/response durable leakage proof
```

Only then should `AgentRuntime.run` receive the coordinator after
`ModelCallPlan`.
