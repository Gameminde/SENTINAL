# Sentinel Real-Model Behavioral Failure And Risk Matrix V1

Status: AUDIT_WITH_BOUNDED_REMEDIATION
Scope: current dirty tree plus historical real-model evidence
Repository: C:\Users\youcefcheriet\sentinal
No provider call executed during this audit.

## Severity Summary

| Severity | Count | Status |
|---|---:|---|
| P0 | 0 | none found |
| P1 | 7 | 5 fixed, 2 accepted limitations for next controlled run |
| Serious P2 | 0 | none left open |
| P2 | 4 | 4 fixed, 0 accepted limitations |
| P3/INFO | 2 | documented |

## Finding Ledger

| ID | Title | Severity | Confidence | Status | Lens | File / Surface |
|---|---|---:|---|---|---|---|
| RM-BEH-001 | Stage B can fail empty after smoke success | P1 | High | OBSERVED_CONFIRMED | real-model behavior | .sentinel-runs/self-exploration/20260616-213422/final_report.json |
| RM-BEH-002 | Exploration could finish with shallow coverage | P1 | High | OBSERVED_FIXED | architecture, test quality | sentinel/operator/interactive_exploration_read_only.py |
| RM-BEH-003 | Duplicate evidence counted as productive | P1 | High | OBSERVED_FIXED | trajectory, performance | sentinel/operator/interactive_exploration_read_only.py |
| RM-BEH-004 | Stage A search index exposed Stage B truth files | P1 | High | OBSERVED_FIXED | security, product truth | sentinel/operator/interactive_exploration_read_only.py |
| RM-BEH-005 | Secret-like allowed files could be excerpted/indexed | P1 | High | OBSERVED_FIXED | security, persistence | sentinel/operator/self_exploration_read_only.py; interactive_exploration_read_only.py |
| RM-BEH-006 | Rejected unsafe visible report text could persist | P1 | High | OBSERVED_FIXED | persistence, provider boundary | sentinel/operator/self_exploration_read_only.py |
| RM-BEH-007 | Diagnostic journal strings were not content-scanned | P2 | High | OBSERVED_FIXED | provider boundary | sentinel/operator/interactive_exploration_read_only.py |
| RM-BEH-008 | Provider-controlled metadata labels could persist unsafe text | P2 | Medium | OBSERVED_FIXED | provider boundary | sentinel/agent/model_execution/openai_compatible.py |
| RM-BEH-009 | Interactive exploration bypasses production proof stack | P1 | High | ACCEPTED_LIMITATION | architecture, product truth | self/interactive exploration harnesses |
| RM-BEH-010 | Stage/report calls can exceed exploration deadline | P2 | Medium | OBSERVED_FIXED | runtime, budget | self_exploration_read_only.py |
| RM-BEH-011 | Snapshot unchanged verification is incomplete on failed report paths | P2 | Medium | OBSERVED_FIXED | isolation, restart | self_exploration_read_only.py |
| RM-BEH-012 | Fake micro-cert clients mark `is_real_model=True` | P3 | Medium | ACCEPTED_LIMITATION | test truth | mutation transport micro-cert tests |
| RM-BEH-013 | Stage A report is shallow but worded like architecture review | P3 | High | ACCEPTED_LIMITATION | product truth | stage_a_report.md |

## Detailed Findings

### RM-BEH-001 - Stage B Can Fail Empty After Smoke Success

Severity: P1
Confidence: High
Status: OBSERVED_CONFIRMED
Lens/reviewer: real-model behavior, provider boundary
File/function: `.sentinel-runs/self-exploration/20260616-213422/final_report.json`

Trigger: A 24-turn self-exploration run completed Stage A, passed both smoke checks, then failed final synthesis with `STAGE_B_EMPTY`.

Failure sequence:

1. Exploration consumed 24 turns and 27 model calls.
2. Stage A produced a visible report.
3. Smoke A and Smoke B passed.
4. Stage B produced no accepted visible final report.
5. Run ended failed, but the available archive does not include a Stage B call-result artifact.

Impact: A smoke pass does not predict report-lane success. The harness can spend substantial tokens and still fail at final synthesis.

Safety impact: No evidence of unsafe persistence in the archived run, but lack of Stage B metadata makes root cause classification weaker.

Task-success impact: High. The model can explore and then fail to produce the final artifact.

Performance impact: High. The failed run used 84,612 cumulative tokens and 1,166.96 seconds.

Current mitigation: Final status is failed, not misreported as completed.

Why mitigation is insufficient: The failure is not diagnosable enough from the archived artifacts.

Reproduction evidence: `final_report.json` has `status=failed`, `verdict=STAGE_B_EMPTY`, `stage_b_report_hash=null`.

Required fix: Add and preserve sanitized Stage B call metadata for future runs, and prefer segmented Stage B reconciliation before monolithic synthesis.

Required regression test: Stage B empty, reasoning-only, timeout, and truncated response paths must persist safe diagnostic metadata without raw provider material.

Remaining limit: Not fixed in this audit because no provider call or report-lane rerun was authorized.

### RM-BEH-002 - Exploration Could Finish With Shallow Coverage

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: architecture, test quality
File/function: `interactive_exploration_read_only.py`

Trigger: The latest 24-turn run inspected README, CLI, package entrypoints, and directories, but missed MissionKernel, authority, AgentRuntime, PowerRuntime, telemetry, receipts, FinalGate, replay, workers, daemon, memory, credentials, and finance.

Failure sequence:

1. The model used directory and CLI observations.
2. It attempted a finish action.
3. The old harness rejected the finish for unknown fields, not for insufficient coverage.
4. No generic depth gate existed to require critical categories.

Impact: The agent could produce architecture claims from superficial evidence.

Safety impact: Product-truth overclaim risk.

Task-success impact: Medium to high for audit tasks.

Performance impact: Medium, because turns can be spent on low-value duplicates before finish.

Current mitigation: Added generic depth gate requiring evidence across entrypoint, mission lifecycle, authority path, execution runtime, telemetry, proof, replay/persistence, and one capability path.

Reproduction evidence: New tests fail before the gate and pass after the fix.

Required regression test: `test_finish_requires_generic_depth_gate` and `test_finish_depth_gate_passes_with_generic_evidence_categories`.

Remaining limit: The gate is evidence-category based, not semantic proof of full correctness.

### RM-BEH-003 - Duplicate Evidence Counted As Productive

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: trajectory, performance
File/function: `interactive_exploration_read_only.py`

Trigger: The run recorded 23 evidence entries but only 19 unique content hashes. Exact duplicates were still treated as productive.

Failure sequence:

1. Model repeated the same directory/list/search targets.
2. Harness registered evidence every time.
3. Successful tool call reset nonproductive loop pressure.

Impact: The agent can appear productive while looping.

Safety impact: Low direct safety impact, but high evaluation truth impact.

Task-success impact: Medium.

Performance impact: High. Exact duplicate observations accounted for about 14,573 exploration tokens.

Current mitigation: Evidence entries now carry novelty status. Duplicate content and duplicate target evidence do not automatically reset the nonproductive streak.

Required regression test: `test_duplicate_evidence_is_not_novel_or_productive`.

Remaining limit: Near-duplicate semantic observations are not fully clustered yet.

### RM-BEH-004 - Stage A Search Index Exposed Stage B Truth Files

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: security, product truth
File/function: `SnapshotSearchIndex.__init__`

Trigger: Stage A indexing used `stage_a_accessible or stage_b_accessible`, so files intended only for final truth reconciliation could be searched during exploration.

Failure sequence:

1. Snapshot file had `stage_b_accessible=True`.
2. Search index included it despite `stage_a_accessible=False`.
3. Model could search hidden rubric or final truth material.

Impact: Exploration could be contaminated by answer/rubric leakage.

Safety impact: Medium. It weakens evidence independence.

Task-success impact: High for evaluation validity.

Current mitigation: Search index now indexes only Stage A accessible files.

Required regression test: `test_stage_b_truth_docs_not_indexed_during_exploration`.

Remaining limit: Stage B inputs still need separate explicit handling in future segmented report lanes.

### RM-BEH-005 - Secret-Like Allowed Files Could Be Excerpted/Indexed

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: security, persistence
File/function: `ReadOnlyRepositorySnapshot.freeze`; `SnapshotSearchIndex.__init__`

Trigger: Policy-allowed files were excerpted or indexed without content-level forbidden payload scanning.

Failure sequence:

1. A file path could be allowed by policy.
2. The content itself could contain API-key-like text.
3. Snapshot excerpt or search index could expose that content to the model.

Impact: Provider-visible leakage risk.

Safety impact: High.

Task-success impact: Low direct impact, but high trust impact.

Current mitigation: Snapshot freezing withholds excerpts/symbols for unsafe content, and interactive search indexing skips unsafe file content.

Required regression tests: `test_snapshot_does_not_excerpt_secret_like_allowed_file`; `test_secret_like_allowed_file_not_indexed_or_exposed`.

Remaining limit: This is scanner-based and cannot guarantee perfect secret detection.

### RM-BEH-006 - Rejected Unsafe Visible Report Text Could Persist

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: persistence, provider boundary
File/function: `_write_self_exploration_outputs`

Trigger: A report rejected by safe-output scanning could still be written into local output artifacts.

Failure sequence:

1. Provider returns visible report containing a forbidden payload.
2. Harness detects unsafe report and marks failure.
3. Old persistence path could still store the raw report text.

Impact: Raw unsafe provider-visible text could remain on disk.

Safety impact: High.

Task-success impact: Low, because run was failed, but persistence doctrine was violated.

Current mitigation: Output writer now replaces unsafe visible report text with a safe placeholder and hash metadata.

Required regression test: `test_runner_rejects_secret_bearing_visible_report`.

Remaining limit: Hash metadata remains; it is evidence only and cannot reconstruct content.

### RM-BEH-007 - Diagnostic Journal Strings Were Not Content-Scanned

Severity: P2
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: provider boundary
File/function: `validate_action`

Trigger: Model-supplied journal fields could contain prompt/provider/secret-like material and be persisted in trajectory logs.

Failure sequence:

1. Model returns valid action plus diagnostic journal text.
2. Journal text is truncated and serialized.
3. No scanner check rejects unsafe content.

Impact: Unsafe model-visible material can persist in logs.

Current mitigation: Journal string fields now use the canonical forbidden payload scanner and reject unsafe fields.

Required regression test: `test_raw_provider_material_in_journal_is_rejected`.

Remaining limit: Safe but misleading journal text remains a quality problem, not a persistence problem.

### RM-BEH-008 - Provider-Controlled Metadata Labels Could Persist Unsafe Text

Severity: P2
Confidence: Medium
Status: OBSERVED_FIXED
Lens/reviewer: provider boundary
File/function: `openai_compatible.py`

Trigger: Provider-controlled `finish_reason`, error type, and error code were persisted after truncation but not content safety scanning.

Failure sequence:

1. Provider wrapper includes unsafe label text.
2. Adapter maps or logs the label.
3. Unsafe text can enter diagnostics.

Impact: Low probability, but provider boundary should not trust labels.

Current mitigation: Unsafe labels are replaced by safe labels and SHA-256 hashes.

Required regression tests: `test_provider_redacts_unsafe_finish_reason`; `test_provider_redacts_unsafe_error_type_and_code`.

Remaining limit: Other provider-specific metadata should be reviewed if new fields are added.

### RM-BEH-009 - Interactive Exploration Bypasses Production Proof Stack

Severity: P1
Confidence: High
Status: OBSERVED_FIXED
Lens/reviewer: architecture, product truth
File/function: self-exploration and interactive-exploration harnesses

Trigger: The real-model exploration harness uses provider adapter and local policy, but not the full MissionKernel -> AgentRuntime -> PowerRuntime -> Gate -> receipt -> FinalGate -> replay stack.

Impact: Its reports must not be used as proof that Sentinel production runtime executed a governed mission.

Current mitigation: Reports now classify the path as experimental and partial.

Required fix: If exploration becomes a product feature, route it through the production proof spine or label it permanently as an experimental evaluator.

Remaining limit: Accepted for current read-only audit experiments.

### RM-BEH-010 - Stage/Report Calls Can Exceed Exploration Deadline

Severity: P2
Confidence: Medium
Status: ACCEPTED_LIMITATION
Lens/reviewer: runtime, budget
File/function: report-lane calls

Trigger: Archived run duration is 1,166.96 seconds while policy max duration was 900 seconds.

Impact: Budget enforcement appears incomplete across smoke/report phases.

Current mitigation: The runner now checks the remaining run-duration budget before Stage A and Stage B provider calls.

Fix applied: budget exhaustion is classified as `RUN_DURATION_BUDGET_EXHAUSTED` and prevents the provider call for that stage.

Regression tests: Stage A call is blocked when the deadline is already exhausted; Stage B call is blocked when Stage A consumes the remaining budget.

Remaining limit: Provider-call timeout enforcement inside the provider adapter is still separate from this run-level deadline gate.

### RM-BEH-011 - Snapshot Verification Incomplete On Failed Report Paths

Severity: P2
Confidence: Medium
Status: OBSERVED_FIXED
Lens/reviewer: isolation, restart
File/function: self-exploration failure paths

Trigger: Snapshot unchanged verification was observed on success-oriented paths, but failed report paths can return before full final verification.

Impact: The harness may not always prove local repository immutability after failed report generation.

Current mitigation: Terminal closeout now always runs snapshot verification before writing the report.

Fix applied: `_finalize_self_exploration_report()` records `snapshot.unchanged_after_run`; if the snapshot changed, the terminal report is rewritten as `SNAPSHOT_CHANGED_DURING_RUN`.

Regression test: Stage B provider failure after repository mutation is reclassified from provider/channel failure to snapshot-change failure.

Remaining limit: Exceptions raised before snapshot freeze still cannot verify a snapshot that does not exist.

### RM-BEH-012 - Fake Micro-Cert Clients Mark `is_real_model=True`

Severity: P3
Confidence: Medium
Status: ACCEPTED_LIMITATION
Lens/reviewer: test truth
File/function: mutation transport micro-cert tests

Trigger: Some fake provider clients expose real-model-like flags for harnessing.

Impact: Can confuse reports unless explicitly labeled as fake/injected.

Required fix: Rename flags or add explicit `transport_backend_kind`.

Remaining limit: Not safety critical.

### RM-BEH-013 - Stage A Report Is Shallow But Worded Like Architecture Review

Severity: P3
Confidence: High
Status: ACCEPTED_LIMITATION
Lens/reviewer: product truth
File/function: `stage_a_report.md`

Trigger: Stage A report is mostly based on README/CLI/operator directory evidence.

Impact: Readers may overinterpret it as full architecture audit.

Current mitigation: This audit states exact coverage.

Required fix: Add maturity labels and coverage maps to generated reports.

Remaining limit: Existing historical report is preserved unchanged.
