"""Model A - no base model. Learns everything from our data, in seconds, on CPU.

  "git clean -fdx" -> char n-grams ("gi", "it", ..., "-fdx")             TfidfVectorizer
                   + shell tokens ("cmd:git", "flag:-fdx", pairs)         TfidfVectorizer
                   -> one weight per feature, summed, squashed            LogisticRegression
                   -> P(dangerous) in [0, 1]
"""
from pathlib import Path

import duckdb
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline, make_union

from shellguard.data import ROOT
from shellguard.prepare import OUT_DIR
from shellguard.tokens import shell_features

MODEL_PATH = ROOT / "models" / "model_a.joblib"
# P(dangerous) at or above this -> "dangerous". Picked in step 8 on out-of-fold train
# predictions: below 0.5 because a miss (irreversible loss) costs more than a false alarm.
THRESHOLD = 0.35
_model: Pipeline | None = None


def train(commands: list[str], labels: list[str]) -> Pipeline:
    model = make_pipeline(
        make_union(
            # "char" (not "char_wb") so n-grams span spaces: "-rf /", "| sh", "of=/dev".
            # lowercase=False: git branch -D (force) is not -d (safe)
            TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2, sublinear_tf=True, lowercase=False),
            # what the shell makes of it: arguments, quoted data, command starts
            TfidfVectorizer(analyzer=shell_features, min_df=2, sublinear_tf=True, lowercase=False),
        ),
        LogisticRegression(max_iter=2000),
    )
    return model.fit(commands, labels)


def save(model: Pipeline, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)  # pickle-based: only load files you built yourself


def load(path: Path = MODEL_PATH) -> Pipeline:
    return joblib.load(path)


def predict(command: str, model: Pipeline | None = None) -> dict:
    global _model
    if model is None:
        model = _model = _model or load()
    p = float(model.predict_proba([command])[0][list(model.classes_).index("dangerous")])
    return {"label": "dangerous" if p >= THRESHOLD else "safe", "probability": p}


if __name__ == "__main__":
    df = duckdb.read_parquet(str(OUT_DIR / "train.parquet")).fetchdf()
    model = train(df.command.tolist(), df.label.tolist())
    save(model)
    n = sum(len(v.vocabulary_) for _, v in model[0].transformer_list)
    print(f"trained on {len(df)} commands, {n} features -> {MODEL_PATH} "
          f"({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
