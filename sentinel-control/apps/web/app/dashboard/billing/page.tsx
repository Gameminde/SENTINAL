import Link from "next/link";
import { PaidRunPanel } from "@/components/paid-run-panel";
import { Chip, Metric, SectionBand } from "@/components/ui";
import { formatCents, listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

export default async function BillingPage() {
  const runs = await listRuns();
  const quotes = runs.filter((run) => run.paidQuote);
  const estimatedTotal = quotes.reduce((total, run) => total + (run.paidQuote?.amountCents || 0), 0);

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Paid Runs</div>
          <h1 className="page-title">Commercial package prep</h1>
          <p className="page-copy">
            Sentinel can price a controlled GTM run package while payment execution stays disabled until a later billing sprint.
          </p>
          <div className="metric-grid">
            <Metric label="Runs" value={`${runs.length}`} sub="available to quote" />
            <Metric label="Quotes" value={`${quotes.length}`} sub="prepared locally" />
            <Metric label="Total" value={formatCents(estimatedTotal)} sub="disabled v1 quotes" />
            <Metric label="Payments" value="Off" sub="no charging in Sprint 6" />
          </div>
        </div>
        <div className="panel">
          <SectionBand eyebrow="Guardrail" title="Payment state">
            <div className="list">
              <div className="list-item">
                <div className="approval-row">
                  <strong>Payment execution</strong>
                  <Chip tone="warn">disabled</Chip>
                </div>
                <p>Quotes prepare the offer and line items only. Checkout, subscriptions, and spend are not active in v1.</p>
              </div>
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="panel">
        <SectionBand eyebrow="Quotes" title="Prepare paid run packages">
          <div className="quote-panel-grid">
            {runs.slice(0, 4).map((run) => (
              <PaidRunPanel key={run.id} run={run} />
            ))}
            {runs.length === 0 ? <div className="empty-state">Create a run before preparing a paid package.</div> : null}
          </div>
        </SectionBand>
      </section>

      <section className="panel">
        <SectionBand eyebrow="Runs" title="Quoted run ledger">
          <div className="list">
            {quotes.length > 0 ? (
              quotes.map((run) => (
                <Link className="list-item" href={`/dashboard/agents/${run.id}`} key={run.id}>
                  <div className="approval-row">
                    <strong>{run.paidQuote?.label}</strong>
                    <Chip tone="warn">{run.paidQuote?.status.replace("_", " ")}</Chip>
                  </div>
                  <p>{run.inputIdea}</p>
                  <span className="page-note">{formatCents(run.paidQuote?.amountCents || 0)}</span>
                </Link>
              ))
            ) : (
              <div className="empty-state">No paid run quotes prepared yet.</div>
            )}
          </div>
        </SectionBand>
      </section>
    </div>
  );
}
