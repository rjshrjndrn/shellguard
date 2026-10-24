import csv
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"


def load_golden() -> list[dict]:
    with (DATA / "golden.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def load_hard() -> list[dict]:
    with (DATA / "hard.csv").open(newline="") as f:
        return list(csv.DictReader(f))
