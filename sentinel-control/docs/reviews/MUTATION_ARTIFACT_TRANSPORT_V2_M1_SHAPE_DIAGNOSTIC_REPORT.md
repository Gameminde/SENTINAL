# MUTATION_ARTIFACT_TRANSPORT_V2 M1 Shape Diagnostic Report

Date: 2026-06-16

## Verdict

```text
MUTATION_ARTIFACT_TRANSPORT_V2_M1_SHAPE_DIAGNOSTIC_COMPLETE
```

This diagnostic did not change the transport protocol, did not run C-A1, and did not apply any provider-generated patch.

## Frozen Policy

```text
experiment_version = MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION_V1
policy_hash = dbe79943054e6ec4da161c24d0082b2b7330685e36cbf7fe27ab28dc26ae3a03
provider = alibaba_model_studio_certification
backend = alibaba_model_studio_openai_compatible_chat
model = deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
fallback_AUTO = false
provider_native_tools = false
```

## Run

```text
output_root = sentinel-control/services/sentinel-core/w/mutation_transport_m1_shape_diagnostic/20260616-163548
probe = M1_SMALL_DIFF only
provider_calls = 1
input_tokens = 166
output_tokens = 320
latency_seconds = 7.2583
finish_reason = stop
truncated = false
cost_status = cost_unknown
```

## Safe Shape Diagnostic

```text
transport_prefix_valid = true
visible_payload_total_length = 5
true_newline_count = 0
literal_backslash_n_count = 0
line_ending_style = none
has_old_marker("---") = false
has_new_marker("+++") = false
has_hunk_marker("@@") = false
has_markdown_fence = false
has_prose_before_patch = false
has_prose_after_diff_markers = false
first_line_hash = 8dce33b49f31396a100fb4baf9f8a5dd5d27a4e29d3e244b8eb7b3ae3e619d2c
payload_hash = 8dce33b49f31396a100fb4baf9f8a5dd5d27a4e29d3e244b8eb7b3ae3e619d2c
```

No raw provider response was persisted. The hashes above identify shape equivalence only.

## Corrected Interpretation

The previous label:

```text
PATCH_TRUNCATION
```

was not proven. The provider reported `finish_reason=stop`, `truncated=false`, and the visible output had no real newline, no literal newline sequence, and no diff markers.

The corrected classification is:

```text
PATCH_SHAPE_OR_NEWLINE_ENCODING_FAILURE
```

More specifically:

```text
visible response appears to be PATCH only
```

This rules out, for this run:

```text
literal \n newline encoding failure
provider adapter newline flattening
markdown fence wrapping
prose-before-patch wrapping
parser losing existing diff markers
```

The strongest current classification is:

```text
MODEL_FORMAT_COMPLIANCE / TRANSPORT_FRAMING
```

not:

```text
PROVIDER_ADAPTER_NORMALIZATION
PATCH_PARSER
PATCH_TRUNCATION
```

## Safety

```text
credential persisted = false
raw provider response persisted = false
provider-native tools = false
fallback/AUTO = false
material patch application = false
validated artifact persisted = false
receipt claiming applied mutation = false
FinalGate claiming applied mutation = false
```

## Recommendation

Do not run C-A1.

Do not replace the transport yet.

The next generic fix should target the model-facing transport frame, not the parser:

```text
MUTATION_ARTIFACT_TRANSPORT_V2_M1_GENERIC_FRAMING_FIX
```

Candidate safe directions:

```text
make the response contract include a mandatory END_PATCH sentinel
add an explicit minimal example in the prompt
ask for the diff body before the PATCH header only if the current frame continues to elicit PATCH-only output
compare UNIFIED_DIFF against ANCHORED_REPLACEMENT in separate micro-probes
```

Do not use C-A1 as certification evidence. C-A1 remains a development fixture.
