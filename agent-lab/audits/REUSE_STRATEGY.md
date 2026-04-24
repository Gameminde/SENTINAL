# Reuse Strategy

The goal is not to copy agent runtimes. The goal is to understand what makes them powerful, then rebuild the useful pieces inside Sentinel's evidence, policy, approval, and trace model.

## TAKE

Patterns that can inspire Sentinel architecture:

- Channel adapter pattern from multi-channel agents.
- Live session/canvas concept for showing agent progress.
- Memory summaries and retrieval patterns.
- Cost, latency, energy, and accuracy as first-class routing metrics.
- Sidecar architecture as a separation between central brain and machine capabilities.
- Workflow builder concepts for showing controlled action plans.

## REWRITE

Concepts that may be valuable but must be rebuilt with Sentinel controls:

- Skill manifest format.
- Skill creation and refinement.
- Local/cloud model router.
- Browser automation.
- Desktop sidecar.
- Email workflows.
- Filesystem tools.
- Scheduled automations.
- Multi-provider LLM routing.

Rewrite requirements:

- explicit permission declarations;
- risk scoring;
- dry-run preview;
- approval gate;
- trace log;
- eval coverage;
- data boundary rules;
- secret-safe memory.

## AVOID

Patterns not aligned with Sentinel v1:

- Unrestricted skills.
- Skill marketplace without scanner.
- Shell execution by default.
- Browser form submission by default.
- Native app control without a sidecar policy model.
- Real email sending without provenance and approval.
- Memory that stores raw secrets or unfiltered private data.
- Self-modifying prompts, code, policies, or skills without review.

## Decision Rule

A pattern can move from Agent Lab into Sentinel only when it has:

1. a product reason;
2. a risk model;
3. a dry-run design;
4. an approval rule;
5. a trace schema;
6. an eval dataset;
7. a rollback plan.
