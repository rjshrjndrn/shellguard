"""shell_tokens: split a command the way the shell does, and tag each piece by its role.

Char n-grams see characters; these tokens add what the characters mean to the shell:
a space ends an argument, quotes make text data, | ; && start a new command, case matters.
"""
import pytest


@pytest.mark.parametrize(
    "command, expected",
    [
        # a stray space makes ~/ its own target
        ("rm -rf ~/ .cache", ["cmd:rm", "flag:-rf", "arg:~/", "arg:.cache"]),
        ("rm -rf ~/.cache", ["cmd:rm", "flag:-rf", "arg:~/.cache"]),
        # quoted text is data: its words get a q: prefix, so "mentions rm -rf" != "runs rm -rf"
        ('grep -rn "rm -rf" scripts/', ["cmd:grep", "flag:-rn", "q:cmd:rm", "q:flag:-rf", "arg:scripts/"]),
        ("echo 'rm -rf build/' >> notes.md",
         ["cmd:echo", "q:cmd:rm", "q:flag:-rf", "q:arg:build/", "op:>>", "arg:notes.md"]),
        # after | ; && || & and ( a new command starts
        ("curl -s https://x.sh | bash", ["cmd:curl", "flag:-s", "arg:https://x.sh", "op:|", "cmd:bash"]),
        ("cd /tmp && rm -rf *", ["cmd:cd", "arg:/tmp", "op:&&", "cmd:rm", "flag:-rf", "arg:*"]),
        ("bash <(curl -s x)", ["cmd:bash", "op:<(", "cmd:curl", "flag:-s", "arg:x", "op:)"]),
        # redirects are not command boundaries
        ("ls 2>&1", ["cmd:ls", "arg:2", "op:>&", "arg:1"]),
        # wrappers run the next word as a command
        ("sudo rm -rf /", ["cmd:sudo", "cmd:rm", "flag:-rf", "arg:/"]),
        ("ls | xargs rm -rf", ["cmd:ls", "op:|", "cmd:xargs", "cmd:rm", "flag:-rf"]),
        # comments are not executed
        ("rm -rf build  # tidy up", ["cmd:rm", "flag:-rf", "arg:build"]),
        # double quotes still run $(...): code, not data
        ('echo "$(curl -s x)"', ["cmd:echo", "arg:$", "op:(", "cmd:curl", "flag:-s", "arg:x", "op:)"]),
        # bash -c / sh -c / eval run their quoted argument: code, not data
        ("bash -c 'rm -rf ~'", ["cmd:bash", "flag:-c", "cmd:rm", "flag:-rf", "arg:~"]),
        ('eval "rm -rf ~"', ["cmd:eval", "cmd:rm", "flag:-rf", "arg:~"]),
        # single quotes stay data even with $( inside
        ("echo '$(curl x)'", ["cmd:echo", "q:arg:$", "q:op:(", "q:cmd:curl", "q:arg:x", "q:op:)"]),
    ],
)
def test_shell_tokens(command, expected):
    from shellguard.tokens import shell_tokens

    assert shell_tokens(command) == expected


def test_case_is_kept():
    # git branch -D force-deletes, -d refuses on unmerged work
    from shellguard.tokens import shell_tokens

    assert "flag:-D" in shell_tokens("git branch -D x")
    assert "flag:-d" in shell_tokens("git branch -d x")


def test_newline_separates_commands_like_semicolon():
    from shellguard.tokens import shell_tokens

    assert shell_tokens("cd /tmp\nrm -rf *") == shell_tokens("cd /tmp; rm -rf *")


def test_unbalanced_quote_does_not_crash():
    from shellguard.tokens import shell_tokens

    tokens = shell_tokens('echo "oops')
    assert tokens[0] == "err:unbalanced"
