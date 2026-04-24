import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { updateWatchlistItem } from "@/lib/run-store";
import type { WatchlistStatus } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const allowedStatuses = new Set<WatchlistStatus>(["monitoring", "needs_review", "interview", "validated", "archived"]);

export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string; itemId: string }> },
) {
  const { runId, itemId } = await params;
  const body = (await request.json().catch(() => null)) as { status?: WatchlistStatus; note?: string } | null;
  const status = body?.status;

  if (!status || !allowedStatuses.has(status)) {
    return NextResponse.json({ error: "Watchlist status is invalid." }, { status: 400 });
  }

  try {
    const user = await getRequestUser(request);
    const run = await updateWatchlistItem(runId, itemId, status, body?.note?.trim() || undefined, user.userId);

    if (!run) {
      return NextResponse.json({ error: "Run or watchlist item not found." }, { status: 404 });
    }

    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
