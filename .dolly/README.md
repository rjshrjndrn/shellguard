# .dolly — shared task memory

Written and read by coding agents via the `dolly` CLI (`npm i -g dolly`).
Commit this directory: it is how the next session — yours or a teammate's —
knows what was decided and why.

- `tasks/<id>-slug/task.md` — short spec, success criteria, and a one-line-per-event
  log. Start here. Every line is stamped with the GitHub handle of whoever did it.
- `tasks/<id>-slug/context/spec.md` — current full spec at the top, every
  superseded version below it under "Superseded versions".
- `tasks/<id>-slug/context/steps.md` — full context of each step, append-only:
  decisions, rejected options, gotchas, what to do next.
- `tasks/<id>-slug/context/plan.md` — the planning interview, when there was one.

Read with `dolly board`, `dolly show <ref>`, `dolly context <ref>`.
Do not hand-edit these files — the CLI maintains frontmatter, spec versions and
step counters.
