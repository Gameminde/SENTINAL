# Sentinel Real-Model Experimental Lane Dirty-Tree Hygiene And Freeze V1

Date: 2026-06-18

Repository: `C:\Users\youcefcheriet\sentinal`

HEAD reviewed: `781e28b945a52fd07e3d638335b496f9c1ee6980`

Origin/main reviewed: `781e28b945a52fd07e3d638335b496f9c1ee6980`

Dirty tree fingerprint, excluding this mutable freeze report to avoid a
self-referential hash:

```text
dc52c236103aaf6389a29707e4da6bcfdcf46ae871a4f7fa8f9c56ab4cdea734
```

This report freezes and classifies the current experimental real-model working
tree before any production-spine integration begins. It does not delete files,
does not commit, does not push, does not run a provider call, and does not mark
any runtime phase locked.

## Decision

```text
REAL_MODEL_EXPERIMENTAL_LANE = FREEZE_FOR_NOW
```

The current experimental lane remains valuable evidence and diagnostic tooling,
but it must not be treated as the production Sentinel operator path.

The next product-power pack should begin only after this hygiene truth is
accepted:

```text
REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1
```

That pack must enter through:

```text
normal operator entry
-> explicit UserModelContract
-> MissionKernel
-> MissionAuthorityEnvelope
-> AgentRuntime / PowerRuntime
-> Gate
-> governed read-only capability
-> certified telemetry
-> receipt
-> FinalGate
-> replay
```

It must not call the experimental self-exploration or certification modules as a
shortcut.

## Classification Legend

```text
PRODUCT_SOURCE          source that touches shared/product runtime surfaces
EXPERIMENTAL_SOURCE     source for the real-model laboratory path
TEST                    test file for product or experimental behavior
EVIDENCE_REPORT         report generated from audits/experiments
HISTORICAL_RUN_SUPPORT  design/report supporting historical reproducibility
OBSOLETE_DUPLICATE      confirmed redundant and safe to remove later
TEMPORARY_ARTIFACT      generated scratch output, not durable evidence
```

No file in this pass is marked `OBSOLETE_DUPLICATE` because no duplicate was
proven safe to remove without a separate review.

## Dirty Tree Manifest

| Status | Classification | Path | SHA-256 |
|---|---|---|---|
| M | PRODUCT_SOURCE | `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/models.py` | `CCAAA94D59C954EB473DC56C96A95ECA86FCC6FD6E054629BDDDE41614BCC744` |
| M | PRODUCT_SOURCE | `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/openai_compatible.py` | `22B475CDC6E7BFEE6BCA2B23185C4A102D49B05791E1BB11AAA4F6ECA2CBCF25` |
| M | TEST | `sentinel-control/services/sentinel-core/tests/test_openai_compatible_provider_base.py` | `26B206A5F7700CE43DB4EA0AF5B868C0C542E730710DD3FE064BE32D4BEE712F` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_M1_CHANNEL_DIAGNOSTIC_REPORT.md` | `03361081F6C9B36757C03CCF5CAE09DD41B5EC4813F7B922357608F456DF01FE` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_M1_SHAPE_DIAGNOSTIC_REPORT.md` | `49B71D5C1696D72BB608E6A95496032AE8E34C5633E53FE90CF74FCEAB568C52` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION_REPORT.md` | `6E41C583AA52BE020486939EAA21A446016EE877EA8FC712D0565A8565BD5B9F` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/OPUS_SENTINEL_REAL_MODEL_HARNESS_V3_1_INDEPENDENT_AUDIT.md` | `0FFEA831B0CE8EB5BB0823571B6358D0CE9C769B43772EF65A82D93B90D9E934` |
| ?? | HISTORICAL_RUN_SUPPORT | `sentinel-control/docs/reviews/REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1_PRE_IMPLEMENTATION_DESIGN.md` | `BB03AAD705BE472584BD924302A7273DD8008E278DAA1DADE65EF5F5BED9FC9C` |
| ?? | HISTORICAL_RUN_SUPPORT | `sentinel-control/docs/reviews/REAL_WORLD_POWER_CONVERGENCE_WAVE_1_REAL_MODEL_AGENT_CERTIFICATION_DESIGN.md` | `58070C344B9E875DE7749808D0DB467D6805BF1C9F8A2F22135631F849455710` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_INTERACTIVE_EXPLORATION_TRAJECTORY_QUALITY_AUDIT_V1.md` | `1A4D0DE258A6E293A470586663F93B90E9619A65724558B9B22BD7A4C1BDDC69` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_PROVIDER_REASONING_VISIBLE_CHANNEL_AUDIT_V1.md` | `A892AF8CC09EA08057119EF53796B46FD46969E066E1EE6944FB2F5C060258F1` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_AND_PREDICTIVE_HARNESS_AUDIT.md` | `49B713DD6FB94B8C2AB3F408FCA9E81E05BA6C307AECA08F387D3357B5B34A2A` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_EXHAUSTIVE_AUDIT_V1.md` | `6AFDF24743B557905FDF9A02A9787BB82F559292E1F37DCB95FFF18E11961FB6` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_EXHAUSTIVE_REMEDIATION_LOCK_REPORT_V1.md` | `639F7FBAF96FEB4915DEFB9AA1B892FDAEF675763FA3C5C9693722A28C803C6E` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_FAILURE_AND_RISK_MATRIX_V1.md` | `9BBF7B3ADE6830F7FFF5B117D46BE43FDB09C1A64E2B8424BA0CE0C11F4FF4F2` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_EXPERIMENTAL_LANE_DIRTY_TREE_HYGIENE_AND_FREEZE_V1.md` | `SELF_REFERENTIAL_SEE_CURRENT_FILE_HASH` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_FAILURE_MODE_MATRIX.md` | `81AD9A6AD5C02C44E32CA16DDF363938146D1337B36DF3C8CDDE4F4EC21E20DA` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_HARNESS_PRE_V3_1_READINESS_REPORT.md` | `C6CF77F23DC73C3BFED99C9B4619574F35396DE9869E8D83D0FC43224266C9C7` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_POWER_TRUTH_RECONCILIATION_V1.md` | `669646FACF3B70DBE1CD202BA59ECEABBDEF263941E6C6634810FF63C3DE181A` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_RUNTIME_CALL_GRAPH_AND_TRUST_BOUNDARIES_V1.md` | `925C703E5CB908E4F73538A11C6D2FAE19AC97D534445759E72ED624574084D6` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_SELF_EXPLORATION_READ_ONLY_V1_REPORT.md` | `5B3CBD682D8E58A5135710F11907414926D2CB065C3C4D1EB01D502C82410D9B` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_TEST_ADEQUACY_AUDIT_V1.md` | `7D7B90F5D78B7277646A87A7F9E4974A5F3ADFFF1BD63C0AF31230A2B6050053` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_RUNTIME_OWNED_MUTATION_INTENT_V1_ARCHITECTURE.md` | `2EC676617ACFC3ECC82D60C6C2596D8802A42EB0991A1BB91A94B0255B4C0F53` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_RUNTIME_OWNED_MUTATION_INTENT_V1_LOCAL_CERTIFICATION_REPORT.md` | `0738FD38B1C3057D4EEDEAF3BC3CEE5D9990806BD069728FB785A125AD77EE4C` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/SENTINEL_WHOLE_SYSTEM_CONVERGENCE_AND_FIRST_RELEASE_READINESS_REVIEW.md` | `286D94EE70350C4DEA34D2F5C5AAFAC0AA0BB99B7387A1669E1E81E9838C5527` |
| ?? | EVIDENCE_REPORT | `sentinel-control/docs/reviews/STAGE_B_SANITIZED_REPORT_CAPTURE_AND_INDEPENDENT_VERIFICATION_V1_REPORT.md` | `B124388F07B661597C742A99E08D604C23BC40ABAFADD2D0BF90BC1534306D72` |
| ?? | EXPERIMENTAL_SOURCE | `sentinel-control/services/sentinel-core/sentinel/operator/interactive_exploration_read_only.py` | `39FC3F5377658210C95146A022B9756097940F1FCBDE74404F3E6D3899675C03` |
| ?? | EXPERIMENTAL_SOURCE | `sentinel-control/services/sentinel-core/sentinel/operator/mutation_artifact_channel.py` | `004EF99FE37FC49C49CCBC21DDD5F55D26ABF72C545D374C0A8145AB82DFD391` |
| ?? | EXPERIMENTAL_SOURCE | `sentinel-control/services/sentinel-core/sentinel/operator/mutation_transport_micro_certification.py` | `CBB5E01C078FCDDB34A5DB99BAD1E5F51DECB883C71EEAA8210A831A295A3855` |
| ?? | EXPERIMENTAL_SOURCE | `sentinel-control/services/sentinel-core/sentinel/operator/real_model_certification.py` | `68E5D28DD7555D6F02B410D785C03BC09788A4BB38372C2C8B72ECB5B551CE49` |
| ?? | EXPERIMENTAL_SOURCE | `sentinel-control/services/sentinel-core/sentinel/operator/self_exploration_read_only.py` | `596D1957E33F692991C529C45E41EC6E57E464307ACE979B9F0DEF3B2A9F8199` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/operator/test_interactive_exploration.py` | `EA45EEB169C5E4D09785918FD08C8005E5C87572C8079A7785808E2346CE344E` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/test_governed_mutation_artifact_channel_v3.py` | `0FBA7572C4DB1A2239484CBD96E53313EFE7763D9E2815EBCF8BBE1855C62076` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/test_mutation_artifact_transport_v2_micro_certification.py` | `79B8745BCA05608815F406A139979CB250910D2E7C2E71CD8180B5694F9B61AE` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/test_real_model_agent_certification_v0.py` | `807300A17A4B8F2C35B4172F510A75CD17A96363939A836B888DE627F70C2BA7` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/test_real_model_behavioral_predictive_harness_audit.py` | `D4F6B6934BF71DEE93A29AA568791C114D6389084F4746E96252CB5C6CEADF3C` |
| ?? | TEST | `sentinel-control/services/sentinel-core/tests/test_self_exploration_read_only_v1.py` | `F54EB4652E9B54F66F90645DA20EB5E2C08B499F28B88388926769DF8BC2D893` |

## Preserve / Delete / Defer Matrix

No file is approved for deletion in this pass. The safe action is to preserve
the experimental state on a dedicated branch, then decide later what can be
promoted to main, archived, or removed.

| Path | Decision | Reason |
|---|---|---|
| `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/models.py` | PRESERVE_AND_REVIEW_BEFORE_MAIN | Product-adjacent provider response metadata; needed by experiments but must be reviewed before main promotion. |
| `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/openai_compatible.py` | PRESERVE_AND_REVIEW_BEFORE_MAIN | Product-adjacent provider adapter changes; safe metadata behavior is useful but requires mainline review. |
| `sentinel-control/services/sentinel-core/tests/test_openai_compatible_provider_base.py` | PRESERVE_AND_REVIEW_BEFORE_MAIN | Regression coverage for provider boundary changes. |
| `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_M1_CHANNEL_DIAGNOSTIC_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical diagnostic evidence. |
| `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_M1_SHAPE_DIAGNOSTIC_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical diagnostic evidence. |
| `sentinel-control/docs/reviews/MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical micro-certification evidence. |
| `sentinel-control/docs/reviews/OPUS_SENTINEL_REAL_MODEL_HARNESS_V3_1_INDEPENDENT_AUDIT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Independent audit evidence. |
| `sentinel-control/docs/reviews/REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1_PRE_IMPLEMENTATION_DESIGN.md` | PRESERVE_AS_NEXT_PACK_DESIGN | Design input for the next production-spine pack; not runtime code. |
| `sentinel-control/docs/reviews/REAL_WORLD_POWER_CONVERGENCE_WAVE_1_REAL_MODEL_AGENT_CERTIFICATION_DESIGN.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical design support for reproducibility. |
| `sentinel-control/docs/reviews/SENTINEL_INTERACTIVE_EXPLORATION_TRAJECTORY_QUALITY_AUDIT_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Audit evidence for trajectory quality. |
| `sentinel-control/docs/reviews/SENTINEL_PROVIDER_REASONING_VISIBLE_CHANNEL_AUDIT_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Provider-boundary evidence. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_AND_PREDICTIVE_HARNESS_AUDIT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical behavioral audit. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_EXHAUSTIVE_AUDIT_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Exhaustive audit record. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_EXHAUSTIVE_REMEDIATION_LOCK_REPORT_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Remediation record for audit truth. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_BEHAVIORAL_FAILURE_AND_RISK_MATRIX_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Risk matrix and finding ledger. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_EXPERIMENTAL_LANE_DIRTY_TREE_HYGIENE_AND_FREEZE_V1.md` | PRESERVE_AS_FREEZE_MANIFEST | This file records the frozen experiment state. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_FAILURE_MODE_MATRIX.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Historical failure taxonomy. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_HARNESS_PRE_V3_1_READINESS_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Pre-V3.1 readiness evidence. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_POWER_TRUTH_RECONCILIATION_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Product-truth reconciliation evidence. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_RUNTIME_CALL_GRAPH_AND_TRUST_BOUNDARIES_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Trust-boundary evidence. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_SELF_EXPLORATION_READ_ONLY_V1_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Self-exploration report. |
| `sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_TEST_ADEQUACY_AUDIT_V1.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Test-quality audit. |
| `sentinel-control/docs/reviews/SENTINEL_RUNTIME_OWNED_MUTATION_INTENT_V1_ARCHITECTURE.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Runtime-owned mutation design evidence. |
| `sentinel-control/docs/reviews/SENTINEL_RUNTIME_OWNED_MUTATION_INTENT_V1_LOCAL_CERTIFICATION_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Local certification evidence. |
| `sentinel-control/docs/reviews/SENTINEL_WHOLE_SYSTEM_CONVERGENCE_AND_FIRST_RELEASE_READINESS_REVIEW.md` | PRESERVE_AS_STRATEGIC_CHECKPOINT | Current global convergence checkpoint. |
| `sentinel-control/docs/reviews/STAGE_B_SANITIZED_REPORT_CAPTURE_AND_INDEPENDENT_VERIFICATION_V1_REPORT.md` | PRESERVE_IN_EXPERIMENTAL_BRANCH | Sanitized Stage B capture evidence. |
| `sentinel-control/services/sentinel-core/sentinel/operator/interactive_exploration_read_only.py` | PRESERVE_AS_EXPERIMENTAL_SOURCE | Laboratory read-only exploration source; not production entry. |
| `sentinel-control/services/sentinel-core/sentinel/operator/mutation_artifact_channel.py` | PRESERVE_AS_EXPERIMENTAL_SOURCE | Laboratory mutation artifact channel; not production entry. |
| `sentinel-control/services/sentinel-core/sentinel/operator/mutation_transport_micro_certification.py` | PRESERVE_AS_EXPERIMENTAL_SOURCE | Laboratory transport micro-certification source. |
| `sentinel-control/services/sentinel-core/sentinel/operator/real_model_certification.py` | PRESERVE_AS_EXPERIMENTAL_SOURCE | Laboratory certification source; not production entry. |
| `sentinel-control/services/sentinel-core/sentinel/operator/self_exploration_read_only.py` | PRESERVE_AS_EXPERIMENTAL_SOURCE | Laboratory self-exploration source; not production entry. |
| `sentinel-control/services/sentinel-core/tests/operator/test_interactive_exploration.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for laboratory interactive exploration. |
| `sentinel-control/services/sentinel-core/tests/test_governed_mutation_artifact_channel_v3.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for laboratory mutation artifact channel. |
| `sentinel-control/services/sentinel-core/tests/test_mutation_artifact_transport_v2_micro_certification.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for transport micro-certification. |
| `sentinel-control/services/sentinel-core/tests/test_real_model_agent_certification_v0.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for real-model certification harness. |
| `sentinel-control/services/sentinel-core/tests/test_real_model_behavioral_predictive_harness_audit.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for behavioral/predictive harness audit. |
| `sentinel-control/services/sentinel-core/tests/test_self_exploration_read_only_v1.py` | PRESERVE_AS_EXPERIMENTAL_TEST | Tests for self-exploration and sanitized Stage B capture. |

## Import And Isolation Findings

Code search over `sentinel-control/services/sentinel-core/sentinel` and
`sentinel-control/services/sentinel-core/tests` shows:

- `interactive_exploration_read_only.py`, `self_exploration_read_only.py`,
  `real_model_certification.py`, `mutation_artifact_channel.py`, and
  `mutation_transport_micro_certification.py` form an experimental cluster.
- Existing product runtime does not appear to import these modules as its normal
  operator entry.
- Tests import these modules directly, which is appropriate for preserving the
  experimental evidence lane.
- The three tracked modified files under `model_execution` are product-adjacent:
  they affect provider response mapping and therefore must be reviewed before
  any clean production commit.

The experimental cluster should be treated as:

```text
preserve as historical evidence and diagnostic lab
do not call directly from the next production-spine pack
do not delete without separate obsolete-duplicate proof
```

## Product-Adjacent Tracked Changes

The tracked provider changes add:

- a memory-only visible-text field on `ProviderModelResponse`, excluded from
  serialized model dumps.
- `finish_reason` and `output_truncated` metadata.
- strict JSON-only behavior for selected requests.
- explicit raw visible text transport for mutation/report laboratory lanes.
- safe finish/error provider-label handling through scanner and hash fallback.
- reasoning presence, hash, character count, and token count metadata.

Classification:

```text
PRODUCT_SOURCE but motivated by experimental provider-boundary evidence
```

Required before a product commit:

- keep local tests green;
- prove no raw visible text, prompt, provider wrapper, reasoning, credential, or
  endpoint secret is serialized;
- confirm these metadata fields do not become authority or correctness proof;
- confirm normal provider execution behavior remains backward-compatible.

## Evidence Reports To Preserve

The untracked reports under `sentinel-control/docs/reviews` should be preserved
because they record failed and successful experiments, audit decisions,
transport diagnostics, report-lane behavior, and the new whole-system
checkpoint.

They are not product capability locks unless explicitly named as lock reports
and supported by canonical truth docs.

## Files Not To Use As Production Entry

The next pack must not use these as a shortcut:

```text
sentinel.operator.real_model_certification
sentinel.operator.self_exploration_read_only
sentinel.operator.interactive_exploration_read_only
sentinel.operator.mutation_transport_micro_certification
```

They may be mined for mechanisms only:

- safe provider metadata;
- safe visible-content hashing;
- evidence catalogs;
- snapshot discipline;
- decision journal shape;
- context compaction;
- report persistence safety.

## No Cleanup Performed

No files were deleted, stashed, reset, or rewritten by this hygiene pass.

Reason: the current tree contains valuable historical failed-run evidence and
experimental diagnostics. Cleanup should happen only after the user approves a
specific preserve/delete list.

## Recommended Next Step

Proceed with a design-only bridge spec for:

```text
REAL_MODEL_READ_ONLY_OPERATOR_PRODUCTION_SPINE_V1
```

Minimum local gates before a real provider call:

```text
fake model through full production spine = PASS
kill/revoke = PASS
deadline = PASS
telemetry disabled = FAIL_CLOSED
wrong authority = BLOCKED
wrong mission/run = BLOCKED
duplicate action = BLOCKED
receipt missing = FinalGate reject
replay = no execution
raw prompt/response/reasoning persistence = 0
```

Only after those gates should one real model read-only mission be attempted.
