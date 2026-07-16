# SENTINEL_BROWSER_ORGAN_MAX_POWER_COMPLETION_AND_UNIFICATION_AUDIT_V2

verdict = VALID_READ_ONLY_CURRENT_POWER_AND_UNIFICATION_AUDIT
date = 2026-07-16
scope = current Sentinel Browser Organ after recent commits
mode = read_only_code_verified_audit

This audit does not declare the Browser Organ complete. It records the current
power truth: what is product-routed, what exists but remains fragmented, what is
duplicated, and what must be reconnected before the Browser Organ can be called
finished.

## Doctrine

MODEL =
reasoning, semantic judgment, strategy, exploration, invention, and unexpected
safe trajectories.

SENTINEL =
digital browser body, senses, affordances, runtime, memory/state, mechanical
reflexes, evidence, and execution boundaries.

Authority remains a thin execution substrate. It is a pass/fail invariant for
real effects, not a browser-power score.

## Current Git Truth

branch = experimental/real-model-lab-freeze-v1

HEAD = f5c1e249dd6579a35bc250c226067707224d1c12

ahead_behind = ahead 45 from origin/experimental/real-model-lab-freeze-v1

tracked_worktree_state = clean

untracked_state = sentinel-control/services/sentinel-core/tmp/

The untracked tmp directory was observed only and was not modified.

Recent browser-related commits included in the current tree include:

- f5c1e24 docs: add browser organ comparative anatomy audit
- 42843c8 fix: harden product replay and cleanup evidence
- 1252991 docs: record browser body outage model feedback fix
- bbb0e9b fix: surface browser body outage to model
- 87d9759 fix: surface browser runtime failures to model
- ee31299 fix: prove browser search write readback materiality
- e350f79 fix: route generic browser evidence extraction
- 11407e4 fix: bound browser extract loop context transport
- f79ffef fix: preserve browser action start failure facts
- dd273b7 fix: govern browser search by typed effect boundary
- 860a6bd fix: type model-native browser search parameters
- 22f8caf fix: stabilize real browser body lifecycle
- fe91223 docs: record browser cortex non-holdout calibration
- 20f0bae test: add browser cortex pack1b generalization corpus
- f6d6885 feat: upgrade browser cortex search entity quality
- 16facc2 feat: add browser cortex environment state materiality

## Inputs Reconciled

The following prior truth artifacts were read as context and then checked
against current source instead of trusted blindly:

- Cognitive OS North Star
- Model Amplification Not Model Replacement Doctrine
- Browser Cortex deep anatomy audit
- Pack 0 executable truth reconciliation
- product cutover registry
- Python.org V3-V6 reports and repeated reliability report
- comparative Agent Labs browser audit
- current browser source and tests

Important reconciliation result:

The previous comparative audit correctly identified receipt/answer evidence as
a major next gap. Current source also shows larger unification gaps: rich
DevTools, AX, visual, trajectory, multi-step, special authority, neural/cortex,
and legacy browser stacks exist but are not fully consumed by the canonical
product BrowserEnvironmentState/ProductActionKernel path.

## Fresh Current Census

Browser-related files by major tree:

| Tree | Browser-related file count |
| --- | ---: |
| sentinel/operator | 128 |
| sentinel/organs/browser | 44 |
| sentinel/agent/organs | 38 |
| sentinel/agent/browser | 51 |
| tests | 321 |
| sentinel-audit/deep-code-audit | 4 |
| agent-lab/module-harvest/browser | 27 |

Current surface counts derived from source census:

| Surface | Fresh count / truth |
| --- | --- |
| canonical product browser runtime paths | 1 primary path through RuntimeHost/ProductActionKernel/RealBrowserControlRuntime |
| alternative browser execution graphs still present | at least 7 families |
| model-facing browser skill surfaces | search, inspect_result, open_result, extract_evidence, extract_product_cards, verify_extraction, finish |
| internal raw primitives still implemented | click, type_text, select_option, assert_text, extract_text, press_key, wait_for_text, wait_for_load, scroll |
| state contracts in product context | BrowserEnvironmentState, BrowserWorldModel, BrowserDecisionFrame, grounded_evidence_summary, runtime_failure_fact |
| receipt/finalgate families | product task loop, real browser runtime, browser session manager, legacy browser V3 models, many organ-local FinalGates |
| test/benchmark surfaces | deterministic corpora, operator tests, browser organ unit tests, gauntlets, fake eval, real mission reports |
| high-value dormant or partial organs | DevTools machine intelligence, trajectory planner, multi-step orchestrator, neural/cortex stack, visual grounding, special-effect browser capabilities |

## Current Canonical Product Graph

The currently proven product browser spine is:

```text
real provider/model
-> ProductModelNativeDecisionClient
-> ActionEnvelope internal action
-> ModelLedProductActionKernelTaskLoop
-> RuntimeHost / ProductActionKernelDispatchAdapter
-> RealBrowserControlRuntime
-> BrowserSessionManagerL5Live
-> CloakBrowserSessionBackend
-> BrowserEnvironmentState / BrowserWorldModel / BrowserDecisionFrame
-> browser action receipt
-> ProductActionKernel receipt
-> task-loop FinalGate certificate
-> replay
-> cleanup
```

Current source evidence:

- `sentinel/operator/product_model_native_decision_client.py:153` maps raw model output into an internal action.
- `sentinel/operator/product_model_native_decision_client.py:184` performs browser-native mapping.
- `sentinel/operator/product_model_native_decision_client.py:633` maps simple skills to internal actions.
- `sentinel/operator/model_led_product_action_kernel_task_loop.py:106` defines the model-led product task loop.
- `sentinel/operator/model_led_product_action_kernel_task_loop.py:239` compiles the product loop context.
- `sentinel/operator/model_led_product_action_kernel_task_loop.py:565` dispatches product actions.
- `sentinel/operator/model_led_product_action_kernel_task_loop.py:1166` builds a browser cognitive decision frame from current context.
- `sentinel/operator/runtime_host.py:419` routes `real_browser.search`.
- `sentinel/operator/runtime_host.py:429` routes `real_browser.extract_evidence`.
- `sentinel/operator/runtime_host.py:439` routes `real_browser.extract_product_cards`.
- `sentinel/operator/runtime_host.py:449` routes `real_browser.verify_extraction`.
- `sentinel/operator/runtime_host.py:459` routes `real_browser.inspect_result`.
- `sentinel/operator/runtime_host.py:469` routes `real_browser.open_result`.
- `sentinel/operator/runtime_host.py:982` creates the `RealBrowserControlRuntime`.
- `sentinel/operator/real_browser_control_runtime.py:649` defines the real browser runtime.
- `sentinel/operator/real_browser_control_runtime.py:825` implements search.
- `sentinel/operator/real_browser_control_runtime.py:1235` implements generic evidence extraction.
- `sentinel/operator/real_browser_control_runtime.py:1281` implements verification.
- `sentinel/agent/organs/browser_session_manager_l5_live.py:357` defines the live L5 session manager and names CloakBrowser as primary.
- `sentinel/organs/browser/cloak_backend.py:52` defines the CloakBrowser session backend.
- `sentinel/operator/browser_environment_state.py:78` defines BrowserEnvironmentState.
- `sentinel/operator/browser_world_model.py:78` defines BrowserWorldModel.
- `sentinel/operator/browser_search_outcomes.py` defines typed search materiality.
- `sentinel/operator/browser_product_cutover_registry.py:143` marks RealBrowserControlRuntime as product owner.
- `sentinel/operator/browser_product_cutover_registry.py:156` marks BrowserSessionManagerL5Live as product/session owner.
- `sentinel/operator/browser_product_cutover_registry.py:166` marks CloakBrowser as the live session backend.
- `sentinel/operator/browser_product_cutover_registry.py:216` through `:222` quarantine Playwright as compatibility/test only.

## Alternative Browser Execution Graphs Still Present

1. Legacy fixture/runtime graph:

```text
BrowserControlRuntime
-> fixture elements
-> click/type/select/assert artifacts
```

Evidence: `sentinel/operator/browser_control_runtime.py:63` defines
`BrowserControlRuntime`, with primitive handlers at `:113`, `:149`, `:172`,
`:198`, and `:220`.

Disposition: HIDE / DELETE_AFTER_PARITY.

2. Agent organ session graph:

```text
AgentRuntime or organ caller
-> BrowserSessionManagerL5Live
-> organ-local receipt/finalgate
```

Evidence: `sentinel/agent/organs/browser_session_manager_l5_live.py:385`,
`:433`, `:465`, and `:550` expose session operations directly.

Disposition: KEEP as hidden backend; prevent product bypass.

3. Organs/browser V3 graph:

```text
sentinel/organs/browser/*
-> controlled runner / lifecycle / interaction execution
-> BrowserV3Receipt families
```

Evidence: `sentinel/organs/browser/models.py` defines many browser models and
receipts; `sentinel/organs/browser/controlled_runner.py` exposes broad
controlled capabilities.

Disposition: RECONNECT valuable perception/action models into the canonical
state and runtime; delete or hide only after parity.

4. Agent/browser cortex graph:

```text
Agent events
-> BrowserEvidenceInterpreter
-> evidence chain / recommendations
```

Evidence: `sentinel/agent/browser/cortex.py:130` defines
`BrowserEvidenceInterpreter`, with recommendations at `:413`.

Disposition: RECONNECT as evidence interpreter; do not let it become a closed
planner.

5. DevTools machine intelligence graph:

```text
BrowserDevToolsMachineIntelligenceOrgan
-> AX/network/console/screenshot evidence bundle
-> organ-local receipt/finalgate
```

Evidence: `sentinel/agent/organs/browser_devtools_machine_intelligence_v1.py`
defines AX refs, network ledger, console ledger, screenshot evidence, receipt,
and FinalGate.

Disposition: RECONNECT sensory output into BrowserEnvironmentState.

6. Trajectory/multi-step graph:

```text
BrowserTrajectoryPlannerL5 / BrowserMultiStepTaskOrchestratorV1
-> organ-local plan / fake backend / receipts
```

Evidence: `sentinel/agent/organs/browser_trajectory_planner_l5.py:185` and
tests for `BrowserMultiStepTaskOrchestratorV1`.

Disposition: RECONNECT as hidden mechanical reflexes and long-horizon planner
support, not as model-strategy replacement.

7. Special-effect graph:

```text
login / private session / cookie storage / JS evaluate / upload / download /
form submit / payment / account creation
-> special authority organs
```

Evidence exists in `sentinel/organs/browser/v3_advanced_authorities.py` and
`sentinel/agent/organs/browser_*` special authority files.

Disposition: KEEP locked as special-effect capabilities; product-route later
through explicit authority/sandbox/SecretBroker, not as permanent prohibitions.

## Component Disposition Summary

The full machine-readable census is in
`SENTINEL_BROWSER_ORGAN_CURRENT_EXECUTABLE_CENSUS_V2.csv`.

High-signal current truth:

| Component family | Reachability | Recommendation |
| --- | --- | --- |
| Product model-native decision path | CANONICAL_PRODUCT_REACHED | KEEP |
| RuntimeHost browser routes | CANONICAL_PRODUCT_REACHED | KEEP |
| RealBrowserControlRuntime | CANONICAL_PRODUCT_REACHED | KEEP |
| BrowserSessionManagerL5Live | HIDDEN_BACKEND_REACHED | KEEP / HIDE direct product bypass |
| CloakBrowserSessionBackend | HIDDEN_BACKEND_REACHED | KEEP |
| BrowserEnvironmentState | PARTIALLY_CONSUMED | MAKE canonical state aggregator |
| BrowserWorldModel | PARTIALLY_CONSUMED | MERGE under BrowserEnvironmentState as semantic graph |
| BrowserDecisionFrame | PARTIALLY_CONSUMED | KEEP as view over canonical state, not separate truth |
| DevTools machine intelligence | VALUABLE_DORMANT / PARTIALLY_CONSUMED metadata only | RECONNECT sensory bundle |
| Trajectory planner | VALUABLE_DORMANT | RECONNECT as hidden reflex/planner support |
| Multi-step orchestrator | VALUABLE_DORMANT | RECONNECT after state unification |
| Agent/browser cortex/neural | VALUABLE_DORMANT / PARALLEL_ACTIVE | RECONNECT as advisory evidence, not controller |
| Playwright engine/session backends | LEGACY_COMPATIBILITY | DELETE_AFTER_PARITY |
| BrowserControlRuntime fixture path | LEGACY_COMPATIBILITY | HIDE / DELETE_AFTER_PARITY |
| Special-effect organs | SPECIAL_EFFECT_CAPABILITY | KEEP locked; route later through explicit grants |
| Receipt/finalgate families | DUPLICATE_CONTRACT | INDEX first, merge later |

## Specific Questions Answered

### 1. Is BrowserEnvironmentState truly the single canonical cognitive browser state?

No. It is named as the canonical state source in the product context, but it is
not yet the only state contract.

Evidence:

- Product loop labels it canonical at `model_led_product_action_kernel_task_loop.py:1200`.
- Product context still carries `browser_world_model`, `browser_world_model_summary`,
  `browser_decision_frame`, `browser_observation_bundle`, and
  `browser_search_materiality` separately at `model_led_product_action_kernel_task_loop.py:315-324`.
- BrowserEnvironmentState currently includes safe protocol and storage metadata
  fields, but `tab_count` and `frame_count` are fixed to 1 in
  `browser_environment_state.py:320`.

Conclusion: BrowserEnvironmentState is the right center, but it is not yet the
whole cortex.

### 2. Is the current product model context the only real decision context?

No. The product context is primary, but legacy and compatibility contexts still
influence decisions.

Evidence:

- Product context includes `model_visible_skills` and `skill_decision_frame`.
- The product loop still exposes legacy browser fields alongside the state at
  `model_led_product_action_kernel_task_loop.py:315-324`.
- `product_model_native_decision_client.py:263` still checks
  `real_browser_control_summary` or `browser_world_model` to decide browser
  mapping.

Conclusion: The model-facing surface is much cleaner, but BrowserEnvironmentState
has not fully displaced legacy context.

### 3. How much of BrowserDevToolsMachineIntelligence is really consumed?

Only partial safe metadata is consumed by the product path. Full sensor power is
not yet product-canonical.

Evidence:

- DevTools machine intelligence defines AX refs, network ledger, console ledger,
  screenshot evidence, evidence bundle, receipt and FinalGate.
- RealBrowserControlRuntime sanitizes safe DevTools metadata at
  `real_browser_control_runtime.py:2818` and combines metadata at `:2869`.
- BrowserEnvironmentState accepts network, console, and storage metadata but not
  the full DevTools evidence bundle.

Conclusion: Reconnect, do not rebuild.

### 4. Is BrowserFailureRecoveryEngine a real mechanical recovery executor?

Not in the product spine. The current product runtime implements mechanical
search/ref recovery locally, while the failure recovery organ is mostly an
evidence/advisory planner with its own receipts.

Evidence:

- RealBrowserControlRuntime has local search recovery helpers at
  `real_browser_control_runtime.py:3148`, `:3153`, `:3353`, and failure packets
  at `:3409` and `:3441`.
- BrowserFailureRecoveryEngine has separate plans/receipts/finalgate in
  `sentinel/agent/organs/browser_failure_recovery_engine_v1.py`.

Conclusion: Merge concepts into hidden body reflexes; do not expose as model
strategy controller.

### 5. Are BrowserTrajectoryPlanner and MultiStepTaskOrchestrator consumed?

No product consumption was found. They are importable, tested, and CLI/demo
reachable, but not canonical product-routed.

Evidence:

- CLI imports and demo routes exist for trajectory planning.
- Tests instantiate these organs directly with fake backends.
- RuntimeHost product browser route does not dispatch through them.

Conclusion: valuable dormant power.

### 6. What remains under browser_control_runtime.py versus real_browser_control_runtime.py?

`browser_control_runtime.py` remains a fixture/legacy primitive runtime.
`real_browser_control_runtime.py` is the product live browser runtime.

Disposition:

- Keep fixture runtime for tests only.
- Do not count it as product browser power.
- Delete only after full parity coverage exists elsewhere.

### 7. What remains inside sentinel/agent/browser cortex/neural/benchmark stacks?

There is a large advisory/cognitive/eval stack:

- `BrowserEvidenceInterpreter`
- neural signal graph / blackboard / neurons
- fake eval / gauntlet / benchmark machinery
- evidence chain and recommendation models

These are not the product browser cortex yet. They are candidates to become
hidden evidence producers and evaluation layers.

### 8. Are organ browser dispatcher paths still independently executable?

Yes. Many browser organs expose `execute`, `run`, direct managers, or fake
backends. Some are direct-test or CLI reachable. They should not be deleted
blindly because they contain real power, but they should not remain separate
product paths.

### 9. Is Playwright compatibility still necessary?

Yes, as compatibility/test coverage only. Exact parity missing before removal:

- complete Cloak parity for every direct Playwright fixture/test route;
- robust visual screenshot/renderer parity;
- broad form/download/upload/login test coverage under Cloak/session;
- multi-tab/frame/Shadow DOM parity;
- stable local body canaries across multiple public sites.

Current source already enforces Playwright compatibility as non-product:
`browser_product_cutover_registry.py:216-222` and
`real_browser_control_runtime.py:2972-3007`.

### 10. Which CDP/BiDi/AX/DOM/network/console/visual/tab capabilities exist but are not exposed canonically?

Existing but not fully canonical:

- AX: `sentinel/organs/browser/cdp_ax.py`, accessibility snapshots, DevTools AX refs.
- DOM: `sentinel/organs/browser/dom_snapshot.py`.
- Network/console: Cloak backend metadata listeners and DevTools ledgers.
- Visual: screenshot/visual grounding/ui observation/rendered snapshot modules.
- Tabs/windows: public lifecycle, advanced pool, multitab operator.
- CDP: DevTools adapter/native CDP backend.
- BiDi: no product-reachable BiDi capability found in current source census.

### 11. Are generic browser capabilities still commerce-shaped internally?

Partially. Generic evidence extraction exists and documentation signals exist,
but the world model still carries product/card compatibility:

- `ProductCandidateCard` and `BrowserSearchResultCard` coexist.
- `_open_world_card_from_text` exists.
- `extract_product_cards` remains a compatibility specialization.
- `BrowserEnvironmentState` and model context still use card/product counts in
  completion and routing helpers.

Conclusion: generic evidence is in place, but commerce-shaped residue remains.

### 12. Can the model freely navigate, follow links, inspect, change strategy, handle pages and recover?

Partially. The product spine now supports search, inspect, open result, extract,
verify and finish. The Python.org success proves safe alternate completion was
possible after earlier failures. However, the proven surface remains much closer
to:

```text
search -> extract evidence -> verify -> finish
```

than a fully open browser organism with multi-tab/multi-page exploration and
long-horizon recovery.

### 13. Which login/form/upload/download/session/JS capabilities are real powers but not product-routed?

Real source exists for:

- login/session/private session/cookie storage/JS/Har body capture;
- upload/download quarantine;
- form submit;
- account creation;
- payment/spend;
- extension/WebMCP bridge.

They are special-effect powers and must remain locked until explicitly
authority-routed. They are not permanent prohibitions.

### 14. Are receipts and FinalGates unified?

No. Product receipts and task-loop certificates exist, but receipt ownership is
fragmented.

Evidence:

- Real browser runtime writes real-browser artifacts.
- BrowserSessionManagerL5Live writes session receipts.
- ProductActionKernel/task loop writes product receipts/certificates.
- Many organ-local FinalGates exist.
- The repeated reliability report recorded
  `browser_receipt_readable_count = 0` and `browser_receipt_missing_count = 15`.

Conclusion: the 0/15 readable receipt failure is proof-index fragmentation, not
search actuation failure.

### 15. Does the final answer/evidence gap require a new component?

It should primarily be solved by indexing and cross-linking existing canonical
receipts first. A small claim-candidate component may be needed, but it must not
be a final semantic judge. It should create:

```text
claim candidate -> evidence ref -> support / contradiction / unknown
```

from existing product/browser/session receipts and safe answer text.

## Unified Versus Fragmented Truth

Unified today:

- one product RuntimeHost/ProductActionKernel route for real browser skills;
- model-native browser skill mapping;
- Cloak-first backend selection and explicit Playwright compatibility boundary;
- typed search materiality;
- generic evidence extraction;
- body failure facts and model-visible failure packets;
- replay no-react and cleanup proven on Python.org.

Fragmented today:

- BrowserEnvironmentState is not the only cognitive state;
- BrowserWorldModel and BrowserDecisionFrame remain separate truth carriers;
- DevTools/AX/DOM/network/visual/tabs sensors are not fully fused into the state;
- trajectory/multi-step/recovery organs are not product-routed;
- special-effect browser powers are separate and not promoted;
- answer claims are not yet independently tied to browser receipts;
- multiple FinalGate/receipt families remain.

## Dormant Power Inventory

High-value dormant or partially consumed power:

1. DevTools machine intelligence: AX refs, network, console, screenshot evidence.
2. DOM/AX snapshots from `sentinel/organs/browser`.
3. Visual grounding / UI observation / rendered snapshots.
4. Multitab/public lifecycle/advanced pool.
5. BrowserTrajectoryPlannerL5.
6. BrowserMultiStepTaskOrchestratorV1.
7. BrowserFailureRecoveryEngineV1.
8. Agent browser cortex and neural stack.
9. Browser benchmark gauntlet and fake eval.
10. Special effect capabilities: form, login, upload/download, JS, private
    session, cookie storage, payment, account creation.

## Missing Power Inventory

Important missing or not-proven power:

1. Full sensory fusion into one BrowserEnvironmentState.
2. Product-reachable tabs/windows and frame/iframe/Shadow DOM state.
3. Product-reachable visual grounding.
4. Product-reachable network/request understanding beyond safe summaries.
5. Product-reachable console/runtime error understanding.
6. Multi-page and long-horizon research planning.
7. Mechanical recovery executor unified across search, navigate, stale refs,
   overlays, dynamic pages and session replacement.
8. Evidence extraction that handles arbitrary entity kinds at T3/T4.
9. Claim-to-evidence matrix and independently readable browser receipt index.
10. Multi-site real-model calibration and frozen holdout generalization.
11. Governed code-as-browser-skill sandbox / SkillCandidate path.
12. Special-effect capability promotion path for ordinary actions like login,
    download, upload and form submit.

## Power Capability Matrix Summary

The complete machine-readable matrix is in
`SENTINEL_BROWSER_ORGAN_POWER_CAPABILITY_REACHABILITY_MATRIX_V2.csv`.

Key tiers:

- T3 proven: Python.org product spine, real Cloak search materiality, generic
  extraction/verification/final answer closeout, replay and cleanup.
- T3 repeated: 5/5 technical Python.org closeout, but answer quality failed due
  to missing preserved claim/receipt evidence.
- Not proven: multi-site generalization, holdout, long-horizon browser missions,
  full sensory fusion, multi-tab/frame/Shadow DOM, special-effect capabilities.

## Final Browser Organ Target

### A. Model-facing high-level affordances

The final model-facing surface should remain open and strategy-free:

- observe
- navigate
- search
- interact
- follow/open
- inspect
- extract_evidence
- verify
- manage_tabs/context
- propose_browser_skill_candidate
- finish
- declare_blocker

The model should never be forced into one exact sequence.

### B. Hidden mechanical reflexes

Hidden body reflexes should include:

- stale-ref refresh;
- hidden/disabled/detached element recovery;
- focus/clear/write/readback;
- submit mechanism selection;
- overlay/modal handling;
- session reopen under typed recovery;
- pagination/infinite-scroll exploration;
- bounded alternate ref/control selection;
- materiality observation;
- cleanup/replay safety.

### C. Hidden perception organs

The final BrowserEnvironmentState should fuse:

- Cloak/session state;
- DOM and Shadow DOM summaries;
- AX/accessibility tree;
- CDP/BiDi where available;
- network/request metadata;
- console/runtime errors;
- tabs/windows/frames;
- visual grounding;
- structured data;
- storage/session metadata without values;
- entity/evidence graph;
- uncertainty, contradictions and recovery affordances.

### D. Evidence/state contracts

One canonical state and proof contract:

```text
BrowserEnvironmentState
-> evidence/entity graph
-> material action receipt
-> browser/session receipt index
-> answer claim evidence cards
-> FinalGate
-> replay verifier
```

### E. Special-effect capabilities

These should be real browser powers, not forever-banned words:

- login/session;
- form submit;
- upload/download;
- messaging/contact;
- payment/spend;
- private browsing/profile/cookie storage;
- JS/evaluate.

They must route through explicit capability grants, SecretBroker/sandbox,
preview/confirmation where appropriate, receipts, replay and revocation.

### F. Compatibility paths to remove

Remove only after parity:

- Playwright product-like paths;
- fixture BrowserControlRuntime as product proof;
- direct organ execution bypasses;
- duplicate BrowserWorldModel/DecisionFrame truth if fully folded into
  BrowserEnvironmentState;
- old receipt/finalgate files after an index proves full parity.

## Browser Organ Completion Gate

The Browser Organ is not finished until all of the following are true:

1. Every high-value existing browser organ is product-consumed, intentionally
   hidden, deferred with reason, or removed after parity.
2. There is exactly one canonical product execution path for model-facing
   browser skills.
3. No valuable dormant organ remains silently outside the spine.
4. No permanent parallel browser runtime exists except explicit compatibility
   paths.
5. BrowserEnvironmentState fuses DOM, AX, network, console, visual, tabs,
   frames and storage/session metadata safely.
6. The model can choose strategies beyond search/extract/verify/finish.
7. Mechanical recovery handles stale/dynamic/session failures without becoming
   a closed cognitive planner.
8. Multi-tab and multi-page operation are product-routed.
9. Long-horizon missions are evaluated with action efficiency and cost.
10. Final answers carry a claim-to-evidence matrix and unsupported claim count.
11. Browser receipts are independently readable from exported proof.
12. Replay verifies no reopen/research/reextract/rewrite.
13. Cleanup proves no remaining live context/profile material.
14. Real-model multi-site non-holdout thresholds pass.
15. Frozen holdout remains locked until the non-holdout gate passes.

Python.org alone cannot complete this gate.

## Prioritized Reconnection Sequence

### RECONNECT_EXISTING_POWER

1. Index existing product/browser/session receipts and answer claims.
2. Fuse DevTools/AX/DOM/network/console/visual metadata into
   BrowserEnvironmentState.
3. Fold BrowserWorldModel and BrowserDecisionFrame into state views.
4. Connect BrowserFailureRecoveryEngine concepts to hidden body reflexes.
5. Connect trajectory and multi-step organs as optional hidden helpers.

### UNIFY_DUPLICATED_POWER

1. Consolidate receipt/finalgate ownership.
2. Collapse agent/browser cortex evidence chain into the product evidence graph.
3. Merge organ/browser V3 models with product BrowserEnvironmentState contracts.
4. Remove duplicate recommendation paths that compete with model freedom.

### BUILD_MISSING_POWER

1. Multi-tab/frame/Shadow DOM product state.
2. Visual grounding product path.
3. Network/console/runtime product summaries.
4. Open-world entity graph beyond commerce/documentation.
5. Governed browser SkillCandidate sandbox.

### PROVE_LIVE_POWER

1. Re-run Python.org after receipt/answer evidence capture.
2. Run multi-site non-holdout calibration.
3. Prove navigation/follow/inspect alternate strategies.
4. Prove multi-page/tabs and dynamic page recovery.
5. Only then unlock frozen holdout.

### DELETE_AFTER_PARITY

1. Playwright compatibility paths.
2. fixture BrowserControlRuntime product-like paths.
3. direct organ demo/CLI routes if equivalent product route exists.
4. stale docs/registries that present registration as product consumption.

## Is Receipt/Answer Evidence Truly Next?

Yes, but only as the first reconnection step, not as the whole Browser Organ
finish.

Reason:

- Repeated Python.org runs show 5/5 technical closeout, search materiality,
  replay and cleanup.
- The failure is independent auditability: browser receipt paths are referenced
  but not readable in the committed safe artifact bundle, and final answer
  claims are not preserved with claim-to-evidence cards.
- Fixing this unlocks truthful measurement of broader browser power. Without
  it, multi-site calibration can run but cannot prove answer quality.

The correct next tranche is:

```text
FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1
```

but scoped as a reconnection/indexing pack:

```text
existing receipts -> canonical safe browser receipt index
sanitized answer claims -> claim-to-evidence matrix
FinalGate -> unsupported claim enforcement
replay -> no new browser receipts / no answer mutation
```

It must not create another isolated receipt system.

## Do Not Touch Yet

- Do not delete Playwright paths until Cloak parity is broader.
- Do not promote login/download/upload/payment/form submit without explicit
  authority/sandbox/SecretBroker design.
- Do not consume frozen holdout.
- Do not run multi-site calibration until receipt/answer evidence can be
  audited.
- Do not replace the model with trajectory planner rules.
- Do not create another browser stack.
- Do not treat BrowserEnvironmentState as fully complete before sensor fusion.
- Do not migrate language/runtime for browser organ while product power gaps
  remain in Python.

## Other Sentinel Organs Appendix

Broad maturity only, not a deep audit:

| Organ family | Broad current maturity |
| --- | --- |
| workspace/files | product-routed and more mature than browser for bounded local effects |
| code/shell | product-routed for bounded run/check workflows; needs long-horizon studio evolution |
| desktop/computer | vision locked but not yet Browser-level product maturity |
| channels | bounded fake/local and some real transport proofs; external sends remain tightly scoped |
| credentials/account | future governed capability via SecretBroker/account grants |
| workers/memory/workflows | product-spine local/fake proof exists; real long-horizon maturity pending |
| voice | outside current browser audit; future cortex organ |
| electronics/IoT | vision-level future organ; not current product runtime |

## Final Verdict

```text
SENTINEL_BROWSER_ORGAN_MAX_POWER_COMPLETION_AND_UNIFICATION_AUDIT_V2
= VALID_READ_ONLY_CURRENT_POWER_AND_UNIFICATION_AUDIT

browser_product_spine = REAL_AND_T3_PROVEN_FOR_PYTHON_ORG_VERTICAL
browser_organ_finished = NO
largest_connected_power = real model + real Cloak + product search/extract/verify/finish + replay/cleanup
largest_fragmented_power = DevTools/AX/DOM/network/visual/trajectory/multi-step/special-effect organs
next_correct_tranche = FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1
next_tranche_kind = RECONNECT_EXISTING_POWER
```
