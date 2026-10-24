"""Scoring: every model is judged by the same numbers. 'dangerous' is the positive class."""
import json

import pytest


def test_score_counts_and_rates():
    from shellguard.evaluate import score

    truth = ["dangerous", "dangerous", "dangerous", "safe", "safe"]
    preds = ["dangerous", "dangerous", "safe", "safe", "dangerous"]
    s = score(truth, preds)
    assert (s["tp"], s["fn"], s["fp"], s["tn"]) == (2, 1, 1, 1)
    assert s["recall"] == pytest.approx(2 / 3)  # caught 2 of 3 dangerous
    assert s["precision"] == pytest.approx(2 / 3)  # 2 of 3 flags were right
    assert s["f1"] == pytest.approx(2 / 3)
    assert s["accuracy"] == pytest.approx(3 / 5)


def test_score_with_no_flags_has_zero_recall_not_crash():
    from shellguard.evaluate import score

    s = score(["dangerous", "safe"], ["safe", "safe"])
    assert s["recall"] == 0 and s["precision"] == 0


def test_run_writes_results_for_test_split_and_golden(tmp_path):
    from shellguard.evaluate import run

    run("baseline", out_dir=tmp_path)
    result = json.loads((tmp_path / "baseline.json").read_text())
    for split in ("test", "golden"):
        assert 0 <= result[split]["recall"] <= 1
    assert result["golden"]["n"] == 48
    assert result["us_per_command"] > 0
