import type { ReactNode } from "react";
import { DashboardShell } from "@/components/shell";
import { ButtonRow } from "@/components/shared";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <DashboardShell
      breadcrumbs={["Sentinel", "Control Room"]}
      actions={<ButtonRow />}
    >
      {children}
    </DashboardShell>
  );
}

