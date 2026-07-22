# Sentinel Browser Product Wiring Re-Audit After Real Model V8 V1

## Verdict

```text
SENTINEL_BROWSER_PRODUCT_WIRING_REAUDIT_AFTER_REAL_MODEL_V8_V1
= VALID_READ_ONLY_PRODUCT_WIRING_REAUDIT_AFTER_REAL_MODEL_EVIDENCE
```

This is an audit verdict, not a Browser Organ capability success claim.

## Current Code Truth

```text
branch = experimental/real-model-lab-freeze-v1
implementation_commit = 821c2b4 fix: prevent partial browser evidence finish loops
real_proof_tranche = BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_REAL_NON_HOLDOUT_PROOF_V8
provider/model = aliyun_dashscope / deepseek-v4-pro
browser_backend = cloak_browser
fixture_backend = false
playwright_fallback = false
holdout_used = false
```

## V8 Real-Model Evidence

```text
attempted_missions = 6
provider_action_decisions = 48
proof_infrastructure_gate_passed = true
safe_bundle_created = 6/6
readable_proof_index = 6/6
material_receipt_missing_count_total = 0
replay_no_react = 6/6
cleanup_success = 6/6

technical_completion = 0/6
useful_answer_completion = 0/6
answer_claim_count = 0
sourced_factual_claim_count = 0
supported_factual_claim_count = 0
unsupported_factual_claim_count = 0
repeated_identical_action_without_new_evidence_count = 10
```

Honest interpretation:

```text
proof infrastructure = PROVEN on this non-holdout batch
false partial-evidence finish = CUT
browser product quality = FAILED
multi-site generalization = NOT PROVEN
answer quality = NOT PROVEN
```

## Wiring That Is Now Working

The real product route is reachable:

```text
real provider/model
-> ProductModelNativeDecisionClient
-> ModelLedProductActionKernelTaskLoop
-> RuntimeHost
-> ProductActionKernel
-> RealBrowserControlRuntime
-> BrowserSessionManager / Cloak
-> receipts
-> BrowserProofIndex
-> replay / cleanup
```

The recent fix corrected a real control-flow defect:

```text
before:
partial grounded evidence + natural "finish/summary" intent
-> browser-native mapper
-> sentinel_loop.finish
-> FINAL_ANSWER_PAYLOAD_INCOMPLETE loop

after:
partial grounded evidence + natural "finish/summary" intent
-> live browser recommendation / safe browser action
-> no fabricated final answer
```

Terminal finish is now allowed only for:

```text
grounded terminal answer support
or grounded terminal blocker support
or objective-aware confirmed negative product relevance when the mission is actually product/price/catalog oriented
```

## Fresh Power Gaps Exposed By V8

### P0. Model-Facing Browser Surface Is Still Too Collapsed

Current simple model surface maps:

```text
real_browser.search
real_browser.inspect_result
real_browser.open_result
-> browse_search
```

That preserves simplicity, but the runtime action map can collapse the next safe browser move back into `real_browser.search`. V8 shows repeated search after partial evidence instead of richer navigation/follow/inspect strategies.

Decision:

```text
RECONNECT_EXISTING_POWER
```

Needed direction:

```text
model-facing browser skills should split into:
observe
navigate
search
follow/open
inspect
extract_evidence
verify_evidence
finish/declarer_blocker
```

Still hide selectors, CDP commands, DOM refs and backend internals.

### P0. Session Continuity Still Fails During Multi-Step Recovery

V8 contains repeated safe body failures:

```text
BODY_SESSION_UNAVAILABLE
real_browser_search_session_open_failed
failure_stage = session_lifecycle
```

Cloak preflight passes, selected and actual backend match, and cleanup succeeds. The failure appears after the mission is already active, during repeated child browser actions.

Decision:

```text
RECONNECT_EXISTING_POWER
```

Needed direction:

```text
root BrowserSessionLease must remain the live execution body across observe/search/extract/verify/recovery
child receipt/session refs must not imply session replacement
body recovery should reopen only through typed root recovery, not by drifting into unavailable child state
```

### P0. BrowserEnvironmentState Is Present But Not Yet Strong Enough

V8 reports useful public evidence counts, entity counts and page classifications, but search-control discovery fails on non-search pages and the model lacks enough semantic state to complete objective answers.

Examples:

```text
real_browser_search_control_not_found
page_kind_guess = documentation_or_article
candidate_entity_kind_counts includes documentation/api symbols
search_like_refs = []
```

Decision:

```text
BUILD_MISSING_POWER + RECONNECT_EXISTING_POWER
```

Needed direction:

```text
BrowserEnvironmentState must fuse DOM, AX, DevTools/CDP/BiDi, network, console, frames/tabs and visual structure into one canonical state.
It must expose page-specific affordances such as follow official link, inspect section, extract selected documentation region, use site nav, or declare search control absent.
```

### P1. Body Failure Packets Exist But Cognitive Diagnosis Is Weak

V8 records:

```text
runtime_failure_fact_seen = true
browser_failure_packet_seen = true
model_diagnostics_count > 0
model_operational_assessment = null in provider-decision evidence events
```

Sentinel is giving the body facts, but the loop does not yet reliably capture a structured model assessment of the blocker.

Decision:

```text
UNIFY_DUPLICATED_POWER
```

Needed direction:

```text
next normal model turn should receive body packet and produce compact operational assessment
assessment remains advisory
receipts remain authoritative
no private reasoning persisted
```

### P1. Proof Index Is Readable But Not Sufficient For Useful Answers

V8 proof infrastructure succeeds, yet:

```text
answer_claim_count = 0
final_answer_present = false
useful_answer_completion = 0/6
```

This is not a proof persistence problem anymore. It is an evidence-to-answer and affordance/state problem.

Decision:

```text
BUILD_MISSING_POWER
```

Needed direction:

```text
answer generation must be grounded in BrowserProofIndex public evidence cards
the model must receive enough human-readable public evidence to answer
claim cards must be created only from supported evidence
```

### P1. Repetition Guard Is Still Too Weak

V8 reduced the old finish repetition but still records:

```text
repeated_identical_action_without_new_evidence_count = 10
```

Decision:

```text
RECONNECT_EXISTING_POWER
```

Needed direction:

```text
same action + same state hash + no new evidence
-> demote that action
-> expose changed assumption requirement
-> recommend alternate affordance
-> block honestly only after alternate paths exhausted
```

## Current Browser Product Power Truth

```text
real provider path = reached
real Cloak backend = reached
proof index = reached and readable
replay no-react = reached
cleanup = reached
search material receipts = exists
generic extraction = exists
verified extraction = exists
partial-evidence false finish = fixed
multi-site useful browser answering = not proven
canonical full sensor fusion = not yet implemented
model-facing browser affordance freedom = too narrow
root live session continuity during recovery = still fragile
```

## Correct Next Tranche

Do not start a pure answer-claim fix first. V8 shows the model often cannot reach or identify the right evidence path.

Proceed with:

```text
BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1
```

Purpose:

```text
Make the model see one coherent browser world state with richer safe affordances,
and make the root live browser body stable across recovery.
```

Required implementation themes:

```text
1. Split model-facing browser affordances beyond browse_search while keeping internals hidden.
2. Route search/inspect/open/follow/extract through the same ProductActionKernel path.
3. Preserve root BrowserSessionLease identity across repeated child browser actions.
4. Turn BODY_SESSION_UNAVAILABLE into typed root recovery before budget exhaustion.
5. Fuse existing BrowserEnvironmentState with stronger DOM/AX/DevTools/network/page affordance evidence.
6. Add repetition guard based on action + state hash + evidence delta.
7. Let the model choose safe alternate strategies; do not force exact trajectories.
```

Acceptance must include:

```text
T1 local regression for partial finish reroute
T1 local regression for collapsed browse_search no longer forcing search when inspect/open/follow is recommended
T1 local regression for repeated same action/state demotion
T2 live Cloak body session continuity proof
T3 real-model non-holdout batch with at least one useful grounded answer
```

## Do Not Touch Yet

```text
frozen holdout
Playwright fallback
provider-native tools
raw DOM/cookies/session/profile persistence
login/payment/contact/upload/download promotion
Computer Cortex
Mission Studio
Self-Thinking
global scanner/security rewrite
```

## Short Conclusion

Sentinel is no longer failing because it cannot call the model or run Cloak. It is failing because the browser body still compresses too much of the browser into `browse_search`, loses session continuity during recovery, and does not expose enough canonical evidence/affordances for the model to satisfy open-world documentation tasks.

The shortest honest path to maximum browser power is now:

```text
canonical browser state + richer safe affordances + stable root session recovery
then repeat the real non-holdout proof batch
then only after that improve claim synthesis and answer polish
```
