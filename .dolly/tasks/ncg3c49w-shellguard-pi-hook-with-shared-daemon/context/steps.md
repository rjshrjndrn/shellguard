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

<!-- dolly:step 0003 -->
## 0003 · 2026-10-25T09:27:52Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/check.py`, `src/shellguard/model_a.py`, `src/shellguard/__main__.py`, `tests/test_check.py`, `tests/test_cli.py`, `README.md`

check(cmd, score=model) in src/shellguard/check.py -> {label, danger_probability, flagged[]}, all rounded to 3 dp.
- Whole command scored first; label from it (measured metric unchanged).
- Only if dangerous: split_chain, dedupe (dict.fromkeys), score parts in ONE batch via model_a.predict_many.
- flagged = parts >= THRESHOLD sorted desc; else [whole command] (single cmd or combination danger).
- Bug caught by test: "rm -rf a; rm -rf a" dedupes to 1 part; guard is `parts != [command]`, not len>1.
- score is injectable (fake scorer in tests records calls -> proves safe chains are not split, parts batched).
- CLI prints {"command", **check()}; exit codes unchanged.
- model_a.predict_many added; predict() now wraps it.
Verified: "git add -A && git commit -m wip && git push --force" -> flagged push 0.985, add 0.844, commit 0.462.
Next: step 3 daemon `shellguard serve` on ~/.cache/shellguard/sock using check().
<!-- /dolly:step 0003 -->
