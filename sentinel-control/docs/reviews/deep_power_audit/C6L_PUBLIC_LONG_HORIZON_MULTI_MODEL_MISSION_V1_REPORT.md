# C6L Public Long-Horizon Multi-Model Mission V1 Report

## Verdict

```text
C6L_PUBLIC_LONG_HORIZON_MULTI_MODEL_MISSION_V1
= VALID_REAL_PRODUCT_ENTRYPOINT_PROVIDER_TRANSPORT_BLOCKED

entrypoint = public Web /api/runs
root MissionRecord = CREATED
provider_calls = 1
browser_dispatches = 0
material_actions = 0
phase_b_model = NOT_REACHED
final_answer = NOT_PRODUCED
cleanup = COMPLETED
FIXED_PROVEN = 0/65
```

This run is consumed and must not be silently retried.

## Frozen Run

```text
implementation_head = c2fea08eff0e016a54bcb7e2f69e3a1d660cb783
entrypoint = POST /api/runs
run_id = GR-202608212236-3f1c14
root_mission_id = root_mission_72b09b782e804d79938143e41abc8cf4
target_origin = sqlite.org
authority = public_web_read_only
browser_allowed_origins = sqlite.org, www.sqlite.org
primary_provider = opencode_chat
primary_backend = opencode_chat_completions
primary_model = x-preview-f-free
handoff_provider = opencode
handoff_backend = opencode_responses
handoff_model = muse-spark-1.2-contributor-free
max_provider_decisions = 30
max_material_actions = 20
max_wall_time_ms = 2700000
```

The pre-run product-route correction in the same checkpoint passes the public run budgets through to the canonical runtime. No provider call was made before the public mission request.

## Timeline

```text
mission_created
mission_queued
mission_running
canonical_authority_snapshot_created
canonical_browser_backend_readiness_passed
canonical_model_decision_failed
mission_blocked
canonical_browser_readonly_cleanup_completed
```

## Browser Readiness

```text
selected_backend_id = sentinel_chromium
actual_backend_id = sentinel_chromium
backend_kind = physical
initial_target = about:blank
network_navigation_during_readiness = false
```

The sovereign browser was ready before provider allocation. No browser action was dispatched because no executable model decision was accepted.

## First Causal Blocker

```text
failure_stage = provider_or_decision_normalization
failure_code = CANONICAL_DECISION_TRANSPORT_REJECTED:provider_failure_PROVIDER_UNKNOWN_ERROR_local_JSONDecodeError
exception_class = ActionKernelError
provider_decision_count = 1
material_action_count = 0
```

Local code inspection maps this to the OpenAI-compatible chat transport receiving a response that could not be parsed by `response.json()` after HTTP status handling. The raw provider response body was not persisted and is not reproduced here.

Safe interpretation:

```text
not_sqlite_failure = true
not_browser_failure = true
not_intent_bridge_failure = true
not_phase_b_failure = true
first_blocker = opencode_chat_transport_json_decode
```

## Gate Results

```text
public_web_entrypoint = PASS
one_root_mission_record = PASS
authority_snapshot_before_provider = PASS
sentinel_chromium_readiness = PASS
both_models_reached = FAIL
product_action_kernel_browser_dispatches_gt_0 = FAIL
official_evidence_refs_gte_6 = FAIL
planned_handoff_checkpoint = NOT_REACHED
second_model_resumed_same_mission = NOT_REACHED
actions_before_handoff_not_replayed = NOT_REACHED
final_grounded_answer_returned_to_ui = FAIL
proof_root_persisted = PASS
proof_root_receipt_verification = PASS_EMPTY_RECEIPT_SET
external_proof_authenticity = MISSING
cleanup_completed = PASS
survivor_count = NOT_MEASURED_IN_THIS_REPORT
```

## Safe Artifact References

```text
public_response_artifact = sentinel-control/data/c6l_public_long_horizon_response.json
canonical_run_artifact = sentinel-control/data/canonical_product_runs/web_canonical_20260821223610_279fac7a
proof_root_id = mission_proof_root_210993c869b746f1bd1b23c9b44bf7b3
proof_root_hash = 6d606788981d06e156e65c101a9dff700b44cda6826d5bd5df1ab67c47bdcbe8
```

Runtime artifacts remain untracked and must not be published as raw session material.

## Next Recommendation

Do not rerun C6L immediately. The next narrow tranche should be provider-transport compatibility, not browser work:

```text
OPENCODE_CHAT_TRANSPORT_SAFE_TELEMETRY_AND_COMPATIBILITY_V1
```

Required offline work:

- add fixtures for non-JSON, empty, HTML/text, and JSON error bodies;
- preserve safe telemetry for JSON decode failures: HTTP status if known, content-type category, body length bucket/hash, and stage;
- distinguish endpoint incompatibility from model narrative-format rejection;
- keep raw body, prompts, credentials and provider output unpersisted.

Only after that offline proof should a new explicitly authorized run be considered. A future retry should either confirm `x-preview-f-free` chat-completions compatibility or move Phase A to a transport already proven with the chosen model.
