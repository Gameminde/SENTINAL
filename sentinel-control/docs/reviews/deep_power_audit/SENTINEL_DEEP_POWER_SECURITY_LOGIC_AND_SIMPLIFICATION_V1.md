# Sentinel Deep Power Audit V1 - Security, Logic Bugs, And Simplification

Status: audit-only

## Security Verdict

Sentinel does not need less protection against real damage.

Sentinel needs less internal friction against useful in-scope action.

Keep hard stops at real-world boundaries:

```text
credentials
Authorization/session/cookie persistence
payment/checkout/trading
external messages outside grant
login/account mutation
destructive write/delete
ungranted origin/workspace escape
provider-native tools
fallback/AUTO
fake receipts
duplicate external sends on replay
```

Move ordinary in-scope failures to recovery:

```text
stale ref
locator timeout
alias mismatch
schema shape miss
dynamic loading
hidden/disabled element
search box candidate failed
extractor too shallow
finish/proof branch mismatch
```

## Hard Stops That Should Stay

| Area | Good existing boundary |
|---|---|
| Provider/model execution | selected provider/backend/model identity checks, catalog gate, scoped credential handles, safe receipts |
| Raw model material | prompt/response mostly excluded or hashed/redacted |
| Power bridge | blocks inactive authority, tampered missions, L6/L7, credential family, irreversible markers, out-of-envelope plans |
| Workspace mutation | root containment, traversal/symlink/sensitive path checks, before/after hashes |
| Shell/code | tokenized allowlist, `shell=False`, scrubbed env, cwd containment |
| External API/channel | allowed domain/method/destination policies, receipts, idempotency intent |
| Browser read-only | URL guard and final URL checks in stronger paths |
| Credential vault | metadata/sealed refs only, no raw secret return |

## Missing Or Fragile Boundaries

| Priority | Boundary | Issue | Fix |
|---|---|---|---|
| P1 | ActionKernel capability/operation | Kernel checks revoked authority and forbidden material, but relies on executors for action allowlists | Kernel should validate action is in current actionability frame or authority envelope |
| P1 | Channel idempotency | Marker written after send success; crash window can resend | Pending-send ledger before transport |
| P1 | Browser post-action origin | Some L5 paths validate before action, not uniformly after click/fill navigation | Central post-action origin revalidation |
| P1 | Browser V3 empty domain set | Empty allowed domains can mean allow-all | Require explicit origin scope for live web control |
| P2 | Shell semantic side effects | `pytest`/build scripts can write or call network | Add execution profile labels and dry-run/no-network modes where needed |
| P2 | Browser screenshots/snapshots | Can capture PII/session state if persisted | Default hash/redact; store bounded text/cards unless explicit visual audit |

## Logic Bugs That Reduce Power

| Priority | Bug | Evidence | Power impact | Fix direction |
|---|---|---|---|---|
| P1 | Material budget can accepted-complete without proof | `ModelLedTaskLoop` can complete on material budget; tests assert patch-only completion | False green; mission can stop before bounded verification | Budget without proof should enter proof/recovery lane or block honestly |
| P1 | Recoverable runtime misses become terminal | `ActionKernel.execute` wraps broad exceptions as `ActionKernelError`; loop blocks | Stale refs/timeouts kill mission | Return recoverable `ActionResult` with refreshed context |
| P1 | `wait_for_text` cannot satisfy real-browser completion | Recommended in context but objective satisfaction only counts assert/extract | Model follows guidance but cannot finish | Count passed wait receipts as proof when appropriate |
| P1 | Browser proof mode only allows assert | After budget, loop restricts real browser proof to assert_text | Product research/extraction tasks are forced into toy assertion | Permit extract/wait/product cards as proof |
| P2 | Extraction alone can satisfy control mission | Real-browser objective can be true with extraction only | Control task can become read-only claim | Require material action plus proof for control objectives |
| P2 | Browser decision extraction bridge not clearly production-wired | Extractor exists but audit saw mostly tests/module refs | Provider output may not become ActionEnvelope reliably | Wire production adapter with typed protocol recovery |

## Security Layers That Look Overcomplicated

| Layer | Diagnosis | Power-first treatment |
|---|---|---|
| `DelegatedActionGate` | Metadata-only, cannot execute | Keep as planner hygiene, do not treat as permission system |
| Manifest/identity registries | Visibility/control-plane only | Useful map, but not a power path |
| Broad string scanners | Can block benign labels and still not replace executor checks | Keep canaries, but rely on boundary-specific runtime checks |
| Credential vault layers | Safe persistence, but not yet materializer | Next value is scoped lease execution, not more docs |
| Parallel browser gates | Duplicate proof logic increases drift | Choose one proof owner and one browser skill |

## Simplification Candidates

| Rank | Candidate | Estimated LOC impact | Power gain |
|---:|---|---:|---|
| 1 | Unify browser stacks under one browser skill | -1200 to -2500 | Huge |
| 2 | Replace organ branch matrices with capability spec registry | -900 to -1300 | High |
| 3 | Collapse duplicate browser FinalGate ownership | -1400 to -1900 | Medium |
| 4 | Shrink read-only audit scaffolding into evidence skill | -2000 to -3200 | High |
| 5 | Split real-model certification monolith | -800 to -1500 net | Medium |
| 6 | Extract `AgentRuntime.run` phases | -300 to -900 net | Medium |
| 7 | Deduplicate authority/receipt/finalgate primitives | -1000 to -2000 | Medium |
| 8 | Descriptor-driven telemetry event recording | -600 to -950 | Medium |

## What To Delete Or Deprecate First

Do not delete hard stops.

Delete/deprecate friction that blocks power without protecting real-world damage:

```text
browser model-facing locator refs not backed by executable resolver
pack-specific proof branches that force toy actions
parallel browser proof implementations
non-product browser/control route names exposed as if product-ready
metadata-only gates that are described as execution readiness
stale docs claiming power where real run still blocks
```

## What To Keep As Sentinel's Moat

```text
receipts
replay no re-execute
FinalGate truth
mission-level authority
scope/origin/destination boundaries
provider truth diagnostics
raw secret/provider/reasoning non-persistence
kill/revocation
```

These are not bureaucracy if they stay invisible and automatic.

They become bureaucracy only when the model has to navigate them instead of using a skill.

