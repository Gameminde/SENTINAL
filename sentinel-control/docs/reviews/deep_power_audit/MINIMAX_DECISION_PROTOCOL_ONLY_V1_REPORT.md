# MINIMAX_DECISION_PROTOCOL_ONLY_V1

## Verdict

```text
MINIMAX_DECISION_PROTOCOL_ONLY_V1
= VALID_REAL_PROVIDER_PROTOCOL_REJECTION

provider = nvidia
model = minimaxai/minimax-m3
provider_calls = 1
retries = 0
ProductActionKernel dispatch = 0
Browser launches/actions = 0
external effects = 0
FIXED_PROVEN = 0/65
```

This was a protocol-only probe, separate from C5B. It did not rerun C5B, did
not dispatch the selected decision, did not launch a browser, and did not
modify the parser after observing the result.

## Pre-Call Ledger Correction

Before the provider call, the ledger was corrected to separate historical and
current counters:

```text
pre_sovereign_C5B_attempts = 1
sovereign_C5B_attempts = 1
cumulative_C5B_attempts = 2

pre_sovereign_C5B_provider_calls = 1
sovereign_C5B_provider_calls = 1
cumulative_C5B_provider_calls = 2

standalone_NVIDIA_smoke_calls = 1
alignment_tranche_provider_calls = 0
sovereign_C5B_browser_dispatches = 0
```

The stale `C5B_NOT_RUN` sovereign status was replaced with an explicit
pre-dispatch sovereign attempt status. The earlier
`source_head_before_tranche = 91cad30d...` was recorded as the intermediate
checked-out HEAD after the previous remote checkpoint and before
`d08dc2fe`.

## Probe Contract

The probe used the production NVIDIA adapter, the canonical product model
request builder, the generic transport decoder, and validation against one
bounded synthetic affordance:

```text
protocol_probe.select
```

The capability was not executable by the probe. Its only purpose was to test
MiniMax output against Sentinel's CanonicalDecision boundary. No effect backend
was invoked.

Authorized transport profiles:

```text
strict_json_content
fenced_strict_json
```

Native tool calls were not enabled because the NVIDIA MiniMax catalog entry is
not marked as supporting provider-native tool calls.

## Observed Safe Shape

The real MiniMax response reached the generic decoder and matched:

```text
matched_transport = strict_json_content
json_detected = true
json_root_type = dict
```

The output was rejected because the canonical decision fields were incomplete:

```text
canonical_fields_present = arguments
canonical_fields_missing = capability, operation
typed_rejection_reason = capability_missing
```

No content, raw arguments, raw provider payload, private reasoning or prompt text
was persisted.

Safe artifact:

```text
sentinel-control/docs/reviews/deep_power_audit/MINIMAX_DECISION_PROTOCOL_ONLY_V1/minimax_decision_protocol_only.safe.json
```

## Interpretation

MiniMax did produce parseable JSON under the visible-content transport, but it
did not select the advertised capability and operation. Sentinel correctly
refused to infer an action from partial JSON. This confirms the alignment
doctrine for this run:

```text
model text != action
partial JSON != CanonicalDecision
arguments alone != capability selection
no action invented = true
```

## Next Step

This probe does not authorize C5B V2. A future tranche may improve the prompt or
provider framing for MiniMax, but this report intentionally does not patch the
parser after the failed real response.

```text
C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_SOVEREIGN_V2
= NOT_AUTHORIZED_BY_THIS_REPORT
```

## Validation

```text
probe and ledger counters verified = passed
git diff --check = passed
secret/raw scan over ledger and probe report artifacts = passed
```
