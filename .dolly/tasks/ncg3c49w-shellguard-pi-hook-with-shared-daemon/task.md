---
id: ncg3c49w
slug: shellguard-pi-hook-with-shared-daemon
title: shellguard pi hook with shared daemon
status: working
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 3
spec_version: 2
created: 2026-10-25T09:11:26Z
updated: 2026-10-25T09:27:52Z
---

# ncg3c49w · shellguard pi hook with shared daemon

<!-- dolly:header -->
`working` · spec v2 · @rjshrjndrn · 3 steps · updated 2026-10-25 09:27Z
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

