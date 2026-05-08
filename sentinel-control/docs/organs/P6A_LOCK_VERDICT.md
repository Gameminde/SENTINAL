# P6A Lock Verdict

Date: 2026-05-09

## Verdict

```text
P6A_EXTERNAL_ORGAN_FOUNDRY = FULL_LOCKED
```

P6A is accepted as full locked. The organ foundry now defines and verifies the
minimum contract surface for future external powers while preserving Sentinel's
authority boundary.

## Accepted Scope

```text
ExternalOrganContract
ExternalOrganRegistry
OrganAuthorityEnvelope
OrganRiskProfile
OrganDryRunReceipt
OrganExecutionReceipt
OrganReplayRecord
OrganKillSwitch
OrganPromotionGate
VendorHarvestReference
```

## Locked Rules

```text
No organ can execute from a harvest reference.
No vendor code copy grants runtime authority.
No vendor runtime bridge is allowed.
No context signal can expand authority.
No workspace fact can expand authority.
No memory item can expand authority.
No expected profit can expand authority.
No dry-run-only authority can start execution.
No execution-shaped receipt can start without explicit executable authority.
No execution-shaped receipt can start when kill switch is triggered.
No payment/trading/account/credential action class is executable by default.
Promotion toward execution requires eval dataset, risk map, failure modes,
rollback/disable plan, receipts, kill switch, and FinalGate compatibility.
```

## Verification

```text
targeted P6A tests = 20 passed
P5L integrated review tests = 23 passed
full sentinel-core regression = 638 passed
```

## Next Phase

```text
next_phase = P6B_AGENT_LAB_ORGAN_HARVEST
```

P6B may classify Agent Lab findings into organ candidates. P6B must not import
vendor runtime, copy vendor code into production, bridge external systems, or
add execution powers.
