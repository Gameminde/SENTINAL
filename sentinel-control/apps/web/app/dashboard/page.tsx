import Link from "next/link";
import { ArrowUpRight, FileText } from "lucide-react";
import { EvidenceLedgerPanel, FirewallPolicyPanel, FirewallReviewPanel } from "@/components/interactive";
import { Arrow, Chip, Metric, SectionBand, StateBadge } from "@/components/ui";
import { ExportButton } from "@/components/shared";
import { agents, executionColumns, projects, runStages, runSummary } from "@/lib/demo-data";

export default function DashboardPage() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Agents / GTM Operator / {runSummary.runId}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
            <Chip tone="neutral">RUN IN PROGRESS</Chip>
            <span className="page-note">Started {runSummary.startedAt}</span>
          </div>

          <h1 className="page-title">{runSummary.title}</h1>
          <p className="page-copy">
            Sentinel Control turns market evidence into a decision, a GTM pack, and a permissioned execution path. The current run is under review, so the pack is ready while external actions remain draft-only.
          </p>

          <div className="metric-grid">
            <Metric label="Verdict" value={runSummary.verdict} sub="Guardrails active across 2 actions" />
            <Metric label="Confidence" value={`${runSummary.confidence}%`} sub="Evidence weighted" />
            <Metric label="Risk Score" value={`${runSummary.riskScore}/100`} sub={runSummary.riskLabel} />
            <Metric label="Actions" value="4" sub="1 approved, 2 pending, 1 blocked" />
          </div>

          <div className="progress" aria-label="Run progress">
            {runStages.map((stage, index) => (
              <div className="progress-step" data-active={stage.key === "firewall" ? "true" : "false"} key={stage.key}>
                <strong>
                  {index + 1}. {stage.label}
                </strong>
                <span>{stage.detail}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <FirewallReviewPanel compact />
        </div>
      </section>

      <div className="workspace-grid">
        <section className="panel">
          <EvidenceLedgerPanel />
        </section>

        <section className="panel">
          <FirewallPolicyPanel />
        </section>
      </div>

      <section className="panel">
        <SectionBand
          eyebrow="Execution"
          title="Execution Board"
          action={
            <div className="section-actions">
              <Link className="ghost-btn" href="/dashboard/agents/GR-2025-05-18-1427">
                <ArrowUpRight size={16} />
                <span>Open Run</span>
              </Link>
              <button className="secondary-btn" type="button">
                <FileText size={16} />
                <span>Export Pack</span>
              </button>
            </div>
          }
        >
          <div className="board-grid">
            {executionColumns.map((column) => (
              <div className="board-column" key={column.title}>
                <div className="board-header">
                  <strong>{column.title}</strong>
                  <Chip tone={column.title === "Needs Approval" ? "warn" : "neutral"}>{column.count}</Chip>
                </div>
                <div className="board-list">
                  {column.cards.map((card) => (
                    <div className="board-card" key={card.title}>
                      <h4>{card.title}</h4>
                      <p>{card.description}</p>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                        <span className="page-note">{card.meta}</span>
                        <Arrow rotated />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionBand>
      </section>

      <section className="columns-2">
        <section className="panel">
          <SectionBand
            eyebrow="Agents"
            title="Active agent stack"
            action={
              <Link className="ghost-btn" href="/dashboard/agents/GR-2025-05-18-1427">
                Open run details
              </Link>
            }
          >
            <div className="list">
              {agents.map((agent) => (
                <div className="list-item" key={agent.name}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start", flexWrap: "wrap" }}>
                    <strong>{agent.name}</strong>
                    <Chip tone={agent.status === "complete" ? "good" : agent.status === "reviewing" ? "warn" : "neutral"}>
                      {agent.status}
                    </Chip>
                  </div>
                  <p>{agent.role}</p>
                  <span className="page-note">{agent.note}</span>
                </div>
              ))}
            </div>
          </SectionBand>
        </section>

        <section className="panel">
          <SectionBand eyebrow="Projects" title="Generated project folders" action={<ExportButton label="Download JSON" />}>
            <div className="list">
              {projects.map((project) => (
                <Link className="list-item" href={`/dashboard/generated-projects/${project.id}`} key={project.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                    <strong>{project.name}</strong>
                    <StateBadge state={project.status === "Needs approval" ? "pending" : "approved"}>{project.status}</StateBadge>
                  </div>
                  <p>{project.description}</p>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                    <span className="page-note">Updated {project.updatedAt}</span>
                    <span className="page-note">{project.files.join(" / ")}</span>
                  </div>
                </Link>
              ))}
            </div>
          </SectionBand>
        </section>
      </section>
    </div>
  );
}
