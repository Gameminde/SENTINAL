# LLM Role Hierarchy

Status: docs/spec lock candidate

## Purpose

The role hierarchy organizes maximum cognition without pretending every model
call should perform the same job. In the first implementation, all roles should
use the same user-selected provider/backend/model. Multi-model specialization
comes later only by explicit contract.

## Role Order

```text
Visionary
-> Strategist
-> Researcher
-> Planner
-> Critic
-> Verifier
-> Risk Reviewer
-> Operator Planner
-> Coder Advisor
-> Synthesizer
```

This is not a rigid pipeline. Roles may loop back when evidence, risk,
criticism, or failed execution changes the mission state.

## Role Purposes

| Role | Primary power | Main output |
| --- | --- | --- |
| Visionary | Generate bold possibilities and opportunities. | Option set, hypotheses, surprising angles. |
| Strategist | Choose coherent mission strategy. | Strategy brief and tradeoffs. |
| Researcher | Find what must be known. | Research questions, evidence needs, source plan. |
| Planner | Turn strategy into plan. | Ordered plan and proposal artifacts. |
| Critic | Attack weak reasoning. | Failure modes and objections. |
| Verifier | Bind claims to evidence. | Evidence verdicts and uncertainty map. |
| Risk Reviewer | Classify authority, budget, and safety risk. | Risk posture and gate expectations. |
| Operator Planner | Translate plan into organ/action candidates. | Delegated action candidates. |
| Coder Advisor | Plan code/project changes. | Patch plan, test plan, architecture notes. |
| Synthesizer | Merge role outputs into a clear next move. | Final role-loop summary and decision packet. |

## Loopback Rules

Loopback is allowed when:

- Critic finds a blocking weakness;
- Verifier finds missing evidence;
- Risk Reviewer finds authority mismatch;
- Operator Planner cannot map proposal to an allowed organ lane;
- execution receipt shows failure;
- budget ledger shows waste;
- user feedback changes priority.

Loopback does not grant new authority. It only improves cognition.

## First Implementation Target

The first runtime implementation after this spec should be:

```text
STRICT_SINGLE_MODEL_ROLE_LOOP
```

Rules:

- same user-selected provider/backend/model for every role;
- no fallback;
- no AUTO routing;
- no organ execution from role output;
- role outputs are safe artifacts and receipts;
- delegated action execution comes in a later pack.
