# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1
# PACK_3_14_READ_ONLY_GATE_SCOPE_ALIGNMENT_V1_REPORT

## Verdict

```text
PACK_3.14 = LOCALLY IMPLEMENTED
provider calls = 0
Pack 4 started = no
push performed = no
```

This pack closes the first post-extraction blocker observed in Attempt 5J:

```text
ATTEMPT_5J_EXTRACTION_LAYER_REAL_READ_ONLY_RECEIPT
= VALID_FAILED_DISPATCHED_BUT_BLOCKED_AFTER_EXTRACTION
```

Attempt 5J proved that the real provider response was semantically extracted into
a canonical read-only decision, but the governed read-only action was blocked at
Gate before a receipt could be created.

## Attempt 5J Evidence

Retained safe artifacts showed:

```text
provider calls total = 1
cockpit provider calls = 0
read-only decision calls = 1
tool calls = 0
successful receipts = 0
FinalGate accepted = false
MissionKernel = BLOCKED
workspace unchanged = true
```

The decision checkpoint showed a post-parse, pre-Gate `list_directory` decision:

```text
action = list_directory
safe_target_kind = snapshot_root
checkpoint_stage = post_parse_pre_gate
```

The failed attempt showed:

```text
failure_code = READ_ACCESS_BLOCKED
runtime_phase = gate
reason = gate_sequence:out_of_scope:escalate
```

The user-approved authority scope contained:

```text
allowed_tools = ["read_only_research_adapter"]
allowed_paths = ["C:\\Users\\youcefcheriet\\sentinel-workspaces\\attempt5b-click"]
```

The issued executable envelope contained empty tool/path grants:

```text
allowed_tools = []
allowed_paths = []
```

## Root Cause

This was not a model schema issue and not a read-only decision extraction issue.
It was a product/runtime authority-scope alignment issue.

The approval layer used product-facing concepts:

```text
tool = read_only_research_adapter
path = absolute approved workspace
```

The default policy and read-only Gate used internal execution concepts:

```text
tool = read_only_observation
path = "."
```

The authority issuer previously used exact string intersection for tools and
paths. That erased both grants:

```text
read_only_research_adapter intersect read_only_observation = empty
absolute workspace intersect "." = empty
```

The read-only Gate then evaluated a valid root read decision against an envelope
with no usable tool or path scope.

## Implementation

### Authority Issuer

`MissionAuthorityEnvelopeIssuer` now preserves the user-approved product route
when it is also covered by the read-only internal policy:

```text
approval tool read_only_research_adapter
+ policy tool read_only_observation
-> envelope tool read_only_research_adapter
```

It also computes path overlap conservatively:

```text
approval path absolute workspace
+ policy path "."
-> envelope path absolute workspace
```

For ordinary relative paths, exact intersection remains required. The earlier
test case where approval paths `[".", "docs"]` and policy paths `[".", "secrets"]`
must produce only `["."]` remains enforced.

### Read-Only Gate

The read-only spine now:

```text
accepts root aliases ".", "snapshot_root", and "workspace_root"
normalizes root aliases to "."
uses the envelope-approved read-only product tool when present
keeps Gate known tools bounded to read_only_observation/read_only_research_adapter
```

This lets the product route preserve the user-approved adapter identity without
giving the model or adapter a new authority surface.

## Why This Does Not Weaken Authority

The fix does not add arbitrary tools. It only bridges:

```text
read_only_research_adapter <-> read_only_observation
```

and only when the read-only policy already allows the internal observation tool.

The fix does not broaden paths. It keeps:

```text
exact path intersections
or the narrower overlapping absolute workspace path
```

Relative path broadening is rejected by existing authority tests.

The read-only spine still blocks:

```text
absolute paths from model decisions
path traversal outside snapshot root
workspace/model/authority fields from model decisions
shell/write/credential actions
fake successful receipts
```

## Regression Proof

New Pack 3.14 coverage proves:

```text
approved workspace scope allows adapter-routed list/search/read receipts
snapshot_root alias reaches a list_directory receipt
relative path escape blocks without a receipt
absolute outside path blocks without a receipt
authority exact-relative path intersection still does not broaden
```

## Validation

Executed focused validation:

```text
py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py -k "pack3_14"
result: 5 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py
result: 23 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_authority_issuer.py
result: 8 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_read_only_research_decision_protocol_pack3_7.py
result: 24 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_model_decision_extractor_pack3_13.py
result: 16 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\test_cli_runtime_host_product_wiring_pack1b.py
result: 19 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\test_real_model_read_only_operator_production_spine_v1.py
result: 48 passed

py -3.13 -O -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py -k "pack3_14" sentinel-control\services\sentinel-core\tests\operator\test_authority_issuer.py
result: 5 passed, with expected pytest optimized-mode assertion warning

py -3.13 -m compileall -q sentinel-control\services\sentinel-core\sentinel\operator\authority_issuer.py sentinel-control\services\sentinel-core\sentinel\operator\read_only_operator_spine.py
result: passed

git diff --check
result: passed, with line-ending normalization warnings only
```

Targeted safety scan found no newly introduced credential, provider wrapper,
raw prompt, raw response, raw reasoning, fallback enablement, AUTO routing, or
provider-native tool enablement. Matches were existing deny-list code/tests and
historical review documentation.

## Remaining Limit

This pack does not prove a new real-provider receipt. It prepares the next
single real attempt by removing the runtime Gate scope mismatch that blocked
Attempt 5J after extraction.

The next real-provider threshold remains:

```text
real provider -> canonical read-only decision -> governed read-only action
-> successful receipt -> workspace unchanged -> replay material purity held
```
