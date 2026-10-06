import threading
import time
from collections import deque


class IncidentStore:
    """Bounded, thread-safe ring buffer of generated incident reports, newest
    first - same pattern as anomaly-detector's AnomalyStore in Phase 3."""

    def __init__(self, max_size: int):
        self._lock = threading.Lock()
        self._items = deque(maxlen=max_size)

    def add(self, item: dict):
        with self._lock:
            self._items.appendleft(item)

    def recent(self, limit: int):
        with self._lock:
            return list(self._items)[:limit]

    def acknowledge(self, trace_id: str, username: str):
        with self._lock:
            for item in self._items:
                if item.get("traceId") == trace_id:
                    item["acknowledgedBy"] = username
                    item["acknowledgedAt"] = time.time()
                    return dict(item)
        return None


class AppState:
    def __init__(self, max_incidents: int):
        self.incident_store = IncidentStore(max_incidents)
