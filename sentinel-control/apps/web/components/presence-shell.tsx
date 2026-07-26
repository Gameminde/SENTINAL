"use client";

import {
  Aperture,
  ChevronLeft,
  ChevronRight,
  CircleStop,
  Eye,
  EyeOff,
  Mic,
  Pause,
  Play,
  RotateCcw,
  Settings2,
  TerminalSquare,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { LivingObsidianStage } from "@/components/living-obsidian-stage";
import {
  mdnPresenceReplay,
  type PresenceEventV1,
  type PresenceState,
} from "@/lib/presence-protocol";

const telemetryIncomplete = "TELEMETRY_INCOMPLETE";
const routeSlots = ["north-west", "west", "south-west", "north-east", "east", "south-east"] as const;

const demoStates = [
  {
    key: "idle",
    label: "idle",
    state: "SLEEPING",
    summary: "Present, quiet, and ready.",
  },
  {
    key: "listening",
    label: "listening",
    state: "LISTENING",
    summary: "I’m gathering the shape of your intent.",
  },
  {
    key: "planning",
    label: "planning",
    state: "PLANNING",
    summary: "I’m testing several routes. One is beginning to hold.",
  },
  {
    key: "acting",
    label: "acting",
    state: "ACTING",
    summary: "The chosen route is moving through the browser organ.",
  },
  {
    key: "waiting",
    label: "waiting",
    state: "WAITING_AUTHORITY",
    summary: "I’m holding at the authority boundary.",
  },
  {
    key: "blocked",
    label: "blocked",
    state: "BLOCKED",
    summary: "The route broke here. I’m preserving the cause.",
  },
  {
    key: "failed",
    label: "failed",
    state: "TELEMETRY_INCOMPLETE",
    summary: "The evidence stream is incomplete. I won’t guess.",
  },
  {
    key: "completed",
    label: "completed",
    state: "COMPLETED",
    summary: "The proof holds. The mission is complete.",
  },
] as const satisfies readonly {
  key: string;
  label: string;
  state: PresenceState;
  summary: string;
}[];

type DemoKey = (typeof demoStates)[number]["key"] | "truth";

function stateLabel(state: PresenceState) {
  return state.replace(/_/g, " ").toLowerCase();
}

function xrayValue(value: unknown) {
  if (value === undefined || value === null || value === "") return telemetryIncomplete;
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function shortRef(value: string | undefined | null) {
  const rendered = xrayValue(value);
  if (rendered === telemetryIncomplete) return rendered;
  if (rendered.length <= 26) return rendered;
  return `${rendered.slice(0, 13)}...${rendered.slice(-9)}`;
}

function formatAffordances(value: string[] | undefined) {
  if (!value?.length) return telemetryIncomplete;
  return value.join(", ");
}

function formatGateResults(value: Record<string, string> | undefined) {
  const entries = Object.entries(value ?? {});
  if (!entries.length) return telemetryIncomplete;
  return entries.map(([key, status]) => `${key}: ${status}`).join(" | ");
}

function decisionLabel(index: number | undefined) {
  return typeof index === "number" && index > 0 ? `D${index}` : "START";
}

export function PresenceShell() {
  const [events, setEvents] = useState<PresenceEventV1[]>(mdnPresenceReplay.events);
  const [connection, setConnection] = useState<"replay" | "connecting" | "live" | "unavailable">("replay");
  const [liveMissionId, setLiveMissionId] = useState("");
  const [eventIndex, setEventIndex] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [routeVisible, setRouteVisible] = useState(false);
  const [xrayVisible, setXrayVisible] = useState(false);
  const [demoVisible, setDemoVisible] = useState(false);
  const [demoKey, setDemoKey] = useState<DemoKey>("truth");
  const [command, setCommand] = useState("");
  const current = events[eventIndex];
  const selected = events[selectedIndex] ?? current;
  const demo = demoStates.find((item) => item.key === demoKey);
  const visualState = demo?.state ?? current.presence_state;
  const visualSummary = demo?.summary ?? current.safe_summary;
  const visualLabel = demo?.label ?? stateLabel(current.presence_state);

  useEffect(() => {
    if (!playing) return;
    if (eventIndex >= events.length - 1) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => {
      setEventIndex((value) => Math.min(value + 1, events.length - 1));
      setSelectedIndex((value) => (value === eventIndex ? Math.min(value + 1, events.length - 1) : value));
    }, 1700);
    return () => window.clearTimeout(timer);
  }, [eventIndex, events.length, playing]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.shiftKey && event.key.toLowerCase() === "x") {
        event.preventDefault();
        setXrayVisible((value) => !value);
      }
      if (event.key === "Escape") setXrayVisible(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (connection !== "live" || !liveMissionId) return;
    const timer = window.setInterval(async () => {
      const after = events[events.length - 1]?.sequence ?? -1;
      try {
        const response = await fetch(
          `/api/presence/events?mission_id=${encodeURIComponent(liveMissionId)}&after=${after}`,
          { cache: "no-store" },
        );
        if (!response.ok) return;
        const payload = (await response.json()) as { events?: PresenceEventV1[] };
        if (!payload.events?.length) return;
        setEvents((currentEvents) => mergePresenceEvents(currentEvents, payload.events || []));
      } catch {
        // A disconnected observer is expected to leave the mission unaffected.
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [connection, events, liveMissionId]);

  const routeEvents = useMemo(() => {
    const start = Math.max(0, Math.min(eventIndex - 3, events.length - routeSlots.length));
    return events.slice(start, start + routeSlots.length);
  }, [eventIndex, events]);

  function chooseEvent(index: number) {
    setEventIndex(index);
    setSelectedIndex(index);
    setPlaying(false);
    setDemoKey("truth");
  }

  function submitCommand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!command.trim()) return;
    setCommand("");
  }

  async function connectLive() {
    setConnection("connecting");
    try {
      const response = await fetch("/api/presence/events?after=-1", { cache: "no-store" });
      const payload = (await response.json().catch(() => null)) as {
        configured?: boolean;
        mission_id?: string;
        events?: PresenceEventV1[];
      } | null;
      if (!response.ok || !payload?.configured || !payload.mission_id || !payload.events?.length) {
        setConnection("unavailable");
        return;
      }
      setEvents(payload.events);
      setLiveMissionId(payload.mission_id);
      setEventIndex(payload.events.length - 1);
      setSelectedIndex(payload.events.length - 1);
      setConnection("live");
      setPlaying(false);
      setDemoKey("truth");
    } catch {
      setConnection("unavailable");
    }
  }

  return (
    <main
      className="presence-page"
      data-demo-active={demo ? "true" : "false"}
      data-presence-state={visualState}
    >
      <div className="presence-noise" />
      <div className="presence-vignette" />

      <header className="presence-topbar">
        <div className="presence-wordmark">
          <span className="presence-sigil" />
          <span>SENTINEL</span>
        </div>
        <button
          className="presence-replay-label"
          data-connection={connection}
          onClick={connection === "live" ? undefined : connectLive}
          type="button"
        >
          <span className="presence-live-dot" />
          <span>
            {connection === "live"
              ? "LIVE SAFE STREAM"
              : connection === "connecting"
                ? "CONNECTING"
                : connection === "unavailable"
                  ? "LIVE UNAVAILABLE"
                  : "SAFE REPLAY"}
          </span>
          <span className="presence-divider">/</span>
          <span>{connection === "live" ? liveMissionId : mdnPresenceReplay.label}</span>
        </button>
        <button
          aria-label="Toggle deterministic visual state lab"
          className="presence-icon-button"
          data-active={demoVisible ? "true" : "false"}
          onClick={() => setDemoVisible((value) => !value)}
          type="button"
        >
          {demoVisible ? <Aperture size={17} /> : <Settings2 size={17} />}
        </button>
      </header>

      <section className="presence-scene" aria-label="Sentinel presence">
        <LivingObsidianStage state={visualState} signal={demo ? demoStates.indexOf(demo) : current.sequence} />

        {routeVisible ? (
          <div className="presence-route" aria-label="Mission route">
            {routeEvents.map((item, slot) => {
              const index = events.indexOf(item);
              return (
                <button
                  className={`presence-route-node route-${routeSlots[slot]}`}
                  data-active={index === eventIndex ? "true" : "false"}
                  data-incomplete={item.telemetry_state === "TELEMETRY_INCOMPLETE" ? "true" : "false"}
                  key={item.event_id}
                  onClick={() => chooseEvent(index)}
                  type="button"
                >
                  <span className="route-node-dot" />
                  <span className="route-node-copy">
                    <small>{item.event_kind} / {decisionLabel(item.decision_index)}</small>
                    <strong>{item.safe_summary}</strong>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        <div className="presence-voice">
          <span className="presence-state-label">
            <i aria-hidden="true" />
            {visualLabel}
          </span>
          <p>{visualSummary}</p>
          <span className="presence-truth-line">
            {demo
              ? "Deterministic visual demo only / no runtime action"
              : current.telemetry_state === "TELEMETRY_INCOMPLETE"
                ? "Historical telemetry gap / no fact inferred"
                : current.event_kind === "TERMINAL"
                  ? "FinalGate truth preserved"
                  : `Persisted event ${current.sequence + 1} of ${events.length}`}
          </span>
        </div>

        <button
          className="presence-route-toggle"
          onClick={() => setRouteVisible((value) => !value)}
          type="button"
        >
          {routeVisible ? <EyeOff size={16} /> : <Eye size={16} />}
          <span>{routeVisible ? "Hide route" : "Show route"}</span>
        </button>
      </section>

      <section
        aria-hidden={!demoVisible}
        aria-label="Deterministic visual states"
        className="presence-v3-demo-rail"
        data-open={demoVisible ? "true" : "false"}
      >
        <span className="demo-rail-label">State lab / zero runtime action</span>
        <div>
          <button
            data-active={demoKey === "truth" ? "true" : "false"}
            onClick={() => setDemoKey("truth")}
            type="button"
          >
            Truth
          </button>
          {demoStates.map((item) => (
            <button
              data-active={demoKey === item.key ? "true" : "false"}
              key={item.key}
              onClick={() => {
                setDemoKey(item.key);
                setPlaying(false);
              }}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <section className="presence-transport" aria-label="Replay controls">
        <button
          className="transport-icon"
          disabled={eventIndex === 0}
          onClick={() => chooseEvent(Math.max(0, eventIndex - 1))}
          type="button"
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="transport-play"
          onClick={() => {
            if (eventIndex === events.length - 1) {
              setEventIndex(0);
              setSelectedIndex(0);
            }
            setDemoKey("truth");
            setPlaying((value) => !value);
          }}
          type="button"
        >
          {playing ? <Pause size={16} /> : <Play size={16} />}
          <span>{playing ? "Pause" : eventIndex === events.length - 1 ? "Replay" : "Play route"}</span>
        </button>
        <input
          aria-label="Replay position"
          className="presence-scrubber"
          max={events.length - 1}
          min={0}
          onChange={(event) => chooseEvent(Number(event.target.value))}
          type="range"
          value={eventIndex}
        />
        <span className="transport-count">{String(eventIndex + 1).padStart(2, "0")} / {events.length}</span>
        <button
          className="transport-icon"
          disabled={eventIndex === events.length - 1}
          onClick={() => chooseEvent(Math.min(events.length - 1, eventIndex + 1))}
          type="button"
        >
          <ChevronRight size={17} />
        </button>
      </section>

      <form className="presence-command" onSubmit={submitCommand}>
        <button aria-label="Voice input unavailable in replay" className="command-mic" disabled type="button">
          <Mic size={18} />
        </button>
        <input
          aria-label="Sentinel command"
          onChange={(event) => setCommand(event.target.value)}
          placeholder="Replay only / connect a live Sentinel stream to issue a mission"
          value={command}
        />
        <span className="command-mode">READ ONLY</span>
      </form>

      <div className="presence-bottom-actions">
        <button
          className="presence-xray-button"
          data-active={xrayVisible ? "true" : "false"}
          onClick={() => setXrayVisible((value) => !value)}
          type="button"
        >
          <TerminalSquare size={16} />
          <span>X-Ray</span>
          <kbd>Shift X</kbd>
        </button>
        <button className="presence-kill-button" disabled title="Historical replay cannot affect the runtime" type="button">
          <CircleStop size={16} />
          <span>Kill unavailable / replay</span>
        </button>
      </div>

      <aside className="presence-xray" data-open={xrayVisible ? "true" : "false"} aria-hidden={!xrayVisible}>
        <div className="xray-head">
          <div>
            <span>X-RAY / READ ONLY</span>
            <strong>Decision {selected.decision_index || telemetryIncomplete}</strong>
          </div>
          <button aria-label="Close X-Ray" onClick={() => setXrayVisible(false)} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="xray-event">
          <span>{selected.event_kind}</span>
          <p>{selected.safe_summary}</p>
        </div>
        <XrayRow label="Provider" value={xrayValue(selected.provider_metadata?.provider_id)} />
        <XrayRow label="Model" value={xrayValue(selected.provider_metadata?.model_id)} />
        <XrayRow label="Latency" value={selected.provider_metadata?.latency_ms ? `${selected.provider_metadata.latency_ms}ms` : telemetryIncomplete} />
        <XrayRow label="Input tokens" value={xrayValue(selected.provider_metadata?.input_tokens)} />
        <XrayRow label="Output tokens" value={xrayValue(selected.provider_metadata?.output_tokens)} />
        <XrayRow label="Context" value={shortRef(selected.context_pack_hash)} />
        <XrayRow label="Affordances" value={formatAffordances(selected.available_affordances)} />
        <XrayRow label="Decision" value={xrayValue(selected.normalized_decision.operation)} />
        <XrayRow label="Dispatch" value={xrayValue(selected.dispatch_status)} />
        <XrayRow label="Product receipt" value={shortRef(selected.product_receipt_ref)} />
        <XrayRow
          alert={Boolean(selected.product_receipt_ref && !selected.browser_receipt_ref)}
          label="Browser receipt"
          value={shortRef(selected.browser_receipt_ref)}
        />
        <XrayRow label="State before" value={shortRef(selected.before_state_fingerprint)} />
        <XrayRow label="State after" value={shortRef(selected.after_state_fingerprint)} />
        <XrayRow label="Evidence before" value={shortRef(selected.before_evidence_fingerprint)} />
        <XrayRow label="Evidence after" value={shortRef(selected.after_evidence_fingerprint)} />
        <XrayRow
          label="Material progress"
          value={selected.material_progress === null ? telemetryIncomplete : selected.material_progress ? "yes" : "no"}
        />
        <XrayRow label="Gate results" value={formatGateResults(selected.gate_results)} />
        <XrayRow label="Authority" value={xrayValue(selected.authority_state)} />
        <XrayRow
          alert={selected.telemetry_state === "TELEMETRY_INCOMPLETE"}
          label="Telemetry"
          value={selected.telemetry_state}
        />
        {selected.first_causal_divergence_ref ? (
          <div className="xray-divergence">
            <span>FIRST CAUSAL DIVERGENCE</span>
            <strong>{selected.first_causal_divergence_ref}</strong>
          </div>
        ) : null}
        {selected.blocker ? (
          <div className="xray-blocker">
            <span>BLOCKER</span>
            <strong>{selected.blocker}</strong>
          </div>
        ) : null}
        <div className="xray-foot">
          <RotateCcw size={14} />
          Artifact history reconstruction / zero provider calls
        </div>
      </aside>
    </main>
  );
}

function mergePresenceEvents(current: PresenceEventV1[], incoming: PresenceEventV1[]) {
  const events = new Map(current.map((event) => [event.sequence, event]));
  for (const event of incoming) {
    const existing = events.get(event.sequence);
    if (!existing || existing.event_hash === event.event_hash) events.set(event.sequence, event);
  }
  return [...events.values()].sort((left, right) => left.sequence - right.sequence);
}

function XrayRow({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className="xray-row" data-alert={alert ? "true" : "false"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
