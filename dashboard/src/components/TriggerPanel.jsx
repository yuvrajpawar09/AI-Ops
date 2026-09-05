import { useState } from "react";
import { config } from "../config.js";
import { shortTraceId } from "../utils/format.js";

const PRESETS = [
  {
    id: "normal",
    label: "Normal order",
    desc: "PROD-1 x1 @ 199.0 - should complete cleanly",
    payload: { customerId: "demo-customer", productId: "PROD-1", quantity: 1, amount: 199.0 },
  },
  {
    id: "out-of-stock",
    label: "Out-of-stock order",
    desc: "PROD-3 x5 (only 2 seeded) - triggers INVENTORY_FAILED",
    payload: { customerId: "demo-customer", productId: "PROD-3", quantity: 5, amount: 99.0 },
  },
  {
    id: "payment-failure",
    label: "Payment failure",
    desc: "amount=0 - payment-service declines it",
    payload: { customerId: "demo-customer", productId: "PROD-1", quantity: 1, amount: 0 },
  },
];

export function TriggerPanel() {
  const [pending, setPending] = useState(null);
  const [log, setLog] = useState([]);

  async function fire(preset) {
    setPending(preset.id);
    try {
      const res = await fetch(`${config.ORDER_API_URL}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preset.payload),
        signal: AbortSignal.timeout(15000),
      });
      const body = await res.json().catch(() => ({}));
      setLog((prev) => [
        {
          key: `${Date.now()}`,
          label: preset.label,
          status: body.status || `HTTP ${res.status}`,
          traceId: body.traceId,
          message: body.message,
        },
        ...prev,
      ].slice(0, 8));
    } catch (err) {
      setLog((prev) => [
        { key: `${Date.now()}`, label: preset.label, status: "ERROR", message: err?.message || "request failed" },
        ...prev,
      ].slice(0, 8));
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Manual Trigger</h2>
      </div>
      <div className="panel-body">
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
                <span className={`trigger-log-status trigger-log-status--${entry.status}`}>{entry.status}</span>
                <span>{entry.label}</span>
                {entry.traceId && <span className="mono" style={{ color: "var(--text-muted)" }}>{shortTraceId(entry.traceId)}</span>}
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
