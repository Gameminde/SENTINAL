# P6R5 Code-Grounded Review Addendum

Date: 2026-05-10

## Purpose

This addendum answers the post-lock correction: P6R5 cannot remain only a
theoretical review. The cognitive mechanics verdict must be grounded in actual
Sentinel code behavior before Desktop Workspace L6 starts.

## Code Zones Reviewed

```text
sentinel/agent/context_pressure.py
sentinel/agent/context_engine.py
sentinel/agent/decision_frame.py
sentinel/agent/evidence_ranker.py
sentinel/agent/state_cards.py
tests/test_p6_context_token_model_economy_frontier.py
tests/test_p6_subquadratic_agent_context_engine.py
```

## Findings Fixed

### P6Q hid over-budget decision frames

`ContextPressureAnalyzer` capped projected `decision_frame_tokens` at the
model budget before cost projection. That made an overloaded context look safe
and underpriced.

Locked correction:

```text
decision_frame_tokens = measured projection
decision_frame_over_budget = true when projection exceeds model budget
cost projection uses measured tokens, not a capped token count
```

### P6R critical evidence preservation was too broad

`ContextCompressionResult` treated any top-k evidence as enough to preserve
critical evidence. That did not prove that required evidence refs survived
compression.

Locked correction:

```text
required_evidence_refs are checked explicitly
missing_evidence_refs are reported
critical_evidence_preserved fails when required refs are missing
```

### P6R receipt replay was not graph-grounded

`DecisionFrameVerifier` only checked that receipt refs existed in the frame.
It did not check whether those refs were resolvable against a known receipt
graph.

Locked correction:

```text
known_receipt_ids can be supplied to the verifier
an empty known receipt graph is treated as authoritative, not as "no graph"
unresolvable receipt refs fail verification
receipt_refs_resolvable requires refs to resolve when a known graph is present
```

### Authority cards could expose forbidden tools as allowed

`AuthorityCardBuilder` could list the same tool in both allowed and forbidden
surfaces.

Locked correction:

```text
forbidden wins over allowed
allowed_tools removes any forbidden overlap
```

### Secret-like dict keys were not sanitized

`sanitize_context_payload` sanitized dict values but preserved raw keys.
Secret-like keys could survive inside stored frame cards.

Locked correction:

```text
dict keys and dict values are sanitized recursively
```

## Verification

```text
P6Q targeted tests = 9 passed
P6R targeted tests = 17 passed
P6M/P6O/P6P/P6L neighbor tests = 33 passed
full sentinel-core tests = not run by instruction
```

Targeted commands:

```bash
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py tests/test_p6_existing_organs_real_world_gauntlet.py tests/test_p6_existing_organs_runtime_promotion_plan.py tests/test_p6_desktop_sidecar_organ.py -v --tb=short
```

## Lock Impact

```text
Desktop L6 started = no
Code/Shell harvest started = no
new organ family = no
new external execution powers = no
authority expansion = no
```

The P6S go condition remains valid, but now it is code-grounded: Desktop
Workspace L6 must use P6R decision frames, preserve required evidence refs,
resolve receipt refs, report over-budget frames honestly, and never dump raw
workspace state into the selected LLM.
