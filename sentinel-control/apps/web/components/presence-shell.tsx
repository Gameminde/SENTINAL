"use client";

import {
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
import {
  mdnPresenceReplay,
  type PresenceEventV1,
  type PresenceState,
} from "@/lib/presence-protocol";

const routeSlots = ["north-west", "west", "south-west", "north-east", "east", "south-east"] as const;

function stateLabel(state: PresenceState) {
  return state.replace(/_/g, " ").toLowerCase();
}

function shortRef(value: string) {
  if (!value) return "not persisted";
  if (value.length <= 26) return value;
  return `${value.slice(0, 13)}…${value.slice(-9)}`;
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
  const [command, setCommand] = useState("");
  const current = events[eventIndex];
  const selected = events[selectedIndex] ?? current;

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
    } catch {
      setConnection("unavailable");
    }
  }

  return (
    <main className="presence-page" data-presence-state={current.presence_state}>
      <div className="presence-aurora presence-aurora-one" />
      <div className="presence-aurora presence-aurora-two" />
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
        <button className="presence-icon-button" aria-label="Settings" type="button">
          <Settings2 size={17} />
        </button>
      </header>

      <section className="presence-scene" aria-label="Sentinel presence">
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
                    <small>{item.event_kind} · {item.decision_index ? `D${item.decision_index}` : "START"}</small>
                    <strong>{item.safe_summary}</strong>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        <div className="presence-core-wrap">
          <div className="presence-orbit orbit-one" />
          <div className="presence-orbit orbit-two" />
          <div className="presence-core" aria-hidden="true">
            <div className="presence-core-shell" />
            <div className="presence-core-vein vein-one" />
            <div className="presence-core-vein vein-two" />
            <div className="presence-core-eye" />
          </div>
          <div className="presence-floor-glow" />
        </div>

        <div className="presence-voice">
          <span className="presence-state-label">{stateLabel(current.presence_state)}</span>
          <p>{current.safe_summary}</p>
          <span className="presence-truth-line">
            {current.telemetry_state === "TELEMETRY_INCOMPLETE"
              ? "Historical telemetry gap · no fact inferred"
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
          placeholder="Replay only · connect a live Sentinel stream to issue a mission"
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
          <kbd>⇧ X</kbd>
        </button>
        <button className="presence-kill-button" disabled title="Historical replay cannot affect the runtime" type="button">
          <CircleStop size={16} />
          <span>Kill unavailable · replay</span>
        </button>
      </div>

      <aside className="presence-xray" data-open={xrayVisible ? "true" : "false"} aria-hidden={!xrayVisible}>
        <div className="xray-head">
          <div>
            <span>X-RAY · READ ONLY</span>
            <strong>Decision {selected.decision_index || "—"}</strong>
          </div>
          <button aria-label="Close X-Ray" onClick={() => setXrayVisible(false)} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="xray-event">
          <span>{selected.event_kind}</span>
          <p>{selected.safe_summary}</p>
        </div>
        <XrayRow label="Context" value={shortRef(selected.context_pack_hash)} />
        <XrayRow label="Decision" value={selected.normalized_decision.operation || "none"} />
        <XrayRow label="Dispatch" value={selected.dispatch_status || "not dispatched"} />
        <XrayRow label="Product receipt" value={shortRef(selected.product_receipt_ref)} />
        <XrayRow
          alert={Boolean(selected.product_receipt_ref && !selected.browser_receipt_ref)}
          label="Browser receipt"
          value={shortRef(selected.browser_receipt_ref)}
        />
        <XrayRow
          label="Material progress"
          value={selected.material_progress === null ? "unknown" : selected.material_progress ? "yes" : "no"}
        />
        <XrayRow label="Authority" value={selected.authority_state} />
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
          Artifact history reconstruction · zero provider calls
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
