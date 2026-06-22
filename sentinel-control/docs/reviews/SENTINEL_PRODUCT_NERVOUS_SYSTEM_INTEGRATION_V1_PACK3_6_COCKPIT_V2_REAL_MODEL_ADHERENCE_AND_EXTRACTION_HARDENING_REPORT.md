# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK3_6_COCKPIT_V2_REAL_MODEL_ADHERENCE_AND_EXTRACTION_HARDENING_REPORT

## Verdict

```text
PACK_3_6 = LOCALLY_IMPLEMENTED
real_provider_called_during_pack = NO
Pack_4_started = NO
additional_capability_connected = NO
push_performed = NO
```

Pack 3.6 hardens the first-turn governed product cockpit protocol after Attempt 5B.
It does not prove a real-provider mission. It prepares Attempt 5C by improving
V2 adherence pressure and safe diagnostics.

## Attempt 5B Evidence

Attempt 5B reached the real Aliyun-hosted DeepSeek V4 Pro provider through the
product route:

```text
provider = aliyun_dashscope
backend = aliyun_openai_compatible_chat
model = deepseek-v4-pro
provider_calls = 1
mission_created = 0
classification = MISSION_NOT_CREATED
```

The setup blockers from earlier attempts did not recur:

```text
BOM input files = closed
external workspace binding = passed
workspace inside .sentinel-runs = did not recur
legacy_operator_decision_validation = did not recur
cockpit_mission_understanding_v2 route = active
```

The retained safe diagnostics showed:

```text
parse_stage = mission_understanding_v2_validation
protocol_version = cockpit_mission_understanding_v2
missing_required_field_names = ["kind", "protocol_version", "reply"]
top_level_key_names = []
provider_response_hash = ad23f560e307a983f4ca1c9fb51e1a942f834e688961d7805eca0c8cfb93ebfa
```

## What Was Proven

```text
product route reached provider = YES
legacy parser removed from real route = YES
workspace binding blocker fixed = YES
V2 schema validator active = YES
safe failure path used = YES
```

## What Was Not Knowable From Attempt 5B

The old diagnostics could not distinguish with enough precision:

```text
empty visible content
empty JSON object
no JSON object
wrong JSON object
Markdown-fenced JSON
multiple JSON objects
truncated JSON
provider wrapper extraction failure
content extraction source
normalization strategy
```

Pack 3.6 adds those structure-only labels without persisting raw provider material.

## Prompt Hardening

The product V2 prompt now explicitly instructs the provider:

```text
Return exactly one JSON object.
Do not wrap in Markdown.
Do not include explanations outside JSON.
Do not include reasoning.
Do not include legacy OperatorLLMDecisionResult.
Do not include MissionStartProposal.
Do not include OperatorIntent, MissionDraft, or MissionAuthoritySummary.
Do not include workspace, workspace_ref, path, allowed_paths, model_contract_ref,
authority_scope, approval_scope, allowed_actions, budget, credentials, or can_execute.
```

It also includes a minimal V2 object skeleton:

```json
{
  "protocol_version": "cockpit_mission_understanding_v2",
  "kind": "draft_mission",
  "reply": "Mission draft ready for approval.",
  "title": "Repository architecture research",
  "objective": "Map packages, command registration, execution flow, and architecture risks.",
  "requested_capability": "read_only_research",
  "constraints": ["read-only"],
  "expected_artifacts": ["evidence-linked technical report"],
  "clarification_questions": []
}
```

Raw prompts remain in memory only and are not persisted as run artifacts.

## Response Extraction Hardening

The OpenAI-compatible adapter now records safe structure-only metadata for
visible content extraction:

```text
content_extraction_source = choices[0].message.content
content_extraction_error = missing_choices_or_message | message_not_object | content_not_string
visible_content_char_count
visible_content_estimated_tokens
finish_reason
output_truncated
normalization_strategy
json_object_detected
markdown_fence_detected
multiple_json_objects_detected
```

It keeps raw content in memory only and persists only hashes and safe labels.

## JSON Normalization Rules

Accepted deterministic cases:

```text
plain JSON object
single JSON object inside one JSON Markdown fence
single JSON object with harmless surrounding whitespace
```

Rejected cases:

```text
multiple JSON objects
truncated JSON
ambiguous repairs
invented missing fields
model repair calls
fallback model calls
raw reasoning fields
unknown authority/control fields
```

No second provider call is introduced.

## Diagnostic Improvements

V2 failure diagnostics now include:

```text
protocol_version
parse_stage
provider_response_hash
visible_content_length
finish_reason
output_truncated
json_object_detected
top_level_type
top_level_key_names
missing_required_field_names
unknown_field_names
validation_error_codes
validation_error_paths
markdown_fence_detected
multiple_json_objects_detected
normalization_strategy
content_extraction_source
content_extraction_error
```

They do not include:

```text
raw prompt
raw provider response
raw visible output
raw reasoning
field values
mission text
credentials
Authorization
provider wrapper payload
```

## Authority Ownership Preserved

The provider-facing V2 schema remains narrow. The model may propose mission
understanding only.

Still rejected if supplied by the model:

```text
workspace
workspace_ref
path
allowed_paths
model_contract_ref
authority_scope
approval_scope
allowed_actions
budget
credentials
can_execute
MissionStartProposal
MissionDraft
MissionAuthoritySummary
```

Sentinel still owns:

```text
IDs
authority
approval scope intersection
workspace binding
model contract binding
tool/action grants
MissionExecutionRequest
```

## Optional JSON Mode Gating

The OpenAI-compatible request body adds:

```json
{"response_format": {"type": "json_object"}}
```

only when:

```text
request_metadata.response_format_json_object = true
AND backend_profile.supports_json_mode = true
```

No provider is assumed to support JSON mode by compatibility alone. Aliyun
currently remains configured without JSON mode support, so Attempt 5C does not
silently depend on unsupported provider behavior.

## Validation Summary

Focused tests added or extended for:

```text
empty visible content diagnostics
empty JSON object diagnostics
provider wrapper extraction errors
finish_reason length/truncation metadata
catalog-gated JSON response_format
explicit V2 prompt skeleton
forbidden internal/authority prompt fields
product-route V2 failure diagnostics
existing V2 draft and deterministic approval behavior
```

## Remaining Real-Model Risk

Attempt 5C may still fail if the real model:

```text
ignores the V2 skeleton
produces malformed JSON
places useful content in reasoning instead of visible content
returns an empty visible message
returns valid JSON with an unsupported kind or capability
```

If it fails, the new diagnostics should distinguish the failure class without
raw provider material.
