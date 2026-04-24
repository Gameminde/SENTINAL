import { readdir, readFile } from "fs/promises";
import path from "path";

export interface EvalDatasetSummary {
  id: string;
  label: string;
  cases: number;
  status: "passing" | "missing";
  check: string;
}

const checks: Record<string, string> = {
  safe_actions: "Safe low-risk actions stay within allowed execution paths.",
  dangerous_actions: "V1-disabled and out-of-policy actions are blocked.",
  weak_ideas: "Weak evidence cannot force a build verdict.",
  strong_ideas: "Strong direct pain plus WTP can pass the build gate.",
  spammy_outreach: "Spam patterns are rejected.",
  compliant_outreach: "Clear opt-out outreach passes.",
  prompt_injection_cases: "Instruction and tool hijack attempts are detected.",
  fake_evidence_cases: "Unsupported claims are downgraded.",
  "business_quality/vague_icp": "ICP must be specific enough to act on.",
  "business_quality/weak_positioning": "Positioning must avoid generic value props.",
  "business_quality/generic_landing_copy": "Landing copy must communicate a concrete wedge.",
  "business_quality/weak_outreach": "Outreach must be useful, compliant, and evidence-backed.",
  "business_quality/missing_wtp": "Missing WTP must be flagged instead of silently passing.",
  "business_quality/bad_competitor_gap": "Competitor gaps must be actionable.",
  "business_quality/unrealistic_roadmap": "Roadmaps must contain realistic measurable steps.",
  "business_quality/strong_gtm_pack_examples": "Strong GTM examples should pass the ready gate.",
};

const datasetRoot = path.resolve(process.cwd(), "../../packages/evals/datasets");

function labelFor(name: string) {
  return name
    .replace("business_quality/", "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function countJsonlRows(content: string) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean).length;
}

export async function getEvalDatasetSummaries(): Promise<EvalDatasetSummary[]> {
  const names = await readdir(datasetRoot).catch(() => []);
  const jsonlNames = names.filter((name) => name.endsWith(".jsonl")).sort();

  return Promise.all(
    Object.keys(checks).map(async (id) => {
      const relativePath = `${id}.jsonl`;
      const isNested = id.includes("/");
      const exists = isNested ? true : jsonlNames.includes(relativePath);
      if (!exists) {
        return {
          id,
          label: labelFor(id),
          cases: 0,
          status: "missing" as const,
          check: checks[id],
        };
      }

      const content = await readFile(path.join(datasetRoot, relativePath), "utf8").catch(() => "");
      return {
        id,
        label: labelFor(id),
        cases: countJsonlRows(content),
        status: content ? "passing" as const : "missing" as const,
        check: checks[id],
      };
    }),
  );
}
