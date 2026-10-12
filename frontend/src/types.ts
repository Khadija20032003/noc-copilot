// API contract with the backend (see backend/app/api.py).

export type AgentName = "Supervisor" | "Research" | "Analyst" | "Answer" | "Verifier";

/** One step of the agent run, shown in the "How I got this" panel. */
export interface TraceEntry {
  agent: AgentName;
  type: "routing" | "tool_call" | "finding" | "answer" | "verdict" | "guard";
  detail: string;
}

export type Severity = "P1" | "P2" | "P3" | "P4";

/** Same values as backend RootCauseId (tools/tickets.py). */
export type RootCauseId = "RC1" | "RC2" | "RC3" | "RC4" | "RC5" | "RC6" | "RC7" | "RC8";

/** Ticket proposed by the assistant (backend TicketDraft). Only stored after the user approves it. */
export interface ProposedTicket {
  severity: Severity;
  pci: number;
  neighbor_pci: number | null;
  site_name: string;
  symptom: string;
  evidence: string;
  root_cause_id: RootCauseId | "unknown";
  recommended_action: string;
  confidence: "high" | "medium" | "low";
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  answer: string;
  /** Formatted as "doc.md > Section". */
  sources: string[];
  trace: TraceEntry[];
  proposed_ticket: ProposedTicket | null;
  /** The Verifier's verdict: true approved, false not approved, null if verification was skipped. */
  verified: boolean | null;
}

/** Returned by POST /api/tickets and listed by GET /api/tickets. */
export interface StoredTicket extends ProposedTicket {
  id: string;
  created_at: string;
  status: "open";
}

export interface HealthResponse {
  status: string;
}
