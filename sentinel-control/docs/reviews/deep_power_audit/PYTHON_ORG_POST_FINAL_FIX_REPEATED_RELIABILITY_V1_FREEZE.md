# PYTHON_ORG_POST_FINAL_FIX_REPEATED_RELIABILITY_V1_FREEZE

## Freeze Verdict

```text
PYTHON_ORG_POST_FINAL_FIX_REPEATED_RELIABILITY_V1
= FROZEN_BEFORE_EXECUTION

holdout = locked
runtime_patch_during_batch = forbidden
fixture_backend = forbidden
Playwright_fallback = forbidden
```

## Pre-Batch Preserved Evidence

```text
v6_minimal_safe_bundle = sentinel-control/docs/reviews/deep_power_audit/evidence_bundles/PYTHON_ORG_V6_MINIMAL_SAFE_EVIDENCE_BUNDLE_V1.json
v6_bundle_hash = 8caa196a083fd79988761e5dab7ea99c769bd7191715bfc8486db18e67e75da0
```

The V6 bundle intentionally preserves safe proof material only. It does not preserve raw provider output, private reasoning, raw DOM, raw URL, raw query, selectors, cookies, session values, profile material, secrets or raw binary path.

## Mission

```text
objective = find grounded official Python documentation explaining pathlib Path.glob and provide a short useful answer
target_class = public non-holdout Python.org
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
browser_backend = real Cloak
allowed_capabilities = real_browser_control, sentinel_loop
max_provider_decisions_per_mission = 10
max_material_actions_per_mission = 16
mission_count = 5
```

## Required Path

```text
real provider/model
-> ModelLedProductActionKernelTaskLoop
-> ProductActionKernel
-> root BrowserSessionLease
-> BrowserSessionManagerL5Live / Cloak backend
-> search / extract_evidence / verify_extraction
-> summarize_evidence
-> finish
-> FinalGate
-> replay no-react
-> post-close cleanup evidence
```

The model remains free to choose any safe evidence-grounded strategy. The evaluator must not require one exact action sequence.

## Denominator Rule

```text
every attempted mission counts in denominator
no retry to turn a failed attempt into success
no patch while a mission is running
no runtime patch between missions in this frozen batch
```

## Success Definition

Each mission success requires both:

```text
technical_completion = completed + finish + FinalGate accepted + replay no-react + cleanup success
answer_quality = useful grounded Path.glob answer supported by official evidence
```

Completed-with-irrelevant-evidence is not success.

## Metrics

```text
mission_success_rate
grounded_objective_satisfaction
search_materiality_success_rate
claim_evidence_coverage
unsupported_claim_rate
provider_decision_distribution
material_action_distribution
repeated_action_rate
recovery_attempts
root_lease_continuity
replay_no_react_rate
cleanup_success_rate
latency_seconds
provider_cost_estimate
```

## Failure Classification

```text
INFRA_BLOCKED
PROVIDER_FAILURE
BODY_FAILURE
SEARCH_MATERIALITY_FAILURE
EXTRACTION_FAILURE
VERIFY_FAILURE
SUMMARY_OR_FINISH_FAILURE
ANSWER_QUALITY_FAILURE
REPLAY_FAILURE
CLEANUP_FAILURE
HARD_BOUNDARY_REGRESSION
```

## Post-Batch Rule

If thresholds pass, proceed to broader non-holdout multi-site calibration. If thresholds fail, fix the general failure class and repeat a new versioned batch.

```text
frozen_holdout = do_not_consume
browser_language = finish Browser Organ first; no Rust/C#/TypeScript migration work
```
