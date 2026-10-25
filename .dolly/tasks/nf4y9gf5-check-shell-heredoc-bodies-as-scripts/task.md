---
id: nf4y9gf5
slug: check-shell-heredoc-bodies-as-scripts
title: check shell heredoc bodies as scripts
status: todo
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 0
spec_version: 1
created: 2026-10-25T17:03:32Z
updated: 2026-10-25T17:03:32Z
---

# nf4y9gf5 · check shell heredoc bodies as scripts

<!-- dolly:header -->
`todo` · spec v1 · @rjshrjndrn · 0 steps · updated 2026-10-25 17:03Z
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

_no steps yet_
