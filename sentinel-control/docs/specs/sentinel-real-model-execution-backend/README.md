# Sentinel Real Model Execution Backend Spec Mirror

Canonical tracked mirror of the local Kiro spec.

## Current Implementation Status Overlay - 2026-05-18

This mirror began as an exact tracked copy of the local Kiro spec. The original
spec body remains historical planning context, but the current repository state
has advanced beyond the initial docs-only plan:

```text
foundation_commit = bcb35d2 runtime: add real model execution foundation
provider_adapter_commit = 187d251 runtime: add real model provider adapters
runtime_wiring_commit = 76ad92e runtime: wire model execution coordinator into agent runtime
real_runtime_validation_commit = 9647993 test: validate real runtime model execution
provider_catalog_commit = 7f0ddcb runtime: add model provider catalog
openai_compatible_base_commit = 4052be9 runtime: harden openai-compatible provider base
```

Current truth:

```text
runtime_model_execution = WIRED
runtime_real_provider_validation = SUCCESS_VALIDATED through AgentRuntime.run
provider_catalog = IMPLEMENTED
openai_compatible_base = HARDENED
provider_expansion_immediate = NO-GO
next_technical_pack = sentinel-model-execution-contract-hardening
```

Open:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
MODEL_EXECUTION_BUDGET_GOVERNANCE
PRODUCTION_PROVIDER_ROUTING
```

The local Kiro files under `.kiro/specs/sentinel-real-model-execution-backend/`
are ignored by repository rules. The three Markdown files in this directory are
exact copies of that local spec so Codex/Opus synchronization can use durable
repo-visible truth without force-adding ignored `.kiro` files.
