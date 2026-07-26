import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const source = readFileSync(resolve("components/presence-shell.tsx"), "utf8");
const protocolSource = readFileSync(resolve("lib/presence-protocol.ts"), "utf8");

const forbiddenPrimaryReplayMarkers = [
  "presence-transport",
  "Replay controls",
  "Replay only",
  "Kill unavailable / replay",
  "? \"Replay\"",
  "Play route",
  "useState<PresenceEventV1[]>(mdnPresenceReplay.events)",
];

for (const marker of forbiddenPrimaryReplayMarkers) {
  if (source.includes(marker) || protocolSource.includes(marker)) {
    throw new Error(`presence shell still exposes primary replay control: ${marker}`);
  }
}

const requiredMarkers = [
  "const latestIndex = Math.max(0, events.length - 1)",
  "const current = events[latestIndex]",
  "presenceStreamConnectingEvent",
  "void connectLive()",
  "Runtime path",
  "Action code",
  "Read-only observer",
];

for (const marker of requiredMarkers) {
  if (!source.includes(marker)) {
    throw new Error(`presence shell is missing real-state marker: ${marker}`);
  }
}

console.log("presence_shell_real_state_contract=PASS");
