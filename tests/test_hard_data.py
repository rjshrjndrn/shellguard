"""The hard set: indirect/obfuscated dangerous commands plus safe lookalikes.
A second exam, never trained on, reported next to golden."""
from collections import Counter

from golden import load_golden, load_hard

ROWS = load_hard()


def test_labels_are_valid_and_kinds_present():
    for r in ROWS:
        assert r["label"] in {"dangerous", "safe"}, r
        assert r["kind"], r


def test_size_and_balance():
    assert Counter(r["label"] for r in ROWS) == {"dangerous": 42, "safe": 13}


def test_no_duplicates_and_no_overlap_with_golden():
    cmds = [r["command"] for r in ROWS]
    assert len(cmds) == len(set(cmds))
    assert set(cmds).isdisjoint(r["command"] for r in load_golden())


def test_agreed_edge_labels():
    label = {r["command"]: r["label"] for r in ROWS}
    assert label["git branch -D main"] == "dangerous"  # owner: deleting a branch counts
    assert label["grep -rn \"rm -rf\" scripts/"] == "safe"  # mentioning is not running
