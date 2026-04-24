import { SectionBand, Chip } from "@/components/ui";
import { evidence } from "@/lib/demo-data";

const columns = [
  {
    title: "Discovery",
    tone: "neutral" as const,
    cards: [
      "Talk to freelancers with recurring late invoices.",
      "Ask what they use today and where the friction shows up.",
    ],
  },
  {
    title: "Reachable channels",
    tone: "good" as const,
    cards: [
      "Freelance communities",
      "Niche professional groups",
      "Warm referrals",
    ],
  },
  {
    title: "Draft outreach",
    tone: "warn" as const,
    cards: [
      "Short, direct, evidence-backed.",
      "No false personalization.",
    ],
  },
  {
    title: "Pilots",
    tone: "neutral" as const,
    cards: [
      "Concierge validation first.",
      "Convert to a subscription only after WTP proof.",
    ],
  },
];

export default function CustomersPage() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Customers</div>
          <h1 className="page-title">First 10 Customers OS</h1>
          <p className="page-copy">
            The customer layer turns evidence into a reachable niche, an outreach motion, and a validation path. It is intentionally narrow: proof before scale.
          </p>
        </div>
        <div className="panel">
          <SectionBand eyebrow="Signals" title="Which signals matter most">
            <div className="list">
              {evidence.slice(0, 4).map((item) => (
                <div className="list-item" key={item.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                    <strong>{item.source}</strong>
                    <Chip tone={item.proofTier === "direct" ? "good" : "neutral"}>{item.proofTier}</Chip>
                  </div>
                  <p>{item.summary}</p>
                </div>
              ))}
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="board-grid" style={{ gridTemplateColumns: "repeat(4, minmax(220px, 1fr))" }}>
        {columns.map((column) => (
          <div className="board-column" key={column.title}>
            <div className="board-header">
              <strong>{column.title}</strong>
              <Chip tone={column.tone}>{column.cards.length}</Chip>
            </div>
            <div className="board-list">
              {column.cards.map((card) => (
                <div className="board-card" key={card}>
                  <h4>{card}</h4>
                  <p>Local state only in v1. Later sprints connect this to real contacts and tasks.</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}

