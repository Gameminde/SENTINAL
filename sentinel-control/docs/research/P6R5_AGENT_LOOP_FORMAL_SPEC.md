# P6R5 Agent Loop Formal Spec

Date: 2026-05-10

## Loop Name

```text
Sentinel Authority-Bound Cognitive Control Loop
```

## Canonical Loop

```text
observe
-> normalize evidence
-> estimate entropy
-> estimate context need
-> retrieve receipt refs
-> build compact decision frame
-> call user-selected LLM
-> verify output
-> route organ/tool
-> execute limited action or dry-run/proposal
-> create receipt
-> update workspace/beliefs
-> replay/FinalGate
-> continue or stop
```

## Step Contracts

| Step | Input | Output | Hard rule |
| --- | --- | --- | --- |
| observe | organ output, user input, receipts | evidence candidates | observation never grants authority |
| normalize evidence | raw output | evidence refs, receipt refs | raw data stays replayable outside prompt |
| estimate entropy | mission state | entropy estimate | entropy informs routing only |
| estimate context need | objective, blockers, tools | context need | no model override |
| retrieve receipt refs | receipt graph | top-k receipts | no raw receipt dump |
| build decision frame | state cards, evidence cards | `LLMDecisionFrame` | authority card required |
| call LLM | compact frame | candidate decision | user-selected model only |
| verify output | candidate decision | accepted/rejected action | action cannot expand authority |
| route organ/tool | accepted action | organ route | only promoted surfaces |
| execute/dry-run | route + authority | receipt | execution must create receipt |
| update state | receipt | workspace/beliefs/signals | rejected claims stay rejected |
| replay/FinalGate | trace + receipt | pass/fail | failure blocks continuation |

## LLM Boundary

The model receives:

```text
mission card
authority card
progress card
top-k evidence summaries
selected tool surface only
current blockers
next decision options
required output schema
receipt refs
```

The model does not receive by default:

```text
all receipts
all files
all pages
all API responses
all channel messages
all tool schemas
all debate transcripts
all historical state
raw secrets
```

## Action Verification

An LLM output becomes actionable only if:

```text
output_schema_valid = true
required_evidence_refs_present = true
authority_card_allows = true
organ_promotion_level_allows = true
risk_lane_allows = true
FinalGate_passes = true
receipt_plan_exists = true
kill_switch_compatible = true
```

If any condition fails:

```text
return safer alternative
or create AuthorityExtensionProposal
or stop
```

## Where P6S Must Attach

P6S Desktop Workspace L6 attaches only at:

```text
route organ/tool
execute limited action or dry-run/proposal
create receipt
update workspace/beliefs
```

It must also feed P6R:

```text
workspace state card
diff summary card
rollback ref
path containment proof
desktop receipt refs
```

It must not feed raw workspace dumps into the model.

## State Transition Invariant

```text
S_{t+1} = update(S_t, receipt_t)
```

No receipt means no trusted state transition.

No authority means no execution transition.

No FinalGate pass means no production-scoped transition.
