import { useState } from "react";
import { PanelError } from "./PanelError.jsx";
import { PanelSkeleton } from "./PanelSkeleton.jsx";
import { outcomeMeta } from "../utils/outcome.js";
import { relativeTime, shortTraceId } from "../utils/format.js";

function RemediationLogEntry({ entry }) {
  return (
    <div className="remediation-log-entry">
      <div className="remediation-log-entry-header">
        <span className="remediation-log-action">{entry.action}</span>
        <span className={`remediation-log-result remediation-log-result--${entry.result}`}>{entry.result}</span>
        {entry.playbook && <span className="remediation-log-playbook">playbook: {entry.playbook}</span>}
      </div>
      <div className="remediation-log-reason">{entry.reason}</div>
      {(entry.request || entry.response) && (
        <pre className="remediation-log-detail">
          {entry.request ? `request:  ${JSON.stringify(entry.request)}\n` : ""}
          {entry.response ? `response: ${JSON.stringify(entry.response)}` : ""}
        </pre>
      )}
    </div>
  );
}

function RemediationRow({ incident }) {
  const [open, setOpen] = useState(false);
  const meta = outcomeMeta(incident.outcome);
  const log = incident.remediationLog || [];

  return (
    <div className="anomaly-row">
      <div className="anomaly-row-header" onClick={() => setOpen((o) => !o)}>
        <span className={`anomaly-chevron ${open ? "open" : ""}`}>&#9656;</span>
        <span className="anomaly-trace-id mono">{shortTraceId(incident.traceId)}</span>
        <span className={`outcome-badge ${meta.className}`}>{meta.label}</span>
        <span className="anomaly-time">{relativeTime(incident.generatedAt)}</span>
      </div>
      {open && (
        <div className="remediation-detail">
          {log.length === 0 ? (
            <div className="panel-empty">No remediation actions logged.</div>
          ) : (
            log.map((entry, i) => <RemediationLogEntry key={i} entry={entry} />)
          )}
        </div>
      )}
    </div>
  );
}

export function RemediationPanel({ incidents, error, status, loading, onRetry }) {
  const items = incidents?.incidents || [];
  return (
    <section className="panel panel--wide">
      <div className="panel-header">
        <h2>Remediation Actions</h2>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {items.length}
        </span>
      </div>
      <div className="panel-body">
        {error ? (
          <PanelError message={error} status={status} onRetry={onRetry} />
        ) : loading && items.length === 0 ? (
          <PanelSkeleton rows={2} />
        ) : items.length === 0 ? (
          <div className="panel-empty">No incidents yet.</div>
        ) : (
          items.map((inc) => <RemediationRow key={inc.traceId + inc.generatedAt} incident={inc} />)
        )}
      </div>
    </section>
  );
}
