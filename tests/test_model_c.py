"""Model C: fine-tuned base model. bge-small's own 33M weights are adjusted on our data
(training may use the M1 GPU), then exported to ONNX so inference is CPU-only, no PyTorch."""
import json
import subprocess
import sys

import pytest

TOY = [
    ("rm -rf /", "dangerous"), ("rm -rf ~", "dangerous"), ("rm -rf /var", "dangerous"),
    ("mkfs.ext4 /dev/sda", "dangerous"), ("dd if=/dev/zero of=/dev/sdb", "dangerous"),
    ("ls -la", "safe"), ("ls /tmp", "safe"), ("cat notes.txt", "safe"),
    ("git status", "safe"), ("echo hello", "safe"),
]


@pytest.fixture(scope="module")
def toy_export(tmp_path_factory):
    """Fine-tune on the toy set, export to ONNX; return (torch model, tokenizer, export dir)."""
    from shellguard.model_c import export, finetune

    model, tok = finetune([c for c, _ in TOY], [l for _, l in TOY], epochs=15, lr=1e-4, batch_size=10)
    out = tmp_path_factory.mktemp("model_c")
    export(model, tok, out)
    return model, tok, out


def test_export_writes_onnx_and_tokenizer(toy_export):
    _, _, out = toy_export
    assert (out / "model.onnx").exists() and (out / "tokenizer.json").exists()


def test_learns_toy_data(toy_export):
    from shellguard.model_c import load, predict

    m = load(toy_export[2])
    assert predict("rm -rf /home", m)["label"] == "dangerous"
    assert predict("ls -la /home", m)["label"] == "safe"


def test_onnx_matches_pytorch(toy_export):
    # the exported file must compute the same thing as the model we trained
    import torch

    from shellguard.model_c import load, predict

    model, tok, out = toy_export
    m = load(out)
    for cmd in ("rm -rf /home", "ls", "git clean -fdx"):
        with torch.no_grad():
            logits = model(**tok(cmd, return_tensors="pt")).logits
        p_torch = torch.softmax(logits, -1)[0, 1].item()
        assert predict(cmd, m)["probability"] == pytest.approx(p_torch, abs=1e-4)


def test_onnx_runs_on_cpu_only(toy_export):
    from shellguard.model_c import load

    session, _ = load(toy_export[2])
    assert session.get_providers() == ["CPUExecutionProvider"]


def test_output_shape(toy_export):
    from shellguard.model_c import load, predict

    out = predict("rm -rf /home", load(toy_export[2]))
    assert set(out) == {"label", "probability"}
    assert 0.0 <= out["probability"] <= 1.0
    assert (out["label"] == "dangerous") == (out["probability"] >= 0.5)


def test_inference_does_not_need_pytorch(toy_export):
    code = (
        "import sys; from shellguard.model_c import load, predict; "
        f"predict('ls', load({str(toy_export[2])!r})); "
        "assert 'torch' not in sys.modules and 'transformers' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_trained_model_beats_regex_baseline():
    c = json.loads(open("results/model_c.json").read())
    base = json.loads(open("results/baseline.json").read())
    assert c["test"]["recall"] > base["test"]["recall"]
