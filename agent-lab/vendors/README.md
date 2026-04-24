# Vendors

This folder is reserved for local vendor checkouts or source snapshots.

OpenClaw is currently cloned for static audit only. Other vendors are not cloned.

## Candidate Projects

| Project | Repository | Research Focus | Default Action |
| --- | --- | --- | --- |
| OpenClaw | https://github.com/basetenlabs/openclaw-baseten | channels, gateway, skills, live canvas | Cloned for static audit only |
| Hermes Agent | https://github.com/nousresearch/hermes-agent | memory, skill creation, learning loop | Audit before clone |
| OpenJarvis | https://github.com/open-jarvis/OpenJarvis | local-first routing, cost/latency/energy evals | Audit before clone |
| JARVIS | https://github.com/vierisid/jarvis | daemon, sidecars, desktop awareness, workflow builder | Audit before clone |

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
