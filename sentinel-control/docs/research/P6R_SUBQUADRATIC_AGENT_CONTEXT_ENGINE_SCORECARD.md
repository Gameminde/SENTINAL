# P6R Subquadratic Agent Context Engine Scorecard

Date: 2026-05-10

## Verdict

```text
phase = P6R_SUBQUADRATIC_AGENT_CONTEXT_ENGINE_PROTOTYPE
status = FULL_LOCKED
previous_phase = P6Q_FULL_LOCKED
next_phase = P6S_DESKTOP_WORKSPACE_L6_PROMOTION
```

P6R creates the first Sentinel-native context engine that prepares compact LLM
decision frames from receipts, evidence cards, authority cards, progress cards,
selected tools, blockers, and required output schemas.

## Locked Components

```text
ContextNeedEstimator
ReceiptGraphRetriever
EvidenceRanker
StateCardBuilder
AuthorityCardBuilder
ToolSurfaceRouter
PromptBudgetAllocator
LLMDecisionFrame
DecisionFrameVerifier
DecisionFrameHash
ContextCompressionResult
```

## Acceptance Checklist

| Requirement | Status |
| --- | --- |
| Preserve authority constraints in frame | locked |
| Preserve critical evidence refs | locked |
| Keep receipt refs, not raw receipts | locked |
| Select only relevant authorized tools | locked |
| Respect user-selected model budget | locked |
| Demonstrate 20k-30k raw context to 1k-2k frame | locked |
| Produce deterministic frame hash | locked |
| Redact secret-like content | locked |
| Fail verifier when critical evidence is missing | locked |
| Add no new external execution powers | locked |
| Add no authority expansion | locked |

## Test Scope

```bash
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py -v --tb=short
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
```

Expected targeted result:

```text
P6R tests = 10 passed
P6Q neighbor tests = 8 passed
full sentinel-core suite = not run by instruction
```

## Locked Doctrine

```text
The user chooses the LLM.
Sentinel optimizes the selected LLM's context.
Sentinel may recommend alternatives, but does not silently override.
Receipts remain exact outside the prompt.
The LLM sees compact decision frames, not raw mission dumps.
```

## Boundary

P6R does not start Desktop Workspace L6, Code/Shell harvest, a new organ
family, browser expansion, payment/spend execution, trading execution,
credential access, production mutation, vendor runtime bridging, or authority
expansion.
