"""Make the dataset's git labels follow the git rule in chain.py.

The raw sources contradict each other on git (`git add . && git commit -m bump`
dangerous, `git add go.mod && git commit -m bump` safe; `git clean -fd`, `git add
id_rsa` safe), so the model learned the git words instead of the danger. A row is
relabelled only when the rule can judge all of it; anything else keeps its label.
"""
import re

from shellguard.chain import destructive, harmless, split_chain

_GIT = re.compile(r"(?:^|[\s;&|(])git\s")  # a git command, not "git" inside a word


def git_label(command: str) -> str | None:
    """'dangerous' if a git part loses work, rewrites or publishes history; 'safe' if
    every part is safe by rule and one of them is git; None if the rule can't judge."""
    parts = split_chain(command)
    git_parts = [p for p in parts if _GIT.search(" " + _code(p))]
    if not git_parts:
        return None
    if any(destructive(p) for p in git_parts):
        return "dangerous"
    if all(harmless(p) for p in parts):
        return "safe"
    return None


def _code(part: str) -> str:
    """The part without quoted text, so `echo 'git push'` is not a git command."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", part)
