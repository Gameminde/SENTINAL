# Browser Neural Operator Cortex Spec Report

Status: SPEC LOCK / no runtime code

Date: 2026-06-02

## Files Read

```text
sentinel-control/services/sentinel-core/sentinel/agent/browser/cortex.py
sentinel-control/services/sentinel-core/tests/test_agent_browser_cortex.py
sentinel-control/docs/browser/BROWSER_CORTEX_INTEGRATION_REPORT.md
sentinel-control/docs/brain/P5A_MULTI_AGENT_BRAIN_ARCHITECTURE.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md
```

## Current State

```text
Browser L5/L6 runtime stack = CLOSED
Browser runtime hardening = CLOSED
Browser Neural Operator Cortex = SPEC ONLY
Browser Multi-Agent Operator Squad = NOT_STARTED
Global Neural Fabric = NOT_STARTED
```

## Design Verdict

Browser Multi-Agent Operator Squad must not be the next implementation layer.
The next layer is Browser Neural Operator Cortex: a signal graph and motor
proposal system that lets browser intelligence become stronger without letting
neurons execute or grant authority.

## Legacy Cortex Finding

Existing code already contains a deterministic browser cortex:

```text
BrowserEvidenceInterpreter
```

It maps browser events into:

```text
confidence scores
hypothesis updates
repair pressure
action recommendations
evidence chains
```

Decision:

```text
HARVEST / WRAP
```

It becomes `LegacyBrowserEvidenceInterpreter` or an adapter feeding
`BrowserObservationNeuron` and `EvidenceAuditorNeuron`. It must not be
duplicated.

## Neuron Law

```text
Neurons think.
Neurons signal.
Neurons propose.
Neurons do not execute.
Neurons do not grant authority.
Neurons do not mutate policy.
Neurons do not unlock credentials.
Neurons do not bypass Gate.
```

## Spec Deliverables

Created:

```text
sentinel-control/docs/browser/BROWSER_NEURAL_OPERATOR_CORTEX_SPEC.md
sentinel-control/docs/browser/BROWSER_NEURAL_OPERATOR_CORTEX_PROGRAM_ROADMAP.md
sentinel-control/docs/reviews/BROWSER_NEURAL_OPERATOR_CORTEX_SPEC_REPORT.md
```

## What Remains Not Started

```text
neural runtime implementation
signal graph code
motor proposal integration
memory feedback integration
durable receipt ledger
browser squad
global neural fabric
generic browser login/upload/download/private session
arbitrary JS outside sandbox
API/channel/shell/desktop/payment execution
credential durable storage
provider fallback/AUTO routing
```

## Recommended Next Pack

```text
BROWSER_NEURAL_CORTEX_V0A_SIGNAL_GRAPH_AND_PERCEPTION
```

This should implement only the signal graph, blackboard, and perception neurons.
No motor dispatch integration yet.
