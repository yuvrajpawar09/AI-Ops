import os

# Matches the env var pattern used by the 4 Java services in Phase 1/2:
# defaults assume running inside docker-compose (hostname "kafka"), override
# for host-side runs (e.g. training/train.py invoked outside Docker).
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "logs")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.join(BASE_DIR, "models"))
DRAIN_CONFIG_PATH = os.path.join(BASE_DIR, "drain3.ini")

DRAIN_STATE_PATH = os.path.join(MODELS_DIR, "drain3_state.bin")
MODEL_PATH = os.path.join(MODELS_DIR, "lstm_autoencoder.pt")
THRESHOLD_PATH = os.path.join(MODELS_DIR, "threshold.json")

# How long (seconds) a traceId can go without a new log line before its
# sequence is considered complete and gets scored. Should comfortably exceed
# the Filebeat/Kafka pipeline's typical delivery latency, not just the app's
# own processing time, or traces get cut off mid-sequence.
IDLE_TIMEOUT_SECONDS = float(os.environ.get("IDLE_TIMEOUT_SECONDS", "8"))

MAX_ANOMALIES_STORED = int(os.environ.get("MAX_ANOMALIES_STORED", "200"))
