# LLM Multi-Model Specialization Roadmap

Status: docs/spec lock candidate

## Purpose

Sentinel should eventually use different models for different cognitive roles,
but not by silent fallback or AUTO routing. User-selected model authority
remains central.

## Sequence

### 1. STRICT_SINGLE_MODEL_ROLE_LOOP

All roles use the same user-selected provider/backend/model.

Rules:

- no fallback;
- no AUTO routing;
- no role-specific override;
- no provider expansion required;
- model choice preserved across the role loop.

### 2. STRICT_MULTI_MODEL_BY_USER

Each role may have a model only if the user explicitly selects it.

Examples:

- strategist model;
- critic model;
- verifier model;
- coder advisor model;
- vision model.

Rules:

- every role model is explicit;
- no silent substitution;
- no provider fallback;
- budgets are role-aware;
- receipts record role/model ids safely.

### 3. FLEX_ROLE_MODEL_POLICY

Sentinel may recommend role/model alternatives within a user-approved policy.

Rules:

- recommendations do not execute by themselves;
- user or policy contract must approve selection;
- provider errors remain honest outcomes;
- fallback still requires explicit contract.

### 4. AUTO_MODEL_ROUTING

AUTO routing is future-only and requires a separate authority contract.

Required before AUTO:

- production provider routing governance;
- model quality/cost/latency evidence;
- fallback safety policy;
- user approval semantics;
- budget enforcement;
- receipt and FinalGate checks;
- no silent override guarantees.

## Role Specialization Vision

Future model classes:

- cheap model for extraction and classification;
- strong model for strategy and deep reasoning;
- coding model for code planning and refactor reasoning;
- critic model for adversarial review;
- verifier model for evidence checks;
- vision model for screens, OCR, image, and video;
- long-context model for large documents and mission memory.

## Current Boundary

This spec defines the roadmap only. It does not implement FLEX or AUTO, add
providers, or call providers.
