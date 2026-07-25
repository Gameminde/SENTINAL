# SENTINEL_PRESENCE_MISSION_XRAY_OBSERVER_V1_REPORT

## Verdict

```text
SENTINEL_PRESENCE_MISSION_XRAY_OBSERVER_V1
= VALID_SUCCESS_LOCAL_DETERMINISTIC_INTEGRATION

proof_tier = T1_LOCAL_DETERMINISTIC_CANDIDATE
provider_calls = 0
real_browser_runs = 0
sqlite_run = NOT_RUN
browser_cortex_changed = no
prompt_or_budget_changed = no
```

This tranche makes persisted Sentinel mission truth observable through one
versioned Presence Protocol, a human Route view, a developer X-Ray view, a
safe replay archive, and a best-effort live sidecar transport.

It does not claim a successful real-model mission, a generalized browser
result, or a production desktop package.

## Product Boundary

The product boundary is now explicit:

```text
canonical persisted mission truth
-> PresenceProjector
-> presence_event_v1
-> Route projection + X-Ray projection
-> Living Obsidian surface
```

The reverse path does not exist in this tranche:

```text
Presence UI -X-> runtime action
Presence UI -X-> authority grant
Presence UI -X-> receipt or FinalGate creation
```

The observer imports no provider client and calls no runtime action. Its
events are data only:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

## Implemented Surfaces

### Presence Protocol V1

`sentinel/operator/presence_observer.py` adds:

```text
PresenceEventV1
PresenceReplayArchiveV1
PresenceProjector
PresenceEventBuffer
PresenceSidecarRelay
PresenceSnapshotSidecar
PresenceJsonlJournal
presence_observer_cli
```

The envelope includes:

```text
event_id
mission_id
sequence
source_sequence
decision_index
timestamp
presence_state
event_kind
safe_summary
provider_metadata
context_pack_ref/hash
available_affordances
normalized_decision
dispatch_status
product_receipt_ref
browser_receipt_ref
before/after state fingerprints
before/after evidence fingerprints
material_progress
authority_state
blocker
gate_results
first_causal_divergence_ref
telemetry_state
ledger_head
source_event_hash
event_hash
```

Event IDs, event hashes and replay archive hashes are deterministic. Replaying
the same safe artifacts does not mint random identities.

### Two Views From One Event

Every `PresenceEventV1` produces:

```text
presence_route_view_v1
= human-readable observation/action/proof/blocker summary

presence_xray_view_v1
= context hash, normalized decision, dispatch, receipts, fingerprints,
   progress truth, authority state, gate results and causal divergence ref
```

Neither projection exposes raw chain-of-thought, raw provider output, full
system prompts, raw browser content, credentials, cookies, tokens, raw
exceptions or sensitive local paths.

### Live Sidecar

`PresenceSnapshotSidecar` observes successive already-persisted safe snapshots.
It:

- emits only source sequences newer than its high watermark;
- deduplicates by `mission_id + sequence`;
- keeps a reconnect buffer;
- never propagates relay failure into mission execution;
- can append validated envelopes to `PresenceJsonlJournal`;
- never invokes a model, runtime action, receipt writer or FinalGate.

The journal is a derived transport cache, not a new source of mission truth.
The separate `sentinel-presence-observer` command can run once for replay
materialization or poll safe artifact files beside a live mission. It is not
started inside RuntimeHost, so the mission loop has no synchronous dependency
on it.

### Read-Only Web Bridge

`GET /api/presence/events` reads a configured safe JSONL journal only when both
of these are supplied:

```text
SENTINEL_PRESENCE_STREAM_ROOT
SENTINEL_PRESENCE_STREAM_PATH
```

The resolved stream path must remain below the configured root. The endpoint:

- performs no writes;
- accepts only `presence_event_v1`;
- requires `data_not_authority=true`;
- requires `can_grant_authority=false`;
- requires `can_execute=false`;
- orders and deduplicates events;
- supports `mission_id` and `after` reconnect cursors;
- returns `503` rather than inventing a live connection when no stream exists.

### Living Obsidian Surface

`/presence` is now the default web entry point. It contains:

- a full-screen living orb rather than a dashboard;
- state-driven cyan, violet, amber and red expressions;
- route hidden by default;
- constellation route nodes when requested;
- a replay scrubber;
- a developer X-Ray capsule;
- `Shift+X` for X-Ray;
- a visible but disabled Kill control during historical replay;
- a command surface explicitly marked read-only during replay;
- a live-connect control that falls back honestly when no stream exists.

The existing `/dashboard` remains available and was not deleted.

## Historical MDN Replay Proof

The projector was executed directly against these three safe members of the
historical ZIP without extracting the archive:

```text
safe_evidence_snapshot.json
safe_browser_proof_index.json
mission_ledger.json
```

No runtime, authority, session, raw provider, raw browser or execution-request
parameter directory was imported into Git.

Observed result:

```text
mission_id =
brp_v1_mdn_css_has

presence_event_count = 46
terminal_presence_state = BLOCKED

first_causal_divergence.decision_index = 5
first_causal_divergence.classification =
BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS

decision 5 product receipt =
product_action_kernel_receipt_cf98fc984b54491aa05b08d3d81374a0
decision 5 browser receipt = absent
decision 5 telemetry = TELEMETRY_INCOMPLETE

decision 7 product receipt =
product_action_kernel_receipt_8780634596bd4ba59490465ad054376b
decision 7 browser receipt = absent
decision 7 telemetry = TELEMETRY_INCOMPLETE
```

The old persisted divergence file named decision 8. The Presence replay does
not copy that obsolete conclusion. It reconstructs causality from the same
safe evidence and proof index through the current tracer in commit
`028fb127928af5e169b5a36f57796f25441ed97e`, which correctly identifies the
first `browser_runtime_observe` failure at decision 5.

The historical receipts remain missing. They are not repaired retroactively.

Deterministic replay identity:

```text
archive_hash =
7ed592866423f533d18334d7d8767fc8e39f202d43767414d1673fff7563c001

safe_evidence_snapshot_hash =
bf19d4be4ea4598953cf6e820570518896d3dffd61c4055c507806b0218f1fd0

browser_proof_index_hash =
0fe12b5a950e5b01c6e11f7a984f06afe444ac88be7f5e9c9068a3634033c3b2

mission_ledger_hash =
4f3b08a05b482eb775a97d0b79c4d965f90df0362014d0e0293104478c542d35

reconstructed_divergence_trace_hash =
e6e819d8a98bc13158c02c89973103ca89910902e4901ab2e438ca5091b180a5
```

Replay metadata is fixed:

```text
replay_mode = artifact_history_reconstruction
history_reconstructed = true
effect_reexecution_attempted = false
reexecuted_actions = false
model_calls_delta = 0
provider_calls_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
```

## New Observe Receipt Proof

A deterministic typed observe failure projects:

```text
operation = real_browser.observe
browser_receipt_ref = readable
product_receipt_ref = readable
typed terminal = typed_observation_failure
before_state_fingerprint = after_state_fingerprint
material_progress = false
telemetry_state = COMPLETE
first_causal_divergence = BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS
```

This distinguishes the new `028fb...` receipt contract from the historical MDN
gap.

## Completion Truth

The visual `COMPLETED` state requires an explicit persisted terminal
`FinalGate_result` with:

```text
accepted = true
```

An action-level FinalGate with only `status=completed` cannot certify the
mission. A terminal verdict claiming completion without an accepting terminal
FinalGate becomes:

```text
presence_state = TELEMETRY_INCOMPLETE
gate_results.finalgate = TELEMETRY_INCOMPLETE
```

The orb cannot become visually successful from model prose or a terminal
status string alone.

## Validation

Python causal and non-regression set:

```text
42/42 passed

test_presence_mission_xray_observer.py
test_browser_observe_receipt_proof_completeness.py
test_browser_receipt_persistence_answer_claim_evidence.py
test_power_cleanup_pack9_product_actionkernel_task_loop.py
test_browser_cortex_progress_repetition_guard.py
test_browser_cortex_divergence_harness.py
```

The Presence test file proves:

```text
historical MDN decision-5 divergence
exactly two historical missing observe receipts
typed observe failure receipt completeness
strict ordering
idempotent deduplication
reconnect after sequence
forbidden-material redaction
terminal FinalGate requirement
observer crash isolation
incremental snapshot observation
append-only safe JSONL journal
standalone observer CLI with zero runtime calls
```

Web validation:

```text
npx tsc --noEmit = PASS
npm run build = PASS
/presence static production route = PASS
/api/presence/events dynamic production route = PASS
```

HTTP behavior:

```text
unconfigured stream
-> 503
-> configured=false
-> no fake events

configured safe test journal
-> configured=true
-> mission_id=live-test
-> sequences=[0,1]
-> schemas=[presence_event_v1,presence_event_v1]
-> can_execute=[false,false]
-> telemetry_incomplete=false
```

## Redaction And Safety

The projection rejects or redacts:

```text
chain_of_thought
private reasoning
raw prompts
raw provider responses
raw browser/DOM material
cookies
credentials
passwords
tokens and secrets
raw exception text
sensitive local paths
```

Provider metadata and normalized decisions are allowlisted. References that
contain a secret or sensitive path become hash-only redacted refs.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/
  presence_observer.py
  presence_observer_cli.py

sentinel-control/services/sentinel-core/
  pyproject.toml

sentinel-control/services/sentinel-core/tests/operator/
  test_presence_mission_xray_observer.py

sentinel-control/apps/web/app/
  page.tsx
  globals.css
  presence/page.tsx
  api/presence/events/route.ts

sentinel-control/apps/web/components/
  presence-shell.tsx

sentinel-control/apps/web/lib/
  presence-protocol.ts
```

## Honest Remaining Boundary

This tranche does not yet:

- launch the SQLite mission;
- call a real provider;
- invoke a real browser;
- auto-start the sidecar from RuntimeHost;
- package the shell in Tauri;
- implement microphone input;
- connect command submission to MissionKernel;
- make Kill executable from the web shell;
- provide a production WebSocket/SSE transport.

The live bridge uses bounded one-second polling over the safe journal. The
future desktop shell can replace this transport without changing
`presence_event_v1`.

## Next Frozen Movement

The observer must be launched as a separate best-effort process before the
already-frozen SQLite mission. The mission loop must not wait for it.

```text
sentinel-presence-observer \
  --snapshot <safe_evidence_snapshot.json> \
  --proof-index <safe_browser_proof_index.json> \
  --mission-ledger <mission_ledger.json> \
  --journal <presence_events.jsonl>
```

Then execute exactly one real run:

```text
SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1
```

The run should produce:

```text
safe evidence snapshot
browser proof index
mission ledger
presence_event_v1 journal
replay archive
Route view
X-Ray view
```

If the observer crashes, the SQLite mission must continue unchanged. If the
mission fails, the UI must expose the first persisted causal divergence rather
than a visual success state.
