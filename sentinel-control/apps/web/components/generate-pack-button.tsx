"use client";

import { FolderOpen } from "lucide-react";
import { useState, useTransition } from "react";
import type { SentinelRunRecord } from "@/lib/types";

export function GeneratePackButton({
  run,
  onRunUpdate,
}: {
  run: SentinelRunRecord;
  onRunUpdate?: (run: SentinelRunRecord) => void;
}) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function generatePack() {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/runs/${run.id}/generate-pack`, { method: "POST" });
      const payload = (await response.json().catch(() => null)) as { run?: SentinelRunRecord; error?: string } | null;

      if (!response.ok || !payload?.run) {
        setError(payload?.error || "Pack generation failed.");
        return;
      }

      onRunUpdate?.(payload.run);
      setMessage("Pack files written locally.");
    });
  }

  return (
    <div className="inline-action-stack">
      <button className="primary-btn" disabled={isPending} onClick={generatePack} type="button">
        <FolderOpen size={16} />
        <span>{isPending ? "Writing pack" : "Write local pack"}</span>
      </button>
      {message ? <span className="page-note">{message}</span> : null}
      {error ? <div className="inline-alert">{error}</div> : null}
    </div>
  );
}
