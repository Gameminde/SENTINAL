import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { updateActionApproval } from "@/lib/run-store";
import type { ApprovalStatus } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const allowedStatuses = new Set<ApprovalStatus>(["approved", "rejected"]);

export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string; actionId: string }> },
) {
  const { runId, actionId } = await params;
  const body = (await request.json().catch(() => null)) as { approvalStatus?: ApprovalStatus } | null;
  const approvalStatus = body?.approvalStatus;

  if (!approvalStatus || !allowedStatuses.has(approvalStatus)) {
    return NextResponse.json({ error: "Approval status must be approved or rejected." }, { status: 400 });
  }

  try {
    const user = await getRequestUser(request);
    const run = await updateActionApproval(runId, actionId, approvalStatus, user.userId);

    if (!run) {
      return NextResponse.json({ error: "Run or action not found." }, { status: 404 });
    }

    return NextResponse.json({ run });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    throw error;
  }
}
