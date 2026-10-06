import os

# Matches the env var pattern used by the 4 Java services in Phase 1/2:
# defaults assume running inside docker-compose (hostname "kafka"), override
# for host-side runs (e.g. training/train.py invoked outside Docker).
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "logs")
KAFKA_GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "anomaly-detector")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.join(BASE_DIR, "models"))
DRAIN_CONFIG_PATH = os.path.join(BASE_DIR, "drain3.ini")

DRAIN_STATE_PATH = os.path.join(MODELS_DIR, "drain3_state.bin")
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(MODELS_DIR, "lstm_autoencoder.pt"))
THRESHOLD_PATH = os.environ.get("THRESHOLD_PATH", os.path.join(MODELS_DIR, "threshold.json"))

# "v1" is the shipped default. "v2" (log-scaled timing + a trace-duration
# channel) detects latency faults far better but flags ordinary timing
# jitter, including the first orders after a cold start. It is kept as an
# opt-in experiment: FEATURE_VERSION=v2 together with MODEL_PATH and
# THRESHOLD_PATH pointing at the _v2 artifacts.
FEATURE_VERSION = os.environ.get("FEATURE_VERSION", "v1")

# How long (seconds) a traceId can go without a new log line before its
# sequence is considered complete and gets scored. Should comfortably exceed
# the Filebeat/Kafka pipeline's typical delivery latency, not just the app's
# own processing time, or traces get cut off mid-sequence.
IDLE_TIMEOUT_SECONDS = float(os.environ.get("IDLE_TIMEOUT_SECONDS", "8"))

MAX_ANOMALIES_STORED = int(os.environ.get("MAX_ANOMALIES_STORED", "200"))

# How long a closed trace is retained so late-arriving lines can be
# merged back into it and the whole trace rescored in place, instead of
# the remainder being scored as a standalone fragment.
CLOSED_TRACE_GRACE_SECONDS = float(os.environ.get("CLOSED_TRACE_GRACE_SECONDS", "60"))
