# Read-Only Operator Terminality And Replay Purity Fix V1

## Verdict

```text
READ_ONLY_OPERATOR_TERMINALITY_AND_REPLAY_PURITY_FIX_V1 = LOCALLY_COMMITTED_CANDIDATE
provider_call = NOT_RUN
push = NOT_PERFORMED_FOR_THIS_FIX
```

This correction pack closes the deterministic review findings left after
`READ_ONLY_OPERATOR_REAL_PROVIDER_FAILURE_HARDENING_V1`.

## Corrections

```text
terminal_ordering = FIXED
pure_replay = FIXED
post_model_checkpoint_before_recheck = FIXED
prebridge_terminal_proof = FIXED
bridge_internal_failure_taxonomy = FIXED
gate_denial_discriminator = FIXED
blocked_finalgate_preserves_prior_receipts = FIXED
```

Terminal failure evidence is now written before the MissionKernel terminal
transition. The MissionKernel `BLOCKED` transition is the final mutation for
internally blocked read-only paths.

Replay reconstruction no longer appends `read_only_spine_replay_built` or
otherwise mutates the replayed timeline. Replay now reports event-count and
mission-status before/after counters.

## Documentation Truth Corrections

```text
safe_target_kind = SYNTACTIC_CLASSIFICATION_ONLY
safe_target_kind_is_verified_filesystem_kind = NO
```

`safe_target_kind` is intentionally safe metadata derived from the canonicalized
decision shape. It is not a verified filesystem existence/type claim.

```text
Attempt_1_original_exact_root_cause = STILL_UNKNOWN
```

Attempt 1 remains a valid failed real-provider attempt. The implemented
hardening closes a generic opaque runtime/bridge failure family, but the exact
original root cause cannot be proven from the retained Attempt 1 artifacts.

```text
remote_truth = e84d32a was already pushed to origin/main and origin/experimental/real-model-lab-freeze-v1
current_reported_remote_head_after_readme_update = 9273927b9a0a5afbcd9fa9745f58673f57a743f5
```

This correction is local-only until separately reviewed.

## Tests

Focused tests were added or tightened for:

```text
MissionKernel terminal event is last for blocked read-only paths
pure replay event/state/write zero-delta
checkpoint persists before kill/revocation/snapshot recheck after model response
prebridge blocks persist terminal proof
bridge internal failure after governed tool attempt is typed
Gate denial has a distinct proof_kind discriminator
blocked FinalGate preserves earlier successful receipt refs
```

## Limits

```text
new_provider_run = NOT_AUTHORIZED
Wave_1_lock = NOT_CHANGED
scores = UNCHANGED
```
