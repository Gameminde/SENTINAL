# Motor Neuron To Organ Dispatch Lock Report

Status: LOCKED

Date: 2026-06-02

## Current State

```text
MotorProposalNeuron = CLOSED
MotorProposalArtifact = CLOSED
Motor proposal to AgentRuntime proposal path = CLOSED
Direct neuron execution = FORBIDDEN
Browser neural memory feedback specialization = NOT_STARTED
Durable receipt ledger = NOT_STARTED
Browser squad = NOT_STARTED
```

## Implementation Summary

This lock adds explicit default-off conversion from
`MotorProposalArtifact` to a normal browser `proposal_artifact` accepted by the
existing Sentinel spine.

```text
MotorProposalArtifact
-> motor_proposal_artifact_to_browser_step_candidate
-> BrainCognitionResult.proposal_artifacts extraction
-> AgentRuntime ORGAN_DISPATCHING
-> OrganDispatcher
-> DelegatedActionGate
-> runtime_execution
-> BrowserSessionManagerL5Live
-> receipt
-> FinalGate
-> memory feedback
-> replan-ready packet
```

## Default-Off Proof

The new config flag defaults off:

```text
browser_neural_motor_proposal_source_enabled = false
```

When disabled, motor proposals are ignored as execution candidates and the
dispatch result remains `NO_CANDIDATES`.

## Boundaries Preserved

```text
neurons do not execute
neurons do not call browser organs directly
neurons do not call the runtime execution layer directly
neurons do not grant authority
neurons do not unlock credentials
dispatcher/gate/runtime still own execution
receipt + FinalGate still required
```

## Tests

```text
python -m pytest tests/test_motor_neuron_to_organ_dispatch_lock.py -q
```

Result:

```text
2 passed
```

## Next Pack

```text
BROWSER_NEURAL_MEMORY_FEEDBACK_LOCK
```
