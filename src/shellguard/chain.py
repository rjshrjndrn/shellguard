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
HARMLESS = {"echo", "printf", "true", "false", ":", "pwd", "cd", "ls", "test", "[",
            "sleep", "which", "type"}
# a redirect writes files; substitutions run code; an env assignment can change what
# runs (LD_PRELOAD=evil.so ls)
_UNSAFE = {"file_redirect", "heredoc_redirect", "herestring_redirect",
           "command_substitution", "process_substitution", "variable_assignment"}
# printing a secret puts it in the agent's context (echo $GITHUB_TOKEN). In the dataset,
# echo/printf of such a name is dangerous 34x, safe 1x; other names are mixed and the
# model scores them noisily (echo $PATH 0.84), so only these names count.
_SECRET_NAME = re.compile(r"TOKEN|SECRET|PASS|KEY|CRED|AUTH|PRIVATE|SESSION|COOKIE", re.I)


def harmless(part: str) -> bool:
    """True if `part` is one plain command from HARMLESS, with nothing that writes or runs code."""
    root = _PARSER.parse(part.encode()).root_node
    if root.has_error or len(root.named_children) != 1:
        return False
    node = root.named_children[0]
    if node.type == "command":
        name = node.child_by_field_name("name")
        if name is None or name.text.decode() not in HARMLESS:
            return False
    elif node.type != "test_command":  # [ ... ] / [[ ... ]]; else pipeline, redirect, loop...
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
