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

<!-- dolly:step 0009 -->
## 0009 · 2026-10-25T10:18:49Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `hooks/pi/menu.ts`, `hooks/pi/index.ts`

Bug report: "pressing s doesn't remember". Root cause from the user's pi session jsonl: memory worked, but the agent varied a harmless echo per call ('echo "removed (exit $?)"' 0.768, 'echo "exit $?"' 0.758) and model A flags short commands noisily (echo hi 0.809 > rm -rf /tmp/tester 0.711). Each call had a NEW flagged part -> popup again.
Fix 1 (python, check.py + chain.harmless): HARMLESS = echo printf true false : pwd cd ls test [ sleep which type; also test_command node ([ ], [[ ]]). Not harmless if any file/heredoc/herestring redirect, command/process substitution, variable_assignment (LD_PRELOAD), pipeline, or >1 statement, or parse error. Harmless parts are not scored/flagged; all-harmless command -> safe, 0.0, model not called.
Fix 2 (popup): askMenu shows already-allowed flagged parts after new ones, "(allowed this session)", dimmed in index.ts.
User decision: session allow = exact flagged part incl. path (already the behaviour); test added in decide.test.ts.
Verified in real pi (tmux, installed via make hook-pi): the 3 session commands -> 1 popup listing only rm -rf /tmp/tester, s, then no popups; dir removed each time.
Note: evaluate.py uses predict(), not check(), so measured metrics are unchanged.
<!-- /dolly:step 0009 -->

<!-- dolly:step 0010 -->
## 0010 · 2026-10-25T10:35:18Z · @rjshrjndrn

- task status: working
- files: `hooks/pi/menu.ts`, `hooks/pi/menu.test.ts`

Popup fix: askMenu no longer prints commands > 3 lines (pi shows them in chat); each flagged part = first line + "(+N lines)"; constant height (test: 4 vs 300 lines). User's 60-line command now renders as 8 lines. In-pi visual check not done: Anthropic usage-policy filter refused the test prompts (rm -rf / git push --force snippets); did not try to word around it.

Findings, NOT fixed, need user decisions:
1. Dilution miss: whole command decides, so a dangerous line inside a long script is diluted below 0.35 and never split.
   "mkdir -p /tmp/sgtest && python3 - <<'EOF' (25 lines) EOF\nrm -rf /tmp/sgtest && echo gone" -> whole 0.208 safe; rm part alone 0.836. Ran in real pi without a popup.
   "git push --force && python3 heredoc": 4 lines 0.632, 7: 0.453, 12: 0.393, 17: 0.354.
   Test split with harmless filter: whole-decides chains recall 0.963 (31 missed, 97 FA); whole-OR-any-non-harmless-part recall 0.985 (13 missed, 128 FA). Full split: 0.986/64 missed/278 FA vs 0.990/46/309.
2. Regression from step 9 harmless(): 8 dangerous test commands are all-harmless and were caught by the model before: echo $PASSWORD, echo $AWS_SECRET_ACCESS_KEY, printf %s $SECRET, echo -n $DB_PASSWORD, echo $GITHUB_TOKEN (6 with $VAR) + 2 printf "<API_KEY>" literals. Fix idea: expansions other than special vars ($? $# ...) make echo/printf not harmless.
<!-- /dolly:step 0010 -->
