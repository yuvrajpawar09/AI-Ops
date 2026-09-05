import logging
import threading
import time

import requests

from app import config
from app.analyzer import analyze_anomaly

logger = logging.getLogger(__name__)


def _poll(state):
    # In-memory dedupe: /anomalies is a sliding window of recent flags, so
    # the same traceId would otherwise get re-analyzed (and re-billed in
    # LLM latency) on every poll until it ages out of anomaly-detector's
    # store. This is intentionally NOT persisted - a restart re-analyzing
    # whatever's still in the window is fine for a demo system.
    seen_trace_ids = set()

    while True:
        try:
            resp = requests.get(
                f"{config.ANOMALY_DETECTOR_URL}/anomalies",
                params={"limit": 100},
                timeout=10,
            )
            resp.raise_for_status()
            anomalies = resp.json().get("anomalies", [])

            for anomaly in anomalies:
                trace_id = anomaly["traceId"]
                if trace_id in seen_trace_ids:
                    continue

                try:
                    incident = analyze_anomaly(anomaly)
                    state.incident_store.add(incident)
                    # Only mark as done on success - a transient failure
                    # (e.g. Ollama reloading a model it had unloaded after
                    # sitting idle) must be retried on the next poll, not
                    # silently dropped forever.
                    seen_trace_ids.add(trace_id)
                    logger.info(
                        "Generated incident report for trace %s (confidence=%.2f)",
                        trace_id, incident["report"].get("confidence", 0.0),
                    )
                except Exception:
                    logger.exception("Failed to analyze anomaly for trace %s - will retry next poll", trace_id)

            if len(seen_trace_ids) > 5000:  # bound memory over a long-running demo
                seen_trace_ids.clear()

        except Exception:
            logger.exception("Failed to poll anomaly-detector")

        time.sleep(config.POLL_INTERVAL_SECONDS)


def start_background_poller(state):
    threading.Thread(target=_poll, args=(state,), daemon=True, name="anomaly-poller").start()
