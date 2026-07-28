# SENTINEL_SQLITE_LIVE_RUN_V3_DEEPSEEK_VS_V4_GLM_COMPARATIVE_REPORT

## Verdict

```text
COMPARISON_SCOPE = SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1
DEEPSEEK_V3 = VALID_FAILED_TRUTHFUL_BLOCKER
GLM_5_2_V4 = VALID_FAILED_TRUTHFUL_BLOCKER
shared_first_causal_blocker = real_browser_search_write_failed
model_winner = none
browser_body_blocker = yes
```

Both models reached the same Sentinel product loop and exposed the same Browser
Organ mechanical failure. This comparison should not be used to rank model
intelligence.

## Runs Compared

| Field | DeepSeek V3 | GLM 5.2 V4 |
| --- | --- | --- |
| Run ID | sqlite_v3_20260728T072411Z | sqlite_v4_glm_5_2_20260728T145552Z |
| Provider | aliyun_dashscope | aliyun_dashscope |
| Backend | aliyun_openai_compatible_chat | aliyun_openai_compatible_chat |
| Model | deepseek-v4-pro | glm-5.2 |
| Browser backend selected | cloak_browser | cloak_browser |
| Browser backend actual | cloak_browser | cloak_browser |
| Session backend kind | cloakbrowser | cloakbrowser |
| Mission verdict | VALID_FAILED_TRUTHFUL_BLOCKER | VALID_FAILED_TRUTHFUL_BLOCKER |
| Blocked reason | BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS | BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS |

## Execution Metrics

| Metric | DeepSeek V3 | GLM 5.2 V4 |
| --- | ---: | ---: |
| Provider decisions | 8 | 8 |
| Material actions consumed | 3 | 3 |
| Events emitted to presence mirror | 58 | 58 |
| Browser action requested events | 5 | 5 |
| Browser action started events | 5 | 5 |
| Failure packet events | 5 | 5 |
| Runtime failure fact events | 5 | 5 |
| FinalGate events | 4 | 4 |
| Material receipt events | 6 | 6 |

## Capability Sequence

DeepSeek V3:

```text
real_browser.search
real_browser.extract_evidence
real_browser.verify_extraction
sentinel_loop.summarize_evidence
real_browser.observe
real_browser.observe
```

GLM 5.2 V4:

```text
real_browser.search
real_browser.extract_evidence
real_browser.verify_extraction
sentinel_loop.summarize_evidence
real_browser.observe
real_browser.observe
```

The two models produced the same high-level product trajectory under the current
model-facing affordance surface.

## Shared Search Actuation Failure

| Search trace field | DeepSeek V3 | GLM 5.2 V4 |
| --- | --- | --- |
| Search status | recoverable_failed | recoverable_failed |
| Typed search outcome | FAILED_RECOVERABLE | FAILED_RECOVERABLE |
| Safe failure code | real_browser_search_write_failed | real_browser_search_write_failed |
| Candidate selected | true | true |
| Ref resolved | true | true |
| Element attached | true | true |
| Element visible | true | true |
| Element enabled | true | true |
| Focus attempted | true | true |
| Focus succeeded | false | false |
| Clear attempted | true | true |
| Clear succeeded | true | true |
| Write attempted | true | true |
| Write method | fill | fill |
| Write succeeded | false | false |
| Readback status | not_attempted | not_attempted |
| Input written | false | false |
| Submission attempted | false | false |
| Request observed | false | false |
| Navigation/state changed | false | false |
| Result region changed | false | false |

This is the core comparison result. Both models asked Sentinel to use the browser
body; the body failed before input write/readback/submission materiality.

## Evidence And Answer Quality

| Field | DeepSeek V3 | GLM 5.2 V4 |
| --- | ---: | ---: |
| Final answer present | false | false |
| Mission objective satisfied | false | false |
| Human-readable public evidence count | 0 | 0 |
| Supported factual claim count | 0 | 0 |
| Unsupported factual claim count | 0 | 0 |

No answer-quality comparison is possible because neither run acquired
human-readable official evidence sufficient to answer the SQLite generated
columns question.

## Proof, Replay And Cleanup

| Field | DeepSeek V3 | GLM 5.2 V4 |
| --- | --- | --- |
| Browser receipts | 5 readable / 0 missing | 5 readable / 0 missing |
| Material browser receipt count | 5 | 5 |
| Proof gate | failed | failed |
| Proof gate failures | evaluator_not_called; proof_index_missing; runtime_provenance_missing_or_unsealed | evaluator_not_called; proof_index_missing; runtime_provenance_missing_or_unsealed |
| Replay reconstructed | true | true |
| Effect reexecution attempted | false | false |
| Reexecuted actions | false | false |
| Model calls delta on replay | 0 | 0 |
| Product dispatch delta on replay | 0 | 0 |
| Receipt writes delta on replay | 0 | 0 |
| Cleanup contexts/process/profile | 0 / 0 / 0 | 0 / 0 / 0 |
| Profile material persisted | false | false |
| Raw provider/browser material persisted | false | false |

## Interpretation

The models are not the active bottleneck in this comparison.

What both runs prove:

```text
real provider/model reached
ProductModelNativeDecisionClient path reached
RuntimeHost/ProductActionKernel path reached
Cloak backend reached
browser receipts persisted and readable in safe evidence
replay no-react held
cleanup held
truthful blocker preserved
```

What neither run proves:

```text
SQLite objective completion
search input write/readback
search submission materiality
human-readable official evidence acquisition
final answer quality
proof infrastructure full pass
```

The next useful engineering target is not prompt tuning and not model switching.
It is:

```text
FIX_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMIT_MATERIALITY_V1
```

The Browser Organ needs a bounded mechanical reflex that can:

```text
resolve fresh control ref
focus reliably
write input
prove normalized readback or justified alternative proof
submit through observed mechanism
observe request/navigation/result-region materiality
return a typed outcome
```

Only after that can DeepSeek versus GLM be compared fairly on strategy,
evidence quality and final answer usefulness.

