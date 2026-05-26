# Browser Operator Agent L4/L5 Live Report

Date: 2026-05-26

## Current State

This pack promotes the existing browser substrate into a visible operator-facing
power path:

```text
Power Lab CLI
-> BrowserOperatorAgentL4L5Live
-> BrowserControlledCapabilityRunner
-> PlaywrightReadOnlyRenderer / PlaywrightLimitedInteractionBackend
-> Browser evidence artifacts
-> Browser organ FinalGate checks
```

This is the first live browser actuator path in the current power-kernel line.
It is not another read-only-only specification.

## Models And Contracts Added

- `BrowserOperatorLiveActionKind`
- `BrowserOperatorLiveStatus`
- `BrowserOperatorLiveContract`
- `BrowserOperatorLiveRequest`
- `BrowserOperatorLiveSafetyValidationResult`
- `BrowserOperatorLiveReceipt`
- `BrowserOperatorLiveResult`
- `BrowserOperatorAgentL4L5Live`

Receipts remain measurement data:

```text
authority_effect = none
data_not_instruction = true
can_grant_authority = false
can_approve_future_execution = false
```

## Live Browser Power

Implemented:

- L4 public browser observation through the real Playwright renderer.
- Screenshot, DOM/text, AX snapshot, network ledger, and artifact receipts.
- L5 limited interaction through the real Playwright interaction backend.
- Observation-before-action with snapshot/page hash binding.
- Browser FinalGate checks over browser capability receipts, dry-run plans, and
  execution contracts.
- CLI commands:
  - `sentinel browser-observe`
  - `sentinel browser-act --action type`

## Boundaries

Blocked explicit action routes:

- browser submit
- browser login
- upload
- download
- arbitrary browser JavaScript
- credential access
- API mutation
- channel send
- shell/process
- desktop action
- payment/spend/trading

Important limitation:

```text
The explicit submit route is not promoted. A future click/action pack still
needs stronger element-effect classification before submit-grade workflows are
claimed safe or controlled. Persistent sessions and credentialed login remain
NOT_STARTED.
```

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_operator_agent_l4_l5_live.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/__init__.py`
- `sentinel-control/services/sentinel-core/sentinel/cli.py`
- `sentinel-control/services/sentinel-core/sentinel/organs/browser/accessibility_snapshot.py`
- `sentinel-control/services/sentinel-core/tests/test_browser_operator_agent_l4_l5_live.py`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md`
- `sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md`

## Verification

Targeted:

```text
python -m pytest tests/test_browser_operator_agent_l4_l5_live.py -q
12 passed
```

Regression:

```text
browser-related pytest selection
356 passed

python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_organ_safety_scanner_consolidation.py tests/test_mission_authority_and_credential_vault_foundation.py -q
45 passed
```

## Truth Table

| Segment | Status | Evidence | Limitation |
|---|---:|---|---|
| Live Playwright L4 observation | CLOSED | `test_live_l4_observe_uses_playwright_and_writes_evidence` | Public/domain-scoped only. |
| L4 screenshot/DOM/AX artifact proof | CLOSED | Same test plus browser regression suite | Output remains untrusted evidence. |
| Live L5 limited click/type interaction | CLOSED | `test_live_l5_click_executes_from_hash_bound_observation`, `test_live_l5_type_executes_from_hash_bound_observation` | Submit-grade workflows need separate authority and stronger element-effect classification. |
| CLI `browser-observe` | CLOSED | `test_cli_browser_observe_runs_existing_browser_engine` | Uses explicit mission file. |
| CLI `browser-act type` | CLOSED | `test_cli_browser_act_type_runs_existing_limited_interaction_engine` | No automatic workflow loop. |
| Explicit submit/login/upload/download/JS/credential routes | CLOSED | `test_live_operator_blocks_non_promoted_dangerous_actions` | Blocking is action-route level; stronger click-effect classification is future work. |
| Persistent browser session | NOT_STARTED | No session manager implemented | Next recommended pack. |
| Credentialed browser login | NOT_STARTED | No credential resolution or login backend promoted | Requires vault backend and special authority. |
| Browser FinalGate | CLOSED | `receipt.finalgate_verified is True` in L4 and L5 tests | Browser-specific FinalGate, not low-risk L2/L3 FinalGate. |

## Next Recommended Pack

```text
BROWSER_SESSION_MANAGER_L5_LIVE
```

Purpose:

- maintain governed public browser sessions across steps;
- track tab/session budgets;
- preserve before/after evidence per step;
- keep submit/login/credential as separate special-authority surfaces.
