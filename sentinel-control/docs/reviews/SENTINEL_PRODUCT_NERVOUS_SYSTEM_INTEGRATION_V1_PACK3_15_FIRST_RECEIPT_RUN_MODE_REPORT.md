# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.15 FIRST RECEIPT RUN MODE REPORT

## Verdict

`PACK_3_15_FIRST_RECEIPT_RUN_MODE = LOCALLY IMPLEMENTED CANDIDATE`

This pack does not start Pack 4 and does not call a provider. It adds one explicit product run mode for the next real-provider attempt:

```text
stop_after_first_material_receipt = true
```

The mode is opt-in, persisted in the immutable `MissionExecutionRequest`, and used only by the Pack 3 read-only research route.

## Attempt 5K Static Stop Root Cause

Attempt 5K was stopped before execution because the runbook required:

```text
one provider call maximum
```

but the existing Pack 3 read-only spine behavior was:

```text
provider decision call
-> governed read-only action
-> receipt
-> continue loop
-> second provider decision call or report lane
```

Therefore the first real receipt threshold could be blocked by a runbook/protocol mismatch rather than a runtime defect.

## Design

### Request-Bound Execution Option

`MissionExecutionRequest` now carries:

```json
{
  "execution_options": {
    "stop_after_first_material_receipt": true
  }
}
```

Rules:

```text
allowed keys = stop_after_first_material_receipt only
value type = boolean only
unknown keys = rejected
included in request_hash = yes
authority effect = none
can_execute = false
can_grant_authority = false
```

This is a code-owned run mode, not model-owned authority.

### CLI Opt-In

The product CLI exposes:

```text
--stop-after-first-material-receipt
```

It is accepted only with:

```text
--explicit-mission-bootstrap
```

This keeps ordinary cockpit/product behavior unchanged and avoids making the flag a generic hidden execution bypass.

### Read-Only Spine Behavior

When the option is active:

```text
valid read-only decision
-> Gate accepted
-> governed material action executes
-> one successful action receipt is persisted
-> accepted read-only FinalGate is persisted
-> read_only_spine_first_material_receipt_terminal event is emitted
-> session returns completed
```

The final report lane is intentionally skipped in this mode.

### Dispatcher Proof Verification

The dispatcher remains strict:

```text
default completed route:
  material receipt + report artifact + accepted FinalGate required

first-receipt route:
  material receipt + accepted FinalGate required
  report artifact intentionally not required
```

If a route blocks before a successful read-only action, no fake receipt is created.

## Authority Preservation

Pack 3.15 does not expand authority:

```text
workspace binding remains explicit
model contract binding remains explicit
coordinator route remains read_only_research only
Gate still validates action and path scope
read-only tool set is unchanged
write/shell/credential/browser/payment/email actions remain unavailable
```

The mode changes when to stop, not what can be done.

## Default Behavior

Without the option, the read-only spine still continues after the first receipt and requires finish/report proof for a completed product mission.

## Local Proofs

Focused tests cover:

```text
first-receipt mode stops after one material receipt
first-receipt mode does not call the report lane
default mode still continues after first receipt
Gate denial in first-receipt mode creates no fabricated receipt
CLI explicit bootstrap persists execution_options
CLI explicit bootstrap with the option performs one decision call and zero report calls
```

## Validation

Executed locally with no provider call:

```text
py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py -k "pack3_15"
result: 3 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py
result: 26 passed

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\test_cli_runtime_host_product_wiring_pack1b.py
result: 20 passed

py -3.13 -m pytest sentinel-control\services\sentinel-core\tests\operator\test_model_decision_extractor_pack3_13.py sentinel-control\services\sentinel-core\tests\operator\test_read_only_research_decision_protocol_pack3_7.py sentinel-control\services\sentinel-core\tests\test_real_model_read_only_operator_production_spine_v1.py --tb=short
result: 88 passed

py -3.13 -O -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_product_nervous_system_pack3.py -k "pack3_15"
result: 3 passed, expected pytest assertion-rewrite warning under -O

py -3.13 -m pytest -q sentinel-control\services\sentinel-core\tests\operator\test_mission_lifecycle_service.py sentinel-control\services\sentinel-core\tests\operator\test_runtime_host_pack1.py
result: 13 passed

py -3.13 -m compileall -q sentinel-control\services\sentinel-core\sentinel\cli.py sentinel-control\services\sentinel-core\sentinel\operator\cockpit.py sentinel-control\services\sentinel-core\sentinel\operator\mission_lifecycle_service.py sentinel-control\services\sentinel-core\sentinel\operator\read_only_operator_spine.py sentinel-control\services\sentinel-core\sentinel\operator\unified_execution_dispatcher.py
result: PASS

git diff --check
result: PASS; Git reported line-ending normalization warnings only
```

Targeted secret/provider/fallback scan found no API key, Authorization value, fallback enablement, provider-native tool enablement, or provider material persistence. The only raw-provider-related matches were existing unsafe diagnostic label markers used as a deny-list in `read_only_operator_spine.py`.

## Remaining Limits

This pack does not prove a real-provider receipt. It prepares the next real-provider run by making the one-call first-receipt threshold structurally possible.

The next eligible experiment is:

```text
ATTEMPT_5K_B_FIRST_RECEIPT_RUN_MODE_REAL_PROVIDER
```

Success threshold:

```text
tool_calls_material >= 1
successful_receipts >= 1
workspace unchanged = true
material replay purity = held
```

If that threshold is met, Pack 4 can be opened for discussion.
