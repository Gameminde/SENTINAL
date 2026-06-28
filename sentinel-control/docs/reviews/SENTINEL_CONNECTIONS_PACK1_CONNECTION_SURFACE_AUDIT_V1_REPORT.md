# SENTINEL CONNECTIONS PACK 1 - CONNECTION SURFACE AUDIT V1

Audit date: 2026-06-28
Repo: `C:\Users\youcefcheriet\sentinal`
Branch: `experimental/real-model-lab-freeze-v1`
Base HEAD after 6C report commit: `9a2fa3b183977f02d8e532b346498a9131cefd09`

## Executive Verdict

`CONNECTION_PACK_1_CONNECTION_SURFACE_AUDIT_V1 = COMPLETE`

No critical uncontrolled connection was found active in the governed product route.

The only real-provider, product-proven execution surface remains the Pack 4A/4B read-only repository route:

```text
CLI cockpit
-> explicit bootstrap
-> MissionExecutionRequest
-> daemon claim
-> coordinator/dispatcher
-> ReadOnlyResearchAdapter
-> ReadOnlyProductionSpineSession
-> governed workspace list/search/read
-> evidence + receipts
-> summary + operator memory candidate
-> FinalGate
-> replay
```

Attempt 6C is accepted as the current proof point: three provider decisions, three material read-only actions, three receipts, mission summary artifact, operator memory candidate artifact, accepted FinalGate, completed MissionKernel, unchanged workspace, and pure material replay.

Pack 1 did not add connection power, call a provider, call external network, push, or start Pack 4B+ implementation.

Final decision:

```text
START_CONNECTION_PACK_2_CONNECTION_MANIFEST_REGISTRY_V1
```

## Evidence Sources Inspected

- Runtime connection registry: `sentinel-control/services/sentinel-core/sentinel/operator/runtime_connections.py`
- Product host/dispatcher/read-only route: `sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py`, `unified_execution_dispatcher.py`, `read_only_operator_spine.py`, `read_only_model_clients.py`
- Provider catalog/client path: `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/provider_profiles.py`, `openai_compatible.py`, `sentinel-control/services/sentinel-core/sentinel/operator/model_client.py`
- Browser organs: `sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_*.py`, `sentinel-control/services/sentinel-core/sentinel/organs/browser/*.py`
- Channel connector: `sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter.py`, `channel_adapter_models.py`, `sentinel-control/services/sentinel-core/sentinel/organs/channels/*.py`
- External API organs: `sentinel-control/services/sentinel-core/sentinel/organs/external_api/*.py`, `sentinel-control/services/sentinel-core/sentinel/agent/organs/external_api_read_write_organ_v1.py`
- Desktop sidecar surfaces: `sentinel-control/services/sentinel-core/sentinel/operator/desktop_sidecar*.py`, `live_desktop_backend*.py`, `sentinel-control/services/sentinel-core/sentinel/organs/desktop/*.py`
- Credential boundary: `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/credentials.py`, `sentinel-control/services/sentinel-core/sentinel/organs/credentials/*.py`
- Skill/plugin fabric: `sentinel-control/services/sentinel-core/sentinel/operator/skill_fabric.py`, `skill_models.py`, `skill_replay.py`
- Daemon/worker orchestration: `sentinel-control/services/sentinel-core/sentinel/operator/daemon*.py`, `worker*.py`
- Voice runtime: `sentinel-control/services/sentinel-core/sentinel/operator/voice*.py`
- External storage/bridges: `sentinel-control/services/sentinel-core/sentinel/shared/db.py`, `sentinel-control/services/sentinel-core/sentinel/cueidea_bridge/client.py`

## Risk Classes

| Class | Meaning |
|---|---|
| C0 | Internal metadata only |
| C1 | Read-only local/workspace |
| C2 | Read-only external inbound |
| C3 | Outbound draft/dry-run only |
| C4 | Controlled external action with explicit approval |
| C5 | High-risk external action, payment, credentials, destructive, privileged |

## Inventory Table

| Surface | Owner file/function | Status | Direction | Data | Credentials | Authority | Can read/write/send/execute | External side effects | Gate/FinalGate | Receipt/evidence | Replay | Kill/revoke | Prompt-injection exposure | Secret-exfil exposure | Risk | Missing controls | Recommended pack |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|
| Model provider catalog and OpenAI-compatible transport | `agent/model_execution/provider_profiles.py`, `openai_compatible.py`, `operator/model_client.py` | implemented | outbound | prompts, visible model output, safe diagnostics | Env names only: `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `SENTINEL_CERT_MODEL_API_KEY`, `DEEPSEEK_API_KEY`, `MISTRAL_API_KEY`, `XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY`, `LMSTUDIO_API_KEY`; endpoint override name `SENTINEL_ALIYUN_DASHSCOPE_BASE_URL` | explicit `UserModelContract`; no provider-native tools by default | read model output only; no tool execution authority | provider call cost/latency only | contract/catalog validation, timeout, no fallback | provider diagnostics and mission events; material receipts belong to downstream route | replay must not call provider | credential env can be removed; no central kill registry yet | high: model output is untrusted | high if prompts or credentials leak; current route redacts | C3 | central connection manifest should bind provider/backend/model/endpoint hashes and allowed payload knobs | CONNECTION_PACK_2 |
| Product read-only repository research | `operator/read_only_operator_spine.py`, `unified_execution_dispatcher.py` | implemented, product-proven | local | workspace directory/file/search observations | none | `MissionAuthorityEnvelope` with `read_only_research`; workspace ref | read yes; write/send/execute no | none outside local workspace | read-only Gate + FinalGate | evidence artifacts, `ReadOnlyActionReceipt`, summary, memory candidate | `ReadOnlyReplayView`, 5Q/6A/6C replay purity verified | authority revocation/expiry checked before dispatch | medium: repo content can be prompt-injection | medium: repo may contain secrets; scanner/bounds reduce but do not remove risk | C1 | add global connection manifest row and standardized secret-policy scan per workspace | CONNECTION_PACK_2 |
| MissionKernel / lifecycle / daemon queue | `operator/kernel.py`, `mission_lifecycle_service.py`, `daemon_runtime.py`, `daemon_store.py`, `runtime_host.py` | implemented | internal | mission events, queue, leases, dead letters | none | MissionAuthorityEnvelope and daemon lease ownership | can transition/dispatch but not an external connector by itself | none | lifecycle status gates | MissionRunStore events, dispatch closeouts | daemon replay builder | queue pause/kill/lease expiry/dead letter | low | low | C0 | include queue/worker surfaces in manifest to avoid hidden dispatch paths | CONNECTION_PACK_2 |
| Worker fleet | `operator/worker_fleet.py`, `worker_models.py`, `worker_replay.py` | implemented/partial | internal | worker tasks, evidence packets | none by default | worker scope/budget/deadline | can orchestrate assigned work; execution depends on injected workers | indirect | task status and merge policies | worker evidence packet refs | worker replay view | cancellation token and killed states | medium if worker input includes untrusted data | medium if worker sees sensitive workspace files | C1/C3 | register as connection-orchestrator with explicit worker capabilities | CONNECTION_PACK_2 |
| Runtime connection registry | `operator/runtime_connections.py` | implemented metadata | internal | connection profiles | none | data-only; cannot enable execution | no execution | none | health gate only | profile hash | export only | none needed | low | low | C0 | extend to full manifest; current registry is not comprehensive | CONNECTION_PACK_2 |
| Browser read-only / observation organs | `agent/organs/browser_readonly_organ_v1.py`, `organs/browser/live_fetch.py`, browser evidence modules | partial/implemented, not current product route | outbound read-only web/browser | page snapshots, DOM, screenshots, HAR metadata | usually none; may inherit browser session in future | browser-scoped authority, allowed domains | read/observe yes; write/send no | web fetch/browser navigation | browser gates/FinalGate classes exist | browser receipts/evidence adapters | browser replay/evidence adapters exist | session controls exist in browser modules; product kill not unified | high: web pages are untrusted instructions | high: pages can contain secret-exfil prompts or hidden fields | C2 | central manifest, domain allowlist, session isolation, browser profile boundary, injection quarantine | CONNECTION_PACK_4 |
| Browser click/type/submit/multitab | `agent/organs/browser_operator_agent_l4_l5_live.py`, `browser_multi_step_task_orchestrator_v1.py`, `browser_form_submit_special_authority_l6.py` | partial/special-authority, not current product route | outbound/bidirectional | user interactions, forms, page state | possible through credential/session broker | browser-scoped explicit authority and L6 special authority | click/type/submit/open tabs | yes, external websites | browser action Gates + FinalGate classes | browser interaction receipts | browser replay studio/organs exist | session manager/kill patterns present, not unified manifest-wide | very high | very high | C4/C5 | require connection manifest, per-domain action policies, dry-run previews, explicit approval, idempotency, transport receipts | CONNECTION_PACK_5/6 |
| Browser login/session/payment/account/download/upload/HAR/JS sandbox | `browser_login_credential_session_broker_l6.py`, `browser_payment_spend_special_authority_l7.py`, `browser_account_creation_special_authority_l7.py`, `browser_download_upload_quarantine_l6.py`, `browser_js_sandbox_special_authority_l6.py`, `browser_network_har_response_quarantine_v1.py` | partial/special-authority/test foundations | bidirectional | credentials/session metadata, payment/account/download/upload/HAR/JS artifacts | credential grants/leases required for login-like flows | L6/L7 special authority models | can execute high-impact browser flows if connected | yes | dedicated FinalGate models | dedicated receipts | replay/quarantine models present | partial per-organ controls | very high | very high | C5 | not connect until identity/credential boundary and external-action receipts are complete | CONNECTION_PACK_3/6 |
| Channel adapters: webhook/email/Slack/Telegram/Discord | `operator/channel_adapter.py`, `channel_adapter_models.py`, `organs/channels/*` | implemented connector runtime, not current product route | inbound/outbound | inbound text/metadata, outbound drafts/sends | credential ref only; no raw values | adapter config, recipient policy, approval policy, send authority | inbound read, draft, send only with injected transport + approval | yes for send | channel send gate + adapter FinalGate | draft/send receipts, delivery refs | channel replay file exists | duplicate-send idempotency; revocation via authority, not unified connector kill | high for inbound prompt injection | high for outbound secret leaks | C2/C3/C4 | manifest all adapters, require explicit transport registration, outbound dry-run approval, recipient provenance, channel-specific credential leases | CONNECTION_PACK_4/5/6 |
| Email-specific surface | channel adapter kind `smtp_email`; channel organ contracts | planned/partial through generic channel | inbound/outbound | messages, recipients, attachments | SMTP credential refs | explicit channel authority and approval | send possible if transport injected | yes | send gate | channel receipts | channel replay | no unified mailbox kill | high | high | C4 | keep draft-only until Pack 5; live send in Pack 6 | CONNECTION_PACK_5/6 |
| Slack/Telegram/Discord-style surface | channel adapter kinds `slack`, `telegram`, `discord` | planned/partial through generic channel | inbound/outbound | messages/channels/threads | platform credential refs | explicit channel authority and approval | send possible if transport injected | yes | send gate | channel receipts | channel replay | no unified app-token revocation yet | high | high | C4 | platform-specific scope/recipient/rate/idempotency policies before live send | CONNECTION_PACK_5/6 |
| External API dry-run planner | `organs/external_api/*.py` | implemented dry-run | outbound | API request plans, cost/privacy/allowlist metadata | credential refs only | dry-run authority | read plan yes; live execute no | no live request | allowlist/dry-run receipt checks | dry-run request receipt | no full product replay yet | none | medium | medium | C3 | promote through manifest and live transport only after approval/receipts | CONNECTION_PACK_5 |
| External API read/write organ | `agent/organs/external_api_read_write_organ_v1.py` | implemented organ, not current product route | outbound | HTTP method/url/body hash/response hash | credential ref id only | allowed methods/domains; mutation authority for non-GET/HEAD | GET/HEAD and optionally mutating methods | yes | `ExternalAPIFinalGate` | `ExternalAPIReceipt` | no product-route replay certification yet | rate ledger only | high | high | C4/C5 | central live connector policy, per-domain budget, idempotency, credential lease and replay certification before product connect | CONNECTION_PACK_6 |
| Desktop/local sidecar | `operator/desktop_sidecar*.py`, `live_desktop_backend*.py`, `organs/desktop/*` | partial/dry-run/fake sidecar foundations | local bidirectional | screen/window/clipboard/filesystem previews, sidecar manifests | sidecar enrollment/credential-like refs | sidecar manifest, allowed apps/windows/paths, special authority | preview; fake sidecar refuses live host actions | local machine side effects if live backend connected | desktop FinalGate adapter/classes | desktop receipts | desktop replay modules exist | sidecar kill switch | very high due screen/clipboard injection | very high due screen/clipboard/files | C4/C5 | keep unconnected until manifest, enrollment, kill switch, human approval and receipt replay certification | CONNECTION_PACK_6 |
| File-system/workspace bridges | `read_only_operator_spine.py`, `agent/organs/reversible_workspace_executor.py`, `local_artifact_executor.py`, `sandbox_shell_code_organ_v1.py` | read-only product implemented; write/shell foundations present but not connected | local | files, patches, shell/code outputs | none by default | workspace path and action-level authority | read-only active; write/shell not product-connected | local mutation possible if future write/shell connected | low-risk/write/shell FinalGate classes exist | read-only receipts; write/shell receipt models | product replay proven only for read-only | revocation via mission authority | medium/high from repo content | high if credentials in workspace | C1 for read-only; C5 for shell/write | do not connect write/shell until separate pack with rollback, diff preview and operator approval | later Pack 4+ not this connection pack |
| Operator memory candidates | `read_only_operator_spine.py` summary/memory candidate artifacts; `workflow_models.py` memory flags | implemented as artifact | internal/local | safe summaries, refs, hashes | none | explicitly data-only, cannot execute/grant authority | read metadata only | none | dispatcher proof verifies hash/ref subsets | summary and memory candidate artifacts | replay verifies summary/memory hashes and refs | no active memory recall kill needed yet | medium if summaries become prompts | medium if summaries contain secrets; current artifact rejects raw secret material | C0/C1 | before active memory use, add tenant, expiry, consent, recall filters, and memory-as-untrusted boundary | CONNECTION_PACK_3/4 |
| Skill/plugin/tool fabric | `operator/skill_fabric.py`, `skill_models.py`, `skill_replay.py`; runtime tool/organ registries | implemented governed fabric/registries | internal to outbound depending skill | skill manifests, requested tools, receipts | depends on requested tools | skill approval and envelope tool subset | execute skill procedure if approved | indirect via requested tools | quarantine/approval and receipt requirements | skill execution receipts | skill replay view | skill revocation | high: skills may encode untrusted procedures | high if skill input includes secrets | C4/C5 | connection manifest must inventory skill requested tools and side effects before execution | CONNECTION_PACK_2/6 |
| Capability ToolRegistry / ExternalOrganRegistry | `capabilities/registry.py`, `organs/registry.py`, `operator/runtime_connections.py` | implemented proposal/contract registries | internal | capability/organ metadata | none | policy-only, registry cannot enable execution | no execution | none | registry policy events | trace events | event replay | not applicable | low | low | C0 | fold into connection manifest as metadata-only surfaces | CONNECTION_PACK_2 |
| Supabase trace repository | `shared/db.py` | partial optional external storage | outbound | trace rows | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` names only | caller-owned | insert/list trace rows | yes, external database | no mission Gate here | repository return values only | no Sentinel replay adapter found | credential revocation external | medium | high if trace rows leak provider/user data | C4 | require manifest, redaction contract, tenant isolation and credential boundary before product use | CONNECTION_PACK_3/6 |
| Cueidea bridge client | `cueidea_bridge/client.py` | partial connector | outbound | project/task payloads | headers passed by caller | caller-owned | GET/POST bridge requests | yes | no product Gate found in client | no receipt found in client | no replay found | no kill found | medium | high depending payload | C4 | put behind external API connector manifest before product use | CONNECTION_PACK_5/6 |
| Voice runtime | `operator/voice_runtime.py`, `voice_models.py`, `voice_replay.py` | implemented/fake backend foundations | bidirectional | audio refs, transcripts, notifications, confirmations | provider contracts may require STT/TTS credentials | voice session/config/confirmation policy | audio input/output, notifications, command envelope | possible through future audio devices/providers | Voice FinalGate | VoiceReceipt | VoiceReplayBuilder | kill word policy | high: ambient voice is untrusted and private | high: speech may contain secrets | C2/C4 | identity/consent/privacy boundary before live voice product route | CONNECTION_PACK_3/4 |
| Financial/spend/trading/account authority | `operator/account_authority_models.py`, spend/trading/capital modules found by event registry | partial/special-authority foundations | outbound | account/payment/trading metadata | credential leases required | explicit special authority | high-risk external actions if connected | yes | specialized FinalGate/receipts | specialized receipts | replay models partial | revocation/approval fields present | very high | very high | C5 | do not connect until after Pack 7 certification and explicit user approvals | later explicit high-risk pack |
| Inbound webhook/server routes | search over `sentinel-control/services/sentinel-core/sentinel` | not found as live web server | inbound | N/A | N/A | N/A | no live server route found | none active | N/A | N/A | N/A | N/A | N/A | N/A | C0 | Generic channel model has webhook kind, but no FastAPI/Flask/APIRouter route was found in this static audit | CONNECTION_PACK_4 if inbound is added |

## Implemented Coverage

### Product-proven

- Read-only repository autopilot with real provider control and receipts.
- Mission lifecycle, immutable request, daemon claim, coordinator decision, dispatcher closeout, proof verification, FinalGate, replay.
- Summary and operator memory candidate artifacts as non-authority read-only products.

### Implemented but not current product route

- Generic channel connector runtime with inbound quarantine, outbound draft, approval, send request, idempotency, receipts and FinalGate.
- External API organ models with dry-run planner and a live-capable organ guarded by methods/domains/mutation authority.
- Desktop sidecar foundations, mostly preview/fake/dry-run with manifest and kill switch controls.
- Skill fabric registry/execution scaffolding with quarantine/approval/revocation/receipt requirements.
- Voice runtime scaffolding and replay models.
- Browser organs spanning read-only observation through L6/L7 special authorities; not connected to the Pack 4 read-only product route.

### Planned / partial / high-risk

- Browser click/submit/login/payment/account flows.
- External channel sends across email/chat platforms.
- Desktop live host control.
- External API mutations with credentials.
- Credential-backed account, payment, trading, or spend actions.

## Credential Boundary Findings

Only credential names were inspected and recorded. No values were printed or persisted by this audit.

Provider catalog credential names:

```text
GROQ_API_KEY
OPENROUTER_API_KEY
NVIDIA_API_KEY
SENTINEL_CERT_MODEL_API_KEY
DEEPSEEK_API_KEY
MISTRAL_API_KEY
XAI_API_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
COHERE_API_KEY
LMSTUDIO_API_KEY
```

Endpoint/config names:

```text
SENTINEL_ALIYUN_DASHSCOPE_BASE_URL
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Findings:

- Provider credentials are process-env based and hashed by source ref in provider handles.
- The Aliyun endpoint override is allowlisted to HTTPS DashScope/MaaS hosts.
- Channel, external API, browser account/login, desktop and voice surfaces use credential refs or contract metadata in their models rather than raw values.
- Credential foundation models block memory/receipt/replay/checkpoint sources from creating credential grants and include revoke/expiry/use-count checks.
- Missing Pack 2/3 control: no single manifest currently binds every connector to identity, tenant, credential lease, allowed destination and replay policy.

## Prompt-Injection Boundary Findings

- The product read-only workspace route treats model decisions as untrusted and passes actions through extraction, validation, Gate and receipts.
- Inbound channel messages are explicitly recorded as untrusted data, with attachment/link quarantine.
- Browser/web/HAR content is inherently untrusted and has multiple receipt renderers that label receipt context as untrusted.
- Workspace files are still a meaningful injection surface because model-led read-only autopilot intentionally feeds safe observation summaries back into later decisions.
- Operator memory candidates remain non-authority artifacts, but active future recall must treat them as untrusted context unless Pack 3/4 memory boundaries are extended.

## Secret-Exfiltration Boundary Findings

- Product route currently avoids raw provider and reasoning persistence.
- Workspace read-only can observe secrets if a user-approved workspace contains them. Current controls are bounded action set, path scope, evidence hashes and safety scans; this is not a substitute for a workspace secret allow/deny policy.
- Browser, desktop and channel surfaces are higher exfiltration risk because they can expose page/session/clipboard/message data to model context.
- External storage and bridge clients need explicit redaction and tenant-bound persistence before product connection.

## Replay / Receipt Gaps

Verified:

- Read-only product route has evidence artifacts, action receipts, FinalGate and replay purity proof from 5Q/6A/6C.
- Daemon, worker, voice, skill and channel replay builders/models exist.

Gaps:

- Browser live, desktop live, external API live, channel live-send, Supabase trace and Cueidea bridge do not have one unified product replay certification story.
- ToolRegistry and ExternalOrganRegistry are metadata-only; they should not be counted as execution replay.
- High-risk special-authority browser/account/payment/trading surfaces need explicit replay certification before connection.

## Kill / Revocation Gaps

Existing controls:

- Mission authority expiry/revocation is checked before dispatch.
- Daemon queue supports pause/kill/dead-letter and lease expiry.
- Worker fleet supports killed state.
- Desktop sidecar has kill switch models.
- Credential grants support expiry/revocation/use-count.
- Skill fabric supports revocation/quarantine.

Gaps:

- No single connection-wide kill switch registry was found across browser, channel, external API, desktop, voice and provider surfaces.
- Live external sends/actions need idempotency plus abort/compensation semantics per connector.

## Recommended Seven-Pack Roadmap

```text
CONNECTION_PACK_2_CONNECTION_MANIFEST_REGISTRY_V1
CONNECTION_PACK_3_IDENTITY_TENANT_CREDENTIAL_BOUNDARY_V1
CONNECTION_PACK_4_INBOUND_READ_ONLY_CONNECTIONS_V1
CONNECTION_PACK_5_OUTBOUND_DRAFT_DRY_RUN_APPROVAL_V1
CONNECTION_PACK_6_CONTROLLED_EXTERNAL_ACTION_RECEIPTS_V1
CONNECTION_PACK_7_CONNECTION_REPLAY_EVAL_FINAL_CERTIFICATION_V1
```

Pack placement notes:

- Pack 2 should create a single manifest for all active/planned connector surfaces, with no execution authority.
- Pack 3 should bind identity, tenant, credentials, env/config sources, revocation and data-retention boundaries.
- Pack 4 should connect only inbound/read-only external data such as web/browser/channel inbound, with quarantine and no outbound send.
- Pack 5 should introduce outbound draft/dry-run approvals, not live sends.
- Pack 6 should add controlled external actions with explicit approval, idempotency, receipts and replay.
- Pack 7 should certify replay/eval/final connection behavior before high-risk expansion.

## No-New-Power Confirmation

- Runtime source changed: no.
- Provider call: no.
- External network call: no.
- Browser/network/email/slack/telegram/discord send action: no.
- Write/shell/browser/network expansion: no.
- Push: no.
- Pack 4B/write/shell/browser/network power: not started.

## Final Decision

```text
START_CONNECTION_PACK_2_CONNECTION_MANIFEST_REGISTRY_V1
```

Reason: no critical uncontrolled connection is active in the product route; the next safest acceleration is a data-only connection manifest registry that makes all future power explicit before any new connector is wired.
