// Baked in at Vite build time (import.meta.env.VITE_* is a static string
// replacement, not a runtime lookup) - see the Dockerfile for how these are
// set as build args. Defaults assume the whole stack runs on localhost,
// which is this project's only deployment target.
export const config = {
  ANOMALY_API_URL: import.meta.env.VITE_ANOMALY_API_URL || "http://localhost:8000",
  RCA_API_URL: import.meta.env.VITE_RCA_API_URL || "http://localhost:8100",
  ORDER_API_URL: import.meta.env.VITE_ORDER_API_URL || "http://localhost:8081",

  ANOMALY_POLL_MS: 7000,
  INCIDENT_POLL_MS: 7000,

  // A service node in the topology view reads "unhealthy" if any anomaly
  // touching it closed within this window - after that it ages back to
  // healthy on its own, the same way an ops dashboard's alert state clears.
  UNHEALTHY_WINDOW_MINUTES: 10,
};
