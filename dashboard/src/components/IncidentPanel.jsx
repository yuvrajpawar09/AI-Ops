import { useMemo, useState } from "react";
import { PanelError } from "./PanelError.jsx";
import { PanelSkeleton } from "./PanelSkeleton.jsx";
import { Meter } from "./Meter.jsx";
import { Tag } from "./Tag.jsx";
import { outcomeMeta } from "../utils/outcome.js";
import { relativeTime, shortTraceId } from "../utils/format.js";
import { incidentApi } from "../auth/api.js";
import { useAuth } from "../auth/AuthContext.jsx";

const CONFIDENCE_BANDS = [
  { id: "all", label: "Any confidence", test: () => true },
  { id: "high", label: "High (>= 0.85)", test: (c) => c >= 0.85 },
  { id: "medium", label: "Medium (0.5 - 0.85)", test: (c) => c >= 0.5 && c < 0.85 },
  { id: "low", label: "Low (< 0.5)", test: (c) => c < 0.5 },
];

function IncidentCard({ incident, canAcknowledge, onChanged }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [acking, setAcking] = useState(false);
  const [ackError, setAckError] = useState(null);
  const report = incident.report || {};
  const hasParseError = Boolean(report.parseError);
  const meta = outcomeMeta(incident.outcome);

  async function acknowledge() {
    setAcking(true);
    setAckError(null);
    try {
      await incidentApi.acknowledge(incident.traceId);
      if (onChanged) await onChanged();
    } catch (err) {
      setAckError(err?.status === 403 ? "Not permitted" : err?.message || "failed");
    } finally {
      setAcking(false);
    }
  }

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

      <div className="incident-actions">
        {report.reasoning && (
          <button className="incident-reasoning-toggle" onClick={() => setShowReasoning((s) => !s)}>
            {showReasoning ? "Hide reasoning" : "Show reasoning"}
          </button>
        )}

        {incident.acknowledgedBy ? (
          <span className="ack-badge">
            acknowledged by {incident.acknowledgedBy}
            {incident.acknowledgedAt ? ` · ${relativeTime(incident.acknowledgedAt)}` : ""}
          </span>
        ) : (
          canAcknowledge && (
            <button className="ack-button" type="button" onClick={acknowledge} disabled={acking}>
              {acking ? "Acknowledging..." : "Acknowledge"}
            </button>
          )
        )}
        {ackError && <span className="ack-error">{ackError}</span>}
      </div>

      {showReasoning && report.reasoning && <div className="incident-reasoning">{report.reasoning}</div>}
    </div>
  );
}

export function IncidentPanel({ incidents, error, status, loading, onChanged }) {
  const { can } = useAuth();
  const items = incidents?.incidents || [];

  const [outcome, setOutcome] = useState("all");
  const [service, setService] = useState("all");
  const [band, setBand] = useState("all");

  const outcomes = useMemo(
    () => Array.from(new Set(items.map((i) => i.outcome).filter(Boolean))).sort(),
    [items]
  );
  const services = useMemo(
    () =>
      Array.from(
        new Set(items.flatMap((i) => i.report?.affectedServices || []).filter(Boolean))
      ).sort(),
    [items]
  );

  const filtered = useMemo(() => {
    const bandTest = CONFIDENCE_BANDS.find((b) => b.id === band)?.test ?? (() => true);
    return items.filter((i) => {
      if (outcome !== "all" && i.outcome !== outcome) return false;
      if (service !== "all" && !(i.report?.affectedServices || []).includes(service)) return false;
      return bandTest(i.report?.confidence ?? 0);
    });
  }, [items, outcome, service, band]);

  const filtersActive = outcome !== "all" || service !== "all" || band !== "all";

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Incident Reports</h2>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {filtersActive ? `${filtered.length} / ${items.length}` : items.length}
        </span>
      </div>

      {!error && items.length > 0 && (
        <div className="panel-filters">
          <label>
            <span className="sr-only">Filter by outcome</span>
            <select value={outcome} onChange={(e) => setOutcome(e.target.value)} aria-label="Filter by outcome">
              <option value="all">Any outcome</option>
              {outcomes.map((o) => (
                <option key={o} value={o}>
                  {outcomeMeta(o).label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="sr-only">Filter by service</span>
            <select value={service} onChange={(e) => setService(e.target.value)} aria-label="Filter by service">
              <option value="all">Any service</option>
              {services.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="sr-only">Filter by confidence</span>
            <select value={band} onChange={(e) => setBand(e.target.value)} aria-label="Filter by confidence">
              {CONFIDENCE_BANDS.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </label>
          {filtersActive && (
            <button
              className="filter-clear"
              type="button"
              onClick={() => {
                setOutcome("all");
                setService("all");
                setBand("all");
              }}
            >
              Clear
            </button>
          )}
        </div>
      )}

      <div className="panel-body">
        {error ? (
          <PanelError message={error} status={status} onRetry={onChanged} />
        ) : loading && items.length === 0 ? (
          <PanelSkeleton rows={2} />
        ) : items.length === 0 ? (
          <div className="panel-empty">No incident reports yet.</div>
        ) : filtered.length === 0 ? (
          <div className="panel-empty">No incidents match these filters.</div>
        ) : (
          filtered.map((inc) => (
            <IncidentCard
              key={inc.traceId + inc.generatedAt}
              incident={inc}
              canAcknowledge={can("acknowledge")}
              onChanged={onChanged}
            />
          ))
        )}
      </div>
    </section>
  );
}
