# Browser Runtime Unification L6 Login/File/JS Dispatch Lock Report

Recorded at: 2026-06-01

## Current State

The previous runtime unification pack promoted L5 browser sessions and the
first L6 form-submit special authority path. This pack promotes the remaining
implemented L6 browser organs through the canonical Sentinel body:

```text
OrganDispatcher
-> DelegatedActionGate
-> execute_organ_runtime_request
-> L6 browser special-authority organ
-> receipt
-> FinalGate certificate
```

## Implemented

```text
Browser login credential session broker through runtime_execution = CLOSED
Browser login credential session broker through OrganDispatcher = CLOSED
Browser download/upload quarantine through runtime_execution = CLOSED
Browser download quarantine through OrganDispatcher = CLOSED
Browser JS sandbox through runtime_execution = CLOSED
Browser JS sandbox through OrganDispatcher = CLOSED
PowerLab browser_login_l6_template executable config = CLOSED
PowerLab browser_file_quarantine_l6_template executable config = CLOSED
PowerLab browser_js_sandbox_l6_template executable config = CLOSED
Ephemeral credential provider values excluded from config serialization = CLOSED
Raw login credential values in runtime/dispatch result = REJECTED
Generic browser login/upload/download/JS without explicit L6 contract = STILL_BLOCKED
Payment/spend/channel/shell/API/desktop execution = NOT_STARTED
```

## Runtime Contract

Promoted mode:

```text
OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY
```

Promoted organs:

```text
browser_session_manager
browser_form_submit_special_authority
browser_login_credential_session_broker
browser_download_upload_quarantine
browser_js_sandbox_special_authority
```

Required posture:

```text
enabled = true
organ_dispatch_enabled = true
allow_browser_live_operator = true
allow_browser_special_authority = true
allowed_action_levels includes L5 and L6
allowed_organs names the exact promoted organ
browser_persist_sessions = true for multi-step open -> action -> close
```

Credential values are accepted only as `browser_ephemeral_credentials` on the
runtime config. That field is excluded from Pydantic serialization and is used
only to instantiate `EphemeralBrowserCredentialProvider` inside one execution.
Receipts contain credential refs/proof ids only, never raw values.

## Safety Notes

The runtime safety scanner hashes promoted typed browser requests, gate results,
delegated lanes, and MissionAuthorityEnvelope payloads before scanning. This
prevents authority metadata such as allowed L6 browser actions from being
misclassified as a raw dangerous instruction while preserving scanner coverage
for request metadata, provider/model overrides, raw secrets, and hidden tool
payloads.

The proposal bridge and delegated gate now treat promoted browser organ labels
and allowed substeps as typed contract metadata, not raw instruction text. This
does not make them executable; execution still requires Gate approval, explicit
runtime opt-in, typed sub-request construction, receipt, and FinalGate.

## Evidence

New tests:

```text
test_runtime_blocks_l6_login_file_js_without_explicit_organs
test_runtime_executes_l6_login_with_ephemeral_credentials_without_persisting_values
test_runtime_executes_l6_file_download_quarantine_and_js_sandbox
test_dispatcher_routes_open_file_js_close_through_runtime
test_dispatcher_routes_open_login_close_through_runtime_without_secret_persistence
```

Executed checks:

```text
python -m pytest tests/test_browser_runtime_unification_l6_login_file_js_dispatch_lock.py -q
python -m pytest tests/test_browser_runtime_unification_l5_l6_dispatch_lock.py tests/test_browser_runtime_unification_l6_login_file_js_dispatch_lock.py -q
python -m pytest tests/test_browser_login_credential_session_broker_l6.py tests/test_browser_download_upload_quarantine_l6.py tests/test_browser_js_sandbox_special_authority_l6.py -q
python -m pytest tests/test_organ_proposal_bridge.py tests/test_delegated_action_gate_model_v0.py tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py -q
```

All targeted checks above passed during implementation.

## Anti-Overclaim

Closed:

```text
L6 login/file quarantine/JS through runtime/dispatcher = CLOSED
```

Not closed:

```text
Generic credential vault secret storage = NOT_STARTED
Generic browser login outside explicit broker = NOT_STARTED
Generic upload/download outside quarantine = NOT_STARTED
Arbitrary JS outside sandbox contract = NOT_STARTED
Payment/spend L7 runtime wiring = NOT_STARTED
Shell/API/channel/desktop runtime power = NOT_STARTED
```

## Next Pack

```text
BROWSER_RUNTIME_AGENTRUNTIME_FULL_BROWSER_STACK_LOCK
```

Goal: expose the full promoted browser stack through `AgentRuntime.run` using
native brain proposal artifacts, not only direct runtime calls and dispatcher
tests.
