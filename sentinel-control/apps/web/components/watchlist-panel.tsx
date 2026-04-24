"use client";

import { useState, useTransition } from "react";
import { Chip } from "@/components/ui";
import type { SentinelRunRecord, WatchlistItemRow, WatchlistStatus } from "@/lib/types";

const statusOptions: Array<{ status: WatchlistStatus; label: string }> = [
  { status: "monitoring", label: "Monitor" },
  { status: "needs_review", label: "Review" },
  { status: "interview", label: "Interview" },
  { status: "validated", label: "Validate" },
  { status: "archived", label: "Archive" },
];

function toneForStatus(status: WatchlistStatus): "neutral" | "good" | "warn" | "bad" {
  if (status === "validated" || status === "interview") return "good";
  if (status === "needs_review") return "warn";
  if (status === "archived") return "bad";
  return "neutral";
}

export function WatchlistPanel({ run }: { run: SentinelRunRecord }) {
  const [runState, setRunState] = useState(run);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function updateItem(item: WatchlistItemRow, status: WatchlistStatus) {
    setError(null);
    setPendingId(item.id);
    startTransition(async () => {
      const response = await fetch(`/api/runs/${runState.id}/watchlist/${item.id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status, note: notes[item.id] || undefined }),
      });
      const payload = (await response.json().catch(() => null)) as { run?: SentinelRunRecord; error?: string } | null;
      if (!response.ok || !payload?.run) {
        setError(payload?.error || "Watchlist update failed.");
      } else {
        setRunState(payload.run);
      }
      setPendingId(null);
    });
  }

  return (
    <div className="watchlist-grid">
      {runState.watchlist.map((item) => (
        <article className="watchlist-card" key={item.id}>
          <div className="watchlist-top">
            <div>
              <strong>{item.label}</strong>
              <span>{item.source}</span>
            </div>
            <Chip tone={toneForStatus(item.status)}>{item.status.replace("_", " ")}</Chip>
          </div>
          <p>{item.summary}</p>
          <div className="watchlist-meta">
            <span>{item.signalType}</span>
            <span>{item.evidenceRefs.length} evidence refs</span>
            <span>{new Date(item.updatedAt).toLocaleDateString()}</span>
          </div>
          {item.note ? <div className="page-note">{item.note}</div> : null}
          <input
            className="input"
            onChange={(event) => setNotes((current) => ({ ...current, [item.id]: event.target.value }))}
            placeholder="Operator note"
            value={notes[item.id] || ""}
          />
          <div className="status-button-row">
            {statusOptions.map((option) => (
              <button
                className={option.status === item.status ? "primary-btn" : "ghost-btn"}
                disabled={isPending && pendingId === item.id}
                key={option.status}
                onClick={() => updateItem(item, option.status)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        </article>
      ))}
      {error ? <div className="inline-alert">{error}</div> : null}
    </div>
  );
}
