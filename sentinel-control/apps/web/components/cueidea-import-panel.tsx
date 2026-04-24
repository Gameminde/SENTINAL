"use client";

import Link from "next/link";
import { RefreshCw, UploadCloud } from "lucide-react";
import { FormEvent, useState, useTransition } from "react";
import { GeneratePackButton } from "@/components/generate-pack-button";
import { Chip, Metric } from "@/components/ui";
import type { RunDepth, SentinelRunRecord } from "@/lib/types";

const sampleReport = JSON.stringify({
  validation_id: "local_sample",
  idea_text: "AI invoice chasing for freelancers",
  status: "completed",
  report: {
    verdict: "niche_down",
    confidence: 74,
    executive_summary: "Freelancers show invoice follow-up pain, but WTP needs direct interviews.",
    market_analysis: {
      evidence: [
        {
          id: "direct_1",
          source: "CueIdea sample",
          title: "Manual invoice follow-ups",
          summary: "Freelancers complain about manually chasing overdue invoices.",
          directness_tier: "direct",
          confidence: "high",
        },
      ],
    },
    wtp_evidence: [
      {
        id: "wtp_1",
        source: "CueIdea sample",
        summary: "A freelancer says they would pay for reminders that do not sound robotic.",
        directness_tier: "direct",
      },
    ],
    competitor_complaints: [
      {
        id: "gap_1",
        source: "CueIdea sample",
        summary: "Existing invoice tools send generic reminders and miss relationship tone.",
        directness_tier: "adjacent",
      },
    ],
  },
}, null, 2);

export function CueIdeaImportPanel({ recentRuns }: { recentRuns: SentinelRunRecord[] }) {
  const [validationId, setValidationId] = useState("");
  const [reportJson, setReportJson] = useState("");
  const [niche, setNiche] = useState("");
  const [depth, setDepth] = useState<RunDepth>("standard");
  const [importedRun, setImportedRun] = useState<SentinelRunRecord | null>(recentRuns[0] || null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function importCueIdea(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      const body = {
        validationId: validationId.trim() || undefined,
        report: reportJson.trim() || undefined,
        niche: niche.trim() || undefined,
        depth,
      };
      const response = await fetch("/api/cueidea/import", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = (await response.json().catch(() => null)) as { run?: SentinelRunRecord; error?: string } | null;

      if (!response.ok || !payload?.run) {
        setError(payload?.error || "CueIdea import failed.");
        return;
      }

      setImportedRun(payload.run);
    });
  }

  return (
    <div className="workspace-grid">
      <section className="panel">
        <form className="cueidea-form" onSubmit={importCueIdea}>
          <div className="section-heading">
            <div>
              <div className="eyebrow">CueIdea Bridge</div>
              <h2>Read-only import</h2>
            </div>
            <Chip tone="good">local</Chip>
          </div>

          <label>
            <span>Validation ID</span>
            <input
              className="input"
              onChange={(event) => setValidationId(event.target.value)}
              placeholder="CueIdea idea_validations.id"
              value={validationId}
            />
          </label>
          <label>
            <span>Pasted report JSON</span>
            <textarea
              className="textarea cueidea-textarea"
              onChange={(event) => setReportJson(event.target.value)}
              placeholder={sampleReport}
              value={reportJson}
            />
          </label>
          <div className="form-row-2">
            <label>
              <span>Niche</span>
              <input className="input" onChange={(event) => setNiche(event.target.value)} value={niche} />
            </label>
            <label>
              <span>Depth</span>
              <select className="select" onChange={(event) => setDepth(event.target.value as RunDepth)} value={depth}>
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </label>
          </div>
          <div className="approval-row">
            <button className="ghost-btn" onClick={() => setReportJson(sampleReport)} type="button">
              Load sample
            </button>
            <button className="primary-btn" disabled={isPending} type="submit">
              {isPending ? <RefreshCw size={16} /> : <UploadCloud size={16} />}
              <span>{isPending ? "Importing" : "Import CueIdea"}</span>
            </button>
          </div>
          {error ? <div className="inline-alert">{error}</div> : null}
        </form>
      </section>

      <section className="panel">
        {importedRun ? (
          <div className="list">
            <div className="list-item">
              <div className="approval-row">
                <strong>{importedRun.inputIdea}</strong>
                <Chip tone="neutral">{importedRun.summary.status}</Chip>
              </div>
              <div className="metric-grid metric-grid-compact">
                <Metric label="Evidence" value={`${importedRun.evidence.length}`} sub="normalized rows" />
                <Metric label="Direct" value={`${importedRun.evidence.filter((row) => row.proofTier === "direct").length}`} sub="proof rows" />
                <Metric label="WTP" value={`${importedRun.evidence.filter((row) => row.details.tags.includes("wtp")).length}`} sub="signals" />
                <Metric label="Files" value={`${importedRun.generatedAssets.length}`} sub="pack docs" />
              </div>
              <div className="approval-row">
                <Link className="secondary-btn" href={`/dashboard/agents/${importedRun.id}`}>
                  Open run
                </Link>
                <GeneratePackButton run={importedRun} onRunUpdate={setImportedRun} />
              </div>
            </div>
            {importedRun.cueideaReport ? (
              <div className="list-item">
                <div className="approval-row">
                  <strong>CueIdea report sections</strong>
                  <Chip tone="neutral">{importedRun.cueideaReport.rawSectionKeys.length} keys</Chip>
                </div>
                <p>{importedRun.cueideaReport.executiveSummary}</p>
                {importedRun.cueideaReport.icp ? <p><strong>ICP:</strong> {importedRun.cueideaReport.icp.slice(0, 280)}</p> : null}
                {importedRun.cueideaReport.pricing ? <p><strong>Pricing:</strong> {importedRun.cueideaReport.pricing.slice(0, 280)}</p> : null}
                {importedRun.cueideaReport.distribution ? <p><strong>Distribution:</strong> {importedRun.cueideaReport.distribution.slice(0, 280)}</p> : null}
              </div>
            ) : null}
            <div className="list-item">
              <div className="approval-row">
                <strong>Prospect/source extraction</strong>
                <Chip tone="neutral">{importedRun.prospectSources.length} sources</Chip>
              </div>
              <div className="source-grid">
                {importedRun.prospectSources.slice(0, 6).map((source) => (
                  <div className="source-card" key={source.id}>
                    <div className="approval-row">
                      <strong>{source.label}</strong>
                      <Chip tone="neutral">{source.sourceType}</Chip>
                    </div>
                    <p>{source.whyRelevant}</p>
                    {source.url ? <span className="page-note">{source.url}</span> : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="list">
              {importedRun.evidence.slice(0, 4).map((row) => (
                <div className="list-item" key={row.id}>
                  <div className="approval-row">
                    <strong>{row.source}</strong>
                    <Chip tone={row.proofTier === "direct" ? "good" : row.proofTier === "adjacent" ? "warn" : "neutral"}>
                      {row.proofTier}
                    </Chip>
                  </div>
                  <p>{row.summary}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state">Import a CueIdea report to create a Sentinel run.</div>
        )}
      </section>
    </div>
  );
}
