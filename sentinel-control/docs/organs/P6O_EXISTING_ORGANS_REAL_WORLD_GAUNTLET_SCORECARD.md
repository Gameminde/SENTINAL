# P6O Existing Organs Real World Gauntlet Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6O_EXISTING_ORGANS_REAL_WORLD_GAUNTLET
previous_phase = P6N_FULL_LOCKED
next_phase = P6P_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN
```

## Goal

Expose the organs already activated by P6M to a stronger practical gauntlet
before creating any new organ family.

This phase is power-first:

```text
push existing organs harder
run them in repeated/batch mode
combine them into cross-organ paths
fix concrete weak points found during the push
turn the measured limits into promotion candidates
```

P6O is not a refusal phase. It is a reality-pressure phase.

## Implemented Code

```text
sentinel-control/services/sentinel-core/sentinel/organs/real_world_gauntlet.py
sentinel-control/services/sentinel-core/sentinel/organs/reality_activation.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_existing_organs_real_world_gauntlet.py
```

## New Models

```text
EnvCredentialGrant
RealityCredentialGrantStore
OrganRealWorldGauntletResult
RealWorldGauntletReport
ExistingOrganRealWorldGauntlet
ExistingOrganRealWorldGauntletRunner
```

## Strengthening Applied

| Organ | P6O push |
| --- | --- |
| Browser | multi-page public reads, link extraction, fetch failure capture, allowlist rejection |
| External API | batch `GET`/`HEAD`, error response capture, mutation/domain rejection |
| Channel | multi-draft local campaign creation with receipts |
| Credentials | env refs now pass through scoped grant, expiry, revocation, and redaction checks |
| Desktop | batch workspace create/write/read/list plus stronger root containment via `Path.relative_to` |
| Capital | receipt-backed signal ledger and spend proposal from cross-organ evidence |
| Trading | multi-symbol read-only market data and paper-trade basket journal refs |
| Spend | multi-vendor test-mode spend with budget, category, vendor, and subscription guard checks |

## Cross-Organ Paths

```text
Browser + API + Desktop + Channel receipts -> Capital assessment
Market data -> Trading paper basket -> Capital signal
Capital assessment -> Spend test-mode proposal/execution path
Credential grant -> API redacted path
```

## Fixed Limits

P6O fixes the weakest P6N gap in credentials by adding:

```text
EnvCredentialGrant
grant expiry checks
grant revocation checks
grant scope checks
grant env-var binding
redacted resolution receipt preservation
```

P6O also hardens local path containment by replacing string-prefix containment
with `Path.relative_to` checks for:

```text
LocalChannelDraftStore
DesktopWorkspaceOperator
```

## Remaining Limits

```text
browser live login/session handling
browser form submit and browser mutation
authenticated API provider adapters
live channel provider drafts/send
real vault adapter and provider credential injection
live desktop host control, screenshot, clipboard, app/window actions
capital live ROI feedback loop
real payment provider
real broker execution and live risk monitor
```

These are not deleted powers. They are next-promotion surfaces.

## Promotion Candidates

```text
desktop_workspace_l6
browser_controlled_navigation_l6
browser_session_read_l6
api_authenticated_read_l6
api_rate_limit_ledger_l6
channel_provider_draft_l6
credential_vault_ref_l6
scoped_provider_injection_l6
capital_roi_feedback_l6
capital_spend_bridge_l6
trading_live_paper_feed_l6
trading_risk_monitor_l6
spend_provider_test_mode_l6
spend_refund_cancel_l6
```

## Verification

```text
P6O targeted tests = 6 passed
P6N neighbor tests = 8 passed
P6M neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_existing_organs_real_world_gauntlet.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_capability_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```
