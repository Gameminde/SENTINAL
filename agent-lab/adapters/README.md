# Adapters

Future experimental adapters live here.

No adapter in this folder is production code.

Potential adapters:

- `openclaw_adapter/` - channel and gateway pattern experiments
- `hermes_skill_adapter/` - skill proposal and learning-loop experiments
- `jarvis_sidecar_adapter/` - sidecar permission model experiments
- `local_model_router/` - local/cloud routing experiments

Adapter rule:

No adapter may call Sentinel production APIs until it has a capability map, failure map, Firewall policy, and eval coverage.
