import { PanelError } from "./PanelError.jsx";
import { config } from "../config.js";

// Mirrors rca-agent/app/dependency_graph.py - the dashboard doesn't infer
// this from data either, it's told the same static topology.
const NODES = [
  { id: "order-service", label: "order-service", x: 200, y: 40 },
  { id: "payment-service", label: "payment-service", x: 100, y: 150 },
  { id: "inventory-service", label: "inventory-service", x: 300, y: 150 },
  { id: "notification-service", label: "notification-service", x: 100, y: 250 },
];

const EDGES = [
  ["order-service", "payment-service"],
  ["order-service", "inventory-service"],
  ["payment-service", "notification-service"],
];

const NODE_W = 128;
const NODE_H = 40;

function computeHealth(anomalies, windowMinutes) {
  const health = {};
  for (const n of NODES) health[n.id] = "unknown";
  if (!anomalies || anomalies.length === 0) return health;

  const cutoff = Date.now() / 1000 - windowMinutes * 60;
  const unhealthy = new Set();
  for (const a of anomalies) {
    if (a.closedAt < cutoff) continue;
    for (const ev of a.events || []) unhealthy.add(ev.service);
  }
  for (const n of NODES) {
    health[n.id] = unhealthy.has(n.id) ? "critical" : "good";
  }
  return health;
}

function edgePoint(from, to, inset) {
  // Trim the line to the node's rect edge instead of its center, so the
  // arrowhead lands on the box border, not inside/behind it.
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.hypot(dx, dy) || 1;
  return {
    x1: from.x + (dx / len) * inset,
    y1: from.y + (dy / len) * inset,
    x2: to.x - (dx / len) * inset,
    y2: to.y - (dy / len) * inset,
  };
}

export function TopologyView({ anomalies, error, status, onRetry }) {
  const health = computeHealth(anomalies?.anomalies, config.UNHEALTHY_WINDOW_MINUTES);
  const nodeById = Object.fromEntries(NODES.map((n) => [n.id, n]));

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Service Topology</h2>
      </div>
      {error ? (
        <PanelError message={error} status={status} onRetry={onRetry} />
      ) : (
        <>
          <svg className="topology-svg" viewBox="0 0 400 290" role="img" aria-label="Service dependency graph">
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="var(--gridline)" />
              </marker>
            </defs>

            {EDGES.map(([fromId, toId]) => {
              const p = edgePoint(nodeById[fromId], nodeById[toId], NODE_H / 2 + 4);
              return (
                <line
                  key={`${fromId}->${toId}`}
                  className="topology-edge"
                  x1={p.x1}
                  y1={p.y1}
                  x2={p.x2}
                  y2={p.y2}
                />
              );
            })}

            {NODES.map((n) => {
              const state = health[n.id];
              const fill =
                state === "good"
                  ? "var(--status-good)"
                  : state === "critical"
                    ? "var(--status-critical)"
                    : "var(--surface-2)";
              return (
                <g key={n.id}>
                  <rect
                    className="topology-node-rect"
                    x={n.x - NODE_W / 2}
                    y={n.y - NODE_H / 2}
                    width={NODE_W}
                    height={NODE_H}
                    rx="8"
                    fill={fill}
                    fillOpacity={state === "unknown" ? 1 : 0.85}
                  />
                  <text className="topology-node-label" x={n.x} y={n.y}>
                    {n.label}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="topology-legend">
            <span className="topology-legend-item">
              <span className="status-dot status-dot--good" /> healthy
            </span>
            <span className="topology-legend-item">
              <span className="status-dot status-dot--critical" /> anomaly in last {config.UNHEALTHY_WINDOW_MINUTES}m
            </span>
            <span className="topology-legend-item">
              <span className="status-dot status-dot--unknown" /> no data yet
            </span>
          </div>
        </>
      )}
    </section>
  );
}
