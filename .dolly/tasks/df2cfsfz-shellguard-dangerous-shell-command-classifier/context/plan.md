<!-- dolly plan · created 2026-10-24T12:58:38Z · @rjshrjndrn -->
# Plan — shellguard: dangerous shell command classifier

> Interview record. Every section below must be answered before `dolly plan finalize`.
> Gate: `dolly plan check` fails while a section is empty, `_TBD_`, or an Open Question is unchecked.

## Brief

Learn to build small focused models from zero. Build a classifier: give it a shell command, it says dangerous or safe. Dangerous = malicious (attacks) OR destructive (irreversible). Irreversible local change is the worst kind (e.g. git clean -fdx). Train on this Mac (M1 8GB). Compare no-base-model vs frozen base vs fine-tuned base.

## Problem

Coding agents (pi) and humans run shell commands that can attack the system or irreversibly destroy local data (git clean -fdx, rm -rf, dd of=/dev/..). Public datasets (bash-datasets, ShellRisk-Bench) label only malicious commands; 115 of 126 destructive-pattern rows in bash-datasets are labelled safe, so no off-the-shelf data covers the destructive half. Owner also has zero ML experience and wants to learn to build small focused models.

## Goal

A local CLI classifies a single shell command as dangerous or safe with a probability, in milliseconds on an M1. Dangerous = malicious OR irreversible-destructive. The model is chosen by measured recall on a held-out test set after comparing three approaches: no base model (char n-gram TF-IDF + logistic regression), frozen base model (bge-small embeddings + logistic regression), and fine-tuned base model (bge-small fine-tuned). Along the way the owner learns data labelling, train/test splits, baselines, evaluation and fine-tuning.

## Scope

In: single-line commands; labels dangerous/safe plus kind (malicious|destructive) for analysis; datasets bash-datasets + ShellRisk-Bench, deduplicated across both; hand-written and templated destructive examples; regex baseline; 3 models; evaluation; CLI.
Out: multi-command sessions/scripts, user intent or task context, auto-blocking hooks in pi (later task), LLM generative models (Qwen/Llama), cloud GPUs, Windows/PowerShell commands.

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

(guesses) pyproject.toml (uv), Makefile (test/train/eval), data/ (raw downloads gitignored, labelled splits), src/shellguard/{data,baseline,features,train,eval,cli}.py, tests/test_golden.py, tests/test_data.py, tests/test_cli.py, models/ (gitignored artefacts), docs/notes per lesson.

## Risks

- Destructive labels are hand/template made: model may learn template artefacts, not danger. Mitigate: hold out hand-written examples as test only, inspect errors.
- Dataset overlap (both use nl2bash, GTFOBins, Atomic Red Team) inflates scores. Mitigate: dedupe on normalised command before split.
- Imbalance (~5% dangerous) makes accuracy meaningless. Mitigate: report recall/precision/F1, PR curve.
- Same-source split overstates real-world performance (ShellRisk-Bench card says so). Mitigate: leave-one-source-out check.
- 8 GB RAM limits model C training. Mitigate: fine-tune bge-small (33M params), short seq len, small batch; fall back to frozen if OOM.
- Inference is CPU-only on an unknown target. Mitigate: every model is benchmarked CPU-only; models B/C must export to ONNX; latency and size are part of model selection, not an afterthought.
- Label boundary disputes (rm -rf ./build). Mitigate: written labelling rule in repo, golden set reviewed by owner.

## Test Plan

Unit: golden commands classified correctly (pytest, parametrised); train/test disjoint; label rule function on edge cases; CLI exit code + output format.
Eval (not pass/fail, recorded): recall/precision/F1 per model and per kind; confusion matrix; leave-one-source-out recall; latency per command.
Manual: owner runs CLI on 10 commands of their own choosing and reviews top-20 misclassifications.

## Open Questions

- [ ] Python level: (a) comfortable (b) can read, not write much (c) new?
- [ ] Labelling rule: strict (rm -rf ./build, node_modules = dangerous) or rebuildable-exception?
- [ ] git push --force, git reset --hard, curl ... | sh, sudo <anything>: dangerous?
- [ ] Integration target: language/runtime (pi extension = Node/TS? Go? Python?), CPU arch (x86_64/arm64), RAM, latency budget per command
- [ ] Call pattern: one process per command (cold start matters) or long-running service?

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

