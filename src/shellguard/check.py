"""check(cmd): verdict plus which parts of a chain made it dangerous.

  check("cd /tmp && rm -rf build && ls")
    -> {"label": "dangerous", "danger_probability": 0.62,
        "flagged": [{"part": "rm -rf build", "danger_probability": 0.82}]}

The whole command decides the label (that is what was measured). Splitting only names
parts to show and remember: every part >= threshold, highest first; the whole chain if
none is dangerous alone. Shared by the CLI and the daemon.
"""
from collections.abc import Callable

from shellguard.chain import split_chain
from shellguard.model_a import THRESHOLD

Scorer = Callable[[list[str]], list[float]]


def _model_scorer(commands: list[str]) -> list[float]:
    from shellguard.model_a import predict_many

    return predict_many(commands)


def check(command: str, score: Scorer = _model_scorer) -> dict:
    p = score([command])[0]
    flagged = []
    if p >= THRESHOLD:
        parts = list(dict.fromkeys(split_chain(command)))  # unique, order kept
        if parts != [command]:  # it was a chain
            hits = [(q, s) for q, s in zip(score(parts), parts) if q >= THRESHOLD]
            flagged = [{"part": s, "danger_probability": round(q, 3)}
                       for q, s in sorted(hits, key=lambda h: -h[0])]
        if not flagged:  # single command, or danger is the combination
            flagged = [{"part": command, "danger_probability": round(p, 3)}]
    return {"label": "dangerous" if p >= THRESHOLD else "safe",
            "danger_probability": round(p, 3), "flagged": flagged}
