---
id: dfwd3y6f
slug: known-safe-command-list
title: known-safe command list
status: validating
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 1
spec_version: 1
created: 2026-10-25T15:15:12Z
updated: 2026-10-25T15:24:55Z
---

# dfwd3y6f · known-safe command list

<!-- dolly:header -->
`validating` · spec v1 · @rjshrjndrn · 1 step · updated 2026-10-25 15:24Z
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

