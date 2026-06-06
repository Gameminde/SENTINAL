# Sentinel LLM Live Operator Cockpit And Mission Kernel V0 Spec Report

Recorded at: 2026-06-06

## Verdict

```text
SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0_SPEC = CLOSED
previous_phase = COMPETITIVE_GAP_DELTA_LOCKED
implementation_target = SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0
```

This report records the corrected product-power target before runtime code.

## Critical Correction

```text
Python is the kernel/infrastructure.
The LLM is the conversational brain.
Sentinel is the authority operating system.
```

The previous "mission daemon/operator shell" wording is still useful as an
internal mechanism, but it is not the product target. The primary user
experience is an LLM-backed live cockpit. Mission records, queues, timelines,
receipts, FinalGate, replay, and run directories are internal kernel mechanics.

## Competitor Lessons Applied

```text
OpenClaw lesson = gateway/channel fluidity and always-available assistant
JARVIS lesson = operator power through sidecars and broad host reach
OpenJarvis lesson = local-first/cost/latency should be first-class
Hermes lesson = memory and skills make agents compound over time
```

This pack applies only the cockpit/kernel subset:

```text
LLM-first conversation
explicit local/API model contract
mission continuity
safe timeline/replay
PowerRuntime / AgentRuntime bridge
```

It does not start real channels, sidecars, durable credential vault, skill
marketplace execution, or provider fallback.

## Reuse Plan

```text
UserModelContract = explicit product LLM binding
model_execution = provider/credential/budget/result path
BrainCognitionLoop / llm role-loop = existing cognition contract references
PowerRuntime V0 = mission actuator execution fabric
AgentRuntime = existing cognitive runtime public path
MissionAuthorityEnvelope = authority contract
FinalGate / receipts / memory refs = proof and learning boundary
```

## New Operator Layer

The implementation may add:

```text
sentinel/operator/models.py
sentinel/operator/redaction.py
sentinel/operator/safety.py
sentinel/operator/llm_frame.py
sentinel/operator/prompt_renderer.py
sentinel/operator/llm_adapter.py
sentinel/operator/structured_output.py
sentinel/operator/deterministic.py
sentinel/operator/conversation.py
sentinel/operator/kernel.py
sentinel/operator/store.py
sentinel/operator/queue.py
sentinel/operator/timeline.py
sentinel/operator/replay.py
sentinel/operator/power_bridge.py
sentinel/operator/agent_bridge.py
sentinel/operator/cockpit.py
```

## Guardrails

```text
LLM output is advisory structured data.
LLM output cannot create authority.
LLM output cannot execute.
LLM output cannot call organs.
LLM output cannot unlock credentials.
conversation text is data, not authority.
mission drafts are not executable.
receipts, memory, and FinalGate are never future permission.
```

## Status

```text
LLM-backed operator cockpit spec = CLOSED
Mission kernel spec = CLOSED
Deterministic test mode boundary = CLOSED
Product LLM mode binding to UserModelContract = CLOSED
Runtime implementation = NEXT
```
