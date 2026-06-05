# Power Actuator Fabric Wave 1 Spec Report

Recorded at: 2026-06-05

## Baseline

```text
baseline_head = 26025a7750be822709aa06356e98d1ebebc4f4bd
baseline_phase = BROWSER_OPERATING_SUBSYSTEM_HARDENED_LIVE_BACKEND_LOCKED
new_phase = POWER_ACTUATOR_FABRIC_WAVE_1_SPEC_LOCKED
next_phase = SENTINEL_POWER_RUNTIME_V0
```

Local and remote `main` were verified to point at the browser hardened live
backend commit before this spec work began.

## AgentLab Evidence Read

This spec was derived from AgentLab as a power-pattern source, not a vendor
runtime dependency.

Files read:

```text
agent-lab/audits/SUPERPOWER_EXTRACTION_TABLE.md
agent-lab/audits/SENTINEL_SUPER_AGENT_BLUEPRINT.md
agent-lab/audits/CAPABILITY_MATRIX.md
agent-lab/sentinel_integration_notes/SENTINEL_RUNTIME_BLUEPRINT.md
agent-lab/sentinel_integration_notes/openclaw_to_sentinel.md
agent-lab/sentinel_integration_notes/jarvis_to_sentinel.md
agent-lab/sentinel_integration_notes/openjarvis_to_sentinel.md
```

Harvested patterns:

```text
OpenClaw = tool/channel/plugin breadth, exec approval, skill scanner
JARVIS = sidecar permission lifecycle, approval/audit, desktop risk classes
OpenJarvis = cost/hardware routing, trace-backed improvement proposals
Hermes = context quarantine, memory compression, hook pipeline
AgentMemory = structured memory lessons
TradingAgents = domain-specialized operator and risk-ledger lessons
Chrome DevTools/CloakBrowser = browser backend intelligence
```

Rejected:

```text
vendor runtime imports
ambient plugin authority
memory-as-authority
direct tool calls from Brain
prompt templates as executable policy
uncontrolled MCP/WebMCP
provider fallback/AUTO routing
```

## Models Defined

The spec defines:

```text
PowerActuatorContract
PowerActuatorRequest
PowerActuatorReceipt
PowerActuatorFinalGateCertificate
PowerActuatorRiskProfile
PowerActuatorCapabilityLevel
PowerActuatorPromotionState
PowerActuatorKillSwitchBinding
PowerActuatorRollbackPolicy
```

## Wave 1 Families

```text
browser
shell_sandbox
code_execution
external_api
channel
workspace
credential_ref
```

## Status Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Power Actuator Fabric Wave 1 spec | CLOSED | `POWER_ACTUATOR_FABRIC_WAVE_1_SPEC.md` | Spec only; runtime starts next. |
| Browser as actuator family | CLOSED | Existing Browser Operating Subsystem locks; spec maps it into fabric. | New backend helpers still need AgentRuntime promotion. |
| Workspace as actuator family | CLOSED | Existing L2/L3 contracts referenced. | PowerRuntime step wrapper starts next. |
| Shell sandbox design | CLOSED | Spec defines allowlist, denylist, receipts, FinalGate. | Organ implementation not started in this phase. |
| Code execution design | CLOSED | Spec constrains code execution through sandbox commands. | No arbitrary interpreter organ yet. |
| External API design | CLOSED | Spec defines read/write authority split. | Organ implementation not started. |
| Channel design | CLOSED | Spec defines draft/send split. | Real channel provider not started. |
| Credential ref semantics | CLOSED | Metadata-only refs/proofs included. | Durable vault remains not started. |
| Vendor runtime reuse | REJECTED | Spec says rewrite only. | None. |

## Non-Scope Preserved

```text
desktop sidecar = NOT_STARTED
durable credential vault = NOT_STARTED
real payment/spend/trading provider = NOT_STARTED
generic private browser sessions = NOT_STARTED
uncontrolled MCP/WebMCP = NOT_STARTED
provider fallback/AUTO routing = NOT_APPROVED
plugin marketplace install = NOT_STARTED
```

## Next Pack

```text
SENTINEL_POWER_RUNTIME_V0
```

Goal: create the first real mission power runtime layer with graph steps,
dependencies, retry budget, kill switch checks, receipt refs, FinalGate refs,
memory feedback refs, and a timeline.
