"""Model C - fine-tuned base model. Unlike B, bge-small's own 33M weights change.

  TRAIN (torch, M1 GPU allowed)                 RUN (CPU only, no torch)
  bge-small + 2-way classification layer   ──▶  models/model_c/model.onnx
  every weight nudged by our 22,624 commands     + tokenizer.json
                                                 onnxruntime -> P(dangerous)

Training-only imports (torch, transformers) live inside finetune()/export() so
predict() needs just onnxruntime + tokenizers.
"""
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from shellguard.data import ROOT

BASE_MODEL = "BAAI/bge-small-en-v1.5"
MODEL_DIR = ROOT / "models" / "model_c"
MAX_TOKENS = 64  # p99 of train commands is 40 tokens
LABELS = ["safe", "dangerous"]  # index 1 = dangerous
_loaded = None


def finetune(commands, labels, epochs=2, lr=5e-5, batch_size=32, seed=42, log=None):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    torch.manual_seed(seed)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL, num_labels=2, id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)}
    ).to(device)

    y = torch.tensor([LABELS.index(l) for l in labels])
    steps = epochs * -(-len(commands) // batch_size)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, num_warmup_steps=steps // 10, num_training_steps=steps)

    model.train()
    for epoch in range(epochs):
        order = torch.randperm(len(commands))
        for i in range(0, len(commands), batch_size):
            idx = order[i : i + batch_size]
            # fixed length = one tensor shape; varying shapes made MPS memory grow until it swapped on 8 GB
            batch = tok([commands[j] for j in idx], padding="max_length", truncation=True,
                        max_length=MAX_TOKENS, return_tensors="pt").to(device)
            loss = model(**batch, labels=y[idx].to(device)).loss
            loss.backward()
            opt.step(); sched.step(); opt.zero_grad()
            if log and (i // batch_size) % 100 == 0:
                mem = f" mps_mem {torch.mps.driver_allocated_memory() / 1e9:.2f}GB" if device == "mps" else ""
                log(f"epoch {epoch + 1}/{epochs} step {i // batch_size} loss {loss.item():.4f}{mem}")
    return model.to("cpu").eval(), tok


def export(model, tok, out_dir: Path = MODEL_DIR) -> None:
    import torch

    out_dir.mkdir(parents=True, exist_ok=True)
    tok.backend_tokenizer.save(str(out_dir / "tokenizer.json"))
    sample = tok(["git clean -fdx", "ls"], padding=True, return_tensors="pt")
    batch, seq = torch.export.Dim("batch"), torch.export.Dim("seq")
    torch.onnx.export(
        model, (), kwargs={"input_ids": sample["input_ids"], "attention_mask": sample["attention_mask"]},
        f=str(out_dir / "model.onnx"), input_names=["input_ids", "attention_mask"], output_names=["logits"],
        dynamic_shapes={"input_ids": {0: batch, 1: seq}, "attention_mask": {0: batch, 1: seq}},
        dynamo=True, external_data=False,
    )


def load(model_dir: Path | str = MODEL_DIR):
    model_dir = Path(model_dir)
    session = ort.InferenceSession(str(model_dir / "model.onnx"), providers=["CPUExecutionProvider"])
    tok = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    tok.enable_truncation(MAX_TOKENS)
    return session, tok


def predict(command: str, loaded=None) -> dict:
    global _loaded
    if loaded is None:
        loaded = _loaded = _loaded or load()
    session, tok = loaded
    enc = tok.encode(command)
    feeds = {"input_ids": np.array([enc.ids], dtype=np.int64),
             "attention_mask": np.array([enc.attention_mask], dtype=np.int64)}
    logits = session.run(["logits"], feeds)[0][0]
    e = np.exp(logits - logits.max())
    p = float(e[1] / e.sum())
    return {"label": "dangerous" if p >= 0.5 else "safe", "probability": p}


if __name__ == "__main__":
    import time

    import duckdb

    from shellguard.prepare import OUT_DIR

    df = duckdb.read_parquet(str(OUT_DIR / "train.parquet")).fetchdf()
    start = time.perf_counter()
    model, tok = finetune(df.command.tolist(), df.label.tolist(), log=print)
    print(f"fine-tuned on {len(df)} commands in {time.perf_counter() - start:.0f}s")
    export(model, tok)
    size = (MODEL_DIR / "model.onnx").stat().st_size / 1e6
    print(f"exported -> {MODEL_DIR}/model.onnx ({size:.0f} MB) + tokenizer.json")
