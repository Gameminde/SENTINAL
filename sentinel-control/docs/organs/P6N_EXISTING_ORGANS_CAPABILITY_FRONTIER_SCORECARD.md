# P6N Existing Organs Capability Frontier Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6N_EXISTING_ORGANS_CAPABILITY_FRONTIER
previous_phase = P6M_FULL_LOCKED
next_phase = P6O_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN
```

## Goal

Push every P6M-activated organ to its current practical limit before adding
another organ family. This is a capability frontier review, not a safety-only
review.

P6N answers:

```text
what each organ can really do now
what it can do repeatedly
what it can do in combination with other organs
what fails
what is too weak
what needs runtime/provider work
what requires LLM runtime integration later
what should be promoted next
```

## Implemented Code

```text
sentinel-control/services/sentinel-core/sentinel/organs/capability_frontier.py
sentinel-control/services/sentinel-core/tests/test_p6_existing_organs_capability_frontier.py
```

## Frontier Models

```text
CapabilityFrontierReport
OrganCapabilityFrontier
MaxSupportedAction
CurrentLimit
FailureMode
MissingRuntimeSurface
PromotionCandidate
RequiredNextAdapter
RequiredLLMIntegration
RiskLaneFit
FrontierStressResult
FrontierLimitReport
CapabilityFrontierBuilder
OrganFrontierStressHarness
CrossOrganFrontierRunner
```

## Stress Coverage

| Organ | Frontier stress |
| --- | --- |
| Browser | multiple allowlisted reads, text/link extraction, timeout capture, non-allowlisted rejection |
| External API | allowlisted `GET` and `HEAD`, mutation rejection, domain rejection, error response capture |
| Channel | multiple local draft files, persisted draft receipts, live send rejection |
| Credentials | env ref resolution, redacted receipt, missing env rejection, wrong-scope rejection, revoked-grant gap |
| Desktop | workspace list/read/write/create, traversal rejection, outside-root rejection, shell/process rejection |
| Capital | real receipt ingestion, signal ledger, opportunity score, spend proposal, unbacked signal rejection |
| Trading | read-only market data, paper trade, real broker rejection, profit guarantee rejection |
| Spend | test-mode provider, budget/category/vendor scope, hidden subscription rejection, real provider rejection |

## Cross-Organ Scenarios

```text
Browser read -> Capital signal -> Spend proposal
API GET -> Capital signal -> Trading paper decision
CredentialRef env resolve -> API read-only request with redacted receipt
Desktop write local draft/report -> Channel draft receipt
Market data -> Trading paper trade -> Capital signal
Multiple receipts -> frontier report
```

## Frontier Findings

What Sentinel can do now:

```text
public browser reads
allowlisted read-only API requests
local channel drafts
env credential refs
workspace file operations
capital signal ingestion
market-data paper trading
test-mode spend
```

What Sentinel can only simulate/test-mode:

```text
live spend
real trading
channel send
desktop host control
```

What Sentinel cannot do yet:

```text
authenticated live provider workflows
account creation
browser mutation
shell execution
```

Blocked misuse objectives:

```text
credential theft
hidden identity
illegal spam
KYC bypass
profit guarantees
```

## Promotion Readout

```text
weakest_organ = credentials
closest_to_production_scoped_execution = desktop
organs_needing_llm_runtime_first = channel, capital, trading
promote_next = desktop workspace ops, browser controlled navigation, API authenticated read-only, channel provider drafts
```

## Verification

```text
P6N targeted tests = 8 passed
P6M neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_existing_organs_capability_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```
