# Vendors

This folder is reserved for local vendor checkouts or source snapshots.

Vendor sources are cloned for static audit only. They are laboratory specimens, not dependencies.

## Candidate Projects

| Project | Repository | Research Focus | Default Action |
| --- | --- | --- | --- |
| OpenClaw | https://github.com/basetenlabs/openclaw-baseten | channels, gateway, skills, live canvas | Cloned for static audit only |
| Hermes Agent | https://github.com/nousresearch/hermes-agent | memory, skill creation, learning loop | Cloned for static audit only |
| OpenJarvis | https://github.com/open-jarvis/OpenJarvis | local-first routing, cost/latency/energy evals | Cloned for static audit only |
| JARVIS | https://github.com/vierisid/jarvis | daemon, sidecars, desktop awareness, workflow builder | Cloned for static audit only |
| TradingAgents | https://github.com/TauricResearch/TradingAgents | multi-agent trading desk, debates, rating, vendor fallback, outcome memory | Cloned for static audit only |
| AgentMemory | https://github.com/rohitg00/agentmemory | persistent agent memory, retrieval, replay, retention, slots, lessons, MCP/API memory surface | Cloned for static audit only |

## Clone Rule

Before cloning a vendor repo, create a short entry in `audits/vendor_clone_checks.md` with:

- repo URL;
- expected disk size;
- dependency stack;
- install commands to avoid;
- execution permissions requested by the project;
- sandbox folder to use;
- whether network access is required;
- whether secrets are required.

## Runtime Rule

Vendor apps must not be run with access to real accounts, real browser profiles, production credentials, SSH keys, wallets, or unrestricted filesystem paths.

Current forensic rule: do not run vendor apps at all unless a later explicit container-only plan is approved.
