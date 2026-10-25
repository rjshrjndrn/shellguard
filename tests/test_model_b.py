"""Model B: frozen base model. bge-small turns a command into 384 numbers (never changed);
only a logistic regression on top is trained."""
import json

import numpy as np
import pytest

TOY = [
    ("rm -rf /", "dangerous"), ("rm -rf ~", "dangerous"), ("rm -rf /var", "dangerous"),
    ("mkfs.ext4 /dev/sda", "dangerous"), ("dd if=/dev/zero of=/dev/sdb", "dangerous"),
    ("ls -la", "safe"), ("ls /tmp", "safe"), ("cat notes.txt", "safe"),
    ("git status", "safe"), ("echo hello", "safe"),
]


def test_embeddings_run_on_cpu_only():
    # target machine may have no GPU; CoreML/CUDA must not be used even if present
    from shellguard.model_b import encoder

    assert encoder().model.model.get_providers() == ["CPUExecutionProvider"]


def test_embed_gives_384_unit_vectors():
    from shellguard.model_b import embed

    v = embed(["ls", "rm -rf /"])
    assert v.shape == (2, 384)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-3)


@pytest.fixture(scope="module")
def toy_model():
    from shellguard.model_b import train

    return train([c for c, _ in TOY], [l for _, l in TOY])


def test_learns_toy_data(toy_model):
    from shellguard.model_b import predict

    assert predict("rm -rf /home", toy_model)["label"] == "dangerous"
    assert predict("ls -la /home", toy_model)["label"] == "safe"


def test_output_shape(toy_model):
    from shellguard.model_b import predict

    out = predict("rm -rf /home", toy_model)
    assert set(out) == {"label", "danger_probability"}
    assert 0.0 <= out["danger_probability"] <= 1.0
    assert (out["label"] == "dangerous") == (out["danger_probability"] >= 0.5)


def test_save_and_load_give_identical_predictions(toy_model, tmp_path):
    from shellguard.model_b import load, predict, save

    path = tmp_path / "head.joblib"
    save(toy_model, path)
    again = load(path)
    for cmd in ("rm -rf /home", "ls", "anything at all"):
        assert predict(cmd, again) == predict(cmd, toy_model)


def test_trained_model_beats_regex_baseline():
    b = json.loads(open("results/model_b.json").read())
    base = json.loads(open("results/baseline.json").read())
    assert b["test"]["recall"] > base["test"]["recall"]
