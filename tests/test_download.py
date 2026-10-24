"""Step 2: `make data` must leave both pinned datasets in data/raw/<name>/, byte-for-byte."""
import hashlib

import duckdb
import pytest

# sha256 per file at the pinned HF commits. cli-command-risk: from the HF API (lfs.oid).
# shell-safety: only train.jsonl is LFS on HF; the other two were hashed at first download.
EXPECTED_SHA256 = {
    ("cli-command-risk", "train.parquet"): "c83a3bdfa95723f241f5106571653bf127b265a2826f007b8983329d74eb6b25",
    ("cli-command-risk", "validation.parquet"): "a9015b5fa10b430c05106cc822371e5b66e86c66b45d9f64ddd8ab3c420d0c2d",
    ("cli-command-risk", "test.parquet"): "b4e8335f2037b1b8af8f9e909f90922fc53638b233f530bbebea1dfc39b9e515",
    ("shell-safety", "train.jsonl"): "698e5ba9cf4984d4fcd845f997e63a8a971ceea71a3b22dcf257379d6e0972ef",
    ("shell-safety", "validation.jsonl"): "ebb74c92b5b879d06af75d2cb456feb0f314c2ae270eb9aa79353c67f364e830",
    ("shell-safety", "test.jsonl"): "23b5c0d32e2d558550b14885580194d3dbb9c4f6810acab14e03d9cdfaa341e8",
}


@pytest.mark.parametrize("dataset, name", EXPECTED_SHA256, ids=[f"{d}/{n}" for d, n in EXPECTED_SHA256])
def test_raw_files_match_pinned_hashes(dataset, name):
    from shellguard.data import RAW_DIR

    path = RAW_DIR / dataset / name
    assert path.exists(), f"{path} missing - run `make data`"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256[(dataset, name)]


def test_cli_command_risk_columns_and_rows():
    from shellguard.data import RAW_DIR

    rel = duckdb.read_parquet(str(RAW_DIR / "cli-command-risk" / "*.parquet"))
    assert {"command", "risk_level", "reversible", "risk_categories"} <= set(rel.columns)
    # measured from the pinned files; the dataset card's 124,923 is stale
    assert rel.count("*").fetchall()[0][0] == 136_497


def test_shell_safety_columns_and_rows():
    from shellguard.data import RAW_DIR

    rows = duckdb.sql(
        f"SELECT label, count(*) FROM read_json('{RAW_DIR / 'shell-safety' / '*.jsonl'}') GROUP BY ALL"
    ).fetchall()
    assert dict(rows) == {"allow": 13_600, "ask": 12_509, "deny": 7_898}
