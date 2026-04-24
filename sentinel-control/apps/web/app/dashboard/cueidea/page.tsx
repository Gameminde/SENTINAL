import { CueIdeaImportPanel } from "@/components/cueidea-import-panel";
import { Metric } from "@/components/ui";
import { listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

export default async function CueIdeaPage() {
  const runs = await listRuns();
  const cueideaRuns = runs.filter((run) => run.traceRecords.some((trace) => trace.eventType === "cueidea_imported"));
  const evidenceCount = cueideaRuns.reduce((total, run) => total + run.evidence.length, 0);
  const writtenCount = cueideaRuns.filter((run) => run.project.status === "Files written locally").length;

  return (
    <div className="page">
      <section className="hero-panel">
        <div className="eyebrow">Sprint 7A</div>
        <h1 className="page-title">CueIdea read-only bridge</h1>
        <p className="page-copy">
          Import CueIdea validation reports into Sentinel, normalize evidence, and generate a local GTM pack without writing back to CueIdea.
        </p>
        <div className="metric-grid">
          <Metric label="Imports" value={`${cueideaRuns.length}`} sub="local Sentinel runs" />
          <Metric label="Evidence" value={`${evidenceCount}`} sub="normalized rows" />
          <Metric label="Generated" value={`${writtenCount}`} sub="local folders" />
          <Metric label="Mode" value="Read-only" sub="CueIdea source" />
        </div>
      </section>

      <CueIdeaImportPanel recentRuns={cueideaRuns} />
    </div>
  );
}
