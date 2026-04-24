"use client";

import { ArrowRight, Download, Play, Share2, SlidersHorizontal } from "lucide-react";
import Link from "next/link";

export function ButtonRow() {
  return (
    <>
      <button className="ghost-btn" type="button">
        <SlidersHorizontal size={16} />
        <span>Run Details</span>
      </button>
      <button className="ghost-btn" type="button">
        <Share2 size={16} />
        <span>Share Run</span>
      </button>
      <button className="primary-btn" type="button">
        <Play size={16} />
        <span>New Run</span>
      </button>
    </>
  );
}

export function FileLink({
  href,
  label,
  secondary,
}: {
  href: string;
  label: string;
  secondary?: string;
}) {
  return (
    <Link href={href} className="board-card" style={{ gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <strong>{label}</strong>
        <ArrowRight size={16} />
      </div>
      {secondary ? <p>{secondary}</p> : null}
    </Link>
  );
}

export function ExportButton({ label }: { label: string }) {
  return (
    <button className="secondary-btn" type="button">
      <Download size={16} />
      <span>{label}</span>
    </button>
  );
}

