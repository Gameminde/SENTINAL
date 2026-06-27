# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.16 READ-ONLY PROVIDER REPLY ENVELOPE UNWRAP FIX REPORT

Date: 2026-06-27

Status: LOCALLY IMPLEMENTED CANDIDATE

Provider calls during this pack: 0

Pack 4 started: no

Push performed: no

## 1. Trigger Evidence

Attempt 5K-B reached the real Aliyun / DeepSeek read-only decision lane once and stopped before any material tool action:

```text
verdict = ATTEMPT_5K_B_VALID_FAILED_PROVIDER_REACHED
outcome_category = C / BLOCKED_BEFORE_RECEIPT_EXTRACTION_FAILURE
provider_calls_total = 1
cockpit_provider_calls = 0
read_only_decision_calls = 1
final_report_calls = 0
tool_calls_material = 0
successful_receipts = 0
FinalGate accepted = false
MissionKernel status = blocked
workspace unchanged = true
replay material deltas = 0
```

Safe retained diagnostics showed the model-visible object that reached read-only validation had the generic envelope shape:

```text
protocol_version = read_only_research_decision_v1
parse_stage = read_only_provider_blocked
json_object_detected = true
top_level_type = dict
top_level_key_names = metadata, reply
canonical decision = null
Gate = not_reached
provider_response_hash = 8038cea5eca9016284f3e1af22562d238e832706aa283e5e22c659ef4de99e39
```

Root cause:

```text
READ_ONLY_PROVIDER_REPLY_ENVELOPE_NOT_UNWRAPPED
```

The product route, explicit bootstrap, dispatcher, read-only spine startup, FinalGate rejection, replay purity, and workspace immutability were already proven by Attempt 5K-B. The missing link was model-interface normalization from a generic provider/model reply envelope into the Pack 3.13 canonical read-only decision extractor.

## 2. Endpoint Hash Drift Check

Safe facts from the retained Attempt 5K-B artifacts:

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = 57ea92c0436d5e76e879dbc39a2e41a14abeba344dff778483dd97a24a41b2d8
endpoint_source = catalog_default_explicit_process_env
model_contract_ref = model_contract:aliyun_dashscope:aliyun_openai_compatible_chat:deepseek-v4-pro:<hash>
```

Earlier real-model evidence used endpoint hash:

```text
96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
```

Interpretation:

```text
provider/backend/model changed = no retained evidence of change
base URL or endpoint material changed = yes, endpoint hash differs
5K-B used the explicit Aliyun / DeepSeek model contract path = yes, by safe model_contract_ref and telemetry
wrong endpoint/contract proven = no
effect on metadata/reply envelope observation = not proven
```

The drift is a comparability risk for future real-provider runs, not evidence that Attempt 5K-B used the wrong provider or wrong model. Future runbooks should pin and report the intended Aliyun base URL source before the provider call. This pack proceeds because the retained failure is at the in-process model-interface boundary after a callable provider response was received.

## 3. Fix Design

The read-only provider decision client now treats supported generic envelopes as transport/interface wrappers, not as `ReadOnlyDecision` objects.

Supported envelope keys:

```text
reply
message
content
output
result
response
```

Supported envelope values:

```text
dict containing a Pack 3.13-supported decision dialect
string containing one parseable JSON object
single fenced JSON object containing a supported decision dialect
```

Flow:

```text
provider visible content
-> parsed object
-> detect supported envelope
-> ignore only safe scalar metadata
-> extract envelope value in memory only
-> parse dict / JSON string / fenced JSON
-> pass parsed object to Pack 3.13 extractor
-> strict ReadOnlyDecision validation
-> unchanged Gate / governed tool execution / receipts
```

No action is inferred from prose, metadata, or defaults.

## 4. Authority And Metadata Boundaries

Metadata remains non-authoritative:

```text
metadata never creates action
metadata never creates authority
metadata object is blocked unless it is the existing provider-blocked sentinel path
safe scalar metadata may be ignored for extraction only
```

Unsafe fields are rejected in the wrapper or inside the envelope value:

```text
shell
write_file
delete_file
modify_file
credential_access
payment
send_email
browser_click
network_request
authority
authority_scope
approval_scope
can_execute
can_grant_authority
workspace_ref
model_contract_ref
budget
credentials
authorization
raw_prompt
raw_response
raw_reasoning
reasoning
reasoning_content
provider_wrapper
```

Raw provider material remains non-persistent:

```text
raw prompt = not persisted
raw provider response = not persisted
raw visible reply = not persisted
raw reasoning / reasoning_content = not persisted
provider wrapper payload = not persisted
```

## 5. Diagnostics

Envelope failures retain structure-only diagnostics:

```text
envelope_detected
envelope_key
envelope_value_type
envelope_json_detected
envelope_parse_status
model_top_level_key_names
metadata_key_present
safe_metadata_ignored
detected_action_field_names
detected_argument_field_names
missing_required_canonical_fields
unsafe_field_name_hashes
provider_response_hash
diagnostic_retention_status
```

Unsafe field names are represented by diagnostic hashes where needed. Raw reply text, field values, hidden reasoning, credentials, and provider wrapper payloads are not retained in diagnostics.

## 6. Local Proof

New fake-provider tests prove:

```text
metadata + reply dict -> list_directory receipt in first-receipt mode
metadata + reply JSON string -> list_directory receipt
metadata + fenced JSON reply -> list_directory receipt
message dict with next_step dialect -> list_directory receipt
prose-only reply -> blocked, no receipt
metadata-only object -> blocked, no receipt
metadata-supplied action -> blocked, no receipt
unsafe write action in reply -> blocked, no receipt
workspace/model/authority-style control field in reply -> blocked, no receipt
raw reasoning/raw response style field in reply -> blocked, no receipt
unsafe metadata object -> blocked, no receipt
replay after success and failure remains non-reexecuting
```

The tests use deterministic fake provider output only. No real provider call is made.

## 7. Remaining Risk

Pack 3.16 does not prove a new real-provider receipt. It prepares the next real run by removing the observed `metadata` / `reply` envelope mismatch while preserving strict validation and authority boundaries.

Remaining real-provider risks:

```text
reply may contain non-JSON prose only
reply may contain a JSON object with no supported action dialect
reply may contain unsupported action names
future endpoint/base URL pinning should be made explicit in the runbook
```

## 8. Validation

Focused local validation:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py -k pack3_16 -q
= 11 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py sentinel-control/services/sentinel-core/tests/operator/test_model_decision_extractor_pack3_13.py -q
= 51 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py -q
= 26 passed

py -3.13 -O -m pytest sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py sentinel-control/services/sentinel-core/tests/operator/test_model_decision_extractor_pack3_13.py sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py -k "pack3_16 or pack3_13 or pack3_14 or pack3_15" -q
= 38 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/read_only_model_clients.py sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py
= passed

git diff --check
= passed, Windows CRLF warnings only
```

Targeted safety scans:

```text
strict secret scan = no matches
raw-provider/fallback/provider-native material scan = expected guard/test/report strings only
```

No provider call, no push, and no Pack 4 work occurred during this pack.
