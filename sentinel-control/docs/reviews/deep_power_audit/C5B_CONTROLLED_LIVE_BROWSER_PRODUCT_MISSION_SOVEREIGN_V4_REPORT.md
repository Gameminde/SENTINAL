# C5B Controlled Live Browser Product Mission Sovereign V4 Report

## Verdict

```text
C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_SOVEREIGN_V4
= VALID_FAILED_PROVIDER_RATE_LIMIT_AFTER_BROWSER_PROGRESS
```

The V4 run was executed exactly once after the SiteScope authority correction. It is consumed and must not be replayed as the same attempt.

## What Changed Before The Run

```text
fix_commit = d04ee176ba159fcde3e151d4d2146be8931566b7
source_head_before_fix = 478d23341e7bf7bfd0a334f9a17e4d41df2d98ff
MiniMax prompt changed = false
Intent Bridge changed = false
provider = NVIDIA MiniMax M3
backend = sentinel_chromium
```

A minimal `SiteScope` was added for public read-only navigation. It accepts only the explicit SQLite apex/www host forms, normalizes host case, trailing dot, default ports and IDNA, and records the transformation in receipts without rewriting the model decision.

## V4 Live Result

```text
mission_record_created_before_provider = true
provider_decisions = 3
ProductActionKernel dispatches = 2
browser_actions_completed = 2
model_selected_finish = false
mission_status = blocked
first_terminal_blocker = provider_failure_PROVIDER_RATE_LIMIT_http_429
cleanup_completed = true
survivor_count = 0
FIXED_PROVEN = 0/65
```

The V3 blocker was not reproduced. The model-selected browser open passed authority through `SiteScope`, reached `ProductActionKernel`, and completed with `actual_backend_id = sentinel_chromium`. A subsequent `extract_evidence` action also completed. The run then stopped on a provider rate-limit rejection before another executable dispatch.

## SiteScope Proof

```text
canonical_site = sqlite.org
accepted_host_forms = [sqlite.org, www.sqlite.org]
normalized_host_observed = www.sqlite.org
authority_match = SiteScope
site_scope_authority_passed = true
decision_rewritten = false
authority_expansion = false
```

The safe bundle records only URL hashes and normalized host metadata.

## Receipts And Proof

```text
canonical_receipts = 2
browser_terminal_receipts = 2
proof_root_persisted = true
kernel_timeline_verified = true
receipt_artifacts_verified = true
record_hash_verified = true
replay_side_effects_reexecuted = false
proof_gap = external_append_only_signer_missing
```

Operations recorded:

```text
1. real_browser.open -> completed
2. real_browser.extract_evidence -> completed
```

## Classification

```text
SQLite/content failure = NO
SiteScope authority failure = NO
Browser backend failure = NO
Model intent bridge failure = NO
Provider availability failure = YES
```

This is not a useful mission success because MiniMax did not reach a model-selected finish and the final answer was not produced.

## Safe Artifacts

```text
safe_bundle = sentinel-control/docs/reviews/deep_power_audit/C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_SOVEREIGN_V4/c5b_sovereign_v4.safe.json
runtime_root = .c5b_sentinel_chromium_minimax_m3_v4  # not committed
raw_provider_material_persisted_in_safe_bundle = false
```
