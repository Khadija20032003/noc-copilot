import { useState } from "react";
import { approveTicket } from "../api";
import type { ProposedTicket, Severity } from "../types";
import Icon from "./Icon";

type Status =
  | { kind: "proposed" }
  | { kind: "submitting" }
  | { kind: "created"; id: string }
  | { kind: "dismissed" }
  | { kind: "failed"; error: string };

// Same labels as backend domain.SEVERITIES and ROOT_CAUSES.
const SEVERITY_NAMES: Record<Severity, string> = { P1: "Critical", P2: "Major", P3: "Minor", P4: "Planning" };
const ROOT_CAUSES: Record<string, string> = {
  RC1: "Downtilt too large",
  RC2: "Overshooting",
  RC3: "Better neighbor available",
  RC4: "Overlapping coverage",
  RC5: "Frequent handovers",
  RC6: "PCI mod 30 conflict",
  RC7: "High UE speed",
  RC8: "Low scheduled resources",
};
const CONFIDENCE_LEVEL = { low: 1, medium: 2, high: 3 } as const;

export default function TicketCard({ ticket }: { ticket: ProposedTicket }) {
  const [status, setStatus] = useState<Status>({ kind: "proposed" });
  const canAct = status.kind === "proposed" || status.kind === "failed";
  const rootCause = ROOT_CAUSES[ticket.root_cause_id];

  async function approve() {
    setStatus({ kind: "submitting" });
    try {
      const stored = await approveTicket(ticket);
      setStatus({ kind: "created", id: stored.id });
    } catch (err) {
      setStatus({ kind: "failed", error: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <section className={`ticket ticket-${status.kind}`} aria-label="Proposed incident ticket">
      <header className="ticket-head">
        <Icon name="ticket" size={16} />
        <span className="ticket-title">Incident ticket</span>
        <span className="ticket-state">
          {status.kind === "created" ? `#${status.id}` : status.kind === "dismissed" ? "Dismissed" : "Draft"}
        </span>
        <span className={`severity severity-${ticket.severity.toLowerCase()}`}>
          {ticket.severity} · {SEVERITY_NAMES[ticket.severity]}
        </span>
      </header>

      <div className="ticket-body">
        <p className="ticket-symptom">{ticket.symptom}</p>

        <dl className="ticket-fields">
          <div>
            <dt>Site</dt>
            <dd>{ticket.site_name}</dd>
          </div>
          <div>
            <dt>Serving PCI</dt>
            <dd className="mono">{ticket.pci}</dd>
          </div>
          {ticket.neighbor_pci != null && (
            <div>
              <dt>Neighbor PCI</dt>
              <dd className="mono">{ticket.neighbor_pci}</dd>
            </div>
          )}
          <div>
            <dt>Root cause</dt>
            <dd>
              <span className="mono">{ticket.root_cause_id}</span>
              {rootCause && <span className="muted"> · {rootCause}</span>}
            </dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd className="confidence">
              <span className="meter" aria-hidden="true">
                {[1, 2, 3].map((i) => (
                  <span key={i} className={i <= CONFIDENCE_LEVEL[ticket.confidence] ? "on" : ""} />
                ))}
              </span>
              {ticket.confidence}
            </dd>
          </div>
        </dl>

        <div className="ticket-section">
          <h4>Evidence</h4>
          <p>{ticket.evidence}</p>
        </div>
        <div className="ticket-section">
          <h4>Recommended action</h4>
          <p>{ticket.recommended_action}</p>
        </div>
      </div>

      <footer className="ticket-footer">
        {status.kind === "created" && (
          <p className="ticket-status ok">
            <Icon name="check" size={15} /> Ticket #{status.id} created.
          </p>
        )}
        {status.kind === "dismissed" && <p className="ticket-status">Dismissed. No ticket was created.</p>}
        {status.kind === "failed" && (
          <p className="ticket-status err">
            <Icon name="alert" size={15} /> Could not create the ticket: {status.error}
          </p>
        )}
        {(canAct || status.kind === "submitting") && (
          <>
            <p className="ticket-hitl">Not created yet. NOC Copilot never creates a ticket without your approval.</p>
            <div className="ticket-actions">
              <button className="btn" onClick={() => setStatus({ kind: "dismissed" })} disabled={!canAct}>
                Dismiss
              </button>
              <button className="btn btn-primary" onClick={approve} disabled={!canAct}>
                <Icon name="check" size={15} />
                {status.kind === "submitting" ? "Creating..." : "Approve and create"}
              </button>
            </div>
          </>
        )}
      </footer>
    </section>
  );
}
