"use client";

import {
  Activity,
  ArrowRight,
  Brain,
  CheckCircle2,
  CircleAlert,
  Cpu,
  FileText,
  Globe2,
  Layers3,
  LockKeyhole,
  Play,
  Radar,
  RefreshCw,
  Route,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { Chip } from "@/components/ui";
import type { RunDepth, SentinelRunRecord } from "@/lib/types";

const missionObjective = `Design, using only official SQLite documentation, the storage architecture for a scientific acquisition application:
- SBG around 40 samples per second;
- other sensors around 1 sample per second;
- multi-sensor temporal alignment;
- long-duration continuous recording;
- dashboard reads during acquisition;
- resilience to crashes and power loss;
- reliable export and backup.

Return a grounded recommendation covering data model, timestamps, transactions, batching, WAL versus rollback journal, checkpointing, synchronous levels, read/write concurrency, busy handling, indexing, backup, recovery, limits and uncertainty. Every material claim must link to official sqlite.org evidence.`;

const providerPresets = [
  {
    id: "tokenrouter-qwen",
    autoSelectable: false,
    label: "Qwen 3.8 Max Free",
    providerId: "tokenrouter",
    backendId: "tokenrouter_chat_completions",
    modelId: "qwen/qwen3.8-max-free",
    note: "TokenRouter / OpenAI-compatible chat / setup required",
  },
  {
    id: "opencode-ox",
    autoSelectable: true,
    label: "Ox Alpha Free",
    providerId: "opencode_chat",
    backendId: "opencode_chat_completions",
    modelId: "x-preview-f-free",
    note: "OpenCode / chat completions",
  },
  {
    id: "opencode-muse",
    autoSelectable: true,
    label: "Muse Spark 1.2 Free",
    providerId: "opencode",
    backendId: "opencode_responses",
    modelId: "muse-spark-1.2-contributor-free",
    note: "OpenCode / responses",
  },
  {
    id: "nvidia-minimax",
    autoSelectable: true,
    label: "MiniMax M3",
    providerId: "nvidia",
    backendId: "nvidia_openai_compatible_chat",
    modelId: "minimaxai/minimax-m3",
    note: "NVIDIA / OpenAI-compatible chat",
  },
] as const;

const noHandoffId = "none";

type ProviderPreset = (typeof providerPresets)[number];
const defaultPrimaryPresetId = providerPresets.find((preset) => preset.autoSelectable)?.id ?? providerPresets[0].id;

function providerById(id: string): ProviderPreset {
  return providerPresets.find((preset) => preset.id === id) ?? providerPresets[0];
}

function toneForStatus(status: string): "neutral" | "good" | "warn" | "bad" {
  const lowered = status.toLowerCase();
  if (lowered.includes("complete") || lowered.includes("success")) return "good";
  if (lowered.includes("block") || lowered.includes("fail") || lowered.includes("error")) return "bad";
  if (lowered.includes("run") || lowered.includes("pending")) return "warn";
  return "neutral";
}

function shortList(items: string[], empty = "none") {
  if (items.length === 0) return empty;
  if (items.length <= 4) return items.join(", ");
  return `${items.slice(0, 4).join(", ")} +${items.length - 4}`;
}

function StatusDot({ status }: { status: string }) {
  return <span className="sentinel-status-dot" data-tone={toneForStatus(status)} aria-hidden="true" />;
}

function ProviderCard({
  preset,
  active,
  role,
}: {
  preset: ProviderPreset;
  active: boolean;
  role: string;
}) {
  return (
    <div className="provider-card" data-active={active ? "true" : "false"}>
      <div>
        <span>{role}</span>
        <strong>{preset.label}</strong>
      </div>
      <small>{preset.note}</small>
      <code>{preset.providerId}/{preset.modelId}</code>
    </div>
  );
}

function MissionSignal({ run }: { run: SentinelRunRecord }) {
  const canonical = run.canonicalMission;
  const status = canonical?.status || run.status;
  const materialCount = canonical?.completedActions.filter((action) => action.materialAction).length ?? 0;
  const evidenceCount = canonical?.evidenceRefs.length ?? run.evidence.length;

  return (
    <div className="sentinel-signal" data-tone={toneForStatus(status)}>
      <div className="signal-rings" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="signal-core">
        <StatusDot status={status} />
        <strong>{canonical ? "CANONICAL" : "LOCAL"}</strong>
        <span>{canonical?.currentStage || "awaiting product mission"}</span>
      </div>
      <div className="signal-readouts">
        <div>
          <span>Actions</span>
          <strong>{canonical?.completedActions.length ?? run.actions.length}</strong>
        </div>
        <div>
          <span>Material</span>
          <strong>{materialCount}</strong>
        </div>
        <div>
          <span>Evidence</span>
          <strong>{evidenceCount}</strong>
        </div>
      </div>
    </div>
  );
}

function CanonicalRunPanel({ run }: { run: SentinelRunRecord }) {
  const canonical = run.canonicalMission;

  if (!canonical) {
    return (
      <section className="console-panel">
        <div className="panel-heading">
          <div>
            <span className="console-eyebrow">Runtime</span>
            <h2>No canonical mission selected</h2>
          </div>
          <Chip tone="warn">historical local record</Chip>
        </div>
        <p className="console-muted">
          This run predates the public product cutover. Launch a new canonical public mission to see provider, body, evidence and cleanup truth from the runtime.
        </p>
      </section>
    );
  }

  const terminalText = canonical.terminalAnswer || canonical.terminalBlocker || "No terminal text returned.";
  const statusTone = toneForStatus(canonical.status);

  return (
    <section className="console-panel mission-truth-panel">
      <div className="panel-heading">
        <div>
          <span className="console-eyebrow">Mission truth</span>
          <h2>{canonical.status.replace(/_/g, " ")}</h2>
        </div>
        <Chip tone={statusTone}>{canonical.currentStage}</Chip>
      </div>

      <div className="truth-grid">
        <div>
          <span>Provider / model</span>
          <strong>{canonical.selectedProvider}/{canonical.selectedModel}</strong>
        </div>
        <div>
          <span>Authority</span>
          <strong>{shortList(canonical.authorityScope.grantedAuthorities, "unknown")}</strong>
        </div>
        <div>
          <span>Site scope</span>
          <strong>{shortList(canonical.authorityScope.browserAllowedOrigins, "unknown")}</strong>
        </div>
        <div>
          <span>Cleanup</span>
          <strong>{canonical.cleanupStatus}</strong>
        </div>
      </div>

      <div className="terminal-answer" data-tone={canonical.terminalAnswer ? "answer" : "blocker"}>
        <span>{canonical.terminalAnswer ? "Terminal answer" : "Terminal blocker"}</span>
        <p>{terminalText}</p>
      </div>

      <div className="proof-strip">
        <div>
          <FileText size={16} />
          <span>Evidence refs</span>
          <strong>{canonical.evidenceRefs.length}</strong>
        </div>
        <div>
          <ShieldCheck size={16} />
          <span>Proof root</span>
          <strong>{canonical.proofRootVerified ? "verified" : "not verified"}</strong>
        </div>
        <div>
          <Route size={16} />
          <span>Replay side effects</span>
          <strong>{canonical.replaySideEffectsReexecuted ? "reexecuted" : "not reexecuted"}</strong>
        </div>
      </div>
    </section>
  );
}

function ActionTimeline({ run }: { run: SentinelRunRecord }) {
  const canonical = run.canonicalMission;
  const actions = canonical?.completedActions ?? [];

  return (
    <section className="console-panel">
      <div className="panel-heading">
        <div>
          <span className="console-eyebrow">Body trace</span>
          <h2>Actions and receipts</h2>
        </div>
        <Chip tone={actions.length > 0 ? "good" : "neutral"}>{actions.length} receipts</Chip>
      </div>

      <div className="timeline">
        {actions.length > 0 ? (
          actions.map((action, index) => (
            <div className="timeline-row" key={`${action.receiptId}-${index}`}>
              <span className="timeline-index">{index + 1}</span>
              <div>
                <strong>{action.capability}.{action.operation}</strong>
                <p>{action.status} / evidence {action.evidenceRefs.length}</p>
              </div>
              <code>{action.receiptId}</code>
            </div>
          ))
        ) : (
          <div className="empty-console">
            <TerminalSquare size={17} />
            <span>No body action has reached a receipt for this selected run.</span>
          </div>
        )}
      </div>
    </section>
  );
}

function EvidencePanel({ run }: { run: SentinelRunRecord }) {
  const canonicalRefs = run.canonicalMission?.evidenceRefs ?? [];
  const rows = run.evidence.slice(0, 6);

  return (
    <section className="console-panel">
      <div className="panel-heading">
        <div>
          <span className="console-eyebrow">Evidence</span>
          <h2>Human-readable support</h2>
        </div>
        <Chip tone={canonicalRefs.length > 0 ? "good" : "neutral"}>{canonicalRefs.length || rows.length} refs</Chip>
      </div>

      <div className="evidence-stack">
        {canonicalRefs.length > 0 ? (
          canonicalRefs.slice(0, 8).map((ref) => (
            <div className="evidence-row" key={ref}>
              <FileText size={15} />
              <span>{ref}</span>
            </div>
          ))
        ) : (
          rows.map((row) => (
            <div className="evidence-row" key={row.id}>
              <FileText size={15} />
              <span>{row.summary}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export function RunOperator({ initialRuns }: { initialRuns: SentinelRunRecord[] }) {
  const [runs, setRuns] = useState(initialRuns);
  const [selectedRunId, setSelectedRunId] = useState(initialRuns[0]?.id ?? "");
  const [idea, setIdea] = useState(missionObjective);
  const [targetOrigin, setTargetOrigin] = useState("sqlite.org");
  const [depth, setDepth] = useState<RunDepth>("deep");
  const [primaryPresetId, setPrimaryPresetId] = useState<string>(defaultPrimaryPresetId);
  const [handoffPresetId, setHandoffPresetId] = useState<string>(noHandoffId);
  const [maxProviderDecisions, setMaxProviderDecisions] = useState(30);
  const [maxMaterialActions, setMaxMaterialActions] = useState(20);
  const [maxWallTimeMinutes, setMaxWallTimeMinutes] = useState(45);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0],
    [runs, selectedRunId],
  );
  const primaryPreset = providerById(primaryPresetId);
  const handoffPreset = handoffPresetId === noHandoffId ? null : providerById(handoffPresetId);
  const selectedCanonical = selectedRun?.canonicalMission;
  const modelVisibleAffordanceText = selectedRun.canonicalMission
    ? selectedRun.canonicalMission.modelVisibleAffordances.join(", ") || "No affordances reported."
    : "Available after a canonical mission returns state.";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          idea,
          niche: targetOrigin,
          depth,
          mode: "canonical_public",
          targetOrigin,
          providerId: primaryPreset.providerId,
          backendId: primaryPreset.backendId,
          modelId: primaryPreset.modelId,
          handoffProviderId: handoffPreset?.providerId,
          handoffBackendId: handoffPreset?.backendId,
          handoffModelId: handoffPreset?.modelId,
          plannedHandoffAfterMaterialActions: handoffPreset ? 4 : undefined,
          plannedHandoffReason: handoffPreset ? "Planned provider-neutral continuation after initial evidence collection." : undefined,
          maxProviderDecisions,
          maxMaterialActions,
          maxWallTimeMs: maxWallTimeMinutes * 60 * 1000,
        }),
      });
      const payload = (await response.json()) as { run?: SentinelRunRecord; error?: string };

      if (!response.ok || !payload.run) {
        throw new Error(payload.error || "Run creation failed.");
      }

      setRuns((current) => [payload.run!, ...current.filter((run) => run.id !== payload.run!.id)]);
      setSelectedRunId(payload.run.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Run creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!selectedRun) {
    return (
      <main className="sentinel-console">
        <section className="console-panel">
          <span className="console-eyebrow">Sentinel</span>
          <h1>No local run state exists yet.</h1>
        </section>
      </main>
    );
  }

  return (
    <main className="sentinel-console">
      <div className="console-backdrop" aria-hidden="true" />

      <header className="console-topbar">
        <Link className="console-brand" href="/">
          <span className="console-brand-mark"><Sparkles size={18} /></span>
          <span>SENTINEL</span>
        </Link>
        <nav className="console-nav" aria-label="Sentinel views">
          <Link href="/presence">Presence</Link>
          <Link href="/dashboard/agents">Legacy dashboard</Link>
        </nav>
      </header>

      <section className="console-hero">
        <div className="console-hero-copy">
          <span className="console-eyebrow">Canonical product cockpit</span>
          <h1>One governed body for any strong model.</h1>
          <p>
            Launch a public read-only mission through the real Sentinel spine, watch the selected model, authority scope, browser body, receipts, evidence, proof root and cleanup return to the interface.
          </p>
        </div>
        <MissionSignal run={selectedRun} />
      </section>

      <section className="launch-grid">
        <form className="launch-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <div>
              <span className="console-eyebrow">Launch</span>
              <h2>Public read-only mission</h2>
            </div>
            <Chip tone="neutral">/api/runs</Chip>
          </div>

          <label className="field-span">
            <span>Mission objective</span>
            <textarea
              className="console-textarea"
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              minLength={8}
              required
            />
          </label>

          <div className="field-grid">
            <label>
              <span>Site authority</span>
              <input className="console-input" value={targetOrigin} onChange={(event) => setTargetOrigin(event.target.value)} />
            </label>
            <label>
              <span>Depth</span>
              <select className="console-input" value={depth} onChange={(event) => setDepth(event.target.value as RunDepth)}>
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </label>
          </div>

          <div className="field-grid">
            <label>
              <span>Primary model</span>
              <select className="console-input" value={primaryPresetId} onChange={(event) => setPrimaryPresetId(event.target.value)}>
                {providerPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>{preset.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Planned handoff</span>
              <select className="console-input" value={handoffPresetId} onChange={(event) => setHandoffPresetId(event.target.value)}>
                <option value={noHandoffId}>None</option>
                {providerPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>{preset.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="provider-grid">
            <ProviderCard preset={primaryPreset} active role="Primary" />
            {handoffPreset ? (
              <ProviderCard preset={handoffPreset} active role="Handoff" />
            ) : (
              <div className="provider-card" data-active="false">
                <div>
                  <span>Handoff</span>
                  <strong>Off</strong>
                </div>
                <small>Single-model mission unless you enable continuation.</small>
                <code>no silent fallback</code>
              </div>
            )}
          </div>

          <div className="budget-grid">
            <label>
              <span>Provider turns</span>
              <input className="console-input" min={1} max={40} type="number" value={maxProviderDecisions} onChange={(event) => setMaxProviderDecisions(Number(event.target.value))} />
            </label>
            <label>
              <span>Material actions</span>
              <input className="console-input" min={1} max={80} type="number" value={maxMaterialActions} onChange={(event) => setMaxMaterialActions(Number(event.target.value))} />
            </label>
            <label>
              <span>Wall time minutes</span>
              <input className="console-input" min={1} max={45} type="number" value={maxWallTimeMinutes} onChange={(event) => setMaxWallTimeMinutes(Number(event.target.value))} />
            </label>
          </div>

          {error ? (
            <div className="console-alert">
              <CircleAlert size={16} />
              <span>{error}</span>
            </div>
          ) : null}

          <button className="console-run-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? <RefreshCw size={17} /> : <Play size={17} />}
            <span>{isSubmitting ? "Sentinel is running" : "Launch canonical mission"}</span>
          </button>
        </form>

        <aside className="console-panel live-panel">
          <div className="panel-heading">
            <div>
              <span className="console-eyebrow">Selected run</span>
              <h2>{selectedRun.summary.title}</h2>
            </div>
            <Chip tone={toneForStatus(selectedRun.status)}>{selectedRun.status.replace(/_/g, " ")}</Chip>
          </div>

          <div className="live-metrics">
            <div>
              <Brain size={16} />
              <span>Model</span>
              <strong>{selectedCanonical ? `${selectedCanonical.selectedProvider}/${selectedCanonical.selectedModel}` : "not selected"}</strong>
            </div>
            <div>
              <LockKeyhole size={16} />
              <span>Authority</span>
              <strong>{selectedCanonical ? shortList(selectedCanonical.authorityScope.grantedAuthorities) : "not granted"}</strong>
            </div>
            <div>
              <Globe2 size={16} />
              <span>Origin</span>
              <strong>{selectedCanonical ? shortList(selectedCanonical.authorityScope.browserAllowedOrigins) : targetOrigin}</strong>
            </div>
            <div>
              <Cpu size={16} />
              <span>Cleanup</span>
              <strong>{selectedCanonical?.cleanupStatus || "unknown"}</strong>
            </div>
          </div>

          <div className="affordance-panel">
            <div className="affordance-head">
              <Layers3 size={16} />
              <span>Executable graph presented to the model</span>
            </div>
            <p>{modelVisibleAffordanceText}</p>
          </div>

          <div className="run-switcher console-run-switcher" aria-label="Recent runs">
            {runs.slice(0, 5).map((run) => (
              <button
                className="run-chip"
                data-active={run.id === selectedRun.id ? "true" : "false"}
                key={run.id}
                onClick={() => setSelectedRunId(run.id)}
                type="button"
              >
                <span>{run.summary.title}</span>
                <small>{run.summary.startedAt}</small>
              </button>
            ))}
          </div>
        </aside>
      </section>

      <section className="runtime-grid">
        <CanonicalRunPanel run={selectedRun} />
        <ActionTimeline run={selectedRun} />
        <EvidencePanel run={selectedRun} />
      </section>

      <section className="console-panel spine-panel">
        <div className="spine-node">
          <Activity size={16} />
          <span>Public request</span>
        </div>
        <ArrowRight size={16} />
        <div className="spine-node">
          <Brain size={16} />
          <span>RuntimeHost</span>
        </div>
        <ArrowRight size={16} />
        <div className="spine-node">
          <Radar size={16} />
          <span>Root mission</span>
        </div>
        <ArrowRight size={16} />
        <div className="spine-node">
          <ShieldCheck size={16} />
          <span>Action kernel</span>
        </div>
        <ArrowRight size={16} />
        <div className="spine-node">
          <CheckCircle2 size={16} />
          <span>Receipts</span>
        </div>
      </section>
    </main>
  );
}
