# Local Model Hardware And Cost Router V1 Lock Report

Date: 2026-06-08

## Verdict

`LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1` is locked as a Sentinel-native local
runtime foundation.

```text
current_phase = LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1_LOCKED
previous_phase = GOVERNED_SKILL_AND_PROCEDURE_FABRIC_V1_LOCKED
next_phase = REAL_CHANNEL_ADAPTERS_V1
roadmap_doctrine = product power under provable authority
```

The router is decision support and explicit binding data. It is not authority,
not execution, not provider fallback/AUTO, not a provider runtime, and not a
new actuator family.

## Sentinel Components Reused

```text
UserModelContract = reused as the only executable model identity contract
ProviderCatalog = reused for descriptor/candidate normalization
ModelCostProfile / ModelCapabilityProfile = reused for cost/context/capability estimates
MissionKernel / MissionRunStore = reused for mission-owned persistence and timeline events
TelemetryKernel / TelemetryStore = reused for route events and product-power metrics
operator redaction/safety utilities = reused for secret/raw prompt/provider response/reasoning blocking
ModelAmplificationHarness / SkillFabric / WorkerFleet / Daemon contracts = treated as context only, never hidden route authority
MissionAuthorityEnvelope / Gate / receipts / FinalGate / replay doctrine = preserved
```

No parallel mission store, provider registry, telemetry store, authority path,
memory system, cockpit, worker runtime, or model execution runtime was created.

## AgentLab Mechanisms Harvested

AgentLab was inspected as source-only reference. No vendor code, runtime,
dependency, service connection, or bridge was copied or installed.

```text
OpenJarvis = local model and hardware awareness, offline/local preference patterns
gptme = explicit operator-facing model/session configuration and cost visibility
JARVIS / Microsoft Agent Framework = observable runtime capability metadata and diagnostics
oh-my-pi = hardware-aware execution discipline and minimized route evidence
Hermes / DeerFlow = workflow-aware model-policy thinking
```

All mechanisms were rewritten Sentinel-native as typed route candidates,
policies, simulation scores, receipts, telemetry, and replay records.

## Runtime Added

```text
sentinel/operator/model_router_models.py
sentinel/operator/model_router.py
sentinel/operator/model_router_replay.py
```

The runtime supports:

```text
ModelRouterConfig
ModelCandidate
ModelCandidateSource
ModelRuntimeKind
ModelBackendKind
ModelCapabilityProfile / ModelCostProfile reuse
ModelHardwareProfile
HardwareInventorySnapshot
HardwareProbeResult
RuntimeAvailabilityProbe
ModelLatencyProfile
ModelQualityProfile
ModelPrivacyProfile
ModelEnergyProfile
ModelContextWindowProfile
RoutePolicy
RouteObjective
RouteConstraint
RouteSimulationRequest
RouteSimulationResult
RouteCandidateScore
RouteDecision
RouteDecisionReceipt
RouteRejectionReason
RouteApprovalRecord
RouteExecutionBinding
RouteTelemetrySummary
RouteReplayView
ModelRouterRuntime
ModelRouterReplayBuilder
```

## Candidate Types Supported

```text
explicit UserModelContract candidates = CLOSED
existing ProviderCatalog candidates = CLOSED / descriptor candidates
ollama descriptors = CLOSED
llama.cpp descriptors = CLOSED
vLLM descriptors = CLOSED
SGLang descriptors = CLOSED
openai-compatible API descriptors = CLOSED / descriptor only
existing cataloged provider descriptors = CLOSED
```

Descriptor does not mean executable backend. Candidate does not mean selected
model. Simulation does not execute. Recommendation does not grant permission.

## Hardware And Runtime Probe Behavior

Hardware snapshots are local and read-only:

```text
platform/system metadata
CPU count
RAM estimate where safely available
machine/python runtime metadata
processor hash, not raw processor text
```

Runtime probes are deliberately narrow:

```text
explicit loopback local endpoint socket check only
no remote provider call
no network scan
no credential/provider-key probe
no runtime install
no model download
no model server start
no local runtime config mutation
```

If safe probing is not possible, the result is `UNKNOWN` or `UNAVAILABLE` with
a safe reason.

## Route Policy Behavior

Implemented policy dimensions:

```text
quality_floor
max_estimated_cost
max_estimated_latency
privacy_requirement
local_only
cloud_allowed
hardware_requirement
context_window_requirement
energy_preference
reliability_requirement
operator_confirmation_required
allowed_provider_ids / allowed_backend_ids / allowed_model_ids
blocked_provider_ids / blocked_backend_ids / blocked_model_ids
```

Policy is data only. If no candidate satisfies policy, the decision is rejected
with reasons. Policy does not create authority.

## Route Receipt Behavior

Route receipts are hash-bound and persist safe metadata only:

```text
candidate ids
policy hash
simulation hash
selected candidate id
rejection reasons
estimated cost / latency / privacy / hardware / context summaries
operator approval ref where present
UserModelContract binding hash where present
telemetry refs
```

Blocked from receipt persistence:

```text
provider keys
raw prompts
raw provider responses
raw reasoning
raw credentials
secret-like values
unredacted endpoint secrets
```

Route receipts are evidence only and cannot become future permission.

## Explicit UserModelContract Binding Behavior

Binding requires exact selected explicit identity:

```text
selected_provider_id
selected_backend_id
selected_model_id
```

If operator confirmation is required, `RouteApprovalRecord` must be present and
hash-valid. Non-operator approval sources such as memory, skill, worker,
daemon, scheduler, or harness are rejected. If execution later fails or a model
is unavailable, Sentinel must fail closed or produce a new route proposal; it
must not fallback silently.

## Telemetry And Metrics

Added telemetry surface:

```text
TelemetrySourceSurface.MODEL_ROUTER
```

Added events:

```text
model_router_candidate_registered
model_router_candidate_rejected
model_router_hardware_snapshot_created
model_router_runtime_probe_started
model_router_runtime_probe_completed
model_router_simulation_started
model_router_simulation_completed
model_router_decision_created
model_router_decision_rejected
model_router_approval_recorded
model_router_binding_created
model_router_binding_rejected
model_router_fallback_blocked
model_router_policy_rejected
```

Added metrics:

```text
model_router_candidate_count
model_router_candidate_rejection_count
model_router_estimated_cost_delta
model_router_estimated_latency_delta
model_router_context_fit_score
model_router_hardware_fit_score
model_router_privacy_score
model_router_quality_score
model_router_route_approval_rate
model_router_fallback_block_count
model_router_policy_reject_count
```

Telemetry remains data only. It cannot execute, grant permission, unlock
credentials, switch providers, or become future permission.

## Replay Behavior

`ModelRouterReplayBuilder` reconstructs:

```text
candidate list
hardware snapshot
runtime probe summaries
route policy
route simulation
candidate scores
rejection reasons
route decision receipt
approval record
binding record
telemetry refs
final selected explicit UserModelContract when binding exists
```

Replay does not re-execute model calls, provider calls, probes, downloads, model
server actions, or local runtime mutations.

## Authority And Model-Contract Review

```text
router-as-authority = BLOCKED
route receipt as future permission = BLOCKED
memory/skill/worker/daemon/scheduler/harness hidden switch = BLOCKED
provider/backend/model override = BLOCKED
provider fallback/AUTO = NOT_APPROVED
provider-native tools = BLOCKED
provider key discovery/persistence = BLOCKED
raw prompt/provider response/reasoning persistence = BLOCKED
new actuator family = NOT_STARTED
vendor runtime = NOT_INTEGRATED
```

The router only proposes, scores, rejects, receipts, explains, and binds an
explicit `UserModelContract` through existing governed paths.

## CodeRabbit Advisory Review

```text
CodeRabbit used: no
review source: unavailable in this environment
findings summary: CodeRabbit plugin/tooling was not available in the active plugin/tool list.
fixes applied: none from CodeRabbit
deferred/rejected findings: not applicable
authority note: CodeRabbit did not become authority and did not replace Sentinel tests or audit.
```

Manual exhaustive audit was performed instead.

## Exhaustive Audit Findings

| Severity | Finding | File / Surface | Decision | Fix Or Rationale | Remaining Limits |
| --- | --- | --- | --- | --- | --- |
| P1 | Local catalog endpoints were treated as explicit probes, causing local contracts to fail closed when no runtime server was running. | `model_router.py` | accepted_and_fixed | Catalog/contract candidates no longer carry executable endpoint probes; only explicit descriptors are probed. | V1 does not manage model servers. |
| P2 | Local latency estimate defaulted to remote unknown and over-rejected local candidates under tight latency policy. | `model_router.py` | accepted_and_fixed | Local catalog candidates use local metadata latency estimate. | Estimate is heuristic until real measurements exist. |
| P2 | Replay test expected final selected contract before explicit binding. | `test_local_model_hardware_and_cost_router_v1.py` | accepted_and_fixed | Test now creates `RouteExecutionBinding` before expecting final selected contract in replay. | Decisions without binding replay as decisions, not final contracts. |
| Info | Fallback/AUTO strings exist in tests/docs as blocked-boundary assertions. | modified files | accepted_with_rationale | Occurrences are negative tests and doctrine, not executable fallback. | Continue scanning future model work. |
| Info | CodeRabbit unavailable. | environment | accepted_with_rationale | Manual audit and regression suite used. | Optional advisory only if available later. |

No open P0, P1, or serious P2 findings remain in this lock.

## Honest V1 Limits

```text
router is not a model execution runtime
router is not automatic failover
router does not download models
router does not start or manage model servers
router does not probe provider keys
router does not call external providers
router does not add local/cloud live switching
router does not add provider-native tools
router does not add a credential vault, channels, desktop, voice, payment, or new actuators
hardware and latency/quality estimates remain heuristic metadata until later measured-runtime phases
```

## Tests And Checks

Completed before lock:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_local_model_hardware_and_cost_router_v1.py -q
result: 17 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_governed_skill_and_procedure_fabric_v1.py sentinel-control/services/sentinel-core/tests/test_model_amplification_execution_harness_v1.py sentinel-control/services/sentinel-core/tests/test_production_mission_daemon_and_scheduler_v1.py sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_and_automatic_replan_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py -q
result: passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_power_runtime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_sentinel_power_runtime_v0.py sentinel-control/services/sentinel-core/tests/test_delegated_action_gate_model_v0.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py sentinel-control/services/sentinel-core/tests/test_agent_core_final_gate.py sentinel-control/services/sentinel-core/tests/test_agent_event_bus.py sentinel-control/services/sentinel-core/tests/test_agent_evidence_chain.py -q
result: passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_gauntlet_v1.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_models_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_flow_v0.py sentinel-control/services/sentinel-core/tests/test_llm_operator_model_client_v0.py sentinel-control/services/sentinel-core/tests/test_model_provider_catalog.py -q
result: passed

py -3.13 -m pytest tests/test_runtime_model_execution_wiring.py -q
workdir: sentinel-control/services/sentinel-core
result: 9 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result: OK
```

Final commit checks are recorded in the final user-facing response.

## Files Created Or Updated

Created:

```text
sentinel-control/services/sentinel-core/sentinel/operator/model_router_models.py
sentinel-control/services/sentinel-core/sentinel/operator/model_router.py
sentinel-control/services/sentinel-core/sentinel/operator/model_router_replay.py
sentinel-control/services/sentinel-core/tests/test_local_model_hardware_and_cost_router_v1.py
sentinel-control/docs/reviews/LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1_LOCK_REPORT.md
```

Updated:

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Next Phase

```text
REAL_CHANNEL_ADAPTERS_V1
```

Do not start Real Channel Adapters until this lock is committed, pushed, and
verified against `origin/main`.
