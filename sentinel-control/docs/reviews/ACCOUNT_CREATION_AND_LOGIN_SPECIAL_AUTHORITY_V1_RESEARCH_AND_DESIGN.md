# Account Creation And Login Special Authority V1 Research And Design

Date: 2026-06-12

## Verdict

`ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1` must be built as a
Sentinel-native special-authority coordinator over the existing credential,
browser, desktop, voice, channel, telemetry, receipt, FinalGate, and replay
spine.

This phase is not a generic login bot, not account farming, not CAPTCHA
solving, not credential harvesting, and not a new browser runtime. It is a
governed account/login authority layer that can plan, checkpoint, simulate,
and execute fake/injected login or account-creation flows only when an explicit
`MissionAuthorityEnvelope` and scoped CredentialVault lease allow it.

## Official Sources Reviewed

- OAuth 2.0 Authorization Framework, RFC 6749:
  `https://www.rfc-editor.org/rfc/rfc6749`
- OAuth 2.0 PKCE, RFC 7636:
  `https://www.rfc-editor.org/rfc/rfc7636`
- OAuth 2.0 for Native Apps, RFC 8252:
  `https://www.rfc-editor.org/rfc/rfc8252`
- OAuth 2.0 Security Best Current Practice, RFC 9700:
  `https://www.rfc-editor.org/rfc/rfc9700`
- OpenID Connect Core 1.0:
  `https://openid.net/specs/openid-connect-core-1_0.html`
- W3C WebAuthn Level 3:
  `https://www.w3.org/TR/webauthn-3/`
- OWASP Authentication Cheat Sheet:
  `https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html`
- OWASP Session Management Cheat Sheet:
  `https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html`
- OWASP Automated Threats to Web Applications:
  `https://owasp.org/www-project-automated-threats-to-web-applications/`
- NIST SP 800-63B:
  `https://pages.nist.gov/800-63-3/sp800-63b.html`

## Research Answers

### 1. What Is Safe To Automate

Safe V1 automation is limited to:

- plan-only login/account-creation flow modeling;
- sandbox or fake/injected provider flows;
- explicit operator-owned account/profile descriptors;
- credential handle and lease binding through `CredentialVaultRuntime`;
- target planning against existing browser/desktop evidence refs;
- safe receipt, telemetry, FinalGate, memory-summary, and replay records;
- checkpoint creation for human-only boundaries.

Unsafe V1 automation remains blocked:

- account farming, ban evasion, fake identity creation, credential stuffing,
  phishing, cookie theft, session hijacking, CAPTCHA solving, MFA interception,
  KYC bypass, and account takeover;
- live public-site account creation or login without explicit policy and a
  future live adapter lock;
- raw credential, token, cookie, OTP, prompt, provider response, or reasoning
  persistence.

### 2. What Must Not Be Bypassed

CAPTCHA, MFA, WebAuthn/passkey user presence, user verification, consent
screens, email/phone verification, terms acknowledgement, age/KYC checks, and
site anti-abuse boundaries must never be bypassed.

Sentinel V1 behavior is:

```text
detect boundary
-> produce HumanCheckpoint
-> pause/escalate
-> resume only after operator completes the required step
```

No solving service, spoofing, interception, credential replay, or evasion path
is allowed.

### 3. CAPTCHA / MFA / KYC

CAPTCHA is an anti-abuse signal and must be checkpointed. MFA/OTP is a human
verification signal and must be checkpointed. KYC/identity verification is a
special legal/identity boundary and must be checkpointed or blocked unless a
future special-authority lock explicitly supports it.

V1 persists only descriptor/checkpoint metadata:

```text
challenge_kind
provider_hash
checkpoint_id
operator_required = true
bypass_allowed = false
```

### 4. OAuth / OIDC

OAuth/OIDC flows must keep `state`, `nonce`, PKCE verifier/challenge refs,
redirect URI scope, and consent checkpoints as safe metadata. Tokens never
enter logs, memory, telemetry, receipts, replay, voice transcripts, desktop
OCR, or channel text. A token exchange is descriptor/fake-only in V1 unless a
future lock creates a live provider path through the CredentialVault/Broker.

### 5. WebAuthn / Passkeys

WebAuthn/passkey flows require user presence and often user verification.
Sentinel may detect and describe the requirement, but it cannot fake,
delegate, bypass, export private key material, or claim user presence.

V1 response:

```text
passkey_required
-> HumanCheckpoint(user_presence_required=true, user_verification_required=true)
```

### 6. CredentialVault Leases

`CredentialVaultRuntime` provides metadata-only secret registration, scoped
unlock sessions, grants, leases, checkout token refs, use receipts, and
FinalGate certificates. These records are not authority. They are proof that a
secret handle was made available to an approved final consumer under an
existing mission grant.

The account authority runtime must use:

```text
SecretAccessRequest
SecretAccessGrant
SecretAccessLease
SecretCheckoutResult
SecretUseReceipt
```

Raw secret material must never leave the vault/broker contract.

### 7. Browser / Desktop / Voice Requests

Browser and desktop systems may provide target plans and evidence refs through
their existing runtime paths. Voice and channel surfaces may request or confirm
operator intent. None of them can approve credential use or account authority.

Blocked direct surfaces:

```text
voice
desktop
channel
skill
worker
daemon
scheduler
memory
llm
```

Those surfaces may create safe checkpoints only.

### 8. Test / Sandbox / Disposable Accounts

V1 supports sandbox or explicitly disposable operator-owned descriptors only.
Disposable does not mean fake identity, spam, or ban evasion. It means the
operator has declared the account/profile as theirs, within mission scope, for
safe testing.

### 9. V1 And Future

V1:

- models account/login special authority;
- creates safe plans, checkpoints, receipts, FinalGate, telemetry, replay;
- binds CredentialVault leases to final fake/injected consumers;
- supports sandbox/fake account flow tests;
- blocks live public-site automation and abuse boundaries.

Future:

- live provider adapters;
- password-manager or OS-keychain live integrations;
- production OAuth token exchange;
- account lifecycle management;
- enterprise SSO;
- compliant KYC/account creation workflows.

## AgentLab Source-Only Synthesis

| Vendor/system | Architecture pattern | Useful mechanism | Sentinel-native adaptation | Risks | What not to copy | Implementation implication |
| --- | --- | --- | --- | --- | --- | --- |
| OpenClaw | Broad tool/channel/plugin admission | Approval and gateway shapes | Admission as account authority policy/checkpoint | Plugin authority and connector overreach | Runtime bridge, remote plugin execution | Treat every surface as request-only data |
| JARVIS / OpenJarvis | Local assistant and session orchestration | Operator-visible session state | Account session binding with safe receipts | Sidecar/session secrets leaking into runtime | Host authority and hidden routing | Session refs are hashes and leases, not authority |
| Agent Zero | Background task/session ergonomics | Long-lived task visibility | Account flow status and replay | Ambient host reach | Unbounded local control | Daemon can observe, not approve |
| gptme | Local config/env handling | Explicit local config ergonomics | Explicit policy and descriptor records | Env/secret leakage | Raw env/key propagation | No provider key or token persistence |
| Hermes / DeerFlow | Workflow credential propagation | Checkpoints in long workflows | HumanCheckpoint and policy-bound resume | Memory or worker carrying credentials | Credential pools and implicit propagation | Workers get refs only, no materialization |
| UI-TARS | Visual login/account flow reasoning | Target grounding and uncertainty | Browser/desktop evidence refs and ambiguity checkpoints | Visual action mistaken for permission | Direct screenshot-to-action | Grounding is not execution |
| Letta / memory agents | Durable memory | Useful account/session summaries | Safe memory summaries with revocation state | Memory-as-authority | Memory-driven approval | Memory cannot approve, route, or unlock |

## Sentinel Components Reused

- `MissionAuthorityEnvelope` remains the only authority source.
- `MissionKernel` and `MissionRunStore` provide mission-owned persistence,
  event timeline, and tamper checks.
- `CredentialVaultRuntime` and `SecretBroker` concepts provide all secret
  access through leases, checkout metadata, receipts, and FinalGate.
- Browser L6 login and L7 account creation organs provide special-authority
  patterns and fake/injected backend expectations.
- Desktop sidecar and live desktop backend provide observation/target evidence
  refs, not authority.
- Voice and channel runtimes can request/checkpoint intent, not execute account
  actions directly.
- TelemetryKernel records account/login metrics and events; no parallel
  telemetry store is created.
- Replay reconstructs state without credential materialization, provider calls,
  screenshots, or repeated actions.

## Runtime Design

The new account authority layer will add focused operator modules:

```text
sentinel/operator/account_authority_models.py
sentinel/operator/account_authority.py
sentinel/operator/account_authority_replay.py
```

The runtime owns:

```text
policy/config
login/account plans
credential lease binding
human checkpoints
fake/injected execution results
session binding
receipts
FinalGate certificates
telemetry summaries
replay views
```

It does not own:

```text
secret storage
browser automation internals
desktop control
provider token exchange
MissionAuthorityEnvelope creation
real account provider integration
```

## Authority And Data Flow

```text
operator request
-> AccountAuthorityRuntime policy scan
-> MissionAuthorityEnvelope validation
-> CredentialVault lease binding if credential required
-> browser/desktop evidence refs
-> checkpoint for CAPTCHA/MFA/passkey/KYC/terms/consent
-> fake/injected consumer result
-> AccountLoginReceipt or AccountCreationReceipt
-> AccountAuthorityFinalGateCertificate
-> TelemetryKernel event/metric
-> replay view
```

Every persisted record uses redacted, hashed, or identifier-only fields.

## Test Strategy

Focused tests must prove:

- no login/account creation without `MissionAuthorityEnvelope`;
- no credential-backed flow without a valid CredentialVault lease;
- lease revocation, kill, and expiry fail closed;
- voice/desktop/channel/skill/worker/daemon/scheduler/memory/LLM cannot
  directly trigger or approve;
- CAPTCHA/MFA/KYC/WebAuthn/passkey create checkpoints;
- fake identity, mass signup, ban evasion, credential stuffing, session theft,
  provider override, fallback/AUTO, raw token/cookie/prompt/provider response,
  and raw credential payloads are rejected;
- receipts, FinalGate, telemetry, memory summaries, and replay never contain raw
  secret material and never become authority.

## Honest V1 Limits

```text
live public-site login = NOT_STARTED
live public-site account creation = NOT_STARTED
real OAuth token exchange = NOT_STARTED
password manager integration = NOT_STARTED
OS keychain live calls = NOT_STARTED
CAPTCHA solving = BLOCKED
KYC bypass = BLOCKED
account farming = BLOCKED
credential stuffing / ATO = BLOCKED
```
