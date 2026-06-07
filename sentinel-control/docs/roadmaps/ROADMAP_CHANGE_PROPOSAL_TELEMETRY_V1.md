# Roadmap Change Proposal - Telemetry V1

Status: `LOCKED`
Date: 2026-06-07

## Decision

Insert:

```text
OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
```

before:

```text
MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

This is a docs-only roadmap change. It does not implement telemetry runtime and
does not start Worker Fleet.

## Baseline

```text
current_phase = DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1_LOCKED
previous_phase = PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED
current_next_phase = MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
baseline_head = b83882b7f9b8d59714e9161e5955bfa3456e85d9
roadmap_doctrine = product power under provable authority
```

## Why Telemetry Moves Before Worker Fleet

Worker Fleet will add parallel workers, child authority envelopes, concurrent
budgets, merge and reject flows, worker failures, and more complicated recovery.
Without a unified telemetry layer first, Sentinel would scale concurrency before
it can reliably measure, debug, compare, and improve that concurrency.

Sentinel already has multiple proof and event surfaces:

```text
EventBus
MissionKernel timeline
MissionRunStore
DurableWorkflowStore
workflow checkpoints
PowerRuntime timeline
AgentRuntime result refs
Persistent Semantic Memory refs
receipts
FinalGate certificates
browser neural ledger
operator replay
```

Those surfaces are valuable, but they are fragmented. The inserted telemetry
phase must unify them into one Sentinel-native measurement spine instead of
creating a parallel telemetry universe.

## Corrected Sequence

```text
1. PERSISTENT_SEMANTIC_MEMORY_V1
2. DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
3. OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
4. MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
5. PRODUCTION_MISSION_DAEMON_AND_PROACTIVE_SCHEDULER_V1
6. MODEL_AMPLIFICATION_EXECUTION_HARNESS_V1
7. GOVERNED_SKILL_AND_PROCEDURE_FABRIC_V1
8. LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1
9. REAL_CHANNEL_ADAPTERS_V1
10. PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1
11. REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
12. DURABLE_CREDENTIAL_VAULT_AND_SESSION_BROKER_V1
13. ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1
14. PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1
15. SECURITY_TESTING_SPECIAL_AUTHORITY_V1
16. ELECTRONICS_DEVICE_CONTROL_AND_IOT_ORGAN_V1
17. BUSINESS_AUTOMATION_PLAYBOOKS_AND_MARKETPLACE_V1
18. SENTINEL_PLATFORM_APP_AND_OPERATOR_CLOUD_V1
19. FINAL_CAPABILITY_GAUNTLET_AND_RELEASE_CERTIFICATION
```

## Telemetry Doctrine

Telemetry is mandatory for Certified Sentinel Mode.

Telemetry is not authority. Telemetry does not execute, grant permission, unlock
credentials, store raw secrets, store raw credentials, store raw prompts, store
raw provider responses, store raw reasoning, or become future permission.

Telemetry must be:

```text
append-only
tamper-resistant
redacted
local-first
hash-bound
non-bypassable by agents/organs/workers/skills/LLM output
operator-visible
```

The operator must know telemetry exists. It must not be hidden from the user.
Agents, workers, organs, skills, memory, and LLM output must not be able to
disable, rewrite, or bypass it.

## Certified Sentinel Mode Rule

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

## Required Telemetry Domains

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

## Required Metrics

```text
mission completion rate
autonomous useful minutes
time to useful result
operator interruption count
organ latency
step latency
workflow checkpoint latency
replan success rate
recovery success rate
Gate reject count
FinalGate reject count
kill switch latency
revocation latency
memory recall count
memory recall utility
memory stale/contradiction hit count
LLM schema failure rate
provider/backend/model selected
token usage
cost per completed mission
receipt completeness
timeline/replay completeness
worker parallel efficiency
future worker conflict rate
```

## Required Events

```text
mission_started
mission_completed
mission_failed
mission_killed
mission_paused
mission_resumed
workflow_checkpoint_created
workflow_checkpoint_failed
workflow_resumed
replan_candidate_created
replan_executed
replan_escalated
replan_rejected
step_started
step_completed
step_failed
gate_allowed
gate_blocked
finalgate_passed
finalgate_failed
organ_called
organ_failed
model_call_started
model_call_completed
model_schema_invalid
memory_recall_used
memory_recall_rejected
secret_redaction_hit
credential_access_denied
kill_switch_triggered
revocation_detected
```

## AgentLab Mechanisms Harvested

AgentLab is source-only reference material. No vendor runtime, vendor code,
dependency install, service connection, or telemetry vendor bridge is approved.

Mechanisms harvested for the future Sentinel-native rewrite:

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

## Non-Scope

This lock does not implement:

```text
telemetry runtime
worker fleet
production daemon
credentials/payment/trading/desktop/channels/voice
provider fallback/AUTO routing
vendor runtime integration
telemetry vendor bridge
new execution surface
```

## Next Implementation Prompt Title

```text
OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1
```
