import type { ChatResponse, HealthResponse, ProposedTicket, StoredTicket } from "./types";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/** Extracts a readable message from an error body ({detail}, {error} or {message}). */
function errorMessage(status: number, body: unknown): string {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    for (const key of ["detail", "error", "message"]) {
      const value = b[key];
      if (typeof value === "string") return value;
      if (value !== undefined) return JSON.stringify(value);
    }
  }
  return `Request failed with HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(res.status, body));
  return body as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function sendChat(sessionId: string, message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export function approveTicket(ticket: ProposedTicket): Promise<StoredTicket> {
  return request<StoredTicket>("/api/tickets", {
    method: "POST",
    body: JSON.stringify(ticket),
  });
}
