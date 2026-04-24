"use client";

import { CheckCircle2, CircleAlert, ChevronRight, Clock3, Lock, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

export function SectionBand({
  title,
  eyebrow,
  action,
  children,
}: {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section-band">
      <div className="section-heading">
        <div>
          {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
          <h2>{title}</h2>
        </div>
        {action ? <div className="section-actions">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  return <span className="chip" data-tone={tone}>{children}</span>;
}

export function Metric({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {sub ? <div className="metric-sub">{sub}</div> : null}
    </div>
  );
}

export function RiskBadge({ level }: { level: "low" | "medium" | "high" | "critical" }) {
  return <span className="risk-badge" data-level={level}>{level}</span>;
}

export function StateBadge({
  state,
  children,
}: {
  state: "approved" | "pending" | "blocked";
  children: ReactNode;
}) {
  return <span className="state-badge" data-state={state}>{children}</span>;
}

export function StatusIcon({ state }: { state: "approved" | "pending" | "blocked" | "review" }) {
  if (state === "approved") return <CheckCircle2 size={16} />;
  if (state === "pending") return <Clock3 size={16} />;
  if (state === "blocked") return <Lock size={16} />;
  return <ShieldCheck size={16} />;
}

export function SmallAlert({ tone }: { tone: "warn" | "bad" }) {
  return tone === "bad" ? <CircleAlert size={16} /> : <ShieldCheck size={16} />;
}

export function Arrow({ rotated = false }: { rotated?: boolean }) {
  return <ChevronRight size={16} style={{ transform: rotated ? "rotate(90deg)" : "none" }} />;
}

