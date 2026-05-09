# P6J1 Power Surface Doctrine Reframe

Date: 2026-05-09

## Goal

P6J1 corrects the P6J vocabulary so Sentinel describes core operator powers as
high-power surfaces, not as inherently dangerous features.

```text
Old framing:
defensive surface labels imply the capability should be slowed down or deleted

New framing:
high-power surfaces are classified, authorized, evaluated, and promoted
```

This is a doctrine and model-language correction. It does not add live external
execution powers.

## Product Doctrine

```text
Sentinel is powerful-by-authority, not safe-by-refusal.
Power is governed capability, not bypass.
Blocked-by-default means not unlocked until authority and promotion exist.
High-power surfaces are product powers and operator powers.
```

High-power surfaces include:

```text
advanced browser operation
live external API use
live channel send
scoped credential use
spend/payment execution
trading execution
desktop/sidecar control
stealth-class browser operation
```

These powers are not deleted. They are classified and moved through the
promotion ladder when Sentinel has explicit authority, eval evidence, receipts,
kill switches, replay, and FinalGate compatibility.

## Black Lane Misuse Objectives

Misuse objectives remain blocked:

```text
fake identity
KYC bypass
credential theft or raw secret extraction
illegal spam
deceptive identity
unlawful evasion
profit guarantees
vendor runtime bridge
budget overrun
unbacked signal spend
```

The distinction is important:

```text
The capability is studied and controlled.
The misuse objective is rejected.
```

## Model Changes

`AgentLabImplementationAlignmentEntry` now uses:

```text
high_power_surfaces
authorized_surfaces
evaluated_surfaces
sandboxed_capability_surfaces
capability_promotion_surfaces
black_lane_blocked_objectives
```

It no longer uses legacy defensive surface fields as the public model language.

## Acceptance Rule

```text
Every high-power surface must have a capability handling path.
Every organ must declare Black Lane misuse objectives.
No vendor runtime bridge.
No vendor code copy.
No silent authority expansion.
No new live execution power in P6J1.
```
