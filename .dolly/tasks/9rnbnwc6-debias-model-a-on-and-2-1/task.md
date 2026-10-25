---
id: 9rnbnwc6
slug: debias-model-a-on-and-2-1
title: debias model A on ~/ and 2>&1
status: todo
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 0
spec_version: 1
created: 2026-10-25T17:03:32Z
updated: 2026-10-25T17:03:32Z
---

# 9rnbnwc6 · debias model A on ~/ and 2>&1

<!-- dolly:header -->
`todo` · spec v1 · @rjshrjndrn · 0 steps · updated 2026-10-25 17:03Z
<!-- /dolly:header -->

## Spec

Model A learned ~/ (76% dangerous) and 2>&1 (95%, n=21) as danger tokens: ls -d ~/x ~/y 2>&1 scores 0.64. Add hand-written paired safe/dangerous rows (data/extra.csv) merged by prepare() into train+test; add measurement cases to hard.csv (exam). Ship only if dangerous recall does not drop on test/golden/hard and hard safe false alarms fall.

## Success Criteria

- [ ] _TBD_

## Full Context

- full spec + every superseded version: `context/spec.md`
- full context of every step: `context/steps.md`
- planning interview, when the task was planned: `context/plan.md`

## Log

_no steps yet_
