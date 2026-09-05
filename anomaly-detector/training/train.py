"""
Trains the LSTM log-sequence autoencoder on a batch of "normal" traffic.

Workflow:
    1. docker compose up --build -d          (brings up all 9 containers)
    2. generate normal traffic, e.g. from the host:
           for i in {1..80}; do
             curl -s -X POST http://localhost:8081/orders \
               -H "Content-Type: application/json" \
               -d '{"customerId":"cust-1","productId":"PROD-1","quantity":1,"amount":199.0}' \
               > /dev/null
             sleep 0.3
           done
    3. docker compose run --rm anomaly-detector python -m training.train
    4. docker compose restart anomaly-detector   (picks up the new model)

This script consumes the SAME Kafka "logs" topic the live service reads,
but with its own fresh consumer group each run (so it always replays from
the beginning of the topic instead of competing with the live service's
"anomaly-detector" group for messages).
"""

import argparse
import json
import os
import time
from collections import defaultdict

import torch
from kafka import KafkaConsumer
from torch.utils.data import DataLoader, TensorDataset

from app import config
from app.drain_parser import build_template_miner
from app.features import MIN_SEQ_LEN, build_sequence_tensor, clamp_template_id, service_id
from app.model import LogSequenceAutoencoder, masked_mse_loss, sequence_errors
from app.timestamps import parse_timestamp


def collect_events(bootstrap_servers, topic, duration_seconds, max_messages):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=f"anomaly-trainer-{int(time.time())}",  # fresh group -> always reads from the start
        auto_offset_reset="earliest",
        consumer_timeout_ms=10_000,  # stop iterating after 10s of no new messages
    )
    traces = defaultdict(list)
    deadline = time.time() + duration_seconds
    count = 0
    print(f"Collecting normal-traffic logs from '{topic}' for up to {duration_seconds}s "
          f"(or {max_messages} messages, whichever comes first)...")

    for record in consumer:
        try:
            payload = json.loads(record.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        trace_id = payload.get("traceId")
        svc = payload.get("service")
        message = payload.get("message")
        if not trace_id or not svc or not message:
            continue

        traces[trace_id].append({
            "service": svc,
            "level": payload.get("level", "INFO"),
            "message": message,
            "timestamp": parse_timestamp(payload.get("timestamp")),
        })
        count += 1
        if count >= max_messages or time.time() >= deadline:
            break

    consumer.close()
    print(f"Collected {count} log lines across {len(traces)} traces.")
    return traces


def build_dataset(traces, template_miner):
    template_seqs, service_seqs, cont_seqs, masks = [], [], [], []

    for trace_id, events in traces.items():
        events.sort(key=lambda e: e["timestamp"])
        if len(events) < MIN_SEQ_LEN:
            continue  # too short to be a meaningful sequence - likely a partial capture

        enriched = []
        for ev in events:
            result = template_miner.add_log_message(ev["message"])
            enriched.append({
                "template_id": clamp_template_id(result["cluster_id"]),
                "service_id": service_id(ev["service"]),
                "level": ev["level"],
                "timestamp": ev["timestamp"],
            })

        t_ids, s_ids, cont, mask = build_sequence_tensor(enriched)
        template_seqs.append(t_ids)
        service_seqs.append(s_ids)
        cont_seqs.append(cont)
        masks.append(mask)

    if not template_seqs:
        raise SystemExit(
            "No usable training sequences collected. Generate more /orders "
            "traffic first, then re-run this script."
        )

    return (
        torch.stack(template_seqs),
        torch.stack(service_seqs),
        torch.stack(cont_seqs),
        torch.stack(masks),
    )


def train(template_ids, service_ids, cont, mask, epochs, lr):
    model = LogSequenceAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    dataset = TensorDataset(template_ids, service_ids, cont, mask)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)

    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for t_batch, s_batch, c_batch, m_batch in loader:
            optimizer.zero_grad()
            recon, target = model(t_batch, s_batch, c_batch)
            loss = masked_mse_loss(recon, target, m_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * t_batch.size(0)
        print(f"epoch {epoch:3d}/{epochs}  loss={total_loss / len(dataset):.5f}")

    return model


def compute_threshold(model, template_ids, service_ids, cont, mask):
    model.eval()
    with torch.no_grad():
        recon, target = model(template_ids, service_ids, cont)
        errors = sequence_errors(recon, target, mask)

    mean = errors.mean().item()
    std = errors.std().item()
    threshold = mean + 3 * std
    return {"mean": mean, "std": std, "threshold": threshold, "n_samples": errors.shape[0]}


def main():
    parser = argparse.ArgumentParser(description="Train the LSTM log-sequence autoencoder on normal traffic.")
    parser.add_argument("--bootstrap-servers", default=config.KAFKA_BOOTSTRAP_SERVERS)
    parser.add_argument("--topic", default=config.KAFKA_TOPIC)
    parser.add_argument("--duration", type=int, default=120, help="max seconds to collect logs for")
    parser.add_argument("--max-messages", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    os.makedirs(config.MODELS_DIR, exist_ok=True)

    template_miner = build_template_miner()
    traces = collect_events(args.bootstrap_servers, args.topic, args.duration, args.max_messages)
    template_ids, service_ids, cont, mask = build_dataset(traces, template_miner)

    print(f"Training on {template_ids.shape[0]} sequences "
          f"({len(template_miner.drain.clusters)} Drain3 templates discovered so far)...")

    model = train(template_ids, service_ids, cont, mask, args.epochs, args.lr)
    stats = compute_threshold(model, template_ids, service_ids, cont, mask)

    torch.save(model.state_dict(), config.MODEL_PATH)
    with open(config.THRESHOLD_PATH, "w") as f:
        json.dump(stats, f, indent=2)
    template_miner.save_state("training complete")

    print(f"Saved model to {config.MODEL_PATH}")
    print(f"Anomaly threshold: {stats['threshold']:.5f} (mean={stats['mean']:.5f}, std={stats['std']:.5f}, "
          f"n={stats['n_samples']})")
    print("Restart the anomaly-detector container to pick up the new model: "
          "docker compose restart anomaly-detector")


if __name__ == "__main__":
    main()
