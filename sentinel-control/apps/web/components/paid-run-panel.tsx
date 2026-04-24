"use client";

import { useMemo, useState, useTransition } from "react";
import { Chip } from "@/components/ui";
import type { PaidRunQuoteRow, SentinelRunRecord } from "@/lib/types";

function formatCents(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function previewQuote(run: SentinelRunRecord): PaidRunQuoteRow {
  const amountCents = run.depth === "deep" ? 9900 : run.depth === "quick" ? 1900 : 4900;
  return {
    id: `quote_preview_${run.id}`,
    runId: run.id,
    label: `${run.summary.verdict} paid run pack`,
    amountCents,
    status: "draft",
    lineItems: [
      "Evidence-backed GTM pack",
      "Firewall review and approval inbox",
      "Trace ledger export",
      "Outreach drafts only",
    ],
    createdAt: run.updatedAt,
  };
}

export function PaidRunPanel({ run }: { run: SentinelRunRecord }) {
  const [runState, setRunState] = useState(run);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const quote = useMemo(() => runState.paidQuote || previewQuote(runState), [runState]);

  function prepareQuote() {
    setError(null);
    startTransition(async () => {
      const response = await fetch(`/api/runs/${runState.id}/paid-quote`, { method: "POST" });
      const payload = (await response.json().catch(() => null)) as { run?: SentinelRunRecord; error?: string } | null;
      if (!response.ok || !payload?.run) {
        setError(payload?.error || "Quote preparation failed.");
      } else {
        setRunState(payload.run);
      }
    });
  }

  return (
    <article className="paid-quote-card">
      <div className="paid-quote-top">
        <div>
          <span className="eyebrow">{runState.depth} run</span>
          <h3>{runState.inputIdea}</h3>
        </div>
        <Chip tone={quote.status === "payment_disabled" ? "warn" : "neutral"}>{quote.status.replace("_", " ")}</Chip>
      </div>
      <div className="paid-quote-price">{formatCents(quote.amountCents)}</div>
      <div className="quote-lines">
        {quote.lineItems.map((line) => (
          <span key={line}>{line}</span>
        ))}
      </div>
      <div className="approval-row">
        <span className="page-note">Payment stays disabled in v1; this prepares the commercial run package only.</span>
        <button className="primary-btn" disabled={isPending} onClick={prepareQuote} type="button">
          Prepare quote
        </button>
      </div>
      {error ? <div className="inline-alert">{error}</div> : null}
    </article>
  );
}
