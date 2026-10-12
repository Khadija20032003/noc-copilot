import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatResponse } from "../types";
import Icon from "./Icon";
import { formatDuration } from "./PendingIndicator";
import TicketCard from "./TicketCard";
import TracePanel from "./TracePanel";

export type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; response: ChatResponse; durationMs?: number }
  | { id: string; role: "error"; text: string };

/** "runbook_coverage.md > RC1 Downtilt..." -> ["runbook_coverage.md", "RC1 Downtilt..."] */
function splitSource(source: string): [string, string] {
  const i = source.indexOf(" > ");
  return i < 0 ? [source, ""] : [source.slice(0, i), source.slice(i + 3)];
}

export default function ChatMessage({ message }: { message: Message }) {
  switch (message.role) {
    case "user":
      return <div className="msg msg-user">{message.text}</div>;

    case "error":
      return (
        <div className="msg msg-error" role="alert">
          <Icon name="alert" size={18} />
          <div>
            <strong>Request failed</strong>
            <p>{message.text}</p>
          </div>
        </div>
      );

    case "assistant": {
      const { answer, sources, trace, proposed_ticket, verified } = message.response;
      return (
        <article className="msg msg-assistant">
          <header className="msg-head">
            <span className="avatar">
              <Icon name="logo" size={15} />
            </span>
            <span className="msg-author">NOC Copilot</span>
            {verified === true && (
              <span className="pill pill-ok" title="The Verifier approved this answer">
                <Icon name="check" size={13} /> Verified
              </span>
            )}
            {verified === false && (
              <span className="pill pill-warn" title="The Verifier still had open issues; read the caveats">
                <Icon name="alert" size={13} /> Not fully verified
              </span>
            )}
            {message.durationMs !== undefined && (
              <span className="msg-time">
                <Icon name="clock" size={13} />
                {formatDuration(message.durationMs)}
              </span>
            )}
          </header>

          <div className="answer">
            <Markdown remarkPlugins={[remarkGfm]}>{answer}</Markdown>
          </div>

          {sources.length > 0 && (
            <section className="sources">
              <h3 className="section-label">Sources · {sources.length}</h3>
              <ol className="source-list">
                {sources.map((s) => {
                  const [doc, section] = splitSource(s);
                  return (
                    <li key={s} className="source" title={s}>
                      <Icon name="file" size={14} />
                      <span className="source-doc">{doc}</span>
                      {section && <span className="source-section">{section}</span>}
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {proposed_ticket && <TicketCard ticket={proposed_ticket} />}
          <TracePanel trace={trace} />
        </article>
      );
    }
  }
}
