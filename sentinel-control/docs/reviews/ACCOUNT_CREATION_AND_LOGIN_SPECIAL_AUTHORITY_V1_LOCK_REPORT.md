# Account Creation And Login Special Authority V1 Lock Report

Date: 2026-06-13

## Verdict

`ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1` is locked as a governed
Sentinel runtime foundation for account creation and login special authority.

```text
current_phase = ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1_LOCKED
previous_phase = DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1_LOCKED
next_phase = PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1
roadmap_doctrine = product power under provable authority
```

This phase adds scoped account/login planning, CredentialVault lease binding,
human checkpoints, fake/injected sandbox execution, session binding, receipts,
FinalGate records, telemetry, and replay. It does not add universal live
public-site login automation, account farming, CAPTCHA/MFA/KYC/passkey bypass,
payment/spend/trading authority, vendor runtime code, or provider fallback/AUTO.

## Sentinel Components Reused

- `MissionKernel`, `MissionRunStore`, mission records, and mission directory
  persistence.
- `MissionAuthorityEnvelope` as the only authority source.
- `CredentialVaultRuntime` and SecretBroker lease/use flow for credential
  checkout, with ephemeral materialization and no durable raw secret storage.
- Existing telemetry kernel/event/metric vocabulary.
- Existing operator redaction/safety posture and safe persistence patterns.
- Existing receipt/FinalGate/replay doctrine.
- Existing cockpit, daemon, worker, skill, desktop, channel, voice, memory, and
  router surfaces as advisory or guarded context only.

## AgentLab Mechanisms Harvested

AgentLab was used as source-only design material. No vendor runtime, bridge,
dependency, account, or code was copied.

- JARVIS / Microsoft Agent Framework: explicit lifecycle, checkpoints, operator
  visibility, and safe terminal states.
- OpenJarvis / Agent Zero / gptme: operator-facing login/account ergonomics and
  background-task status discipline.
- Hermes / DeerFlow: long-running procedure continuation and escalation
  checkpoints.
- oh-my-pi: hash-anchored evidence, minimized structured outputs, and safe
  result economy.
- OpenClaw: broad skill/tool inspiration, but no plugin authority transfer.

## Standards And Security References

The design report records the normative sources used:

- OAuth 2.0 Authorization Framework, RFC 6749:
  https://www.rfc-editor.org/rfc/rfc6749
- OAuth 2.0 PKCE, RFC 7636:
  https://www.rfc-editor.org/rfc/rfc7636
- OAuth 2.0 for Native Apps, RFC 8252:
  https://www.rfc-editor.org/rfc/rfc8252
- OAuth 2.0 Security Best Current Practice, RFC 9700:
  https://www.rfc-editor.org/rfc/rfc9700
- OpenID Connect Core 1.0:
  https://openid.net/specs/openid-connect-core-1_0.html
- W3C WebAuthn Level 3:
  https://www.w3.org/TR/webauthn-3/
- OWASP Authentication Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP Automated Threats to Web Applications:
  https://owasp.org/www-project-automated-threats-to-web-applications/
- NIST SP 800-63B:
  https://pages.nist.gov/800-63-4/sp800-63b.html

## Runtime Added

Created:

```text
sentinel-control/services/sentinel-core/sentinel/operator/account_authority_models.py
sentinel-control/services/sentinel-core/sentinel/operator/account_authority.py
sentinel-control/services/sentinel-core/sentinel/operator/account_authority_replay.py
sentinel-control/services/sentinel-core/tests/test_account_creation_login_special_authority_v1.py
sentinel-control/docs/reviews/ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1_RESEARCH_AND_DESIGN.md
sentinel-control/docs/reviews/ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1_LOCK_REPORT.md
```

Updated:

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Modes And Maturity

Supported V1 modes:

```text
ACCOUNT_LOGIN_SPECIAL_AUTHORITY
ACCOUNT_CREATION_SPECIAL_AUTHORITY
```

Maturity:

```text
fake_backend = CLOSED
injected_transport = CLOSED
sandbox_account_creation = CLOSED
CredentialVault lease-backed login = CLOSED
universal live public-site login = NOT_STARTED
production OAuth/OIDC token exchange = NOT_STARTED
live WebAuthn/passkey automation = BLOCKED / human checkpoint only
CAPTCHA/MFA/OTP/KYC bypass = BLOCKED
```

## Login Flow Behavior

The login path:

```text
MissionAuthorityEnvelope
-> AccountLoginRequest
-> AccountAuthorityPolicy and safety scan
-> CredentialVault lease binding
-> human checkpoint descriptors when boundaries appear
-> AccountLoginPlan
-> CredentialVault checkout/use receipt
-> session binding
-> account login receipt
-> FinalGate certificate
-> telemetry
-> replay
```

Credential material is checked out through `CredentialVaultRuntime` and is not
persisted by the account authority runtime. The vault mission event metadata was
hardened to store hashes for `consumer_kind` and `purpose`, avoiding persistence
of browser-login surface labels in mission event payloads.

## Account Creation Behavior

The account creation path is sandbox/fake/injected only in V1. It requires:

```text
operator_owned_profile_authorized = true
identity_profile_ref
terms_ack_ref
operator_approval_ref
```

Disposable accounts and sandbox accounts are permitted only when the runtime
configuration explicitly allows them. Mass account creation, fake identity,
terms bypass, CAPTCHA/KYC bypass, ban evasion, and account farming are blocked.

## Boundary Handling

The runtime creates checkpoints instead of bypassing:

```text
MFA
OTP / email / phone verification
CAPTCHA
KYC
WebAuthn / passkey user presence
consent / terms
```

OAuth/OIDC/PKCE descriptors are modeled as safe metadata only. V1 does not
exchange live authorization codes, persist tokens, persist session cookies, or
call provider APIs.

## Integration Boundaries

- Browser/Desktop/Voice/Channel/Worker/Skill/Daemon/Scheduler/Memory/LLM
  surfaces can provide context or proposal records only.
- None of those surfaces may direct-control account/login execution.
- AccountAuthorityRuntime does not expose a direct organ handle, dispatcher
  bypass, provider-native tool path, or browser session manager bypass.
- Payment/spend/trading remains the next phase and was not started.

## Receipts And FinalGate

Receipts contain safe metadata only:

```text
mission_id
authority_envelope_id
credential lease hash
session binding hash
plan hash
policy hash
telemetry refs
status
```

FinalGate records terminal account/login truth such as `completed`, `blocked`,
`checkpoint_required`, `revoked`, and `failed`. FinalGate remains
certification only and cannot become future permission.

## Telemetry And Metrics

Added account authority telemetry source, events, and metrics:

```text
account_authority_config_registered
account_login_plan_created
account_login_checkpoint_created
account_login_completed
account_login_blocked
account_creation_plan_created
account_creation_checkpoint_created
account_creation_completed
account_creation_blocked
account_session_bound
account_flow_finalgate_certified
account_flow_replay_built
```

```text
account_login_success_rate
account_creation_success_rate
account_flow_checkpoint_count
account_flow_block_count
account_credential_lease_bind_count
account_replay_completeness
```

Telemetry is data only. It cannot approve, execute, unlock credentials, grant
authority, or become future permission.

## Replay

`AccountAuthorityReplayBuilder` reconstructs account/login plans, creation
plans, checkpoints, session bindings, receipts, FinalGate refs, and telemetry
refs without re-executing login, creating accounts, materializing credentials,
solving CAPTCHA, bypassing MFA/KYC/passkeys, calling provider APIs, or invoking
browser/desktop actions.

## CodeRabbit Advisory Review

CodeRabbit used: no.

Review source: local availability check.

Summary: `coderabbit` CLI was unavailable in this environment. Per phase
doctrine, no unknown dependency was installed and no token/auth flow was
started. Manual exhaustive audit, targeted tests, regression slices, compile,
and scans were performed instead.

Confirmation: CodeRabbit did not become authority and did not replace Sentinel
tests, audit, or this lock report.

## Exhaustive Audit Findings

| Severity | Finding | File / Surface | Decision | Fix or rationale | Remaining limits |
|---|---|---|---|---|---|
| P0 | Account/Login phase might persist credential-adjacent surface labels through credential vault mission events. | `credential_vault.py` mission event metadata | Accepted and fixed | Replaced `consumer_kind` and `purpose` event values with safe hashes. Existing credential tests still pass. | Event explains via hashes, not raw labels. |
| P0 | Login or account creation without `MissionAuthorityEnvelope`. | `account_authority.py` | Blocked | Runtime validates envelope, mission id, action class, tool scope, and domain/service scope before planning/execution. | Live public-site adapters remain not started. |
| P0 | CAPTCHA/MFA/OTP/KYC/passkey bypass. | `account_authority_models.py`, `account_authority.py` | Blocked | Boundary descriptors produce human checkpoints. Abuse patterns are rejected. | Human operator must complete boundary outside bypass logic. |
| P0 | Raw credential/token/session cookie persistence. | Account authority persistence and receipts | Blocked | Requests are redacted/scanned, receipts reject raw persistence flags, and runtime stores hashes/refs only. | CredentialVault remains the only credential materialization path. |
| P1 | Account creation could drift into fake identity or account farming. | `AccountCreationRequest`, identity policy, safety scan | Blocked | Operator-owned profile, identity ref, terms ack, and approval ref are required. Abuse phrases are rejected. | Production site-specific compliance remains future work. |
| P1 | Advisory surfaces could direct-control account/login. | `request_advisory_surface_account_action` | Blocked | Voice, desktop, channel, skill, worker, daemon, scheduler, memory, and LLM advisory requests fail closed. | Future phases must add explicit authority contracts before any expansion. |
| P1 | Receipt/FinalGate/Memory/Telemetry-as-authority. | Models and tests | Blocked | All model artifacts keep `data_not_authority=true`; tests assert no future permission. | None. |
| P2 | OAuth/OIDC/PKCE could overclaim production support. | Docs and design report | Accepted and bounded | Docs state descriptors only; no live token exchange or provider call in V1. | Production OAuth/OIDC provider integration remains not started. |
| P2 | CodeRabbit advisory unavailable. | Environment | Accepted with rationale | Manual audit performed; no dependency/token install. | Optional future review can run when authenticated tooling exists. |
| P2 | Scan output contains forbidden-word hits. | Modified files | Reviewed | Hits are blocked states, guard names, docs, and test fixtures; no live secret/provider key persistence found. | Keep scans in future phases. |

No open P0, P1, or serious P2 issues remain for this lock.

## Tests And Checks

Targeted and regression tests run with exit code 0:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_account_creation_login_special_authority_v1.py sentinel-control/services/sentinel-core/tests/test_durable_credential_vault_secret_broker_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py sentinel-control/services/sentinel-core/tests/test_live_desktop_operator_backend_system_monitoring_v1.py sentinel-control/services/sentinel-core/tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py sentinel-control/services/sentinel-core/tests/test_real_channel_adapters_v1.py sentinel-control/services/sentinel-core/tests/test_local_model_hardware_and_cost_router_v1.py sentinel-control/services/sentinel-core/tests/test_governed_skill_and_procedure_fabric_v1.py sentinel-control/services/sentinel-core/tests/test_model_amplification_execution_harness_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_production_mission_daemon_and_scheduler_v1.py sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_and_automatic_replan_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_llm_live_operator_conversation_intake_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_mission_kernel_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_power_runtime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_replay_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_product_gauntlet_v0.py sentinel-control/services/sentinel-core/tests/test_sentinel_power_runtime_v0.py sentinel-control/services/sentinel-core/tests/test_agent_runtime.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py sentinel-control/services/sentinel-core/tests/test_agent_evidence_chain.py sentinel-control/services/sentinel-core/tests/test_agent_event_bus.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_agent_runtime_certification.py sentinel-control/services/sentinel-core/tests/test_delegated_action_gate_model_v0.py sentinel-control/services/sentinel-core/tests/test_low_risk_execution_finalgate_receipts.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
```

Scans run on modified files:

```text
secret/raw credential/token/provider key scan
raw prompt/provider response/reasoning scan
fallback/AUTO scan
direct organ bypass scan
payment/trading accidental-start scan
```

Scan result: only blocked-state, guard-name, doc, or test-fixture references
were found; no live secret, provider key, raw prompt, raw provider response,
raw reasoning persistence, direct organ bypass, provider fallback/AUTO path, or
payment/spend/trading implementation was found in the phase files.

## Honest V1 Limits

- No live public-site account provider adapter.
- No production OAuth/OIDC token exchange.
- No WebAuthn/passkey bypass or automation.
- No CAPTCHA solving.
- No KYC bypass.
- No account farming or synthetic identity creation.
- No payment/spend/trading authority.
- No hidden browser/desktop/voice/channel account-control path.
- No provider fallback/AUTO.

## Next Phase

```text
PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1
```

Stop condition honored: payment/spend/trading was not started in this phase.
