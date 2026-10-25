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

<!-- dolly:step 0006 -->
## 0006 · 2026-10-24T13:37:33Z · @rjshrjndrn

- task status: working
- files: `results/baseline.json`

Lesson 6 (model B, frozen base) landed. Hypothesis refuted.
- model_b.py: fastembed TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=models/fastembed, providers=["CPUExecutionProvider"]) cached via functools.cache; embed batch 256; LogisticRegression(max_iter=1000) head saved joblib (2 KB). Base model 64 MB in models/fastembed (gitignored).
- CPU-only asserted: encoder().model.model.get_providers() == ["CPUExecutionProvider"] (CoreML present on this Mac, so must be explicit).
- Train 265 s wall / 1043 s CPU, 1.27 GB RSS (embedding 22,624 cmds dominates).
- Results: test recall 0.916 precision 0.872 F1 0.893 (241 missed, 387 FA); golden recall 0.84 precision 0.75 F1 0.792 (11 wrong); 5.6 ms/cmd single-call CPU.
- vs A: worse everywhere (A: 0.986/0.973/0.980, golden 0.863, 250 us, 1.1 MB).
- Root cause measured: bge-small cosine sim rm -rf / vs rm -rf ./build = 0.91; git clean -fdx vs git clean -n = 0.84. Sentence encoder erases the path/flag detail that decides danger; linear head can't recover it.
- Did not try: MLP head, other encoders (code-specific like jina-code / CodeBERT). Possible but out of plan.
Next: step 7 fine-tune bge-small (MPS for training allowed, export ONNX, CPU inference). 8 GB RAM risk. Key question to measure: does fine-tuning pull rm -rf / and rm -rf ./build apart, and does it beat A at all? If not, A ships.
<!-- /dolly:step 0006 -->

<!-- dolly:step 0007 -->
## 0007 · 2026-10-24T14:09:39Z · @rjshrjndrn

- task status: working
- files: none

Lesson 7 (model C, fine-tuned bge-small) landed.
- model_c.py: AutoModelForSequenceClassification(bge-small, 2 labels), manual loop: AdamW lr 5e-5 wd 0.01, linear warmup 10%, batch 32, 2 epochs, seed 42, padding="max_length" 64 tokens. MPS if available. Export torch.onnx.export(dynamo=True, dynamic batch/seq, external_data=False) + tokenizer.json via tok.backend_tokenizer.save. Inference: tokenizers + onnxruntime CPUExecutionProvider + softmax; torch/transformers imported only inside finetune/export.
- torch/transformers/onnx/onnxscript are dev deps only.
- 8 GB issue: dynamic padding run swapped (4.3 GB, 22% CPU, 13 min, killed). 40-step benchmarks: mps fixed 381ms/step, mps dynamic 282, cpu dynamic 326 (CPU only ~15% slower than MPS here). Fixed padding run: MPS driver mem flat 2.30 GB all 1414 steps, 572 s, peak RSS 1.56 GB. Root cause (shape-cache growth) inferred, not proven.
- Loss 0.69 -> 0.10 (end ep1) -> ~0.02.
- Results CPU: test recall 0.985 precision 0.987 F1 0.986 (43 missed, 36 FA); golden recall 0.92 precision 0.958 F1 0.939, wrong: git stash clear, nc -e /bin/sh (p=0.00!), cat /etc/hosts. 14.2 ms/cmd, 135 MB fp32 onnx.
- vs A: golden 3 wrong vs 7; test precision better; 57x slower, 120x bigger.
- nc -e: 0 occurrences in train -> C confidently wrong (0.00), A unsure (0.64). Over-confidence on unseen patterns.
- Tests (7): ONNX == torch within 1e-4; CPU-only provider; fresh process imports no torch/transformers; load() string path bug found+fixed.
- Warnings from dynamo exporter about axis names sharing constraints: harmless.
Next: step 8 choose. Options: A (fast/tiny) vs C (better golden). Try int8 dynamic quantisation of C (onnxruntime.quantization.quantize_dynamic) to cut size/latency; tune threshold on a validation slice of TRAIN (not test, not golden); then wire shellguard.predict and turn golden tests green or document remaining misses. Data gaps (nc -e, git stash clear, /etc reads) are a candidate follow-up: add hand examples to TRAIN.
<!-- /dolly:step 0007 -->

<!-- dolly:step 0008 -->
## 0008 · 2026-10-24T15:59:26Z · @rjshrjndrn

- task status: working
- files: none

Step 8 a-d landed; threshold (8e) and wiring pending owner choice.
- 8a data/hard.csv: 55 probes (42 dangerous, 13 safe lookalikes), kinds rce/obfuscated/indirect_delete/footgun/git/exfil/persist/cloud/lookalike. Excluded from train/test (8 verbatim overlaps). evaluate reports test+golden+hard. git branch -D main = dangerous (owner), dataset says low/reversible.
- 8b HF search: patronus-studio/cat-shell-risk-commander (tfidf+logreg JSON) golden 37/48 hard 35/55 vs ours A 41/48 44/55; misses git clean -fdx. Others: 3B LLM, ModernBERT 150M, paiml 63% acc. Dataset tomngdev/shell-safety-v1.1 (MIT) added.
- Second source: shell-safety pinned fee89770; deny/ask -> dangerous (owner: in doubt, dangerous), allow -> safe; any-copy rule across both sources; raw files moved to data/raw/<dataset>/. Pool 42,009 cmds (53.9% dangerous), train 33,607 / test 8,402.
- Before->after on exams: A misses 11->4, FA 8->11; C misses 8->5, FA 5->9.
- Model C crash: Mac froze + rebooted mid-training (boot failure count 1). PyTorch MPS default high watermark 1.7x recommended (5.73 GB) = 9.7 GB on 8 GB machine -> swaps instead of OOM. Fix: setdefault PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.6, LOW=0.5 (high alone rejected: "invalid low watermark ratio 1.4"). batch 32 OOMed at the cap with 128 tokens; batch 16 fits at 2.34 GB. MAX_TOKENS 64->128 (p99 136 tokens). 32 min training. Machine stalls periodically under load during training.
- C inference now ~26 ms (was 13.5) on same hardware; cause not investigated (A unchanged at ~0.3 ms so CPU not throttled).
- Pick: A (exam misses 4 vs 5, ~90x faster, ~40x smaller). B not retrained.
- Threshold: 5-fold OOF on train: 0.50 rec .953 prec .949; 0.40 .974/.919; 0.35 .983/.895; 0.30 .988/.867; 0.25 .993/.835; 0.20 .997/.797. Waiting for owner.
- Open: golden tests require all 48 correct; A gets 41. Options: xfail(strict) the known misses with reasons, or keep red.
Next: set threshold in model_a, wire shellguard.predict -> model_a, resolve golden test policy, then step 9 CLI.
<!-- /dolly:step 0008 -->

<!-- dolly:step 0009 -->
## 0009 · 2026-10-24T16:38:17Z · @rjshrjndrn

- task status: working
- files: none

Shell-aware features for model A (owner insight: space has meaning in shell).
- tokens.py: shell_tokens via shlex(posix=False, punctuation_chars="();<>|&\n", whitespace " \t\r", wordchars=all printable except space/quotes/punct, commenters=""). Tags cmd:/flag:/arg:/op:, q: prefix for quoted data, except bash/sh -c, eval, and "$(...)"/backticks in double quotes (code). Comments dropped at word start. Wrappers sudo/xargs/env/... -> next word is cmd. Bare $ -> arg:$. newline -> op:;. Unbalanced quote -> err:unbalanced + whitespace split. shell_features adds neighbour pairs (module-level so joblib can pickle it).
- Known tokenizer shortcut: posix=False splits --data="a b" into two words.
- model_a: make_union(char 2-5 lowercase=False, TfidfVectorizer(analyzer=shell_features)) + LogisticRegression(max_iter=2000). 149,125 features, 4.5 MB, ~611 us/cmd (was 268).
- Variant comparison (same split): A test F1 .966 309 wrong; A1 case only .966; A2 +shell .975; A3 +pairs .977 213 wrong. Exams flat (15->16 wrong). OOF @.35: 300/2090 -> 200/1353.
- Motivating cases barely moved: rm -rf ~/ .cache 0.69 == ~/.cache 0.69; branch -D 0.49 vs -d 0.50; grep "rm -rf" fixed 0.39->0.15. Cause: training data has 0 stray-space rows, 4 branch -D, 2 branch -d (all dangerous). Unit test proves the features CAN learn -D vs -d from 6 rows.
- New OOF threshold table: .50 518/573, .40 268/1014, .35 200/1353, .30 124/1783, .25 87/2446.
Next: owner picks threshold; then wire shellguard.predict, xfail known golden misses, re-score. Data follow-up for the motivating cases (stray space, branch -D/-d, mention vs execution).
<!-- /dolly:step 0009 -->

<!-- dolly:step 0010 -->
## 0010 · 2026-10-24T16:51:05Z · @rjshrjndrn

- task status: working
- files: none

Steps 8f, 8g, 9 landed. Model A shipped with a CLI.
- 8f threshold 0.35 (THRESHOLD const in model_a). Shipped-model runs: 0.50 misses git clean -fdx (p=0.4999); 0.35 = 0 dangerous exam misses, test recall .988, 56 missed / 281 FA (was 107/106 at .5). Exams were looked at per-threshold -> no longer fully unseen for threshold choice; value matches train-OOF table.
- 12 exam false alarms persist at every threshold (curl|jq 1.00, cat /etc/hosts .95, echo $PATH .84, base64 -d, aws s3 ls, man rm, history|grep curl, git push origin feature/login, npm install, curl -o, rm -rf node_modules). Cause: shell-safety 'ask' = dangerous; network/etc commands. Data fix only.
- 8g src/shellguard/__init__.py re-exports model_a.predict. tests/test_golden.py: 6 strict xfails with reasons (KNOWN_MISTAKES dict) + test that the dict only names golden commands. make test all green: 136 passed, 6 xfailed.
- 9 CLI src/shellguard/__main__.py: args joined by space or stdin (rstrip \n); one JSON line {command,label,probability}; exit 0 safe / 1 dangerous / 2 usage (stderr). pyproject script -> shellguard.__main__:main. tests/test_cli.py 7 cases incl. no duckdb/torch at startup.
- Startup 1.1 s: sklearn import 0.65 s, joblib.load 0.4 s, predict 0.6 ms. pandas unavoidable: sklearn/utils/fixes.py imports it if installed. duckdb import moved under model_a __main__.
Next (owner-approved order): tree-sitter-bash features as a measured change; then training data for gaps. Possible later: JSON weight export (portable, skips sklearn startup).
<!-- /dolly:step 0010 -->

<!-- dolly:step 0011 -->
## 0011 · 2026-10-24T17:03:52Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/tokens.py`, `tests/test_tokens.py`, `README.md`

Tree-sitter-bash tokenizer trial: tie, kept shlex on main.
- Branch tree-sitter-tokens (commit 2e2dda8): tokens.py rewritten on tree-sitter 0.26 + tree-sitter-bash 0.25.1; 30 token tests pass incl. 11 new (--data="a b" one arg, $var as command name, $( as one op, backticks, heredoc to shell = code / to cat = data, for loops, functions, env assignment, export as cmd, syntax error flagged). 21 us/command, 0 crashes, 545 syntax-error commands on 42,009.
- Numbers @0.35 (same split): test 51/271 vs shlex 56/281; OOF 194/1340 vs 200/1353; golden equal 0/6; hard 1/7 vs 0/8 (git branch -D main 0.37 -> 0.349 now missed; docker system df fixed).
- Probes: cat heredoc 0.97 -> 0.67 (correct), others within 0.05.
- Reason for tie: training data lacks heredocs/loops/obfuscation; char n-grams already cover the rest.
- Decision (owner): keep shlex. Revisit tree-sitter when porting to another language (bindings exist) or after training data adds structure-dependent examples.
Next: training data for known gaps, or JSON export for startup / portability.
<!-- /dolly:step 0011 -->

<!-- dolly:step 0012 -->
## 0012 · 2026-10-25T07:44:26Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/model_a.py`, `tests/test_install.py`, `.gitignore`, `README.md`

uv tool install . produced a shellguard that raised FileNotFoundError: MODEL_PATH was ROOT/models/model_a.joblib, ROOT computed from __file__ parents, which points into site-packages' parent when installed. Fix: MODEL_PATH = Path(__file__).parent / 'model_a.joblib' (git-ignored, uv_build includes it in the wheel; verified with unzip -l). tests/test_install.py builds the wheel, installs into a fresh venv, runs the CLI from tmp dir; asserts stderr empty first because a crash also exits 1. Install test adds ~15 s to make test. README: quick start block, big picture with both datasets + hard.csv, update notes on steps 1/5, current scores table, tree-sitter moved from 'not yet' to 'tried and parked', layout fixed. Models B/C still save to models/.
<!-- /dolly:step 0012 -->
