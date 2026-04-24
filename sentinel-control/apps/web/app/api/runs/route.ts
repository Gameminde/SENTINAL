import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { createRun, listRunsForUser } from "@/lib/run-store";
import type { CreateRunInput, RunDepth } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const allowedDepths = new Set<RunDepth>(["quick", "standard", "deep"]);

export async function GET(request: Request) {
  try {
    const user = await getRequestUser(request);
    const runs = await listRunsForUser(user.userId);
    return NextResponse.json({ runs, user: { id: user.userId, source: user.source, authenticated: user.authenticated } });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as Partial<CreateRunInput> | null;
  const idea = body?.idea?.trim();
  const depth = body?.depth && allowedDepths.has(body.depth) ? body.depth : "standard";

  if (!idea || idea.length < 8) {
    return NextResponse.json({ error: "Idea must contain at least 8 characters." }, { status: 400 });
  }

  try {
    const user = await getRequestUser(request);
    const run = await createRun({
      idea,
      niche: body?.niche?.trim() || undefined,
      depth,
      userId: user.userId,
    });

    return NextResponse.json({ run }, { status: 201 });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
