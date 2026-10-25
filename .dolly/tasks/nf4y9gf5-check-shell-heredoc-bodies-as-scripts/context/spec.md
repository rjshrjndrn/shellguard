<!-- dolly spec · task nf4y9gf5 -->
# Spec — check shell heredoc bodies as scripts

**current: v1** · updated 2026-10-25T17:03:32Z by @rjshrjndrn

<!-- dolly:spec-current -->
<!-- v1 · 2026-10-25T17:03:32Z · @rjshrjndrn -->

bash/sh/zsh/dash (+ -s) reading a quoted heredoc: the body is a shell script but tree-sitter leaves it as one opaque heredoc_body, so destructive()/split_chain never see rm -rf inside; only the model catches it. Strip header/footer and run the body through the same chain checks. Non-shell readers (python, cat) unchanged.
<!-- /dolly:spec-current -->

---

## Superseded versions

<!-- dolly:spec-history -->
_none — v1 is the first spec_
<!-- /dolly:spec-history -->
