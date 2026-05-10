# P6R Lock Verdict

Date: 2026-05-10

```text
phase = P6R_SUBQUADRATIC_AGENT_CONTEXT_ENGINE_PROTOTYPE
verdict = FULL_LOCKED
previous_phase = P6Q_FULL_LOCKED
next_phase = P6S_DESKTOP_WORKSPACE_L6_PROMOTION
```

## What Locked

P6R locks a prototype subquadratic agent context engine. It converts large
multi-organ context into a compact `LLMDecisionFrame` using top-k receipts,
evidence cards, state cards, authority cards, selected tools, blockers, and
required output schema.

## Why It Matters

P6Q proved that stronger organs create token pressure through receipts, tool
schemas, browser/API outputs, workspace state, channel drafts, and market
signals. P6R gives Sentinel a context economy layer before Desktop Workspace L6
so real organs can become stronger without flooding the selected model.

## Locked Guarantees

```text
User-selected model is preserved.
Prompt budget is derived from UserModelContract.
Authority constraints are carried into the frame.
Critical evidence refs are carried into the frame.
Required evidence refs can be checked explicitly after compression.
Raw receipts remain outside the prompt.
Receipt refs remain replayable.
Receipt refs can be checked against a known receipt graph.
An empty known receipt graph is authoritative and rejects all frame receipt refs.
Tool surface is minimized.
Frame hash is deterministic.
Secret-like content is redacted in values and keys.
Stored frame cards are sanitized before hashing and persistence.
Over-budget frames remain measurable and fail the budget check.
Forbidden tools win over allowed-tool overlap.
Missing critical evidence fails verification.
```

## Boundaries

```text
new external execution powers = 0
desktop L6 started = no
code/shell harvest started = no
new organ family = no
payment/spend execution = no
trading execution = no
credential access = no
authority expansion = no
vendor runtime bridge = no
```

## Verification

```bash
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py -v --tb=short
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
```

Expected result:

```text
P6R targeted tests = 17 passed
P6Q neighbor tests = 9 passed
full sentinel-core suite = not run by instruction
```
