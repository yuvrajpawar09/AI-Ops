import argparse
import json
import os
import random
import subprocess
import threading
import time
from collections import defaultdict

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

ORDER_URL = "http://localhost:8081/orders"
ADMIN_URL = "http://localhost:8081/admin/config"
ANOMALIES_URL = "http://localhost:8000/anomalies"

NORMAL = {"customerId": "bench-normal", "productId": "PROD-1", "quantity": 1, "amount": 199.0}
FAULT_ZERO = {"customerId": "bench-zero", "productId": "PROD-1", "quantity": 1, "amount": 0}
FAULT_STOCK = {"customerId": "bench-stock", "productId": "PROD-3", "quantity": 5, "amount": 99.0}
FAULT_NOTIF = {"customerId": "bench-notif", "productId": "PROD-1", "quantity": 1, "amount": 149.0}
FAULT_LAT = {"customerId": "bench-latency", "productId": "PROD-1", "quantity": 1, "amount": 179.0}


_RESTORE = True


def dc(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def restore_state():
    if not _RESTORE:
        return
    print("[restore] unpausing, resetting inventory stock, restarting rca-agent")
    dc("unpause", "inventory-service")
    dc("compose", "start", "notification-service")
    dc("compose", "restart", "inventory-service")
    dc("compose", "start", "rca-agent")
    print("[restore] demo state restored")


def post_order(payload, truth, label, lock):
    try:
        r = requests.post(ORDER_URL, json=payload, timeout=30)
        body = r.json()
    except Exception as e:
        with lock:
            truth.append({"traceId": None, "label": label, "status": f"ERROR {e}"})
        return
    with lock:
        truth.append({"traceId": body.get("traceId"), "label": label, "status": body.get("status")})


class Poller(threading.Thread):
    def __init__(self, url=ANOMALIES_URL, interval=3.0):
        super().__init__(daemon=True)
        self.url = url
        self.interval = interval
        self.flagged = {}
        self.events = {}
        self.errors = 0
        self.last_error = None
        self._stop_evt = threading.Event()

    def run(self):
        while not self._stop_evt.is_set():
            try:
                r = requests.get(self.url, params={"limit": 500}, timeout=10)
                r.raise_for_status()
                for a in r.json().get("anomalies", []):
                    self.flagged.setdefault(a["traceId"], a["score"])
                    self.events.setdefault(a["traceId"], len(a.get("events", [])))
            except Exception as e:
                self.errors += 1
                self.last_error = repr(e)
            self._stop_evt.wait(self.interval)

    def stop(self):
        self._stop_evt.set()


SERVICES = ["order-service", "payment-service", "inventory-service", "notification-service"]
IDLE_TIMEOUT = 8.0


def harvest_service_logs(trace_ids):
    counts = {t: 0 for t in trace_ids}
    keyword = {t: 0 for t in trace_ids}
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
            if t in counts:
                counts[t] += 1
                if str(p.get("level", "")).upper() in ("WARN", "ERROR"):
                    keyword[t] = 1
    return counts, keyword


def kafka_delivery(trace_ids):
    from kafka import KafkaConsumer

    wanted = set(trace_ids)
    delivered = {}
    spread = {}
    consumer = KafkaConsumer(
        "logs",
        bootstrap_servers="localhost:9092",
        group_id=f"bench-integrity-{int(time.time())}",
        auto_offset_reset="earliest",
        consumer_timeout_ms=20000,
    )
    for rec in consumer:
        try:
            p = json.loads(rec.value.decode("utf-8"))
        except Exception:
            continue
        t = p.get("traceId")
        if t not in wanted:
            continue
        delivered[t] = delivered.get(t, 0) + 1
        ts = rec.timestamp / 1000.0
        lo, hi = spread.get(t, (ts, ts))
        spread[t] = (min(lo, ts), max(hi, ts))
    consumer.close()
    return delivered, spread


def final_snapshot(url):
    try:
        r = requests.get(url, params={"limit": 500}, timeout=15)
        r.raise_for_status()
        return r.json().get("anomalies", [])
    except Exception:
        return []


def pipeline_integrity(trace_ids, detector_counts, emitted, snapshot, reopened):
    delivered, spread = kafka_delivery(trace_ids)

    complete = 0
    short_delivery = 0
    wide_spread = 0
    for t in trace_ids:
        e = emitted.get(t, 0)
        d = delivered.get(t, 0)
        lo, hi = spread.get(t, (0.0, 0.0))
        s = hi - lo
        ok_d = e > 0 and d == e
        ok_s = s < IDLE_TIMEOUT
        if ok_d and ok_s:
            complete += 1
        else:
            if not ok_d:
                short_delivery += 1
            if not ok_s:
                wide_spread += 1

    scored = [(t, detector_counts[t], emitted.get(t, 0)) for t in trace_ids if t in detector_counts]
    scored_complete = sum(1 for _, dc, em in scored if dc == em and em > 0)
    fragments = [(t, dc, em) for t, dc, em in scored if em > 0 and dc != em]
    seen = {}
    for a in snapshot:
        seen[a["traceId"]] = seen.get(a["traceId"], 0) + 1
    duplicates = {t: n for t, n in seen.items() if n > 1}
    spreads = sorted(hi - lo for lo, hi in spread.values()) or [0.0]

    return {
        "traces_checked": len(trace_ids),
        "delivery_complete": complete,
        "delivery_complete_pct": complete / max(1, len(trace_ids)),
        "incomplete_delivery": short_delivery,
        "spread_exceeds_idle_timeout": wide_spread,
        "idle_timeout_seconds": IDLE_TIMEOUT,
        "kafka_spread_seconds": {
            "median": spreads[len(spreads) // 2],
            "p95": spreads[int(len(spreads) * 0.95)] if len(spreads) > 1 else spreads[0],
            "max": spreads[-1],
        },
        "flagged_traces_cross_checked": len(scored),
        "flagged_traces_with_full_event_count": scored_complete,
        "assembly_complete_pct": (scored_complete / len(scored)) if scored else 1.0,
        "split_closures": len(fragments),
        "split_closure_examples": [{"traceId": t, "scored": dc, "emitted": em}
                                   for t, dc, em in fragments[:5]],
        "duplicate_trace_ids_in_store": len(duplicates),
        "reopened_traces_merged": reopened,
    }


def score_against(labelled, flagged):
    tp = sum(1 for t in labelled if t["label"] != "normal" and t["traceId"] in flagged)
    fn = sum(1 for t in labelled if t["label"] != "normal" and t["traceId"] not in flagged)
    fp = sum(1 for t in labelled if t["label"] == "normal" and t["traceId"] in flagged)
    tn = sum(1 for t in labelled if t["label"] == "normal" and t["traceId"] not in flagged)
    p, r, f1 = prf(tp, fp, fn)
    by = defaultdict(lambda: {"n": 0, "flagged": 0})
    for t in labelled:
        by[t["label"]]["n"] += 1
        if t["traceId"] in flagged:
            by[t["label"]]["flagged"] += 1
    return {
        "precision": p, "recall": r, "f1": f1,
        "false_positive_rate": fp / max(1, fp + tn),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "per_fault_recall": {
            k: {"n": v["n"], "flagged": v["flagged"],
                "recall": (v["flagged"] / v["n"] if v["n"] else 0.0)}
            for k, v in sorted(by.items())
        },
    }


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal", type=int, default=300)
    ap.add_argument("--per-fault", type=int, default=25)
    ap.add_argument("--settle", type=int, default=90)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-restore", action="store_true")
    ap.add_argument("--compare-url", default="")
    ap.add_argument("--label", default="v1")
    args = ap.parse_args()

    global _RESTORE
    _RESTORE = not args.no_restore

    rng = random.Random(args.seed)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    truth = []
    lock = threading.Lock()

    print("[setup] stopping rca-agent so remediation cannot alter the system mid-benchmark")
    dc("compose", "stop", "rca-agent")

    print("[setup] restarting inventory-service to reset in-memory stock")
    dc("compose", "restart", "inventory-service")

    print("[setup] restarting anomaly-detector to clear its in-memory anomaly store")
    dc("compose", "restart", "anomaly-detector")
    time.sleep(30)

    print("[setup] forcing rejectZeroAmount=false")
    try:
        requests.post(ADMIN_URL, json={"rejectZeroAmount": False}, timeout=10)
    except Exception as e:
        print(f"[warn ] could not reach admin config: {e}")

    for url in (ORDER_URL.replace("/orders", "/actuator/health"), ANOMALIES_URL):
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            raise SystemExit(f"[fatal] prerequisite not reachable: {url} ({e})")

    poller = Poller()
    poller.start()
    poller2 = None
    if args.compare_url:
        poller2 = Poller(url=args.compare_url)
        poller2.start()
        print(f"[setup] also polling comparison detector at {args.compare_url}")
    t0 = time.time()

    mixed = ([("normal", NORMAL)] * args.normal
             + [("amount_zero", FAULT_ZERO)] * args.per_fault
             + [("out_of_stock", FAULT_STOCK)] * args.per_fault)
    rng.shuffle(mixed)

    print(f"[run  ] phase 1: {len(mixed)} interleaved orders (normal + amount_zero + out_of_stock)")
    for i, (label, payload) in enumerate(mixed, 1):
        post_order(payload, truth, label, lock)
        if i % 50 == 0:
            print(f"\r        {i}/{len(mixed)}", end="", flush=True)
        time.sleep(0.05)
    print(f"\r        {len(mixed)}/{len(mixed)}")

    print(f"[run  ] phase 2: notification-service stopped, {args.per_fault} orders")
    dc("compose", "stop", "notification-service")
    time.sleep(3)
    for _ in range(args.per_fault):
        post_order(FAULT_NOTIF, truth, "notification_down", lock)
        time.sleep(0.05)
    dc("compose", "start", "notification-service")
    time.sleep(15)

    print(f"[run  ] phase 3: inventory-service latency, {args.per_fault} orders")
    batch = 5
    for start in range(0, args.per_fault, batch):
        n = min(batch, args.per_fault - start)
        dc("pause", "inventory-service")
        threads = [threading.Thread(target=post_order, args=(FAULT_LAT, truth, "inventory_latency", lock))
                   for _ in range(n)]
        for t in threads:
            t.start()
        time.sleep(2.5)
        dc("unpause", "inventory-service")
        for t in threads:
            t.join()
        time.sleep(1)

    sent = time.time() - t0
    print(f"[run  ] all orders sent in {sent:.0f}s; settling {args.settle}s for trace close + scoring")
    for remaining in range(args.settle, 0, -10):
        time.sleep(10)
        print(f"\r        {remaining-10}s left, flagged so far: {len(poller.flagged)}", end="", flush=True)
    print()
    poller.stop()
    poller.join(timeout=5)
    if poller2:
        poller2.stop()
        poller2.join(timeout=5)

    flagged = poller.flagged
    labelled = [t for t in truth if t["traceId"]]
    dropped = len(truth) - len(labelled)

    tp = sum(1 for t in labelled if t["label"] != "normal" and t["traceId"] in flagged)
    fn = sum(1 for t in labelled if t["label"] != "normal" and t["traceId"] not in flagged)
    fp = sum(1 for t in labelled if t["label"] == "normal" and t["traceId"] in flagged)
    tn = sum(1 for t in labelled if t["label"] == "normal" and t["traceId"] not in flagged)
    p, r, f1 = prf(tp, fp, fn)

    by_type = defaultdict(lambda: {"n": 0, "flagged": 0})
    for t in labelled:
        by_type[t["label"]]["n"] += 1
        if t["traceId"] in flagged:
            by_type[t["label"]]["flagged"] += 1

    status_mix = defaultdict(lambda: defaultdict(int))
    for t in labelled:
        status_mix[t["label"]][t["status"]] += 1

    print("[check] harvesting service logs for integrity check and keyword baseline")
    all_ids = [t["traceId"] for t in labelled]
    emitted, kw_flag = harvest_service_logs(all_ids)
    snapshot = final_snapshot(ANOMALIES_URL)
    try:
        reopened = requests.get("http://localhost:8000/health", timeout=10).json().get("reopenedTraces", 0)
    except Exception:
        reopened = -1
    snap_counts = {a["traceId"]: len(a.get("events", [])) for a in snapshot}
    integrity = pipeline_integrity(all_ids, snap_counts, emitted, snapshot, reopened)

    k_tp = sum(1 for t in labelled if t["label"] != "normal" and kw_flag.get(t["traceId"]))
    k_fn = sum(1 for t in labelled if t["label"] != "normal" and not kw_flag.get(t["traceId"]))
    k_fp = sum(1 for t in labelled if t["label"] == "normal" and kw_flag.get(t["traceId"]))
    k_tn = sum(1 for t in labelled if t["label"] == "normal" and not kw_flag.get(t["traceId"]))
    kp, kr, kf1 = prf(k_tp, k_fp, k_fn)
    kw_by_type = defaultdict(lambda: {"n": 0, "flagged": 0})
    for t in labelled:
        kw_by_type[t["label"]]["n"] += 1
        if kw_flag.get(t["traceId"]):
            kw_by_type[t["label"]]["flagged"] += 1

    keyword_baseline = {
        "precision": kp, "recall": kr, "f1": kf1,
        "confusion_matrix": {"tp": k_tp, "fp": k_fp, "fn": k_fn, "tn": k_tn},
        "false_positive_rate": k_fp / max(1, k_fp + k_tn),
        "per_fault_recall": {
            k: {"n": v["n"], "flagged": v["flagged"], "recall": (v["flagged"] / v["n"] if v["n"] else 0.0)}
            for k, v in sorted(kw_by_type.items())
        },
    }

    results = {
        "pipeline_integrity": integrity,
        "keyword_baseline": keyword_baseline,
        "orders_sent": len(truth),
        "orders_with_traceid": len(labelled),
        "orders_dropped": dropped,
        "flagged_traces_total": len(flagged),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": p,
        "recall": r,
        "f1": f1,
        "per_fault_recall": {
            k: {"n": v["n"], "flagged": v["flagged"], "recall": (v["flagged"] / v["n"] if v["n"] else 0.0)}
            for k, v in sorted(by_type.items())
        },
        "status_mix": {k: dict(v) for k, v in sorted(status_mix.items())},
        "settle_seconds": args.settle,
        "seed": args.seed,
    }

    with open(os.path.join(RESULTS_DIR, "fault_injection_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 64)
    pct = integrity["delivery_complete_pct"]
    verdict = "PASS" if pct >= 0.99 else "FAIL"
    print(f"PIPELINE INTEGRITY : {integrity['delivery_complete']}/{integrity['traces_checked']} "
          f"complete = {pct:.3%}  [{verdict}, criterion >=99%]")
    print(f"  incomplete delivery      : {integrity['incomplete_delivery']}")
    print(f"  kafka spread > {IDLE_TIMEOUT}s idle : {integrity['spread_exceeds_idle_timeout']}")
    ks = integrity["kafka_spread_seconds"]
    print(f"  kafka arrival spread     : median={ks['median']:.2f}s p95={ks['p95']:.2f}s max={ks['max']:.2f}s")
    print(f"  assembly complete         : "
          f"{integrity['flagged_traces_with_full_event_count']}/{integrity['flagged_traces_cross_checked']} "
          f"= {integrity['assembly_complete_pct']:.3%}")
    sc = integrity["split_closures"]
    print(f"  SPLIT CLOSURES            : {sc}  [{'PASS' if sc == 0 else 'FAIL'}, require 0]")
    print(f"  duplicate traceIds stored : {integrity['duplicate_trace_ids_in_store']}")
    print(f"  late lines merged (grace) : {integrity['reopened_traces_merged']}")
    if integrity["split_closure_examples"]:
        print(f"  examples: {integrity['split_closure_examples']}")
    print("=" * 64)
    print(f"orders sent        : {len(truth)} ({dropped} without traceId)")
    print(f"flagged traces     : {len(flagged)}")
    print(f"confusion          : tp={tp} fp={fp} fn={fn} tn={tn}")
    print(f"precision          : {p:.4f}")
    print(f"recall             : {r:.4f}")
    print(f"F1                 : {f1:.4f}")
    print("-" * 64)
    print(f"{'':<22}{'':>6}{'LSTM':>20}{'KEYWORD':>20}")
    print(f"{'fault type':<22}{'n':>6}{'flagged':>10}{'recall':>10}{'flagged':>10}{'recall':>10}")
    kwr = keyword_baseline["per_fault_recall"]
    for k, v in results["per_fault_recall"].items():
        w = kwr.get(k, {"flagged": 0, "recall": 0.0})
        print(f"{k:<22}{v['n']:>6}{v['flagged']:>10}{v['recall']:>10.3f}"
              f"{w['flagged']:>10}{w['recall']:>10.3f}")
    print("-" * 64)
    print(f"{'overall':<22}{'':>6}{'LSTM':>20}{'KEYWORD':>20}")
    print(f"{'  precision':<28}{p:>14.4f}{kp:>20.4f}")
    print(f"{'  recall':<28}{r:>14.4f}{kr:>20.4f}")
    print(f"{'  F1':<28}{f1:>14.4f}{kf1:>20.4f}")
    print(f"{'  false-positive rate':<28}{fp/max(1,fp+tn):>14.4f}"
          f"{keyword_baseline['false_positive_rate']:>20.4f}")
    print("=" * 64)
    for k, v in results["status_mix"].items():
        print(f"{k:<22}{dict(v)}")

    if poller2:
        v2 = score_against(labelled, poller2.flagged)
        results["comparison_detector"] = {"url": args.compare_url, **v2}
        with open(os.path.join(RESULTS_DIR, "fault_injection_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print()
        print("=" * 72)
        print("SIDE BY SIDE          v1 (shipped)        v2 (log-time+duration)      keyword")
        print("-" * 72)
        rows = [("precision", p, v2["precision"], kp),
                ("recall", r, v2["recall"], kr),
                ("F1", f1, v2["f1"], kf1),
                ("FPR", fp / max(1, fp + tn), v2["false_positive_rate"],
                 keyword_baseline["false_positive_rate"])]
        for name, a, b, c in rows:
            print(f"{name:<18}{a:>14.4f}{b:>22.4f}{c:>17.4f}")
        print("-" * 72)
        print(f"{'per-fault recall':<18}{'v1':>14}{'v2':>22}{'keyword':>17}")
        for k in sorted(results["per_fault_recall"]):
            a = results["per_fault_recall"][k]["recall"]
            b = v2["per_fault_recall"].get(k, {"recall": 0.0})["recall"]
            c = keyword_baseline["per_fault_recall"].get(k, {"recall": 0.0})["recall"]
            print(f"{k:<18}{a:>14.3f}{b:>22.3f}{c:>17.3f}")
        print("=" * 72)
        cm = v2["confusion_matrix"]
        print(f"v2 confusion: tp={cm['tp']} fp={cm['fp']} fn={cm['fn']} tn={cm['tn']}")

    restore_state()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback

        traceback.print_exc()
        restore_state()
        raise
