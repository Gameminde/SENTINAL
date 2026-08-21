import { RunOperator } from "@/components/run-operator";
import { listRuns } from "@/lib/run-store";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const runs = await listRuns();
  return <RunOperator initialRuns={runs} />;
}
