import { Search } from "lucide-react";
import { EvidenceLedgerPanel } from "@/components/interactive";
import { ExportButton } from "@/components/shared";
import { Chip, SectionBand } from "@/components/ui";
import { evidence } from "@/lib/demo-data";

export default function EvidencePage() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Evidence</div>
          <h1 className="page-title">Evidence Ledger</h1>
          <p className="page-copy">
            Every recommendation in Sentinel Control points back to evidence. This page makes direct proof, adjacent proof, and supporting signals visible before any action is approved.
          </p>
          <div className="toolbar" style={{ marginTop: 18 }}>
            <button className="secondary-btn" type="button">
              <Search size={16} />
              <span>Open ledger search</span>
            </button>
            <ExportButton label="Export rows" />
          </div>
        </div>

        <div className="panel">
          <SectionBand eyebrow="Summary" title="Ledger status">
            <div className="metric-grid" style={{ marginTop: 0 }}>
              <div className="metric">
                <div className="metric-label">Rows</div>
                <div className="metric-value">{evidence.length}</div>
                <div className="metric-sub">normalized across runs</div>
              </div>
              <div className="metric">
                <div className="metric-label">Direct</div>
                <div className="metric-value">3</div>
                <div className="metric-sub">proof-backed</div>
              </div>
              <div className="metric">
                <div className="metric-label">Adjacent</div>
                <div className="metric-value">3</div>
                <div className="metric-sub">wedge shaping</div>
              </div>
              <div className="metric">
                <div className="metric-label">WTP</div>
                <div className="metric-value">1</div>
                <div className="metric-sub">pricing signal</div>
              </div>
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="panel">
        <EvidenceLedgerPanel />
      </section>

      <section className="columns-2">
        <section className="panel">
          <SectionBand eyebrow="Selected" title="Why selection matters">
            <div className="list">
              <div className="list-item">
                <strong>{evidence[0].source}</strong>
                <p>{evidence[0].details.excerpt}</p>
                <span className="page-note">{evidence[0].details.methodology}</span>
              </div>
              <div className="list-item">
                <strong>Decision rule</strong>
                <p>Direct pain and WTP are the only signals allowed to drive a build decision in this workflow.</p>
              </div>
            </div>
          </SectionBand>
        </section>

        <section className="panel">
          <SectionBand eyebrow="Policy" title="Evidence rules" action={<Chip tone="neutral">Traceable claims only</Chip>}>
            <div className="list">
              <div className="list-item">
                <strong>Direct proof</strong>
                <p>Observed posts, explicit complaints, or buyer-native quotes.</p>
              </div>
              <div className="list-item">
                <strong>Adjacent proof</strong>
                <p>Useful for shaping the wedge, but never enough to skip verification.</p>
              </div>
              <div className="list-item">
                <strong>Supporting proof</strong>
                <p>Timing or technical context only. Never use it as the sole basis for execution.</p>
              </div>
            </div>
          </SectionBand>
        </section>
      </section>
    </div>
  );
}
