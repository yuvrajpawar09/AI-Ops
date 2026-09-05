import threading
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


class AppState:
    def __init__(self, max_incidents: int):
        self.incident_store = IncidentStore(max_incidents)
