# Organ Gap Analysis

Status: audit lock

Date: 2026-05-19

## Summary

Sentinel has strong local execution, memory, cognition, and many latent
high-power organ families. The remaining gaps are mostly not about imagination.
They are about controlled promotion: each missing organ needs a Sentinel-native
contract, fake evals, receipts, rollback or disable posture, and FinalGate.

## Missing Or Under-Promoted Organs

### Browser Read-Only Organ V1

Spec status:

- `BROWSER_READONLY_OR_PREPARATION_SPEC` is locked as the Wave 2 entry spec.
- Runtime implementation is not started.
- Existing browser read/render/extract modules should be harvested through a
  Sentinel-native request/receipt/FinalGate wrapper.

Importance:

- Gives Sentinel reliable external perception and research evidence.
- Already has read/render/extract code and many browser docs/benchmarks.

Risk:

- Web prompt injection.
- Raw page body leakage.
- Domain/redirect abuse.

Recommended architecture:

- `BrowserReadOnlyRequest`, `BrowserReadOnlyReceipt`,
  `BrowserReadOnlyFinalGate`.
- Domain allowlist, redirect ledger, content hash, extraction hash.
- Rendered output must be untrusted data.

Required contracts:

- no submit, no login, no upload/download;
- DLP/redaction;
- network budget;
- evidence refs and source confidence.

### Browser Semantic Extraction Organ

Importance:

- Converts page evidence into structured facts, links, forms, prices,
  competitors, and claims.

Risk:

- Extracted content becoming instruction.
- Form labels or visual text smuggling commands.

Recommended architecture:

- extraction as `CLAIMED` or `OBSERVED`, never `SUPPORTED` without evidence;
- contradiction refs survive;
- source refs and DOM/AX/screenshot hashes.

Required contracts:

- data-not-instruction renderer;
- prompt-injection scanner;
- evidence verifier binding.

### Browser Preparation Organ

Spec status:

- `BROWSER_READONLY_OR_PREPARATION_SPEC` defines the preparation contract.
- Runtime implementation is not started.
- Preparation remains plan-only and cannot call browser backends.

Importance:

- Plans navigation/click/type workflows before action.

Risk:

- Prepared plan could be treated as execution permission.

Recommended architecture:

- plan-only candidate and dry-run preview;
- no backend call;
- no browser state mutation.

Required contracts:

- proposed step hashes;
- target refs;
- submit-disabled invariant.

### Browser Action Organ

Importance:

- Real operational browser power: navigation, click/type, controlled submit
  later.

Risk:

- Account mutation, form submit, purchase, posting, upload/download, login.

Recommended architecture:

- split action classes: navigation-only, limited interaction, submit,
  upload/download, private session, login;
- every class gets its own authority and FinalGate.

Required contracts:

- sandbox profile;
- domain allowlist;
- before/after DOM/AX/screenshot;
- exact preview match;
- credential broker only for login.

### Desktop Sidecar Observe Organ

Importance:

- Gives Sentinel awareness of host state, windows, screenshots, clipboard, and
  UI context.

Risk:

- Screen/clipboard secrets, private data capture, prompt injection in UI.

Recommended architecture:

- signed permissioned sidecar manifest;
- sanitizer/redactor before storage;
- user-visible enrollment and kill switch;
- observe-only first.

Required contracts:

- screenshot/OCR hash and redaction receipt;
- no raw screen durable storage by default;
- no action RPC in observe pack.

### Desktop Sidecar Action Organ

Importance:

- Full body control on local applications.

Risk:

- Host compromise, destructive UI actions, secret exfiltration, irreversible
  app actions.

Recommended architecture:

- action preview;
- user review for sensitive actions;
- per-app/window authority;
- revocable sidecar token;
- kill switch.

Required contracts:

- before/after screenshot;
- app/window binding;
- no shell/process by default;
- rollback unavailable must be honest.

### Vision/OCR/Screenshot Organ

Importance:

- Needed for browser visual grounding, desktop observe, PDF/image extraction,
  and multimodal research.

Risk:

- OCR prompt injection.
- Secrets in images.
- false visual grounding.

Recommended architecture:

- OCR is observation, not instruction;
- source image hash;
- crop/region refs;
- redaction before memory.

Required contracts:

- secret scanner;
- contradiction refs;
- confidence/variance;
- visual FinalGate for action grounding.

### PDF/Image Extraction Organ

Importance:

- Business docs, reports, invoices, screenshots, product images, contracts.

Risk:

- malicious PDF/text instructions;
- private data leakage;
- binary parsing vulnerabilities.

Recommended architecture:

- extraction sandbox;
- text/hash output only;
- raw file quarantine;
- structured claim status.

Required contracts:

- file type policy;
- size limits;
- no script/macros;
- redaction and provenance.

### API Read-Only Organ

Importance:

- Reads official APIs, dashboards, CRM, analytics, monitoring, docs.

Risk:

- credential scope creep;
- response data injection;
- paid API cost.

Recommended architecture:

- endpoint allowlist;
- credential ref only;
- read-only methods;
- rate/cost budget.

Required contracts:

- request/response metadata hashes;
- redacted response summaries;
- no raw auth headers;
- API FinalGate.

### API Mutation Organ

Importance:

- Controlled external system actions.

Risk:

- production mutation, account changes, billing, deletes, irreversible writes.

Recommended architecture:

- dry-run preview first;
- method/path/body contract;
- exact approval for mutation;
- compensation/rollback plan.

Required contracts:

- explicit L5/L6/L7 authority;
- provider-specific rollback or disable posture;
- idempotency key policy;
- external mutation FinalGate.

### Channel Draft Organ

Importance:

- Safe communication preparation without send.

Risk:

- draft leakage;
- bad recipient provenance;
- spammy content.

Recommended architecture:

- local draft or provider draft only;
- recipient provenance object;
- compliance classifier.

Required contracts:

- no send invariant;
- draft hash;
- delete/disable draft rollback if provider draft exists.

### Channel/Email Send Organ

Importance:

- Real outbound action.

Risk:

- unauthorized send, spam, legal/compliance, reputational damage.

Recommended architecture:

- exact preview;
- user approval for recipient/content/channel;
- rate limit;
- opt-out and compliance gate.

Required contracts:

- send receipt;
- platform delivery metadata;
- edit/delete/compensation posture;
- FinalGate certification.

### Sandbox Shell Organ

Importance:

- Enables build/test/code execution, package checks, diagnostics.
- Provides the correct replacement for adjacent app process execution patterns
  such as `RedditPulse` web-triggered Python workers.

Risk:

- host compromise, data exfiltration, persistence, dependency execution.

Recommended architecture:

- container or disposable workspace only;
- command allowlist;
- no host shell;
- no secrets;
- network off by default.

Required contracts:

- command hash;
- timeout;
- stdout/stderr hash;
- filesystem diff;
- sandbox destroy receipt.
- env allowlist with no provider/service keys unless explicitly scoped.

### Job Worker Organ

Importance:

- Sentinel needs a governed way to run long-lived local jobs such as report
  generation, validation, scraping, or enrichment without adopting ad hoc web
  route process execution.

Risk:

- child processes can inherit secrets;
- logs can leak sensitive output;
- retries can create cost explosions;
- web-triggered workers can become shell execution.

Recommended architecture:

- no shell by default;
- command/entrypoint allowlist;
- per-job env allowlist;
- artifact output directory;
- timeout and retry budget;
- receipt for accepted, blocked, failed, completed jobs.

Required contracts:

- job id, mission id, lane id, gate result id;
- argv hash, not raw secrets;
- stdout/stderr redaction hash;
- process exit receipt;
- sandbox destroy or cleanup receipt;
- FinalGate certification.

### Test Runner Organ

Importance:

- Lets Sentinel verify code changes without arbitrary shell.

Risk:

- test commands can execute arbitrary project code.

Recommended architecture:

- allowlisted test commands only;
- project-root containment;
- no install step unless separately authorized;
- output redaction.

Required contracts:

- command fixture;
- timeout/cost budget;
- artifact capture;
- no credentials.

### Code Patch Organ

Importance:

- Bounded code mutation and repair.

Risk:

- broad file edits, hidden payloads, tests bypassed.

Recommended architecture:

- patch plan first;
- safe apply under approved root;
- affected file list;
- test plan;
- rollback diff.

Required contracts:

- before/after hash per file;
- no generated secrets;
- code review receipt;
- FinalGate for patch.

### Skill Scanner Organ

Importance:

- Enables future skill/plugin ecosystem safely.

Risk:

- malicious skill instructions, scripts, dependencies, marketplace supply chain.

Recommended architecture:

- source-only scanner;
- permission extraction;
- shell/network/secret/file/API/channel/browser classifiers.

Required contracts:

- report hash;
- ruleset version;
- no install/runtime;
- fake malicious fixtures.

### Skill Sandbox Organ

Importance:

- Tests skills/plugins before any runtime exposure.

Risk:

- sandbox escape, dependency install, network or secret access.

Recommended architecture:

- offline fake runtime;
- no host install;
- no credentials;
- no persistent service.

Required contracts:

- sandbox destroy receipt;
- dependency hash;
- blocked action ledger.

### Plugin Install / Runtime Organ

Importance:

- Massive capability expansion.

Risk:

- arbitrary code, persistence, network, secrets, shell, hidden routes.

Recommended architecture:

- install plan, static scan, sandbox eval, permission manifest, user approval;
- runtime broker that never bypasses Sentinel gates.

Required contracts:

- package hash;
- postinstall disabled;
- network/FS policy;
- kill switch and disable receipt.

### Credential Broker Organ

Importance:

- Required for authenticated APIs, browser login, channels, devops.

Risk:

- raw key leakage and overbroad grants.

Recommended architecture:

- vault-backed credential refs;
- short-lived scoped grants;
- no raw secret returned to cognition/memory.

Required contracts:

- grant receipt;
- redaction proof;
- revocation ledger;
- organ/action scope binding.

### Scheduler/Automation Organ

Importance:

- Future persistent missions and timed actions.

Risk:

- stale authority, hidden delayed execution, recurrence drift.

Recommended architecture:

- schedule metadata only first;
- every run revalidates authority/gate/FinalGate;
- no schedule inherits old permission automatically.

Required contracts:

- schedule hash;
- expiry;
- cancellation receipt;
- revalidation receipt.

### DevOps/Cloud Organ

Importance:

- Infrastructure and deployment power.

Risk:

- production outage, data loss, cloud cost, secret exposure.

Recommended architecture:

- plan/apply separation;
- read-only inventory first;
- mutation only with explicit production authority.

Required contracts:

- cloud account/environment binding;
- dry-run;
- rollback plan;
- cost cap;
- approval and FinalGate.

### Spend/Trading Organ

Importance:

- Capital and market operations.

Risk:

- financial loss, legal/regulatory risk, fraud-like outcomes.

Recommended architecture:

- L7 exceptional authority only;
- paper/test-mode first;
- max spend/max loss policies;
- kill switch.

Required contracts:

- broker/payment provider contract;
- explicit user approval;
- receipt and journal;
- cancel/refund/hedge posture.

## Biggest Current Gaps

1. Unified organ adapter layer between older `sentinel.organs.*` and newer
   `sentinel.agent.organs.*`.
2. Browser promotion path into the new gate/FinalGate chain.
3. Credential broker with real vault-backed refs.
4. Safe shell/test runner separation.
5. Skill/plugin scanner and sandbox as first-class organs.
6. Explicit no-memory-as-instruction enforcement when retrieval eventually
   enters prompt context.
7. Quarantine or rewrite adjacent web-worker/process execution so it cannot be
   mistaken for approved Sentinel organ execution.

## Gap Verdict

Sentinel lacks almost none of the conceptual organs. It lacks promotion
contracts for the highest-power surfaces. The next expansion must be browser
read-only/preparation, not browser submit or desktop action.
