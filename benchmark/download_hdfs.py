import argparse
import csv
import io
import json
import os
import random
import sys
import zipfile
from urllib.request import urlopen

DATA_URL = "https://zenodo.org/records/8196385/files/HDFS_v1.zip"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ZIP_PATH = os.path.join(DATA_DIR, "HDFS_v1.zip")
CACHE_PATH = os.path.join(DATA_DIR, "hdfs_subsample.jsonl")
META_PATH = os.path.join(DATA_DIR, "hdfs_subsample_meta.json")

BLOCK_RE = __import__("re").compile(r"blk_-?\d+")


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000_000:
        print(f"[skip] {dest} already present ({os.path.getsize(dest):,} bytes)")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"[get ] {url}")
    tmp = dest + ".part"
    with urlopen(url) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            pct = (done / total * 100) if total else 0
            print(f"\r       {done/1e6:,.0f} / {total/1e6:,.0f} MB ({pct:.1f}%)", end="", flush=True)
    print()
    os.replace(tmp, dest)


def find_member(zf, suffix):
    for name in zf.namelist():
        if name.endswith(suffix):
            return name
    raise SystemExit(f"member ending in {suffix!r} not found; have: {zf.namelist()[:20]}")


def load_labels(zf):
    name = find_member(zf, "anomaly_label.csv")
    labels = {}
    with zf.open(name) as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"))
        header = next(reader)
        for row in reader:
            if len(row) < 2:
                continue
            labels[row[0]] = 1 if row[1].strip().lower().startswith("anom") else 0
    return labels


def choose_blocks(labels, n_blocks, seed):
    rng = random.Random(seed)
    normal = [b for b, y in labels.items() if y == 0]
    anomaly = [b for b, y in labels.items() if y == 1]
    ratio = len(anomaly) / len(labels)
    n_anom = max(1, round(n_blocks * ratio))
    n_norm = n_blocks - n_anom
    rng.shuffle(normal)
    rng.shuffle(anomaly)
    chosen = set(normal[:n_norm]) | set(anomaly[:n_anom])
    return chosen, ratio, n_norm, n_anom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if os.path.exists(CACHE_PATH) and not args.force:
        print(f"[skip] cache exists: {CACHE_PATH}")
        return

    download(DATA_URL, ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH) as zf:
        print("[meta] members:", [n for n in zf.namelist()][:10])
        labels = load_labels(zf)
        print(f"[meta] labelled blocks: {len(labels):,}  anomalies: {sum(labels.values()):,}")

        chosen, ratio, n_norm, n_anom = choose_blocks(labels, args.blocks, args.seed)
        print(f"[meta] natural anomaly ratio: {ratio:.4%}")
        print(f"[meta] sampling {len(chosen):,} blocks ({n_norm:,} normal / {n_anom:,} anomaly)")

        log_name = find_member(zf, "HDFS.log")
        buckets = {b: [] for b in chosen}
        kept = 0
        seen = 0
        with zf.open(log_name) as raw:
            stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
            for line in stream:
                seen += 1
                if seen % 2_000_000 == 0:
                    print(f"\r       scanned {seen:,} lines, kept {kept:,}", end="", flush=True)
                ids = BLOCK_RE.findall(line)
                if not ids:
                    continue
                line = line.rstrip("\n")
                for b in set(ids):
                    bucket = buckets.get(b)
                    if bucket is not None:
                        bucket.append(line)
                        kept += 1
        print(f"\r       scanned {seen:,} lines, kept {kept:,}")

    empty = [b for b, v in buckets.items() if not v]
    for b in empty:
        del buckets[b]
    print(f"[meta] blocks with >=1 line: {len(buckets):,} (dropped {len(empty):,} empty)")

    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = CACHE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as out:
        for b, lines in buckets.items():
            out.write(json.dumps({"block_id": b, "label": labels[b], "lines": lines}) + "\n")
    os.replace(tmp, CACHE_PATH)

    meta = {
        "source_url": DATA_URL,
        "requested_blocks": args.blocks,
        "seed": args.seed,
        "total_labelled_blocks": len(labels),
        "total_anomalies": sum(labels.values()),
        "natural_anomaly_ratio": ratio,
        "sampled_blocks": len(buckets),
        "sampled_anomalies": sum(labels[b] for b in buckets),
        "total_lines_kept": kept,
        "source_lines_scanned": seen,
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[done] cache -> {CACHE_PATH} ({os.path.getsize(CACHE_PATH)/1e6:,.0f} MB)")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
