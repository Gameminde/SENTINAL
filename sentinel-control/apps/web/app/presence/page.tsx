import type { Metadata } from "next";
import { PresenceShell } from "@/components/presence-shell";

export const metadata: Metadata = {
  title: "Sentinel Presence",
  description: "Living Obsidian mission presence, route and developer X-Ray.",
};

export default function PresencePage() {
  return <PresenceShell />;
}
