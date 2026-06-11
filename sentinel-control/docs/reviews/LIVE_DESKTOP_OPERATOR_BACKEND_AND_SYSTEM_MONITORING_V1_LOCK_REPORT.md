# Live Desktop Operator Backend And System Monitoring V1 Lock Report

Date: 2026-06-11

## Verdict

```text
LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1 = LOCKED
previous_phase = PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1_LOCKED
next_phase = REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
roadmap_doctrine = product power under provable authority
```

This phase is inserted before `REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1`. It
closes the next desktop-power gap after Permissioned Desktop Sidecar V1 by
adding a live-desktop-ready backend foundation, safe system monitoring,
permission UI/tray/service shapes, fake/injected action execution, benchmark
gauntlet, receipts, FinalGate, telemetry, replay, and kill/revocation behavior.

It does not claim final production Windows/macOS/Linux app readiness, an
installed tray daemon, an OS service supervisor, unrestricted global
mouse/keyboard control, hidden capture, keylogging, credential harvesting,
payment/account/security/device power, provider fallback/AUTO, or vendor
runtime integration.

## Sentinel Components Reused

- `DesktopSidecar` models, permission policies, control modes, receipts,
  FinalGate certificates, monitoring snapshot models, before/after evidence,
  sensitive-region posture, and replay doctrine.
- `MissionKernel` and `MissionRunStore` for mission-scoped storage, timeline
  hash chain, pause/kill terminal checks, event persistence, and receipts.
- `MissionAuthorityEnvelope` for every monitoring/action/benchmark authority
  check.
- Existing `TelemetryKernel` and `TelemetryStore`; no parallel telemetry store
  was created.
- Existing redaction and operator payload safety utilities; raw prompts,
  provider responses, reasoning, credentials, tokens, screenshots, and OCR text
  remain blocked from persistence.

## AgentLab Mechanisms Harvested

- UI-TARS: visual grounding and desktop benchmark thinking, rewritten as
  evidence-linked targets and fake/injected desktop benchmark tasks.
- JARVIS: local desktop assistant and system-status shape, rewritten as
  operator-visible permission/tray/service descriptors.
- Agent Zero and gptme: background task supervision and compact local session
  status, rewritten as `DesktopOperatorSession` and monitoring ticks.
- oh-my-pi: hash-anchored state and typed minimized results, rewritten as
  hash-bound configs, action plans, receipts, replay, and benchmark results.
- OpenClaw/Hermes: broad tool reach and multi-step continuity, rewritten as
  Sentinel-native control modes and runtime-bound action planning.

No vendor code, vendor runtime, bridge, dependency, account, cloud service, or
telemetry vendor was integrated.

## Runtime Added

- `LiveDesktopBackendConfig`, backend kind/maturity/capability profiles, and
  registry.
- `DesktopOperatorSession`, `DesktopOperatorSessionPolicy`, and session state.
- Safe local system/app/window/process/hardware/sensor/clock monitoring
  snapshots using existing desktop snapshot models.
- Explicit monitoring sessions and monitoring ticks.
- Permission UI, tray, and service supervisor shape models.
- Desktop action command, idempotency key, safety check, execution plan,
  approval record, action receipt, and execution result.
- Fake/injected action backend adapter for tests and benchmark.
- Desktop benchmark scenario/run/result and replay view.
- Live desktop replay builder that reconstructs state without new snapshots or
  re-actions.

## Backend Maturity

```text
implemented_maturity = local_monitoring_backend + fake/injected action backend
live_opt_in_action_backend = descriptor-shaped only, not exercised by default
production_ready_backend = NOT_STARTED / explicitly rejected by model validators
production OS tray/service app = NOT_STARTED
```

## Observation And Monitoring Behavior

- System monitoring is local, read-only, and mission scoped.
- Metrics include OS/platform, session hash, display count, visible window/app
  summaries, process summaries, CPU/RAM/disk/network samples, GPU/sensor/battery
  unknown posture, system clock hash, and background activity counts.
- Unavailable metrics return structured `UNKNOWN`, `UNSUPPORTED`, or
  `PROBE_FAILED`; no fake precision is claimed.
- Monitoring requires explicit session policy enablement.
- Monitoring is blocked after kill or revocation.
- Always-on monitoring is modeled as explicit policy shape only; no hidden
  background capture loop is implemented.

## Desktop Action Behavior

- Action flow is proposal/plan first.
- Execution requires a valid `MissionAuthorityEnvelope`, control mode, app/window
  allowlist, sensitive-region check, approval when policy requires it,
  kill/revocation recheck, telemetry, receipt, FinalGate, and replay record.
- The executable V1 backend is fake/injected only.
- Live opt-in action backend shape rejects use without explicit opt-in and is
  not enabled in normal tests.
- Clipboard is blocked by default.
- Sensitive regions block live action plans.

## Receipt And FinalGate Behavior

Desktop monitoring/actions emit safe hash-bound receipts with mission/backend
refs, policy hash, authority envelope ref, app/window refs, idempotency keys,
before/after evidence hashes where applicable, telemetry refs, status, and
timestamps.

Receipts, FinalGate, memory, telemetry, screenshots, monitoring signals, process
state, or benchmark results cannot become future permission.

## Telemetry And Metrics

Added live desktop event vocabulary:

```text
live_desktop_backend_registered
live_desktop_backend_rejected
desktop_operator_session_started
desktop_operator_session_completed
desktop_operator_session_failed
desktop_operator_mode_changed
desktop_system_snapshot_requested
desktop_system_snapshot_completed
desktop_system_snapshot_blocked
desktop_monitoring_session_started
desktop_monitoring_tick_completed
desktop_monitoring_session_stopped
desktop_process_snapshot_created
desktop_window_snapshot_created
desktop_hardware_metric_snapshot_created
desktop_live_action_planned
desktop_live_action_blocked
desktop_live_action_started
desktop_live_action_completed
desktop_live_action_failed
desktop_live_action_kill_blocked
desktop_benchmark_started
desktop_benchmark_completed
desktop_benchmark_failed
desktop_service_shape_created
desktop_tray_shape_created
```

Added product-power metrics:

```text
desktop_system_snapshot_count
desktop_monitoring_tick_count
desktop_monitoring_block_count
desktop_process_count_sample
desktop_window_count_sample
desktop_cpu_usage_sample
desktop_ram_usage_sample
desktop_gpu_metric_available
desktop_sensor_metric_available
desktop_action_success_rate
desktop_action_block_rate
desktop_kill_block_count
desktop_replay_no_reaction_pass_rate
desktop_benchmark_pass_rate
desktop_benchmark_failure_count
```

Telemetry remains local, redacted, hash-bound data only.

## Replay Behavior

`LiveDesktopBackendReplayBuilder` reconstructs configs, sessions, monitoring
results, monitoring ticks, action plans, action results, benchmark runs,
receipt refs, FinalGate refs, telemetry refs, and tamper status.

Replay flags prove:

```text
recollected_system_metrics = false
reexecuted_actions = false
```

Replay does not take screenshots, collect new metrics, read clipboard, call live
desktop APIs, or repeat click/type/hotkey actions.

## Authority Review

Hard boundaries preserved:

- No desktop backend can create or expand `MissionAuthorityEnvelope`.
- No monitoring signal can become authority.
- No screenshot/process/window/app state can become authority.
- No benchmark result can become authority.
- No memory/skill/worker/daemon/scheduler/channel/LLM output can direct-control
  desktop.
- No replay can re-execute desktop action.
- No receipt or FinalGate certificate can become future permission.

## CodeRabbit Advisory Review

CodeRabbit used: no.

CodeRabbit was unavailable in this environment; manual exhaustive audit was
performed instead. CodeRabbit did not become authority and did not replace
tests, Sentinel audit, or this lock report.

## Exhaustive Audit Findings

| Severity | Finding | File / Surface | Decision | Fix Or Rationale | Remaining Limits |
| --- | --- | --- | --- | --- | --- |
| P0 | Hidden screenshot loop risk | Live backend runtime | Passed | No ambient loop exists; monitoring requires explicit session policy | Production OS service remains not started |
| P0 | Keylogging / credential harvesting risk | Action command and persistence | Passed | Clipboard blocked by default; secret-like text rejected; raw credential/token persistence blocked | No credential vault in this phase |
| P0 | Desktop backend as authority | Runtime authority checks | Passed | Every monitoring/action/benchmark path requires `MissionAuthorityEnvelope`; backend cannot create grants | Authority UX remains external |
| P1 | Replay re-action risk | Replay builder | Passed | Replay only loads stored JSON and timeline events; flags no recollection/re-execution | No live replay UI yet |
| P1 | Sensitive region action risk | Action planning | Passed | Sensitive labels block action plan | V1 deterministic labels only; no perfect OCR/vision claim |
| P1 | Telemetry bypass risk | MissionRunStore/TelemetryKernel | Passed | Events/metrics use existing telemetry sink | Production telemetry service/cloud not started |
| P1 | Docs overclaim risk | Docs and roadmap | Fixed | Docs now state local same-process foundation, fake/injected action backend, no production OS app/tray/service | Live opt-in production adapter remains future |
| P2 | System metric availability | Snapshot builder | Passed | Unknown/unavailable metrics are explicit; no fake precision | GPU/temp/fan coverage depends on future opt-in adapter |
| P2 | Benchmark adequacy | Tests and report | Passed | Fake/injected gauntlet proves governed backend and replay no-reaction | Does not prove superiority over every live JARVIS desktop agent |

No open P0/P1 or serious P2 findings remain.

## Honest V1 Limits

- Local same-process runtime foundation only.
- Fake/injected action backend is the only default executable backend.
- Optional live opt-in backend is descriptor-shaped; normal tests do not call
  live OS APIs.
- No installed tray app, OS service, permission GUI, global UI Automation, or
  multi-platform host-control adapter is claimed.
- No credential vault, payment/account/security/device power, voice runtime, or
  provider fallback/AUTO was started.

## Tests And Checks

Verification completed during implementation:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_live_desktop_operator_backend_system_monitoring_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_live_desktop_operator_backend_system_monitoring_v1.py sentinel-control/services/sentinel-core/tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py sentinel-control/services/sentinel-core/tests/test_p6_desktop_agentlab_harvest.py sentinel-control/services/sentinel-core/tests/test_p6_desktop_sidecar_organ.py sentinel-control/services/sentinel-core/tests/test_p6_desktop_workspace_l6.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_real_channel_adapters_v1.py sentinel-control/services/sentinel-core/tests/test_channel_draft_send_organ_v1.py sentinel-control/services/sentinel-core/tests/test_local_model_hardware_and_cost_router_v1.py sentinel-control/services/sentinel-core/tests/test_governed_skill_and_procedure_fabric_v1.py sentinel-control/services/sentinel-core/tests/test_model_amplification_execution_harness_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_production_mission_daemon_and_scheduler_v1.py sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_and_automatic_replan_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_gauntlet_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_flow_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_power_runtime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_cli_v0.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_sentinel_power_runtime_v0.py sentinel-control/services/sentinel-core/tests/test_agent_runtime.py sentinel-control/services/sentinel-core/tests/test_brain_to_organ_runtime_closed_loop.py sentinel-control/services/sentinel-core/tests/test_delegated_action_gate_model_v0.py sentinel-control/services/sentinel-core/tests/test_agent_core_final_gate.py sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py -q
py -3.13 -m pytest tests/test_browser_visual_grounding_ocr_v1.py tests/test_browser_organ_final_gate.py tests/test_gate_sequence_runtime_wiring.py tests/test_gate_sequence_integration.py -q
```

The browser visual/Gate slice was run from `sentinel-control/services/sentinel-core`
because `test_browser_organ_final_gate.py` intentionally launches a fresh child
Python process that needs the package root on `sys.path`.

Additional checks:

```text
git diff --check
secret/raw credential/token scan on modified files
raw screenshot/OCR/text persistence scan on modified files
raw prompt/provider response/reasoning scan on modified files
fallback/AUTO scan on modified files
direct organ bypass scan on modified files
replay re-action/re-snapshot risk scan on modified files
coderabbit --version
```

## Files Created

```text
sentinel-control/services/sentinel-core/sentinel/operator/live_desktop_backend_models.py
sentinel-control/services/sentinel-core/sentinel/operator/live_desktop_backend.py
sentinel-control/services/sentinel-core/sentinel/operator/live_desktop_backend_replay.py
sentinel-control/services/sentinel-core/tests/test_live_desktop_operator_backend_system_monitoring_v1.py
sentinel-control/docs/reviews/LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1_LOCK_REPORT.md
```

## Files Updated

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/operator/desktop_sidecar_models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Next Phase

```text
REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
```

Stop condition honored: Realtime Voice was not started.
