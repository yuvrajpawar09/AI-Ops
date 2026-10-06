import { config } from "../config.js";
import { usePolling } from "../hooks/usePolling.js";
import { TopologyView } from "../components/TopologyView.jsx";
import { AnomalyTimeline } from "../components/AnomalyTimeline.jsx";
import { IncidentPanel } from "../components/IncidentPanel.jsx";
import { TriggerPanel } from "../components/TriggerPanel.jsx";
import { RemediationPanel } from "../components/RemediationPanel.jsx";
import { AppHeader } from "../components/AppHeader.jsx";

export default function Dashboard() {
  const anomalies = usePolling(`${config.ANOMALY_API_URL}/anomalies?limit=100`, config.ANOMALY_POLL_MS);
  const incidents = usePolling(`${config.RCA_API_URL}/incidents?limit=50`, config.INCIDENT_POLL_MS);

  return (
    <div className="dashboard">
      <AppHeader anomalies={anomalies} incidents={incidents} />

      <div className="dashboard-grid">
        <TopologyView
          anomalies={anomalies.data}
          error={anomalies.error}
          status={anomalies.status}
          onRetry={anomalies.refresh}
        />
        <TriggerPanel />
        <AnomalyTimeline
          anomalies={anomalies.data}
          error={anomalies.error}
          status={anomalies.status}
          loading={anomalies.loading}
          onRetry={anomalies.refresh}
        />
        <IncidentPanel
          incidents={incidents.data}
          error={incidents.error}
          status={incidents.status}
          loading={incidents.loading}
          onChanged={incidents.refresh}
        />
        <RemediationPanel
          incidents={incidents.data}
          error={incidents.error}
          status={incidents.status}
          loading={incidents.loading}
          onRetry={incidents.refresh}
        />
      </div>
    </div>
  );
}
