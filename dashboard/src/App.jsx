import { config } from "./config.js";
import { usePolling } from "./hooks/usePolling.js";
import { TopologyView } from "./components/TopologyView.jsx";
import { AnomalyTimeline } from "./components/AnomalyTimeline.jsx";
import { IncidentPanel } from "./components/IncidentPanel.jsx";
import { TriggerPanel } from "./components/TriggerPanel.jsx";
import { RemediationPanel } from "./components/RemediationPanel.jsx";
import { StatusDot } from "./components/StatusDot.jsx";

export default function App() {
  // Each backend endpoint is polled exactly once, here at the top, and the
  // result is passed down as props - TopologyView and AnomalyTimeline both
  // need the anomalies feed, but neither re-polls it independently.
  const anomalies = usePolling(`${config.ANOMALY_API_URL}/anomalies?limit=100`, config.ANOMALY_POLL_MS);
  const incidents = usePolling(`${config.RCA_API_URL}/incidents?limit=50`, config.INCIDENT_POLL_MS);

  const overallState = anomalies.error || incidents.error ? "unknown" : "good";

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1 style={{ display: "inline" }}>AI-OPS DASHBOARD</h1>
          <span className="subtitle">autonomous log anomaly detection &amp; root cause analysis</span>
        </div>
        <div className="header-status">
          <StatusDot state={overallState} />
          {anomalies.data ? `${anomalies.data.count} anomalies` : "..."} &middot;{" "}
          {incidents.data ? `${incidents.data.count} incidents` : "..."}
        </div>
      </header>

      <div className="dashboard-grid">
        <TopologyView anomalies={anomalies.data} error={anomalies.error} />
        <TriggerPanel />
        <AnomalyTimeline anomalies={anomalies.data} error={anomalies.error} />
        <IncidentPanel incidents={incidents.data} error={incidents.error} />
        <RemediationPanel incidents={incidents.data} error={incidents.error} />
      </div>
    </div>
  );
}
