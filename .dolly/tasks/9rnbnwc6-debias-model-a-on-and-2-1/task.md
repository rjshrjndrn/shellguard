---
id: 9rnbnwc6
slug: debias-model-a-on-and-2-1
title: debias model A on ~/ and 2>&1
status: validating
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 2
spec_version: 1
created: 2026-10-25T17:03:32Z
updated: 2026-10-25T17:14:04Z
---

# 9rnbnwc6 · debias model A on ~/ and 2>&1

<!-- dolly:header -->
`validating` · spec v1 · @rjshrjndrn · 2 steps · updated 2026-10-25 17:14Z
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

- `2026-10-25 17:05Z` @rjshrjndrn: status todo → working.
- `2026-10-25 17:08Z` @rjshrjndrn: Retrained with data/extra.csv: target ls -d ~/x ~/y 2>&1 drops 0.64->0.33 (now safe) and new ~/ safe exam rows average 0.27->0.15, but git branch -D main drops 0.369->0.301 and slips past check(). Fails the ship rule (hard recall 1.0->0.979); not shipped, awaiting owner call.
  files: `data/extra.csv`, `src/shellguard/prepare.py`, `data/hard.csv` · full: `steps.md#0001`
- `2026-10-25 17:14Z` @rjshrjndrn: Shipped retrained model A (owner accepted git branch -D main regression). Installed CLI now says safe at 0.327 for ls -d ~/x ~/y 2>&1. README check() numbers were stale (old model + current check = 493 FA, not 310); re-measured.
  files: `src/shellguard/model_a.joblib`, `results/model_a.json`, `README.md`, `tests/test_evaluate.py` · full: `steps.md#0002`
- `2026-10-25 17:14Z` @rjshrjndrn: status working → validating. Run /reload in pi, then retry ls -d ~/x ~/y 2>&1 (should run without a prompt). Accepted: git branch -D main no longer flagged.

