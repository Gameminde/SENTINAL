# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.3 COCKPIT MISSION UNDERSTANDING PROTOCOL V2 REPORT

## Verdict

`PACK_3_3_COCKPIT_MISSION_UNDERSTANDING_PROTOCOL_V2` adds a narrow
provider-facing first-turn mission-understanding protocol and keeps Sentinel
responsible for canonical mission objects, authority summaries, approval
scope intersection, and execution state.

This pack does not call a provider, does not retry Attempt 2, does not start
Pack 4, and does not connect any additional capability.

## Attempt 2 Stage Truth

The retained Attempt 2 summary proves:

- provider connectivity worked;
- the corrected two-turn input framing worked;
- no mission was created;
- the blocking stage was cockpit structured-output validation.

The exact original invalid field or shape is still unknown because safe
field-level diagnostics were not retained before this pack. This pack closes
the generic protocol fragility and adds future-safe diagnostics; it does not
claim a guessed DeepSeek-specific root cause.

Current stages after Pack 3.3:

```text
provider response
-> visible content extraction by the provider adapter
-> deterministic JSON extraction/normalization
-> CockpitMissionUnderstandingV2 validation
-> Sentinel-owned canonicalization
-> cockpit state transition
-> deterministic approval start when a valid draft exists
```

## Old Versus New Protocol

Old provider-facing protocol:

```text
Provider was asked to emit broad internal operator objects:
OperatorIntent
MissionDraft
MissionAuthoritySummary
MissionStartProposal
metadata
```

Problem:

```text
The provider had to reproduce internal Sentinel object shape,
including fields Sentinel should own.
```

New provider-facing protocol:

```text
protocol_version = cockpit_mission_understanding_v2

kind:
  draft_mission
  ask_clarification
  greeting
  unknown

fields:
  reply
  title
  objective
  constraints
  expected_artifacts
  requested_capability
  clarification_questions
```

Forbidden from provider output:

```text
mission_id
draft_id
proposal_id
authority_summary
approval_scope
allowed_actions
forbidden_actions
can_execute
can_grant_authority
budgets
paths
credential grants
raw prompt
raw provider response
reasoning
```

## Provider-Facing V2 Example

```json
{
  "protocol_version": "cockpit_mission_understanding_v2",
  "kind": "draft_mission",
  "reply": "Mission draft ready for approval.",
  "title": "Repository architecture research",
  "objective": "Map packages, command registration, execution flow, and architecture risks.",
  "constraints": ["read-only", "no mutation"],
  "expected_artifacts": ["evidence-linked technical report"],
  "requested_capability": "read_only_research",
  "clarification_questions": []
}
```

## Sentinel-Owned Canonicalization

After V2 validation, Sentinel creates:

- `OperatorIntent`;
- `MissionDraft`;
- `MissionAuthoritySummary`.

Sentinel generates all internal IDs. The model cannot create executable
authority, budgets, paths, model routing, tool grants, or authority envelopes.

For `read_only_research`, Sentinel maps the capability to:

```text
list_directory
read_file_segment
search_text
finish_exploration
```

The capability remains advisory until explicit user approval and the existing
authority issuer/lifecycle path create executable authority.

## Authority Derivation

Executable action scope is derived from:

```text
connected capability contract
AND explicit MissionAuthorityApprovalScope
AND policy limits
AND model-requested capability
```

The provider may request `read_only_research`; it does not grant the concrete
actions. The concrete action list is code-owned and then restricted by the
approval scope.

Forbidden actions are unioned from policy and explicit approval restrictions.
The provider cannot reduce the forbidden set.

## Safe Diagnostic Contract

Structured-output failures now return safe structure-only diagnostics:

```json
{
  "protocol_version": "cockpit_mission_understanding_v2",
  "parse_stage": "mission_understanding_v2_validation",
  "provider_response_hash": "<hash>",
  "visible_content_length": null,
  "finish_reason": null,
  "output_truncated": null,
  "json_object_detected": true,
  "top_level_type": "dict",
  "top_level_key_names": ["kind", "protocol_version", "reply", "requested_capability"],
  "missing_required_field_names": ["title"],
  "unknown_field_names": [],
  "validation_error_codes": ["value_error"],
  "validation_error_paths": [],
  "markdown_fence_detected": null,
  "multiple_json_objects_detected": null
}
```

Diagnostics intentionally exclude:

- raw prompt;
- raw provider response;
- raw visible output;
- raw reasoning;
- field values;
- mission text;
- credentials;
- authorization material;
- provider wrapper keys.

## JSON Normalization

Accepted locally without a second provider call:

- plain JSON object;
- one JSON object inside a single Markdown JSON fence;
- one uniquely detectable top-level JSON object with harmless whitespace.

Rejected:

- multiple candidate JSON objects;
- truncated JSON;
- unknown authority/control fields;
- raw `reasoning` field;
- model-supplied executable flags;
- model-supplied budgets, paths, credentials, or authority summaries.

## Approval Behavior

When the first turn stores a valid mission draft and authority summary, an
unambiguous approval phrase such as `start`, `oui commence`, `approve`, or the
long Attempt 2 approval sentence is handled deterministically by the cockpit.

No second provider call is made for approval interpretation.

If an approval phrase arrives without a valid stored draft, the cockpit fails
closed and does not call the provider.

## Scripted Run Outcome Truth

The JSON CLI output now annotates the final turn with a safe
`conversation_outcome`:

```text
conversation_completed
mission_not_created
mission_queued
mission_dispatched
mission_terminal
```

This prevents a zero CLI exit code from being treated as proof that a mission
was created.

## Compatibility Note

Existing deterministic cockpit smoke tests remain supported. A
`legacy_deterministic_scope_compatibility` marker prevents old deterministic
approval-scope smoke tests from accidentally exercising the Pack 3 dispatcher.
This marker is gated by deterministic `non_product_mode` and does not apply to
LLM product mode.

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/operator/structured_output.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/llm_adapter.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/llm_frame.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/prompt_renderer.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/cockpit.py`
- `sentinel-control/services/sentinel-core/sentinel/cli.py`
- `sentinel-control/services/sentinel-core/tests/test_cockpit_mission_understanding_protocol_v2.py`
- `sentinel-control/services/sentinel-core/tests/test_llm_operator_model_client_v0.py`

## Validation Summary

Focused local validation only; no provider call.

```text
Pack 3.3 protocol/model-client focused slice: 19 passed
Cockpit/model-client/CLI product wiring focused slice: 54 passed
```

Additional compile, `python -O`, diff, and safety scan results are recorded in
the final implementation response for this pack.

## Remaining Limits

- Attempt 2 exact original invalid field remains unknown.
- This pack does not prove a new real-provider product mission.
- This pack does not start Pack 4.
- This pack does not add browser, desktop, channels, credentials, finance,
  voice, or memory surfaces.
