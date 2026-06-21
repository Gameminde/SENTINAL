# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.5 - Cockpit V2 Product Route Activation Fix

## Verdict

```text
PACK_3_5_COCKPIT_V2_PRODUCT_ROUTE_ACTIVATION_FIX = LOCALLY_IMPLEMENTED
real provider call during this pack = NO
Pack 4 started = NO
push performed = NO
```

Pack 3.5 fixes the concrete Attempt 4C blocker:

```text
Attempt 4C classification = VALID_FAILED_PROVIDER_REACHED
mission created = NO
provider calls = 1
observed parse_stage = legacy_operator_decision_validation
root cause = governed CLI product route did not force Cockpit Mission Understanding V2 validation
```

## Attempt 4C Evidence

Attempt 4C proved that the Aliyun / DeepSeek route was reachable and that the earlier BOM/static input blockers were closed. The mission still was not created because the first provider response was validated by the legacy broad `OperatorLLMDecisionResult` path.

Safe observed fields:

```text
parse_stage = legacy_operator_decision_validation
missing_required_field_names = ["reply"]
protocol_version = unknown
json_object_detected = true
mission_created = NO
```

That was inconsistent with Pack 3.3, whose intended product protocol is:

```text
protocol_version = cockpit_mission_understanding_v2
parser = CockpitMissionUnderstandingV2
canonicalization = Sentinel-owned
```

## Where Legacy Validation Entered

Before Pack 3.5:

```text
CLI cockpit product route
-> LLMLiveOperatorCockpit
-> OperatorConversationEngine
-> OperatorLLMConversationAdapter
-> validate_operator_structured_output(raw_output)
-> if raw_output.protocol_version == cockpit_mission_understanding_v2:
     V2 validation
   else:
     legacy OperatorLLMDecisionResult validation
```

So a provider object missing `protocol_version` fell back to:

```text
parse_stage = legacy_operator_decision_validation
```

This made the real product route diagnostics look like the old broad schema even though the route was supposed to be V2-only.

## Wiring Fix

Pack 3.5 adds a product-route requirement flag:

```text
LLMLiveOperatorCockpit(require_mission_understanding_v2=True)
-> OperatorConversationEngine
-> OperatorLLMConversationAdapter
-> validate_operator_structured_output(required_protocol_version="cockpit_mission_understanding_v2")
```

The flag is enabled in the governed CLI product route:

```text
py -3.13 -m sentinel.cli cockpit --model-contract ... --authority-scope ... --workspace ... --script ... --json
```

It is not enabled for the explicit legacy-internal direct route. Existing legacy/direct tests remain isolated.

## Provider-Facing Prompt Proof

The rendered cockpit prompt now explicitly says:

```text
Use protocol_version exactly "cockpit_mission_understanding_v2".
Do not emit legacy OperatorLLMDecisionResult, MissionStartProposal, OperatorIntent, MissionDraft, or MissionAuthoritySummary objects.
```

The provider-facing object remains narrow. The model is asked only for a V2 mission-understanding object. It is not asked to create:

```text
OperatorIntent
MissionDraft
MissionAuthoritySummary
MissionStartProposal
approval_scope
workspace_ref
model_contract_ref
authority envelope
internal ids
can_execute
```

Sentinel remains responsible for canonicalization and executable product binding.

## V2 Diagnostics Contract

For governed product LLM mode, malformed first-turn output now produces safe V2 diagnostics:

```text
protocol_version = cockpit_mission_understanding_v2
parse_stage = mission_understanding_v2_validation
json_object_detected = true
top_level_key_names = [...]
missing_required_field_names = [...]
unknown_field_names = [...]
validation_error_codes = [...]
validation_error_paths = [...]
provider_response_hash = <safe hash only>
```

The diagnostics do not persist:

```text
raw provider response
raw prompt
raw visible output
raw reasoning
field values
credentials
authorization material
provider wrapper payload
```

## Approval No-Second-Call Proof

The existing CLI product wiring test remains green and proves the successful product route uses this call pattern:

```text
cockpit mission-understanding call
-> approval turn
-> exploration decision call
-> exploration decision call
-> final report call
```

The approval turn does not call the cockpit provider again. It deterministically starts the mission from:

```text
stored MissionDraft
stored MissionAuthoritySummary
ProductExecutionBinding.workspace_ref
ProductExecutionBinding.model_contract_ref
MissionAuthorityApprovalScope
```

## Workspace And Model Contract Request Proof

The focused CLI product wiring test verifies the persisted `MissionExecutionRequest` contains:

```text
workspace_ref = workspace:<absolute resolved path>
model_contract_ref = model_contract:<provider>:<backend>:<model>:<hash>
```

It also verifies the old executable fallback ref is not used:

```text
model_contract_ref != model_contract:operator_session
```

## Tests Added

Pack 3.5 adds CLI-product-route tests proving:

1. A malformed first-turn object in the actual CLI route reports `mission_understanding_v2_validation`, not `legacy_operator_decision_validation`.
2. The actual CLI route rejects model-supplied `workspace_ref`, `model_contract_ref`, `approval_scope`, and `can_execute` through V2 diagnostics.
3. The actual product prompt contains the explicit V2 protocol instruction and legacy-output prohibition.

## Focused Validation Performed

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py -k "requires_v2_mission_understanding_diagnostics or rejects_model_supplied_bindings_with_v2_diagnostics or prompt_is_v2_product_protocol"
result: 3 passed

py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py
result: 12 passed

py -3.13 -m pytest -q tests/test_cockpit_mission_understanding_protocol_v2.py
result: 21 passed

py -3.13 -m pytest -q tests/test_llm_operator_model_client_v0.py tests/test_llm_operator_adapter_v0.py
result: 19 passed
```

Additional focused validation:

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/test_llm_operator_model_client_v0.py tests/test_llm_operator_adapter_v0.py
result: 52 passed

py -3.13 -O -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_cockpit_mission_understanding_protocol_v2.py
result: 33 passed

py -3.13 -m pytest -q tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py tests/operator/test_product_nervous_system_pack3.py
result: 31 passed

py -3.13 -m compileall -q sentinel
result: passed

git diff --check
result: passed, Windows CRLF warnings only

targeted secret scan
result: no API key, bearer token, or authorization material found in modified/untracked files

targeted raw-provider/fallback/provider-native scan
result: only expected doctrine, validation, hashing, and non-persistence test strings found; no provider-native tool integration or fallback/AUTO provider routing added
```

## Remaining Limits

```text
Pack 3.5 does not prove a new real-provider mission.
Pack 3.5 does not start Pack 4.
Pack 3.5 does not add another capability.
Pack 3.5 does not change maturity scores.
```

The next real attempt should now fail, if it fails, with:

```text
parse_stage = mission_understanding_v2_validation
```

If the model returns valid V2 output, the second approval turn should create and queue the mission through the existing Pack 3.4 workspace-bound product path.
