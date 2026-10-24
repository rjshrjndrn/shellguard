"""Shell-aware tokens: split like the shell, tag each word by its role.

  'grep -rn "rm -rf" x | bash'
    -> cmd:grep flag:-rn q:cmd:rm q:flag:-rf arg:x op:| cmd:bash

Char n-grams see characters; these tokens add what the shell makes of them:
space ends an argument, quotes make text data, | ; && start a command, case matters.
"""
import shlex
import string

SEPARATORS = {"|", "||", "&&", ";", "&", "\n", "(", "$(", "<(", ">(", "`"}  # next word is a command
WRAPPERS = {"sudo", "doas", "xargs", "env", "nohup", "nice", "time", "exec", "command", "timeout", "watch"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}  # with -c, their quoted argument is code
PUNCTUATION = "();<>|&\n"
# everything else printable belongs to a word (shlex's default splits URLs at ':')
WORDCHARS = "".join(c for c in string.printable if c not in " \t\r\n\x0b\x0c'\"" + PUNCTUATION)


def _split(command: str) -> list[str]:
    # shortcut: posix=False keeps quotes so we can tell data from code, but splits
    # --data="a b" in two; fine for features, not a real shell parser
    lex = shlex.shlex(command, posix=False, punctuation_chars=PUNCTUATION)
    lex.whitespace = " \t\r"  # newline is a separator, not whitespace
    lex.wordchars = WORDCHARS
    lex.commenters = ""  # '#' starts a comment only at a word start; handled below
    return list(lex)


def shell_tokens(command: str) -> list[str]:
    try:
        words = _split(command)
    except ValueError:  # unbalanced quotes: the shell would refuse too
        return ["err:unbalanced"] + [f"arg:{w}" for w in command.split()]

    out, expect_cmd, in_comment, cmd, dash_c = [], True, False, "", False
    for w in words:
        if in_comment and w != "\n":
            continue
        in_comment = False
        if w.startswith("#"):
            in_comment = True
        elif w == "$":  # $( ... ): the command is the word after (, not $
            out.append("arg:$")
        elif w[0] in PUNCTUATION:
            out.append("op:" + (";" if w == "\n" else w))  # newline == ;
            expect_cmd = w in SEPARATORS or w.endswith("(")
        elif w[0] in "'\"" and w[-1] == w[0] and len(w) > 1:
            inner = w[1:-1]
            is_code = (
                cmd == "eval" or (cmd in SHELLS and dash_c)  # bash -c '...' runs it
                or (w[0] == '"' and ("$(" in inner or "`" in inner))  # "$(...)" runs inside ""
            )
            out += [t if is_code else f"q:{t}" for t in shell_tokens(inner)]  # data gets q:
            expect_cmd = False
        elif expect_cmd:
            out.append(f"cmd:{w}")
            cmd, dash_c = w, False
            expect_cmd = w in WRAPPERS  # sudo rm: rm is the real command
        elif w.startswith("-") and len(w) > 1:
            out.append(f"flag:{w}")
            dash_c = dash_c or w == "-c"
        else:
            out.append(f"arg:{w}")
    return out


def shell_features(command: str) -> list[str]:
    """Tokens plus neighbour pairs, so order counts: "flag:-rf arg:~/" is its own feature."""
    t = shell_tokens(command)
    return t + [f"{a} {b}" for a, b in zip(t, t[1:])]
