# Sentinel Real-Model Runtime Call Graph And Trust Boundaries V1

Status: COMPLETED
Scope: current real-model experimental harnesses and production runtime relationship
No provider call executed during this audit.

## High-Level Classification

The real-model self-exploration and interactive exploration harnesses are experimental evaluator paths. They reuse selected Sentinel components but do not execute through the full production mission proof spine.

## Path Classification

| Path | Classification | Notes |
|---|---|---|
| `OpenAICompatibleChatProvider` | PRODUCTION_RUNTIME_PATH and EXPERIMENTAL_HARNESS_PATH | shared provider adapter |
| `self_exploration_read_only.py` | EXPERIMENTAL_HARNESS_PATH | read-only evaluator, not production mission runtime |
| `interactive_exploration_read_only.py` | EXPERIMENTAL_HARNESS_PATH / PARALLEL_RUNTIME_PATH | own policy, own JSONL trajectory, own evidence catalog |
| `real_model_certification.py` | EXPERIMENTAL_HARNESS_PATH | coding mission certification harness |
| `mutation_artifact_channel.py` | EXPERIMENTAL_HARNESS_PATH | governed artifact channel for certification |
| `MissionKernel` | PRODUCTION_RUNTIME_PATH | not used by self-exploration harness |
| `AgentRuntime` / `PowerRuntime` | PRODUCTION_RUNTIME_PATH | not used for self-exploration read-only tools |
| Gate / receipts / FinalGate | PRODUCTION_RUNTIME_PATH | not invoked by self-exploration harness |

## Self-Exploration Call Path

```text
policy freeze
-> repository snapshot freeze
-> provider smoke checks
-> model decision
-> strict action parser
-> local read-only policy validation
-> snapshot tool execution
-> evidence catalog update
-> trajectory JSONL persistence
-> Stage A visible report
-> Stage B synthesis attempt
-> final_report.json
```

## Production Spine Comparison

| Sentinel guarantee | Self-exploration reuse status |
|---|---|
| UserModelContract | partially reused through explicit provider configuration |
| MissionKernel lifecycle | bypassed |
| MissionAuthorityEnvelope | bypassed |
| AgentRuntime | bypassed |
| PowerRuntime | bypassed |
| Gate | bypassed |
| certified telemetry | bypassed; external JSONL diagnostics only |
| durable receipt ledger | bypassed |
| FinalGate | bypassed |
| replay | bypassed; local trajectory reconstruction only |
| worker fleet | bypassed |
| durable workflow | bypassed |
| memory | bypassed |

## Trust Boundaries

| Boundary | Trusted side | Untrusted side | Control |
|---|---|---|---|
| Provider response | local validator | model/provider output | strict parser and schema |
| Reasoning channel | none | provider reasoning | non-executable, non-persistent |
| Snapshot tools | frozen inventory | repository content | path and policy validation |
| Evidence catalog | local hashes | model claims | evidence refs required |
| Report text | local safe writer | provider visible output | safety scanner and placeholder persistence |
| Stage A vs Stage B | explicit accessibility flags | hidden rubric/truth docs | fixed Stage A indexing |

## Key Risk

The word "governed" can be misleading for these harnesses. Governance here means local experimental policy enforcement, not the full Sentinel mission authority and proof path.

## Remediation Applied

- Added generic depth gate for finish decisions.
- Added duplicate-evidence novelty tracking.
- Removed Stage B truth files from Stage A search indexing.
- Added content safety scanning for snapshot/search exposure.
- Added journal field safety scanning.

## Recommendation

Future reports must label self-exploration as:

```text
LIVE_BOUNDED_EXPERIMENTAL_EVALUATOR
```

not:

```text
PRODUCTION_RUNTIME_CERTIFIED_MISSION
```
