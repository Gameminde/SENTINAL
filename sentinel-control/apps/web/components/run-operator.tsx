"use client";

import { Play, RefreshCw } from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { EvidenceLedgerPanel, FirewallReviewPanel } from "@/components/interactive";
import { FeedbackControls } from "@/components/feedback-controls";
import { GeneratePackButton } from "@/components/generate-pack-button";
import { ExportButton } from "@/components/shared";
import { Chip, Metric, SectionBand } from "@/components/ui";
import type { RunDepth, SentinelRunRecord } from "@/lib/types";

export function RunOperator({ initialRuns }: { initialRuns: SentinelRunRecord[] }) {
  const [runs, setRuns] = useState(initialRuns);
  const [selectedRunId, setSelectedRunId] = useState(initialRuns[0]?.id ?? "");
  const [idea, setIdea] = useState("AI invoice chasing for freelancers");
  const [niche, setNiche] = useState("Freelancers and small agencies");
  const [depth, setDepth] = useState<RunDepth>("standard");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0],
    [runs, selectedRunId],
  );

  function replaceRun(updatedRun: SentinelRunRecord) {
    setRuns((current) => current.map((run) => (run.id === updatedRun.id ? updatedRun : run)));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ idea, niche, depth }),
      });
      const payload = (await response.json()) as { run?: SentinelRunRecord; error?: string };

      if (!response.ok || !payload.run) {
        throw new Error(payload.error || "Run creation failed.");
      }

      setRuns((current) => [payload.run!, ...current.filter((run) => run.id !== payload.run!.id)]);
      setSelectedRunId(payload.run.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Run creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!selectedRun) {
    return (
      <div className="page">
        <section className="panel">
          <SectionBand eyebrow="Agents" title="Run the Sentinel GTM Operator">
            <p className="page-copy">No local run state exists yet.</p>
          </SectionBand>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="hero">
        <section className="hero-panel">
          <div className="eyebrow">Agents</div>
          <h1 className="page-title">Run the Sentinel GTM Operator</h1>
          <p className="page-copy">
            Create a local Sentinel run, generate the evidence ledger and GTM pack outline, then approve or reject actions through the Firewall queue.
          </p>

          <form className="run-form" onSubmit={handleSubmit}>
            <label>
              <span>Idea</span>
              <input
                className="input"
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                minLength={8}
                required
              />
            </label>
            <label>
              <span>Niche</span>
              <input className="input" value={niche} onChange={(event) => setNiche(event.target.value)} />
            </label>
            <label>
              <span>Depth</span>
              <select className="select" value={depth} onChange={(event) => setDepth(event.target.value as RunDepth)}>
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </label>
            <button className="primary-btn" type="submit" disabled={isSubmitting}>
              {isSubmitting ? <RefreshCw size={16} /> : <Play size={16} />}
              <span>{isSubmitting ? "Creating run" : "Run analysis"}</span>
            </button>
          </form>

          {error ? <div className="inline-alert">{error}</div> : null}

          <div className="progress">
            {selectedRun.stages.map((stage, index) => (
              <div className="progress-step" data-active={stage.active ? "true" : "false"} key={stage.key}>
                <strong>
                  {index + 1}. {stage.label}
                </strong>
                <span>{stage.detail}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Current run</div>
              <h2>{selectedRun.summary.title}</h2>
            </div>
            <Chip tone="neutral">#{selectedRun.id}</Chip>
          </div>
          <div className="metric-grid metric-grid-compact">
            <Metric label="Verdict" value={selectedRun.summary.verdict} sub={selectedRun.status.replace(/_/g, " ")} />
            <Metric label="Confidence" value={`${selectedRun.confidence}%`} sub={selectedRun.depth} />
            <Metric label="Risk" value={`${selectedRun.riskScore}`} sub={selectedRun.riskLabel} />
            <Metric label="Actions" value={`${selectedRun.actions.length}`} sub="firewall reviewed" />
          </div>

          <div className="run-switcher" aria-label="Recent runs">
            {runs.slice(0, 5).map((run) => (
              <button
                className="run-chip"
                data-active={run.id === selectedRun.id ? "true" : "false"}
                key={run.id}
                onClick={() => setSelectedRunId(run.id)}
                type="button"
              >
                <span>{run.summary.title}</span>
                <small>{run.summary.startedAt}</small>
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="workspace-grid">
        <section className="panel">
          <EvidenceLedgerPanel evidenceItems={selectedRun.evidence} />
        </section>
        <section className="panel">
          <FirewallReviewPanel
            actionItems={selectedRun.actions}
            feedbackItems={selectedRun.feedback}
            runId={selectedRun.id}
            onRunUpdate={replaceRun}
          />
        </section>
      </div>

      <section className="columns-2">
        <section className="panel">
          <SectionBand
            eyebrow="Pack"
            title="Generated assets"
            action={
              <div className="section-actions">
                <GeneratePackButton run={selectedRun} onRunUpdate={replaceRun} />
                <ExportButton label="Export JSON" />
              </div>
            }
          >
            <div className="list">
              {selectedRun.generatedAssets.map((asset) => (
                <div className="list-item" key={asset.id}>
                  <Link href={`/dashboard/generated-projects/${selectedRun.project.id}`}>
                    <strong>{asset.title}</strong>
                    <p>{asset.assetType} / refs {asset.evidenceRefs.length}</p>
                  </Link>
                  <FeedbackControls
                    feedback={selectedRun.feedback}
                    onRunUpdate={replaceRun}
                    runId={selectedRun.id}
                    targetId={asset.id}
                    targetType="asset"
                  />
                </div>
              ))}
            </div>
          </SectionBand>
        </section>

        <section className="panel">
          <SectionBand
            eyebrow="Trace"
            title="Run ledger"
            action={
              <Link href={`/dashboard/agents/${selectedRun.id}`} className="secondary-btn">
                Open run detail
              </Link>
            }
          >
            <div className="list">
              {selectedRun.traceRecords.slice(0, 6).map((trace) => (
                <div className="list-item" key={trace.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                    <strong>{trace.eventType}</strong>
                    <Chip tone={trace.eventType === "approval_recorded" ? "good" : "neutral"}>{new Date(trace.createdAt).toLocaleTimeString()}</Chip>
                  </div>
                  <p>{trace.message}</p>
                </div>
              ))}
            </div>
          </SectionBand>
        </section>
      </section>
    </div>
  );
}
