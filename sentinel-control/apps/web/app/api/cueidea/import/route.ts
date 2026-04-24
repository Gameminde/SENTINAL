import { NextResponse } from "next/server";
import { AuthRequiredError, getRequestUser } from "@/lib/auth";
import { fetchCueIdeaValidation, normalizeCueIdeaImport } from "@/lib/cueidea-import";
import { createRunFromCueIdeaImport } from "@/lib/run-store";
import type { CueIdeaImportRequest } from "@/lib/cueidea-import";
import type { RunDepth } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const allowedDepths = new Set<RunDepth>(["quick", "standard", "deep"]);

function parseReport(value: unknown) {
  if (typeof value !== "string") return value;
  return JSON.parse(value);
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as CueIdeaImportRequest | null;
  const validationId = body?.validationId?.trim();
  const depth = body?.depth && allowedDepths.has(body.depth) ? body.depth : "standard";

  if (!validationId && body?.report === undefined) {
    return NextResponse.json({ error: "Provide a CueIdea validation id or pasted report JSON." }, { status: 400 });
  }

  try {
    const user = await getRequestUser(request);
    const payload = validationId ? await fetchCueIdeaValidation(validationId) : parseReport(body?.report);
    const imported = normalizeCueIdeaImport(payload);
    const run = await createRunFromCueIdeaImport(imported, {
      depth,
      niche: body?.niche?.trim() || undefined,
      userId: user.userId,
    });

    return NextResponse.json({ run, imported }, { status: 201 });
  } catch (error) {
    if (error instanceof AuthRequiredError) return NextResponse.json({ error: error.message }, { status: 401 });
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "CueIdea import failed." },
      { status: 400 },
    );
  }
}
