# SENTINEL_BROWSER_ORGAN_COMPARATIVE_EXECUTABLE_ANATOMY_AND_POWER_GAP_AUDIT_V1

Status: `READ_ONLY_AUDIT_COMPLETED`

Date: 2026-07-16

Scope: current Sentinel Browser Organ product path, Agent Lab browser/agent systems, exact local OpenClaw and Jarvis projects, and high-value executable comparators from the local census.

Constraints honored:

- No runtime behavior changes.
- No provider calls.
- No browser execution.
- No dependency installation.
- No competitor code execution.
- No push.
- No frozen holdout usage.
- No competitor code copied.
- Raw local paths intentionally omitted; local identities are recorded with path hashes.
- Claims below rely on source/code evidence and existing local audit artifacts, not README-only marketing claims.

Doctrine preserved:

```text
MODEL = semantic judgment, strategy, invention
SENTINEL = body, senses, runtime, evidence, authority and laws
```

The audit rejects features that replace model strategy with a closed planner, even when they automate more.

## Proof Tiers Used

```text
T0_STATIC_INSPECTED = code or docs inspected only
T1_EXECUTABLE_CODE_REACHABLE = executable route exists by source call path, not run here
T2_LIVE_BODY_PROVEN = live browser body proof exists outside this audit
T3_REAL_MODEL_PRODUCT_PROVEN = real model + real browser product proof exists outside this audit
T4_HOLDOUT_GENERALIZATION_PROVEN = frozen holdout proof exists
```

This audit did not run code, so comparator systems are classified only up to `T1` unless an existing accepted Sentinel proof already exists.

## Exact Local Identities

Raw paths are deliberately excluded. `path_hash` is a stable local identity hash for the discovered project root.

| system_id | path_hash | project | commit/version | license | runtime |
|---|---:|---|---|---|---|
| `sentinel_browser_product_path` | `sentinel_repo_relative` | Sentinel Browser Organ product path | current working tree | internal | Python |
| `openclaw_current_external` | `a98599a7eeda8c9d` | OpenClaw external checkout | `aa76cf43f0113b25091cd6edda0b791b0f611822` / `2026.4.19-beta.2` | MIT | TypeScript/Node |
| `openclaw_agent_lab_snapshot` | `2373f213526fe6ae` | OpenClaw Agent Lab snapshot | `a2288c2b09e621f89a915960398f58e200b3b69d` / `2026.2.1` | MIT | TypeScript/Node |
| `jarvis_agent_lab_snapshot` | `562e2cfbf6a890b3` | Jarvis Agent Lab snapshot | `20bf2b79657002fa2668a2ecf4ff5c6611d9bd4b` | Jarvis Source Available License 2.0 | TypeScript/Bun + sidecar |
| `openjarvis_agent_lab_snapshot` | `bbb15d21fa3467a3` | OpenJarvis Agent Lab snapshot | `bb904804302dd7a6f81698b49bf38dd22f06e3de` | Apache-2.0 | Python/Rust/TypeScript |
| `webwright_agent_lab_snapshot` | `2e418707f78d6a2a` | Webwright Agent Lab snapshot | `4a46f282ec37f27d6003cc498a977939d62d9015` | MIT | Python |
| `ui_tars_agent_lab_snapshot` | `abb32c7b74b22c9e` | UI-TARS Desktop / Agent TARS snapshot | `e9f3387288da4af2ad99972da2ac916cdabce093` | Apache-2.0 | TypeScript/Electron/Node |
| `gptme_agent_lab_snapshot` | `d01398dea8edc474` | gptme snapshot | `7355b1820342a43cda846cd88cee291b77b6f2dc` | permissive MIT-like | Python |
| `agent_zero_agent_lab_snapshot` | `a737c56bd1a6277d` | Agent Zero snapshot | `f9d8167a0004632ea7d8b37f585f392c39865919` | MIT | Python |
| `deerflow_agent_lab_snapshot` | `c8e6eb79bb7cffbb` | DeerFlow snapshot | `9a5de8d6a5a75c9f277a79d36b90407e3029a1ba` | MIT | Python/TypeScript |

The exact comparison matrix is in:

```text
SENTINEL_BROWSER_ORGAN_COMPARISON_MATRIX_V1.csv
```

## A. Executable Product Graphs

### Sentinel Browser Organ Product Path

Reachability: `CURRENT_PRODUCT_REACHABLE`

Proof tier:

- `T3` for repeated Python.org product-spine missions accepted before this audit.
- `T1/T2` for individual sub-capabilities depending on local/live proof.
- `T4` not yet proven.

Executable graph:

```text
ModelLedProductActionKernelTaskLoop
-> RuntimeHost
-> ProductActionKernel / ProductActionKernelDispatchAdapter
-> real_browser skill executor
-> RealBrowserControlRuntime / BrowserSessionManagerL5Live
-> CloakBrowserSessionBackend
-> ProductActionKernelReceipt + BrowserSessionReceipt
-> FinalGate
-> replay no-react
```

Key source evidence:

- `sentinel/operator/runtime_host.py:417` registers `real_browser.search` as product skill `browse_search`.
- `sentinel/operator/runtime_host.py:854` starts the product browser executor.
- `sentinel/operator/runtime_host.py:971` routes browser action execution.
- `sentinel/operator/runtime_host.py:1002` creates safe failure packets after browser action failures.
- `sentinel/operator/runtime_host.py:1454` performs real browser preflight and backend truth checks.
- `sentinel/operator/model_led_product_action_kernel_task_loop.py:152` is the product model-led loop.
- `sentinel/agent/organs/browser_session_manager_l5_live.py:357` defines the Cloak-first live session manager.
- `sentinel/agent/organs/browser_session_manager_l5_live.py:418` writes open-session receipts.
- `sentinel/agent/organs/browser_session_manager_l5_live.py:452` writes observe receipts.
- `sentinel/agent/organs/browser_session_manager_l5_live.py:533` writes interaction receipts.
- `sentinel/organs/browser/cloak_backend.py:52` defines `CloakBrowserSessionBackend`.
- `sentinel/operator/unified_execution_dispatcher.py:173` defines `ProductActionKernelReceipt`.
- `sentinel/operator/mission_artifact_bundle.py:112` exports mission artifact bundles.

Sentinel is strongest in governed product routing, backend truth, receipts, replay, and hard-boundary discipline. Its current browser weakness is less about raw actuation now and more about persistent answer-quality evidence: final browser answers need a first-class claim-to-evidence matrix tied back to browser receipts.

### OpenClaw Current External Checkout

Reachability: `PRODUCT_REACHABLE_IN_OWN_RUNTIME`

Proof tier: `T1_EXECUTABLE_CODE_REACHABLE` in this audit.

Executable graph:

```text
OpenClaw agent/tool layer
-> browser control server
-> browser routes
-> snapshot / act / storage / debug / tabs
-> Playwright / Chrome CDP sessions
-> route response to agent
```

Key source evidence:

- `extensions/browser/src/server.ts:26` starts the browser control server.
- `extensions/browser/src/browser/routes/index.ts:7` registers browser route families.
- `extensions/browser/src/browser/routes/agent.snapshot.ts:355` exposes snapshot perception.
- `extensions/browser/src/browser/routes/agent.act.ts:336` exposes browser action execution.
- `extensions/browser/src/browser/routes/agent.storage.ts:67` exposes storage operations.
- `extensions/browser/src/browser/routes/agent.debug.ts:68` exposes request/debug metadata.
- `extensions/browser/src/browser/routes/tabs.ts:146` manages tabs.
- `extensions/browser/src/browser/pw-session.ts:82` stores network/request state.
- `extensions/browser/src/browser/pw-tools-core.snapshot.ts:23` captures accessibility tree snapshots.
- `extensions/browser/src/browser/pw-tools-core.interactions.ts:497` executes browser interactions.
- `src/agents/openclaw-tools.ts:51` creates OpenClaw tools for agents.

OpenClaw has broader browser senses than Sentinel currently exposes in one product frame: AX snapshots, Chrome MCP snapshot, screenshots with labels, CDP sessions, network request caches, storage, debug traces, tabs, and action routes. It does not show Sentinel-grade independent receipt/replay/FinalGate or answer claim evidence. The useful adaptation is its multi-source perception and ref caches, not its raw route surface.

### Agent Lab OpenClaw Snapshot

Reachability: `PRODUCT_REACHABLE_IN_OWN_RUNTIME`

Proof tier: `T0/T1`, source-only local audit.

Evidence:

- `agent-lab/audits/final/openclaw_final_forensic_report.md`
- `agent-lab/module-harvest/browser/openclaw/OPENCLAW_BROWSER_ENTRYPOINTS.md`
- `agent-lab/module-harvest/browser/openclaw/P3N_BROWSER_FINAL_SUPREMACY_REVIEW.md`

The snapshot independently confirms the same pattern: strong browser gateway and plugin ecosystem; broad raw browser power; weaker proof architecture. It is useful as a second provenance point but should not override the current external checkout.

### Jarvis Agent Lab Snapshot

Reachability: `PRODUCT_REACHABLE_IN_OWN_RUNTIME`

Proof tier: `T1_EXECUTABLE_CODE_REACHABLE` for authority/sidecar/tool paths.

Executable graph:

```text
Jarvis agent/orchestrator
-> tool registry
-> authority engine / approval / audit
-> sidecar RPC or local controller
-> browser/desktop action
-> tool result
```

Key source evidence:

- `src/authority/engine.ts:61` defines the central `AuthorityEngine`.
- `src/authority/tool-action-map.ts:20` maps browser tools to `access_browser`.
- `src/sidecar/protocol.ts:33` defines sidecar RPC requests.
- `src/sidecar/types.ts:8` defines sidecar capabilities including browser/screenshot.
- `src/actions/tools/desktop.ts:288` exposes desktop snapshots.
- `src/actions/tools/desktop.ts:321` exposes desktop click.
- `src/actions/tools/desktop.ts:478` exposes screenshots.
- `src/actions/browser/session.ts`, `src/actions/browser/cdp.ts`, and `src/actions/browser/chrome-launcher.ts` contain browser/session/CDP surfaces.

Jarvis is valuable for the Computer Cortex direction: sidecar registration, capability manifests, revocation, emergency pause/kill, desktop UI tree, and audit/approval structures. Its danger is approval theater and fixed tool categories if copied above the model rather than below the effect boundary.

### Webwright Agent Lab Snapshot

Reachability: `PRODUCT_REACHABLE_IN_OWN_RUNTIME`

Proof tier: `T1_EXECUTABLE_CODE_REACHABLE`

Executable graph:

```text
DefaultAgent
-> model writes executable Python action
-> LocalBrowserEnvironment
-> Playwright page/context/browser
-> screenshot/log observation
-> trajectory artifact
-> final script/result
```

Key source evidence:

- `src/webwright/agents/default.py:83` defines `DefaultAgent`.
- `src/webwright/agents/default.py:341` runs the agent loop.
- `src/webwright/agents/default.py:400` executes model actions.
- `src/webwright/agents/default.py:455` serializes trajectory format.
- `src/webwright/environments/local_browser.py:191` defines live browser environment.
- `src/webwright/environments/local_browser.py:387` executes actions.
- `src/webwright/environments/local_browser.py:432` runs generated Python code.
- `src/webwright/environments/local_browser.py:463` captures observations.
- `src/webwright/run/cli.py:31` defines CLI run entry.

Webwright is the strongest comparator for model amplification: the model writes code-as-action, producing reusable scripts and trajectories. For Sentinel, this should become a governed `SkillCandidate` / Mission Studio sandbox pattern, not the default browser organ. Raw script execution, screenshots, and arbitrary Playwright must not bypass Sentinel authority, receipts, and replay.

### UI-TARS Desktop / Agent TARS Snapshot

Reachability: `PRODUCT_REACHABLE_IN_OWN_RUNTIME`

Proof tier: `T1_EXECUTABLE_CODE_REACHABLE`

Executable graph:

```text
GUI/Agent TARS prompt and action parser
-> GUIAgentToolCallEngine
-> browser/computer operator
-> screenshot/visual grounding
-> parsed action execution
-> event stream / visualizer
```

Key source evidence:

- `multimodal/gui-agent/operator-browser/src/browser-operator.ts:218` receives parsed actions.
- `multimodal/gui-agent/operator-browser/src/browser-operator.ts:237` executes a single browser action.
- `multimodal/gui-agent/operator-browser/src/browser-operator.ts:650` locates active page state.
- `multimodal/gui-agent/agent-sdk/src/ToolCallEngine.ts:35` defines GUI action engine.
- `multimodal/gui-agent/agent-sdk/src/prompts.ts:9` defines GUI/browser action prompts.
- `multimodal/tarko/agent/src/agent/agent-runner.ts` and snapshot/event-stream directories show agent/event replay data.

UI-TARS is valuable for visual fallback, event streams, and computer/browser hybrid thinking. The danger is a model ceiling: the prompt exposes a small action grammar and encourages one-screen action parsing. Sentinel should absorb visual grounding as a sense, not make a screenshot action grammar the model's whole cognitive interface.

### OpenJarvis Agent Lab Snapshot

Reachability: `EXECUTABLE_NOT_BROWSER_PRODUCT_ROUTED`

Proof tier: `T0/T1` adjacent comparator.

Key source evidence:

- `docs/user-guide/tools.md:100` describes `ToolExecutor` as central dispatch.
- `docs/user-guide/tools.md:181` states built-in tools are registry-discovered.
- `tests/evals/*` contains broad evaluation machinery.
- `rust/crates/openjarvis-security/src/capabilities.rs` indicates capability-security modeling.
- `src/openjarvis/agents/deep_research.py` and examples show research/citation patterns.

OpenJarvis is not the best browser organ comparator, but it is valuable for evaluation depth, local/cloud model routing, cost/energy telemetry, skill discovery, and learning loops. These patterns matter after Sentinel's browser evidence layer is stable.

### Additional Comparators From Census

`gptme`, `Agent Zero`, and `DeerFlow` were included in the CSV as secondary comparators. They are useful for general agent-loop and research-flow patterns, but the local evidence inspected did not make them higher-value browser organ comparators than OpenClaw, Webwright, Jarvis, UI-TARS, and OpenJarvis.

## B. Sentinel Advantages

1. Product spine ownership is stronger than every comparator inspected.

Sentinel routes product browser skills through `RuntimeHost -> ProductActionKernel -> browser runtime -> receipts -> FinalGate -> replay`. OpenClaw and UI-TARS have rich browser routes; Webwright has rich trajectories; Jarvis has authority/audit; none show the same unified product-spine receipt and replay contract.

2. Backend truth is first-class.

Sentinel explicitly separates selected backend and actual backend, and previously blocked silent Cloak-to-Playwright mismatch. OpenClaw/Webwright/UI-TARS are powerful but less strict about product-backend proof.

3. Authority doctrine is more precise.

Recent typed-effect work separates semantic data from capability requests and authority grants. Jarvis has a useful authority engine, but Sentinel's doctrine better avoids topic policing when implemented consistently.

4. Replay/no-react is a real differentiator.

OpenClaw has traces and routes. Webwright has trajectories. UI-TARS has event streams. Sentinel has replay no-react as an explicit product invariant.

5. The Cognitive OS direction is more open-world.

Sentinel's doctrine says classifiers generate candidates/evidence and the model remains the mind. This avoids the ceiling risk in prompt-action grammars and closed planners.

## C. Sentinel Deficits

1. Browser sensing breadth still trails OpenClaw.

OpenClaw exposes AX snapshots, Playwright AI snapshots, screenshots with labels, CDP, network request caches, storage routes, debug traces, and tabs. Sentinel has pieces of this through BrowserEnvironmentState, Cloak, safe DevTools context, and session receipts, but not yet one complete product-grade perception ledger.

2. Answer-quality evidence is not yet independently strong enough.

Sentinel has receipts and evidence summaries, but final browser answers need a stable `claim -> evidence_ref -> support/contradiction/unknown` matrix. This is the direct input to `FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1`.

3. Receipt locations are fragmented.

Evidence exists across `product_action_kernel/receipts`, `real_browser_control/receipts`, browser session receipts, crash-safe ledgers, FinalGate outputs, and bundles. The next fix should index and cross-link them rather than add another isolated receipt file.

4. Visual fallback is under-integrated.

UI-TARS and OpenClaw show stronger screenshot/visual labeling patterns. Sentinel should add safe visual references as evidence, not raw screenshots by default.

5. Code-as-action is not productized as a governed browser skill genesis path.

Webwright's main leap is letting the model create reusable browser scripts. Sentinel should adapt this as sandboxed `SkillCandidate` experimentation, not raw default execution.

6. Multi-site browser quality is still not proven.

Python.org product proof is valuable, but the frozen holdout remains locked and multi-site calibration remains open.

## D. Patterns Worth Adapting

1. OpenClaw multi-source snapshots.

Adapt role/AX snapshots, AI snapshots, request summaries, debug state, tab state, and ref caches into `BrowserEnvironmentState`, with safe evidence refs and no raw DOM/cookies/session persistence.

2. OpenClaw route-level ref caches.

Adapt stable ref cache freshness and locator provenance, but hide raw refs from model-facing cognition. The model should see semantic affordances and uncertainty.

3. Webwright code-as-action as sandboxed SkillCandidate generation.

Use it in Mission Studios: model creates browser scripts/tools in a sandbox, benchmarked and promoted only with evidence. Do not make arbitrary Playwright code the product path.

4. Webwright trajectory viewer concept.

Sentinel should have an audit viewer over receipts, evidence refs, model decisions, and replay proof. It must be privacy-safe and hash/ref based.

5. Jarvis sidecar capability manifest and emergency controller.

Useful for future Computer Cortex and physical/desktop body: capability manifests, revocation, emergency pause/kill, and reduced child authority.

6. UI-TARS visual grounding/event stream.

Adapt as a safe visual fallback layer that generates references and uncertainty, not as a screenshot-first closed action grammar.

7. OpenJarvis evaluation and learning loops.

Adopt benchmark/cost/energy/reliability thinking and SkillCandidate evaluation, but keep Sentinel proof and authority as the execution spine.

## E. Patterns That Would Create A Model-Intelligence Ceiling

1. Fixed browser planners that force one action sequence.

Reject. The model must be free to search, navigate, inspect, extract, or declare blockers through any safe grounded strategy.

2. Prompt-only GUI action grammars as the main cognitive protocol.

Reject as primary path. They can be compatibility adapters or visual operator backends, not the model's whole interface.

3. Closed product ontologies.

Reject. Entity extraction must allow documentation pages, APIs, code symbols, unknown entity types, and model-proposed attributes.

4. Raw micro-route browser APIs as model surface.

Reject as primary path. OpenClaw-like `act`, `storage`, `evaluate`, `tabs` routes are valuable internal organs but too low-level and high-risk as model-facing product language.

5. Code-as-action without authority and replay.

Reject as default. Webwright's freedom is powerful, but Sentinel must sandbox it and produce receipts/replay before promotion.

6. Approval theater.

Reject. Jarvis-style approvals are useful only at real effect boundaries; they should not block ordinary cognition or reversible in-scope actions.

## F. Critical Gaps For The Final Browser Organ

P0 gaps:

1. Browser receipt persistence index.

Create one mission-scoped index mapping:

```text
model decision id
-> internal ActionEnvelope id
-> ProductActionKernelReceipt id
-> browser/session receipt id
-> BrowserEnvironmentState evidence refs
-> final answer claim refs
```

2. Final answer claim capture.

Every browser research answer should persist:

```text
claim_id
claim_text_hash
claim_type
support_status = supported | contradicted | unknown | unsupported
evidence_refs
source_kind
confidence
unknowns
contradictions
```

3. Unsupported claim gate.

FinalGate for browser knowledge missions should reject unsupported material claims while accepting truthful blockers/unknowns.

4. Evidence refs across perception channels.

AX/DOM/network/console/visual/structured-data snippets should create safe evidence refs, not raw dumps.

5. Audit bundle readback.

The exported mission artifact must be able to prove, from files alone, that the final answer came from supported evidence and that replay did not redo browser effects.

P1 gaps:

6. Visual fallback evidence references.

Use screenshot/vision only as bounded safe evidence, with crop/ref hashes or labels; no full screenshot by default.

7. Network and console materiality evidence.

Search materiality should include safe request/navigation/result-region deltas and console/runtime error summaries.

8. Open-world entity graph.

Preserve unknown kinds, model-proposed attributes, contradictions, and relationships without coercing all results into commerce/product shapes.

P2 gaps:

9. Governed SkillCandidate for browser scripts.

Adapt Webwright-style reusable scripts in a sandbox after receipt/answer evidence is solid.

10. Browser audit viewer.

Build a human-readable viewer over the evidence bundle after the data model is correct.

## G. Proposed Fair Executable Benchmark Specification

Name:

```text
BROWSER_ORGAN_EXECUTABLE_EVIDENCE_AND_ANSWER_QUALITY_BENCH_V1
```

Purpose:

Measure browser organ quality without forcing one exact action trajectory.

Systems under test:

- Sentinel Browser Organ product path.
- Optional sandboxed comparator wrappers only after separate security review.
- No competitor execution inside this Stage A audit.

Task set:

- 20 non-holdout public read-only tasks.
- 5 commerce/catalog.
- 5 documentation/API/code-reference.
- 4 news/article/information retrieval.
- 3 multilingual.
- 3 negative/uncertain-answer tasks.
- At least 5 tasks where search is not the best first strategy.
- At least 5 tasks requiring follow-link or inspect-result.
- At least 5 tasks requiring extraction from multiple evidence sources.

Allowed model freedom:

- Query formulation free.
- Navigation strategy free inside origin/scope.
- Multiple safe trajectories accepted.
- Unexpected successful safe path recorded as capability discovery.

Metrics:

```text
objective_satisfaction_rate
grounded_answer_rate
unsupported_claim_count
claim_evidence_coverage
search_materiality_precision
entity_type_precision
unknown_preservation_rate
recovery_success_rate
repeated_action_without_new_evidence_rate
root_lease_continuity_rate
browser_receipt_persistence_rate
claim_to_browser_receipt_link_rate
FinalGate_false_accept_count
FinalGate_false_reject_count
replay_side_effect_count
cleanup_success_rate
hard_boundary_violation_count
raw_secret_or_raw_dom_persistence_count
latency_and_cost_distribution
```

Success threshold for Sentinel Browser Organ pre-holdout:

```text
tasks_measured >= 18/20
grounded_answer_rate >= 0.85
claim_evidence_coverage >= 0.95
unsupported_material_claims = 0
browser_receipt_persistence_rate = 1.0
claim_to_browser_receipt_link_rate >= 0.95
replay_side_effect_count = 0
hard_boundary_violation_count = 0
raw_secret_or_raw_dom_persistence_count = 0
```

Holdout remains locked until the non-holdout benchmark passes.

## H. Prioritized Recommendations For FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1

1. Add a mission-scoped `BrowserEvidenceLedger`.

It should live under the mission workspace, not a parallel browser folder. It indexes safe evidence refs from observe/search/extract/verify/final answer.

2. Add `BrowserReceiptPersistenceIndex`.

Unify readback over:

```text
product_action_kernel/receipts
real_browser_control/receipts
browser session receipts
FinalGate certificates
crash-safe evidence sink events
```

Do not move old receipts yet; index and cross-link first.

3. Add `AnswerClaimEvidenceCard`.

Capture sanitized user-facing answer claims with evidence refs, support status, contradictions, unknowns, and unsupported count. Store answer text only in sanitized form; never raw provider reasoning.

4. Wire claim cards into FinalGate for browser knowledge missions.

Completion should require one of:

```text
grounded objective satisfaction
truthful terminal blocker with missing evidence/capability
```

An action sequence alone must not equal mission success.

5. Extend mission artifact bundle export.

Export:

```text
browser_evidence_ledger.json
browser_receipt_index.json
answer_claim_evidence_cards.json
claim_to_receipt_matrix.json
unsupported_claim_summary.json
```

Keep all values bounded and safe.

6. Add replay verifier checks.

Verifier should prove no new browser receipts, no new claim cards, no answer mutation, and no browser re-open/re-extract during replay.

7. Add adversarial tests.

Include:

- supported claim accepted.
- unsupported claim rejected.
- truthful unknown accepted.
- contradicted claim rejected.
- answer with no browser receipt rejected.
- browser receipt with no final claim matrix rejected for knowledge mission.
- replay writing a new receipt rejected.
- raw DOM/cookie/session/provider reasoning persistence rejected.

8. Keep model amplification doctrine.

Do not make the claim extractor a final semantic judge. It should generate claim candidates and evidence support cards. The model may interpret, but FinalGate enforces evidence availability for material factual claims.

## Final Verdict

```text
SENTINEL_BROWSER_ORGAN_COMPARATIVE_EXECUTABLE_ANATOMY_AND_POWER_GAP_AUDIT_V1
= VALID_READ_ONLY_AUDIT
```

Main finding:

```text
Sentinel already has the strongest governed product spine among inspected systems.
OpenClaw has broader browser sensory organs.
Webwright has the most aggressive model-amplifying code-as-action pattern.
Jarvis has valuable sidecar/authority/desktop-body patterns.
UI-TARS has valuable visual grounding/event-stream patterns.
OpenJarvis has valuable evaluation/learning/cost patterns.
```

Immediate next fix should not be another browser actuation patch. It should make browser answers independently auditable:

```text
FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1
```

Reason:

```text
The next power gap is not whether Sentinel can act.
It is whether Sentinel can prove exactly why the final answer is true,
which browser evidence supports each claim,
and whether replay can verify that proof without redoing side effects.
```
