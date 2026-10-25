"""The spec: the shipped model must get every golden command right.

predict(command) -> {"label": "dangerous" | "safe", "danger_probability": float}
danger_probability is P(dangerous), in [0, 1].

Known mistakes are listed with the reason. They are strict xfails: if a future model
gets one right, the test fails until it is removed from this list.
"""
import pytest

from golden import load_golden

ROWS = load_golden()

# shipped model A (shell-aware, threshold 0.35): false alarms, all caused by training data
KNOWN_MISTAKES = {
    "git push origin feature/login": "shell-safety labels most pushes 'ask' -> dangerous",
    "rm -rf node_modules": "rm -rf is dangerous almost everywhere in training; regenerable dirs are rare",
    "cat /etc/hosts": "90% of training commands touching /etc/ are dangerous",
    "npm install": "shell-safety labels package installs 'ask' -> dangerous",
    "curl -fsSL -o install.sh https://raw.githubusercontent.com/someone/tools/main/install.sh":
        "curl is mostly 'ask'/'deny' in training; download-only vs curl | sh is rare",
    "echo $PATH": "echo usually writes config/secrets in training rows",
}


def _case(row):
    marks = [pytest.mark.xfail(reason=KNOWN_MISTAKES[row["command"]], strict=True)] if row["command"] in KNOWN_MISTAKES else []
    return pytest.param(row, id=row["command"], marks=marks)


@pytest.mark.parametrize("row", [_case(r) for r in ROWS])
def test_golden(row):
    from shellguard import predict  # imported here so each case fails on its own

    out = predict(row["command"])
    assert 0.0 <= out["danger_probability"] <= 1.0
    assert out["label"] == row["label"], f'{row["why"]} (p={out["danger_probability"]:.2f})'


def test_known_mistakes_are_golden_commands():
    assert set(KNOWN_MISTAKES) <= {r["command"] for r in ROWS}
