import json
import logging
import threading
import time
from collections import defaultdict

from kafka import KafkaConsumer

from app import config
from app.features import MIN_SEQ_LEN, clamp_template_id, service_id
from app.timestamps import parse_timestamp

logger = logging.getLogger(__name__)


class TraceBuffer:
    """Thread-safe buffer of in-flight traces, keyed by traceId. Written to
    by the Kafka consumer thread, read/drained by the trace-closer thread."""

    def __init__(self, grace_seconds=None):
        self._lock = threading.Lock()
        self._traces = defaultdict(list)  # traceId -> list of enriched events
        self._last_seen = {}  # traceId -> wall-clock time of its last event
        # Lines for one trace can straggle in after the idle timeout has
        # already closed it - the pipeline delivers the head promptly and the
        # tail a beat later. Without this, the remainder opened a brand-new
        # buffer entry and got scored as a standalone fragment, which looks
        # exactly like a broken transaction and fires a false positive. We
        # retain closed traces for a grace window so late lines can be merged
        # back and the whole trace rescored in place.
        self._closed = {}  # traceId -> (events, closed_at)
        self.grace_seconds = (
            config.CLOSED_TRACE_GRACE_SECONDS if grace_seconds is None else grace_seconds
        )
        self.reopened = 0

    def add(self, trace_id, event):
        with self._lock:
            if trace_id in self._closed:
                retained, _ = self._closed.pop(trace_id)
                self._traces[trace_id] = retained + self._traces[trace_id]
                self.reopened += 1
            self._traces[trace_id].append(event)
            self._last_seen[trace_id] = time.time()

    def pop_idle(self, idle_seconds):
        """Removes and returns (traceId, events) for every trace that has
        gone quiet for at least idle_seconds - i.e. the flow is done. Closed
        traces are retained for grace_seconds so late-arriving lines can
        reopen and extend them rather than forming a second fragment."""
        now = time.time()
        closed = []
        with self._lock:
            idle_ids = [tid for tid, last in self._last_seen.items() if now - last >= idle_seconds]
            for tid in idle_ids:
                events = self._traces.pop(tid)
                del self._last_seen[tid]
                self._closed[tid] = (events, now)
                closed.append((tid, events))
            for tid in [t for t, (_, ts) in self._closed.items() if now - ts > self.grace_seconds]:
                del self._closed[tid]
        return closed


def _handle_message(raw_value, state):
    try:
        payload = json.loads(raw_value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return

    trace_id = payload.get("traceId")
    service = payload.get("service")
    message = payload.get("message")
    if not trace_id or not service or not message:
        return  # not one of our 4 services' application log lines

    result = state.template_miner.add_log_message(message)
    event = {
        "template_id": clamp_template_id(result["cluster_id"]),
        "template": result["template_mined"],
        "service_id": service_id(service),
        "service": service,
        "level": payload.get("level", "INFO"),
        "message": message,
        "timestamp": parse_timestamp(payload.get("timestamp")),
    }
    state.buffer.add(trace_id, event)


def _consume(state):
    while True:
        try:
            consumer = KafkaConsumer(
                config.KAFKA_TOPIC,
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=config.KAFKA_GROUP_ID,
                auto_offset_reset="latest",
                enable_auto_commit=True,
            )
            logger.info(
                "Kafka consumer connected to %s, topic '%s'",
                config.KAFKA_BOOTSTRAP_SERVERS, config.KAFKA_TOPIC,
            )
            for record in consumer:
                try:
                    _handle_message(record.value, state)
                except Exception:
                    logger.exception("Failed to process one Kafka message")
        except Exception:
            logger.exception("Kafka consumer error - reconnecting in 5s")
            time.sleep(5)


def _close_idle_traces(state):
    while True:
        time.sleep(1.0)
        for trace_id, events in state.buffer.pop_idle(config.IDLE_TIMEOUT_SECONDS):
            events.sort(key=lambda e: e["timestamp"])
            if len(events) < MIN_SEQ_LEN or state.scorer is None:
                continue

            score, is_anomaly = state.scorer.score(events)
            if is_anomaly:
                state.anomaly_store.upsert({
                    "traceId": trace_id,
                    "score": round(score, 5),
                    "threshold": round(state.scorer.threshold, 5),
                    "closedAt": time.time(),
                    "events": [
                        {
                            "service": e["service"],
                            "level": e["level"],
                            "message": e["message"],
                            "template": e["template"],
                            "timestamp": e["timestamp"],
                        }
                        for e in events
                    ],
                })
                logger.warning(
                    "Anomaly flagged for trace %s (score=%.5f > threshold=%.5f)",
                    trace_id, score, state.scorer.threshold,
                )
            else:
                state.anomaly_store.remove(trace_id)


def start_background_threads(state):
    threading.Thread(target=_consume, args=(state,), daemon=True, name="kafka-consumer").start()
    threading.Thread(target=_close_idle_traces, args=(state,), daemon=True, name="trace-closer").start()
