import { useEffect, useState } from "react";
import Icon from "./Icon";

export function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

/** Shown while the agents run (often 30 s to 2 min): elapsed time and the pipeline, no fake progress. */
export default function PendingIndicator({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="pending" role="status">
      <div className="pending-head">
        <span className="spinner" aria-hidden="true" />
        <span className="pending-title">Agents are working</span>
        <span className="pending-time">
          <Icon name="clock" size={13} />
          {formatDuration(now - startedAt)}
        </span>
      </div>
      <div className="pending-bar" aria-hidden="true">
        <span />
      </div>
      <p className="pending-flow">
        Supervisor routes the question to Research (runbooks) and Analyst (network data), then the Answer is
        checked by the Verifier. Complex diagnoses can take up to two minutes.
      </p>
    </div>
  );
}
