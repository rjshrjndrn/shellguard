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

<!-- dolly:step 0004 -->
## 0004 · 2026-10-25T09:33:30Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/daemon.py`, `src/shellguard/__main__.py`, `tests/test_daemon.py`

src/shellguard/daemon.py: serve(sock, model_path, idle=1800, poll=1, score) -> reason str.
- Protocol: newline JSON, {"command": str} -> {"command", label, danger_probability, flagged}; bad request -> {"error"}; many lines per connection OK.
- Single instance: fcntl.flock(<sock>.lock, EX|NB). Changed from plan (bind-as-lock): with bind, two clients both deleting a stale socket could delete a fresh one -> orphan daemon. Lock holder alone unlinks leftovers; kernel releases lock on death (kill -9 safe).
- Dir 0700, socket 0600.
- Watcher loop (poll s): socket (ino,mtime,size) changed -> "socket gone"; model file id changed/missing -> "model changed"; idle -> "idle". Then shutdown, unlink own socket, release lock.
- Binds before loading model so early clients queue in backlog instead of respawning.
- ThreadingUnixStreamServer + a lock around scoring.
- CLI: `shellguard --serve [--socket P] [--idle S]` (flag, not subcommand, so a command named "serve" can still be checked).
- request(sock, cmd, timeout) client helper (Python; used by tests).
Measured: warm round trip 0.78-1.01 ms (Python client, 50 requests). 3 concurrent starts -> 1 daemon, 2 print "already running".
Test gotcha: wait for connectable(), not sock.exists() (a leftover file exists before bind).
Next: step 4 hooks/pi/decide.ts.
<!-- /dolly:step 0004 -->

<!-- dolly:step 0007 -->
## 0007 · 2026-10-25T09:55:51Z · @rjshrjndrn

- task status: working
- files: `hooks/pi/index.ts`, `hooks/pi/menu.ts`, `hooks/pi/menu.test.ts`

hooks/pi/index.ts wires: session_start (status + warm the daemon via check("true")), tool_call (bash only) -> client.check -> decide -> popup/block, /shellguard on|off|status with arg completions, status bar "shellguard: off" when disabled.
hooks/pi/menu.ts: popup as data (askMenu, failedMenu, press(key), render) -> 11 node tests; index.ts adds theme colours + matchesKey + truncateToWidth.
Imports @earendil-works/pi-coding-agent and pi-tui are provided by pi's loader (virtual modules) - no package.json needed.
Type-checked index.ts against pi's real .d.ts with tsc 5 (strict) - 0 errors.
Manual, real pi in tmux (/tmp/sgpi):
- pi -p: daemon auto-spawned in ~/.cache/shellguard; command blocked, model read reason.
- popup named only "rm -rf ..." in a 3-part chain; s -> ran; later chain with that part + "git reset --hard" -> popup listed only the reset (new part); Down Down Enter -> deny.
- /shellguard status lists allowed parts; off -> flagged command ran with no popup, status bar shows "shellguard: off"; on -> popup back; Esc -> denied.
- shellguard missing from PATH + daemon stopped -> "shellguard failed: cannot start shellguard ... ENOENT" popup; enter -> ran.
Observed: pi waits for all tool_call hooks of a batch before executing, so an allowed call waits for its sibling's popup.
Noise seen: "echo done" flagged 0.722 alongside rm -rf in -p mode (known short-part noise).
Not measured inside pi: per-call latency; node client p50 0.84 ms is the bound (hook adds no I/O).
Next: step 7 make hook-pi / unhook-pi + README.
<!-- /dolly:step 0007 -->
