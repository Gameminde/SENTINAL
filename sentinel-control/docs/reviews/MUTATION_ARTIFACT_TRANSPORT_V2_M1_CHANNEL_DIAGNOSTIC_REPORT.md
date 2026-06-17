# Mutation Artifact Transport V2 M1 Channel Diagnostic Report

Status: DIAGNOSED

Date: 2026-06-16

Scope: M1 only. No C-A1 mission was run. No mutation was applied. No scores changed.

## Verdict

The M1 failure is classified as:

```text
MODEL_PROVIDER_OUTPUT_CHANNEL_BEHAVIOR
```

The visible provider content was only the transport prefix:

```text
visible_content_char_count = 5
visible_content_estimated_tokens = 2
```

The provider also returned safe metadata showing a separate reasoning channel:

```text
reasoning_present = true
reasoning_char_count = 681
reasoning_hash = 4ede8fd632ccef9a4ab8454ca1659304fdcfd7ce269720b371b0174fae3a4879
reasoning_token_count = null
output_tokens = 165
output_minus_visible_estimated_tokens = 163
finish_reason = stop
truncated = false
```

This means the prior shape diagnosis was correct that the visible payload was not truncated, flattened, Markdown-wrapped, or newline-escaped. The missing patch content appears to have gone into a non-executable reasoning channel rather than the final visible content field.

## Safe Evidence

Output root:

```text
sentinel-control/services/sentinel-core/w/mutation_transport_m1_channel_diagnostic/20260616-165636
```

Policy hash:

```text
dbe79943054e6ec4da161c24d0082b2b7330685e36cbf7fe27ab28dc26ae3a03
```

Provider contract identifiers:

```text
provider_id = alibaba_model_studio_certification
backend_id = alibaba_model_studio_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
```

Shape diagnostic:

```text
total_length = 5
true_newline_count = 0
literal_backslash_n_count = 0
has_old_marker = false
has_new_marker = false
has_hunk_marker = false
has_markdown_fence = false
line_ending_style = none
payload_hash = 8dce33b49f31396a100fb4baf9f8a5dd5d27a4e29d3e244b8eb7b3ae3e619d2c
```

No raw patch, raw reasoning, raw prompt, raw provider response, credential, or authorization header was persisted.

## What This Rules Out

```text
PATCH_TRUNCATION = not supported
PROVIDER_ADAPTER_NEWLINE_FLATTENING = not supported
LITERAL_BACKSLASH_N_ENCODING = not supported
MARKDOWN_FENCE_WRAPPING = not supported
PARSER_BUG = not supported by this evidence
```

## What This Supports

```text
MODEL_PROVIDER_OUTPUT_CHANNEL_BEHAVIOR = supported
```

The model/provider produced useful hidden reasoning-channel material while leaving the visible final content as only:

```text
PATCH
```

Sentinel correctly refused to recover or execute raw reasoning content.

## Strategic Recommendation

Do not run C-A1 yet.

Do not add a blind framing fix yet.

The next generic fix should be provider/model-contract level, not parser level:

```text
1. Add an explicit artifact-lane provider profile option that requests useful output in visible content only, if the provider documents such a control.
2. If supported, disable or minimize reasoning for the mutation artifact lane through explicit pinned contract parameters.
3. Keep the local validator strict and continue rejecting reasoning as non-executable.
4. Re-run exactly one M1 after the provider-channel control is explicit.
5. Only continue to M2-M5 if M1 emits a real visible patch.
```

## Checks Run

```text
py -3.13 -m pytest -q tests/test_openai_compatible_provider_base.py tests/test_mutation_artifact_transport_v2_micro_certification.py
py -3.13 -m pytest -q tests/test_real_model_behavioral_predictive_harness_audit.py tests/test_governed_mutation_artifact_channel_v3.py
py -3.13 -m compileall -q sentinel
git diff --check
```

`git diff --check` reported only CRLF working-copy warnings for already modified tracked files.

## Boundaries Preserved

```text
no C-A1 mission run
no patch applied
no raw reasoning persisted
no raw provider response persisted
no credential persisted
no fallback/AUTO
no provider-native tools
no score change
no commit/push
```
