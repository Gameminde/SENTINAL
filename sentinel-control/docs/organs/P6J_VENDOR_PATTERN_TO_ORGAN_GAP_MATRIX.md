# P6J Vendor Pattern To Organ Gap Matrix

Date: 2026-05-09

## Matrix

| Organ | Source-backed patterns | Current Sentinel rewrites | Gaps closed now | Deferred gaps |
| --- | --- | --- | --- | --- |
| Browser | OpenClaw browser/control plane, JARVIS browser/sidecar awareness, CloakBrowser P0-P5 power classification | BrowserReliabilityProfile, BrowserSessionContinuityPolicy, BrowserPowerGovernor, BrowserMisuseClassifier, BrowserDetectionBench, BrowserComplianceGate | Cloak-like powers are classified, not deleted | BrowserFinalGateAdapter, special-authority stealth sandbox |
| External API | OpenClaw connector/plugin manifest, OpenJarvis cost/rate routing, financial-services connector workflows, TradingAgents data vendor fallback | ExternalAPIAllowlist, APICostEstimator, APIPrivacyRiskClassifier, ExternalAPIDryRunPlanner, TradingAgentsDataVendorRoute | API organ now explicitly maps vendor fallback power | live read-only API sandbox with credential refs |
| Channel | OpenClaw channel adapters, Hermes context reuse, JARVIS approval lifecycle/templates | ChannelMessageDraft, ChannelSendGate, InboundChannelMessage, RecipientProvenance, ChannelRateLimitPolicy | Inbound context remains untrusted and draft-first lifecycle is source-backed | limited authorized send runtime |
| Credentials | JARVIS vault/sidecar secret-risk, OpenClaw plugin/channel credentials, Hermes external-account skills | CredentialRef, ScopedCredentialGrant, CredentialVaultPolicy, CredentialTraceRedactor, revoke_credential_grant | Raw secrets remain blocked from prompt/memory/workspace/vendor harvest | real vault adapter behind Red Lane special authority |
| Capital | financial-services procedures, OpenJarvis cost routing, Hermes memory, TradingAgents outcome memory | CapitalOpportunity, SignalLedger, AdaptiveOperatingEnvelope, BudgetReallocator, DynamicSpendPolicy, CapitalRiskReview | TradingAgents outcome memory is recognized as future capital-learning input | CapitalAnalysisBench, spend promotion |
| Spend | financial-services human review boundary, JARVIS approval/kill switch, OpenClaw receipt/action kernel lessons | SpendAuthorityEnvelope, SpendRequest, FakeSpendProvider, SpendReceipt, SubscriptionGuard, RefundCancelPath, SpendKillSwitch | Fake provider stays the only executable spend surface | real provider adapter after OrganBench and special authority |
| Trading | TradingAgents risk debate/portfolio manager, financial-services evidence/review boundary | TradingSpecialAuthority, BrokerContract, AssetPolicy, PositionSizingPolicy, MaxLossPolicy, StopLossPolicy, PaperTradeProvider, TradingReceipt | Paper provider is bound to authority asset scope and max leverage | real broker adapter after special authority and OrganBench |
| TradingAgents Harvest | Trading desk role graph, five-tier rating parser, vendor fallback, outcome memory | TradingAgentsFirmPlan, TradingAgentsRoleAssignment, TradingAgentsSignalParser, TradingAgentsDataVendorRoute, TradingOutcomeMemoryEntry | TradingAgents is now official P6J source evidence | OrganBench trading fixtures |

## Dangerous Surface Handling

| Surface | Handling |
| --- | --- |
| fake identity / KYC bypass / credential theft | blocked |
| unauthorized scraping / spam / deceptive identity | blocked |
| raw credential read | blocked |
| vendor runtime bridge | blocked |
| profit guarantee | blocked |
| budget overrun / unbacked signal spend | blocked |
| live API calls | promotion-gated |
| live channel send | promotion-gated |
| real payment execution | promotion-gated |
| real trading execution | promotion-gated |
| stealth browser operation | promotion-gated |
| dry-run request planning / fake providers / paper trading | sandboxed |

## Alignment Verdict

P6C-P6I.6 are no longer generic organ shells. Each one has a source-backed
mechanism, a Sentinel rewrite, an explicit control layer, and a promotion path.
No gap required new external power in P6J.
