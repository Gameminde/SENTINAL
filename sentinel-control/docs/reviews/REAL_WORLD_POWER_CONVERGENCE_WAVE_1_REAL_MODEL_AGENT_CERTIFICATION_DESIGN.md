# Real-World Power Convergence Wave 1 - Real Model Agent Certification Design

Date: 2026-06-14

## Purpose

This pack tests whether one explicitly selected real model can drive Sentinel through controlled coding and browser missions using the existing governed runtime spine.

It is not a provider expansion, not a router, not fallback/AUTO, and not a deterministic adapter certification.

## Selected Model Contract

The certification uses one API model contract:

```text
provider_id = alibaba_model_studio_certification
backend_id = alibaba_model_studio_openai_compatible_chat
model = deepseek-v4-pro
endpoint = user-provided OpenAI-compatible endpoint
temperature = 0
provider-native tools = disabled
fallback/AUTO = blocked
credential source = runtime env var only
```

The API key is never written to the repository, receipts, reports, memory, or durable telemetry. Safe records may contain provider/backend/model ids, model contract hash, request/response hashes, token counts, latency, and cost estimates when available.

## Runtime Spine Reused

```text
UserModelContract
OpenAICompatibleChatProvider
ProviderCredentialHandle
ModelExecution redaction/hash utilities
MissionKernel / MissionRunStore
L3ReversibleWorkspaceExecutor
ShellCodeSandboxOrganV1
BrowserSessionManagerL5Live
BrowserFormSubmitSpecialAuthorityL6
MissionAuthorityEnvelope
receipts
FinalGate certificates
MissionReplayBuilder
```

## Certification Loop

```text
natural task goal
-> safe observation frame
-> real model emits one structured proposal
-> certification validator rejects unsafe/prohibited payloads
-> existing governed runtime executes allowed action
-> deterministic oracle evaluates actual state
-> safe observation or terminal record
```

The model output remains advisory data. The oracle and existing runtime proofs decide pass/fail.

## Structured Actions

Allowed action families are intentionally small and generic:

```text
read_file
run_tests
replace_file
open_browser
observe_browser
type_text
click
submit_form
open_tab
switch_tab
checkpoint
complete
```

The validator rejects:

```text
authority grants
provider/backend/model overrides
fallback/AUTO
provider-native tool requests
direct organ calls
raw credentials
raw prompts
raw provider responses
raw reasoning
payment/trading/security/account/desktop power
```

## Anti-Overfitting

The harness can define controlled fixtures and deterministic oracles. It cannot hide precomputed solutions, selectors, file names, or click scripts in the model prompt. Prompts expose generic tool schemas, current observations, and mission goals.

## Reporting Rule

All runs are retained, including failures. A run only passes when the deterministic oracle confirms the environment state. The model saying `complete` is not success.

## Wave 1 Truth

This pack can close the missing `AGENT_LEVEL_NOT_RUN` proof if a real model runs. It cannot by itself close all Wave 1 gates because process-restart continuity, safe public SaaS corpus, and soak remain separate gates.
