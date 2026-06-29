# SENTINEL_CORE_POWER_CONTRACT_LOCK_V1

## 1. Executive Verdict

This document is the canonical kernel power contract for Pack 6C.

Pack 6C MUST NOT be treated as a browser-only stable-ref patch. The browser
failure exposed the issue, but the issue is in the shared execution contract:

```text
what the model sees as actionable
MUST be executable by the runtime,
and if execution fails inside granted authority,
Sentinel MUST recover instead of terminal-blocking,
unless the requested effect is real damage or scope escape.
```

Pack 6C is NOT ACCEPTED unless it strengthens the kernel-wide actionability and
recovery contract across model-led power surfaces.

## 2. Core Doctrine

Sentinel MUST obey these laws:

```text
Model leads.
Sentinel executes.
Receipts/replay happen in the background.
FinalGate certifies truth; it is not the recovery engine.
Hard stop only on real damage or scope escape.
Confusion inside granted scope becomes recovery.
Do not control intelligence.
Control real-world power.
```

Primary law:

```text
Sentinel does not block because it is confused.
Sentinel blocks only because the requested effect is outside authority,
would cause real damage,
would corrupt source invariants,
or would falsify proof/replay.
```

## 3. Four-Plane Model

Pack 6C MUST preserve and wire these four planes.

| Plane | Responsibility | Pack 6C obligation |
|---|---|---|
| Intelligence Plane | The model chooses the next action. | Keep the model as pilot inside the mission grant. |
| Actionability Plane | Sentinel exposes live executable candidates, or produces recovery. | Add a registry/frame contract so candidates are executable. |
| Authority Plane | Sentinel checks whether the requested effect is inside mission scope. | Hard-stop scope escape and real damage; normalize aliases before checks. |
| Proof Plane | Sentinel receipts, verifies, certifies, and replays without repeating side effects. | Preserve receipts, FinalGate truth, and replay purity. |

Sentinel is currently strongest in Authority and Proof. Pack 6C MUST strengthen
Actionability and Recovery.

## 4. Failure Taxonomy

All model-led execution failures MUST be classified before terminalization.

| Class | Terminal? | Examples | Required runtime behavior | Required loop behavior | Proof/replay impact |
|---|---:|---|---|---|---|
| `HARD_STOP_REAL_DAMAGE` | Yes | payment, checkout, contact supplier, credential access, duplicate external send on replay | Refuse before effect if possible; never fake receipt | Terminal block | Certificate must record honest block; replay must not repeat side effect |
| `HARD_STOP_OUT_OF_SCOPE_AUTHORITY` | Yes | workspace escape, ungranted browser origin, ungranted channel destination | Refuse under authority boundary | Terminal block | No material receipt; safe denial proof only |
| `RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE` | No while budget remains | unknown ref, stale selector, runtime ref registry mismatch | Return recovery observation | Continue with recovery lane | No material effect; recovery observation may be receipted |
| `RECOVERABLE_MODEL_PROTOCOL_FAILURE` | No while budget remains | malformed JSON, metadata-only response, wrong envelope key | Return correction diagnostic | Continue with correction lane | No material effect |
| `RECOVERABLE_BROWSER_STATE_FAILURE` | No while budget remains, except boundary blockers | dynamic loading, search control not found, modal/consent | Observe/wait/refresh or classify blocker | Continue or valid-fail when unrecoverable | Browser state proof must be hash/safe summary only |
| `AUTHORITY_ALIAS_OR_MAPPING_BUG` | No as product behavior; source fix required | `read_only` vs `read_only_research`, `finish` vs `sentinel_loop.finish` | Normalize aliases before Gate/runtime | Continue after normalization or block as source invariant if impossible | Must not masquerade as safety success |
| `ACTIONABILITY_CONTRACT_VIOLATION` | No as product behavior; source fix required | candidate shown to model cannot execute | Produce recovery observation and fix registry contract | Continue while budget remains | Candidate registry hash should expose mismatch safely |
| `CONTEXT_TOO_THIN` | No while budget remains | model lacks refs/schema/progress | Provide richer correction/context frame | Continue with correction lane | No material effect |
| `BUDGET_TOO_STRICT` | No if proof/finish is pending | material budget reached before proof/finish | Open proof/finish lane | Continue bounded proof/finish | Must not create false success |
| `FALSE_SUCCESS_PREVENTION` | Yes for the attempted finish | finish before proof, missing receipt, tampered proof | Refuse success | Guide proof action if in scope | FinalGate must reject false success |
| `SOURCE_BUG_OR_RUNTIME_INVARIANT` | Yes until fixed | missing executor, corrupted registry, invalid source state | Refuse and report source invariant | Terminal block | No fake receipt; report invariant safely |

## 5. Hard-Stop Law

Terminal hard stop is allowed only for:

```text
real damage
scope escape
credential/secret compromise
irreversible external effect outside grant
replay side-effect repeat
proof falsification
source invariant corruption
```

Examples that MUST remain hard stops:

```text
payment
checkout
contact supplier
send inquiry outside grant
login with credentials
credential access/exfiltration
ungranted browser origin
ungranted channel destination
duplicate external send on replay
workspace path escape
destructive write/delete outside grant
provider-native tools
fallback/AUTO
tampered receipt/finalgate/replay proof
```

Pack 6C MUST NOT weaken these hard stops.

## 6. Recovery Law

If the action is inside mission authority and no real-world damage occurred,
Sentinel MUST prefer recovery/correction over terminal block while budget
remains.

Recoverable examples:

```text
unknown browser ref
stale selector
model JSON malformed
metadata-only model response
action alias mismatch
authority alias mismatch
runtime ref registry mismatch
search control not found
dynamic loading not settled
finish missing after proof
material budget reached before proof/finish
```

A recoverable failure MUST NOT be presented as a safety win.

## 7. Actionability Contract

Invariant:

```text
Anything shown to the model as an actionable candidate MUST be executable by
the runtime that receives the ActionEnvelope.
```

Required implications:

```text
DecisionContext MUST NOT expose executable candidates invented only by prose.
DecisionContext MUST derive executable candidates from ActionabilityFrame /
runtime registry or an equivalent runtime-backed source.
Candidate refs MUST have a registry id or equivalent runtime binding.
Candidate actions MUST include canonical capability, operation, required params,
and executable target refs or aliases.
If a candidate becomes stale, the runtime MUST create recovery observation
instead of terminal block.
```

A model-visible candidate that cannot execute is a kernel contract violation,
not a model failure and not a safety win.

## 8. Mission Authority Contract

Invariant:

```text
Mission-level grant unlocks smooth execution inside scope.
Per-action checks enforce boundary, but MUST NOT create friction for
already-granted actions.
```

Required implications:

```text
Aliases MUST be normalized before authority checks.
Runtime names, model names, and authority names MUST converge to canonical
action ids.
read_only / read_only_research aliases MUST NOT cause false Gate denial.
finish / sentinel_loop.finish MUST be canonicalized.
bounded_channel / channel_transport aliases MUST be canonicalized.
real_browser.* / real_browser_control.real_browser.* MUST be canonicalized.
```

Authority checks MUST block effects, not naming confusion.

## 9. Power State Machine

Pack 6C MUST implement or preserve a generic state machine with these states:

```text
DECISION_REQUESTED
MODEL_ACTION_PARSED
ACTIONABILITY_VALIDATED
AUTHORITY_CHECKED
MATERIAL_ACTION_EXECUTED
PROOF_ACTION_EXECUTED
RECOVERY_OBSERVATION_CREATED
CORRECTION_TURN_REQUESTED
FINISH_REQUESTED
TERMINAL_COMPLETED
TERMINAL_BLOCKED
```

Transition laws:

```text
If action crosses real boundary:
  TERMINAL_BLOCKED

If action is in scope but not currently executable:
  RECOVERY_OBSERVATION_CREATED
  then continue while recovery budget remains

If model output is visible but malformed:
  CORRECTION_TURN_REQUESTED
  then continue while correction budget remains

If proof exists and objective is satisfied:
  FINISH_REQUESTED
  then require sentinel_loop.finish

If replay would repeat external side effect:
  TERMINAL_BLOCKED

If proof is missing:
  do not claim success
  guide proof action if in scope
```

## 10. ActionKernel Contract

`ActionKernelError` MUST NOT be the generic path for all failures.

Required distinction:

```text
ActionKernelError =
  hard boundary,
  missing executor/invariant,
  or unrecoverable source bug.

RecoverableActionResult / RecoverableActionObservation =
  in-scope runtime/protocol/state failure.
```

Pack 6C is NOT ACCEPTED if every runtime miss still terminalizes through
`ActionKernelError`.

## 11. ModelLedTaskLoop Contract

`ModelLedTaskLoop` MUST NOT terminal-block recoverable in-scope failures while
recovery/correction budget remains.

It MUST support these lanes:

```text
material lane
proof lane
recovery lane
correction lane
finish lane
```

It MUST terminal-block only when:

```text
hard stop class
recovery budget exhausted
correction budget exhausted
proof contradiction
replay side-effect repeat risk
source invariant corruption
```

## 12. Budget Lane Contract

Pack 6C MUST separate budgets:

```text
max_material_actions
max_recovery_turns
max_correction_turns
max_proof_turns
max_finish_turns
max_repeated_recovery_for_same_failure
max_repeated_effective_action
```

Budget laws:

```text
Material budget MUST NOT kill proof or finish.
Recovery budget MUST NOT allow infinite loops.
Finish/proof lanes are bounded but separate from material effects.
Recovery/correction turns MUST be bounded and observable.
```

## 13. FinalGate Contract

FinalGate MUST certify terminal truth.

FinalGate MUST NOT replace recovery.

FinalGate MUST prevent false success.

FinalGate MUST preserve replay purity.

FinalGate SHOULD certify valid failure honestly after recovery/correction is
exhausted or a hard boundary is reached.

## 14. Cross-Surface Obligations

This is not a browser-only lock.

| Surface | Hard stop example | Recoverable in-scope example | Actionability requirement | Proof/replay requirement |
|---|---|---|---|---|
| `browser / real_browser_control` | payment, login, contact supplier, unbounded URL, credential field | unknown ref, stale selector, dynamic load, modal | Browser candidates MUST be registry-backed and alias-resolvable | Replay MUST NOT reopen/reclick/retype/resubmit/reextract |
| `channel / bounded_channel / channel_transport` | ungranted destination, duplicate send on replay | action alias mismatch, finish missing after delivery | Destination/action aliases MUST canonicalize to granted destination | Replay MUST NOT resend; delivery receipt required |
| `workspace_patch` | outside workspace, destructive write outside grant, base hash mismatch | patch verification pending, path alias mismatch | Patch target MUST be approved-root normalized | Patch receipt and verification/proof receipt required |
| `code_execution_sandbox` | shell/network escape, ungranted profile, credential read | bounded check missing, profile alias mismatch | Profile/action MUST be executable and listed in context | Command replay MUST NOT rerun; execution receipt required |
| `read_only_research` | outside path, secret path, unapproved root | read-only alias mismatch, search target normalization | Read-only actions MUST carry approved workspace scope | Observation receipt required; replay must not reread materially |
| `finish / FinalGate` | finish without proof, tampered proof | finish missing after proof | Finish aliases MUST canonicalize to `sentinel_loop.finish` | Terminal certificate must match receipts/replay |

## 15. Browser As First Acceptance Case, Not Whole Pack

Attempt 5B browser ref failure is the first acceptance case for Pack 6C, but
Pack 6C is a kernel power contract pack, not a browser patch.

Browser requirements to lock:

```text
BrowserActionabilityRegistry
ref aliases such as search_box
canonical executable refs
state-hash/epoch binding
unknown/stale ref -> recovery observation
payment/login/contact/credential/unbounded URL -> hard stop
```

Pack 6C is NOT ACCEPTED if it only fixes Alibaba/browser refs.

## 16. Pack 6C Acceptance Gates

Pack 6C is accepted only if:

```text
1. Generic loop distinguishes hard stop from recoverable in-scope failure.
2. ActionKernel no longer terminalizes all runtime misses the same way.
3. DecisionContext exposes candidates from an actionability registry/frame.
4. Authority aliases normalize before Gate/runtime dispatch.
5. Recovery/correction turns are first-class and budgeted separately.
6. Browser unknown ref recovers instead of terminal block.
7. Malformed visible model output triggers correction turn.
8. Material budget does not block proof/finish.
9. Hard danger remains terminal.
10. Replay never repeats external side effects.
11. Power Pack 1-6 regressions still pass.
```

## 17. Non-Goals

Pack 6C MUST NOT be:

```text
browser-only ref patch as the whole solution
prompt-only fix
Alibaba-specific selector hack
raw DOM or screenshot persistence
per-click approval friction
weakening hard stops for payment/login/credentials/scope escape
removing receipts/replay
provider-native tools
fallback/AUTO
```

## 18. Recommended Next Implementation

After this lock is committed and accepted, the next implementation SHOULD be:

```text
POWER_PACK_6C_ACTIONABILITY_RECOVERY_AND_POWER_STATE_MACHINE_V1
```

Minimum implementation obligations:

```text
typed failure classes
recoverable action observation/result path
ActionKernel hard-stop vs recovery distinction
ModelLedTaskLoop recovery/correction lanes
separate material/proof/recovery/correction/finish budgets
ActionAliasNormalizer
ActionabilityFrame or equivalent runtime-backed candidate registry
BrowserActionabilityRegistry as first concrete acceptance case
tests proving recovery vs hard stop
replay purity preserved
```

The next real proof after Pack 6C SHOULD be:

```text
REAL_POWER_ATTEMPT_5C_MODEL_LED_ALIBABA_ACTIONABILITY_RECOVERY_V1
```
