# Sentinel Real-Model Failure Mode Matrix

Date: 2026-06-15

Scope: local-only predictive matrix for real-model harness behavior before V3.1.

## Matrix

| Failure mode | Class | Trigger | Runtime behavior after audit | Test coverage |
| --- | --- | --- | --- | --- |
| Narrative response instead of JSON | OBSERVED_FIXED | Provider returns prose. | Rejected as hash-only non-JSON; bounded repair. | `test_structured_output_failures_are_safely_classified` |
| Markdown/prose-wrapped JSON | OBSERVED_FIXED | JSON embedded inside text. | Strict certification request does not extract embedded JSON. | `test_strict_json_request_does_not_extract_material_json_from_prose` |
| Partial/truncated JSON | OBSERVED_FIXED | Provider finish reason `length`. | Classified as `TRUNCATED_JSON`; no material action. | `test_truncated_control_response_is_classified_without_raw_content` |
| Unknown action | GUARDED | Model emits unsupported action. | Rejected before execution. | `test_structured_output_failures_are_safely_classified` |
| Multiple actions | GUARDED | `actions` or `tool_calls`. | Rejected as `MULTIPLE_ACTIONS`. | `test_structured_output_failures_are_safely_classified` |
| Reasoning field | GUARDED | Raw `reasoning` field. | Rejected; hash-only provider metadata allowed. | `test_provider_hash_only_reasoning_metadata_is_ignored_but_raw_reasoning_is_rejected` |
| Action not legal in state | OBSERVED_FIXED | Mutation before observed target. | Blocked as `illegal_in_current_state`; mutation lane not opened. | `test_model_cannot_enter_mutation_lane_before_factually_ready` |
| Premature complete | GUARDED | Model says done without proof. | Oracle rejects; no score evidence. | `test_early_terminal_decision_fails_oracle_when_requirements_remain` |
| Invalid selector then valid repair | GUARDED | First invalid structured response. | One bounded correction; invalid still counted. | `test_one_invalid_output_gets_one_bounded_repair_and_is_still_counted` |
| Two invalid selectors | GUARDED | Second invalid after repair. | Fail closed. | `test_second_consecutive_invalid_output_fails_closed_without_unbounded_retry` |
| Provider timeout/error | OBSERVED_PARTIALLY_FIXED | Provider error before material action. | Bounded retry; state preserved; no duplicated material action. | `test_provider_retry_preserves_state_without_duplicate_material_action` |
| Late response after kill | OBSERVED_FIXED | Mission killed during model call. | Late response discarded; no action execution. | `test_late_model_response_after_kill_cannot_execute_action` |
| Truncated mutation chunk | PREDICTED_HIGH_PROBABILITY_FIXED | Mutation lane output hits ceiling. | Classified as truncation; bounded repair; no apply. | `test_truncated_mutation_chunks_fail_closed_after_bounded_repair` |
| Oversized mutation chunk | GUARDED | Chunk exceeds configured size. | Rejected before visibility. | `test_oversized_and_multi_file_mutations_fail_before_visibility` |
| Missing/out-of-order/duplicate chunk | GUARDED | Bad chunk sequence. | Rejected before assembly. | `test_duplicate_out_of_order_and_wrong_payload_hash_are_rejected` |
| Wrong mission/run/mutation id | GUARDED | Cross-run chunk mix. | Rejected. | `test_chunk_correlation_must_match_validated_proposal` |
| Hash mismatch | GUARDED | Payload hash/base hash mismatch. | Rejected before apply. | `test_wrong_aggregate_hash_and_malformed_diff_are_rejected_without_apply` |
| Stale file after artifact generation | GUARDED | Workspace changes after assembly. | Apply blocked by base hash. | `test_stale_file_after_artifact_generation_blocks_apply` |
| Kill before apply | GUARDED | Mission killed/revoked before material execution. | Apply blocked. | `test_kill_or_revocation_blocks_assembly_and_apply` |
| Kill during apply | OBSERVED_FIXED | Terminal state appears after executor mutates. | Immediate rollback and FinalGate proof. | `test_kill_during_mutation_apply_rolls_back_before_return` |
| Failed verification after apply | PREDICTED_HIGH_PROBABILITY_FIXED | Run ends failed after mutation. | Unverified governed mutations are rolled back. | `test_failed_run_rolls_back_unverified_applied_mutation` |
| Replay re-action | GUARDED | Replay requested after run. | Replay remains evidence-only. | `test_replay_reconstructs_mutation_evidence_without_reapplying` |
| Report counter mismatch | OBSERVED_FIXED | Proof flag counted `any` proof. | Proof complete now requires passed run plus material proof refs. | `test_report_counters_match_retained_run_counters` |
| Prompt injection in source file | GUARDED | Workspace content instructs bypass. | Framed as untrusted data; cannot alter legal actions/state. | `test_workspace_prompt_injection_is_untrusted_data_and_cannot_change_state` |
| Raw provider wrapper persistence | GUARDED | Provider text or wrapper appears. | Only hashes/validated payload retained. | `test_safe_records_never_persist_raw_provider_wrapper_or_payload` |
| Split secret across chunks | GUARDED | Secret assembled from chunks. | Assembly secret scan blocks. | `test_assembly_secret_scan_catches_secret_split_across_chunks` |
| Multi-file atomic mutation | ACCEPTED_LIMITATION | One selector requests multiple targets. | Rejected; no V3 multi-file atomicity. | `test_oversized_and_multi_file_mutations_fail_before_visibility` |
| Process restart during artifact assembly | ACCEPTED_LIMITATION | Harness process dies mid-channel. | In-memory state lost safely; durable resume not implemented. | Documented limitation |
| Concurrent missions same workspace | ACCEPTED_LIMITATION | Two harness runs target same files. | No local harness workspace lease; external daemon/lease system not bound here. | Documented limitation |

## Severity Summary

Open P0: none.

Open P1: none identified for a single controlled V3.1 C-A1 run.

Serious P2 before V3.1: none identified.

Accepted limitations:

- no durable mutation chunk resume after process restart
- no harness-level workspace lease for simultaneous certification missions
- no multi-file atomic mutation in V3.1
- no full AgentRuntime/PowerRuntime unification for internal harness executor calls
- no browser certification in this audit

## V3.1 Frozen Policy Recommendation

```text
experiment_version = V3_1_STATEFUL_STRICT_JSON_GOVERNED_MUTATION
task = C-A1 only for first run
provider/backend/model = explicit pinned UserModelContract
fallback/AUTO = disabled
provider_native_tools = disabled
strict_json_only = true
control_output_tokens = 900
mutation_output_tokens = 2400
provider_retry_budget = 1
structured_repair_budget = 1 per lane
max_steps = 18
max_total_model_calls = 18
max_tool_steps = 16
max_total_tokens = existing certification cap
max_duration = existing certification cap
governed_mutation_channel = enabled
oracle = independent pytest/oracle only
failed_run_rollback = required
stop_after = first fresh V3.1 C-A1 run
```
