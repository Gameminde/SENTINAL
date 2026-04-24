# OpenJarvis Cost Router Map

Status: source-level public README scan only. No local clone or runtime test yet.

## Initial Observations

- Local-first routing and cost/latency/energy evaluation are the main patterns to study.
- The framework treats cost and efficiency as product constraints, not afterthoughts.
- This maps well to Sentinel's future per-run budget controls.

## Benchmark Priorities

1. Local vs cloud routing.
2. Cost per run.
3. Latency per task type.
4. Accuracy vs cost scoring.
5. Fallback behavior.

## Sentinel Position

- Take the evaluation mindset.
- Rewrite routing around Sentinel run budgets and risk classes.
- Keep out of the main product until GTM quality is stronger.
