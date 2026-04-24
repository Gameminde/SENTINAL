import type { EvidenceRow, RunDepth } from "@/lib/types";

type AnyRecord = Record<string, unknown>;

export interface NormalizedCueIdeaImport {
  validationId?: string;
  idea: string;
  status?: string;
  verdict?: string;
  confidence: number;
  summary: string;
  evidenceRows: EvidenceRow[];
  directCount: number;
  adjacentCount: number;
  wtpCount: number;
  raw: AnyRecord;
}

export interface CueIdeaImportRequest {
  validationId?: string;
  report?: unknown;
  depth?: RunDepth;
  niche?: string;
}

function record(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(...values: unknown[]) {
  return values.map((value) => String(value || "").trim()).filter(Boolean).join(" ").trim();
}

function confidence(value: unknown, fallback = 65) {
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["high", "strong", "confirmed"].includes(normalized)) return 90;
    if (["medium", "moderate", "solid"].includes(normalized)) return 65;
    if (["low", "weak", "early"].includes(normalized)) return 35;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  const score = parsed <= 1 ? parsed * 100 : parsed;
  return Math.max(0, Math.min(100, Math.round(score)));
}

function extractReport(payload: AnyRecord): AnyRecord {
  for (const value of [payload.report, payload.result, payload.data]) {
    const candidate = record(value);
    if (Object.keys(candidate).length > 0) return candidate;
  }
  return payload;
}

function proofTier(entry: AnyRecord): EvidenceRow["proofTier"] {
  const joined = text(
    entry.proof_tier,
    entry.directness_tier,
    entry.evidence_taxonomy,
    entry.directness,
    entry.relevance,
  ).toLowerCase();
  if (joined.includes("direct")) return "direct";
  if (joined.includes("adjacent")) return "adjacent";
  return "supporting";
}

function tagsFor(entry: AnyRecord, tier: EvidenceRow["proofTier"]) {
  const joined = text(
    entry.evidence_type,
    entry.signal_kind,
    entry.what_it_proves,
    entry.summary,
    entry.title,
    entry.body,
  ).toLowerCase();
  const tags = new Set<string>();
  if (tier === "direct") tags.add("direct proof");
  if (tier === "adjacent") tags.add("adjacent proof");
  if (joined.match(/\b(wtp|willingness to pay|would pay|will pay|paid|budget)\b/)) tags.add("wtp");
  if (joined.includes("price") || joined.includes("pricing") || joined.includes("cost")) tags.add("pricing");
  if (joined.includes("competitor") || joined.includes("alternative") || joined.includes("complaint") || joined.includes("switching")) tags.add("competitor gap");
  if (joined.includes("trend") || joined.includes("growing") || joined.includes("momentum")) tags.add("trend");
  if (joined.includes("community") || joined.includes("subreddit") || joined.includes("forum")) tags.add("community");
  if (joined.includes("pain") || joined.includes("problem") || joined.includes("manual") || joined.includes("frustrated")) tags.add("pain");
  if (tags.size === 0) tags.add("cueidea");
  return Array.from(tags);
}

function collectEvidenceEntries(report: AnyRecord) {
  const market = record(report.market_analysis);
  return [
    ...list(market.evidence),
    ...list(market.pain_quotes),
    ...list(report.debate_evidence),
    ...list(report.evidence),
    ...list(report.wtp_evidence),
    ...list(report.willingness_to_pay_evidence),
    ...list(report.competitor_complaints),
  ].filter((entry) => Object.keys(record(entry)).length > 0) as AnyRecord[];
}

function evidenceRow(entry: AnyRecord, index: number, validationId?: string): EvidenceRow {
  const tier = proofTier(entry);
  const title = text(entry.post_title, entry.title, entry.keyword) || `CueIdea evidence ${index + 1}`;
  const summary = text(entry.summary) || text(entry.what_it_proves) || text(entry.insight) || text(entry.body) || title;
  const tags = tagsFor(entry, tier);

  return {
    id: String(entry.id || `cue_ev_${validationId || "local"}_${index}`),
    source: text(entry.source, entry.platform) || "CueIdea",
    proofTier: tier,
    summary,
    confidence: confidence(entry.confidence || entry.score),
    freshness: text(entry.created_at, entry.observed_at, entry.scraped_at) || "CueIdea import",
    actionRefs: ["A-101", "A-102"],
    quote: text(entry.quote, entry.pain_quote) || undefined,
    url: text(entry.url, entry.permalink) || undefined,
    details: {
      excerpt: text(entry.excerpt, entry.body, entry.what_it_proves) || summary,
      methodology: "Read-only CueIdea import normalized into Sentinel evidence rows.",
      tags,
    },
  };
}

export function normalizeCueIdeaImport(payload: unknown): NormalizedCueIdeaImport {
  const root = record(payload);
  const report = extractReport(root);
  const validationId = text(root.id, root.validation_id, report.id) || undefined;
  const idea = text(root.idea_text, root.idea, report.idea_text, report.idea, report.input_idea) || "CueIdea imported idea";
  const evidenceRows = collectEvidenceEntries(report).map((entry, index) => evidenceRow(entry, index, validationId));
  const directCount = evidenceRows.filter((row) => row.proofTier === "direct").length;
  const adjacentCount = evidenceRows.filter((row) => row.proofTier === "adjacent").length;
  const wtpCount = evidenceRows.filter((row) => row.details.tags.includes("wtp") || row.details.tags.includes("pricing")).length;

  return {
    validationId,
    idea,
    status: text(root.status, report.status) || undefined,
    verdict: text(root.verdict, report.verdict) || undefined,
    confidence: confidence(report.confidence || root.confidence, 0),
    summary: text(
      report.executive_summary,
      report.summary,
      record(report.market_analysis).pain_description,
      "CueIdea validation imported without an executive summary.",
    ),
    evidenceRows,
    directCount,
    adjacentCount,
    wtpCount,
    raw: root,
  };
}

export async function fetchCueIdeaValidation(validationId: string) {
  const url = process.env.CUEIDEA_SUPABASE_URL || process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.CUEIDEA_SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error("CueIdea Supabase env is missing. Set CUEIDEA_SUPABASE_URL and CUEIDEA_SUPABASE_SERVICE_ROLE_KEY, or paste a report JSON.");
  }

  const baseUrl = url.replace(/\/$/, "");
  const query = `${baseUrl}/rest/v1/idea_validations?select=id,user_id,idea_text,status,report,created_at&id=eq.${encodeURIComponent(validationId)}&limit=1`;
  const response = await fetch(query, {
    method: "GET",
    headers: {
      apikey: key,
      authorization: `Bearer ${key}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`CueIdea read-only fetch failed: ${response.status} ${body}`);
  }

  const rows = await response.json() as AnyRecord[];
  if (!rows[0]) {
    throw new Error("CueIdea validation was not found.");
  }
  return rows[0];
}
