import { FlaskConical, ShieldCheck } from "lucide-react";
import { Chip, Metric, SectionBand } from "@/components/ui";
import { getEvalDatasetSummaries } from "@/lib/eval-results";

export const dynamic = "force-dynamic";

export default async function EvalsPage() {
  const datasets = await getEvalDatasetSummaries();
  const totalCases = datasets.reduce((total, dataset) => total + dataset.cases, 0);
  const passing = datasets.filter((dataset) => dataset.status === "passing").length;
  const missing = datasets.length - passing;

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Evals</div>
          <h1 className="page-title">Safety and quality evaluation board</h1>
          <p className="page-copy">
            Sprint 5B makes Sentinel measurable: action safety, idea quality, outreach compliance, injection handling, and evidence quality all have explicit datasets.
          </p>
          <div className="metric-grid">
            <Metric label="Datasets" value={`${datasets.length}`} sub="registered checks" />
            <Metric label="Cases" value={`${totalCases}`} sub="JSONL rows" />
            <Metric label="Passing Sets" value={`${passing}`} sub="covered by pytest" />
            <Metric label="Missing" value={`${missing}`} sub="dataset files" />
          </div>
        </div>

        <div className="panel">
          <SectionBand eyebrow="Runner" title="Current eval contract">
            <div className="list">
              <div className="list-item">
                <strong>Python runner</strong>
                <p>`sentinel.learning.eval_runner` executes these datasets against Firewall, Debate, outreach review, prompt-injection detection, and fake-evidence scoring.</p>
              </div>
              <div className="list-item">
                <strong>Test gate</strong>
                <p>`services/sentinel-core/tests/test_evals.py` fails if any required Sprint 5 case fails.</p>
              </div>
            </div>
          </SectionBand>
        </div>
      </section>

      <section className="panel">
        <SectionBand
          eyebrow="Datasets"
          title="Eval coverage"
          action={
            <button className="secondary-btn" type="button">
              <FlaskConical size={16} />
              <span>{totalCases} cases</span>
            </button>
          }
        >
          <div className="eval-grid">
            {datasets.map((dataset) => (
              <div className="eval-card" key={dataset.id}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start", flexWrap: "wrap" }}>
                  <div>
                    <strong>{dataset.label}</strong>
                    <p>{dataset.check}</p>
                  </div>
                  <Chip tone={dataset.status === "passing" ? "good" : "bad"}>
                    <ShieldCheck size={14} />
                    {dataset.status}
                  </Chip>
                </div>
                <div className="eval-footer">
                  <span>{dataset.cases} cases</span>
                  <span>{dataset.id}.jsonl</span>
                </div>
              </div>
            ))}
          </div>
        </SectionBand>
      </section>
    </div>
  );
}
