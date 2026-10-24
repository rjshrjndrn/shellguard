"""Download the pinned training datasets into data/raw/<name>/."""
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

# name -> (HF repo, pinned commit so data never changes, files)
DATASETS = {
    "cli-command-risk": (
        "yannelli/cli-command-risk",
        "5e1283ed01fef1ebe7453feaaf058d9cd5767384",
        ["data/train.parquet", "data/validation.parquet", "data/test.parquet"],
    ),
    "shell-safety": (
        "tomngdev/shell-safety-v1.1",
        "fee89770c315d525ef2ee42adee6ef9725a7621e",
        ["train.jsonl", "validation.jsonl", "test.jsonl"],
    ),
}


def download() -> None:
    for name, (repo, revision, files) in DATASETS.items():
        out = RAW_DIR / name
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{f}"
            print(f"downloading {url}")
            urllib.request.urlretrieve(url, out / Path(f).name)


if __name__ == "__main__":
    download()
