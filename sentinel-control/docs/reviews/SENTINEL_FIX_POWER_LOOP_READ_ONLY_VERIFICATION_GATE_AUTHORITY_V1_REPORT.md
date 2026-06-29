# SENTINEL FIX POWER LOOP READ ONLY VERIFICATION GATE AUTHORITY V1 REPORT

## Verdict

```text
FIX_POWER_LOOP_READ_ONLY_VERIFICATION_GATE_AUTHORITY_V1 = LOCALLY_IMPLEMENTED_CANDIDATE
```

## Accepted Starting State

```text
FIX_REAL_MODEL_CODE_EXECUTION_ACTION_PROTOCOL_OR_CONTEXT_V1 = LOCALLY_COMMITTED_CANDIDATE
commit = e1ba980702c0630263ab5c70f391bf02530e5563

REAL_POWER_ATTEMPT_2B_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1 = VALID_FAILED
report_commit = 8cb5c248a7acc7001fc349424bb355a4c7af0730
```

Attempt 2B proved:

```text
real provider called successfully
provider_decision_calls = 5
extraction_failures = 0
code execution = yes
workspace patch = yes
workspace mutation limited to fixture
replay material deltas = 0
raw provider/reasoning/credential persistence = no
fallback/AUTO = no
provider-native tools = no
```

Attempt 2B failed because:

```text
finish = no
bounded_check_run = no
objective_satisfied = false
finish_available = false
read-only verification attempts = READ_ACCESS_BLOCKED
```

## Root Cause

The generic model-led Power Loop granted the read-only capability as:

```text
allowed_tools = ["read_only_research", ...]
```

But the production read-only spine Gate selected the tool alias:

```text
read_only_observation
```

unless the authority envelope contained:

```text
read_only_research_adapter
```

Therefore a valid in-workspace Power Loop read-only action reached the Gate as:

```text
action_type = list_directory | read_file_segment | search_text
tool = read_only_observation
```

while the envelope allowed:

```text
tool = read_only_research
```

Gate 2 correctly treated that as out of scope:

```text
gate_sequence:out_of_scope:escalate
```

The bug was authority alias propagation, not a model, provider, schema, or path-boundary issue.

## Fix

Updated:

```text
sentinel/operator/read_only_operator_spine.py
```

The production read-only Gate now recognizes the Power Loop capability alias:

```text
read_only_research
```

as both:

```text
selected Gate tool when the mission authority grants read_only_research
known read-only Gate tool for the session
```

Existing aliases remain supported:

```text
read_only_observation
read_only_research_adapter
```

## Why This Does Not Weaken Gate

The fix does not bypass Gate.

It only ensures the Gate evaluates the action under the same read-only tool/capability actually granted by the mission authority envelope.

The Gate still enforces:

```text
action in allowed_actions
tool in allowed_tools
target path inside allowed_paths
path traversal blocked
absolute outside path blocked
sensitive snapshot paths blocked
forbidden actions blocked
unknown tools blocked
```

## Regression Tests

Updated:

```text
tests/operator/test_power_pack3_code_execution_sandbox.py
```

New tests prove:

```text
Power Loop read_only.list_directory succeeds inside granted fixture workspace using the production read-only spine
Power Loop read_only.read_file_segment succeeds on a granted fixture file using the production read-only spine
Power Loop read_only.search_text after patch creates a real read-only receipt
outside workspace path traversal remains blocked by Gate
production read-only receipt satisfies objective_satisfied
finish-only turn activates after code_exec + patch + read-only verification receipts
```

The previous tests used a synthetic `ActionResult` for read-only actions, so they did not exercise the production read-only Gate path that failed in Attempt 2B.

## Validation

Commands run:

```text
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
```

Result:

```text
12 passed
```

```text
py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
```

Result:

```text
6 passed
```

```text
py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
```

Result:

```text
7 passed
```

```text
py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
```

Result:

```text
9 passed
```

```text
py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
```

Result:

```text
48 passed
```

```text
py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
```

Result:

```text
28 passed
```

```text
py -3.13 -m compileall sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py sentinel/operator/code_execution_sandbox_runtime.py sentinel/operator/workspace_patch_runtime.py sentinel/operator/read_only_operator_spine.py
```

Result:

```text
passed
```

```text
git diff --check
```

Result:

```text
passed
```

Targeted scan:

```text
rg -n "API key|Authorization|raw_prompt|raw_response|raw_reasoning|reasoning_content|provider-native|provider_native|fallback|AUTO|Bearer|secret=|api_key=|curl|wget|shell=True|shell=False" sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py sentinel-control/services/sentinel-core/tests/operator/test_power_pack3_code_execution_sandbox.py
```

Result:

```text
runtime source hits are the existing diagnostic unsafe-label denylist
test hits are existing redaction fixtures for Authorization: Bearer token and secret=hidden
no credential values, raw provider output, fallback/AUTO enablement, or provider-native tool enablement introduced
```

## Confirmation

```text
new power = no
Gate bypass = no
fallback/AUTO introduced = no
provider-native tools introduced = no
provider call during fix = 0
push = not performed
Power Pack 4 = not started
```

## Next Required Real Run

After this fix is committed, run exactly one:

```text
REAL_POWER_ATTEMPT_2C_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1
```

Success target:

```text
real model chooses bounded code execution
workspace patch happens
read-only verification succeeds without READ_ACCESS_BLOCKED
bounded check or equivalent verification receipt exists
model emits sentinel_loop.finish explicitly
mission completes by model finish, not material budget
replay no-rerun/no-reapply/no-reexecute
```
