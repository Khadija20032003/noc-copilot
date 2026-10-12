/** Colored label for an agent name; unknown agents get a neutral style. */
export default function AgentBadge({ agent }: { agent: string }) {
  return <span className={`agent-badge agent-${agent.toLowerCase()}`}>{agent}</span>;
}
