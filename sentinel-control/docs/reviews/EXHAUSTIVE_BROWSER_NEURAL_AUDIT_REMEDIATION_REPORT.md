# Exhaustive Browser Neural Audit Remediation Report

Date: 2026-06-03

Status: `IMPLEMENTED / VERIFIED LOCALLY`

Scope:

- browser runtime L5/L6 hardening;
- browser neural cortex / squad / gauntlet safety invariants;
- receipts, FinalGate, memory replay, EventBus, authority validators;
- local artifact and reversible workspace path safety;
- credential/provider override firewalls;
- mission runner revocation handling;
- existing reality activation and desktop L6 leakage review.

This report is an audit/remediation record, not a new power activation pack.
No default-on execution, provider fallback, generic browser login, generic
upload/download, arbitrary JavaScript outside the sandbox, API mutation, channel
send, shell, desktop action, payment, spend, or trading execution was added.

## Executive Verdict

Sentinel's browser/runtime stack is materially stronger after this pass:

```text
Full test suite = GREEN locally
Collected tests after final hardening = 2145
Observed full-suite command = py -3.13 -m pytest -q exited 0
Observed full-suite failures = 0
Browser L5/L6 opt-in runtime path = preserved
Browser neural feedback/ledger/squad = tested
Failure receipt / FinalGate posture = hardened
Default-off execution posture = preserved
Raw credential persistence = not introduced
```

After the first full-suite run, additional strict-boolean and browser cleanup
hardening tests were added, then the complete local suite was rerun and exited
successfully.

The most important repair is not a new feature. It is that dangerous or
exceptional paths now preserve the Sentinel law: failures are represented as
governed data with safe summaries, receipts, FinalGate-compatible evidence, and
no authority expansion.

## Audit Method

The audit used four passes:

1. Read and inspect current dirty diff across browser runtime, neural browser,
   credentials, EventBus, FinalGate, memory replay, L2/L3, mission runner, and
   tests.
2. Reproduce failures with targeted tests before applying fixes where possible.
3. Apply root-cause fixes rather than symptom-only changes.
4. Run targeted suites and then the complete local pytest suite.

Additional sidecar agents were requested for independent review, but they did
not return useful results before the local verification completed.

## Bugs Found And Fixed

### 1. Mission revocation downgraded to generic action failure

Status: `CLOSED`

Files:

- `sentinel/mission/runner.py`
- `tests/test_mission_kernel.py`
- `tests/test_mission_runner_browser_operator_route_rejected.py`

Problem:

`MissionRevokedException` could be caught by a broad executor exception path and
reported as a generic `ACTION_BLOCKED` instead of a mission revocation.

Fix:

The runner now preserves `MissionRevokedException` identity, emits
`MISSION_REVOKED`, marks the mission as revoked, and avoids generic failure
downgrade.

### 2. Reality activation read receipts exposed raw file content

Status: `CLOSED`

Files:

- `sentinel/organs/reality_activation.py`
- `tests/test_p6_existing_organs_reality_activation.py`

Fix:

`DesktopWorkspaceOperator.read_file()` receipts now include byte count and
content hash only, not raw file content.

### 3. Desktop Workspace L6 path proof could be forged

Status: `CLOSED`

Files:

- `sentinel/organs/desktop/workspace_l6.py`
- `tests/test_p6_desktop_workspace_l6.py`

Fix:

Receipts now include `workspace_root` and `path_containment_proof_hash`.
FinalGate recomputes containment proof and rejects forged or out-of-root paths.

### 4. Browser dispatcher could leave persistent sessions orphaned

Status: `CLOSED`

Files:

- `sentinel/agent/organs/runtime_execution.py`
- `sentinel/agent/organs/organ_dispatch.py`
- browser runtime dispatch tests.

Fix:

`close_browser_runtime_sessions_for_config()` closes dispatcher-owned browser
session managers at batch end. Direct lower-level runtime calls still keep
explicit persist-session semantics across calls.

### 5. Browser dispatcher exception path could miss cleanup

Status: `CLOSED`

Files:

- `sentinel/agent/organs/organ_dispatch.py`
- `tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py`

Problem:

The dispatcher closed batch-scoped persistent browser sessions on normal return,
but a raised exception from `_execute_candidate()` after a browser manager was
created could skip cleanup.

Fix:

`OrganDispatcher.dispatch()` now closes the browser runtime session cache for
the mission/config before re-raising candidate execution exceptions.

Proof:

- `test_organ_dispatch_closes_persistent_browser_session_cache_when_candidate_execution_raises`

### 6. Browser session close failure could leave stale open state

Status: `CLOSED`

Files:

- `sentinel/agent/organs/browser_session_manager_l5_live.py`
- `tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py`

Fix:

`_LiveBrowserSession.close()` now marks `closed=True` in a `finally` block even
if the live backend throws during close.

Proof:

- `test_live_browser_session_marks_closed_even_if_backend_close_raises`

### 7. Browser download save failure could leave partial quarantine artifacts

Status: `CLOSED`

Files:

- `sentinel/agent/organs/browser_session_manager_l5_live.py`
- `tests/test_browser_download_upload_quarantine_l6.py`

Problem:

The download quarantine cleanup block began after `download.save_as()`. If
`save_as()` created a partial `.part` file and then raised, cleanup could be
skipped.

Fix:

`download.save_as()` is now inside the cleanup `try` block.

Proof:

- `test_l6_download_save_as_failure_removes_temp_artifact`

### 8. Browser L5/L6 preflight failure could bypass organ-specific receipt shape

Status: `CLOSED`

Files:

- `sentinel/agent/organs/runtime_execution.py`

Fix:

Browser session, form submit, login, upload/download quarantine, and JS sandbox
preflight blocks now produce organ-specific blocked results and certificates
where a typed sub-request exists.

### 9. Browser blocked reason contract was inconsistent

Status: `CLOSED`

Files:

- `sentinel/agent/organs/runtime_execution.py`

Fix:

Canonical global reasons remain unprefixed; browser-local reasons keep their
browser prefix; generic organ-local reasons are prefixed deterministically.

### 10. OrganDispatch boolean parsing accepted truthy strings unsafely

Status: `CLOSED`

Files:

- `sentinel/agent/organs/organ_dispatch.py`

Fix:

Special-authority browser flags now use strict boolean parsing. Invalid boolean
strings fail closed.

### 11. Unknown browser session/file action kinds fell back to active defaults

Status: `CLOSED`

Files:

- `sentinel/agent/organs/organ_dispatch.py`

Fix:

Unknown browser session/file action kinds now return `None` and no typed
sub-request is built.

### 12. EventBus payload immutability broke dict/list compatibility

Status: `CLOSED`

Files:

- `sentinel/shared/events.py`
- `sentinel/agent/evidence.py`
- `tests/test_agent_event_bus.py`

Fix:

Introduced JSON-compatible `FrozenDict` and `FrozenList`, with mutation methods
blocked, deepcopy stable, and serializers that thaw to plain data. Event
payloads now also require a top-level mapping instead of accepting arbitrary
scalar/list payload shapes.

### 13. Credential expiration boundary allowed access at the exact expiry instant

Status: `CLOSED`

Files:

- `sentinel/organs/credentials/foundation.py`
- `sentinel/organs/credentials/vault_policy.py`
- `sentinel/organs/credentials/scoped_grant.py`
- credential foundation and P6 vault policy tests.

Problem:

Some credential grant and credential ref checks used `now > expires_at`, leaving
the exact expiration instant still active.

Fix:

Credential foundation, scoped vault policy, and scoped grant activity now treat
`now >= expires_at` as expired/inactive.

Proof:

- `test_grant_blocks_access_at_exact_expiration_boundary`
- `test_policy_blocks_grant_at_exact_expiration_boundary`
- `test_policy_blocks_credential_ref_at_exact_expiration_boundary`
- `test_scoped_credential_grant_inactive_at_exact_expiration_boundary`

### 14. EvidenceChainReviewer expected only mutable lists

Status: `CLOSED`

Files:

- `sentinel/agent/evidence.py`

Fix:

Reviewer now accepts `list` and `tuple` for evidence and contradiction refs.

### 15. Browser V3 authority grant metadata false positives

Status: `CLOSED`

Files:

- `sentinel/mission/models.py`

Fix:

Validator now permits safe metadata paths such as `authority_class`, `id`, and
`blocked_flow_types`, while still rejecting secrets, provider override,
authority expansion, runtime payload, unsafe browser payloads, and credential
payloads.

### 16. Credential grant metadata accepted unsafe payload classes

Status: `CLOSED`

Files:

- `sentinel/mission/models.py`

Fix:

Credential grants are explicitly metadata-only and reject secret-like material,
provider override, authority expansion, external action payloads, credential
dangerous payloads, and unsafe runtime payloads.

### 17. Pydantic warning from unvalidated test model copy

Status: `CLOSED`

Files:

- `tests/test_agent_core_final_gate.py`

Fix:

The test now updates `trace_refs` with a tuple rather than a list when using
`model_copy`.

### 18. Full-scale perf benchmark failed on nearly full disk

Status: `CLOSED / ENVIRONMENT-AWARE`

Files:

- `tests/perf/hot_cold/test_phase_b_benchmarks.py`

Fix:

Full-scale perf tests now skip with an explicit low-disk reason when temp disk
is insufficient, and rollback checks `conn.in_transaction`.

### 19. Dispatcher and controlled browser runner used Python truthiness for string flags

Status: `CLOSED`

Files:

- `sentinel/agent/organs/organ_dispatch.py`
- `sentinel/organs/browser/controlled_runner.py`
- `tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py`
- `tests/test_agent_browser_v3_form_submit.py`

Problem:

Several authority-sensitive or evidence-shaping flags were parsed with
`bool(value)`. In Python, `"false"` is truthy, so raw metadata could make
`allow_overwrite`, `allow_delete`, `allow_cross_origin`, storage/body capture,
or screenshot/PDF capture behave differently than the operator intended.

Fix:

Dispatcher L2/L3/browser special-authority builders now use strict boolean
parsing. The controlled browser runner now uses a local boolean parser that
preserves existing missing-value defaults while preventing `"false"` from
becoming enabled behavior.

Proof:

- `test_organ_dispatch_l2_l3_contract_booleans_are_strict_not_truthy_strings`
- `test_organ_dispatch_browser_capture_screenshot_boolean_is_strict`
- `test_controlled_runner_boolean_arguments_do_not_treat_false_strings_as_true`

## Current Browser Stack Status

```text
Browser ReadOnly / Preparation / Semantic Extraction = CLOSED / opt-in
Browser L5 live session manager = CLOSED / opt-in
Browser L6 form submit special authority = CLOSED / opt-in
Browser L6 login credential session broker = CLOSED / opt-in with ephemeral provider
Browser L6 upload/download quarantine = CLOSED / opt-in
Browser L6 JS sandbox = CLOSED / opt-in
Browser neural signal graph and perception neurons = CLOSED
Browser neural motor proposals through dispatcher = CLOSED
Browser neural memory feedback = CLOSED
Durable browser neural receipt ledger foundation = CLOSED
Browser multi-agent operator squad = CLOSED
Browser neural gauntlet = CLOSED
```

Important boundary:

`CLOSED` here means contract/runtime/test closure for the Sentinel-governed
surface. It does not mean generic default-on browser power, unbounded login,
unbounded upload/download, arbitrary JS, uncontrolled MCP, payment, external API
mutation, or shell execution.

## Safety Boundaries Rechecked

```text
Default-on organ execution = REJECTED
Provider/backend/model override through dispatch = REJECTED
Raw credential persistence = NOT_STARTED
Generic browser login = NOT_STARTED
Generic browser upload/download = NOT_STARTED
Arbitrary JS outside sandbox = REJECTED
API mutation = NOT_STARTED
Channel send = NOT_STARTED
Shell/process execution = NOT_STARTED
Desktop action beyond governed workspace file I/O = NOT_STARTED
Payment/spend/trading live execution = NOT_STARTED
Memory/replay/receipt as authority = REJECTED
FinalGate as future permission = REJECTED
```

## Verification Commands Run

Targeted suites:

```text
py -3.13 -m pytest tests/test_mission_kernel.py tests/test_mission_runner_browser_operator_route_rejected.py tests/test_p6_existing_organs_reality_activation.py tests/test_p6_desktop_workspace_l6.py -q
py -3.13 -m pytest tests/test_agent_event_bus.py tests/test_trace_hash_property.py -q
py -3.13 -m pytest tests/test_low_risk_local_artifact_executor_l2.py tests/test_reversible_workspace_action_executor_l3.py -q
py -3.13 -m pytest tests/test_browser_js_sandbox_special_authority_l6.py tests/test_browser_download_upload_quarantine_l6.py tests/test_browser_runtime_unification_l6_login_file_js_dispatch_lock.py tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py tests/test_browser_runtime_unification_l5_l6_dispatch_lock.py tests/test_browser_runtime_agentruntime_full_browser_stack_lock.py -q
py -3.13 -m pytest tests/test_browser_neural_safety_invariants_audit_lock.py tests/test_browser_neural_gauntlet_lock.py tests/test_browser_multi_agent_operator_squad_lock.py tests/test_durable_receipt_ledger_foundation.py tests/test_browser_neural_memory_feedback_lock.py tests/test_motor_neuron_to_organ_dispatch_lock.py tests/test_browser_neural_cortex_v0a_signal_graph.py tests/test_browser_neural_cortex_v0b_motor_proposal.py -q
py -3.13 -m pytest tests/test_mission_authority_and_credential_vault_foundation.py tests/test_real_model_execution_backend.py tests/test_openai_compatible_provider_base.py tests/test_p6_credential_vault_policy.py tests/test_model_provider_catalog.py tests/test_runtime_model_execution_wiring.py -q -rs
py -3.13 -m pytest tests/test_brain_native_candidate_source_and_memory_feedback_lock.py tests/test_brain_to_organ_runtime_closed_loop.py tests/test_delegated_action_gate_model_v0.py tests/test_organ_proposal_bridge.py tests/test_organ_safety_scanner_consolidation.py tests/test_sentinel_power_lab_runtime_v0.py -q
py -3.13 -m pytest tests/test_browser_final_capability_lock.py tests/perf/hot_cold/test_phase_b_benchmarks.py -q
py -3.13 -m pytest tests/test_agent_core_final_gate.py::test_core_final_gate_rejects_controlled_execution_missing_policy_or_capture_trace_refs -q
py -3.13 -m pytest tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py -q
py -3.13 -m pytest tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py tests/test_agent_browser_v3_form_submit.py tests/test_agent_browser_v3_upload_authorized.py -q
```

Full suite:

```text
py -3.13 -m pytest -q
$lines = py -3.13 -m pytest --collect-only -q; ...; COLLECTED_COUNT=2145
```

Observed final full-suite result:

```text
Collected tests = 2145
Full-suite command exit code = 0
Failed = 0
```

During this audit, the local C: drive repeatedly approached very low free disk
after full-suite runs, so low-disk perf skips are expected and explicit where
they occur.

## Residual Risks

### Disk and persistence infrastructure

Status: `OPEN`

Sentinel needs a dedicated test artifact root or CI disk budget for full-scale
perf gates.

### Browser backend breadth

Status: `OPEN / NEXT POWER WORK`

The governed L5/L6 stack exists, but true elite browser operation still needs
more live backend breadth, recovery intelligence, observability, and benchmark
gauntlets against real multi-step tasks.

### Durable EventBus / WAL

Status: `OPEN`

EventBus payload safety is improved, but durable event persistence remains a
separate pack.

### Runtime and FinalGate size

Status: `OPEN / ARCHITECTURE DEBT`

`runtime.py` and `final_gate.py` remain large. This pass avoided decomposition
because the user requested power/audit hardening, not a refactor-only pack.

## Next Recommended Pack

`BROWSER_NEURAL_OPERATOR_CORTEX_HARDENED_LIVE_BACKEND_LOCK`

Purpose:

- live backend adapter hardening;
- multi-step task continuation under one session graph;
- richer failure recovery using DOM + AX + screenshot + network + console;
- stronger browser neural blackboard scoring;
- observability/replay improvements;
- optional Chrome DevTools/CDP adapter behind Sentinel authority.

The pack should remain opt-in and governed, but it should target real browser
mission power, not another read-only/spec-only loop.
