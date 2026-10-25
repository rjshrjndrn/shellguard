<!-- dolly steps · task dfwd3y6f · append-only, newest at the bottom -->
# Full step context — known-safe command list

Short summaries live in `../task.md`. Each entry below is the full context of one step:
decisions and why, options rejected, gotchas, snippets, what to do next.

<!-- dolly:step 0001 -->
## 0001 · 2026-10-25T15:24:54Z · @rjshrjndrn

- task status: working
- files: `src/shellguard/chain.py`, `src/shellguard/check.py`, `tests/test_chain.py`, `tests/test_check.py`, `README.md`

Grew chain.harmless() into a Codex-style known-safe check (openai/codex is_safe_command.rs,
Apache-2.0; idea + names only, own Python).
- READ_ONLY names need literal args (no $VAR, {a,b}, $()) because they read files; HARMLESS
  (echo/cd/ls...) keep allowing variables, as before.
- OPTION_RULES: find w/o -exec/-execdir/-ok/-okdir/-delete/-fls/-fprint*; rg w/o --pre,
  --hostname-bin, --search-zip, -z (incl. clusters like -iz); base64 w/o -o/--output; sed only
  `sed -n Np|M,Np [file]`.
- Pipelines allowed if every stage is safe. Name must be bare (./cat, /tmp/x/cat -> model).
- _SECRET_PATH regex on args: ~/.ssh ~/.aws ~/.kube ~/.docker ~/.gnupg ~/.config/gh, .env*,
  .netrc .git-credentials .npmrc .pypirc, /etc/shadow|gshadow|sudoers, id_rsa..., *.pem *.key
  *.p12 *.pfx, secret(s)/token(s)/credential(s)/password(s) file names. Not tokenizer.py.
- git excluded on purpose: Codex removed git from its safe list 2026-08 (#39524) because repo
  config can make git status run helpers.
Measured (ShellRisk test, never trained): benign flagged 1493 -> 1335 / 4001 (37.3 -> 33.4%);
terminalbench 61.5 -> 58.4%, swesmith 21.9 -> 18.0%, nl2bash 52.4 -> 44.0%. Risky caught
139 -> 137/193 (lost cat /etc/shells, rev /tmp/file | rev; both GTFOBins). golden 25/25,
hard 42/42, our test 4486/4526 dangerous caught.
Why small: remaining non-safe benign parts start with python (1005), find -exec (187), git
(244), echo with redirects, pip, rm, ... ; only 78 would be fixed by allowing 2>/dev/null.
Next lever is retraining on agent traffic (paused; user wants to try this first).
Uncommitted Makefile/tests/test_install.py (--compile-bytecode) predate this task; left alone.
Scratch scripts: /tmp/srb/measure.py, /tmp/srb/allow.py.
<!-- /dolly:step 0001 -->
