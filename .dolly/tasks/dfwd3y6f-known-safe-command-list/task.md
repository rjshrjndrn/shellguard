---
id: dfwd3y6f
slug: known-safe-command-list
title: known-safe command list
status: validating
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 3
spec_version: 1
created: 2026-10-25T15:15:12Z
updated: 2026-10-25T17:49:37Z
---

# dfwd3y6f · known-safe command list

<!-- dolly:header -->
`validating` · spec v1 · @rjshrjndrn · 3 steps · updated 2026-10-25 17:49Z
<!-- /dolly:header -->

## Spec

Grow chain.harmless into a Codex-style known-safe check: read-only commands + flag rules (find/rg/git/sed), pipes between safe commands, full-path match, secret path/name check. Safe -> model skipped. Goal: fewer false alarms on agent traffic, golden/hard still 25/25 and 42/42.

## Success Criteria

- [ ] _TBD_

## Full Context

- full spec + every superseded version: `context/spec.md`
- full context of every step: `context/steps.md`
- planning interview, when the task was planned: `context/plan.md`

## Log

- `2026-10-25 15:18Z` @rjshrjndrn: status todo → working.
- `2026-10-25 15:24Z` @rjshrjndrn: Known-safe read-only list (Codex-style) skips the model for grep/cat/head/find/rg/sed -n and pipes of them; secret paths still scored, git left out. Benign agent false alarms 37.3% -> 33.4%, golden/hard unchanged.
  files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `tests/test_chain.py`, `tests/test_check.py`, `README.md` · full: `steps.md#0001`
- `2026-10-25 15:24Z` @rjshrjndrn: status working → validating. Try it in pi after /reload: read-only commands should pass silently; decide whether to retrain on agent traffic next.
- `2026-10-25 15:56Z` @rjshrjndrn: find -delete bypass came from contradictory labels (safe 419 / dangerous 383); deletes/overwrites are now a syntax rule (1.0, no model) through wrappers, loops, pipes. Benign agent flags 1335->1338; README warns it's a classifier, not a guarantee.
  files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `tests/test_chain.py`, `tests/test_check.py`, `tests/test_daemon.py`, `README.md` · full: `steps.md#0002`
- `2026-10-25 17:49Z` @rjshrjndrn: Everyday git (status/add/commit/switch/stash...) is safe by rule; push, --amend, checkout -- ., restore, branch -d, stash drop, add of a secret always ask. Model had learned git words from 30/30 dangerous commit rows. Golden/hard unchanged.
  files: `src/shellguard/chain.py`, `tests/test_chain.py`, `tests/test_check.py`, `README.md` · full: `steps.md#0003`

