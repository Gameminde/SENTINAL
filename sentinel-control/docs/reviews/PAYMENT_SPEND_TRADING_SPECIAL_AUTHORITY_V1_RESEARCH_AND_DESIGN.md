# PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1 Research And Design

## Verdict

Payment, spend, transfer, and trading operations are special-authority actions. V1 must be sandbox-first and paper-first: Sentinel can plan, preview, checkpoint, simulate, execute fake sandbox spend, execute paper trading, receipt, FinalGate-certify, and replay without live provider/broker calls.

Live money, live broker orders, raw card/bank/broker credential handling, KYC/MFA/SCA bypass, fraud workflows, market manipulation, and automatic financial advice-as-authority remain blocked.

## Official Source Research

Sources inspected:

- PCI SSC PCI DSS overview: https://www.pcisecuritystandards.org/standards/pci-dss/
- Stripe Payment Intents and idempotent requests: https://docs.stripe.com/payments/payment-intents and https://docs.stripe.com/api/idempotent_requests
- PayPal idempotency: https://developer.paypal.com/api/rest/reference/idempotency/
- Adyen API idempotency: https://docs.adyen.com/development-resources/api-idempotency
- Plaid Link account-linking flow: https://plaid.com/docs/link/
- Open Banking UK Payment Initiation API Profile: https://openbankinguk.github.io/read-write-api-site3/v4.0/profiles/payment-initiation-api-profile.html
- Alpaca paper trading and order/buying-power docs: https://alpaca.markets/sdks/python/trading.html and https://docs.alpaca.markets/us/docs/orders-at-alpaca
- FINRA manipulative trading report: https://www.finra.org/rules-guidance/guidance/reports/2025-finra-annual-regulatory-oversight-report/manipulative-trading
- CFTC anti-manipulation rule page: https://www.cftc.gov/LawRegulation/DoddFrankAct/Rulemakings/DF_23_DFManipulation/index.htm
- SEC day-trading risk bulletin: https://www.sec.gov/about/reports-publications/investorpubsdaytipshtm

Research conclusions:

1. Safe automation in V1: local plans, previews, risk summaries, policy checks, sandbox spend, paper trading, idempotency reservation, receipts, FinalGate, and replay.
2. Never automate/bypass: raw payment credential collection, unauthorized transfers, real-money execution by default, hidden subscriptions, fraud-check evasion, SCA/MFA/KYC bypass, card testing, refund/chargeback abuse, market manipulation, insider-info trading, and hidden broker orders.
3. Sandbox/paper/live separation: candidate financial providers are descriptors. Sandbox spend and paper trading can execute only against fake/injected backends. Live money is modeled as `LIVE_MONEY_SPECIAL_AUTHORITY_LOCKED` and blocked by default.
4. Intent/order modeling: use descriptors and refs only: `PaymentIntentDescriptor`, `PaymentMethodRef`, `TradeOrderTicket`, `TradeOrderPreview`, and hash-bound idempotency keys.
5. Limits: enforce budget caps, velocity limits, merchant/recipient/instrument allowlists, risky-order checkpoints, and operator-originated approvals before material execution.
6. CredentialVault: provides mission/purpose/consumer/scope/time-bound leases and use receipts. A lease is proof of scoped secret handling, not authority.
7. Browser/Desktop/Voice/Channel: may request or explain a financial proposal/checkpoint only. They cannot submit payment/trade actions directly.
8. Idempotency: reserve before action, bind receipts to the reservation, block duplicate retries/replay, and record duplicate prevention.
9. V1/Future: V1 is fake/sandbox/paper with policy and proof. Future live money requires a stricter separate certification lock.

## AgentLab Mechanism Harvest

| Vendor/system | Architecture pattern | Useful mechanism | Sentinel-native adaptation | Risks | What not to copy | Implementation implication |
|---|---|---|---|---|---|---|
| OpenClaw | Broad tools/plugins/channels | Explicit approval surfaces and scanner posture | Financial scanner plus checkpoint-only external surfaces | Plugin chaos, external mutation | Runtime bridge, plugin execution | Financial actions enter only through Sentinel runtime |
| JARVIS / OpenJarvis | Local assistant with sidecar/session state | Operator-visible action state and local status | Financial status/replay/receipts visible through existing stores | Sidecar overreach, hidden submission | Desktop/browser authority model | Browser/Desktop create proposals only |
| Agent Zero | Autonomous tools with intervention UX | Operator checkpoint ergonomics | Checkpoints for new merchant, high amount, market order, KYC/MFA/SCA | Ambient tool execution | Direct tool access | Financial runtime enforces approval |
| gptme | Local config/env/session discipline | Explicit session config and compact output | Safe refs, hashes, and minimized receipts | Env/secret leaks | Env secret usage | No provider key/raw prompt/provider response persistence |
| Hermes / DeerFlow | Long workflow propagation | Durable checkpoints and replan limits | Financial plans and idempotency survive retry without duplicate action | Worker/memory approval drift | Memory/worker authority propagation | Worker/skill/daemon/scheduler cannot approve |
| UI-TARS | Visual checkout/trading UI risk | Visual evidence and target preview | Desktop/browser evidence refs, no direct submit | Credential OCR, hidden click | Uncontrolled computer-use loop | Financial actions require runtime proof |
| Letta / memory agents | Persistent context | Memory utility only | Store safe financial summaries only | Memory poisoning | Memory-as-policy | Memory cannot authorize spend/trade |

## Sentinel Components Reused

- `MissionAuthorityEnvelope` remains the only authority source.
- `MissionKernel` and `MissionRunStore` provide mission records, status, timeline, tamper checks, and run directories.
- `CredentialVaultRuntime`, `SecretBroker`, and `SecretAccessLease` provide scoped credential refs and use receipts.
- `TelemetryKernel` receives redacted financial events and metrics.
- Existing operator redaction/scanner utilities block raw secrets, raw prompts, provider responses, and reasoning.
- Existing browser payment/spend L7 organ informs safe payment-ref, cap, and FinalGate patterns.
- Existing AccountAuthority patterns inform service/scope binding, hash-only lease persistence, and replay no-action design.

## Runtime Design

New Sentinel-native operator modules:

- `sentinel/operator/financial_authority_models.py`
- `sentinel/operator/financial_authority.py`
- `sentinel/operator/financial_authority_replay.py`

Runtime flow:

```text
SpendRequest / TradingRequest
-> MissionAuthorityEnvelope check
-> FinancialAuthorityConfig/Policy check
-> budget/cap/velocity check
-> merchant/recipient/instrument/order policy check
-> safety scan
-> checkpoint if needed
-> idempotency reservation
-> fake sandbox spend or paper trading execution only
-> receipt
-> FinalGate
-> telemetry
-> replay
```

## Authority And Secret Law

- Financial config, policy, plan, checkpoint, receipt, telemetry, replay, memory, voice, desktop, browser, channel, skill, worker, daemon, scheduler, CredentialVault lease, and FinalGate are data/proof only.
- No model in this phase can create or expand `MissionAuthorityEnvelope`.
- Credential lease IDs are live same-process capabilities. Durable financial records persist only hash/ref metadata.
- Raw card numbers, CVV/CVC, bank credentials, broker keys, tokens, session cookies, OTP/passkey material, prompts, provider responses, and reasoning are rejected or redacted before persistence.

## V1 Limits

- No live payment provider calls.
- No live broker calls.
- No real card/bank/broker credentials.
- No refunds/disputes/chargebacks.
- No crypto/wire transfer.
- No margin/leverage/options/derivatives execution.
- No legal, tax, or investment advice authority.
- No provider fallback/AUTO or vendor runtime bridge.
