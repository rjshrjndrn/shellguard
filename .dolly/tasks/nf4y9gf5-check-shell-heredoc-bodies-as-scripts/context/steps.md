<!-- dolly steps · task nf4y9gf5 · append-only, newest at the bottom -->
# Full step context — check shell heredoc bodies as scripts

Short summaries live in `../task.md`. Each entry below is the full context of one step:
decisions and why, options rejected, gotchas, snippets, what to do next.

<!-- dolly:step 0001 -->
## 0001 · 2026-10-25T17:18:31Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `tests/test_chain.py`, `tests/test_check.py`, `README.md`

chain.shell_heredocs(part): walks the tree for redirected_statement whose body (last cmd of a && list) is sh/bash/zsh/dash/ksh, unwrapped through _WRAPPERS (sudo/env/...), with only flags or -s (positional args allowed), no -c. check() appends split_chain(body) parts while iterating (nesting). Outer statement stays a part, so model still scores the whole: detection only grows. Test split: 25 rows hit, FA 515->516; golden/hard unchanged. Not covered: herestrings (bash <<< ...), piped scripts (echo .. | sh, curl | sh is model-caught), bash -o opt <<EOF (value looks like a script file -> not expanded, conservative).
<!-- /dolly:step 0001 -->
