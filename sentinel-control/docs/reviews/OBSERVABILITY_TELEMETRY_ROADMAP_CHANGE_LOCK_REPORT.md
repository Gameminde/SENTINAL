# Observability Telemetry Roadmap Change Lock Report

Status: `LOCKED`
Date: 2026-06-07

## Scope

This is a docs-only roadmap change. It inserts:

```text
OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
```

before:

```text
MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

No runtime code was changed. No telemetry runtime was implemented. Worker Fleet
was not started.

## Why Telemetry Was Inserted

Sentinel now has a live LLM cockpit, MissionKernel, persistent semantic memory,
durable workflow, automatic replan, PowerRuntime, AgentRuntime bridge, receipts,
FinalGate, timeline, and replay. The measurement spine is still split across
EventBus, MissionKernel timelines, PowerRuntime timelines, workflow checkpoints,
browser ledgers, receipt refs, FinalGate refs, and memory refs.

Worker Fleet adds parallelism, child authority envelopes, concurrent budgets,
worker failures, merge/reject paths, and conflict handling. Building those
without unified telemetry would make Sentinel harder to debug and harder to
measure precisely at the moment it becomes more concurrent.

## What Changed In The Master Roadmap

The master sequence changed from:

```text
1. PERSISTENT_SEMANTIC_MEMORY_V1
2. DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
3. MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

to:

```text
1. PERSISTENT_SEMANTIC_MEMORY_V1
2. DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
3. OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
4. MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

All later phases shift by one slot. The next implementation phase is now
Telemetry V1, not Worker Fleet.

## Certified Mode Telemetry Rule

```text
Certified Sentinel Mode requires local telemetry.
```

If telemetry is unavailable, corrupted, disabled, or tampered with:

```text
certified_mode = false
sensitive execution = fail_closed
worker fleet = blocked
credential/payment/trading/desktop/device phases = blocked
release certification = invalid
```

Development mode may exist later, but it is not Certified Sentinel Mode and
must not unlock dangerous powers.

## What Telemetry Must Never Do

Telemetry must never:

```text
create authority
execute actions
grant permission
unlock credentials
store raw secrets
store raw credentials
store raw prompts
store raw provider responses
store raw reasoning
become future permission
hide itself from the operator
be disabled, rewritten, or bypassed by agents/organs/workers/skills/LLM output
```

Telemetry must be append-only, tamper-resistant, redacted, local-first,
hash-bound, non-bypassable by runtime participants, and operator-visible.

## AgentLab Mechanisms Harvested

AgentLab was used as source-only reference. No vendor runtime was integrated and
no vendor code was copied.

Harvested mechanisms:

```text
Microsoft Agent Framework / JARVIS:
  durable lifecycle observability, task state visibility, restart/checkpoint diagnostics

Hermes / Letta:
  memory utility and recall quality measurement

gptme / Agent Zero:
  background mission status and operator-facing logs

oh-my-pi:
  minimized structured results, hash-anchored execution state, tool output economy

OpenClaw / DeerFlow:
  multi-agent and workflow status visibility
```

## Future Telemetry Domains

```text
OperationalTelemetry
AuthorityTelemetry
LLMTelemetry
OrganTelemetry
MemoryTelemetry
WorkflowTelemetry
ReplanTelemetry
WorkerTelemetry
CostTelemetry
SafetyTelemetry
ProductPowerTelemetry
```

## What Remains Next

```text
next_phase = OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
```

Worker Fleet remains next after Telemetry V1:

```text
MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1 = NOT_STARTED / after telemetry
```

## What Remains Not Started

```text
telemetry runtime
worker fleet
production daemon
provider fallback/AUTO
vendor runtime bridge
credentials/payment/trading/desktop/channels/voice
telemetry vendor bridge
new execution surface
```

## Files Changed

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/roadmaps/ROADMAP_CHANGE_PROPOSAL_TELEMETRY_V1.md
sentinel-control/docs/reviews/OBSERVABILITY_TELEMETRY_ROADMAP_CHANGE_LOCK_REPORT.md
```

## Checks Run

```text
git status --short --untracked-files=all
git diff --check
git show --check HEAD
git diff --cached --check
```

Runtime tests are not required because this lock is docs-only.
