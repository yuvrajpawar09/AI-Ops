import { useState } from "react";
import { PanelError } from "./PanelError.jsx";
import { relativeTime, shortTraceId } from "../utils/format.js";

function LogLine({ event }) {
  return (
    <div className="log-line">
      <div className="log-line-meta">
        <span className="log-line-service">{event.service}</span>
        <span className={`log-line-level log-line-level--${event.level}`}>{event.level}</span>
      </div>
      <div className="log-line-message">{event.message}</div>
      <div className="log-line-template">{event.template}</div>
    </div>
  );
}

function AnomalyRow({ anomaly }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="anomaly-row">
      <div className="anomaly-row-header" onClick={() => setOpen((o) => !o)}>
        <span className={`anomaly-chevron ${open ? "open" : ""}`}>&#9656;</span>
        <span className="anomaly-trace-id mono">{shortTraceId(anomaly.traceId)}</span>
        <span className="anomaly-score">score {anomaly.score.toFixed(3)}</span>
        <span className="anomaly-time">{relativeTime(anomaly.closedAt)}</span>
      </div>
      {open && (
        <div className="anomaly-log">
          {(anomaly.events || []).map((ev, i) => (
            <LogLine key={i} event={ev} />
          ))}
        </div>
      )}
    </div>
  );
}

export function AnomalyTimeline({ anomalies, error }) {
  const items = anomalies?.anomalies || [];
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Live Anomaly Timeline</h2>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {items.length}
        </span>
      </div>
      <div className="panel-body">
        {error ? (
          <PanelError message={error} />
        ) : items.length === 0 ? (
          <div className="panel-empty">No anomalies flagged yet.</div>
        ) : (
          items.map((a) => <AnomalyRow key={a.traceId + a.closedAt} anomaly={a} />)
        )}
      </div>
    </section>
  );
}
