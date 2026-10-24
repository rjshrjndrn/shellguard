import csv
from pathlib import Path

GOLDEN = Path(__file__).parent.parent / "data" / "golden.csv"


def load_golden() -> list[dict]:
    with GOLDEN.open(newline="") as f:
        return list(csv.DictReader(f))
