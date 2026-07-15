# SENTINEL_CRASH_SAFE_BOUNDED_LIVE_RUN_EVIDENCE_SINK_V1_REPORT

```text
CRASH_SAFE_BOUNDED_LIVE_RUN_EVIDENCE_SINK_V1 = IMPLEMENTED_LOCAL_CANDIDATE
implementation_commit = 1b4c6f3 fix: add crash safe live run evidence sink
provider_calls = 0
live_browser_calls = 0
python_org_v3_run = not_yet
```

## Purpose

The V2 body canary failed as an observability failure: stdout exceeded capture
limits and the run left no bounded safe artifact proving the body result. This
pack adds a narrow crash-safe evidence sink so future live runs preserve
minimum safe truth even if stdout, report synthesis or cleanup fails.

This is not a browser cognition change and not a search-actuation fix.

## What Changed

Added:

```text
sentinel/operator/live_run_evidence_sink.py
```

The sink writes:

```text
safe_evidence_events.jsonl
safe_evidence_snapshot.json
```

The artifact is append-first and snapshot-atomic:

```text
record transition
-> append JSONL with fsync
-> atomic replace snapshot
-> preserve local integrity hash chain
```

The sink records bounded safe events such as:

```text
run_started
provider_decision_received
action_envelope_accepted
browser_action_started
runtime_failure_fact_created
model_visible_failure_packet_created
model_blocker_assessment_received
material_receipt_created
FinalGate_result
cleanup_result
terminal_verdict
```

## Product Loop Wiring

Updated:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/runtime_host.py
sentinel/operator/product_model_native_decision_client.py
```

`RuntimeHost.run_product_action_kernel_task_loop(...)` now accepts an optional
`evidence_sink`. The sink is passed into `ModelLedProductActionKernelTaskLoop`
and receives safe transition facts from the real product path.

`RuntimeHost` records cleanup in a `finally` block after closing the product
task resource scope.

`ProductModelNativeDecisionClient` extracts only the requested concise
operational assessment fields:

```text
perceived_blocker
failure_interpretation
proposed_next_strategy
required_evidence
missing_capability
objective_satisfied
confidence
```

The assessment is advisory evidence. It does not override receipts, grant
authority or become proof.

## Safe Persistence Rules

The sink persists:

```text
typed statuses
hashes
receipt refs
evidence refs
provider decision count
action sequence
model operational assessment
session continuity identity hashes
cleanup facts
terminal verdict
```

The sink redacts or hashes:

```text
raw provider output
private chain-of-thought / reasoning
raw DOM
raw query
raw URL
selectors
cookies
session/profile material
secrets
raw binary path
```

It does not topic-police safe semantic words. Ordinary words such as login,
download, upload and payment may remain semantic data when they are not
structured effect requests or secret-bearing values.

## Local Proof

Added:

```text
tests/operator/test_crash_safe_bounded_live_run_evidence_sink.py
```

The local proof simulates:

```text
massive stdout-sized provider output
report synthesis AttributeError
cleanup after run
partially completed mission
secret-like value redaction
safe topic-word preservation
RuntimeHost product-loop partial block evidence
```

The proof confirms:

```text
safe artifact survives report exception
safe artifact survives cleanup of transient runtime material
raw provider output is not persisted
private chain-of-thought is not persisted
raw query/URL are hashed/redacted
runtime_failure_fact remains authoritative
model_blocker_assessment remains advisory
cleanup_result is recorded
terminal_verdict is recorded
```

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_crash_safe_bounded_live_run_evidence_sink.py -q
result = 4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
result = 54 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 99 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 26 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result = passed

git diff --check
result = passed
```

Targeted scan:

```text
new real secret/provider-native/raw-material hit count = 0
synthetic secret test strings = present only inside redaction tests
raw Cloak binary path persisted = no
```

## Remaining Truth

```text
REAL_BROWSER_SEARCH_ACTUATION_FIX = not proven by this pack
ROOT_SESSION_CONTINUITY = not proven by this pack
MODEL_VISIBLE_BODY_FAILURE_AND_RECOVERY_FEEDBACK = local transport ready, real cognitive proof pending
```

Next authorized tranche:

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V3
```

That tranche must run exactly once, with the crash-safe sink active before the
first provider decision.

