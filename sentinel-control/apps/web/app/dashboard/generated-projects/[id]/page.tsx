import { FileText, FolderOpen } from "lucide-react";
import { FeedbackControls } from "@/components/feedback-controls";
import { SectionBand, Chip } from "@/components/ui";
import { projects } from "@/lib/demo-data";
import { listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

const fallbackFiles = [
  { id: "fallback_verdict", name: "00_VERDICT.md", body: "Decision: niche down first.\n\nDo not build until WTP and reachability are both proven." },
  { id: "fallback_evidence", name: "01_EVIDENCE.md", body: "Evidence references: ev_001, ev_002, ev_005, ev_007.\n\nDirect pain is visible and WTP exists." },
  { id: "fallback_icp", name: "02_ICP.md", body: "Primary ICP: freelancers and small agencies who manage recurring unpaid invoices." },
  { id: "fallback_outreach", name: "05_OUTREACH_MESSAGES.md", body: "Draft-only outreach. Ask for feedback. Do not auto-send." },
  { id: "fallback_roadmap", name: "07_7_DAY_ROADMAP.md", body: "Day 1-2 interview.\nDay 3 landing test.\nDay 4 pricing test.\nDay 5 approval review.\nDay 6-7 decision." },
];

export default async function GeneratedProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const runs = await listRuns();
  const run = runs.find((item) => item.project.id === id);
  const project = run?.project ?? projects.find((item) => item.id === id) ?? projects[0];
  const files = run?.generatedAssets.map((asset) => ({ id: asset.id, name: asset.title, body: asset.content })) ?? fallbackFiles;
  const traceRecords = run?.traceRecords ?? [
    { id: "fallback_started", eventType: "run_started", message: "Idea received and evidence capture initiated." },
    { id: "fallback_decision", eventType: "decision_created", message: "Debate returned niche down because WTP was present but the wedge is still narrow." },
    { id: "fallback_action", eventType: "action_proposed", message: "Folder creation and draft-only outreach were proposed before execution." },
  ];

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Generated Project</div>
          <h1 className="page-title">{project.name}</h1>
          <p className="page-copy">{project.description}</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
            <Chip tone="good"><FolderOpen size={14} /> Folder created</Chip>
            <Chip tone="neutral"><FileText size={14} /> {project.files.length} docs</Chip>
          </div>
        </div>
        <div className="panel">
          <SectionBand eyebrow="Contents" title="Pack files">
            <div className="list">
              {project.files.map((file) => (
                <div className="list-item" key={file}>
                  <strong>{file}</strong>
                  <p>Included in the generated project and linked to the evidence trail.</p>
                </div>
              ))}
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="columns-2">
        <section className="panel">
          <SectionBand eyebrow="Preview" title="File browser">
            <div className="list">
              {files.map((file, index) => (
                <div className="list-item" key={file.name} style={{ borderColor: index === 0 ? "rgba(31,138,142,0.22)" : undefined }}>
                  <strong>{file.name}</strong>
                  <p style={{ whiteSpace: "pre-line" }}>{file.body}</p>
                  {run ? <FeedbackControls feedback={run.feedback} runId={run.id} targetId={file.id} targetType="asset" /> : null}
                </div>
              ))}
            </div>
          </SectionBand>
        </section>

        <section className="panel">
          <SectionBand eyebrow="Trace" title="Execution log">
            <div className="list">
              {traceRecords.map((trace) => (
                <div className="list-item" key={trace.id}>
                  <strong>{trace.eventType}</strong>
                  <p>{trace.message}</p>
                </div>
              ))}
            </div>
          </SectionBand>
        </section>
      </section>
    </div>
  );
}
