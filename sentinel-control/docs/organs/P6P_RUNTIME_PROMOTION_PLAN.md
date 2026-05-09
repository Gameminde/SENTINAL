# P6P Runtime Promotion Plan

Date: 2026-05-09

## Summary

P6O proved that existing organs can move in max-mode batches and cross-organ
paths. P6P turns that evidence into the next build order.

The purpose is not to slow Sentinel down. The purpose is to promote the powers
that are already closest to real scoped execution.

## Next Build Block

```text
next_build_block = desktop_workspace_l6
```

Desktop workspace operations are closest to production-scoped execution because
they already perform real local workspace create/write/read/list with receipts
and stronger root containment.

## Promotion Order

### 1. Desktop Workspace L6

Purpose:

```text
turn workspace file operations into a production-scoped limited execution surface
```

Required:

```text
workspace operation adapter
workspace receipt adapter
workspace root authority
allowed path policy
mutation scope
path containment receipts
rollback written artifacts
```

### 2. Browser Controlled Navigation L6

Purpose:

```text
move from public read batches to controlled navigation without login/session mutation
```

Required:

```text
controlled navigation adapter
browser receipt aggregator
allowed domains
navigation action scope
timeout budget
page evidence receipts
```

### 3. API Authenticated Read L6

Purpose:

```text
read authenticated APIs through scoped credential refs, still read-only
```

Required:

```text
authenticated read-only adapter
rate-limit ledger
allowed vendor
allowed endpoint
credential ref scope
API response receipts
credential ref receipts
```

### 4. Channel Provider Draft L6

Purpose:

```text
create real provider drafts without live send
```

Required:

```text
Gmail/Outlook draft adapter
recipient provenance adapter
draft-only authority
provider draft receipt
delete/disable draft rollback
```

### 5. Credential Vault Ref L6

Purpose:

```text
move from env grants to vault-backed references and revocation ledger
```

Required:

```text
vault ref adapter
grant revocation ledger
credential ref
scope grant
expiry
allowed organ/action
redaction receipt
```

### 6. Capital ROI Feedback L6

Purpose:

```text
ingest real outcome feedback into capital scoring
```

Required:

```text
ROI feedback adapter
capital receipt aggregator
allowed signal sources
budget context
feedback scope
stale opportunity handling
```

### 7. Trading Live Paper Feed L6

Purpose:

```text
connect live/polled market data to paper trading and risk monitoring
```

Required:

```text
live market data adapter
trading risk monitor
allowed symbols
broker paper scope
max loss policy
market feed receipts
paper trade receipts
```

### 8. Spend Provider Test Mode L6

Purpose:

```text
connect a real provider test-mode surface without real charge
```

Required:

```text
provider test-mode adapter
refund/cancel adapter
explicit spend authority
vendor/category scope
budget cap
provider test receipt
kill-switch receipt
```

## Deferred New Organ Families

```text
code_shell
memory_self_improvement
new_desktop_family
```

These stay deferred until existing organs finish their L6 promotion path.

## Deferred High-Power Surfaces

```text
real_payment_provider -> provider test-mode promotion and spend FinalGate
real_broker_execution -> live paper feed, risk monitor, broker authority, trading FinalGate
live_channel_send -> provider draft promotion, recipient provenance, send gate, channel FinalGate
browser_login_session -> controlled navigation, session policy, domain authority, browser FinalGate
desktop_screenshot_clipboard -> sanitizer proof, sidecar authority, desktop FinalGate
```

These powers are not deleted. They are staged.
