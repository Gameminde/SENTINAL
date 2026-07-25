import { readFile } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type SafePresenceEvent = {
  schema_version: "presence_event_v1";
  mission_id: string;
  sequence: number;
  event_hash: string;
  data_not_authority: true;
  can_grant_authority: false;
  can_execute: false;
};

export async function GET(request: NextRequest) {
  const configuredRoot = process.env.SENTINEL_PRESENCE_STREAM_ROOT;
  const configuredPath = process.env.SENTINEL_PRESENCE_STREAM_PATH;
  if (!configuredRoot || !configuredPath) {
    return NextResponse.json(
      {
        configured: false,
        events: [],
        message: "No live Presence Protocol stream is configured.",
      },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }

  const root = resolve(configuredRoot);
  const streamPath = resolve(configuredPath);
  const pathFromRoot = relative(root, streamPath);
  if (pathFromRoot.startsWith("..") || isAbsolute(pathFromRoot)) {
    return NextResponse.json(
      { configured: false, events: [], message: "Presence stream path is outside its allowed root." },
      { status: 403, headers: { "cache-control": "no-store" } },
    );
  }

  const after = safeSequence(request.nextUrl.searchParams.get("after"));
  const requestedMission = request.nextUrl.searchParams.get("mission_id") || "";
  try {
    const source = await readFile(streamPath, "utf8");
    const parsed: SafePresenceEvent[] = [];
    let invalidLineCount = 0;
    for (const line of source.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try {
        const candidate: unknown = JSON.parse(line);
        if (!isSafePresenceEvent(candidate)) {
          invalidLineCount += 1;
          continue;
        }
        parsed.push(candidate);
      } catch {
        invalidLineCount += 1;
      }
    }
    parsed.sort((left, right) => left.sequence - right.sequence);
    const missionId = requestedMission || parsed[parsed.length - 1]?.mission_id || "";
    const deduplicated = new Map<number, SafePresenceEvent>();
    for (const event of parsed) {
      if (event.mission_id !== missionId || event.sequence <= after) continue;
      const existing = deduplicated.get(event.sequence);
      if (!existing || existing.event_hash === event.event_hash) {
        deduplicated.set(event.sequence, event);
      } else {
        invalidLineCount += 1;
      }
    }
    return NextResponse.json(
      {
        configured: true,
        mission_id: missionId,
        events: [...deduplicated.values()],
        telemetry_incomplete: invalidLineCount > 0,
        invalid_line_count: invalidLineCount,
      },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      {
        configured: true,
        events: [],
        message: "The safe Presence Protocol stream is not readable yet.",
      },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }
}

function safeSequence(value: string | null) {
  const parsed = Number.parseInt(value || "-1", 10);
  return Number.isFinite(parsed) && parsed >= -1 ? parsed : -1;
}

function isSafePresenceEvent(value: unknown): value is SafePresenceEvent {
  if (!value || typeof value !== "object") return false;
  const event = value as Record<string, unknown>;
  return (
    event.schema_version === "presence_event_v1" &&
    typeof event.mission_id === "string" &&
    event.mission_id.length > 0 &&
    typeof event.sequence === "number" &&
    Number.isInteger(event.sequence) &&
    event.sequence >= 0 &&
    typeof event.event_hash === "string" &&
    event.event_hash.length > 0 &&
    event.data_not_authority === true &&
    event.can_grant_authority === false &&
    event.can_execute === false
  );
}
