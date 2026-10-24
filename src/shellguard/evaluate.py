"""Score a model on the test split and both exams (golden, hard); write results/<name>.json."""
import importlib
import json
import sys
import time
from pathlib import Path

import duckdb

from shellguard.data import ROOT
from shellguard.prepare import GOLDEN, HARD, OUT_DIR, load_csv

RESULTS_DIR = ROOT / "results"  # committed, so models can be compared over time


def score(truth: list[str], preds: list[str]) -> dict:
    pairs = list(zip(truth, preds))
    tp = sum(t == p == "dangerous" for t, p in pairs)
    fn = sum(t == "dangerous" != p for t, p in pairs)
    fp = sum(p == "dangerous" != t for t, p in pairs)
    tn = len(pairs) - tp - fn - fp
    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"n": len(pairs), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "recall": recall, "precision": precision, "f1": f1, "accuracy": (tp + tn) / len(pairs)}


def run(name: str, out_dir: Path = RESULTS_DIR) -> dict:
    predict = importlib.import_module(f"shellguard.{name}").predict
    test = duckdb.read_parquet(str(OUT_DIR / "test.parquet")).fetchdf()

    start = time.perf_counter()
    test_preds = [predict(c)["label"] for c in test.command]
    us = 1e6 * (time.perf_counter() - start) / len(test)

    result = {
        "model": name,
        "test": score(test.label.tolist(), test_preds),
        "us_per_command": us,
    }
    for exam, path in (("golden", GOLDEN), ("hard", HARD)):
        rows = load_csv(path)
        preds = [predict(r["command"])["label"] for r in rows]
        result[exam] = score([r["label"] for r in rows], preds)
        result[f"{exam}_misses"] = [r["command"] for r, p in zip(rows, preds) if p != r["label"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    r = run(sys.argv[1])
    for split in ("test", "golden", "hard"):
        s = r[split]
        print(f"{split:6} n={s['n']:5}  recall={s['recall']:.3f}  precision={s['precision']:.3f}  "
              f"f1={s['f1']:.3f}  missed={s['fn']}  false_alarms={s['fp']}")
    print(f"speed  {r['us_per_command']:.1f} µs/command")
    for exam in ("golden", "hard"):
        print(f"{exam} wrong:", *r[f"{exam}_misses"], sep="\n  ")
