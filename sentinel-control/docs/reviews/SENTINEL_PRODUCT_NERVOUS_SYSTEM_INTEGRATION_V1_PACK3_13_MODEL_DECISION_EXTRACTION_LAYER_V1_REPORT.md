# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.13 MODEL DECISION EXTRACTION LAYER V1 REPORT

## Canonical Scope

Pack 3.13 adds a Sentinel-owned extraction layer for read-only model decisions.

It does not call a real provider, does not start Pack 4, does not add a second
capability, and does not prove a real-provider read-only receipt. It prepares
the next real run to test whether Sentinel can extract a safe canonical action
from model output and produce the first governed read-only receipt.

## Attempt 5I Evidence

Attempt 5I proved the product route reached the dispatched read-only decision
lane and retained safe diagnostics. The retained shape showed:

```text
json_object_detected = true
top_level_type = dict
validation_payload_key_names = [action, arguments, evidence_refs, operator_message]
missing_required_field_names = []
validation_error_codes = [unknown_field]
unknown_field_names = [diagnostic_label_hash:*]
```

This means the route, provider call boundary, bridge diagnostics, blocked
FinalGate, MissionKernel blocking, replay purity, and workspace immutability
were useful. The remaining blocker was strict direct validation against
near-raw model output.

## Why Strict Raw Schema Is Not Product-Viable

Different models commonly express the same tool decision with different
field names. A product route should not require every model to speak the exact
internal Pydantic dialect. Sentinel should translate model dialects into one
internal canonical decision, then validate and govern that decision strictly.

Pack 3.13 therefore changes the product read-only decision path to:

```text
provider visible JSON
-> safe extraction / dialect normalization
-> canonical ReadOnlyDecision payload
-> strict ReadOnlyDecision validation
-> governed action validation
-> read-only execution / receipt or blocked FinalGate
```

Execution uses only the extracted canonical payload. The raw model object is
not used for execution.

## Extractor Architecture

Implementation:

```text
sentinel/operator/model_decision_extractor.py
```

The extractor returns:

```text
ModelDecisionExtractionResult(payload, diagnostics)
```

or raises:

```text
ModelDecisionExtractionError(diagnostics)
```

The canonical payload is:

```json
{
  "action": "list_directory | search_text | read_file_segment | finish_exploration",
  "arguments": {},
  "evidence_refs": [],
  "operator_message": "optional"
}
```

Persisted structural diagnostics use `model_top_level_type` and
`model_top_level_key_names` instead of `raw_top_level_*` because existing event
safety gates reject `raw_*` metadata labels. No raw provider content is
persisted.

## Supported Model Dialects

Action aliases:

```text
action
tool
tool_name
name
next_action
chosen_action
operation
next_step.name
function.name
```

Argument aliases:

```text
arguments
args
params
parameters
input
tool_input
next_step.input
function.arguments
```

Evidence aliases:

```text
evidence_refs
evidence
references
source_refs
receipt_refs
```

Operator message aliases:

```text
operator_message
message
summary
rationale_summary
note
```

Safe scalar provider/adapter metadata is ignored during extraction. Sanitized
diagnostic labels of the form `diagnostic_label_hash:<sha256>` are also ignored
when the canonical decision is otherwise valid.

## Unsafe Rejection Policy

The extractor rejects unsafe action names, including:

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
```

It rejects unsafe control or raw-material fields anywhere in the model object,
including:

```text
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
metadata
```

Unsafe field names are represented only as safe labels when retained in
diagnostics. Field values are not persisted.

## Canonical Validation Proof

Focused extractor tests prove:

```text
canonical action/arguments validates
tool/params validates
tool_name/args validates
next_step.name/input validates
function.name/arguments validates
safe scalar metadata is ignored
diagnostic_label_hash metadata is ignored
missing action fails safely
missing arguments fail unless the action permits empty arguments
unsafe actions and authority/raw/reasoning fields fail closed
```

The read-only product integration tests prove a 5I-shaped object with canonical
keys plus a sanitized diagnostic label no longer blocks before execution.

## Fake Receipt Proof

The focused fake-provider path proves:

```text
tool + params
-> canonical list_directory decision
-> strict validation
-> governed read-only action
-> successful receipt
-> accepted FinalGate
-> MissionKernel COMPLETED
```

This is local proof only. It does not claim a real-provider receipt.

## Blocked FinalGate Proof

The unsafe fake-provider path proves:

```text
tool = write_file
-> extractor rejects unsafe action
-> no successful receipt
-> rejected FinalGate
-> MissionKernel BLOCKED
```

Diagnostics retain only safe structural information such as:

```text
parse_stage = read_only_decision_validation
extraction_failed = true
unsafe_action_names = [write_file]
```

## Replay Purity Proof

Focused tests assert replay does not reexecute the mission route. The validated
zero-delta surfaces include:

```text
model call counts
receipt write counts
FinalGate write counts
reexecuted = false
```

## Validation Run

Commands executed:

```powershell
py -3.13 -m pytest -q tests/operator/test_model_decision_extractor_pack3_13.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py
```

Result: PASS.

```powershell
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_mission_execution_coordinator.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result: PASS.

```powershell
py -3.13 -O -m pytest -q tests/operator/test_model_decision_extractor_pack3_13.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py
```

Result: PASS with the expected pytest warning that Python `-O` disables assert
statements outside test modules/plugins.

```powershell
py -3.13 -m compileall -q sentinel\operator\model_decision_extractor.py sentinel\operator\read_only_model_clients.py tests\operator\test_model_decision_extractor_pack3_13.py tests\operator\test_read_only_research_decision_protocol_pack3_7.py
```

Result: PASS.

```powershell
git diff --check
```

Result: PASS. Git reported only line-ending normalization warnings for existing
working-copy behavior.

Targeted provider-material and raw-material scan over touched implementation
and tests found only forbidden labels in rejection constants and adversarial
tests. No API key, Authorization header, fallback enablement, AUTO routing,
provider-native tool enablement, raw provider payload persistence, or raw
reasoning persistence was introduced.

## Remaining Real-Model Risk

Pack 3.13 improves the runtime-model interface, but the next real run still has
real-model risk:

```text
the model may produce no JSON
the model may produce an unsupported action
the model may omit required arguments
the model may finish prematurely
the report lane may still fail later
```

Those are now expected to surface as clearer extraction or governed execution
outcomes rather than brittle raw-schema failures.

## Final Statement

Pack 3.13 moves Sentinel from exact-schema dependence toward a product-grade
model-decision extraction layer while preserving authority ownership and strict
governed execution. The next real run should target the first successful
governed read-only receipt.
