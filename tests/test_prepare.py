"""Step 3: raw parquet -> one row per command, labelled, split 80/20.

Output: train.parquet and test.parquet with columns
  command (str), label ("dangerous" | "safe"), categories (list[str])
"""
import duckdb
import pytest

from golden import load_golden


@pytest.fixture(scope="module")
def split(tmp_path_factory):
    from shellguard.prepare import prepare

    out = tmp_path_factory.mktemp("prepared")
    prepare(out_dir=out)
    load = lambda name: duckdb.read_parquet(str(out / name)).fetchdf()
    return load("train.parquet"), load("test.parquet")


def test_columns(split):
    train, _ = split
    assert list(train.columns) == ["command", "label", "categories"]
    assert set(train.label) == {"dangerous", "safe"}


def test_one_row_per_command(split):
    train, test = split
    for df in (train, test):
        assert not df.command.duplicated().any()


def test_train_and_test_share_no_command(split):
    train, test = split
    assert set(train.command).isdisjoint(test.command)


def test_golden_commands_are_never_in_train_or_test(split):
    # golden is the final exam; 16 of its commands appear verbatim in the dataset
    train, test = split
    golden = {r["command"] for r in load_golden()}
    assert golden.isdisjoint(train.command)
    assert golden.isdisjoint(test.command)


def test_all_remaining_commands_are_kept(split):
    train, test = split
    assert len(train) + len(test) == 28_296 - 16  # distinct commands minus golden overlap


def test_test_is_20_percent_and_stratified(split):
    train, test = split
    assert len(test) / (len(train) + len(test)) == pytest.approx(0.20, abs=0.001)
    rate = lambda df: (df.label == "dangerous").mean()
    assert rate(train) == pytest.approx(rate(test), abs=0.005)


@pytest.mark.parametrize(
    "command, expected",
    [
        ("sudo usermod --append --groups wheel admin", "dangerous"),  # high but reversible
        ("rm -rf /tmp/*", "dangerous"),  # low/moderate but irreversible
        ("chmod +s /bin/bash", "dangerous"),  # copies disagree on reversible
        ("sudo ls --version ./.cache", "safe"),  # safe + reversible
    ],
)
def test_label_rule(split, command, expected):
    labels = {c: l for df in split for c, l in zip(df.command, df.label)}
    assert labels[command] == expected


def test_split_is_repeatable(tmp_path):
    from shellguard.prepare import prepare

    a, b = tmp_path / "a", tmp_path / "b"
    prepare(out_dir=a)
    prepare(out_dir=b)
    for name in ("train.parquet", "test.parquet"):
        cmds = lambda d: duckdb.read_parquet(str(d / name)).fetchdf().command.tolist()
        assert cmds(a) == cmds(b)
