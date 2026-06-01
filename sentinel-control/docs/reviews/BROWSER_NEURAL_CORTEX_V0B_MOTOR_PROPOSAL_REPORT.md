# Browser Neural Cortex V0B Motor Proposal Report

Status: LOCKED

Date: 2026-06-02

## Current State

```text
Signal graph and perception neurons = CLOSED
Planning/risk/recovery/motor proposal neurons = CLOSED
Motor proposal integration through AgentRuntime = NOT_STARTED
Browser squad = NOT_STARTED
Global neural fabric = NOT_STARTED
```

## Files Added

```text
sentinel/agent/browser/neural/planning.py
sentinel/agent/browser/neural/risk.py
sentinel/agent/browser/neural/recovery.py
sentinel/agent/browser/neural/motor_proposal.py
tests/test_browser_neural_cortex_v0b_motor_proposal.py
```

## Implemented

```text
IntentNeuron
RiskBoundaryNeuron
ActionPlannerNeuron
VerifierNeuron
FailureRecoveryNeuron
MemoryRecallNeuron
MotorProposalNeuron
MotorProposalArtifact
MotorNeuronOutputEnvelope
```

## Motor Proposal Boundary

`MotorProposalNeuron` emits proposal artifacts only.

```text
dispatch_required = true
can_execute = false
authority_effect = "none"
execution_effect = "none"
```

It does not directly call the runtime execution layer, browser organs, browser
session managers, or credential providers.

## Tests

```text
python -m pytest tests/test_browser_neural_cortex_v0b_motor_proposal.py -q
```

Result:

```text
6 passed
```

## Next Pack

```text
MOTOR_NEURON_TO_ORGAN_DISPATCH_LOCK
```

Goal: let `AgentRuntime` consume motor proposal artifacts as proposal artifacts
only, then route them through `OrganDispatcher`, `DelegatedActionGate`, runtime
execution, receipts, FinalGate, memory feedback, and replan packet.
