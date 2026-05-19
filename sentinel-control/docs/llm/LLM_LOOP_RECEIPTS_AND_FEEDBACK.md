# LLM Loop Receipts And Feedback

Status: docs/spec lock candidate

## Purpose

Sentinel must make the LLM stronger over time by giving it safe memory of what
happened.

```text
memory -> reasoning -> delegated action -> receipt -> feedback -> better reasoning
```

Receipts are the LLM's memory of truth. They are not authority.

## Receipt Classes

Future role and action loops should produce:

- role-loop receipt;
- proposal receipt;
- gate decision receipt;
- delegated lane receipt;
- organ execution receipt;
- blocked action receipt;
- budget receipt;
- evidence receipt;
- rollback/revocation receipt;
- FinalGate receipt.

## Safe Receipt Rules

Receipts may contain:

- ids;
- hashes;
- provider/backend/model ids;
- role ids;
- action level;
- risk class;
- budget use;
- gate decision;
- evidence refs;
- receipt refs;
- sanitized summaries;
- FinalGate result.

Receipts must not contain:

- raw provider keys;
- raw Bearer tokens;
- raw prompts;
- raw provider responses;
- raw reasoning or thinking fields;
- hidden action payloads;
- secrets;
- unredacted credentials.

## Feedback Into Cognition

The LLM may receive safe summaries of:

- what worked;
- what failed;
- what was blocked;
- why the gate rejected an action;
- what evidence was missing;
- what budget was wasted;
- what risk was underestimated;
- what rollback occurred.

Feedback should improve:

- future strategy;
- evidence discipline;
- risk anticipation;
- plan quality;
- budget efficiency;
- organ action precision;
- self-improvement proposals.

## Feedback Cannot Do

Feedback cannot:

- grant authority;
- rewrite history;
- mark unsupported claims as verified;
- override provider/backend/model choice;
- unlock credentials;
- allow skipped user approval;
- bypass FinalGate.

## Living Mission Memory

`LivingMissionMemory` is future safe mission memory made from:

- evidence;
- receipts;
- traces;
- past failures;
- rejected plans;
- successful strategies;
- open questions;
- uncertainty;
- learned patterns.

It improves reasoning without expanding authority.
