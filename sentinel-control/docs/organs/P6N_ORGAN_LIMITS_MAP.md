# P6N Organ Limits Map

Date: 2026-05-09

## Summary

P6N confirms that Sentinel should keep improving existing organs before adding
new organ families. The current frontier is real but uneven: Desktop workspace
ops are closest to production-scoped execution, while Credentials are the
weakest because they only resolve local env refs and do not yet have a real
vault/provider injection path.

## Limits By Organ

### Browser

Can do now:

```text
read multiple allowlisted public pages
extract text and links
produce receipts for each read
capture fetch failure as operational failure
reject non-allowlisted URLs
```

Limits:

```text
no login
no form submit
no browser mutation
no stealth/captcha/bypass
```

Next adapters:

```text
controlled navigation adapter
browser receipt aggregator
LLM page-understanding runtime
```

### External API

Can do now:

```text
allowlisted GET
allowlisted HEAD
response receipts
error response capture
```

Limits:

```text
no mutation
no paid API live mode
no account-affecting API
```

Next adapters:

```text
authenticated read-only adapter
rate-limit ledger
credential injection through scoped refs
```

### Channel

Can do now:

```text
create multiple local drafts
persist draft files
link draft receipts
```

Limits:

```text
live send missing
provider adapter missing
send gate not integrated with live provider
```

Next adapters:

```text
provider draft adapter
recipient provenance adapter
LLM personalization runtime
```

### Credentials

Can do now:

```text
resolve env-backed CredentialRef
redact secret in receipts
reject missing env refs
reject wrong scope
```

Limits:

```text
no real vault adapter
no provider credential injection yet
revoked grant enforcement still needs real grant store
```

Next adapters:

```text
vault adapter
scoped provider injection
revocation ledger integration
```

### Desktop

Can do now:

```text
list workspace tree
read allowed file
write allowed file
create folder/file
reject path traversal
reject outside-root path
reject shell/process execution
```

Limits:

```text
no host control
no screenshots/clipboard live
no app/window actions live
```

Next adapters:

```text
workspace file ops promotion
sanitized screenshot adapter
clipboard gate
```

### Capital

Can do now:

```text
ingest browser/API/channel/desktop/trading receipts as signals
create signal ledger
produce opportunity score
produce spend proposal
reject unbacked signal refs
```

Limits:

```text
cannot spend
no live ROI feedback loop yet
```

Next adapters:

```text
ROI feedback adapter
spend proposal receipt integration
LLM opportunity synthesis runtime
```

### Trading

Can do now:

```text
read market data
run paper trade from market data
journal decision
reject real broker execution
reject profit guarantee
```

Limits:

```text
real broker missing
live risk monitoring missing
```

Next adapters:

```text
live paper broker feed
market data provider adapter
risk monitor
TradingAgents LLM synthesis runtime
```

### Spend

Can do now:

```text
run test-mode spend provider
enforce budget cap
enforce vendor/category scope
reject hidden subscription
reject real provider execution
```

Limits:

```text
real payment provider not configured
refund/cancel path needs provider integration
```

Next adapters:

```text
real provider test mode
refund/cancel provider adapter
budget ledger integration
```
