"""The spec: the shipped model must get every golden command right.

predict(command) -> {"label": "dangerous" | "safe", "probability": float}
probability is P(dangerous), in [0, 1].
"""
import pytest

from golden import load_golden

ROWS = load_golden()


@pytest.mark.parametrize("row", ROWS, ids=[r["command"] for r in ROWS])
def test_golden(row):
    from shellguard import predict  # imported here so each case fails on its own

    out = predict(row["command"])
    assert 0.0 <= out["probability"] <= 1.0
    assert out["label"] == row["label"], f'{row["why"]} (p={out["probability"]:.2f})'
