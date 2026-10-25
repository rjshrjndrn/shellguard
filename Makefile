.PHONY: help test data prepare eval train install hook-pi unhook-pi

MODEL ?= baseline
PI_EXT ?= $(HOME)/.pi/agent/extensions/shellguard
SG_SOCK ?= $(HOME)/.cache/shellguard/sock

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

test: ## run all tests (python + pi hook)
	uv run pytest -q
	node --test hooks/pi/*.test.ts

data: ## download pinned dataset to data/raw/
	uv run python -m shellguard.data

prepare: ## dedupe + label + split into data/{train,test}.parquet
	uv run python -m shellguard.prepare

train: ## train MODEL into models/ (e.g. make train MODEL=model_a)
	uv run python -m shellguard.$(MODEL)

eval: ## score MODEL (default baseline) on test split + golden set
	uv run python -m shellguard.evaluate $(MODEL)

install: ## install the shellguard CLI globally (python 3.12)
	uv tool install --force --python 3.12 .

hook-pi: install ## install the pi extension into ~/.pi/agent/extensions/shellguard
	rm -rf "$(PI_EXT)"
	mkdir -p "$(PI_EXT)"
	find hooks/pi -maxdepth 1 -name '*.ts' ! -name '*.test.ts' -exec cp {} "$(PI_EXT)/" \;
	rm -f "$(SG_SOCK)"  # running daemon exits; next check starts the new one
	@echo "installed to $(PI_EXT); run /reload in pi (or restart it)"

unhook-pi: ## remove the pi extension and stop the shellguard daemon
	rm -rf "$(PI_EXT)"
	rm -f "$(SG_SOCK)"  # daemon exits within ~1 s once its socket is gone
