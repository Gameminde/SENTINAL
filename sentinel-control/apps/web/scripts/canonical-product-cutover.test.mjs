import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");

function read(rel) {
  return readFileSync(path.join(root, rel), "utf8");
}

const route = read("app/api/runs/route.ts");
const runtime = read("lib/canonical-runtime.ts");
const store = read("lib/run-store.ts");
const operator = read("components/run-operator.tsx");

assert.match(route, /runCanonicalProductMissionFromWeb/, "public run route must invoke the canonical runtime helper");
assert.match(route, /mode === "sandbox_hypothesis" \? "sandbox_hypothesis" : "canonical_public"/, "canonical public mode must be the default public route");
assert.match(route, /maxProviderDecisions:\s*body\?\.maxProviderDecisions/, "public run route must pass provider decision budget");
assert.match(route, /maxMaterialActions:\s*body\?\.maxMaterialActions/, "public run route must pass material action budget");
assert.match(route, /maxWallTimeMs:\s*body\?\.maxWallTimeMs/, "public run route must pass wall-time budget");
assert.doesNotMatch(route, /browser-observe|browser-act|https:\/\/integrate\.api\.nvidia\.com|dashscope-intl\.aliyuncs\.com/, "route must not call a browser or provider directly");

assert.match(runtime, /"canonical-product-run"/, "web helper must launch the canonical product CLI");
assert.match(runtime, /"--enable-browser-readonly-physical"/, "web helper must enable the canonical physical browser backend");
assert.match(runtime, /"--browser-allowed-origin"/, "web helper must pass explicit origin authority");
assert.match(runtime, /const timeoutMs = clampWallTimeMs\(input\.maxWallTimeMs\)/, "web helper must derive subprocess timeout from bounded input");
assert.match(runtime, /setTimeout\(\(\) => \{[\s\S]*?\}, timeoutMs\)/, "web helper must use the bounded wall-time budget");
assert.doesNotMatch(runtime, /browser-observe|browser-act|browser-session-demo/, "web helper must not bypass the canonical product route");
assert.doesNotMatch(runtime, /stdout.*traceRecords|stderr.*traceRecords/, "raw process output must not be persisted into run traces");

assert.match(store, /canonical\.model_visible_affordances/, "web store must persist affordances from the runtime result");
assert.match(store, /canonical\.completed_actions/, "web store must persist completed actions from runtime receipts");
assert.match(store, /canonical\.proof_root\?\.receipt_artifacts_verified/, "web store must expose proof-root verification");

assert.match(operator, /mode: "canonical_public"/, "visible run button must launch canonical public mode");
assert.match(operator, /selectedRun\.canonicalMission\.modelVisibleAffordances/, "UI must render graph-projected affordances");
assert.doesNotMatch(operator, /workspace\.list|real_browser\.open|real_browser\.extract_evidence/, "UI component must not hardcode capability names");

console.log("canonical-product-cutover.test.mjs passed");
