# JARVIS Desktop Map

Status: source-level public README scan only. No local clone or runtime test yet.

## Initial Observations

- Daemon plus sidecar architecture is the primary pattern to study.
- Desktop awareness, screenshots, filesystem, terminal, clipboard, and browser controls create a broad permission surface.
- The sidecar model could inspire Sentinel later, but only with a strict permission manifest.

## Benchmark Priorities

1. Sidecar enrollment.
2. Capability declarations.
3. Desktop awareness scope.
4. Browser automation boundaries.
5. Audit trail completeness.

## Sentinel Position

- Take architecture inspiration from daemon/sidecar separation.
- Rewrite permission model and trace schema.
- Avoid desktop control until the Firewall can govern sidecars.
