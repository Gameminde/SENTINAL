# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# Pack 3.9 Explicit Product Mission Bootstrap Report

## Verdict

```text
PACK_3_9_EXPLICIT_PRODUCT_MISSION_BOOTSTRAP = LOCALLY_IMPLEMENTED_CANDIDATE
provider_called = false
Pack_4_started = false
capability_added = false
```

Pack 3.9 adds an explicit governed product-script bootstrap path for already
bounded CLI missions. It does not weaken or replace the interactive
`cockpit_mission_understanding_v2` path.

## Attempt 5E Evidence

Attempt 5E reached the real Aliyun / DeepSeek route but failed before mission
creation:

```text
classification = MISSION_NOT_CREATED
provider_calls = 1
parse_stage = mission_understanding_v2_validation
protocol_version = cockpit_mission_understanding_v2
top_level_key_names = ["metadata", "reply"]
missing_required_field_names = ["kind", "protocol_version"]
metadata_origin = model_output
```

Pack 3.8 proved the `metadata` field was model-owned output, not adapter
metadata pollution. The product route, workspace binding, authority scope,
provider endpoint, and legacy-parser removal were already proven. The remaining
blocker was real-model adherence to the cockpit V2 draft envelope.

## Why Prompt-Only Tuning Is Not Enough

The explicit product CLI route already receives trusted non-model inputs:

```text
user mission text
explicit --workspace
explicit --authority-scope
explicit UserModelContract
explicit approval turn
```

For this bounded scripted route, Sentinel can create the mission draft and
authority summary deterministically. The model should not be responsible for
creating product authority envelopes or blocking mission creation because it
missed JSON fields in the cockpit-understanding phase.

## Bootstrap Contract

The new flag is:

```text
--explicit-mission-bootstrap
```

It is valid only for the governed product CLI route and only when all required
inputs are present:

```text
--script
--workspace
--authority-scope
--model-contract
--json
```

It is not valid in deterministic test mode and is not valid for
`--legacy-internal-direct`.

The script must contain exactly two nonempty turns:

```text
turn 1 = operator mission text
turn 2 = start
```

The approval is intentionally ASCII-only for scripted product runs to avoid the
mojibake seen in earlier French approval input files.

## Sentinel-Owned Objects

In explicit bootstrap mode, Sentinel deterministically creates:

```text
OperatorIntent
MissionDraft
MissionAuthoritySummary
```

The draft and summary are data-only:

```text
bootstrap_protocol = explicit_product_mission_bootstrap_v1
requested_capability = read_only_research
operation = inspect_repository
expected_artifacts = ["evidence-linked technical report"]
```

Sentinel owns all executable bindings:

```text
workspace_ref = workspace:<approved external absolute path>
model_contract_ref = model_contract:<provider>:<backend>:<model>:<hash>
capability_id = read_only_research
operation = inspect_repository
authority_envelope_ref = issued envelope id
```

The bootstrap path does not use legacy fallback refs:

```text
snapshot:operator_session
model_contract:operator_session
```

## Why This Is Not Fallback Or AUTO

This mode is explicit and opt-in. It does not select a different provider,
model, backend, adapter, capability, workspace, or authority scope. It only
changes who creates the initial draft envelope for a scripted, already-bounded
product mission:

```text
before = provider must emit cockpit V2 mission draft JSON
after  = Sentinel creates the draft from trusted CLI inputs
```

The selected UserModelContract remains explicit. Provider-native tools remain
disabled. No fallback or AUTO route is introduced.

## Provider Call Boundary

In explicit bootstrap mode:

```text
cockpit provider calls = 0
read-only exploration provider calls = allowed after dispatch
read-only report provider calls = allowed after exploration
```

The first provider call, if the mission dispatches, belongs to:

```text
read_only_research_decision_v1
```

This prepares Attempt 5F to test the read-only decision lane directly instead
of retesting whether DeepSeek can create the cockpit V2 draft envelope.

## Authority Preservation

Executable scope remains the intersection of:

```text
ProductExecutionBinding
MissionAuthorityApprovalScope
read_only_research capability contract
policy limits
```

Forbidden actions from the approval scope are preserved and combined with the
read-only route's forbidden action set. The created request remains data-only,
hash-bound, and persisted by `MissionLifecycleService` before enqueue.

## Request Creation Proof

Focused tests prove:

```text
capability_id = read_only_research
operation = inspect_repository
workspace_ref = workspace:<resolved workspace>
model_contract_ref = model_contract:<provider>:<backend>:<model>:<hash>
old snapshot/model fallback refs absent
```

The CLI route still pumps through the real RuntimeHost/daemon/dispatcher after
the deterministic approval turn.

## Strict Interactive V2 Preserved

The existing interactive cockpit V2 path remains strict:

```text
cockpit_mission_understanding_v2 is still required in product LLM mode
mission_understanding_v2_validation still rejects model-owned metadata
provider-supplied workspace/model-contract/authority fields remain rejected
```

Pack 3.9 adds a separate explicit script bootstrap mode. It does not weaken
`cockpit_mission_understanding_v2`.

## Remaining Risk

Pack 3.9 does not prove a real-provider mission. It prepares Attempt 5F by
allowing explicit product-script missions to reach the read-only decision lane
without relying on cockpit JSON adherence.

The next real risk moves to:

```text
read_only_research_decision_v1 adherence
read-only action quality
final report lane quality
proof verification under real model output
```

## Local Validation

Focused validation:

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py -k "explicit_bootstrap"
6 passed

py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py
55 passed

py -3.13 -m pytest -q tests/operator/test_product_nervous_system_pack3.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py
31 passed

py -3.13 -O -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py
55 passed

py -3.13 -m compileall -q sentinel\cli.py sentinel\operator\cockpit.py
PASS

git diff --check
PASS
```

Targeted scans found no raw credential, API key, raw prompt, raw response, raw
reasoning, provider wrapper payload, fallback/AUTO enablement, or provider-native
tool enablement in the Pack 3.9 implementation. Remaining scan hits were benign
documentation/test references or ordinary variable names unrelated to model
routing.
