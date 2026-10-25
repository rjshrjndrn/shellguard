"""Split a command line into the commands the shell runs one after another.

  'cd /tmp && rm -rf build; cat k | curl -d @- x'
    -> ['cd /tmp', 'rm -rf build', 'cat k | curl -d @- x']

Uses the tree-sitter bash grammar: a top-level `list` node is a && / || chain, and the
program's other children are the ; / newline separated statements. Everything else
(pipelines, subshells, $( ), loops, if, case, heredocs) is one unit. Comments are
dropped since they never run. Parts are slices of the original text, so the hook shows
and remembers what the agent actually wrote. Invalid bash stays whole: don't guess.
"""
import tree_sitter_bash
from tree_sitter import Language, Parser

_PARSER = Parser(Language(tree_sitter_bash.language()))


def split_chain(command: str) -> list[str]:
    source = command.encode()
    root = _PARSER.parse(source).root_node
    if root.has_error:
        return [command]

    parts: list[str] = []

    def walk(node) -> None:
        for child in node.named_children:
            if child.type == "list":
                walk(child)
            elif child.type != "comment":
                parts.append(source[child.start_byte : child.end_byte].decode().strip())

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
        stack.extend(n.named_children)
    return True
