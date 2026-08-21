import { createHash, randomUUID } from "crypto";
import { mkdir, writeFile } from "fs/promises";
import path from "path";
import { spawn } from "child_process";

export type CanonicalProductRunInput = {
  objective: string;
  targetOrigin?: string;
  providerId?: string;
  backendId?: string;
  modelId?: string;
  maxProviderDecisions?: number;
  maxMaterialActions?: number;
};

export type CanonicalProductCliResult = {
  root_mission_id: string;
  status: string;
  final_reason: string;
  blocked_reason?: string | null;
  provider_decision_count: number;
  material_action_count: number;
  current_stage: string;
  provider_model: string;
  authority_scope: {
    granted_authorities?: string[];
    browser_allowed_origins?: string[];
    public_web_read_only?: boolean;
  };
  model_visible_affordances: string[];
  completed_actions: Array<{
    receipt_id: string;
    capability: string;
    operation: string;
    status: string;
    material_action: boolean;
    evidence_refs: string[];
  }>;
  evidence_refs: string[];
  terminal_answer?: string;
  mission_record_created_before_provider: boolean;
  root_created_before_first_provider_call: boolean;
  product_receipt_refs: string[];
  proof_root: {
    proof_root_id?: string;
    receipt_artifacts_verified?: boolean;
    kernel_timeline_verified?: boolean;
    proof_root_hash?: string;
  };
  replay: {
    side_effects_reexecuted?: boolean;
    timeline_verified?: boolean;
  };
  cleanup_completed: boolean;
  public_product_spine: Record<string, unknown>;
};

const DEFAULT_OBJECTIVE = "Find official SQLite documentation explaining generated columns and provide a short useful answer.";

function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

function safeRunId() {
  return `web_canonical_${new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14)}_${randomUUID().slice(0, 8)}`;
}

function webDataRoot() {
  return path.resolve(process.cwd(), "../../data");
}

function sentinelCoreRoot() {
  return path.resolve(process.env.SENTINEL_CORE_ROOT || path.resolve(process.cwd(), "../../services/sentinel-core"));
}

function pythonInvocationPrefix() {
  const configured = process.env.SENTINEL_PYTHON_COMMAND?.trim();
  if (configured) return [configured];
  return process.platform === "win32" ? ["py", "-3.13"] : ["python"];
}

function parseCliJson(stdout: string): CanonicalProductCliResult {
  const lines = stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const candidate = [...lines].reverse().find((line) => line.startsWith("{") && line.endsWith("}"));
  if (!candidate) {
    throw new Error(`canonical_product_json_missing:${sha256(stdout).slice(0, 16)}`);
  }
  return JSON.parse(candidate) as CanonicalProductCliResult;
}

export async function runCanonicalProductMissionFromWeb(
  input: CanonicalProductRunInput,
): Promise<{ runId: string; runRoot: string; workspaceRoot: string; result: CanonicalProductCliResult }> {
  const runId = safeRunId();
  const dataRoot = webDataRoot();
  const runRoot = path.join(dataRoot, "canonical_product_runs", runId);
  const workspaceRoot = path.join(dataRoot, "canonical_product_workspaces", runId);
  const objective = input.objective.trim() || DEFAULT_OBJECTIVE;
  const targetOrigin = (input.targetOrigin || "sqlite.org").trim() || "sqlite.org";
  const providerId = (input.providerId || process.env.SENTINEL_CANONICAL_MODEL_PROVIDER_ID || "aliyun_dashscope").trim();
  const backendId = (input.backendId || process.env.SENTINEL_CANONICAL_MODEL_BACKEND_ID || "aliyun_openai_compatible_chat").trim();
  const modelId = (input.modelId || process.env.SENTINEL_CANONICAL_MODEL_ID || "qwen-plus").trim();

  await mkdir(runRoot, { recursive: true });
  await mkdir(workspaceRoot, { recursive: true });
  await writeFile(
    path.join(workspaceRoot, "PUBLIC_PRODUCT_REQUEST.md"),
    `# Public Product Request\n\nObjective hash: ${sha256(objective)}\nTarget origin: ${targetOrigin}\n`,
    "utf8",
  );

  const [pythonBin, ...pythonPrefixArgs] = pythonInvocationPrefix();
  const args = [
    ...pythonPrefixArgs,
    "-m",
    "sentinel.cli",
    "canonical-product-run",
    "--objective",
    objective,
    "--workspace",
    workspaceRoot,
    "--run-root",
    runRoot,
    "--provider-id",
    providerId,
    "--backend-id",
    backendId,
    "--model-id",
    modelId,
    "--max-provider-decisions",
    String(input.maxProviderDecisions ?? 10),
    "--max-material-actions",
    String(input.maxMaterialActions ?? 16),
    "--enable-browser-readonly-physical",
    "--browser-allowed-origin",
    targetOrigin,
    "--json",
  ];

  const result = await new Promise<CanonicalProductCliResult>((resolve, reject) => {
    const child = spawn(pythonBin, args, {
      cwd: sentinelCoreRoot(),
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error("canonical_product_subprocess_timeout"));
    }, 10 * 60 * 1000);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", (error) => {
      clearTimeout(timeout);
      reject(new Error(`canonical_product_subprocess_error:${error.name}`));
    });
    child.on("close", () => {
      clearTimeout(timeout);
      try {
        resolve(parseCliJson(stdout));
      } catch (error) {
        reject(new Error(`${error instanceof Error ? error.message : "canonical_product_parse_failed"}:stderr_hash:${sha256(stderr).slice(0, 16)}`));
      }
    });
  });

  return { runId, runRoot, workspaceRoot, result };
}
