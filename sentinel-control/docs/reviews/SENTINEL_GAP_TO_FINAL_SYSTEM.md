# Sentinel Gap To Final System

Date: 2026-05-18
Mode: docs-only gap audit.

## Final Intended Sentinel

The final system is a general mission-governed agent and Mission OS:

```text
user mission and authority contract
-> model-powered planning, research, critique, verification
-> bounded organ proposals
-> user approval / special authority where needed
-> controlled browser/desktop/API/channel/credential/spend/trading actions
-> trace, receipts, rollback, replay
-> FinalGate certification
```

The LLM is the raw intelligence engine. Sentinel is the control system around
that intelligence: authority, execution, memory, evidence, planning, receipts,
review, and final certification.

## Gap Summary

| Gap | Current state | Final target |
| --- | --- | --- |
| State truth | Current docs stale vs latest code | Single accurate state lock and README |
| LLM usage | One-pass structured decision/result | Iterative planner/critic/verifier/model roles |
| Provider breadth | Groq proven; OpenRouter/NVIDIA diagnostic; catalog/base ready | Multiple explicit user-selected providers with native policies |
| Budget | Frame budget exists; action/mission token budgets open | End-to-end model/tool/mission token and cost governance |
| Brain | Internal L4 control modules locked | Live model-backed Brain roles with no authority expansion |
| Organs | Many staged organ modules | Product-grade controlled execution across approved surfaces |
| Browser | Strong research/modules/benchmarks | User-approved browser workflow automation |
| Desktop | Workspace/sidecar concepts | Controlled desktop project execution |
| External API | Contracts/dry-run | P6U authenticated read, later write/mutation by explicit authority |
| Channels | Draft/compliance models | User-approved sends and inbox workflows |
| Credentials | Scoped concepts | Real safe vault/ref lifecycle |
| Product UI | Docs/mock/specs | Usable Mission OS interface |
| Long horizon | Plans and benches | Durable mission memory, resumption, rollback, audits |

## Top 10 Missing Pieces

1. Current state lock consolidation after runtime wiring, real runtime
   validation, provider catalog, and provider-base hardening.
2. Action token-budget closure.
3. Mission token-budget closure.
4. Explicit deferral split for model execution:
   real provider adapter success vs runtime wiring vs budget governance.
5. Deep model role architecture:
   planner, critic, verifier, researcher, coder, strategist.
6. Model loop receipts:
   per-role prompt/result hashes, no raw prompt/response/reasoning durability.
7. Native provider packs with skip-safe tests and redaction rules.
8. Browser/desktop/API/channel organ integration through model proposals,
   not model execution.
9. Product workflow layer that exposes authority, approval, trace, and receipts
   to users.
10. Long-horizon mission state, replay, rollback, and resume controls.

## Biggest Illusions To Avoid

1. "Real provider call means full AI agent."
   False. It proves the model path, not deep cognition or product execution.

2. "Brain docs mean live Brain."
   False. Brain L4 internal layers are implemented/tested, but many are not
   model-backed live loops.

3. "Provider catalog means provider routing."
   False. Catalog is metadata and policy. Recommendations cannot execute.

4. "Organs exist so Sentinel can use them freely."
   False. Organs require explicit authority, promotion gates, receipts, and
   FinalGate.

5. "Fallback improves reliability automatically."
   Dangerous. Fallback changes provider/model and can violate user-selected
   model doctrine unless explicitly contracted.

## Final LLM-Powered Sentinel Vision

When full LLM power is unlocked safely, Sentinel can become:

- an autonomous research mission runner that collects evidence, challenges its
  own hypotheses, and produces cited conclusions;
- a product launch generator that builds GTM packs, landing copy, lead-source
  plans, outreach drafts, and risk reviews without sending anything unless
  authority permits;
- a codebase planner and refactor strategist that proposes patches and test
  plans while execution remains controlled;
- a browser workflow planner that understands pages/screens and proposes
  authority-bound interactions;
- a desktop project assistant that manages local workspace actions only under
  explicit sidecar/workspace contracts;
- a document/OCR intelligence system with vision models and evidence receipts;
- a multi-model debate system where cheap models draft, strong models reason,
  critic models attack, and verifier models check evidence;
- a business opportunity discovery engine that keeps opportunity separate from
  authority;
- a self-reviewing agent that records uncertainty, alternatives, and failures
  without mutating policy or code on its own;
- a Mission OS where every action has trace, rollback posture, receipt, and a
  FinalGate-certified terminal state.

The key is not to make the LLM weaker. The key is to make the LLM powerful in
the right role: intelligence and proposals, not authority and direct execution.

## Recommended Architecture Evolution

### Step 1 - Reconcile State

Update lock docs and README so they reflect:

- runtime model execution is wired;
- real Groq runtime path is validated;
- provider catalog exists;
- OpenAI-compatible base is hardened;
- action/mission token deferrals remain open.

### Step 2 - Close Budget Boundaries

Before deeper provider expansion or model role loops:

- implement per-action token spend tracking;
- implement mission-level token budget accumulation;
- surface budget exhaustion through BLOCKED/FinalGate-safe results;
- keep provider errors honest.

### Step 3 - Add Model Role Loops As Proposal-Only

Add:

- planner role
- critic role
- verifier role
- uncertainty report
- confidence calibration
- evidence challenge

No role can execute tools/organs or grant authority.

### Step 4 - Expand Providers With Catalog Discipline

Implement one provider pack at a time:

- DeepSeek or Mistral OpenAI-compatible first if catalog/base tests pass;
- native OpenAI Responses after state/budget rules;
- Anthropic/Gemini/Cohere later because native response/reasoning/tool semantics
  differ.

### Step 5 - Attach Model Planning To Organs Safely

Only after budget/state lock:

- browser planning proposals;
- API read proposals;
- channel draft proposals;
- desktop workspace proposals.

Every organ action remains authority-gated.

## What Must Not Start Yet

- Silent provider fallback.
- AUTO model routing.
- P6U API authenticated read implementation before state/budget closure.
- Brain/Science live model society before proposal-only role contracts.
- Tool/function calling from provider output.
- Browser login/session/form mutation outside locked authority.
- Channel send.
- Spend/trading/payment execution.
- Provider key management product without credential threat model.

## Code Blockers Behind The Gap

| Final-system capability | Current blocker | Why it matters |
| --- | --- | --- |
| Long autonomous missions | Runtime has model decision seam, but not persistent multi-step planner/critic/verifier loop | Without loop control, the LLM remains a one-shot decision engine. |
| Multi-model role specialization | Provider catalog is metadata-only; no role contract or model quality router | Sentinel cannot yet use cheap/strong/coding/vision/critic models deliberately. |
| User-approved tool execution | Model output cannot call tools, and organ proposal-to-approval path is not generalized | This is correct for safety, but means model plans cannot yet become controlled action broadly. |
| Full browser workflow automation | Browser layers block high-risk actions and do not have final product workflow integration | Browser power is guarded but not yet fully useful for real tasks. |
| Desktop assistant power | Desktop L6 is workspace file operations, not full desktop control | Safe, but not yet desktop awareness or control. |
| API assistant power | P6U authenticated read not started in this audit state | API read/write remains future authority surface. |
| Budget-complete model/tool runtime | Action and mission token-budget deferrals remain open | Large model loops cannot be safely scaled without budget authority. |
| Production provider reliability | No fallback policy, limited retry/rate-limit handling, diagnostics for some providers | Provider failure remains honest but not resilient. |
| Evidence-rich Brain | Receipts/events exist, but Brain does not yet deeply use evidence for self-correction loops | Final system needs evidence-driven learning without authority expansion. |
| State truth continuity | Lock docs are stale after runtime/provider progress | Future agents may act on old truth and redo/contradict work. |

## LLM Power Gap In Concrete Terms

Current LLM interaction:

```text
structured frame -> prompt -> provider -> JSON decision -> validation
```

Needed future interaction:

```text
mission understanding
-> planner model proposes strategy
-> critic model attacks assumptions
-> verifier model checks evidence
-> budget policy approves continued reasoning
-> authority layer decides which action proposals are allowed
-> organs execute only authorized actions
-> evidence/receipts feed back into next reasoning step
-> FinalGate certifies terminal state
```

The gap is not "can Sentinel call a model?" That is now proven. The gap is
"can Sentinel use model intelligence repeatedly, cheaply, and safely without
letting intelligence become authority?"

## What Must Be Built Before Full Power

1. State truth consolidation: update locks, README, implementation logs, and
   spec mirrors to reflect post-Wave-9 reality.
2. Budget closure: action and mission token budget deferrals must close before
   large iterative model loops.
3. Model role contracts: planner, critic, verifier, researcher, coder, and
   risk reviewer roles must be explicit and non-executing.
4. Debate/review loop: multi-step reasoning with evidence checks and stop
   conditions.
5. Organ proposal schema: model can propose an organ action, but execution
   requires authority, risk, receipt, and FinalGate checks.
6. Provider quality telemetry: track model reliability by mission class without
   storing raw prompts/responses.
7. Streaming/redaction policy: decide how streaming and reasoning fields are
   handled before production use.
8. UI/product flow: expose enough workflow power for a user to supervise long
   missions.
