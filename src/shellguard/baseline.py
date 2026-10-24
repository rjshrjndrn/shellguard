"""Regex baseline: hand-written patterns, written from general knowledge without
looking at the test data. Not a model - it is the score a model must beat."""
import re

PATTERNS = [
    # destructive
    r"\brm\s+-\w*[rf]\w*\s+(/|~|\$HOME|\$\w+|\"\$)",  # rm -rf on root, home or a variable
    r"\bmkfs\b",
    r"\bdd\b.*\bof=/dev/",
    r"\bshred\b",
    r"\bgit\s+clean\s+-\w*f",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\b.*(\s-f\b|--force)",
    r"\bkubectl\s+delete\b",
    r"\bterraform\s+destroy\b",
    r"\bDROP\s+(DATABASE|TABLE)\b",
    r"\bchmod\s+-R\s+777\b",
    # malicious
    r"/dev/tcp/",  # bash reverse shell
    r"\bnc\b.*\s-e\s",  # netcat reverse shell
    r"\|\s*(sudo\s+)?(ba|z)?sh\b",  # pipe into a shell
    r"\bchmod\s+(u\+s|\+s|4755)\b",  # setuid
    r"/etc/sudoers",
    r":\(\)\s*\{",  # fork bomb
]
DANGER = re.compile("|".join(PATTERNS), re.IGNORECASE)


def predict(command: str) -> dict:
    hit = DANGER.search(command) is not None
    return {"label": "dangerous" if hit else "safe", "probability": float(hit)}
