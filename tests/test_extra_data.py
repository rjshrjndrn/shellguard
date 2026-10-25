"""Hand-written training rows (data/extra.csv) that break token shortcuts the raw
datasets taught model A: ~/ and 2>&1 appear mostly in dangerous rows there, so the
model scored them as danger whatever the verb. Rows come in twins sharing those
tokens, so the model has to learn the verb, not "~/ = safe" instead."""
from collections import Counter

import duckdb
import pytest

from golden import DATA, load_golden, load_hard


def load_extra() -> list[dict]:
    import csv

    with (DATA / "extra.csv").open(newline="") as f:
        return list(csv.DictReader(f))


ROWS = load_extra()


def test_columns_and_labels():
    assert ROWS and set(ROWS[0]) == {"command", "label"}
    assert {r["label"] for r in ROWS} == {"dangerous", "safe"}


def test_no_duplicates():
    cmds = [r["command"] for r in ROWS]
    assert len(cmds) == len(set(cmds))


def test_never_an_exam_command():
    exams = {r["command"] for r in load_golden() + load_hard()}
    assert exams.isdisjoint(r["command"] for r in ROWS)


def test_not_already_in_raw_data():
    # a clash would be relabelled by "most dangerous copy wins" and silently undo the row
    from shellguard.data import RAW_DIR

    raw = {c for (c,) in duckdb.sql(
        f"SELECT command FROM read_parquet('{RAW_DIR}/cli-command-risk/*.parquet') "
        f"UNION SELECT command FROM read_json('{RAW_DIR}/shell-safety/*.jsonl')").fetchall()}
    assert raw.isdisjoint(r["command"] for r in ROWS)


@pytest.mark.parametrize("token", ["~/", "2>&1", "2>/dev/null"])
def test_each_token_appears_on_both_sides(token):
    # one-sided rows would just flip the shortcut ("~/ = safe")
    labels = Counter(r["label"] for r in ROWS if token in r["command"])
    assert labels["safe"] >= 10 and labels["dangerous"] >= 10, labels
