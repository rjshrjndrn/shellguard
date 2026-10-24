<!-- dolly plan · created 2026-10-24T12:58:38Z · @rjshrjndrn -->
# Plan — shellguard: dangerous shell command classifier

> Interview record. Every section below must be answered before `dolly plan finalize`.
> Gate: `dolly plan check` fails while a section is empty, `_TBD_`, or an Open Question is unchecked.

## Brief

Learn to build small focused models from zero. Build a classifier: give it a shell command, it says dangerous or safe. Dangerous = malicious (attacks) OR destructive (irreversible). Irreversible local change is the worst kind (e.g. git clean -fdx). Train on this Mac (M1 8GB). Compare no-base-model vs frozen base vs fine-tuned base.

## Problem

Coding agents (pi) and humans run shell commands that can attack the system or irreversibly destroy local data (git clean -fdx, rm -rf, dd of=/dev/..). Owner has zero ML experience and wants to learn to build small focused models. Data: bash-datasets and ShellRisk-Bench label only malicious commands (115 of 126 destructive-pattern rows in bash-datasets are labelled safe). yannelli/cli-command-risk (HF, CC-BY-4.0, 2026-10) labels both, with a reversible flag.

## Goal

A local CLI classifies a single shell command as dangerous or safe with a probability, in milliseconds on an M1. Dangerous = malicious OR irreversible-destructive. The model is chosen by measured recall on a held-out test set after comparing three approaches: no base model (char n-gram TF-IDF + logistic regression), frozen base model (bge-small embeddings + logistic regression), and fine-tuned base model (bge-small fine-tuned). Along the way the owner learns data labelling, train/test splits, baselines, evaluation and fine-tuning.

## Scope

In: single-line commands; label dangerous/safe derived from cli-command-risk (risk_level + reversible), keep category for error analysis; dedupe by command (dataset repeats each command across 5 shells) and re-split ourselves; hand-written golden set as a separate real-world test; regex baseline; models A/B/C; CPU-only evaluation; CLI.
Out: multi-command scripts, user intent/context, pi integration (later task), generative LLMs, cloud GPUs, Windows/PowerShell. bash-datasets/ShellRisk-Bench only if malicious recall is weak.

## Success Criteria

- [ ] Golden test set (~40 hand-labelled commands incl. git clean -fdx, rm -rf ~, dd of=/dev/sda, reverse shell) exists before any model, and the chosen model passes all of it
- [ ] No command string appears in both train and test (asserted by test)
- [ ] Regex baseline recall/precision recorded as the floor
- [ ] Models A, B, C each report recall, precision, F1 overall and per kind on the same test split
- [ ] Every model's inference benchmarked CPU-only (GPU/MPS/CoreML disabled): latency per command, cold start, artefact size
- [ ] Chosen model has higher recall on dangerous than the regex baseline, at a threshold picked from the precision/recall curve
- [ ] shellguard "<cmd>" prints label + probability on a CPU-only machine; CLI covered by a test
- [ ] Each lesson = one commit with tests written first

## Changes

(guesses) pyproject.toml (uv), Makefile (test/data/train/eval), data/raw (gitignored parquet downloads), data/golden.csv (hand-labelled, committed), src/shellguard/{data,baseline,train,evaluate,cli}.py, tests/test_golden.py, tests/test_data.py, tests/test_cli.py, models/ (gitignored artefacts), notes/ per lesson.

## Risks

- Synthetic data: commands use placeholders (<PATH>, example.com, RFC 5737 IPs); model may learn 'example.com = dangerous'. Mitigate: golden set of real-looking commands kept out of training; inspect errors.
- Leakage: each command appears under 5 shells and 22 commands span the shipped splits. Mitigate: dedupe on command, re-split, assert disjoint by test.
- Label noise: dataset itself is inconsistent at the edge (find . -name *.o -delete irreversible, rm -rf ./build reversible). Mitigate: written label rule, review top errors, golden set decides disputes.
- 8 GB RAM limits model C training. Mitigate: fine-tune bge-small (33M), short seq len, small batch; fall back to frozen if OOM.
- Inference CPU-only on unknown target. Mitigate: benchmark every model with GPU/MPS/CoreML off; B/C must export to ONNX; latency and size count in model choice.

## Test Plan

Unit: golden commands classified correctly (pytest, parametrised); train/test disjoint; label rule function on edge cases; CLI exit code + output format.
Eval (not pass/fail, recorded): recall/precision/F1 per model and per kind; confusion matrix; leave-one-source-out recall; latency per command.
Manual: owner runs CLI on 10 commands of their own choosing and reviews top-20 misclassifications.

## Open Questions

- [x] Python level: (a) comfortable
- [x] Dataset: use yannelli/cli-command-risk, add golden set by hand
- [x] Integration target / call pattern: deferred until model exists
- [x] Label rule: dangerous = NOT reversible OR risk_level in (high, critical)

## Q&A

**Q (2026-10-24 12:58Z):** What counts as dangerous?

**A:** Both malicious (attacks: reverse shells, privesc, exfil) and destructive (irreversible changes).

**Q (2026-10-24 12:58Z):** Which error is worse?

**A:** An irreversible local change is the worst outcome; git clean -fdx is the example. So missing a dangerous command (false negative) costs more than a false alarm: optimise recall.

**Q (2026-10-24 12:58Z):** Hardware?

**A:** Train on this Mac: Apple M1, 8 GB RAM, 4P+4E cores, MPS available.

**Q (2026-10-24 12:58Z):** Where does the code live?

**A:** New repo ~/Documents/projects/personal/shellguard (git init done, dolly store local).

**Q (2026-10-24 13:01Z):** Where must the model run?

**A:** Inference must run on CPU only: the integration target may have no GPU. Training may use the M1. Measured on M1 CPU: TF-IDF+logreg 215 us/cmd; bge-small ONNX CPU embedding 3.5 ms/cmd, 64 MB model.

**Q (2026-10-24 13:07Z):** Python level?

**A:** (a) comfortable. Explain ML concepts, not Python syntax.

**Q (2026-10-24 13:07Z):** Build our own dataset or use existing?

**A:** Existing first. Exa found yannelli/cli-command-risk (HF, CC-BY-4.0, 25,702 distinct commands, risk_level safe..critical + reversible flag + categories). It covers destructive AND malicious and its labels match the owner's probes: git clean -fdx / git reset --hard / git push -f = irreversible; rm -rf ./build and node_modules = low, reversible; rm -rf ~ and / = critical. bash-datasets + ShellRisk-Bench only label malicious, so they become extra malicious data at most. Own work = hand-written golden set, not a whole dataset.

**Q (2026-10-24 13:07Z):** Integration target and call pattern?

**A:** Deferred: build the model first, decide integration later. Constraint kept: inference CPU-only.

**Q (2026-10-24 13:10Z):** Label rule?

**A:** Confirmed: dangerous = NOT reversible OR risk_level in (high, critical).

