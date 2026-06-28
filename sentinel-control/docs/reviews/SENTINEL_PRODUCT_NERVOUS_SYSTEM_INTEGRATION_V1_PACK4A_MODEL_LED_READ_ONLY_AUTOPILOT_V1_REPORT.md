# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK4A_MODEL_LED_READ_ONLY_AUTOPILOT_V1_REPORT

## Verdict

```text
PACK_4A_MODEL_LED_READ_ONLY_AUTOPILOT_V1 = LOCALLY IMPLEMENTED
provider calls = 0
push = not performed
write/shell/browser/network power = not implemented
```

## Pack 3.20 Accepted State

```text
Attempt 5Q = PRODUCT_FIRST_RECEIPT_ACHIEVED
5Q replay purity = VERIFIED
real provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
route = product cockpit
receipt = readonly_receipt_ab84ac1c46ad40c7a99d9d61b68cbbb1
FinalGate = accepted
mission = completed
workspace unchanged = true
```

Pack 4A starts from that locked receipt proof and extends the same governed read-only route from first receipt to bounded model-led multi-step exploration.

## Pack 4A Design

Pack 4A adds an explicit model-led read-only autopilot mode:

```text
execution_options.model_led_read_only_autopilot = true
execution_options.low_friction_read_only_power_mode = true
execution_options.max_material_receipts = <positive integer>
execution_options.max_provider_decision_calls = <positive integer>
```

CLI flags:

```text
--model-led-read-only-autopilot
--low-friction-read-only-power-mode
--max-material-receipts <n>
--max-provider-decision-calls <n>
```

This mode is available only for the existing governed product route:

```text
capability_id = read_only_research
operation = inspect_repository
explicit bootstrap = required by CLI
approved workspace binding = required by CLI
```

It intentionally does not require:

```text
--stop-after-first-material-receipt
```

and it cannot be combined with first-receipt mode.

## Runtime Changes

Changed runtime files:

```text
sentinel-control/services/sentinel-core/sentinel/cli.py
sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py
sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py
sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py
```

Changed focused tests:

```text
sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py
sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py
```

The implementation reuses:

```text
MissionExecutionRequest.execution_options
UnifiedExecutionDispatcher
ReadOnlyResearchAdapter
ReadOnlyProductionSpineSession
ReadOnlyActionReceipt
ReadOnlyFinalGateCertificate
MissionReplayBuilder / ReadOnlyReplayView
```

No duplicate request, receipt, FinalGate, replay, or dispatcher truth system was added.

## Loop Semantics

Pack 4A loop:

```text
decision call
-> extract/validate canonical ReadOnlyDecision
-> Gate boundary check
-> execute read-only action
-> evidence artifact
-> receipt artifact
-> append safe observation context
-> repeat
```

The loop terminalizes when:

```text
finish_exploration is chosen after at least one observation
OR max_material_receipts is reached
OR max_provider_decision_calls is reached after at least one receipt
```

Terminal success writes one accepted read-only FinalGate with existing material receipt refs. It does not fabricate a finish receipt and does not require report generation in Pack 4A autopilot mode.

## Receipt And Evidence Behavior

Focused fake-provider proof covers:

```text
list_directory -> evidence + receipt
search_text -> evidence + receipt
read_file_segment -> evidence + receipt
```

Each material action still passes the Gate path before execution. Each material observation is persisted as bounded read-only evidence and then receipted.

The next model decision context includes prior safe observations and receipt refs through the existing read-only spine context. The tests verify that the second and third decision calls receive one and two previous observations respectively.

## Budget Behavior

Material receipt budget:

```text
max_material_receipts = 3
```

stops after the third governed material receipt, writes accepted FinalGate reason:

```text
model_led_read_only_autopilot_material_receipt_budget_reached
```

Provider decision-call budget:

```text
max_provider_decision_calls = 1
```

stops after one successful material receipt, writes accepted FinalGate reason:

```text
model_led_read_only_autopilot_provider_decision_budget_reached
```

If budget is reached before any receipt, the spine blocks instead of creating a false success.

## Finish Behavior

`finish_exploration` in Pack 4A:

```text
requires at least one prior successful observation
does not call the report lane
does not create a fake material receipt
accepts FinalGate over existing material receipts
```

FinalGate reason:

```text
model_led_read_only_autopilot_finish_exploration
```

## Unsafe Rejection Proof

Hard blocks remain active:

```text
workspace escape
absolute outside path
write/delete/modify
shell
network/browser/email/payment
credential access
authority escalation
model-supplied workspace/model_contract/authority/budget/can_execute
raw provider/reasoning persistence
fake receipts
fallback/AUTO
provider-native tools
```

Focused Pack 4A test proves `../outside` blocks before receipt creation and terminalizes as `mission_blocked`.

Existing Pack 3.17 and Pack 3.7 regressions continue to prove unsafe tools, path traversal, outside absolute paths, provider-native tool material, and unsafe control fields remain blocked.

## Replay Purity Proof

Pack 4A focused test constructs a `ReadOnlyProductionSpineSession(...).build_replay()` view over the completed autopilot mission and compares pre/post counters:

```text
decision client calls unchanged
report client calls unchanged
MissionRunStore event count unchanged
receipt writes unchanged
failed-attempt writes unchanged
report artifact writes unchanged
FinalGate writes unchanged
dispatch decision writes unchanged
dispatch closeout writes unchanged
mission status unchanged
timeline verification remains true
```

Replay result:

```text
reexecuted = false
```

## Tests Run

Red tests were run first and failed on the expected missing feature boundaries:

```text
py -3.13 -m pytest tests/operator/test_product_nervous_system_pack3.py -k pack4a -q
FAILED with unsupported execution option keys

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py::test_cli_explicit_bootstrap_can_enable_model_led_read_only_autopilot -q
FAILED with unrecognized CLI arguments
```

Green/focused regression tests:

```text
py -3.13 -m pytest tests/operator/test_product_nervous_system_pack3.py -k pack4a -q
4 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py::test_cli_explicit_bootstrap_can_enable_model_led_read_only_autopilot -q
1 passed

py -3.13 -m pytest tests/operator/test_model_decision_extractor_pack3_13.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py -q
60 passed

py -3.13 -m pytest tests/operator/test_product_nervous_system_pack3.py -q
38 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
23 passed

py -3.13 -m pytest tests/operator/test_mission_lifecycle_service.py tests/operator/test_mission_execution_coordinator.py tests/operator/test_runtime_connection_registry.py -q
17 passed

py -3.13 -m pytest tests/test_llm_operator_model_client_v0.py::test_pack3_18_provider_http_error_is_not_wrapped_as_model_authored_reply tests/test_model_provider_catalog.py::test_pack3_18_provider_inventory_reports_safe_facts_without_credentials -q
2 passed
```

## Remaining Limits

Pack 4A does not add:

```text
write power
shell power
browser/network power
credential access
provider-native tools
fallback/AUTO
multi-capability routing
real-provider Attempt 6A execution
```

The next real run remains:

```text
ATTEMPT_6A_MODEL_LED_MULTI_RECEIPT_READ_ONLY_REAL_PROVIDER
```

Success threshold for that future run:

```text
provider decision calls >= 2
material receipts >= 2
FinalGate accepted
mission completed
workspace unchanged
material replay purity held
no fallback/AUTO
no provider-native tools
no raw provider/reasoning/credential persistence
```

## Confirmation

```text
provider call = not performed
push = not performed
Pack 4 write/shell/browser/network power = not implemented
```
