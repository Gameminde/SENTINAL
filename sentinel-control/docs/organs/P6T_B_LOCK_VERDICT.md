# P6T-B Lock Verdict

Date: 2026-05-10

## Verdict

```text
phase = P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_IMPLEMENTATION
verdict = FULL_LOCKED
previous_phase = P6T_A_FULL_LOCKED
next_phase = P6U_API_AUTHENTICATED_READ_L6
```

## Summary

P6T-B promotes the existing Sentinel browser organ to controlled navigation L6.

Sentinel can now do scoped browser navigation:

```text
allowed-domain public page navigation/read
redirect-chain verification
domain/scheme proof
compact page evidence cards
link/action candidate refs
navigation receipts
P6R-compatible decision-frame slices
normal/sandbox/proposal/black-lane route classification
```

## Required Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/browser/navigation_l6.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_controlled_navigation_l6.py
sentinel-control/docs/organs/P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_SCORECARD.md
sentinel-control/docs/organs/P6T_B_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## What Locked

```text
BrowserNavigationAuthority requires mission/root authority, allowlisted domains,
allowed schemes, allowed operation classes, timeout and byte budgets, expiry,
evidence refs, trace refs, and P6T-A source-binding refs.

BrowserNavigationAdapter permits only normal read-only navigation to
allowlisted http/https public domains.

BrowserRiskRouter classifies suspicious schemes and actions into
NORMAL_NAVIGATION, QUARANTINE_SANDBOX_INSPECTION, PROPOSAL_ONLY, or
BLACK_LANE_BLOCK.

BrowserNavigationReceipt records requested URL, final URL, redirect chain,
domain proof, scheme proof, action type, authority ref, source-binding refs,
timeout/cost trace, compact summary hash, page content hash, and link candidate
refs.

BrowserNavigationDecisionFrameSlice keeps raw pages, full DOM dumps, all links,
and untrusted page instructions out of the LLM-facing context.

BrowserNavigationFinalGate rejects missing receipt, missing source-binding refs,
forbidden scheme, missing allowlist proof, missing timeout budget, kill switch,
proposal-only route, black-lane route, unsafe receipt summary, receipt hash
mismatch, and authority expansion.
```

## Verification

```text
P6T-B targeted tests = 35 passed
P6C browser organ neighbor tests = 11 passed
P6R/P6Q context economy neighbor tests = 26 passed
P6M reality activation neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

Command:

```bash
python -m pytest tests/test_p6_browser_controlled_navigation_l6.py -v --tb=short
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

## Boundaries

```text
new browser organ family = no
login/session mutation = no
form submit = no
file upload = no
file download automation = no
payment/checkout = no
publishing/posting/sending = no
arbitrary JS execution = no
stealth/captcha/bypass = no
browser profile takeover = no
personal/default browser profile connection = no
credential secret access = no
browser power expansion beyond controlled navigation = no
vendor runtime bridge = no
vendor code copy = no
authority expansion = no
```

## Next Phase

```text
P6U_API_AUTHENTICATED_READ_L6
```
