import { useState } from "react";
import { PanelError } from "./PanelError.jsx";
import { Meter } from "./Meter.jsx";
import { Tag } from "./Tag.jsx";
import { outcomeMeta } from "../utils/outcome.js";
import { relativeTime, shortTraceId } from "../utils/format.js";

function IncidentCard({ incident }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const report = incident.report || {};
  const hasParseError = Boolean(report.parseError);
  const meta = outcomeMeta(incident.outcome);

  return (
    <div className={`incident-card ${hasParseError ? "incident-card--parse-error" : ""}`}>
      {hasParseError && <div className="incident-parse-warning">&#9888; model output could not be fully parsed</div>}

      <div className="incident-root-cause">{report.rootCause || "(no root cause returned)"}</div>

      <div className="incident-meta-row">
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {shortTraceId(incident.traceId)} &middot; {relativeTime(incident.generatedAt)}
        </span>
        {incident.outcome && <span className={`outcome-badge ${meta.className}`}>{meta.label}</span>}
        <div style={{ width: 140 }}>
          <Meter value={report.confidence ?? 0} />
        </div>
      </div>

      <div>
        {(report.affectedServices || []).map((s) => (
          <Tag key={s}>{s}</Tag>
        ))}
      </div>

      {report.suggestedFix && (
        <div className="incident-fix">
          <strong>Suggested fix:</strong> {report.suggestedFix}
        </div>
      )}

      {report.reasoning && (
        <>
          <button className="incident-reasoning-toggle" onClick={() => setShowReasoning((s) => !s)}>
            {showReasoning ? "Hide reasoning" : "Show reasoning"}
          </button>
          {showReasoning && <div className="incident-reasoning">{report.reasoning}</div>}
        </>
      )}
    </div>
  );
}

export function IncidentPanel({ incidents, error }) {
  const items = incidents?.incidents || [];
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Incident Reports</h2>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {items.length}
        </span>
      </div>
      <div className="panel-body">
        {error ? (
          <PanelError message={error} />
        ) : items.length === 0 ? (
          <div className="panel-empty">No incident reports yet.</div>
        ) : (
          items.map((inc) => <IncidentCard key={inc.traceId + inc.generatedAt} incident={inc} />)
        )}
      </div>
    </section>
  );
}
