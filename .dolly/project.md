<!-- dolly project brief · repo-level knowledge, maintained by agents -->
# Project brief — shellguard

> What is true about this codebase. Task-independent.
> Agents: read this before planning. Correct it when you find it wrong —
> a stale brief is worse than none.

## Overview

<!-- ask: What this repo is, who uses it, what it must not stop doing. -->

_TBD_

## Architecture

Model A (char n-gram + shell-token TF-IDF, logistic regression, threshold 0.35) is the shipped model, committed at src/shellguard/model_a.joblib. check() in src/shellguard/check.py is the verdict used by the CLI, the daemon and the pi hook: chain split with tree-sitter-bash (chain.py), harmless plain parts skipped, dangerous if whole OR any non-harmless part >= 0.35. shellguard --serve is a shared daemon on ~/.cache/shellguard/sock (flock single-instance, exits on idle/model change/socket removal). hooks/pi/ is the pi extension, installed by make hook-pi (copy, not symlink).

## Conventions

<!-- ask: How code here is written: patterns to follow, patterns banned, and why. -->

_TBD_

## Invariants

- Model A averages evidence over the whole command: a dangerous part inside a long chain is diluted (rm -rf after safe commands drops from 0.71 to ~0.1). Splitting in check() is the safety net, not cosmetics.
- tree-sitter attaches trailing redirects/heredocs to the whole && list; chain.py gives them to the last command.
- Exam sets data/golden.csv and data/hard.csv are never trained on.
- evaluate.py measures predict() (model alone); check() numbers are measured separately and are in the README.

## Glossary

<!-- ask: Domain words that mean something specific here. -->

_TBD_
