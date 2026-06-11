# Permissioned Desktop Sidecar And Visual Grounding V1 Lock Report

Date: 2026-06-11

## Verdict

`PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1` is locked as a
Sentinel-native local runtime foundation.

```text
current_phase = PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1_LOCKED
previous_phase = REAL_CHANNEL_ADAPTERS_V1_LOCKED
next_phase = REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
roadmap_doctrine = product power under provable authority
```

The implementation is not observation-only. It preserves the product doctrine:

```text
No hidden ambient control.
No unauthorized control.
Yes to future full user-consented always-on desktop monitoring and control.
```

V1 closes the safe foundation: policy modes, permissioned observation,
monitoring snapshots, visual grounding, action preview/proposal, fake/injected
action backend, before/after evidence, receipts, FinalGate, telemetry, replay,
kill/revocation checks, app/window/display/region allowlists, and sensitive
region handling.

V1 does not implement a production live host-control adapter, hidden screenshot
loop, keylogger, credential vault, payment/account/security/device action,
provider fallback/AUTO, or vendor runtime bridge.

## Sentinel Components Reused

```text
MissionKernel / MissionRunStore = reused for mission-owned persistence, timeline, hash-chain verification
TelemetryKernel / TelemetryStore = reused for desktop sidecar events and metrics
MissionAuthorityEnvelope = reused as the only observation/action authority source
operator redaction/safety utilities = reused for secret/control/provider override blocking
browser visual grounding doctrine = reused conceptually for evidence-linked target candidates
receipt / FinalGate / replay doctrine = preserved; replay never captures or acts
PowerRuntime / AgentRuntime boundaries = preserved; no direct organ bypass added
kill/revocation checks = reused through MissionKernel terminal-state checks plus sidecar kill binding
```

No parallel desktop runtime, authority system, mission store, telemetry system,
memory system, daemon, worker fleet, model router, channel runtime, or vendor
runtime was created.

## AgentLab Mechanisms Harvested

AgentLab was inspected as source-only reference. No vendor code, runtime,
dependency, service connection, account, plugin bridge, or desktop automation
backend was copied, installed, or run.

```text
UI-TARS = visual grounding and screenshot-to-target thinking, rewritten as evidence-linked target candidates only
JARVIS = local sidecar/app-window status visibility and assistant ergonomics, rewritten as permissioned sidecar descriptors
Agent Zero / gptme = operator-visible progress and compact local state summaries
oh-my-pi = hash-anchored state, minimized structured results, before/after evidence discipline
OpenClaw / Hermes = multi-step guarded tool breadth and continuity patterns
```

All mechanisms were rewritten Sentinel-native as policy records, injected
backends, hash-only observation evidence, typed visual grounding results,
proposal-only action previews, receipts, telemetry, and replay.

## Runtime Added

```text
sentinel/operator/desktop_sidecar_models.py
sentinel/operator/desktop_sidecar.py
sentinel/operator/desktop_sidecar_replay.py
```

Implemented concepts:

```text
DesktopSidecarConfig
DesktopSidecarId / kind / maturity
DesktopCapabilityProfile
DesktopPermissionPolicy
DesktopMonitoringPolicy
DesktopObservationRequest / Result
DesktopScreenshotRef
DesktopWindowRef / AppRef / DisplayRef / RegionRef
DesktopVisualGroundingRequest / Result
DesktopTargetCandidate
DesktopActionProposal / Preview / Approval / Request / Result
DesktopActionKind / ActionPolicy
DesktopBeforeAfterEvidence
DesktopSensitiveRegionPolicy / RedactionResult
DesktopKillSwitchBinding / RevocationCheck
DesktopSidecarReceipt
DesktopSidecarFinalGateCertificate
DesktopSidecarTelemetrySummary
DesktopSidecarReplayView / ReplayBuilder
DesktopSidecarRegistry / Runtime
```

## Sidecar Maturity

```text
contract_only = modeled
fake_backend = modeled
injected_transport = implemented and tested
local_observation_adapter = modeled, not live production adapter
live_opt_in_adapter = modeled as future maturity, not implemented
production_ready_adapter = blocked in V1
```

Tests use a fake/injected backend. No live OS automation, desktop API calls,
screen recorder, clipboard read/write, camera/microphone capture, model server,
provider call, or external service is invoked.

## Observation Behavior

Desktop observation requires:

```text
MissionAuthorityEnvelope with desktop_observe
desktop_sidecar tool grant or sidecar-specific grant
registered sidecar config
operator-visible request
no ambient loop
app/window/display/region policy compliance
mission not killed/revoked/expired
```

Observation persists hash-only screenshot evidence by default:

```text
screenshot_hash
byte_count
raw_screenshot_persisted = false
safe text snippet hashes only
redaction result
receipt refs
FinalGate refs
telemetry refs
```

Raw screenshot bytes, raw OCR text, credential text, provider keys, prompts,
provider responses, and reasoning are blocked from persistence.

## Monitoring Behavior

V1 adds permissioned monitoring snapshots for local product power and future
always-on supervision:

```text
system snapshot
app snapshot
window snapshot
process snapshot
hardware metrics
sensor metrics
clock metrics
background activity snapshot
monitoring receipt
```

Unavailable data is represented as `UNKNOWN`, `UNSUPPORTED`,
`PERMISSION_REQUIRED`, or `BLOCKED_BY_POLICY`; V1 does not fake hardware
capability.

## Visual Grounding Behavior

Visual grounding converts an observation into target candidates. It never
executes action.

```text
target candidates are region-bound
confidence and ambiguity are explicit
evidence refs are preserved
ambiguous targets require checkpoint/block
sensitive targets block live action
```

## Desktop Action And Preview Behavior

V1 supports action previews and fake/injected action execution only.

Action execution requires:

```text
MissionAuthorityEnvelope with desktop_action
registered sidecar
allowed action kind
allowed app/window/region
operator approval when required by policy
mission not killed/revoked/expired
fake/injected backend
receipt
FinalGate
telemetry
replay record
```

Delegated-session mode may allow scoped injected actions without per-step
approval only when the policy explicitly disables per-action approval. This is
still bounded by mission authority, allowlists, kill/revocation checks, receipts,
FinalGate, telemetry, and replay.

Live opt-in host actions remain `NOT_STARTED`.

## Permission, Allowlist, And Approval Policy

Implemented modes:

```text
OBSERVE_ONLY
MONITOR_ONLY
ASSISTED_OPERATOR
APPROVED_ACTION_OPERATOR
DELEGATED_SESSION_OPERATOR
CONTINUOUS_SUPERVISION_OPERATOR
```

Policy includes:

```text
allowed_modes
active_mode
allowed_apps / blocked_apps
allowed_windows / blocked_windows
allowed_displays
blocked_region_labels
persist_full_screenshot_allowed = blocked in V1
persist_full_ocr_text_allowed = blocked in V1
always_on_allowed
production_always_on_ready = blocked in V1
approval_required_for_each_action
allowed_action_kinds
max_actions_per_session
```

## Sensitive Region And Redaction Behavior

V1 uses deterministic policy labels and region metadata. It does not claim
perfect visual privacy detection.

Sensitive categories modeled:

```text
password fields
credential managers
payment / banking / financial regions
private messages
health / legal / identity documents
API keys / tokens / provider keys
seed phrases / recovery codes / 2FA codes
browser login/session material
```

If sensitivity is known or uncertain for live action, the safe result is block
or operator checkpoint, not execution.

## Receipt And FinalGate Behavior

Desktop receipts contain safe metadata only:

```text
sidecar id
mission/run id
authority envelope ref
display/window/app/region hashes
operation type
screenshot hash/ref
target candidate refs
policy hash
approval ref
before/after hashes
sensitive-region flags
telemetry refs
status
timestamp
```

Blocked from receipts:

```text
raw credentials
raw passwords
raw tokens
raw provider keys
raw full screenshots by default
raw prompts
raw provider responses
raw reasoning
unredacted sensitive document content
```

FinalGate certifies terminal desktop truth such as observed, grounded,
previewed, blocked, failed, revoked, needs approval, or sensitive-region
blocked. FinalGate certificates cannot become future permission.

## Telemetry And Metrics

Added telemetry source surface:

```text
TelemetrySourceSurface.DESKTOP_SIDECAR
```

Added events:

```text
desktop_sidecar_registered
desktop_sidecar_rejected
desktop_observation_requested
desktop_observation_blocked
desktop_observation_completed
desktop_screenshot_captured
desktop_screenshot_redacted
desktop_sensitive_region_detected
desktop_grounding_requested
desktop_grounding_completed
desktop_grounding_failed
desktop_action_proposed
desktop_action_preview_created
desktop_action_approval_required
desktop_action_approved
desktop_action_blocked
desktop_action_started
desktop_action_completed
desktop_action_failed
desktop_kill_switch_triggered
desktop_revocation_detected
desktop_replay_built
```

Added metrics:

```text
desktop_observation_count
desktop_observation_block_count
desktop_grounding_success_rate
desktop_grounding_ambiguity_rate
desktop_sensitive_region_block_count
desktop_action_preview_count
desktop_action_block_count
desktop_action_success_rate
desktop_receipt_completeness
desktop_replay_completeness
desktop_kill_latency
```

Telemetry remains data only. It cannot approve, execute, grant authority, unlock
credentials, or become future permission.

## Replay Behavior

`DesktopSidecarReplayBuilder` reconstructs:

```text
sidecar configs
observation records
monitoring records
grounding records
action previews
approvals
action results
receipts
FinalGate refs
telemetry refs
tamper status
```

Replay never captures a new screenshot, repeats an action, reads clipboard,
calls live desktop APIs, fetches app/window state, or unlocks credentials.

## Authority Review

```text
desktop sidecar creates authority = BLOCKED
desktop observation creates authority = BLOCKED
visual grounding executes = BLOCKED
desktop action without MissionAuthorityEnvelope = BLOCKED
desktop action without approval when required = BLOCKED
desktop action outside app/window/region policy = BLOCKED
desktop action after kill/revocation = BLOCKED
LLM/memory/skill/worker/daemon/scheduler/channel direct control = BLOCKED
receipt/FinalGate/memory/telemetry as authority = BLOCKED
raw credential/token/prompt/provider response/reasoning persistence = BLOCKED
provider fallback/AUTO = NOT_APPROVED
```

## CodeRabbit Advisory Review

```text
CodeRabbit used: no
review source: unavailable CLI
finding summary: CodeRabbit CLI was not installed in this environment
fixes applied: none from CodeRabbit
deferred/rejected findings: none
authority status: CodeRabbit did not become authority
```

CodeRabbit was not installed (`coderabbit` command unavailable). No unknown
dependencies were installed and no token/auth flow was started. Manual
exhaustive audit and targeted tests were performed instead.

## Exhaustive Audit Findings

| Severity | Finding | File/surface | Decision | Fix or rationale | Remaining limits |
| --- | --- | --- | --- | --- | --- |
| P1 | Desktop action telemetry events were rejected because raw `desktop_action_*` event type was projected into telemetry metadata and hit the external-action scanner. | `sentinel/telemetry/kernel.py` | accepted_and_fixed | Replaced raw mission event type with `mission_event_type_hash` and safe event family. | Event kind remains explicit through typed telemetry enum. |
| P1 | AgentRuntime regression exposed runtime import cycle through `proposal_bridge.py` importing `BrainCognitionResult` while Brain was partially initialized. | `sentinel/agent/organs/proposal_bridge.py` | accepted_and_fixed | Converted runtime import to lazy coercion helper and made bridge input data-typed. | No behavior change to bridge coercion after Brain is loaded. |
| P2 | Observation request model initially rejected hidden/ambient payload before runtime policy could audit/block it. | `sentinel/operator/desktop_sidecar_models.py` | accepted_and_fixed | Runtime now blocks hidden/ambient capture and tests assert the block. | Model still accepts invalid request data as untrusted input. |
| P2 | Early event metadata included sensitive/control terms such as action kind and target sensitivity. | `sentinel/operator/desktop_sidecar.py` | accepted_and_fixed | Telemetry metadata now uses hashes/counts and safe sidecar ids. | Mission events remain readable through safe summaries. |
| P2 | Raw OCR persistence field names included raw-text wording in config JSON. | `sentinel/operator/desktop_sidecar_models.py` | accepted_and_fixed | Renamed to policy booleans that are blocked in V1. | No raw OCR/screenshot persistence supported in V1. |
| Info | Live opt-in desktop adapter is not implemented. | runtime/docs | accepted_deferred_with_reason | V1 intentionally uses fake/injected backend only. | Future phase must add real OS adapter with opt-in policy and authority. |
| Info | Sensitive-region detection is deterministic metadata/rule based, not vision-perfect. | runtime/docs | accepted_deferred_with_reason | Report and docs state honest V1 limit. | Future live adapter needs stronger privacy detection. |

No open P0/P1 or serious P2 issues remain.

## Tests And Checks

Targeted tests run:

```text
py -3.13 -m pytest tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py -q
```

Relevant regression slices run:

```text
py -3.13 -m pytest tests/test_real_channel_adapters_v1.py tests/test_local_model_hardware_and_cost_router_v1.py tests/test_governed_skill_and_procedure_fabric_v1.py tests/test_model_amplification_execution_harness_v1.py -q
py -3.13 -m pytest tests/test_production_mission_daemon_and_scheduler_v1.py tests/test_mission_worker_fleet_authority_inheritance_v1.py tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_durable_mission_workflow_and_automatic_replan_v1.py tests/test_durable_mission_workflow_replan_gauntlet_v1.py -q
py -3.13 -m pytest tests/test_llm_live_operator_models_v0.py tests/test_llm_live_operator_conversation_intake_v0.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_replay_v0.py tests/test_agent_runtime.py tests/test_agent_event_bus.py tests/test_agent_evidence_chain.py tests/test_low_risk_execution_finalgate_receipts.py -q
py -3.13 -m pytest tests/test_sentinel_power_runtime_v0.py tests/test_power_fabric_orchestration_demo.py tests/test_browser_visual_grounding_ocr_v1.py -q
py -3.13 -m pytest tests/test_agent_runtime.py tests/test_brain_to_organ_runtime_closed_loop.py tests/test_agent_evidence_chain.py -q
```

Final checks and scans are recorded in the commit/push transcript and final
user report.

## Files Created Or Updated

Created:

```text
sentinel-control/services/sentinel-core/sentinel/operator/desktop_sidecar_models.py
sentinel-control/services/sentinel-core/sentinel/operator/desktop_sidecar.py
sentinel-control/services/sentinel-core/sentinel/operator/desktop_sidecar_replay.py
sentinel-control/services/sentinel-core/tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py
sentinel-control/docs/reviews/PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1_LOCK_REPORT.md
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
sentinel-control/services/sentinel-core/sentinel/agent/organs/proposal_bridge.py
```

## Honest V1 Limits

```text
not a production OS service sidecar
not a live host-control adapter
not a keylogger
not a screen recorder
not raw screenshot/OCR persistence
not credential vault
not payment/account/security/device power
not hidden ambient authority
not perfect visual privacy detection
not provider fallback/AUTO
not vendor runtime
```

## Next Phase

```text
REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
```

Voice must be a cockpit transport and ambient operator surface, never authority
or direct execution.
