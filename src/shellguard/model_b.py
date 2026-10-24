"""Model B - frozen base model. A pretrained encoder turns text into meaning-numbers;
we never change it, we only train a small classifier on top.

  "git clean -fdx" -> bge-small (33M params, frozen, ONNX on CPU) -> 384 numbers
                   -> LogisticRegression (384 weights, trained by us) -> P(dangerous)
"""
from functools import cache
from pathlib import Path

import duckdb
import joblib
import numpy as np
from fastembed import TextEmbedding
from sklearn.linear_model import LogisticRegression

from shellguard.data import ROOT
from shellguard.prepare import OUT_DIR

BASE_MODEL = "BAAI/bge-small-en-v1.5"
CACHE_DIR = ROOT / "models" / "fastembed"  # base model downloaded here once (64 MB)
HEAD_PATH = ROOT / "models" / "model_b_head.joblib"
_head: LogisticRegression | None = None


@cache
def encoder() -> TextEmbedding:
    return TextEmbedding(BASE_MODEL, cache_dir=str(CACHE_DIR), providers=["CPUExecutionProvider"])


def embed(commands: list[str]) -> np.ndarray:
    return np.array(list(encoder().embed(commands, batch_size=256)))


def train(commands: list[str], labels: list[str]) -> LogisticRegression:
    return LogisticRegression(max_iter=1000).fit(embed(commands), labels)


def save(head: LogisticRegression, path: Path = HEAD_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(head, path)  # pickle-based: only load files you built yourself


def load(path: Path = HEAD_PATH) -> LogisticRegression:
    return joblib.load(path)


def predict(command: str, head: LogisticRegression | None = None) -> dict:
    global _head
    if head is None:
        head = _head = _head or load()
    p = float(head.predict_proba(embed([command]))[0][list(head.classes_).index("dangerous")])
    return {"label": "dangerous" if p >= 0.5 else "safe", "probability": p}


if __name__ == "__main__":
    import time

    df = duckdb.read_parquet(str(OUT_DIR / "train.parquet")).fetchdf()
    start = time.perf_counter()
    head = train(df.command.tolist(), df.label.tolist())
    save(head)
    print(f"trained on {len(df)} commands in {time.perf_counter() - start:.0f}s -> {HEAD_PATH} "
          f"({HEAD_PATH.stat().st_size / 1e3:.0f} KB head + 64 MB frozen base model)")
