.PHONY: help test data prepare eval train

MODEL ?= baseline

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

test: ## run all tests
	uv run pytest -q

data: ## download pinned dataset to data/raw/
	uv run python -m shellguard.data

prepare: ## dedupe + label + split into data/{train,test}.parquet
	uv run python -m shellguard.prepare

train: ## train MODEL into models/ (e.g. make train MODEL=model_a)
	uv run python -m shellguard.$(MODEL)

eval: ## score MODEL (default baseline) on test split + golden set
	uv run python -m shellguard.evaluate $(MODEL)
