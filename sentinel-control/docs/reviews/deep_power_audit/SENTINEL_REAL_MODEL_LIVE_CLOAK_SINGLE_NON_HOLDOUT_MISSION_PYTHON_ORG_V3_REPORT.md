# SENTINEL_REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V3_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V3
= VALID_FAILED_OBSERVABILITY
```

This run consumed exactly one real-provider mission. No retry mission was run.

The run proves the real mind-to-body path reached:

```text
real deepseek-v4-pro provider
-> model-native decision
-> real_browser.search ActionEnvelope
-> browser_action_started
-> cleanup_result
```

It failed before Sentinel created a `runtime_failure_fact` or
`model_visible_body_failure_packet`. Therefore V3 does **not** prove browser
search actuation, recovery reasoning, or grounded completion. It proves the
next blocker is observability/lifecycle around the real browser action start.

## Scope

```text
provider_is_real = true
provider_id = aliyun_dashscope
provider_backend = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
fixture_backend = false
Playwright_fallback = false
frozen_holdout_used = false
calibration_batch = false
target_site = python.org
```

Mission objective was frozen before execution and persisted only by hash:

```text
mission_objective_hash =
0b167e44cd57a3cbde7019117f4e2e6b2b9efda12fcd7bb553cda64b6b4fd349
```

Read-only public-Web authority was used. No login, upload, download, contact,
payment, provider-native tool, fallback/AUTO, or external mutation authority was
granted.

## Pre-Provider Harness Attempts

Two launcher attempts failed before provider consumption and are not counted as
provider missions:

```text
attempt_0_provider_decision_events = 0
attempt_1_provider_decision_events = 0
```

The first failure was a harness bug: `cloakbrowser.binary_info()` exposed
`binary_path`, while the launcher initially looked for `executable_path` and
then tried to hash the current directory. This was corrected in the launcher
only; no Sentinel runtime behavior was modified.

## Cloak Provenance

The final V3 run restored the previously validated Cloak binary candidate into
process scope only.

```text
cloak_candidate_verified = true
cloak_binary_sha256 =
03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
cloak_binary_path_hash =
f3fad5133de1a876082e5a7f6be7c61cf083e2a4742c4cf44fcfa6cfe34d3a2e
cloak_binary_version = 146.0.7680.177.5
cloak_binary_tier = free
raw_binary_path_persisted = false
```

The raw binary path was not printed or persisted.

## Evidence Sink Proof

The crash-safe bounded evidence sink survived the terminal failure and retained
the important transitions:

```text
safe_evidence_event_count = 7
event_sequence =
run_started
-> run_started
-> provider_decision_received
-> action_envelope_accepted
-> browser_action_started
-> cleanup_result
-> terminal_verdict
```

Safe evidence integrity:

```text
evidence_snapshot_integrity_hash =
66e7980f400c17afacab7ebc02c90674842e437e0b9adfa766fd5c21cbb26c94
```

The sink recorded:

```text
provider_decision_count = 1
action_sequence = real_browser_control.real_browser.search
material_receipt_count = 0
finalgate_result_count = 0
cleanup_recorded = true
raw_material_persisted = false
```

## Model Decision

```text
provider_decision_calls = 1
provider_decisions_model_native = true
provider_native_tools = false
raw_provider_output_persisted = false
raw_provider_reasoning_persisted = false
```

DeepSeek selected a safe browser skill:

```text
capability_id = real_browser_control
operation = real_browser.search
params_hash = 391d19bbb17cb894e0ee3ec895b903c2d28dc7052cb1d681fe3ce8b678c8e8c2
target_ref_hash = safe hash only
```

This satisfies the mind-side entry condition for V3: the real model produced a
model-native action that reached the internal ActionEnvelope boundary.

## Body Failure

The run failed after `browser_action_started` and before a product dispatch
result could be persisted:

```text
exception_class = FileNotFoundError
exception_hash =
e5f6fc103011debaf974a999aef54e9ea49d5a8118afdb85a46592ef172fc78e
runtime_failure_fact_created = false
model_visible_body_failure_packet_created = false
model_blocker_assessment_received = false
material_receipt_created = false
FinalGate_result = false
```

Cleanup still ran:

```text
cleanup_completed = true
remaining_product_task_resource_scope_count = 0
browser_lease_lifecycle_state = not_acquired
```

Important interpretation:

```text
provider_and_model_path = reached
typed_action_boundary = reached
browser_action_start = reached
root_browser_lease_acquired = false
runtime_failure_fact = missing
model_visible_failure_packet = missing
next_model_recovery_turn = not reached
```

Because the root browser lease remained `not_acquired`, the failure occurred
before Sentinel could prove selected/actual backend identity for the material
browser action.

## Mind/Body Assessment

```text
BODY_VERDICT.lifecycle = cleanup_after_exception_observed
BODY_VERDICT.session_reuse = not_proven
BODY_VERDICT.cleanup = cleanup_result_recorded
BODY_VERDICT.backend_truth = not_reached_for_material_action

MIND_BODY_VERDICT.model_strategy_accepted = true
MIND_BODY_VERDICT.useful_action_ratio = not_measurable_after_first_action_start
MIND_BODY_VERDICT.recovery_quality = not_reached
MIND_BODY_VERDICT.search_actuation = not_reached
MIND_BODY_VERDICT.evidence_quality = not_reached

MISSION_VERDICT = blocked_by_observability_gap
```

This is not a mission success. It is a valid integrated failure showing that
the model can reach the body, but the body still needs to preserve and expose
failure facts when the browser action start path throws before `ActionResult`.

## Safety

```text
raw_provider_output_persisted = false
private_reasoning_persisted = false
raw_DOM_persisted = false
raw_query_persisted = false
raw_URL_persisted = false
raw_selector_persisted = false
cookies_or_session_material_persisted = false
raw_binary_path_persisted = false
authority_expansion_count = 0
provider_native_tools = false
fallback_AUTO = false
```

## Replay

Replay no-react could not be computed for a completed mission because no
mission dispatch result or material receipt was created:

```text
replay_no_react = not_applicable_no_material_receipt
```

The safe evidence artifact itself remained stable enough to report the terminal
truth after the failure.

## Conclusion

```text
VALID_FAILED_OBSERVABILITY
```

V3 proves:

```text
real model/provider path works
model-native action mapping works
crash-safe evidence sink works
cleanup evidence survives terminal failure
```

V3 does not prove:

```text
Cloak material browser action
root lease continuity
runtime_failure_fact delivery to the model
model-visible recovery assessment
grounded Python.org objective completion
```

## Next Root Fix

Recommended next tranche:

```text
FIX_BROWSER_ACTION_START_EXCEPTION_TO_RUNTIME_FAILURE_FACT_V1
```

Target:

```text
Any exception after browser_action_started and before ProductActionKernel
dispatch completion must be converted into a safe runtime_failure_fact and
model_visible_body_failure_packet, with cleanup evidence preserved.
```

This should not be a Python.org selector patch and should not weaken
Cloak-first or typed-effect boundaries.
