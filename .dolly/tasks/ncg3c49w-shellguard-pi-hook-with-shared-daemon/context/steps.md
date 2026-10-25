<!-- dolly steps · task ncg3c49w · append-only, newest at the bottom -->
# Full step context — shellguard pi hook with shared daemon

Short summaries live in `../task.md`. Each entry below is the full context of one step:
decisions and why, options rejected, gotchas, snippets, what to do next.

<!-- dolly:step 0002 -->
## 0002 · 2026-10-25T09:24:23Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/chain.py`, `tests/test_chain.py`, `pyproject.toml`

split_chain(cmd) in src/shellguard/chain.py uses tree-sitter-bash.
- Top-level `list` nodes are && / || chains (recurse); other named children of program are ;/newline statements.
- Pipelines, subshells, $( ), backticks, for/if/while/case, heredocs = one unit. Comments dropped.
- root.has_error -> [command] (bash -n agrees on the test cases; dataset errors sampled were PowerShell/cmd).
- Parts are byte slices of the original text (encode/decode), so unicode-safe.
Compared on 23 cases: hand scanner 23/23 but breaks loops/if/case/heredocs; shlex tokens 17/23; bashlex 19/23 at 227 us; tree-sitter 21/23 where both "fails" were wrong expectations (comment, invalid bash).
Dataset: 42,009 cmds, 8 us avg, 3,614 split into >1, 545 (1.3%) parse errors kept whole.
Known limit: a compound command (loop/if) is one part; no recursion into blocks.
Next: step 2 check(cmd) -> {label, danger_probability, flagged[]} shared by CLI + daemon.
<!-- /dolly:step 0002 -->
