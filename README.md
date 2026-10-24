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

### Step 3 — Prepare: dedupe, label, split ⏳

1. **Dedupe.** Each command appears up to 5× (once per shell: bash, zsh, sh,
   dash, fish). 136,497 rows → 28,296 distinct commands. Keep one row per command.
   13 commands have conflicting labels across copies — rule for those decided in step 3.
   Without this, the same command lands in train *and* test, and the score lies.
2. **Label rule** (one line, the whole definition):
   ```
   dangerous = (reversible == False) OR risk_level in {high, critical}
   ```
   - `not reversible` catches destructive commands.
   - `high/critical` catches malicious ones the dataset marks reversible
     (e.g. adding a user to `wheel`).
   - Expected: ~14.4k dangerous, ~13.9k safe — roughly balanced.
3. **Ignore the dataset's own split.** 22 commands appear in more than one of
   its train/validation/test files. We re-split ourselves.
4. **Split** 80% train / 20% test, *stratified* (same dangerous/safe ratio in
   both), fixed random seed so it is repeatable.
5. **Write** `data/train.parquet`, `data/test.parquet`.

Tests (written first): train and test share no command; both classes present
in both; label rule gives the expected label on hand-picked rows.

### Step 4 — Baseline: a regex list ⏳

A dozen hand-written patterns (`rm -rf /`, `git clean`, `/dev/tcp/`, `| sh`, …).
Not a model. It sets the **number to beat**: if a model can't beat a regex list,
the model is pointless.

### Step 5 — Model A: no base model (TF-IDF + logistic regression) ⏳

Trains from nothing, in seconds, on CPU.

```
"git clean -fdx" ──▶ chop into character pieces   ──▶ count + weight   ──▶ weighted sum ──▶ squash to 0..1
                     "gi","it","t ","cl",…,"-fdx"      (TF-IDF vector)      (logistic        = P(dangerous)
                     (char n-grams, length 2–5)                              regression)
```

- **Character n-grams**: overlapping slices of 2–5 characters. Catches `-rf`,
  `/dev/`, `--force` even inside unseen commands.
- **TF-IDF**: pieces that appear everywhere (like `" "`) get low weight;
  rare telling ones (like `/dev/tcp`) get high weight.
- **Logistic regression**: learns one weight per piece. Positive weight pushes
  toward dangerous. Training = adjust weights to reduce mistakes on train data.
- Expected size < 1 MB. Measured earlier on this Mac: ~215 µs per command, CPU.

### Step 6 — Model B: frozen base model (bge-small embeddings + logistic regression) ⏳

Uses a pretrained model, `BAAI/bge-small-en-v1.5` (33M parameters, 64 MB), via
`fastembed` (ONNX, CPU). It turns each command into 384 numbers that capture
meaning. We do **not** change it; we only train a logistic regression on top.
Measured earlier: ~3.5 ms per command, CPU.

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
.dolly/                  task log (plan, decisions, steps)
```
