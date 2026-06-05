# Power Actuator Fabric Wave 1 Self-Audit Remediation Report

Recorded at: 2026-06-05

## Verdict

```text
POWER_ACTUATOR_FABRIC_WAVE_1_SELF_AUDIT_REMEDIATION = CLOSED
POWER_ACTUATOR_FABRIC_WAVE_1 = LOCKED
```

The Wave 1 actuator fabric has been audited after the orchestration demo. The
audit covered PowerRuntime, sandbox shell/code, external API, channel
draft/send, the orchestration demo, focused tests, and truth docs.

## Findings Treated

```text
ADAPTER_MISLABELED_STEP_BYPASS = CLOSED
SHELL_OUTPUT_CAP_NON_WEAKENING = CLOSED
EXTERNAL_API_AUTH_HEADER_NAME_GAPS = CLOSED
RECEIPT_MEMORY_AS_AUTHORITY_REF_DRIFT = CLOSED
POWER_DEMO_IMPORT_CYCLE = CLOSED
DOCS_STALE_NEXT_PHASE_OVERCLAIM = CLOSED
POWER_DEMO_RAW_BODY_RECIPIENT_DURABILITY = CLOSED
PROVIDER_FALLBACK_AUTO_SCAN = CLOSED
RAW_SECRET_PERSISTENCE_SCAN = CLOSED
```

## Fixes

Adapter admission guards:

```text
External API adapter requires actuator_family=external_api, organ_kind=external_api, action_kind=request.
Channel adapter requires actuator_family=channel, organ_kind=channel_draft_send, action_kind=draft/send.
Shell adapter requires actuator_family=shell_sandbox, organ_kind=sandbox_shell_code, action_kind=run_command.
```

Shell output cap:

```text
effective_output_max_bytes = min(request.output_max_bytes, contract.max_output_bytes)
```

External API header guard:

```text
Authorization, Proxy-Authorization, Cookie, Set-Cookie, X-Api-Key,
X-Api-Token, X-Auth-Token, and session-token-style headers are rejected by
name before transport.
```

Authority ref drift:

```text
API mutation and channel send reject receipt, FinalGate, certificate, memory,
replan, and timeline-shaped refs as authority refs.
```

Demo import cycle:

```text
sentinel.power.__init__ now lazy-loads run_power_fabric_orchestration_demo.
```

Docs truth repair:

```text
README and roadmaps now identify the demo as fixture-backed where needed and
point next phase to MISSION_DAEMON_AND_OPERATOR_SHELL_V0 after this lock.
```

## Test Evidence

Targeted checks:

```text
py -3.13 -m pytest tests/test_external_api_read_write_organ_v1.py::test_external_api_rejects_receipt_or_memory_as_mutation_authority_ref tests/test_channel_draft_send_organ_v1.py::test_channel_rejects_receipt_or_memory_as_send_authority_ref -q
2 passed

py -3.13 -m pytest tests/test_external_api_read_write_organ_v1.py::test_external_api_power_executor_blocks_mislabeled_step_before_transport tests/test_channel_draft_send_organ_v1.py::test_channel_power_executor_blocks_mislabeled_step_before_sender tests/test_sandbox_shell_code_organ_v1.py::test_shell_code_power_executor_blocks_mislabeled_step_before_subprocess -q
3 passed

py -3.13 -m pytest tests/test_external_api_read_write_organ_v1.py::test_external_api_rejects_raw_auth_cookie_token_headers tests/test_external_api_read_write_organ_v1.py::test_external_api_allows_credential_ref_as_metadata_only_without_raw_secret tests/test_sandbox_shell_code_organ_v1.py::test_shell_code_sandbox_contract_output_cap_cannot_be_weakened -q
3 passed
```

Focused Wave 1 slice:

```text
py -3.13 -m pytest tests/test_power_fabric_orchestration_demo.py tests/test_channel_draft_send_organ_v1.py tests/test_external_api_read_write_organ_v1.py tests/test_sandbox_shell_code_organ_v1.py tests/test_sentinel_power_runtime_v0.py -q
40 passed
```

Gate/proposal regression:

```text
py -3.13 -m pytest tests/test_delegated_action_gate_model_v0.py tests/test_organ_proposal_bridge.py -q
51 passed
```

## Remaining Honest Limits

```text
shell OS/container isolation = DEFERRED
mission daemon/operator shell = NOT_STARTED
real channel connector = NOT_STARTED
durable credential vault = NOT_STARTED
unbounded API mutation = NOT_STARTED
generic browser login/payment/API/channel/shell/desktop = NOT_STARTED
provider fallback/AUTO = NOT_APPROVED
```

The shell sandbox is command-gated and uses `shell=False`, cwd containment, env
scrubbing, timeout, output cap, receipts, and FinalGate. It is not yet a
container or OS-level isolation boundary.
