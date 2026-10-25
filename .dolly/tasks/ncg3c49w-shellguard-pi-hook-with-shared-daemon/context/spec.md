<!-- dolly spec · task ncg3c49w -->
# Spec — shellguard pi hook with shared daemon

**current: v3** · updated 2026-10-25T10:51:57Z by @rjshrjndrn · superseded versions are kept at the bottom of this file

<!-- dolly:spec-current -->
<!-- v3 · 2026-10-25T10:51:57Z · @rjshrjndrn -->

# shellguard pi hook with shared daemon (v2)

Before pi runs a bash command, shellguard scores it in ~1 ms via a shared daemon; dangerous ones stop and ask (allow once / allow for session / deny), naming the flagged parts of a chain.

Verdict (check()):
- chain split with tree-sitter-bash on && || ; newline (never |, quotes, $( ), loops, heredocs)
- harmless plain parts (echo printf true false : pwd cd ls test [ sleep which type, no redirect/substitution/env assignment/secret-looking variable) are never flagged; all-harmless command -> safe 0.0
- dangerous if the whole command OR any non-harmless part >= 0.35 (v1: whole only)
- danger_probability = max(whole, parts); flagged = parts >= 0.35 highest first, else whole
- session allow = exact flagged part incl. path, whitespace-insensitive

Measured (test split): hook recall 0.991, 40 missed, 310 false alarms (model alone 0.988 / 56 / 281).
<!-- /dolly:spec-current -->

---

## Superseded versions

<!-- dolly:spec-history -->
## v2 — 2026-10-25T09:11:49Z · @rjshrjndrn

> superseded by v3: Whole-command-only verdict let long scripts dilute a dangerous line (rm -rf after a 25-line heredoc scored 0.208 and ran unprompted); harmless-part rule added; secret-variable echos scored again.

# shellguard pi hook with shared daemon

## Problem

pi runs agent bash commands without a second look. shellguard model A can flag dangerous ones, but its CLI takes ~1.1 s per call (707 ms sklearn import + 247 ms model load; scoring itself is 0.55 ms), too slow for every bash call.

## Goal

Before pi runs a bash command, shellguard scores it in ~1 ms; dangerous ones stop and ask the user, with the flagged part of a chain named and rememberable for the session.

## Scope

In:
- shellguard serve: shared daemon on a unix socket, JSON line protocol
- chain split (&& || ; newline, never |) only when the whole command is flagged
- pi extension in repo (hooks/pi/), installed by make hook-pi (copy), removed by make unhook-pi
- popup: Allow once (enter) / Allow for this session (s) / Deny (d, esc), arrow+enter too
- /shellguard on|off|status, session-scoped
- failure popup: shellguard failed, run anyway?
Out:
- Claude Code hook (later, reuses the socket)
- TS port of the model
- prefix/regex allow rules
- persisting allows across sessions

## Success Criteria

- [ ] warm check p50 <= 5 ms measured end to end from the extension
- [ ] cd /tmp && rm -rf build && ls -> popup names rm -rf build; allow for session lets a later chain with only that flagged part run without asking
- [ ] safe command runs with no popup
- [ ] daemon killed -> next call respawns; socket missing -> spawn; two clients at once -> one daemon
- [ ] retrained model -> daemon replaced on next session start
- [ ] /shellguard off -> no checks; on -> checks resume
- [ ] shellguard broken -> failure popup; no UI -> blocked
- [ ] make hook-pi installs, make unhook-pi removes; make test green

## Changes

- src/shellguard/chain.py: split_chain(cmd) using tokens._split; quote-aware
- src/shellguard/daemon.py: serve() on ~/.cache/shellguard/sock (dir 0700); request {cmd} -> {label, danger_probability, flagged:[parts], model_sha}; idle exit 30 min; bind race = second loses and connects
- __main__.py: shellguard serve subcommand
- hooks/pi/client.ts: connect, else remove stale socket + spawn detached daemon + retry; restart daemon if model_sha differs from disk; 1 s timeout
- hooks/pi/decide.ts: pure (result, allowedSet, enabled, hasUI) -> allow|ask|block
- hooks/pi/index.ts: tool_call wiring, ctx.ui.custom popup, /shellguard command, status bar
- Makefile: hook-pi, unhook-pi; README section

## Risks

- stale daemon after retrain/reinstall -> model_sha handshake
- orphan daemon -> 30 min idle exit
- spawn race -> socket bind is the lock
- daemon down/slow -> failure popup, 1 s timeout, block when no UI
- split false alarms on short parts -> split only after whole chain is flagged
- 185 MB RSS for the shared daemon

## Test Plan

- pytest: split_chain (quotes, operators, pipes kept, unbalanced quotes -> whole), daemon protocol over a real socket in tmp dir (score, flagged parts, model_sha, idle exit with short timeout, bind race)
- node --test: decide.ts truth table; client.ts against a real daemon (spawn, stale socket, sha mismatch restart, timeout -> error)
- manual in pi: popup keys, session allow, /shellguard off/on, failure popup; measure latency

## Open Questions

- [x] all resolved in Q&A

## Decisions (from planning Q&A)

**Q (2026-10-25 09:11Z):** Score whole chain or each part?

**A:** Whole chain decides; split only when flagged, to name and remember the dangerous parts. Pipes never split.

**Q (2026-10-25 09:11Z):** What does allow for session remember?

**A:** The flagged parts (whitespace-normalised); whole chain if no part is flagged on its own.

**Q (2026-10-25 09:11Z):** shellguard fails?

**A:** Failure popup: run anyway or deny. No UI -> block.

**Q (2026-10-25 09:11Z):** TS port or daemon?

**A:** Shared daemon on a unix socket, spawned detached by the first agent, reused by others.

**Q (2026-10-25 09:11Z):** Install?

**A:** make hook-pi copies the extension into ~/.pi/agent/extensions/shellguard/. pi only for now.

## v1 — 2026-10-25T09:11:26Z · @rjshrjndrn

> superseded by v2: planning finished — spec derived from plan.md

# shellguard pi hook with shared daemon

_Spec is being written by the planning interview. See `plan.md`._
<!-- /dolly:spec-history -->
