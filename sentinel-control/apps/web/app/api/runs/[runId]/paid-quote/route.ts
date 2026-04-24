import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { preparePaidRunQuote } from "@/lib/run-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  try {
    const user = await getRequestUser(request);
    const run = await preparePaidRunQuote(runId, user.userId);

    if (!run) {
      return NextResponse.json({ error: "Run not found." }, { status: 404 });
    }

    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
