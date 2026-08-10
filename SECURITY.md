# Security Policy

Sentinel Control is experimental, pre-release agent infrastructure. Its security model treats authority, secrets, evidence, replay, revocation, and external effects as first-class trust boundaries.

Security reports are especially important when they involve a path that could let a model, worker, tool, browser session, desktop runtime, memory record, skill, or external input gain more authority than intended.

## Supported versions

Sentinel is under active development and does not yet maintain multiple supported release branches.

Security fixes are expected to target the current active codebase unless a maintainer explicitly identifies another supported version.

## Reporting a vulnerability

Please do **not** publish exploit details, credentials, secrets, private session material, or a working authority-bypass proof of concept in a public GitHub issue.

If GitHub offers a **Report a vulnerability** / private security advisory flow for this repository, use that private channel.

If no private reporting channel is available, open a minimal public issue asking the maintainer for a private contact path. Include only enough information to classify the affected Sentinel surface; do not include the exploit procedure or sensitive material publicly.

Useful private reports should include, when possible:

- affected component and commit/revision
- impact and expected trust boundary
- reproducible steps
- whether real external side effects are possible
- whether authority, revocation, kill, replay, or evidence can be bypassed
- whether credentials, tokens, cookies, prompts, provider responses, or other sensitive material can leak or persist unexpectedly
- a minimal proof of concept with secrets removed
- suggested mitigation, if known

## High-priority security classes

We especially want reports involving:

### Authority escape

A model, worker, skill, memory record, tool result, browser/desktop state, telemetry record, receipt, or other data object is able to grant or expand real execution authority.

### Kill or revocation bypass

A mission or capability continues material execution after its authority was revoked or its kill path was triggered.

### Replay with side effects

Inspecting, replaying, resuming, or reconstructing history causes an external action to execute again unexpectedly.

### Secret exposure or persistence

Raw credentials, authentication tokens, cookies, payment material, provider secrets, private prompts/responses, or other protected material are exposed, logged, persisted, or returned outside the intended boundary.

### Proof or receipt tampering

A material action can be falsely certified, evidence can be replaced without detection, or terminal truth can claim success that is not supported by the recorded execution state.

### Browser/session boundary escape

Browser execution crosses an origin, profile, session, account, workspace, or authority boundary that should have remained scoped.

### Desktop boundary escape

Desktop observation or action occurs outside the explicitly permissioned mission, display, app/window, control mode, or configured target boundary.

### Sandbox/workspace escape

Code or tool execution escapes its intended workspace, command allowlist, filesystem boundary, environment, or controlled runtime.

### Cross-mission contamination

Authority, secrets, state, evidence, workers, or artifacts from one mission become available to another mission without an explicit valid relationship.

## Not a security vulnerability by itself

The following may be bugs or product limitations but are not automatically security vulnerabilities:

- a model gives a poor answer
- a mission fails to complete
- a browser extraction is incomplete
- a deterministic/local-only capability is not yet production-ready
- an explicitly documented experimental or fake/injected adapter does not provide live functionality

However, if any of those failures cause an authority, secret, evidence, replay, or boundary violation, report them as security issues.

## Safe testing expectations

Please test against systems, accounts, data, and infrastructure you own or have explicit permission to use.

Do not use vulnerability research on Sentinel as justification to access third-party accounts, evade authentication or security checkpoints, collect credentials, manipulate financial systems, or cause unauthorized external effects.

## Disclosure

We prefer coordinated disclosure. Please give maintainers a reasonable opportunity to understand and fix a vulnerability before publishing detailed exploitation material.

Sentinel's goal is not only to become more capable. The control plane around that capability must remain stronger than the model operating inside it.
