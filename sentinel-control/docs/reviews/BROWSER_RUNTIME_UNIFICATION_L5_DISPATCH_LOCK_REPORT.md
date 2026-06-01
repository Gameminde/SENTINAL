# Browser Runtime Unification L5/L6 Dispatch Lock Report

Recorded at: 2026-06-01

## Current State

The audit finding was valid: Sentinel had powerful browser L5/L6 organs, but
the main runtime execution path only promoted L2/L3 and L4 browser perception.
Some browser powers were reachable through direct organ tests or CLI demos, not
through the canonical body:

```text
AgentRuntime / OrganDispatcher
-> DelegatedActionGate
-> execute_organ_runtime_request
-> live browser organ
-> receipt
-> FinalGate
```

This pack closes the first runtime-power gap for the existing live browser
session manager and promotes the first L6 special-authority browser action:
non-sensitive form submit through an already-open governed session.

## Implemented

```text
Browser L5 runtime mode = CLOSED
Browser L5/L6 special-authority runtime mode = CLOSED
PowerLab operator_browser_l5_template executable config = CLOSED
PowerLab browser_form_submit_l6_template executable config = CLOSED
BrowserSessionManagerL5Live through runtime_execution = CLOSED
BrowserSessionManagerL5Live through OrganDispatcher = CLOSED
BrowserSessionManagerL5Live through AgentRuntime.run explicit opt-in = CLOSED
Runtime-preserved browser session open -> observe -> close = CLOSED
BrowserFormSubmitSpecialAuthorityL6 through runtime_execution = CLOSED
BrowserFormSubmitSpecialAuthorityL6 through OrganDispatcher = CLOSED
Dispatcher session-id binding from prior browser receipts = CLOSED
Receipt + BrowserSessionFinalGate certificate returned through runtime = CLOSED
Receipt + BrowserFormSubmitFinalGate certificate returned through runtime = CLOSED
AgentRuntime default-off posture = PRESERVED
L6 login/download/upload/JS runtime promotion = NOT_STARTED
Generic browser submit/login/credential use = NOT_STARTED
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/delegated_action_gate.py
sentinel-control/services/sentinel-core/sentinel/power_lab.py
sentinel-control/services/sentinel-core/tests/test_browser_runtime_unification_l5_l6_dispatch_lock.py
```

## Runtime Contract

New explicit runtime mode:

```text
OrganRuntimeExecutionMode.BROWSER_LIVE_OPERATOR_ONLY
OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY
```

Current promoted organs:

```text
browser_session_manager
browser_form_submit_special_authority
```

Current promoted action levels:

```text
L5 browser session manager
L6 non-sensitive form submit special authority
```

Required explicit config:

```text
enabled = true
organ_dispatch_enabled = true
mode = browser_live_operator_only
allow_browser_live_operator = true
allowed_action_levels includes L5
allowed_organs includes browser_session_manager
```

For L6 form submit:

```text
mode = browser_l5_l6_special_authority_only
allow_browser_live_operator = true
allow_browser_special_authority = true
allowed_action_levels includes L5 and L6
allowed_organs includes browser_session_manager and browser_form_submit_special_authority
browser_persist_sessions = true for open -> submit -> close sequences
```

Default config still blocks before executor call.

## Gate Semantics

DelegatedActionGate now allows L5/L6 browser candidates only when the normal
gate reason list is empty. That means the candidate must already have:

```text
root authority
allowed L5 or L6 action level
allowed browser organ kind
special authority
valid evidence refs
passing budget
valid organ contract
no provider/model override
no unsafe payload
```

L7 remains non-promoted through this runtime path. L6 is promoted only for
`browser_form_submit_special_authority`; login, upload, download, and JS remain
organ-level contracts outside the canonical runtime dispatcher until separate
packs promote them explicitly.

## PowerLab Semantics

`operator_browser_l5_template` is now an executable runtime config only when
`enable_organ_dispatch=True`.

`browser_form_submit_l6_template` is now an executable runtime config only when
`enable_organ_dispatch=True`. It does not enable login, credential use, upload,
download, payment, or arbitrary JavaScript.

Still non-executing:

```text
browser_login_l6_template
browser_file_quarantine_l6_template
browser_js_sandbox_l6_template
full_power_template
```

## Evidence

New tests:

```text
test_power_lab_promotes_operator_browser_l5_template_to_executable_runtime_config
test_default_runtime_still_blocks_browser_l5_session_manager
test_browser_l6_high_risk_templates_remain_non_executing_except_form_submit
test_browser_live_runtime_blocks_l6_submit_login_credential_surfaces
test_runtime_executes_browser_l5_session_manager_open_with_receipt_and_finalgate
test_runtime_preserves_l5_browser_session_across_open_and_observe
test_runtime_executes_l6_non_sensitive_form_submit_with_persisted_l5_session
test_dispatcher_routes_browser_l5_session_manager_through_gate_to_runtime
test_dispatcher_routes_l5_open_then_l6_form_submit_through_runtime
test_agentruntime_run_routes_browser_l5_session_manager_when_explicitly_opted_in
```

Executed checks:

```text
python -m pytest tests/test_browser_runtime_unification_l5_l6_dispatch_lock.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_browser_session_manager_l5_live.py tests/test_browser_form_submit_special_authority_l6.py -q
python -m pytest tests/test_delegated_action_gate_model_v0.py tests/test_organ_execution_agentruntime_opt_in.py tests/test_browser_readonly_preparation_agentruntime_opt_in.py tests/test_browser_semantic_extraction_agentruntime_opt_in.py -q
python -m pytest tests/test_brain_to_organ_runtime_closed_loop.py tests/test_brain_native_candidate_source_and_memory_feedback_lock.py tests/test_agent_runtime.py -q
python -m pytest tests/test_browser_operator_agent_l4_l5_live.py tests/test_browser_trajectory_planner_l5.py -q
python -m pytest tests/test_browser_login_credential_session_broker_l6.py tests/test_browser_download_upload_quarantine_l6.py tests/test_browser_js_sandbox_special_authority_l6.py -q
python -m pytest tests/test_low_risk_local_artifact_executor_l2.py tests/test_reversible_workspace_action_executor_l3.py tests/test_low_risk_execution_finalgate_receipts.py -q
```

All targeted tests above passed.

## Anti-Overclaim

This is not a full browser final capability lock.

Closed:

```text
L5 browser session manager through runtime/dispatcher = CLOSED
L6 non-sensitive form submit through runtime/dispatcher = CLOSED
```

Not closed:

```text
L6 login/file quarantine/JS through runtime/dispatcher = NOT_STARTED
Live DevTools/CDP runtime adapter = NOT_STARTED
Persistent multi-session runtime registry = NOT_STARTED
Generic browser login/submit/upload/download = NOT_STARTED
Credential-backed runtime use = NOT_STARTED
```

## Next Pack

```text
BROWSER_RUNTIME_UNIFICATION_L6_LOGIN_FILE_JS_DISPATCH_LOCK
```

Goal: promote login broker, file quarantine, and JS sandbox through the same
runtime/dispatcher path, one by one, with explicit special authority and no
default-on behavior.
