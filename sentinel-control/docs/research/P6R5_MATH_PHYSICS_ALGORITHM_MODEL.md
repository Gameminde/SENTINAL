# P6R5 Math Physics Algorithm Model

Date: 2026-05-10

## Mathematical Model

Sentinel mission state at step `t`:

```text
S_t = (
  G_t,  mission goal and success criteria
  U_t,  user constraints and preferences
  E_t,  MissionAuthorityEnvelope / RootAuthorityEnvelope
  W_t,  MissionGlobalWorkspace
  B_t,  BayesianBeliefState
  R_t,  receipt graph and replay records
  O_t,  organ registry and promotion levels
  M_t,  UserModelContract
  K_t,  known blockers and open questions
  H_t   trace history
)
```

Possible actions:

```text
A_t = {
  observe,
  retrieve,
  compress,
  ask_model,
  plan,
  dry_run,
  execute_limited,
  propose_authority_extension,
  reject,
  stop
}
```

Selected context:

```text
C_t = f_context(S_t, M_t, budget_t)
```

P6R defines `C_t` as an `LLMDecisionFrame`, not as the raw state.

Decision objective:

```text
a_t = argmax_a [
  E(progress | S_t, a)
  + E(information_gain | S_t, a)
  - token_cost(C_t, M_t)
  - latency_cost(a)
  - risk_cost(a)
  - retry_cost(a, M_t)
]
```

Subject to:

```text
authority_allows(E_t, a) = true
risk(a) <= allowed_risk(E_t)
receipt_integrity(R_t, a) = true
no_authority_expansion(a) = true
FinalGate(S_t, a) = pass
```

This is the formal Sentinel difference: action value is not enough. A valuable
action still fails if authority, receipt integrity, or FinalGate fails.

## Physical / Control-System Model

Sentinel can be modeled as a feedback-control system:

```text
sensors =
  browser receipts
  API receipts
  channel draft receipts
  desktop workspace receipts
  market data receipts
  spend test-mode receipts
  user feedback

controller =
  Brain L4
  authority envelope
  context engine
  evidence ranker
  FinalGate

actuators =
  promoted organs
  dry-run organs
  proposal generators

memory =
  workspace
  belief state
  receipt graph
  trace chain
  skill/procedure graph

energy / cost =
  tokens
  latency
  dollars
  risk
  user attention

feedback =
  receipts
  verifier outcomes
  error states
  success/failure signals
  replay checks
```

This is stronger than a plain prompt/tool loop because the loop has persistent
state, receipts, authority constraints, replay, and promotion levels.

It is not yet a complete feedback-control agent because the live LLM runtime,
long mission runner, and production organ wiring are still incomplete.

## Algorithmic Model

Target mission loop:

```text
while mission_not_done:
    S_t = build_state()
    entropy = MissionEntropyEstimator(S_t)
    route = AgentCountController(entropy, budget)
    society = AgentSocietyManager(route, authority)
    workspace_snapshot = MissionGlobalWorkspace.snapshot(S_t)
    belief_state = BayesianBeliefState.update(evidence)
    debate_route = AdaptiveDebateRouter(entropy, contradictions, impact)
    action_scores = EpistemicActionEvaluator(candidate_actions)
    context_need = ContextNeedEstimator(S_t, next_decision)
    receipts = ReceiptGraphRetriever(R_t, context_need)
    evidence_cards = EvidenceRanker(receipts, context_need)
    tools = ToolSurfaceRouter(candidate_tools, authority, context_need)
    frame = LLMDecisionFrame(
        mission_card,
        authority_card,
        progress_card,
        top_k_evidence,
        selected_tool_surface=tools,
        blockers,
        next_options,
        receipt_refs
    )
    DecisionFrameVerifier(frame)
    model_output = call_user_selected_llm(frame)
    proposed_action = parse_and_verify(model_output)
    organ_route = route_promoted_organ(proposed_action)
    result = execute_or_dry_run(organ_route)
    receipt = create_receipt(result)
    R_t = append_receipt(receipt)
    W_t = update_workspace(receipt)
    B_t = update_beliefs(receipt)
    FinalGate.verify(S_t, receipt)
```

## Complexity Analysis

Naive context strategy:

```text
prompt_tokens_t = O(|history| + |receipts| + |workspace| + |tools|)
```

This grows badly as organs produce more outputs.

P6R strategy:

```text
receipt_selection = O(n log n) for n receipt candidates
tool_selection = O(m) for m candidate tools
frame_tokens = O(k + selected_tools + cards)
```

Where `k` is top-k evidence, not all receipts.

The intended shape:

```text
raw_context = 20k-30k tokens or more
decision_frame = 1k-2k tokens
exact_receipts = outside prompt, replayable by refs
```

## Deterministic vs LLM-Dependent Parts

Deterministic now:

```text
entropy heuristics
agent count route
workspace deltas
belief update constraints
receipt ranking heuristics
tool surface routing
prompt budget checks
frame hashing
authority and FinalGate checks
test-mode organ receipts
```

LLM-dependent later:

```text
semantic interpretation of compact frames
creative strategy generation
ambiguous action choice
long-horizon plan repair
tradeoff explanation
natural-language product decisions
```

The architecture is healthy only if deterministic layers constrain the LLM,
not if the LLM silently replaces them.
