import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { recordFeedback } from "@/lib/run-store";
import type { CreateFeedbackInput, FeedbackRating, FeedbackTargetType } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const targetTypes = new Set<FeedbackTargetType>(["action", "asset", "evidence", "run"]);
const ratings = new Set<FeedbackRating>(["useful", "weak", "approved", "rejected"]);

export async function POST(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const body = (await request.json().catch(() => null)) as Partial<CreateFeedbackInput> | null;

  if (!body?.targetType || !targetTypes.has(body.targetType)) {
    return NextResponse.json({ error: "Feedback target type is invalid." }, { status: 400 });
  }

  if (!body.targetId?.trim()) {
    return NextResponse.json({ error: "Feedback target id is required." }, { status: 400 });
  }

  if (!body.rating || !ratings.has(body.rating)) {
    return NextResponse.json({ error: "Feedback rating is invalid." }, { status: 400 });
  }

  try {
    const user = await getRequestUser(request);
    const run = await recordFeedback(runId, {
      targetType: body.targetType,
      targetId: body.targetId.trim(),
      rating: body.rating,
      note: body.note?.trim() || undefined,
    }, user.userId);

    if (!run) {
      return NextResponse.json({ error: "Run not found." }, { status: 404 });
    }

    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
