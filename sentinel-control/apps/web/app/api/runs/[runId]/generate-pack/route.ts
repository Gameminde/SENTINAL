import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { executeGeneratedProject } from "@/lib/run-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;

  try {
    const user = await getRequestUser(request);
    const run = await executeGeneratedProject(runId, user.userId);
    if (!run) {
      return NextResponse.json({ error: "Run not found." }, { status: 404 });
    }
    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Pack generation failed." },
      { status: 400 },
    );
  }
}
