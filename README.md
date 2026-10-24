# shellguard

Give it one shell command, get back whether it is **dangerous** or **safe**,
with a probability. Small, local, CPU-only.

```
$ shellguard "git clean -fdx"
{"command": "git clean -fdx", "label": "dangerous", "probability": 0.97}
```
(target output — see [Final output](#final-output); not built yet)

This repo is also a learning project: build a small focused model from zero,
every step written down. Status markers: ✅ done · ⏳ planned.

---

## What "dangerous" means

Dangerous = **malicious** OR **destructive**.

| Kind | Meaning | Examples |
|---|---|---|
| destructive | irreversible loss of data or state | `git clean -fdx`, `git reset --hard`, `git push --force`, `rm -rf ~`, `dd of=/dev/sda` |
| malicious | attack, privilege grab, secret leak, running unverified code | reverse shell, `chmod u+s /bin/bash`, `curl … \| sh`, editing `/etc/sudoers` |
| safe | read-only, routine, or easy to regenerate | `ls`, `git status`, `rm -rf node_modules`, `rm -rf ./build` |

The worst mistake is **missing an irreversible local change**. So we prefer
false alarms over misses: we optimise **recall** on the dangerous class.

---

## The big picture

```
 ┌──────────────────────────── TRAIN (once, on a Mac M1) ───────────────────────────┐
 │                                                                                   │
 │  Hugging Face                                                                     │
 │  yannelli/cli-command-risk ──download──▶ data/raw/*.parquet   (136,497 rows)      │
 │                                              │                                    │
 │                                   dedupe + label rule + split                     │
 │                                              ▼                                    │
 │                         data/train.parquet (80%)   data/test.parquet (20%)        │
 │                                 │                         │                       │
 │                       fit model A / B / C          measure recall/precision       │
 │                                 ▼                         ▲                       │
 │                          models/<file> ───────────────────┘                       │
 │                                                                                   │
 │  data/golden.csv (48 hand-written commands) ── never trained on ── final exam     │
 └───────────────────────────────────────────────────────────────────────────────────┘
                                   │  copy one model file
                                   ▼
 ┌────────────────────── RUN (anywhere, CPU only, no GPU) ──────────────────────┐
 │  shellguard "<cmd>"  ──▶  load model file  ──▶  predict  ──▶  JSON + exit code │
 └──────────────────────────────────────────────────────────────────────────────┘
```

---

## Step by step

### Step 0 — Setup ✅

Needs [uv](https://docs.astral.sh/uv/) (Python package manager). Python 3.12.

```bash
uv sync          # creates .venv/, installs deps from uv.lock
make test        # runs pytest
make help        # lists all make targets
```

How the project was created (for the record):
```bash
git init
uv init --package --name shellguard --python 3.12 --vcs none --no-readme .
uv add --dev pytest
```

### Step 1 — Golden set: write the exam before the model ✅

File: `data/golden.csv` — 48 commands, hand-labelled, columns
`command,label,kind,why`. 25 dangerous (17 destructive, 8 malicious), 23 safe.

Why it exists:
- The training data is **synthetic** (uses `example.com`, `<PATH>`, test IPs).
  A model can learn shortcuts like "`example.com` ⇒ dangerous". The golden set
  uses real-looking commands, so it catches that.
- It is **never** used for training. It is the final exam.
- It is the **spec**. `tests/test_golden.py` says: the shipped model must get
  every one right.

Tests:
- `tests/test_golden_data.py` — file is well-formed: valid labels, no
  duplicates, ≥15 per class, `git clean -fdx` is dangerous, `rm -rf node_modules` is safe.
- `tests/test_golden.py` — one test per command, calls
  `shellguard.predict(cmd)` and expects `{"label": ..., "probability": P(dangerous)}`.

Right now: 4 data tests pass, 48 golden tests **fail** (no model yet). That is
correct — tests first, then code.

### Step 2 — Download the dataset ✅

Source: <https://huggingface.co/datasets/yannelli/cli-command-risk>
License: CC-BY-4.0. Pinned to commit `5e1283ed01fef1ebe7453feaaf058d9cd5767384`
so the data never changes under us.

Files (downloaded to `data/raw/`, git-ignored):
```
https://huggingface.co/datasets/yannelli/cli-command-risk/resolve/5e1283ed01fef1ebe7453feaaf058d9cd5767384/data/train.parquet
https://huggingface.co/datasets/yannelli/cli-command-risk/resolve/5e1283ed01fef1ebe7453feaaf058d9cd5767384/data/validation.parquet
https://huggingface.co/datasets/yannelli/cli-command-risk/resolve/5e1283ed01fef1ebe7453feaaf058d9cd5767384/data/test.parquet
```

Columns we use: `command`, `risk_level` (safe/low/moderate/high/critical),
`reversible` (bool), `risk_categories` (list, for error analysis only).

Why this dataset: it is the only one found that labels **both** destructive and
malicious commands, with a `reversible` flag. Checked against our rule:
`git clean -fdx` → high, not reversible ✓; `rm -rf node_modules` → low,
reversible ✓. Two other datasets (`bash-datasets`, `ShellRisk-Bench`) label
only malicious commands — 115 of 126 `rm -rf`/`dd`/`mkfs` rows there are
labelled *safe*, so we don't use them.

```bash
make data   # runs: uv run python -m shellguard.data
```

What it does (`src/shellguard/data.py`): creates `data/raw/`, downloads the
3 URLs above with Python's `urllib`. No Hugging Face library needed — it's
just 3 HTTP downloads, 1.8 MB total.

Tests (`tests/test_download.py`):
- each file's sha256 equals the hash Hugging Face publishes for that commit
  (proves we got the exact pinned bytes):
  - `train.parquet` `c83a3bdf…`
  - `validation.parquet` `a9015b5f…`
  - `test.parquet` `b4e8335f…`
- the 4 columns we need exist, and there are **136,497 rows** in total.

Found while testing:
- The dataset card says 124,923 rows / 25,702 commands. The real files have
  **136,497 rows / 28,296 distinct commands**. The card is out of date;
  we trust the files.
- 13 commands have conflicting labels across their copies. Step 3 handles them.
- DuckDB 2.0 removed `.fetchone()` on relations; use `.fetchall()`.

### Step 3 — Prepare: dedupe, label, split ✅

```bash
make prepare   # runs: uv run python -m shellguard.prepare
```

Code: `src/shellguard/prepare.py` — one SQL query (DuckDB) + one scikit-learn call.

```
data/raw/*.parquet  136,497 rows
   │ 1. GROUP BY command               → 28,296 commands
   │ 2. drop golden commands           → 28,280   (16 golden cmds were in the data!)
   │ 3. label rule                     → 14,341 dangerous / 13,939 safe
   │ 4. train_test_split(stratify, seed=42)
   ▼
data/train.parquet  22,624 commands  50.7% dangerous
data/test.parquet    5,656 commands  50.7% dangerous
```

1. **Dedupe.** Each command appears up to 5× (once per shell: bash, zsh, sh,
   dash, fish). `GROUP BY command` keeps one row per command. Without this the
   same command lands in train *and* test, and the score lies.
2. **Drop golden commands.** 16 of the 48 golden commands (`git clean -fdx`,
   `rm -rf ~`, `ls -la`, …) appear word-for-word in the dataset. If the model
   trained on them, the golden exam would be an open-book exam. They are removed.
3. **Label rule** — the whole definition:
   ```
   dangerous = (any copy not reversible) OR (any copy is high/critical)
   ```
   - `not reversible` catches destructive commands (`rm -rf /tmp/*`).
   - `high/critical` catches malicious ones the dataset marks reversible
     (`sudo usermod --append --groups wheel admin`).
   - "any copy": 13 commands disagree across their copies (e.g. `chmod +s /bin/bash`
     is reversible in one shell, not in another). We take the most dangerous
     reading — misses are worse than false alarms.
   - `categories` = union of all copies' categories, kept for error analysis only.
4. **Our own split.** The dataset's own train/validation/test files are ignored
   (22 commands sit in more than one). `train_test_split(test_size=0.2,
   stratify=label, random_state=42)`:
   - *stratify* = both parts get the same dangerous/safe ratio (50.7%).
   - *random_state* = fixed seed, so the split is identical every run. Rows are
     sorted by command first, so input order can't change it either.
5. **Write** `data/train.parquet`, `data/test.parquet` (git-ignored, rebuilt by `make prepare`).

Output columns: `command` (str), `label` (`dangerous`/`safe`), `categories` (list).

Tests (`tests/test_prepare.py`, written first, 11 cases): exact columns; one row
per command; train ∩ test = ∅; no golden command in either; 28,280 total;
test = 20% ± 0.1%; same dangerous rate ± 0.5%; label rule on 4 hand-picked
commands; two runs give identical splits.

Known limit — **near-duplicates**: the dataset is template-generated, so
`git push -f origin main` can be in train while `git push -f origin develop` is
in test. Test scores will look better than real life. The golden set (no
templates, never seen) is the honest check.

### Step 4 — Baseline: a regex list ✅

```bash
make eval                 # = make eval MODEL=baseline
```

**What:** `src/shellguard/baseline.py` — 17 hand-written regex patterns
(`rm -rf /`, `mkfs`, `dd of=/dev/`, `git clean -f`, `git reset --hard`,
`git push --force`, `/dev/tcp/`, `| sh`, `chmod u+s`, `/etc/sudoers`, fork
bomb, …). Any match ⇒ dangerous (probability 1.0), else safe (0.0).
Written from general knowledge, **without looking at the test data** — tuning
patterns on the test set would be cheating.

**Why:** it's the number to beat. If a trained model can't beat 17 regexes,
the model is pointless.

**How it's scored** — `src/shellguard/evaluate.py`, used for every model from now on:

```
                    predicted dangerous   predicted safe
 really dangerous         TP                  FN  ← "missed"  (the bad one)
 really safe              FP ← "false alarm"  TN

 recall    = TP / (TP + FN)   of all dangerous commands, how many we caught   ← main number
 precision = TP / (TP + FP)   of everything we flagged, how much was really dangerous
 f1        = harmonic mean of the two
```

`make eval MODEL=<name>` runs `shellguard.<name>.predict` on every
`data/test.parquet` command and every `data/golden.csv` command, times it, and
writes `results/<name>.json` (committed, so models can be compared).

**Result — the floor:**

| | n | recall | precision | f1 | missed | false alarms |
|---|---|---|---|---|---|---|
| test split | 5,656 | **0.236** | 0.920 | 0.375 | 2,192 | 59 |
| golden set | 48 | 0.760 | 1.000 | 0.864 | 6 | 0 |

Speed: ~4 µs/command.

What this teaches:
- **High precision, terrible recall.** When a regex fires it's usually right
  (92%), but it misses 3 of every 4 dangerous commands. Hand rules only catch
  what you thought of.
- **What it misses** (top test categories): data_destruction 734,
  device_overwrite 504 (`cp disk.img /dev/nvme0n1`, `wipefs`), overbroad_permissions 462
  (`chmod --recursive 000`), shell_footgun, credential_exposure.
- **False alarms are subtle:** `mkfs.ext4 -n /dev/sda` is labelled *safe* —
  `-n` is a dry run. A regex can't see that; a model might learn it.
- **Golden 0.76 is flattering.** I wrote both the golden set and the patterns,
  so they share my blind spots. Missed: `git stash clear`, `> ~/.bashrc`,
  `find . -type f -delete`, `docker volume rm`, secret exfil via curl,
  `history -c`. The test split (0.236) is the more honest number here.

Tests (written first): `tests/test_baseline.py` — 7 obvious dangerous, 5 obvious
safe; `tests/test_evaluate.py` — scorer counts/rates on a toy example, no
crash at zero flags, `run()` writes results for both splits.

### Step 5 — Model A: no base model (TF-IDF + logistic regression) ✅

```bash
make train MODEL=model_a   # 2.4 s on M1 CPU → models/model_a.joblib (1.1 MB)
make eval  MODEL=model_a   # → results/model_a.json
```

Code: `src/shellguard/model_a.py` — a 2-step scikit-learn `Pipeline`:

```
"git clean -fdx"
   │ 1. TfidfVectorizer(analyzer="char", ngram_range=(2,5), min_df=2, sublinear_tf=True)
   ▼    chop into every 2–5 char slice: "gi","it",…,"-fdx" → 40,965 possible slices
[0, 0.12, 0, 0.31, …]   one number per slice: how much this command has it, down-weighted
   │                    if the slice is common everywhere (TF-IDF)
   │ 2. LogisticRegression(max_iter=1000)
   ▼    weighted sum of those numbers → squashed to 0..1
P(dangerous) = 0.97   ≥ 0.5 → "dangerous"
```

Settings and why:
- `analyzer="char"` — slices span spaces, so `"-rf /"`, `"| sh"`, `"of=/dev"` are
  features. (`char_wb` would cut at spaces.)
- `ngram_range=(2,5)` — slices of 2 to 5 characters.
- `min_df=2` — ignore slices seen in only 1 command (noise; keeps the file small).
- `sublinear_tf=True` — a slice repeated 10× counts ~3×, not 10×.
- `max_iter=1000` — let the optimiser run long enough to converge.
- Nothing was tuned on the test set or golden set.

**Training** = `pipeline.fit(train_commands, train_labels)`. The vectorizer
learns the slice vocabulary + weights; the logistic regression finds one weight
per slice that best separates dangerous from safe on the 22,624 train commands.

**Saving** = `joblib.dump` → `models/model_a.joblib`. joblib uses pickle, which
can run code on load — fine for a file we built ourselves, never for a
downloaded one. (Step 8 decides the shipped format: JSON weights or ONNX.)

**Result:**

| | test recall | test precision | test F1 | golden recall | golden precision | speed (CPU) | size |
|---|---|---|---|---|---|---|---|
| regex baseline | 0.236 | 0.920 | 0.375 | 0.760 | 1.000 | 4 µs | — |
| **model A** | **0.986** | **0.973** | **0.980** | **0.880** | 0.846 | 250 µs | 1.1 MB |

What this teaches:
- **Learning beats rules:** misses on test dropped from 2,192 to 41.
- **No overfitting:** train recall 0.990 vs test 0.986 — the model isn't just
  memorising its training rows.
- **But test ≠ real life.** Test F1 0.98, golden F1 0.86. The test split comes
  from the same template generator as training; golden doesn't. Golden misses:
  - *data gaps* — never seen in training: fork bomb `:(){ :|:& };:` (0 examples),
    `git stash clear` (0), `kubectl delete namespace` (11 examples).
  - *shortcut learning* — false alarms on `cat /etc/hosts` (0.94),
    `echo $PATH` (0.86), `tar -czf …` (0.69), `rm -rf node_modules` (0.69).
    In training, 90% of commands with `/etc/` and 83% with `echo` are dangerous,
    so the model learned "`/etc/` ⇒ danger" instead of what the command does.
  - Top "dangerous" slices it learned: `' > '`, `'-f'`, `' -r'`, `'*.'` — partly
    real signal, partly template artefacts.
- **Don't fix it by tuning on golden.** If we tweak until golden passes, golden
  stops being an honest exam. Fixes must come from better *training* data or
  a better model (B, C), checked against golden afterwards.

Tests (written first, `tests/test_model_a.py`): learns a 10-row toy set;
output is `{label, probability}` with label = probability ≥ 0.5; save→load gives
identical predictions; trained model's test recall beats the baseline's
(read from committed `results/*.json`).

### Step 6 — Model B: frozen base model (bge-small embeddings + logistic regression) ✅

```bash
make train MODEL=model_b   # 265 s on M1 CPU, 1.3 GB RAM → models/model_b_head.joblib (2 KB)
make eval  MODEL=model_b   # → results/model_b.json
```

Code: `src/shellguard/model_b.py`.

```
"git clean -fdx"
   │ 1. bge-small-en-v1.5  (pretrained by BAAI, 33M weights, FROZEN — we never change it)
   │    run with fastembed = ONNX Runtime, forced to CPUExecutionProvider
   ▼
[0.02, -0.11, …]  384 numbers, length 1 ("embedding" = the command's meaning as a point in space)
   │ 2. LogisticRegression(max_iter=1000)   ← the ONLY part we train: 384 weights + 1
   ▼
P(dangerous)
```

- **Base model**: `BAAI/bge-small-en-v1.5`, downloaded once by fastembed into
  `models/fastembed/` (64 MB, git-ignored). It was trained by someone else on
  huge amounts of English text to put similar-meaning sentences close together.
- **Frozen** = its 33M weights are used as-is. Training only fits the 385
  numbers of the logistic regression on top ("the head"). That's *transfer
  learning*: reuse knowledge, train a tiny bit.
- **CPU-only, enforced**: this Mac also offers CoreML; we pass
  `providers=["CPUExecutionProvider"]` and a test asserts the ONNX session uses
  only that.
- Shipping B means shipping **two** files: the 64 MB base model + the 2 KB head.

**Result:**

| | test recall | test precision | test F1 | golden F1 | golden wrong | speed (CPU) | size | train time |
|---|---|---|---|---|---|---|---|---|
| regex | 0.236 | 0.920 | 0.375 | 0.864 | 6 | 4 µs | — | — |
| **A** no base | **0.986** | **0.973** | **0.980** | **0.863** | 7 | **250 µs** | **1.1 MB** | **2.4 s** |
| **B** frozen base | 0.916 | 0.872 | 0.893 | 0.792 | 11 | 5,575 µs | 64 MB | 265 s |

**B loses to A on every number.** My hypothesis ("meaning will fix the `/etc/`
false alarm") was wrong — data said no. Why:

```
bge-small similarity (1.0 = identical meaning):
  "rm -rf /"        vs "rm -rf ./build"   0.91   ← wipe the disk vs. routine cleanup
  "git clean -fdx"  vs "git clean -n"     0.84   ← irreversible vs. dry run
  "rm -rf /"        vs "ls -la"           0.61
```

- bge-small learned *English sentence* meaning. Shell danger lives in **tiny
  details** — one path, one flag. To the base model, `rm -rf /` and
  `rm -rf ./build` are "the same sentence about deleting".
- The embedding is a lossy squeeze into 384 numbers. Once the detail is
  squeezed out, no head on top can get it back.
- Model A reads raw character slices, so `-n`, `-fdx`, `/` vs `./build` stay visible.
- Lesson: a bigger, "smarter" pretrained model is not automatically better.
  It's better only if what it learned matches your task.

What could make a base model win → **step 7**: *fine-tune* it, i.e. let our
data change its weights so it learns that `/` vs `./build` matters.

Tests (written first, `tests/test_model_b.py`, 6): ONNX session is CPU-only;
embeddings are 384-wide unit vectors; learns the toy set; output shape; save→load
identical; test recall beats the regex baseline.

### Step 7 — Model C: fine-tuned base model ⏳

Same bge-small, but this time we **adjust all its weights** on our data
(training may use the M1 GPU/MPS). Then export to ONNX so it still runs
CPU-only. Optional: if it doesn't beat A/B, it's for learning, not shipping.
Risk: 8 GB RAM — small batches, short sequences.

### Step 8 — Evaluate and pick ⏳

On the same `data/test.parquet` for every model, with GPU/MPS/CoreML disabled:
- **Recall** (of all dangerous commands, how many we caught) — the main number.
- **Precision** (of all we flagged, how many were really dangerous).
- **F1**, confusion matrix, recall per category (destructive vs malicious).
- **Latency** per command, cold start, file size.
- **Golden set**: must pass all 48.
- **Threshold**: default cut is 0.5; we may lower it to trade false alarms for
  fewer misses.

Winner = highest recall that passes the golden set, then smallest/fastest.

### Step 9 — Package: CLI ⏳

`shellguard "<command>"` loads the model file and prints JSON.

---

## Final output

What you get at the end (proposed; format of the model file decided in step 8):

1. **A model file** in `models/` — one file, copied to wherever it runs.
   - Model A: candidates are a JSON file of weights (any language can read it)
     or ONNX (`.onnx`, run with ONNX Runtime).
   - Model B/C: ONNX file(s), ~64 MB.
2. **A CLI** — `shellguard`, installed with `uv tool install .`:
   ```
   $ shellguard "rm -rf node_modules"
   {"command": "rm -rf node_modules", "label": "safe", "probability": 0.04}
   $ echo $?
   0          # proposed: 0 = safe, 1 = dangerous, so scripts/hooks can use it
   ```
3. **A Python function** — `from shellguard import predict` →
   `{"label": "dangerous", "probability": 0.97}`.

It is **not** a standalone compiled binary (yet). Integration target (pi
extension, Go, …) is decided after the model exists.

---

## Layout

```
data/golden.csv          hand-labelled exam (committed)
data/raw/                downloaded parquet (git-ignored)
data/{train,test}.parquet  our split (git-ignored, rebuilt by make)
src/shellguard/          code
tests/                   pytest
models/                  trained files (git-ignored)
results/                 scores per model (committed)
.dolly/                  task log (plan, decisions, steps)
```
