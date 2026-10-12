import type { TraceEntry } from "../types";
import AgentBadge from "./AgentBadge";
import Icon from "./Icon";

const TYPE_LABELS: Record<TraceEntry["type"], string> = {
  routing: "Routing",
  tool_call: "Tool call",
  finding: "Finding",
  answer: "Draft",
  verdict: "Verdict",
  guard: "Guard",
};

export default function TracePanel({ trace }: { trace: TraceEntry[] }) {
  if (trace.length === 0) return null;
  const agents = [...new Set(trace.map((t) => t.agent))];
  const toolCalls = trace.filter((t) => t.type === "tool_call").length;

  return (
    <details className="trace">
      <summary>
        <Icon name="chevron" size={14} />
        <Icon name="layers" size={15} />
        <span className="trace-title">How I got this</span>
        <span className="trace-meta">
          {trace.length} steps · {toolCalls} tool calls
        </span>
        <span className="trace-agents">
          {agents.map((a) => (
            <AgentBadge key={a} agent={a} />
          ))}
        </span>
      </summary>
      <ol className="trace-list">
        {trace.map((entry, i) => (
          <li key={i} className={`trace-entry trace-${entry.type} dot-${entry.agent.toLowerCase()}`}>
            <div className="trace-entry-head">
              <AgentBadge agent={entry.agent} />
              <span className="trace-type">{TYPE_LABELS[entry.type]}</span>
            </div>
            {entry.type === "tool_call" ? (
              <pre className="trace-code">{entry.detail}</pre>
            ) : (
              <p className="trace-detail">{entry.detail}</p>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}
