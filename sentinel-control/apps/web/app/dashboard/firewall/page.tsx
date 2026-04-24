import { FirewallPolicyPanel, FirewallReviewPanel } from "@/components/interactive";

export default function FirewallPage() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-panel">
          <div className="eyebrow">Firewall</div>
          <h1 className="page-title">AgentOps Firewall</h1>
          <p className="page-copy">
            Every proposed action passes through risk scoring, path policy, dry-run preview, and approval state. V1 keeps external contact, browser submission, shell execution, and code changes disabled.
          </p>
        </div>
        <div className="panel">
          <FirewallPolicyPanel />
        </div>
      </section>

      <section className="panel">
        <FirewallReviewPanel />
      </section>
    </div>
  );
}
