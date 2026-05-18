# AgentLab vs Sentinel LLM Backend Matrix

Date: 2026-05-18
Status: Docs-only comparison matrix

## Summary

AgentLab shows what powerful agents already do: call models, route tools, use
memory, run browsers/desktops/channels, manage costs, and persist state.

Sentinel must not copy those runtimes. Sentinel should extract the mechanisms
and rewrite them as:

```text
Brain + Authority + Context Economy + Receipts + FinalGate
```

Pack A is the first backend foundation for that rewrite.

## Matrix

| Source | What it proves | Where it beats Sentinel today | Sentinel advantage | Pack A harvest | Do not copy |
| --- | --- | --- | --- | --- | --- |
| OpenClaw | A broad gateway/action runtime can expose browser, channels, plugins, skills, shell, memory, sub-agents, and approvals through one control plane | Wider live action surface and richer gateway runtime | Stronger authority boundaries, receipts, promotion gates, no vendor bridge | Provider registry discipline, no fake backend tests, explicit execution boundary, future action-kernel compatibility | Dynamic plugin loading, shell as general tool, broad channel/browser mutation, always-allow approvals |
| JARVIS | Sidecar/desktop agents need enrollment, capabilities, RPC, approvals, deferred execution, emergency stop, and audit trail | Stronger live desktop/sidecar and awareness runtime | Stronger proof-first rewrite and centralized MissionAuthorityEnvelope doctrine | Default-off coordinator, receipt shape, deferred execution semantics, provider execution as auditable action | Host shell, all-capability sidecar, arbitrary browser evaluate, screenshot/clipboard ingestion without sanitizer |
| Hermes | Long-lived agents need memory, skills, prompt/context assembly, compression, delegation, and learning loops | More complete memory/skill/compression lifecycle | Memory and skills cannot become authority in Sentinel | Redaction rules, prompt hash discipline, response validation, no raw prompt persistence | Memory as policy, skill prompt injection, fail-open hooks, background mutation |
| OpenJarvis | Model execution needs cost routing, local/cloud discipline, complexity scoring, telemetry, hardware awareness, and sandbox discipline | Stronger model/cost/router telemetry and local/cloud mechanics | User-selected model remains authoritative; optimizer cannot silently override | `ModelCallPlan` to request metadata, provider/backend IDs, token/cost fields, timeout/retry policy | Auto-overriding user model, learned config mutation, open-by-default capability policy |
| TradingAgents | Complex decisions benefit from role topology, debate, risk desk, rating, and outcome memory | Stronger domain role/debate flow | Stronger execution boundary; no real trading from model output | `LLMDecisionResult` can preserve decision/rationale/evidence/confidence without granting action | Real broker bridge, profit guarantee, unchecked leverage, domain result as authority |

## What Sentinel Already Has

Sentinel already has:

```text
MissionAuthorityEnvelope as authority source
Brain L4 internal cognitive modules
LLMDecisionFrame with authority/evidence/tool-surface cards
Prompt render wrapper
ModelCallPlan metadata
ContextCacheKey with mission_hot_hash and authority_hash
FinalGate
EventBus / receipts / replay doctrine
P6R context economy
Browser-LLM ContextPack boundary
organ promotion ladder
```

This is enough to build a model execution foundation without creating a new
organ or copying a vendor runtime.

## What Pack A Adds

Pack A can add:

```text
RealModelRequest
ProviderModelResponse
LLMDecisionResult
ModelExecutionOutcome
ModelTimeoutPolicy
ModelRetryPolicy
ModelExecutionBudgetPolicy
RealModelProvider protocol
ModelProviderRegistry
ProviderCredentialHandle
environment credential resolver shape
request hash
prompt hash metadata
response validator
model execution receipt
default-off coordinator
```

Pack A should not add:

```text
real provider adapter
provider SDK import
network/API call
API key handling beyond env-var resolver shape and missing-env result
AgentRuntime wiring
P6U API read organ
tool execution from model output
authority expansion from model response
```

## Surpass-Not-Imitate Rule

OpenClaw and JARVIS are powerful because they connect models to tools and
machine surfaces. Sentinel should surpass them by ensuring every model output
is:

```text
validated
authority-neutral
receipt-bound
redacted
traceable
non-executing by default
```

Hermes and OpenJarvis are powerful because they preserve context and optimize
model cost. Sentinel should surpass them by ensuring memory, skills, and cost
recommendations do not silently become policy or model override.

TradingAgents is powerful because it structures reasoning. Sentinel should
surpass it by preserving role/debate outputs as evidence summaries and not as
action authority.

## Risk Matrix For Pack A

| Risk | Vendor lesson | Sentinel test implication |
| --- | --- | --- |
| Fake provider accepted | Lab fake runtimes are useful only when labeled fake | Registry rejects fake provider marker |
| Missing credential becomes success | Provider fallbacks can hide failures | Missing env returns `MISSING_CREDENTIAL` and no provider call |
| Prompt body stored | Hermes/OpenClaw prompt/context surfaces get large and sensitive | Serializable metadata contains prompt hash only |
| Model output drives tools | OpenClaw/JARVIS can put tools close to model loops | `LLMDecisionResult` cannot execute tools/organs |
| Silent model override | OpenJarvis-like routers can change model choice | User-selected model remains authoritative |
| Memory/context becomes authority | Hermes shows this is tempting | Validator rejects authority-expanding fields |
| Receipt lacks replay value | Gateway/operator runtimes need audit | Deterministic receipt hash over sanitized metadata |

## Final Comparative Verdict

```text
OpenClaw/JARVIS = stronger live operator surfaces
Hermes/OpenJarvis = stronger implemented memory/model-routing runtime
TradingAgents = stronger specialized debate topology
Sentinel = stronger authority/proof/replay architecture
```

Therefore Pack A is the correct bridge:

```text
not more organs yet
not fake provider
not direct tool execution
first: prove model request/result discipline
```
