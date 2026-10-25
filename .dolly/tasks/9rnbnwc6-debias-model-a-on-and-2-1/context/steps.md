<!-- dolly steps · task 9rnbnwc6 · append-only, newest at the bottom -->
# Full step context — debias model A on ~/ and 2>&1

Short summaries live in `../task.md`. Each entry below is the full context of one step:
decisions and why, options rejected, gotchas, snippets, what to do next.

<!-- dolly:step 0001 -->
## 0001 · 2026-10-25T17:08:21Z · @rjshrjndrn

- task status: working
- files: `data/extra.csv`, `src/shellguard/prepare.py`, `data/hard.csv`

Fair comparison: old split rebuilt from f6805cc prepare.py into /tmp/oldsplit; scored both models on the 2193 test rows unseen by both: old recall 0.9892 (14 missed, 71 FA), new 0.9876 (16 missed, 74 FA) - within noise. Hard: FA 10->9, 1 new miss (git branch -D main, was only 0.019 over threshold before). destructive() does not cover git branch -D, so check() now says safe. Models: /tmp/model_a_before.joblib, /tmp/model_a_after.joblib; src/shellguard/model_a.joblib currently = after (git-ignored, not installed). Options: accept; add git branch -D twins to extra (risks teaching to the exam); add git branch -D/--force-delete to destructive(); or drop the retrain.
<!-- /dolly:step 0001 -->

<!-- dolly:step 0002 -->
## 0002 · 2026-10-25T17:14:03Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/model_a.joblib`, `results/model_a.json`, `README.md`, `tests/test_evaluate.py`

Commits c398e94 (hard exam rows), f41fd3c (extra.csv + prepare), f78b302 (evaluate test size), f6f1dd3 (model + README). make test: 424 py + 55 node pass. make hook-pi run; pi needs /reload. Follow-up candidates: destructive() rule for git branch -D / --delete --force; check() false alarms on test are 515 (most from non-harmless parts) - worth its own look.
<!-- /dolly:step 0002 -->
