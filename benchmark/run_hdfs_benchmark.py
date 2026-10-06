import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)
from torch.utils.data import DataLoader, TensorDataset

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DETECTOR = os.path.join(REPO, "anomaly-detector")
sys.path.insert(0, DETECTOR)

import app.features as app_features  # noqa: E402
from app.features import (  # noqa: E402
    MIN_SEQ_LEN,
    build_sequence_tensor,
    clamp_template_id,
)
from app.model import (  # noqa: E402
    LogSequenceAutoencoder,
    masked_mse_loss,
    sequence_errors,
)

DATA_DIR = os.path.join(HERE, "data")
CACHE_PATH = os.path.join(DATA_DIR, "hdfs_subsample.jsonl")
RESULTS_DIR = os.path.join(HERE, "results")


def tensor_cache_path(seq_len):
    return os.path.join(DATA_DIR, f"hdfs_tensors_seq{seq_len}.pt")

LINE_RE = re.compile(r"^(\d{6})\s+(\d{6})\s+(\d+)\s+(\w+)\s+([^:]+):\s*(.*)$")
KEYWORD_RE = re.compile(r"ERROR|WARN|Exception", re.IGNORECASE)


def parse_line(line):
    m = LINE_RE.match(line)
    if not m:
        return None
    date, tm, _pid, level, component, content = m.groups()
    try:
        ts = datetime.strptime(date + tm, "%y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None
    return {"timestamp": ts, "level": level.upper(), "component": component.strip(), "content": content}


def load_blocks(path, limit=None):
    blocks = []
    with open(path, "r", encoding="utf-8") as f:
        for i, raw in enumerate(f):
            if limit and i >= limit:
                break
            blocks.append(json.loads(raw))
    return blocks


def build_miner(ini_path):
    cfg = TemplateMinerConfig()
    cfg.load(ini_path)
    return TemplateMiner(persistence_handler=None, config=cfg)


def build_dataset(limit, refresh, seq_len):
    cache = tensor_cache_path(seq_len)
    if os.path.exists(cache) and not refresh:
        print(f"[cache] loading tensors from {cache}")
        blob = torch.load(cache, weights_only=False)
        if blob.get("limit") == limit and blob.get("seq_len") == seq_len:
            return blob
        print("[cache] key mismatch, rebuilding")

    print("[load] reading cached subsample")
    blocks = load_blocks(CACHE_PATH, limit or None)
    print(f"[load] {len(blocks):,} blocks, {sum(b['label'] for b in blocks):,} anomalous")

    miner = build_miner(os.path.join(DETECTOR, "drain3.ini"))
    print("[parse] drain3 template mining")
    parsed = []
    comp_counter = Counter()
    unparsed = 0
    for n, b in enumerate(blocks):
        if n and n % 10_000 == 0:
            print(f"\r        {n:,}/{len(blocks):,}", end="", flush=True)
        events = []
        for line in b["lines"]:
            p = parse_line(line)
            if p is None:
                unparsed += 1
                continue
            res = miner.add_log_message(p["content"])
            comp_counter[p["component"]] += 1
            events.append({"cluster_id": res["cluster_id"], "component": p["component"],
                           "level": p["level"], "timestamp": p["timestamp"]})
        if len(events) >= MIN_SEQ_LEN:
            events.sort(key=lambda e: e["timestamp"])
            parsed.append({"label": b["label"], "events": events,
                           "keyword": 1 if any(KEYWORD_RE.search(l) for l in b["lines"]) else 0})
    print(f"\r        {len(blocks):,}/{len(blocks):,}")
    n_templates = len(miner.drain.clusters)
    print(f"[parse] templates discovered: {n_templates}")
    print(f"[parse] usable blocks: {len(parsed):,} ({unparsed:,} unparsable lines)")

    top = [c for c, _ in comp_counter.most_common(4)]
    comp_to_id = {c: i + 1 for i, c in enumerate(top)}
    print(f"[adapt] component->service_id: {comp_to_id}")

    print("[feat] building sequence tensors")
    T, S, C, M, Y, K = [], [], [], [], [], []
    for bl in parsed:
        evs = [{"template_id": clamp_template_id(e["cluster_id"]),
                "service_id": comp_to_id.get(e["component"], 0),
                "level": e["level"], "timestamp": e["timestamp"]} for e in bl["events"]]
        t, s, c, m = build_sequence_tensor(evs)
        T.append(t); S.append(s); C.append(c); M.append(m)
        Y.append(bl["label"]); K.append(bl["keyword"])

    blob = {"T": torch.stack(T), "S": torch.stack(S), "C": torch.stack(C), "M": torch.stack(M),
            "Y": np.array(Y), "K": np.array(K), "templates": n_templates,
            "comp_to_id": comp_to_id, "unparsed": unparsed, "limit": limit, "seq_len": seq_len}
    os.makedirs(DATA_DIR, exist_ok=True)
    cache = tensor_cache_path(seq_len)
    torch.save(blob, cache)
    print(f"[cache] saved tensors -> {cache}")
    return blob


def evaluate(y, scores, thr):
    pred = (scores > thr).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    fpr = cm[0, 1] / max(1, cm[0, 0] + cm[0, 1])
    return {"threshold": float(thr), "precision": float(p), "recall": float(r), "f1": float(f1),
            "false_positive_rate": float(fpr),
            "confusion_matrix": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]),
                                 "fn": int(cm[1, 0]), "tp": int(cm[1, 1])}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--val-frac", type=float, default=0.125)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--reuse-model", action="store_true")
    ap.add_argument("--seq-len", type=int, default=app_features.MAX_SEQ_LEN)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    production_seq_len = app_features.MAX_SEQ_LEN
    app_features.MAX_SEQ_LEN = args.seq_len
    tag = "" if args.seq_len == production_seq_len else f"_seq{args.seq_len}"
    print(f"[config] sequence length {args.seq_len} "
          f"(production default {production_seq_len}; overridden in-process only)")

    blob = build_dataset(args.limit, args.refresh, args.seq_len)
    T, S, C, M, Y, K = blob["T"], blob["S"], blob["C"], blob["M"], blob["Y"], blob["K"]

    normal_idx = np.where(Y == 0)[0]
    anom_idx = np.where(Y == 1)[0]
    rng = np.random.RandomState(args.seed)
    rng.shuffle(normal_idx)
    split = int(0.8 * len(normal_idx))
    train_pool = normal_idx[:split]
    test_idx = np.concatenate([normal_idx[split:], anom_idx])
    rng.shuffle(test_idx)

    cut = int((1.0 - args.val_frac) * len(train_pool))
    train_idx, val_idx = train_pool[:cut], train_pool[cut:]

    print(f"[split] train: {len(train_idx):,} normal   val: {len(val_idx):,} normal (held out, no anomalies)")
    print(f"[split] test : {len(test_idx):,} ({int((Y[test_idx]==0).sum()):,} normal / {int(Y[test_idx].sum()):,} anomaly)")

    model = LogSequenceAutoencoder()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] {n_params:,} trainable parameters")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    ds = TensorDataset(T[train_idx], S[train_idx], C[train_idx], M[train_idx])
    dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True)

    model_path = os.path.join(RESULTS_DIR, f"hdfs_model{tag}.pt")
    if args.reuse_model and os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
        print(f"[train] reusing cached weights from {model_path}")
    else:
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
        torch.save(model.state_dict(), model_path)

    model.eval()

    def score(idx):
        out = []
        with torch.no_grad():
            for i in range(0, len(idx), 2048):
                sl = idx[i : i + 2048]
                recon, target = model(T[sl], S[sl], C[sl])
                out.append(sequence_errors(recon, target, M[sl]).numpy())
        return np.concatenate(out)

    train_scores, val_scores, test_scores = score(train_idx), score(val_idx), score(test_idx)
    y_test = Y[test_idx]
    np.savez(os.path.join(RESULTS_DIR, f"hdfs_scores{tag}.npz"),
             train=train_scores, val=val_scores, test=test_scores, y_test=y_test)

    mean, std = float(train_scores.mean()), float(train_scores.std())
    thr_sigma = mean + 3 * std
    thr_p95 = float(np.percentile(val_scores, 95))
    thr_p99 = float(np.percentile(val_scores, 99))
    thr_p999 = float(np.percentile(val_scores, 99.9))

    print(f"[thresh] train mean={mean:.6f} std={std:.6f}")
    print(f"[thresh] production rule mean+3sigma = {thr_sigma:.6f}")
    print(f"[thresh] validation p95/p99/p99.9    = {thr_p95:.6f} / {thr_p99:.6f} / {thr_p999:.6f}")

    ops = {
        "production_mean_plus_3std": evaluate(y_test, test_scores, thr_sigma),
        "validation_p95_fpr5pct": evaluate(y_test, test_scores, thr_p95),
        "validation_p99_fpr1pct": evaluate(y_test, test_scores, thr_p99),
        "validation_p999_fpr0p1pct": evaluate(y_test, test_scores, thr_p999),
    }

    roc = float(roc_auc_score(y_test, test_scores))
    ap_score = float(average_precision_score(y_test, test_scores))

    kw_pred = K[test_idx]
    kp, kr, kf1, _ = precision_recall_fscore_support(y_test, kw_pred, average="binary", zero_division=0)
    kcm = confusion_matrix(y_test, kw_pred, labels=[0, 1])
    keyword = {"precision": float(kp), "recall": float(kr), "f1": float(kf1),
               "confusion_matrix": {"tn": int(kcm[0, 0]), "fp": int(kcm[0, 1]),
                                    "fn": int(kcm[1, 0]), "tp": int(kcm[1, 1])}}

    prec_c, rec_c, _ = precision_recall_curve(y_test, test_scores)
    plt.figure(figsize=(6.5, 5))
    plt.plot(rec_c, prec_c, lw=2, label=f"LSTM autoencoder (AP={ap_score:.3f})")
    sg, pv = ops["production_mean_plus_3std"], ops["validation_p99_fpr1pct"]
    plt.scatter([sg["recall"]], [sg["precision"]], color="crimson", zorder=5,
                label=f"mean+3sigma (F1={sg['f1']:.3f})")
    plt.scatter([pv["recall"]], [pv["precision"]], color="seagreen", marker="D", zorder=5,
                label=f"val p99 calibrated (F1={pv['f1']:.3f})")
    plt.scatter([kr], [kp], color="darkorange", marker="s", zorder=5,
                label=f"keyword baseline (F1={kf1:.3f})")
    plt.xlabel("Recall"); plt.ylabel("Precision")
    plt.title("HDFS_v1 held-out: precision-recall")
    plt.grid(alpha=0.3); plt.legend(loc="best", fontsize=8); plt.tight_layout()
    pr_png = os.path.join(RESULTS_DIR, f"hdfs_pr_curve{tag}.png")
    plt.savefig(pr_png, dpi=150); plt.close()

    grid = np.unique(np.concatenate([
        np.quantile(test_scores, np.linspace(0.0, 1.0, 600)),
        np.array([thr_sigma, thr_p95, thr_p99, thr_p999]),
    ]))
    grid = grid[grid > 0]
    sweep = []
    for t in grid:
        pr_ = (test_scores > t).astype(int)
        pp, rr, ff, _ = precision_recall_fscore_support(y_test, pr_, average="binary", zero_division=0)
        sweep.append((float(t), float(pp), float(rr), float(ff)))
    sw = np.array(sweep)

    plt.figure(figsize=(7.5, 5))
    plt.plot(sw[:, 0], sw[:, 1], label="precision")
    plt.plot(sw[:, 0], sw[:, 2], label="recall")
    plt.plot(sw[:, 0], sw[:, 3], label="F1")
    plt.axvline(thr_sigma, color="crimson", ls="--", label=f"mean+3sigma = {thr_sigma:.4f}")
    plt.axvline(thr_p99, color="seagreen", ls=":", label=f"val p99 = {thr_p99:.4f}")
    plt.xscale("log")
    plt.xlabel("Reconstruction-error threshold (log scale)"); plt.ylabel("Score")
    plt.title("HDFS_v1 held-out: threshold sweep")
    plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
    sweep_png = os.path.join(RESULTS_DIR, f"hdfs_threshold_sweep{tag}.png")
    plt.savefig(sweep_png, dpi=150); plt.close()

    best = max(sweep, key=lambda s: s[3])

    results = {
        "dataset": "LogHub HDFS_v1",
        "sequence_length": args.seq_len,
        "blocks_total": int(len(Y)),
        "blocks_anomalous": int(Y.sum()),
        "templates_discovered": blob["templates"],
        "component_to_service_id": blob["comp_to_id"],
        "unparsable_lines": int(blob["unparsed"]),
        "model_parameters": int(n_params),
        "epochs": args.epochs,
        "train_blocks": int(len(train_idx)),
        "val_blocks": int(len(val_idx)),
        "test_blocks": int(len(test_idx)),
        "test_normal": int((y_test == 0).sum()),
        "test_anomaly": int(y_test.sum()),
        "train_error_mean": mean,
        "train_error_std": std,
        "roc_auc": roc,
        "average_precision": ap_score,
        "operating_points": ops,
        "keyword_baseline": keyword,
        "best_achievable_f1_on_test": {"threshold": best[0], "precision": best[1],
                                       "recall": best[2], "f1": best[3]},
        "artifacts": {"pr_curve": os.path.relpath(pr_png, REPO),
                      "threshold_sweep": os.path.relpath(sweep_png, REPO)},
    }
    with open(os.path.join(RESULTS_DIR, f"hdfs_results{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 78)
    print(f"ROC-AUC {roc:.4f}   average precision {ap_score:.4f}   "
          f"test {int((y_test==0).sum()):,}N/{int(y_test.sum()):,}A")
    print("=" * 78)
    print(f"{'operating point':<30}{'thr':>9}{'prec':>8}{'rec':>8}{'F1':>8}{'FPR':>8}")
    print("-" * 78)
    for name, o in ops.items():
        print(f"{name:<30}{o['threshold']:>9.4f}{o['precision']:>8.3f}{o['recall']:>8.3f}"
              f"{o['f1']:>8.3f}{o['false_positive_rate']:>8.3f}")
    print(f"{'keyword baseline':<30}{'-':>9}{kp:>8.3f}{kr:>8.3f}{kf1:>8.3f}"
          f"{kcm[0,1]/max(1,kcm[0,0]+kcm[0,1]):>8.3f}")
    print("-" * 78)
    for name, o in ops.items():
        c = o["confusion_matrix"]
        print(f"{name:<30} tn={c['tn']:<7,} fp={c['fp']:<6,} fn={c['fn']:<6,} tp={c['tp']:,}")
    print(f"{'keyword baseline':<30} tn={kcm[0,0]:<7,} fp={kcm[0,1]:<6,} "
          f"fn={kcm[1,0]:<6,} tp={kcm[1,1]:,}")
    print("=" * 78)
    print(f"diagnostic only (NOT an operating point) best F1 on test = {best[3]:.4f} at thr={best[0]:.4f}")
    print(f"[done] wrote {RESULTS_DIR}")


if __name__ == "__main__":
    main()
