# REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1_FAKE_MODEL_GATE_REPORT

## Verdict

`REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1` now has a deterministic fake-model gate for the first read-only operator vertical slice through the existing cockpit, MissionKernel, and AgentRuntime bridge mediation path.

This is not a real-provider run, not Wave 1 certification, and not production certification.

## What Was Implemented

Added a Sentinel-native read-only operator spine module:

```text
sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py
```

Added deterministic tests:

```text
sentinel-control/services/sentinel-core/tests/test_real_model_read_only_operator_production_spine_v1.py
```

The fake-model gate proves:

```text
LLMLiveOperatorCockpit.handle(...)
-> explicit UserModelContract-backed LLM cockpit intake
-> MissionKernel mission creation and enqueue
-> MissionAuthorityEnvelope
-> OperatorAgentRuntimeBridge
-> read-only multi-turn decision loop
-> per-action policy gate
-> read-only list/read evidence
-> action receipts
-> terminal FinalGate
-> AgentRuntime bridge result event
-> MissionRunStore event timeline
-> replay view rebuilt from persisted refs without re-execution
```

## Reused Sentinel Components

```text
LLMLiveOperatorCockpit
OperatorConversationEngine
OperatorLLMConversationAdapter
UserModelContract
MissionKernel
MissionRunStore
MissionRecord / MissionEvent
TelemetryKernel certified-mode requirement
operator safety scanner / redaction helpers
mission lifecycle policy
MissionAuthorityEnvelope identity / expiry / revocation checks
OperatorAgentRuntimeBridge terminal / telemetry / proof checks
GateSequence.default(...) for per-action authorization
```

## Gate Scenarios Covered

```text
successful multi-turn read-only fake-model mission
killed mission blocks before model or tool action
kill after model response blocks before action receipt
kill after tool result blocks before receipt
uncertified telemetry blocks before model or tool action
write_file action rejected by decision schema
successful read-only mission mediated by OperatorAgentRuntimeBridge
wrong authority envelope blocked before read-only runtime call
revoked authority envelope blocked before read-only runtime call
expired authority envelope blocked before read-only runtime call
authority revoked after model response blocks before action
terminal report with unsupported write/send claim rejected by FinalGate
terminal report with unknown/cross-run evidence ref rejected by FinalGate
model/decision client error classified safely without tool action
model/decision timeout classified safely without tool action
authority scope narrowing blocked by GateSequence before action
path traversal / absolute Windows path / UNC path blocked before receipt
sensitive snapshot paths blocked before receipt
explicit output/excluded directory paths blocked before receipt
symlink escape blocked before receipt
snapshot drift after model response blocks before action
deadline exhausted before model call blocks without action
deadline exhausted after model response blocks before action
duplicate read-only observation reuses evidence ref and marks duplicate evidence
replay rebuilds from stored refs without model/tool re-execution
replay rejects missing receipt artifacts
replay rejects tampered receipt hashes
replay rejects cross-mission receipt refs
replay rejects tampered FinalGate certificates
replay rejects cross-mission FinalGate certificates
replay rejects injected receipt events after terminal state
```

## Receipts And FinalGate

Current read-only action receipts use:

```text
class: sentinel.operator.read_only_operator_spine.ReadOnlyActionReceipt
write method: MissionRunStore.atomic_write_json(...)
path: <mission_run_dir>/read_only_spine/receipts/<receipt_id>.json
event binding: MissionRunStore.append_event(..., receipt_refs=[receipt_id])
hash binding: ReadOnlyActionReceipt.with_hash()
mission binding: receipt.mission_id and MissionRunStore mission event mission_id
```

There is no repository-wide `DurableReceiptLedger` class currently used by this read-only observation path. The durable proof surface for this fake gate is therefore the mission run store event chain plus the read-only receipt model and hash-bound artifact files. This is acceptable for the fake gate, but it is a named V1 limit before production certification.

The terminal report path writes exactly one read-only FinalGate certificate and completes the mission through `MissionKernel`.

Blocked sessions write a rejected terminal FinalGate and a safe blocked event without action receipts.

When mediated through `OperatorAgentRuntimeBridge`, the bridge receives the read-only FinalGate certificate object and returns the same terminal certificate ref recorded in the read-only event timeline. This closes the earlier risk of synthetic proof refs diverging from the stored read-only certificate.

## Gate Behavior

Per-action authorization now uses:

```text
GateSequence.default(project_root=snapshot_root, known_tools={"read_only_observation"})
MissionAction(action_type=<read-only action>, tool="read_only_observation", target=<requested path>)
MissionAuthorityEnvelope allowed_actions / allowed_tools / allowed_paths
MissionState(mission_id=<mission_id>)
```

The read-only path still keeps a small local schema/path guard around the canonical GateSequence. That local guard is defensive validation, not a substitute for the canonical GateSequence.

## Runtime Race Guards

The fake gate rechecks runtime openness at the dangerous boundaries:

```text
before model decision
after model response / before action
before GateSequence evaluation
after read-only tool result / before observation is accepted and receipted
```

The recheck covers:

```text
MissionKernel terminal status
active MissionAuthorityEnvelope revocation/expiry when mediated through OperatorAgentRuntimeBridge
deadline exhaustion
certified telemetry availability
```

This closes the fake-gate windows where a model could return a decision and then the mission or authority became invalid before the read-only action or receipt.

## Terminal Report Grounding

`ReadOnlyDecision` now carries explicit `evidence_refs` for terminal report grounding. The terminal FinalGate rejects supplied refs that are not present in the current session observations, preventing unknown or cross-run evidence refs from being used as proof. V1 still does not prove full semantic claim-to-evidence verification for every sentence; that remains a named limit before a real-provider run.

## Replay Integrity

Replay now verifies stored proof artifacts before reconstructing:

```text
receipt file exists
receipt mission_id matches current mission
receipt hash verifies after reload
FinalGate file exists
FinalGate mission_id matches current mission
FinalGate hash verifies after reload
receipt / FinalGate write counters do not change during replay
model / tool counters do not change during replay
```

Injected receipt refs, missing artifacts, tampered hashes, and cross-mission proof reuse all fail closed before replay is accepted.

## Snapshot Isolation

The read-only snapshot path guard now blocks:

```text
path traversal
absolute Windows paths
UNC paths
symlink escapes
.env / .git / .codex / .sentinel-runs / read_only_spine
credentials.json / secrets.json
explicitly excluded output or rubric directories
```

The canonical `GateSequence` may block some path escapes before the local guard runs; both are accepted as safe as long as no receipt or observation is accepted.

## Snapshot Drift

The session calculates a safe snapshot fingerprint at startup and rechecks it at runtime boundaries. Sensitive and explicitly excluded paths are not read during fingerprinting. Drift after a model response now blocks before tool execution or receipt creation.

## What This Does Not Claim

This gate now proves AgentRuntime bridge mediation for the fake-model read-only vertical slice.

It still does not claim full production certification:

```text
no real provider call
no full production resume/restart path
no WorkerFleet/daemon scheduling path
no PowerRuntime material-action execution
no browser/desktop/channel capability execution
no complete adversarial corpus
no repository-wide durable receipt ledger integration beyond MissionRunStore receipt/event binding
```

The read-only loop is intentionally not forced through `OperatorPowerRuntimeBridge`, because PowerRuntime is the material-action path. If read-only observation remains separate, the product architecture should name it explicitly as a governed read-only observation runtime behind MissionKernel / MissionAuthorityEnvelope / AgentRuntimeBridge / telemetry / receipts / FinalGate / replay.

Required next architecture step:

```text
extend this bridge-bound fake gate into the planned real-provider single-run experiment only after the remaining fake adversarial cases are covered,
or define the exact canonical read-only runtime bridge if read-only observation is intentionally separate from material PowerRuntime execution.
```

## Safety Results

```text
no real provider call
no fallback/AUTO
no provider-native tools
no raw prompt persistence
no raw provider response persistence
no raw reasoning persistence
no raw credential/provider key persistence
no workspace mutation action
no shell/API/browser/desktop/channel/payment/security action
```

## Tests And Checks

Passed:

```text
py -3.13 -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py -> 35 passed
py -3.13 -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_operator_adapter_v0.py -> passed
py -3.13 -O -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_operator_adapter_v0.py -> passed
py -3.13 -m pytest -q tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py -> passed
py -3.13 -m pytest -q tests/test_gate_sequence_runtime_wiring.py tests/test_gate_sequence_integration.py tests/test_final_gate_terminality.py tests/test_final_gate_registry.py tests/test_final_gate_determinism.py tests/test_llm_live_operator_replay_v0.py -> passed
py -3.13 -m pytest -q tests/test_agent_evidence_chain.py tests/test_agent_event_bus.py tests/test_agent_trace_replay.py tests/test_low_risk_execution_finalgate_receipts.py -> passed
py -3.13 -m compileall -q sentinel -> passed
git diff --check -> passed
```

Targeted scans:

```text
real temporary credential / endpoint scan: NO_MATCHES
raw prompt / raw provider response / raw reasoning / provider-native / fallback-AUTO scan on new files: NO_MATCHES
direct organ / shell / runtime-bypass scan on new code/tests: NO_MATCHES
```

## Next Recommended Work

Do not run another real provider call yet.

Next step should finish the remaining fake adversarial matrix:

```text
READ_ONLY_OPERATOR_FAKE_ADVERSARIAL_COMPLETION_V1
```

Acceptance target:

```text
provider/model error,
semantic claim-to-evidence verification for every terminal report sentence,
and no overclaim beyond fake-model bridge-bound certification.
```
