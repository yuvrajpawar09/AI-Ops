import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter

import numpy as np
import requests
import torch
from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig
from torch.utils.data import DataLoader, TensorDataset

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DETECTOR = os.path.join(REPO, "anomaly-detector")
sys.path.insert(0, DETECTOR)

from app.features import (  # noqa: E402
    CONT_FEATURE_DIM_V2,
    MIN_SEQ_LEN,
    build_sequence_tensor_v2,
    clamp_template_id,
    service_id,
)
from app.model import (  # noqa: E402
    LogSequenceAutoencoder,
    masked_mse_loss,
    sequence_errors,
)
from app.timestamps import parse_timestamp  # noqa: E402

SERVICES = ["order-service", "payment-service", "inventory-service", "notification-service"]
ORDER_URL = "http://localhost:8081/orders"
MODELS_V2 = os.path.join(DETECTOR, "models_v2")
PROD_DRAIN = os.path.join(DETECTOR, "models", "drain3_state.bin")
V2_DRAIN = os.path.join(MODELS_V2, "drain3_state.bin")


def make_payload(rng, tag):
    return {
        "customerId": f"{tag}-cust-{rng.randint(1, 250)}",
        "productId": rng.choice(["PROD-1", "PROD-2"]),
        "quantity": rng.randint(1, 10),
        "amount": round(rng.uniform(10.0, 5000.0), 2),
    }


def _one(payload, out, lock):
    try:
        r = requests.post(ORDER_URL, json=payload, timeout=30)
        body = r.json()
        if body.get("status") == "COMPLETED":
            with lock:
                out.append(body["traceId"])
    except Exception:
        pass


def send(n, tag, rng):
    ids = []
    lock = threading.Lock()
    sent = 0
    while sent < n:
        if rng.random() < 0.3:
            burst = min(rng.randint(4, 10), n - sent)
            threads = [threading.Thread(target=_one, args=(make_payload(rng, tag), ids, lock))
                       for _ in range(burst)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            sent += burst
            time.sleep(rng.uniform(0.2, 0.8))
        else:
            _one(make_payload(rng, tag), ids, lock)
            sent += 1
            time.sleep(rng.uniform(0.01, 0.15))
        if sent % 100 < 2:
            print(f"\r  {tag}: {sent}/{n}", end="", flush=True)
    print(f"\r  {tag}: {len(ids)}/{n} completed orders captured")
    return ids


def harvest(trace_ids):
    want = set(trace_ids)
    per = {t: [] for t in trace_ids}
    for svc in SERVICES:
        out = subprocess.run(["docker", "logs", svc], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        for line in (out.stdout + "\n" + out.stderr).splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = p.get("traceId")
            if t in want:
                per[t].append(p)
    return per


def build(per, miner):
    T, S, C, M, lens = [], [], [], [], []
    for _t, lines in per.items():
        if len(lines) < MIN_SEQ_LEN:
            continue
        lines.sort(key=lambda p: parse_timestamp(p.get("timestamp")))
        evs = []
        for p in lines:
            res = miner.add_log_message(p.get("message", ""))
            evs.append({
                "template_id": clamp_template_id(res["cluster_id"]),
                "service_id": service_id(p.get("service", "")),
                "level": p.get("level", "INFO"),
                "timestamp": parse_timestamp(p.get("timestamp")),
            })
        lens.append(len(evs))
        a, b, c, d = build_sequence_tensor_v2(evs)
        T.append(a); S.append(b); C.append(c); M.append(d)
    if not T:
        raise SystemExit("no usable training sequences harvested")
    return torch.stack(T), torch.stack(S), torch.stack(C), torch.stack(M), lens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=1000)
    ap.add_argument("--val", type=int, default=300)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pause", type=float, default=0.03)
    ap.add_argument("--settle", type=int, default=60)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    os.makedirs(MODELS_V2, exist_ok=True)

    print("[setup] stopping rca-agent and resetting state")
    subprocess.run(["docker", "compose", "stop", "rca-agent"], capture_output=True, text=True)
    requests.post("http://localhost:8081/admin/config", json={"rejectZeroAmount": False}, timeout=10)

    print(f"[traffic] generating {args.train} train + {args.val} val normal orders")
    rng = random.Random(args.seed)
    train_ids = send(args.train, "v2tr", rng)
    val_ids = send(args.val, "v2va", rng)

    print(f"[wait] settling {args.settle}s so every line reaches the service logs")
    time.sleep(args.settle)

    print("[drain3] loading production template state (copy, production file untouched)")
    shutil.copyfile(PROD_DRAIN, V2_DRAIN)
    cfg = TemplateMinerConfig()
    cfg.load(os.path.join(DETECTOR, "drain3.ini"))
    miner = TemplateMiner(persistence_handler=FilePersistence(V2_DRAIN), config=cfg)
    print(f"[drain3] clusters loaded: {len(miner.drain.clusters)}")

    print("[harvest] reading service logs")
    tr_per = harvest(train_ids)
    va_per = harvest(val_ids)

    Tt, St, Ct, Mt, tr_lens = build(tr_per, miner)
    Tv, Sv, Cv, Mv, va_lens = build(va_per, miner)

    print(f"[data] train sequences {Tt.shape[0]:,}  val sequences {Tv.shape[0]:,}")
    print(f"[data] train length distribution: {Counter(tr_lens).most_common()}")
    print(f"[data] val   length distribution: {Counter(va_lens).most_common()}")
    full = sum(1 for n in tr_lens if n == 10) / max(1, len(tr_lens))
    print(f"[data] share of complete 10-line traces in training set: {full:.2%}")

    model = LogSequenceAutoencoder(cont_dim=CONT_FEATURE_DIM_V2)
    print(f"[model] v2, {sum(p.numel() for p in model.parameters()):,} parameters")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    ds = TensorDataset(Tt, St, Ct, Mt)
    dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True)

    model.train()
    for ep in range(1, args.epochs + 1):
        tot = 0.0
        for tb, sb, cb, mb in dl:
            opt.zero_grad()
            recon, target = model(tb, sb, cb)
            loss = masked_mse_loss(recon, target, mb)
            loss.backward()
            opt.step()
            tot += loss.item() * tb.size(0)
        print(f"\r[train] epoch {ep:3d}/{args.epochs} loss={tot/len(ds):.6f}", end="", flush=True)
    print()

    model.eval()
    with torch.no_grad():
        tr_scores = sequence_errors(*model(Tt, St, Ct), Mt).numpy()
        va_scores = sequence_errors(*model(Tv, Sv, Cv), Mv).numpy()

    val_p99 = float(np.percentile(va_scores, 99))
    val_sigma = float(va_scores.mean() + 3 * va_scores.std())
    thr = max(val_p99, val_sigma)
    stats = {
        "feature_version": "v2",
        "threshold": thr,
        "rule": "max(validation p99, validation mean + 3*std)",
        "val_mean_plus_3std": val_sigma,
        "chosen_by": "p99" if val_p99 >= val_sigma else "mean+3std",
        "train_mean": float(tr_scores.mean()),
        "train_std": float(tr_scores.std()),
        "val_p95": float(np.percentile(va_scores, 95)),
        "val_p99": val_p99,
        "val_p999": float(np.percentile(va_scores, 99.9)),
        "n_train": int(Tt.shape[0]),
        "n_val": int(Tv.shape[0]),
        "train_length_distribution": dict(Counter(tr_lens)),
        "complete_trace_share": full,
    }
    torch.save(model.state_dict(), os.path.join(MODELS_V2, "lstm_autoencoder.pt"))
    with open(os.path.join(MODELS_V2, "threshold.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    miner.save_state("v2 training complete")

    print(f"[thresh] val p99          = {val_p99:.9f}")
    print(f"[thresh] val mean+3std    = {val_sigma:.9f}")
    print(f"[thresh] chosen           = {thr:.9f}  (by {stats['chosen_by']})")
    print(f"[done] wrote {MODELS_V2}")
    print(json.dumps({k: v for k, v in stats.items() if k != "train_length_distribution"}, indent=2))


if __name__ == "__main__":
    main()
