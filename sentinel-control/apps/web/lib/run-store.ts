import { randomUUID } from "crypto";
import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";
import type { NormalizedCueIdeaImport } from "@/lib/cueidea-import";
import { actions, agents, evidence, firewallPolicies, projects, runStages, runSummary } from "@/lib/demo-data";
import type {
  ActionRow,
  ApprovalStatus,
  CostSummaryRow,
  CreateFeedbackInput,
  CreateRunInput,
  EvidenceRow,
  ExecutionBoardColumnRow,
  FeedbackEntryRow,
  GTMPackQualityRow,
  GeneratedAssetRow,
  PaidRunQuoteRow,
  ProspectSourceRow,
  RunDepth,
  SentinelRunRecord,
  TraceLogRow,
  WatchlistItemRow,
  WatchlistStatus,
} from "@/lib/types";

type RunState = {
  version: 1;
  runs: SentinelRunRecord[];
};

const STORE_PATH = path.resolve(process.cwd(), "../../data/web_state.json");
const DEFAULT_USER_ID = "local_user";

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function nowIso() {
  return new Date().toISOString();
}

function compactDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatCents(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

export function estimateRunCost(run: Pick<SentinelRunRecord, "depth" | "evidence" | "actions" | "generatedAssets">): CostSummaryRow {
  const depthMultiplier = run.depth === "deep" ? 1.8 : run.depth === "quick" ? 0.55 : 1;
  const lines = [
    {
      label: "Research and evidence normalization",
      tokens: Math.round((run.evidence.length * 820 + 1200) * depthMultiplier),
      estimatedCents: Math.round((run.evidence.length * 9 + 18) * depthMultiplier),
    },
    {
      label: "Debate and verdict",
      tokens: Math.round(1800 * depthMultiplier),
      estimatedCents: Math.round(24 * depthMultiplier),
    },
    {
      label: "GTM pack generation",
      tokens: Math.round((run.generatedAssets.length * 950 + 1600) * depthMultiplier),
      estimatedCents: Math.round((run.generatedAssets.length * 8 + 22) * depthMultiplier),
    },
    {
      label: "Firewall review",
      tokens: Math.round(run.actions.length * 260),
      estimatedCents: Math.round(run.actions.length * 3),
    },
  ];

  return {
    currency: "USD",
    totalCents: lines.reduce((total, line) => total + line.estimatedCents, 0),
    lines,
    note: "Local estimate only; real model/API accounting will replace this when live providers are connected.",
  };
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64) || "sentinel-project";
}

function runIdFromDate(date = new Date()) {
  const stamp = date
    .toISOString()
    .replace(/[-:T.Z]/g, "")
    .slice(0, 12);
  return `GR-${stamp}-${randomUUID().slice(0, 6)}`;
}

function proofTierFor(type: string): EvidenceRow["proofTier"] {
  if (type === "direct") return "direct";
  if (type === "adjacent") return "adjacent";
  return "supporting";
}

function watchlistId(prefix: string, idea: string) {
  return `${prefix}_${slugify(idea).slice(0, 36)}`;
}

function buildWatchlistRows(idea: string, evidenceRows: EvidenceRow[], updatedAt = nowIso()): WatchlistItemRow[] {
  const competitorRefs = evidenceRows
    .filter((row) => row.proofTier === "adjacent" || row.details.tags.some((tag) => tag.includes("competitor")))
    .map((row) => row.id);
  const wtpRefs = evidenceRows
    .filter((row) => row.details.tags.some((tag) => tag === "wtp" || tag === "pricing" || tag === "interview"))
    .map((row) => row.id);
  const riskRefs = evidenceRows
    .filter((row) => row.details.tags.some((tag) => tag === "firewall" || tag === "risk" || tag === "policy"))
    .map((row) => row.id);
  const fallbackRefs = evidenceRows.slice(0, 2).map((row) => row.id);

  return [
    {
      id: watchlistId("wl_competitor", idea),
      label: "Competitor gap watch",
      signalType: "competitor",
      status: "monitoring",
      summary: "Track alternatives, repeated complaints, and gaps that can become the narrow wedge.",
      source: "Competitor evidence slot",
      evidenceRefs: competitorRefs.length > 0 ? competitorRefs : fallbackRefs,
      updatedAt,
    },
    {
      id: watchlistId("wl_wtp", idea),
      label: "WTP interview watch",
      signalType: "wtp",
      status: "needs_review",
      summary: "Move to interview once a real prospect or pricing signal is attached to the run.",
      source: "WTP evidence slot",
      evidenceRefs: wtpRefs.length > 0 ? wtpRefs : fallbackRefs,
      updatedAt,
    },
    {
      id: watchlistId("wl_risk", idea),
      label: "Execution risk watch",
      signalType: "risk",
      status: "monitoring",
      summary: "Keep external contact, code mutation, browser submission, shell execution, and spend blocked or approval-gated.",
      source: "AgentOps Firewall",
      evidenceRefs: riskRefs.length > 0 ? riskRefs : fallbackRefs,
      updatedAt,
    },
  ];
}

function buildPaidRunQuote(run: Pick<SentinelRunRecord, "id" | "depth" | "summary" | "cost">): PaidRunQuoteRow {
  const amountCents = run.depth === "deep" ? 9900 : run.depth === "quick" ? 1900 : 4900;
  return {
    id: `quote_${run.id}`,
    runId: run.id,
    label: `${run.summary.verdict} paid run pack`,
    amountCents,
    status: "payment_disabled",
    lineItems: [
      "Evidence-backed GTM pack",
      "Firewall review and approval inbox",
      "Trace ledger export",
      "Outreach drafts only",
      `Estimated internal cost ${formatCents(run.cost.totalCents)}`,
    ],
    createdAt: nowIso(),
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function textValue(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(textValue).filter(Boolean).join("\n");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, entry]) => {
        const body = textValue(entry);
        return body ? `${key}: ${body}` : "";
      })
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

function cueideaReport(imported?: NormalizedCueIdeaImport) {
  if (!imported) return {};
  const root = asRecord(imported.raw);
  const report = asRecord(root.report);
  return Object.keys(report).length > 0 ? report : root;
}

function firstSection(report: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = textValue(report[key]);
    if (value) return value;
  }
  return "";
}

function buildCueIdeaReportSummary(imported: NormalizedCueIdeaImport | undefined, importedAt: string): SentinelRunRecord["cueideaReport"] {
  if (!imported) return undefined;
  const report = cueideaReport(imported);
  return {
    validationId: imported.validationId,
    status: imported.status,
    importedAt,
    executiveSummary: imported.summary,
    icp: firstSection(report, ["ideal_customer_profile", "icp", "target_customer", "audience"]),
    positioning: firstSection(report, ["positioning", "positioning_strategy", "offer_angle", "differentiation"]),
    pricing: firstSection(report, ["pricing_strategy", "pricing", "willingness_to_pay"]),
    competitorLandscape: firstSection(report, ["competition_landscape", "competitors", "competitor_analysis"]),
    distribution: firstSection(report, ["distribution_strategy", "distribution", "community_sources", "go_to_market"]),
    rawSectionKeys: Object.keys(report).slice(0, 24),
  };
}

function sourceTypeFrom(row: EvidenceRow): ProspectSourceRow["sourceType"] {
  const joined = `${row.source} ${row.details.tags.join(" ")}`.toLowerCase();
  if (joined.includes("reddit") || joined.includes("forum") || joined.includes("community") || joined.includes("discord") || joined.includes("slack")) return "community";
  if (joined.includes("g2") || joined.includes("capterra") || joined.includes("review")) return "review_site";
  if (joined.includes("competitor") || joined.includes("alternative")) return "competitor";
  if (row.url) return "direct_source";
  if (joined.includes("search") || joined.includes("keyword")) return "search";
  return "unknown";
}

function buildProspectSources(idea: string, evidenceRows: EvidenceRow[], imported?: NormalizedCueIdeaImport): ProspectSourceRow[] {
  const byKey = new Map<string, ProspectSourceRow>();

  for (const row of evidenceRows) {
    const key = `${row.source}-${row.url || row.details.tags.join(",")}`;
    const current = byKey.get(key);
    if (current) {
      current.evidenceRefs = Array.from(new Set([...current.evidenceRefs, row.id]));
      continue;
    }
    byKey.set(key, {
      id: `src_${slugify(key).slice(0, 42) || randomUUID().slice(0, 8)}`,
      label: row.source,
      sourceType: sourceTypeFrom(row),
      source: row.source,
      url: row.url,
      whyRelevant: row.summary,
      evidenceRefs: [row.id],
    });
  }

  const report = cueideaReport(imported);
  const communities = [
    ...asList(report.community_sources),
    ...asList(report.distribution_sources),
    ...asList(asRecord(report.distribution_strategy).sources),
    ...asList(asRecord(report.ideal_customer_profile).communities),
  ];
  communities.forEach((entry, index) => {
    const row = asRecord(entry);
    const label = textValue(row.name || row.source || row.community || entry) || `CueIdea source ${index + 1}`;
    const key = `cueidea-${label}`;
    if (!byKey.has(key)) {
      byKey.set(key, {
        id: `src_${slugify(label).slice(0, 42)}`,
        label,
        sourceType: "community",
        source: "CueIdea report",
        url: textValue(row.url) || undefined,
        whyRelevant: textValue(row.reason || row.summary || row.description) || `Potential source for ${idea}.`,
        evidenceRefs: evidenceRows.slice(0, 2).map((rowItem) => rowItem.id),
      });
    }
  });

  return Array.from(byKey.values()).slice(0, 12);
}

const majorQualitySections = ["icp", "wtp", "competitor_gap", "positioning", "outreach", "landing", "roadmap"] as const;

function assetContent(assets: GeneratedAssetRow[], assetType: string) {
  return assets.find((asset) => asset.assetType === assetType)?.content || "";
}

function assetRefs(assets: GeneratedAssetRow[], assetType: string) {
  return assets.find((asset) => asset.assetType === assetType)?.evidenceRefs || [];
}

function hasSpecificNumbers(value: string) {
  return /\b\d+([%-]|\s*(clients|prospects|days|hours|minutes|monthly|mo|users|interviews))?\b/i.test(value);
}

function wordCount(value: string) {
  return (value.toLowerCase().match(/[a-z0-9$%+-]+/g) || []).length;
}

function scoreQualityText(name: string, value: string, refs: string[], minWords: number) {
  const messages: string[] = [];
  let score = 35;
  const lowered = value.toLowerCase();
  if (wordCount(value) >= minWords) score += 25;
  else messages.push("too short");
  if (refs.length > 0 || lowered.includes("evidence_gap")) score += 25;
  else messages.push("missing evidence");
  if (hasSpecificNumbers(value)) score += 10;
  if (/(small businesses|startups|everyone|anyone|all companies|businesses and startups)/i.test(value)) {
    score -= 30;
    messages.push("generic wording");
  }
  return {
    name,
    score: Math.max(0, Math.min(100, score)),
    passed: false,
    message: messages.join(", ") || "specific and evidenced",
  };
}

function evaluateGtmQuality(assets: GeneratedAssetRow[]): GTMPackQualityRow {
  const icp = assetContent(assets, "icp");
  const wtp = assetContent(assets, "decision_rules");
  const competitor = assetContent(assets, "competitor_gaps");
  const positioning = assetContent(assets, "landing_copy");
  const outreach = assetContent(assets, "outreach");
  const landing = positioning;
  const roadmap = assetContent(assets, "roadmap");

  const sectionScores = [
    scoreQualityText("icp", icp, assetRefs(assets, "icp"), 14),
    scoreQualityText("wtp", wtp, assetRefs(assets, "decision_rules"), 8),
    scoreQualityText("competitor_gap", competitor, assetRefs(assets, "competitor_gaps"), 10),
    scoreQualityText("positioning", positioning, assetRefs(assets, "landing_copy"), 8),
    scoreQualityText("outreach", outreach, assetRefs(assets, "outreach"), 14),
    scoreQualityText("landing", landing, assetRefs(assets, "landing_copy"), 8),
    scoreQualityText("roadmap", roadmap, assetRefs(assets, "roadmap"), 22),
  ];

  for (const section of sectionScores) {
    const lowered = (
      section.name === "icp" ? icp :
      section.name === "wtp" ? wtp :
      section.name === "competitor_gap" ? competitor :
      section.name === "positioning" ? positioning :
      section.name === "outreach" ? outreach :
      section.name === "landing" ? landing :
      roadmap
    ).toLowerCase();

    if (section.name === "wtp" && !/(would pay|willingness|budget|pricing|\$|\/mo|paid|weak)/i.test(lowered)) {
      section.score = Math.max(0, section.score - 25);
      section.message = `${section.message}; weak WTP language`;
    }
    if (section.name === "competitor_gap" && !/(miss|lack|without|but|wedge|gap|generic)/i.test(lowered)) {
      section.score = Math.max(0, section.score - 20);
      section.message = `${section.message}; not actionable`;
    }
    if (section.name === "outreach") {
      const hasSpam = /(guaranteed\s+\d+x|scraped your|know you need|keep following up|final chance)/i.test(lowered);
      const hasOptOut = /(reply stop|not relevant|no worries|not the right person)/i.test(lowered);
      if (hasSpam) {
        section.score = 0;
        section.message = "spam patterns";
      } else if (!hasOptOut) {
        section.score = Math.max(0, section.score - 20);
        section.message = `${section.message}; missing opt-out`;
      }
    }
    if (section.name === "roadmap" && /(complete saas|100 customers|expand globally)/i.test(lowered)) {
      section.score = Math.max(0, section.score - 45);
      section.message = `${section.message}; unrealistic plan`;
    }
    section.passed = section.score >= 70;
  }

  const missingEvidence = majorQualitySections.filter((name) => {
    const assetType = name === "competitor_gap" ? "competitor_gaps" : name === "wtp" ? "decision_rules" : name === "positioning" || name === "landing" ? "landing_copy" : name;
    return assetRefs(assets, assetType).length === 0;
  });
  const blockers = sectionScores.filter((section) => !section.passed).map((section) => `${section.name}: ${section.message}`);
  if (missingEvidence.length > 0) {
    blockers.push(`missing evidence_refs or evidence_gap for: ${missingEvidence.join(", ")}`);
  }

  let score = Math.round(sectionScores.reduce((total, section) => total + section.score, 0) / sectionScores.length);
  if (blockers.length > 0) score = Math.min(score, 79);
  const status = score >= 80 && blockers.length === 0 ? "ready" : score === 0 ? "draft" : "needs_revision";
  return {
    score,
    status,
    sectionScores,
    blockers,
    warnings: sectionScores.filter((section) => section.passed && section.score < 82).map((section) => `${section.name}: ${section.message}`),
  };
}

function buildEvidenceRows(idea: string, niche?: string): EvidenceRow[] {
  const target = niche?.trim() || "the first reachable ICP";
  const sourceIdea = idea.trim();

  return [
    {
      id: `ev_${randomUUID().slice(0, 8)}`,
      source: "CueIdea signal draft",
      proofTier: proofTierFor("direct"),
      summary: `Initial demand signal says "${sourceIdea}" should be tested against ${target} before build work.`,
      confidence: 82,
      freshness: "just now",
      actionRefs: ["A-101", "A-102"],
      quote: `The pain is specific enough to validate with ${target}.`,
      details: {
        excerpt: "Direct validation placeholder created by the local Sentinel run until the CueIdea Bridge is connected live.",
        methodology: "Local run generation maps the idea into proof tiers, then requires live evidence before production decisions.",
        tags: ["direct proof", "pain", "validation"],
      },
    },
    {
      id: `ev_${randomUUID().slice(0, 8)}`,
      source: "WTP hypothesis",
      proofTier: proofTierFor("direct"),
      summary: `The first paid test should ask whether ${target} would pay to remove the workflow friction behind "${sourceIdea}".`,
      confidence: 74,
      freshness: "just now",
      actionRefs: ["A-101"],
      details: {
        excerpt: "WTP is treated as a hypothesis, not proof, until interviews or pricing signals are attached.",
        methodology: "Sentinel marks WTP as required before a build verdict can pass.",
        tags: ["wtp", "pricing", "interview"],
      },
    },
    {
      id: `ev_${randomUUID().slice(0, 8)}`,
      source: "Competitor gap hypothesis",
      proofTier: proofTierFor("adjacent"),
      summary: `Alternatives likely exist, so Sentinel should look for a narrow wedge where generic tools do not serve ${target}.`,
      confidence: 66,
      freshness: "just now",
      actionRefs: ["A-102", "A-103"],
      details: {
        excerpt: "Adjacent proof only; useful for positioning but not enough for a build decision alone.",
        methodology: "Local run creates the competitor research slot that Sprint 5 will replace with live sources.",
        tags: ["competitor gap", "adjacent proof"],
      },
    },
    {
      id: `ev_${randomUUID().slice(0, 8)}`,
      source: "Execution risk scan",
      proofTier: proofTierFor("supporting"),
      summary: "External contact, browser actions, shell commands, and code changes remain blocked or approval-gated.",
      confidence: 90,
      freshness: "just now",
      actionRefs: ["A-103", "A-104"],
      details: {
        excerpt: "The action plan can create local files and drafts, but high-impact work remains disabled in v1.",
        methodology: "Risk is derived from AgentOps Firewall v0 policy.",
        tags: ["firewall", "risk", "policy"],
      },
    },
  ];
}

function buildActionsRows(idea: string, evidenceRows: EvidenceRow[], slug: string): ActionRow[] {
  const directRefs = evidenceRows.filter((row) => row.proofTier === "direct").map((row) => row.id);
  const allRefs = evidenceRows.map((row) => row.id);

  return [
    {
      id: "A-101",
      tool: "prepare_email_draft",
      title: "Draft outreach to validate WTP",
      intent: "Validate interest from target ICP",
      risk: "medium",
      approvalStatus: "pending",
      requiresApproval: true,
      dryRun: {
        whyNeeded: "Test willingness to pay before broader build work.",
        preview: {
          subject: `Quick question about ${idea}`,
          body: "Draft only: I am validating this workflow problem and would value 10 minutes of feedback. Reply stop if not relevant.",
        },
        evidenceUsed: directRefs,
      },
      sourceNotes: ["Direct pain required", "WTP must be validated"],
    },
    {
      id: "A-102",
      tool: "create_file",
      title: "Write GTM Pack sections",
      intent: "Persist a local first-customer pack",
      risk: "low",
      approvalStatus: "not_required",
      requiresApproval: false,
      dryRun: {
        whyNeeded: "Create a portable pack for review and handoff.",
        preview: {
          path: `./data/generated_projects/${slug}/00_VERDICT.md`,
          content: "Niche down first, build only after WTP proof.",
        },
        evidenceUsed: allRefs,
      },
      sourceNotes: ["Allowed path only", "Evidence referenced"],
    },
    {
      id: "A-103",
      tool: "send_email",
      title: "Send pilot invite",
      intent: "External contact",
      risk: "high",
      approvalStatus: "blocked",
      blocked: true,
      requiresApproval: true,
      dryRun: {
        whyNeeded: "Blocked in v1; drafts only.",
        preview: {
          to: "not executed",
          subject: "Pilot invitation",
          body: "Blocked because v1 does not send email.",
        },
        evidenceUsed: directRefs.slice(0, 1),
      },
      sourceNotes: ["V1-disabled action", "Would contact an external person"],
    },
    {
      id: "A-104",
      tool: "create_folder",
      title: "Create generated project folder",
      intent: "Store local project docs",
      risk: "low",
      approvalStatus: "not_required",
      requiresApproval: false,
      dryRun: {
        whyNeeded: "Create the project root before writing docs.",
        preview: {
          path: `./data/generated_projects/${slug}`,
        },
        evidenceUsed: allRefs,
      },
      sourceNotes: ["Allowed path only", "Project root"],
    },
  ];
}

function buildGeneratedAssets(
  idea: string,
  evidenceRows: EvidenceRow[],
  slug: string,
  imported?: NormalizedCueIdeaImport,
  prospectSources: ProspectSourceRow[] = [],
): GeneratedAssetRow[] {
  const refs = evidenceRows.map((row) => row.id);
  const createdAt = nowIso();
  const base = `data/generated_projects/${slug}`;
  const evidenceSummary = evidenceRows.slice(0, 8).map((row) => `- ${row.id}: ${row.summary}`).join("\n") || "- No evidence attached yet.";
  const wtpRows = evidenceRows.filter((row) => row.details.tags.includes("wtp") || row.details.tags.includes("pricing"));
  const gapRows = evidenceRows.filter((row) => row.details.tags.some((tag) => tag.includes("competitor")));
  const report = buildCueIdeaReportSummary(imported, createdAt);
  const sourceLines = prospectSources.map((source) => `- ${source.label} (${source.sourceType}): ${source.whyRelevant}`).join("\n");

  return [
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "verdict",
      title: "00_VERDICT.md",
      filePath: `${base}/00_VERDICT.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# Executive Verdict\n\nIdea: ${idea}\n\nDecision: niche_down\n\n${report?.executiveSummary || "Build only after direct WTP proof is confirmed."}\n\n## Decision discipline\n\nBuild only after WTP and reachable ICP proof are confirmed.\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "evidence",
      title: "01_EVIDENCE.md",
      filePath: `${base}/01_EVIDENCE.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# Evidence\n\n${evidenceSummary}\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "icp",
      title: "02_ICP.md",
      filePath: `${base}/02_ICP.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# ICP\n\n${report?.icp || `Start with the narrowest buyer group that appears in direct evidence for: ${idea}.`}\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "competitor_gaps",
      title: "03_COMPETITOR_GAPS.md",
      filePath: `${base}/03_COMPETITOR_GAPS.md`,
      evidenceRefs: gapRows.map((row) => row.id).length > 0 ? gapRows.map((row) => row.id) : refs,
      createdAt,
      content: `# Competitor Gaps\n\n${report?.competitorLandscape || gapRows.map((row) => `- ${row.summary}`).join("\n") || "- Attach competitor complaints before a build verdict."}\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "landing_copy",
      title: "04_LANDING_PAGE_COPY.md",
      filePath: `${base}/04_LANDING_PAGE_COPY.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# Landing Page Copy\n\n${report?.positioning ? `${report.positioning}\n\n` : ""}Headline: Solve the painful workflow behind ${idea} for the narrowest proven ICP.\n\nCTA: Join the validation pilot.\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "outreach",
      title: "05_OUTREACH_MESSAGES.md",
      filePath: `${base}/05_OUTREACH_MESSAGES.md`,
      evidenceRefs: refs,
      createdAt,
      content: "# Outreach Messages\n\nDraft only. User approval required before any external contact.\n",
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "interview_script",
      title: "06_INTERVIEW_SCRIPT.md",
      filePath: `${base}/06_INTERVIEW_SCRIPT.md`,
      evidenceRefs: refs,
      createdAt,
      content: "# Interview Script\n\nAsk about current workaround, cost of the pain, existing alternatives, urgency, and willingness to pay.\n",
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "roadmap",
      title: "07_7_DAY_ROADMAP.md",
      filePath: `${base}/07_7_DAY_ROADMAP.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# 7-Day Validation Roadmap\n\n${report?.distribution ? `${report.distribution}\n\n` : ""}Day 1-2: interviews. Day 3-4: landing test. Day 5-6: pricing test. Day 7: build / pivot / kill review.\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "watchlist",
      title: "08_WATCHLIST.md",
      filePath: `${base}/08_WATCHLIST.md`,
      evidenceRefs: refs,
      createdAt,
      content: "# Watchlist\n\nTrack competitor complaints, WTP phrases, direct buyer quotes, and community movement.\n",
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "decision_rules",
      title: "09_DECISION_RULES.md",
      filePath: `${base}/09_DECISION_RULES.md`,
      evidenceRefs: wtpRows.map((row) => row.id).length > 0 ? wtpRows.map((row) => row.id) : refs,
      createdAt,
      content: `# Decision Rules\n\n${report?.pricing ? `${report.pricing}\n\n` : ""}Kill if no direct pain after 5 interviews. Pivot if pain exists but WTP stays weak. Build only if WTP and reachable ICP are proven.\n`,
    },
    {
      id: `asset_${randomUUID().slice(0, 8)}`,
      assetType: "prospect_sources",
      title: "10_PROSPECT_SOURCES.md",
      filePath: `${base}/10_PROSPECT_SOURCES.md`,
      evidenceRefs: refs,
      createdAt,
      content: `# Prospect Sources\n\n${sourceLines || "- No prospect sources extracted yet."}\n`,
    },
  ];
}

function seedRun(): SentinelRunRecord {
  const createdAt = "2025-05-18T14:27:00.000Z";
  const run: SentinelRunRecord = {
    id: runSummary.runId,
    userId: DEFAULT_USER_ID,
    inputIdea: runSummary.title,
    niche: "Manufacturing segment",
    depth: "standard",
    status: "ready_for_approval",
    verdict: "niche_down",
    confidence: runSummary.confidence,
    riskScore: runSummary.riskScore,
    riskLabel: runSummary.riskLabel,
    createdAt,
    updatedAt: createdAt,
    summary: clone(runSummary),
    stages: runStages.map((stage) => ({ ...stage, active: stage.key === "firewall" })),
    agents: clone(agents),
    evidence: clone(evidence),
    actions: clone(actions),
    generatedAssets: buildGeneratedAssets(runSummary.title, evidence, "ai-invoice-chasing"),
    watchlist: buildWatchlistRows(runSummary.title, evidence, createdAt),
    traceRecords: [
      {
        id: "trace_seed_started",
        eventType: "run_started",
        message: "Idea received and evidence capture initiated.",
        createdAt,
      },
      {
        id: "trace_seed_decision",
        eventType: "decision_created",
        message: "Debate returned niche down because WTP was present but the wedge is still narrow.",
        createdAt,
      },
      {
        id: "trace_seed_action",
        eventType: "action_proposed",
        message: "Folder creation and draft-only outreach were proposed before execution.",
        createdAt,
      },
    ],
    cost: {
      currency: "USD",
      totalCents: 0,
      lines: [],
      note: "",
    },
    feedback: [],
    prospectSources: buildProspectSources(runSummary.title, evidence),
    gtmQuality: evaluateGtmQuality(buildGeneratedAssets(runSummary.title, evidence, "ai-invoice-chasing")),
    project: clone(projects[0]),
  };
  run.cost = estimateRunCost(run);
  return run;
}

function normalizeRun(run: SentinelRunRecord): SentinelRunRecord {
  return {
    ...run,
    cost: run.cost && run.cost.lines?.length > 0 ? run.cost : estimateRunCost(run),
    feedback: Array.isArray(run.feedback) ? run.feedback : [],
    watchlist: Array.isArray(run.watchlist) ? run.watchlist : buildWatchlistRows(run.inputIdea, run.evidence, run.updatedAt || run.createdAt),
    prospectSources: Array.isArray(run.prospectSources) ? run.prospectSources : buildProspectSources(run.inputIdea, run.evidence),
    gtmQuality: run.gtmQuality || evaluateGtmQuality(run.generatedAssets),
  };
}

async function readState(): Promise<RunState> {
  try {
    const raw = await readFile(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw) as RunState;
    if (parsed.version === 1 && Array.isArray(parsed.runs)) {
      return { version: 1, runs: parsed.runs.map(normalizeRun) };
    }
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code !== "ENOENT") {
      console.warn("Sentinel local store could not be read; recreating seed state.", error);
    }
  }

  const state: RunState = { version: 1, runs: [seedRun()] };
  await writeState(state);
  return state;
}

async function writeState(state: RunState) {
  await mkdir(path.dirname(STORE_PATH), { recursive: true });
  await writeFile(STORE_PATH, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function supabaseConfig() {
  if (process.env.SENTINEL_ENABLE_SUPABASE_SYNC === "false") return null;
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return { url: url.replace(/\/$/, ""), key };
}

async function supabaseRequest(table: string, init: RequestInit, query = "") {
  const config = supabaseConfig();
  if (!config) return;

  const response = await fetch(`${config.url}/rest/v1/${table}${query}`, {
    ...init,
    headers: {
      apikey: config.key,
      authorization: `Bearer ${config.key}`,
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Supabase ${table} request failed: ${response.status} ${body}`);
  }
}

async function upsertRows(table: string, rows: Record<string, unknown>[]) {
  if (rows.length === 0) return;
  await supabaseRequest(table, {
    method: "POST",
    headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify(rows),
  }, "?on_conflict=id");
}

function evidenceType(row: EvidenceRow) {
  if (row.details.tags.includes("wtp")) return "wtp";
  if (row.details.tags.includes("pricing")) return "pricing";
  if (row.details.tags.includes("competitor complaint")) return "competitor_complaint";
  if (row.proofTier === "direct") return "direct_proof";
  if (row.proofTier === "adjacent") return "adjacent_proof";
  return "community_signal";
}

function dryRunFor(action: ActionRow) {
  return {
    action: action.tool,
    risk: action.risk,
    why_needed: action.dryRun.whyNeeded,
    evidence_used: action.dryRun.evidenceUsed,
    preview: action.dryRun.preview,
    requires_approval: action.requiresApproval,
  };
}

function traceEventForSupabase(eventType: string) {
  const allowed = new Set([
    "run_started",
    "evidence_recorded",
    "decision_created",
    "action_proposed",
    "firewall_reviewed",
    "approval_recorded",
    "action_executed",
    "asset_generated",
    "run_completed",
    "run_failed",
  ]);
  if (allowed.has(eventType)) return eventType;
  if (eventType === "cueidea_imported") return "evidence_recorded";
  if (eventType === "feedback_recorded" || eventType === "watchlist_updated" || eventType === "paid_quote_prepared") return "approval_recorded";
  return "evidence_recorded";
}

async function syncRunToSupabase(run: SentinelRunRecord) {
  if (!supabaseConfig()) return;

  try {
    await upsertRows("agent_runs", [
      {
        id: run.id,
        user_id: run.userId,
        input_idea: run.inputIdea,
        status: run.status,
        verdict: run.verdict,
        confidence: run.confidence / 100,
        risk_score: run.riskScore,
        metadata: { depth: run.depth, niche: run.niche, source: "apps/web", cost: run.cost },
        created_at: run.createdAt,
        updated_at: run.updatedAt,
      },
    ]);

    await Promise.all([
      upsertRows("evidence_items", run.evidence.map((row) => ({
        id: row.id,
        run_id: run.id,
        source: row.source,
        url: row.url || null,
        quote: row.quote || null,
        summary: row.summary,
        confidence: row.confidence / 100,
        freshness_score: 1,
        relevance_score: row.confidence / 100,
        evidence_type: evidenceType(row),
        metadata: { proof_tier: row.proofTier, details: row.details, action_refs: row.actionRefs },
        payload: row,
      }))),
      upsertRows("decision_plans", [
        {
          id: `plan_${run.id}`,
          run_id: run.id,
          verdict: run.verdict,
          goal: run.inputIdea,
          reasoning_summary: "Local Sentinel run created a niche-down verdict until live research evidence is attached.",
          confidence: run.confidence / 100,
          risk_score: run.riskScore,
          raw_json: { summary: run.summary, stages: run.stages },
        },
      ]),
      upsertRows("agent_actions", run.actions.map((action) => ({
        id: `${run.id}_${action.id}`,
        run_id: run.id,
        action_type: action.tool,
        tool: action.tool,
        intent: action.intent,
        input_json: action.dryRun.preview,
        expected_output: action.title,
        risk_level: action.risk,
        requires_approval: action.requiresApproval,
        approval_status: action.approvalStatus,
        dry_run_json: dryRunFor(action),
        evidence_refs: action.dryRun.evidenceUsed,
      }))),
      upsertRows("generated_assets", run.generatedAssets.map((asset) => ({
        id: asset.id,
        run_id: run.id,
        asset_type: asset.assetType,
        title: asset.title,
        content: asset.content,
        file_path: asset.filePath || null,
        evidence_refs: asset.evidenceRefs,
        created_at: asset.createdAt,
      }))),
      upsertRows("trace_records", run.traceRecords.map((trace) => ({
        id: trace.id,
        user_id: run.userId,
        run_id: run.id,
        event_type: traceEventForSupabase(trace.eventType),
        payload: { message: trace.message, action_id: trace.actionId || null, original_event_type: trace.eventType },
        input_snapshot: {},
        decision_snapshot: null,
        action_snapshot: trace.actionId ? { action_id: trace.actionId } : null,
        output_snapshot: null,
        timestamp: trace.createdAt,
      }))),
      upsertRows("firewall_policies", firewallPolicies.map((policy) => ({
        id: `pol_${policy.tool}`,
        tool_name: policy.tool,
        risk_level: policy.risk,
        auto_allowed: policy.autoAllowed,
        requires_user_approval: policy.approval,
        v1_disabled: policy.disabled,
        policy_json: { scope: policy.scope },
      }))),
    ]);
  } catch (error) {
    console.warn("Sentinel Supabase sync skipped after failure.", error);
  }
}

async function syncApprovalToSupabase(run: SentinelRunRecord, action: ActionRow, trace: TraceLogRow) {
  if (!supabaseConfig()) return;

  try {
    await Promise.all([
      supabaseRequest(
        "agent_actions",
        {
          method: "PATCH",
          headers: { Prefer: "return=minimal" },
          body: JSON.stringify({ approval_status: action.approvalStatus }),
        },
        `?id=eq.${encodeURIComponent(`${run.id}_${action.id}`)}&run_id=eq.${encodeURIComponent(run.id)}`,
      ),
      upsertRows("trace_records", [
        {
          id: trace.id,
          user_id: run.userId,
          run_id: run.id,
          event_type: trace.eventType,
          payload: { message: trace.message, action_id: trace.actionId || action.id },
          input_snapshot: {},
          decision_snapshot: null,
          action_snapshot: { action_id: action.id, approval_status: action.approvalStatus },
          output_snapshot: null,
          timestamp: trace.createdAt,
        },
      ]),
    ]);
  } catch (error) {
    console.warn("Sentinel Supabase approval sync skipped after failure.", error);
  }
}

export async function listRuns() {
  const state = await readState();
  return clone(state.runs);
}

export async function listRunsForUser(userId?: string) {
  const state = await readState();
  const runs = userId ? state.runs.filter((item) => item.userId === userId) : state.runs;
  return clone(runs);
}

export async function getRun(runId: string, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  return run ? clone(run) : null;
}

function boardCard(
  id: string,
  title: string,
  description: string,
  meta: string,
  href: string,
  tone: ExecutionBoardColumnRow["cards"][number]["tone"] = "neutral",
) {
  return { id, title, description, meta, href, tone };
}

export async function getExecutionBoard(): Promise<ExecutionBoardColumnRow[]> {
  const runs = await listRuns();

  const ideaCards = runs.map((run) =>
    boardCard(
      `idea_${run.id}`,
      run.inputIdea,
      run.niche || run.depth,
      run.summary.startedAt,
      `/dashboard/agents/${run.id}`,
    ),
  );
  const packCards = runs
    .filter((run) => run.generatedAssets.length > 0)
    .map((run) =>
      boardCard(
        `pack_${run.id}`,
        run.project.name,
        `${run.generatedAssets.length} assets generated`,
        run.project.updatedAt,
        `/dashboard/generated-projects/${run.project.id}`,
        "good",
      ),
    );
  const approvalCards = runs.flatMap((run) =>
    run.actions
      .filter((action) => action.approvalStatus === "pending")
      .map((action) =>
        boardCard(
          `approval_${run.id}_${action.id}`,
          action.title,
          action.intent,
          action.risk,
          `/dashboard/agents/${run.id}`,
          "warn",
        ),
      ),
  );
  const outreachCards = runs.flatMap((run) =>
    run.actions
      .filter((action) => action.tool === "prepare_email_draft")
      .map((action) =>
        boardCard(
          `outreach_${run.id}_${action.id}`,
          action.title,
          action.approvalStatus,
          action.requiresApproval ? "approval required" : "draft ready",
          `/dashboard/agents/${run.id}`,
          action.approvalStatus === "approved" ? "good" : "warn",
        ),
      ),
  );
  const interviewCards = runs.flatMap((run) =>
    run.watchlist
      .filter((item) => item.status === "interview" || item.signalType === "wtp")
      .map((item) =>
        boardCard(
          `interview_${run.id}_${item.id}`,
          item.label,
          item.summary,
          item.status,
          `/dashboard/agents/${run.id}`,
          item.status === "interview" ? "good" : "warn",
        ),
      ),
  );
  const monitoringCards = runs.flatMap((run) =>
    run.watchlist
      .filter((item) => item.status === "monitoring" || item.status === "needs_review")
      .map((item) =>
        boardCard(
          `watch_${run.id}_${item.id}`,
          item.label,
          item.source,
          item.status,
          `/dashboard/agents/${run.id}`,
          item.status === "needs_review" ? "warn" : "neutral",
        ),
      ),
  );
  const decisionCards = runs.map((run) =>
    boardCard(
      `decision_${run.id}`,
      run.summary.verdict,
      `Confidence ${run.confidence}% with risk ${run.riskScore}`,
      run.verdict,
      `/dashboard/agents/${run.id}`,
      run.verdict === "build" ? "good" : run.verdict === "kill" ? "bad" : "neutral",
    ),
  );

  return [
    { id: "ideas", title: "Ideas", cards: ideaCards },
    { id: "packs", title: "Packs generated", cards: packCards },
    { id: "approval", title: "Needs approval", cards: approvalCards },
    { id: "outreach", title: "Outreach drafts", cards: outreachCards },
    { id: "interviews", title: "Interviews", cards: interviewCards },
    { id: "monitoring", title: "Monitoring", cards: monitoringCards },
    { id: "decision", title: "Decision", cards: decisionCards },
  ];
}

export async function createRun(input: CreateRunInput) {
  const state = await readState();
  const createdAt = nowIso();
  const id = runIdFromDate(new Date(createdAt));
  const idea = input.idea.trim();
  const depth: RunDepth = input.depth || "standard";
  const slug = slugify(idea);
  const evidenceRows = buildEvidenceRows(idea, input.niche);
  const actionRows = buildActionsRows(idea, evidenceRows, slug);
  const prospectSources = buildProspectSources(idea, evidenceRows);
  const assets = buildGeneratedAssets(idea, evidenceRows, slug, undefined, prospectSources);
  const traceRecords: TraceLogRow[] = [
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "run_started",
      message: "Idea received from the web dashboard.",
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "evidence_recorded",
      message: `${evidenceRows.length} evidence placeholders recorded for local review.`,
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "decision_created",
      message: "Local verdict is niche_down until live WTP evidence is attached.",
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "action_proposed",
      message: `${actionRows.length} actions proposed before execution.`,
      createdAt,
    },
  ];

  const run: SentinelRunRecord = {
    id,
    userId: input.userId || DEFAULT_USER_ID,
    inputIdea: idea,
    niche: input.niche?.trim() || undefined,
    depth,
    status: "ready_for_approval",
    verdict: "niche_down",
    confidence: depth === "deep" ? 78 : depth === "quick" ? 68 : 74,
    riskScore: depth === "deep" ? 32 : depth === "quick" ? 42 : 36,
    riskLabel: depth === "quick" ? "Moderate" : "Controlled",
    createdAt,
    updatedAt: createdAt,
    summary: {
      title: idea,
      status: "Ready for approval",
      runId: id,
      startedAt: compactDate(createdAt),
      verdict: "Niche down first",
      confidence: depth === "deep" ? 78 : depth === "quick" ? 68 : 74,
      riskScore: depth === "deep" ? 32 : depth === "quick" ? 42 : 36,
      riskLabel: depth === "quick" ? "Moderate" : "Controlled",
    },
    stages: runStages.map((stage) => ({ ...stage, detail: stage.key === "approval" ? "Pending" : stage.detail, active: stage.key === "approval" })),
    agents: clone(agents),
    evidence: evidenceRows,
    actions: actionRows,
    generatedAssets: assets,
    watchlist: buildWatchlistRows(idea, evidenceRows, createdAt),
    traceRecords,
    cost: {
      currency: "USD",
      totalCents: 0,
      lines: [],
      note: "",
    },
    feedback: [],
    prospectSources,
    gtmQuality: evaluateGtmQuality(assets),
    project: {
      id: slug,
      name: idea,
      status: "Pack generated",
      updatedAt: compactDate(createdAt),
      description: "Local Sentinel run generated a first-customer GTM pack and approval queue.",
      files: assets.map((asset) => asset.title),
    },
  };
  run.cost = estimateRunCost(run);

  state.runs = [run, ...state.runs].slice(0, 25);
  await writeState(state);
  await syncRunToSupabase(run);
  return clone(run);
}

function verdictFromCueIdea(value?: string): SentinelRunRecord["verdict"] {
  const normalized = (value || "").toLowerCase();
  if (normalized.includes("build")) return "build";
  if (normalized.includes("pivot")) return "pivot";
  if (normalized.includes("kill")) return "kill";
  if (normalized.includes("research")) return "research_more";
  return "niche_down";
}

export async function createRunFromCueIdeaImport(imported: NormalizedCueIdeaImport, input: { depth?: RunDepth; niche?: string; userId?: string } = {}) {
  const state = await readState();
  const createdAt = nowIso();
  const id = runIdFromDate(new Date(createdAt));
  const idea = imported.idea.trim();
  const depth: RunDepth = input.depth || "standard";
  const slug = slugify(`${idea}-${imported.validationId || id}`);
  const evidenceRows = imported.evidenceRows.length > 0 ? imported.evidenceRows : buildEvidenceRows(idea, input.niche);
  const actionRows = buildActionsRows(idea, evidenceRows, slug);
  const prospectSources = buildProspectSources(idea, evidenceRows, imported);
  const assets = buildGeneratedAssets(idea, evidenceRows, slug, imported, prospectSources);
  const verdict = verdictFromCueIdea(imported.verdict);
  const confidence = imported.confidence > 0 ? imported.confidence : depth === "deep" ? 72 : 64;
  const riskScore = imported.wtpCount > 0 && imported.directCount > 0 ? 34 : 48;
  const traceRecords: TraceLogRow[] = [
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "cueidea_imported",
      message: `CueIdea validation ${imported.validationId || "local JSON"} imported in read-only mode.`,
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "evidence_recorded",
      message: `${evidenceRows.length} CueIdea evidence rows normalized (${imported.directCount} direct, ${imported.adjacentCount} adjacent, ${imported.wtpCount} WTP/pricing).`,
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "decision_created",
      message: imported.summary,
      createdAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "action_proposed",
      message: `${actionRows.length} actions proposed from CueIdea evidence before execution.`,
      createdAt,
    },
  ];

  const run: SentinelRunRecord = {
    id,
    userId: input.userId || DEFAULT_USER_ID,
    inputIdea: idea,
    niche: input.niche?.trim() || undefined,
    depth,
    status: "ready_for_approval",
    verdict,
    confidence,
    riskScore,
    riskLabel: riskScore >= 45 ? "Needs proof" : "Controlled",
    createdAt,
    updatedAt: createdAt,
    summary: {
      title: idea,
      status: "CueIdea imported",
      runId: id,
      startedAt: compactDate(createdAt),
      verdict: imported.verdict || verdict.replace(/_/g, " "),
      confidence,
      riskScore,
      riskLabel: riskScore >= 45 ? "Needs proof" : "Controlled",
    },
    stages: runStages.map((stage) => ({
      ...stage,
      detail: stage.key === "evidence" ? `${evidenceRows.length} imported` : stage.key === "approval" ? "Pending" : stage.detail,
      active: stage.key === "approval",
    })),
    agents: clone(agents),
    evidence: evidenceRows,
    actions: actionRows,
    generatedAssets: assets,
    watchlist: buildWatchlistRows(idea, evidenceRows, createdAt),
    traceRecords,
    cost: {
      currency: "USD",
      totalCents: 0,
      lines: [],
      note: "",
    },
    feedback: [],
    prospectSources,
    cueideaReport: buildCueIdeaReportSummary(imported, createdAt),
    gtmQuality: evaluateGtmQuality(assets),
    project: {
      id: slug,
      name: idea,
      status: "Pack generated",
      updatedAt: compactDate(createdAt),
      description: `Read-only CueIdea import ${imported.validationId || "from local JSON"} converted into a Sentinel GTM pack.`,
      files: assets.map((asset) => asset.title),
    },
  };
  run.cost = estimateRunCost(run);

  state.runs = [run, ...state.runs].slice(0, 25);
  await writeState(state);
  await syncRunToSupabase(run);
  return clone(run);
}

export async function updateActionApproval(runId: string, actionId: string, approvalStatus: ApprovalStatus, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  if (!run) return null;

  const action = run.actions.find((item) => item.id === actionId);
  if (!action) return null;

  if (action.blocked || action.approvalStatus === "blocked") {
    action.approvalStatus = "blocked";
  } else if (action.approvalStatus === "pending" && (approvalStatus === "approved" || approvalStatus === "rejected")) {
    action.approvalStatus = approvalStatus;
  }

  run.updatedAt = nowIso();
  const trace: TraceLogRow = {
    id: `trace_${randomUUID().slice(0, 8)}`,
    eventType: "approval_recorded",
    actionId: action.id,
    message: `${action.id} ${action.approvalStatus} by local dashboard.`,
    createdAt: run.updatedAt,
  };
  run.traceRecords = [trace, ...run.traceRecords];

  await writeState(state);
  await syncApprovalToSupabase(run, action, trace);
  return clone(run);
}

export async function recordFeedback(runId: string, input: CreateFeedbackInput, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  if (!run) return null;

  const createdAt = nowIso();
  const feedback: FeedbackEntryRow = {
    id: `fb_${randomUUID().slice(0, 8)}`,
    targetType: input.targetType,
    targetId: input.targetId,
    rating: input.rating,
    note: input.note?.trim() || undefined,
    createdAt,
  };
  const trace: TraceLogRow = {
    id: `trace_${randomUUID().slice(0, 8)}`,
    eventType: "feedback_recorded",
    actionId: input.targetType === "action" ? input.targetId : undefined,
    message: `${input.targetType} ${input.targetId} marked ${input.rating}${feedback.note ? `: ${feedback.note}` : "."}`,
    createdAt,
  };

  run.feedback = [feedback, ...(run.feedback || [])];
  run.traceRecords = [trace, ...run.traceRecords];
  run.updatedAt = createdAt;

  await writeState(state);

  if (supabaseConfig()) {
    await upsertRows("trace_records", [
      {
        id: trace.id,
        user_id: run.userId,
        run_id: run.id,
        event_type: "approval_recorded",
        payload: { message: trace.message, feedback },
        input_snapshot: {},
        decision_snapshot: null,
        action_snapshot: input.targetType === "action" ? { action_id: input.targetId, feedback } : null,
        output_snapshot: { feedback },
        timestamp: trace.createdAt,
      },
    ]).catch((error) => {
      console.warn("Sentinel Supabase feedback sync skipped after failure.", error);
    });
  }

  return clone(run);
}

export async function updateWatchlistItem(runId: string, itemId: string, status: WatchlistStatus, note?: string, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  if (!run) return null;

  const item = run.watchlist.find((entry) => entry.id === itemId);
  if (!item) return null;

  const updatedAt = nowIso();
  item.status = status;
  item.updatedAt = updatedAt;
  item.note = note?.trim() || item.note;

  const trace: TraceLogRow = {
    id: `trace_${randomUUID().slice(0, 8)}`,
    eventType: "watchlist_updated",
    message: `${item.label} moved to ${status}${item.note ? `: ${item.note}` : "."}`,
    createdAt: updatedAt,
  };

  run.traceRecords = [trace, ...run.traceRecords];
  run.updatedAt = updatedAt;

  await writeState(state);
  return clone(run);
}

export async function preparePaidRunQuote(runId: string, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  if (!run) return null;

  const updatedAt = nowIso();
  run.paidQuote = buildPaidRunQuote(run);
  run.updatedAt = updatedAt;

  const trace: TraceLogRow = {
    id: `trace_${randomUUID().slice(0, 8)}`,
    eventType: "paid_quote_prepared",
    message: `${run.paidQuote.label} prepared with payment disabled for v1.`,
    createdAt: updatedAt,
  };
  run.traceRecords = [trace, ...run.traceRecords];

  await writeState(state);
  return clone(run);
}

function generatedProjectsRoot() {
  return path.resolve(process.cwd(), "../../data/generated_projects");
}

function resolveGeneratedAssetPath(filePath: string) {
  const root = generatedProjectsRoot();
  const normalized = filePath.replace(/\\/g, "/").replace(/^\.\//, "");
  const prefix = "data/generated_projects/";
  if (!normalized.startsWith(prefix)) {
    throw new Error("Generated asset path must stay inside data/generated_projects.");
  }

  const relative = normalized.slice(prefix.length);
  const resolved = path.resolve(root, relative);
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
    throw new Error("Generated asset path escapes data/generated_projects.");
  }
  return resolved;
}

export async function executeGeneratedProject(runId: string, userId?: string) {
  const state = await readState();
  const run = state.runs.find((item) => item.id === runId && (!userId || item.userId === userId));
  if (!run) return null;

  const generatedAt = nowIso();
  const writtenFiles: string[] = [];

  for (const asset of run.generatedAssets) {
    if (!asset.filePath) continue;
    const filePath = resolveGeneratedAssetPath(asset.filePath);
    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, asset.content, "utf8");
    writtenFiles.push(asset.filePath);
  }

  const tracePath = path.resolve(generatedProjectsRoot(), run.project.id, "trace.json");
  if (!tracePath.startsWith(`${generatedProjectsRoot()}${path.sep}`)) {
    throw new Error("Trace export path escapes data/generated_projects.");
  }
  await mkdir(path.dirname(tracePath), { recursive: true });
  await writeFile(tracePath, `${JSON.stringify({ run, exportedAt: generatedAt }, null, 2)}\n`, "utf8");
  writtenFiles.push(`data/generated_projects/${run.project.id}/trace.json`);

  run.project = {
    ...run.project,
    status: "Files written locally",
    updatedAt: compactDate(generatedAt),
    files: Array.from(new Set([...run.project.files, ...run.generatedAssets.map((asset) => asset.title), "trace.json"])),
  };
  run.updatedAt = generatedAt;

  const traces: TraceLogRow[] = [
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "action_executed",
      message: `Generated project folder written inside data/generated_projects/${run.project.id}.`,
      createdAt: generatedAt,
    },
    {
      id: `trace_${randomUUID().slice(0, 8)}`,
      eventType: "asset_generated",
      message: `${writtenFiles.length} local files created for the GTM pack.`,
      createdAt: generatedAt,
    },
  ];
  run.traceRecords = [...traces, ...run.traceRecords];

  await writeState(state);
  return clone(run);
}
