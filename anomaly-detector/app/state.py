import threading
from collections import deque

from app.drain_parser import build_template_miner
from app.kafka_consumer import TraceBuffer
from app.scorer import try_load_scorer


class AnomalyStore:
    """Bounded, thread-safe ring buffer of recently flagged anomalies,
    newest first. Deliberately in-memory only, matching Phase 1's
    "no database yet" philosophy - /anomalies is a live tail, not an archive."""

    def __init__(self, max_size):
        self._lock = threading.Lock()
        self._items = deque(maxlen=max_size)

    def add(self, item):
        with self._lock:
            self._items.appendleft(item)

    def upsert(self, item):
        with self._lock:
            tid = item.get("traceId")
            for i, existing in enumerate(self._items):
                if existing.get("traceId") == tid:
                    del self._items[i]
                    break
            self._items.appendleft(item)

    def remove(self, trace_id):
        with self._lock:
            for i, existing in enumerate(self._items):
                if existing.get("traceId") == trace_id:
                    del self._items[i]
                    return True
        return False

    def recent(self, limit):
        with self._lock:
            return list(self._items)[:limit]


class AppState:
    def __init__(self, max_anomalies):
        self.template_miner = build_template_miner()
        self.buffer = TraceBuffer()
        self.scorer = try_load_scorer()
        self.anomaly_store = AnomalyStore(max_anomalies)
