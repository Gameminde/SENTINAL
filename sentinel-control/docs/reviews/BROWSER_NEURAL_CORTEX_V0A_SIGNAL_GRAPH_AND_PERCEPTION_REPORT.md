# Browser Neural Cortex V0A Signal Graph And Perception Report

Status: LOCKED

Date: 2026-06-02

## Current State

```text
Browser Neural Operator Cortex spec = CLOSED
Signal graph and perception neurons = CLOSED
Motor proposal neurons = NOT_STARTED
Dispatcher integration = NOT_STARTED
Browser squad = NOT_STARTED
Global neural fabric = NOT_STARTED
```

## Files Added

```text
sentinel/agent/browser/neural/__init__.py
sentinel/agent/browser/neural/models.py
sentinel/agent/browser/neural/signal_graph.py
sentinel/agent/browser/neural/blackboard.py
sentinel/agent/browser/neural/perception.py
tests/test_browser_neural_cortex_v0a_signal_graph.py
```

## Implemented

```text
NeuronKind
NeuronSafetyBoundary
NeuronSignal
NeuronGraphEdge
NeuronInputEnvelope
NeuronOutputEnvelope
NeuronActivationRecord
BrowserSignalGraph
BrowserEvidenceBlackboard
LegacyBrowserEvidenceInterpreterAdapter
BrowserObservationNeuron
PageStateNeuron
TargetGroundingNeuron
EvidenceAuditorNeuron
```

## Boundaries Preserved

```text
neurons do not execute
neurons do not grant authority
neurons do not access credentials
neurons do not unlock credentials
neurons do not mutate policy
neurons do not create delegated lanes
neurons do not call organs directly
neurons do not directly call the runtime execution layer
```

## Legacy Cortex Harvest

The existing deterministic `BrowserEvidenceInterpreter` is wrapped by
`LegacyBrowserEvidenceInterpreterAdapter`. V0A does not duplicate the old
cortex; it makes it available as a harvested evidence interpreter for later
neural perception flows.

## Data Safety

Signals store:

```text
refs
hashes
safe summaries
sanitized payloads
risk flags
```

Signals do not persist raw bearer tokens, raw credential values, raw cookies,
raw provider responses, raw prompts, or hidden reasoning.

## Tests

```text
python -m pytest tests/test_browser_neural_cortex_v0a_signal_graph.py -q
```

Result:

```text
8 passed
```

## Next Pack

```text
BROWSER_NEURAL_CORTEX_V0B_MOTOR_PROPOSAL_TO_DISPATCH
```
