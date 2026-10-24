---
id: df2cfsfz
slug: shellguard-dangerous-shell-command-classifier
title: "shellguard: dangerous shell command classifier"
status: working
owner: rjshrjndrn
collaborators: [rjshrjndrn]
tags: []
steps: 3
spec_version: 2
created: 2026-10-24T12:58:38Z
updated: 2026-10-24T13:17:48Z
---

# df2cfsfz · shellguard: dangerous shell command classifier

<!-- dolly:header -->
`working` · spec v2 · @rjshrjndrn · 3 steps · updated 2026-10-24 13:17Z
<!-- /dolly:header -->

## Spec

A local CLI classifies a single shell command as dangerous or safe with a probability, in milliseconds on an M1. Dangerous = malicious OR irreversible-destructive. The model is chosen by measured recall on a held-out test set after comparing three approaches: no base model (char n-gram TF-IDF + logistic regression), frozen base model (bge-small embeddings + logistic regression), and fine-tuned base model (bge-small fine-tuned). Along the way the owner learns data labelling, train/test splits, baselines, evaluation and fine-tuning.

Full spec: `context/spec.md` · plan: `context/plan.md`

## Success Criteria

- [ ] Golden test set (~40 hand-labelled commands incl. git clean -fdx, rm -rf ~, dd of=/dev/sda, reverse shell) exists before any model, and the chosen model passes all of it
- [ ] No command string appears in both train and test (asserted by test)
- [ ] Regex baseline recall/precision recorded as the floor
- [ ] Models A, B, C each report recall, precision, F1 overall and per kind on the same test split
- [ ] Every model's inference benchmarked CPU-only (GPU/MPS/CoreML disabled): latency per command, cold start, artefact size
- [ ] Chosen model has higher recall on dangerous than the regex baseline, at a threshold picked from the precision/recall curve
- [ ] shellguard "<cmd>" prints label + probability on a CPU-only machine; CLI covered by a test
- [ ] Each lesson = one commit with tests written first

## Full Context

- full spec + every superseded version: `context/spec.md`
- full context of every step: `context/steps.md`
- planning interview, when the task was planned: `context/plan.md`

## Log

- `2026-10-24 13:10Z` @rjshrjndrn: status planning → working.
- `2026-10-24 13:10Z` @rjshrjndrn: spec → v2. planning finished — spec derived from plan.md
  previous version kept in `spec.md`

### plan finalized · 2026-10-24 13:10Z · @rjshrjndrn

Plan complete. Status → todo.

- plan: `context/plan.md`
- `2026-10-24 13:10Z` @rjshrjndrn: status todo → working.
- `2026-10-24 13:13Z` @rjshrjndrn: Golden set (48 real-looking cmds) is the spec; 48 golden tests red until a model exists. README documents every step, dataset pinned to HF commit 5e1283e.
  full: `steps.md#0001`
- `2026-10-24 13:15Z` @rjshrjndrn: make data downloads pinned HF parquet, sha256-verified. Real files hold 136,497 rows / 28,296 distinct commands (card stale); 13 commands carry conflicting labels for step 3.
  full: `steps.md#0002`
- `2026-10-24 13:17Z` @rjshrjndrn: Prepared 28,280 labelled commands, split 22,624/5,656 at 50.7% dangerous. 16 golden commands were in the dataset verbatim; removed so the exam stays unseen. Template near-dupes still cross the split (known optimism).
  full: `steps.md#0003`

