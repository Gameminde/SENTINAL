# P6P Existing Organs Runtime Promotion Plan Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6P_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN
previous_phase = P6O_FULL_LOCKED
next_phase = P6Q_CODE_SHELL_AGENTLAB_HARVEST
```

## Goal

Convert the P6O real-world gauntlet evidence into a deterministic L6 promotion
plan for existing organs only.

P6P does not create a new organ family. It decides which current power surfaces
should be promoted next and what each promotion must require.

## Implemented Code

```text
sentinel-control/services/sentinel-core/sentinel/organs/runtime_promotion.py
sentinel-control/services/sentinel-core/tests/test_p6_existing_organs_runtime_promotion_plan.py
```

## Models

```text
RuntimePromotionCandidate
RuntimePromotionPlan
ExistingOrgansRuntimePromotionPlanner
```

## Deterministic Priority Order

```text
1. desktop_workspace_l6
2. browser_controlled_navigation_l6
3. api_authenticated_read_l6
4. channel_provider_draft_l6
5. credential_vault_ref_l6
6. capital_roi_feedback_l6
7. trading_live_paper_feed_l6
8. spend_provider_test_mode_l6
```

## Required Promotion Contract

Every candidate requires:

```text
source P6O evidence refs
required adapters
required authority
required receipts
rollback/disable plan
kill switch
FinalGate
no authority expansion
```

## High-Power Surfaces

P6P treats high-power surfaces as unlockable product powers, not deleted
features:

```text
real_payment_provider
real_broker_execution
live_channel_send
browser_login_session
desktop_screenshot_clipboard
```

These surfaces are deferred until their lower-level promotion path is proven.

## Black Lane Objectives

```text
misuse objectives
credential theft
fake identity
KYC bypass
illegal spam
unlawful evasion
profit guarantees
```

## Verification

```text
P6P targeted tests = 5 passed
P6O neighbor tests = 6 passed
P6N neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_existing_organs_runtime_promotion_plan.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_real_world_gauntlet.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_capability_frontier.py -v --tb=short
```
