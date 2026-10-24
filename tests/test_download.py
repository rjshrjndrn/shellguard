"""Step 2: `make data` must leave the pinned dataset in data/raw/, byte-for-byte."""
import hashlib

import duckdb

# sha256 of each file at HF commit 5e1283e, from the HF API (lfs.oid)
EXPECTED_SHA256 = {
    "train.parquet": "c83a3bdfa95723f241f5106571653bf127b265a2826f007b8983329d74eb6b25",
    "validation.parquet": "a9015b5fa10b430c05106cc822371e5b66e86c66b45d9f64ddd8ab3c420d0c2d",
    "test.parquet": "b4e8335f2037b1b8af8f9e909f90922fc53638b233f530bbebea1dfc39b9e515",
}


def test_raw_files_match_pinned_hashes():
    from shellguard.data import RAW_DIR

    for name, sha in EXPECTED_SHA256.items():
        path = RAW_DIR / name
        assert path.exists(), f"{path} missing - run `make data`"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, name


def test_raw_data_has_expected_columns_and_rows():
    from shellguard.data import RAW_DIR

    rel = duckdb.read_parquet(str(RAW_DIR / "*.parquet"))
    assert {"command", "risk_level", "reversible", "risk_categories"} <= set(rel.columns)
    # measured from the pinned files; the dataset card's 124,923 is stale
    assert rel.count("*").fetchall()[0][0] == 136_497
