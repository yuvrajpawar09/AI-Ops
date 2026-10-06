import argparse
import json
import statistics
import sys
import time

import requests

OLLAMA = "http://localhost:11434"

SYSTEM = (
    "You are an experienced Site Reliability Engineer performing root cause analysis on a failure "
    "automatically flagged by an anomaly detector in a microservices system. Respond with a single "
    "JSON object and nothing else, matching exactly this schema: "
    '{"rootCause": "...", "affectedServices": ["..."], "confidence": 0.0, "suggestedFix": "...", '
    '"reasoning": "..."} . confidence must be a number between 0.0 and 1.0.'
)

USER = """## Service dependency graph
order-service calls: payment-service, inventory-service
payment-service calls: notification-service
inventory-service calls: (none)
notification-service calls: (none)

## Anomaly summary
traceId: 8f3c1a92-77bd-4e1a-9c0b-2f5a7e4d1b33
anomaly score: 0.41553 (flagged - exceeded the learned normal-traffic threshold of 0.29270)
total trace duration: 2.55s

## Log sequence for this trace, in order
[+  0.00s] order-service        INFO  Order 70cb0c0b created for customer bench-latency (product=PROD-1, qty=1, amount=179.0)
[+  0.00s] order-service        INFO  Calling payment-service at http://payment-service:8082/payments
[+  0.01s] payment-service      INFO  Processing payment b54aa275 for order 70cb0c0b (amount=179.0)
[+  0.01s] payment-service      INFO  Payment b54aa275 succeeded for order 70cb0c0b
[+  0.01s] payment-service      INFO  Calling notification-service at http://notification-service:8084/notifications
[+  0.02s] notification-service INFO  Notification 918c3b69 sent to customer bench-latency for order 70cb0c0b
[+  0.02s] order-service        INFO  Order 70cb0c0b payment confirmed (paymentId=b54aa275)
[+  0.02s] order-service        INFO  Calling inventory-service at http://inventory-service:8083/inventory/reserve
[+  2.55s] inventory-service    INFO  Reserved 1 units of PROD-1 for order 70cb0c0b (reservationId=4d22ce3a)
[+  2.55s] order-service        INFO  Order 70cb0c0b completed successfully

Analyze this sequence and produce the JSON incident report described in your instructions."""


def one(model, keep_alive):
    t0 = time.time()
    r = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
            "keep_alive": keep_alive,
        },
        timeout=600,
    )
    wall = time.time() - t0
    r.raise_for_status()
    d = r.json()
    return {
        "wall_seconds": wall,
        "total_duration_s": d.get("total_duration", 0) / 1e9,
        "load_duration_s": d.get("load_duration", 0) / 1e9,
        "prompt_eval_count": d.get("prompt_eval_count", 0),
        "eval_count": d.get("eval_count", 0),
        "eval_duration_s": d.get("eval_duration", 0) / 1e9,
        "content_chars": len(d.get("message", {}).get("content", "")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    print(f"[{args.label}] warming model (cold load excluded from the timed reps)")
    warm = one(args.model, "10m")
    print(f"[{args.label}] warm-up wall={warm['wall_seconds']:.2f}s load={warm['load_duration_s']:.2f}s")

    reps = []
    for i in range(args.reps):
        m = one(args.model, "10m")
        tps = m["eval_count"] / m["eval_duration_s"] if m["eval_duration_s"] else 0.0
        reps.append({**m, "tokens_per_second": tps})
        print(f"[{args.label}] rep {i+1}: wall={m['wall_seconds']:.2f}s  "
              f"eval={m['eval_count']} tok in {m['eval_duration_s']:.2f}s  ({tps:.1f} tok/s)")

    walls = [r["wall_seconds"] for r in reps]
    tpss = [r["tokens_per_second"] for r in reps]
    summary = {
        "label": args.label,
        "model": args.model,
        "reps": reps,
        "wall_mean": statistics.mean(walls),
        "wall_min": min(walls),
        "wall_max": max(walls),
        "tokens_per_second_mean": statistics.mean(tpss),
        "warmup": warm,
    }
    print(f"[{args.label}] MEAN wall {summary['wall_mean']:.2f}s  "
          f"({summary['wall_min']:.2f}-{summary['wall_max']:.2f}s)  "
          f"{summary['tokens_per_second_mean']:.1f} tok/s")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"[{args.label}] wrote {args.out}")


if __name__ == "__main__":
    main()
