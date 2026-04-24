"use client";

import { Check, Filter, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { actions, evidence, firewallPolicies } from "@/lib/demo-data";
import type { ActionRow, ApprovalStatus, EvidenceRow, FeedbackEntryRow, SentinelRunRecord } from "@/lib/types";
import { Chip, RiskBadge, SectionBand, StateBadge } from "@/components/ui";
import { FeedbackControls } from "@/components/feedback-controls";

type EvidenceFilter = "all" | EvidenceRow["proofTier"];

const filterLabels: Record<EvidenceFilter, string> = {
  all: "All",
  direct: "Direct",
  adjacent: "Adjacent",
  supporting: "Supporting",
};

function badgeState(status: ApprovalStatus, blocked?: boolean) {
  if (blocked || status === "blocked" || status === "rejected") return "blocked";
  if (status === "approved" || status === "not_required") return "approved";
  return "pending";
}

export function EvidenceLedgerPanel({ evidenceItems = evidence }: { evidenceItems?: EvidenceRow[] }) {
  const [filter, setFilter] = useState<EvidenceFilter>("all");
  const [selectedId, setSelectedId] = useState(evidenceItems[0]?.id ?? "");
  const [query, setQuery] = useState("");

  const filteredEvidence = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return evidenceItems.filter((row) => {
      const matchesTier = filter === "all" || row.proofTier === filter;
      const matchesQuery =
        normalizedQuery.length === 0 ||
        row.source.toLowerCase().includes(normalizedQuery) ||
        row.summary.toLowerCase().includes(normalizedQuery) ||
        row.details.tags.some((tag) => tag.toLowerCase().includes(normalizedQuery));

      return matchesTier && matchesQuery;
    });
  }, [evidenceItems, filter, query]);

  useEffect(() => {
    if (!evidenceItems.some((row) => row.id === selectedId)) {
      setSelectedId(evidenceItems[0]?.id ?? "");
    }
  }, [evidenceItems, selectedId]);

  const selected = filteredEvidence.find((row) => row.id === selectedId) ?? filteredEvidence[0];

  return (
    <SectionBand
      eyebrow="Evidence"
      title="Evidence Ledger"
      action={
        <>
          <div className="search-control">
            <Search size={16} />
            <input
              aria-label="Search evidence"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search signal, source, tag"
            />
          </div>
          <button className="ghost-btn" type="button">
            <Filter size={16} />
            <span>{filteredEvidence.length} rows</span>
          </button>
        </>
      }
    >
      <div className="tabs" aria-label="Evidence filter">
        {(Object.keys(filterLabels) as EvidenceFilter[]).map((key) => (
          <button
            className="tab"
            data-active={filter === key ? "true" : "false"}
            key={key}
            onClick={() => setFilter(key)}
            type="button"
          >
            {filterLabels[key]}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Proof Tier</th>
              <th>Summary</th>
              <th>Confidence</th>
              <th>Freshness</th>
              <th>Linked Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvidence.map((row) => {
              const selectedRow = row.id === selected?.id;

              return (
                <tr data-selected={selectedRow ? "true" : "false"} key={row.id}>
                  <td>
                    <button className="row-button" onClick={() => setSelectedId(row.id)} type="button">
                      <span className="row-title">{row.source}</span>
                      <span className="row-meta">{row.id}</span>
                    </button>
                  </td>
                  <td>
                    <span className="tier-badge">{row.proofTier}</span>
                  </td>
                  <td>
                    <div style={{ display: "grid", gap: 4 }}>
                      <span>{row.summary}</span>
                      {row.quote ? <span className="row-meta">Quote: "{row.quote}"</span> : null}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: "grid", gap: 8 }}>
                      <span>{row.confidence}%</span>
                      <div className="confidence-bar">
                        <div style={{ width: `${row.confidence}%` }} />
                      </div>
                    </div>
                  </td>
                  <td>{row.freshness}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {row.actionRefs.map((ref) => (
                        <Chip key={ref} tone={ref === "A-103" ? "bad" : "neutral"}>
                          {ref}
                        </Chip>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selected ? (
        <div className="detail-grid">
          <div className="detail-box">
            <div className="detail-label">Selected evidence</div>
            <div className="detail-body">{selected.details.excerpt}</div>
          </div>
          <div className="detail-box">
            <div className="detail-label">Methodology</div>
            <div className="detail-body">{selected.details.methodology}</div>
          </div>
          <div className="detail-box">
            <div className="detail-label">Tags</div>
            <div className="detail-body" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {selected.details.tags.map((tag) => (
                <Chip key={tag} tone="neutral">
                  {tag}
                </Chip>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-state">No evidence matches this filter.</div>
      )}
    </SectionBand>
  );
}

export function FirewallReviewPanel({
  compact = false,
  actionItems = actions,
  runId,
  feedbackItems = [],
  onRunUpdate,
}: {
  compact?: boolean;
  actionItems?: ActionRow[];
  runId?: string;
  feedbackItems?: FeedbackEntryRow[];
  onRunUpdate?: (run: SentinelRunRecord) => void;
}) {
  const [statuses, setStatuses] = useState<Record<string, ApprovalStatus>>(() =>
    Object.fromEntries(actionItems.map((action) => [action.id, action.approvalStatus])),
  );
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const pendingCount = actionItems.filter((action) => statuses[action.id] === "pending" && !action.blocked).length;

  useEffect(() => {
    setStatuses(Object.fromEntries(actionItems.map((action) => [action.id, action.approvalStatus])));
  }, [actionItems]);

  async function setActionStatus(action: ActionRow, status: ApprovalStatus) {
    if (action.blocked) return;

    if (!runId) {
      setStatuses((current) => ({ ...current, [action.id]: status }));
      return;
    }

    setBusyAction(action.id);
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/actions/${encodeURIComponent(action.id)}/approval`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ approvalStatus: status }),
      });
      const payload = (await response.json()) as { run?: SentinelRunRecord; error?: string };

      if (!response.ok || !payload.run) {
        throw new Error(payload.error || "Approval update failed.");
      }

      setStatuses(Object.fromEntries(payload.run.actions.map((item) => [item.id, item.approvalStatus])));
      onRunUpdate?.(payload.run);
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <SectionBand
      eyebrow="Firewall"
      title="Review queue"
      action={<Chip tone={pendingCount > 0 ? "warn" : "good"}>{pendingCount} pending</Chip>}
    >
      <div className="firewall-stack">
        {actionItems.map((item) => {
          const status = statuses[item.id] ?? item.approvalStatus;
          const disabled =
            busyAction === item.id ||
            item.blocked ||
            status === "approved" ||
            status === "rejected" ||
            status === "not_required";
          const previewEntries = Object.entries(item.dryRun.preview).slice(0, compact ? 2 : 3);

          return (
            <div className="firewall-card" data-highlight={item.blocked ? "true" : "false"} key={item.id}>
              <div className="firewall-top">
                <div>
                  <strong>
                    {item.id} {item.title}
                  </strong>
                  <span>{item.intent}</span>
                </div>
                <RiskBadge level={item.risk} />
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <StateBadge state={badgeState(status, item.blocked)}>{status.toUpperCase()}</StateBadge>
                {item.requiresApproval ? <Chip tone="warn">Approval required</Chip> : <Chip tone="good">Auto allowed</Chip>}
                {item.blocked ? <Chip tone="bad">V1 disabled</Chip> : null}
              </div>

              <div className="dry-run">
                <h4>Dry-run preview</h4>
                <div className="dry-run-grid">
                  {previewEntries.map(([key, value]) => (
                    <div className="dry-run-kpi" key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="approval-row">
                <span className="page-note">{item.dryRun.whyNeeded}</span>
                <div className="section-actions">
                  <button
                    className="ghost-btn"
                    disabled={disabled}
                    onClick={() => void setActionStatus(item, "rejected")}
                    type="button"
                  >
                    <X size={16} />
                    <span>{busyAction === item.id ? "Saving" : "Reject"}</span>
                  </button>
                  <button
                    className="secondary-btn"
                    disabled={disabled}
                    onClick={() => void setActionStatus(item, "approved")}
                    type="button"
                  >
                    <Check size={16} />
                    <span>{busyAction === item.id ? "Saving" : "Approve"}</span>
                  </button>
                </div>
              </div>

              {runId ? (
                <FeedbackControls
                  feedback={feedbackItems}
                  onRunUpdate={onRunUpdate}
                  runId={runId}
                  targetId={item.id}
                  targetType="action"
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </SectionBand>
  );
}

export function FirewallPolicyPanel() {
  return (
    <SectionBand eyebrow="Policy" title="Permission policies">
      <div className="firewall-stack">
        {firewallPolicies.map((policy) => (
          <div className="list-item" key={policy.tool}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <strong>{policy.tool}</strong>
              <RiskBadge level={policy.risk} />
            </div>
            <p>{policy.scope}</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {policy.autoAllowed ? <Chip tone="good">Auto allowed</Chip> : <Chip tone="warn">Approval</Chip>}
              {policy.disabled ? <Chip tone="bad">V1 disabled</Chip> : <Chip tone="neutral">Enabled</Chip>}
            </div>
          </div>
        ))}
      </div>
    </SectionBand>
  );
}
