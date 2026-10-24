"""Download the pinned cli-command-risk dataset into data/raw/."""
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

REPO = "yannelli/cli-command-risk"
REVISION = "5e1283ed01fef1ebe7453feaaf058d9cd5767384"  # pinned so data never changes
FILES = ["train.parquet", "validation.parquet", "test.parquet"]


def download() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/data/{name}"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, RAW_DIR / name)


if __name__ == "__main__":
    download()
