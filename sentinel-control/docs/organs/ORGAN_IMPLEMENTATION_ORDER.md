# Organ Implementation Order

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This document locks the implementation waves for Sentinel organs. The order is
designed to grow power without jumping from proposal/gate metadata into broad
world mutation.

## Wave 1: L2/L3 Local Safe Organs

Organs:

- Local Artifact Executor L2;
- Reversible Workspace Action Executor L3;
- Code Patch Plan / Safe Apply later;
- Test Runner allowlist spec.

Why this order:

- local artifacts and reversible workspace actions are the smallest real body
  movement;
- path containment, receipts, before/after hashes, rollback, and FinalGate can
  be proven without external accounts;
- these surfaces prepare the receipt and rollback discipline needed for all
  later organs.

Required preconditions:

- L2/L3 spec locked;
- `DelegatedActionGateModelV0` exists;
- lane metadata exists;
- workspace root policy;
- no raw prompt/response/reasoning/key durability.

Tests required:

- allowed workspace only;
- symlink and parent traversal blocked;
- before/after hash for L3;
- rollback tested before L3 mutation;
- no shell/network/credentials/send.

Vendor-harvest dependencies:

- Agent Lab sandbox workspace;
- OpenClaw filesystem failure modes;
- JARVIS sidecar risk lessons.

## Wave 2: Read-Only Perception Organs

Organs:

- Browser Read-Only Organ;
- API Read-Only Organ;
- Vision/OCR/PDF extraction;
- Research/Web Evidence Organ.

Why this order:

- perception gives Sentinel eyes before stronger hands;
- read-only surfaces can grow evidence quality without external mutation;
- prompt injection and raw data redaction can be tested early.

Required preconditions:

- untrusted-context rendering;
- injection scanner;
- domain/endpoint allowlists;
- DLP/redaction policy;
- receipt model for source refs and extraction hashes.

Tests required:

- browser submit/login/upload/download blocked;
- API mutation blocked;
- evidence remains data, not instruction;
- screenshot/OCR redacts sensitive regions;
- raw extraction is not durably stored when unsafe.

Vendor-harvest dependencies:

- OpenClaw browser snapshot lessons;
- Hermes context scanner;
- JARVIS screen sanitizer requirements;
- AgentMemory raw-capture rejection.

## Wave 3: Draft/Preparation Organs

Organs:

- Channel Draft Organ;
- Email Draft Organ;
- Browser Preparation Organ;
- GTM Execution Organ.

Why this order:

- drafts create useful operational leverage without external mutation;
- GTM assets can become strong outputs while send/publish remains gated.

Required preconditions:

- contact/recipient provenance model;
- draft-only receipt model;
- no-send invariant;
- user review fields.

Tests required:

- draft cannot send;
- browser preparation cannot submit;
- recipient provenance missing requires review;
- GTM asset receipts contain hashes only.

Vendor-harvest dependencies:

- OpenClaw channel manifests;
- Hermes Google Workspace risk notes;
- Sentinel GTM pack quality gates.

## Wave 4: Controlled External Action Organs

Organs:

- Email Send Organ;
- Channel Send Organ;
- API Mutation Organ;
- Browser Action Organ with no submit first, submit later only with explicit
  authority.

Why this order:

- external mutation is where Sentinel becomes operationally powerful;
- every action needs preview, user approval where required, contact/domain
  policy, rollback/compensation posture, and FinalGate.

Required preconditions:

- draft/preparation organs proven;
- external contact policy;
- API endpoint policy;
- browser sandbox profile;
- explicit approval receipts;
- revocation/disable plan.

Tests required:

- no send without exact approval;
- no API mutation without endpoint/method authority;
- no browser submit/login/upload/download without explicit special contract;
- approval preview must match execution.

Vendor-harvest dependencies:

- OpenClaw channels and browser gateway;
- Hermes workspace/channel risk;
- JARVIS browser templates as non-executing study material.

## Wave 5: High-Power Local/Desktop Organs

Organs:

- Desktop Sidecar Observe;
- Desktop Sidecar Action;
- Shell Sandbox;
- DevOps/Cloud.

Why this order:

- these are host or infrastructure power surfaces;
- they require stronger sandboxing, signed sidecar identity, kill switch,
  sanitizer, and audit.

Required preconditions:

- sidecar capability manifest;
- sidecar enrollment/revocation;
- screen/context sanitizer;
- sandbox/container policy;
- command/API allowlists;
- user approval UI.

Tests required:

- token replay blocked;
- capability mismatch blocked;
- screenshot secret redacted;
- shell cannot run on host;
- cloud mutation requires special approval and rollback plan.

Vendor-harvest dependencies:

- JARVIS sidecar and desktop awareness;
- OpenClaw shell scanner;
- OpenJarvis security config.

## Wave 6: Skill/Plugin Ecosystem

Organs:

- Skill Scanner;
- Skill Sandbox;
- Plugin Install;
- Plugin Runtime.

Why this order:

- skill/plugin ecosystems are a power multiplier and a supply-chain risk;
- scanner and sandbox must exist before install/runtime.

Required preconditions:

- static scanner;
- canonical JSON/Markdown reports;
- source hash and ruleset version;
- fake eval fixtures;
- sandbox runtime policy;
- no host install.

Tests required:

- shell/install/secret manager skills blocked;
- plugin HTTP route requires review;
- package install/postinstall blocked;
- external send plugin blocked or review-only;
- report consistency tests pass.

Vendor-harvest dependencies:

- OpenClaw scanner;
- OpenJarvis skill importer/quarantine;
- Hermes skill index.

## Wave 7: Exceptional Authority Organs

Organs:

- Credential Reference;
- Spend/Trading;
- Production mutation;
- L7 special approval only.

Why this order:

- these surfaces can cost money, affect accounts, change production, or create
  financial/legal risk;
- they should only exist after the action kernel, receipts, rollback, replay,
  and FinalGate are mature.

Required preconditions:

- special authority contracts;
- user approval semantics;
- credential refs and revocation;
- budget/max-loss policy;
- kill switch;
- production rollback/disable plan;
- compliance/risk review.

Tests required:

- raw secret never exposed;
- credential ref scope enforced;
- max loss/spend cap enforced;
- broker/payment calls are fake or paper until explicit live contract;
- kill switch blocks further actions.

Vendor-harvest dependencies:

- TradingAgents risk debate and checkpoints;
- OpenClaw credential/channel scanner;
- P6 capital/spend/trading scorecards.

## Anti-Drift Rules

Do not skip directly from this roadmap to:

- broad organ execution;
- browser submit;
- channel send;
- API mutation;
- desktop action;
- shell host execution;
- plugin runtime;
- credential access;
- spend/trading;
- provider expansion;
- fallback routing;
- AUTO routing.

Every organ must pass through spec, fake eval, TDD implementation, receipt,
rollback, and FinalGate proof before promotion.
