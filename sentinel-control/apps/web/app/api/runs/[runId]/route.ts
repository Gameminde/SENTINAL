import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { getRun } from "@/lib/run-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  try {
    const user = await getRequestUser(_request);
    const run = await getRun(runId, user.userId);

    if (!run) {
      return NextResponse.json({ error: "Run not found." }, { status: 404 });
    }

    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
