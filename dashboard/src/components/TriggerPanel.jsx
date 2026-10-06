import { useState } from "react";
import { adminApi } from "../auth/api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { shortTraceId } from "../utils/format.js";

const PRESETS = [
  {
    id: "normal",
    label: "Normal order",
    desc: "PROD-1 x1 @ 199.0 - should complete cleanly",
  },
  {
    id: "out_of_stock",
    label: "Out-of-stock order",
    desc: "PROD-3 x5 (only 2 seeded) - triggers INVENTORY_FAILED",
  },
  {
    id: "payment_failure",
    label: "Payment failure",
    desc: "amount=0 - payment-service declines it",
  },
];

export function TriggerPanel() {
  const { can } = useAuth();
  const allowed = can("trigger");
  const [pending, setPending] = useState(null);
  const [log, setLog] = useState([]);

  function push(entry) {
    setLog((prev) => [{ key: `${Date.now()}-${Math.random()}`, ...entry }, ...prev].slice(0, 8));
  }

  async function fire(preset) {
    setPending(preset.id);
    try {
      const body = await adminApi.trigger(preset.id);
      push({
        label: preset.label,
        status: body.status || "SENT",
        traceId: body.traceId,
        message: body.message,
      });
    } catch (err) {
      push({
        label: preset.label,
        status: err?.status === 403 ? "FORBIDDEN" : "ERROR",
        message: err?.message || "request failed",
      });
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Manual Trigger</h2>
        {!allowed && <span className="panel-badge">read-only</span>}
      </div>
      <div className="panel-body">
        {!allowed ? (
          <div className="panel-empty">
            Placing test orders requires the ADMIN role. Your role can view detections and reports
            but not generate traffic.
          </div>
        ) : (
          <>
            <div className="trigger-buttons">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  className="trigger-button"
                  disabled={pending !== null}
                  onClick={() => fire(p)}
                >
                  <span className="trigger-button-label">
                    {pending === p.id ? "Sending..." : p.label}
                  </span>
                  <span className="trigger-button-desc">{p.desc}</span>
                </button>
              ))}
            </div>

            <div className="trigger-log">
              <div className="trigger-log-title">Recent triggers</div>
              {log.length === 0 ? (
                <div className="panel-empty">Nothing triggered yet this session.</div>
              ) : (
                log.map((entry) => (
                  <div className="trigger-log-entry" key={entry.key}>
                    <span className={`trigger-log-status trigger-log-status--${entry.status}`}>
                      {entry.status}
                    </span>
                    <span>{entry.label}</span>
                    {entry.traceId && (
                      <span className="mono" style={{ color: "var(--text-muted)" }}>
                        {shortTraceId(entry.traceId)}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
