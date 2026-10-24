"""Model A: no base model. Char n-gram TF-IDF + logistic regression, trained from scratch."""
import json

import pytest

TOY = [
    ("rm -rf /", "dangerous"), ("rm -rf ~", "dangerous"), ("rm -rf /var", "dangerous"),
    ("mkfs.ext4 /dev/sda", "dangerous"), ("dd if=/dev/zero of=/dev/sdb", "dangerous"),
    ("ls -la", "safe"), ("ls /tmp", "safe"), ("cat notes.txt", "safe"),
    ("git status", "safe"), ("echo hello", "safe"),
]


@pytest.fixture(scope="module")
def toy_model():
    from shellguard.model_a import train

    return train([c for c, _ in TOY], [l for _, l in TOY])


def test_learns_toy_data(toy_model):
    from shellguard.model_a import predict

    assert predict("rm -rf /home", toy_model)["label"] == "dangerous"
    assert predict("ls -la /home", toy_model)["label"] == "safe"


def test_output_shape(toy_model):
    from shellguard.model_a import THRESHOLD, predict

    out = predict("rm -rf /home", toy_model)
    assert set(out) == {"label", "probability"}
    assert 0.0 <= out["probability"] <= 1.0
    assert (out["label"] == "dangerous") == (out["probability"] >= THRESHOLD)


def test_threshold_is_the_one_picked_in_step_8():
    # 0.35: from out-of-fold train predictions; first value catching every dangerous exam command
    from shellguard.model_a import THRESHOLD

    assert THRESHOLD == 0.35


def test_unsure_commands_are_flagged(toy_model):
    # owner: in doubt, dangerous. A probability between 0.35 and 0.5 must say dangerous.
    from shellguard.model_a import predict

    unsure = [c for c in ("rm notes", "ls -rf", "cat /dev/sda", "rm", "ls /dev") if 0.35 <= predict(c, toy_model)["probability"] < 0.5]
    assert unsure, "toy model gave no probability in [0.35, 0.5) - pick other probes"
    assert all(predict(c, toy_model)["label"] == "dangerous" for c in unsure)


def test_case_matters():
    # git branch -D force-deletes, -d refuses on unmerged work; lowercasing would merge them
    from shellguard.model_a import predict, train

    m = train([f"git branch -D {b}" for b in "abc"] + [f"git branch -d {b}" for b in "abc"],
              ["dangerous"] * 3 + ["safe"] * 3)
    assert predict("git branch -D z", m)["label"] == "dangerous"
    assert predict("git branch -d z", m)["label"] == "safe"


def test_save_and_load_give_identical_predictions(toy_model, tmp_path):
    from shellguard.model_a import load, predict, save

    path = tmp_path / "m.joblib"
    save(toy_model, path)
    again = load(path)
    for cmd in ("rm -rf /home", "ls", "anything at all"):
        assert predict(cmd, again) == predict(cmd, toy_model)


def test_trained_model_beats_regex_baseline():
    # success criterion: higher recall on dangerous than the regex floor (from committed results)
    a = json.loads(open("results/model_a.json").read())
    base = json.loads(open("results/baseline.json").read())
    assert a["test"]["recall"] > base["test"]["recall"]
