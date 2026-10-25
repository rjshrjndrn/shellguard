"""check(cmd): verdict plus which parts of a chain made it dangerous.

  check("cd /tmp && rm -rf build && ls")
    -> {"label": "dangerous", "danger_probability": 0.82,
        "flagged": [{"part": "rm -rf build", "danger_probability": 0.82}]}

Dangerous if the whole command OR any non-harmless part of the chain is >= threshold:
scoring only the whole let a long script dilute a dangerous line (25-line heredoc +
rm -rf: whole 0.208, rm part 0.836). danger_probability is the highest of those scores.
flagged = every part >= threshold, highest first; the whole chain if none is dangerous
alone (the danger is the combination). Harmless parts (chain.harmless: plain echo, cd, ls,
read-only cat, grep, head, find, rg, ... and pipes of them) are
never flagged, and a command made only of them is safe without asking the model.
Shared by the CLI and the daemon.
"""
from collections.abc import Callable

from shellguard.chain import harmless, split_chain
from shellguard.model_a import THRESHOLD

Scorer = Callable[[list[str]], list[float]]


def _model_scorer(commands: list[str]) -> list[float]:
    from shellguard.model_a import predict_many

    return predict_many(commands)


def check(command: str, score: Scorer = _model_scorer) -> dict:
    parts = list(dict.fromkeys(split_chain(command)))  # unique, order kept
    if parts and all(harmless(s) for s in parts):  # e.g. `echo hi`, `cd /tmp && pwd`
        return {"label": "safe", "danger_probability": 0.0, "flagged": []}
    risky = [s for s in parts if not harmless(s)] if parts != [command] else []
    p, *qs = score([command, *risky])  # one batch
    hits = sorted(((q, s) for q, s in zip(qs, risky) if q >= THRESHOLD), key=lambda h: -h[0])
    flagged = [{"part": s, "danger_probability": round(q, 3)} for q, s in hits]
    if p >= THRESHOLD and not flagged:  # single command, or danger is the combination
        flagged = [{"part": command, "danger_probability": round(p, 3)}]
    worst = max([p, *qs])
    return {"label": "dangerous" if flagged else "safe",
            "danger_probability": round(worst, 3), "flagged": flagged}
