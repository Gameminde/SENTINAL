"use client";

import { Check, Flag, ThumbsUp, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { FeedbackEntryRow, FeedbackRating, FeedbackTargetType, SentinelRunRecord } from "@/lib/types";

const ratingConfig: Array<{ rating: FeedbackRating; label: string; icon: typeof ThumbsUp }> = [
  { rating: "useful", label: "Useful", icon: ThumbsUp },
  { rating: "weak", label: "Weak", icon: Flag },
  { rating: "approved", label: "Approve", icon: Check },
  { rating: "rejected", label: "Reject", icon: X },
];

export function FeedbackControls({
  runId,
  targetType,
  targetId,
  feedback = [],
  onRunUpdate,
}: {
  runId: string;
  targetType: FeedbackTargetType;
  targetId: string;
  feedback?: FeedbackEntryRow[];
  onRunUpdate?: (run: SentinelRunRecord) => void;
}) {
  const [note, setNote] = useState("");
  const [busyRating, setBusyRating] = useState<FeedbackRating | null>(null);
  const [error, setError] = useState<string | null>(null);

  const latestFeedback = useMemo(
    () => feedback.find((entry) => entry.targetType === targetType && entry.targetId === targetId),
    [feedback, targetId, targetType],
  );

  async function submitFeedback(rating: FeedbackRating) {
    setError(null);
    setBusyRating(rating);
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/feedback`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ targetType, targetId, rating, note }),
      });
      const payload = (await response.json()) as { run?: SentinelRunRecord; error?: string };

      if (!response.ok || !payload.run) {
        throw new Error(payload.error || "Feedback could not be saved.");
      }

      setNote("");
      onRunUpdate?.(payload.run);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Feedback could not be saved.");
    } finally {
      setBusyRating(null);
    }
  }

  return (
    <div className="feedback-box">
      <div className="feedback-top">
        <span>{latestFeedback ? `Last marked ${latestFeedback.rating}` : "Mark for learning"}</span>
        {latestFeedback?.note ? <small>{latestFeedback.note}</small> : null}
      </div>
      <input
        aria-label={`Feedback note for ${targetId}`}
        className="feedback-input"
        onChange={(event) => setNote(event.target.value)}
        placeholder="Optional note"
        value={note}
      />
      <div className="feedback-actions">
        {ratingConfig.map(({ rating, label, icon: Icon }) => (
          <button
            className="ghost-btn"
            disabled={busyRating !== null}
            key={rating}
            onClick={() => void submitFeedback(rating)}
            type="button"
          >
            <Icon size={15} />
            <span>{busyRating === rating ? "Saving" : label}</span>
          </button>
        ))}
      </div>
      {error ? <div className="inline-alert">{error}</div> : null}
    </div>
  );
}
