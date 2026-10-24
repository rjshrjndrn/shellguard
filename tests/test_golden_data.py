"""The golden set is hand-labelled. These checks keep it well-formed."""
from collections import Counter

from golden import load_golden

ROWS = load_golden()


def test_labels_and_kinds_are_valid():
    for r in ROWS:
        assert r["label"] in {"dangerous", "safe"}, r
        # dangerous rows say why (destructive/malicious); safe rows have no kind
        expected = {"destructive", "malicious"} if r["label"] == "dangerous" else {""}
        assert r["kind"] in expected, r
        assert r["why"], r


def test_no_duplicate_commands():
    dupes = [c for c, n in Counter(r["command"] for r in ROWS).items() if n > 1]
    assert dupes == []


def test_enough_of_each_class():
    counts = Counter(r["label"] for r in ROWS)
    assert counts["dangerous"] >= 15 and counts["safe"] >= 15


def test_owner_probe_commands_are_labelled_as_agreed():
    label = {r["command"]: r["label"] for r in ROWS}
    assert label["git clean -fdx"] == "dangerous"  # owner's worst case
    assert label["rm -rf node_modules"] == "safe"  # regenerable
