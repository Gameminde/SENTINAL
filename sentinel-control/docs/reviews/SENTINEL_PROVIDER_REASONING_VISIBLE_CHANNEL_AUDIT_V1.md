# Sentinel Provider Reasoning And Visible Channel Audit V1

Status: COMPLETED_WITH_TARGETED_FIXES
Scope: OpenAI-compatible adapter, real-model harness evidence, self-exploration evidence
No provider call executed during this audit.

## Verdict

Sentinel correctly treats visible content as the only executable/provider-visible result channel and rejects raw reasoning as a non-executable, non-persistent channel. The remaining risk is not that raw reasoning is executed. The remaining risk is that provider wrappers and labels can be strange, sparse, or misleading, so every provider-controlled metadata field must be treated as untrusted.

## Provider Boundary Map

| Surface | Classification | Audit result |
|---|---|---|
| Request messages | provider-boundary | explicit contract path in adapter |
| Model identity | provider-boundary | pinned by contract in real-run configs |
| Visible content | executable only after local validation | required for action/report lanes |
| `reasoning_content` | non-executable | not used as authority or patch content |
| Raw provider wrapper | non-persistent | must remain memory-only |
| `finish_reason` | provider-controlled metadata | fixed to safety-scan before persistence |
| Error `type` / `code` | provider-controlled metadata | fixed to safety-scan before persistence |
| Usage metadata | diagnostic | cost can be unknown; unknown is not free |

## Historical Evidence

The self-exploration run:

- Smoke A passed.
- Smoke B passed.
- Stage A produced visible report.
- Stage B failed empty.
- Archived Stage B metadata is insufficient to determine whether the failure was visible-empty, reasoning-heavy, provider-transport, or report-lane acceptance.

The mutation transport diagnostics indicated a separate channel/shape ambiguity:

- visible payload could be as short as `PATCH`
- output token counts were higher than visible character count
- this could indicate provider/model output-channel behavior
- raw reasoning must not be recovered as patch content

## Fix Applied

`openai_compatible.py` now sanitizes provider-controlled metadata labels:

- unsafe `finish_reason` is replaced with a safe placeholder and hash
- unsafe provider error type/code values are replaced with safe placeholders and hashes
- the hash is evidence only and cannot recreate content

## Required Provider Rules

1. Visible content is required for action/report lanes.
2. Raw reasoning is never executed.
3. Raw reasoning is never persisted.
4. Reasoning hashes cannot become proof of correctness.
5. Empty visible output fails honestly.
6. Provider errors are distinct from protocol errors.
7. Late provider responses must not revive terminal runs.
8. Retried provider responses must not duplicate material actions.

## Tests Added

- `test_provider_redacts_unsafe_finish_reason`
- `test_provider_redacts_unsafe_error_type_and_code`

## Remaining Limits

- The archived Stage B run lacks enough metadata to classify its empty output root cause.
- Future Stage B calls must persist safe metadata: prompt length, input tokens, visible output length, reasoning presence, finish reason, latency, and output tokens.
- A provider/model profile may be needed for lanes where visible content must contain patch artifacts.

## Recommendation

Before any new full exploration run, execute only a Stage B micro-diagnostic against the existing Stage A artifact, preserving safe channel metadata and no raw reasoning.
