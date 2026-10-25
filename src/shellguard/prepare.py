"""Both raw datasets -> one labelled row per command -> stratified 80/20 split."""
import csv
from pathlib import Path

import duckdb
from sklearn.model_selection import train_test_split

from shellguard.data import RAW_DIR, ROOT

GOLDEN = ROOT / "data" / "golden.csv"
HARD = ROOT / "data" / "hard.csv"
EXAMS = (GOLDEN, HARD)  # hand-written exams: never trained on, never in test
# hand-written rows that break token shortcuts in the raw data (~/, 2>&1); split like the rest
EXTRA = ROOT / "data" / "extra.csv"
OUT_DIR = ROOT / "data"
SEED = 42

# One row per command, from both sources. Each row first gets a per-source verdict:
#   cli-command-risk: dangerous = not reversible, or high/critical
#   shell-safety:     dangerous = deny or ask (owner: in doubt, dangerous)
# A command repeats (once per shell, or in both sources) and copies can disagree,
# so the label takes the most dangerous reading of any copy.
LABELLED = """
WITH rows AS (
    SELECT command, NOT reversible OR risk_level IN ('high', 'critical') AS dangerous,
           risk_categories AS categories
    FROM read_parquet($ccr)
    UNION ALL
    SELECT command, label IN ('deny', 'ask'), ['shell-safety:' || label]
    FROM read_json($shell_safety)
    UNION ALL
    SELECT command, label = 'dangerous', ['extra']
    FROM read_csv($extra, all_varchar = true)
)
SELECT command,
       CASE WHEN bool_or(dangerous) THEN 'dangerous' ELSE 'safe' END AS label,
       list_sort(list_distinct(flatten(list(categories)))) AS categories
FROM rows
WHERE command NOT IN (SELECT unnest($exams::VARCHAR[]))  -- exams stay unseen
GROUP BY command
ORDER BY command  -- fixed order so the seeded split is repeatable
"""


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def exam_commands() -> list[str]:
    return [r["command"] for path in EXAMS for r in load_csv(path)]


def prepare(out_dir: Path = OUT_DIR) -> None:
    params = {
        "ccr": str(RAW_DIR / "cli-command-risk" / "*.parquet"),
        "shell_safety": str(RAW_DIR / "shell-safety" / "*.jsonl"),
        "exams": exam_commands(),
        "extra": str(EXTRA),
    }
    df = duckdb.execute(LABELLED, params).fetchdf()
    train, test = train_test_split(df, test_size=0.2, stratify=df.label, random_state=SEED)

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("test", test)):
        duckdb.from_df(part).write_parquet(str(out_dir / f"{name}.parquet"))
        print(f"{name}: {len(part)} commands, {(part.label == 'dangerous').mean():.1%} dangerous")


if __name__ == "__main__":
    prepare()
