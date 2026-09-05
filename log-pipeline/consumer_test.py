"""
Phase 2 sanity check: prints every message that arrives on the Kafka "logs"
topic, so you can confirm the pipeline

    Spring Boot services -> Docker json-file logs -> Filebeat -> Kafka

is actually working end-to-end before Phase 3 (the LSTM anomaly detector)
starts reading from this same topic.

Run this from the host machine (NOT inside a container) - it connects via
Kafka's PLAINTEXT_HOST listener, which docker-compose.yml publishes as
localhost:9092.

Usage:
    pip install -r requirements.txt
    python consumer_test.py
"""

import json

from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "logs"


def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="aiops-test-consumer",
    )

    print(f"Listening on topic '{TOPIC}' at {KAFKA_BOOTSTRAP_SERVERS} ... (Ctrl+C to stop)\n")

    for record in consumer:
        raw = record.value.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[unparsable] {raw}")
            continue

        service = payload.get("service", "?")
        level = payload.get("level", "?")
        trace_id = payload.get("traceId", "-")
        message = payload.get("message", "")
        print(f"[{service:20s}] [{level:5s}] traceId={trace_id} | {message}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
