# P6A External Organ Foundry Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6A_EXTERNAL_ORGAN_FOUNDRY
status = FULL_LOCK_CANDIDATE
previous_phase = ARCHITECTURE_A_TO_Z_LOCKED
next_phase = P6B_AGENT_LAB_ORGAN_HARVEST
```

## Purpose

P6A creates the Sentinel-native contract layer for future external organs. It
does not add new runtime powers. Its job is to make sure every harvested power
has authority mapping, risk profiling, dry-run receipts, execution receipt
shape, replay, kill switch, promotion gates, and FinalGate compatibility before
any future execution level.

## Required Models

```text
ExternalOrganContract = present
ExternalOrganRegistry = present
OrganAuthorityEnvelope = present
OrganRiskProfile = present
OrganDryRunReceipt = present
OrganExecutionReceipt = present
OrganReplayRecord = present
OrganKillSwitch = present
OrganPromotionGate = present
VendorHarvestReference = present
```

## Hardening Results

```text
authority mapping required = pass
risk profile schema required = pass
dry-run receipt schema required = pass
execution receipt schema required = pass
trace/event compatibility required = pass
kill-switch compatibility required = pass
FinalGate compatibility required = pass
vendor code copy blocked = pass
vendor runtime bridge blocked = pass
VendorHarvestReference authority grant blocked = pass
signals/workspace/memory/expected profit cannot expand authority = pass
payment/trading/account/credential action classes blocked by default = pass
dry-run-only execution blocked = pass
execution-shaped request requires explicit authority and kill switch = pass
forged dry-run hash rejected = pass
forged execution hash rejected = pass
replay checks dry-run/execution linkage = pass
promotion gate requires eval dataset = pass
promotion gate requires risk map = pass
promotion gate requires failure modes = pass
promotion gate requires rollback/disable plan = pass
promotion gate requires FinalGate adapter = pass
```

## Tests

```text
python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
result = 20 passed

python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
result = 23 passed

python -m pytest tests -v --tb=short
result = 638 passed
```

## No-Power Confirmation

```text
browser execution added = no
payment/spend runtime added = no
trading runtime added = no
account creation runtime added = no
credential access added = no
vendor runtime bridge added = no
vendor code copied = no
silent authority expansion = no
```

## Autonomy/Risk Lane Correction

P6A safety is not a permanent restriction. It is a promotion boundary.

```text
blocked-by-default = not executable until promoted
blocked-by-default != forbidden forever
```

Sentinel must compete with highly automated agents by becoming more autonomous
inside explicit authority, not by refusing all risk. Future phases may promote
Orange and Red Lane action classes when explicit root authority, risk budget,
receipts, replay, kill switch, and FinalGate compatibility exist.

Black Lane misuse objectives remain always blocked:

```text
fraud
fake identity
KYC bypass
credential theft
illegal spam
unlawful evasion
profit guarantees
```

## Review Notes

P6A is a foundry layer, not an organ runtime. It allows Sentinel to classify and
prepare future powers without executing them. External execution remains gated
behind later promotion levels and phase-specific lock criteria.
