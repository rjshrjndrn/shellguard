<!-- dolly steps · task df2cfsfz · append-only, newest at the bottom -->
# Full step context — shellguard: dangerous shell command classifier

Short summaries live in `../task.md`. Each entry below is the full context of one step:
decisions and why, options rejected, gotchas, snippets, what to do next.

<!-- dolly:step 0001 -->
## 0001 · 2026-10-24T13:13:08Z · @rjshrjndrn

- task status: working
- files: none

Lesson 1 (golden set) landed.

- data/golden.csv: 48 commands (17 destructive, 8 malicious, 23 safe), real-looking (no example.com / <PATH>), columns command,label,kind,why. Never used for training.
- tests/test_golden_data.py: format checks, passes.
- tests/test_golden.py: spec for predict(cmd) -> {"label": "dangerous"|"safe", "probability": P(dangerous)}. All 48 fail with ImportError, by design (TDD red).
- Edge choices: rm -rf node_modules / ./build = safe (regenerable, matches dataset low+reversible). sudo systemctl status = safe. curl -o file (download only) = safe, curl | sh = malicious. rm -rf "$BUILD_DIR"/* = dangerous (empty var).
- csv.writer writes CRLF by default; converted to LF. Use lineterminator="\n" if regenerated.
- README documents all steps 0-9 + final output (model file JSON or ONNX, CLI printing JSON, exit 0 safe / 1 dangerous proposed).
- Dataset pinned: yannelli/cli-command-risk commit 5e1283ed01fef1ebe7453feaaf058d9cd5767384.
Next: lesson 2 = make data (download pinned parquet to data/raw).
<!-- /dolly:step 0001 -->

<!-- dolly:step 0002 -->
## 0002 · 2026-10-24T13:15:14Z · @rjshrjndrn

- task status: working
- files: none

Lesson 2 (download) landed.
- src/shellguard/data.py: urllib download of 3 parquet files from HF resolve URLs at REVISION 5e1283ed01fef1ebe7453feaaf058d9cd5767384 into data/raw/ (gitignored). `make data`.
- tests/test_download.py: sha256 per file == HF API lfs.oid; columns command/risk_level/reversible/risk_categories present; total rows 136,497.
- Surprise: dataset card says 124,923 rows / 25,702 distinct; real files 136,497 rows / 28,296 distinct. Card stale. README fixed.
- 13 commands have >1 distinct (risk_level, reversible) across copies -> step 3 must pick a rule (suggest: dangerous if ANY copy is dangerous, matches recall-first goal).
- DuckDB 2.0 python: relation.fetchone() removed -> use fetchall().
- duckdb added as runtime dep (used for data prep).
Next: step 3 prepare (dedupe, label rule, conflict rule, stratified 80/20 split, disjointness test). Balance estimate ~14.4k/13.9k was from earlier wrong-card numbers; recompute.
<!-- /dolly:step 0002 -->

<!-- dolly:step 0003 -->
## 0003 · 2026-10-24T13:17:48Z · @rjshrjndrn

- task status: working
- files: none

Lesson 3 (prepare) landed. make prepare -> data/{train,test}.parquet.
- SQL (DuckDB): GROUP BY command; label = dangerous if NOT bool_and(reversible) OR bool_or(risk_level in high/critical) (any copy dangerous wins; 13 conflicting cmds, all critical/high or irreversible anyway); categories = union; exclude golden commands; ORDER BY command for determinism.
- sklearn train_test_split(test_size=0.2, stratify=label, random_state=42).
- Result: 28,280 cmds (28,296 - 16 golden overlap). train 22,624 / test 5,656, both 50.7% dangerous.
- Big catch: 16 of 48 golden commands appear verbatim in the dataset (git clean -fdx, rm -rf ~, ls -la, ...). Removed from train+test so golden stays an unseen exam.
- Known limit, not fixed: template near-duplicates (git push -f origin main/develop) cross the split -> test metrics optimistic. Golden set is the honest check. Could do grouped split later if gap between test and golden is large.
- Test perf: building union per parametrised case cost 15s; dict lookup -> 1.2s.
- Deps added: scikit-learn, pandas.
Next: step 4 regex baseline (set the floor), then step 5 model A.
<!-- /dolly:step 0003 -->

<!-- dolly:step 0004 -->
## 0004 · 2026-10-24T13:21:34Z · @rjshrjndrn

- task status: working
- files: none

Lesson 4 (regex baseline + scorer) landed.
- baseline.py: 17 regexes, IGNORECASE, any match -> dangerous p=1.0. Written without looking at test data.
- evaluate.py: score() hand-rolled tp/fn/fp/tn/recall/precision/f1/accuracy (dangerous = positive); run(name) imports shellguard.<name>.predict, scores test.parquet + golden.csv, times us/command over test, writes results/<name>.json (committed dir; moved from gitignored models/).
- make eval MODEL=baseline.
- FLOOR: test recall 0.236 precision 0.920 f1 0.375 (missed 2192, FA 59); golden recall 0.760 precision 1.0 (6 misses: git stash clear, > ~/.bashrc, find -type f -delete, docker volume rm, aws creds | curl, history -c); ~4 us/cmd.
- Golden baseline is flattering (same author as golden). Test split is the honest number for baseline.
- Misses by category: data_destruction 734, device_overwrite 504, overbroad_permissions 462, shell_footgun 236, credential_exposure 222.
- Dataset nuance: mkfs.* -n / -N (dry run) labelled safe -> regex false alarms. Some labels look noisy: "yes sample > ./node_modules/.cache/test.img" dangerous.
Next: step 5 model A (TF-IDF char n-grams + logistic regression). Must export to a CPU-only artefact; plan JSON weights or joblib first, decide in step 8.
<!-- /dolly:step 0004 -->

<!-- dolly:step 0005 -->
## 0005 · 2026-10-24T13:29:54Z · @rjshrjndrn

- task status: working
- files: none

Lesson 5 (model A) landed.
- model_a.py: Pipeline(TfidfVectorizer(char, 2-5, min_df=2, sublinear_tf), LogisticRegression(max_iter=1000)); joblib save/load (pickle, trusted-only); predict(cmd, model=None) lazy-loads models/model_a.joblib; threshold 0.5.
- make train MODEL=model_a: 2.4s, 40,965 features, 1.1 MB.
- Results: test recall 0.986 precision 0.973 F1 0.980 (41 missed, 77 FA); golden recall 0.88 precision 0.846 F1 0.863 (3 missed, 4 FA); 250 us/cmd CPU.
- Train recall 0.990 -> no overfitting in-distribution.
- Golden misses = data gaps: fork bomb (0 in train), git stash clear (0), kubectl delete namespace (11 rows, p=0.44).
- Golden false alarms = shortcut learning: cat /etc/hosts 0.94 (/etc/ 332 dangerous vs 36 safe in train), echo $PATH 0.86 (echo 499 vs 101), tar -czf 0.69, rm -rf node_modules 0.69.
- Rule kept: never tune on golden. Fixes must come from training data (e.g. add safe /etc reads, fork bombs) or better models.
- Golden tests (tests/test_golden.py) still red: they import shellguard.predict, wired only in step 8 after choosing a model.
Next: step 6 model B (frozen bge-small via fastembed + logreg). Hypothesis: semantic embeddings may reduce /etc/ shortcut false alarms but may lose exact-token signal like -fdx.
<!-- /dolly:step 0005 -->
