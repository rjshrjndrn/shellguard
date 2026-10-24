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
