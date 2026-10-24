"""Raw parquet -> one labelled row per command -> stratified 80/20 split."""
import csv
from pathlib import Path

import duckdb
from sklearn.model_selection import train_test_split

from shellguard.data import RAW_DIR, ROOT

GOLDEN = ROOT / "data" / "golden.csv"
HARD = ROOT / "data" / "hard.csv"
EXAMS = (GOLDEN, HARD)  # hand-written exams: never trained on, never in test
OUT_DIR = ROOT / "data"
SEED = 42

# One row per command. A command repeats once per shell; its copies can disagree
# (13 do), so the label takes the most dangerous reading of any copy:
#   dangerous = any copy not reversible, or any copy high/critical.
LABELLED = """
SELECT command,
       CASE WHEN NOT bool_and(reversible) OR bool_or(risk_level IN ('high', 'critical'))
            THEN 'dangerous' ELSE 'safe' END AS label,
       list_sort(list_distinct(flatten(list(risk_categories)))) AS categories
FROM read_parquet($raw)
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
    df = duckdb.execute(LABELLED, {"raw": str(RAW_DIR / "*.parquet"), "exams": exam_commands()}).fetchdf()
    train, test = train_test_split(df, test_size=0.2, stratify=df.label, random_state=SEED)

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("test", test)):
        duckdb.from_df(part).write_parquet(str(out_dir / f"{name}.parquet"))
        print(f"{name}: {len(part)} commands, {(part.label == 'dangerous').mean():.1%} dangerous")


if __name__ == "__main__":
    prepare()
