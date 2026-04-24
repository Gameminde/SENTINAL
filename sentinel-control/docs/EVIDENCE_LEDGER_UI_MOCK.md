# Evidence Ledger UI Mock

Sprint 2 creates the product shape for an Evidence Ledger screen before the real web UI exists.

## Page

`/dashboard/evidence`

## Purpose

Show why Sentinel reached a decision, before any action is approved.

## Primary Panels

1. Evidence Summary
   - direct evidence count
   - adjacent evidence count
   - WTP/pricing signal count
   - source count
   - freshness

2. Evidence Table
   - type
   - proof tier
   - source
   - quote/summary
   - confidence
   - relevance
   - URL

3. Claims Linked To Evidence
   - each recommendation shows `evidence_refs`
   - missing references block GTM recommendations in later sprints

4. Firewall Context
   - proposed action
   - risk level
   - dry-run preview
   - approval status

## Empty State

Before evidence exists:

> No Sentinel decision can be generated yet. Add CueIdea validation or research evidence first.

