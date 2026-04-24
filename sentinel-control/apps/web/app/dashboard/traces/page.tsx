import Link from "next/link";
import { Activity, ArrowUpRight, ReceiptText } from "lucide-react";
import { Chip, Metric, SectionBand } from "@/components/ui";
import { estimateRunCost, formatCents, listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

function eventTone(eventType: string): "neutral" | "good" | "warn" | "bad" {
  if (eventType === "approval_recorded" || eventType === "run_completed") return "good";
  if (eventType === "feedback_recorded") return "good";
  if (eventType === "run_failed") return "bad";
  if (eventType === "action_proposed" || eventType === "firewall_reviewed") return "warn";
  return "neutral";
}

export default async function TracesPage() {
  const runs = await listRuns();
  const traceRows = runs
    .flatMap((run) =>
      run.traceRecords.map((trace) => ({
        ...trace,
        runId: run.id,
        runTitle: run.summary.title,
      })),
    )
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());

  const totalCost = runs.reduce((total, run) => total + (run.cost || estimateRunCost(run)).totalCents, 0);
  const pendingActions = runs.reduce(
    (total, run) => total + run.actions.filter((action) => action.approvalStatus === "pending").length,
    0,
  );

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Traces</div>
          <h1 className="page-title">Trace and cost ledger</h1>
          <p className="page-copy">
            Inspect every local run event, approval record, generated asset trail, and estimated run cost from one audit surface.
          </p>
          <div className="metric-grid">
            <Metric label="Runs" value={`${runs.length}`} sub="local records" />
            <Metric label="Trace Events" value={`${traceRows.length}`} sub="stored ledger rows" />
            <Metric label="Pending Actions" value={`${pendingActions}`} sub="approval queue" />
            <Metric label="Estimated Cost" value={formatCents(totalCost)} sub="local estimate" />
          </div>
        </div>

        <div className="panel">
          <SectionBand eyebrow="Eval Readiness" title="Sprint 5 checks">
            <div className="list">
              {[
                "dangerous actions blocked",
                "weak ideas cannot force build",
                "outreach compliance checked",
                "prompt injection detected",
                "fake evidence downgraded",
                "trace events required",
              ].map((label) => (
                <div className="list-item" key={label}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                    <strong>{label}</strong>
                    <Chip tone="good">covered</Chip>
                  </div>
                </div>
              ))}
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="workspace-grid">
        <section className="panel">
          <SectionBand
            eyebrow="Ledger"
            title="Trace timeline"
            action={
              <Link className="secondary-btn" href="/dashboard/agents">
                <Activity size={16} />
                <span>Open operator</span>
              </Link>
            }
          >
            <div className="trace-list">
              {traceRows.map((trace) => (
                <div className="trace-row" key={`${trace.runId}-${trace.id}`}>
                  <div className="trace-dot" data-tone={eventTone(trace.eventType)} />
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                      <strong>{trace.eventType}</strong>
                      <Chip tone={eventTone(trace.eventType)}>{new Date(trace.createdAt).toLocaleString()}</Chip>
                    </div>
                    <p>{trace.message}</p>
                    <div className="trace-meta">
                      <span>{trace.runTitle}</span>
                      <Link href={`/dashboard/agents/${trace.runId}`}>
                        Open run <ArrowUpRight size={13} />
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SectionBand>
        </section>

        <section className="panel">
          <SectionBand
            eyebrow="Cost"
            title="Run cost estimates"
            action={
              <button className="ghost-btn" type="button">
                <ReceiptText size={16} />
                <span>Local estimate</span>
              </button>
            }
          >
            <div className="list">
              {runs.map((run) => {
                const cost = run.cost || estimateRunCost(run);
                return (
                  <div className="list-item" key={run.id}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start", flexWrap: "wrap" }}>
                      <div>
                        <strong>{run.summary.title}</strong>
                        <p>{run.id}</p>
                      </div>
                      <Chip tone="neutral">{formatCents(cost.totalCents)}</Chip>
                    </div>
                    <div className="cost-lines">
                      {cost.lines.map((line) => (
                        <div className="cost-line" key={line.label}>
                          <div>
                            <span>{line.label}</span>
                            <small>{line.tokens.toLocaleString()} est. tokens</small>
                          </div>
                          <strong>{formatCents(line.estimatedCents)}</strong>
                        </div>
                      ))}
                    </div>
                    <span className="page-note">{cost.note}</span>
                  </div>
                );
              })}
            </div>
          </SectionBand>
        </section>
      </section>
    </div>
  );
}
