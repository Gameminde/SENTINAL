# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# Pack 3.8 Cockpit V2 Real-Model Variance And Metadata Filter Fix Report

## Scope

Pack 3.8 addresses the Attempt 5D-B failure where the real provider route
reached Aliyun / DeepSeek and returned a detectable JSON object, but cockpit
V2 validation failed before mission creation.

No provider call is part of this pack. Pack 4 is not started.

## Attempt 5D-B Evidence

Attempt 5D-B safe diagnostics showed:

```text
parse_stage = mission_understanding_v2_validation
protocol_version = cockpit_mission_understanding_v2
json_object_detected = true
top_level_type = dict
top_level_key_names = ["metadata", "reply"]
missing_required_field_names = ["kind", "protocol_version"]
unknown_field_names = ["metadata"]
validation_error_codes = ["extra_forbidden", "missing"]
```

The provider route, Aliyun endpoint, external workspace binding, BOMless input,
and V2 activation were therefore proven. The remaining failure was cockpit V2
schema adherence variance.

## Metadata Origin Finding

```text
metadata_origin = model_output
```

Code tracing shows `OpenAICompatibleChatProvider.map_payload()` parses
`choices[0].message.content` into the visible JSON object, then appends safe
provider metadata under explicit keys such as:

```text
visible_content_char_count
finish_reason
output_truncated
content_extraction_source
normalization_strategy
json_object_detected
provider_response_hash
```

It does not create a top-level `metadata` field. `OperatorCatalogModelClient`
passes `response.content` through as the raw candidate object. Cockpit V2
validation strips only explicit safe provider metadata fields before Pydantic
validation. Therefore a top-level `metadata` key in Attempt 5D-B is treated as
model-owned visible output and remains rejected.

## Implementation

### Prompt Stabilization

The cockpit V2 prompt was changed to positive-schema-first framing:

```text
Return exactly one JSON object.
Allowed top-level keys are exactly:
protocol_version, kind, reply, title, objective, requested_capability,
constraints, expected_artifacts, clarification_questions.
Use this minimal JSON skeleton...
```

The provider-facing instruction now avoids naming legacy internal objects in
the main prompt. It still states the required safety rules:

```text
No Markdown.
No prose outside JSON.
No reasoning.
No authority.
No workspace.
No credentials.
```

The safe frame still tells the model that Sentinel owns authority, workspace
binding, model contract binding, budgets, execution requests, and tool grants.

### Diagnostic Hardening

Cockpit V2 diagnostics now include:

```text
adapter_metadata_filtered = true | false
metadata_origin = model_output | adapter_metadata | unknown
```

Safe provider metadata is still filtered before schema validation. A
model-owned top-level `metadata` field is not filtered and remains an unknown
field.

## Validation Preservation

Pack 3.8 does not weaken validation:

```text
{"reply": "..."} alone is rejected.
model-owned metadata is rejected.
missing kind/protocol_version blocks mission creation.
unknown authority/workspace/model-contract/budget/can_execute fields remain rejected.
Sentinel does not invent missing V2 fields.
No repair call, fallback/AUTO, or alternate model is introduced.
```

## Safe Diagnostic Example

For a model-owned response shape equivalent to:

```text
top_level_key_names = ["metadata", "reply"]
```

the diagnostics are:

```text
parse_stage = mission_understanding_v2_validation
protocol_version = cockpit_mission_understanding_v2
metadata_origin = model_output
adapter_metadata_filtered = false
unknown_field_names = ["metadata"]
missing_required_field_names includes ["kind", "protocol_version"]
```

No raw prompt, raw provider response, raw visible output, raw reasoning,
mission text, credentials, authorization material, or provider wrapper payload
is persisted in this diagnostic.

## Remaining Real-Model Risk

Pack 3.8 prepares the next attempt by reducing prompt-induced variance and
improving diagnostics. It does not prove a real-provider mission. A real model
can still fail to produce the required V2 object, but future failures should
more clearly distinguish:

```text
model-owned wrong object
adapter metadata filtering
empty/missing visible content
provider extraction failure
```
