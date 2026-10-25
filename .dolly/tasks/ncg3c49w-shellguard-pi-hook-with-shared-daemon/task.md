---
id: ncg3c49w
slug: shellguard-pi-hook-with-shared-daemon
title: shellguard pi hook with shared daemon
status: validating
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 9
spec_version: 2
created: 2026-10-25T09:11:26Z
updated: 2026-10-25T10:18:49Z
---

# ncg3c49w · shellguard pi hook with shared daemon

<!-- dolly:header -->
`validating` · spec v2 · @rjshrjndrn · 9 steps · updated 2026-10-25 10:18Z
<!-- /dolly:header -->

## Spec

Before pi runs a bash command, shellguard scores it in ~1 ms; dangerous ones stop and ask the user, with the flagged part of a chain named and rememberable for the session.

Full spec: `context/spec.md` · plan: `context/plan.md`

## Success Criteria

- [ ] warm check p50 <= 5 ms measured end to end from the extension
- [ ] cd /tmp && rm -rf build && ls -> popup names rm -rf build; allow for session lets a later chain with only that flagged part run without asking
- [ ] safe command runs with no popup
- [ ] daemon killed -> next call respawns; socket missing -> spawn; two clients at once -> one daemon
- [ ] retrained model -> daemon replaced on next session start
- [ ] /shellguard off -> no checks; on -> checks resume
- [ ] shellguard broken -> failure popup; no UI -> blocked
- [ ] make hook-pi installs, make unhook-pi removes; make test green

## Full Context

- full spec + every superseded version: `context/spec.md`
- full context of every step: `context/steps.md`
- planning interview, when the task was planned: `context/plan.md`

## Log

- `2026-10-25 09:11Z` @rjshrjndrn: spec → v2. planning finished — spec derived from plan.md
  previous version kept in `spec.md`

### plan finalized · 2026-10-25 09:11Z · @rjshrjndrn

Plan complete. Status → todo.

- plan: `context/plan.md`
- `2026-10-25 09:15Z` @rjshrjndrn: Decided: flagged[] lists every dangerous part with its score, sorted; CLI and daemon share check() and both emit flagged[].
- `2026-10-25 09:17Z` @rjshrjndrn: status todo → working.
- `2026-10-25 09:24Z` @rjshrjndrn: split_chain lands on tree-sitter-bash: hand scanner and shlex cut loops/if/heredocs into junk parts; grammar keeps them whole, 8 us/cmd, invalid bash stays whole.
  files: `src/shellguard/chain.py`, `tests/test_chain.py`, `pyproject.toml` · full: `steps.md#0002`
- `2026-10-25 09:27Z` @rjshrjndrn: check() returns verdict + flagged parts; whole command decides, parts only named (batched, deduped, highest first, whole chain when none alone). CLI prints it.
  files: `src/shellguard/check.py`, `src/shellguard/model_a.py`, `src/shellguard/__main__.py`, `tests/test_check.py`, `tests/test_cli.py`, `README.md` · full: `steps.md#0003`
- `2026-10-25 09:33Z` @rjshrjndrn: Daemon lands: shellguard --serve answers check() over a 0600 unix socket in ~1 ms; flock (not bind) is the single-instance guard so racing clients can't orphan a daemon; exits on idle, model change, socket removal.
  files: `src/shellguard/daemon.py`, `src/shellguard/__main__.py`, `tests/test_daemon.py` · full: `steps.md#0004`
- `2026-10-25 09:37Z` @rjshrjndrn: decide.ts: pure allow/ask/failed/block logic for the pi hook; session allows keyed by whitespace-normalised part; asks list only parts not yet allowed; no UI blocks. node --test wired into make test.
  files: `hooks/pi/decide.ts`, `hooks/pi/decide.test.ts`, `Makefile`
- `2026-10-25 09:46Z` @rjshrjndrn: client.ts: connects to the daemon socket, spawns it detached on ENOENT/ECONNREFUSED and retries (respawn every 1.5 s covers losing the lock to a shutting-down daemon). Warm p50 0.84 ms from node.
  files: `hooks/pi/client.ts`, `hooks/pi/client.test.ts`
- `2026-10-25 09:55Z` @rjshrjndrn: pi extension works end to end in real pi: popup names only new flagged parts, s remembers them, arrows/esc deny, failure popup when shellguard is missing, /shellguard on|off|status, no-UI blocks with reason.
  files: `hooks/pi/index.ts`, `hooks/pi/menu.ts`, `hooks/pi/menu.test.ts` · full: `steps.md#0007`
- `2026-10-25 09:59Z` @rjshrjndrn: make hook-pi installs CLI (py3.12) + copies runtime .ts to ~/.pi/agent/extensions/shellguard and drops the daemon socket so a fresh daemon starts; unhook-pi removes both. Installed for real; pi -p blocked rm -rf with no --extension flag.
  files: `Makefile`, `README.md`, `tests/test_make_hook.py`
- `2026-10-25 09:59Z` @rjshrjndrn: status working → validating. Restart pi (or /reload): try a chain with rm -rf (popup names it), press s, repeat; /shellguard off|on|status; make unhook-pi removes it.
- `2026-10-25 10:11Z` @rjshrjndrn: status validating → working.
- `2026-10-25 10:18Z` @rjshrjndrn: 's' looked broken: memory worked, but each call added a new harmless echo that model A flagged (echo hi 0.81 > rm -rf 0.71). Harmless plain commands are no longer flagged; popup also shows already-allowed parts. Real pi replay: 1 popup, then none.
  files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `hooks/pi/menu.ts`, `hooks/pi/index.ts` · full: `steps.md#0009`
- `2026-10-25 10:18Z` @rjshrjndrn: status working → validating. Restart pi or /reload. Ask it to rm -rf a scratch dir a few times: one popup, s, then none. Mixed new + allowed parts show the allowed ones greyed.

