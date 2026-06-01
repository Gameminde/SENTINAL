# Browser Neural Operator Cortex Spec

Status: SPEC / no runtime power added

Date: 2026-06-02

## Purpose

The Browser Neural Operator Cortex is the controlled cognitive layer above the
existing browser L4/L5/L6 runtime stack. It converts browser receipts, evidence,
failures, and verification results into typed signals, then emits motor
proposal artifacts that must still pass through the Sentinel spine.

```text
browser receipts / evidence refs
-> browser neural signals
-> signal graph / evidence blackboard
-> motor proposal artifact
-> AgentRuntime
-> OrganDispatcher
-> DelegatedActionGate
-> runtime_execution
-> browser organ
-> receipt
-> FinalGate
```

## Core Law

```text
Neurons think.
Neurons signal.
Neurons propose.
Neurons do not execute.
Neurons do not grant authority.
Neurons do not mutate policy.
Neurons do not unlock credentials.
Neurons do not bypass Gate.
Motor neurons emit proposal_artifacts only.
Only the Sentinel spine moves the world.
```

## Neuron Interface Standard V0

### Required Models

```text
NeuronId
NeuronKind
NeuronSignal
NeuronSignalRef
NeuronGraphEdge
NeuronActivationRecord
NeuronInputEnvelope
NeuronOutputEnvelope
NeuronSafetyBoundary
BrowserSignalGraph
BrowserEvidenceBlackboard
```

### Required Invariants

Every neuron output must carry these safety fields:

```text
data_not_instruction = true
authority_effect = "none"
execution_effect = "none"
can_execute = false
can_grant_authority = false
can_access_credentials = false
can_unlock_credentials = false
can_mutate_policy = false
can_create_delegated_lane = false
can_call_runtime_execution = false
can_call_organ_directly = false
```

No neuron may import or instantiate:

```text
runtime_execution
BrowserSessionManagerL5Live
BrowserFormSubmitSpecialAuthorityL6
BrowserLoginCredentialSessionBrokerL6
BrowserDownloadUploadQuarantineL6
BrowserArbitraryJSSandboxSpecialAuthorityL6
credential providers
```

### Signal Shape

```text
signal_id
mission_id
neuron_id
neuron_kind
source_signal_refs
source_evidence_refs
source_receipt_refs
payload_summary
payload_hash
risk_flags
confidence
created_at
data_not_instruction
authority_effect
execution_effect
```

Signals store summaries, hashes, and refs. They must not persist raw browser
private data, raw credentials, cookies, auth headers, raw prompts, hidden
reasoning, provider responses, or secret-like values.

## Browser Neural Cortex V0

V0 is split into perception and motor-proposal layers.

### Perception Neurons

```text
BrowserObservationNeuron
PageStateNeuron
TargetGroundingNeuron
EvidenceAuditorNeuron
```

Responsibilities:

- convert browser receipts and existing browser trace events into observation
  signals;
- summarize page state from DOM/AX/screenshot/network/console metadata refs;
- bind target candidates to source evidence refs;
- audit evidence quality, injection flags, contradiction flags, and missing
  evidence.

### Planning / Recovery / Motor Neurons

```text
IntentNeuron
RiskBoundaryNeuron
ActionPlannerNeuron
VerifierNeuron
FailureRecoveryNeuron
MemoryRecallNeuron
MotorProposalNeuron
```

Responsibilities:

- translate mission intent and page state into candidate next steps;
- detect auth walls, CAPTCHA, payment, KYC, credential, upload/download, and JS
  boundary risks;
- produce verification plans and recovery options;
- emit motor proposal artifacts only.

## Legacy Browser Cortex Harvest Plan

Existing code:

```text
sentinel/agent/browser/cortex.py
tests/test_agent_browser_cortex.py
docs/browser/BROWSER_CORTEX_INTEGRATION_REPORT.md
```

The existing `BrowserEvidenceInterpreter` is deterministic and already maps
browser trace events into:

```text
source confidence
hypothesis deltas
repair pressure
action recommendations
evidence chains
```

Harvest rule:

```text
Do not duplicate it.
Wrap it as LegacyBrowserEvidenceInterpreter.
Use it as an input adapter for BrowserObservationNeuron and EvidenceAuditorNeuron.
Keep its rule: browser evidence may influence reasoning, never authority.
```

## Browser Signal Graph / Evidence Blackboard

The blackboard is append-only for V0 and stores:

```text
signal refs
evidence refs
receipt refs
FinalGate certificate refs
target candidates
risk flags
verification results
recovery attempts
memory feedback refs
replan refs
```

Graph rules:

```text
append-only in-memory graph for V0
stable signal hash for every node
edge hash binds source signal -> derived signal
deterministic ordering
no deletion or mutation of prior nodes
```

## Motor Proposal Contract

`MotorProposalNeuron` output:

```text
proposal_artifact
organ_kind
action_level
target_ref
source_evidence_refs
required_authority
risk_flags
expected_receipt_type
verification_plan
```

Forbidden:

```text
direct organ execution
direct runtime_execution call
credential resolution
authority grant creation
mission envelope mutation
policy mutation
provider/backend/model override
```

## Memory Feedback Contract

Memory receives context, never authority:

```text
signals used
proposal emitted
gate decision
receipt refs
FinalGate certificate refs
failure/recovery signals
verified outcome
open risks
recommended next loop input
```

Memory feedback must not:

```text
grant authority
unlock credentials
approve future execution
turn confidence into permission
override provider/backend/model selection
```

## Deferred

```text
Browser Multi-Agent Operator Squad
Global Neural Fabric
generic browser login/upload/download/private session
arbitrary JS outside sandbox
API/channel/shell/desktop/payment execution
durable credential storage
provider fallback/AUTO routing
```

## Required Tests For V0

```text
test_neuron_signal_is_data_not_instruction
test_neuron_cannot_grant_authority
test_neuron_cannot_execute
test_neuron_cannot_access_credentials
test_signal_graph_is_append_only_and_hash_bound
test_browser_receipt_becomes_observation_signal
test_legacy_cortex_harvested_not_duplicated
test_no_raw_credentials_or_secret_persistence
test_motor_proposal_neuron_emits_proposal_artifact_only
test_motor_proposal_still_requires_dispatcher_gate_runtime
test_no_neural_module_imports_runtime_execution
test_no_neuron_directly_instantiates_browser_organs
```
