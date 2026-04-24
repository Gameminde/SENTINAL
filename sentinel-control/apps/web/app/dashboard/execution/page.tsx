import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { WatchlistPanel } from "@/components/watchlist-panel";
import { Chip, Metric, SectionBand } from "@/components/ui";
import { getExecutionBoard, listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

export default async function ExecutionPage() {
  const [board, runs] = await Promise.all([getExecutionBoard(), listRuns()]);
  const latestRun = runs[0];
  const pendingCount = runs.reduce((total, run) => total + run.actions.filter((action) => action.approvalStatus === "pending").length, 0);
  const monitoringCount = runs.reduce(
    (total, run) => total + run.watchlist.filter((item) => item.status === "monitoring" || item.status === "needs_review").length,
    0,
  );
  const interviewCount = runs.reduce((total, run) => total + run.watchlist.filter((item) => item.status === "interview").length, 0);

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Execution Board</div>
          <h1 className="page-title">Controlled pipeline from idea to decision</h1>
          <p className="page-copy">
            Runs move through packs, approvals, outreach drafts, interviews, monitoring, and final decision without bypassing trace or firewall policy.
          </p>
          <div className="metric-grid">
            <Metric label="Runs" value={`${runs.length}`} sub="local workspace" />
            <Metric label="Pending" value={`${pendingCount}`} sub="approval inbox" />
            <Metric label="Monitoring" value={`${monitoringCount}`} sub="watchlist signals" />
            <Metric label="Interviews" value={`${interviewCount}`} sub="active WTP path" />
          </div>
        </div>
        <div className="panel">
          <SectionBand eyebrow="Latest run" title={latestRun?.summary.title || "No runs yet"}>
            {latestRun ? (
              <div className="list">
                <Link className="list-item" href={`/dashboard/agents/${latestRun.id}`}>
                  <div className="approval-row">
                    <strong>{latestRun.summary.verdict}</strong>
                    <Chip tone="neutral">{latestRun.riskLabel}</Chip>
                  </div>
                  <p>{latestRun.project.description}</p>
                  <span className="page-note">Open run detail</span>
                </Link>
              </div>
            ) : (
              <div className="empty-state">Create a run to start the board.</div>
            )}
          </SectionBand>
        </div>
      </section>

      <section className="panel">
        <SectionBand eyebrow="Pipeline" title="Execution Board">
          <div className="board-grid board-grid-wide">
            {board.map((column) => (
              <div className="board-column" key={column.id}>
                <div className="board-header">
                  <strong>{column.title}</strong>
                  <Chip tone={column.id === "approval" ? "warn" : "neutral"}>{column.cards.length}</Chip>
                </div>
                <div className="board-list">
                  {column.cards.length > 0 ? (
                    column.cards.map((card) => (
                      <Link className="board-card" data-tone={card.tone} href={card.href} key={card.id}>
                        <div className="approval-row">
                          <h4>{card.title}</h4>
                          <ArrowUpRight size={15} />
                        </div>
                        <p>{card.description}</p>
                        <span className="page-note">{card.meta}</span>
                      </Link>
                    ))
                  ) : (
                    <div className="empty-state">No cards</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </SectionBand>
      </section>

      {latestRun ? (
        <section className="panel">
          <SectionBand eyebrow="Watchlist" title="Signal updates">
            <WatchlistPanel run={latestRun} />
          </SectionBand>
        </section>
      ) : null}
    </div>
  );
}
