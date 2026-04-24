# Sentinel Control Security Model

## Security Principle

Sentinel Control uses a permission-first execution model. Every execution must pass through:

- evidence;
- risk score;
- permission policy;
- dry-run preview;
- user approval when required;
- trace log.

## Risk Levels

| Level | Meaning | Default behavior |
| --- | --- | --- |
| LOW | Local, reversible, contained action | May run automatically if policy allows |
| MEDIUM | User-visible or external-facing draft/action | Requires user approval |
| HIGH | External contact, publishing, browser submit, money movement | Requires approval; many are disabled in v1 |
| CRITICAL | Shell, code modification, secrets, broad filesystem access | Disabled in v1 |

## Approval Rules

- LOW actions can run only if the policy marks them as auto-allowed.
- MEDIUM, HIGH, and CRITICAL actions require approval.
- Any v1-disabled action is blocked even if input parameters look safe.
- Approval must be logged before execution.
- Approval applies to the exact dry-run preview, not to a broad future capability.

## Tool Permission Model

Each tool has a policy with:

- tool name;
- risk level;
- auto-allowed flag;
- approval requirement;
- v1 disabled flag;
- allowed paths or constraints;
- policy metadata.

Unknown tools default to CRITICAL and blocked.

## Trace Logging Requirements

Trace records are required for:

- run start;
- evidence recording;
- decision creation;
- action proposal;
- firewall review;
- approval recording;
- action execution;
- asset generation;
- run completion or failure.

Trace logs must preserve enough snapshots to reconstruct why an action was proposed and what evidence supported it.

## Data Privacy Requirements

- Store only the minimum input needed for decision and traceability.
- Do not store secrets inside traces.
- Do not log raw API keys.
- External contact data must be user-provided or explicitly approved before use.
- Generated outreach remains draft-only in v1.

## Auth And User Separation

- Local development uses `SENTINEL_REQUIRE_AUTH=false` and `local_user`.
- Hosted environments must set `SENTINEL_REQUIRE_AUTH=true`.
- API routes resolve a user before reading or mutating run state.
- Run reads and action updates are scoped by `user_id`.
- Supabase service-role keys stay server-side only.
- Bearer tokens are verified against Supabase Auth when auth is required.

## Safe Outreach Policy

The GTM Operator may generate outreach drafts, but v1 does not send them.

Drafts should:

- avoid deception;
- avoid fake personalization;
- include opt-out language when appropriate;
- reference evidence-backed pain rather than fabricated claims;
- be logged with evidence references.
