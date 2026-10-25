---
id: nf4y9gf5
slug: check-shell-heredoc-bodies-as-scripts
title: check shell heredoc bodies as scripts
status: validating
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 1
spec_version: 1
created: 2026-10-25T17:03:32Z
updated: 2026-10-25T17:18:31Z
---

# nf4y9gf5 · check shell heredoc bodies as scripts

<!-- dolly:header -->
`validating` · spec v1 · @rjshrjndrn · 1 step · updated 2026-10-25 17:18Z
<!-- /dolly:header -->

## Spec

bash/sh/zsh/dash (+ -s) reading a quoted heredoc: the body is a shell script but tree-sitter leaves it as one opaque heredoc_body, so destructive()/split_chain never see rm -rf inside; only the model catches it. Strip header/footer and run the body through the same chain checks. Non-shell readers (python, cat) unchanged.

## Success Criteria

- [ ] _TBD_

## Full Context

- full spec + every superseded version: `context/spec.md`
- full context of every step: `context/steps.md`
- planning interview, when the task was planned: `context/plan.md`

## Log

- `2026-10-25 17:14Z` @rjshrjndrn: status todo → working.
- `2026-10-25 17:18Z` @rjshrjndrn: Shell heredoc bodies are now split and checked like chains: rm -rf inside bash <<'EOF' is flagged 1.0 by rule, not by luck of the whole-command score. Text/python/bash file.sh/bash -c heredocs unchanged.
  files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `tests/test_chain.py`, `tests/test_check.py`, `README.md` · full: `steps.md#0001`
- `2026-10-25 17:18Z` @rjshrjndrn: status working → validating. Run /reload in pi; try bash <<'EOF' with rm -rf inside - should flag the rm line at 1.0.

