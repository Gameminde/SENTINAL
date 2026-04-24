import { notFound } from "next/navigation";
import Link from "next/link";
import { FeedbackControls } from "@/components/feedback-controls";
import { GeneratePackButton } from "@/components/generate-pack-button";
import { EvidenceLedgerPanel, FirewallReviewPanel } from "@/components/interactive";
import { ExportButton } from "@/components/shared";
import { Chip, Metric, SectionBand } from "@/components/ui";
import { getRun } from "@/lib/run-store";

export const dynamic = "force-dynamic";

function qualityTone(status: string): "neutral" | "good" | "warn" | "bad" {
  if (status === "ready") return "good";
  if (status === "draft") return "bad";
  return "warn";
}

export default async function RunDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const run = await getRun(runId);

  if (!run) {
    notFound();
  }

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Run Detail</div>
          <h1 className="page-title">{run.summary.title}</h1>
          <p className="page-copy">
            Run {run.id} is locked to evidence, risk, dry-run previews, and approval policy.
          </p>
          <div className="metric-grid">
            <Metric label="Verdict" value={run.summary.verdict} sub={run.verdict.replace(/_/g, " ")} />
            <Metric label="Confidence" value={`${run.confidence}%`} sub="weighted by direct proof" />
            <Metric label="Risk" value={`${run.riskScore}`} sub={run.riskLabel} />
            <Metric label="GTM Quality" value={`${run.gtmQuality.score}`} sub={run.gtmQuality.status.replace("_", " ")} />
          </div>
        </div>
        <div className="panel">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Approval inbox</div>
              <h2>Actions needing attention</h2>
            </div>
            <Chip tone="warn">{run.actions.filter((action) => action.approvalStatus === "pending").length} pending</Chip>
          </div>
          <FirewallReviewPanel actionItems={run.actions} feedbackItems={run.feedback} runId={run.id} compact />
        </div>
      </section>

      <section className="panel">
        <SectionBand
          eyebrow="Quality"
          title="GTM Pack Quality Gate"
          action={<Chip tone={qualityTone(run.gtmQuality.status)}>{run.gtmQuality.status.replace("_", " ")}</Chip>}
        >
          <div className="quality-grid">
            {run.gtmQuality.sectionScores.map((section) => (
              <div className="quality-card" data-pass={section.passed ? "true" : "false"} key={section.name}>
                <div className="approval-row">
                  <strong>{section.name.replace("_", " ")}</strong>
                  <Chip tone={section.passed ? "good" : "warn"}>{section.score}</Chip>
                </div>
                <p>{section.message}</p>
              </div>
            ))}
          </div>
          {run.gtmQuality.blockers.length > 0 ? (
            <div className="inline-alert">
              {run.gtmQuality.blockers.slice(0, 3).join(" / ")}
            </div>
          ) : null}
        </SectionBand>
      </section>

      <div className="workspace-grid">
        <section className="panel">
          <EvidenceLedgerPanel evidenceItems={run.evidence} />
        </section>

        <section className="panel">
          <SectionBand
            eyebrow="Pack"
            title="Generated folder preview"
            action={
              <div className="section-actions">
                <GeneratePackButton run={run} />
                <ExportButton label="Download pack" />
              </div>
            }
          >
            <div className="list">
              {run.generatedAssets.map((asset) => (
                <div className="list-item" key={asset.id}>
                  <Link href={`/dashboard/generated-projects/${run.project.id}`}>
                    <strong>{asset.title}</strong>
                    <p>{asset.assetType} / refs {asset.evidenceRefs.length}</p>
                  </Link>
                  <FeedbackControls feedback={run.feedback} runId={run.id} targetId={asset.id} targetType="asset" />
                </div>
              ))}
            </div>
          </SectionBand>
        </section>
      </div>

      <section className="panel">
        <SectionBand eyebrow="Trace" title="Run ledger">
          <div className="list">
            {run.traceRecords.map((trace) => (
              <div className="list-item" key={trace.id}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <strong>{trace.eventType}</strong>
                  <Chip tone={trace.eventType === "approval_recorded" ? "good" : "neutral"}>
                    {new Date(trace.createdAt).toLocaleString()}
                  </Chip>
                </div>
                <p>{trace.message}</p>
              </div>
            ))}
          </div>
        </SectionBand>
      </section>
    </div>
  );
}
