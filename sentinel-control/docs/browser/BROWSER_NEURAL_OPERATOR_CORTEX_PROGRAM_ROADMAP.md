# Browser Neural Operator Cortex Program Roadmap

Status: active browser neural program roadmap

Date: 2026-06-02

## Current Program Truth

```text
current_phase = BROWSER_RUNTIME_FAILURE_AND_CONCURRENCY_HARDENING_LOCKED
next_phase = BROWSER_NEURAL_OPERATOR_CORTEX_SPEC
```

The browser L5/L6 stack is runtime-connected. The next layer must be a neural
signal/motor cortex before any browser squad or global neural fabric.

## Phase 0 - Runtime Hardening And State Truth Repair

Status: CLOSED

Completed:

```text
browser session cache race hardening
L5/L6 session continuity hardening
governed browser executor failure result
Gate priority hardening
candidate correlation hardening
state truth repair to point next phase at Cortex Spec
```

## Phase 1 - Browser Neural Operator Cortex Spec

Status: CURRENT

Deliverables:

```text
BROWSER_NEURAL_OPERATOR_CORTEX_SPEC.md
BROWSER_NEURAL_OPERATOR_CORTEX_PROGRAM_ROADMAP.md
BROWSER_NEURAL_OPERATOR_CORTEX_SPEC_REPORT.md
```

No runtime code. No new execution power.

## Phase 2 - Signal Graph And Perception Neurons

Target pack:

```text
BROWSER_NEURAL_CORTEX_V0A_SIGNAL_GRAPH_AND_PERCEPTION
```

Likely files:

```text
sentinel/agent/browser/neural/__init__.py
sentinel/agent/browser/neural/models.py
sentinel/agent/browser/neural/signal_graph.py
sentinel/agent/browser/neural/blackboard.py
sentinel/agent/browser/neural/perception.py
tests/test_browser_neural_cortex_v0a_signal_graph.py
```

Neurons:

```text
BrowserObservationNeuron
PageStateNeuron
TargetGroundingNeuron
EvidenceAuditorNeuron
```

## Phase 3 - Planning And Motor Proposal Neurons

Target pack:

```text
BROWSER_NEURAL_CORTEX_V0B_MOTOR_PROPOSAL_TO_DISPATCH
```

Likely files:

```text
sentinel/agent/browser/neural/planning.py
sentinel/agent/browser/neural/risk.py
sentinel/agent/browser/neural/recovery.py
sentinel/agent/browser/neural/motor_proposal.py
tests/test_browser_neural_cortex_v0b_motor_proposal.py
```

Neurons:

```text
IntentNeuron
RiskBoundaryNeuron
ActionPlannerNeuron
VerifierNeuron
FailureRecoveryNeuron
MemoryRecallNeuron
MotorProposalNeuron
```

## Phase 4 - Motor Proposal To Organ Dispatch Lock

Target pack:

```text
MOTOR_NEURON_TO_ORGAN_DISPATCH_LOCK
```

Goal:

```text
Browser neural cortex emits proposal_artifacts.
AgentRuntime dispatches through existing OrganDispatcher/Gate/runtime path.
No neuron executes directly.
```

## Phase 5 - Browser Neural Memory Feedback Lock

Target pack:

```text
BROWSER_NEURAL_MEMORY_FEEDBACK_LOCK
```

Goal:

```text
signals, proposals, gate decisions, receipts, FinalGate certificates, recovery
attempts, and verifier outcomes feed memory as context only.
```

## Phase 6 - Durable Receipt Ledger Foundation

Target pack:

```text
DURABLE_RECEIPT_LEDGER_FOUNDATION
```

Goal:

```text
append-only local foundation for neural browser trace replay before squad.
```

Required shape:

```text
workflow_id
run_id
call_id
neuron_signal_id
receipt_id
prev_hash
event_hash
created_at
actor_or_neuron_id
state
refs
```

## Phase 7 - Browser Multi-Agent Operator Squad

Target pack:

```text
BROWSER_MULTI_AGENT_OPERATOR_SQUAD_LOCK
```

Roles:

```text
Scout
Planner
Operator
Verifier
Recovery
Boundary
EvidenceAuditor
```

Each role is a view over neurons/signals, not an authority source.

## Phase 8 - Browser Neural Gauntlet

Target pack:

```text
BROWSER_NEURAL_GAUNTLET_LOCK
```

Scenarios:

```text
one-page task recovery
multi-step browser mission with verifier/recovery
stale selector recovery
modal/overlay recovery
redirect flow
auth wall detection
payment boundary detection
download quarantine path
JS sandbox path
invented evidence rejection
memory-not-authority regression
```

## Phase 9 - Self Audit And Remediation

Audit axes:

```text
neuron authority drift
direct organ imports
runtime_execution imports inside neural modules
raw credential/browser data persistence
signal graph hash integrity
ledger replay
memory-as-authority
confidence-as-permission
squad role privilege escalation
docs overclaim
stale CURRENT_STATE_LOCK
```

## Final Expected State

```text
current_phase = BROWSER_NEURAL_GAUNTLET_LOCKED
next_phase = external audit / next Browser live backend decision
```

Not claimed:

```text
Global Neural Fabric complete
full multi-agent OS complete
live DevTools CDP/MCP complete
payment/account authority live
credential durable storage complete
shell/API/channel/desktop complete
```
