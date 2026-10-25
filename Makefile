.PHONY: help test data prepare eval train install hook-pi unhook-pi hook-claude unhook-claude

MODEL ?= baseline
PI_EXT ?= $(HOME)/.pi/agent/extensions/shellguard
SG_SOCK ?= $(HOME)/.cache/shellguard/sock
CLAUDE_HOOK ?= $(HOME)/.claude/hooks/shellguard
CLAUDE_SETTINGS ?= $(HOME)/.claude/settings.json
# our PreToolUse entry is the one whose command runs .../shellguard/claude/hook.ts
SG_NOT_OURS = map(select([.hooks[]?.command // "" | contains("shellguard/claude/hook.ts")] | any | not))

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

test: ## run all tests (python + pi and claude hooks)
	uv run pytest -q
	node --test hooks/pi/*.test.ts hooks/claude/*.test.ts

data: ## download pinned dataset to data/raw/
	uv run python -m shellguard.data

prepare: ## dedupe + label + split into data/{train,test}.parquet
	uv run python -m shellguard.prepare

train: ## train MODEL into models/ (e.g. make train MODEL=model_a)
	uv run python -m shellguard.$(MODEL)

eval: ## score MODEL (default baseline) on test split + golden set
	uv run python -m shellguard.evaluate $(MODEL)

install: ## install the shellguard CLI globally (python 3.12)
	uv tool install --force --compile-bytecode --python 3.12 .

hook-pi: install ## install the pi extension into ~/.pi/agent/extensions/shellguard
	rm -rf "$(PI_EXT)"
	mkdir -p "$(PI_EXT)"
	find hooks/pi -maxdepth 1 -name '*.ts' ! -name '*.test.ts' -exec cp {} "$(PI_EXT)/" \;
	rm -f "$(SG_SOCK)"  # running daemon exits; next check starts the new one
	@echo "installed to $(PI_EXT); run /reload in pi (or restart it)"

unhook-pi: ## remove the pi extension and stop the shellguard daemon
	rm -rf "$(PI_EXT)"
	rm -f "$(SG_SOCK)"  # daemon exits within ~1 s once its socket is gone

hook-claude: install ## install the Claude Code hook (global ~/.claude/settings.json)
	@test -f "$(CLAUDE_SETTINGS)" || { mkdir -p "$(dir $(CLAUDE_SETTINGS))" && echo '{}' > "$(CLAUDE_SETTINGS)"; }
	jq --arg cmd 'node "$(CLAUDE_HOOK)/claude/hook.ts"' \
	  '.hooks.PreToolUse = ((.hooks.PreToolUse // []) | $(SG_NOT_OURS)) + [{matcher: "Bash", hooks: [{type: "command", command: $$cmd, timeout: 10}]}]' \
	  "$(CLAUDE_SETTINGS)" > "$(CLAUDE_SETTINGS).sg-tmp" || { rm -f "$(CLAUDE_SETTINGS).sg-tmp"; exit 1; }
	rm -rf "$(CLAUDE_HOOK)"
	mkdir -p "$(CLAUDE_HOOK)/pi" "$(CLAUDE_HOOK)/claude"
	cp hooks/pi/client.ts hooks/pi/decide.ts "$(CLAUDE_HOOK)/pi/"
	cp hooks/claude/hook.ts "$(CLAUDE_HOOK)/claude/"
	cat "$(CLAUDE_SETTINGS).sg-tmp" > "$(CLAUDE_SETTINGS)" && rm "$(CLAUDE_SETTINGS).sg-tmp"  # keeps symlinks
	rm -f "$(SG_SOCK)"  # running daemon exits; next check starts the new one
	@echo "installed to $(CLAUDE_HOOK), registered in $(CLAUDE_SETTINGS); new Claude Code sessions pick it up"

unhook-claude: ## remove the Claude Code hook (other hooks untouched)
	rm -rf "$(CLAUDE_HOOK)"
	@if [ -f "$(CLAUDE_SETTINGS)" ]; then \
	  jq 'if .hooks.PreToolUse then .hooks.PreToolUse |= $(SG_NOT_OURS) | (if .hooks.PreToolUse == [] then del(.hooks.PreToolUse) else . end) else . end' \
	    "$(CLAUDE_SETTINGS)" > "$(CLAUDE_SETTINGS).sg-tmp" || { rm -f "$(CLAUDE_SETTINGS).sg-tmp"; exit 1; }; \
	  cat "$(CLAUDE_SETTINGS).sg-tmp" > "$(CLAUDE_SETTINGS)" && rm "$(CLAUDE_SETTINGS).sg-tmp"; \
	fi
