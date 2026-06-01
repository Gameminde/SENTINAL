# Browser Runtime AgentRuntime Full Browser Stack Lock Report

Recorded at: 2026-06-01

## Current State

The previous packs proved the promoted browser L5/L6 organs through direct
runtime calls and `OrganDispatcher`. This pack proves the full promoted browser
stack through `AgentRuntime.run()` with native Brain proposal artifacts.

```text
BrainCognitionLoop
-> proposal_artifacts
-> AgentRuntime ORGAN_DISPATCHING
-> OrganDispatcher
-> DelegatedActionGate
-> execute_organ_runtime_request
-> browser L5/L6 organ
-> receipt
-> FinalGate certificate
-> RoleLoopMemoryBridge feedback
-> replan-ready packet
```

## Implemented

```text
Brain-native L6 browser login proposal acceptance = CLOSED
Brain-native L6 browser file quarantine proposal acceptance = CLOSED
Brain-native L6 browser JS sandbox proposal acceptance = CLOSED
AgentRuntime open -> login -> close path = CLOSED
AgentRuntime open -> download quarantine -> JS sandbox -> close path = CLOSED
Temporary user_input candidate bridge disabled by default = CLOSED
Raw credential value persistence in AgentRunResult = REJECTED
Memory feedback through RoleLoopMemoryBridge = CLOSED
Replan-ready packet = CLOSED
Automatic replan execution = NOT_STARTED
Durable credential secret storage = NOT_STARTED
Generic login/upload/download/private session = NOT_STARTED
Arbitrary JS outside sandbox contract = NOT_STARTED
```

## Code Change

`BrainCognitionLoop` now treats promoted browser organ names as typed metadata
before running the shared safety scanner. The value is replaced with a stable
hash only when the key is exactly `browser_organ_kind` and the value is one of
the promoted Sentinel browser organ identifiers:

```text
browser_session_manager
browser_form_submit_special_authority
browser_login_credential_session_broker
browser_download_upload_quarantine
browser_js_sandbox_special_authority
```

This does not permit raw `browser_login`, `browser_submit`, credential access,
provider/model override, or hidden tool payloads. Those remain scanned and
rejected.

## Evidence

New tests:

```text
test_agentruntime_brain_native_routes_l6_login_stack_without_temporary_bridge
test_agentruntime_brain_native_routes_file_quarantine_and_js_sandbox_stack
```

Red/green evidence:

```text
Initial failure:
brain_candidate_source_status = PARTIAL
BrainCognitionLoop rejected $.existing_proposal_artifacts[1].browser_organ_kind

After fix:
python -m pytest tests/test_browser_runtime_agentruntime_full_browser_stack_lock.py -q
.. [100%]
```

## Anti-Overclaim

Closed:

```text
AgentRuntime.run full promoted browser stack from Brain-native proposal_artifacts = CLOSED
```

Not closed:

```text
Durable credential value storage = NOT_STARTED
Generic browser credential use outside L6 broker = NOT_STARTED
Generic upload/download outside quarantine = NOT_STARTED
Generic arbitrary JS = NOT_STARTED
Payment/spend L7 runtime wiring = NOT_STARTED
Shell/API/channel/desktop execution = NOT_STARTED
Automatic replan execution = NOT_STARTED
```

## Next Pack

```text
BROWSER_MULTI_AGENT_OPERATOR_SQUAD_LOCK
```

Goal: move from one browser operator path to a controlled squad pattern where
multiple browser-specialized agents can observe, act, verify, recover, and hand
off under one Sentinel authority envelope and shared receipt timeline.
