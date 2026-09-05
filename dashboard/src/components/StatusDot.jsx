export function StatusDot({ state }) {
  // state: "good" | "critical" | "unknown"
  return <span className={`status-dot status-dot--${state}`} />;
}
