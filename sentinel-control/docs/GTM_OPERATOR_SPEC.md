# Sentinel GTM Operator Spec

## Goal

Sentinel GTM Operator turns a product idea into a proof-backed GTM Pack.

The GTM Pack must be useful without the UI and must cite the evidence behind its claims.

## Pack Structure

1. Executive Verdict
2. Best Niche
3. ICP
4. Pain Summary
5. WTP Evidence
6. Competitor Gap
7. Positioning
8. Offer Angle
9. Landing Page Copy
10. Outreach Messages
11. Interview Script
12. Prospect Sources
13. 7-Day Validation Roadmap
14. Decision Rules
15. Watchlist

## Generated Project Folder

Later sprints generate:

```text
data/generated_projects/{slug}/
├── 00_VERDICT.md
├── 01_EVIDENCE.md
├── 02_ICP.md
├── 03_COMPETITOR_GAPS.md
├── 04_LANDING_PAGE_COPY.md
├── 05_OUTREACH_MESSAGES.md
├── 06_INTERVIEW_SCRIPT.md
├── 07_7_DAY_ROADMAP.md
├── 08_WATCHLIST.md
└── trace.json
```

## Sprint 1 Boundary

Sprint 1 creates schemas, trace logging, policies, migration SQL, and tests. It does not generate GTM packs yet.

