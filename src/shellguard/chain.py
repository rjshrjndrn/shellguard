"""Split a command line into the commands the shell runs one after another.

  'cd /tmp && rm -rf build; cat k | curl -d @- x'
    -> ['cd /tmp', 'rm -rf build', 'cat k | curl -d @- x']

Uses the tree-sitter bash grammar: a top-level `list` node is a && / || chain, and the
program's other children are the ; / newline separated statements. Everything else
(pipelines, subshells, $( ), loops, if, case, heredocs) is one unit. Comments are
dropped since they never run. Parts are slices of the original text, so the hook shows
and remembers what the agent actually wrote. Invalid bash stays whole: don't guess.
"""
import re
import shlex

import tree_sitter_bash
from tree_sitter import Language, Parser

_PARSER = Parser(Language(tree_sitter_bash.language()))


def split_chain(command: str) -> list[str]:
    source = command.encode()
    root = _PARSER.parse(source).root_node
    if root.has_error:
        return [command]

    parts: list[str] = []

    def walk(node, end: int | None = None) -> None:
        """`end`: stretch the last part to here (it owns a redirect, see below)."""
        kids = [c for c in node.named_children if c.type != "comment"]
        for i, child in enumerate(kids):
            last_end = end if end is not None and i == len(kids) - 1 else None
            body = child.child_by_field_name("body") if child.type == "redirected_statement" else None
            if child.type == "list":
                walk(child, last_end)
            elif body is not None and body.type == "list":
                # tree-sitter hangs `a && b 2>&1` / `cd x && cat > f <<EOF` on the whole
                # list; in bash the redirect belongs to the last command only
                walk(body, child.end_byte)
            else:
                stop = last_end if last_end is not None else child.end_byte
                parts.append(source[child.start_byte : stop].decode().strip())

    walk(root)
    return [p for p in parts if p]


# Commands that cannot change anything on their own. Model A scores short commands
# noisily (`echo hi` 0.81 > `rm -rf /tmp/x` 0.71), so these are never flagged.
# They don't read file contents, so variables in their arguments are fine.
HARMLESS = {"echo", "printf", "true", "false", ":", "pwd", "cd", "ls", "test", "[",
            "sleep", "which", "type"}
# Read-only commands, after Codex (openai/codex, Apache-2.0, codex-rs/shell-command/
# src/command_safety/is_safe_command.rs). git is left out on purpose: repo config can
# make even `git status` run helpers (Codex #39524). These read files, so arguments
# must be literal: a variable could name a secret, or hide an option below.
READ_ONLY = {"cat", "cut", "expr", "grep", "head", "id", "nl", "paste", "rev", "seq",
             "stat", "tail", "tr", "uname", "uniq", "wc", "whoami"}
_FIND_UNSAFE = {"-exec", "-execdir", "-ok", "-okdir", "-delete",    # run code, delete
                "-fls", "-fprint", "-fprint0", "-fprintf"}          # write a file
_SHORT = re.compile(r"-[^-]")  # a cluster of short flags: -iz is -i -z


def _rg_ok(w: list[str]) -> bool:  # --pre/--hostname-bin run a command, -z runs decompressors
    return not any(a.split("=")[0] in ("--pre", "--hostname-bin", "--search-zip")
                   or (_SHORT.match(a) and "z" in a) for a in w[1:])


def _base64_ok(w: list[str]) -> bool:  # -o / --output writes a file
    return not any(a.startswith("--output") or (_SHORT.match(a) and "o" in a) for a in w[1:])


def _sed_ok(w: list[str]) -> bool:  # only `sed -n 10p [file]` / `sed -n 1,5p [file]`
    return (len(w) in (3, 4) and w[1] == "-n" and re.fullmatch(r"(\d+,)?\d+p", w[2]) is not None
            and (len(w) == 3 or not w[3].startswith("-")))


OPTION_RULES = {"find": lambda w: not _FIND_UNSAFE & set(w), "rg": _rg_ok,
                "base64": _base64_ok, "sed": _sed_ok}

# a redirect writes files; substitutions run code; an env assignment can change what
# runs (LD_PRELOAD=evil.so ls)
_UNSAFE = {"file_redirect", "heredoc_redirect", "herestring_redirect",
           "command_substitution", "process_substitution", "variable_assignment"}
# printing a secret puts it in the agent's context (echo $GITHUB_TOKEN). In the dataset,
# echo/printf of such a name is dangerous 34x, safe 1x; other names are mixed and the
# model scores them noisily (echo $PATH 0.84), so only these names count.
_SECRET_NAME = re.compile(r"TOKEN|SECRET|PASS|KEY|CRED|AUTH|PRIVATE|SESSION|COOKIE", re.I)
# reading one of these prints a key into the agent's context (cat ~/.ssh/id_rsa)
_SECRET_PATH = re.compile(
    r"(^|/)\.(ssh|aws|kube|docker|gnupg|config/gh)(/|$)"
    r"|(^|/)\.(env|netrc|git-credentials|npmrc|pypirc)(\.|/|$)"
    r"|^/etc/(shadow|gshadow|sudoers)"
    r"|(^|/)id_(rsa|dsa|ecdsa|ed25519)|\.(pem|key|p12|pfx)$"
    r"|(^|[/_.-])(secrets?|tokens?|credentials?|passwords?)([_.-][^/]*)?\.\w+$", re.I)
_LITERAL = {"word", "number", "raw_string"}


def harmless(part: str) -> bool:
    """True if `part` can't change anything or leak a secret: one known command, or a
    pipeline of them, with nothing that writes, runs code or names a secret."""
    root = _PARSER.parse(part.encode()).root_node
    if root.has_error or len(root.named_children) != 1:
        return False
    node = root.named_children[0]
    commands = node.named_children if node.type == "pipeline" else [node]
    return all(_safe(c) for c in commands)


def _safe(node) -> bool:
    if node.type == "command":
        name = node.child_by_field_name("name")
        name = name.text.decode() if name is not None else None
        args = node.children_by_field_name("argument")
        if name in HARMLESS:
            ok = True
        elif name in READ_ONLY or name in OPTION_RULES:
            words = [_word(a) for a in args]
            ok = (all(_literal(a) for a in args)
                  and (name in READ_ONLY or OPTION_RULES[name]([name, *words])))
        else:
            return False
        if not ok or any(_SECRET_PATH.search(_path(a)) for a in args):
            return False
    elif node.type != "test_command":  # [ ... ] / [[ ... ]]; else redirect, loop, subshell...
        return False
    stack = list(node.named_children)
    while stack:
        n = stack.pop()
        if n.type in _UNSAFE:
            return False
        if n.type == "variable_name" and _SECRET_NAME.search(n.text.decode()):
            return False
        stack.extend(n.named_children)
    return True


def _literal(node) -> bool:
    """Plain text after quoting: no variables, $'..', {a,b} or substitutions."""
    if node.type in _LITERAL:
        return "{" not in node.text.decode() if node.type == "word" else True
    if node.type == "string":
        return all(c.type == "string_content" for c in node.named_children)
    if node.type == "concatenation":
        return all(_literal(c) for c in node.named_children)
    return False


def _word(node) -> str:
    try:
        return "".join(shlex.split(node.text.decode()))
    except ValueError:
        return node.text.decode()


def _path(node) -> str:  # quotes dropped, Windows separators as /
    return node.text.decode().replace("\\", "/").replace('"', "").replace("'", "")


# Commands that delete or overwrite data. Read off the syntax tree because the model
# can't be trusted with them: find -delete is labelled safe 419x and dangerous 383x
# in the data, so `-maxdepth 1` (a "safe" word) dropped `find ~ -delete` to 0.24.
_DELETES = {"rm", "rmdir", "unlink", "shred", "truncate"}
# commands that run the command after them; options listed take a value
_WRAPPERS = {"sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U"},
             "doas": {"-u", "-C"}, "env": {"-u", "-C", "-S"}, "command": set(),
             "nohup": set(), "time": {"-f", "-o"}, "nice": {"-n"}, "exec": {"-a"},
             "stdbuf": {"-i", "-o", "-e"}, "ionice": {"-c", "-n", "-p"},
             "timeout": {"-s", "-k"},
             "xargs": {"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a", "-l"}}
_GIT_GLOBAL = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}  # take a value


def destructive(part: str) -> bool:
    """True if any command in `part` deletes or overwrites data: rm, rmdir, unlink,
    shred, truncate, find -delete / -exec rm, git clean -f, git reset --hard,
    dd of=, mkfs. Also through sudo/env/xargs/..., in loops, $( ) and pipes."""
    root = _PARSER.parse(part.encode()).root_node
    if root.has_error:
        return False  # can't tell; the model scores it
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == "command":
            words = [_word(c) for c in n.named_children
                     if c.type not in ("variable_assignment", "file_redirect", "herestring_redirect")]
            if _destroys(words):
                return True
        stack.extend(n.named_children)
    return False


def _destroys(w: list[str]) -> bool:
    while w:
        name = w[0].rsplit("/", 1)[-1]
        if name in _WRAPPERS:
            if name == "command" and any(a in ("-v", "-V") for a in w[1:2]):
                return False  # command -v rm: looks the name up, runs nothing
            w = _unwrap(name, w[1:])
            continue
        if name in _DELETES or name.startswith("mkfs"):
            return True
        if name == "dd":
            return any(a.startswith("of=") and a != "of=/dev/null" for a in w[1:])
        if name == "find":
            return "-delete" in w or any(
                a in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(w)
                and _destroys(w[i + 1:i + 2]) for i, a in enumerate(w))
        if name == "git":
            return _git_destroys(w[1:])
        return False
    return False


def _unwrap(name: str, w: list[str]) -> list[str]:
    """Drop a wrapper's options (and env's NAME=value), return the command it runs."""
    takes_value, i = _WRAPPERS[name], 0
    while i < len(w) and (w[i].startswith("-") or (name == "env" and "=" in w[i])):
        i += 2 if w[i] in takes_value else 1
    if name == "timeout" and i < len(w):
        i += 1  # the duration
    if name == "nice" and i < len(w) and w[i].lstrip("-").isdigit():
        i += 1
    return w[i:]


_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}


def shell_heredocs(part: str) -> list[str]:
    """Bodies of heredocs fed to a shell (`bash <<'EOF' ... EOF`, `sudo sh -s <<EOF`):
    that text is a script the shell runs, so it can be checked like any command.
    Not for `bash file.sh <<EOF` (stdin of a script) or `bash -c` (script is the arg)."""
    root = _PARSER.parse(part.encode()).root_node
    if root.has_error:
        return []
    bodies, stack = [], [root]
    while stack:
        n = stack.pop()
        cmd = n.child_by_field_name("body") if n.type == "redirected_statement" else None
        while cmd is not None and cmd.type == "list":  # `cd x && sh <<EOF`: the last one reads it
            cmd = cmd.named_children[-1]
        if cmd is not None and cmd.type == "command" and _runs_stdin(
                [_word(c) for c in cmd.named_children if c.type != "variable_assignment"]):
            bodies += [b.text.decode() for r in n.named_children if r.type == "heredoc_redirect"
                       for b in r.named_children if b.type == "heredoc_body"]
        stack.extend(reversed(n.named_children))
    return bodies


def _runs_stdin(w: list[str]) -> bool:
    """True if words `w` are a shell that reads its script from stdin."""
    while w and w[0].rsplit("/", 1)[-1] in _WRAPPERS:
        w = _unwrap(w[0].rsplit("/", 1)[-1], w[1:])
    if not w or w[0].rsplit("/", 1)[-1] not in _SHELLS:
        return False
    flags = [a for a in w[1:] if a.startswith("-")]
    short = "".join(a[1:] for a in flags if _SHORT.match(a))
    if "c" in short:
        return False
    return "s" in short or len(flags) == len(w) - 1  # -s: the rest are $1 $2 ...


def _git_destroys(w: list[str]) -> bool:
    i = 0
    while i < len(w) and w[i].startswith("-"):
        i += 2 if w[i] in _GIT_GLOBAL else 1
    sub, args = (w[i], w[i + 1:]) if i < len(w) else ("", [])
    if sub == "reset":
        return "--hard" in args
    if sub == "clean":
        short = "".join(a[1:] for a in args if _SHORT.match(a))
        dry = "n" in short or "--dry-run" in args
        return not dry and ("f" in short or "--force" in args)
    return False
