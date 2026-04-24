"use client";

import Link from "next/link";
import { BookOpenText, Cable, CreditCard, FlaskConical, FolderOpen, Kanban, LayoutDashboard, ListTree, Shield, Users, Workflow } from "lucide-react";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { href: "/dashboard", label: "Agents", icon: LayoutDashboard },
  { href: "/dashboard/cueidea", label: "CueIdea", icon: Cable },
  { href: "/dashboard/firewall", label: "Firewall", icon: Shield },
  { href: "/dashboard/execution", label: "Execution", icon: Kanban },
  { href: "/dashboard/customers", label: "Customers", icon: Users },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/evidence", label: "Evidence", icon: BookOpenText },
  { href: "/dashboard/traces", label: "Traces", icon: ListTree },
  { href: "/dashboard/evals", label: "Evals", icon: FlaskConical },
  { href: "/dashboard/generated-projects/ai-invoice-chasing", label: "Projects", icon: FolderOpen },
  { href: "/dashboard/agents/GR-2025-05-18-1427", label: "Run Detail", icon: Workflow },
];

export function DashboardShell({
  children,
  breadcrumbs,
  actions,
}: {
  children: ReactNode;
  breadcrumbs: string[];
  actions?: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <Shield size={20} strokeWidth={2.3} />
          </div>
          <div className="brand-text">
            <strong>SENTINEL CONTROL</strong>
            <span>Operator + Firewall</span>
          </div>
        </div>

        <nav className="nav" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Link className="nav-item" data-active={active ? "true" : "false"} href={item.href} key={item.href}>
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="status-card">
            <div className="status-row">
              <span>System Status</span>
              <span style={{ color: "var(--success)" }}>All Systems Operational</span>
            </div>
            <div className="status-row">
              <span>Active Runs</span>
              <strong>12</strong>
            </div>
            <div className="status-row">
              <span>Pending Approvals</span>
              <strong style={{ color: "var(--warn)" }}>3</strong>
            </div>
            <div className="status-row">
              <span>Blocked Actions</span>
              <strong style={{ color: "var(--danger)" }}>2</strong>
            </div>
          </div>

          <div className="user-chip">
            <div className="user-avatar">AC</div>
            <div>
              <strong style={{ display: "block" }}>Alex Chen</strong>
              <span style={{ color: "rgba(255,255,255,0.68)", fontSize: "0.88rem" }}>Admin</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topbar">
          <div className="crumbs" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, index) => (
              <span key={`${crumb}-${index}`} style={{ display: "inline-flex", gap: 10, alignItems: "center" }}>
                {index > 0 ? <span style={{ color: "var(--muted-2)" }}>/</span> : null}
                <strong>{crumb}</strong>
              </span>
            ))}
          </div>
          <div className="top-actions">{actions}</div>
        </header>

        <main>{children}</main>
      </div>
    </div>
  );
}
