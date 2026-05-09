# Advisory To Executable Promotion Ladder

## Levels

```text
L0 vendor observation
L1 extraction matrix
L2 Sentinel contract
L3 fake eval
L4 dry-run
L5 sandbox
L6 limited execution
L7 production-scoped execution
L8 continuous OrganBench monitoring
```

## Promotion Requirements

Every organ phase must declare:

```text
current promotion level
target promotion level
blocked promotion levels
required evidence to promote
rollback/demotion criteria
```

## Non-Negotiable Rule

No organ reaches L6 until it has:

```text
contract
authority mapping
risk profile
dry-run receipt
execution receipt
trace events
fake benchmark
kill switch
FinalGate compatibility
```

## Autonomy And Risk Lanes

Sentinel is powerful by authority, not safe by refusal. The promotion ladder
does not mean dangerous powers are deleted forever. It means they are not
executable until the correct organ level, authority, controls, receipts, replay,
kill switch, and FinalGate proof exist.

```text
Green Lane:
- local, reversible, low-risk actions
- auto-execute when allowed by root authority and local policy

Blue Lane:
- external read-only or low-risk actions
- auto-execute with trace when authorized

Orange Lane:
- cost/account/message/API actions
- execute inside explicit RootAuthorityEnvelope and risk budget
- no micro-approval for every small authorized action

Red Lane:
- high-risk actions such as trading, spend runtime, credentials,
  desktop/sidecar, stealth browser
- require special authority, caps, receipts, kill switch, and FinalGate

Black Lane:
- fraud, fake identity, KYC bypass, credential theft, illegal spam,
  unlawful evasion, profit guarantees
- always blocked as misuse objectives
```

## Promotion Meaning

```text
blocked-by-default = not executable until promoted
blocked-by-default != forbidden forever
misuse objective = forbidden even if the capability exists
```

Risk is allowed only when:

```text
user authority is explicit
risk budget exists
action class is promoted
receipts/replay exist
kill switch exists
FinalGate passes
```

Risk is not allowed when:

```text
it crosses root authority
it hides cost or identity
it creates unapproved obligation
it violates legal/compliance boundaries
it bypasses policy
```
