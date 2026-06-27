# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.19 PROVIDER REGRESSION FORENSIC REVIEW V1

Status: AUDIT ONLY  
Created: 2026-06-27  
Repository: `C:\Users\youcefcheriet\sentinal`  
Branch: `experimental/real-model-lab-freeze-v1`  
Current HEAD reviewed: `778bed5693905fe44a3710f2b4e36546e6159bdf`  
Current HEAD subject: `runtime: preserve provider truth for read-only power mode`

## Scope And Constraints

This is a forensic review of the provider regression between earlier Aliyun / DeepSeek product attempts that returned visible model content and later attempts that produced `PROVIDER_ERROR` / provider-blocked envelopes.

This pack did not:

- call a real provider;
- start Pack 4;
- switch provider;
- push;
- modify runtime source code;
- inspect or persist raw provider prompt, response, reasoning, wrapper payload, credentials, Authorization material, endpoint URL, or raw cloned repository contents.

The only output created by this pack is this audit report.

## Executive Verdict

Recommended next action:

```text
RESTORE_ALIYUN_ENDPOINT_CONTRACT_AND_RUN_ONCE
```

Most likely regression point:

```text
effective Aliyun endpoint contract drift between endpoint_hash 96fd... and endpoint_hash 57ea...
```

Confidence:

```text
MEDIUM_HIGH
```

Why confidence is not HIGH:

- older successful-content runs retained endpoint hashes but did not retain the endpoint source label;
- later provider-error runs before Pack 3.18 did not retain HTTP status or provider error code;
- therefore the exact provider-side error class cannot be proven from existing artifacts alone.

Why endpoint drift is still the strongest finding:

- 5F through 5J used endpoint hash `96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497`;
- 5K-B through 5M used endpoint hash `57ea92c0436d5e76e879dbc39a2e41a14abeba344dff778483dd97a24a41b2d8`;
- 5I and 5J prove visible content reached extraction under the earlier hash;
- 5K-B, 5L, and 5M all fail before content extraction under the later hash;
- provider/backend/model remained `aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro`;
- `OpenAICompatibleChatProvider` and provider catalog code did not change between 5J and current HEAD;
- 5J to 5K-B introduced first-receipt runtime behavior only, not read-only provider request-body code.

## Timeline Table

Safe artifact roots inspected:

```text
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5f-20260622-162132
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5g-20260622-152554
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5h-20260622-205406
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5i-20260623-005530
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5j-20260623-092156
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5kb-20260627-142858
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5l-20260627-212152
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5m-20260627-220029
```

| Attempt | Source commit | Provider / backend / model | Endpoint source | Endpoint hash | Provider calls | Read-only calls | Parse stage / safe outcome | Content extraction source | Provider failure | HTTP / provider code retained | Top-level keys | Visible model content reached extraction | Synthetic Sentinel wrapper | Gate reached | Receipt |
|---|---|---|---|---|---:|---:|---|---|---|---|---|---|---|---|---|
| 5F | `b2a5bbd28e72aca59189d61458bc867e19c9d2b9` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | not retained | `96fd7aa...` | not retained; provider reached by accepted run narrative | not retained | `read_only_decision_schema_invalid` | not retained | no retained provider failure | not retained | not retained | likely yes, but insufficient safe diagnostics | no retained evidence | no | no |
| 5G | `1821bbb6c333395a0989f8e040d0fab07d6f7bd6` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | not retained | `96fd7aa...` | not retained | not retained | `model_decision_error`, diagnostics absent | not retained | no retained provider failure | not retained | not retained | unknown | no retained evidence | no | no |
| 5H | `dc48a8a4076ee76f0c99bb276b2258c36453a71a` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | not retained | `96fd7aa...` | not retained | not retained | `read_only_decision_schema_invalid`, then bridge internal closeout | not retained | no retained provider failure | not retained | not retained | unknown | no retained evidence | no | no |
| 5I | `778d72b4e21e5e4c32daf50e2ace9fe1dc3ff3a8` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | not retained | `96fd7aa...` | not retained | not retained | `read_only_decision_validation` | `choices[0].message.content` | false | not retained | `action`, `arguments`, `evidence_refs`, `operator_message`, plus safe/diagnostic keys and one unsafe diagnostic hash key | yes | no | no | no |
| 5J | `c28487ba04f5e14f967e6c91183e4d826256a307` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | not retained | `96fd7aa...` | 1 started | 1 started | extracted decision reached Gate, then `gate_sequence:out_of_scope:escalate` | extraction succeeded enough to build canonical decision | false | not retained | canonical extracted decision summary retained, raw top-level not retained here | yes | no | yes | no |
| 5K-B | `31bf00eb6de02b0cbd89e31895f65f1fd6eb1f83` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | `catalog_default_explicit_process_env` | `57ea92...` | 1 | 1 | `read_only_provider_blocked` | null | true at route level as `PROVIDER_ERROR` wrapper | not retained | `metadata`, `reply` | no | yes | no | no |
| 5L | `1cc9533712d6fed793b3ff05fb056a513aefa69a` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | `explicit_process_env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` | `57ea92...` | 1 | 1 | `read_only_provider_blocked` | null | true at route level as `PROVIDER_ERROR` wrapper | not retained | `metadata`, `reply` | no | yes | no | no |
| 5M | expected `b7ea2ea79801c69f95919fe8bb7dcf98ee46348e`; preflight source not retained | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | `explicit_process_env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` | `57ea92...` | 1 | 1 | `read_only_provider_blocked` | null | true at route level as `PROVIDER_ERROR` wrapper | not retained | `metadata`, `reply` | no | yes | no | no |

Notes:

- 5M source commit is inferred from the accepted Pack 3.17 run context and git history; the 5M preflight file itself did not retain `source_head`.
- 5K-B/5L/5M provider-error envelopes have the same retained provider response hash: `8038cea5eca9016284f3e1af22562d238e832706aa283e5e22c659ef4de99e39`.
- `metadata` / `reply` in 5K-B/5L/5M are Sentinel wrapper keys, not proven model output keys.

## Known Blocker Classification

| Question | Finding |
|---|---|
| Did endpoint/base URL change? | Yes. Effective endpoint hash changed from `96fd...` through 5J to `57ea...` starting 5K-B. |
| Did `model-contract.json` shape change? | Yes, but not in a way that matches the provider-error boundary. Shape changed earlier from no `id` to `id`, then later to a stable attempt-specific id. 5J had the later shape and still got visible/extractable content. |
| Did `provider_id` / `backend_id` / `model_id` change? | No. From 5G onward the selected triple is consistently `aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro`. |
| Did endpoint hash derivation inputs change? | Yes. Hash input changed from an older effective endpoint template to the catalog default endpoint template with `/chat/completions` appended. |
| Did request payload shape change? | Not between 5J and 5K-B for the read-only decision provider client. The 5J to 5K-B source diff changes first-receipt route behavior, not `read_only_model_clients.py`, `model_client.py`, `openai_compatible.py`, or `provider_profiles.py`. |
| Did we add any option that changes provider request body? | First-receipt and low-friction options alter runtime termination/Gate behavior. They are persisted as execution options but are not inserted into `RealModelRequest.request_metadata` for the decision call by `_decision_prompt()` / `_request()`. |
| Did `OpenAICompatibleChatProvider` behavior change? | No code diff from 5F/5J to current HEAD. It still sends a single user message, `stream=false`, temperature `0`, `max_completion_tokens`, optional JSON response format only when metadata requests it and backend supports it, and optional reasoning disable fields from backend profile. |
| Did `OperatorCatalogModelClient` behavior change? | Yes after 5M: current HEAD preserves provider-failure diagnostics if `ProviderModelResponse.error_class` has safe content. That is diagnostics-only for future runs and did not cause 5K-B/5L/5M. |
| Did content extraction change? | Yes across Pack 3.13/3.16 for model dialect/envelope handling, but 5K-B provider-blocked before content extraction. The `metadata/reply` wrapper arrived from Sentinel block handling, not from successful content extraction. |
| Did credential/env source change? | Credential env var remained the product route env. Endpoint env source changed or was repinned: older artifacts retained only hash; later artifacts retained `SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` source and hash `57ea...`. |
| Did low-friction or first-receipt affect provider payload? | No evidence. First-receipt is the only source diff from 5J to 5K-B, but it does not change `ReadOnlyProviderDecisionClient._request()` or the OpenAI-compatible provider body. Low-friction arrived after 5K-B. |
| Did security/sanitization collapse a usable provider response into `PROVIDER_ERROR`? | Not proven. Pre-Pack 3.18 did collapse provider error details into a wrapper, but the provider had already returned `error_class`. No retained evidence proves a usable `choices[0].message.content` was collapsed into `PROVIDER_ERROR`. |

## Endpoint Hash Comparison

Earlier endpoint hash:

```text
96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
```

Later endpoint hash:

```text
57ea92c0436d5e76e879dbc39a2e41a14abeba344dff778483dd97a24a41b2d8
```

Findings:

- `57ea...` matches the catalog default Aliyun-compatible endpoint template after Sentinel appends `/chat/completions`.
- The code path that generates the later endpoint is `provider_profiles._aliyun_dashscope_endpoint()`, which uses `SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` if present, otherwise the catalog default, then appends `/chat/completions` if needed.
- The later 5L/5M preflight explicitly records endpoint source as `explicit_process_env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` and hash `57ea...`.
- The earlier 5F through 5J artifacts retain the endpoint hash `96fd...` but not the endpoint source label, so the exact raw source cannot be recovered from safe artifacts.
- The change happened between 5J (`c28487b...`, endpoint hash `96fd...`) and 5K-B (`31bf00e...`, endpoint hash `57ea...`).
- Source diffs from 5J to 5K-B did not modify provider catalog or OpenAI-compatible provider code, so this is most likely an environment/runbook endpoint contract change rather than a provider adapter code change.

Does it change the actual provider URL/path?

```text
YES, by hash evidence. The raw URL is intentionally not printed here.
```

Can older successful runs be reproduced with the same hash?

```text
NOT PROVEN. The safe artifact set proves the old hash, but not the raw endpoint input needed to recreate it. A future runbook can require the process endpoint hash to equal 96fd... before spending a provider call.
```

## Model Contract Comparison

| Attempt group | Model contract shape | Provider triple | Notes |
|---|---|---|---|
| 5F | shape hash `3fde8a837ad6e69f9ba660954ad28db488ac829e63d2d84c3d6d708b8d88e008`; no `id` field | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | Early explicit bootstrap shape. |
| 5G through 5I | shape hash `149cdf67303ceac495c291b8fa25ca6d85c8b998c37f13b332fb5d6cc0404b9e`; includes `id` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | Visible content still reached extraction in 5I. |
| 5J through 5M | shape hash `9a8dd7d796f6083ffe8438dd3454fecb049ab35969a88b69ae1f78950dcbcb76`; includes stable attempt-specific `id` | Aliyun / OpenAI-compatible / DeepSeek V4 Pro | 5J still reached Gate with visible/extracted content. Therefore this shape is not the provider-error boundary. |

Safe model contract keys retained:

```text
alternative_model_recommendations
capability_profile
context_budget_policy
cost_profile
id (except 5F)
model_override_attempted
quality_expectation
selected_backend_id
selected_model
selected_provider_id
user_selected
```

Read-only decision output budget was stable in the 5J/5K-B/5M contract family:

```text
reserve_output_tokens = 2400
max_decision_frame_tokens = 900
max_evidence_tokens = 3500
```

## Provider Request Shape Comparison

Static code path:

- `ReadOnlyProviderDecisionClient.complete()` builds the prompt and calls `_request()`.
- `_request()` constructs a `RealModelRequest` with `runtime="read_only_research_product"`, provider/backend/model from `UserModelContract`, `estimated_output_tokens=max_output_tokens`, and safe request metadata containing lane, selected provider/backend/model, routing policy, mission/status/observation count/legal actions.
- `OperatorCatalogModelClient.complete()` creates `OpenAICompatibleChatProvider`.
- `OpenAICompatibleChatProvider.execute()` posts to the configured chat-completions endpoint.

Safe request-body shape from current static code:

| Field | Shape |
|---|---|
| `messages` | exactly one message |
| roles used | `user` only |
| message content | prompt text in memory only; not persisted by this audit |
| `model` | `deepseek-v4-pro` |
| streaming | `stream=false` |
| output budget field | `max_completion_tokens` |
| read-only output budget | 2400 tokens in the retained 5J/5K-B/5M model contracts |
| temperature | `0` |
| `top_p` | absent |
| `response_format` / JSON mode | absent for read-only product lane; only added for `runtime=="operator_llm_conversation"` when backend declares JSON mode |
| provider-native tools | absent |
| extra request-body kwargs | no code path found for additional provider-native tools or fallback |
| header names | `Content-Type`, `Authorization` when credential env is present |
| endpoint path hash | `96fd...` through 5J; `57ea...` from 5K-B onward |

5J to 5K-B diff review:

- changed CLI/runtime first-receipt mode;
- added execution option propagation;
- added terminalize-after-first-material-receipt path;
- did not change `read_only_model_clients.py`;
- did not change `model_client.py`;
- did not change `openai_compatible.py`;
- did not change `provider_profiles.py`.

Conclusion:

```text
No provider-request-body regression is proven between 5J and 5K-B.
```

## Static Code Review Findings

### OpenAICompatibleChatProvider

Relevant file:

```text
sentinel-control/services/sentinel-core/sentinel/agent/model_execution/openai_compatible.py
```

Findings:

- `execute()` still validates provider/backend, credential env hash, model support, then posts with `headers` and `_request_body()`.
- `_request_body()` still uses:
  - single `user` message;
  - `stream=false`;
  - `max_completion_tokens`;
  - `temperature=0`;
  - optional `response_format={"type":"json_object"}` only if request metadata asks and backend supports it;
  - optional reasoning control from backend profile.
- No diff exists from 5F/5J to current HEAD for this file.

Provider-error classification:

- Current provider code can preserve HTTP diagnostics through `_http_error_response()` / `_http_error_diagnostic()`.
- Pre-Pack 3.18 product artifacts did not surface those details through the read-only route.

### OperatorCatalogModelClient

Relevant file:

```text
sentinel-control/services/sentinel-core/sentinel/operator/model_client.py
```

Findings:

- JSON response format is only added for `runtime=="operator_llm_conversation"`.
- Read-only product requests use `runtime=="read_only_research_product"`, so JSON mode is not injected by this client.
- Current HEAD added `_provider_failure_payload()` and `_provider_failure_category()` to preserve safe provider failures.
- This current preservation was added after the 5K-B/5L/5M provider-error cluster and cannot be its cause.

### ReadOnlyProviderDecisionClient

Relevant file:

```text
sentinel-control/services/sentinel-core/sentinel/operator/read_only_model_clients.py
```

Findings:

- `_request()` still binds provider/backend/model from the explicit `UserModelContract`.
- It records safe metadata but does not include endpoint URL, credentials, prompt body, raw response, or provider-native tool material.
- Pack 3.13/3.16 introduced extraction/envelope logic for model-dialect tolerance.
- 5K-B/5L/5M did not reach that successful extraction branch; they were blocked at provider-wrapper stage.

### ReadOnlyProductionSpineSession

Relevant file:

```text
sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py
```

Findings:

- Pack 3.15 first-receipt mode changes terminal behavior after a material receipt.
- Pack 3.17 low-friction mode changes Gate handling for approved in-scope read-only actions.
- Neither mode changes the provider HTTP request body.
- 5M had both `low_friction_read_only_power_mode` and `stop_after_first_material_receipt` execution options, but it blocked before Gate and before any material action.

### UnifiedExecutionDispatcher

Relevant file:

```text
sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py
```

Findings:

- First-receipt support adds special proof closeout after receipts.
- It does not execute coordinator/provider logic itself and does not alter model request body.
- In 5K-B/5L/5M it persisted blocked dispatch closeout after the read-only adapter/spine blocked.

## Provider Failure Classification

Likely classification:

```text
endpoint mismatch or endpoint contract drift
```

Alternative classifications not proven:

- `auth/config error`: possible, but credentials were present and earlier/later route used the same credential env. HTTP status not retained.
- `bad request / unsupported parameter`: less likely because 5J to 5K-B did not change provider request-body code and the same OpenAI-compatible provider implementation produced visible content earlier.
- `rate limit`: not supported by retained artifacts.
- `model unavailable`: possible but not supported by retained artifacts.
- `Sentinel wrapper bug`: partially true for loss of details before Pack 3.18, but not proven as the original provider failure cause.
- `security/sanitization collapse`: not supported by retained artifacts; the wrapper represented an already errored provider call.
- `unknown`: still applies to exact HTTP/provider code because it was not retained in 5K-B/5L/5M.

Safe retained error facts:

```text
5K-B / 5L / 5M:
parse_stage = read_only_provider_blocked
top_level_type = dict
top_level_key_names = metadata, reply
provider_response_hash = 8038cea5eca9016284f3e1af22562d238e832706aa283e5e22c659ef4de99e39
FinalGate accepted = false
MissionKernel = blocked
receipts = 0
Gate = not reached
```

Missing facts:

```text
http_status = not retained
provider_error_code = not retained
provider_error_type = not retained
provider_error_message_hash = not retained
provider_error_body_hash = not retained
```

Current HEAD Pack 3.18 is expected to retain these safe fields if the same provider error occurs again.

## Diagnostics-Only Versus Payload-Affecting Changes

Diagnostics-only changes:

- Pack 3.18 provider truth retention in `OperatorCatalogModelClient`;
- read-only provider-failure diagnostic propagation;
- additional safe summary/report files.

Runtime-only changes:

- explicit bootstrap;
- first-receipt mode;
- low-friction read-only Gate path;
- dispatcher proof closeout behavior;
- terminal FinalGate/closeout handling.

Provider payload changes:

- No provider request-body change proven between 5J and 5K-B.
- Prompt changed earlier in Pack 3.10/3.13, but 5I and 5J still produced visible/extractable content after those hardening changes.

Model contract changes:

- Shape/id changes occurred, but 5J used the later model-contract family and still reached extracted decision/Gate.

Endpoint/env changes:

- Strongly evidenced: endpoint hash switched from `96fd...` to `57ea...` at the same point visible content stopped and provider-error wrappers started.

## Proven

- Provider/backend/model identity did not drift.
- OpenAI-compatible provider implementation did not change from 5J to current HEAD.
- Provider catalog implementation did not change from 5J to current HEAD.
- 5J to 5K-B did not change the read-only decision provider-client request construction.
- 5K-B/5L/5M all used endpoint hash `57ea...` and all produced provider-error wrappers.
- Earlier 5I/5J used endpoint hash `96fd...` and visible content reached extraction / Gate.
- Current HEAD has better provider error preservation than the failed attempts had.

## Not Proven

- The raw endpoint that produced `96fd...`.
- The exact HTTP status or provider error code behind 5K-B/5L/5M.
- Whether `57ea...` is intrinsically invalid, regionally wrong, account-incompatible, model-unavailable, or temporarily blocked.
- Whether the same provider call would succeed today if run against `96fd...`.
- Whether Aliyun changed behavior externally between attempts.

## Minimal Next Action

Before any provider switch:

1. Restore the Aliyun endpoint contract used by the earlier successful-content hash.
2. Require preflight to prove:

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
provider truth retention = current Pack 3.18 code active
```

3. Run exactly one provider attempt only after that preflight passes.
4. If the restored endpoint still fails, use Pack 3.18 safe provider fields to classify:

```text
PROVIDER_AUTH_ERROR
PROVIDER_BAD_REQUEST
PROVIDER_RATE_LIMIT
PROVIDER_MODEL_UNAVAILABLE
PROVIDER_TRANSPORT_ERROR
PROVIDER_UNKNOWN_ERROR
```

Recommended next action remains:

```text
RESTORE_ALIYUN_ENDPOINT_CONTRACT_AND_RUN_ONCE
```

## Final Audit Decision

```text
PACK_3_19_PROVIDER_REGRESSION_FORENSIC_REVIEW_V1 = COMPLETED
provider call executed = NO
source code modified = NO
report created = YES
push executed = NO
Pack 4 started = NO
provider switched = NO
recommended_next_action = RESTORE_ALIYUN_ENDPOINT_CONTRACT_AND_RUN_ONCE
```
