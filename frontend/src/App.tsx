import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { getHealth, sendChat } from "./api";
import ChatMessage, { type Message } from "./components/ChatMessage";
import ExampleQuestions from "./components/ExampleQuestions";
import Icon, { type IconName } from "./components/Icon";
import PendingIndicator from "./components/PendingIndicator";

type Health = "checking" | "ok" | "down";

const HEALTH_POLL_MS = 30_000;
const HEALTH_LABELS: Record<Health, string> = {
  checking: "Connecting",
  ok: "Operational",
  down: "Backend unreachable",
};

const CAPABILITIES: { icon: IconName; title: string; text: string }[] = [
  { icon: "book", title: "Runbooks and policy", text: "Root causes RC1 to RC8, KPI thresholds and the P1 to P4 escalation policy." },
  { icon: "database", title: "Drive-test data", text: "Read-only SQL over cells and measurements, with distance and PCI checks." },
  { icon: "shield", title: "Verified answers", text: "A Verifier checks diagnoses, numbers and citations before the answer is shown." },
];

export default function App() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [health, setHealth] = useState<Health>("checking");
  const threadEnd = useRef<HTMLDivElement>(null);
  const pending = pendingSince !== null;

  useEffect(() => {
    const check = () =>
      getHealth()
        .then((h) => setHealth(h.status === "ok" ? "ok" : "down"))
        .catch(() => setHealth("down"));
    check();
    const timer = setInterval(check, HEALTH_POLL_MS);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || pending) return;
    const startedAt = Date.now();
    setInput("");
    setPendingSince(startedAt);
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", text: question }]);
    try {
      const response = await sendChat(sessionId, question);
      const durationMs = Date.now() - startedAt;
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "assistant", response, durationMs }]);
    } catch (err) {
      const text = err instanceof Error ? err.message : String(err);
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "error", text }]);
    } finally {
      setPendingSince(null);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  function newConversation() {
    setSessionId(crypto.randomUUID());
    setMessages([]);
    setInput("");
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="logo" size={18} />
          </span>
          <span className="brand-name">NOC Copilot</span>
          <span className="brand-sep" aria-hidden="true" />
          <span className="brand-org">NordTel · 5G RAN Operations</span>
        </div>
        <div className="header-right">
          <span className={`status status-${health}`} title={HEALTH_LABELS[health]}>
            <span className="status-dot" aria-hidden="true" />
            <span className="status-label">{HEALTH_LABELS[health]}</span>
          </span>
          <button className="btn" onClick={newConversation} disabled={pending}>
            <Icon name="plus" size={15} />
            <span className="btn-label">New conversation</span>
          </button>
        </div>
      </header>

      <div className={`layout ${messages.length === 0 ? "is-empty" : ""}`}>
        <aside className="sidebar">
          <ExampleQuestions disabled={pending} onPick={(q) => void send(q)} />
          <div className="sidebar-foot">
            <div className="notice">
              <Icon name="shield" size={16} />
              <p>
                <strong>Approval required.</strong> Tickets are only proposed. Nothing is created until you
                approve it.
              </p>
            </div>
            <p className="session">Session {sessionId.slice(0, 8)}</p>
          </div>
        </aside>

        <main className="chat">
          <div className="thread" aria-live="polite">
            <div className="thread-inner">
              {messages.length === 0 && (
                <section className="welcome">
                  <span className="welcome-mark">
                    <Icon name="logo" size={26} />
                  </span>
                  <h1>Diagnose a cell degradation</h1>
                  <p className="welcome-lead">
                    Ask about a KPI, a runbook or a drive-test route. Specialist agents gather the evidence and
                    a Verifier checks diagnoses and numbers before you see them.
                  </p>
                  <div className="capabilities">
                    {CAPABILITIES.map((c) => (
                      <div key={c.title} className="capability">
                        <span className="capability-icon">
                          <Icon name={c.icon} size={18} />
                        </span>
                        <h2>{c.title}</h2>
                        <p>{c.text}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
              {pendingSince !== null && <PendingIndicator startedAt={pendingSince} />}
              <div ref={threadEnd} />
            </div>
          </div>

          <form className="composer" onSubmit={onSubmit}>
            <div className="composer-box">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder={pending ? "Waiting for the agents..." : "Ask about a cell, a KPI or a route"}
                disabled={pending}
                rows={2}
                aria-label="Message"
              />
              <button
                className="send-btn"
                type="submit"
                disabled={pending || !input.trim()}
                aria-label="Send"
                title="Send"
              >
                <Icon name="send" size={18} />
              </button>
            </div>
            <p className="composer-hint">
              <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line
            </p>
          </form>
        </main>
      </div>
    </div>
  );
}
